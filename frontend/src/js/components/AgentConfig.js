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

    this.init();
    this.loadAgents();
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

  openModal(agent = null) {
    this.currentAgentId = agent ? agent.id : null;

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
  }

  async handleSubmit(e) {
    e.preventDefault();

    const config = {
      name: document.getElementById("agent-name").value,
      description: document.getElementById("agent-description").value,
      model: document.getElementById("agent-model").value,
      system_prompt: document.getElementById("agent-prompt").value,
      a2a_enabled: document.getElementById("agent-a2a").checked,
      tools: [],
    };

    try {
      if (this.currentAgentId) {
        // Update existing agent
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
      if (window.app && window.app.canvasMode) {
        window.app.loadCanvasAgents();
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
      if (window.app && window.app.canvasMode) {
        window.app.loadCanvasAgents();
      }
    } catch (error) {
      showToast("Failed to delete agent", "error");
      console.error("Error deleting agent:", error);
    }
  }
}

export default AgentConfig;
