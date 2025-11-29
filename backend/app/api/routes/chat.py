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
from app.services.agent_pipeline import AgentPipelineService
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

        # Prepare user message with file context if attached
        user_message = request_data.message

        # DEBUG: Log request data
        logger.info(
            "[DEBUG] Request data",
            message_preview=user_message[:50],
            has_attached_file=bool(request_data.attached_file),
            attached_file=(
                request_data.attached_file if request_data.attached_file else None
            ),
        )

        if request_data.attached_file:
            file_info = request_data.attached_file
            file_context = f"\n\n[File attached: {file_info.get('filename')} ({file_info.get('size_mb', 0)} MB) at path: {file_info.get('path')}]"
            user_message_with_context = user_message + file_context
            logger.info(
                "File attached to message",
                filename=file_info.get("filename"),
                path=file_info.get("path"),
            )
        else:
            user_message_with_context = user_message

        # Add user message to history (without file context for display)
        conversation_history.add_message(
            conversation_id=conversation_id, role="user", content=request_data.message
        )

        # Get agent registry from app state
        agent_registry = getattr(request.app.state, "agent_registry", None)

        if not agent_registry:
            raise HTTPException(status_code=500, detail="Agent registry not available")

        # Create pipeline service
        pipeline_service = AgentPipelineService(llm_service, agent_registry)

        # Process through the three-agent pipeline
        try:
            assistant_content, orchestration_data = (
                await pipeline_service.process_with_pipeline(
                    user_message=user_message_with_context,  # Use message with file context
                    conversation_history=history,
                )
            )
        except Exception as pipeline_error:
            logger.error("Pipeline processing error", error=str(pipeline_error))
            raise HTTPException(
                status_code=500,
                detail=f"Error processing pipeline: {str(pipeline_error)}",
            )

        # Add assistant response to history
        conversation_history.add_message(
            conversation_id=conversation_id, role="assistant", content=assistant_content
        )

        # Determine which agents were involved
        agents_involved = ["interaction_agent"]
        if orchestration_data:
            agents_involved.extend(["planner_agent", "orchestrator_agent"])

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
                "model": settings.default_model,
                "orchestration": orchestration_data,  # Include orchestration if present
                "agents_used": agents_involved,
            },
            agent_id=None,  # Multi-agent response
        )

        return ChatResponse(
            message=response_message,
            conversation_id=conversation_id,
            agents_involved=agents_involved,
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
