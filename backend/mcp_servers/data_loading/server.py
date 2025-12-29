"""
Data Loading and Preprocessing MCP Server

Provides tools for loading CSV/Excel files and basic preprocessing operations.
"""
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union
from mcp.server.fastmcp import FastMCP

# Create FastMCP server instance
mcp = FastMCP("Data Loading Server")


@mcp.tool()
def load_csv(filepath: str, encoding: str = "utf-8", delimiter: str = ",") -> dict:
    """Load a CSV file and return metadata.
    
    Args:
        filepath: Path to CSV file (relative to /app/data/uploads/)
        encoding: File encoding (default: utf-8)
        delimiter: Column delimiter (default: comma)
        
    Returns:
        Dictionary with file metadata including rows, columns, dtypes, and sample data
    """
    # Resolve path
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    # Load CSV
    df = pd.read_csv(filepath, encoding=encoding, delimiter=delimiter)
    
    return {
        "success": True,
        "filepath": filepath,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "sample_data": df.head(5).to_dict(orient="records"),
        "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024:.2f} KB"
    }


@mcp.tool()
def get_column_info(filepath: str, column_name: str) -> dict:
    """Get detailed information about a specific column.
    
    Args:
        filepath: Path to CSV file
        column_name: Name of the column to analyze
        
    Returns:
        Dictionary with column statistics and info
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    if column_name not in df.columns:
        return {"error": f"Column '{column_name}' not found"}
    
    col = df[column_name]
    
    info = {
        "column_name": column_name,
        "dtype": str(col.dtype),
        "non_null_count": int(col.count()),
        "null_count": int(col.isna().sum()),
        "unique_count": int(col.nunique()),
    }
    
    # Add numeric statistics if applicable
    if pd.api.types.is_numeric_dtype(col):
        info.update({
            "mean": float(col.mean()) if not pd.isna(col.mean()) else None,
            "median": float(col.median()) if not pd.isna(col.median()) else None,
            "std": float(col.std()) if not pd.isna(col.std()) else None,
            "min": float(col.min()) if not pd.isna(col.min()) else None,
            "max": float(col.max()) if not pd.isna(col.max()) else None,
        })
    else:
        # For categorical/text data
        info["most_common"] = col.value_counts().head(5).to_dict()
    
    return info


@mcp.tool()
def detect_missing_values(filepath: str) -> dict:
    """Detect missing values in the dataset.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        Dictionary with missing value statistics per column
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    missing_info = {}
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        if null_count > 0:
            missing_info[col] = {
                "count": null_count,
                "percentage": round((null_count / len(df)) * 100, 2)
            }
    
    return {
        "total_rows": len(df),
        "columns_with_missing": len(missing_info),
        "missing_data": missing_info,
        "complete_columns": [col for col in df.columns if col not in missing_info]
    }


@mcp.tool()
def detect_duplicates(filepath: str, subset: Optional[List[str]] = None) -> dict:
    """Detect duplicate rows in the dataset.
    
    Args:
        filepath: Path to CSV file
        subset: List of column names to check for duplicates (None = all columns)
        
    Returns:
        Dictionary with duplicate statistics
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    duplicates = df.duplicated(subset=subset, keep=False)
    dup_count = int(duplicates.sum())
    
    return {
        "total_rows": len(df),
        "duplicate_rows": dup_count,
        "percentage": round((dup_count / len(df)) * 100, 2),
        "unique_rows": len(df) - dup_count,
        "checked_columns": subset if subset else "all"
    }


@mcp.tool()
def infer_data_types(filepath: str) -> dict:
    """Automatically infer and suggest optimal data types for columns.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        Dictionary with current and suggested data types
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    type_info = {}
    for col in df.columns:
        current_type = str(df[col].dtype)
        
        # Try to infer better type
        suggested_type = current_type
        if current_type == "object":
            # Check if it could be numeric
            try:
                pd.to_numeric(df[col], errors='raise')
                suggested_type = "numeric (float/int)"
            except:
                # Check if it could be datetime
                try:
                    pd.to_datetime(df[col], errors='raise')
                    suggested_type = "datetime"
                except:
                    # Check if it's categorical
                    if df[col].nunique() / len(df) < 0.5:  # Less than 50% unique
                        suggested_type = "categorical"
        
        type_info[col] = {
            "current": current_type,
            "suggested": suggested_type,
            "unique_values": int(df[col].nunique()),
            "unique_ratio": round(df[col].nunique() / len(df), 3)
        }
    
    return type_info


@mcp.tool()
def get_basic_stats(filepath: str) -> dict:
    """Get basic statistical summary of the dataset.
    
    Args:
        filepath: Path to CSV file
        
    Returns:
        Dictionary with statistical summary
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    
    return {
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "numeric_columns": len(numeric_cols),
        "categorical_columns": len(categorical_cols),
        "total_missing": int(df.isna().sum().sum()),
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024**2), 2),
        "numeric_summary": df[numeric_cols].describe().to_dict() if numeric_cols else {},
        "categorical_summary": {
            col: {
                "unique": int(df[col].nunique()),
                "top": df[col].mode()[0] if len(df[col].mode()) > 0 else None,
                "freq": int(df[col].value_counts().iloc[0]) if len(df[col]) > 0 else 0
            }
            for col in categorical_cols
        } if categorical_cols else {}
    }


@mcp.tool()
def read_file_head(filepath: str, n_rows: int = 10) -> dict:
    """Read first N rows of a CSV file.
    
    Args:
        filepath: Path to CSV file
        n_rows: Number of rows to read (default: 10)
        
    Returns:
        Dictionary with first N rows
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath, nrows=n_rows)
    
    return {
        "rows_read": len(df),
        "columns": df.columns.tolist(),
        "data": df.to_dict(orient="records")
    }


@mcp.tool()
def validate_csv_structure(filepath: str, expected_columns: Optional[List[str]] = None) -> dict:
    """Validate CSV file structure and integrity.
    
    Args:
        filepath: Path to CSV file
        expected_columns: List of expected column names (optional)
        
    Returns:
        Dictionary with validation results
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    try:
        df = pd.read_csv(filepath)
        
        issues = []
        
        # Check for empty file
        if len(df) == 0:
            issues.append("File is empty")
        
        # Check for unnamed columns
        unnamed_cols = [col for col in df.columns if 'Unnamed' in str(col)]
        if unnamed_cols:
            issues.append(f"Found unnamed columns: {unnamed_cols}")
        
        # Check expected columns
        if expected_columns:
            missing_cols = set(expected_columns) - set(df.columns)
            extra_cols = set(df.columns) - set(expected_columns)
            if missing_cols:
                issues.append(f"Missing expected columns: {list(missing_cols)}")
            if extra_cols:
                issues.append(f"Extra columns found: {list(extra_cols)}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist()
        }
    except Exception as e:
        return {
            "valid": False,
            "issues": [f"Error reading file: {str(e)}"],
            "rows": 0,
            "columns": 0
        }


# Run the server
if __name__ == "__main__":
    mcp.run()
