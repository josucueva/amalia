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
        </div>
        <div class="session-actions">
          <button class="session-action-btn edit-btn" data-session-id="${
            session.id
          }" title="Edit">[ EDIT ]</button>
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

      // Edit button
      const editBtn = item.querySelector(".edit-btn");
      if (editBtn) {
        editBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.editSession(sessionId);
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

      // Clear chat and show welcome message
      if (globalThis.chat) {
        globalThis.chat.clearMessages();
        globalThis.chat.showWelcomeMessage();
      }

      // Clear canvas and show welcome message if in canvas mode
      if (globalThis.app && globalThis.app.canvasMode) {
        globalThis.app.clearCanvas();
        globalThis.app.showCanvasWelcome();
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
      const currentSession = state.getState().currentSession;

      // Don't switch if already on this session
      if (currentSession?.id === sessionId) {
        console.log("Already on session:", sessionId);
        return;
      }

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
        } else {
          globalThis.chat.showWelcomeMessage();
        }
      }

      // Clear canvas and load session-specific pipeline
      if (globalThis.app) {
        // Clear existing canvas
        if (globalThis.app.canvasMode) {
          globalThis.app.clearCanvas();
          if (!session.pipelines || session.pipelines.length === 0) {
            globalThis.app.showCanvasWelcome();
          }
        }

        // Load last pipeline if in canvas mode and session has pipelines
        if (
          globalThis.app.canvasMode &&
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

      // Update active session indicator
      this.updateActiveSession(sessionId);

      console.log("✓ Switched to session:", sessionId);
      showToast(`Switched to: ${session.title}`, "success");
    } catch (error) {
      console.error("Error switching session:", error);
      showToast("Failed to switch session", "error");
    }
  }

  async editSession(sessionId) {
    try {
      const sessions = state.getState().sessions;
      const session = sessions.find((s) => s.id === sessionId);
      if (!session) return;

      const newTitle = prompt("Enter new session title:", session.title);
      if (!newTitle || newTitle.trim() === "") return;
      if (newTitle.trim() === session.title) return;

      await api.updateSession(sessionId, { title: newTitle.trim() });

      // Update current session if editing the active one
      if (state.getState().currentSession?.id === sessionId) {
        const updatedSession = await api.getSession(sessionId);
        state.setState({ currentSession: updatedSession });
      }

      // Reload sessions list
      await this.loadSessions();

      showToast("Session renamed", "success");
    } catch (error) {
      console.error("Error editing session:", error);
      showToast("Failed to rename session", "error");
    }
  }

  async deleteSession(sessionId) {
    if (!confirm("Delete this session? This cannot be undone.")) return;

    try {
      await api.deleteSession(sessionId);

      // If deleting current session, clear it and show welcome state
      if (state.getState().currentSession?.id === sessionId) {
        state.setState({ currentSession: null });

        // Clear chat and show welcome message
        if (globalThis.chat) {
          globalThis.chat.clearMessages();
          globalThis.chat.showWelcomeMessage();
        }

        // Clear canvas and show welcome message
        if (globalThis.app && globalThis.app.canvasMode) {
          globalThis.app.clearCanvas();
          globalThis.app.showCanvasWelcome();
        }
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
