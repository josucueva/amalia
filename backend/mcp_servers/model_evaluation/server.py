"""
Model Evaluation Tools MCP Server

Provides comprehensive model evaluation, metrics calculation, and visualization tools.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
    mean_squared_error, mean_absolute_error, r2_score,
    roc_auc_score, roc_curve, precision_recall_curve
)
import pickle
import json
from mcp.server.fastmcp import FastMCP

# Create FastMCP server instance
mcp = FastMCP("Model Evaluation Server")


@mcp.tool()
def evaluate_classification_model(
    model_path: str,
    test_data_path: str,
    target_column: str
) -> dict:
    """Evaluate a trained classification model.
    
    Args:
        model_path: Path to saved model pickle file
        test_data_path: Path to test dataset CSV
        target_column: Name of the target column
        
    Returns:
        Dictionary with comprehensive evaluation metrics
    """
    # Load model
    if not model_path.startswith("/app/"):
        model_path = f"/app/data/uploads/{model_path}"
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Load test data
    if not test_data_path.startswith("/app/"):
        test_data_path = f"/app/data/uploads/{test_data_path}"
    
    df = pd.read_csv(test_data_path)
    
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Prepare data
    X_test = df.drop(columns=[target_column])
    y_test = df[target_column]
    
    # Handle categorical features
    for col in X_test.select_dtypes(include=['object']).columns:
        X_test[col] = pd.factorize(X_test[col])[0]
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    accuracy = float(accuracy_score(y_test, y_pred))
    
    # For binary classification, calculate additional metrics
    is_binary = len(np.unique(y_test)) == 2
    
    if is_binary:
        precision = float(precision_score(y_test, y_pred, average='binary'))
        recall = float(recall_score(y_test, y_pred, average='binary'))
        f1 = float(f1_score(y_test, y_pred, average='binary'))
    else:
        precision = float(precision_score(y_test, y_pred, average='weighted'))
        recall = float(recall_score(y_test, y_pred, average='weighted'))
        f1 = float(f1_score(y_test, y_pred, average='weighted'))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": cm.tolist(),
        "test_samples": len(y_test),
        "n_classes": len(np.unique(y_test)),
        "is_binary": is_binary
    }


@mcp.tool()
def evaluate_regression_model(
    model_path: str,
    test_data_path: str,
    target_column: str
) -> dict:
    """Evaluate a trained regression model.
    
    Args:
        model_path: Path to saved model pickle file
        test_data_path: Path to test dataset CSV
        target_column: Name of the target column
        
    Returns:
        Dictionary with regression evaluation metrics
    """
    # Load model
    if not model_path.startswith("/app/"):
        model_path = f"/app/data/uploads/{model_path}"
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Load test data
    if not test_data_path.startswith("/app/"):
        test_data_path = f"/app/data/uploads/{test_data_path}"
    
    df = pd.read_csv(test_data_path)
    
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Prepare data
    X_test = df.drop(columns=[target_column])
    y_test = df[target_column]
    
    # Handle categorical features
    for col in X_test.select_dtypes(include=['object']).columns:
        X_test[col] = pd.factorize(X_test[col])[0]
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    r2 = float(r2_score(y_test, y_pred))
    mse = float(mean_squared_error(y_test, y_pred))
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(y_test, y_pred))
    
    # Calculate MAPE (Mean Absolute Percentage Error)
    mape = float(np.mean(np.abs((y_test - y_pred) / y_test)) * 100) if (y_test != 0).all() else None
    
    return {
        "r2_score": round(r2, 4),
        "mse": round(mse, 4),
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "mape": round(mape, 4) if mape else None,
        "test_samples": len(y_test),
        "prediction_range": {
            "min": round(float(y_pred.min()), 4),
            "max": round(float(y_pred.max()), 4)
        },
        "actual_range": {
            "min": round(float(y_test.min()), 4),
            "max": round(float(y_test.max()), 4)
        }
    }


@mcp.tool()
def get_classification_report(
    model_path: str,
    test_data_path: str,
    target_column: str
) -> dict:
    """Get detailed classification report.
    
    Args:
        model_path: Path to saved model pickle file
        test_data_path: Path to test dataset CSV
        target_column: Name of the target column
        
    Returns:
        Dictionary with per-class metrics
    """
    # Load model
    if not model_path.startswith("/app/"):
        model_path = f"/app/data/uploads/{model_path}"
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Load test data
    if not test_data_path.startswith("/app/"):
        test_data_path = f"/app/data/uploads/{test_data_path}"
    
    df = pd.read_csv(test_data_path)
    
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Prepare data
    X_test = df.drop(columns=[target_column])
    y_test = df[target_column]
    
    # Handle categorical features
    for col in X_test.select_dtypes(include=['object']).columns:
        X_test[col] = pd.factorize(X_test[col])[0]
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Get classification report
    report = classification_report(y_test, y_pred, output_dict=True)
    
    return {
        "per_class_metrics": report,
        "classes": list(np.unique(y_test)),
        "overall_accuracy": round(float(report["accuracy"]), 4)
    }


@mcp.tool()
def calculate_confusion_matrix(
    model_path: str,
    test_data_path: str,
    target_column: str,
    normalize: Optional[str] = None
) -> dict:
    """Calculate and optionally normalize confusion matrix.
    
    Args:
        model_path: Path to saved model pickle file
        test_data_path: Path to test dataset CSV
        target_column: Name of the target column
        normalize: Normalization mode ('true', 'pred', 'all', or None)
        
    Returns:
        Dictionary with confusion matrix
    """
    # Load model
    if not model_path.startswith("/app/"):
        model_path = f"/app/data/uploads/{model_path}"
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Load test data
    if not test_data_path.startswith("/app/"):
        test_data_path = f"/app/data/uploads/{test_data_path}"
    
    df = pd.read_csv(test_data_path)
    
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Prepare data
    X_test = df.drop(columns=[target_column])
    y_test = df[target_column]
    
    # Handle categorical features
    for col in X_test.select_dtypes(include=['object']).columns:
        X_test[col] = pd.factorize(X_test[col])[0]
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate confusion matrix
    cm = confusion_matrix(y_test, y_pred, normalize=normalize)
    
    return {
        "confusion_matrix": cm.tolist(),
        "normalized": normalize if normalize else "none",
        "classes": list(np.unique(y_test))
    }


@mcp.tool()
def predict_with_model(
    model_path: str,
    input_data_path: str,
    output_path: Optional[str] = None
) -> dict:
    """Make predictions using a trained model.
    
    Args:
        model_path: Path to saved model pickle file
        input_data_path: Path to input data CSV (without target column)
        output_path: Optional path to save predictions
        
    Returns:
        Dictionary with predictions
    """
    # Load model
    if not model_path.startswith("/app/"):
        model_path = f"/app/data/uploads/{model_path}"
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Load input data
    if not input_data_path.startswith("/app/"):
        input_data_path = f"/app/data/uploads/{input_data_path}"
    
    df = pd.read_csv(input_data_path)
    
    # Handle categorical features
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = pd.factorize(df[col])[0]
    
    # Make predictions
    predictions = model.predict(df)
    
    # Add predictions to dataframe
    df['prediction'] = predictions
    
    # Save if output path provided
    if output_path:
        if not output_path.startswith("/app/"):
            output_path = f"/app/data/uploads/{output_path}"
        df.to_csv(output_path, index=False)
    
    return {
        "predictions": predictions.tolist()[:100],  # Limit to first 100
        "total_predictions": len(predictions),
        "unique_predictions": len(np.unique(predictions)),
        "saved_to": output_path if output_path else None
    }


@mcp.tool()
def calculate_residuals(
    model_path: str,
    test_data_path: str,
    target_column: str
) -> dict:
    """Calculate prediction residuals for regression models.
    
    Args:
        model_path: Path to saved model pickle file
        test_data_path: Path to test dataset CSV
        target_column: Name of the target column
        
    Returns:
        Dictionary with residual statistics
    """
    # Load model
    if not model_path.startswith("/app/"):
        model_path = f"/app/data/uploads/{model_path}"
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Load test data
    if not test_data_path.startswith("/app/"):
        test_data_path = f"/app/data/uploads/{test_data_path}"
    
    df = pd.read_csv(test_data_path)
    
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Prepare data
    X_test = df.drop(columns=[target_column])
    y_test = df[target_column]
    
    # Handle categorical features
    for col in X_test.select_dtypes(include=['object']).columns:
        X_test[col] = pd.factorize(X_test[col])[0]
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate residuals
    residuals = y_test - y_pred
    
    return {
        "mean_residual": round(float(residuals.mean()), 4),
        "std_residual": round(float(residuals.std()), 4),
        "min_residual": round(float(residuals.min()), 4),
        "max_residual": round(float(residuals.max()), 4),
        "median_residual": round(float(np.median(residuals)), 4),
        "residual_range": round(float(residuals.max() - residuals.min()), 4),
        "samples": len(residuals)
    }


@mcp.tool()
def compare_model_predictions(
    model1_path: str,
    model2_path: str,
    test_data_path: str,
    target_column: str,
    task: str = "classification"
) -> dict:
    """Compare predictions from two different models.
    
    Args:
        model1_path: Path to first model
        model2_path: Path to second model
        test_data_path: Path to test dataset CSV
        target_column: Name of the target column
        task: 'classification' or 'regression'
        
    Returns:
        Dictionary comparing both models
    """
    # Load models
    if not model1_path.startswith("/app/"):
        model1_path = f"/app/data/uploads/{model1_path}"
    if not model2_path.startswith("/app/"):
        model2_path = f"/app/data/uploads/{model2_path}"
    
    with open(model1_path, 'rb') as f:
        model1 = pickle.load(f)
    with open(model2_path, 'rb') as f:
        model2 = pickle.load(f)
    
    # Load test data
    if not test_data_path.startswith("/app/"):
        test_data_path = f"/app/data/uploads/{test_data_path}"
    
    df = pd.read_csv(test_data_path)
    
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Prepare data
    X_test = df.drop(columns=[target_column])
    y_test = df[target_column]
    
    # Handle categorical features
    for col in X_test.select_dtypes(include=['object']).columns:
        X_test[col] = pd.factorize(X_test[col])[0]
    
    # Make predictions
    y_pred1 = model1.predict(X_test)
    y_pred2 = model2.predict(X_test)
    
    # Calculate metrics
    if task == "classification":
        score1 = float(accuracy_score(y_test, y_pred1))
        score2 = float(accuracy_score(y_test, y_pred2))
        metric = "accuracy"
    else:
        score1 = float(r2_score(y_test, y_pred1))
        score2 = float(r2_score(y_test, y_pred2))
        metric = "r2_score"
    
    # Agreement between models
    agreement = float(np.mean(y_pred1 == y_pred2))
    
    return {
        "task": task,
        "metric": metric,
        "model1_score": round(score1, 4),
        "model2_score": round(score2, 4),
        "difference": round(score2 - score1, 4),
        "better_model": "model2" if score2 > score1 else "model1" if score1 > score2 else "tie",
        "agreement_ratio": round(agreement, 4),
        "test_samples": len(y_test)
    }


@mcp.tool()
def error_analysis(
    model_path: str,
    test_data_path: str,
    target_column: str,
    task: str = "classification"
) -> dict:
    """Perform error analysis on model predictions.
    
    Args:
        model_path: Path to saved model pickle file
        test_data_path: Path to test dataset CSV
        target_column: Name of the target column
        task: 'classification' or 'regression'
        
    Returns:
        Dictionary with error analysis
    """
    # Load model
    if not model_path.startswith("/app/"):
        model_path = f"/app/data/uploads/{model_path}"
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Load test data
    if not test_data_path.startswith("/app/"):
        test_data_path = f"/app/data/uploads/{test_data_path}"
    
    df = pd.read_csv(test_data_path)
    
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}
    
    # Prepare data
    X_test = df.drop(columns=[target_column])
    y_test = df[target_column]
    
    # Handle categorical features
    for col in X_test.select_dtypes(include=['object']).columns:
        X_test[col] = pd.factorize(X_test[col])[0]
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    if task == "classification":
        # Find misclassified samples
        errors = y_test != y_pred
        error_rate = float(errors.mean())
        
        return {
            "task": "classification",
            "total_samples": len(y_test),
            "errors": int(errors.sum()),
            "error_rate": round(error_rate, 4),
            "accuracy": round(1 - error_rate, 4),
            "error_indices": np.where(errors)[0].tolist()[:50]  # First 50 error indices
        }
    else:
        # Find samples with large errors
        residuals = np.abs(y_test - y_pred)
        threshold = np.percentile(residuals, 90)  # Top 10% errors
        large_errors = residuals > threshold
        
        return {
            "task": "regression",
            "total_samples": len(y_test),
            "large_errors": int(large_errors.sum()),
            "error_threshold": round(float(threshold), 4),
            "mean_absolute_error": round(float(residuals.mean()), 4),
            "max_error": round(float(residuals.max()), 4),
            "large_error_indices": np.where(large_errors)[0].tolist()[:50]
        }


# Run the server
if __name__ == "__main__":
    mcp.run()
