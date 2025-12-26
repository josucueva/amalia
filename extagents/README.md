# External Agents Container

Simulates external agent providers (Google Cloud, AWS, Anthropic) for AMALIA workflows.

## 🎯 Purpose

This container provides **two execution modes** for external agents:

### 1. **Simulation Mode** (Default - FAST ⚡)

- **Speed**: Instant responses (~10ms)
- **Cost**: Free - no API calls
- **Use case**: Testing, development, demos
- Returns hardcoded/formatted responses

### 2. **Real LLM Mode** (Optional - SLOW 🐌)

- **Speed**: 2-10 seconds (same as internal agents)
- **Cost**: Uses actual LLM API calls
- **Use case**: Production, real AI processing
- Calls Google Gemini / Claude / GPT models

---

## 🚀 Quick Start

### Default Mode (Simulation - Fast)

```bash
# Already configured - just run
docker compose up extagents
```

### Enable Real LLM Mode (Slow but Real AI)

```bash
# Edit docker-compose.yml
# Change: USE_REAL_LLMS=false
# To:     USE_REAL_LLMS=true

# Add API keys to .env file
echo "GOOGLE_API_KEY=your_key_here" >> .env

# Rebuild and restart
docker compose up --build extagents
```

---

## 📊 Performance Comparison

| Mode           | Response Time | API Calls | Cost | Use Case                  |
| -------------- | ------------- | --------- | ---- | ------------------------- |
| **Simulation** | ~10ms         | None      | Free | Testing, demos            |
| **Real LLM**   | 2-10s         | Yes       | $$   | Production, real analysis |

---

## 🔧 Available Agents

### 1. Google Data Validator

- **ID**: `google_data_validator`
- **Provider**: `google`
- **Endpoint**: `/agents/google_data_validator/execute`
- **Simulation**: Returns validation checklist
- **Real LLM**: Uses Gemini for actual validation

### 2. AWS Feature Engineer

- **ID**: `aws_feature_engineer`
- **Provider**: `aws`
- **Endpoint**: `/agents/aws_feature_engineer/execute`
- **Simulation**: Returns feature engineering steps
- **Real LLM**: Uses Gemini for real feature suggestions

### 3. Anthropic Summarizer

- **ID**: `anthropic_summarizer`
- **Provider**: `anthropic`
- **Endpoint**: `/agents/anthropic_summarizer/execute`
- **Simulation**: Returns first 5 lines
- **Real LLM**: Uses Gemini/Claude for real summarization

---

## 🧪 Testing

### Test Simulation Mode (Fast)

```bash
curl -X POST http://localhost:9000/agents/google_data_validator/execute \
  -H "Content-Type: application/json" \
  -d '{
    "instanceId": "test_123",
    "agentType": "google_data_validator",
    "input": "Sample data to validate"
  }'

# Response in ~10ms
# Output includes: "[SIMULATED - No actual LLM call made]"
```

### Test Real LLM Mode (Slow)

```bash
# First enable USE_REAL_LLMS=true in docker-compose.yml

curl -X POST http://localhost:9000/agents/google_data_validator/execute \
  -H "Content-Type: application/json" \
  -d '{
    "instanceId": "test_456",
    "agentType": "google_data_validator",
    "input": "Validate this CSV: Name,Age\nJohn,25\nJane,30"
  }'

# Response in ~3-5 seconds
# Output: Real AI analysis from Gemini
```

---

## 📝 Adding New External Agents

### 1. Add Simulation Function

```python
def simulate_my_agent(req: ExecuteRequest) -> str:
    return "Quick simulated response"
```

### 2. Add Real LLM Function (Optional)

```python
async def my_agent_with_llm(req: ExecuteRequest) -> str:
    messages = [
        {"role": "system", "content": "You are an expert..."},
        {"role": "user", "content": req.input}
    ]
    response = await acompletion(
        model="gemini/gemini-2.0-flash-exp",
        messages=messages,
        temperature=0.5,
        max_tokens=2000
    )
    return response.choices[0].message.content
```

### 3. Register Both

```python
AGENT_SIMULATORS = {
    "my_agent": ("custom", simulate_my_agent),
}

AGENT_LLM_FUNCTIONS = {
    "my_agent": my_agent_with_llm,
}
```

### 4. Create YAML Config

```yaml
# config/agents/my_agent.yaml
agent:
  name: my_agent
  provider: custom
  remote_endpoint: http://extagents:9000/agents/my_agent/execute
  # ... rest of config
```

---

## 🔍 Monitoring

### Watch Logs

```bash
docker compose logs -f extagents
```

### Check Mode

```bash
docker compose logs extagents | grep "Real LLM mode"
# If enabled: "Real LLM mode enabled for external agents"
# If disabled: No such message
```

### Count Executions

```bash
docker compose logs extagents | grep "External agent executed" | wc -l
```

### See Which Mode Was Used

```bash
docker compose logs extagents | grep "mode="
# Output shows: mode=simulation or mode=real_llm
```

---

## 💡 Why Two Modes?

**Development/Testing** → Use **Simulation Mode**

- Instant responses for rapid iteration
- No API costs
- Predictable outputs for testing

**Production/Real Use** → Use **Real LLM Mode**

- Actual AI analysis
- Dynamic, context-aware responses
- Better quality, but slower and costs money

---

## 🎛️ Configuration

### Environment Variables

| Variable            | Default | Description               |
| ------------------- | ------- | ------------------------- |
| `USE_REAL_LLMS`     | `false` | Enable real LLM API calls |
| `GOOGLE_API_KEY`    | -       | Google Gemini API key     |
| `OPENAI_API_KEY`    | -       | OpenAI GPT API key        |
| `ANTHROPIC_API_KEY` | -       | Anthropic Claude API key  |

---

## 📚 API Reference

### POST `/agents/{agent_id}/execute`

**Request:**

```json
{
  "instanceId": "instance_123",
  "agentType": "google_data_validator",
  "input": "Data or prompt to process",
  "filePath": "/app/data/uploads/file.csv",
  "inputs": [],
  "config": {}
}
```

**Response:**

```json
{
  "instanceId": "instance_123",
  "agentType": "google_data_validator",
  "timestamp": "2025-12-26T16:00:00Z",
  "output": "Processed result...",
  "provider": "google",
  "metadata": {
    "received_inputs": 0
  }
}
```

### GET `/health`

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2025-12-26T16:00:00Z"
}
```

---

## 🚨 Troubleshooting

**Issue: External agents respond instantly**

- ✅ Normal! Default mode is **simulation** (fast)
- To get real AI: Set `USE_REAL_LLMS=true`

**Issue: "litellm not installed" warning**

- Run: `docker compose build extagents`
- LiteLLM is now in requirements.txt

**Issue: LLM mode enabled but still fast**

- Check logs: `docker compose logs extagents | grep "mode="`
- Verify API key is set: `docker compose config | grep GOOGLE_API_KEY`

**Issue: Real LLM mode gives errors**

- Check API key is valid
- Check model name in code (e.g., `gemini/gemini-2.0-flash-exp`)
- View detailed logs: `docker compose logs extagents`

---

## 🎓 Summary

✅ **Current setup** = Fast simulations (instant responses)  
🔧 **To enable real AI** = Set `USE_REAL_LLMS=true` + add API keys  
📊 **Trade-off** = Speed vs. Real Intelligence

Perfect for development now, production-ready when you need it! 🚀
