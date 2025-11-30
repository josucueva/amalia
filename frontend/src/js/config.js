/**
 * API Configuration
 */
const API_BASE_URL =
  window.location.hostname === "localhost" ? "http://localhost:8000" : "/api";

export const API_ENDPOINTS = {
  health: `${API_BASE_URL}/api/health`,
  chat: `${API_BASE_URL}/api/chat`,
  agents: `${API_BASE_URL}/api/agents`,
  files: `${API_BASE_URL}/api/files`,
  canvas: `${API_BASE_URL}/api/canvas`,
  models: `${API_BASE_URL}/api/models`,
  mcpServers: `${API_BASE_URL}/api/mcp-servers`,
  sessions: `${API_BASE_URL}/api/sessions`,
};

export default {
  API_BASE_URL,
  API_ENDPOINTS,
};
