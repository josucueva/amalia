"""
Agent pipeline service for handling multi-agent workflows.
Implements the hidden agent flow: Interaction → Planner → Orchestrator
"""

import json
import re
import structlog
from typing import Dict, Any, Optional, Tuple, List

from app.services.llm_service import LLMService
from app.services.mcp_service import MCPService
from app.services.model_service import ModelService
from app.services.mcp_server_service import get_mcp_server_service
from app.agents.registry import AgentRegistry
from app.models.agent import Agent

logger = structlog.get_logger()

# Maximum number of tool call iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 10


class AgentPipelineService:
    """Service for orchestrating multi-agent pipelines."""

    def __init__(self, llm_service: LLMService, agent_registry: AgentRegistry):
        """
        Initialize the pipeline service.

        Args:
            llm_service: LLM service instance
            agent_registry: Agent registry instance
        """
        self.llm_service = llm_service
        self.agent_registry = agent_registry
        self.model_service = ModelService()

    async def _execute_tool_calls(
        self, mcp_service: MCPService, tool_calls: List[Dict[str, Any]]
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
                        (
                            str(item.get("text", item))
                            if isinstance(item, dict)
                            else str(item)
                        )
                        for item in tool_result
                    )
                else:
                    output = str(tool_result)

                tool_results.append(
                    {"tool_call_id": tool_call["id"], "role": "tool", "content": output}
                )
            except Exception as e:
                logger.error(
                    "Tool execution failed", tool=tool_call["name"], error=str(e)
                )
                tool_results.append(
                    {
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "content": f"Error executing tool: {str(e)}",
                    }
                )
        return tool_results

    async def _generate_agent_response_with_tools(
        self,
        agent: Agent,
        user_message: str,
        conversation_history: list,
    ) -> str:
        """Generate agent response with MCP tool support.

        Args:
            agent: The agent to use
            user_message: User's message
            conversation_history: Previous messages

        Returns:
            Final agent response as string
        """
        mcp_service = None

        try:
            # Initialize MCP service if agent has MCP servers configured
            available_tools = []

            # Check if the model supports function calling
            model_supports_tools = True
            if agent.config.model:
                # Try to find model by full name (e.g., "groq/llama-3.3-70b-versatile")
                models = self.model_service.get_all_models()
                for model in models:
                    if model.model_name == agent.config.model:
                        model_supports_tools = model.supports_function_calling
                        logger.info(
                            "Model function calling support check",
                            model=agent.config.model,
                            supports_function_calling=model_supports_tools,
                        )
                        break

            # Load MCP servers from both legacy config and new server IDs
            mcp_servers_config = {}

            # New: Prefer mcp_server_ids if the field exists (even if empty list)
            # This allows users to explicitly disable MCP servers
            if (
                hasattr(agent.config, "mcp_server_ids")
                and agent.config.mcp_server_ids is not None
            ):
                # Use the new server IDs approach
                mcp_server_service = get_mcp_server_service()
                for server_id in agent.config.mcp_server_ids:
                    server = mcp_server_service.get_server(server_id)
                    if server and server.is_available:
                        from app.models.agent import MCPServerConfig

                        mcp_servers_config[server_id] = MCPServerConfig(
                            command=server.command, args=server.args, env=server.env
                        )
            elif agent.config.mcp_servers:
                # Legacy: Fall back to old mcp_servers dict only if new field doesn't exist
                mcp_servers_config = agent.config.mcp_servers

            if mcp_servers_config and model_supports_tools:
                mcp_service = MCPService()
                await mcp_service.connect_servers(mcp_servers_config)

                # Get available tools in OpenAI function calling format
                available_tools = mcp_service.get_tools_for_llm()
                logger.info(
                    "MCP tools loaded for agent",
                    agent=agent.config.name,
                    tool_count=len(available_tools),
                )
            elif mcp_servers_config and not model_supports_tools:
                logger.warning(
                    "MCP servers configured but model doesn't support function calling",
                    agent=agent.config.name,
                    model=agent.config.model,
                )

            # Generate initial response
            result = await self.llm_service.generate_agent_response(
                user_message=user_message,
                agent_config=agent.config.dict(),
                conversation_history=conversation_history,
                tools=available_tools if available_tools else None,
            )

            # Handle tool calls with proper LLM loop
            iteration = 0
            messages = []

            # Build initial message context
            if agent.config.system_prompt:
                messages.append(
                    {"role": "system", "content": agent.config.system_prompt}
                )
            if conversation_history:
                messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_message})

            while (
                isinstance(result, dict)
                and "tool_calls" in result
                and iteration < MAX_TOOL_ITERATIONS
            ):
                iteration += 1
                tool_calls = result["tool_calls"]

                logger.info(
                    "Processing tool calls",
                    agent=agent.config.name,
                    iteration=iteration,
                    tool_count=len(tool_calls),
                    tools=[tc["name"] for tc in tool_calls],
                )

                # Execute tools and collect results
                tool_results = await self._execute_tool_calls(mcp_service, tool_calls)

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
                result = await self.llm_service.generate_response(
                    messages=messages,
                    model=agent.config.model,
                    temperature=agent.config.temperature,
                    max_tokens=agent.config.max_tokens,
                    tools=available_tools,
                )

            if iteration >= MAX_TOOL_ITERATIONS:
                logger.warning(
                    "Max tool iterations reached",
                    agent=agent.config.name,
                    iterations=iteration,
                )

            # Return final response as string
            return result if isinstance(result, str) else str(result)

        finally:
            # Cleanup MCP connections
            if mcp_service:
                await mcp_service.disconnect_all()

    def _extract_file_path_from_message(self, message: str) -> Optional[str]:
        """
        Extract file path from user message.

        Args:
            message: User message potentially containing file attachment info

        Returns:
            File path or None
        """
        import re
        # Look for pattern: [File attached: filename at path: /app/data/...]
        match = re.search(r"\[File attached:.*?at path: ([^\]]+)\]", message)
        if match:
            return match.group(1).strip()
        return None

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response.

        Args:
            response: LLM response text

        Returns:
            Parsed JSON dict or None
        """
        try:
            # Try to extract JSON from code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end > start:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
            elif response.strip().startswith("{"):
                # Try parsing whole response as JSON
                return json.loads(response.strip())
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning("Failed to extract JSON from response", error=str(e))

        return None

    async def process_with_pipeline(
        self, user_message: str, conversation_history: list
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process a user message through the three-agent pipeline.

        Flow: Interaction Agent → Planner Agent → Orchestrator Agent

        Args:
            user_message: User's original message
            conversation_history: Previous messages

        Returns:
            Tuple of (final_response, orchestration_data)
        """
        # Step 1: Interaction Agent - Refine the prompt
        interaction_agent = self.agent_registry.get_agent_by_name("interaction_agent")
        if not interaction_agent:
            logger.error("Interaction agent not found")
            return "Interaction agent is not available.", None

        logger.info("Step 1: Processing with interaction agent")
        interaction_response = await self._generate_agent_response_with_tools(
            agent=interaction_agent,
            user_message=user_message,
            conversation_history=conversation_history,
        )

        # Check if interaction agent wants to plan a pipeline
        action_data = self._extract_json_from_response(interaction_response)

        if not action_data or action_data.get("action") != "plan_pipeline":
            # No pipeline planning needed, return interaction agent's response
            logger.info("No pipeline planning requested")
            return interaction_response, None

        improved_prompt = action_data.get("improved_prompt", user_message)
        
        # Extract file path if present
        file_path = self._extract_file_path_from_message(user_message)
        if file_path:
            logger.info("File path extracted from message", file_path=file_path)
            # Add file path to improved prompt for planner
            improved_prompt = f"{improved_prompt}\n\n[ATTACHED_FILE: {file_path}]"
        
        logger.info(
            "Step 2: Interaction agent created improved prompt",
            prompt_length=len(improved_prompt),
            has_file=bool(file_path),
        )

        # Step 2: Planner Agent - Create execution plan
        planner_agent = self.agent_registry.get_agent_by_name("planner_agent")
        if not planner_agent:
            logger.error("Planner agent not found")
            return "Pipeline planning is not available.", None

        logger.info("Step 3: Processing with planner agent")
        planner_response = await self._generate_agent_response_with_tools(
            agent=planner_agent,
            user_message=improved_prompt,
            conversation_history=[],  # Fresh context for planner
        )

        plan_data = self._extract_json_from_response(planner_response)

        if not plan_data or "plan" not in plan_data:
            logger.error("Planner failed to create valid plan")
            return "Failed to create execution plan.", None

        plan = plan_data["plan"]
        logger.info(
            "Step 4: Planner created plan",
            phases=len(plan.get("phases", [])),
            complexity=plan.get("complexity"),
        )

        # Step 3: Orchestrator Agent - Create canvas configuration
        orchestrator_agent = self.agent_registry.get_agent_by_name("orchestrator_agent")
        if not orchestrator_agent:
            logger.error("Orchestrator agent not found")
            return "Pipeline orchestration is not available.", None

        # Convert plan to a message for orchestrator
        orchestrator_input = json.dumps(plan_data, indent=2)

        logger.info("Step 5: Processing with orchestrator agent")
        orchestrator_response = await self._generate_agent_response_with_tools(
            agent=orchestrator_agent,
            user_message=f"Create a canvas configuration for this plan:\n\n{orchestrator_input}",
            conversation_history=[],  # Fresh context for orchestrator
        )

        orchestration_data = self._extract_json_from_response(orchestrator_response)

        if not orchestration_data or "orchestration" not in orchestration_data:
            logger.error("Orchestrator failed to create valid configuration")
            return "Failed to create pipeline configuration.", None

        orchestration = orchestration_data["orchestration"]

        # Map agent types to agent IDs
        orchestration = self._resolve_agent_types(orchestration)
        
        # Add file path to first node if file was attached
        if file_path and orchestration.get("nodes"):
            first_node = orchestration["nodes"][0]
            first_node["filePath"] = file_path
            logger.info("File path added to first node", instance_id=first_node.get("instanceId"), file_path=file_path)

        logger.info(
            "Step 6: Orchestrator created configuration",
            nodes=len(orchestration.get("nodes", [])),
            connections=len(orchestration.get("connections", [])),
            has_file=bool(file_path),
        )

        # Create final user-facing message
        objective = plan.get("objective", "your pipeline")
        phases_count = len(plan.get("phases", []))
        nodes_count = len(orchestration.get("nodes", []))

        final_message = f"""✅ Pipeline created successfully!

**Objective:** {objective}

**Plan:**
- {phases_count} phases identified
- {nodes_count} agents instantiated
- Complexity: {plan.get("complexity", "unknown")}

Switch to Canvas Mode to see your pipeline in action!"""

        return final_message, {"orchestration": orchestration}

    def _resolve_agent_types(self, orchestration: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve agent type names to actual agent IDs.

        Args:
            orchestration: Orchestration data with agentType fields

        Returns:
            Updated orchestration with agentId fields
        """
        nodes = orchestration.get("nodes", [])

        for node in nodes:
            agent_type = node.get("agentType")
            if agent_type and "agentId" not in node:
                # Find agent by name
                agent = self.agent_registry.get_agent_by_name(agent_type)
                if agent:
                    node["agentId"] = agent.id
                else:
                    logger.warning(
                        f"Agent type '{agent_type}' not found, keeping type name"
                    )
                    node["agentId"] = agent_type

        orchestration["nodes"] = nodes
        return orchestration

    def execute_simple_build(self) -> Dict[str, Any]:
        """
        Simple build command for backward compatibility.
        Creates a basic pipeline with 2 random agents.

        Returns:
            Orchestration data with nodes and connections
        """
        import random
        import time

        # Get all available agents (excluding hidden and interaction agents)
        agents = self.agent_registry.list_agents()
        available_agents = [
            agent
            for agent in agents
            if agent.config.name
            not in ["interaction_agent", "planner_agent", "orchestrator_agent"]
            and not agent.config.metadata.get("is_hidden", False)
        ]

        if len(available_agents) < 2:
            raise ValueError("Not enough agents available")

        # Select two random agents
        selected_agents = random.sample(available_agents, 2)

        # Generate instance IDs
        timestamp = int(time.time() * 1000)
        instance1_id = f"instance_{timestamp}_{random.randint(1000, 9999)}"
        instance2_id = f"instance_{timestamp + 1}_{random.randint(1000, 9999)}"

        orchestration = {
            "nodes": [
                {
                    "instanceId": instance1_id,
                    "agentId": selected_agents[0].id,
                    "position": {"x": 200, "y": 200},
                },
                {
                    "instanceId": instance2_id,
                    "agentId": selected_agents[1].id,
                    "position": {"x": 500, "y": 200},
                },
            ],
            "connections": [
                {
                    "id": f"conn_{timestamp}",
                    "fromInstanceId": instance1_id,
                    "toInstanceId": instance2_id,
                }
            ],
            "message": f"Simple pipeline with {selected_agents[0].config.name} → {selected_agents[1].config.name}",
        }

        return {"orchestration": orchestration}
