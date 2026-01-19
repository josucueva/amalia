# Three-Agent Pipeline System

## Overview

AMALIA now features an intelligent three-agent pipeline system that automatically creates ML workflows from natural language descriptions.

## Architecture

### The Three Agents

1. **Interaction Agent** (Visible)

   - User-facing conversational interface
   - Refines user requirements
   - Asks clarifying questions
   - Triggers pipeline creation

2. **Planner Agent** (Hidden)

   - Receives refined prompts
   - Creates execution plans with phases
   - Identifies required agents
   - Estimates complexity

3. **Orchestrator Agent** (Hidden)
   - Receives execution plans
   - Instantiates agents on canvas
   - Creates connections
   - Positions nodes spatially

## How It Works

### Example Workflow

```
User: "I want to analyze customer data and build a prediction model"

↓ Interaction Agent refines to:
  "Load customer.csv, clean data by handling missing values,
   train classification model, evaluate performance"

↓ Planner Agent creates plan:
  Phase 1: data_loader → Load CSV file
  Phase 2: data_preprocessor → Clean and prepare data
  Phase 3: model_trainer → Train classifier
  Phase 4: model_evaluator → Evaluate metrics

↓ Orchestrator Agent creates canvas:
  4 nodes positioned and connected
  Data flows: Loader → Preprocessor → Trainer → Evaluator

↓ User sees:
  "✅ Pipeline created! 4 phases, 4 agents. Switch to Canvas Mode!"
```

## Usage

### Triggering Pipeline Creation

Simply describe what you want to accomplish in the chat:

- ❌ Bad: "help me"
- ✅ Good: "Load sales.csv, clean it, and train a model"

- ❌ Bad: "do stuff"
- ✅ Good: "Analyze customer churn with visualization and prediction"

### What Happens Behind the Scenes

1. **Interaction Agent** processes your message
2. If clear enough → Creates improved prompt
3. **Planner Agent** breaks it into phases
4. **Orchestrator Agent** builds the visual pipeline
5. You see results in Canvas Mode!

## Configuration Files

### Interaction Agent

- File: `config/agents/interaction_agent.yaml`
- Role: User-facing, visible in UI
- Model: `gemini/gemini-2.5-flash`
- Temperature: 0.7 (balanced creativity)

### Planner Agent

- File: `config/agents/planner_agent.yaml`
- Role: Hidden, strategic planning
- Model: `gemini/gemini-2.5-flash`
- Temperature: 0.4 (more focused)
- Metadata: `is_hidden: true`

### Orchestrator Agent

- File: `config/agents/orchestrator_agent.yaml`
- Role: Hidden, pipeline instantiation
- Model: `gemini/gemini-2.5-flash`
- Temperature: 0.3 (very precise)
- Metadata: `is_hidden: true`

## Communication

By default, agents communicate **directly** without A2A protocol:

```yaml
a2a_enabled: false # Direct function calls (fast)
```

This can be changed to `true` for Redis-based message queue in the future.

## Benefits

✅ **User-Friendly**: Natural language input
✅ **Intelligent**: Automatic phase decomposition  
✅ **Transparent**: Hidden agents work seamlessly
✅ **Flexible**: Easy to modify each agent's behavior
✅ **Visual**: See your pipeline on the canvas

## API Flow

```
POST /api/chat
  ↓
AgentPipelineService.process_with_pipeline()
  ↓
[Interaction Agent] → Refine prompt
  ↓
[Planner Agent] → Create plan
  ↓
[Orchestrator Agent] → Build canvas
  ↓
Response with orchestration data
  ↓
Frontend displays in Canvas Mode
```

## Debugging

### Check Agent Status

```bash
curl http://localhost:8000/api/agents?include_hidden=true
```

### View Logs

```bash
tail -f logs/app.log | grep -E "Interaction|Planner|Orchestrator"
```

### Test Individual Agents

The agents are loaded on startup from YAML files. If any are missing, you'll see errors in the logs.

## Customization

### Modify Agent Behavior

Edit the YAML files in `config/agents/`:

- Change `system_prompt` to alter behavior
- Adjust `temperature` for creativity vs precision
- Update `communication` rules for agent interaction

### Add New Agent Types

1. Create YAML config in `config/agents/`
2. Add to planner's available agent types
3. Update orchestrator to handle the new type
4. Restart backend to load new agent

## Troubleshooting

### Pipeline Not Created

- Check if all 3 agents are loaded: `GET /api/agents?include_hidden=true`
- View logs for LLM errors
- Ensure API keys are set in `.env`

### Invalid JSON from Agents

- Agents must return properly formatted JSON
- Check `system_prompt` instructions
- Lower temperature for more consistent output

### Canvas Not Updating

- Switch to Canvas Mode manually
- Check browser console for errors
- Verify `sessionStorage.pendingPipeline` exists

## Future Enhancements

- [ ] Add more sophisticated planning algorithms
- [ ] Support for parallel agent execution
- [ ] Real-time agent communication (A2A with Redis)
- [ ] User feedback loop for plan refinement
- [ ] Pipeline templates and presets

---

**Implementation Date**: November 26, 2025
**Status**: ✅ Fully Implemented
**Version**: 1.0
