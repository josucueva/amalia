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
import SessionSidebar from "./components/SessionSidebar.js";
import ConnectionManager from "./managers/ConnectionManager.js";
import { showToast } from "./utils/helpers.js";
import state from "./utils/state.js";
import config from "./config.js";

const { API_BASE_URL } = config;

class App {
  // Component references
  chat = null;
  fileUpload = null;
  agentConfig = null;
  sessionSidebar = null;
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

  // Canvas pan and zoom state
  canvasPan = {
    x: 0,
    y: 0,
    scale: 1,
    isPanning: false,
    startX: 0,
    startY: 0,
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

    // Store app globally before component init
    globalThis.app = this;

    // Initialize components
    this.chat = new Chat();
    this.fileUpload = new FileUpload();
    this.agentConfig = new AgentConfig();
    this.sessionSidebar = new SessionSidebar();
    await this.sessionSidebar.init();

    // Make chat globally accessible for session sidebar
    globalThis.chat = this.chat;

    // Restore last active session or show welcome
    await this.restoreSession();

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

      fileInputInline.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (file) {
          await this.handleFileUpload(file);
        }
      });
    }

    // Setup remove file button
    const removeFileBtn = document.getElementById("remove-file-btn");
    const filePreview = document.getElementById("file-preview");
    if (removeFileBtn && filePreview) {
      removeFileBtn.addEventListener("click", () => {
        console.log("[DEBUG] Removing file from state (main.js)");
        state.setState({ currentFile: null });
        filePreview.style.display = "none";
        if (fileInputInline) {
          fileInputInline.value = "";
        }
        console.log(
          "[DEBUG] File removed, state.currentFile:",
          state.getState().currentFile
        );
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

  /**
   * Restore the most recent active session on app load
   */
  async restoreSession() {
    try {
      const sessions = state.getState().sessions;
      if (sessions && sessions.length > 0) {
        // Get the most recent session (first in list)
        const mostRecentSession = sessions[0];
        const fullSession = await api.getSession(mostRecentSession.id);
        state.setState({ currentSession: fullSession });

        // Restore messages to chat
        if (fullSession.messages && fullSession.messages.length > 0) {
          fullSession.messages.forEach((msg) => {
            this.chat.addMessage({
              role: msg.role,
              content: msg.content,
              timestamp: msg.timestamp,
            });
          });
        } else {
          this.chat.showWelcomeMessage();
        }

        console.log("✓ Restored session:", fullSession.id);
      } else {
        // No sessions, show welcome
        this.chat.showWelcomeMessage();
      }
    } catch (error) {
      console.error("Error restoring session:", error);
      // Show welcome message on error
      this.chat.showWelcomeMessage();
    }
  }

  async handleFileUpload(file) {
    console.log("[DEBUG] handleFileUpload called with:", file.name, file.size);

    if (!file.name.endsWith(".csv")) {
      showToast("Please upload a CSV file", "error");
      return;
    }

    // Validate file size (50MB)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      showToast("File size exceeds 50MB limit", "error");
      return;
    }

    try {
      showToast("Uploading file...", "info");
      console.log("[DEBUG] Calling api.uploadFile...");

      // Actually upload the file to the server
      const response = await api.uploadFile(file);
      console.log("[DEBUG] Upload response:", response);

      // Store in state for chat to access
      state.setState({ currentFile: response });
      console.log("[DEBUG] State updated with currentFile:", response);

      // Verify state was set
      const currentState = state.getState();
      console.log(
        "[DEBUG] Verified state.currentFile:",
        currentState.currentFile
      );

      // Show file preview in chat
      const filePreview = document.getElementById("file-preview");
      const fileName = filePreview.querySelector(".file-name");
      fileName.textContent = `📄 ${file.name} (${response.size_mb} MB)`;
      filePreview.style.display = "flex";

      showToast(`File "${file.name}" uploaded successfully`, "success");
    } catch (error) {
      console.error("[DEBUG] Upload error:", error);
      showToast("File upload failed. Please try again.", "error");
    }
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
        // Update data badges to show input/output status
        this.updateNodeDataBadges(node, result);
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

    // Get instance data to extract config overrides
    const agentData = JSON.parse(node.dataset.agentData || "{}");
    const instanceConfig = agentData.config || null;

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
          config: instanceConfig, // Send instance-specific config
          mcpServerIds: agentData.mcpServerIds || [], // Send MCP server IDs
          filePath: agentData.filePath || null, // Send file path if attached
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

  /**
   * Update data badges on a node based on execution results
   * @param {HTMLElement} node - The agent node element
   * @param {Object} executionData - The execution result data
   */
  updateNodeDataBadges(node, executionData) {
    if (!node || !executionData) return;

    const inputBadge = node.querySelector(".input-badge");
    const outputBadge = node.querySelector(".output-badge");
    const agentData = JSON.parse(node.dataset.agentData || "{}");

    // Show input badge if node received inputs OR has a file attached
    if (inputBadge) {
      const hasInputs = executionData.inputs > 0;
      const hasFile = agentData.filePath;

      if (hasInputs || hasFile) {
        inputBadge.style.display = "flex";
        if (hasFile && executionData.inputs === 0) {
          inputBadge.title = "File input attached";
        } else {
          inputBadge.title = `${executionData.inputs} input(s) received`;
        }
      }
    }

    // Show output badge if node produced output
    if (outputBadge && executionData.output) {
      outputBadge.style.display = "flex";
      outputBadge.title = "Output generated";
    }

    // Re-initialize Lucide icons for badges
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
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

  /**
   * Show detailed data viewer modal for a specific node
   * @param {string} instanceId - The node instance ID
   * @param {Object} agentInstance - The agent instance data
   */
  showNodeDataViewer(instanceId, agentInstance) {
    const result = this.executionResults.get(instanceId);
    const hasExecutionData = !!result;

    // Allow viewing even without execution data (will show inputs/connections)
    if (!hasExecutionData && !agentInstance.filePath) {
      // Check if there are any input connections
      const connections = this.connectionManager.getConnectionsData();
      const inputConnections = connections.filter(
        (conn) => conn.to.instanceId === instanceId
      );
      if (inputConnections.length === 0) {
        showToast(
          "No data available - agent not executed and no inputs connected",
          "info"
        );
        return;
      }
    }

    // Get input data from connected nodes
    const connections = this.connectionManager.getConnectionsData();
    const inputConnections = connections.filter(
      (conn) => conn.to.instanceId === instanceId
    );
    const inputData = inputConnections.map((conn) => {
      const inputResult = this.executionResults.get(conn.from.instanceId);
      return {
        fromAgent: conn.from.agentId,
        fromInstance: conn.from.instanceId,
        data: inputResult || null,
      };
    });

    // Check if this node has a file attached
    const hasFileInput = agentInstance.filePath;
    const totalInputs = inputData.length + (hasFileInput ? 1 : 0);

    // Create modal
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.id = "node-data-viewer-modal";
    modal.style.display = "flex";

    modal.innerHTML = `
      <div class="modal-content data-viewer-modal-content">
        <div class="modal-header">
          <h2>Node Data: ${agentInstance.config?.name || agentInstance.id}</h2>
          <button class="modal-close" onclick="document.getElementById('node-data-viewer-modal').remove()">
            <i data-lucide="x"></i>
          </button>
        </div>
        <div class="modal-body data-viewer-body">
          <!-- Metadata Section -->
          <div class="data-section">
            <h3>Execution Metadata</h3>
            <div class="data-grid">
              <div class="data-field">
                <label>Instance ID:</label>
                <span class="data-value monospace">${
                  hasExecutionData ? result.instanceId : instanceId
                }</span>
              </div>
              <div class="data-field">
                <label>Agent Type:</label>
                <span class="data-value">${
                  hasExecutionData
                    ? result.agentType
                    : agentInstance.config?.name || agentInstance.id
                }</span>
              </div>
              ${
                hasExecutionData
                  ? `
              <div class="data-field">
                <label>Timestamp:</label>
                <span class="data-value">${new Date(
                  result.timestamp
                ).toLocaleString()}</span>
              </div>
              <div class="data-field">
                <label>Input Count:</label>
                <span class="data-value badge-count">${result.inputs}</span>
              </div>
              <div class="data-field">
                <label>Status:</label>
                <span class="data-value status-${
                  result.error ? "error" : "success"
                }">
                  ${result.error ? "Error" : "Success"}
                </span>
              </div>
              `
                  : `
              <div class="data-field">
                <label>Status:</label>
                <span class="data-value status-pending">Not Executed</span>
              </div>
              `
              }
            </div>
          </div>

          <!-- Input Data Section -->
          <div class="data-section">
            <h3>Input Data (${totalInputs} source${
      totalInputs === 1 ? "" : "s"
    })</h3>
            ${
              hasFileInput
                ? `
              <div class="data-connections">
                <div class="connection-data">
                  <div class="connection-header">
                    <span class="connection-label">File Input</span>
                    <span class="connection-id monospace">Attached File</span>
                  </div>
                  <pre class="data-preview file-path-display">
File Path: ${agentInstance.filePath}

Note: Agent should use MCP filesystem tools to read this file.
The file path has been passed to the agent's execution context.
                  </pre>
                </div>
              </div>
            `
                : ""
            }
            ${
              inputData.length > 0
                ? `
              <div class="data-connections">
                ${inputData
                  .map(
                    (input, idx) => `
                  <div class="connection-data">
                    <div class="connection-header">
                      <span class="connection-label">From: ${
                        input.fromAgent
                      }</span>
                      <span class="connection-id monospace">${
                        input.fromInstance
                      }</span>
                    </div>
                    ${
                      input.data
                        ? `
                      <pre class="data-preview">${this.formatDataForDisplay(
                        input.data.output
                      )}</pre>
                    `
                        : '<p class="no-data">No data available</p>'
                    }
                  </div>
                `
                  )
                  .join("")}
              </div>
            `
                : !hasFileInput
                ? '<p class="no-data">No input connections</p>'
                : ""
            }
          </div>

          <!-- Output Data Section -->
          <div class="data-section">
            <h3>Output Data</h3>
            ${
              !hasExecutionData
                ? '<p class="no-data">Agent has not been executed yet</p>'
                : result.error
                ? `
              <div class="error-display">
                <span>ERROR: ${result.error}</span>
              </div>
            `
                : `
              <pre class="data-preview output-preview">${this.formatDataForDisplay(
                result.output
              )}</pre>
            `
            }
          </div>

          <!-- Actions Section -->
          ${
            hasExecutionData
              ? `
          <div class="data-section data-actions">
            <button class="btn btn-secondary" id="copy-output-btn">
              COPY OUTPUT
            </button>
            <button class="btn btn-secondary" onclick="${this.getDownloadDataHandler(
              result
            )}">
              DOWNLOAD JSON
            </button>
          </div>
          `
              : ""
          }
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" onclick="document.getElementById('node-data-viewer-modal').remove()">
            Close
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Add copy output button handler
    const copyBtn = modal.querySelector("#copy-output-btn");
    if (copyBtn && hasExecutionData && !result.error) {
      copyBtn.addEventListener("click", () => {
        navigator.clipboard
          .writeText(JSON.stringify(result.output, null, 2))
          .then(() => showToast("Output copied to clipboard", "success"))
          .catch((err) => showToast("Failed to copy output", "error"));
      });
    }

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

    // Close on Escape key
    const escapeHandler = (e) => {
      if (e.key === "Escape") {
        modal.remove();
        document.removeEventListener("keydown", escapeHandler);
      }
    };
    document.addEventListener("keydown", escapeHandler);
  }

  /**
   * Format data for display in the data viewer
   * @param {any} data - The data to format
   * @returns {string} Formatted string
   */
  formatDataForDisplay(data) {
    if (data === null || data === undefined) {
      return "(no data)";
    }

    if (typeof data === "string") {
      // Truncate very long strings
      if (data.length > 2000) {
        return data.substring(0, 2000) + "\n... (truncated)";
      }
      return data;
    }

    try {
      return JSON.stringify(data, null, 2);
    } catch (error) {
      console.warn("Failed to stringify data:", error);
      return String(data);
    }
  }

  /**
   * Get download handler for execution data
   * @param {Object} result - The execution result
   * @returns {string} JavaScript code for download handler
   */
  getDownloadDataHandler(result) {
    const dataStr = JSON.stringify(result, null, 2);
    const escaped = dataStr.replaceAll('"', "&quot;").replaceAll("'", "\\'");
    return `(() => {
      const data = '${escaped}';
      const blob = new Blob([data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'execution-${result.instanceId}-${Date.now()}.json';
      a.click();
      URL.revokeObjectURL(url);
      showToast('Data downloaded', 'success');
    })()`;
  }

  /**
   * Show file attachment modal for data_loader nodes
   * @param {HTMLElement} node - The node element
   * @param {Object} agentInstance - The agent instance data
   */
  async showFileAttachmentModal(node, agentInstance) {
    try {
      // Fetch available files
      const response = await api.listFiles();
      const files = response.files || [];

      // Create modal
      const modal = document.createElement("div");
      modal.className = "modal";
      modal.id = "file-attachment-modal";
      modal.style.display = "flex";

      modal.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <h2>Attach File to Data Loader</h2>
            <button class="modal-close" onclick="document.getElementById('file-attachment-modal').remove()">
              <i data-lucide="x"></i>
            </button>
          </div>
          <div class="modal-body">
            ${
              agentInstance.filePath
                ? `
              <div class="current-file-info">
                <h3>Current File</h3>
                <div class="file-path-display">
                  <i data-lucide="file-text"></i>
                  <span>${agentInstance.filePath}</span>
                </div>
                <button class="btn btn-secondary" id="remove-file-attachment">
                  <i data-lucide="x"></i> Remove Attachment
                </button>
              </div>
              <div class="divider"></div>
            `
                : ""
            }
            <h3>Available Files</h3>
            ${
              files.length === 0
                ? `
              <p class="no-data">No files uploaded yet. Please upload a CSV file first.</p>
            `
                : `
              <div class="file-list">
                ${files
                  .map(
                    (file) => `
                  <div class="file-item" data-filename="${file.filename}">
                    <div class="file-info">
                      <i data-lucide="file-text"></i>
                      <div class="file-details">
                        <span class="file-name">${file.filename}</span>
                        <span class="file-meta">${file.size_mb} MB • ${new Date(
                      file.created_at * 1000
                    ).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <button class="btn btn-primary btn-sm attach-file-btn" data-filename="${
                      file.filename
                    }">
                      ATTACH
                    </button>
                  </div>
                `
                  )
                  .join("")}
              </div>
            `
            }
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" onclick="document.getElementById('file-attachment-modal').remove()">
              Cancel
            </button>
          </div>
        </div>
      `;

      document.body.appendChild(modal);

      // Initialize Lucide icons
      if (globalThis.lucide) {
        globalThis.lucide.createIcons();
      }

      // Add event listeners for attach buttons
      modal.querySelectorAll(".attach-file-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const filename = btn.dataset.filename;
          this.attachFileToNode(node, agentInstance, filename);
          modal.remove();
        });
      });

      // Add event listener for remove button
      const removeBtn = modal.querySelector("#remove-file-attachment");
      if (removeBtn) {
        removeBtn.addEventListener("click", () => {
          this.removeFileFromNode(node, agentInstance);
          modal.remove();
        });
      }

      // Close on overlay click
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          modal.remove();
        }
      });

      // Close on Escape key
      const escapeHandler = (e) => {
        if (e.key === "Escape") {
          modal.remove();
          document.removeEventListener("keydown", escapeHandler);
        }
      };
      document.addEventListener("keydown", escapeHandler);
    } catch (error) {
      console.error("Error loading files:", error);
      showToast("Failed to load files", "error");
    }
  }

  /**
   * Attach a file to a data_loader node
   * @param {HTMLElement} node - The node element
   * @param {Object} agentInstance - The agent instance data
   * @param {string} filename - The filename to attach
   */
  attachFileToNode(node, agentInstance, filename) {
    // Build the full file path
    const filePath = `/app/data/uploads/${filename}`;

    // Update agent instance data
    const updatedInstance = {
      ...agentInstance,
      filePath: filePath,
    };

    // Update node dataset
    node.dataset.agentData = JSON.stringify(updatedInstance);

    // Add or update file indicator
    let fileIndicator = node.querySelector(".node-file-indicator");
    if (!fileIndicator) {
      fileIndicator = document.createElement("div");
      fileIndicator.className = "node-file-indicator";
      node.appendChild(fileIndicator);
    }

    fileIndicator.setAttribute("title", `File attached: ${filename}`);
    fileIndicator.innerHTML = '<i data-lucide="file-text"></i>';

    // Re-initialize Lucide icons
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    // Update data badges
    this.updateNodeDataBadges(node.dataset.instanceId, {
      hasInputData: true,
      hasOutputData: false,
    });

    showToast(`File "${filename}" attached successfully`, "success");
  }

  /**
   * Remove file attachment from a node
   * @param {HTMLElement} node - The node element
   * @param {Object} agentInstance - The agent instance data
   */
  removeFileFromNode(node, agentInstance) {
    // Update agent instance data
    const updatedInstance = {
      ...agentInstance,
      filePath: null,
    };

    // Update node dataset
    node.dataset.agentData = JSON.stringify(updatedInstance);

    // Remove file indicator
    const fileIndicator = node.querySelector(".node-file-indicator");
    if (fileIndicator) {
      fileIndicator.remove();
    }

    // Update data badges
    const hasInputConnections = this.connectionManager
      .getConnectionsData()
      .some((conn) => conn.to.instanceId === node.dataset.instanceId);

    this.updateNodeDataBadges(node.dataset.instanceId, {
      hasInputData: hasInputConnections,
      hasOutputData: this.executionResults.has(node.dataset.instanceId),
    });

    showToast("File attachment removed", "success");
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
      // Show welcome if no session or no pipelines
      const currentSession = globalThis.state?.getState().currentSession;
      if (
        !currentSession ||
        !currentSession.pipelines ||
        currentSession.pipelines.length === 0
      ) {
        this.showCanvasWelcome();
      }
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
    this.setupCanvasPanZoom();
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

  /**
   * Setup canvas pan and zoom functionality
   */
  setupCanvasPanZoom() {
    const canvasContent = document.getElementById("canvas-content");
    if (!canvasContent) return;

    // Track spacebar state for panning
    let isSpacePressed = false;

    document.addEventListener("keydown", (e) => {
      if (e.code === "Space" && !e.repeat && this.canvasMode) {
        isSpacePressed = true;
        // Only add panning cursor if not already panning
        if (!this.canvasPan.isPanning) {
          canvasContent.style.cursor = "grab";
        }
      }
    });

    document.addEventListener("keyup", (e) => {
      if (e.code === "Space") {
        isSpacePressed = false;
        if (!this.canvasPan.isPanning) {
          canvasContent.style.cursor = "";
        }
      }
    });

    // Mouse wheel for zoom (with Ctrl) or pan (without Ctrl)
    canvasContent.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();

        // Ctrl/Cmd + wheel = zoom, otherwise = pan
        if (e.ctrlKey || e.metaKey) {
          // Zoom functionality
          const delta = e.deltaY > 0 ? 0.9 : 1.1;
          const newScale = Math.max(
            0.1,
            Math.min(3, this.canvasPan.scale * delta)
          );

          // Zoom towards mouse position
          const rect = canvasContent.getBoundingClientRect();
          const mouseX = e.clientX - rect.left;
          const mouseY = e.clientY - rect.top;

          const dx = mouseX - this.canvasPan.x;
          const dy = mouseY - this.canvasPan.y;

          this.canvasPan.x = mouseX - dx * (newScale / this.canvasPan.scale);
          this.canvasPan.y = mouseY - dy * (newScale / this.canvasPan.scale);
          this.canvasPan.scale = newScale;

          this.updateCanvasTransform();
        } else {
          // Pan functionality - supports both vertical and horizontal scrolling
          const panSpeed = 1; // Adjust for sensitivity

          // deltaX for horizontal scroll (trackpad/shift+wheel)
          // deltaY for vertical scroll (normal wheel)
          this.canvasPan.x -= e.deltaX * panSpeed;
          this.canvasPan.y -= e.deltaY * panSpeed;

          this.updateCanvasTransform();
        }
      },
      { passive: false }
    );

    // Spacebar + drag for panning (or middle mouse button)
    canvasContent.addEventListener("mousedown", (e) => {
      // Only pan if clicking directly on canvas (not on nodes)
      const isCanvasBackground =
        e.target === canvasContent ||
        e.target.classList.contains("canvas-welcome");

      // Middle mouse button or spacebar + left click on canvas background
      if (
        isCanvasBackground &&
        (e.button === 1 || (e.button === 0 && isSpacePressed))
      ) {
        e.preventDefault();
        this.canvasPan.isPanning = true;
        this.canvasPan.startX = e.clientX - this.canvasPan.x;
        this.canvasPan.startY = e.clientY - this.canvasPan.y;
        canvasContent.classList.add("panning");
        canvasContent.style.cursor = "grabbing";
      }
    });

    document.addEventListener("mousemove", (e) => {
      if (this.canvasPan.isPanning) {
        e.preventDefault();
        this.canvasPan.x = e.clientX - this.canvasPan.startX;
        this.canvasPan.y = e.clientY - this.canvasPan.startY;
        this.updateCanvasTransform();
      }
    });

    document.addEventListener("mouseup", () => {
      if (this.canvasPan.isPanning) {
        this.canvasPan.isPanning = false;
        canvasContent.classList.remove("panning");
        // Restore cursor based on spacebar state
        canvasContent.style.cursor = isSpacePressed ? "grab" : "";
      }
    });

    // Keyboard shortcuts for zoom
    document.addEventListener("keydown", (e) => {
      if (!this.canvasMode) return;

      if (e.ctrlKey || e.metaKey) {
        if (e.key === "0") {
          e.preventDefault();
          this.resetCanvasView();
        } else if (e.key === "=" || e.key === "+") {
          e.preventDefault();
          const oldScale = this.canvasPan.scale;
          const newScale = Math.min(3, oldScale * 1.2);

          // Zoom toward canvas center
          const rect = canvasContent.getBoundingClientRect();
          const centerX = rect.width / 2;
          const centerY = rect.height / 2;

          const dx = centerX - this.canvasPan.x;
          const dy = centerY - this.canvasPan.y;

          this.canvasPan.x = centerX - dx * (newScale / oldScale);
          this.canvasPan.y = centerY - dy * (newScale / oldScale);
          this.canvasPan.scale = newScale;

          this.updateCanvasTransform();
        } else if (e.key === "-" || e.key === "_") {
          e.preventDefault();
          const oldScale = this.canvasPan.scale;
          const newScale = Math.max(0.1, oldScale * 0.8);

          // Zoom toward canvas center
          const rect = canvasContent.getBoundingClientRect();
          const centerX = rect.width / 2;
          const centerY = rect.height / 2;

          const dx = centerX - this.canvasPan.x;
          const dy = centerY - this.canvasPan.y;

          this.canvasPan.x = centerX - dx * (newScale / oldScale);
          this.canvasPan.y = centerY - dy * (newScale / oldScale);
          this.canvasPan.scale = newScale;

          this.updateCanvasTransform();
        }
      }
    });
  }

  /**
   * Update canvas transform based on pan and zoom state
   */
  updateCanvasTransform() {
    const canvasContent = document.getElementById("canvas-content");
    if (!canvasContent) return;

    const nodes = canvasContent.querySelectorAll(".agent-node");
    const welcome = canvasContent.querySelector(".canvas-welcome");

    // Apply transform to all nodes
    nodes.forEach((node) => {
      const originalX = parseFloat(node.dataset.originalX || node.style.left);
      const originalY = parseFloat(node.dataset.originalY || node.style.top);

      if (!node.dataset.originalX) {
        node.dataset.originalX = originalX;
        node.dataset.originalY = originalY;
      }

      const newX = this.canvasPan.x + originalX * this.canvasPan.scale;
      const newY = this.canvasPan.y + originalY * this.canvasPan.scale;

      node.style.transform = `translate(${newX - originalX}px, ${
        newY - originalY
      }px) scale(${this.canvasPan.scale})`;
      node.style.transformOrigin = "0 0";
    });

    // Apply transform to welcome message
    if (welcome) {
      welcome.style.transform = `translate(-50%, -50%) scale(${this.canvasPan.scale})`;
    }
  }

  /**
   * Reset canvas view to default
   */
  resetCanvasView() {
    this.canvasPan.x = 0;
    this.canvasPan.y = 0;
    this.canvasPan.scale = 1;
    this.updateCanvasTransform();
    showToast("Canvas view reset", "info");
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
    // Store original position for pan/zoom transform
    node.dataset.originalX = snappedX;
    node.dataset.originalY = snappedY;

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
      <div class="agent-node-model" title="Model: ${agent.config.model}">${
      agent.config.model
    }</div>
      <div class="agent-node-input" data-port="input" title="Input connection"></div>
      <div class="agent-node-output" data-port="output" title="Output connection"></div>
      <div class="agent-node-data-badges">
        <span class="data-badge input-badge" style="display: none;" title="Has input data">
          <i data-lucide="arrow-down-to-line"></i>
        </span>
        <span class="data-badge output-badge" style="display: none;" title="Has output data">
          <i data-lucide="arrow-up-from-line"></i>
        </span>
      </div>
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
    // Remove canvas welcome message if present when node is added
    const canvasContent = document.getElementById("canvas-content");
    if (canvasContent) {
      const welcomeMsg = canvasContent.querySelector(".canvas-welcome");
      if (welcomeMsg) welcomeMsg.remove();
    }
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
        // Update original position for pan/zoom transform
        element.dataset.originalX = newX;
        element.dataset.originalY = newY;

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
      let screenX = e.clientX - rect.left;
      let screenY = e.clientY - rect.top;

      // Convert screen coordinates to canvas coordinates (accounting for pan/zoom)
      let x = (screenX - this.canvasPan.x) / this.canvasPan.scale;
      let y = (screenY - this.canvasPan.y) / this.canvasPan.scale;

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

      // Apply current pan/zoom transform to the new node
      this.updateCanvasTransform();
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
      // Check if node has execution results
      const hasExecutionData = this.executionResults.has(instanceId);

      // Check if this is a data_loader agent - check by name since ID is generated
      const isDataLoader = agentInstance.config?.name === "data_loader";

      // Show normal controls
      menu.innerHTML = `
        <button class="agent-node-menu-btn" data-action="execute-prompt" title="Execute with custom prompt">EXECUTE</button>
        <button class="agent-node-menu-btn" data-action="view-data">VIEW DATA</button>
        ${
          isDataLoader
            ? '<button class="agent-node-menu-btn" data-action="attach-file">ATTACH FILE</button>'
            : ""
        }
        <button class="agent-node-menu-btn" data-action="edit">EDIT</button>
        <button class="agent-node-menu-btn" data-action="duplicate">DUPLICATE</button>
        <button class="agent-node-menu-btn delete" data-action="delete">DELETE</button>
      `;
    }

    // Position menu to the right of the node
    const nodeRect = node.getBoundingClientRect();
    const parentRect = node.parentElement.getBoundingClientRect();
    menu.style.left = nodeRect.right - parentRect.left + 8 + "px";
    menu.style.top = nodeRect.top - parentRect.top + "px";

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
      const executePromptBtn = menu.querySelector(
        '[data-action="execute-prompt"]'
      );
      if (executePromptBtn) {
        executePromptBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.showExecutePromptModal(node, agentInstance);
          this.hideNodeActionMenu();
        });
      }

      const viewDataBtn = menu.querySelector('[data-action="view-data"]');
      if (viewDataBtn) {
        viewDataBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.showNodeDataViewer(instanceId, agentInstance);
          this.hideNodeActionMenu();
        });
      }

      const attachFileBtn = menu.querySelector('[data-action="attach-file"]');
      if (attachFileBtn) {
        attachFileBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.showFileAttachmentModal(node, agentInstance);
          this.hideNodeActionMenu();
        });
      }

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

            // Update the model display
            const modelDisplay = node.querySelector(".agent-node-model");
            if (modelDisplay) {
              modelDisplay.textContent = updatedConfig.model;
              modelDisplay.title = `Model: ${updatedConfig.model}`;
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

  showExecutePromptModal(node, agentInstance) {
    const instanceId = node.dataset.instanceId;

    // Create modal
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.id = "execute-prompt-modal";
    modal.style.display = "flex";

    modal.innerHTML = `
      <div class="modal-content" style="max-width: 600px;">
        <div class="modal-header">
          <h2>Execute Agent: ${
            agentInstance.config?.name || agentInstance.id
          }</h2>
          <button class="modal-close" onclick="document.getElementById('execute-prompt-modal').remove()">
            <i data-lucide="x"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="execute-user-prompt">User Prompt</label>
            <textarea
              id="execute-user-prompt"
              class="form-control"
              rows="6"
              placeholder="Enter a custom prompt to execute this agent directly (bypasses interaction agent for testing)..."
              autofocus
            ></textarea>
            <small class="form-help">
              This prompt will be sent directly to the agent for execution. 
              Use this to test individual agents without going through the full pipeline.
            </small>
          </div>
          <div class="form-group">
            <label>Agent Info</label>
            <div class="agent-info-grid">
              <div class="info-field">
                <span class="info-label">Type:</span>
                <span class="info-value">${
                  agentInstance.config?.name || "N/A"
                }</span>
              </div>
              <div class="info-field">
                <span class="info-label">Model:</span>
                <span class="info-value">${
                  agentInstance.config?.model || "N/A"
                }</span>
              </div>
              <div class="info-field">
                <span class="info-label">Instance ID:</span>
                <span class="info-value monospace">${instanceId}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="document.getElementById('execute-prompt-modal').remove()">
            Cancel
          </button>
          <button class="btn btn-primary" id="execute-prompt-btn">
            Execute Agent
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Initialize Lucide icons
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    // Handle execute button
    const executeBtn = document.getElementById("execute-prompt-btn");
    const promptTextarea = document.getElementById("execute-user-prompt");

    executeBtn.addEventListener("click", async () => {
      const userPrompt = promptTextarea.value.trim();

      if (!userPrompt) {
        showToast("Please enter a prompt", "warning");
        promptTextarea.focus();
        return;
      }

      // Close modal
      modal.remove();

      // Execute the node with the custom prompt
      try {
        this.setNodeExecutionState(node, "running");

        // Get input from connected nodes
        const connections = this.connectionManager.getConnectionsData();
        const inputs = connections
          .filter((conn) => conn.to.instanceId === instanceId)
          .map((conn) => this.executionResults.get(conn.from.instanceId))
          .filter((result) => result !== undefined);

        // Add user prompt as additional context
        const promptInput = {
          instanceId: "user_prompt",
          agentType: "user_input",
          output: userPrompt,
          timestamp: new Date().toISOString(),
          inputs: 0,
        };

        // Prepend user prompt to inputs
        const allInputs = [promptInput, ...inputs];

        // Execute via API
        const response = await fetch(`${API_BASE_URL}/api/canvas/execute`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            instanceId,
            agentType: node.dataset.agentId,
            inputs: allInputs,
            config: agentInstance.config || null,
            mcpServerIds: agentInstance.mcpServerIds || [],
            filePath: agentInstance.filePath || null,
          }),
        });

        if (!response.ok) {
          throw new Error(`Failed to execute agent: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.error) {
          throw new Error(result.error);
        }

        // Store and display results
        this.executionResults.set(instanceId, result);
        this.updateNodeDataBadges(node, result);
        this.setNodeExecutionState(node, "completed");

        showToast("Agent executed successfully", "success");
      } catch (error) {
        console.error("Error executing agent:", error);
        this.setNodeExecutionState(node, "error");
        showToast(`Execution failed: ${error.message}`, "error");
      }
    });

    // Close on overlay click
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });

    // Close on Escape key
    const escapeHandler = (e) => {
      if (e.key === "Escape") {
        modal.remove();
        document.removeEventListener("keydown", escapeHandler);
      }
    };
    document.addEventListener("keydown", escapeHandler);

    // Focus the textarea
    setTimeout(() => promptTextarea.focus(), 100);
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
  }

  showCanvasWelcome() {
    const canvasContent = document.getElementById("canvas-content");
    if (!canvasContent) return;

    // Remove existing welcome message if any
    const existingWelcome = canvasContent.querySelector(".canvas-welcome");
    if (existingWelcome) {
      existingWelcome.remove();
    }

    // Only show welcome if no agent nodes are present
    if (canvasContent.querySelectorAll(".agent-node").length > 0) return;

    const welcomeDiv = document.createElement("div");
    welcomeDiv.className = "canvas-welcome";
    welcomeDiv.innerHTML = `
      <div class="canvas-welcome-content">
        <h2>Agent Canvas</h2>
        <p>Start chatting to build your first pipeline</p>
        <div class="canvas-welcome-hint">
          <span>💡</span>
          <p>Or drag agents from the sidebar to create a custom workflow</p>
        </div>
      </div>
    `;

    canvasContent.appendChild(welcomeDiv);
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

    // Remove welcome message if present
    const welcomeMsg = canvasContent.querySelector(".canvas-welcome");
    if (welcomeMsg) {
      welcomeMsg.remove();
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
        mcpServerIds: nodeData.mcpServerIds || [],
        filePath: nodeData.filePath || null,
      };

      node.dataset.agentData = JSON.stringify(agentInstance);
      node.style.left = `${nodeData.position.x}px`;
      node.style.top = `${nodeData.position.y}px`;

      // Count MCP tools for consistency with manually created nodes
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
        <div class="agent-node-model" title="Model: ${agent.config.model}">${
        agent.config.model
      }</div>
        ${
          nodeData.filePath
            ? '<div class="node-file-indicator" title="File attached: ' +
              nodeData.filePath.split("/").pop() +
              '"><i data-lucide="file-text"></i></div>'
            : ""
        }
        <div class="agent-node-input" data-port="input" title="Input connection"></div>
        <div class="agent-node-output" data-port="output" title="Output connection"></div>
        <div class="agent-node-data-badges">
          <span class="data-badge input-badge" style="display: none;" title="Has input data">
            <i data-lucide="arrow-down-to-line"></i>
          </span>
          <span class="data-badge output-badge" style="display: none;" title="Has output data">
            <i data-lucide="arrow-up-from-line"></i>
          </span>
        </div>
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
  app.init();
});
