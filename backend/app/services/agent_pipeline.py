"""
Agent pipeline service for handling multi-agent workflows.
Implements the hidden agent flow: Interaction → Planner → Orchestrator
"""

import json
import re
from pathlib import Path
import structlog
from typing import Dict, Any, Optional, Tuple, List
import yaml

from app.services.llm_service import LLMService
from app.services.mcp_service import MCPService
from app.services.model_service import ModelService
from app.agents.registry import AgentRegistry
from app.models.agent import Agent

logger = structlog.get_logger()

# Maximum number of tool call iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 10


class AgentPipelineService:
    """Service for orchestrating multi-agent pipelines."""

    def __init__(
        self,
        llm_service: LLMService,
        agent_registry: AgentRegistry,
        mcp_server_service=None,
    ):
        """
        Initialize the pipeline service.

        Args:
            llm_service: LLM service instance
            agent_registry: Agent registry instance
            mcp_server_service: MCP server service instance (optional)
        """
        self.llm_service = llm_service
        self.agent_registry = agent_registry
        self.model_service = ModelService()
        self.mcp_server_service = mcp_server_service

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

            # Check if the model supports function calling.
            # Local Ollama models are conservative by default to avoid sending
            # large tool schemas that can cause long stalls/timeouts.
            model_name = agent.config.model or ""
            model_supports_tools = not model_name.startswith("ollama/")
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
                if self.mcp_server_service:
                    for server_id in agent.config.mcp_server_ids:
                        server = await self.mcp_server_service.get_server(server_id)
                        if not server:
                            candidate_ids = [
                                f"python-{server_id}",
                                server_id.replace("-", "_"),
                                server_id.replace("_", "-"),
                                f"python-{server_id.replace('-', '_')}",
                                f"python-{server_id.replace('_', '-')}",
                            ]
                            for candidate_id in candidate_ids:
                                if candidate_id == server_id:
                                    continue
                                server = await self.mcp_server_service.get_server(
                                    candidate_id
                                )
                                if server:
                                    break

                        if server and server.is_available:
                            from app.models.agent import MCPServerConfig

                            mcp_servers_config[server_id] = MCPServerConfig(
                                command=server.command, args=server.args, env=server.env
                            )
                        else:
                            logger.warning(
                                "Configured MCP server ID could not be resolved",
                                agent=agent.config.name,
                                requested_server_id=server_id,
                            )
                else:
                    logger.warning(
                        "MCP server service not available, skipping MCP server loading",
                        agent=agent.config.name,
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
                    parsed = json.loads(json_str)
                    logger.debug(
                        "Extracted JSON from code block", keys=list(parsed.keys())
                    )
                    return parsed
            elif "```" in response:
                # Try generic code block
                start = response.find("```") + 3
                end = response.find("```", start)
                if end > start:
                    json_str = response[start:end].strip()
                    # Remove language identifier if present
                    if json_str.startswith(("json\n", "JSON\n")):
                        json_str = json_str[4:].strip()
                    parsed = json.loads(json_str)
                    logger.debug(
                        "Extracted JSON from generic code block",
                        keys=list(parsed.keys()),
                    )
                    return parsed
            elif response.strip().startswith("{"):
                # Try parsing whole response as JSON
                parsed = json.loads(response.strip())
                logger.debug("Parsed entire response as JSON", keys=list(parsed.keys()))
                return parsed
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(
                "Failed to extract JSON from response",
                error=str(e),
                response_preview=response[:200] if response else None,
            )

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
        interaction_agent = self.agent_registry.get_agent("interaction_agent")
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

        file_path = self._extract_file_path_from_message(user_message)
        if file_path and not self._dataset_analysis_is_sufficient(
            action_data, file_path
        ):
            logger.warning(
                "Interaction output missing required dataset analysis; requesting strict retry",
                file_path=file_path,
            )
            retry_prompt = (
                f"{user_message}\n\n"
                "[STRICT_REQUIREMENT]\n"
                "You must call MCP tools read_file_head(filepath, n_rows=100) and analyze_csv "
                "before responding. Return JSON with action=plan_pipeline and complete "
                "dataset_analysis including file_path, rows, column_names, column_types, "
                "target_column, task_type, data_quality, and sample_rows."
            )
            interaction_response = await self._generate_agent_response_with_tools(
                agent=interaction_agent,
                user_message=retry_prompt,
                conversation_history=conversation_history,
            )
            action_data = self._extract_json_from_response(interaction_response)

        if not action_data or action_data.get("action") != "plan_pipeline":
            # No pipeline planning needed, return interaction agent's response
            logger.info("No pipeline planning requested")
            return interaction_response, None

        improved_prompt = action_data.get("improved_prompt", user_message)
        dataset_analysis = (
            action_data.get("dataset_analysis", {})
            if isinstance(action_data, dict)
            else {}
        )

        # Extract file path if present
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
        planner_agent = self.agent_registry.get_agent("planner_agent")
        if not planner_agent:
            logger.error("Planner agent not found")
            return "Pipeline planning is not available.", None

        logger.info("Step 3: Processing with planner agent")
        planner_input = improved_prompt
        if dataset_analysis:
            planner_input = (
                f"{improved_prompt}\n\n"
                "[DATASET_ANALYSIS_JSON]\n"
                f"{json.dumps(dataset_analysis, ensure_ascii=True)}"
            )

        planner_response = await self._generate_agent_response_with_tools(
            agent=planner_agent,
            user_message=planner_input,
            conversation_history=[],  # Fresh context for planner
        )

        plan_data = self._extract_json_from_response(planner_response)

        if file_path and not self._plan_has_header_evidence(plan_data, file_path):
            logger.warning(
                "Planner output missing header evidence; requesting strict retry",
                file_path=file_path,
            )
            planner_retry_input = (
                f"{planner_input}\n\n"
                "[STRICT_REQUIREMENT]\n"
                "Before final plan, call MCP read_file_head on the attached dataset and include "
                "plan.planner_file_header with file_path, columns, sample_rows_read."
            )
            planner_response = await self._generate_agent_response_with_tools(
                agent=planner_agent,
                user_message=planner_retry_input,
                conversation_history=[],
            )
            plan_data = self._extract_json_from_response(planner_response)

        if not plan_data or "plan" not in plan_data:
            logger.error(
                "Planner failed to create valid plan",
                plan_data=plan_data,
                response_preview=planner_response[:500] if planner_response else None,
            )
            return "Failed to create execution plan.", None

        plan = plan_data["plan"]
        logger.info(
            "Step 4: Planner created plan",
            phases=len(plan.get("phases", [])),
            complexity=plan.get("complexity"),
        )

        logger.info("Step 5: Building simplified orchestration export")
        orchestration = await self._build_simplified_orchestration_export(
            plan_data=plan_data,
            file_path=file_path,
            target_column_hint=(
                action_data.get("dataset_analysis", {}).get("target_column")
                if isinstance(action_data, dict)
                else None
            ),
            dataset_analysis=(
                dataset_analysis if isinstance(dataset_analysis, dict) else None
            ),
        )

        final_message = (
            "✅ Simplified pipeline export generated.\n\n"
            "This export includes only real MCP server records and agent YAML references. "
            "It is intended as an intermediate AMALIA format for downstream conversion "
            "to Sim AI workflows."
        )

        return final_message, {"orchestration": orchestration}

    async def _build_simplified_orchestration_export(
        self,
        plan_data: Dict[str, Any],
        file_path: Optional[str],
        target_column_hint: Optional[str] = None,
        dataset_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a deterministic intermediate export from planner output.

        The output is intentionally simpler than Sim AI canvas JSON and keeps only
        the agent/YAML references plus real MCP server records required for
        downstream conversion.
        """
        plan = plan_data.get("plan", {})
        phases = plan.get("phases", [])
        objective_text = str(plan.get("objective") or "")
        inferred_task_type = self._infer_task_type(objective_text, file_path)
        tool_catalog = self._load_tool_catalog_index()
        validation_issues: List[Dict[str, Any]] = []

        resolved_dataset_path = self._resolve_data_file_path(file_path)
        if file_path and not resolved_dataset_path:
            validation_issues.append(
                {
                    "code": "dataset_file_not_found",
                    "message": f"Dataset file not found on disk: {file_path}",
                }
            )

        servers_by_id: Dict[str, Any] = {}
        servers_by_name: Dict[str, Any] = {}
        servers_by_normalized_name: Dict[str, Any] = {}
        if self.mcp_server_service:
            try:
                servers = await self.mcp_server_service.list_servers()
                for server in servers:
                    servers_by_id[server.id] = server
                    servers_by_name[server.name.lower()] = server
                    servers_by_normalized_name[
                        self._normalize_reference(server.name)
                    ] = server
            except Exception as exc:
                logger.warning("Failed to list MCP servers for export", error=str(exc))

        used_server_ids: set[str] = set()
        steps: List[Dict[str, Any]] = []
        nodes: List[Dict[str, Any]] = []
        connections: List[Dict[str, Any]] = []

        for index, phase in enumerate(phases, start=1):
            phase_number = int(phase.get("phase_number") or index)
            planner_agent_id = str(phase.get("agent_id") or "").strip()
            planner_agent_name = str(phase.get("agent_name") or "").strip()

            agent = self._resolve_agent_reference(planner_agent_id, planner_agent_name)

            resolved_agent_id = agent.id if agent else None
            agent_yaml_relative, agent_yaml_exists = self._resolve_agent_yaml_reference(
                resolved_agent_id
            )
            if not resolved_agent_id:
                validation_issues.append(
                    {
                        "code": "agent_unresolved",
                        "message": (
                            "Planner referenced unresolved agent "
                            f"id='{planner_agent_id}' name='{planner_agent_name}'"
                        ),
                        "phase_number": phase_number,
                    }
                )
            elif not agent_yaml_exists:
                validation_issues.append(
                    {
                        "code": "agent_yaml_missing",
                        "message": f"Agent YAML not found: {agent_yaml_relative}",
                        "phase_number": phase_number,
                    }
                )

            planner_server_name = str(phase.get("mcp_server") or "").strip()
            resolved_server = self._resolve_server_reference(
                planner_server_name,
                servers_by_id,
                servers_by_name,
                servers_by_normalized_name,
            )

            resolved_server_payload = None
            if resolved_server:
                used_server_ids.add(resolved_server.id)
                resolved_server_payload = {
                    "id": resolved_server.id,
                    "name": resolved_server.name,
                    "is_available": resolved_server.is_available,
                }
            else:
                validation_issues.append(
                    {
                        "code": "mcp_server_unresolved",
                        "message": (
                            f"Planner referenced unresolved MCP server '{planner_server_name}'"
                        ),
                        "phase_number": phase_number,
                    }
                )

            step_tools = []
            for tool in phase.get("tools", []):
                tool_name = str(tool.get("tool_name") or "")
                selected_model_type = self._select_model_type_for_phase(phase)
                planner_parameters = tool.get("parameters")
                replication_parameters = self._build_tool_replication_parameters(
                    tool_name=tool_name,
                    tool_catalog=tool_catalog,
                    file_path=file_path,
                    target_column=target_column_hint,
                    task_type=inferred_task_type,
                    selected_model_type=selected_model_type,
                    planner_parameters=(
                        planner_parameters
                        if isinstance(planner_parameters, dict)
                        else None
                    ),
                    dataset_analysis=(
                        dataset_analysis if isinstance(dataset_analysis, dict) else None
                    ),
                )
                catalog_parameters = self._catalog_parameters_for_tool(
                    tool_name=tool_name,
                    tool_catalog=tool_catalog,
                )
                if not catalog_parameters:
                    validation_issues.append(
                        {
                            "code": "tool_not_in_catalog",
                            "message": f"Tool '{tool_name}' not found in mcp-catalog.yaml",
                            "phase_number": phase_number,
                        }
                    )
                    continue

                missing_required_parameters = self._find_missing_required_parameters(
                    catalog_parameters=catalog_parameters,
                    replication_parameters=replication_parameters,
                )
                if missing_required_parameters:
                    validation_issues.append(
                        {
                            "code": "tool_required_parameters_unresolved",
                            "message": (
                                f"Tool '{tool_name}' has unresolved required parameters: "
                                f"{', '.join(missing_required_parameters)}"
                            ),
                            "phase_number": phase_number,
                            "tool_name": tool_name,
                            "missing_parameters": missing_required_parameters,
                        }
                    )

                step_tools.append(
                    {
                        "tool_name": tool_name,
                        "description": tool.get("description"),
                        "catalog_parameters": catalog_parameters,
                        "planner_parameters": (
                            planner_parameters
                            if isinstance(planner_parameters, dict)
                            else {}
                        ),
                        "replication_parameters": replication_parameters,
                        "missing_required_parameters": missing_required_parameters,
                        "parameter_source": "mcp_catalog_defaults_and_context",
                    }
                )

            selected_model_type = self._select_model_type_for_phase(phase)

            if not step_tools:
                validation_issues.append(
                    {
                        "code": "no_valid_tools_for_phase",
                        "message": "All tools in phase were invalid or unresolved",
                        "phase_number": phase_number,
                    }
                )

            steps.append(
                {
                    "phase_number": phase_number,
                    "agent": {
                        "id": resolved_agent_id,
                        "name": agent.config.name if agent else planner_agent_name,
                        "yaml_path": agent_yaml_relative,
                        "yaml_exists": agent_yaml_exists,
                        "planner_reference": {
                            "agent_id": planner_agent_id or None,
                            "agent_name": planner_agent_name or None,
                        },
                    },
                    "planner_mcp_server": planner_server_name,
                    "resolved_mcp_server": resolved_server_payload,
                    "tools": step_tools,
                    "selected_model_type": selected_model_type,
                    "rationale": phase.get("rationale"),
                }
            )

            nodes.append(
                {
                    "instanceId": f"phase-{phase_number}",
                    "agentId": (
                        resolved_agent_id
                        or planner_agent_id
                        or planner_agent_name
                        or f"unresolved_phase_{phase_number}"
                    ),
                    "position": {"x": 220 * phase_number, "y": 200},
                }
            )

        for idx in range(len(nodes) - 1):
            connections.append(
                {
                    "id": f"conn-{idx + 1}",
                    "fromInstanceId": nodes[idx]["instanceId"],
                    "toInstanceId": nodes[idx + 1]["instanceId"],
                }
            )

        mcp_servers = []
        for server_id in sorted(used_server_ids):
            server = servers_by_id.get(server_id)
            if not server:
                continue
            mcp_servers.append(
                {
                    "id": server.id,
                    "name": server.name,
                    "command": server.command,
                    "args": server.args,
                    "env": server.env,
                    "is_available": server.is_available,
                    "description": server.description,
                }
            )

        return {
            "type": "amalia_pipeline_export_v1",
            "format_version": "1.0",
            "objective": plan.get("objective"),
            "complexity": plan.get("complexity"),
            "dataset": {
                "file_path": file_path,
                "exists_on_disk": bool(resolved_dataset_path),
                "resolved_path": (
                    str(resolved_dataset_path) if resolved_dataset_path else None
                ),
            },
            "steps": steps,
            "mcp_servers": mcp_servers,
            "validation": {
                "status": "valid" if not validation_issues else "invalid",
                "issue_count": len(validation_issues),
                "issues": validation_issues,
            },
            # Kept for backward compatibility with existing session snapshot handling.
            "nodes": nodes,
            "connections": connections,
        }

    def _normalize_reference(self, value: Optional[str]) -> str:
        """Normalize IDs/names to compare planner references deterministically."""
        if not value:
            return ""
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())

    def _resolve_agent_reference(
        self,
        planner_agent_id: str,
        planner_agent_name: str,
    ) -> Optional[Agent]:
        """Resolve planner agent references to a canonical registry agent."""
        if planner_agent_id:
            agent = self.agent_registry.get_agent(planner_agent_id)
            if agent:
                return agent

        if planner_agent_name:
            agent = self.agent_registry.get_agent_by_name(planner_agent_name)
            if agent:
                return agent

        normalized_id = self._normalize_reference(planner_agent_id)
        normalized_name = self._normalize_reference(planner_agent_name)
        if not normalized_id and not normalized_name:
            return None

        for candidate in self.agent_registry.list_agents():
            if (
                normalized_id
                and self._normalize_reference(candidate.id) == normalized_id
            ):
                return candidate
            if (
                normalized_name
                and self._normalize_reference(candidate.config.name) == normalized_name
            ):
                return candidate

        return None

    def _resolve_server_reference(
        self,
        planner_server_reference: str,
        servers_by_id: Dict[str, Any],
        servers_by_name: Dict[str, Any],
        servers_by_normalized_name: Dict[str, Any],
    ) -> Optional[Any]:
        """Resolve planner MCP server references to a canonical server record."""
        if not planner_server_reference:
            return None

        if planner_server_reference in servers_by_id:
            return servers_by_id[planner_server_reference]

        lowered = planner_server_reference.lower()
        if lowered in servers_by_name:
            return servers_by_name[lowered]

        normalized_reference = self._normalize_reference(planner_server_reference)
        if normalized_reference and normalized_reference in servers_by_normalized_name:
            return servers_by_normalized_name[normalized_reference]

        candidate_ids = [
            planner_server_reference,
            f"python-{planner_server_reference}",
            planner_server_reference.replace("-", "_"),
            planner_server_reference.replace("_", "-"),
            f"python-{planner_server_reference.replace('-', '_')}",
            f"python-{planner_server_reference.replace('_', '-')}",
        ]

        for candidate_id in candidate_ids:
            if candidate_id in servers_by_id:
                return servers_by_id[candidate_id]

        return None

    def _find_missing_required_parameters(
        self,
        catalog_parameters: List[Dict[str, Any]],
        replication_parameters: Dict[str, Any],
    ) -> List[str]:
        """Return required catalog parameters still unresolved in replication params."""
        missing: List[str] = []
        for parameter in catalog_parameters:
            if not parameter.get("required"):
                continue

            name = parameter.get("name")
            if not name:
                continue

            value = replication_parameters.get(name)
            if value is None or value == "":
                missing.append(name)

        return missing

    def _dataset_analysis_is_sufficient(
        self,
        action_data: Optional[Dict[str, Any]],
        expected_file_path: str,
    ) -> bool:
        """Validate that interaction agent included concrete dataset analysis."""
        if not isinstance(action_data, dict):
            return False
        if action_data.get("action") != "plan_pipeline":
            return False

        analysis = action_data.get("dataset_analysis")
        if not isinstance(analysis, dict):
            return False

        required_keys = [
            "file_path",
            "rows",
            "column_names",
            "column_types",
            "sample_rows",
        ]
        if any(key not in analysis for key in required_keys):
            return False

        file_path = str(analysis.get("file_path") or "")
        if expected_file_path and file_path and expected_file_path not in file_path:
            return False

        rows = analysis.get("rows")
        column_names = analysis.get("column_names")
        if not isinstance(rows, int) or rows <= 0:
            return False
        if not isinstance(column_names, list) or not column_names:
            return False

        return True

    def _plan_has_header_evidence(
        self,
        plan_data: Optional[Dict[str, Any]],
        expected_file_path: str,
    ) -> bool:
        """Validate planner output includes MCP-backed header evidence."""
        if not isinstance(plan_data, dict):
            return False
        plan = plan_data.get("plan")
        if not isinstance(plan, dict):
            return False

        header = plan.get("planner_file_header")
        if not isinstance(header, dict):
            return False

        file_path = str(header.get("file_path") or "")
        columns = header.get("columns")
        sample_rows_read = header.get("sample_rows_read")

        if expected_file_path and file_path and expected_file_path not in file_path:
            return False
        if not isinstance(columns, list) or not columns:
            return False
        if not isinstance(sample_rows_read, int) or sample_rows_read < 1:
            return False

        return True

    def _resolve_data_file_path(self, file_path: Optional[str]) -> Optional[Path]:
        """Resolve runtime dataset path to an existing local path for factual checks."""
        if not file_path:
            return None

        candidate = Path(file_path)
        if candidate.exists():
            return candidate

        normalized = str(file_path).replace("\\", "/")
        if normalized.startswith("/app/"):
            relative = normalized[len("/app/") :]
            local_candidate = Path(relative)
            if local_candidate.exists():
                return local_candidate

        for fallback in [
            Path("data") / Path(file_path).name,
            Path("backend/data") / Path(file_path).name,
        ]:
            if fallback.exists():
                return fallback

        return None

    def _resolve_agent_yaml_reference(
        self,
        agent_id: Optional[str],
    ) -> Tuple[Optional[str], bool]:
        """Resolve canonical agent YAML path in both repo-root and backend cwd contexts."""
        if not agent_id:
            return None, False

        relative_path = f"config/agents/{agent_id}.yaml"
        project_root = Path(__file__).resolve().parents[3]
        backend_root = Path(__file__).resolve().parents[2]

        candidates = [
            Path(relative_path),
            backend_root / relative_path,
            project_root / relative_path,
        ]

        for candidate in candidates:
            if candidate.exists():
                return relative_path, True

        return relative_path, False

    def _load_tool_catalog_index(self) -> Dict[str, Dict[str, Any]]:
        """Load MCP tool metadata from mcp-catalog.yaml into a tool lookup."""
        catalog_paths = [
            Path("/app/mcp-catalog.yaml"),
            Path("backend/mcp-catalog.yaml"),
            Path("mcp-catalog.yaml"),
        ]

        catalog_data = None
        for path in catalog_paths:
            if not path.exists():
                continue
            try:
                with open(path, "r", encoding="utf-8") as file:
                    catalog_data = yaml.safe_load(file) or {}
                break
            except Exception as exc:
                logger.warning(
                    "Failed to read MCP catalog", path=str(path), error=str(exc)
                )

        if not catalog_data:
            return {}

        tool_catalog: Dict[str, Dict[str, Any]] = {}
        for server in catalog_data.get("servers", []) or []:
            server_name = str(server.get("name") or "")
            for tool in server.get("tools", []) or []:
                tool_name = str(tool.get("name") or "")
                if not tool_name:
                    continue

                parsed_inputs = []
                for raw_input in tool.get("inputs", []) or []:
                    if not isinstance(raw_input, dict) or len(raw_input) != 1:
                        continue
                    param_name = next(iter(raw_input.keys()))
                    type_spec = str(raw_input[param_name])
                    default_match = re.search(r"\(default:\s*([^\)]+)\)", type_spec)
                    default_value = None
                    if default_match:
                        default_value = default_match.group(1).strip().strip("'\"")

                    parsed_inputs.append(
                        {
                            "name": param_name,
                            "type_spec": type_spec,
                            "default": default_value,
                        }
                    )

                tool_catalog[tool_name] = {
                    "server_name": server_name,
                    "inputs": parsed_inputs,
                }

        return tool_catalog

    def _build_tool_replication_parameters(
        self,
        tool_name: str,
        tool_catalog: Dict[str, Dict[str, Any]],
        file_path: Optional[str],
        target_column: Optional[str],
        task_type: Optional[str],
        selected_model_type: Optional[str],
        planner_parameters: Optional[Dict[str, Any]] = None,
        dataset_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build deterministic parameters to help replay a generated pipeline."""
        params: Dict[str, Any] = {}
        tool_info = tool_catalog.get(tool_name) or {}
        planner_parameters = planner_parameters or {}
        dataset_analysis = dataset_analysis or {}

        for input_info in tool_info.get("inputs", []):
            name = input_info.get("name")
            if not name:
                continue

            if name in planner_parameters and planner_parameters.get(name) is not None:
                params[name] = planner_parameters.get(name)
                continue

            if name in {"filepath", "filename", "input_data_path", "test_data_path"}:
                if file_path:
                    params[name] = file_path
                else:
                    params[name] = None
                continue

            if name == "target_column" and target_column:
                params[name] = target_column
                continue

            inferred_value = self._infer_dataset_specific_param(
                tool_name=tool_name,
                param_name=name,
                dataset_analysis=dataset_analysis,
                target_column=target_column,
                task_type=task_type,
                selected_model_type=selected_model_type,
            )
            if inferred_value is not None:
                params[name] = inferred_value
                continue

            if name == "model_type" and selected_model_type:
                params[name] = selected_model_type
                continue

            default_value = input_info.get("default")
            if default_value is not None:
                params[name] = default_value
            else:
                params[name] = None

        # Carry planner-specific parameters even when tool is not in catalog.
        for key, value in planner_parameters.items():
            if key not in params:
                params[key] = value

        # Backstop for training tools when planner output is sparse or tool name is non-catalog.
        lowered_name = tool_name.lower()
        if "train" in lowered_name and "model_type" not in params:
            if selected_model_type:
                params["model_type"] = selected_model_type
            elif task_type == "classification":
                params["model_type"] = "random_forest"
            elif task_type == "regression":
                params["model_type"] = "random_forest_regressor"

        if "train" in lowered_name and "test_size" not in params:
            params["test_size"] = 0.2

        if "train" in lowered_name and "random_state" not in params:
            params["random_state"] = 42

        if "train" in lowered_name and target_column and "target_column" not in params:
            params["target_column"] = target_column

        if (
            file_path
            and "filepath" not in params
            and any(
                token in lowered_name
                for token in [
                    "load",
                    "read",
                    "train",
                    "evaluate",
                    "detect",
                    "scale",
                    "encode",
                ]
            )
        ):
            params["filepath"] = file_path

        return params

    def _infer_dataset_specific_param(
        self,
        tool_name: str,
        param_name: str,
        dataset_analysis: Dict[str, Any],
        target_column: Optional[str],
        task_type: Optional[str],
        selected_model_type: Optional[str],
    ) -> Any:
        """Infer context-aware tool parameter values from interaction dataset analysis."""
        columns = dataset_analysis.get("column_names") or []
        column_types = dataset_analysis.get("column_types") or {}
        rows = dataset_analysis.get("rows")
        target = target_column or dataset_analysis.get("target_column")

        numeric_markers = ("int", "float", "double", "number")
        categorical_markers = ("object", "category", "string", "bool")

        numeric_columns = [
            col
            for col in columns
            if any(
                marker in str(column_types.get(col, "")).lower()
                for marker in numeric_markers
            )
            and col != target
        ]
        categorical_columns = [
            col
            for col in columns
            if any(
                marker in str(column_types.get(col, "")).lower()
                for marker in categorical_markers
            )
            and col != target
        ]

        lowered_tool = tool_name.lower()

        if param_name == "target_column" and target:
            return target

        if param_name == "model_type":
            if selected_model_type:
                return selected_model_type
            if task_type == "regression":
                return "random_forest_regressor"
            if task_type == "classification":
                return "random_forest"

        if param_name == "columns":
            if "encode" in lowered_tool and categorical_columns:
                return categorical_columns
            if (
                any(token in lowered_tool for token in ["scale", "noise", "outlier"])
                and numeric_columns
            ):
                return numeric_columns
            if numeric_columns:
                return numeric_columns
            if categorical_columns:
                return categorical_columns

        if param_name == "n_components" and numeric_columns:
            return max(1, min(5, len(numeric_columns)))

        if param_name == "k":
            feature_count = len([c for c in columns if c != target])
            if feature_count > 0:
                return min(10, feature_count)

        if param_name == "method":
            if "feature_selection" in lowered_tool:
                return (
                    "f_classif" if task_type != "regression" else "mutual_info_classif"
                )
            if "encode" in lowered_tool:
                return "onehot"
            if "scale" in lowered_tool:
                return "standard"

        if param_name == "test_size" and isinstance(rows, int) and rows > 0:
            if rows < 500:
                return 0.2
            if rows < 5000:
                return 0.25
            return 0.3

        if param_name == "noise_level" and numeric_columns:
            return 0.01

        return None

    def _catalog_parameters_for_tool(
        self,
        tool_name: str,
        tool_catalog: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Return parameter schema metadata for one tool from mcp-catalog."""
        tool_info = tool_catalog.get(tool_name) or {}
        catalog_parameters: List[Dict[str, Any]] = []
        for input_info in tool_info.get("inputs", []):
            name = input_info.get("name")
            if not name:
                continue

            type_spec = str(input_info.get("type_spec") or "")
            is_optional = "optional" in type_spec.lower()
            has_default = input_info.get("default") is not None

            catalog_parameters.append(
                {
                    "name": name,
                    "type": type_spec,
                    "default": input_info.get("default"),
                    "required": not is_optional and not has_default,
                }
            )

        return catalog_parameters

    def _select_model_type_for_phase(self, phase: Dict[str, Any]) -> Optional[str]:
        """Infer selected model type from planner text to make training steps reproducible."""
        search_text = " ".join(
            [
                str(phase.get("agent_name") or ""),
                str(phase.get("rationale") or ""),
                " ".join(
                    str(t.get("description") or "") for t in phase.get("tools", [])
                ),
                " ".join(str(t.get("tool_name") or "") for t in phase.get("tools", [])),
            ]
        ).lower()

        model_keywords = [
            "random_forest",
            "logistic_regression",
            "logistic",
            "svm",
            "xgboost",
            "gradient_boosting",
            "decision_tree",
            "knn",
            "naive_bayes",
            "linear_regression",
        ]

        for model_name in model_keywords:
            if model_name in search_text:
                return model_name

        if "model_trainer" in search_text or "train" in search_text:
            return "random_forest"

        return None

    def _infer_task_type(
        self, objective_text: str, file_path: Optional[str]
    ) -> Optional[str]:
        """Infer classification/regression hint from objective/path."""
        haystack = f"{objective_text} {file_path or ''}".lower()
        if "classification" in haystack:
            return "classification"
        if "regression" in haystack:
            return "regression"
        return None

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
                # Try to find agent by ID first, then by name
                agent = self.agent_registry.get_agent(agent_type)
                if not agent:
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
