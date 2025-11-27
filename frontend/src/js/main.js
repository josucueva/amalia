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

class App {
  constructor() {
    this.chat = null;
    this.fileUpload = null;
    this.agentConfig = null;
    this.connectionManager = null;
    this.canvasMode = false;
    this.menuCloseListener = null; // Track document click listener for menu
    this.showHiddenAgents = false; // Toggle for showing hidden agents

    // Canvas grid configuration
    // Note: gridSize must match the CSS grid pattern in main.css (.canvas-content)
    this.canvasConfig = {
      gridSize: 20, // Grid cell size in pixels
      snapToGrid: true, // Enable/disable grid snapping
      dragThreshold: 5, // Minimum pixels movement to initiate drag
    };
  }

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

  runPipeline() {
    // Placeholder for future pipeline execution functionality
    showToast("Pipeline execution will be implemented soon", "info");
    console.log("🚀 Run pipeline functionality - Coming soon!");
    // TODO: Implement actual pipeline execution logic
    // - Validate pipeline has nodes and connections
    // - Send execution request to backend
    // - Show execution progress
    // - Display results
  }

  toggleCanvasMode() {
    this.canvasMode = !this.canvasMode;
    const overlay = document.getElementById("canvas-overlay");
    const chatContainer = document.querySelector(".chat-container");
    const btnText = document.getElementById("canvas-btn-text");
    const agentsBtn = document.getElementById("agents-btn");
    const runBtn = document.getElementById("run-btn");

    if (this.canvasMode) {
      overlay.classList.add("active");
      if (chatContainer) chatContainer.style.display = "none";
      if (btnText) btnText.textContent = "Chat Mode";
      if (agentsBtn) agentsBtn.style.display = "inline-block";
      // Run button stays visible in canvas mode

      // Initialize connection manager if not already done
      if (!this.connectionManager) {
        console.log("🔧 Initializing ConnectionManager...");
        this.connectionManager = new ConnectionManager();
        const canvasContent = document.getElementById("canvas-content");
        if (canvasContent) {
          this.connectionManager.initialize(canvasContent);
          console.log("✅ ConnectionManager initialized");

          // Expose for debugging
          window.connectionManager = this.connectionManager;
        }
      }

      this.loadCanvasAgents();
      this.setupCanvasDrop(); // Enable drag-drop

      // Check for pending pipeline from BUILD command
      const pendingPipeline = sessionStorage.getItem("pendingPipeline");
      if (pendingPipeline) {
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
    } else {
      overlay.classList.remove("active");
      if (chatContainer) chatContainer.style.display = "flex";
      if (btnText) btnText.textContent = "Canvas Mode";
      if (agentsBtn) agentsBtn.style.display = "none";
      // Run button stays visible in chat mode
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
        agents.forEach((agent) => {
          // Create item in sidebar list (draggable)
          const listItem = this.createAgentListItem(agent);
          canvasAgentList.appendChild(listItem);
        });

        // Initialize Lucide icons after all items are added
        if (window.lucide) {
          window.lucide.createIcons();
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
      .substr(2, 9)}`;
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

    // Initialize Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
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
            !isHidden
              ? '<button class="canvas-agent-action-btn delete-btn">[ DELETE ]</button>'
              : ""
          }
        </div>
      </div>
    `;

    // Initialize Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
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

    const app = this;
    const { gridSize, snapToGrid, dragThreshold } = this.canvasConfig;

    dragHandle.addEventListener("mousedown", dragStart);

    function dragStart(e) {
      // Don't drag if clicking on port or action buttons
      if (e.target.dataset.port || e.target.closest(".agent-node-menu-btn"))
        return;

      // Close any open menus when starting to drag
      app.hideNodeActionMenu();

      // Store initial state
      isDragging = true;
      hasMoved = false;
      startX = e.clientX;
      startY = e.clientY;

      // Get current position
      const currentLeft = parseInt(element.style.left) || 0;
      const currentTop = parseInt(element.style.top) || 0;
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
    }

    function drag(e) {
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
          newX = app.snapToGrid(newX, gridSize);
          newY = app.snapToGrid(newY, gridSize);
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
        if (app.connectionManager) {
          const instanceId = element.dataset.instanceId;
          app.connectionManager.updateConnectionPositions(instanceId);
        }
      }
    }

    function dragEnd(e) {
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
    }
  }

  setupCanvasDrop() {
    const canvasContent = document.getElementById("canvas-content");
    if (!canvasContent) return;

    canvasContent.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    });

    canvasContent.addEventListener("drop", (e) => {
      e.preventDefault();
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
    });
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
    menu.innerHTML = `
      <button class="agent-node-menu-btn" data-action="edit">EDIT</button>
      <button class="agent-node-menu-btn" data-action="duplicate">DUPLICATE</button>
      <button class="agent-node-menu-btn delete" data-action="delete">DELETE</button>
    `;

    // Position menu above the node
    const nodeRect = node.getBoundingClientRect();
    const parentRect = node.parentElement.getBoundingClientRect();
    menu.style.left = nodeRect.left - parentRect.left + "px";
    menu.style.bottom = parentRect.bottom - nodeRect.top + 8 + "px";

    node.parentElement.appendChild(menu);

    // Add event listeners
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
    if (window.lucide) {
      window.lucide.createIcons();
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
    document.querySelectorAll(".agent-node").forEach((node) => node.remove());
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
    const nodeElements = [];
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
      nodeElements.push(node);
    }

    // Initialize Lucide icons once after all nodes are added
    if (window.lucide) {
      window.lucide.createIcons();
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
  window.app = app; // Store globally for cross-component access
  app.init();
});
