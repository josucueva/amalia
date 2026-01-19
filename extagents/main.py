from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import structlog
import os

logger = structlog.get_logger()
app = FastAPI(title="External Agents Provider", version="0.1.0")

# Optional: Enable real LLM calls for external agents
USE_REAL_LLMS = os.getenv("USE_REAL_LLMS", "false").lower() == "true"

if USE_REAL_LLMS:
    try:
        from litellm import acompletion
        logger.info("Real LLM mode enabled for external agents")
    except ImportError:
        logger.warning("litellm not installed, falling back to simulation mode")
        USE_REAL_LLMS = False


class ExecuteRequest(BaseModel):
    instanceId: str
    agentType: str
    input: str
    filePath: Optional[str] = None
    inputs: Optional[List[Dict[str, Any]]] = None
    config: Optional[Dict[str, Any]] = None


class ExecuteResponse(BaseModel):
    instanceId: str
    agentType: str
    timestamp: str
    output: str
    provider: str
    metadata: Optional[Dict[str, Any]] = None


def simulate_google_validator(req: ExecuteRequest) -> str:
    """Simulated Google Cloud data validation (instant response)."""
    # Simple simulation: echo with validation note
    details = []
    if req.filePath:
        details.append(f"FILE: {req.filePath}")
    details.append("VALIDATION: Checked headers, row counts, and data types.")
    details.append("RESULT: No critical issues found.")
    details.append("\n[SIMULATED - No actual LLM call made]")
    return "\n\n".join(details + ["\n" + req.input[:1000]])


async def google_validator_with_llm(req: ExecuteRequest) -> str:
    """Real LLM-powered validation using Google Gemini (slower, real AI)."""
    messages = [
        {
            "role": "system",
            "content": "You are a data validation expert from Google Cloud. Validate data quality, schemas, and types.",
        },
        {"role": "user", "content": req.input},
    ]
    response = await acompletion(
        model="gemini/gemini-2.5-flash-lite",
        messages=messages,
        temperature=0.2,
        max_tokens=1000,
    )
    return response.choices[0].message.content


def simulate_aws_feature_engineer(req: ExecuteRequest) -> str:
    """Simulated AWS feature engineering (instant response)."""
    steps = [
        "FEATURE ENGINEERING:",
        "- Encoded categoricals",
        "- Standardized numeric features",
        "- Removed duplicates",
        "- Filled missing values (median/mode)",
        "\n[SIMULATED - No actual LLM call made]",
    ]
    return "\n".join(steps) + "\n\nCONTEXT:\n" + req.input[:1000]


async def aws_feature_engineer_with_llm(req: ExecuteRequest) -> str:
    """Real LLM-powered feature engineering (slower, real AI)."""
    messages = [
        {
            "role": "system",
            "content": "You are an AWS ML feature engineering expert. Transform and create features for machine learning.",
        },
        {"role": "user", "content": req.input},
    ]
    response = await acompletion(
        model="gemini/gemini-2.5-flash-lite",
        messages=messages,
        temperature=0.3,
        max_tokens=1200,
    )
    return response.choices[0].message.content


def simulate_anthropic_summarizer(req: ExecuteRequest) -> str:
    """Simulated Anthropic summarization (instant response)."""
    # Very basic summarization stub
    summary = req.input.strip().split("\n")[:5]
    result = "SUMMARY:\n" + "\n".join(summary)
    result += "\n\n[SIMULATED - No actual LLM call made]"
    return result


async def anthropic_summarizer_with_llm(req: ExecuteRequest) -> str:
    """Real LLM-powered summarization using Claude (slower, real AI)."""
    messages = [
        {
            "role": "system",
            "content": "You are an Anthropic AI summarization expert. Create concise, accurate summaries.",
        },
        {"role": "user", "content": f"Summarize this:\n\n{req.input}"},
    ]
    response = await acompletion(
        model="gemini/gemini-2.5-flash-lite",  # Or use "anthropic/claude-3-5-sonnet" if you have API key
        messages=messages,
        temperature=0.2,
        max_tokens=800,
    )
    return response.choices[0].message.content


AGENT_SIMULATORS = {
    "google_data_validator": ("google", simulate_google_validator),
    "aws_feature_engineer": ("aws", simulate_aws_feature_engineer),
    "anthropic_summarizer": ("anthropic", simulate_anthropic_summarizer),
}

# Real LLM implementations (used when USE_REAL_LLMS=true)
AGENT_LLM_FUNCTIONS = {
    "google_data_validator": google_validator_with_llm,
    "aws_feature_engineer": aws_feature_engineer_with_llm,
    "anthropic_summarizer": anthropic_summarizer_with_llm,
}


@app.post("/agents/{agent_id}/execute", response_model=ExecuteResponse)
async def execute_agent(agent_id: str, req: ExecuteRequest):
    provider, simulator = AGENT_SIMULATORS.get(agent_id, ("custom", None))
    
    # Use real LLM if enabled and available
    if USE_REAL_LLMS and agent_id in AGENT_LLM_FUNCTIONS:
        try:
            logger.info(
                "Executing with REAL LLM",
                agent_id=agent_id,
                provider=provider,
                instance_id=req.instanceId,
            )
            output = await AGENT_LLM_FUNCTIONS[agent_id](req)
        except Exception as e:
            logger.error(
                "LLM execution failed, falling back to simulation",
                agent_id=agent_id,
                error=str(e),
            )
            output = simulator(req) if simulator else f"[Error: {str(e)}]"
    elif simulator is None:
        # Fallback: echo service
        output = f"[Echo from external agent '{agent_id}']\n\n" + req.input
    else:
        # Use simulation (fast)
        output = simulator(req)

    logger.info(
        "External agent executed",
        agent_id=agent_id,
        provider=provider,
        instance_id=req.instanceId,
        mode="real_llm" if (USE_REAL_LLMS and agent_id in AGENT_LLM_FUNCTIONS) else "simulation",
    )

    return ExecuteResponse(
        instanceId=req.instanceId,
        agentType=req.agentType,
        timestamp=datetime.now(timezone.utc).isoformat(),
        output=output,
        provider=provider,
        metadata={"received_inputs": len(req.inputs or [])},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
