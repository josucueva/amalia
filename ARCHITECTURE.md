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
│  │  /api/health    /api/canvas                         │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │                                   │
│  ┌─────────────────── Business Logic ──────────────────┐   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │      Agent Pipeline Service (NEW!)           │  │   │
│  │  │  Orchestrates the 3-agent workflow:          │  │   │
│  │  │  Interaction → Planner → Orchestrator        │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │   │
│  │  │    Agent     │  │    Config    │  │   File    │ │   │
│  │  │   Registry   │  │    Loader    │  │  Handler  │ │   │
│  │  └──────────────┘  └──────────────┘  └───────────┘ │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐  │   │
│  │  │        LLM Service (LiteLLM)                 │  │   │
│  │  │  Unified interface for multiple providers    │  │   │
│  │  └──────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│  ┌─────────────────── Agent System ─────────────────────┐  │
│  │                                                        │  │
│  │  Visible Agents:                                      │  │
│  │  ├─ interaction_agent (user-facing)                   │  │
│  │  ├─ data_loader                                       │  │
│  │  ├─ data_preprocessor                                 │  │
│  │  ├─ model_trainer                                     │  │
│  │  ├─ model_evaluator                                   │  │
│  │  └─ data_visualizer                                   │  │
│  │                                                        │  │
│  │  Hidden Agents (transparent to user):                 │  │
│  │  ├─ planner_agent (creates execution plans)           │  │
│  │  └─ orchestrator_agent (instantiates pipelines)       │  │
│  └────────────────────────────────────────────────────────┘  │
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
│  │   OpenAI     │  │   Gemini     │  │    Redis     │      │
│  │   (GPT-4)    │  │  (Flash 2.5) │  │ (Future MQ)  │      │
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
Agent Pipeline Service
    │
    ├─── Step 1: Interaction Agent
    │    - Refines user prompt
    │    - Decides if pipeline building is needed
    │    - Returns JSON action or normal response
    │
    ├─── Step 2: Planner Agent (if pipeline needed)
    │    - Receives improved prompt
    │    - Creates execution plan with phases
    │    - Identifies required agent types
    │
    ├─── Step 3: Orchestrator Agent (if pipeline needed)
    │    - Receives execution plan
    │    - Creates canvas configuration
    │    - Positions agents and creates connections
    │
    ▼
Response (with orchestration data if applicable)
    │
    ▼
Chat Component → Display + Trigger Canvas Update
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

## Three-Agent Pipeline Architecture

### Overview

AMALIA implements a sophisticated three-agent pipeline for intelligent pipeline creation:

1. **Interaction Agent** (user-facing) - Refines requirements
2. **Planner Agent** (hidden) - Creates execution plans
3. **Orchestrator Agent** (hidden) - Instantiates pipelines

### Agent Roles

#### 1. Interaction Agent

- **Purpose**: First point of contact with users
- **Visibility**: Visible in UI
- **Responsibilities**:
  - Listen to user requirements
  - Ask clarifying questions if needed
  - Refine prompts into clear, actionable descriptions
  - Decide when to trigger pipeline creation
- **Output**: JSON with `action: "plan_pipeline"` and improved prompt

#### 2. Planner Agent (Hidden)

- **Purpose**: Strategic planning and phase decomposition
- **Visibility**: Hidden from users (metadata: `is_hidden: true`)
- **Responsibilities**:
  - Receive improved prompts from interaction agent
  - Break down objectives into logical phases
  - Identify required agent types for each phase
  - Define data flow between phases
  - Estimate complexity (simple/medium/complex)
- **Output**: JSON with execution plan containing phases

#### 3. Orchestrator Agent (Hidden)

- **Purpose**: Canvas pipeline instantiation
- **Visibility**: Hidden from users (metadata: `is_hidden: true`)
- **Responsibilities**:
  - Receive execution plans from planner agent
  - Create canvas node configurations
  - Position agents spatially on canvas
  - Create connections between agents
  - Map agent types to actual agent IDs
- **Output**: JSON with nodes and connections for canvas

### Communication Flow Example

```
User: "I want to analyze sales data and predict churn"
    │
    ▼
[Interaction Agent]
    │ Refines prompt
    └─> { action: "plan_pipeline",
          improved_prompt: "Load sales.csv, clean data,
          train classifier, evaluate" }
        │
        ▼
[Planner Agent]
    │ Creates execution plan
    └─> { plan: {
          phases: [
            { phase: 1, agent_type: "data_loader" },
            { phase: 2, agent_type: "data_preprocessor" },
            { phase: 3, agent_type: "model_trainer" },
            { phase: 4, agent_type: "model_evaluator" }
          ],
          complexity: "medium"
        }}
        │
        ▼
[Orchestrator Agent]
    │ Creates canvas configuration
    └─> { orchestration: {
          nodes: [4 positioned agents],
          connections: [3 connections]
        }}
        │
        ▼
User Interface: "✅ Pipeline created! 4 phases, 4 agents."
Canvas Mode: Displays visual pipeline
```

### Benefits

1. **Separation of Concerns**: Each agent has a single responsibility
2. **Transparency**: Hidden agents work behind the scenes
3. **Flexibility**: Easy to improve each agent independently
4. **User Experience**: Simple interface, complex orchestration

### Implementation Details

- **Communication**: Direct function calls (no A2A) by default
- **Filtering**: Hidden agents excluded from UI lists (`include_hidden=False`)
- **Service Layer**: `AgentPipelineService` orchestrates the flow
- **Error Handling**: Graceful fallback if any agent is unavailable

---

This architecture supports the current MVP and is designed to scale for future features like visual pipeline building, multi-user support, and advanced agent orchestration.
