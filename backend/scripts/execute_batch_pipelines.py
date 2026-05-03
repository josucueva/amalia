"""
Execute generated AMALIA batch exports by replaying pipeline MCP tools in order.

This script runs each workflow phase/tool sequentially and propagates runtime outputs
between tools to produce deterministic and reproducible batch metrics.
"""

from __future__ import annotations

import argparse
import inspect
import json
import math
import os
import pickle
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import Lasso, LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import GridSearchCV, cross_val_score, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_classif, f_regression


@dataclass
class PipelineRunResult:
    dataset_id: str
    artifact_file: str
    task_type: str
    target_column: Optional[str]
    model_type: Optional[str]
    status: str
    error: Optional[str]
    metrics: Dict[str, Any]


@dataclass
class PipelineExecutionContext:
    dataset_id: str
    artifact_path: Path
    output_models_dir: Path
    current_dataset_path: Optional[Path]
    current_model_path: Optional[Path] = None
    current_test_indices_file: Optional[Path] = None
    task_type: str = "unknown"
    target_column: Optional[str] = None
    model_type: Optional[str] = None
    last_training_metrics: Optional[Dict[str, Any]] = None
    last_evaluation_metrics: Optional[Dict[str, Any]] = None
    path_notes: List[str] = None

    def __post_init__(self) -> None:
        if self.path_notes is None:
            self.path_notes = []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute generated batch pipelines")
    parser.add_argument(
        "--batch-dir",
        required=True,
        help="Path to batch export folder (e.g., ../data/batch_exports/batch_...)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for run results. Default: ../data/batch_results/<batch_name>",
    )
    return parser.parse_args()


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def uploads_root() -> Path:
    return backend_root() / "data" / "uploads"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_artifact_path(raw_path: str) -> Path:
    value = str(raw_path).strip()
    path = Path(value)
    if path.exists():
        return path

    normalized = value.replace("\\", "/")
    if normalized.startswith("/app/"):
        suffix = normalized[len("/app/") :]
        candidate = backend_root() / Path(suffix)
        if candidate.exists():
            return candidate

    candidate = uploads_root() / Path(value).name
    if candidate.exists():
        return candidate

    return path


def resolve_input_path(raw_path: str) -> Path:
    path = resolve_artifact_path(raw_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {raw_path}")
    return path


def resolve_output_path(raw_path: Optional[str], default_name: str) -> Path:
    if raw_path:
        value = str(raw_path).strip()
        normalized = value.replace("\\", "/")
        if normalized.startswith("/app/"):
            candidate = backend_root() / Path(normalized[len("/app/") :])
        else:
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = uploads_root() / candidate
    else:
        candidate = uploads_root() / default_name

    ensure_parent(candidate)
    return candidate


def maybe_unwrap_transformed_filename(raw_path: str) -> Optional[str]:
    normalized = str(raw_path).replace("\\", "/")
    if not normalized.lower().endswith(".csv"):
        return None

    filename = Path(normalized).name
    stem = Path(filename).stem
    suffix_patterns = [
        r"_scaled$",
        r"_encoded$",
        r"_preprocessed$",
        r"_cleaned$",
        r"_train$",
        r"_test$",
    ]
    updated = stem
    for pattern in suffix_patterns:
        updated = re.sub(pattern, "", updated, flags=re.IGNORECASE)

    if updated == stem:
        return None
    return str(Path(normalized).with_name(f"{updated}.csv"))


def collect_candidate_filepaths(
    payload: Dict[str, Any],
    workflow: Dict[str, Any],
    primary_filepath: Optional[str],
) -> List[str]:
    candidates: List[str] = []
    if primary_filepath:
        candidates.append(str(primary_filepath))

    payload_filepath = payload.get("file_path")
    if payload_filepath:
        candidates.append(str(payload_filepath))

    for step in workflow.get("steps", []):
        for tool in step.get("tools", []):
            params = tool.get("tool_parameters") or {}
            if not isinstance(params, dict):
                continue
            for key in ("filepath", "test_data_path", "input_data_path"):
                value = params.get(key)
                if value:
                    candidates.append(str(value))

    deduped: List[str] = []
    seen = set()
    for candidate in candidates:
        marker = candidate.replace("\\", "/").strip().lower()
        if not marker or marker in seen:
            continue
        seen.add(marker)
        deduped.append(candidate)
    return deduped


def resolve_dataset_file(
    requested_path: Optional[str],
    candidates: List[str],
) -> Tuple[Optional[Path], Optional[str]]:
    checked: List[str] = []

    def _attempt(raw: Optional[str]) -> Optional[Path]:
        if not raw:
            return None
        checked.append(str(raw))
        resolved = resolve_artifact_path(str(raw))
        return resolved if resolved.exists() else None

    direct = _attempt(requested_path)
    if direct:
        return direct, None

    transformed_hint = maybe_unwrap_transformed_filename(str(requested_path or ""))
    if transformed_hint:
        transformed_candidate = _attempt(transformed_hint)
        if transformed_candidate:
            return (
                transformed_candidate,
                f"Recovered source dataset path from transformed filename: {requested_path}",
            )

    for candidate in candidates:
        resolved = _attempt(candidate)
        if resolved:
            return resolved, f"Used fallback candidate filepath: {candidate}"

    attempted = ", ".join(checked[:8]) if checked else "<none>"
    return None, f"Dataset file not found. attempted_paths=[{attempted}]"


def normalize_model_type(model_type: Optional[str], task_type: str) -> str:
    mt = (model_type or "").strip().lower()
    if mt in {"", "none", "null"}:
        return ""

    aliases = {
        "random_forest_classifier": "random_forest",
        "random_forest_regressor": "random_forest",
        "linear_regression": "linear",
        "logistic_regression": "logistic",
        "svc": "svm",
        "kneighbors": "knn",
    }
    normalized = aliases.get(mt, mt)
    if task_type == "regression" and normalized == "svm":
        return "svr"
    return normalized


def sanitize_hyperparameters(
    task_type: str, model_type: str, hyperparameters: Dict[str, Any]
) -> Dict[str, Any]:
    allowed: Dict[Tuple[str, str], set[str]] = {
        ("classification", "logistic"): {"max_iter", "C", "solver", "penalty", "class_weight"},
        ("classification", "decision_tree"): {"max_depth", "min_samples_split", "min_samples_leaf", "criterion"},
        ("classification", "random_forest"): {"n_estimators", "max_depth", "min_samples_split", "min_samples_leaf", "criterion", "max_features"},
        ("classification", "svm"): {"C", "kernel", "gamma", "degree", "class_weight"},
        ("classification", "knn"): {"n_neighbors", "weights", "metric"},
        ("classification", "naive_bayes"): {"var_smoothing"},
        ("classification", "gradient_boosting"): {"n_estimators", "learning_rate", "max_depth", "subsample"},
        ("regression", "linear"): {"fit_intercept", "positive"},
        ("regression", "ridge"): {"alpha", "fit_intercept", "solver"},
        ("regression", "lasso"): {"alpha", "fit_intercept", "max_iter"},
        ("regression", "decision_tree"): {"max_depth", "min_samples_split", "min_samples_leaf", "criterion"},
        ("regression", "random_forest"): {"n_estimators", "max_depth", "min_samples_split", "min_samples_leaf", "criterion", "max_features"},
        ("regression", "svr"): {"C", "kernel", "gamma", "degree", "epsilon"},
        ("regression", "knn"): {"n_neighbors", "weights", "metric"},
        ("regression", "gradient_boosting"): {"n_estimators", "learning_rate", "max_depth", "subsample"},
    }
    whitelist = allowed.get((task_type, model_type))
    if not whitelist:
        return {}
    return {k: v for k, v in (hyperparameters or {}).items() if k in whitelist}


def get_server_info_tool(
    tool: Optional[str] = None,
    server: Optional[str] = None,
    arguments: Optional[Any] = None,
    filepath: Optional[str] = None,
) -> dict:
    files = sorted(str(p) for p in uploads_root().glob("**/*") if p.is_file())[:100]
    return {
        "success": True,
        "tool": tool,
        "server": server,
        "arguments": arguments,
        "filepath": filepath,
        "data_directory": str(uploads_root()),
        "data_dir_exists": uploads_root().exists(),
        "available_files": files,
        "file_count": len(files),
        "working_directory": str(Path.cwd()),
    }


def get_column_info_tool(filepath: str, column_name: str) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    if column_name not in df.columns:
        return {"error": f"Column '{column_name}' not found"}
    col = df[column_name]
    return {
        "column_name": column_name,
        "dtype": str(col.dtype),
        "null_count": int(col.isna().sum()),
        "unique_count": int(col.nunique(dropna=True)),
        "sample_values": col.dropna().head(10).tolist(),
    }


def detect_missing_values_tool(filepath: str) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    missing = {col: int(val) for col, val in df.isna().sum().items() if int(val) > 0}
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "total_missing": int(df.isna().sum().sum()),
        "missing_values": missing,
    }


def detect_duplicates_tool(filepath: str, subset: Optional[List[str]] = None) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    duplicates = df.duplicated(subset=subset).sum()
    return {
        "rows": len(df),
        "subset": subset,
        "duplicate_rows": int(duplicates),
        "duplicate_ratio": float(duplicates / max(1, len(df))),
    }


def infer_data_types_tool(filepath: str) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    return {"data_types": {col: str(dtype) for col, dtype in df.dtypes.items()}}


def get_basic_stats_tool(filepath: str) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "basic_stats": df.describe(include="all").fillna("").to_dict(),
    }


def read_file_head_tool(filepath: str, n_rows: int = 10) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    return {"head": df.head(max(1, int(n_rows))).to_dict(orient="records")}


def validate_csv_structure_tool(
    filepath: str,
    expected_columns: Optional[List[str]] = None,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    current_columns = df.columns.tolist()
    if not expected_columns:
        return {"valid": True, "columns": current_columns}
    missing = [col for col in expected_columns if col not in current_columns]
    return {
        "valid": len(missing) == 0,
        "missing_columns": missing,
        "columns": current_columns,
    }


def rename_columns_tool(
    filepath: str,
    column_mapping: Dict[str, str],
    output_filepath: Optional[str] = None,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    renamed = df.rename(columns=column_mapping)
    saved_to = None
    if output_filepath:
        out_path = resolve_output_path(output_filepath, Path(filepath).name)
        renamed.to_csv(out_path, index=False)
        saved_to = str(out_path)
    return {"saved_to": saved_to, "columns": renamed.columns.tolist()}


def add_column_headers_tool(
    filepath: str,
    column_names: List[str],
    output_filepath: Optional[str] = None,
    has_header: bool = False,
) -> dict:
    header = 0 if has_header else None
    df = pd.read_csv(resolve_input_path(filepath), header=header)
    if len(column_names) != len(df.columns):
        return {"error": "Provided column_names length does not match dataset columns"}
    df.columns = column_names
    saved_to = None
    if output_filepath:
        out_path = resolve_output_path(output_filepath, Path(filepath).name)
        df.to_csv(out_path, index=False)
        saved_to = str(out_path)
    return {"saved_to": saved_to, "columns": df.columns.tolist()}


def detect_outliers_tool(
    filepath: str, column: str, method: str = "iqr", threshold: float = 1.5
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if method == "zscore":
        std = series.std() or 1.0
        z = ((series - series.mean()) / std).abs()
        outlier_indices = series.index[z > threshold].tolist()
    else:
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - threshold * iqr
        upper = q3 + threshold * iqr
        mask = (series < lower) | (series > upper)
        outlier_indices = series.index[mask].tolist()
    return {"column": column, "method": method, "outliers": outlier_indices}


def create_feature_bins_tool(
    filepath: str,
    column: str,
    bins: int = 5,
    labels: Optional[List[str]] = None,
    output_filepath: Optional[str] = None,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    binned_col = f"{column}_binned"
    df[binned_col] = pd.cut(pd.to_numeric(df[column], errors="coerce"), bins=bins, labels=labels)
    saved_to = None
    if output_filepath:
        out_path = resolve_output_path(output_filepath, Path(filepath).name)
        df.to_csv(out_path, index=False)
        saved_to = str(out_path)
    return {"binned_column": binned_col, "saved_to": saved_to}


def analyze_csv_tool(filename: str) -> dict:
    return load_csv_tool(filename)


def _math_binary_tool(a: float, b: float, op: str) -> dict:
    if op == "add":
        result = a + b
    elif op == "subtract":
        result = a - b
    elif op == "multiply":
        result = a * b
    elif op == "divide":
        if b == 0:
            return {"error": "Division by zero"}
        result = a / b
    elif op == "power":
        result = a**b
    else:
        return {"error": f"Unsupported operation '{op}'"}
    return {"result": result}


def add_tool(a: float, b: float) -> dict:
    return _math_binary_tool(a, b, "add")


def subtract_tool(a: float, b: float) -> dict:
    return _math_binary_tool(a, b, "subtract")


def multiply_tool(a: float, b: float) -> dict:
    return _math_binary_tool(a, b, "multiply")


def divide_tool(a: float, b: float) -> dict:
    return _math_binary_tool(a, b, "divide")


def power_tool(base: float, exponent: float) -> dict:
    return {"result": base**exponent}


def square_root_tool(number: float) -> dict:
    if number < 0:
        return {"error": "Cannot take square root of negative number"}
    return {"result": math.sqrt(number)}


def factorial_tool(n: int) -> dict:
    if n < 0:
        return {"error": "Factorial is undefined for negative numbers"}
    return {"result": math.factorial(n)}


def mean_tool(numbers: List[float]) -> dict:
    if not numbers:
        return {"error": "numbers cannot be empty"}
    return {"result": float(np.mean(numbers))}


def median_tool(numbers: List[float]) -> dict:
    if not numbers:
        return {"error": "numbers cannot be empty"}
    return {"result": float(np.median(numbers))}


def standard_deviation_tool(numbers: List[float]) -> dict:
    if not numbers:
        return {"error": "numbers cannot be empty"}
    return {"result": float(np.std(numbers))}


def percentage_tool(part: float, whole: float) -> dict:
    if whole == 0:
        return {"error": "whole cannot be zero"}
    return {"result": float((part / whole) * 100.0)}


def gcd_tool(a: int, b: int) -> dict:
    return {"result": math.gcd(int(a), int(b))}


def lcm_tool(a: int, b: int) -> dict:
    return {"result": abs(int(a * b)) // math.gcd(int(a), int(b))}


def load_csv_tool(filepath: str, encoding: str = "utf-8", delimiter: str = ",") -> dict:
    df = pd.read_csv(resolve_input_path(filepath), encoding=encoding, delimiter=delimiter)
    return {
        "success": True,
        "filepath": filepath,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "sample_data": df.head(5).to_dict(orient="records"),
        "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB",
    }


def handle_missing_values_tool(
    filepath: str,
    strategy: str = "mean",
    columns: Optional[List[str]] = None,
    output_filepath: Optional[str] = None,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    original_rows = len(df)

    if strategy == "drop":
        df = df.dropna(subset=columns) if columns else df.dropna()
        rows_removed = original_rows - len(df)
        result = {
            "strategy": "drop",
            "rows_removed": rows_removed,
            "remaining_rows": len(df),
        }
    else:
        if columns is None:
            columns = df.columns[df.isna().any()].tolist()

        filled_columns = []
        for col in columns:
            if col not in df.columns or not df[col].isna().any():
                continue
            if strategy in {"mean", "median"} and pd.api.types.is_numeric_dtype(df[col]):
                fill_value = df[col].mean() if strategy == "mean" else df[col].median()
                df[col] = df[col].fillna(fill_value)
                filled_columns.append(col)
            elif strategy == "mode":
                mode = df[col].mode()
                df[col] = df[col].fillna(mode.iloc[0] if len(mode) > 0 else 0)
                filled_columns.append(col)
            elif strategy == "constant":
                df[col] = df[col].fillna(0)
                filled_columns.append(col)

        result = {
            "strategy": strategy,
            "columns_filled": filled_columns,
            "total_filled": len(filled_columns),
        }

    if output_filepath:
        out_path = resolve_output_path(output_filepath, Path(filepath).name)
        df.to_csv(out_path, index=False)
        result["saved_to"] = str(out_path)

    result["remaining_missing"] = int(df.isna().sum().sum())
    return result


def remove_duplicates_tool(
    filepath: str,
    subset: Optional[List[str]] = None,
    keep: str = "first",
    output_filepath: Optional[str] = None,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    original_rows = len(df)
    keep_param = keep if keep != "none" else False
    cleaned = df.drop_duplicates(subset=subset, keep=keep_param)
    removed = original_rows - len(cleaned)

    saved_to = None
    if output_filepath:
        out_path = resolve_output_path(output_filepath, Path(filepath).name)
        cleaned.to_csv(out_path, index=False)
        saved_to = str(out_path)

    return {
        "original_rows": original_rows,
        "duplicates_removed": removed,
        "remaining_rows": len(cleaned),
        "saved_to": saved_to,
    }


def scale_features_tool(
    filepath: str,
    columns: List[str],
    method: str = "standard",
    output_filepath: Optional[str] = None,
) -> dict:
    from sklearn.preprocessing import MinMaxScaler, StandardScaler

    df = pd.read_csv(resolve_input_path(filepath))
    valid_columns = [
        col for col in columns if col in df.columns and pd.api.types.is_numeric_dtype(df[col])
    ]
    if not valid_columns:
        return {"error": "No valid numeric columns found"}

    scaler = StandardScaler() if method == "standard" else MinMaxScaler()
    df[valid_columns] = scaler.fit_transform(df[valid_columns])

    saved_to = None
    if output_filepath:
        out_path = resolve_output_path(output_filepath, Path(filepath).name)
        df.to_csv(out_path, index=False)
        saved_to = str(out_path)

    return {"method": method, "columns_scaled": valid_columns, "saved_to": saved_to}


def encode_categorical_tool(
    filepath: str,
    columns: List[str],
    method: str = "onehot",
    output_filepath: Optional[str] = None,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    encoded_columns: List[str] = []

    for col in columns:
        if col not in df.columns:
            continue
        if method == "label":
            from sklearn.preprocessing import LabelEncoder

            encoder = LabelEncoder()
            df[col] = encoder.fit_transform(df[col].astype(str))
            encoded_columns.append(col)
        elif method == "onehot":
            cardinality = int(df[col].nunique(dropna=True))
            if cardinality > 50:
                from sklearn.preprocessing import LabelEncoder

                encoder = LabelEncoder()
                df[col] = encoder.fit_transform(df[col].astype(str))
                encoded_columns.append(col)
                continue
            dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
            df = pd.concat([df, dummies], axis=1)
            df.drop(col, axis=1, inplace=True)
            encoded_columns.append(col)
            encoded_columns.extend(dummies.columns.tolist())

    saved_to = None
    if output_filepath:
        out_path = resolve_output_path(output_filepath, Path(filepath).name)
        df.to_csv(out_path, index=False)
        saved_to = str(out_path)

    return {
        "method": method,
        "original_columns": columns,
        "result_columns": encoded_columns,
        "new_shape": {"rows": len(df), "columns": len(df.columns)},
        "saved_to": saved_to,
    }


def split_dataset_tool(
    filepath: str,
    train_ratio: float = 0.8,
    random_state: int = 42,
    shuffle: bool = True,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    if shuffle:
        df = df.sample(frac=1, random_state=random_state).reset_index(drop=True)

    split_idx = int(len(df) * train_ratio)
    train_df = df[:split_idx]
    test_df = df[split_idx:]

    base_name = Path(filepath).stem
    train_path = resolve_output_path(None, f"{base_name}_train.csv")
    test_path = resolve_output_path(None, f"{base_name}_test.csv")
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    return {
        "original_rows": len(df),
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "train_ratio": train_ratio,
        "train_path": str(train_path),
        "test_path": str(test_path),
    }


def filter_rows_tool(
    filepath: str,
    column: str,
    condition: str,
    value: Any,
    output_filepath: Optional[str] = None,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    original_rows = len(df)
    if condition == "eq":
        filtered = df[df[column] == value]
    elif condition == "ne":
        filtered = df[df[column] != value]
    elif condition == "gt":
        filtered = df[df[column] > value]
    elif condition == "lt":
        filtered = df[df[column] < value]
    elif condition == "gte":
        filtered = df[df[column] >= value]
    elif condition == "lte":
        filtered = df[df[column] <= value]
    elif condition == "contains":
        filtered = df[df[column].astype(str).str.contains(str(value), na=False)]
    else:
        return {"error": f"Unknown condition: {condition}"}

    saved_to = None
    if output_filepath:
        out_path = resolve_output_path(output_filepath, Path(filepath).name)
        filtered.to_csv(out_path, index=False)
        saved_to = str(out_path)

    return {
        "original_rows": original_rows,
        "filtered_rows": len(filtered),
        "rows_removed": original_rows - len(filtered),
        "condition": f"{column} {condition} {value}",
        "saved_to": saved_to,
    }


def _encode_features(df: pd.DataFrame) -> pd.DataFrame:
    encoded = df.copy()
    for col in encoded.select_dtypes(include=["object"]).columns:
        encoded[col] = pd.factorize(encoded[col])[0]
    return encoded


def _build_classification_model(
    model_type: str, random_state: int, hyperparameters: Dict[str, Any]
):
    if model_type == "logistic":
        kwargs = {"max_iter": 1000, "random_state": random_state}
        kwargs.update(hyperparameters)
        return LogisticRegression(**kwargs)
    if model_type == "decision_tree":
        kwargs = {"random_state": random_state}
        kwargs.update(hyperparameters)
        return DecisionTreeClassifier(**kwargs)
    if model_type == "random_forest":
        kwargs = {"n_estimators": 100, "random_state": random_state}
        kwargs.update(hyperparameters)
        return RandomForestClassifier(**kwargs)
    if model_type == "svm":
        kwargs = {"random_state": random_state}
        kwargs.update(hyperparameters)
        return SVC(**kwargs)
    if model_type == "knn":
        return KNeighborsClassifier(**hyperparameters)
    if model_type == "naive_bayes":
        return GaussianNB(**hyperparameters)
    if model_type == "gradient_boosting":
        kwargs = {"random_state": random_state}
        kwargs.update(hyperparameters)
        return GradientBoostingClassifier(**kwargs)
    return None


def _build_regression_model(
    model_type: str, random_state: int, hyperparameters: Dict[str, Any]
):
    if model_type == "linear":
        return LinearRegression(**hyperparameters)
    if model_type == "ridge":
        kwargs = {"random_state": random_state}
        kwargs.update(hyperparameters)
        return Ridge(**kwargs)
    if model_type == "lasso":
        kwargs = {"random_state": random_state}
        kwargs.update(hyperparameters)
        return Lasso(**kwargs)
    if model_type == "decision_tree":
        kwargs = {"random_state": random_state}
        kwargs.update(hyperparameters)
        return DecisionTreeRegressor(**kwargs)
    if model_type == "random_forest":
        kwargs = {"n_estimators": 100, "random_state": random_state}
        kwargs.update(hyperparameters)
        return RandomForestRegressor(**kwargs)
    if model_type == "svr":
        return SVR(**hyperparameters)
    if model_type == "knn":
        return KNeighborsRegressor(**hyperparameters)
    if model_type == "gradient_boosting":
        kwargs = {"random_state": random_state}
        kwargs.update(hyperparameters)
        return GradientBoostingRegressor(**kwargs)
    return None


def train_classification_model_tool(
    filepath: str,
    target_column: str,
    model_type: str = "random_forest",
    test_size: float = 0.2,
    random_state: int = 42,
    hyperparameters: Optional[Dict[str, Any]] = None,
    model_save_path: Optional[str] = None,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}

    X = _encode_features(df.drop(columns=[target_column]))
    y = df[target_column]
    if len(X) > 20000:
        sampled = X.sample(n=20000, random_state=random_state)
        y = y.loc[sampled.index]
        X = sampled
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    hp = sanitize_hyperparameters(
        "classification",
        normalize_model_type(model_type, "classification"),
        dict(hyperparameters or {}),
    )
    if "n_estimators" in hp:
        hp["n_estimators"] = min(int(hp["n_estimators"]), 100)
    model = _build_classification_model(model_type, random_state, hp)
    if model is None:
        return {"error": f"Unknown model type: {model_type}"}

    try:
        model.fit(X_train, y_train)
    except TypeError as exc:
        return {
            "error": f"Invalid hyperparameters for model '{model_type}': {str(exc)}",
            "model_type": model_type,
            "hyperparameters": hp,
        }

    train_score = float(model.score(X_train, y_train))
    test_score = float(model.score(X_test, y_test))
    saved_to = None
    test_indices_file = None
    if model_save_path:
        out_path = resolve_output_path(model_save_path, "model.pkl")
        with open(out_path, "wb") as file:
            pickle.dump(model, file)
        saved_to = str(out_path)
        
        # Save test set indices for later evaluation
        indices_path = str(out_path).replace('.pkl', '_test_indices.json')
        test_indices = list(X_test.index)
        with open(indices_path, 'w') as f:
            json.dump(test_indices, f)
        test_indices_file = str(indices_path)

    return {
        "model_type": model_type,
        "task": "classification",
        "train_accuracy": round(train_score, 4),
        "test_accuracy": round(test_score, 4),
        "overfitting_gap": round(train_score - test_score, 4),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "features": X.columns.tolist(),
        "n_classes": int(len(np.unique(y))),
        "model_saved": saved_to,
        "test_indices_file": test_indices_file,
    }


def train_regression_model_tool(
    filepath: str,
    target_column: str,
    model_type: str = "random_forest",
    test_size: float = 0.2,
    random_state: int = 42,
    hyperparameters: Optional[Dict[str, Any]] = None,
    model_save_path: Optional[str] = None,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}

    X = _encode_features(df.drop(columns=[target_column]))
    y = df[target_column]
    if len(X) > 20000:
        sampled = X.sample(n=20000, random_state=random_state)
        y = y.loc[sampled.index]
        X = sampled
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    hp = sanitize_hyperparameters(
        "regression",
        normalize_model_type(model_type, "regression"),
        dict(hyperparameters or {}),
    )
    if "n_estimators" in hp:
        hp["n_estimators"] = min(int(hp["n_estimators"]), 100)
    model = _build_regression_model(model_type, random_state, hp)
    if model is None:
        return {"error": f"Unknown model type: {model_type}"}

    try:
        model.fit(X_train, y_train)
    except TypeError as exc:
        return {
            "error": f"Invalid hyperparameters for model '{model_type}': {str(exc)}",
            "model_type": model_type,
            "hyperparameters": hp,
        }

    train_r2 = float(model.score(X_train, y_train))
    test_r2 = float(model.score(X_test, y_test))
    y_pred = model.predict(X_test)
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(y_test, y_pred))

    saved_to = None
    test_indices_file = None
    if model_save_path:
        out_path = resolve_output_path(model_save_path, "model.pkl")
        with open(out_path, "wb") as file:
            pickle.dump(model, file)
        saved_to = str(out_path)
        
        # Save test set indices for later evaluation
        indices_path = str(out_path).replace('.pkl', '_test_indices.json')
        test_indices = list(X_test.index)
        with open(indices_path, 'w') as f:
            json.dump(test_indices, f)
        test_indices_file = str(indices_path)

    return {
        "model_type": model_type,
        "task": "regression",
        "train_r2": round(train_r2, 4),
        "test_r2": round(test_r2, 4),
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "mse": round(mse, 4),
        "overfitting_gap": round(train_r2 - test_r2, 4),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "features": X.columns.tolist(),
        "model_saved": saved_to,
        "test_indices_file": test_indices_file,
    }


def evaluate_classification_model_tool(
    model_path: str, test_data_path: str, target_column: str, test_indices_file: str = None
) -> dict:
    with open(resolve_input_path(model_path), "rb") as file:
        model = pickle.load(file)

    df = pd.read_csv(resolve_input_path(test_data_path))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}

    # Filter to only test set if indices file is provided
    if test_indices_file:
        try:
            indices_path = resolve_input_path(test_indices_file)
            if os.path.exists(indices_path):
                with open(indices_path, 'r') as f:
                    test_indices = json.load(f)
                df = df.iloc[test_indices]  # Filter to only test set
        except Exception as e:
            print(f"Warning: Could not load test indices: {e}")
            pass

    X_test = _encode_features(df.drop(columns=[target_column]))
    y_test = df[target_column]
    y_pred = model.predict(X_test)

    accuracy = float(accuracy_score(y_test, y_pred))
    is_binary = len(np.unique(y_test)) == 2
    if is_binary:
        precision = float(precision_score(y_test, y_pred, average="binary"))
        recall = float(recall_score(y_test, y_pred, average="binary"))
        f1 = float(f1_score(y_test, y_pred, average="binary"))
    else:
        precision = float(precision_score(y_test, y_pred, average="weighted"))
        recall = float(recall_score(y_test, y_pred, average="weighted"))
        f1 = float(f1_score(y_test, y_pred, average="weighted"))

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "test_samples": len(y_test),
        "n_classes": len(np.unique(y_test)),
        "is_binary": is_binary,
    }


def evaluate_regression_model_tool(
    model_path: str, test_data_path: str, target_column: str, test_indices_file: str = None
) -> dict:
    with open(resolve_input_path(model_path), "rb") as file:
        model = pickle.load(file)

    df = pd.read_csv(resolve_input_path(test_data_path))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}

    # Filter to only test set if indices file is provided
    if test_indices_file:
        try:
            indices_path = resolve_input_path(test_indices_file)
            if os.path.exists(indices_path):
                with open(indices_path, 'r') as f:
                    test_indices = json.load(f)
                df = df.iloc[test_indices]  # Filter to only test set
        except Exception as e:
            print(f"Warning: Could not load test indices: {e}")
            pass

    X_test = _encode_features(df.drop(columns=[target_column]))
    y_test = df[target_column]
    y_pred = model.predict(X_test)

    r2 = float(r2_score(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(y_test, y_pred))
    mape = (
        float(np.mean(np.abs((y_test - y_pred) / y_test)) * 100)
        if (y_test != 0).all()
        else None
    )

    return {
        "r2_score": round(r2, 4),
        "mse": round(mse, 4),
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "mape": round(mape, 4) if mape is not None else None,
        "test_samples": len(y_test),
    }


def get_classification_report_tool(
    model_path: str, test_data_path: str, target_column: str, test_indices_file: str = None
) -> dict:
    with open(resolve_input_path(model_path), "rb") as file:
        model = pickle.load(file)
    df = pd.read_csv(resolve_input_path(test_data_path))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Filter to only test set if indices file is provided
    if test_indices_file:
        try:
            indices_path = resolve_input_path(test_indices_file)
            if os.path.exists(indices_path):
                with open(indices_path, 'r') as f:
                    test_indices = json.load(f)
                df = df.iloc[test_indices]  # Filter to only test set
        except Exception as e:
            print(f"Warning: Could not load test indices: {e}")
            pass
    
    X_test = _encode_features(df.drop(columns=[target_column]))
    y_test = df[target_column]
    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    return {"report": report}


def calculate_confusion_matrix_tool(
    model_path: str,
    test_data_path: str,
    target_column: str,
    normalize: Optional[str] = None,
    test_indices_file: str = None,
) -> dict:
    with open(resolve_input_path(model_path), "rb") as file:
        model = pickle.load(file)
    df = pd.read_csv(resolve_input_path(test_data_path))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Filter to only test set if indices file is provided
    if test_indices_file:
        try:
            indices_path = resolve_input_path(test_indices_file)
            if os.path.exists(indices_path):
                with open(indices_path, 'r') as f:
                    test_indices = json.load(f)
                df = df.iloc[test_indices]  # Filter to only test set
        except Exception as e:
            print(f"Warning: Could not load test indices: {e}")
            pass
    
    X_test = _encode_features(df.drop(columns=[target_column]))
    y_test = df[target_column]
    y_pred = model.predict(X_test)
    normalize_mode = "true" if str(normalize).lower() in {"true", "1", "yes"} else None
    matrix = confusion_matrix(y_test, y_pred, normalize=normalize_mode)
    return {"confusion_matrix": np.asarray(matrix).tolist()}


def predict_with_model_tool(
    model_path: str,
    input_data_path: str,
    output_path: Optional[str] = None,
) -> dict:
    with open(resolve_input_path(model_path), "rb") as file:
        model = pickle.load(file)
    df = pd.read_csv(resolve_input_path(input_data_path))
    X = _encode_features(df)
    predictions = model.predict(X)
    saved_to = None
    if output_path:
        out = resolve_output_path(output_path, f"{Path(input_data_path).stem}_predictions.csv")
        pd.DataFrame({"prediction": predictions}).to_csv(out, index=False)
        saved_to = str(out)
    return {"predictions": predictions.tolist(), "saved_to": saved_to}


def calculate_residuals_tool(model_path: str, test_data_path: str, target_column: str, test_indices_file: str = None) -> dict:
    with open(resolve_input_path(model_path), "rb") as file:
        model = pickle.load(file)
    df = pd.read_csv(resolve_input_path(test_data_path))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Filter to only test set if indices file is provided
    if test_indices_file:
        try:
            indices_path = resolve_input_path(test_indices_file)
            if os.path.exists(indices_path):
                with open(indices_path, 'r') as f:
                    test_indices = json.load(f)
                df = df.iloc[test_indices]  # Filter to only test set
        except Exception as e:
            print(f"Warning: Could not load test indices: {e}")
            pass
    
    X = _encode_features(df.drop(columns=[target_column]))
    y = pd.to_numeric(df[target_column], errors="coerce")
    y_pred = pd.Series(model.predict(X), index=y.index)
    residuals = (y - y_pred).dropna()
    return {"residuals": residuals.tolist()}


def compare_model_predictions_tool(
    model1_path: str,
    model2_path: str,
    test_data_path: str,
    target_column: str,
    task: str = "classification",
) -> dict:
    with open(resolve_input_path(model1_path), "rb") as file:
        model1 = pickle.load(file)
    with open(resolve_input_path(model2_path), "rb") as file:
        model2 = pickle.load(file)
    df = pd.read_csv(resolve_input_path(test_data_path))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    X = _encode_features(df.drop(columns=[target_column]))
    y = df[target_column]
    pred1 = model1.predict(X)
    pred2 = model2.predict(X)
    if str(task).lower() == "regression":
        score1 = r2_score(y, pred1)
        score2 = r2_score(y, pred2)
    else:
        score1 = accuracy_score(y, pred1)
        score2 = accuracy_score(y, pred2)
    return {"model1_score": float(score1), "model2_score": float(score2)}


def error_analysis_tool(
    model_path: str,
    test_data_path: str,
    target_column: str,
    task: str = "classification",
) -> dict:
    with open(resolve_input_path(model_path), "rb") as file:
        model = pickle.load(file)
    df = pd.read_csv(resolve_input_path(test_data_path))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    X = _encode_features(df.drop(columns=[target_column]))
    y = df[target_column]
    y_pred = model.predict(X)
    if str(task).lower() == "regression":
        residuals = pd.Series(y) - pd.Series(y_pred)
        return {
            "mae": float(np.mean(np.abs(residuals))),
            "max_abs_error": float(np.max(np.abs(residuals))),
        }
    y = pd.Series(y).astype(str)
    y_pred = pd.Series(y_pred).astype(str)
    mismatches = (y != y_pred).sum()
    return {"misclassified": int(mismatches), "error_rate": float(mismatches / max(1, len(y)))}


def save_evaluation_results_tool(
    metrics: Optional[Dict[str, Any]],
    task_type: str,
    model_name: str,
    dataset_name: str,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None,
    pipeline: Optional[Any] = None,
    registry_path: Optional[str] = None,
) -> dict:
    if registry_path:
        candidate = resolve_output_path(registry_path, "evaluation_results.json")
        out_path = (
            candidate / "evaluation_results.json"
            if candidate.exists() and candidate.is_dir()
            else candidate
        )
        if out_path.suffix.lower() != ".json":
            out_path = out_path / "evaluation_results.json"
    else:
        out_path = uploads_root() / "evaluation_results.json"
    ensure_parent(out_path)
    existing: List[Dict[str, Any]] = []
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8") or "[]")
        if not isinstance(existing, list):
            existing = []
    entry = {
        "id": len(existing) + 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "task_type": task_type,
        "model_name": model_name,
        "dataset_name": dataset_name,
        "notes": notes,
        "tags": tags or [],
        "pipeline": pipeline if pipeline is not None else {},
        "metrics": metrics or {},
    }
    existing.append(entry)
    out_path.write_text(json.dumps(existing, indent=2, ensure_ascii=True), encoding="utf-8")
    return {
        "saved": True,
        "entry_id": entry["id"],
        "registry_file": str(out_path),
        "total_records": len(existing),
        "entry": entry,
    }


def list_evaluation_results_tool(
    task_type: Optional[str] = None,
    model_name: Optional[str] = None,
    tag: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    last_n: Optional[int] = None,
    registry_path: Optional[str] = None,
) -> dict:
    if registry_path:
        candidate = resolve_output_path(registry_path, "evaluation_results.json")
        out_path = (
            candidate / "evaluation_results.json"
            if candidate.exists() and candidate.is_dir()
            else candidate
        )
        if out_path.suffix.lower() != ".json":
            out_path = out_path / "evaluation_results.json"
    else:
        out_path = uploads_root() / "evaluation_results.json"
    if not out_path.exists():
        return {"total_in_registry": 0, "returned": 0, "records": [], "model_summary": {}}
    records = json.loads(out_path.read_text(encoding="utf-8") or "[]")
    filtered = []
    for rec in records:
        if task_type and rec.get("task_type") != task_type:
            continue
        if model_name and rec.get("model_name") != model_name:
            continue
        if tag and tag not in rec.get("tags", []):
            continue
        rec_pipeline_id = (rec.get("pipeline") or {}).get("pipeline_id")
        if pipeline_id and rec_pipeline_id != pipeline_id:
            continue
        filtered.append(rec)
    if last_n:
        filtered = filtered[-int(last_n) :]
    summary: Dict[str, Any] = {}
    for rec in filtered:
        name = str(rec.get("model_name") or "unknown")
        summary.setdefault(name, {"runs": 0, "latest_timestamp": None, "latest_metrics": {}})
        summary[name]["runs"] += 1
        summary[name]["latest_timestamp"] = rec.get("created_at")
        summary[name]["latest_metrics"] = rec.get("metrics", {})
    return {
        "total_in_registry": len(records),
        "returned": len(filtered),
        "registry_file": str(out_path),
        "records": filtered,
        "model_summary": summary,
    }


def cross_validate_model_tool(
    filepath: str,
    target_column: str,
    model_type: str = "random_forest",
    task: str = "classification",
    cv_folds: int = 5,
    random_state: int = 42,
) -> dict:
    return {
        "cross_validation_scores": [],
        "mean_score": None,
        "note": "Skipped in local batch replay to keep execution bounded",
    }


def hyperparameter_tuning_tool(
    filepath: str,
    target_column: str,
    model_type: str = "random_forest",
    task: str = "classification",
    param_grid: Optional[Dict[str, List[Any]]] = None,
    cv_folds: int = 3,
    random_state: int = 42,
) -> dict:
    return {
        "best_params": {},
        "best_score": None,
        "note": "Skipped in local batch replay to keep execution bounded",
    }


def get_feature_importance_tool(
    filepath: str,
    target_column: str,
    model_type: str = "random_forest",
    task: str = "classification",
    top_n: int = 10,
) -> dict:
    return {
        "feature_importance": {},
        "note": "Skipped in local batch replay to keep execution bounded",
    }


def compare_models_tool(
    filepath: str,
    target_column: str,
    task: str = "classification",
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    return {
        "comparison_results": {},
        "best_model": None,
        "best_score": None,
        "note": "Skipped in local batch replay to keep execution bounded",
    }


def feature_selection_tool(
    filepath: str,
    target_column: str,
    method: str = "f_classif",
    k: int = 10,
) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    X = _encode_features(df.drop(columns=[target_column]))
    y = df[target_column]
    selector_fn = f_regression if method == "f_regression" else f_classif
    selector = SelectKBest(score_func=selector_fn, k=min(max(1, int(k)), X.shape[1]))
    selector.fit(X, y)
    selected = X.columns[selector.get_support()].tolist()
    return {"selected_features": selected}


def dimensionality_reduction_tool(filepath: str, n_components: int = 2) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    X = _encode_features(df)
    components = min(max(1, int(n_components)), X.shape[1], max(1, X.shape[0] - 1))
    pca = PCA(n_components=components)
    reduced = pca.fit_transform(X)
    return {
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "reduced_data": reduced.tolist(),
    }


def generate_synthetic_data_tool(filepath: str, target_column: str) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    grouped = df.groupby(target_column)
    max_size = grouped.size().max()
    synthesized = []
    for _, group in grouped:
        if len(group) < max_size:
            sampled = group.sample(max_size - len(group), replace=True, random_state=42)
            group = pd.concat([group, sampled], ignore_index=True)
        synthesized.append(group)
    out_df = pd.concat(synthesized, ignore_index=True)
    out_path = resolve_output_path(None, f"{Path(filepath).stem}_synthetic.csv")
    out_df.to_csv(out_path, index=False)
    return {"output_path": str(out_path), "rows_generated": int(len(out_df) - len(df))}


def add_noise_tool(filepath: str, columns: List[str], noise_level: float = 0.01) -> dict:
    df = pd.read_csv(resolve_input_path(filepath))
    valid = [c for c in columns if c in df.columns]
    for col in valid:
        numeric = pd.to_numeric(df[col], errors="coerce")
        noise = np.random.normal(0, float(noise_level), size=len(df))
        df[col] = np.where(numeric.notna(), numeric + noise, df[col])
    out_path = resolve_output_path(None, f"{Path(filepath).stem}_noisy.csv")
    df.to_csv(out_path, index=False)
    return {"output_path": str(out_path), "columns": valid}


TOOL_EXECUTORS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "get_server_info": get_server_info_tool,
    "load_csv": load_csv_tool,
    "get_column_info": get_column_info_tool,
    "detect_missing_values": detect_missing_values_tool,
    "detect_duplicates": detect_duplicates_tool,
    "infer_data_types": infer_data_types_tool,
    "get_basic_stats": get_basic_stats_tool,
    "read_file_head": read_file_head_tool,
    "validate_csv_structure": validate_csv_structure_tool,
    "handle_missing_values": handle_missing_values_tool,
    "remove_duplicates": remove_duplicates_tool,
    "scale_features": scale_features_tool,
    "encode_categorical": encode_categorical_tool,
    "split_dataset": split_dataset_tool,
    "filter_rows": filter_rows_tool,
    "rename_columns": rename_columns_tool,
    "add_column_headers": add_column_headers_tool,
    "detect_outliers": detect_outliers_tool,
    "create_feature_bins": create_feature_bins_tool,
    "analyze_csv": analyze_csv_tool,
    "add": add_tool,
    "subtract": subtract_tool,
    "multiply": multiply_tool,
    "divide": divide_tool,
    "power": power_tool,
    "square_root": square_root_tool,
    "factorial": factorial_tool,
    "mean": mean_tool,
    "median": median_tool,
    "standard_deviation": standard_deviation_tool,
    "percentage": percentage_tool,
    "gcd": gcd_tool,
    "lcm": lcm_tool,
    "train_classification_model": train_classification_model_tool,
    "train_regression_model": train_regression_model_tool,
    "cross_validate_model": cross_validate_model_tool,
    "hyperparameter_tuning": hyperparameter_tuning_tool,
    "get_feature_importance": get_feature_importance_tool,
    "compare_models": compare_models_tool,
    "evaluate_classification_model": evaluate_classification_model_tool,
    "evaluate_regression_model": evaluate_regression_model_tool,
    "get_classification_report": get_classification_report_tool,
    "calculate_confusion_matrix": calculate_confusion_matrix_tool,
    "predict_with_model": predict_with_model_tool,
    "calculate_residuals": calculate_residuals_tool,
    "compare_model_predictions": compare_model_predictions_tool,
    "error_analysis": error_analysis_tool,
    "save_evaluation_results": save_evaluation_results_tool,
    "list_evaluation_results": list_evaluation_results_tool,
    "feature_selection": feature_selection_tool,
    "dimensionality_reduction": dimensionality_reduction_tool,
    "generate_synthetic_data": generate_synthetic_data_tool,
    "add_noise": add_noise_tool,
}


def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    tool_name_aliases = {
        "read_csv": "load_csv",
        "detect_duplication": "detect_duplicates",
        "drop_duplicates": "remove_duplicates",
        "classification_report": "get_classification_report",
        "confusion_matrix": "calculate_confusion_matrix",
    }
    resolved_tool_name = tool_name_aliases.get(tool_name.strip().lower(), tool_name)
    executor = TOOL_EXECUTORS.get(resolved_tool_name)
    if executor is None:
        return {"error": f"Unsupported tool: {tool_name}"}
    signature = inspect.signature(executor)
    accepts_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
    )
    if accepts_var_kw:
        filtered_params = params
    else:
        accepted = set(signature.parameters.keys())
        filtered_params = {k: v for k, v in params.items() if k in accepted}
    return executor(**filtered_params)


def run_single_pipeline(artifact_path: Path, output_models_dir: Path) -> PipelineRunResult:
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    dataset_id = str(payload.get("dataset_id") or artifact_path.stem)
    workflow = payload.get("workflow") or {}
    steps = workflow.get("steps") or []
    if not isinstance(steps, list) or not steps:
        return PipelineRunResult(
            dataset_id=dataset_id,
            artifact_file=artifact_path.name,
            task_type=str(payload.get("task_type") or "unknown"),
            target_column=payload.get("target_column"),
            model_type=None,
            status="failed",
            error="Workflow has no executable steps",
            metrics={},
        )

    initial_filepath = str(payload.get("file_path") or "")
    candidate_paths = collect_candidate_filepaths(payload, workflow, initial_filepath)
    resolved_file, path_note = resolve_dataset_file(initial_filepath, candidate_paths)
    if not resolved_file:
        return PipelineRunResult(
            dataset_id=dataset_id,
            artifact_file=artifact_path.name,
            task_type=str(payload.get("task_type") or "unknown"),
            target_column=payload.get("target_column"),
            model_type=None,
            status="failed",
            error=path_note or "Dataset file not found",
            metrics={},
        )

    context = PipelineExecutionContext(
        dataset_id=dataset_id,
        artifact_path=artifact_path,
        output_models_dir=output_models_dir,
        current_dataset_path=resolved_file,
        task_type=str(payload.get("task_type") or "unknown").strip().lower(),
        target_column=payload.get("target_column"),
    )
    if path_note:
        context.path_notes.append(path_note)

    executed_tools: List[Dict[str, Any]] = []

    try:
        for step in steps:
            phase_number = int(step.get("phase_number") or len(executed_tools) + 1)
            for tool in step.get("tools", []):
                tool_name = str(tool.get("tool_name") or "").strip()
                params = dict(tool.get("tool_parameters") or {})
                if not tool_name:
                    return PipelineRunResult(
                        dataset_id=dataset_id,
                        artifact_file=artifact_path.name,
                        task_type=context.task_type,
                        target_column=context.target_column,
                        model_type=context.model_type,
                        status="failed",
                        error=f"Phase {phase_number} contains unnamed tool",
                        metrics={},
                    )

                if tool_name in {
                    "load_csv",
                    "handle_missing_values",
                    "remove_duplicates",
                    "scale_features",
                    "encode_categorical",
                    "split_dataset",
                    "filter_rows",
                    "train_classification_model",
                    "train_regression_model",
                } and not params.get("filepath"):
                    params["filepath"] = str(context.current_dataset_path)

                if tool_name in {"train_classification_model", "train_regression_model"}:
                    context.task_type = (
                        "classification"
                        if tool_name == "train_classification_model"
                        else "regression"
                    )
                    context.target_column = params.get("target_column") or context.target_column
                    candidate_model_type = (
                        params.get("model_type")
                        or step.get("selected_model_type")
                        or context.model_type
                    )
                    context.model_type = normalize_model_type(
                        candidate_model_type, context.task_type
                    )
                    params["model_type"] = context.model_type or params.get("model_type")
                    if not params.get("model_save_path"):
                        params["model_save_path"] = str(
                            output_models_dir / f"{dataset_id}.pkl"
                        )

                if tool_name in {
                    "evaluate_classification_model",
                    "evaluate_regression_model",
                    "get_classification_report",
                    "calculate_confusion_matrix",
                    "calculate_residuals",
                    "error_analysis",
                }:
                    if not params.get("model_path") and context.current_model_path:
                        params["model_path"] = str(context.current_model_path)
                    elif params.get("model_path"):
                        try:
                            resolve_input_path(str(params["model_path"]))
                        except Exception:
                            if context.current_model_path:
                                params["model_path"] = str(context.current_model_path)
                    if not params.get("test_data_path") and context.current_dataset_path:
                        params["test_data_path"] = str(context.current_dataset_path)
                    elif params.get("test_data_path"):
                        try:
                            resolve_input_path(str(params["test_data_path"]))
                        except Exception:
                            if context.current_dataset_path:
                                params["test_data_path"] = str(context.current_dataset_path)
                    if not params.get("target_column") and context.target_column:
                        params["target_column"] = context.target_column
                    if not params.get("test_indices_file") and context.current_test_indices_file:
                        params["test_indices_file"] = str(context.current_test_indices_file)

                result = execute_tool(tool_name, params)
                if result.get("error"):
                    return PipelineRunResult(
                        dataset_id=dataset_id,
                        artifact_file=artifact_path.name,
                        task_type=context.task_type,
                        target_column=context.target_column,
                        model_type=context.model_type,
                        status="failed",
                        error=f"{tool_name}: {result['error']}",
                        metrics={},
                    )

                executed_tools.append(
                    {"phase_number": phase_number, "tool_name": tool_name}
                )

                if result.get("saved_to"):
                    context.current_dataset_path = resolve_artifact_path(
                        str(result["saved_to"])
                    )
                if tool_name == "split_dataset":
                    if result.get("train_path"):
                        context.current_dataset_path = resolve_artifact_path(
                            str(result["train_path"])
                        )
                if tool_name in {"train_classification_model", "train_regression_model"}:
                    context.last_training_metrics = result
                    if result.get("model_saved"):
                        context.current_model_path = resolve_artifact_path(
                            str(result["model_saved"])
                        )
                    if result.get("test_indices_file"):
                        context.current_test_indices_file = resolve_artifact_path(
                            str(result["test_indices_file"])
                        )
                if tool_name in {
                    "evaluate_classification_model",
                    "evaluate_regression_model",
                }:
                    context.last_evaluation_metrics = result

    except Exception as exc:
        return PipelineRunResult(
            dataset_id=dataset_id,
            artifact_file=artifact_path.name,
            task_type=context.task_type,
            target_column=context.target_column,
            model_type=context.model_type,
            status="failed",
            error=str(exc),
            metrics={},
        )

    metrics = dict(context.last_evaluation_metrics or context.last_training_metrics or {})
    metrics.update(
        {
            "resolved_dataset_path": (
                str(context.current_dataset_path) if context.current_dataset_path else None
            ),
            "model_path": (
                str(context.current_model_path) if context.current_model_path else None
            ),
            "executed_tools": len(executed_tools),
            "tool_flow": [f"{i['phase_number']}:{i['tool_name']}" for i in executed_tools],
        }
    )
    if context.path_notes:
        metrics["filepath_resolution_notes"] = context.path_notes

    return PipelineRunResult(
        dataset_id=dataset_id,
        artifact_file=artifact_path.name,
        task_type=context.task_type,
        target_column=context.target_column,
        model_type=context.model_type,
        status="success",
        error=None,
        metrics=metrics,
    )


def aggregate_summary(results: List[PipelineRunResult]) -> Dict[str, Any]:
    total = len(results)
    succeeded = [r for r in results if r.status == "success"]
    failed = [r for r in results if r.status != "success"]
    classification = [r for r in succeeded if r.task_type == "classification"]
    regression = [r for r in succeeded if r.task_type == "regression"]

    def avg(values: List[float]) -> Optional[float]:
        filtered = [v for v in values if v is not None]
        if not filtered:
            return None
        return round(float(np.mean(filtered)), 4)

    return {
        "total_pipelines": total,
        "successful": len(succeeded),
        "failed": len(failed),
        "classification_successful": len(classification),
        "regression_successful": len(regression),
        "avg_classification_accuracy": avg(
            [
                r.metrics.get("accuracy", r.metrics.get("test_accuracy"))
                for r in classification
            ]
        ),
        "avg_regression_r2": avg(
            [r.metrics.get("r2_score", r.metrics.get("test_r2")) for r in regression]
        ),
        "avg_regression_rmse": avg([r.metrics.get("rmse") for r in regression]),
        "failed_examples": [
            {
                "dataset_id": r.dataset_id,
                "artifact_file": r.artifact_file,
                "error": r.error,
            }
            for r in failed[:10]
        ],
    }


def main() -> None:
    args = parse_args()

    batch_dir = Path(args.batch_dir)
    if not batch_dir.is_absolute():
        batch_dir = (backend_root() / batch_dir).resolve()
    if not batch_dir.exists() or not batch_dir.is_dir():
        raise SystemExit(f"Batch folder not found: {batch_dir}")

    out_dir = (
        Path(args.output_dir)
        if args.output_dir
        else (backend_root() / "data" / "batch_results" / batch_dir.name)
    )
    if not out_dir.is_absolute():
        out_dir = (backend_root() / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    models_dir = out_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    artifact_files = sorted(batch_dir.glob("*.json"))
    results: List[PipelineRunResult] = []
    for artifact in artifact_files:
        if artifact.name.endswith("_artifacts.zip"):
            continue
        try:
            results.append(run_single_pipeline(artifact, models_dir))
        except Exception as exc:
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            results.append(
                PipelineRunResult(
                    dataset_id=str(payload.get("dataset_id") or artifact.stem),
                    artifact_file=artifact.name,
                    task_type=str(payload.get("task_type") or "unknown"),
                    target_column=payload.get("target_column"),
                    model_type=None,
                    status="failed",
                    error=str(exc),
                    metrics={},
                )
            )

    summary = aggregate_summary(results)
    result_rows = [
        {
            "dataset_id": r.dataset_id,
            "artifact_file": r.artifact_file,
            "task_type": r.task_type,
            "target_column": r.target_column,
            "model_type": r.model_type,
            "status": r.status,
            "error": r.error,
            **r.metrics,
        }
        for r in results
    ]

    (out_dir / "pipeline_results.json").write_text(
        json.dumps(result_rows, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    pd.DataFrame(result_rows).to_csv(out_dir / "pipeline_results.csv", index=False)

    print(json.dumps({"output_dir": str(out_dir), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
