"""
Agent Executor for Autonomous A2A Communication.

Executes agents when they receive A2A messages in autonomous mode.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import structlog

from app.models.message import A2AMessage

logger = structlog.get_logger()


class AgentExecutor:
    """
    Executes agents in response to A2A messages.
    
    In autonomous mode, agents subscribe to their inbox channel and
    automatically execute when they receive messages.
    """
    
    def __init__(self, llm_service, agent_registry, a2a_service):
        """
        Initialize agent executor.
        
        Args:
            llm_service: LLM service for agent execution
            agent_registry: Agent registry for lookups
            a2a_service: A2A service for sending replies
        """
        self.llm_service = llm_service
        self.agent_registry = agent_registry
        self.a2a_service = a2a_service
        
        # Track active executions to prevent duplicates
        self._active_executions = set()
        
    async def execute_from_message(
        self,
        agent_id: str,
        message: A2AMessage
    ) -> Optional[str]:
        """
        Execute an agent based on an incoming A2A message.
        
        Args:
            agent_id: ID of the agent to execute
            message: Incoming A2A message
            
        Returns:
            Agent output or None if execution failed
        """
        # Prevent duplicate executions
        execution_key = f"{agent_id}:{message.correlation_id}"
        if execution_key in self._active_executions:
            logger.warning(
                "Duplicate execution prevented",
                agent_id=agent_id,
                correlation_id=message.correlation_id
            )
            return None
            
        self._active_executions.add(execution_key)
        
        try:
            agent = self.agent_registry.get_agent(agent_id)
            if not agent:
                logger.error("Agent not found for execution", agent_id=agent_id)
                return None
            
            # Extract input from message content
            message_input = self._extract_input_from_message(message)
            
            logger.info(
                "🤖 Autonomous agent execution triggered",
                agent_id=agent_id,
                from_agent=message.from_agent,
                correlation_id=message.correlation_id,
                message_type=message.message_type
            )
            
            # Build messages for LLM
            messages = [
                {"role": "system", "content": agent.config.system_prompt},
                {"role": "user", "content": message_input}
            ]
            
            # Execute agent using LLM service
            result = await self.llm_service.generate_response(
                messages=messages,
                model=agent.config.model,
                temperature=agent.config.temperature,
                max_tokens=agent.config.max_tokens,
                tools=None  # TODO: Add MCP tools support
            )
            
            output = result if isinstance(result, str) else str(result)
            
            logger.info(
                "✅ Autonomous execution completed",
                agent_id=agent_id,
                correlation_id=message.correlation_id,
                output_length=len(output)
            )
            
            # If this was a request, send a reply
            if message.message_type == "request":
                await self._send_reply(agent_id, message, output)
            
            return output
            
        except Exception as e:
            logger.error(
                "Autonomous execution failed",
                agent_id=agent_id,
                correlation_id=message.correlation_id,
                error=str(e)
            )
            return None
            
        finally:
            self._active_executions.discard(execution_key)
    
    def _extract_input_from_message(self, message: A2AMessage) -> str:
        """
        Extract input text from message content.
        
        Args:
            message: A2A message
            
        Returns:
            Formatted input string
        """
        content = message.content
        
        # If content has an 'output' field, use it
        if isinstance(content, dict):
            if "output" in content:
                input_text = content["output"]
            elif "input" in content:
                input_text = content["input"]
            else:
                # Convert dict to string
                input_text = str(content)
        else:
            input_text = str(content)
        
        # Add context about the sender
        context = f"[Message from {message.from_agent}]\n\n{input_text}"
        
        return context
    
    async def _send_reply(
        self,
        agent_id: str,
        original_message: A2AMessage,
        output: str
    ) -> None:
        """
        Send a reply to the original sender.
        
        Args:
            agent_id: ID of the agent sending the reply
            original_message: Original message to reply to
            output: Agent output to send as reply
        """
        try:
            await self.a2a_service.send_message(
                from_agent=agent_id,
                to_agent=original_message.from_agent,
                content={"reply": output},
                message_type="reply",
                correlation_id=original_message.correlation_id,
                validate=False  # Skip permission check for replies
            )
            
            logger.info(
                "📨 Reply sent",
                from_agent=agent_id,
                to_agent=original_message.from_agent,
                correlation_id=original_message.correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Failed to send reply",
                agent_id=agent_id,
                error=str(e)
            )
