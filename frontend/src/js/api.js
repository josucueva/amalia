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
  async sendMessage(message, conversationId = null) {
    return this.post(API_ENDPOINTS.chat, {
      message,
      conversation_id: conversationId,
      stream: false,
    });
  }

  async getConversationHistory(conversationId) {
    return this.get(`${API_ENDPOINTS.chat}/history/${conversationId}`);
  }

  // Agents API
  async listAgents() {
    return this.get(API_ENDPOINTS.agents);
  }

  async getAgents() {
    // Alias for listAgents to maintain compatibility
    const response = await this.listAgents();
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

  // Health check
  async healthCheck() {
    return this.get(API_ENDPOINTS.health);
  }
}

export default new ApiClient();
