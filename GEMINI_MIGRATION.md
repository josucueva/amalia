# Gemini 2.5 Pro Migration

## Overview

The platform has been configured to use **Google Gemini 2.0 Flash (Experimental)** as the default LLM model instead of OpenAI GPT-4o.

## Changes Made

### 1. Backend Configuration

**File**: `backend/app/config.py`

- Changed `default_model` from `"gpt-4o"` to `"gemini/gemini-2.0-flash-exp"`

### 2. Environment Variables

**File**: `.env.example`

- Updated `DEFAULT_MODEL` from `gpt-4o` to `gemini/gemini-2.0-flash-exp`

### 3. Agent Configurations

All three pre-configured agents updated to use Gemini:

**Files Modified**:

- `config/agents/data_preprocessor.yaml`
- `config/agents/model_trainer.yaml`
- `config/agents/model_evaluator.yaml`

**Change**: `model: "gpt-4o"` → `model: "gemini/gemini-2.0-flash-exp"`

### 4. Frontend UI

**File**: `frontend/index.html`

Updated agent model dropdown with Gemini models as primary options:

- ✅ Gemini 2.0 Flash (Experimental) - **DEFAULT**
- Gemini 1.5 Pro
- Gemini 1.5 Flash
- GPT-4o
- GPT-4 Turbo
- GPT-3.5 Turbo
- Ollama - Llama 2

## Model Identifier

The LiteLLM library uses the following format for Gemini models:

- `gemini/gemini-2.0-flash-exp` - Gemini 2.0 Flash (Experimental)
- `gemini/gemini-1.5-pro` - Gemini 1.5 Pro
- `gemini/gemini-1.5-flash` - Gemini 1.5 Flash

## Required Environment Variable

Make sure your `.env` file includes your Google API key:

```bash
GOOGLE_API_KEY=your-actual-google-api-key-here
```

## Testing the Integration

1. Start the platform: `.\run.ps1`
2. Open http://localhost:5173
3. Send a test message in the chat interface
4. The backend will use Gemini 2.0 Flash for all agent interactions

## Next Steps

To fully activate LLM functionality:

1. Update `backend/app/api/routes/chat.py` to integrate LiteLLM
2. Replace placeholder responses with actual Gemini API calls
3. Implement streaming responses for better UX
4. Add error handling for API rate limits

## Notes

- LiteLLM automatically handles the Gemini API authentication using `GOOGLE_API_KEY`
- The `gemini/` prefix tells LiteLLM to use Google's Gemini API
- All existing agents will automatically use Gemini when loaded
- New agents created via GUI will default to Gemini 2.0 Flash
