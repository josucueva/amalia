# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Browser                         │
│                     (http://localhost:5173)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP/REST
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Frontend (Vite + Vanilla JS)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Chat     │  │ File Upload  │  │Agent Config  │      │
│  │  Component   │  │  Component   │  │  Component   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │  API Client │                          │
│                    └─────────────┘                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ REST API
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Backend (FastAPI + Python)                      │
│                 (http://localhost:8000)                      │
│                                                              │
│  ┌─────────────────── API Layer ───────────────────────┐   │
│  │  /api/chat      /api/agents      /api/files         │   │
│  │  /api/health                                         │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │                                   │
│  ┌─────────────────── Business Logic ──────────────────┐   │
│  │                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │   │
│  │  │    Agent     │  │    Config    │  │   File    │ │   │
│  │  │   Registry   │  │    Loader    │  │  Handler  │ │   │
│  │  └──────────────┘  └──────────────┘  └───────────┘ │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │        Agent Communication Layer             │  │   │
│  │  │  (A2A Protocol - Future Implementation)      │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │           MCP Tool System                     │  │   │
│  │  │  (Model Context Protocol - Future)           │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│  ┌─────────────────── Data Layer ─────────────────────┐    │
│  │                                                      │    │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐ │    │
│  │  │   Agent    │  │    CSV     │  │   Message    │ │    │
│  │  │   Models   │  │   Storage  │  │   History    │ │    │
│  │  └────────────┘  └────────────┘  └──────────────┘ │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
                         │
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  External Services                           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   OpenAI     │  │   Ollama     │  │    Redis     │      │
│  │   (GPT-4o)   │  │   (Local)    │  │ (Future MQ)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Component Interaction Flow

### 1. User Sends Chat Message

```
User Input
    │
    ▼
Chat Component
    │
    ▼
API Client (POST /api/chat)
    │
    ▼
Chat Router (Backend)
    │
    ▼
Agent Registry
    │
    ▼
Agent Execution
    │
    ▼
LLM Service (OpenAI/Ollama)
    │
    ▼
Response
    │
    ▼
Chat Component (Display)
```

### 2. File Upload Flow

```
User Selects File
    │
    ▼
FileUpload Component
    │
    ▼
Validation (Type, Size)
    │
    ▼
API Client (POST /api/files/upload)
    │
    ▼
File Router (Backend)
    │
    ▼
File Storage (data/uploads/)
    │
    ▼
Response with File ID
    │
    ▼
State Update
```

### 3. Agent Configuration Flow

```
User Creates Agent
    │
    ▼
AgentConfig Component
    │
    ▼
Form Validation
    │
    ▼
API Client (POST /api/agents)
    │
    ▼
Agent Router (Backend)
    │
    ▼
Agent Factory
    │
    ▼
Agent Registry
    │
    ▼
YAML Generator (Optional)
    │
    ▼
Response
```

## Data Models

### Agent Model

```
Agent
├── id: string
├── config: AgentConfig
│   ├── name: string
│   ├── description: string
│   ├── model: string
│   ├── system_prompt: string
│   ├── a2a_enabled: boolean
│   ├── tools: List[string]
│   └── communication: CommunicationConfig
├── status: AgentStatus
├── created_at: datetime
└── updated_at: datetime
```

### Message Model

```
Message
├── id: string
├── role: MessageRole (user|assistant|agent|system)
├── content: string
├── timestamp: datetime
├── status: MessageStatus
├── metadata: dict
└── agent_id: string (optional)
```

## Technology Stack Layers

```
┌─────────────────────────────────────────┐
│          Presentation Layer              │
│  (HTML, CSS, Vanilla JavaScript)         │
├─────────────────────────────────────────┤
│          Application Layer               │
│  (FastAPI Routes, Components)            │
├─────────────────────────────────────────┤
│           Business Layer                 │
│  (Agent System, Logic, Rules)            │
├─────────────────────────────────────────┤
│           Data Access Layer              │
│  (File I/O, Config Loader)               │
├─────────────────────────────────────────┤
│          Infrastructure Layer            │
│  (LLM APIs, Storage, Message Queue)      │
└─────────────────────────────────────────┘
```

## Design Patterns Applied

1. **Factory Pattern**: Agent creation
2. **Registry Pattern**: Agent management
3. **Strategy Pattern**: Communication methods (A2A vs Direct)
4. **Observer Pattern**: State management in frontend
5. **Repository Pattern**: Data access abstraction
6. **MVC-like**: Component-based architecture

## Security Layers

```
Input Validation
    ↓
File Type/Size Checks
    ↓
API Rate Limiting
    ↓
CORS Configuration
    ↓
Environment Variables
    ↓
Sanitized Output
```

## Scalability Considerations

- **Horizontal Scaling**: Stateless API design
- **Message Queue**: Redis for async agent communication
- **Caching**: Redis for session data
- **Load Balancing**: Docker Compose ready
- **CDN Ready**: Static assets in frontend

## Development vs Production

### Development

- Hot reload (both frontend and backend)
- Detailed logging
- CORS allows localhost
- SQLite database

### Production (Future)

- Compiled frontend bundle
- JSON logging
- Restricted CORS
- PostgreSQL database
- Redis message queue
- Docker deployment
- Reverse proxy (Nginx)

---

This architecture supports the current MVP and is designed to scale for future features like visual pipeline building, multi-user support, and advanced agent orchestration.
