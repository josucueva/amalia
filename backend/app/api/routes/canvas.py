"""
Canvas routes for managing agent pipelines and connections.
"""

import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import structlog

from app.services.agent_pipeline import AgentPipelineService
from app.services.llm_service import get_llm_service
from app.services.mcp_service import MCPService
from app.services.mcp_server_service import get_mcp_server_service
from app.services.model_service import ModelService
from app.config import get_settings

logger = structlog.get_logger()
router = APIRouter()

# Maximum number of tool call iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 10


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
    config: Optional[Dict[str, Any]] = None  # Instance-specific config overrides
    mcpServerIds: Optional[List[str]] = None  # MCP server IDs for this instance
    filePath: Optional[str] = None  # File path attached to this node


class ExecuteNodeResponse(BaseModel):
    instanceId: str
    agentType: str
    timestamp: str
    inputs: int
    output: str
    error: Optional[str] = None


async def _execute_tool_calls(
    mcp_service: MCPService, tool_calls: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Execute a list of tool calls and return the results.

    Args:
        mcp_service: The MCP service instance to use.
        tool_calls: List of tool call specifications.

    Returns:
        List of tool results with tool_call_id and output.
    """
    tool_results = []
    for tool_call in tool_calls:
        try:
            tool_result = await mcp_service.execute_tool(
                tool_call["name"], tool_call["arguments"]
            )
            # Format result content
            if isinstance(tool_result, list):
                output = "\n".join(
                    str(item.get("text", item)) if isinstance(item, dict) else str(item)
                    for item in tool_result
                )
            else:
                output = str(tool_result)

            tool_results.append(
                {"tool_call_id": tool_call["id"], "role": "tool", "content": output}
            )
        except Exception as e:
            logger.error("Tool execution failed", tool=tool_call["name"], error=str(e))
            tool_results.append(
                {
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "content": f"Error executing tool: {str(e)}",
                }
            )
    return tool_results


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
    mcp_service = None

    try:
        logger.info(
            "Executing agent node",
            instance_id=request_data.instanceId,
            agent_type=request_data.agentType,
            inputs_count=len(request_data.inputs),
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
                detail=f"Agent type '{request_data.agentType}' not found",
            )

        # Prepare input for agent execution
        # Combine all inputs into a single context
        if request_data.inputs:
            combined_input = "\n\n".join(
                [
                    f"Input {i+1}:\n{inp.get('output', '')}"
                    for i, inp in enumerate(request_data.inputs)
                ]
            )
        else:
            combined_input = (
                "No input data provided. Please process this request independently."
            )
        
        # If this node has a file attached, prepend file path to input
        if request_data.filePath:
            file_instruction = f"""[FILE ATTACHED]
You have access to a file at path: {request_data.filePath}

Use the read_file or read_text_file tool to load and process this file.

IMPORTANT: The file path is: {request_data.filePath}

"""
            combined_input = file_instruction + combined_input
            logger.info("File path added to node input", instance_id=request_data.instanceId, file_path=request_data.filePath)

        # Get LLM service
        settings = get_settings()
        llm_service = get_llm_service(settings)

        # Initialize MCP service if agent has MCP servers configured
        available_tools = []

        # Use instance-specific MCP server IDs if provided, otherwise fall back to agent config
        mcp_server_ids_to_use = (
            request_data.mcpServerIds
            if request_data.mcpServerIds is not None
            else (
                agent.config.mcp_server_ids
                if hasattr(agent.config, "mcp_server_ids")
                else None
            )
        )

        # Check if model supports function calling
        model_supports_tools = True
        model_service = ModelService()
        models = model_service.get_all_models()
        for model in models:
            if model.model_name == (
                request_data.config.get("model", agent.config.model)
                if request_data.config
                else agent.config.model
            ):
                model_supports_tools = model.supports_function_calling
                break

        if mcp_server_ids_to_use and model_supports_tools:
            # Load MCP servers using the new server IDs approach
            mcp_service = MCPService()
            mcp_server_service = get_mcp_server_service()
            mcp_servers_config = {}

            for server_id in mcp_server_ids_to_use:
                server = mcp_server_service.get_server(server_id)
                if server and server.is_available:
                    from app.models.agent import MCPServerConfig

                    mcp_servers_config[server_id] = MCPServerConfig(
                        command=server.command, args=server.args, env=server.env
                    )

            if mcp_servers_config:
                await mcp_service.connect_servers(mcp_servers_config)
                available_tools = mcp_service.get_tools_for_llm()
                logger.info(
                    "MCP tools loaded for instance",
                    instance_id=request_data.instanceId,
                    tool_count=len(available_tools),
                )
        elif agent.config.mcp_servers:
            # Legacy: Fall back to old mcp_servers dict if no server IDs provided
            mcp_service = MCPService()
            await mcp_service.connect_servers(agent.config.mcp_servers)

            # Get available tools in OpenAI function calling format
            available_tools = mcp_service.get_tools_for_llm()
            logger.info("MCP tools loaded", tool_count=len(available_tools))

        # Use instance config overrides if provided
        instance_model = (
            request_data.config.get("model", agent.config.model)
            if request_data.config
            else agent.config.model
        )
        instance_temperature = (
            request_data.config.get("temperature", agent.config.temperature)
            if request_data.config
            else agent.config.temperature
        )
        instance_max_tokens = (
            request_data.config.get("max_tokens", agent.config.max_tokens)
            if request_data.config
            else agent.config.max_tokens
        )
        instance_system_prompt = (
            request_data.config.get("system_prompt", agent.config.system_prompt)
            if request_data.config
            else agent.config.system_prompt
        )

        # Build conversation messages for the LLM
        messages = [
            {"role": "system", "content": instance_system_prompt},
            {"role": "user", "content": combined_input},
        ]

        # Execute the agent using LLM service with tools
        result = await llm_service.generate_response(
            messages=messages,
            model=instance_model,
            temperature=instance_temperature,
            max_tokens=instance_max_tokens,
            tools=available_tools if available_tools else None,
        )

        # Handle tool calls with proper LLM loop
        iteration = 0
        while (
            isinstance(result, dict)
            and "tool_calls" in result
            and iteration < MAX_TOOL_ITERATIONS
        ):
            iteration += 1
            tool_calls = result["tool_calls"]

            logger.info(
                "Processing tool calls",
                iteration=iteration,
                tool_count=len(tool_calls),
                tools=[tc["name"] for tc in tool_calls],
            )

            # Execute tools and collect results
            tool_results = await _execute_tool_calls(mcp_service, tool_calls)

            # Build the assistant message with tool calls
            assistant_message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": (
                                json.dumps(tc["arguments"])
                                if not isinstance(tc["arguments"], str)
                                else tc["arguments"]
                            ),
                        },
                    }
                    for tc in tool_calls
                ],
            }

            # Add assistant message and tool results to conversation
            messages.append(assistant_message)
            for tr in tool_results:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "content": tr["content"],
                    }
                )

            # Get next response from LLM
            result = await llm_service.generate_response(
                messages=messages,
                model=instance_model,
                temperature=instance_temperature,
                max_tokens=instance_max_tokens,
                tools=available_tools,
            )

        if iteration >= MAX_TOOL_ITERATIONS:
            logger.warning(
                "Max tool iterations reached",
                instance_id=request_data.instanceId,
                iterations=iteration,
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
        logger.error(
            "Error executing node", error=str(e), instance_id=request_data.instanceId
        )
        return ExecuteNodeResponse(
            instanceId=request_data.instanceId,
            agentType=request_data.agentType,
            timestamp=datetime.now(timezone.utc).isoformat(),
            inputs=len(request_data.inputs),
            output="",
            error=str(e),
        )
    finally:
        # Ensure MCP connections are cleaned up even on error
        if mcp_service:
            try:
                await mcp_service.disconnect_all()
            except Exception as cleanup_error:
                logger.warning("Error during MCP cleanup", error=str(cleanup_error))


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
