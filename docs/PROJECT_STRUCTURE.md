# Project Structure

```
platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Configuration management
│   │   ├── database.py             # MongoDB connection handling
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py         # Chat endpoints
│   │   │   │   ├── sessions.py     # Session management endpoints
│   │   │   │   ├── agents.py       # Agent management endpoints
│   │   │   │   ├── mcp_servers.py  # MCP server endpoints
│   │   │   │   ├── models.py       # LLM model endpoints
│   │   │   │   ├── files.py        # File upload endpoints
│   │   │   │   ├── canvas.py       # Canvas/Pipeline endpoints
│   │   │   │   └── health.py       # Health check endpoints
│   │   │   └── deps.py             # API dependencies
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── agent_service_db.py       # Agent persistence service
│   │   │   ├── session_manager_db.py     # Session persistence service
│   │   │   ├── mcp_server_service_db.py  # MCP server persistence service
│   │   │   └── model_service_db.py       # Model persistence service
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base agent class
│   │   │   ├── factory.py          # Agent factory pattern
│   │   │   ├── config_loader.py    # YAML config loader
│   │   │   └── registry.py         # Agent registry
│   │   ├── communication/
│   │   │   ├── __init__.py
│   │   │   ├── a2a.py              # A2A protocol implementation
│   │   │   ├── message_queue.py    # Message queue handler
│   │   │   └── router.py           # Message routing
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── mcp_client.py       # MCP client implementation
│   │   │   ├── csv_tools.py        # CSV processing tools
│   │   │   └── base_tools.py       # Base tool classes
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py            # Agent data models
│   │   │   ├── session.py          # Session data models
│   │   │   ├── mcp_server.py       # MCP server data models
│   │   │   ├── message.py          # Message data models
│   │   │   └── config.py           # Config data models
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logger.py           # Logging utilities
│   │       └── validators.py       # Validation utilities
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_agents.py
│   │   └── test_api.py
│   └── requirements.txt
│
├── frontend/
│   ├── index.html                  # Main HTML file
│   ├── src/
│   │   ├── js/
│   │   │   ├── main.js             # Application entry point
│   │   │   ├── api.js              # API client
│   │   │   ├── components/
│   │   │   │   ├── Chat.js         # Chat component
│   │   │   │   ├── AgentConfig.js  # Agent configuration component
│   │   │   │   ├── FileUpload.js   # File upload component
│   │   │   │   └── MessageList.js  # Message list component
│   │   │   ├── utils/
│   │   │   │   ├── state.js        # State management
│   │   │   │   └── helpers.js      # Helper functions
│   │   │   └── config.js           # Frontend config
│   │   ├── css/
│   │   │   ├── main.css            # Main stylesheet
│   │   │   ├── chat.css            # Chat styles
│   │   │   ├── components.css      # Component styles
│   │   │   └── variables.css       # CSS variables
│   │   └── assets/
│   │       └── icons/              # Icon files
│   └── vite.config.js              # Vite configuration
│
├── config/
│   ├── agents/
│   │   ├── data_preprocessor.yaml
│   │   ├── model_trainer.yaml
│   │   └── evaluator.yaml
│   └── app_config.yaml
│
├── data/
│   └── uploads/                    # Temporary uploaded files
│
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── README.md
└── REQUIREMENTS.md
```
