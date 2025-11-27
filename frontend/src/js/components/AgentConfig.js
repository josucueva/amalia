/**
 * Agent Configuration Component
 */
import api from "../api.js";
import state from "../utils/state.js";
import { showToast } from "../utils/helpers.js";

class AgentConfig {
  constructor() {
    this.agentsBtn = document.getElementById("agents-btn");
    this.agentModal = document.getElementById("agent-modal");
    this.closeModalBtn = document.getElementById("close-agent-modal");
    this.cancelBtn = document.getElementById("cancel-agent-btn");
    this.agentForm = document.getElementById("agent-form");
    this.agentList = document.getElementById("agent-list");
    this.reloadBtn = document.getElementById("reload-agents-btn");
    this.currentAgentId = null;

    // Icon picker elements
    this.iconPickerModal = document.getElementById("icon-picker-modal");
    this.iconPickerGrid = document.getElementById("icon-picker-grid");
    this.selectIconBtn = document.getElementById("select-icon-btn");
    this.clearIconBtn = document.getElementById("clear-icon-btn");
    this.closeIconPickerBtn = document.getElementById("close-icon-picker");
    this.selectedIcon = null;

    this.init();
    this.loadAgents();
    this.initIconPicker();
  }

  init() {
    // Close modal
    if (this.closeModalBtn) {
      this.closeModalBtn.addEventListener("click", () => this.closeModal());
    }

    if (this.cancelBtn) {
      this.cancelBtn.addEventListener("click", () => this.closeModal());
    }

    if (this.agentModal) {
      this.agentModal.addEventListener("click", (e) => {
        if (e.target === this.agentModal) {
          this.closeModal();
        }
      });
    }

    // Form submission
    if (this.agentForm) {
      this.agentForm.addEventListener("submit", (e) => this.handleSubmit(e));
    }

    // Reload agents
    if (this.reloadBtn) {
      this.reloadBtn.addEventListener("click", () => this.reloadAgents());
    }
  }

  initIconPicker() {
    // ML/Data Science related icons from Lucide
    this.mlIcons = [
      { name: "database", label: "Database" },
      { name: "bar-chart", label: "Bar Chart" },
      { name: "line-chart", label: "Line Chart" },
      { name: "pie-chart", label: "Pie Chart" },
      { name: "activity", label: "Activity" },
      { name: "brain", label: "Brain" },
      { name: "cpu", label: "CPU" },
      { name: "network", label: "Network" },
      { name: "git-branch", label: "Pipeline" },
      { name: "layers", label: "Layers" },
      { name: "target", label: "Target" },
      { name: "zap", label: "Spark" },
      { name: "trending-up", label: "Trending" },
      { name: "filter", label: "Filter" },
      { name: "shuffle", label: "Shuffle" },
      { name: "sliders", label: "Sliders" },
      { name: "settings", label: "Settings" },
      { name: "box", label: "Box" },
      { name: "package", label: "Package" },
      { name: "file-text", label: "File" },
      { name: "folder", label: "Folder" },
      { name: "archive", label: "Archive" },
      { name: "clipboard", label: "Clipboard" },
      { name: "check-circle", label: "Check" },
      { name: "alert-circle", label: "Alert" },
      { name: "info", label: "Info" },
      { name: "sparkles", label: "Sparkles" },
      { name: "wand", label: "Wand" },
      { name: "beaker", label: "Beaker" },
      { name: "microscope", label: "Microscope" },
    ];

    // Populate icon grid
    this.iconPickerGrid.innerHTML = this.mlIcons
      .map(
        (icon) => `
      <div class="icon-picker-item" data-icon="${icon.name}">
        <i data-lucide="${icon.name}"></i>
        <span>${icon.label}</span>
      </div>
    `
      )
      .join("");

    // Initialize Lucide icons
    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    // Icon picker events
    if (this.selectIconBtn) {
      this.selectIconBtn.addEventListener("click", () => this.openIconPicker());
    }

    if (this.clearIconBtn) {
      this.clearIconBtn.addEventListener("click", () => this.clearIcon());
    }

    if (this.closeIconPickerBtn) {
      this.closeIconPickerBtn.addEventListener("click", () =>
        this.closeIconPicker()
      );
    }

    if (this.iconPickerModal) {
      this.iconPickerModal.addEventListener("click", (e) => {
        if (e.target === this.iconPickerModal) {
          this.closeIconPicker();
        }
      });
    }

    // Icon selection
    this.iconPickerGrid
      .querySelectorAll(".icon-picker-item")
      .forEach((item) => {
        item.addEventListener("click", (e) => {
          e.stopPropagation(); // Prevent event bubbling
          const iconName = item.dataset.icon;
          this.selectIcon(iconName);
        });
      });
  }

  openIconPicker() {
    this.iconPickerModal.style.display = "flex";
    // Highlight currently selected icon
    this.iconPickerGrid
      .querySelectorAll(".icon-picker-item")
      .forEach((item) => {
        item.classList.toggle(
          "selected",
          item.dataset.icon === this.selectedIcon
        );
      });
  }

  closeIconPicker() {
    if (this.iconPickerModal) {
      this.iconPickerModal.style.setProperty("display", "none", "important");
    }
  }

  selectIcon(iconName) {
    this.selectedIcon = iconName;
    const agentIconInput = document.getElementById("agent-icon");
    if (agentIconInput) {
      agentIconInput.value = iconName;
    }

    // Hide preview - we only show the icon name
    const preview = document.getElementById("icon-preview");
    if (preview) {
      preview.style.display = "none";
    }

    // Close the modal
    this.closeIconPicker();
  }

  clearIcon() {
    this.selectedIcon = null;
    document.getElementById("agent-icon").value = "";
    document.getElementById("icon-preview").style.display = "none";
  }

  openModal(agent = null, updateCallback = null) {
    this.currentAgentId = agent ? agent.id : null;
    this.instanceUpdateCallback = updateCallback; // Store callback for canvas instances

    // Update modal title
    const modalTitle = this.agentModal.querySelector(".modal-header h2");
    if (modalTitle) {
      modalTitle.textContent = agent ? "Edit Agent" : "Agent Configuration";
    }

    // Update submit button text
    const submitBtn = this.agentForm.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.textContent = agent ? "Update Agent" : "Create Agent";
    }

    if (agent) {
      // Populate form with agent data
      document.getElementById("agent-name").value = agent.config.name;
      document.getElementById("agent-description").value =
        agent.config.description;
      document.getElementById("agent-icon").value = agent.config.icon || "";
      this.selectedIcon = agent.config.icon || null;

      // Hide icon preview - we only show the icon name in the input
      document.getElementById("icon-preview").style.display = "none";

      document.getElementById("agent-model").value = agent.config.model;
      document.getElementById("agent-prompt").value =
        agent.config.system_prompt;
      document.getElementById("agent-a2a").checked = agent.config.a2a_enabled;
    }

    this.agentModal.style.display = "flex";
  }

  closeModal() {
    this.agentModal.style.display = "none";
    this.agentForm.reset();
    this.currentAgentId = null;
    this.instanceUpdateCallback = null; // Clear callback
    this.selectedIcon = null;
    document.getElementById("icon-preview").style.display = "none";
  }

  async handleSubmit(e) {
    e.preventDefault();

    const config = {
      name: document.getElementById("agent-name").value,
      description: document.getElementById("agent-description").value,
      icon: document.getElementById("agent-icon").value || null,
      model: document.getElementById("agent-model").value,
      system_prompt: document.getElementById("agent-prompt").value,
      a2a_enabled: document.getElementById("agent-a2a").checked,
      tools: [],
    };

    try {
      // If there's a callback, it's a canvas instance - just update locally
      if (this.instanceUpdateCallback) {
        this.instanceUpdateCallback(config);
        showToast("Agent instance updated", "success");
        this.closeModal();
        return;
      }

      if (this.currentAgentId) {
        // Update existing agent in backend
        await api.updateAgent(this.currentAgentId, config);
        showToast("Agent updated successfully", "success");
      } else {
        // Create new agent
        await api.createAgent(config);
        showToast("Agent created successfully", "success");
      }

      this.closeModal();
      this.loadAgents();

      // Trigger canvas refresh if in canvas mode
      if (globalThis.app?.canvasMode) {
        globalThis.app.loadCanvasAgents();
      }
    } catch (error) {
      const action = this.currentAgentId ? "update" : "create";
      showToast(`Failed to ${action} agent`, "error");
      console.error(`Error ${action}ing agent:`, error);
    }
  }

  async loadAgents() {
    try {
      this.agentList.innerHTML = '<div class="loading">Loading agents...</div>';

      const response = await api.listAgents();
      state.setState({ agents: response.agents });

      this.renderAgents(response.agents);
    } catch (error) {
      this.agentList.innerHTML =
        '<div class="loading">Failed to load agents</div>';
      console.error("Error loading agents:", error);
    }
  }

  renderAgents(agents) {
    if (agents.length === 0) {
      this.agentList.innerHTML = `
                <div class="card">
                    <div class="card-body text-center text-muted">
                        <p>No agents configured</p>
                        <p class="mt-1">Click "Agents" to create one</p>
                    </div>
                </div>
            `;
      return;
    }

    this.agentList.innerHTML = agents
      .map(
        (agent) => `
            <div class="agent-item" data-agent-id="${agent.id}">
                <div class="agent-name">
                    <span class="agent-status ${agent.status}"></span>
                    ${agent.config.name}
                </div>
                <div class="agent-description">${agent.config.description}</div>
            </div>
        `
      )
      .join("");

    // Add click handlers
    this.agentList.querySelectorAll(".agent-item").forEach((item) => {
      item.addEventListener("click", () =>
        this.selectAgent(item.dataset.agentId)
      );
    });
  }

  selectAgent(agentId) {
    // Remove active class from all
    this.agentList.querySelectorAll(".agent-item").forEach((item) => {
      item.classList.remove("active");
    });

    // Add active class to selected
    const selectedItem = this.agentList.querySelector(
      `[data-agent-id="${agentId}"]`
    );
    if (selectedItem) {
      selectedItem.classList.add("active");
    }
  }

  async reloadAgents() {
    try {
      showToast("Reloading agents from YAML...", "info");
      await api.reloadAgentsFromYaml();
      await this.loadAgents();
      showToast("Agents reloaded successfully", "success");
    } catch (error) {
      showToast("Failed to reload agents", "error");
      console.error("Error reloading agents:", error);
    }
  }

  async deleteAgent(agentId, agentName) {
    if (!confirm(`Are you sure you want to delete agent "${agentName}"?`)) {
      return;
    }

    try {
      await api.deleteAgent(agentId);
      showToast("Agent deleted successfully", "success");
      this.loadAgents();

      // Trigger canvas refresh if in canvas mode
      if (globalThis.app?.canvasMode) {
        globalThis.app.loadCanvasAgents();
      }
    } catch (error) {
      showToast("Failed to delete agent", "error");
      console.error("Error deleting agent:", error);
    }
  }
}

export default AgentConfig;
