# AutoML Agentic Platform - Technical Requirements Document

## Project Overview

A web-based AutoML platform powered by AI agents that enables users to build machine learning pipelines through natural language interactions. The platform combines agent-based architecture with drag-and-drop workflow capabilities, similar to Orange or KNIME, but with conversational AI at its core.

## Core Requirements

### 1. System Architecture

**Pattern**: Clean Architecture + Microservices-oriented design

- **Frontend**: Single Page Application (SPA) with vanilla JavaScript/modern CSS
- **Backend**: Python-based REST API (FastAPI for performance and modern async support)
- **Agent Layer**: Distributed agent system with A2A (Agent-to-Agent) communication
- **Configuration**: YAML-based + GUI-based agent configuration
- **Tools**: Model Context Protocol (MCP) integration for agent tools

### 2. User Interface Requirements

#### 2.1 Chat Interface (Primary Interaction)

- ChatGPT-like conversational interface
- Natural language input for all user interactions
- Real-time message streaming
- Support for multi-turn conversations
- Clear visual feedback for agent actions
- Message history with timestamps
- Support for file attachments (CSV only for MVP)

#### 2.2 Agent Configuration GUI

- Visual agent creation and editing interface
- Form-based configuration for:
  - Agent name and description
  - System prompts
  - Model selection (local/remote: GPT-5.1, Gemini, Ollama, Mistral, etc.)
  - Communication settings (A2A enabled/disabled)
  - MCP tool assignments
  - Input/output specifications
- Live YAML preview
- Save/Load configurations
- Agent template library

#### 2.3 Visual Pipeline Builder (Future)

- Drag-and-drop canvas for pipeline creation
- Visual representation of agent connections
- Data flow visualization
- Not in MVP scope

### 3. Agent System Requirements

#### 3.1 Agent Configuration

**Dual configuration approach**:

1. **YAML Files**: For developers and version control

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
       can_send_to: ["model_trainer", "feature_engineer"]
   ```

2. **GUI Configuration**: Web-based form that generates/updates YAML

#### 3.2 Agent Capabilities

- **System Prompts**: Each agent has customizable behavior via system prompts
- **Model Flexibility**: Support for multiple LLM providers
- **Tool Usage**: MCP-based tool integration
- **Communication**:
  - A2A protocol for inter-agent messaging
  - Direct agent-to-agent communication
  - Message queuing and routing
- **Specialized Behaviors**:
  - Data preprocessing agents
  - Model training agents
  - Evaluation agents
  - Visualization agents

#### 3.3 Agent Communication

**Two modes**:

1. **With A2A**: Structured protocol-based communication
2. **Without A2A**: Direct function calls/REST API between agents

### 4. Data Handling (MVP Scope)

#### 4.1 CSV Support

- File upload via drag-and-drop or file picker
- Automatic schema detection
- Preview of uploaded data (first 100 rows)
- Basic validation (file size limits, format checking)
- Storage in temporary session-based location

#### 4.2 Data Processing

- Agents can read, transform, and analyze CSV data
- Support for common operations:
  - Filtering
  - Aggregation
  - Feature engineering
  - Missing value handling
  - Outlier detection

### 5. MCP (Model Context Protocol) Integration

#### 5.1 Tool System

- MCP server integration for tool discovery
- Tool registration and management
- Dynamic tool binding to agents
- Standard tools for MVP:
  - `csv_reader`: Read and parse CSV files
  - `data_analyzer`: Statistical analysis
  - `data_transformer`: Data manipulation
  - `model_trainer`: ML model training interface
  - `model_evaluator`: Model evaluation metrics

#### 5.2 Tool Execution

- Asynchronous tool execution
- Result streaming to chat interface
- Error handling and retry logic
- Tool execution history

### 6. Technical Stack

#### 6.1 Backend

- **Framework**: FastAPI (Python 3.11+)
- **Web Server**: Uvicorn
- **Agent Framework**: LangGraph or custom implementation
- **LLM Integration**: LiteLLM (unified interface for all models)
- **Message Queue**: Redis or RabbitMQ (for A2A communication)
- **File Storage**: Local filesystem (session-based for MVP)
- **Database**: SQLite (for MVP) → PostgreSQL (production)
- **Configuration**: Pydantic for validation, PyYAML for parsing

#### 6.2 Frontend

- **Core**: Vanilla JavaScript (ES6+)
- **CSS Framework**: Modern CSS with CSS Grid and Flexbox
- **UI Components**: Custom lightweight components
- **Icons**: Lucide Icons or similar
- **Build Tool**: Vite (for development server and bundling)
- **State Management**: Reactive vanilla JS patterns

#### 6.3 Infrastructure

- **Containerization**: Docker + Docker Compose
- **Environment Management**: .env files
- **Configuration**: YAML files for agents
- **Logging**: Structured logging (JSON format)

### 7. Design Patterns

#### 7.1 Backend Patterns

- **Repository Pattern**: Data access abstraction
- **Factory Pattern**: Agent creation and initialization
- **Strategy Pattern**: Different communication strategies (A2A vs direct)
- **Observer Pattern**: Event-driven agent communication
- **Chain of Responsibility**: Agent pipeline execution

#### 7.2 Frontend Patterns

- **Module Pattern**: Encapsulated JavaScript modules
- **Observer Pattern**: Event-driven UI updates
- **Component Pattern**: Reusable UI components
- **Singleton Pattern**: Application state management

### 8. Modern Web Features to Leverage

#### 8.1 HTML5

- **File API**: For CSV uploads
- **WebSockets**: Real-time communication
- **Local Storage**: Session persistence
- **Semantic HTML**: Accessibility and SEO

#### 8.2 CSS3

- **CSS Grid**: Layout system
- **CSS Custom Properties**: Theming
- **CSS Animations**: Smooth transitions
- **Container Queries**: Responsive components
- **CSS Nesting**: Cleaner stylesheets

#### 8.3 JavaScript (ES2024)

- **Async/Await**: Asynchronous operations
- **Modules**: Code organization
- **Fetch API**: HTTP requests
- **Streams API**: Large file handling
- **Web Workers**: Background processing

### 9. Security Considerations

- **Input Validation**: All user inputs sanitized
- **File Upload Limits**: Max 50MB for CSV files
- **CORS**: Properly configured
- **API Authentication**: JWT tokens (future)
- **Rate Limiting**: Prevent abuse
- **Secure Headers**: CSP, HSTS, etc.

### 10. MVP Feature Scope

#### Included in MVP

✅ Chat interface with natural language interaction
✅ Agent configuration via YAML files
✅ Agent configuration via GUI
✅ Basic agent execution with system prompts
✅ CSV file upload and parsing
✅ MCP tool integration (basic tools)
✅ A2A communication (simplified)
✅ Single model support (OpenAI GPT or local Ollama)
✅ Basic data preprocessing capabilities

#### Deferred to Future Phases

❌ Visual drag-and-drop pipeline builder
❌ Multiple simultaneous model support
❌ Advanced agent orchestration
❌ User authentication and multi-tenancy
❌ Database integration (beyond local SQLite)
❌ Advanced data visualization
❌ Model deployment capabilities
❌ Collaborative features

### 11. Development Phases

#### Phase 1: Foundation (Current)

1. Project structure setup
2. Backend API skeleton
3. Basic frontend layout
4. Requirements documentation

#### Phase 2: Core Features

1. Chat interface implementation
2. YAML-based agent configuration
3. Basic agent execution
4. CSV file handling

#### Phase 3: Advanced Features

1. GUI agent configuration
2. MCP tool integration
3. A2A communication
4. Multi-agent orchestration

#### Phase 4: Polish

1. Error handling and validation
2. UI/UX improvements
3. Performance optimization
4. Documentation

### 12. Non-Functional Requirements

#### 12.1 Performance

- Chat response time: < 2 seconds for LLM responses
- File upload: Support up to 50MB CSV files
- UI responsiveness: 60 FPS animations
- API response time: < 500ms for non-LLM operations

#### 12.2 Scalability

- Support for 10+ concurrent agents
- Handle CSV files with 1M+ rows
- Message queue for async operations

#### 12.3 Usability

- Intuitive chat interface
- Clear error messages
- Responsive design (desktop-first, mobile-friendly)
- Accessibility compliance (WCAG 2.1 Level AA)

#### 12.4 Maintainability

- Modular code structure
- Comprehensive error logging
- Configuration via environment variables
- Clear documentation

### 13. Success Metrics

- User can create and configure an agent via GUI in < 5 minutes
- User can upload CSV and get insights via chat in < 30 seconds
- System can process ML pipeline with 3+ agents
- Zero critical security vulnerabilities
- 90%+ test coverage for core functionality

## Architectural Decisions

### Why FastAPI?

- Modern async support for real-time features
- Automatic API documentation (OpenAPI/Swagger)
- High performance
- Easy WebSocket integration
- Type hints and validation with Pydantic

### Why Vanilla JS over React/Vue?

- Reduced complexity and dependencies
- Faster load times
- Better understanding of fundamentals
- No build step complexity (beyond Vite bundling)
- Easier to maintain for small team

### Why YAML for Configuration?

- Human-readable and editable
- Version control friendly
- Industry standard for configuration
- Easy to validate and parse
- Supports comments for documentation

### Why MCP for Tools?

- Standardized protocol for LLM tools
- Growing ecosystem
- Separation of concerns
- Easy to extend
- Works with multiple LLM providers

## Conclusion

This platform will democratize ML pipeline creation by combining the power of AI agents with an intuitive conversational interface. The architecture emphasizes simplicity, maintainability, and extensibility while leveraging modern web technologies and design patterns.
