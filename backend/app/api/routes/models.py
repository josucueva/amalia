"""
API routes for LLM model management.
"""

from fastapi import APIRouter, HTTPException
from typing import List
import structlog
import uuid

from app.models.llm_model import LLMModel, LLMModelCreateRequest, LLMModelListResponse
from app.services.model_service import get_model_service

router = APIRouter(prefix="/api/models", tags=["models"])
logger = structlog.get_logger()


@router.get("", response_model=LLMModelListResponse)
async def list_models(available_only: bool = False):
    """
    Get all LLM models or only available ones.

    Args:
        available_only: If True, only return models with configured API keys

    Returns:
        List of LLM models
    """
    try:
        service = get_model_service()

        if available_only:
            models = service.get_available_models()
        else:
            models = service.get_all_models()

        return LLMModelListResponse(models=models, count=len(models))
    except Exception as e:
        logger.error("Error listing models", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_id}", response_model=LLMModel)
async def get_model(model_id: str):
    """
    Get a specific LLM model by ID.

    Args:
        model_id: The model ID

    Returns:
        The LLM model
    """
    try:
        service = get_model_service()
        model = service.get_model(model_id)

        if not model:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        return model
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting model", model_id=model_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=LLMModel)
async def create_model(req: LLMModelCreateRequest):
    """
    Create a new LLM model.

    Args:
        req: Model creation request

    Returns:
        The created model
    """
    try:
        service = get_model_service()

        # Generate unique ID
        model_id = f"model-{uuid.uuid4().hex[:12]}"

        model = LLMModel(
            id=model_id,
            display_name=req.display_name,
            model_name=req.model_name,
            provider=req.provider,
            api_key_name=req.api_key_name,
            supports_function_calling=req.supports_function_calling,
            max_tokens=req.max_tokens,
            description=req.description,
        )

        created_model = service.add_model(model)
        logger.info("Model created", model_id=model_id, display_name=req.display_name)

        return created_model
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating model", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{model_id}", response_model=LLMModel)
async def update_model(model_id: str, req: LLMModelCreateRequest):
    """
    Update an existing LLM model.

    Args:
        model_id: The model ID
        req: Model update request

    Returns:
        The updated model
    """
    try:
        service = get_model_service()

        model = LLMModel(
            id=model_id,
            display_name=req.display_name,
            model_name=req.model_name,
            provider=req.provider,
            api_key_name=req.api_key_name,
            supports_function_calling=req.supports_function_calling,
            max_tokens=req.max_tokens,
            description=req.description,
        )

        updated_model = service.update_model(model_id, model)
        logger.info("Model updated", model_id=model_id)

        return updated_model
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error updating model", model_id=model_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{model_id}")
async def delete_model(model_id: str):
    """
    Delete an LLM model.

    Args:
        model_id: The model ID

    Returns:
        Success message
    """
    try:
        service = get_model_service()
        success = service.delete_model(model_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

        logger.info("Model deleted", model_id=model_id)
        return {"message": "Model deleted successfully", "model_id": model_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting model", model_id=model_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
