"""
Utility for managing environment variables in .env file.
"""

import os
from pathlib import Path
import structlog

logger = structlog.get_logger()


def update_env_file(key: str, value: str, env_file: str = ".env") -> bool:
    """
    Update or add an environment variable in the .env file.
    
    Args:
        key: Environment variable name
        value: Environment variable value
        env_file: Path to .env file (default: ".env")
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        env_path = Path(env_file)
        
        # Read existing content
        if env_path.exists():
            with open(env_path, "r") as f:
                lines = f.readlines()
        else:
            lines = []
        
        # Check if key exists
        key_exists = False
        new_lines = []
        
        for line in lines:
            # Skip empty lines and comments
            if line.strip().startswith("#") or not line.strip():
                new_lines.append(line)
                continue
                
            # Check if this line contains our key
            if "=" in line:
                env_key = line.split("=")[0].strip()
                if env_key == key:
                    # Update existing key
                    new_lines.append(f"{key}={value}\n")
                    key_exists = True
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        
        # If key doesn't exist, add it
        if not key_exists:
            # Add a newline if file doesn't end with one
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(f"\n# Added by model configuration\n{key}={value}\n")
        
        # Write back to file atomically
        temp_file = env_path.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            f.writelines(new_lines)
        
        temp_file.replace(env_path)
        
        # Update current process environment
        os.environ[key] = value
        
        logger.info("Environment variable updated", key=key, file=str(env_path))
        return True
        
    except Exception as e:
        logger.error("Error updating .env file", key=key, error=str(e))
        return False


def generate_env_var_name(provider: str, model_name: str) -> str:
    """
    Generate a unique environment variable name for an API key.
    
    Args:
        provider: Model provider (e.g., "gemini", "openai")
        model_name: Model name
        
    Returns:
        str: Generated environment variable name
    """
    # Use provider-based naming convention
    provider_upper = provider.upper()
    return f"{provider_upper}_API_KEY"
