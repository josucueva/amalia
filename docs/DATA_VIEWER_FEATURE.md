# Data Viewer Feature - Implementation Guide

## Overview

The Data Viewer feature provides a comprehensive way to inspect inputs and outputs of executed agents in the canvas pipeline.

## Features Implemented

### 1. **Visual Data Badges on Nodes**

- **Input Badge** (left): Shows when a node has received input data
  - Icon: Arrow down to line
  - Color: Blue (#4a9eff)
  - Tooltip: Shows input count
- **Output Badge** (right): Shows when a node has generated output
  - Icon: Arrow up from line
  - Color: Green (#50c878)
  - Animates on completion with pulse effect

### 2. **VIEW DATA Button**

- Appears in the action menu for nodes that have been executed
- Located alongside EDIT, DUPLICATE, DELETE buttons
- Opens the Data Viewer Modal

### 3. **Data Viewer Modal**

Comprehensive modal showing:

#### Execution Metadata Section

- Instance ID (monospace)
- Agent Type
- Timestamp (localized)
- Input Count (badge)
- Status (Success/Error with color coding)

#### Input Data Section

- Shows all inputs from connected nodes
- Each input displays:
  - Source agent ID
  - Source instance ID
  - Data preview (formatted JSON/text)
  - Truncated if too long (2000 chars)

#### Output Data Section

- Formatted output data
- JSON pretty-printing
- Error display if execution failed
- Scrollable preview (max 300px height)

#### Actions Section

- **Copy Output**: Copies output to clipboard
- **Download JSON**: Downloads full execution data as JSON file

## Usage

### For Users

1. **Run a pipeline** using the RUN button
2. **Click on any executed node** to open the action menu
3. **Click "VIEW DATA"** to see detailed execution information
4. **Inspect inputs/outputs** in the modal
5. **Copy or download data** as needed

### For Developers

#### Updating Node Badges

```javascript
// Called automatically after node execution
this.updateNodeDataBadges(node, executionResult);
```

#### Showing Data Viewer

```javascript
// Called from action menu
this.showNodeDataViewer(instanceId, agentInstance);
```

#### Data Format

Execution results are stored in `this.executionResults` Map:

```javascript
{
  instanceId: "instance_123456",
  agentType: "data_loader",
  timestamp: "2025-11-29T10:30:00.000Z",
  inputs: 2,
  output: "...data...",
  error: null // or error message
}
```

## Design Patterns Used

### 1. **Observer Pattern**

- Execution state changes trigger badge updates
- Automatic UI updates on data availability

### 2. **Factory Pattern**

- Modal generation based on execution data
- Dynamic content rendering

### 3. **State Management**

- Centralized execution results in Map
- Clean separation of concerns

### 4. **Progressive Disclosure**

- Visual indicators (badges) for quick overview
- Detailed modal for in-depth inspection

## CSS Architecture

### Component Hierarchy

```
.agent-node
├── .agent-node-header
├── .agent-node-model
├── .agent-node-data-badges
│   ├── .input-badge.data-badge
│   └── .output-badge.data-badge
├── .agent-node-input (port)
└── .agent-node-output (port)

.modal (data viewer)
└── .data-viewer-modal-content
    ├── .modal-header
    ├── .data-viewer-body
    │   ├── .data-section (metadata)
    │   ├── .data-section (inputs)
    │   └── .data-section (outputs)
    └── .modal-footer
```

### Key CSS Classes

- `.data-badge`: Base badge styling
- `.input-badge`: Blue input indicator
- `.output-badge`: Green output indicator
- `.data-section`: Modal content sections
- `.data-preview`: Code/data display areas
- `.error-display`: Error message formatting

## Accessibility

- **Keyboard Navigation**: Modal closes on Escape key
- **ARIA Labels**: Icons have descriptive titles
- **Color Coding**: Supplemented with text labels
- **Contrast**: Meets WCAG AA standards (with minor exceptions for error backgrounds)

## Performance Considerations

1. **Lazy Loading**: Badges only appear after execution
2. **Data Truncation**: Long strings limited to 2000 chars
3. **Virtual Scrolling**: Scrollable preview areas prevent DOM bloat
4. **Event Delegation**: Efficient event handling on modal

## Future Enhancements

### Potential Additions

- [ ] Data diff viewer (compare executions)
- [ ] Export to CSV for tabular data
- [ ] Syntax highlighting for JSON/code
- [ ] Search/filter within data
- [ ] Real-time streaming for long-running operations
- [ ] Data visualization (charts for numeric data)
- [ ] Schema validation display
- [ ] Data lineage tracking

## Testing Checklist

- [ ] Badge appears after successful execution
- [ ] Badge shows correct input count
- [ ] VIEW DATA button appears for executed nodes
- [ ] Modal displays all metadata correctly
- [ ] Input data from multiple sources shown
- [ ] Output data formatted properly
- [ ] Error state displays correctly
- [ ] Copy to clipboard works
- [ ] Download JSON works
- [ ] Modal closes on Escape
- [ ] Modal closes on overlay click
- [ ] Responsive on different screen sizes

## Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Known Limitations

1. **Large Data**: Very large outputs (>10MB) may cause performance issues
2. **Binary Data**: Non-text data not displayed well
3. **Nested Objects**: Deep nesting may be hard to read (consider tree view)

## Troubleshooting

### Badges Don't Appear

- Check that `updateNodeDataBadges()` is called after execution
- Verify execution results are stored in `executionResults` Map
- Check console for errors

### Modal Shows "No Data Available"

- Ensure node has been executed at least once
- Check that `instanceId` matches between execution and retrieval
- Verify execution didn't fail silently

### Copy/Download Doesn't Work

- Check browser clipboard permissions
- Verify JSON data is valid
- Check browser download settings

## Code References

### Main Files

- `frontend/src/js/main.js` - Core implementation
  - `updateNodeDataBadges()` (line ~520)
  - `showNodeDataViewer()` (line ~550)
  - `formatDataForDisplay()` (line ~700)
- `frontend/src/css/main.css` - Styling
  - `.agent-node-data-badges` (line ~590)
  - `.data-viewer-modal-content` (line ~1040)

### Related Components

- `ConnectionManager.js` - Connection data retrieval
- `executeNode()` - Execution result storage
- Action menu system - VIEW DATA button integration
