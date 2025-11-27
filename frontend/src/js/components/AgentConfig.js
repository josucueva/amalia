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
    this.currentAgentData = null; // Store original agent data to preserve metadata
    this.mcpServers = {}; // Store MCP server configurations

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
    this.initMCPSection();
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
      addMCPBtn.addEventListener("click", () => this.openMCPConfigPanel());
    }

    // MCP config panel handlers
    const closeMCPConfig = document.getElementById("close-mcp-config");
    const cancelMCPServer = document.getElementById("cancel-mcp-server");
    const mcpServerForm = document.getElementById("mcp-server-form");

    if (closeMCPConfig) {
      closeMCPConfig.addEventListener("click", () =>
        this.closeMCPConfigPanel()
      );
    }

    if (cancelMCPServer) {
      cancelMCPServer.addEventListener("click", () =>
        this.closeMCPConfigPanel()
      );
    }

    if (mcpServerForm) {
      mcpServerForm.addEventListener("submit", (e) =>
        this.handleMCPServerSubmit(e)
      );
    }
  }

  openMCPConfigPanel() {
    const modalContainer = document.querySelector(".agent-modal-container");

    if (modalContainer) {
      modalContainer.classList.add("mcp-panel-active");
    }
  }

  closeMCPConfigPanel() {
    const modalContainer = document.querySelector(".agent-modal-container");
    const form = document.getElementById("mcp-server-form");

    if (modalContainer) {
      modalContainer.classList.remove("mcp-panel-active");
    }

    // Wait for animation to complete before resetting form
    setTimeout(() => {
      if (form) {
        form.reset();
      }
    }, 300);
  }

  handleMCPServerSubmit(e) {
    e.preventDefault();

    const name = document.getElementById("mcp-server-name").value.trim();
    const command = document.getElementById("mcp-server-command").value.trim();
    const argsText = document.getElementById("mcp-server-args").value.trim();
    const envText = document.getElementById("mcp-server-env").value.trim();

    // Parse arguments (one per line)
    const args = argsText
      ? argsText
          .split("\n")
          .map((a) => a.trim())
          .filter((a) => a)
      : [];

    // Parse environment variables (JSON)
    let env = null;
    if (envText) {
      try {
        env = JSON.parse(envText);
      } catch (error) {
        alert(
          "Invalid JSON in environment variables. Please check the format."
        );
        return;
      }
    }

    // Add server to collection
    this.mcpServers[name] = {
      command,
      args,
      env,
    };

    // Update the server list display
    this.renderMCPServers();

    // Close the panel
    this.closeMCPConfigPanel();
  }

  showAddMCPServerDialog() {
    const name = prompt("Server name:");
    if (!name || !name.trim()) return;

    const command = prompt("Command to run:");
    if (!command || !command.trim()) return;

    const argsInput = prompt("Arguments (comma-separated, optional):");
    const args = argsInput ? argsInput.split(",").map((a) => a.trim()) : [];

    this.mcpServers[name.trim()] = {
      command: command.trim(),
      args: args,
      env: null,
    };

    this.renderMCPServers();
  }

  renderMCPServers() {
    const container = document.getElementById("mcp-servers-list");
    if (!container) return;

    if (Object.keys(this.mcpServers).length === 0) {
      container.innerHTML = `
        <div class="mcp-empty-state">
          No MCP servers configured. Click "Add MCP Server" to connect tools.
        </div>
      `;
      return;
    }

    container.innerHTML = Object.entries(this.mcpServers)
      .map(
        ([name, config]) => `
        <div class="mcp-server-item" data-server-name="${name}">
          <div class="mcp-server-info">
            <div class="mcp-server-name">${name}</div>
            <div class="mcp-server-command">${
              config.command
            } ${config.args.join(" ")}</div>
          </div>
          <button class="mcp-server-remove" data-server-name="${name}">✕</button>
        </div>
      `
      )
      .join("");

    // Add remove handlers
    container.querySelectorAll(".mcp-server-remove").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const serverName = e.target.dataset.serverName;
        delete this.mcpServers[serverName];
        this.renderMCPServers();
      });
    });
  }

  openModal(agent = null, updateCallback = null) {
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

      document.getElementById("agent-model").value = agent.config.model;
      document.getElementById("agent-prompt").value =
        agent.config.system_prompt;
      document.getElementById("agent-a2a").checked = agent.config.a2a_enabled;

      // Load MCP servers
      this.mcpServers = agent.config.mcp_servers || {};
      this.renderMCPServers();
    } else {
      // Reset MCP servers for new agent
      this.mcpServers = {};
      this.renderMCPServers();
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
    this.mcpServers = {}; // Clear MCP servers
    document.getElementById("icon-preview").style.display = "none";

    // Close MCP config panel if open
    const modalContainer = document.querySelector(".agent-modal-container");
    if (modalContainer) {
      modalContainer.classList.remove("mcp-panel-active");
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
      mcp_servers: this.mcpServers, // Include MCP servers
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
}

export default AgentConfig;
