from datetime import datetime, timezone

import pytest

from app.agents.registry import AgentRegistry
from app.models.agent import Agent, AgentConfig
from app.services.agent_pipeline import AgentPipelineService


class FakeMCPServer:
    def __init__(self, server_id: str, name: str):
        self.id = server_id
        self.name = name
        self.command = "python"
        self.args = ["server.py"]
        self.env = {}
        self.is_available = True
        self.description = "test server"


class FakeMCPServerService:
    def __init__(self, servers):
        self._servers = servers

    async def list_servers(self):
        return self._servers


def _build_registry_with_agent() -> AgentRegistry:
    registry = AgentRegistry()
    agent = Agent(
        id="data_loader",
        config=AgentConfig(
            name="Data Loader Agent",
            description="Loads tabular datasets",
            model="gpt-4o-mini",
            system_prompt="You load datasets",
            mcp_server_ids=[],
            mcp_servers={},
            tools=[],
        ),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    registry.register_agent(agent)
    return registry


@pytest.mark.asyncio
async def test_simplified_export_marks_invalid_when_required_params_unresolved():
    registry = _build_registry_with_agent()
    mcp_service = FakeMCPServerService(
        [FakeMCPServer("python-data-loading", "Data Loading Server")]
    )
    pipeline = AgentPipelineService(
        llm_service=None,
        agent_registry=registry,
        mcp_server_service=mcp_service,
    )

    pipeline._load_tool_catalog_index = lambda: {
        "train_model": {
            "server_name": "Model Training Server",
            "inputs": [
                {"name": "target_column", "type_spec": "str", "default": None},
                {"name": "test_size", "type_spec": "float", "default": "0.2"},
            ],
        }
    }

    orchestration = await pipeline._build_simplified_orchestration_export(
        plan_data={
            "plan": {
                "objective": "Build a classification pipeline",
                "phases": [
                    {
                        "phase_number": 1,
                        "agent_name": "data loader agent",
                        "mcp_server": "Data-Loading Server",
                        "tools": [{"tool_name": "train_model", "parameters": {}}],
                    }
                ],
            }
        },
        file_path=None,
        target_column_hint=None,
        dataset_analysis={"rows": 100, "column_names": ["f1", "target"]},
    )

    assert orchestration["steps"][0]["agent"]["id"] == "data_loader"
    assert (
        orchestration["steps"][0]["resolved_mcp_server"]["id"] == "python-data-loading"
    )
    assert orchestration["validation"]["status"] == "warning"

    issue_codes = [issue["code"] for issue in orchestration["validation"]["issues"]]
    assert "tool_required_parameters_unresolved" in issue_codes


@pytest.mark.asyncio
async def test_simplified_export_is_valid_with_required_params_present():
    registry = _build_registry_with_agent()
    mcp_service = FakeMCPServerService(
        [FakeMCPServer("python-data-loading", "Data Loading Server")]
    )
    pipeline = AgentPipelineService(
        llm_service=None,
        agent_registry=registry,
        mcp_server_service=mcp_service,
    )

    pipeline._load_tool_catalog_index = lambda: {
        "train_model": {
            "server_name": "Model Training Server",
            "inputs": [
                {"name": "target_column", "type_spec": "str", "default": None},
                {"name": "test_size", "type_spec": "float", "default": "0.2"},
            ],
        }
    }

    orchestration = await pipeline._build_simplified_orchestration_export(
        plan_data={
            "plan": {
                "objective": "Build a classification pipeline",
                "phases": [
                    {
                        "phase_number": 1,
                        "agent_id": "data_loader",
                        "mcp_server": "python-data-loading",
                        "tools": [
                            {
                                "tool_name": "train_model",
                                "parameters": {"target_column": "target"},
                            }
                        ],
                    }
                ],
            }
        },
        file_path=None,
        target_column_hint="target",
        dataset_analysis={"rows": 100, "column_names": ["f1", "target"]},
    )

    assert orchestration["validation"]["status"] == "valid"
    assert orchestration["validation"]["issue_count"] == 0
    assert orchestration["steps"][0]["tools"][0]["missing_required_parameters"] == []
