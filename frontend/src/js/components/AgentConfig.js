/**
 * Agent Configuration Component
 */
import api from "../api.js";
import state from "../utils/state.js";
import { showToast } from "../utils/helpers.js";
import modelConfig from "./ModelConfig.js";
import mcpServerManager from "./MCPServerManager.js";

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
    this.currentAgentData = null; // Store original agent data to preserve metadata
    this.selectedMCPServerIds = []; // Store selected MCP server IDs
    this.availableMCPServers = []; // Store available MCP servers
    this.models = []; // Available models from API

    // Model selector elements
    this.modelSelect = document.getElementById("agent-model");
    this.addModelBtn = document.getElementById("add-model-btn");
    this.editModelBtn = document.getElementById("edit-model-btn");
    this.deleteModelBtn = document.getElementById("delete-model-btn");

    // Icon picker elements
    this.iconPickerModal = document.getElementById("icon-picker-modal");
    this.iconPickerGrid = document.getElementById("icon-picker-grid");
    this.selectIconBtn = document.getElementById("select-icon-btn");
    this.clearIconBtn = document.getElementById("clear-icon-btn");
    this.closeIconPickerBtn = document.getElementById("close-icon-picker");
    this.selectedIcon = null;

    this.init();
    this.loadAgents();
    this.loadModels();
    this.loadMCPServers();
    this.initIconPicker();
    this.initMCPSection();
    this.initModelSection();
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

  initMCPSection() {
    const addMCPBtn = document.getElementById("add-mcp-server-btn");
    if (addMCPBtn) {
      addMCPBtn.addEventListener("click", () => {
        mcpServerManager.open(null, () => {
          this.loadMCPServers();
        });
      });
    }
  }

  async openModal(agent = null, updateCallback = null) {
    this.currentAgentId = agent ? agent.id : null;
    this.currentAgentData = agent; // Store original agent data
    this.instanceUpdateCallback = updateCallback; // Store callback for canvas instances

    // Check if this is a hidden/system agent
    const isHidden = agent?.config?.metadata?.is_hidden === true;

    // Update modal title
    const modalTitle = this.agentModal.querySelector(".modal-header h2");
    if (modalTitle) {
      modalTitle.textContent = "Agent Details";
    }

    // Update submit button text
    const submitBtn = this.agentForm.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.textContent = agent ? "Update Agent" : "Create Agent";
    }

    // Hide/show icon input for hidden agents
    const iconFormGroup = document
      .querySelector('label[for="agent-icon"]')
      ?.closest(".form-group");
    if (iconFormGroup) {
      iconFormGroup.style.display = isHidden ? "none" : "block";
    }

    // Ensure models and MCP servers are loaded before populating
    await Promise.all([this.loadModels(), this.loadMCPServers()]);

    if (agent) {
      // Populate form with agent data
      document.getElementById("agent-name").value = agent.config.name;
      document.getElementById("agent-description").value =
        agent.config.description;

      // Only set icon for non-hidden agents
      if (!isHidden) {
        document.getElementById("agent-icon").value = agent.config.icon || "";
        this.selectedIcon = agent.config.icon || null;
      }

      // Hide icon preview - we only show the icon name in the input
      document.getElementById("icon-preview").style.display = "none";

      // Set model value - ensure it's set after dropdown is populated
      const modelSelect = document.getElementById("agent-model");
      if (modelSelect && agent.config.model) {
        modelSelect.value = agent.config.model;
        // If the value didn't set (model not in dropdown), log a warning
        if (modelSelect.value !== agent.config.model) {
          console.warn(
            `Model ${agent.config.model} not found in dropdown, available models:`,
            Array.from(modelSelect.options).map((opt) => opt.value)
          );
        }
      }

      document.getElementById("agent-prompt").value =
        agent.config.system_prompt;
      document.getElementById("agent-a2a").checked = agent.config.a2a_enabled;

      // Load selected MCP servers
      this.selectedMCPServerIds = agent.config.mcp_server_ids || [];

      // Legacy: Support old mcp_servers format
      if (
        agent.config.mcp_servers &&
        Object.keys(agent.config.mcp_servers).length > 0 &&
        this.selectedMCPServerIds.length === 0
      ) {
        this.selectedMCPServerIds = Object.keys(agent.config.mcp_servers);
      }

      this.renderMCPServersList();
    } else {
      // Reset MCP servers for new agent
      this.selectedMCPServerIds = [];
      this.renderMCPServersList();

      // Set default model if none selected
      if (this.models && this.models.length > 0 && this.modelSelect) {
        // Try to find the default model from config (gemini-2.5-flash)
        const defaultModel = this.models.find(
          (m) => m.id === "gemini-2.5-flash"
        );
        if (defaultModel) {
          this.modelSelect.value = defaultModel.model_name;
        } else {
          // Fall back to first available model
          const firstAvailable = this.models.find((m) => m.is_available);
          if (firstAvailable) {
            this.modelSelect.value = firstAvailable.model_name;
          } else if (this.models[0]) {
            // Last resort: just use first model
            this.modelSelect.value = this.models[0].model_name;
          }
        }
      }
    }

    this.agentModal.style.display = "flex";
  }

  closeModal() {
    this.agentModal.style.display = "none";
    this.agentForm.reset();
    this.currentAgentId = null;
    this.currentAgentData = null; // Clear stored agent data
    this.instanceUpdateCallback = null; // Clear callback
    this.selectedIcon = null;
    this.selectedMCPServerIds = []; // Clear selected MCP servers
    document.getElementById("icon-preview").style.display = "none";

    // Close MCP config panel and model config panel if open
    const modalContainer = document.querySelector(".agent-modal-container");
    if (modalContainer) {
      modalContainer.classList.remove("mcp-panel-active");
      modalContainer.classList.remove("model-panel-active");
    }

    // Reset icon form group visibility
    const iconFormGroup = document
      .querySelector('label[for="agent-icon"]')
      ?.closest(".form-group");
    if (iconFormGroup) {
      iconFormGroup.style.display = "block";
    }
  }

  async handleSubmit(e) {
    e.preventDefault();

    // Build config object, preserving original fields if updating
    const config = {
      name: document.getElementById("agent-name").value,
      description: document.getElementById("agent-description").value,
      icon: document.getElementById("agent-icon").value || null,
      model: document.getElementById("agent-model").value,
      system_prompt: document.getElementById("agent-prompt").value,
      a2a_enabled: document.getElementById("agent-a2a").checked,
      tools: this.currentAgentData?.config?.tools || [],
      mcp_server_ids: this.selectedMCPServerIds, // Use new server IDs
      mcp_servers: {}, // Clear legacy mcp_servers when using new system
      // Preserve communication and metadata from original agent
      communication: this.currentAgentData?.config?.communication || {
        can_receive_from: ["*"],
        can_send_to: [],
      },
      metadata: this.currentAgentData?.config?.metadata || {},
      temperature: this.currentAgentData?.config?.temperature || 0.7,
      max_tokens: this.currentAgentData?.config?.max_tokens || 2000,
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

  // Model Management Methods
  initModelSection() {
    // Add click handler for add model button
    if (this.addModelBtn) {
      this.addModelBtn.addEventListener("click", () => {
        modelConfig.open((newModel) => {
          // Callback when model is added
          this.loadModels();
        });
      });
    }

    // Edit model button
    if (this.editModelBtn) {
      this.editModelBtn.addEventListener("click", () => {
        const selectedOption =
          this.modelSelect.options[this.modelSelect.selectedIndex];
        if (!selectedOption || !selectedOption.dataset.modelId) {
          showToast("Please select a model to edit", "info");
          return;
        }

        const modelId = selectedOption.dataset.modelId;
        const model = this.models.find((m) => m.id === modelId);

        if (model) {
          modelConfig.open((updatedModel) => {
            // Callback when model is updated
            this.loadModels();
          }, model);
        }
      });
    }

    // Delete model button
    if (this.deleteModelBtn) {
      this.deleteModelBtn.addEventListener("click", async () => {
        const selectedOption =
          this.modelSelect.options[this.modelSelect.selectedIndex];
        if (!selectedOption || !selectedOption.dataset.modelId) {
          showToast("Please select a model to delete", "info");
          return;
        }

        const modelId = selectedOption.dataset.modelId;
        const model = this.models.find((m) => m.id === modelId);

        if (!model) return;

        const confirmed = confirm(
          `Are you sure you want to delete the model "${model.display_name}"?\n\nThis will NOT delete the API key from your .env file.`
        );

        if (confirmed) {
          try {
            await api.deleteModel(modelId);
            showToast(
              `Model "${model.display_name}" deleted successfully`,
              "success"
            );
            await this.loadModels();
          } catch (error) {
            console.error("Error deleting model:", error);
            showToast("Failed to delete model", "error");
          }
        }
      });
    }
  }

  async loadModels() {
    try {
      const response = await api.listModels(false); // Load ALL models, not just available ones
      this.models = response.models || [];
      this.populateModelDropdown();
    } catch (error) {
      console.error("Error loading models:", error);
      showToast("Failed to load models", "error");
    }
  }

  populateModelDropdown() {
    if (!this.modelSelect) return;

    const currentValue = this.modelSelect.value;

    // Clear existing options
    this.modelSelect.innerHTML = "";

    // If no models loaded yet, show a placeholder
    if (!this.models || this.models.length === 0) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Loading models...";
      this.modelSelect.appendChild(option);
      return;
    }

    // Add models from API, showing availability status
    this.models.forEach((model) => {
      const option = document.createElement("option");
      option.value = model.model_name;
      // Show availability indicator in the display name
      const availabilityIndicator = model.is_available ? "✓" : "⚠";
      option.textContent = `${availabilityIndicator} ${model.display_name}`;
      option.dataset.modelId = model.id;
      option.dataset.available = model.is_available;

      // Add a hint in the title for unavailable models
      if (!model.is_available) {
        option.title = `API key not configured: ${
          model.api_key_name || "unknown"
        }`;
      }

      this.modelSelect.appendChild(option);
    });

    // Restore selection if it exists in the new list
    if (currentValue) {
      const matchingOption = Array.from(this.modelSelect.options).find(
        (opt) => opt.value === currentValue
      );
      if (matchingOption) {
        this.modelSelect.value = currentValue;
        return;
      }
    }

    // If no current value or it doesn't exist anymore, set default
    if (!this.modelSelect.value || this.modelSelect.value === "") {
      // Try to select gemini-2.5-flash as default
      const defaultModel = this.models.find((m) => m.id === "gemini-2.5-flash");
      if (defaultModel) {
        this.modelSelect.value = defaultModel.model_name;
      } else {
        // Fall back to first available model
        const firstAvailable = this.models.find((m) => m.is_available);
        if (firstAvailable) {
          this.modelSelect.value = firstAvailable.model_name;
        }
      }
    }
  }

  async loadMCPServers() {
    try {
      const response = await api.listMCPServers(true); // Only available servers
      this.availableMCPServers = response.servers || [];
      this.renderMCPServersList();
    } catch (error) {
      console.error("Error loading MCP servers:", error);
      showToast("Failed to load MCP servers", "error");
    }
  }

  renderMCPServersList() {
    const container = document.getElementById("mcp-servers-list");
    if (!container) return;

    container.innerHTML = "";

    if (this.availableMCPServers.length === 0) {
      container.innerHTML = `
        <div style="padding: 1rem; text-align: center; color: #6b7280;">
          No MCP servers available. Add one to get started.
        </div>
      `;
      return;
    }

    this.availableMCPServers.forEach((server) => {
      const isSelected = this.selectedMCPServerIds.includes(server.id);

      const serverItem = document.createElement("div");
      serverItem.className = `mcp-server-item ${isSelected ? "selected" : ""}`;
      serverItem.innerHTML = `
        <div class="mcp-server-checkbox">
          <input type="checkbox" id="mcp-${server.id}" ${
        isSelected ? "checked" : ""
      } data-server-id="${server.id}">
          <label for="mcp-${server.id}">
            <div class="mcp-server-name">${server.name}</div>
            ${
              server.description
                ? `<div class="mcp-server-description">${server.description}</div>`
                : ""
            }
          </label>
        </div>
        <div class="mcp-server-actions">
          <button type="button" class="icon-btn edit-mcp-server" data-server-id="${
            server.id
          }" title="Edit server">
            <i data-lucide="edit-2"></i>
          </button>
          <button type="button" class="icon-btn delete-mcp-server" data-server-id="${
            server.id
          }" title="Delete server">
            <i data-lucide="trash-2"></i>
          </button>
        </div>
      `;

      container.appendChild(serverItem);

      // Add event listeners
      const checkbox = serverItem.querySelector("input[type='checkbox']");
      checkbox?.addEventListener("change", (e) => {
        if (e.target.checked) {
          if (!this.selectedMCPServerIds.includes(server.id)) {
            this.selectedMCPServerIds.push(server.id);
          }
        } else {
          this.selectedMCPServerIds = this.selectedMCPServerIds.filter(
            (id) => id !== server.id
          );
        }
        serverItem.classList.toggle("selected", e.target.checked);
      });

      const editBtn = serverItem.querySelector(".edit-mcp-server");
      editBtn?.addEventListener("click", () => this.editMCPServer(server.id));

      const deleteBtn = serverItem.querySelector(".delete-mcp-server");
      deleteBtn?.addEventListener("click", () =>
        this.deleteMCPServer(server.id)
      );
    });

    // Reinitialize Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  editMCPServer(serverId) {
    mcpServerManager.open(serverId, () => {
      this.loadMCPServers();
    });
  }

  async deleteMCPServer(serverId) {
    const server = this.availableMCPServers.find((s) => s.id === serverId);
    if (!server) return;

    if (!confirm(`Are you sure you want to delete "${server.name}"?`)) {
      return;
    }

    try {
      await api.deleteMCPServer(serverId);
      showToast(`MCP server "${server.name}" deleted successfully`, "success");
      this.selectedMCPServerIds = this.selectedMCPServerIds.filter(
        (id) => id !== serverId
      );
      this.loadMCPServers();
    } catch (error) {
      console.error("Error deleting MCP server:", error);
      showToast("Failed to delete MCP server", "error");
    }
  }
}

export default AgentConfig;
