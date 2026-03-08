/**
 * ConnectionManager - Manages visual connections between agent nodes
 * Design Pattern: Singleton for managing canvas connections as a directed graph
 */

class ConnectionManager {
  constructor() {
    this.connections = new Map(); // Map<connectionId, Connection>
    this.svgOverlay = null;
    this.activeConnection = null;
    this.mouseMoveHandler = null;
    this.escapeHandler = null;
    this.enabled = true; // Control whether connections are active
    this.selectedConnectionId = null; // Track currently selected connection
  }

  /**
   * Get color from CSS custom properties
   */
  getCSSColor(varName) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(varName)
      .trim();
  }

  /**
   * Initialize the SVG overlay for drawing connections
   */
  initialize(canvasElement) {
    if (this.svgOverlay) {
      this.svgOverlay.remove();
    }

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "connection-overlay");
    svg.style.position = "absolute";
    svg.style.top = "0";
    svg.style.left = "0";
    svg.style.width = "100%";
    svg.style.height = "100%";
    svg.style.pointerEvents = "auto"; // Enable pointer events for clicking
    svg.style.zIndex = "1";

    canvasElement.appendChild(svg);
    this.svgOverlay = svg;

    return this;
  }

  /**
   * Handle port click for connection creation
   */
  handlePortClick(node, portType, event) {
    const port = event.target;

    console.log("🔵 Port clicked:", {
      nodeId: node.dataset.instanceId,
      portType,
      hasActiveConnection: !!this.activeConnection,
      svgOverlay: !!this.svgOverlay,
    });

    // If no active connection, start one
    if (!this.activeConnection) {
      this.startConnection(node, portType, port);
    } else {
      // Complete the connection
      this.completeConnection(node, portType);
    }
  }

  /**
   * Start creating a connection from a port
   */
  startConnection(sourceNode, portType, port) {
    const sourceInstanceId = sourceNode.dataset.instanceId;

    // With the viewport approach, node.style.left/top ARE the canvas-space coordinates.
    // No originalX/Y dataset attributes needed.
    const nodeX = Number.parseFloat(sourceNode.style.left) || 0;
    const nodeY = Number.parseFloat(sourceNode.style.top) || 0;
    const nodeWidth = sourceNode.offsetWidth;
    const nodeHeight = sourceNode.offsetHeight;

    // Port centre in canvas coordinates
    const startX = portType === "output" ? nodeX + nodeWidth : nodeX;
    const startY = nodeY + nodeHeight / 2;

    this.activeConnection = {
      sourceNode,
      sourceInstanceId,
      sourcePortType: portType,
      sourcePort: port,
      startX,
      startY,
      tempLine: null,
    };

    // Visual feedback - highlight the source port
    port.style.backgroundColor = "#1a1a1a";
    port.style.transform =
      portType === "output" ? "translateY(-50%) scale(1.5)" : "scale(1.5)";

    // Add mousemove listener to draw temporary line
    this.mouseMoveHandler = (e) => this.updateTempLine(e);
    document.addEventListener("mousemove", this.mouseMoveHandler);

    // Add escape key to cancel
    this.escapeHandler = (e) => {
      if (e.key === "Escape") {
        this.cancelConnection();
      }
    };
    document.addEventListener("keydown", this.escapeHandler);

    console.log(
      "✓ Connection started from",
      portType,
      "port of node",
      sourceInstanceId,
    );
  }

  /**
   * Update temporary connection line as mouse moves
   */
  updateTempLine(event) {
    if (!this.activeConnection) return;

    // SVG is inside #canvas-viewport. The viewport is inside #canvas-content.
    // #canvas-content is the stable (non-transformed) clipping boundary — use its
    // getBoundingClientRect() to get the screen origin of the canvas area.
    // The viewport's style.transform carries the current pan/zoom state.
    const canvasViewport = this.svgOverlay.parentElement;
    const canvasContent = canvasViewport.parentElement;
    const canvasRect = canvasContent.getBoundingClientRect();

    // Parse translate and scale from #canvas-viewport's transform
    const transform = canvasViewport.style.transform || "";
    let panX = 0,
      panY = 0,
      scale = 1;

    const translateMatch = transform.match(
      /translate\(([^,]+)px,\s*([^)]+)px\)/,
    );
    if (translateMatch) {
      panX = Number.parseFloat(translateMatch[1]) || 0;
      panY = Number.parseFloat(translateMatch[2]) || 0;
    }

    const scaleMatch = transform.match(/scale\(([^)]+)\)/);
    if (scaleMatch) {
      scale = Number.parseFloat(scaleMatch[1]) || 1;
    }

    // Convert screen coordinates to canvas (viewport) coordinates
    const screenX = event.clientX - canvasRect.left;
    const screenY = event.clientY - canvasRect.top;
    const currentX = (screenX - panX) / scale;
    const currentY = (screenY - panY) / scale;

    // Remove old temp line if exists
    if (this.activeConnection.tempLine) {
      this.activeConnection.tempLine.remove();
    }

    // Create new temp line
    this.activeConnection.tempLine = this.createConnectionPath(
      this.activeConnection.startX,
      this.activeConnection.startY,
      currentX,
      currentY,
      true,
    );

    this.svgOverlay.appendChild(this.activeConnection.tempLine);
  }

  /**
   * Complete the connection to a target port
   */
  completeConnection(targetNode, targetPortType) {
    if (!this.activeConnection) return;

    const targetInstanceId = targetNode.dataset.instanceId;

    console.log("Attempting to complete connection:", {
      from: this.activeConnection.sourceInstanceId,
      fromPort: this.activeConnection.sourcePortType,
      to: targetInstanceId,
      toPort: targetPortType,
    });

    // Validate connection
    if (
      this.validateConnectionSimple(
        this.activeConnection.sourceInstanceId,
        this.activeConnection.sourcePortType,
        targetInstanceId,
        targetPortType,
      )
    ) {
      this.createConnection(
        this.activeConnection.sourceInstanceId,
        this.activeConnection.sourcePortType,
        targetInstanceId,
        targetPortType,
      );
      this.cancelConnection();
    } else {
      console.log("✗ Connection validation failed");
      this.cancelConnection();
    }
  }

  /**
   * Cancel active connection
   */
  cancelConnection() {
    if (!this.activeConnection) return;

    // Remove temp line
    if (this.activeConnection.tempLine) {
      this.activeConnection.tempLine.remove();
    }

    // Restore source port style
    const port = this.activeConnection.sourcePort;
    port.style.backgroundColor = "";
    port.style.transform = "";

    // Remove event listeners
    if (this.mouseMoveHandler) {
      document.removeEventListener("mousemove", this.mouseMoveHandler);
      this.mouseMoveHandler = null;
    }
    if (this.escapeHandler) {
      document.removeEventListener("keydown", this.escapeHandler);
      this.escapeHandler = null;
    }

    this.activeConnection = null;
    console.log("✓ Connection cancelled");
  }

  /**
   * Validate if a connection can be made (simplified for click-based system)
   */
  validateConnectionSimple(
    sourceInstanceId,
    sourcePortType,
    targetInstanceId,
    targetPortType,
  ) {
    // Can't connect to self
    if (sourceInstanceId === targetInstanceId) {
      console.log("✗ Cannot connect node to itself");
      return false;
    }

    // Must connect output to input or input to output
    if (sourcePortType === targetPortType) {
      console.log("✗ Cannot connect same port types");
      return false;
    }

    // Determine the direction (always output -> input)
    const fromInstanceId =
      sourcePortType === "output" ? sourceInstanceId : targetInstanceId;
    const toInstanceId =
      sourcePortType === "output" ? targetInstanceId : sourceInstanceId;
    const connectionId = this.getConnectionId(fromInstanceId, toInstanceId);

    // Check if connection already exists
    if (this.connections.has(connectionId)) {
      console.log("✗ Connection already exists");
      return false;
    }

    return true;
  }

  /**
   * Create a permanent connection between two nodes
   */
  createConnection(
    sourceInstanceId,
    sourcePortType,
    targetInstanceId,
    targetPortType,
  ) {
    // Normalize connection direction (output -> input)
    const fromInstanceId =
      sourcePortType === "output" ? sourceInstanceId : targetInstanceId;
    const toInstanceId =
      sourcePortType === "output" ? targetInstanceId : sourceInstanceId;

    const connectionId = this.getConnectionId(fromInstanceId, toInstanceId);

    // Get node elements
    const sourceNode = document.querySelector(
      `[data-instance-id="${fromInstanceId}"]`,
    );
    const targetNode = document.querySelector(
      `[data-instance-id="${toInstanceId}"]`,
    );

    if (!sourceNode || !targetNode) {
      console.error("✗ Could not find nodes for connection");
      return null;
    }

    const connection = {
      id: connectionId,
      from: {
        instanceId: fromInstanceId,
        agentId: sourceNode.dataset.agentId,
      },
      to: {
        instanceId: toInstanceId,
        agentId: targetNode.dataset.agentId,
      },
      element: null,
      enabled: true, // Individual connection enabled state
    };

    // Create visual connection
    connection.element = this.drawConnection(
      sourceNode,
      targetNode,
      connectionId,
    );
    this.connections.set(connectionId, connection);

    console.log("✓ Connection created:", {
      from: fromInstanceId,
      to: toInstanceId,
      totalConnections: this.connections.size,
    });

    return connection;
  }

  /**
   * Draw a connection line between two nodes
   */
  drawConnection(sourceNode, targetNode, connectionId = null) {
    // Both nodes and this SVG overlay live inside #canvas-viewport, so they share
    // the same canvas coordinate system. Read positions directly from style.left/top
    // and use offsetWidth/Height for dimensions — no screen-space math needed.
    const startX =
      (parseFloat(sourceNode.style.left) || 0) + sourceNode.offsetWidth;
    const startY =
      (parseFloat(sourceNode.style.top) || 0) + sourceNode.offsetHeight / 2;
    const endX = parseFloat(targetNode.style.left) || 0;
    const endY =
      (parseFloat(targetNode.style.top) || 0) + targetNode.offsetHeight / 2;

    const path = this.createConnectionPath(
      startX,
      startY,
      endX,
      endY,
      false,
      connectionId,
    );
    this.svgOverlay.appendChild(path);

    return path;
  }

  /**
   * Create an SVG path element for a connection
   */
  createConnectionPath(
    x1,
    y1,
    x2,
    y2,
    isTemporary = false,
    connectionId = null,
  ) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const d = this.calculateBezierPath(x1, y1, x2, y2);

    const accentColor = this.getCSSColor("--accent-color");
    const textSecondary = this.getCSSColor("--text-secondary");

    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", isTemporary ? textSecondary : accentColor);
    path.setAttribute("stroke-width", "2");
    path.setAttribute("stroke-dasharray", isTemporary ? "5,5" : "none");
    path.setAttribute(
      "opacity",
      this.enabled ? (isTemporary ? "0.5" : "1") : "0.3",
    );
    path.style.pointerEvents = isTemporary ? "none" : "stroke";
    path.style.cursor = isTemporary ? "default" : "pointer";
    path.style.strokeWidth = "12"; // Wider invisible stroke for easier clicking
    path.style.stroke = "transparent";

    // Create visible path on top
    const visiblePath = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "path",
    );
    visiblePath.setAttribute("d", d);
    visiblePath.setAttribute("fill", "none");
    visiblePath.setAttribute(
      "stroke",
      isTemporary ? textSecondary : accentColor,
    );
    visiblePath.setAttribute("stroke-width", "2");
    visiblePath.setAttribute(
      "stroke-dasharray",
      isTemporary ? "5,5" : this.enabled ? "none" : "5,5",
    );
    visiblePath.setAttribute(
      "opacity",
      this.enabled ? (isTemporary ? "0.5" : "1") : "0.3",
    );
    visiblePath.style.pointerEvents = "none";

    // Group both paths
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.appendChild(path);
    group.appendChild(visiblePath);

    if (!isTemporary && connectionId) {
      group.dataset.connectionId = connectionId;

      // Add click handler for deletion
      path.addEventListener("click", (e) => {
        e.stopPropagation();
        this.showConnectionMenu(connectionId, e);
      });

      // Add hover effect
      path.addEventListener("mouseenter", () => {
        const connection = this.connections.get(connectionId);
        const isEnabled = connection && connection.enabled !== false;
        const accentHover = this.getCSSColor("--accent-hover");
        const textTertiary = this.getCSSColor("--text-tertiary");
        visiblePath.setAttribute(
          "stroke",
          isEnabled ? accentHover : textTertiary,
        );
        visiblePath.setAttribute("stroke-width", "3");
      });

      path.addEventListener("mouseleave", () => {
        // Don't restore if this connection is currently selected
        if (this.selectedConnectionId === connectionId) {
          return;
        }
        const connection = this.connections.get(connectionId);
        const isEnabled = connection && connection.enabled !== false;
        const accentColor = this.getCSSColor("--accent-color");
        const textTertiary = this.getCSSColor("--text-tertiary");
        visiblePath.setAttribute(
          "stroke",
          isEnabled ? accentColor : textTertiary,
        );
        visiblePath.setAttribute("stroke-width", "2");
      });
    }

    return group;
  }

  /**
   * Update an existing path element
   */
  updateConnectionPath(group, x1, y1, x2, y2) {
    const d = this.calculateBezierPath(x1, y1, x2, y2);
    const paths = group.querySelectorAll("path");
    paths.forEach((path) => {
      path.setAttribute("d", d);
    });
  }

  /**
   * Calculate a straight line path
   */
  calculateBezierPath(x1, y1, x2, y2) {
    // Use simple straight line for better rendering
    return `M ${x1} ${y1} L ${x2} ${y2}`;
  }

  /**
   * Show context menu for a connection
   */
  showConnectionMenu(connectionId, event) {
    // Remove any existing menu
    const existingMenu = document.getElementById("connection-menu");
    if (existingMenu) existingMenu.remove();

    const connection = this.connections.get(connectionId);
    if (!connection) return;

    // Clear previous selection and set new one
    if (
      this.selectedConnectionId &&
      this.selectedConnectionId !== connectionId
    ) {
      this.highlightConnection(this.selectedConnectionId, false);
    }
    this.selectedConnectionId = connectionId;

    // Highlight the selected connection
    this.highlightConnection(connectionId, true);

    const menu = document.createElement("div");
    menu.id = "connection-menu";
    menu.className = "agent-node-menu";
    menu.style.position = "fixed";
    menu.style.left = event.clientX + "px";
    menu.style.top = event.clientY + "px";
    menu.style.zIndex = "10000";

    const toggleText = connection.enabled ? "DISABLE" : "ENABLE";

    menu.innerHTML = `
      <button class="agent-node-menu-btn toggle-connection">${toggleText}</button>
      <button class="agent-node-menu-btn delete">DELETE</button>
    `;

    document.body.appendChild(menu);

    // Toggle button handler
    const toggleBtn = menu.querySelector(".toggle-connection");
    toggleBtn.addEventListener("click", () => {
      this.toggleConnectionEnabled(connectionId);
      this.highlightConnection(connectionId, false);
      this.selectedConnectionId = null;
      menu.remove();
    });

    // Delete button handler
    const deleteBtn = menu.querySelector(".delete");
    deleteBtn.addEventListener("click", () => {
      this.removeConnection(connectionId);
      this.selectedConnectionId = null;
      menu.remove();
    });

    // Close menu on outside click
    const closeMenu = (e) => {
      if (!menu.contains(e.target)) {
        this.highlightConnection(connectionId, false);
        this.selectedConnectionId = null;
        menu.remove();
        document.removeEventListener("click", closeMenu);
      }
    };
    setTimeout(() => document.addEventListener("click", closeMenu), 0);
  }

  /**
   * Highlight or unhighlight a connection
   */
  highlightConnection(connectionId, highlight) {
    const connection = this.connections.get(connectionId);
    if (!connection || !connection.element) return;

    const visiblePath = connection.element.querySelector("path:last-child");
    if (!visiblePath) return;

    if (highlight) {
      // Use CSS variable highlight color
      const accentHover = this.getCSSColor("--accent-hover");
      visiblePath.setAttribute("stroke", accentHover);
      visiblePath.setAttribute("stroke-width", "3");
      visiblePath.setAttribute("opacity", "1");
    } else {
      // Restore normal state
      const isEnabled = connection.enabled !== false;
      const accentColor = this.getCSSColor("--accent-color");
      const textTertiary = this.getCSSColor("--text-tertiary");
      visiblePath.setAttribute(
        "stroke",
        isEnabled ? accentColor : textTertiary,
      );
      visiblePath.setAttribute("stroke-width", "2");
      this.updateConnectionVisualState(connection);
    }
  }

  /**
   * Update all connection positions (call when nodes are moved)
   */
  updateConnectionPositions(instanceId) {
    const connectionsToUpdate = Array.from(this.connections.values()).filter(
      (conn) =>
        conn.from.instanceId === instanceId ||
        conn.to.instanceId === instanceId,
    );

    connectionsToUpdate.forEach((connection) => {
      const sourceNode = document.querySelector(
        `[data-instance-id="${connection.from.instanceId}"]`,
      );
      const targetNode = document.querySelector(
        `[data-instance-id="${connection.to.instanceId}"]`,
      );

      if (sourceNode && targetNode && connection.element) {
        // Remove old path
        connection.element.remove();
        // Draw new path
        connection.element = this.drawConnection(
          sourceNode,
          targetNode,
          connection.id,
        );
      }
    });
  }

  /**
   * Remove a connection
   */
  removeConnection(connectionId) {
    const connection = this.connections.get(connectionId);
    if (connection) {
      if (connection.element) {
        connection.element.remove();
      }
      this.connections.delete(connectionId);
      console.log("✓ Connection removed:", connectionId);
    }
  }

  /**
   * Remove all connections for a specific node instance
   */
  removeNodeConnections(instanceId) {
    const connectionsToRemove = Array.from(this.connections.entries()).filter(
      ([_, conn]) =>
        conn.from.instanceId === instanceId ||
        conn.to.instanceId === instanceId,
    );

    connectionsToRemove.forEach(([connectionId, _]) => {
      this.removeConnection(connectionId);
    });

    console.log(
      `✓ Removed ${connectionsToRemove.length} connections for node ${instanceId}`,
    );
  }

  /**
   * Get connection ID from instance IDs
   */
  getConnectionId(fromInstanceId, toInstanceId) {
    return `${fromInstanceId}_to_${toInstanceId}`;
  }

  /**
   * Get all connections as a serializable array
   */
  getConnectionsData() {
    return Array.from(this.connections.values()).map((conn) => ({
      id: conn.id,
      from: conn.from,
      to: conn.to,
      enabled: conn.enabled !== undefined ? conn.enabled : true,
    }));
  }

  /**
   * Get all connections for a specific node
   */
  getNodeConnections(instanceId) {
    return Array.from(this.connections.values()).filter(
      (conn) =>
        conn.from.instanceId === instanceId ||
        conn.to.instanceId === instanceId,
    );
  }

  /**
   * Clear all connections
   */
  clearAll() {
    this.connections.forEach((connection) => {
      if (connection.element) {
        connection.element.remove();
      }
    });
    this.connections.clear();
    console.log("✓ All connections cleared");
  }

  /**
   * Enable or disable connections (global)
   */
  setEnabled(enabled) {
    this.enabled = enabled;

    // Update visual state of all connections
    this.connections.forEach((connection) => {
      if (connection.element) {
        this.updateConnectionVisualState(connection);
      }
    });

    console.log(`✓ Connections ${enabled ? "enabled" : "disabled"}`);
  }

  /**
   * Toggle individual connection enabled state
   */
  toggleConnectionEnabled(connectionId) {
    const connection = this.connections.get(connectionId);
    if (!connection) return;

    connection.enabled = !connection.enabled;
    this.updateConnectionVisualState(connection);

    const status = connection.enabled ? "enabled" : "disabled";
    console.log(`✓ Connection ${connectionId} ${status}`);

    // Show toast notification if available
    if (typeof showToast === "function") {
      showToast(`Connection ${status}`, "info");
    }
  }

  /**
   * Update visual state of a connection based on global and individual enabled states
   */
  updateConnectionVisualState(connection) {
    if (!connection.element) return;

    const visiblePath = connection.element.querySelector("path:last-child");
    if (!visiblePath) return;

    // Connection is visually enabled only if both global and individual states are enabled
    const isVisuallyEnabled = this.enabled && connection.enabled;

    // Apply visual state
    visiblePath.setAttribute("opacity", isVisuallyEnabled ? "1" : "0.3");
    visiblePath.setAttribute(
      "stroke-dasharray",
      isVisuallyEnabled ? "none" : "5,5",
    );

    // Change color if individually disabled (even if globally enabled)
    const textTertiary = this.getCSSColor("--text-tertiary");
    const accentColor = this.getCSSColor("--accent-color");
    if (this.enabled && !connection.enabled) {
      visiblePath.setAttribute("stroke", textTertiary); // Gray for disabled
    } else {
      visiblePath.setAttribute("stroke", accentColor); // Accent color for normal
    }
  }

  /**
   * Export canvas state (for save/load functionality)
   */
  exportState() {
    const nodes = [];
    const nodeElements = document.querySelectorAll(".agent-node");

    nodeElements.forEach((nodeEl) => {
      try {
        const instanceData = JSON.parse(nodeEl.dataset.agentData);
        const position = {
          x: parseFloat(nodeEl.style.left) || 0,
          y: parseFloat(nodeEl.style.top) || 0,
        };
        nodes.push({
          ...instanceData,
          position,
        });
      } catch (error) {
        console.error("Error parsing node data:", error);
      }
    });

    return {
      nodes,
      connections: this.getConnectionsData(),
      version: "1.0",
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Import canvas state (for save/load functionality)
   */
  importState(state, createNodeCallback) {
    if (!state || !state.nodes) {
      console.error("Invalid state data");
      return false;
    }

    // Clear existing
    this.clearAll();
    document.querySelectorAll(".agent-node").forEach((node) => node.remove());

    // Create nodes
    const instanceMap = new Map(); // Map old instanceId to new instanceId

    state.nodes.forEach((nodeData) => {
      const oldInstanceId = nodeData.instanceId;
      const newNode = createNodeCallback(
        nodeData,
        nodeData.position.x,
        nodeData.position.y,
      );
      const newInstanceId = newNode.dataset.instanceId;
      instanceMap.set(oldInstanceId, newInstanceId);
    });

    // Recreate connections with new instance IDs
    if (state.connections && state.connections.length > 0) {
      setTimeout(() => {
        state.connections.forEach((connData) => {
          const newFromId = instanceMap.get(connData.from.instanceId);
          const newToId = instanceMap.get(connData.to.instanceId);

          if (newFromId && newToId) {
            const fromNode = document.querySelector(
              `[data-instance-id="${newFromId}"]`,
            );
            const toNode = document.querySelector(
              `[data-instance-id="${newToId}"]`,
            );

            if (fromNode && toNode) {
              const connection = this.createConnection(
                newFromId,
                "output",
                newToId,
                "input",
              );
              // Restore individual enabled state
              if (connection && connData.enabled !== undefined) {
                connection.enabled = connData.enabled;
                this.updateConnectionVisualState(connection);
              }
            }
          }
        });
        console.log(`✓ Imported ${state.connections.length} connections`);
      }, 100);
    }

    console.log(`✓ Canvas state imported: ${state.nodes.length} nodes`);
    return true;
  }

  /**
   * Export canvas state to Sim AI workflow format
   */
  async exportToSimAI(mcpServers = []) {
    const nodes = [];
    const nodeElements = document.querySelectorAll(".agent-node");

    // Parse all nodes
    nodeElements.forEach((nodeEl) => {
      try {
        const instanceData = JSON.parse(nodeEl.dataset.agentData);
        const position = {
          x: parseFloat(nodeEl.style.left) || 0,
          y: parseFloat(nodeEl.style.top) || 0,
        };
        nodes.push({
          ...instanceData,
          position,
        });
      } catch (error) {
        console.error("Error parsing node data:", error);
      }
    });

    const connections = this.getConnectionsData();

    // Separate the canvas start node from agent nodes
    const startNode = nodes.find(
      (n) => n.agentId === "start_trigger" || n.type === "start",
    );
    const agentNodes = nodes.filter(
      (n) => n.agentId !== "start_trigger" && n.type !== "start",
    );

    // Perform topological sort to determine execution order (agent nodes only)
    const sortedNodes = this.topologicalSort(agentNodes, connections);

    // Generate Sim AI format
    const simWorkflow = {
      version: "1.0",
      exportedAt: new Date().toISOString(),
      state: {
        blocks: {},
        edges: [],
        loops: {},
        parallels: {},
        metadata: {
          name: "amalia_workflow",
          description: "Workflow exported from AMALIA",
          color: "#22c55e",
          exportedAt: new Date().toISOString(),
        },
        variables: {},
      },
    };

    // Create start_trigger block — populate filePath from the canvas start node
    const startTriggerId = this.generateUUID();
    const filePathInputId = this.generateUUID();
    const inputTextId = this.generateUUID();
    const canvasFilePath = startNode?.filePath || "";

    simWorkflow.state.blocks[startTriggerId] = {
      id: startTriggerId,
      type: "start_trigger",
      name: "Start",
      position: {
        x: sortedNodes.length > 0 ? sortedNodes[0].position.x - 250 : -140,
        y: sortedNodes.length > 0 ? sortedNodes[0].position.y : -370,
      },
      enabled: true,
      horizontalHandles: true,
      advancedMode: false,
      triggerMode: false,
      height: 0,
      subBlocks: {
        inputFormat: {
          id: "inputFormat",
          type: "input-format",
          value: [
            {
              id: filePathInputId,
              name: "filePath",
              type: "string",
              value: canvasFilePath,
              collapsed: false,
            },
            {
              id: inputTextId,
              name: "inputText",
              type: "string",
              value: "",
              collapsed: false,
              description: "",
            },
          ],
        },
      },
      outputs: {
        files: {
          type: "file[]",
          description: "User uploaded files",
        },
        input: {
          type: "string",
          description: "Primary user input or message",
        },
        conversationId: {
          type: "string",
          description: "Conversation thread identifier",
        },
      },
      data: {},
      locked: false,
    };

    // Convert each agent node to Sim AI agent block
    sortedNodes.forEach((node, index) => {
      const blockId = this.generateUUID();
      const agentBlock = this.convertToSimAgentBlock(blockId, node, mcpServers);
      simWorkflow.state.blocks[blockId] = agentBlock;

      // If this is the first node, connect it to start_trigger
      if (index === 0) {
        const edgeId = this.generateUUID();
        simWorkflow.state.edges.push({
          id: edgeId,
          source: startTriggerId,
          target: blockId,
          sourceHandle: "source",
          targetHandle: "target",
          type: "default",
          data: {},
        });
      }

      // Store block ID for connection mapping
      node._simBlockId = blockId;
    });

    // Create edges based on connections
    connections.forEach((conn) => {
      const sourceNode = nodes.find(
        (n) => n.instanceId === conn.from.instanceId,
      );
      const targetNode = nodes.find((n) => n.instanceId === conn.to.instanceId);

      if (
        sourceNode &&
        targetNode &&
        sourceNode._simBlockId &&
        targetNode._simBlockId
      ) {
        const edgeId = this.generateUUID();
        simWorkflow.state.edges.push({
          id: edgeId,
          source: sourceNode._simBlockId,
          target: targetNode._simBlockId,
          sourceHandle: "source",
          targetHandle: "target",
          type: "default",
          data: {},
        });
      }
    });

    return simWorkflow;
  }

  /**
   * Convert Amalia agent to Sim AI agent block
   */
  convertToSimAgentBlock(blockId, node, mcpServers) {
    // Get MCP tools for this agent
    const agentMcpTools = this.getAgentMcpTools(node, mcpServers);

    // Build agent instruction as a user message (Sim AI uses role:"user" for block instructions)
    const systemPrompt =
      node.config?.system_prompt ||
      node.system_prompt ||
      node.config?.description ||
      node.description ||
      "You are a helpful AI assistant.";

    const messages = [
      {
        role: "user",
        content: systemPrompt,
      },
    ];

    return {
      id: blockId,
      type: "agent",
      name: node.config?.name || node.name || "Agent",
      position: {
        x: node.position.x,
        y: node.position.y,
      },
      enabled: true,
      horizontalHandles: true,
      advancedMode: false,
      triggerMode: false,
      height: 0,
      subBlocks: {
        model: {
          id: "model",
          type: "combobox",
          value: this.convertModelName(node.config?.model || node.model),
        },
        tools: {
          id: "tools",
          type: "tool-input",
          value: agentMcpTools,
        },
        apiKey: {
          id: "apiKey",
          type: "short-input",
          value: "{{OPENROUTER_API_KEY}}",
        },
        skills: {
          id: "skills",
          type: "skill-input",
          value: [],
        },
        messages: {
          id: "messages",
          type: "messages-input",
          value: messages,
        },
        maxTokens: {
          id: "maxTokens",
          type: "short-input",
          value: node.config?.max_tokens || node.max_tokens || null,
        },
        verbosity: {
          id: "verbosity",
          type: "dropdown",
          value: "",
        },
        memoryType: {
          id: "memoryType",
          type: "dropdown",
          value: "none",
        },
        temperature: {
          id: "temperature",
          type: "slider",
          value: node.config?.temperature ?? node.temperature ?? 0.7,
        },
        azureEndpoint: {
          id: "azureEndpoint",
          type: "short-input",
          value: null,
        },
        bedrockRegion: {
          id: "bedrockRegion",
          type: "short-input",
          value: null,
        },
        thinkingLevel: {
          id: "thinkingLevel",
          type: "dropdown",
          value: "",
        },
        vertexProject: {
          id: "vertexProject",
          type: "short-input",
          value: null,
        },
        conversationId: {
          id: "conversationId",
          type: "short-input",
          value: null,
        },
        responseFormat: {
          id: "responseFormat",
          type: "code",
          value: null,
        },
        vertexLocation: {
          id: "vertexLocation",
          type: "short-input",
          value: null,
        },
        azureApiVersion: {
          id: "azureApiVersion",
          type: "short-input",
          value: null,
        },
        reasoningEffort: {
          id: "reasoningEffort",
          type: "dropdown",
          value: "",
        },
        bedrockSecretKey: {
          id: "bedrockSecretKey",
          type: "short-input",
          value: null,
        },
        vertexCredential: {
          id: "vertexCredential",
          type: "oauth-input",
          value: null,
        },
        slidingWindowSize: {
          id: "slidingWindowSize",
          type: "short-input",
          value: null,
        },
        bedrockAccessKeyId: {
          id: "bedrockAccessKeyId",
          type: "short-input",
          value: null,
        },
        slidingWindowTokens: {
          id: "slidingWindowTokens",
          type: "short-input",
          value: null,
        },
      },
      outputs: {
        cost: {
          type: "json",
          description: "Cost of the API call",
        },
        model: {
          type: "string",
          description: "Model used for generation",
        },
        tokens: {
          type: "json",
          description: "Token usage statistics",
        },
        content: {
          type: "string",
          description: "Generated response content",
        },
        toolCalls: {
          type: "json",
          description: "Tool calls made",
        },
        providerTiming: {
          type: "json",
          description: "Provider timing information",
        },
      },
      data: {},
      locked: false,
    };
  }

  /**
   * MCP server ID → { url, name } mapping for Sim AI export.
   * URLs use host.docker.internal so they resolve correctly when Sim AI
   * runs inside Docker and needs to reach servers on the host.
   */
  static get MCP_SERVER_MAP() {
    return {
      "python-mathematics": {
        url: "http://host.docker.internal:8001/mcp",
        name: "Mathematics Server",
      },
      mathematics: {
        url: "http://host.docker.internal:8001/mcp",
        name: "Mathematics Server",
      },
      "data-loading": {
        url: "http://host.docker.internal:8002/mcp",
        name: "Data Loading Server",
      },
      data_loading: {
        url: "http://host.docker.internal:8002/mcp",
        name: "Data Loading Server",
      },
      "data-preparation": {
        url: "http://host.docker.internal:8003/mcp",
        name: "Data Preparation Server",
      },
      data_preparation: {
        url: "http://host.docker.internal:8003/mcp",
        name: "Data Preparation Server",
      },
      "model-training": {
        url: "http://host.docker.internal:8004/mcp",
        name: "Model Training Server",
      },
      model_training: {
        url: "http://host.docker.internal:8004/mcp",
        name: "Model Training Server",
      },
      "model-evaluation": {
        url: "http://host.docker.internal:8005/mcp",
        name: "Model Evaluation Server",
      },
      model_evaluation: {
        url: "http://host.docker.internal:8005/mcp",
        name: "Model Evaluation Server",
      },
      "feature-engineering": {
        url: "http://host.docker.internal:8006/mcp",
        name: "Feature Engineering Server",
      },
      feature_engineering: {
        url: "http://host.docker.internal:8006/mcp",
        name: "Feature Engineering Server",
      },
    };
  }

  /**
   * Get MCP tools for an agent in Sim AI format.
   *
   * Priority order:
   *   1. node.mcpTools  — structured tools set by the orchestrator / canvas converter
   *   2. node.mcp_server_ids — look up servers from the mcpServers registry
   */
  getAgentMcpTools(node, mcpServers) {
    const serverMap = ConnectionManager.MCP_SERVER_MAP;

    // --- Priority 1: use the mcpTools array stored on the canvas node ---
    // These are set by convertSimAIToCanvas → extractMcpTools and carry
    // the exact tool names chosen by the orchestrator.
    if (
      node.mcpTools &&
      Array.isArray(node.mcpTools) &&
      node.mcpTools.length > 0
    ) {
      return node.mcpTools.map((tool) => {
        const serverId = tool.serverId || tool.params?.serverId || "";
        const toolName =
          tool.toolName || tool.params?.toolName || tool.title || "";
        const serverInfo = serverMap[serverId] || {};
        const serverUrl =
          serverInfo.url ||
          tool.serverUrl ||
          tool.params?.serverUrl ||
          `http://host.docker.internal:8000/mcp`;
        const serverName =
          serverInfo.name ||
          tool.serverName ||
          tool.params?.serverName ||
          serverId;

        return {
          type: "mcp",
          title: tool.title || toolName,
          params: {
            serverId,
            toolName,
            serverUrl,
            serverName,
          },
          schema: tool.schema || {
            type: "object",
            properties: {},
            description: `${toolName} tool from ${serverName}`,
            additionalProperties: false,
          },
          toolId: `${serverId}-${toolName}`,
          isExpanded: false,
          usageControl: "auto",
        };
      });
    }

    // --- Priority 2: fall back to mcp_server_ids from the registry ---
    const tools = [];
    if (node.mcp_server_ids && Array.isArray(node.mcp_server_ids)) {
      node.mcp_server_ids.forEach((serverId) => {
        const server = mcpServers.find((s) => s.id === serverId);
        if (server) {
          if (server.tools && Array.isArray(server.tools)) {
            server.tools.forEach((tool) => {
              tools.push(this.formatMcpTool(tool, server));
            });
          } else {
            tools.push(this.createPlaceholderMcpTool(server));
          }
        }
      });
    }

    return tools;
  }

  /**
   * Format MCP tool in Sim AI structure (used when building from server registry)
   */
  formatMcpTool(tool, server) {
    const serverInfo = ConnectionManager.MCP_SERVER_MAP[server.id] || {};
    const serverUrl =
      serverInfo.url || server.url || `http://host.docker.internal:8000/mcp`;
    const serverName = serverInfo.name || server.name;
    return {
      type: "mcp",
      title: tool.name || "unnamed_tool",
      params: {
        serverId: server.id,
        toolName: tool.name,
        serverUrl,
        serverName,
        ...tool.defaultParams,
      },
      schema: tool.inputSchema || {
        type: "object",
        properties: {},
        description: tool.description || "No description available",
        additionalProperties: false,
      },
      toolId: `${server.id}-${tool.name}`,
      isExpanded: false,
      usageControl: "auto",
    };
  }

  /**
   * Create placeholder MCP tool when tool details aren't available
   */
  createPlaceholderMcpTool(server) {
    const serverInfo = ConnectionManager.MCP_SERVER_MAP[server.id] || {};
    const serverUrl =
      serverInfo.url || server.url || `http://host.docker.internal:8000/mcp`;
    const serverName = serverInfo.name || server.name;
    return {
      type: "mcp",
      title: serverName,
      params: {
        serverId: server.id,
        toolName: "placeholder",
        serverUrl,
        serverName,
      },
      schema: {
        type: "object",
        properties: {},
        description: server.description || `MCP Server: ${serverName}`,
        additionalProperties: false,
      },
      toolId: `${server.id}-placeholder`,
      isExpanded: false,
      usageControl: "auto",
    };
  }

  /**
   * Convert Amalia model name to Sim AI format
   */
  convertModelName(modelName) {
    if (!modelName) return "openrouter/openrouter/auto";

    // If already in openrouter format, return as is
    if (modelName.startsWith("openrouter/")) {
      return modelName;
    }

    // Convert common model names
    const modelMap = {
      "gpt-4o": "openai/gpt-4o",
      "gpt-4": "openai/gpt-4",
      "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
      "claude-3-opus": "anthropic/claude-3-opus",
      "claude-3-sonnet": "anthropic/claude-3-sonnet",
      "claude-3-haiku": "anthropic/claude-3-haiku",
      "gemini-pro": "google/gemini-pro",
      "gemini-2.5-flash": "google/gemini-2.5-flash",
    };

    return modelMap[modelName] || `openrouter/${modelName}`;
  }

  /**
   * Topological sort for determining execution order
   */
  topologicalSort(nodes, connections) {
    const graph = new Map();
    const inDegree = new Map();
    const nodeMap = new Map();

    // Build graph
    nodes.forEach((node) => {
      const id = node.instanceId;
      nodeMap.set(id, node);
      graph.set(id, []);
      inDegree.set(id, 0);
    });

    connections.forEach((conn) => {
      const from = conn.from.instanceId;
      const to = conn.to.instanceId;
      if (graph.has(from) && graph.has(to)) {
        graph.get(from).push(to);
        inDegree.set(to, inDegree.get(to) + 1);
      }
    });

    // Find nodes with no incoming edges
    const queue = [];
    inDegree.forEach((degree, nodeId) => {
      if (degree === 0) {
        queue.push(nodeId);
      }
    });

    // If no starting nodes, sort by position (left to right)
    if (queue.length === 0 && nodes.length > 0) {
      return [...nodes].sort((a, b) => a.position.x - b.position.x);
    }

    // Perform topological sort
    const sorted = [];
    while (queue.length > 0) {
      const nodeId = queue.shift();
      sorted.push(nodeMap.get(nodeId));

      const neighbors = graph.get(nodeId) || [];
      neighbors.forEach((neighbor) => {
        inDegree.set(neighbor, inDegree.get(neighbor) - 1);
        if (inDegree.get(neighbor) === 0) {
          queue.push(neighbor);
        }
      });
    }

    // If sorted length doesn't match, there might be cycles
    // Fall back to position-based sorting
    if (sorted.length !== nodes.length) {
      console.warn("Cycle detected in workflow, falling back to position sort");
      return [...nodes].sort((a, b) => a.position.x - b.position.x);
    }

    return sorted;
  }

  /**
   * Generate UUID for Sim AI blocks
   */
  generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  /**
   * Debug test method - creates a test connection between first two nodes
   */
  testConnection() {
    const nodes = document.querySelectorAll(".agent-node");
    if (nodes.length < 2) {
      console.error("❌ Need at least 2 nodes on canvas to test");
      return false;
    }

    const node1 = nodes[0];
    const node2 = nodes[1];

    console.log("🧪 Testing connection between:", {
      from: node1.dataset.instanceId,
      to: node2.dataset.instanceId,
    });

    // Create test connection
    const result = this.createConnection(
      node1.dataset.instanceId,
      "output",
      node2.dataset.instanceId,
      "input",
    );

    if (result) {
      console.log("✅ Test connection created! Check the canvas.");
      return true;
    }
    console.error("❌ Test connection failed");
    return false;
  }
}

export default ConnectionManager;
