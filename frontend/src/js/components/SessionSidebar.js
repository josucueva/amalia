/**
 * Session sidebar component for managing chat sessions
 */
import api from "../api.js";
import state from "../utils/state.js";
import { showToast } from "../utils/helpers.js";

class SessionSidebar {
  constructor() {
    this.container = null;
    this.isOpen = false;
  }

  async init() {
    // Create sidebar HTML
    this.createSidebar();

    // Load sessions
    await this.loadSessions();

    // Subscribe to state changes
    state.subscribe((newState) => {
      if (newState.currentSession) {
        this.updateActiveSession(newState.currentSession.id);
      }
    });
  }

  createSidebar() {
    // Create sidebar container
    const sidebar = document.createElement("div");
    sidebar.id = "session-sidebar";
    sidebar.className = "session-sidebar";
    sidebar.innerHTML = `
      <div class="session-sidebar-content">
        <button class="btn btn-primary btn-block" id="new-session-btn" title="New Session">
          + New Session
        </button>
        <div class="session-list" id="session-list">
          <!-- Sessions will be populated here -->
        </div>
      </div>
    `;

    // Add to page
    document.body.appendChild(sidebar);
    this.container = sidebar;

    // Connect to header toggle button
    const toggleBtn = document.getElementById("toggle-sessions-btn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => this.toggle());
    }

    // Add event listeners
    document
      .getElementById("new-session-btn")
      .addEventListener("click", () => this.createNewSession());
  }

  async loadSessions() {
    try {
      const response = await api.listSessions("active", 20);
      const sessions = response.sessions;

      state.setState({ sessions });
      this.renderSessions(sessions);
    } catch (error) {
      console.error("Error loading sessions:", error);
      showToast("Failed to load sessions", "error");
    }
  }

  renderSessions(sessions) {
    const sessionList = document.getElementById("session-list");
    if (!sessionList) return;

    if (sessions.length === 0) {
      sessionList.innerHTML = `
        <div class="empty-sessions">
          <p>No sessions yet</p>
          <p class="hint">Click + to create one</p>
        </div>
      `;
      return;
    }

    sessionList.innerHTML = sessions
      .map(
        (session) => `
      <div class="session-item ${
        state.getState().currentSession?.id === session.id ? "active" : ""
      }"
           data-session-id="${session.id}">
        <div class="session-item-content">
          <div class="session-title">${this.escapeHtml(session.title)}</div>
          <div class="session-meta">
            ${
              session.pipelines?.length
                ? `${session.pipelines.length} pipeline${
                    session.pipelines.length !== 1 ? "s" : ""
                  }`
                : "No pipelines"
            }
          </div>
        </div>
        <div class="session-actions">
          <button class="session-action-btn delete-btn" data-session-id="${
            session.id
          }" title="Delete">[ DELETE ]</button>
        </div>
      </div>
    `
      )
      .join("");

    // Add event listeners
    sessionList.querySelectorAll(".session-item").forEach((item) => {
      const sessionId = item.dataset.sessionId;

      // Click to switch session
      const contentDiv = item.querySelector(".session-item-content");
      if (contentDiv) {
        contentDiv.addEventListener("click", () => {
          this.switchSession(sessionId);
        });
      }

      // Delete button
      const deleteBtn = item.querySelector(".delete-btn");
      if (deleteBtn) {
        deleteBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.deleteSession(sessionId);
        });
      }
    });
  }

  async createNewSession() {
    try {
      const session = await api.createSession();
      state.setState({ currentSession: session });

      // Clear chat messages
      if (globalThis.chat) {
        globalThis.chat.clearMessages();
      }

      // Reload sessions list
      await this.loadSessions();

      showToast("New session created", "success");
    } catch (error) {
      console.error("Error creating session:", error);
      showToast("Failed to create session", "error");
    }
  }

  async switchSession(sessionId) {
    try {
      const session = await api.getSession(sessionId);
      state.setState({ currentSession: session });

      // Load session messages into chat
      if (globalThis.chat) {
        globalThis.chat.clearMessages();

        if (session.messages && session.messages.length > 0) {
          session.messages.forEach((msg) => {
            globalThis.chat.addMessage({
              role: msg.role,
              content: msg.content,
              timestamp: msg.timestamp,
            });
          });
        }

        // Load last pipeline if in canvas mode
        if (
          globalThis.app?.canvasMode &&
          session.pipelines &&
          session.pipelines.length > 0
        ) {
          const lastPipeline = session.pipelines[session.pipelines.length - 1];
          await globalThis.app.createPipelineFromData(
            lastPipeline.nodes,
            lastPipeline.connections
          );
        }
      }

      showToast(`Switched to: ${session.title}`, "success");
    } catch (error) {
      console.error("Error switching session:", error);
      showToast("Failed to switch session", "error");
    }
  }

  async deleteSession(sessionId) {
    if (!confirm("Delete this session? This cannot be undone.")) return;

    try {
      await api.deleteSession(sessionId);

      // If deleting current session, create new one
      if (state.getState().currentSession?.id === sessionId) {
        await this.createNewSession();
      }

      // Reload sessions list
      await this.loadSessions();

      showToast("Session deleted", "success");
    } catch (error) {
      console.error("Error deleting session:", error);
      showToast("Failed to delete session", "error");
    }
  }

  updateActiveSession(sessionId) {
    const items = document.querySelectorAll(".session-item");
    items.forEach((item) => {
      if (item.dataset.sessionId === sessionId) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });
  }

  toggle() {
    this.isOpen = !this.isOpen;
    if (this.container) {
      this.container.classList.toggle("open", this.isOpen);
    }
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

export default SessionSidebar;
