"""
Service for managing LLM model configurations.
"""
import json
import os
from pathlib import Path
from typing import Optional
import structlog
from app.models.llm_model import LLMModel, ModelProvider

logger = structlog.get_logger()


class ModelService:
    """Service for managing LLM model configurations."""

    def __init__(self, models_file: str = "data/models.json"):
        """
        Initialize the model service.

        Args:
            models_file: Path to the models JSON file
        """
        self.models_file = Path(models_file)
        self.models: dict[str, LLMModel] = {}
        self._ensure_data_directory()
        self._load_models()

    def _ensure_data_directory(self):
        """Ensure the data directory exists."""
        self.models_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_models(self):
        """Load models from JSON file."""
        if not self.models_file.exists():
            self._create_default_models()
            return

        try:
            with open(self.models_file, 'r') as f:
                data = json.load(f)
                self.models = {
                    model_id: LLMModel(**model_data)
                    for model_id, model_data in data.items()
                }
            logger.info("Models loaded", count=len(self.models), file=str(self.models_file))
        except Exception as e:
            logger.error("Error loading models", error=str(e), file=str(self.models_file))
            self._create_default_models()

    def _create_default_models(self):
        """Create default model configurations."""
        default_models = [
            LLMModel(
                id="groq-llama-3.3-70b",
                display_name="Groq Llama 3.3 70B",
                model_name="groq/llama-3.3-70b-versatile",
                provider=ModelProvider.GROQ,
                api_key_name="GROQ_API_KEY",
                is_available=True,
                supports_function_calling=False,
                max_tokens=8000,
                description="Fast and capable 70B model (no function calling support)"
            ),
            LLMModel(
                id="gemini-2.5-flash",
                display_name="Gemini 2.5 Flash",
                model_name="gemini/gemini-2.5-flash",
                provider=ModelProvider.GEMINI,
                api_key_name="GOOGLE_API_KEY",
                is_available=True,
                supports_function_calling=True,
                max_tokens=8192,
                description="Fast Gemini 2.5 model"
            ),
            LLMModel(
                id="gemini-2.5-pro",
                display_name="Gemini 2.5 Pro",
                model_name="gemini/gemini-2.5-pro",
                provider=ModelProvider.GEMINI,
                api_key_name="GOOGLE_API_KEY",
                is_available=True,
                supports_function_calling=True,
                max_tokens=8192,
                description="Advanced Gemini 2.5 model with enhanced capabilities"
            ),
        ]
        
        self.models = {model.id: model for model in default_models}
        self._save_models()
        logger.info("Default models created", count=len(self.models))

    def _save_models(self):
        """Save models to JSON file atomically."""
        try:
            # Write to temporary file first
            temp_file = self.models_file.with_suffix('.tmp')
            data = {model_id: model.model_dump() for model_id, model in self.models.items()}
            
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic replace
            temp_file.replace(self.models_file)
            logger.info("Models saved", count=len(self.models), file=str(self.models_file))
        except Exception as e:
            logger.error("Error saving models", error=str(e), file=str(self.models_file))
            raise

    def _check_availability(self, model: LLMModel) -> bool:
        """
        Check if a model is available (has required API key).

        Args:
            model: The model to check

        Returns:
            bool: True if available, False otherwise
        """
        if not model.api_key_name:
            return True
        
        return bool(os.environ.get(model.api_key_name))

    def get_all_models(self) -> list[LLMModel]:
        """
        Get all models.

        Returns:
            List of all LLM models
        """
        # Update availability based on current environment
        for model in self.models.values():
            model.is_available = self._check_availability(model)
        
        return list(self.models.values())

    def get_available_models(self) -> list[LLMModel]:
        """
        Get only available models (with configured API keys).

        Returns:
            List of available LLM models
        """
        all_models = self.get_all_models()
        return [model for model in all_models if model.is_available]

    def get_model(self, model_id: str) -> Optional[LLMModel]:
        """
        Get a specific model by ID.

        Args:
            model_id: The model ID

        Returns:
            The LLM model or None if not found
        """
        model = self.models.get(model_id)
        if model:
            model.is_available = self._check_availability(model)
        return model

    def add_model(self, model: LLMModel) -> LLMModel:
        """
        Add a new model.

        Args:
            model: The model to add

        Returns:
            The added model
        """
        if model.id in self.models:
            raise ValueError(f"Model with ID {model.id} already exists")
        
        model.is_available = self._check_availability(model)
        self.models[model.id] = model
        self._save_models()
        logger.info("Model added", model_id=model.id, display_name=model.display_name)
        return model

    def update_model(self, model_id: str, model: LLMModel) -> LLMModel:
        """
        Update an existing model.

        Args:
            model_id: The ID of the model to update
            model: The updated model data

        Returns:
            The updated model
        """
        if model_id not in self.models:
            raise ValueError(f"Model with ID {model_id} not found")
        
        model.id = model_id  # Ensure ID doesn't change
        model.is_available = self._check_availability(model)
        self.models[model_id] = model
        self._save_models()
        logger.info("Model updated", model_id=model_id)
        return model

    def delete_model(self, model_id: str) -> bool:
        """
        Delete a model.

        Args:
            model_id: The ID of the model to delete

        Returns:
            True if deleted, False if not found
        """
        if model_id not in self.models:
            return False
        
        del self.models[model_id]
        self._save_models()
        logger.info("Model deleted", model_id=model_id)
        return True


# Global model service instance
_model_service: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """
    Get the global model service instance.

    Returns:
        The model service
    """
    global _model_service
    if _model_service is None:
        _model_service = ModelService()
    return _model_service
