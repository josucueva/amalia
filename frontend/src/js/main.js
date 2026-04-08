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
import themeManager from "./utils/theme.js";

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
  lastBatchJobId = null;

  // Canvas drop listeners (to prevent duplicates)
  canvasDropListeners = {
    dragover: null,
    drop: null,
  };

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

  // Connection state
  connectionsEnabled = true;

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
          state.getState().currentFile,
        );
      });
    }

    // Setup configure interaction agent button
    const configureInteractionAgentBtn = document.getElementById(
      "configure-interaction-agent-btn",
    );
    if (configureInteractionAgentBtn) {
      configureInteractionAgentBtn.addEventListener("click", async () => {
        await this.openInteractionAgentConfig();
      });
    }

    // Setup batch automation buttons in chat input
    const scanLaunchBtn = document.getElementById("scan-launch-btn");
    if (scanLaunchBtn) {
      scanLaunchBtn.addEventListener("click", async () => {
        await this.handleScanAndLaunch();
      });
    }

    const validateManifestBtn = document.getElementById(
      "validate-manifest-btn",
    );
    if (validateManifestBtn) {
      validateManifestBtn.addEventListener("click", async () => {
        await this.handleValidateManifest();
      });
    }

    const rerunFailedBtn = document.getElementById("rerun-failed-btn");
    if (rerunFailedBtn) {
      rerunFailedBtn.addEventListener("click", async () => {
        await this.handleRerunFailed();
      });
    }

    // Setup canvas control buttons
    const saveCanvasBtn = document.getElementById("save-canvas-btn");
    const exportFormatSelect = document.getElementById("export-format-select");
    if (saveCanvasBtn) {
      saveCanvasBtn.addEventListener("click", () => {
        const format = exportFormatSelect?.value || "amalia";
        if (format === "sim-ai") {
          this.exportToSimAI();
        } else {
          this.saveCanvasState();
        }
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
            "Are you sure you want to clear the canvas? This cannot be undone.",
          )
        ) {
          this.clearCanvas();
          // Also remove session-specific persisted canvas so it doesn't re-appear on refresh
          const sessionId = globalThis.state?.getState().currentSession?.id;
          if (sessionId) {
            localStorage.removeItem(`amalia_canvas_${sessionId}`);
          }
        }
      });
    }

    // Theme toggle button
    const themeToggleBtn = document.getElementById("theme-toggle-btn");
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener("click", () => {
        themeManager.toggle();
        this.updateThemeIcon();
      });
      // Set initial icon
      this.updateThemeIcon();
    }

    // Setup keyboard shortcuts
    this.setupKeyboardShortcuts();

    console.log("✓ Application initialized successfully");
  }

  /**
   * Update theme toggle text based on current theme
   */
  updateThemeIcon() {
    const themeText = document.getElementById("theme-text");
    if (themeText) {
      themeText.textContent = themeManager.isDark() ? "Light" : "Dark";
    }
  }

  /**
   * Restore the most recent active session on app load
   */
  async restoreSession() {
    try {
      const sessions = state.getState().sessions;

      if (sessions && sessions.length > 0) {
        // Get the most recent session (first in list, sorted by updated_at desc)
        const mostRecentSession = sessions[0];

        // Fetch full session data from backend
        const fullSession = await api.getSession(mostRecentSession.id);
        if (!fullSession) {
          console.warn("Most recent session not found, showing welcome");
          this.chat.showWelcomeMessage();
          return;
        }

        // Update state with full session
        state.setState({ currentSession: fullSession });

        // Queue canvas pipeline for restore from localStorage.
        // When a pipeline is created, Chat.js saves it to localStorage with key
        // `amalia_canvas_${sessionId}`. sessionStorage is cleared on tab close, so we
        // re-populate it here so loadPendingPipeline() can pick it up when canvas opens.
        const savedCanvasData = localStorage.getItem(
          `amalia_canvas_${fullSession.id}`,
        );
        if (savedCanvasData) {
          sessionStorage.setItem("pendingPipeline", savedCanvasData);
          console.log(
            "✓ Canvas pipeline queued for restore, session:",
            fullSession.id,
          );
        }

        // Restore messages to chat
        if (fullSession.messages && fullSession.messages.length > 0) {
          fullSession.messages.forEach((msg) => {
            this.chat.addMessage({
              role: msg.role,
              content: msg.content,
              timestamp: msg.timestamp,
            });
          });
          console.log("✓ Restored", fullSession.messages.length, "messages");
        } else {
          this.chat.showWelcomeMessage();
        }

        console.log(
          "✓ Restored session:",
          fullSession.id,
          "-",
          fullSession.title,
        );
      } else {
        // No sessions available
        console.log("No sessions available, showing welcome");
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
        currentState.currentFile,
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
      // Fetch all agents (interaction agent is now visible)
      const agents = await api.getAgents(true);
      const interactionAgent = agents.find(
        (agent) => agent.id === "interaction_agent",
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

  addSystemMessage(content) {
    if (!this.chat) return;
    this.chat.addMessage({
      role: "system",
      content,
      timestamp: new Date().toISOString(),
    });
  }

  async handleScanAndLaunch() {
    const datasetsRoot =
      prompt(
        "Datasets root folder (relative to backend).",
        "data/uploads/datasets",
      ) || "data/uploads/datasets";

    const taskTypeRaw = prompt(
      "Task filter (optional: classification/regression). Leave empty for all.",
      "",
    );
    const tierRaw = prompt(
      "Tier filter (optional: easy/mid/hard). Leave empty for all.",
      "",
    );
    const limitRaw = prompt(
      "Limit datasets (optional number). Leave empty for no limit.",
      "",
    );

    const payload = {
      datasets_root: datasetsRoot.trim(),
      file_extensions: [".csv"],
      settings: {
        max_retries: 2,
        fail_fast: false,
        create_sessions: true,
      },
    };

    const taskType = taskTypeRaw ? taskTypeRaw.trim().toLowerCase() : "";
    const tier = tierRaw ? tierRaw.trim().toLowerCase() : "";
    const limit = Number.parseInt(limitRaw || "", 10);

    if (taskType) payload.task_type = taskType;
    if (tier) payload.tier = tier;
    if (!Number.isNaN(limit) && limit > 0) payload.limit = limit;

    try {
      showToast("Launching batch scan...", "info");
      const response = await api.scanAndLaunchBatch(payload);
      this.lastBatchJobId = response.batch_job_id;

      const status = await api.getBatchJobStatus(response.batch_job_id);
      const summary = [
        `Batch launched: ${response.batch_job_id}`,
        `Status: ${response.status}`,
        `Datasets: ${response.total_datasets}`,
        `Progress: ${status.progress.processed}/${status.progress.total}`,
      ].join("\n");

      this.addSystemMessage(summary);
      showToast(
        `Batch started (${response.total_datasets} datasets)`,
        "success",
      );
    } catch (error) {
      const detail = error.message || "Unknown error";
      this.addSystemMessage(`Scan-and-launch failed:\n${detail}`);
      showToast("Scan-and-launch failed", "error");
      console.error("Scan-and-launch error:", error);
    }
  }

  async handleValidateManifest() {
    const manifestPath = prompt(
      "Manifest path to validate (JSON/CSV).",
      "data/batch_exports/manifests/latest.json",
    );
    if (!manifestPath) return;

    try {
      showToast("Validating manifest...", "info");
      const result = await api.validateBatchManifest(manifestPath.trim());

      const issuePreview = (result.issues || [])
        .slice(0, 5)
        .map((issue) => `- row ${issue.row_index}: ${issue.error}`)
        .join("\n");

      const summary = [
        `Manifest validation: ${result.manifest_path}`,
        `Rows: ${result.total_rows}`,
        `Valid: ${result.valid_rows}`,
        `Invalid: ${result.invalid_rows}`,
        issuePreview ? `Issues:\n${issuePreview}` : "Issues: none",
      ].join("\n");

      this.addSystemMessage(summary);
      showToast(
        `Manifest checked: ${result.valid_rows} valid, ${result.invalid_rows} invalid`,
        result.invalid_rows > 0 ? "warning" : "success",
      );
    } catch (error) {
      const detail = error.message || "Unknown error";
      this.addSystemMessage(`Manifest validation failed:\n${detail}`);
      showToast("Manifest validation failed", "error");
      console.error("Manifest validation error:", error);
    }
  }

  async handleRerunFailed() {
    const defaultJobId = this.lastBatchJobId || "";
    const jobId = prompt("Source batch job ID.", defaultJobId);
    if (!jobId) return;

    const includeSkipped = confirm("Include skipped items in rerun?");
    const limitRaw = prompt(
      "Limit rerun items (optional number). Leave empty for all.",
      "",
    );
    const limit = Number.parseInt(limitRaw || "", 10);

    const payload = {
      include_skipped: includeSkipped,
    };
    if (!Number.isNaN(limit) && limit > 0) {
      payload.limit = limit;
    }

    try {
      showToast("Submitting rerun for failed items...", "info");
      const response = await api.rerunFailedBatchItems(jobId.trim(), payload);
      this.lastBatchJobId = response.batch_job_id;

      const summary = [
        `Rerun batch launched: ${response.batch_job_id}`,
        `Source job: ${jobId.trim()}`,
        `Status: ${response.status}`,
        `Items queued: ${response.total_datasets}`,
      ].join("\n");

      this.addSystemMessage(summary);
      showToast("Rerun batch submitted", "success");
    } catch (error) {
      const detail = error.message || "Unknown error";
      this.addSystemMessage(`Rerun failed request failed:\n${detail}`);
      showToast("Rerun failed request failed", "error");
      console.error("Rerun failed error:", error);
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

      // Ctrl+Shift+C: Toggle connections on/off (only in canvas mode)
      if (e.ctrlKey && e.shiftKey && e.key === "C") {
        if (this.canvasMode) {
          e.preventDefault();
          this.toggleConnections();
        }
      }

      // Ctrl+Shift+T: Toggle theme (works everywhere)
      if (e.ctrlKey && e.shiftKey && e.key === "T") {
        e.preventDefault();
        themeManager.toggle();
        this.updateThemeIcon();
        showToast(
          `Switched to ${themeManager.isDark() ? "dark" : "light"} mode`,
          "info",
        );
      }
    });
  }

  /**
   * Show detailed data viewer modal for a specific node (config only, no execution data)
   * @param {string} instanceId - The node instance ID
   * @param {Object} agentInstance - The agent instance data
   */
  showNodeDataViewer(instanceId, agentInstance) {
    // Show agent configuration info (pipeline design only — no execution in Amalia)
    const connections = this.connectionManager
      ? this.connectionManager.getConnectionsData()
      : [];
    const inputCount = connections.filter(
      (c) => c.to.instanceId === instanceId,
    ).length;
    const outputCount = connections.filter(
      (c) => c.from.instanceId === instanceId,
    ).length;

    const modal = document.createElement("div");
    modal.className = "modal";
    modal.id = "node-data-viewer-modal";
    modal.style.display = "flex";

    modal.innerHTML = `
      <div class="modal-content data-viewer-modal-content">
        <div class="modal-header">
          <h2>Node Info: ${agentInstance.config?.name || agentInstance.id}</h2>
          <button class="modal-close" onclick="document.getElementById('node-data-viewer-modal').remove()">
            <i data-lucide="x"></i>
          </button>
        </div>
        <div class="modal-body data-viewer-body">
          <div class="data-section">
            <h3>Agent Configuration</h3>
            <div class="data-grid">
              <div class="data-field">
                <label>Instance ID:</label>
                <span class="data-value monospace">${instanceId}</span>
              </div>
              <div class="data-field">
                <label>Agent Type:</label>
                <span class="data-value">${agentInstance.config?.name || agentInstance.id}</span>
              </div>
              <div class="data-field">
                <label>Model:</label>
                <span class="data-value">${agentInstance.config?.model || "N/A"}</span>
              </div>
              <div class="data-field">
                <label>Input Connections:</label>
                <span class="data-value">${inputCount}</span>
              </div>
              <div class="data-field">
                <label>Output Connections:</label>
                <span class="data-value">${outputCount}</span>
              </div>
            </div>
          </div>
          ${
            agentInstance.mcpTools && agentInstance.mcpTools.length > 0
              ? `
          <div class="data-section">
            <h3>MCP Tools (${agentInstance.mcpTools.length})</h3>
            <div class="tools-list">
              ${agentInstance.mcpTools
                .map(
                  (tool) => `
                <div class="tool-item">
                  <div class="tool-header">
                    <i data-lucide="wrench" class="tool-icon"></i>
                    <span class="tool-title">${tool.title}</span>
                  </div>
                  <div class="tool-details">
                    <span class="tool-server">${tool.serverName}</span>
                    <span class="tool-id monospace">${tool.toolId}</span>
                  </div>
                </div>
              `,
                )
                .join("")}
            </div>
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

    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.remove();
    });

    const escapeHandler = (e) => {
      if (e.key === "Escape") {
        modal.remove();
        document.removeEventListener("keydown", escapeHandler);
      }
    };
    document.addEventListener("keydown", escapeHandler);
  }

  toggleCanvasMode() {
    this.canvasMode = !this.canvasMode;
    this.updateUIForMode();

    if (this.canvasMode) {
      this.initializeCanvasMode();
      // Pipeline loading is handled by loadPendingPipeline() inside initializeCanvasMode().
      // It reads sessionStorage.pendingPipeline which is populated from two sources:
      //   1. restoreSession() on page load – reads from localStorage (amalia_canvas_${id})
      //   2. Chat.js handlePipelineCreation() – set when a pipeline is first created
      //
      // Show the welcome message only if no pipeline nodes appear within 400ms
      // (loadPendingPipeline uses a 200ms internal setTimeout).
      setTimeout(() => {
        const canvasContent = document.getElementById("canvas-content");
        const hasNodes =
          canvasContent &&
          canvasContent.querySelectorAll(".agent-node").length > 0;
        if (!hasNodes) {
          this.showCanvasWelcome();
        }
      }, 400);
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
    // Always mount SVG overlay inside the viewport so it shares the same coordinate
    // system as the nodes — no separate transform needed on the SVG itself.
    const canvasViewport = document.getElementById("canvas-viewport");
    const mountTarget =
      canvasViewport || document.getElementById("canvas-content");

    if (mountTarget) {
      this.connectionManager.initialize(mountTarget);
      console.log("ConnectionManager initialized (mounted in viewport)");
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
          pipelineData.connections,
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
          // Zoom functionality (reduced sensitivity for smoother control)
          const delta = e.deltaY > 0 ? 0.95 : 1.05;
          const newScale = Math.max(
            0.1,
            Math.min(3, this.canvasPan.scale * delta),
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
      { passive: false },
    );

    const canvasViewport = document.getElementById("canvas-viewport");

    // Spacebar + drag for panning (or middle mouse button)
    canvasContent.addEventListener("mousedown", (e) => {
      // Pan when clicking on the canvas background (not on nodes or controls).
      // Valid background targets: the clip container, the viewport div, the SVG overlay,
      // or the welcome message — anything that isn't an interactive element.
      const isCanvasBackground =
        e.target === canvasContent ||
        e.target === canvasViewport ||
        e.target.classList.contains("canvas-welcome") ||
        (e.target.tagName === "svg" &&
          e.target.classList.contains("connection-overlay"));

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
   * Update canvas viewport transform for pan/zoom.
   *
   * Single-transform pattern (React Flow / Figma / Excalidraw):
   *   ONE div (#canvas-viewport) holds ALL nodes + the SVG overlay.
   *   Pan/zoom = single CSS transform on that div. Nodes never need their own transforms.
   */
  updateCanvasTransform() {
    const viewport = document.getElementById("canvas-viewport");
    if (!viewport) return;
    const { x, y, scale } = this.canvasPan;
    viewport.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
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

  /**
   * Update all connection positions (called after zoom/pan)
   * Note: With SVG transform applied to overlay, this is only needed when nodes are moved
   */
  updateAllConnections() {
    if (!this.connectionManager) return;

    const connections = this.connectionManager.getConnectionsData();
    connections.forEach((conn) => {
      this.connectionManager.updateConnectionPositions(conn.from.instanceId);
    });
  }

  /**
   * Toggle connections on/off for testing
   */
  toggleConnections() {
    this.connectionsEnabled = !this.connectionsEnabled;

    if (this.connectionManager) {
      this.connectionManager.setEnabled(this.connectionsEnabled);
    }

    const status = this.connectionsEnabled ? "enabled" : "disabled";
    showToast(`Connections ${status}`, "info");
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
    // Canvas-space position. With the viewport approach these are permanent coordinates —
    // no originalX/Y bookkeeping needed; the viewport's transform handles pan/zoom.
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
      <div class="agent-node-model" title="Model: ${agent.config.model}">${
        agent.config.model
      }</div>
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

      // Screen-space deltas for threshold detection
      const deltaXScreen = e.clientX - startX;
      const deltaYScreen = e.clientY - startY;

      // Threshold is in screen pixels (feels natural regardless of zoom)
      if (
        !hasMoved &&
        (Math.abs(deltaXScreen) > dragThreshold ||
          Math.abs(deltaYScreen) > dragThreshold)
      ) {
        hasMoved = true;
      }

      if (hasMoved) {
        // Convert screen-space delta → canvas-space delta by dividing by current zoom.
        // This keeps drag speed consistent at all zoom levels.
        const scale = this.canvasPan.scale;
        let newX = initialLeft + deltaXScreen / scale;
        let newY = initialTop + deltaYScreen / scale;

        // Snap to grid (grid is in canvas space)
        if (snapToGrid) {
          newX = this.snapToGrid(newX, gridSize);
          newY = this.snapToGrid(newY, gridSize);
        }

        // Canvas is infinite — no bounds clamping needed
        element.style.left = `${newX}px`;
        element.style.top = `${newY}px`;

        // Redraw any connections attached to this node
        if (this.connectionManager) {
          this.connectionManager.updateConnectionPositions(
            element.dataset.instanceId,
          );
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
        this.canvasDropListeners.dragover,
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

      // Get drop position relative to canvas-content (the stable, non-transformed boundary)
      const rect = canvasContent.getBoundingClientRect();
      const screenX = e.clientX - rect.left;
      const screenY = e.clientY - rect.top;

      // Convert screen coordinates to canvas-space (divide by scale, subtract pan offset)
      const x = (screenX - this.canvasPan.x) / this.canvasPan.scale - 50;
      const y = (screenY - this.canvasPan.y) / this.canvasPan.scale - 40;

      // Append to viewport so the node inherits the pan/zoom transform automatically
      const viewport = document.getElementById("canvas-viewport");
      const node = this.createAgentNode(agentData, x, y);
      (viewport || canvasContent).appendChild(node);

      // Initialize Lucide icons after appending to DOM
      if (globalThis.lucide) {
        globalThis.lucide.createIcons();
      }
    };

    // Add listeners
    canvasContent.addEventListener(
      "dragover",
      this.canvasDropListeners.dragover,
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

    const instanceId = node.dataset.instanceId;

    menu.innerHTML = `
      <button class="agent-node-menu-btn" data-action="info">INFO</button>
      <button class="agent-node-menu-btn" data-action="edit">EDIT</button>
      <button class="agent-node-menu-btn" data-action="duplicate">DUPLICATE</button>
      <button class="agent-node-menu-btn delete" data-action="delete">DELETE</button>
    `;

    // Menu uses fixed positioning relative to the screen so it is not affected
    // by the canvas-viewport CSS transform.
    const nodeRect = node.getBoundingClientRect();
    menu.style.position = "fixed";
    menu.style.left = nodeRect.right + 8 + "px";
    menu.style.top = nodeRect.top + "px";

    document.body.appendChild(menu);

    // INFO - show node config viewer
    menu
      .querySelector('[data-action="info"]')
      .addEventListener("click", (e) => {
        e.stopPropagation();
        this.showNodeDataViewer(instanceId, agentInstance);
        this.hideNodeActionMenu();
      });

    // EDIT - open agent config modal
    menu
      .querySelector('[data-action="edit"]')
      .addEventListener("click", (e) => {
        e.stopPropagation();
        this.agentConfig.openModal(agentInstance, (updatedConfig) => {
          const updatedInstance = { ...agentInstance, config: updatedConfig };
          node.dataset.agentData = JSON.stringify(updatedInstance);
          const header = node.querySelector(".agent-node-header");
          if (header) {
            header.innerHTML = updatedConfig.icon
              ? `<i data-lucide="${updatedConfig.icon}" class="agent-node-icon"></i>`
              : `<span class="agent-node-name">${updatedConfig.name}</span>`;
            if (globalThis.lucide) globalThis.lucide.createIcons();
          }
          const modelDisplay = node.querySelector(".agent-node-model");
          if (modelDisplay) {
            modelDisplay.textContent = updatedConfig.model;
            modelDisplay.title = `Model: ${updatedConfig.model}`;
          }
        });
        this.hideNodeActionMenu();
      });

    // DUPLICATE
    menu
      .querySelector('[data-action="duplicate"]')
      .addEventListener("click", (e) => {
        e.stopPropagation();
        this.duplicateAgentNode(node, agentInstance);
        this.hideNodeActionMenu();
      });

    // DELETE
    menu
      .querySelector('[data-action="delete"]')
      .addEventListener("click", (e) => {
        e.stopPropagation();
        if (this.connectionManager) {
          this.connectionManager.removeNodeConnections(instanceId);
        }
        node.remove();
        this.hideNodeActionMenu();
      });

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
    // Use canvas-space coordinates (style.left/top) directly — getBoundingClientRect
    // would return screen-space values affected by the viewport transform.
    const offset = this.canvasConfig.gridSize * 2;
    const x = (parseFloat(originalNode.style.left) || 0) + offset;
    const y = (parseFloat(originalNode.style.top) || 0) + offset;

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
   * Export canvas to Sim AI workflow format
   */
  async exportToSimAI() {
    if (!this.connectionManager) {
      console.warn("Connection manager not initialized");
      return;
    }

    try {
      // Fetch MCP servers for tool integration
      const mcpServers = await this.fetchMCPServers();

      // Generate Sim AI workflow
      const simWorkflow =
        await this.connectionManager.exportToSimAI(mcpServers);

      // Download as JSON file
      const blob = new Blob([JSON.stringify(simWorkflow, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `amalia_workflow_${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      console.log("✓ Sim AI workflow exported", simWorkflow);
      showToast("Workflow exported to Sim AI format", "success");
      return simWorkflow;
    } catch (error) {
      console.error("Error exporting to Sim AI:", error);
      showToast("Failed to export workflow", "error");
    }
  }

  /**
   * Fetch MCP servers with their tools for export
   */
  async fetchMCPServers() {
    try {
      const response = await fetch("/api/mcp-servers");
      if (!response.ok) {
        throw new Error("Failed to fetch MCP servers");
      }
      const data = await response.json();
      const servers = data.servers || [];

      // Enhance servers with tool information if available
      // For now, return servers as-is. Tools will be fetched separately if needed
      // or created as placeholders during export
      return servers.map((server) => ({
        ...server,
        // Add URL based on common patterns (can be overridden if server has explicit URL)
        url: server.url || this.inferMcpServerUrl(server),
      }));
    } catch (error) {
      console.error("Error fetching MCP servers:", error);
      return [];
    }
  }

  /**
   * Infer MCP server URL from server configuration.
   * Canonical source of truth is ConnectionManager.MCP_SERVER_MAP;
   * this is a fallback for servers fetched from the registry that
   * don't already carry an explicit URL.
   */
  inferMcpServerUrl(server) {
    const serverIdToPort = {
      mathematics: 8001,
      "python-mathematics": 8001,
      "data-loading": 8002,
      data_loading: 8002,
      "data-preparation": 8003,
      data_preparation: 8003,
      "model-training": 8004,
      model_training: 8004,
      "model-evaluation": 8005,
      model_evaluation: 8005,
      "feature-engineering": 8006,
      feature_engineering: 8006,
    };

    const serverId = server.id?.toLowerCase() || "";
    const port = serverIdToPort[serverId] || 8000;
    return `http://host.docker.internal:${port}/mcp`;
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
      const canvasViewport = document.getElementById("canvas-viewport");
      const canvasContent = document.getElementById("canvas-content");
      const nodeContainer = canvasViewport || canvasContent;

      if (!nodeContainer || !this.connectionManager) {
        console.error("Canvas not ready");
        return false;
      }

      // Use arrow function to preserve 'this' context
      const success = this.connectionManager.importState(
        state,
        (agent, x, y) => {
          const node = this.createAgentNode(agent, x, y);
          nodeContainer.appendChild(node);
          return node;
        },
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
    console.log("[Pipeline] Creating pipeline from data", {
      nodes: nodes.length,
      connections: connections.length,
    });

    if (!this.canvasMode) {
      console.warn("Not in canvas mode, storing pipeline for later");
      return;
    }

    const canvasContent = document.getElementById("canvas-content");
    const canvasViewport = document.getElementById("canvas-viewport");
    if (!canvasContent) {
      console.error("Canvas content not found");
      return;
    }
    // Nodes go into the viewport so they inherit the pan/zoom transform for free.
    // Fall back to canvasContent if for some reason the viewport isn't present yet.
    const nodeContainer = canvasViewport || canvasContent;

    // Remove welcome message if present
    const welcomeMsg = canvasContent.querySelector(".canvas-welcome");
    if (welcomeMsg) {
      welcomeMsg.remove();
    }

    // Get all agents
    const agents = await api.getAgents();
    const agentMap = new Map(agents.map((a) => [a.id, a]));

    console.log("[Pipeline] Available agents:", Array.from(agentMap.keys()));

    // Create nodes
    let nodeIndex = 0;
    for (const nodeData of nodes) {
      console.log("[Pipeline] Processing node", {
        index: nodeIndex,
        type: nodeData.type,
        agentId: nodeData.agentId,
        position: nodeData.position,
      });

      // Handle start trigger node
      if (nodeData.type === "start" || nodeData.agentId === "start_trigger") {
        const node = this.createStartNode(nodeData);
        node.style.animation = "fadeInUp 0.3s ease forwards";
        node.style.animationDelay = `${nodeIndex * 0.05}s`;
        nodeContainer.appendChild(node);
        console.log("[Pipeline] Start node created");
        nodeIndex++;
        continue;
      }

      // Handle regular agent nodes
      const agent = agentMap.get(nodeData.agentId);
      if (!agent) {
        console.error(
          "[Pipeline] Agent not found in registry:",
          nodeData.agentId,
        );
        console.error(
          "[Pipeline] Available agent IDs:",
          Array.from(agentMap.keys()),
        );
        continue;
      }

      console.log("[Pipeline] Creating agent node", {
        agentId: nodeData.agentId,
        agentName: agent.config.name,
        position: nodeData.position,
      });

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
        mcpTools: nodeData.mcpTools || [],
        filePath: nodeData.filePath || null,
      };

      node.dataset.agentData = JSON.stringify(agentInstance);
      // Canvas-space position — the viewport's transform handles pan/zoom, no originalX/Y needed.
      node.style.left = `${nodeData.position.x}px`;
      node.style.top = `${nodeData.position.y}px`;

      // Use MCP tools from nodeData if available
      const mcpTools = nodeData.mcpTools || [];
      const toolCount =
        mcpTools.length || Object.keys(agent.config.mcp_servers || {}).length;

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
              '"><i data-lucide="paperclip" style="width:10px;height:10px;"></i></div>'
            : ""
        }
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

      // Add fade-in animation
      node.style.animation = "fadeInUp 0.3s ease forwards";
      node.style.animationDelay = `${nodeIndex * 0.05}s`;

      nodeContainer.appendChild(node);

      nodeIndex++;
    }

    // Initialize Lucide icons once after all nodes are added
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    // Create connections in order
    if (this.connectionManager && connections.length > 0) {
      console.log("[Pipeline] Creating connections:", connections.length);
      setTimeout(() => {
        connections.forEach((conn, index) => {
          console.log(`[Pipeline] Connection ${index + 1}:`, {
            from: conn.fromInstanceId,
            to: conn.toInstanceId,
          });
          this.connectionManager.createConnection(
            conn.fromInstanceId,
            "output",
            conn.toInstanceId,
            "input",
          );
        });
        console.log(`✓ Created ${connections.length} connections`);
      }, 200);
    }

    console.log(
      `✓ Pipeline created: ${nodes.length} nodes, ${connections.length} connections`,
    );
    showToast(`Pipeline created with ${nodes.length} agents`, "success");
  }

  /**
   * Create a start trigger node
   */
  createStartNode(nodeData) {
    const node = document.createElement("div");
    node.className = "agent-node start-node";
    node.dataset.instanceId = nodeData.instanceId;
    node.dataset.agentId = "start_trigger";
    node.dataset.agentData = JSON.stringify(nodeData);
    // Canvas-space position — viewport transform handles pan/zoom, no originalX/Y needed.
    node.style.left = `${nodeData.position.x}px`;
    node.style.top = `${nodeData.position.y}px`;

    const fileInfo = nodeData.filePath
      ? `<div class="node-file-indicator" title="File: ${nodeData.filePath.split("/").pop()}">
           <i data-lucide="paperclip" style="width:10px;height:10px;"></i>
         </div>`
      : "";

    node.innerHTML = `
      ${fileInfo}
      <div class="agent-node-header">
        <i data-lucide="play-circle" class="agent-node-icon"></i>
      </div>
      <div class="agent-node-model">START</div>
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

    return node;
  }
}

// Initialize app when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  const app = new App();
  app.init();
});
