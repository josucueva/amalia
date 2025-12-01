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

    // Get node position in original canvas coordinates
    const nodeX = Number.parseFloat(
      sourceNode.dataset.originalX || sourceNode.style.left || 0
    );
    const nodeY = Number.parseFloat(
      sourceNode.dataset.originalY || sourceNode.style.top || 0
    );
    const nodeWidth = sourceNode.offsetWidth;
    const nodeHeight = sourceNode.offsetHeight;

    // Calculate port center in canvas coordinates
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
      sourceInstanceId
    );
  }

  /**
   * Update temporary connection line as mouse moves
   */
  updateTempLine(event) {
    if (!this.activeConnection) return;

    // Get canvas element and its bounding rect
    const canvasContent = this.svgOverlay.parentElement;
    const canvasRect = canvasContent.getBoundingClientRect();

    // Get current pan/zoom state from the SVG overlay transform
    // The transform is set by main.js in format: translate(x, y) scale(s)
    const transform = this.svgOverlay.style.transform || "";
    let panX = 0,
      panY = 0,
      scale = 1;

    // Parse translate values
    const translateMatch = transform.match(
      /translate\(([^,]+)px,\s*([^)]+)px\)/
    );
    if (translateMatch) {
      panX = Number.parseFloat(translateMatch[1]) || 0;
      panY = Number.parseFloat(translateMatch[2]) || 0;
    }

    // Parse scale value
    const scaleMatch = transform.match(/scale\(([^)]+)\)/);
    if (scaleMatch) {
      scale = Number.parseFloat(scaleMatch[1]) || 1;
    }

    // Convert screen coordinates to canvas coordinates
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
      true
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
        targetPortType
      )
    ) {
      this.createConnection(
        this.activeConnection.sourceInstanceId,
        this.activeConnection.sourcePortType,
        targetInstanceId,
        targetPortType
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
    targetPortType
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
    targetPortType
  ) {
    // Normalize connection direction (output -> input)
    const fromInstanceId =
      sourcePortType === "output" ? sourceInstanceId : targetInstanceId;
    const toInstanceId =
      sourcePortType === "output" ? targetInstanceId : sourceInstanceId;

    const connectionId = this.getConnectionId(fromInstanceId, toInstanceId);

    // Get node elements
    const sourceNode = document.querySelector(
      `[data-instance-id="${fromInstanceId}"]`
    );
    const targetNode = document.querySelector(
      `[data-instance-id="${toInstanceId}"]`
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
      connectionId
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
    // Get node positions in original canvas coordinates (not transformed)
    const sourceX = Number.parseFloat(
      sourceNode.dataset.originalX || sourceNode.style.left || 0
    );
    const sourceY = Number.parseFloat(
      sourceNode.dataset.originalY || sourceNode.style.top || 0
    );
    const targetX = Number.parseFloat(
      targetNode.dataset.originalX || targetNode.style.left || 0
    );
    const targetY = Number.parseFloat(
      targetNode.dataset.originalY || targetNode.style.top || 0
    );

    // Get port offsets within the node (approximate - ports are at edges)
    const nodeWidth = sourceNode.offsetWidth;
    const nodeHeight = sourceNode.offsetHeight;

    // Output port is on the right edge, input port is on the left edge
    const startX = sourceX + nodeWidth; // Right edge
    const startY = sourceY + nodeHeight / 2; // Middle height
    const endX = targetX; // Left edge
    const endY = targetY + nodeHeight / 2; // Middle height

    const path = this.createConnectionPath(
      startX,
      startY,
      endX,
      endY,
      false,
      connectionId
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
    connectionId = null
  ) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const d = this.calculateBezierPath(x1, y1, x2, y2);

    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", isTemporary ? "#888888" : "#1a1a1a");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("stroke-dasharray", isTemporary ? "5,5" : "none");
    path.setAttribute(
      "opacity",
      this.enabled ? (isTemporary ? "0.5" : "1") : "0.3"
    );
    path.style.pointerEvents = isTemporary ? "none" : "stroke";
    path.style.cursor = isTemporary ? "default" : "pointer";
    path.style.strokeWidth = "12"; // Wider invisible stroke for easier clicking
    path.style.stroke = "transparent";

    // Create visible path on top
    const visiblePath = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "path"
    );
    visiblePath.setAttribute("d", d);
    visiblePath.setAttribute("fill", "none");
    visiblePath.setAttribute("stroke", isTemporary ? "#888888" : "#1a1a1a");
    visiblePath.setAttribute("stroke-width", "2");
    visiblePath.setAttribute(
      "stroke-dasharray",
      isTemporary ? "5,5" : this.enabled ? "none" : "5,5"
    );
    visiblePath.setAttribute(
      "opacity",
      this.enabled ? (isTemporary ? "0.5" : "1") : "0.3"
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
        visiblePath.setAttribute("stroke", isEnabled ? "#d3d3ff" : "#9ca3af");
        visiblePath.setAttribute("stroke-width", "3");
      });

      path.addEventListener("mouseleave", () => {
        // Don't restore if this connection is currently selected
        if (this.selectedConnectionId === connectionId) {
          return;
        }
        const connection = this.connections.get(connectionId);
        const isEnabled = connection && connection.enabled !== false;
        visiblePath.setAttribute("stroke", isEnabled ? "#1a1a1a" : "#9ca3af");
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
   * Calculate a smooth bezier curve path
   */
  calculateBezierPath(x1, y1, x2, y2) {
    const dx = Math.abs(x2 - x1);
    const controlPointOffset = Math.min(dx * 0.5, 100);

    const cx1 = x1 + controlPointOffset;
    const cy1 = y1;
    const cx2 = x2 - controlPointOffset;
    const cy2 = y2;

    return `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;
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
      visiblePath.setAttribute("stroke", "#d3d3ff");
      visiblePath.setAttribute("stroke-width", "3");
      visiblePath.setAttribute("opacity", "1");
    } else {
      // Restore normal state
      const isEnabled = connection.enabled !== false;
      visiblePath.setAttribute("stroke", isEnabled ? "#1a1a1a" : "#9ca3af");
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
        conn.from.instanceId === instanceId || conn.to.instanceId === instanceId
    );

    connectionsToUpdate.forEach((connection) => {
      const sourceNode = document.querySelector(
        `[data-instance-id="${connection.from.instanceId}"]`
      );
      const targetNode = document.querySelector(
        `[data-instance-id="${connection.to.instanceId}"]`
      );

      if (sourceNode && targetNode && connection.element) {
        // Remove old path
        connection.element.remove();
        // Draw new path
        connection.element = this.drawConnection(
          sourceNode,
          targetNode,
          connection.id
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
        conn.from.instanceId === instanceId || conn.to.instanceId === instanceId
    );

    connectionsToRemove.forEach(([connectionId, _]) => {
      this.removeConnection(connectionId);
    });

    console.log(
      `✓ Removed ${connectionsToRemove.length} connections for node ${instanceId}`
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
        conn.from.instanceId === instanceId || conn.to.instanceId === instanceId
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
      isVisuallyEnabled ? "none" : "5,5"
    );

    // Change color if individually disabled (even if globally enabled)
    if (this.enabled && !connection.enabled) {
      visiblePath.setAttribute("stroke", "#9ca3af"); // Gray for disabled
    } else {
      visiblePath.setAttribute("stroke", "#1a1a1a"); // Black for normal
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
        nodeData.position.y
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
              `[data-instance-id="${newFromId}"]`
            );
            const toNode = document.querySelector(
              `[data-instance-id="${newToId}"]`
            );

            if (fromNode && toNode) {
              const connection = this.createConnection(
                newFromId,
                "output",
                newToId,
                "input"
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
      "input"
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
