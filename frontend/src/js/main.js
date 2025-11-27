/**
 * Main Application Entry Point
 *
 * Canvas Grid System:
 * - 20px grid (matches CSS background pattern)
 * - All node placements snap to grid for clean alignment
 * - Dragging uses threshold detection and smooth grid snapping
 * - Boundary checking ensures nodes stay within canvas
 */
import api from "./api.js";
import Chat from "./components/Chat.js";
import FileUpload from "./components/FileUpload.js";
import AgentConfig from "./components/AgentConfig.js";
import ConnectionManager from "./managers/ConnectionManager.js";
import { showToast } from "./utils/helpers.js";
import config from "./config.js";

const { API_BASE_URL } = config;

class App {
  // Component references
  chat = null;
  fileUpload = null;
  agentConfig = null;
  connectionManager = null;
  uploadedFile = null;

  // State
  canvasMode = false;
  showHiddenAgents = false;
  menuCloseListener = null;

  // Canvas drop listeners (to prevent duplicates)
  canvasDropListeners = {
    dragover: null,
    drop: null,
  };

  // Pipeline execution state
  isExecuting = false;
  executionPaused = false;
  executionCancelled = false;
  currentExecutingNode = null;
  executionResults = new Map();
  executionOrder = [];

  // Canvas grid configuration
  canvasConfig = {
    gridSize: 20,
    snapToGrid: true,
    dragThreshold: 5,
  };

  async init() {
    console.log("🚀 Initializing AMALIA...");

    // Check backend health
    try {
      const health = await api.healthCheck();
      console.log("✓ Backend connection established:", health);
    } catch (error) {
      console.error("✗ Backend connection failed:", error);
      showToast("Unable to connect to backend server", "error");
    }

    // Initialize components
    this.chat = new Chat();
    this.fileUpload = new FileUpload();
    this.agentConfig = new AgentConfig();

    // Setup canvas mode toggle
    const canvasBtn = document.getElementById("canvas-btn");
    if (canvasBtn) {
      canvasBtn.addEventListener("click", () => {
        this.toggleCanvasMode();
      });
    }

    // Setup run button
    const runBtn = document.getElementById("run-btn");
    if (runBtn) {
      runBtn.addEventListener("click", () => {
        this.runPipeline();
      });
    }

    // Setup agents button (opens agent modal)
    const agentsBtn = document.getElementById("agents-btn");
    if (agentsBtn) {
      agentsBtn.addEventListener("click", () => {
        this.agentConfig.openModal();
      });
    }

    // Setup create agent button in canvas sidebar
    const createAgentBtn = document.getElementById("create-agent-btn");
    if (createAgentBtn) {
      createAgentBtn.addEventListener("click", () => {
        this.agentConfig.openModal();
      });
    }

    // Setup inline file upload
    const uploadInlineBtn = document.getElementById("upload-inline-btn");
    const fileInputInline = document.getElementById("file-input-inline");

    if (uploadInlineBtn && fileInputInline) {
      uploadInlineBtn.addEventListener("click", () => {
        fileInputInline.click();
      });

      fileInputInline.addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (file) {
          this.handleFileUpload(file);
        }
      });
    }

    // Setup configure interaction agent button
    const configureInteractionAgentBtn = document.getElementById(
      "configure-interaction-agent-btn"
    );
    if (configureInteractionAgentBtn) {
      configureInteractionAgentBtn.addEventListener("click", async () => {
        await this.openInteractionAgentConfig();
      });
    }

    // Setup canvas control buttons
    const saveCanvasBtn = document.getElementById("save-canvas-btn");
    if (saveCanvasBtn) {
      saveCanvasBtn.addEventListener("click", () => {
        this.saveCanvasState();
      });
    }

    const loadCanvasBtn = document.getElementById("load-canvas-btn");
    if (loadCanvasBtn) {
      loadCanvasBtn.addEventListener("click", () => {
        this.loadCanvasState();
      });
    }

    const clearCanvasBtn = document.getElementById("clear-canvas-btn");
    if (clearCanvasBtn) {
      clearCanvasBtn.addEventListener("click", () => {
        if (
          confirm(
            "Are you sure you want to clear the canvas? This cannot be undone."
          )
        ) {
          this.clearCanvas();
        }
      });
    }

    // Setup keyboard shortcuts
    this.setupKeyboardShortcuts();

    console.log("✓ Application initialized successfully");
  }

  handleFileUpload(file) {
    if (!file.name.endsWith(".csv")) {
      showToast("Please upload a CSV file", "error");
      return;
    }

    const filePreview = document.getElementById("file-preview");
    const fileName = filePreview.querySelector(".file-name");

    fileName.textContent = file.name;
    filePreview.style.display = "flex";

    // Store file for later use
    this.uploadedFile = file;

    showToast(`File "${file.name}" ready to upload`, "info");
  }

  async openInteractionAgentConfig() {
    try {
      // Fetch agents including hidden ones since interaction_agent is hidden
      const agents = await api.getAgents(true);
      const interactionAgent = agents.find(
        (agent) => agent.config.name === "interaction_agent"
      );

      if (interactionAgent) {
        this.agentConfig.openModal(interactionAgent);
      } else {
        showToast("Interaction agent not found", "error");
      }
    } catch (error) {
      console.error("Error loading interaction agent:", error);
      showToast("Failed to load interaction agent", "error");
    }
  }

  /**
   * Setup keyboard shortcuts for canvas mode
   */
  setupKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      // Ctrl+Shift+H: Toggle hidden agents visibility (only in canvas mode)
      if (e.ctrlKey && e.shiftKey && e.key === "H") {
        // Only work in canvas mode - don't prevent default in chat mode
        if (this.canvasMode) {
          e.preventDefault();
          this.showHiddenAgents = !this.showHiddenAgents;
          this.loadCanvasAgents();

          // Show feedback toast
          const status = this.showHiddenAgents ? "shown" : "hidden";
          showToast(`Hidden agents ${status}`, "info");
        }
      }
    });
  }

  async runPipeline() {
    if (this.isExecuting) {
      console.warn("Pipeline already executing");
      return;
    }

    // Get all nodes and connections
    const nodes = Array.from(document.querySelectorAll(".agent-node"));
    const connections = this.connectionManager.getConnectionsData();

    // Validation
    if (nodes.length === 0) {
      showToast("No agents on canvas to execute", "warning");
      return;
    }

    // Calculate execution order (topological sort)
    this.executionOrder = this.calculateExecutionOrder(nodes, connections);

    if (!this.executionOrder) {
      showToast("Cannot execute: Circular dependencies detected", "error");
      return;
    }

    // Reset state
    this.isExecuting = true;
    this.executionPaused = false;
    this.executionCancelled = false;
    this.executionResults.clear();

    showToast(`Executing ${this.executionOrder.length} agents...`, "info");

    // Execute sequentially
    await this.executeSequentialPipeline();

    // Cleanup
    this.isExecuting = false;
    this.currentExecutingNode = null;

    if (this.executionCancelled) {
      showToast("Pipeline execution cancelled", "warning");
    } else {
      showToast("Pipeline execution completed", "success");
    }
  }

  calculateExecutionOrder(nodes, connections) {
    // Build adjacency list and in-degree map
    const graph = new Map(); // instanceId -> [dependent instanceIds]
    const inDegree = new Map(); // instanceId -> number of dependencies
    const nodeMap = new Map(); // instanceId -> node element

    // Initialize
    for (const node of nodes) {
      const instanceId = node.dataset.instanceId;
      graph.set(instanceId, []);
      inDegree.set(instanceId, 0);
      nodeMap.set(instanceId, node);
    }

    // Build graph from connections
    for (const conn of connections) {
      const fromId = conn.from.instanceId;
      const toId = conn.to.instanceId;

      if (graph.has(fromId) && graph.has(toId)) {
        graph.get(fromId).push(toId);
        inDegree.set(toId, inDegree.get(toId) + 1);
      }
    }

    // Topological sort (Kahn's algorithm)
    const queue = [];
    const order = [];

    // Start with nodes that have no dependencies
    for (const [instanceId, degree] of inDegree) {
      if (degree === 0) {
        queue.push(instanceId);
      }
    }

    while (queue.length > 0) {
      const current = queue.shift();
      order.push(nodeMap.get(current));

      // Process dependents
      for (const dependent of graph.get(current)) {
        inDegree.set(dependent, inDegree.get(dependent) - 1);
        if (inDegree.get(dependent) === 0) {
          queue.push(dependent);
        }
      }
    }

    // Check for cycles
    if (order.length !== nodes.length) {
      console.error("Circular dependency detected in pipeline");
      return null;
    }

    return order;
  }

  async executeSequentialPipeline() {
    for (const node of this.executionOrder) {
      // Check for cancellation
      if (this.executionCancelled) {
        this.setNodeExecutionState(node, "cancelled");
        continue;
      }

      // Wait if paused
      while (this.executionPaused && !this.executionCancelled) {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      if (this.executionCancelled) {
        this.setNodeExecutionState(node, "cancelled");
        continue;
      }

      // Execute this node
      this.currentExecutingNode = node;
      this.setNodeExecutionState(node, "running");

      try {
        const result = await this.executeNode(node);
        this.executionResults.set(node.dataset.instanceId, result);
        this.setNodeExecutionState(node, "completed");
      } catch (error) {
        console.error(
          `Error executing node ${node.dataset.instanceId}:`,
          error
        );
        this.executionResults.set(node.dataset.instanceId, {
          error: error.message,
        });
        this.setNodeExecutionState(node, "error");

        // Stop execution on error
        showToast(`Execution failed: ${error.message}`, "error");
        this.executionCancelled = true;
      }
    }
  }

  async executeNode(node) {
    const instanceId = node.dataset.instanceId;
    const agentId = node.dataset.agentId; // This is the agent ID (e.g., "data_loader")

    // Get input from connected nodes
    const connections = this.connectionManager.getConnectionsData();
    const inputs = connections
      .filter((conn) => conn.to.instanceId === instanceId)
      .map((conn) => this.executionResults.get(conn.from.instanceId))
      .filter((result) => result !== undefined);

    // Call backend API to execute agent
    try {
      const response = await fetch(`${API_BASE_URL}/api/canvas/execute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          instanceId,
          agentType: agentId, // Send agentId as agentType
          inputs,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to execute agent: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      return result;
    } catch (error) {
      console.error("Error executing node:", error);
      throw error;
    }
  }

  setNodeExecutionState(node, state) {
    // Remove all state classes
    node.classList.remove(
      "node-running",
      "node-completed",
      "node-error",
      "node-cancelled",
      "node-loading"
    );

    // Add new state class
    if (state === "running") {
      node.classList.add("node-running", "node-loading");
    } else if (state === "completed") {
      node.classList.add("node-completed");
    } else if (state === "error") {
      node.classList.add("node-error");
    } else if (state === "cancelled") {
      node.classList.add("node-cancelled");
    }
  }

  pauseExecution() {
    this.executionPaused = true;
    showToast("Execution paused", "info");
  }

  resumeExecution() {
    this.executionPaused = false;
    showToast("Execution resumed", "info");
  }

  cancelExecution() {
    this.executionCancelled = true;
    showToast("Cancelling execution...", "warning");
  }

  showExecutionLogs(instanceId) {
    const result = this.executionResults.get(instanceId);

    if (!result) {
      showToast("No execution logs available for this agent", "info");
      return;
    }

    // Create and show logs modal
    const modal = document.createElement("div");
    modal.className = "modal-overlay";
    modal.id = "execution-logs-modal";

    modal.innerHTML = `
      <div class="modal-content execution-logs-modal-content">
        <div class="modal-header">
          <h2>Execution Logs</h2>
          <button class="modal-close" onclick="document.getElementById('execution-logs-modal').remove()">
            <i data-lucide="x"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="execution-logs-info">
            <div class="log-field">
              <label>Instance ID:</label>
              <span>${result.instanceId}</span>
            </div>
            <div class="log-field">
              <label>Agent Type:</label>
              <span>${result.agentType}</span>
            </div>
            <div class="log-field">
              <label>Timestamp:</label>
              <span>${new Date(result.timestamp).toLocaleString()}</span>
            </div>
            <div class="log-field">
              <label>Input Count:</label>
              <span>${result.inputs}</span>
            </div>
          </div>
          <div class="execution-logs-output">
            <h3>Output</h3>
            <pre>${
              result.error
                ? `ERROR: ${result.error}`
                : JSON.stringify(result.output, null, 2)
            }</pre>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="document.getElementById('execution-logs-modal').remove()">Close</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Initialize Lucide icons
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    // Close on overlay click
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }

  toggleCanvasMode() {
    this.canvasMode = !this.canvasMode;
    this.updateUIForMode();

    if (this.canvasMode) {
      this.initializeCanvasMode();
    }
  }

  updateUIForMode() {
    const overlay = document.getElementById("canvas-overlay");
    const chatContainer = document.querySelector(".chat-container");
    const btnText = document.getElementById("canvas-btn-text");
    const agentsBtn = document.getElementById("agents-btn");

    if (this.canvasMode) {
      overlay?.classList.add("active");
      if (chatContainer) chatContainer.style.display = "none";
      if (btnText) btnText.textContent = "Chat Mode";
      if (agentsBtn) agentsBtn.style.display = "inline-block";
    } else {
      overlay?.classList.remove("active");
      if (chatContainer) chatContainer.style.display = "flex";
      if (btnText) btnText.textContent = "Canvas Mode";
      if (agentsBtn) agentsBtn.style.display = "none";
    }
  }

  initializeCanvasMode() {
    this.ensureConnectionManager();
    this.loadCanvasAgents();
    this.setupCanvasDrop();
    this.loadPendingPipeline();
  }

  ensureConnectionManager() {
    if (this.connectionManager) return;

    console.log("🔧 Initializing ConnectionManager...");
    this.connectionManager = new ConnectionManager();
    const canvasContent = document.getElementById("canvas-content");

    if (canvasContent) {
      this.connectionManager.initialize(canvasContent);
      console.log("✅ ConnectionManager initialized");
      globalThis.connectionManager = this.connectionManager;
    }
  }

  loadPendingPipeline() {
    const pendingPipeline = sessionStorage.getItem("pendingPipeline");
    if (!pendingPipeline) return;

    try {
      const pipelineData = JSON.parse(pendingPipeline);
      sessionStorage.removeItem("pendingPipeline");
      setTimeout(() => {
        this.createPipelineFromData(
          pipelineData.nodes,
          pipelineData.connections
        );
      }, 500);
    } catch (error) {
      console.error("Error loading pending pipeline:", error);
    }
  }

  async loadCanvasAgents() {
    try {
      // Fetch agents with include_hidden parameter
      const agents = await api.getAgents(this.showHiddenAgents);
      const canvasAgentList = document.getElementById("canvas-agent-list");

      if (!canvasAgentList) {
        console.error("Canvas agent list not found");
        return;
      }

      canvasAgentList.innerHTML = "";

      console.log("Loading agents:", agents);

      if (agents && agents.length > 0) {
        for (const agent of agents) {
          const listItem = this.createAgentListItem(agent);
          canvasAgentList.appendChild(listItem);
        }

        // Initialize Lucide icons after all items are added
        if (globalThis.lucide) {
          globalThis.lucide.createIcons();
        }
      } else {
        canvasAgentList.innerHTML =
          '<div style="color: var(--text-secondary); font-size: var(--font-size-xs); text-align: center; padding: var(--spacing-lg) 0;">No agents configured</div>';
      }
    } catch (error) {
      console.error("Error loading canvas agents:", error);
      const canvasAgentList = document.getElementById("canvas-agent-list");
      if (canvasAgentList) {
        canvasAgentList.innerHTML =
          '<div style="color: #dc2626; font-size: var(--font-size-xs); text-align: center; padding: var(--spacing-lg) 0;">Error loading agents</div>';
      }
    }
  }

  createAgentNode(agent, x, y) {
    // Snap position to grid
    const snappedX = this.snapToGrid(x, this.canvasConfig.gridSize);
    const snappedY = this.snapToGrid(y, this.canvasConfig.gridSize);

    // Create a unique instance of the agent for this node
    const instanceId = `instance_${Date.now()}_${Math.random()
      .toString(36)
      .substring(2, 11)}`;
    const agentInstance = {
      ...agent,
      instanceId: instanceId,
      position: { x: snappedX, y: snappedY },
    };

    const node = document.createElement("div");
    node.className = "agent-node";
    node.dataset.instanceId = instanceId;
    node.dataset.agentId = agent.id; // Keep reference to template agent
    node.dataset.agentData = JSON.stringify(agentInstance);
    node.style.left = `${snappedX}px`;
    node.style.top = `${snappedY}px`;

    // Count MCP tools
    const mcpServers = agent.config.mcp_servers || {};
    const toolCount = Object.keys(mcpServers).length;

    node.innerHTML = `
      <div class="agent-node-header">
        ${
          agent.config.icon
            ? `<i data-lucide="${agent.config.icon}" class="agent-node-icon"></i>`
            : `<span class="agent-node-name">${agent.config.name}</span>`
        }
        ${
          toolCount > 0
            ? `<span class="tool-count-badge">${toolCount}</span>`
            : ""
        }
      </div>
      <div class="agent-node-input" data-port="input" title="Input connection"></div>
      <div class="agent-node-output" data-port="output" title="Output connection"></div>
    `;

    // Initialize Lucide icons
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    // Make draggable
    this.makeDraggableNode(node);

    // Add connection port handlers
    this.setupConnectionPorts(node);

    // Add click handler for action menu - pass instance data
    node.addEventListener("click", (e) => {
      // Don't show menu if clicking on ports
      if (e.target.dataset.port) return;

      // Don't show menu if node was just dragged
      if (node._justDragged) {
        node._justDragged = false;
        return;
      }

      // Get fresh instance data from node to ensure we have latest state
      const currentInstance = JSON.parse(node.dataset.agentData);
      this.showNodeActionMenu(node, currentInstance);
    });

    return node;
  }

  createAgentListItem(agent) {
    // Check if agent is hidden (system agent)
    const isHidden = agent.config.metadata?.is_hidden === true;

    const item = document.createElement("div");
    item.className = "canvas-agent-item";
    // Hidden agents cannot be dragged/instantiated
    item.draggable = !isHidden;
    item.dataset.agentId = agent.id;
    item.dataset.agentData = JSON.stringify(agent);

    // Add visual indicator for hidden agents
    if (isHidden) {
      item.classList.add("hidden-agent");
    }

    item.innerHTML = `
      <div class="canvas-agent-item-content">
        <div class="canvas-agent-item-name">
          ${
            // Hidden agents don't show icons
            !isHidden && agent.config.icon
              ? `<i data-lucide="${agent.config.icon}" style="width: 16px; height: 16px; margin-right: 8px;"></i>`
              : ""
          }${agent.config.name}
        </div>
        <div class="canvas-agent-item-desc">${agent.config.description}</div>
        <div class="canvas-agent-item-actions">
          <button class="canvas-agent-action-btn edit-btn">[ EDIT ]</button>
          ${
            // Hidden agents cannot be deleted
            isHidden
              ? ""
              : '<button class="canvas-agent-action-btn delete-btn">[ DELETE ]</button>'
          }
        </div>
      </div>
    `;

    // Initialize Lucide icons
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    // Drag handlers - only for non-hidden agents
    if (!isHidden) {
      item.addEventListener("dragstart", (e) => {
        e.dataTransfer.effectAllowed = "copy";
        e.dataTransfer.setData("application/json", item.dataset.agentData);
        item.classList.add("dragging");
      });

      item.addEventListener("dragend", (e) => {
        item.classList.remove("dragging");
      });
    }

    // Edit button handler
    const editBtn = item.querySelector(".edit-btn");
    editBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.agentConfig.openModal(agent);
    });

    // Delete button handler - only for non-hidden agents
    if (!isHidden) {
      const deleteBtn = item.querySelector(".delete-btn");
      if (deleteBtn) {
        deleteBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.agentConfig.deleteAgent(agent.id, agent.config.name);
        });
      }
    }

    return item;
  }

  /**
   * Snap coordinate to grid
   * @param {number} value - The coordinate value to snap
   * @param {number} gridSize - The grid size in pixels
   * @returns {number} Snapped coordinate
   */
  snapToGrid(value, gridSize) {
    return Math.round(value / gridSize) * gridSize;
  }

  /**
   * Make a node draggable with grid snapping support
   * Implements best practices: event delegation, threshold detection, grid alignment
   *
   * Click vs Drag Detection:
   * - Click: mousedown -> mouseup within 5px threshold -> shows menu
   * - Drag: mousedown -> move > 5px -> mousemove updates position -> mouseup sets flag
   * - The _justDragged flag prevents click handler from firing after drag
   *
   * @param {HTMLElement} element - The node element to make draggable
   */
  makeDraggableNode(element) {
    const header = element.querySelector(".agent-node-header");
    const dragHandle = header || element;

    // Drag state (encapsulated in closure)
    let isDragging = false;
    let hasMoved = false;
    let startX = 0;
    let startY = 0;
    let initialLeft = 0;
    let initialTop = 0;

    const { gridSize, snapToGrid, dragThreshold } = this.canvasConfig;

    dragHandle.addEventListener("mousedown", (e) => {
      // Don't drag if clicking on port or action buttons
      if (e.target.dataset.port || e.target.closest(".agent-node-menu-btn"))
        return;

      // Close any open menus when starting to drag
      this.hideNodeActionMenu();

      // Store initial state
      isDragging = true;
      hasMoved = false;
      startX = e.clientX;
      startY = e.clientY;

      // Get current position
      const currentLeft = Number.parseInt(element.style.left, 10) || 0;
      const currentTop = Number.parseInt(element.style.top, 10) || 0;
      initialLeft = currentLeft;
      initialTop = currentTop;

      // Visual feedback
      element.style.cursor = "grabbing";
      element.style.zIndex = "1000"; // Bring to front while dragging

      // Bind events to document for better tracking
      document.addEventListener("mousemove", drag);
      document.addEventListener("mouseup", dragEnd);

      e.preventDefault();
      e.stopPropagation();
    });

    const drag = (e) => {
      if (!isDragging) return;

      e.preventDefault();

      // Calculate movement delta
      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;

      // Check if we've moved beyond threshold
      if (
        !hasMoved &&
        (Math.abs(deltaX) > dragThreshold || Math.abs(deltaY) > dragThreshold)
      ) {
        hasMoved = true;
      }

      if (hasMoved) {
        // Calculate new position
        let newX = initialLeft + deltaX;
        let newY = initialTop + deltaY;

        // Apply grid snapping
        if (snapToGrid) {
          newX = this.snapToGrid(newX, gridSize);
          newY = this.snapToGrid(newY, gridSize);
        }

        // Ensure node stays within canvas bounds
        const parent = element.parentElement;
        if (parent) {
          const maxX = parent.clientWidth - element.offsetWidth;
          const maxY = parent.clientHeight - element.offsetHeight;

          newX = Math.max(0, Math.min(newX, maxX));
          newY = Math.max(0, Math.min(newY, maxY));
        }

        // Apply new position
        element.style.left = newX + "px";
        element.style.top = newY + "px";

        // Update connections in real-time
        if (this.connectionManager) {
          const instanceId = element.dataset.instanceId;
          this.connectionManager.updateConnectionPositions(instanceId);
        }
      }
    };

    const dragEnd = (e) => {
      // Clean up event listeners first
      document.removeEventListener("mousemove", drag);
      document.removeEventListener("mouseup", dragEnd);

      // Reset visual state
      element.style.cursor = "move";
      element.style.zIndex = "2"; // Reset z-index

      // Set flag to prevent click event if node was actually dragged
      if (hasMoved) {
        element._justDragged = true;
        // Clear the flag after a short delay to allow future clicks
        setTimeout(() => {
          element._justDragged = false;
        }, 100);
      }

      // Reset drag state
      isDragging = false;
      hasMoved = false;
    };
  }

  setupCanvasDrop() {
    const canvasContent = document.getElementById("canvas-content");
    if (!canvasContent) return;

    // Remove existing listeners if any to prevent duplicates
    if (this.canvasDropListeners.dragover) {
      canvasContent.removeEventListener(
        "dragover",
        this.canvasDropListeners.dragover
      );
    }
    if (this.canvasDropListeners.drop) {
      canvasContent.removeEventListener("drop", this.canvasDropListeners.drop);
    }

    // Create and store new listeners
    this.canvasDropListeners.dragover = (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    };

    this.canvasDropListeners.drop = (e) => {
      e.preventDefault();
      e.stopPropagation();

      const agentData = JSON.parse(e.dataTransfer.getData("application/json"));

      // Get drop position relative to canvas
      const rect = canvasContent.getBoundingClientRect();
      let x = e.clientX - rect.left;
      let y = e.clientY - rect.top;

      // Offset to center the node on cursor (approximate node size)
      const nodeHalfWidth = 50; // Half of typical node width
      const nodeHalfHeight = 40; // Half of typical node height
      x = Math.max(0, x - nodeHalfWidth);
      y = Math.max(0, y - nodeHalfHeight);

      // Create node at drop position (will be snapped to grid inside createAgentNode)
      const node = this.createAgentNode(agentData, x, y);
      canvasContent.appendChild(node);

      // Initialize Lucide icons after appending to DOM
      if (globalThis.lucide) {
        globalThis.lucide.createIcons();
      }
    };

    // Add listeners
    canvasContent.addEventListener(
      "dragover",
      this.canvasDropListeners.dragover
    );
    canvasContent.addEventListener("drop", this.canvasDropListeners.drop);
  }

  setupConnectionPorts(node) {
    const outputPort = node.querySelector('[data-port="output"]');
    const inputPort = node.querySelector('[data-port="input"]');

    if (outputPort) {
      outputPort.addEventListener("click", (e) => {
        e.stopPropagation();
        if (this.connectionManager) {
          this.connectionManager.handlePortClick(node, "output", e);
        }
      });
    }

    if (inputPort) {
      inputPort.addEventListener("click", (e) => {
        e.stopPropagation();
        if (this.connectionManager) {
          this.connectionManager.handlePortClick(node, "input", e);
        }
      });
    }
  }

  showNodeActionMenu(node, agentInstance) {
    // Remove any existing menus
    this.hideNodeActionMenu();

    const menu = document.createElement("div");
    menu.className = "agent-node-menu";
    menu.id = "active-node-menu";

    // Check if this node is currently executing
    const instanceId = node.dataset.instanceId;
    const isExecuting = this.currentExecutingNode === node;

    if (isExecuting) {
      // Show execution controls
      menu.innerHTML = `
        <button class="agent-node-menu-btn" data-action="pause">${
          this.executionPaused ? "RESUME" : "PAUSE"
        }</button>
        <button class="agent-node-menu-btn" data-action="cancel">CANCEL</button>
        <button class="agent-node-menu-btn" data-action="logs">LOGS</button>
      `;
    } else {
      // Show normal controls
      menu.innerHTML = `
        <button class="agent-node-menu-btn" data-action="edit">EDIT</button>
        <button class="agent-node-menu-btn" data-action="duplicate">DUPLICATE</button>
        <button class="agent-node-menu-btn delete" data-action="delete">DELETE</button>
      `;
    }

    // Position menu above the node
    const nodeRect = node.getBoundingClientRect();
    const parentRect = node.parentElement.getBoundingClientRect();
    menu.style.left = nodeRect.left - parentRect.left + "px";
    menu.style.bottom = parentRect.bottom - nodeRect.top + 8 + "px";

    node.parentElement.appendChild(menu);

    // Add event listeners based on menu type
    if (isExecuting) {
      const pauseBtn = menu.querySelector('[data-action="pause"]');
      if (pauseBtn) {
        pauseBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          if (this.executionPaused) {
            this.resumeExecution();
          } else {
            this.pauseExecution();
          }
          this.hideNodeActionMenu();
        });
      }

      const cancelBtn = menu.querySelector('[data-action="cancel"]');
      if (cancelBtn) {
        cancelBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.cancelExecution();
          this.hideNodeActionMenu();
        });
      }

      const logsBtn = menu.querySelector('[data-action="logs"]');
      if (logsBtn) {
        logsBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.showExecutionLogs(instanceId);
          this.hideNodeActionMenu();
        });
      }
    } else {
      // Normal menu event listeners
      menu
        .querySelector('[data-action="edit"]')
        .addEventListener("click", (e) => {
          e.stopPropagation();
          // Open modal with instance data and update callback
          this.agentConfig.openModal(agentInstance, (updatedConfig) => {
            // Update the instance data in the node
            const updatedInstance = {
              ...agentInstance,
              config: updatedConfig,
            };
            node.dataset.agentData = JSON.stringify(updatedInstance);
            // Update the displayed name and icon if changed
            const header = node.querySelector(".agent-node-header");
            if (header) {
              if (updatedConfig.icon) {
                header.innerHTML = `<i data-lucide="${updatedConfig.icon}" class="agent-node-icon"></i>`;
              } else {
                header.innerHTML = `<span class="agent-node-name">${updatedConfig.name}</span>`;
              }
              // Re-initialize Lucide icons
              if (globalThis.lucide) {
                globalThis.lucide.createIcons();
              }
            }
          });
          this.hideNodeActionMenu();
        });

      menu
        .querySelector('[data-action="duplicate"]')
        .addEventListener("click", (e) => {
          e.stopPropagation();
          this.duplicateAgentNode(node, agentInstance);
          this.hideNodeActionMenu();
        });

      menu
        .querySelector('[data-action="delete"]')
        .addEventListener("click", (e) => {
          e.stopPropagation();
          const instanceId = node.dataset.instanceId;

          // Remove all connections for this node
          if (this.connectionManager) {
            this.connectionManager.removeNodeConnections(instanceId);
          }

          node.remove();
          this.hideNodeActionMenu();
        });
    }

    // Close menu when clicking outside
    // Remove any existing listener first to prevent conflicts
    if (this.menuCloseListener) {
      document.removeEventListener("click", this.menuCloseListener);
    }

    // Create and store the new listener
    this.menuCloseListener = (e) => {
      // Don't close if clicking on a node (let the node's click handler manage it)
      if (e.target.closest(".agent-node")) {
        return;
      }
      this.hideNodeActionMenu();
    };

    // Add listener after a short delay to avoid immediate trigger
    setTimeout(() => {
      document.addEventListener("click", this.menuCloseListener);
    }, 10);
  }

  hideNodeActionMenu() {
    const existingMenu = document.getElementById("active-node-menu");
    if (existingMenu) {
      existingMenu.remove();
    }

    // Remove the document click listener
    if (this.menuCloseListener) {
      document.removeEventListener("click", this.menuCloseListener);
      this.menuCloseListener = null;
    }
  }

  duplicateAgentNode(originalNode, agentInstance) {
    const rect = originalNode.getBoundingClientRect();
    const parentRect = originalNode.parentElement.getBoundingClientRect();

    // Position duplicate offset from original (will be snapped to grid)
    // Use 2 grid cells offset for clear visual separation
    const offset = this.canvasConfig.gridSize * 2;
    const x = rect.left - parentRect.left + offset;
    const y = rect.top - parentRect.top + offset;

    // Create a new independent instance (removes instanceId so a new one is generated)
    const templateAgent = {
      id: agentInstance.id,
      config: { ...agentInstance.config },
      status: agentInstance.status,
      created_at: agentInstance.created_at,
    };

    const duplicateNode = this.createAgentNode(templateAgent, x, y);
    originalNode.parentElement.appendChild(duplicateNode);

    // Re-initialize Lucide icons after appending to DOM
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }
  }

  /**
   * Save current canvas state to localStorage
   */
  saveCanvasState() {
    if (!this.connectionManager) {
      console.warn("Connection manager not initialized");
      return;
    }

    const state = this.connectionManager.exportState();
    localStorage.setItem("amalia_canvas_state", JSON.stringify(state));
    console.log("✓ Canvas state saved", state);
    showToast("Canvas saved successfully", "success");
    return state;
  }

  /**
   * Load canvas state from localStorage
   */
  loadCanvasState() {
    const stateJson = localStorage.getItem("amalia_canvas_state");
    if (!stateJson) {
      console.log("No saved canvas state found");
      return false;
    }

    try {
      const state = JSON.parse(stateJson);
      const canvasContent = document.getElementById("canvas-content");

      if (!canvasContent || !this.connectionManager) {
        console.error("Canvas not ready");
        return false;
      }

      // Use arrow function to preserve 'this' context
      const success = this.connectionManager.importState(
        state,
        (agent, x, y) => {
          const node = this.createAgentNode(agent, x, y);
          canvasContent.appendChild(node);
          return node;
        }
      );

      if (success) {
        showToast("Canvas loaded successfully", "success");
      }
      return success;
    } catch (error) {
      console.error("Error loading canvas state:", error);
      showToast("Error loading canvas", "error");
      return false;
    }
  }

  /**
   * Clear canvas state
   */
  clearCanvas() {
    if (this.connectionManager) {
      this.connectionManager.clearAll();
    }

    for (const node of document.querySelectorAll(".agent-node")) {
      node.remove();
    }

    console.log("✓ Canvas cleared");
    showToast("Canvas cleared", "info");
  }

  /**
   * Create pipeline from BUILD command response
   */
  async createPipelineFromData(nodes, connections) {
    if (!this.canvasMode) {
      console.warn("Not in canvas mode, storing pipeline for later");
      return;
    }

    const canvasContent = document.getElementById("canvas-content");
    if (!canvasContent) {
      console.error("Canvas content not found");
      return;
    }

    // Get all agents
    const agents = await api.getAgents();
    const agentMap = new Map(agents.map((a) => [a.id, a]));

    // Create nodes
    for (const nodeData of nodes) {
      const agent = agentMap.get(nodeData.agentId);
      if (!agent) {
        console.error("Agent not found:", nodeData.agentId);
        continue;
      }

      // Create node with specific instance ID and position
      const node = document.createElement("div");
      node.className = "agent-node";
      node.dataset.instanceId = nodeData.instanceId;
      node.dataset.agentId = nodeData.agentId;

      const agentInstance = {
        ...agent,
        instanceId: nodeData.instanceId,
        position: nodeData.position,
      };

      node.dataset.agentData = JSON.stringify(agentInstance);
      node.style.left = `${nodeData.position.x}px`;
      node.style.top = `${nodeData.position.y}px`;

      node.innerHTML = `
        <div class="agent-node-header">
          ${
            agent.config.icon
              ? `<i data-lucide="${agent.config.icon}" class="agent-node-icon"></i>`
              : `<span class="agent-node-name">${agent.config.name}</span>`
          }
        </div>
        <div class="agent-node-input" data-port="input" title="Input connection"></div>
        <div class="agent-node-output" data-port="output" title="Output connection"></div>
      `;

      // Make draggable
      this.makeDraggableNode(node);

      // Add connection port handlers
      this.setupConnectionPorts(node);

      // Add click handler for action menu
      node.addEventListener("click", (e) => {
        if (e.target.dataset.port) return;
        const currentInstance = JSON.parse(node.dataset.agentData);
        this.showNodeActionMenu(node, currentInstance);
      });

      canvasContent.appendChild(node);
    }

    // Initialize Lucide icons once after all nodes are added
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    // Create connections
    if (this.connectionManager && connections.length > 0) {
      setTimeout(() => {
        for (const conn of connections) {
          this.connectionManager.createConnection(
            conn.fromInstanceId,
            "output",
            conn.toInstanceId,
            "input"
          );
        }
        console.log(`✓ Created ${connections.length} connections`);
      }, 100);
    }

    console.log(
      `✓ Pipeline created: ${nodes.length} nodes, ${connections.length} connections`
    );
    showToast(`Pipeline created with ${nodes.length} agents`, "success");
  }
}

// Initialize app when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  const app = new App();
  globalThis.app = app; // Store globally for cross-component access
  app.init();
});
