# Agentic AutoML Platform

A conversational AI-powered AutoML platform that enables users to build machine learning pipelines through natural language interactions.

## Features

- 🤖 **AI Agent System**: Configurable agents with specialized behaviors
- 💬 **ChatGPT-like Interface**: Natural language interaction for ML tasks
- 🔧 **Dual Configuration**: YAML files + GUI-based agent configuration
- 🔗 **Agent Communication**: A2A (Agent-to-Agent) protocol support
- 🛠️ **MCP Integration**: Model Context Protocol for tool usage
- 📊 **CSV Support**: Upload and process datasets
- 🎨 **Modern UI**: Clean, responsive interface with latest web technologies
- 💾 **Persistent Storage**: Docker volumes ensure data survives container restarts

## Tech Stack

### Backend

- **FastAPI**: Modern, high-performance Python web framework
- **LiteLLM**: Unified interface for multiple LLM providers
- **Pydantic**: Data validation and settings management
- **Redis**: Message queue for agent communication

### Frontend

- **Vanilla JavaScript**: Modern ES6+ with no heavy frameworks
- **Vite**: Fast development server and build tool
- **Modern CSS**: Grid, Flexbox, Custom Properties

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend development)
- Docker (optional)

### Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd platform
```

2. **Backend Setup**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Frontend Setup**

```bash
cd frontend
npm install
```

4. **Environment Configuration**

```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running the Application

**Development Mode:**

Terminal 1 - Backend:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Frontend:

```bash
cd frontend
npm run dev
```

Access the application at: `http://localhost:5173`

**Using Docker:**

```bash
docker-compose up
```

**Managing Persistent Data:**

All application data is stored in Docker volumes and persists across container restarts:

```powershell
# Backup your data
.\manage-volumes.ps1 -Action backup

# Restore from backup
.\manage-volumes.ps1 -Action restore

# List all volumes
.\manage-volumes.ps1 -Action list
```

See [PERSISTENCE.md](docs/PERSISTENCE.md) for detailed information about data persistence.

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed structure.

## Configuration

### Agent Configuration (YAML)

Create agent configurations in `config/agents/`:

```yaml
agent:
  name: "data_preprocessor"
  description: "Handles data cleaning and transformation"
  model: "gpt-4o"
  system_prompt: "You are a data preprocessing expert..."
  a2a_enabled: true
  tools:
    - csv_reader
    - data_transformer
  communication:
    can_receive_from: ["*"]
    can_send_to: ["model_trainer"]
```

## Usage

### Chat Interface

Type natural language queries like:

- "Load the sales data and show me the first 10 rows"
- "Clean the data and remove missing values"
- "Train a classification model on this dataset"

### Agent Configuration

**Via YAML**: Create/edit YAML files in `config/agents/`
**Via GUI**: Use the web interface to configure agents visually

## Documentation

- [Data Persistence Guide](docs/PERSISTENCE.md)
- [Requirements Document](docs/REQUIREMENTS.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)
- [API Documentation](http://localhost:8000/docs)

## Roadmap

### MVP (Current Phase)

- [x] Requirements documentation
- [x] Project structure
- [ ] Chat interface
- [ ] Agent configuration system
- [ ] CSV processing
- [ ] MCP tool integration

### Future Phases

- [ ] Visual pipeline builder
- [ ] Multi-user support
- [ ] Advanced orchestration
- [ ] Model deployment

## License

MIT License

---

Built with ❤️ using modern web technologies and AI agents
