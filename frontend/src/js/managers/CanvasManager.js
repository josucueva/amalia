import { showToast } from "../utils/helpers.js";
import api from "../api.js";

export default class CanvasManager {
  constructor(app) {
    this.app = app;
    this.canvasContent = document.getElementById("canvas-content");
    
    // Canvas grid configuration
    this.config = {
      gridSize: 20,
      snapToGrid: true,
      dragThreshold: 5,
    };

    // Canvas pan and zoom state
    this.panState = {
      x: 0,
      y: 0,
      scale: 1,
      isPanning: false,
      startX: 0,
      startY: 0,
    };

    // Canvas drop listeners
    this.dropListeners = {
      dragover: null,
      drop: null,
    };
  }

  init() {
    this.setupCanvasPanZoom();
    this.setupCanvasDrop();
  }

  /**
   * Snap coordinate to grid
   */
  snapToGrid(value) {
    return Math.round(value / this.config.gridSize) * this.config.gridSize;
  }

  /**
   * Setup canvas pan and zoom functionality
   */
  setupCanvasPanZoom() {
    if (!this.canvasContent) return;

    // Track spacebar state for panning
    let isSpacePressed = false;

    document.addEventListener("keydown", (e) => {
      if (e.code === "Space" && !e.repeat && this.app.canvasMode) {
        isSpacePressed = true;
        if (!this.panState.isPanning) {
          this.canvasContent.style.cursor = "grab";
        }
      }
    });

    document.addEventListener("keyup", (e) => {
      if (e.code === "Space") {
        isSpacePressed = false;
        if (!this.panState.isPanning) {
          this.canvasContent.style.cursor = "";
        }
      }
    });

    // Mouse wheel for zoom (with Ctrl) or pan (without Ctrl)
    this.canvasContent.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();

        if (e.ctrlKey || e.metaKey) {
          // Zoom
          const delta = e.deltaY > 0 ? 0.95 : 1.05;
          const newScale = Math.max(0.1, Math.min(3, this.panState.scale * delta));

          const rect = this.canvasContent.getBoundingClientRect();
          const mouseX = e.clientX - rect.left;
          const mouseY = e.clientY - rect.top;

          const dx = mouseX - this.panState.x;
          const dy = mouseY - this.panState.y;

          this.panState.x = mouseX - dx * (newScale / this.panState.scale);
          this.panState.y = mouseY - dy * (newScale / this.panState.scale);
          this.panState.scale = newScale;

          this.updateCanvasTransform();
        } else {
          // Pan
          const panSpeed = 1;
          this.panState.x -= e.deltaX * panSpeed;
          this.panState.y -= e.deltaY * panSpeed;
          this.updateCanvasTransform();
        }
      },
      { passive: false }
    );

    // Panning drag handler
    this.canvasContent.addEventListener("mousedown", (e) => {
      const isCanvasBackground =
        e.target === this.canvasContent ||
        e.target.classList.contains("canvas-welcome");

      if (
        isCanvasBackground &&
        (e.button === 1 || (e.button === 0 && isSpacePressed))
      ) {
        e.preventDefault();
        this.panState.isPanning = true;
        this.panState.startX = e.clientX - this.panState.x;
        this.panState.startY = e.clientY - this.panState.y;
        this.canvasContent.classList.add("panning");
        this.canvasContent.style.cursor = "grabbing";
      }
    });

    document.addEventListener("mousemove", (e) => {
      if (this.panState.isPanning) {
        e.preventDefault();
        this.panState.x = e.clientX - this.panState.startX;
        this.panState.y = e.clientY - this.panState.startY;
        this.updateCanvasTransform();
      }
    });

    document.addEventListener("mouseup", () => {
      if (this.panState.isPanning) {
        this.panState.isPanning = false;
        this.canvasContent.classList.remove("panning");
        this.canvasContent.style.cursor = isSpacePressed ? "grab" : "";
      }
    });

    // Keyboard shortcuts for zoom
    document.addEventListener("keydown", (e) => {
      if (!this.app.canvasMode) return;

      if (e.ctrlKey || e.metaKey) {
        if (e.key === "0") {
          e.preventDefault();
          this.resetView();
        } else if (e.key === "=" || e.key === "+") {
          e.preventDefault();
          this.zoom(1.2);
        } else if (e.key === "-" || e.key === "_") {
          e.preventDefault();
          this.zoom(0.8);
        }
      }
    });
  }

  zoom(factor) {
    const oldScale = this.panState.scale;
    let newScale = oldScale * factor;
    
    // Clamp scale
    if (factor > 1) newScale = Math.min(3, newScale);
    else newScale = Math.max(0.1, newScale);

    const rect = this.canvasContent.getBoundingClientRect();
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    const dx = centerX - this.panState.x;
    const dy = centerY - this.panState.y;

    this.panState.x = centerX - dx * (newScale / oldScale);
    this.panState.y = centerY - dy * (newScale / oldScale);
    this.panState.scale = newScale;

    this.updateCanvasTransform();
  }

  updateCanvasTransform() {
    if (!this.canvasContent) return;

    const nodes = this.canvasContent.querySelectorAll(".agent-node");
    const welcome = this.canvasContent.querySelector(".canvas-welcome");

    nodes.forEach((node) => {
      const originalX = parseFloat(node.dataset.originalX || node.style.left);
      const originalY = parseFloat(node.dataset.originalY || node.style.top);

      if (!node.dataset.originalX) {
        node.dataset.originalX = originalX;
        node.dataset.originalY = originalY;
      }

      const newX = this.panState.x + originalX * this.panState.scale;
      const newY = this.panState.y + originalY * this.panState.scale;

      node.style.transform = `translate(${newX - originalX}px, ${
        newY - originalY
      }px) scale(${this.panState.scale})`;
      node.style.transformOrigin = "0 0";
    });

    if (welcome) {
      welcome.style.transform = `translate(-50%, -50%) scale(${this.panState.scale})`;
    }

    if (this.app.connectionManager && this.app.connectionManager.svgOverlay) {
      const svg = this.app.connectionManager.svgOverlay;
      svg.style.transform = `translate(${this.panState.x}px, ${this.panState.y}px) scale(${this.panState.scale})`;
      svg.style.transformOrigin = "0 0";
    }
  }

  resetView() {
    this.panState.x = 0;
    this.panState.y = 0;
    this.panState.scale = 1;
    this.updateCanvasTransform();
    showToast("Canvas view reset", "info");
  }

  setupCanvasDrop() {
    if (!this.canvasContent) return;

    // Remove existing listeners
    if (this.dropListeners.dragover) {
      this.canvasContent.removeEventListener("dragover", this.dropListeners.dragover);
    }
    if (this.dropListeners.drop) {
      this.canvasContent.removeEventListener("drop", this.dropListeners.drop);
    }

    this.dropListeners.dragover = (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    };

    this.dropListeners.drop = (e) => {
      e.preventDefault();
      e.stopPropagation();

      try {
        const agentData = JSON.parse(e.dataTransfer.getData("application/json"));

        const rect = this.canvasContent.getBoundingClientRect();
        let screenX = e.clientX - rect.left;
        let screenY = e.clientY - rect.top;

        let x = (screenX - this.panState.x) / this.panState.scale;
        let y = (screenY - this.panState.y) / this.panState.scale;

        const nodeHalfWidth = 50;
        const nodeHalfHeight = 40;
        x = Math.max(0, x - nodeHalfWidth);
        y = Math.max(0, y - nodeHalfHeight);

        const node = this.createAgentNode(agentData, x, y);
        this.canvasContent.appendChild(node);

        if (globalThis.lucide) {
          globalThis.lucide.createIcons();
        }

        this.updateCanvasTransform();
      } catch (error) {
        console.error("Error dropping agent:", error);
      }
    };

    this.canvasContent.addEventListener("dragover", this.dropListeners.dragover);
    this.canvasContent.addEventListener("drop", this.dropListeners.drop);
  }

  createAgentNode(agent, x, y) {
    const snappedX = this.snapToGrid(x);
    const snappedY = this.snapToGrid(y);

    const instanceId = `instance_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
    const agentInstance = {
      ...agent,
      instanceId: instanceId,
      position: { x: snappedX, y: snappedY },
    };

    const node = document.createElement("div");
    node.className = "agent-node";
    node.dataset.instanceId = instanceId;
    node.dataset.agentId = agent.id;
    node.dataset.agentData = JSON.stringify(agentInstance);
    node.style.left = `${snappedX}px`;
    node.style.top = `${snappedY}px`;
    node.dataset.originalX = snappedX;
    node.dataset.originalY = snappedY;

    const mcpServers = agent.config.mcp_servers || {};
    const toolCount = Object.keys(mcpServers).length;

    node.innerHTML = `
      <div class="agent-node-header">
        ${
          agent.config.icon
            ? `<i data-lucide="${agent.config.icon}" class="agent-node-icon"></i>`
            : `<span class="agent-node-name">${agent.config.name}</span>`
        }
        ${toolCount > 0 ? `<span class="tool-count-badge">${toolCount}</span>` : ""}
      </div>
      <div class="agent-node-model" title="Model: ${agent.config.model}">${agent.config.model}</div>
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

    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    this.makeDraggableNode(node);
    this.setupConnectionPorts(node);

    node.addEventListener("click", (e) => {
      if (e.target.dataset.port) return;
      if (node._justDragged) {
        node._justDragged = false;
        return;
      }
      const currentInstance = JSON.parse(node.dataset.agentData);
      this.app.showNodeActionMenu(node, currentInstance);
    });

    return node;
  }

  makeDraggableNode(element) {
    const canvasContent = document.getElementById("canvas-content");
    if (canvasContent) {
      const welcomeMsg = canvasContent.querySelector(".canvas-welcome");
      if (welcomeMsg) welcomeMsg.remove();
    }
    
    const header = element.querySelector(".agent-node-header");
    const dragHandle = header || element;

    let isDragging = false;
    let hasMoved = false;
    let startX = 0;
    let startY = 0;
    let initialLeft = 0;
    let initialTop = 0;

    dragHandle.addEventListener("mousedown", (e) => {
      if (e.target.dataset.port || e.target.closest(".agent-node-menu-btn")) return;

      this.app.hideNodeActionMenu();

      isDragging = true;
      hasMoved = false;
      startX = e.clientX;
      startY = e.clientY;

      const currentLeft = parseInt(element.style.left, 10) || 0;
      const currentTop = parseInt(element.style.top, 10) || 0;
      initialLeft = currentLeft;
      initialTop = currentTop;

      element.style.cursor = "grabbing";
      element.style.zIndex = "1000";

      document.addEventListener("mousemove", drag);
      document.addEventListener("mouseup", dragEnd);

      e.preventDefault();
      e.stopPropagation();
    });

    const drag = (e) => {
      if (!isDragging) return;
      e.preventDefault();

      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;

      if (!hasMoved && (Math.abs(deltaX) > this.config.dragThreshold || Math.abs(deltaY) > this.config.dragThreshold)) {
        hasMoved = true;
      }

      if (hasMoved) {
        let newX = initialLeft + deltaX;
        let newY = initialTop + deltaY;

        if (this.config.snapToGrid) {
          newX = this.snapToGrid(newX);
          newY = this.snapToGrid(newY);
        }

        const parent = element.parentElement;
        if (parent) {
          const maxX = parent.clientWidth - element.offsetWidth;
          const maxY = parent.clientHeight - element.offsetHeight;
          newX = Math.max(0, Math.min(newX, maxX));
          newY = Math.max(0, Math.min(newY, maxY));
        }

        element.style.left = newX + "px";
        element.style.top = newY + "px";
        element.dataset.originalX = newX;
        element.dataset.originalY = newY;

        if (this.app.connectionManager) {
          this.app.connectionManager.updateConnectionPositions(element.dataset.instanceId);
        }
      }
    };

    const dragEnd = (e) => {
      document.removeEventListener("mousemove", drag);
      document.removeEventListener("mouseup", dragEnd);

      element.style.cursor = "move";
      element.style.zIndex = "2";

      if (hasMoved) {
        element._justDragged = true;
        setTimeout(() => {
          element._justDragged = false;
        }, 100);
      }

      isDragging = false;
      hasMoved = false;
    };
  }

  setupConnectionPorts(node) {
    const outputPort = node.querySelector('[data-port="output"]');
    const inputPort = node.querySelector('[data-port="input"]');

    if (outputPort) {
      outputPort.addEventListener("click", (e) => {
        e.stopPropagation();
        if (this.app.connectionManager) {
          this.app.connectionManager.handlePortClick(node, "output", e);
        }
      });
    }

    if (inputPort) {
      inputPort.addEventListener("click", (e) => {
        e.stopPropagation();
        if (this.app.connectionManager) {
          this.app.connectionManager.handlePortClick(node, "input", e);
        }
      });
    }
  }

  clearCanvas() {
    if (this.app.connectionManager) {
      this.app.connectionManager.clearAll();
    }
    const nodes = document.querySelectorAll(".agent-node");
    nodes.forEach(node => node.remove());
    console.log("✓ Canvas cleared");
  }

  saveState() {
    if (!this.app.connectionManager) return;
    const state = this.app.connectionManager.exportState();
    localStorage.setItem("amalia_canvas_state", JSON.stringify(state));
    showToast("Canvas saved successfully", "success");
    return state;
  }

  loadState() {
    const stateJson = localStorage.getItem("amalia_canvas_state");
    if (!stateJson) return false;

    try {
      const state = JSON.parse(stateJson);
      if (!this.canvasContent || !this.app.connectionManager) return false;

      const success = this.app.connectionManager.importState(state, (agent, x, y) => {
        const node = this.createAgentNode(agent, x, y);
        this.canvasContent.appendChild(node);
        return node;
      });

      if (success) showToast("Canvas loaded successfully", "success");
      return success;
    } catch (error) {
      console.error("Error loading canvas state:", error);
      showToast("Error loading canvas", "error");
      return false;
    }
  }

  async loadAgents(showHidden = false) {
    try {
      const agents = await api.getAgents(showHidden);
      const canvasAgentList = document.getElementById("canvas-agent-list");
      
      if (!canvasAgentList) return;
      canvasAgentList.innerHTML = "";

      if (agents && agents.length > 0) {
        for (const agent of agents) {
          const listItem = this.createAgentListItem(agent);
          canvasAgentList.appendChild(listItem);
        }
        if (globalThis.lucide) globalThis.lucide.createIcons();
      } else {
        canvasAgentList.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 20px;">No agents configured</div>';
      }
    } catch (error) {
      console.error("Error loading canvas agents:", error);
    }
  }

  createAgentListItem(agent) {
    const isHidden = agent.config.metadata?.is_hidden === true;
    const item = document.createElement("div");
    item.className = "canvas-agent-item";
    item.draggable = !isHidden;
    item.dataset.agentId = agent.id;
    item.dataset.agentData = JSON.stringify(agent);

    if (isHidden) item.classList.add("hidden-agent");

    item.innerHTML = `
      <div class="canvas-agent-item-content">
        <div class="canvas-agent-item-name">
          ${!isHidden && agent.config.icon ? `<i data-lucide="${agent.config.icon}" style="width: 16px; height: 16px; margin-right: 8px;"></i>` : ""}
          ${agent.config.name}
        </div>
        <div class="canvas-agent-item-desc">${agent.config.description}</div>
        <div class="canvas-agent-item-actions">
          <button class="canvas-agent-action-btn edit-btn">[ EDIT ]</button>
          ${!isHidden ? '<button class="canvas-agent-action-btn delete-btn">[ DELETE ]</button>' : ""}
        </div>
      </div>
    `;

    if (!isHidden) {
      item.addEventListener("dragstart", (e) => {
        e.dataTransfer.effectAllowed = "copy";
        e.dataTransfer.setData("application/json", item.dataset.agentData);
        item.classList.add("dragging");
      });
      item.addEventListener("dragend", () => item.classList.remove("dragging"));
    }

    item.querySelector(".edit-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      this.app.agentConfig.openModal(agent);
    });

    if (!isHidden) {
      const deleteBtn = item.querySelector(".delete-btn");
      if (deleteBtn) {
        deleteBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.app.agentConfig.deleteAgent(agent.id, agent.config.name);
        });
      }
    }

    return item;
  }
}
