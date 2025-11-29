"""
LLM Model configuration models.
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ModelProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    TOGETHER = "together"
    AZURE = "azure"
    CUSTOM = "custom"


class LLMModel(BaseModel):
    """LLM Model configuration."""
    id: str = Field(..., description="Unique identifier for the model")
    display_name: str = Field(..., description="Human-readable name for the model")
    model_name: str = Field(..., description="Full model identifier (e.g., 'groq/llama-3.3-70b-versatile')")
    provider: ModelProvider = Field(..., description="Model provider")
    api_key_name: Optional[str] = Field(None, description="Environment variable name for API key (e.g., 'GROQ_API_KEY')")
    is_available: bool = Field(True, description="Whether the model is available for use")
    supports_function_calling: bool = Field(True, description="Whether the model supports function calling")
    max_tokens: Optional[int] = Field(None, description="Maximum token limit for the model")
    description: Optional[str] = Field(None, description="Description of the model")

    class Config:
        use_enum_values = True


class LLMModelCreateRequest(BaseModel):
    """Request to create a new LLM model."""
    display_name: str = Field(..., description="Human-readable name for the model")
    model_name: str = Field(..., description="Full model identifier (e.g., 'groq/llama-3.3-70b-versatile')")
    provider: ModelProvider = Field(..., description="Model provider")
    api_key_name: Optional[str] = Field(None, description="Environment variable name for API key")
    supports_function_calling: bool = Field(True, description="Whether the model supports function calling")
    max_tokens: Optional[int] = Field(None, description="Maximum token limit")
    description: Optional[str] = Field(None, description="Description of the model")

    class Config:
        use_enum_values = True


class LLMModelListResponse(BaseModel):
    """Response containing a list of LLM models."""
    models: list[LLMModel]
    count: int
