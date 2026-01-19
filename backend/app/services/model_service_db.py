"""
MongoDB-based model service for managing LLM model configurations.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import structlog

from app.models.llm_model import LLMModel, ModelProvider
from app.database import get_db

logger = structlog.get_logger()


class ModelService:
    """Service for managing LLM model configurations using MongoDB."""

    def __init__(self):
        """Initialize the model service."""
        self.collection_name = "models"

    def _get_collection(self):
        """Get models collection."""
        return get_db()[self.collection_name]

    async def initialize_default_models(self):
        """Load models from data/models.json if exists, otherwise create defaults."""
        collection = self._get_collection()
        count = await collection.count_documents({})

        if count == 0:
            # Try to load from existing JSON file first
            models_json_path = Path("data/models.json")
            if models_json_path.exists():
                try:
                    with open(models_json_path, "r", encoding="utf-8") as f:
                        models_data = json.load(f)

                    models = []
                    for model_id, model_dict in models_data.items():
                        try:
                            model = LLMModel(**model_dict)
                            models.append(model)
                        except Exception as e:
                            logger.error(
                                "Failed to parse model", model_id=model_id, error=str(e)
                            )

                    if models:
                        await collection.insert_many([m.model_dump() for m in models])
                        logger.info(
                            "Models loaded from JSON",
                            count=len(models),
                            source="data/models.json",
                        )
                        return
                except Exception as e:
                    logger.error("Failed to load models from JSON", error=str(e))

            # Fallback to default models
            default_models = self._get_default_models()
            if default_models:
                await collection.insert_many([m.model_dump() for m in default_models])
                logger.info("Default models initialized", count=len(default_models))

    def _get_default_models(self) -> List[LLMModel]:
        """Get default model configurations."""
        return [
            LLMModel(
                id="groq-llama-3.3-70b",
                display_name="Groq Llama 3.3 70B",
                model_name="groq/llama-3.3-70b-versatile",
                provider=ModelProvider.GROQ,
                api_key_name="GROQ_API_KEY",
                is_available=True,
                supports_function_calling=False,
                max_tokens=8000,
                description="Fast and capable 70B model (no function calling support)",
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
                description="Fast Gemini 2.5 model",
            ),
            LLMModel(
                id="gpt-4o",
                display_name="GPT-4o",
                model_name="gpt-4o",
                provider=ModelProvider.OPENAI,
                api_key_name="OPENAI_API_KEY",
                is_available=True,
                supports_function_calling=True,
                max_tokens=4096,
                description="Latest GPT-4 optimized model",
            ),
        ]

    async def get_model(self, model_id: str) -> Optional[LLMModel]:
        """
        Get a model by ID.

        Args:
            model_id: Model ID

        Returns:
            Model or None if not found
        """
        collection = self._get_collection()
        data = await collection.find_one({"id": model_id})

        if data:
            data.pop("_id", None)
            return LLMModel(**data)
        return None

    async def list_models(self, available_only: bool = False) -> List[LLMModel]:
        """
        List all models.

        Args:
            available_only: Only return available models

        Returns:
            List of models
        """
        collection = self._get_collection()

        query = {}
        if available_only:
            query["is_available"] = True

        models = []
        async for doc in collection.find(query):
            doc.pop("_id", None)
            models.append(LLMModel(**doc))

        return models

    async def add_model(self, model: LLMModel) -> LLMModel:
        """
        Add a new model.

        Args:
            model: Model to add

        Returns:
            Added model

        Raises:
            ValueError: If model ID already exists
        """
        collection = self._get_collection()

        # Check if exists
        existing = await collection.find_one({"id": model.id})
        if existing:
            raise ValueError(f"Model with ID '{model.id}' already exists")

        await collection.insert_one(model.model_dump())
        logger.info("Model added", model_id=model.id, name=model.display_name)
        return model

    async def update_model(self, model_id: str, model: LLMModel) -> Optional[LLMModel]:
        """
        Update an existing model.

        Args:
            model_id: Model ID
            model: Updated model data

        Returns:
            Updated model or None if not found
        """
        collection = self._get_collection()

        result = await collection.replace_one({"id": model_id}, model.model_dump())

        if result.matched_count == 0:
            return None

        logger.info("Model updated", model_id=model_id)
        return model

    async def delete_model(self, model_id: str) -> bool:
        """
        Delete a model.

        Args:
            model_id: Model ID

        Returns:
            True if deleted, False if not found
        """
        collection = self._get_collection()
        result = await collection.delete_one({"id": model_id})

        if result.deleted_count > 0:
            logger.info("Model deleted", model_id=model_id)
            return True
        return False

    async def set_model_availability(self, model_id: str, is_available: bool) -> bool:
        """
        Set model availability status.

        Args:
            model_id: Model ID
            is_available: Availability status

        Returns:
            True if updated, False if not found
        """
        collection = self._get_collection()

        result = await collection.update_one(
            {"id": model_id}, {"$set": {"is_available": is_available}}
        )

        if result.matched_count > 0:
            logger.info(
                "Model availability updated",
                model_id=model_id,
                is_available=is_available,
            )
            return True
        return False

    async def get_models_by_provider(self, provider: ModelProvider) -> List[LLMModel]:
        """
        Get models by provider.

        Args:
            provider: Model provider

        Returns:
            List of models for the provider
        """
        collection = self._get_collection()

        models = []
        async for doc in collection.find({"provider": provider.value}):
            doc.pop("_id", None)
            models.append(LLMModel(**doc))

        return models
