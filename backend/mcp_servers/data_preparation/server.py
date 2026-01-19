"""
Data Preparation Tools MCP Server

Provides advanced data transformation, feature engineering, and preparation tools.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder, OneHotEncoder
from sklearn.impute import SimpleImputer
from mcp.server.fastmcp import FastMCP
import json

# Create FastMCP server instance
mcp = FastMCP("Data Preparation Server")


@mcp.tool()
def handle_missing_values(
    filepath: str,
    strategy: str = "mean",
    columns: Optional[List[str]] = None,
    output_filepath: Optional[str] = None
) -> dict:
    """Handle missing values using various strategies.
    
    Args:
        filepath: Path to CSV file
        strategy: Imputation strategy ('mean', 'median', 'mode', 'constant', 'drop')
        columns: Specific columns to handle (None = all columns with missing values)
        output_filepath: Optional path to save cleaned data
        
    Returns:
        Dictionary with operation results
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    original_rows = len(df)
    
    if strategy == "drop":
        df = df.dropna(subset=columns) if columns else df.dropna()
        rows_removed = original_rows - len(df)
        result = {
            "strategy": "drop",
            "rows_removed": rows_removed,
            "remaining_rows": len(df)
        }
    else:
        # Select columns with missing values
        if columns is None:
            columns = df.columns[df.isna().any()].tolist()
        
        filled_columns = []
        for col in columns:
            if df[col].isna().any():
                if strategy in ["mean", "median"] and pd.api.types.is_numeric_dtype(df[col]):
                    if strategy == "mean":
                        df[col].fillna(df[col].mean(), inplace=True)
                    else:
                        df[col].fillna(df[col].median(), inplace=True)
                    filled_columns.append(col)
                elif strategy == "mode":
                    df[col].fillna(df[col].mode()[0] if len(df[col].mode()) > 0 else 0, inplace=True)
                    filled_columns.append(col)
                elif strategy == "constant":
                    df[col].fillna(0, inplace=True)
                    filled_columns.append(col)
        
        result = {
            "strategy": strategy,
            "columns_filled": filled_columns,
            "total_filled": len(filled_columns)
        }
    
    # Save if output path provided
    if output_filepath:
        if not output_filepath.startswith("/app/"):
            output_filepath = f"/app/data/uploads/{output_filepath}"
        df.to_csv(output_filepath, index=False)
        result["saved_to"] = output_filepath
    
    result["remaining_missing"] = int(df.isna().sum().sum())
    return result


@mcp.tool()
def remove_duplicates(
    filepath: str,
    subset: Optional[List[str]] = None,
    keep: str = "first",
    output_filepath: Optional[str] = None
) -> dict:
    """Remove duplicate rows from dataset.
    
    Args:
        filepath: Path to CSV file
        subset: Columns to consider for duplicates (None = all columns)
        keep: Which duplicates to keep ('first', 'last', False=remove all)
        output_filepath: Optional path to save cleaned data
        
    Returns:
        Dictionary with operation results
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    original_rows = len(df)
    
    keep_param = keep if keep != "none" else False
    df_cleaned = df.drop_duplicates(subset=subset, keep=keep_param)
    
    removed = original_rows - len(df_cleaned)
    
    if output_filepath:
        if not output_filepath.startswith("/app/"):
            output_filepath = f"/app/data/uploads/{output_filepath}"
        df_cleaned.to_csv(output_filepath, index=False)
    
    return {
        "original_rows": original_rows,
        "duplicates_removed": removed,
        "remaining_rows": len(df_cleaned),
        "saved_to": output_filepath if output_filepath else None
    }


@mcp.tool()
def scale_features(
    filepath: str,
    columns: List[str],
    method: str = "standard",
    output_filepath: Optional[str] = None
) -> dict:
    """Scale numerical features using standardization or normalization.
    
    Args:
        filepath: Path to CSV file
        columns: List of column names to scale
        method: Scaling method ('standard' or 'minmax')
        output_filepath: Optional path to save scaled data
        
    Returns:
        Dictionary with scaling results
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    # Verify columns exist and are numeric
    valid_columns = []
    for col in columns:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            valid_columns.append(col)
    
    if not valid_columns:
        return {"error": "No valid numeric columns found"}
    
    # Scale
    if method == "standard":
        scaler = StandardScaler()
    else:
        scaler = MinMaxScaler()
    
    df[valid_columns] = scaler.fit_transform(df[valid_columns])
    
    if output_filepath:
        if not output_filepath.startswith("/app/"):
            output_filepath = f"/app/data/uploads/{output_filepath}"
        df.to_csv(output_filepath, index=False)
    
    return {
        "method": method,
        "columns_scaled": valid_columns,
        "saved_to": output_filepath if output_filepath else None
    }


@mcp.tool()
def encode_categorical(
    filepath: str,
    columns: List[str],
    method: str = "onehot",
    output_filepath: Optional[str] = None
) -> dict:
    """Encode categorical variables.
    
    Args:
        filepath: Path to CSV file
        columns: List of column names to encode
        method: Encoding method ('onehot' or 'label')
        output_filepath: Optional path to save encoded data
        
    Returns:
        Dictionary with encoding results
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    encoded_columns = []
    
    for col in columns:
        if col not in df.columns:
            continue
            
        if method == "label":
            # Label encoding
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoded_columns.append(col)
        elif method == "onehot":
            # One-hot encoding
            dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
            df = pd.concat([df, dummies], axis=1)
            df.drop(col, axis=1, inplace=True)
            encoded_columns.append(col)
            encoded_columns.extend(dummies.columns.tolist())
    
    if output_filepath:
        if not output_filepath.startswith("/app/"):
            output_filepath = f"/app/data/uploads/{output_filepath}"
        df.to_csv(output_filepath, index=False)
    
    return {
        "method": method,
        "original_columns": columns,
        "result_columns": encoded_columns,
        "new_shape": {"rows": len(df), "columns": len(df.columns)},
        "saved_to": output_filepath if output_filepath else None
    }


@mcp.tool()
def detect_outliers(
    filepath: str,
    column: str,
    method: str = "iqr",
    threshold: float = 1.5
) -> dict:
    """Detect outliers in a numerical column.
    
    Args:
        filepath: Path to CSV file
        column: Column name to check for outliers
        method: Detection method ('iqr' or 'zscore')
        threshold: Threshold for outlier detection (IQR multiplier or z-score)
        
    Returns:
        Dictionary with outlier information
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    
    if not pd.api.types.is_numeric_dtype(df[column]):
        return {"error": f"Column '{column}' is not numeric"}
    
    col_data = df[column].dropna()
    
    if method == "iqr":
        Q1 = col_data.quantile(0.25)
        Q3 = col_data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
    else:  # zscore
        mean = col_data.mean()
        std = col_data.std()
        z_scores = np.abs((df[column] - mean) / std)
        outliers = df[z_scores > threshold]
    
    return {
        "column": column,
        "method": method,
        "threshold": threshold,
        "outlier_count": len(outliers),
        "outlier_percentage": round((len(outliers) / len(df)) * 100, 2),
        "outlier_indices": outliers.index.tolist()[:100],  # Limit to first 100
        "bounds": {
            "lower": float(lower_bound) if method == "iqr" else None,
            "upper": float(upper_bound) if method == "iqr" else None
        }
    }


@mcp.tool()
def create_feature_bins(
    filepath: str,
    column: str,
    bins: int = 5,
    labels: Optional[List[str]] = None,
    output_filepath: Optional[str] = None
) -> dict:
    """Create bins/categories from a continuous numerical column.
    
    Args:
        filepath: Path to CSV file
        column: Column name to bin
        bins: Number of bins to create
        labels: Optional labels for bins
        output_filepath: Optional path to save binned data
        
    Returns:
        Dictionary with binning results
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    
    new_col_name = f"{column}_binned"
    
    try:
        df[new_col_name] = pd.cut(df[column], bins=bins, labels=labels)
        
        if output_filepath:
            if not output_filepath.startswith("/app/"):
                output_filepath = f"/app/data/uploads/{output_filepath}"
            df.to_csv(output_filepath, index=False)
        
        return {
            "original_column": column,
            "new_column": new_col_name,
            "bins": bins,
            "value_counts": df[new_col_name].value_counts().to_dict(),
            "saved_to": output_filepath if output_filepath else None
        }
    except Exception as e:
        return {"error": f"Binning failed: {str(e)}"}


@mcp.tool()
def split_dataset(
    filepath: str,
    train_ratio: float = 0.8,
    random_state: int = 42,
    shuffle: bool = True
) -> dict:
    """Split dataset into training and testing sets.
    
    Args:
        filepath: Path to CSV file
        train_ratio: Ratio of training data (0.0 to 1.0)
        random_state: Random seed for reproducibility
        shuffle: Whether to shuffle before splitting
        
    Returns:
        Dictionary with split information and saved file paths
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    if shuffle:
        df = df.sample(frac=1, random_state=random_state).reset_index(drop=True)
    
    split_idx = int(len(df) * train_ratio)
    train_df = df[:split_idx]
    test_df = df[split_idx:]
    
    # Generate output filenames
    base_name = filepath.rsplit('/', 1)[-1].replace('.csv', '')
    train_path = f"/app/data/uploads/{base_name}_train.csv"
    test_path = f"/app/data/uploads/{base_name}_test.csv"
    
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    
    return {
        "original_rows": len(df),
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "train_ratio": train_ratio,
        "train_path": train_path,
        "test_path": test_path
    }


@mcp.tool()
def filter_rows(
    filepath: str,
    column: str,
    condition: str,
    value: Any,
    output_filepath: Optional[str] = None
) -> dict:
    """Filter rows based on a condition.
    
    Args:
        filepath: Path to CSV file
        column: Column name to filter on
        condition: Condition operator ('eq', 'ne', 'gt', 'lt', 'gte', 'lte', 'contains')
        value: Value to compare against
        output_filepath: Optional path to save filtered data
        
    Returns:
        Dictionary with filtering results
    """
    if not filepath.startswith("/app/"):
        filepath = f"/app/data/uploads/{filepath}"
    
    df = pd.read_csv(filepath)
    
    if column not in df.columns:
        return {"error": f"Column '{column}' not found"}
    
    original_rows = len(df)
    
    # Apply condition
    if condition == "eq":
        df_filtered = df[df[column] == value]
    elif condition == "ne":
        df_filtered = df[df[column] != value]
    elif condition == "gt":
        df_filtered = df[df[column] > value]
    elif condition == "lt":
        df_filtered = df[df[column] < value]
    elif condition == "gte":
        df_filtered = df[df[column] >= value]
    elif condition == "lte":
        df_filtered = df[df[column] <= value]
    elif condition == "contains":
        df_filtered = df[df[column].astype(str).str.contains(str(value), na=False)]
    else:
        return {"error": f"Unknown condition: {condition}"}
    
    if output_filepath:
        if not output_filepath.startswith("/app/"):
            output_filepath = f"/app/data/uploads/{output_filepath}"
        df_filtered.to_csv(output_filepath, index=False)
    
    return {
        "original_rows": original_rows,
        "filtered_rows": len(df_filtered),
        "rows_removed": original_rows - len(df_filtered),
        "condition": f"{column} {condition} {value}",
        "saved_to": output_filepath if output_filepath else None
    }


# Run the server
if __name__ == "__main__":
    mcp.run()
