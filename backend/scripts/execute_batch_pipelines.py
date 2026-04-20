"""
Execute AMALIA batch pipeline artifacts directly in code (without SIM workflow conversion).

This runner focuses on the numeric part of each generated pipeline:
- Reads one batch export folder with artifact JSON files
- Extracts training intent from each pipeline (task, target, model, test_size, random_state)
- Trains/evaluates a scikit-learn model per dataset
- Writes per-pipeline results and an aggregate summary

Usage (from backend/):
    python scripts/execute_batch_pipelines.py \
      --batch-dir ../data/batch_exports/batch_20260413210359_e0bfce22

Notes:
- Paths in artifacts are usually /app/... and are mapped to local backend paths.
- This does not depend on SIM conversion.
- Preprocessing steps from artifacts are not replayed one-by-one yet; this script
  executes the core train/evaluate flow to produce comparable numeric metrics.
"""

from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor


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
        help=(
            "Output directory for run results. Default: ../data/batch_results/<batch_name>"
        ),
    )
    return parser.parse_args()


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return backend_root().parent


def resolve_artifact_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if p.exists():
        return p

    normalized = str(raw_path).replace("\\", "/")
    if normalized.startswith("/app/"):
        # Map /app/... -> backend/... for local execution
        suffix = normalized[len("/app/") :]
        candidate = backend_root() / suffix
        if candidate.exists():
            return candidate

    # Fallbacks
    candidate = backend_root() / "data" / "uploads" / Path(raw_path).name
    if candidate.exists():
        return candidate

    return p


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def normalize_model_type(model_type: Optional[str], task_type: str) -> str:
    mt = (model_type or "").strip().lower()
    if mt in {"", "none", "null"}:
        return "random_forest"
    if mt == "random_forest_regressor":
        return "random_forest"
    return mt


def choose_train_tool(workflow: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any], Optional[str]]:
    selected_model_type = None
    for step in workflow.get("steps", []):
        selected_model_type = selected_model_type or step.get("selected_model_type")
        for tool in step.get("tools", []):
            tool_name = str(tool.get("tool_name") or "")
            if tool_name in {"train_classification_model", "train_regression_model"}:
                return tool_name, (tool.get("tool_parameters") or {}), selected_model_type
    return None, {}, selected_model_type


def encode_categorical_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.select_dtypes(include=["object"]).columns:
        out[col] = pd.factorize(out[col].astype(str))[0]
    return out


def build_model(task_type: str, model_type: str, hyperparameters: Dict[str, Any], random_state: int):
    hp = dict(hyperparameters or {})

    if task_type == "classification":
        if model_type in {"logistic", "logistic_regression"}:
            kwargs = {"max_iter": 1000, "random_state": random_state}
            kwargs.update(hp)
            return LogisticRegression(**kwargs)
        if model_type in {"decision_tree", "decision_tree_classifier"}:
            kwargs = {"random_state": random_state}
            kwargs.update(hp)
            return DecisionTreeClassifier(**kwargs)
        if model_type in {"random_forest", "random_forest_classifier"}:
            kwargs = {"n_estimators": 100, "random_state": random_state}
            kwargs.update(hp)
            return RandomForestClassifier(**kwargs)
        if model_type in {"svm", "svc"}:
            kwargs = {"random_state": random_state}
            kwargs.update(hp)
            return SVC(**kwargs)
        if model_type in {"knn", "kneighbors"}:
            return KNeighborsClassifier(**hp)
        if model_type in {"naive_bayes", "gaussian_nb"}:
            return GaussianNB(**hp)
        if model_type in {"gradient_boosting", "gradient_boosting_classifier"}:
            kwargs = {"random_state": random_state}
            kwargs.update(hp)
            return GradientBoostingClassifier(**kwargs)

    else:
        if model_type in {"linear", "linear_regression"}:
            return LinearRegression(**hp)
        if model_type in {"ridge"}:
            kwargs = {"random_state": random_state}
            kwargs.update(hp)
            return Ridge(**kwargs)
        if model_type in {"lasso"}:
            kwargs = {"random_state": random_state}
            kwargs.update(hp)
            return Lasso(**kwargs)
        if model_type in {"decision_tree", "decision_tree_regressor"}:
            kwargs = {"random_state": random_state}
            kwargs.update(hp)
            return DecisionTreeRegressor(**kwargs)
        if model_type in {"random_forest", "random_forest_regressor"}:
            kwargs = {"n_estimators": 100, "random_state": random_state}
            kwargs.update(hp)
            return RandomForestRegressor(**kwargs)
        if model_type in {"svr", "svm"}:
            return SVR(**hp)
        if model_type in {"knn", "kneighbors"}:
            return KNeighborsRegressor(**hp)
        if model_type in {"gradient_boosting", "gradient_boosting_regressor"}:
            kwargs = {"random_state": random_state}
            kwargs.update(hp)
            return GradientBoostingRegressor(**kwargs)

    raise ValueError(f"Unsupported model_type='{model_type}' for task='{task_type}'")


def run_single_pipeline(artifact_path: Path, output_models_dir: Path) -> PipelineRunResult:
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))

    dataset_id = str(payload.get("dataset_id") or artifact_path.stem)
    workflow = payload.get("workflow") or {}
    task_type = str(payload.get("task_type") or "").strip().lower()

    train_tool_name, train_params, selected_model_type = choose_train_tool(workflow)
    if not task_type:
        if train_tool_name == "train_regression_model":
            task_type = "regression"
        else:
            task_type = "classification"

    if not train_tool_name:
        return PipelineRunResult(
            dataset_id=dataset_id,
            artifact_file=artifact_path.name,
            task_type=task_type,
            target_column=None,
            model_type=None,
            status="failed",
            error="No training tool found in workflow",
            metrics={},
        )

    filepath = train_params.get("filepath") or payload.get("file_path")
    target_column = train_params.get("target_column") or payload.get("target_column")
    model_type = normalize_model_type(
        train_params.get("model_type") or selected_model_type,
        task_type,
    )
    test_size = float(train_params.get("test_size") or 0.2)
    random_state = int(train_params.get("random_state") or 42)
    hyperparameters = train_params.get("hyperparameters") or {}

    if not filepath:
        return PipelineRunResult(
            dataset_id=dataset_id,
            artifact_file=artifact_path.name,
            task_type=task_type,
            target_column=target_column,
            model_type=model_type,
            status="failed",
            error="Missing filepath in artifact",
            metrics={},
        )

    resolved_file = resolve_artifact_path(str(filepath))
    if not resolved_file.exists():
        return PipelineRunResult(
            dataset_id=dataset_id,
            artifact_file=artifact_path.name,
            task_type=task_type,
            target_column=target_column,
            model_type=model_type,
            status="failed",
            error=f"Dataset file not found: {filepath}",
            metrics={},
        )

    df = pd.read_csv(resolved_file)

    if not target_column or target_column not in df.columns:
        return PipelineRunResult(
            dataset_id=dataset_id,
            artifact_file=artifact_path.name,
            task_type=task_type,
            target_column=target_column,
            model_type=model_type,
            status="failed",
            error=f"Invalid target_column '{target_column}'",
            metrics={},
        )

    X = encode_categorical_features(df.drop(columns=[target_column]))
    y = df[target_column]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    model = build_model(
        task_type=task_type,
        model_type=model_type,
        hyperparameters=hyperparameters,
        random_state=random_state,
    )
    model.fit(X_train, y_train)

    model_path = output_models_dir / f"{dataset_id}.pkl"
    ensure_parent(model_path)
    with open(model_path, "wb") as handle:
        pickle.dump(model, handle)

    metrics: Dict[str, Any] = {
        "dataset_rows": int(len(df)),
        "feature_count": int(X.shape[1]),
        "target_column": target_column,
        "model_type": model_type,
        "model_path": str(model_path),
    }

    if task_type == "classification":
        y_pred = model.predict(X_test)
        unique_count = len(np.unique(y_test))
        average = "binary" if unique_count == 2 else "weighted"

        metrics.update(
            {
                "train_accuracy": round(float(model.score(X_train, y_train)), 4),
                "test_accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
                "precision": round(
                    float(precision_score(y_test, y_pred, average=average, zero_division=0)),
                    4,
                ),
                "recall": round(
                    float(recall_score(y_test, y_pred, average=average, zero_division=0)),
                    4,
                ),
                "f1_score": round(
                    float(f1_score(y_test, y_pred, average=average, zero_division=0)),
                    4,
                ),
                "test_samples": int(len(y_test)),
                "n_classes": int(unique_count),
            }
        )
    else:
        y_pred = model.predict(X_test)
        mse = float(mean_squared_error(y_test, y_pred))
        metrics.update(
            {
                "train_r2": round(float(model.score(X_train, y_train)), 4),
                "test_r2": round(float(r2_score(y_test, y_pred)), 4),
                "mse": round(mse, 4),
                "rmse": round(float(np.sqrt(mse)), 4),
                "mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
                "test_samples": int(len(y_test)),
            }
        )

    return PipelineRunResult(
        dataset_id=dataset_id,
        artifact_file=artifact_path.name,
        task_type=task_type,
        target_column=target_column,
        model_type=model_type,
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
        if not values:
            return None
        return round(float(np.mean(values)), 4)

    summary = {
        "total_pipelines": total,
        "successful": len(succeeded),
        "failed": len(failed),
        "classification_successful": len(classification),
        "regression_successful": len(regression),
        "avg_classification_test_accuracy": avg(
            [r.metrics.get("test_accuracy") for r in classification if r.metrics.get("test_accuracy") is not None]
        ),
        "avg_regression_test_r2": avg(
            [r.metrics.get("test_r2") for r in regression if r.metrics.get("test_r2") is not None]
        ),
        "avg_regression_rmse": avg(
            [r.metrics.get("rmse") for r in regression if r.metrics.get("rmse") is not None]
        ),
        "failed_examples": [
            {
                "dataset_id": r.dataset_id,
                "artifact_file": r.artifact_file,
                "error": r.error,
            }
            for r in failed[:10]
        ],
    }
    return summary


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
            result = run_single_pipeline(artifact, models_dir)
        except Exception as exc:  # defensive: never abort entire batch
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            result = PipelineRunResult(
                dataset_id=str(payload.get("dataset_id") or artifact.stem),
                artifact_file=artifact.name,
                task_type=str(payload.get("task_type") or "unknown"),
                target_column=payload.get("target_column"),
                model_type=None,
                status="failed",
                error=str(exc),
                metrics={},
            )
        results.append(result)

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

    # JSON outputs
    (out_dir / "pipeline_results.json").write_text(
        json.dumps(result_rows, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    # CSV output for quick spreadsheet analysis
    pd.DataFrame(result_rows).to_csv(out_dir / "pipeline_results.csv", index=False)

    print(json.dumps({"output_dir": str(out_dir), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
