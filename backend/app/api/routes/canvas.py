"""
Canvas routes for managing agent pipelines and connections.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import structlog

from app.services.agent_pipeline import AgentPipelineService
from app.services.llm_service import get_llm_service
from app.config import get_settings

logger = structlog.get_logger()
router = APIRouter()


class NodePosition(BaseModel):
    x: float
    y: float


class CanvasNode(BaseModel):
    instanceId: str
    agentId: str
    position: NodePosition


class CanvasConnection(BaseModel):
    id: str
    fromInstanceId: str
    toInstanceId: str


class BuildPipelineRequest(BaseModel):
    command: str  # e.g., "BUILD"


class BuildPipelineResponse(BaseModel):
    success: bool
    message: str
    nodes: List[CanvasNode]
    connections: List[CanvasConnection]


class ExecuteNodeRequest(BaseModel):
    instanceId: str
    agentType: str
    inputs: List[dict] = []


class ExecuteNodeResponse(BaseModel):
    instanceId: str
    agentType: str
    timestamp: str
    inputs: int
    output: str
    error: Optional[str] = None


@router.post("/execute", response_model=ExecuteNodeResponse)
async def execute_node(
    request_data: ExecuteNodeRequest,
    request: Request,
):
    """
    Execute a single agent node in the pipeline.

    Args:
        request_data: Node execution request
        request: FastAPI request object

    Returns:
        ExecuteNodeResponse: Execution result
    """
    try:
        from datetime import datetime, timezone
        from app.services.mcp_service import MCPService
        
        logger.info(
            "Executing agent node",
            instance_id=request_data.instanceId,
            agent_type=request_data.agentType,
            inputs_count=len(request_data.inputs)
        )

        # Get agent registry
        agent_registry = getattr(request.app.state, "agent_registry", None)
        if not agent_registry:
            raise HTTPException(status_code=500, detail="Agent registry not available")

        # Get the agent from registry
        agent = agent_registry.get_agent(request_data.agentType)
        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent type '{request_data.agentType}' not found"
            )

        # Prepare input for agent execution
        # Combine all inputs into a single context
        if request_data.inputs:
            combined_input = "\n\n".join([
                f"Input {i+1}:\n{inp.get('output', '')}" 
                for i, inp in enumerate(request_data.inputs)
            ])
        else:
            combined_input = "No input data provided. Please process this request independently."

        # Get LLM service
        settings = get_settings()
        llm_service = get_llm_service(settings)

        # Initialize MCP service if agent has MCP servers configured
        mcp_service = None
        available_tools = []
        
        if agent.config.mcp_servers:
            mcp_service = MCPService()
            await mcp_service.connect_servers(agent.config.mcp_servers)
            
            # Get available tools in OpenAI format
            mcp_tools = mcp_service.get_available_tools()
            available_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["inputSchema"]
                    }
                }
                for tool in mcp_tools
            ]
            
            logger.info("MCP tools loaded", tool_count=len(available_tools))

        # Execute the agent using LLM service with tools
        result = await llm_service.generate_agent_response(
            user_message=combined_input,
            agent_config={**agent.config.dict(), "tools": available_tools} if available_tools else agent.config.dict(),
            conversation_history=[]
        )

        # Handle tool calls if present
        if isinstance(result, dict) and "tool_calls" in result:
            # Execute tools and get results
            tool_results = []
            for tool_call in result["tool_calls"]:
                try:
                    tool_result = await mcp_service.execute_tool(
                        tool_call["name"],
                        tool_call["arguments"]
                    )
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "output": str(tool_result)
                    })
                except Exception as e:
                    logger.error("Tool execution failed", tool=tool_call["name"], error=str(e))
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "output": f"Error: {str(e)}"
                    })
            
            # Get final response from LLM with tool results
            # This would require another LLM call with tool results
            # For simplicity, we'll return the tool results as output
            result = f"Tools executed: {len(tool_results)}\n\n" + "\n\n".join(
                [f"Tool result: {tr['output']}" for tr in tool_results]
            )

        # Cleanup MCP connections
        if mcp_service:
            await mcp_service.disconnect_all()

        return ExecuteNodeResponse(
            instanceId=request_data.instanceId,
            agentType=request_data.agentType,
            timestamp=datetime.now(timezone.utc).isoformat(),
            inputs=len(request_data.inputs),
            output=result if isinstance(result, str) else str(result),
        )

    except HTTPException:
        raise
    except Exception as e:
        from datetime import datetime, timezone
        logger.error("Error executing node", error=str(e), instance_id=request_data.instanceId)
        return ExecuteNodeResponse(
            instanceId=request_data.instanceId,
            agentType=request_data.agentType,
            timestamp=datetime.now(timezone.utc).isoformat(),
            inputs=len(request_data.inputs),
            output="",
            error=str(e)
        )


@router.post("/build", response_model=BuildPipelineResponse)
async def build_pipeline(
    request_data: BuildPipelineRequest,
    request: Request,
):
    """
    Execute a BUILD command to create a pipeline with agents.

    Args:
        request_data: Build command request
        request: FastAPI request object

    Returns:
        BuildPipelineResponse: Created nodes and connections
    """
    try:
        logger.info("Processing BUILD command", command=request_data.command)

        # Get agent registry
        agent_registry = getattr(request.app.state, "agent_registry", None)
        if not agent_registry:
            raise HTTPException(status_code=500, detail="Agent registry not available")

        # Get LLM service
        settings = get_settings()
        llm_service = get_llm_service(settings)

        # Create pipeline service
        pipeline_service = AgentPipelineService(llm_service, agent_registry)

        # Execute simple build (for backward compatibility)
        result = pipeline_service.execute_simple_build()
        
        orchestration = result["orchestration"]
        
        return BuildPipelineResponse(
            success=True,
            message=orchestration.get("message", "Pipeline created"),
            nodes=orchestration["nodes"],
            connections=orchestration["connections"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error building pipeline", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

