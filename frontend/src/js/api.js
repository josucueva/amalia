/**
 * API Client for backend communication
 */
import { API_ENDPOINTS } from "./config.js";

class ApiClient {
  /**
   * Make a GET request
   */
  async get(url) {
    try {
      const response = await fetch(url, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("GET request failed:", error);
      throw error;
    }
  }

  /**
   * Make a POST request
   */
  async post(url, data) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("POST request failed:", error);
      throw error;
    }
  }

  /**
   * Make a DELETE request
   */
  async delete(url) {
    try {
      const response = await fetch(url, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("DELETE request failed:", error);
      throw error;
    }
  }

  /**
   * Make a PUT request
   */
  async put(url, data) {
    try {
      const response = await fetch(url, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("PUT request failed:", error);
      throw error;
    }
  }

  /**
   * Upload a file
   */
  async uploadFile(file) {
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_ENDPOINTS.files}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error("File upload failed:", error);
      throw error;
    }
  }

  // Chat API
  async sendMessage(requestData) {
    // Support both old format (message, conversationId) and new format (requestData object)
    if (typeof requestData === "string") {
      // Old format: sendMessage(message, conversationId)
      const message = requestData;
      const conversationId = arguments[1] || null;
      requestData = {
        message,
        conversation_id: conversationId,
        stream: false,
      };
    }

    return this.post(API_ENDPOINTS.chat, requestData);
  }

  async getConversationHistory(conversationId) {
    return this.get(`${API_ENDPOINTS.chat}/history/${conversationId}`);
  }

  // Agents API
  async listAgents(includeHidden = false) {
    const url = includeHidden
      ? `${API_ENDPOINTS.agents}?include_hidden=true`
      : API_ENDPOINTS.agents;
    return this.get(url);
  }

  async getAgents(includeHidden = false) {
    // Alias for listAgents to maintain compatibility
    const response = await this.listAgents(includeHidden);
    return response.agents || [];
  }

  async getAgent(agentId) {
    return this.get(`${API_ENDPOINTS.agents}/${agentId}`);
  }

  async createAgent(config) {
    return this.post(API_ENDPOINTS.agents, { config });
  }

  async updateAgent(agentId, config) {
    return this.put(`${API_ENDPOINTS.agents}/${agentId}`, { config });
  }

  async deleteAgent(agentId) {
    return this.delete(`${API_ENDPOINTS.agents}/${agentId}`);
  }

  async reloadAgentsFromYaml() {
    return this.post(`${API_ENDPOINTS.agents}/reload-from-yaml`, {});
  }

  // Files API
  async listFiles() {
    return this.get(`${API_ENDPOINTS.files}/list`);
  }

  async deleteFile(fileId) {
    return this.delete(`${API_ENDPOINTS.files}/${fileId}`);
  }

  // Canvas API
  async buildPipeline(command) {
    return this.post(`${API_ENDPOINTS.canvas}/build`, {
      command,
    });
  }

  // Models API
  async listModels(availableOnly = false) {
    const url = availableOnly
      ? `${API_ENDPOINTS.models}?available_only=true`
      : API_ENDPOINTS.models;
    return this.get(url);
  }

  async getModel(modelId) {
    return this.get(`${API_ENDPOINTS.models}/${modelId}`);
  }

  async addModel(data) {
    return this.post(API_ENDPOINTS.models, data);
  }

  async updateModel(modelId, data) {
    return this.put(`${API_ENDPOINTS.models}/${modelId}`, data);
  }

  async deleteModel(modelId) {
    return this.delete(`${API_ENDPOINTS.models}/${modelId}`);
  }

  // MCP Server API methods
  async listMCPServers(availableOnly = false) {
    const url = availableOnly
      ? `${API_ENDPOINTS.mcpServers}?available_only=true`
      : API_ENDPOINTS.mcpServers;
    return this.get(url);
  }

  async getMCPServer(serverId) {
    return this.get(`${API_ENDPOINTS.mcpServers}/${serverId}`);
  }

  async addMCPServer(data) {
    return this.post(API_ENDPOINTS.mcpServers, data);
  }

  async updateMCPServer(serverId, data) {
    return this.put(`${API_ENDPOINTS.mcpServers}/${serverId}`, data);
  }

  async deleteMCPServer(serverId) {
    return this.delete(`${API_ENDPOINTS.mcpServers}/${serverId}`);
  }

  // Sessions API
  async createSession(title = null) {
    return this.post(API_ENDPOINTS.sessions, { title });
  }

  async listSessions(status = null, limit = null) {
    let url = API_ENDPOINTS.sessions;
    const params = [];
    if (status) params.push(`status=${status}`);
    if (limit) params.push(`limit=${limit}`);
    if (params.length > 0) url += `?${params.join("&")}`;
    return this.get(url);
  }

  async getSession(sessionId) {
    return this.get(`${API_ENDPOINTS.sessions}/${sessionId}`);
  }

  async updateSession(sessionId, data) {
    return this.put(`${API_ENDPOINTS.sessions}/${sessionId}`, data);
  }

  async deleteSession(sessionId) {
    return this.delete(`${API_ENDPOINTS.sessions}/${sessionId}`);
  }

  async addMessageToSession(sessionId, role, content, metadata = null) {
    return this.post(`${API_ENDPOINTS.sessions}/${sessionId}/messages`, {
      role,
      content,
      metadata,
    });
  }

  async addPipelineToSession(sessionId, nodes, connections) {
    return this.post(`${API_ENDPOINTS.sessions}/${sessionId}/pipelines`, {
      nodes,
      connections,
    });
  }

  async clearSessionMessages(sessionId) {
    return this.delete(`${API_ENDPOINTS.sessions}/${sessionId}/messages`);
  }

  // Health check
  async healthCheck() {
    return this.get(API_ENDPOINTS.health);
  }
}

export default new ApiClient();
