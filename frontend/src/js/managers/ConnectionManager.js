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
    svg.style.pointerEvents = "none";
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
    const canvasRect = this.svgOverlay.parentElement.getBoundingClientRect();
    const portRect = port.getBoundingClientRect();

    // Calculate port center relative to canvas
    const startX = portRect.left + portRect.width / 2 - canvasRect.left;
    const startY = portRect.top + portRect.height / 2 - canvasRect.top;

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
    this.mouseMoveHandler = (e) => this.updateTempLine(e, canvasRect);
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
  updateTempLine(event, canvasRect) {
    if (!this.activeConnection) return;

    const currentX = event.clientX - canvasRect.left;
    const currentY = event.clientY - canvasRect.top;

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
    };

    // Create visual connection
    connection.element = this.drawConnection(sourceNode, targetNode);
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
  drawConnection(sourceNode, targetNode) {
    const canvasRect = this.svgOverlay.parentElement.getBoundingClientRect();
    const sourcePort = sourceNode.querySelector('[data-port="output"]');
    const targetPort = targetNode.querySelector('[data-port="input"]');

    const sourceRect = sourcePort.getBoundingClientRect();
    const targetRect = targetPort.getBoundingClientRect();

    const startX = sourceRect.left + sourceRect.width / 2 - canvasRect.left;
    const startY = sourceRect.top + sourceRect.height / 2 - canvasRect.top;
    const endX = targetRect.left + targetRect.width / 2 - canvasRect.left;
    const endY = targetRect.top + targetRect.height / 2 - canvasRect.top;

    const path = this.createConnectionPath(startX, startY, endX, endY, false);
    this.svgOverlay.appendChild(path);

    return path;
  }

  /**
   * Create an SVG path element for a connection
   */
  createConnectionPath(x1, y1, x2, y2, isTemporary = false) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    const d = this.calculateBezierPath(x1, y1, x2, y2);

    path.setAttribute("d", d);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", isTemporary ? "#888888" : "#1a1a1a");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("stroke-dasharray", isTemporary ? "5,5" : "none");
    path.setAttribute("opacity", isTemporary ? "0.5" : "1");
    path.style.pointerEvents = "none";

    return path;
  }

  /**
   * Update an existing path element
   */
  updateConnectionPath(path, x1, y1, x2, y2) {
    const d = this.calculateBezierPath(x1, y1, x2, y2);
    path.setAttribute("d", d);
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
        connection.element = this.drawConnection(sourceNode, targetNode);
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
              this.createConnection(newFromId, "output", newToId, "input");
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
