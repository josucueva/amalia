"""
LLM service for handling model interactions.
"""
import os
import json
from typing import List, Dict, Any, Optional, AsyncIterator, Union
import structlog
from litellm import acompletion, completion_cost
import asyncio

from app.config import Settings

logger = structlog.get_logger()


class LLMService:
    """Service for interacting with LLM models via LiteLLM."""
    
    def __init__(self, settings: Settings):
        """
        Initialize LLM service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self._setup_api_keys()
        
    def _setup_api_keys(self):
        """Set up API keys in environment for LiteLLM."""
        if self.settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.settings.openai_api_key
            
        if self.settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.settings.anthropic_api_key
            
        if self.settings.google_api_key:
            os.environ["GEMINI_API_KEY"] = self.settings.google_api_key
            os.environ["GOOGLE_API_KEY"] = self.settings.google_api_key
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Union[str, Dict[str, Any], AsyncIterator[str]]:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to settings.default_model)
            temperature: Temperature for sampling
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            tools: Optional list of tools available to the LLM
            
        Returns:
            Generated response text or async iterator for streaming
        """
        model = model or self.settings.default_model
        
        try:
            logger.info(
                "Generating LLM response",
                model=model,
                message_count=len(messages),
                stream=stream,
                tools_count=len(tools) if tools else 0
            )
            
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
            
            # Add tools if provided
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"
            
            # Call LiteLLM
            response = await acompletion(**request_params)
            
            if stream:
                return self._stream_response(response)
            else:
                # Check for tool calls
                choice = response.choices[0]
                if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                    # Return tool calls for external processing
                    return {
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "name": tc.function.name,
                                "arguments": json.loads(tc.function.arguments)
                            }
                            for tc in choice.message.tool_calls
                        ]
                    }
                
                content = choice.message.content
                
                # Log usage
                try:
                    cost = completion_cost(completion_response=response)
                    logger.info(
                        "LLM response generated",
                        model=model,
                        tokens=response.usage.total_tokens if hasattr(response, 'usage') else 0,
                        cost=cost
                    )
                except Exception as e:
                    logger.warning("Could not calculate cost", error=str(e))
                
                return content
                
        except Exception as e:
            logger.error(
                "Error generating LLM response",
                error=str(e),
                model=model
            )
            raise
    
    async def _stream_response(self, response) -> AsyncIterator[str]:
        """
        Stream response chunks from LLM.
        
        Args:
            response: LiteLLM streaming response
            
        Yields:
            Response chunks
        """
        try:
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error("Error streaming response", error=str(e))
            raise
    
    async def generate_with_system_prompt(
        self,
        user_message: str,
        system_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate a response with a system prompt and conversation history.
        
        Args:
            user_message: User's message
            system_prompt: System prompt for the agent
            conversation_history: Previous messages in conversation
            model: Model to use
            temperature: Temperature for sampling
            max_tokens: Maximum tokens
            
        Returns:
            Generated response
        """
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return await self.generate_response(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def generate_agent_response(
        self,
        user_message: str,
        agent_config: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a response using agent configuration.
        
        Args:
            user_message: User's message
            agent_config: Agent configuration dict
            conversation_history: Previous messages
            
        Returns:
            Generated response
        """
        return await self.generate_with_system_prompt(
            user_message=user_message,
            system_prompt=agent_config.get("system_prompt", ""),
            conversation_history=conversation_history,
            model=agent_config.get("model"),
            temperature=agent_config.get("temperature", 0.7),
            max_tokens=agent_config.get("max_tokens", 2000)
        )


def get_llm_service(settings: Settings) -> LLMService:
    """
    Get LLM service instance.
    
    Args:
        settings: Application settings
        
    Returns:
        LLMService instance
    """
    return LLMService(settings)
