# Quick Start Guide

## Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- Git

## Installation

### 1. Backend Setup

Open PowerShell and navigate to the backend directory:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Frontend Setup

Open a new PowerShell window and navigate to the frontend directory:

```powershell
cd frontend
npm install
```

### 3. Environment Configuration

Copy the example environment file:

```powershell
cp .env.example .env
```

Edit `.env` and add your API keys:

- `OPENAI_API_KEY` - Your OpenAI API key (if using GPT models)
- Or configure Ollama for local models

### 4. Create Required Directories

```powershell
New-Item -ItemType Directory -Force -Path data\uploads
New-Item -ItemType Directory -Force -Path logs
```

## Running the Application

### Start Backend (Terminal 1)

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000
API Documentation: http://localhost:8000/docs

### Start Frontend (Terminal 2)

```powershell
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:5173

## Using Docker (Alternative)

```powershell
docker-compose up
```

This will start both backend and frontend services.

## First Steps

1. Open http://localhost:5173 in your browser
2. The application will load with 3 pre-configured agents from YAML files
3. Upload a CSV file using the "Upload Data" button
4. Start chatting with the AI agents!

## Example Queries

- "Show me the first 10 rows of my data"
- "Clean the data and remove missing values"
- "What's the summary statistics of my dataset?"
- "Train a classification model"

## Troubleshooting

### Backend won't start

- Ensure Python 3.11+ is installed: `python --version`
- Check if port 8000 is available
- Verify all dependencies are installed: `pip list`

### Frontend won't start

- Ensure Node.js 18+ is installed: `node --version`
- Delete `node_modules` and run `npm install` again
- Check if port 5173 is available

### Can't connect to backend

- Verify backend is running at http://localhost:8000
- Check CORS settings in `.env`
- Look at browser console for errors

## Next Steps

- Read [REQUIREMENTS.md](REQUIREMENTS.md) for detailed documentation
- Check [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for codebase organization
- Create custom agents by editing YAML files in `config/agents/`
- Use the GUI to create new agents interactively

## Development

### Backend Testing

```powershell
cd backend
pytest
```

### Code Formatting

```powershell
cd backend
black app/
flake8 app/
```

### Frontend Build

```powershell
cd frontend
npm run build
```

## Support

For issues, please check:

- Backend logs in `logs/app.log`
- Browser console for frontend errors
- Backend API docs at http://localhost:8000/docs
