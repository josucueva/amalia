"""
Chat routes for handling user conversations.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
import structlog
from datetime import datetime
import uuid

from app.models import ChatRequest, ChatResponse, Message, MessageRole, MessageStatus
from app.agents.registry import AgentRegistry
from app.services.llm_service import LLMService, get_llm_service
from app.services.conversation_history import conversation_history
from app.config import Settings, get_settings

logger = structlog.get_logger()
router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    request_data: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """
    Process a chat message and return a response.

    Args:
        request_data: Chat request with user message
        request: FastAPI request object
        settings: Application settings

    Returns:
        ChatResponse: Response from the agent(s)
    """
    try:
        logger.info("Processing chat request", message_length=len(request_data.message))

        # Generate IDs
        conversation_id = (
            request_data.conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        )
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        response_id = f"msg_{uuid.uuid4().hex[:12]}"

        # Get LLM service
        llm_service = get_llm_service(settings)

        # Get or create conversation history
        history = conversation_history.get_history(conversation_id, max_messages=20)

        # Add user message to history
        conversation_history.add_message(
            conversation_id=conversation_id, role="user", content=request_data.message
        )

        # Get agent registry from app state
        agent_registry = getattr(request.app.state, "agent_registry", None)

        # Select agent - prioritize interaction_agent
        selected_agent = None
        agent_config_dict = None

        if agent_registry:
            agents = agent_registry.list_agents()

            # First, try to find the interaction agent
            for agent in agents:
                if agent.config.name == "interaction_agent":
                    selected_agent = agent
                    agent_config_dict = selected_agent.config.dict()
                    break

            # If no interaction agent, use first available
            if not selected_agent and agents:
                selected_agent = agents[0]
                agent_config_dict = selected_agent.config.dict()

        if not agent_config_dict:
            # Default interaction agent configuration
            agent_config_dict = {
                "name": "interaction_agent",
                "model": settings.default_model,
                "system_prompt": "You are an interaction agent that helps users refine their requirements. Analyze the user's message, ask clarifying questions if needed, or provide an improved version of their prompt. Be concise and focus on understanding intent.",
                "temperature": 0.7,
                "max_tokens": 1500,
            }

        # Generate response using LLM
        try:
            assistant_content = await llm_service.generate_agent_response(
                user_message=request_data.message,
                agent_config=agent_config_dict,
                conversation_history=history,
            )
        except Exception as llm_error:
            logger.error("LLM generation error", error=str(llm_error))
            raise HTTPException(
                status_code=500, detail=f"Error generating response: {str(llm_error)}"
            )

        # Add assistant response to history
        conversation_history.add_message(
            conversation_id=conversation_id, role="assistant", content=assistant_content
        )

        # Create response message
        response_message = Message(
            id=response_id,
            role=MessageRole.ASSISTANT,
            content=assistant_content,
            timestamp=datetime.now(),
            status=MessageStatus.COMPLETED,
            metadata={
                "conversation_id": conversation_id,
                "user_message_id": message_id,
                "model": agent_config_dict["model"],
            },
            agent_id=selected_agent.id if selected_agent else None,
        )

        return ChatResponse(
            message=response_message,
            conversation_id=conversation_id,
            agents_involved=[selected_agent.id] if selected_agent else [],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error processing chat request", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """
    Get conversation history.

    Args:
        conversation_id: Conversation ID

    Returns:
        dict: Conversation history
    """
    logger.info("Fetching conversation history", conversation_id=conversation_id)

    messages = conversation_history.get_history(conversation_id)

    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "total": len(messages),
    }


@router.delete("/history/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation.

    Args:
        conversation_id: Conversation ID

    Returns:
        dict: Deletion confirmation
    """
    logger.info("Deleting conversation", conversation_id=conversation_id)

    conversation_history.clear_conversation(conversation_id)

    return {"status": "deleted", "conversation_id": conversation_id}


@router.get("/conversations")
async def list_conversations():
    """
    List all conversations.

    Returns:
        dict: List of conversations
    """
    conversations = conversation_history.get_all_conversations()

    return {"conversations": conversations, "total": len(conversations)}
