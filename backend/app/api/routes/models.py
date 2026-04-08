"""
API routes for LLM model management.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import List
import structlog
import uuid

from app.models.llm_model import (
    LLMModel,
    LLMModelCreateRequest,
    LLMModelListResponse,
    ModelProvider,
)
from app.utils.env_manager import update_env_file, generate_env_var_name

router = APIRouter(prefix="/api/models", tags=["models"])
logger = structlog.get_logger()


def _is_model_available(req: LLMModelCreateRequest, api_key_name: str | None) -> bool:
    """Determine model availability from provider requirements."""
    if req.provider == ModelProvider.OLLAMA:
        return True
    return bool(api_key_name)


@router.get(
    "",
    response_model=LLMModelListResponse,
    responses={500: {"description": "Error listing models"}},
)
async def list_models(request: Request, available_only: bool = False):
    """
    Get all LLM models or only available ones.

    Args:
        available_only: If True, only return models with configured API keys

    Returns:
        List of LLM models
    """
    try:
        service = request.app.state.model_service
        models = await service.list_models(available_only=available_only)
        return LLMModelListResponse(models=models, count=len(models))
    except Exception as e:
        logger.error("Error listing models", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{model_id}",
    response_model=LLMModel,
    responses={
        404: {"description": "Model not found"},
        500: {"description": "Error getting model"},
    },
)
async def get_model(request: Request, model_id: str):
    """
    Get a specific LLM model by ID.

    Args:
        model_id: The model ID

    Returns:
        The LLM model
    """
    try:
        service = request.app.state.model_service
        model = await service.get_model(model_id)

        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        return model
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting model", model_id=model_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "",
    response_model=LLMModel,
    responses={
        400: {"description": "Invalid model request"},
        500: {"description": "Error creating model"},
    },
)
async def create_model(request: Request, req: LLMModelCreateRequest):
    """
    Create a new LLM model.

    Args:
        req: Model creation request

    Returns:
        The created model
    """
    try:
        service = request.app.state.model_service

        # Generate unique ID
        model_id = f"model-{uuid.uuid4().hex[:12]}"

        # Handle API key if provided
        api_key_name = req.api_key_name
        if req.api_key_value:
            # If API key value is provided but no env var name, generate one
            if not api_key_name:
                api_key_name = generate_env_var_name(req.provider, req.model_name)

            # Save API key to .env file
            success = update_env_file(api_key_name, req.api_key_value)
            if not success:
                logger.warning(
                    "Failed to save API key to .env file", api_key_name=api_key_name
                )

        model = LLMModel(
            id=model_id,
            display_name=req.display_name,
            model_name=req.model_name,
            provider=req.provider,
            api_key_name=api_key_name,
            is_available=_is_model_available(req, api_key_name),
            supports_function_calling=req.supports_function_calling,
            max_tokens=req.max_tokens,
            description=req.description,
        )

        created_model = await service.add_model(model)
        logger.info("Model created", model_id=model_id, display_name=req.display_name)

        return created_model
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating model", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{model_id}",
    response_model=LLMModel,
    responses={
        404: {"description": "Model not found"},
        500: {"description": "Error updating model"},
    },
)
async def update_model(request: Request, model_id: str, req: LLMModelCreateRequest):
    """
    Update an existing LLM model.

    Args:
        model_id: The model ID
        req: Model update request

    Returns:
        The updated model
    """
    try:
        service = request.app.state.model_service

        # Handle API key if provided
        api_key_name = req.api_key_name
        if req.api_key_value:
            # If API key value is provided but no env var name, generate one
            if not api_key_name:
                api_key_name = generate_env_var_name(req.provider, req.model_name)

            # Save API key to .env file
            success = update_env_file(api_key_name, req.api_key_value)
            if not success:
                logger.warning(
                    "Failed to save API key to .env file", api_key_name=api_key_name
                )

        model = LLMModel(
            id=model_id,
            display_name=req.display_name,
            model_name=req.model_name,
            provider=req.provider,
            api_key_name=api_key_name,
            is_available=_is_model_available(req, api_key_name),
            supports_function_calling=req.supports_function_calling,
            max_tokens=req.max_tokens,
            description=req.description,
        )

        updated_model = await service.update_model(model_id, model)
        logger.info("Model updated", model_id=model_id)

        return updated_model
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error updating model", model_id=model_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{model_id}",
    responses={
        404: {"description": "Model not found"},
        500: {"description": "Error deleting model"},
    },
)
async def delete_model(request: Request, model_id: str):
    """
    Delete an LLM model.

    Args:
        model_id: The model ID

    Returns:
        Success message
    """
    try:
        service = request.app.state.model_service
        success = await service.delete_model(model_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        logger.info("Model deleted", model_id=model_id)
        return {"message": "Model deleted successfully", "model_id": model_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting model", model_id=model_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
