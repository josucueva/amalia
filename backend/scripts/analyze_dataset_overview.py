"""Generate a compact dataset-level summary for selected datasets.

The script reports only:
- total number of columns
- a general overview of column data types
- dataset-level missing-data information

Defaults point to the three datasets requested by the user.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASETS = {
    "glass_easy_classification": BACKEND_ROOT
    / "data/uploads/datasets/classification/easy/uciml_glass/glass.csv",
    "housing_mid_regression": BACKEND_ROOT
    / "data/uploads/datasets/regression/mid/camnugent_california-housing-prices/housing.csv",
    "loan_hard_classification": BACKEND_ROOT
    / "data/uploads/datasets/classification/hard/abhishek14398_loan-dataset/loan.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze selected datasets and print a compact structural summary."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save the JSON summary.",
    )
    parser.add_argument(
        "datasets",
        nargs="*",
        help=(
            "Optional dataset paths. If omitted, the script uses the default glass, "
            "housing, and loan CSV files."
        ),
    )
    return parser.parse_args()


def resolve_datasets(raw_paths: List[str]) -> Dict[str, Path]:
    if not raw_paths:
        return DEFAULT_DATASETS

    resolved: Dict[str, Path] = {}
    for raw_path in raw_paths:
        path = Path(raw_path)
        resolved[path.stem] = path if path.is_absolute() else (BACKEND_ROOT / raw_path)
    return resolved


def _sample_values(series: pd.Series, limit: int = 20) -> List[str]:
    return [
        str(value).strip() for value in series.dropna().astype(str).head(limit).tolist()
    ]


def _looks_like_date(values: List[str], column_name: str) -> bool:
    name = column_name.lower()
    if any(token in name for token in ("date", "_d", "_dt", "time", "cr_line")):
        return True
    if not values:
        return False
    parsed = 0
    for value in values:
        try:
            pd.to_datetime(value, errors="raise")
            parsed += 1
        except Exception:
            continue
    return parsed / len(values) >= 0.8


def _looks_like_url(values: List[str], column_name: str) -> bool:
    if "url" in column_name.lower():
        return True
    return any(value.startswith(("http://", "https://", "www.")) for value in values)


def _looks_like_numeric_text(values: List[str], column_name: str) -> bool:
    name = column_name.lower()
    numeric_tokens = ("rate", "pct", "percent", "ratio", "term", "revol")
    if not any(token in name for token in numeric_tokens):
        return False
    if not values:
        return False

    parsed = 0
    for value in values:
        cleaned = value.replace("%", "")
        cleaned = re.sub(r"[^0-9eE+\-.]", "", cleaned)
        if not cleaned:
            continue
        try:
            float(cleaned)
            parsed += 1
        except ValueError:
            continue
    return parsed / len(values) >= 0.8


def _looks_like_identifier_or_code(values: List[str], column_name: str) -> bool:
    name = column_name.lower()
    if any(token in name for token in ("id", "code", "zip", "state", "serial")):
        return True
    if not values:
        return False
    unique_ratio = len(set(values)) / len(values)
    avg_length = sum(len(value) for value in values) / len(values)
    return unique_ratio >= 0.8 and avg_length <= 12


def _looks_like_free_text(values: List[str]) -> bool:
    if not values:
        return False
    avg_length = sum(len(value) for value in values) / len(values)
    space_ratio = sum(1 for value in values if " " in value) / len(values)
    unique_ratio = len(set(values)) / len(values)
    return avg_length >= 15 or (space_ratio >= 0.5 and unique_ratio >= 0.5)


def classify_object_column(series: pd.Series, column_name: str) -> str:
    values = _sample_values(series)
    if not values:
        return "empty_object"
    if _looks_like_date(values, column_name):
        return "date_like"
    if _looks_like_url(values, column_name):
        return "url_like"
    if _looks_like_numeric_text(values, column_name):
        return "numeric_text"
    if _looks_like_identifier_or_code(values, column_name):
        return "identifier_or_code"
    if _looks_like_free_text(values):
        return "free_text"
    return "categorical"


def analyze_dataset(dataset_path: Path) -> Dict[str, Any]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    dataframe = pd.read_csv(dataset_path)
    row_count = int(dataframe.shape[0])
    column_count = int(dataframe.shape[1])

    dtype_counts = dataframe.dtypes.astype(str).value_counts().sort_index()
    dtype_overview = [
        {
            "dtype": dtype_name,
            "column_count": int(count),
            "pct_of_columns": round((int(count) / column_count) * 100, 4),
        }
        for dtype_name, count in dtype_counts.items()
    ]

    object_columns = [
        column
        for column in dataframe.columns
        if str(dataframe[column].dtype) == "object"
    ]
    object_categories: Dict[str, List[str]] = {}
    for column_name in object_columns:
        category = classify_object_column(dataframe[column_name], column_name)
        object_categories.setdefault(category, []).append(column_name)

    object_overview = {
        "object_column_count": int(len(object_columns)),
        "subtypes": [
            {
                "subtype": subtype,
                "column_count": int(len(columns)),
                "pct_of_object_columns": (
                    round((len(columns) / len(object_columns)) * 100, 4)
                    if object_columns
                    else 0.0
                ),
                "pct_of_all_columns": round((len(columns) / column_count) * 100, 4),
                "example_columns": columns[:3],
            }
            for subtype, columns in sorted(object_categories.items())
        ],
    }

    missing_cells = int(dataframe.isna().sum().sum())
    total_cells = int(row_count * column_count)
    missing_pct = round((missing_cells / total_cells) * 100, 4) if total_cells else 0.0
    columns_with_missing = int((dataframe.isna().sum() > 0).sum())

    return {
        "file": str(dataset_path),
        "row_count": row_count,
        "column_count": column_count,
        "dtype_overview": dtype_overview,
        "object_overview": object_overview,
        "missing_overview": {
            "missing_cells": missing_cells,
            "total_cells": total_cells,
            "missing_pct": missing_pct,
            "columns_with_missing": columns_with_missing,
        },
    }


def main() -> None:
    args = parse_args()
    datasets = resolve_datasets(args.datasets)

    summary = {name: analyze_dataset(path) for name, path in datasets.items()}

    output_text = json.dumps(summary, indent=2, ensure_ascii=False)
    print(output_text)

    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = BACKEND_ROOT / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
