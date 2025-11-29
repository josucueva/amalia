/**
 * MCP Server Management Component
 * Manages MCP server configurations with persistence
 */
import api from "../api.js";
import { showToast } from "../utils/helpers.js";

class MCPServerManager {
  constructor() {
    this.panel = document.getElementById("mcp-config-panel");
    this.agentModal = document.querySelector(".agent-modal-container");
    this.form = document.getElementById("mcp-server-form");
    this.closeBtn = document.getElementById("close-mcp-config");
    this.cancelBtn = document.getElementById("cancel-mcp-server");
    this.isOpen = false;
    this.editingServerId = null;
    this.onServerSaved = null;

    this.init();
  }

  init() {
    if (!this.panel || !this.form) return;

    this.attachEventListeners();
  }

  attachEventListeners() {
    // Close button
    this.closeBtn?.addEventListener("click", () => this.close());

    // Cancel button
    this.cancelBtn?.addEventListener("click", () => this.close());

    // Form submit
    this.form?.addEventListener("submit", (e) => this.handleSubmit(e));
  }

  async handleSubmit(e) {
    e.preventDefault();

    const formData = {
      name: document.getElementById("mcp-server-name").value.trim(),
      command: document.getElementById("mcp-server-command").value.trim(),
      args: this.parseArgs(
        document.getElementById("mcp-server-args").value.trim()
      ),
      env: this.parseEnv(
        document.getElementById("mcp-server-env").value.trim()
      ),
      description:
        document.getElementById("mcp-server-description")?.value.trim() || null,
    };

    if (!formData.name || !formData.command) {
      showToast("Name and command are required", "error");
      return;
    }

    try {
      let server;
      if (this.editingServerId) {
        // Update existing server
        server = await api.updateMCPServer(this.editingServerId, formData);
        showToast(
          `MCP server "${server.name}" updated successfully`,
          "success"
        );
      } else {
        // Create new server
        server = await api.addMCPServer(formData);
        showToast(`MCP server "${server.name}" added successfully`, "success");
      }

      // Call callback if provided
      if (this.onServerSaved) {
        this.onServerSaved(server);
      }

      this.close();
    } catch (error) {
      console.error("Error saving MCP server:", error);
      showToast(error.message || "Failed to save MCP server", "error");
    }
  }

  parseArgs(argsText) {
    if (!argsText) return [];
    return argsText
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line);
  }

  parseEnv(envText) {
    if (!envText) return null;
    try {
      return JSON.parse(envText);
    } catch (error) {
      showToast("Invalid JSON in environment variables", "error");
      throw error;
    }
  }

  open(serverId = null, callback = null) {
    this.isOpen = true;
    this.editingServerId = serverId;
    this.onServerSaved = callback;

    // Add class to agent modal container to show the panel
    if (this.agentModal) {
      this.agentModal.classList.add("mcp-panel-active");
    }

    // If editing, load server data
    if (serverId) {
      this.loadServerData(serverId);
    } else {
      this.form?.reset();
    }
  }

  async loadServerData(serverId) {
    try {
      const server = await api.getMCPServer(serverId);

      document.getElementById("mcp-server-name").value = server.name;
      document.getElementById("mcp-server-command").value = server.command;
      document.getElementById("mcp-server-args").value = (
        server.args || []
      ).join("\n");
      document.getElementById("mcp-server-env").value = server.env
        ? JSON.stringify(server.env, null, 2)
        : "";
      if (document.getElementById("mcp-server-description")) {
        document.getElementById("mcp-server-description").value =
          server.description || "";
      }
    } catch (error) {
      console.error("Error loading MCP server:", error);
      showToast("Failed to load MCP server data", "error");
      this.close();
    }
  }

  close() {
    this.isOpen = false;
    this.editingServerId = null;

    // Remove class from agent modal container to hide the panel
    if (this.agentModal) {
      this.agentModal.classList.remove("mcp-panel-active");
    }

    // Wait for animation before resetting
    setTimeout(() => {
      this.form?.reset();
    }, 300);

    this.onServerSaved = null;
  }
}

// Export singleton instance
export default new MCPServerManager();
