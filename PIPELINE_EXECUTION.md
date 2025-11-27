# Pipeline Execution Implementation

## Overview

Sequential pipeline execution system with visual feedback, execution controls, and logging capabilities.

## Features Implemented

### 1. **Execution State Management**

- **Properties Added to `App` Class:**
  - `isExecuting`: Boolean flag for pipeline execution status
  - `executionPaused`: Pause control flag
  - `executionCancelled`: Cancellation control flag
  - `currentExecutingNode`: Reference to actively executing node
  - `executionResults`: Map storing results by instanceId
  - `executionOrder`: Topologically sorted array of nodes

### 2. **Pipeline Execution Logic**

#### `runPipeline()` Method

- Validates canvas has nodes before execution
- Calculates execution order using topological sort
- Detects circular dependencies
- Manages execution state lifecycle
- Provides toast notifications for status updates

#### `calculateExecutionOrder()` Method

- **Algorithm:** Kahn's topological sort
- Builds dependency graph from connections
- Returns execution order or `null` if cycles detected
- Ensures correct sequential execution respecting dependencies

#### `executeSequentialPipeline()` Method

- Iterates through ordered nodes
- Supports pause/resume functionality
- Handles cancellation gracefully
- Catches and logs execution errors
- Stops pipeline on first error

#### `executeNode()` Method

- **Backend Integration:** POST `/api/canvas/execute`
- Collects inputs from connected nodes
- Sends execution request to backend
- Returns structured execution result
- Handles errors with proper error messages

### 3. **Visual Feedback System**

#### CSS Classes for Node States

- `.node-running`: Blue pulsing glow with animation
- `.node-completed`: Green border and subtle shadow
- `.node-error`: Red border indicating failure
- `.node-cancelled`: Orange border with reduced opacity
- `.node-loading`: Animated spinner overlay

#### `setNodeExecutionState()` Method

- Removes previous state classes
- Applies appropriate state class
- Manages loading spinner visibility

### 4. **Execution Control Menu**

#### Dynamic Menu System

- **Normal Mode:** EDIT, DUPLICATE, DELETE buttons
- **Execution Mode:** PAUSE/RESUME, CANCEL, LOGS buttons
- Context-aware menu based on execution state
- Positioned above node during execution

#### Control Functions

- `pauseExecution()`: Pauses pipeline without losing state
- `resumeExecution()`: Continues from paused state
- `cancelExecution()`: Cancels remaining executions

### 5. **Logs Modal Component**

#### `showExecutionLogs()` Method

- Displays execution results for specific node
- Shows instanceId, agentType, timestamp, input count
- Formats output in readable JSON
- Displays errors prominently
- Modal dismissible via overlay click or close button

#### CSS Styling

- `.execution-logs-modal-content`: Wide modal (800px)
- `.execution-logs-info`: Grid layout for metadata
- `.execution-logs-output`: Formatted code block
- Monospace font for technical data
- Scrollable output area (max 400px)

### 6. **Backend Execute Endpoint**

#### Route: `POST /api/canvas/execute`

**File:** `backend/app/api/routes/canvas.py`

**Request Model:**

```python
class ExecuteNodeRequest(BaseModel):
    instanceId: str
    agentType: str
    inputs: List[dict] = []
```

**Response Model:**

```python
class ExecuteNodeResponse(BaseModel):
    instanceId: str
    agentType: str
    timestamp: str
    inputs: int
    output: str
    error: Optional[str] = None
```

**Functionality:**

- Retrieves agent from registry by type
- Combines inputs from previous nodes
- Executes agent's `process()` method
- Returns structured result with timestamp
- Handles errors gracefully with error field

## Usage

### Running a Pipeline

1. Place agent nodes on canvas
2. Connect nodes to define dependencies
3. Click **RUN** button (visible in both chat and canvas modes)
4. Watch visual feedback as nodes execute sequentially

### Controlling Execution

1. **Pause:** Hover over executing node → Click PAUSE
2. **Resume:** Hover over paused node → Click RESUME
3. **Cancel:** Hover over executing node → Click CANCEL
4. **View Logs:** Hover over completed/error node → Click LOGS

### Viewing Results

- **During Execution:** Blue pulsing glow on running node
- **After Execution:** Green border for success, red for errors
- **Logs:** Click LOGS button to see detailed output and metadata

## Technical Details

### Execution Flow

```
1. User clicks RUN button
2. Validate canvas has nodes
3. Build dependency graph from connections
4. Topological sort (detect cycles)
5. For each node in order:
   a. Check for pause/cancel
   b. Set node to "running" state
   c. Collect inputs from completed predecessors
   d. Call backend execute endpoint
   e. Store result in executionResults map
   f. Set node to "completed" or "error" state
6. Show completion toast
```

### Dependency Resolution

- Uses Kahn's algorithm for topological sorting
- Builds adjacency list and in-degree map
- Nodes with no dependencies execute first
- Detects cycles by comparing sorted count to total nodes

### Error Handling

- **Network errors:** Caught in `executeNode()`, thrown to pipeline
- **Agent errors:** Returned in response `error` field
- **Execution errors:** Sets node to error state, stops pipeline
- **Validation errors:** Prevents execution with error toast

## Files Modified

### Frontend

- `frontend/src/js/main.js`

  - Added execution state properties
  - Implemented pipeline execution methods
  - Updated `showNodeActionMenu()` for dynamic controls
  - Added `showExecutionLogs()` modal

- `frontend/src/css/main.css`
  - Node execution state styles
  - Loading spinner animation
  - Execution logs modal styles

### Backend

- `backend/app/api/routes/canvas.py`
  - Added `ExecuteNodeRequest` model
  - Added `ExecuteNodeResponse` model
  - Implemented `POST /api/canvas/execute` endpoint

## Future Enhancements

### Potential Improvements

1. **Parallel Execution:** Execute independent branches simultaneously
2. **Progress Bar:** Show overall pipeline progress percentage
3. **Execution History:** Store and replay previous executions
4. **Streaming Output:** Real-time output updates during execution
5. **Breakpoints:** Pause execution at specific nodes
6. **Conditional Execution:** Skip nodes based on conditions
7. **Retry Logic:** Automatically retry failed nodes
8. **Export Results:** Download execution logs as JSON/CSV

### Known Limitations

1. Sequential execution only (no parallel branches)
2. No execution persistence across page refresh
3. No intermediate result caching
4. Limited error recovery options
5. No execution time estimation

## Testing Recommendations

### Test Scenarios

1. **Simple Pipeline:** 2-3 connected nodes in sequence
2. **Branching Pipeline:** One node feeding multiple dependents
3. **Merging Pipeline:** Multiple nodes feeding one dependent
4. **Circular Dependencies:** Test cycle detection
5. **Empty Canvas:** Test validation with no nodes
6. **Disconnected Nodes:** Test nodes without connections
7. **Error Handling:** Test with agent that throws errors
8. **Pause/Resume:** Test mid-execution controls
9. **Cancel:** Test cancellation at different stages
10. **Logs Modal:** Test with various output formats

### Expected Behaviors

- ✅ Nodes execute in dependency order
- ✅ Visual states update correctly
- ✅ Pause preserves execution state
- ✅ Cancel stops remaining nodes
- ✅ Errors stop pipeline and show error state
- ✅ Logs modal displays all execution details
- ✅ Menu switches context during execution
- ✅ Toast notifications inform user of status

## API Integration

### Frontend API Call

```javascript
const response = await fetch(`${API_URL}/api/canvas/execute`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    instanceId: "node-123",
    agentType: "data_loader",
    inputs: [{ output: "previous result 1" }, { output: "previous result 2" }],
  }),
});

const result = await response.json();
// { instanceId, agentType, timestamp, inputs, output, error }
```

### Backend Execution

```python
# Get agent from registry
agent = agent_registry.get_agent(request_data.agentType)

# Combine inputs
combined_input = "\n".join([
    str(inp.get("output", "")) for inp in request_data.inputs
])

# Execute agent
result = await agent.process(combined_input)

# Return response
return ExecuteNodeResponse(
    instanceId=request_data.instanceId,
    agentType=request_data.agentType,
    timestamp=datetime.utcnow().isoformat(),
    inputs=len(request_data.inputs),
    output=result
)
```

## Troubleshooting

### Common Issues

**Pipeline doesn't start:**

- Ensure canvas has at least one node
- Check browser console for errors
- Verify backend is running

**Circular dependency detected:**

- Review connections for cycles
- Use topological view to identify loops
- Remove or reconfigure problematic connections

**Node stuck in running state:**

- Check backend logs for agent errors
- Verify agent `process()` method returns properly
- Check network tab for failed API calls

**Logs modal shows "No execution logs":**

- Ensure node has been executed
- Check executionResults map in console
- Verify instanceId matches

**Execution controls not appearing:**

- Ensure node is currently executing
- Check `this.currentExecutingNode` value
- Verify menu is being recreated on hover
