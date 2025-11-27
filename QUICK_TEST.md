# Quick Start: Three-Agent Pipeline System

## Testing the Implementation

### 1. Start the Backend

```bash
cd backend
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Verify Agents Loaded

Check logs for:

```
INFO     Agents loaded    count=8
```

Or check the API:

```bash
curl http://localhost:8000/api/agents?include_hidden=true | jq
```

You should see 8 agents:

- ✅ interaction_agent
- ✅ data_loader
- ✅ data_preprocessor
- ✅ model_trainer
- ✅ model_evaluator
- ✅ data_visualizer
- ✅ planner_agent (hidden)
- ✅ orchestrator_agent (hidden)

### 3. Start the Frontend

```bash
cd frontend
npm run dev
```

### 4. Test the System

Open http://localhost:5173 and try these prompts:

#### Simple Conversation (No Pipeline)

```
"What can you help me with?"
```

**Expected**: Normal response from interaction agent only.

#### Pipeline Creation

```
"I want to load a CSV file, clean the data, train a model, and evaluate it"
```

**Expected**:

1. Interaction agent refines the prompt
2. Planner creates a 4-phase plan
3. Orchestrator builds canvas with 4 nodes
4. Message: "✅ Pipeline created! Switch to Canvas Mode!"

#### Another Example

```
"Analyze customer churn data with preprocessing and prediction"
```

**Expected**: Similar flow, canvas pipeline created.

### 5. View in Canvas Mode

1. Click "Canvas Mode" button
2. You should see visual pipeline with connected agents
3. Nodes positioned left-to-right
4. Connections showing data flow

---

## Monitoring

### Backend Logs

```bash
tail -f logs/app.log | grep -E "Step [1-6]|Interaction|Planner|Orchestrator"
```

**Expected output for pipeline creation:**

```
INFO Step 1: Processing with interaction agent
INFO Step 2: Interaction agent created improved prompt
INFO Step 3: Processing with planner agent
INFO Step 4: Planner created plan phases=4 complexity=medium
INFO Step 5: Processing with orchestrator agent
INFO Step 6: Orchestrator created configuration nodes=4 connections=3
```

### API Endpoint Testing

**Test chat endpoint:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Build a pipeline for data analysis",
    "stream": false
  }' | jq
```

**Test agents endpoint:**

```bash
# Visible agents only (default)
curl http://localhost:8000/api/agents | jq '.total'
# Should return: 6

# All agents including hidden
curl http://localhost:8000/api/agents?include_hidden=true | jq '.total'
# Should return: 8
```

---

## Troubleshooting

### Issue: "Interaction agent not found"

**Fix:**

```bash
# Check if agent loaded
curl http://localhost:8000/api/agents | jq '.agents[] | select(.config.name == "interaction_agent")'

# If missing, check YAML file exists
ls -la config/agents/interaction_agent.yaml

# Restart backend to reload
```

### Issue: "Planner agent not found"

**Fix:**

```bash
# Check with include_hidden
curl http://localhost:8000/api/agents?include_hidden=true | jq '.agents[] | select(.config.name == "planner_agent")'

# Check YAML exists
ls -la config/agents/planner_agent.yaml

# Verify is_hidden metadata
cat config/agents/planner_agent.yaml | grep "is_hidden"
```

### Issue: No pipeline created

**Debug steps:**

1. Check frontend console for errors
2. Check backend logs: `tail -f logs/app.log`
3. Verify API keys in `.env`: `GOOGLE_API_KEY` or `OPENAI_API_KEY`
4. Test LLM connection: `curl http://localhost:8000/api/health`

### Issue: Canvas not updating

**Fix:**

1. Switch to Canvas Mode manually
2. Check browser console for errors
3. Check `sessionStorage.pendingPipeline`:
   ```javascript
   console.log(sessionStorage.getItem("pendingPipeline"));
   ```
4. Hard refresh: Ctrl+Shift+R

---

## Example Prompts That Work Well

### Good Prompts (Clear Intent)

✅ "Load sales data, clean it, and train a prediction model"  
✅ "Analyze customer churn with preprocessing and evaluation"  
✅ "Build a pipeline for data visualization and insights"  
✅ "Create a workflow for model training and testing"

### Prompts That Need Clarification

⚠️ "Help me with data" (too vague)  
⚠️ "Do ML stuff" (unclear objective)  
⚠️ "Analyze" (needs more context)

---

## Configuration Tweaks

### Make Planner More Creative

Edit `config/agents/planner_agent.yaml`:

```yaml
temperature: 0.7 # Up from 0.4
```

### Make Orchestrator More Precise

Edit `config/agents/orchestrator_agent.yaml`:

```yaml
temperature: 0.1 # Down from 0.3
```

### Change Default Model

Edit `backend/.env`:

```env
DEFAULT_MODEL=openai/gpt-4o  # Instead of gemini
```

---

## Debugging Commands

### Check Agent Registry State

```bash
# In Python shell
python3 << EOF
from app.agents.registry import AgentRegistry
from app.agents.config_loader import load_agents_from_directory

registry = AgentRegistry()
agents = load_agents_from_directory("./config/agents")
for agent in agents:
    print(f"{agent.config.name}: hidden={agent.is_hidden()}")
EOF
```

### Manually Test Pipeline Service

```bash
# In Python shell with backend running
python3 << EOF
import asyncio
from app.services.agent_pipeline import AgentPipelineService
from app.services.llm_service import get_llm_service
from app.agents.registry import AgentRegistry
from app.config import get_settings

settings = get_settings()
llm_service = get_llm_service(settings)
registry = AgentRegistry()

# Load agents
from app.agents.config_loader import load_agents_from_directory
agents = load_agents_from_directory("./config/agents")
for agent in agents:
    registry.register_agent(agent)

pipeline = AgentPipelineService(llm_service, registry)

# Test
async def test():
    result, data = await pipeline.process_with_pipeline(
        "Build a data analysis pipeline",
        []
    )
    print(f"Result: {result}")
    print(f"Data: {data}")

asyncio.run(test())
EOF
```

---

## Success Indicators

✅ Backend starts without errors  
✅ 8 agents loaded (6 visible + 2 hidden)  
✅ Chat messages processed  
✅ Pipelines created from descriptions  
✅ Canvas displays visual workflows  
✅ Hidden agents not in UI  
✅ Logs show 3-agent flow

---

## Next Steps

1. **Test with real data**: Upload a CSV and test the full flow
2. **Customize agents**: Edit YAML prompts for your use case
3. **Monitor performance**: Check LLM costs and latency
4. **Add more agents**: Create specialized agents for your domain
5. **Enable A2A**: Set `a2a_enabled: true` and configure Redis

---

**For full details, see:**

- `IMPLEMENTATION_SUMMARY.md` - Complete technical details
- `THREE_AGENT_SYSTEM.md` - User-facing documentation
- `ARCHITECTURE.md` - System architecture updates
