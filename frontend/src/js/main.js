/**
 * Main Application Entry Point
 */
import api from "./api.js";
import Chat from "./components/Chat.js";
import FileUpload from "./components/FileUpload.js";
import AgentConfig from "./components/AgentConfig.js";
import { showToast } from "./utils/helpers.js";

class App {
  constructor() {
    this.chat = null;
    this.fileUpload = null;
    this.agentConfig = null;
    this.canvasMode = false;
  }

  async init() {
    console.log("🚀 Initializing Agentic Platform...");

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

  toggleCanvasMode() {
    this.canvasMode = !this.canvasMode;
    const overlay = document.getElementById("canvas-overlay");
    const chatContainer = document.querySelector(".chat-container");
    const btnText = document.getElementById("canvas-btn-text");
    const agentsBtn = document.getElementById("agents-btn");

    if (this.canvasMode) {
      overlay.classList.add("active");
      if (chatContainer) chatContainer.style.display = "none";
      if (btnText) btnText.textContent = "Chat Mode";
      if (agentsBtn) agentsBtn.style.display = "inline-block";
      this.loadCanvasAgents();
      this.setupCanvasDrop(); // Enable drag-drop
    } else {
      overlay.classList.remove("active");
      if (chatContainer) chatContainer.style.display = "flex";
      if (btnText) btnText.textContent = "Canvas Mode";
      if (agentsBtn) agentsBtn.style.display = "none";
    }
  }

  async loadCanvasAgents() {
    try {
      const agents = await api.getAgents();
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
    const node = document.createElement("div");
    node.className = "agent-node";
    node.dataset.agentId = agent.id;
    node.style.left = `${x}px`;
    node.style.top = `${y}px`;

    node.innerHTML = `
      <div class="agent-node-header">${agent.config.name}</div>
      <div class="agent-node-input" data-port="input" title="Input connection"></div>
      <div class="agent-node-output" data-port="output" title="Output connection"></div>
    `;

    // Make draggable
    this.makeDraggableNode(node);

    // Add connection port handlers
    this.setupConnectionPorts(node);

    return node;
  }

  createAgentListItem(agent) {
    const item = document.createElement("div");
    item.className = "canvas-agent-item";
    item.draggable = true;
    item.dataset.agentId = agent.id;
    item.dataset.agentData = JSON.stringify(agent);

    item.innerHTML = `
      <div class="canvas-agent-item-content">
        <div class="canvas-agent-item-name">${agent.config.name}</div>
        <div class="canvas-agent-item-desc">${agent.config.description}</div>
        <div class="canvas-agent-item-actions">
          <button class="canvas-agent-action-btn edit-btn">[ EDIT ]</button>
          <button class="canvas-agent-action-btn delete-btn">[ DELETE ]</button>
        </div>
      </div>
    `;

    // Drag start handler
    item.addEventListener("dragstart", (e) => {
      e.dataTransfer.effectAllowed = "copy";
      e.dataTransfer.setData("application/json", item.dataset.agentData);
      item.classList.add("dragging");
    });

    item.addEventListener("dragend", (e) => {
      item.classList.remove("dragging");
    });

    // Edit button handler
    const editBtn = item.querySelector(".edit-btn");
    editBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.agentConfig.openModal(agent);
    });

    // Delete button handler
    const deleteBtn = item.querySelector(".delete-btn");
    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.agentConfig.deleteAgent(agent.id, agent.config.name);
    });

    return item;
  }

  makeDraggableNode(element) {
    const header = element.querySelector(".agent-node-header");
    const dragHandle = header || element;

    let isDragging = false;
    let offsetX = 0;
    let offsetY = 0;

    dragHandle.addEventListener("mousedown", dragStart);

    function dragStart(e) {
      // Don't drag if clicking on port
      if (e.target.dataset.port) return;

      isDragging = true;

      // Calculate offset from mouse to element's top-left corner
      const rect = element.getBoundingClientRect();
      offsetX = e.clientX - rect.left;
      offsetY = e.clientY - rect.top;

      element.style.cursor = "grabbing";

      document.addEventListener("mousemove", drag);
      document.addEventListener("mouseup", dragEnd);

      e.preventDefault();
    }

    function drag(e) {
      if (!isDragging) return;

      e.preventDefault();

      // Get parent's position
      const parentRect = element.parentElement.getBoundingClientRect();

      // Calculate new position: mouse position relative to parent, minus the offset where user clicked
      const newX = e.clientX - parentRect.left - offsetX;
      const newY = e.clientY - parentRect.top - offsetY;

      element.style.left = newX + "px";
      element.style.top = newY + "px";
    }

    function dragEnd(e) {
      isDragging = false;
      element.style.cursor = "move";

      document.removeEventListener("mousemove", drag);
      document.removeEventListener("mouseup", dragEnd);
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
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Create node at drop position
      const node = this.createAgentNode(agentData, x, y);
      canvasContent.appendChild(node);
    });
  }

  setupConnectionPorts(node) {
    const outputPort = node.querySelector('[data-port="output"]');
    const inputPort = node.querySelector('[data-port="input"]');

    if (outputPort) {
      outputPort.addEventListener("mousedown", (e) => {
        e.stopPropagation();
        this.startConnection(node, "output", e);
      });
    }

    if (inputPort) {
      inputPort.addEventListener("mousedown", (e) => {
        e.stopPropagation();
        this.startConnection(node, "input", e);
      });
    }
  }

  startConnection(node, portType, event) {
    // Store connection state
    if (!this.connections) this.connections = [];
    if (!this.tempConnection) {
      this.tempConnection = {
        fromNode: portType === "output" ? node : null,
        toNode: portType === "input" ? node : null,
        startPort: portType,
      };

      // Visual feedback - create temporary line
      const svg = document.getElementById("canvas-svg");
      if (!svg) {
        const newSvg = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "svg"
        );
        newSvg.id = "canvas-svg";
        newSvg.style.position = "absolute";
        newSvg.style.top = "0";
        newSvg.style.left = "0";
        newSvg.style.width = "100%";
        newSvg.style.height = "100%";
        newSvg.style.pointerEvents = "none";
        newSvg.style.zIndex = "1";
        document.getElementById("canvas-content").appendChild(newSvg);
      }

      console.log("Connection started from", portType, "port");
    }
  }
}

// Initialize app when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  const app = new App();
  window.app = app; // Store globally for cross-component access
  app.init();
});
