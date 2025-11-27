"""
Agent pipeline service for handling multi-agent workflows.
Implements the hidden agent flow: Interaction → Planner → Orchestrator
"""
import json
import re
import structlog
from typing import Dict, Any, Optional, Tuple

from app.services.llm_service import LLMService
from app.agents.registry import AgentRegistry

logger = structlog.get_logger()


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
        self,
        user_message: str,
        conversation_history: list
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
        interaction_response = await self.llm_service.generate_agent_response(
            user_message=user_message,
            agent_config=interaction_agent.config.dict(),
            conversation_history=conversation_history
        )
        
        # Check if interaction agent wants to plan a pipeline
        action_data = self._extract_json_from_response(interaction_response)
        
        if not action_data or action_data.get("action") != "plan_pipeline":
            # No pipeline planning needed, return interaction agent's response
            logger.info("No pipeline planning requested")
            return interaction_response, None
        
        improved_prompt = action_data.get("improved_prompt", user_message)
        logger.info("Step 2: Interaction agent created improved prompt", 
                   prompt_length=len(improved_prompt))
        
        # Step 2: Planner Agent - Create execution plan
        planner_agent = self.agent_registry.get_agent_by_name("planner_agent")
        if not planner_agent:
            logger.error("Planner agent not found")
            return "Pipeline planning is not available.", None
        
        logger.info("Step 3: Processing with planner agent")
        planner_response = await self.llm_service.generate_agent_response(
            user_message=improved_prompt,
            agent_config=planner_agent.config.dict(),
            conversation_history=[]  # Fresh context for planner
        )
        
        plan_data = self._extract_json_from_response(planner_response)
        
        if not plan_data or "plan" not in plan_data:
            logger.error("Planner failed to create valid plan")
            return "Failed to create execution plan.", None
        
        plan = plan_data["plan"]
        logger.info("Step 4: Planner created plan", 
                   phases=len(plan.get("phases", [])),
                   complexity=plan.get("complexity"))
        
        # Step 3: Orchestrator Agent - Create canvas configuration
        orchestrator_agent = self.agent_registry.get_agent_by_name("orchestrator_agent")
        if not orchestrator_agent:
            logger.error("Orchestrator agent not found")
            return "Pipeline orchestration is not available.", None
        
        # Convert plan to a message for orchestrator
        orchestrator_input = json.dumps(plan_data, indent=2)
        
        logger.info("Step 5: Processing with orchestrator agent")
        orchestrator_response = await self.llm_service.generate_agent_response(
            user_message=f"Create a canvas configuration for this plan:\n\n{orchestrator_input}",
            agent_config=orchestrator_agent.config.dict(),
            conversation_history=[]  # Fresh context for orchestrator
        )
        
        orchestration_data = self._extract_json_from_response(orchestrator_response)
        
        if not orchestration_data or "orchestration" not in orchestration_data:
            logger.error("Orchestrator failed to create valid configuration")
            return "Failed to create pipeline configuration.", None
        
        orchestration = orchestration_data["orchestration"]
        
        # Map agent types to agent IDs
        orchestration = self._resolve_agent_types(orchestration)
        
        logger.info("Step 6: Orchestrator created configuration",
                   nodes=len(orchestration.get("nodes", [])),
                   connections=len(orchestration.get("connections", [])))
        
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
                    logger.warning(f"Agent type '{agent_type}' not found, keeping type name")
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
            agent for agent in agents 
            if agent.config.name not in ["interaction_agent", "planner_agent", "orchestrator_agent"]
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
                    "position": {"x": 200, "y": 200}
                },
                {
                    "instanceId": instance2_id,
                    "agentId": selected_agents[1].id,
                    "position": {"x": 500, "y": 200}
                }
            ],
            "connections": [
                {
                    "id": f"conn_{timestamp}",
                    "fromInstanceId": instance1_id,
                    "toInstanceId": instance2_id
                }
            ],
            "message": f"Simple pipeline with {selected_agents[0].config.name} → {selected_agents[1].config.name}"
        }
        
        return {"orchestration": orchestration}
