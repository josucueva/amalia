/**
 * Chat Component
 */
import api from "../api.js";
import state from "../utils/state.js";
import { formatTimestamp, sanitizeHTML, showToast } from "../utils/helpers.js";

class Chat {
  constructor() {
    this.messagesContainer = document.getElementById("chat-messages");
    this.chatForm = document.getElementById("chat-form");
    this.chatInput = document.getElementById("chat-input");
    this.sendBtn = document.getElementById("send-btn");

    // Message history for arrow key navigation
    this.messageHistory = [];
    this.historyIndex = -1;

    this.init();
  }

  init() {
    if (this.chatForm) {
      this.chatForm.addEventListener("submit", (e) => this.handleSubmit(e));
    }

    // Handle keyboard shortcuts in chat input
    if (this.chatInput) {
      this.chatInput.addEventListener("keydown", (e) => this.handleKeyDown(e));

      // Auto-resize textarea as user types
      this.chatInput.addEventListener("input", () => {
        this.autoResizeTextarea();
      });

      // Initialize textarea height
      this.autoResizeTextarea();
    }

    // Handle example queries
    const exampleQueries = document.querySelectorAll(".example-query");
    exampleQueries.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this.chatInput) {
          this.chatInput.value = btn.textContent.replaceAll('"', "");
          this.handleSubmit(new Event("submit"));
        }
      });
    });
  }

  autoResizeTextarea() {
    this.chatInput.style.height = "auto";
    this.chatInput.style.height = this.chatInput.scrollHeight + "px";
  }

  handleKeyDown(e) {
    // Shift + Enter: Add new line (default textarea behavior)
    if (e.key === "Enter" && e.shiftKey) {
      // Allow default behavior (new line)
      return;
    }

    // Enter without Shift: Submit form
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      this.handleSubmit(e);
      return;
    }

    // Arrow Up: Previous message in history
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (this.messageHistory.length === 0) return;

      if (this.historyIndex === -1) {
        // Save current input before navigating history
        this.currentDraft = this.chatInput.value;
        this.historyIndex = this.messageHistory.length - 1;
      } else if (this.historyIndex > 0) {
        this.historyIndex--;
      }

      this.chatInput.value = this.messageHistory[this.historyIndex];
      this.autoResizeTextarea();
      // Move cursor to end
      this.chatInput.setSelectionRange(
        this.chatInput.value.length,
        this.chatInput.value.length
      );
      return;
    }

    // Arrow Down: Next message in history
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (this.historyIndex === -1) return;

      if (this.historyIndex < this.messageHistory.length - 1) {
        this.historyIndex++;
        this.chatInput.value = this.messageHistory[this.historyIndex];
      } else {
        // Restore draft or clear
        this.historyIndex = -1;
        this.chatInput.value = this.currentDraft || "";
      }

      this.autoResizeTextarea();
      // Move cursor to end
      this.chatInput.setSelectionRange(
        this.chatInput.value.length,
        this.chatInput.value.length
      );
      return;
    }
  }

  async handleSubmit(e) {
    e.preventDefault();

    const message = this.chatInput.value.trim();
    if (!message) return;

    // Add to message history
    this.messageHistory.push(message);
    this.historyIndex = -1;
    this.currentDraft = "";

    // Clear input and reset height
    this.chatInput.value = "";
    this.autoResizeTextarea();

    // Remove welcome message if present
    const welcomeMsg = this.messagesContainer.querySelector(".welcome-message");
    if (welcomeMsg) {
      welcomeMsg.remove();
    }

    // Add user message to chat
    this.addMessage({
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    });

    // Show typing indicator
    this.showTypingIndicator();

    try {
      // Get or create current session
      let currentSession = state.getState().currentSession;
      const isFirstMessage = !currentSession;

      if (!currentSession) {
        const sessionResponse = await api.createSession();
        currentSession = sessionResponse;
        state.setState({ currentSession });
        console.log("[Session] Created new session:", currentSession.id);
      }

      // Reload session sidebar to show the new session (for first message)
      if (isFirstMessage && globalThis.app?.sessionSidebar) {
        await globalThis.app.sessionSidebar.loadSessions();
      }

      // Get current file from state if one was uploaded
      const currentFile = state.getState().currentFile;

      // DEBUG: Log current file state
      console.log("[DEBUG] Current file from state:", currentFile);

      // Send message to backend with session_id
      const requestData = {
        message,
        session_id: currentSession.id,
        stream: false,
      };

      // Include file info if a file was uploaded
      if (currentFile) {
        requestData.attached_file = {
          filename: currentFile.filename,
          path: currentFile.path,
          size_mb: currentFile.size_mb,
          file_id: currentFile.file_id,
        };
        console.log(
          "[DEBUG] Attaching file to request:",
          requestData.attached_file
        );
      } else {
        console.log("[DEBUG] No file attached to this message");
      }

      const response = await api.sendMessage(requestData);

      // Update session in state
      if (response.message.metadata?.session_id) {
        const updatedSession = await api.getSession(
          response.message.metadata.session_id
        );
        state.setState({ currentSession: updatedSession });
      }

      // Remove typing indicator
      this.removeTypingIndicator();

      // Check if response contains orchestration data
      const orchestration = response.message.metadata?.orchestration;

      if (orchestration?.orchestration) {
        // Pipeline was created by the three-agent system
        await this.handlePipelineCreation(
          response.message.content,
          orchestration.orchestration
        );
      } else {
        // Normal response from interaction agent
        this.addMessage(response.message);
      }
    } catch (error) {
      this.removeTypingIndicator();
      showToast("Failed to send message. Please try again.", "error");
      console.error("Error sending message:", error);
    }
  }

  async handlePipelineCreation(agentMessage, orchestrationData) {
    // Show the agent's message first
    this.addMessage({
      role: "assistant",
      content: agentMessage,
      timestamp: new Date().toISOString(),
    });

    // Trigger canvas update if in canvas mode
    if (globalThis.app?.canvasMode) {
      globalThis.app.createPipelineFromData(
        orchestrationData.nodes,
        orchestrationData.connections
      );
    } else {
      // Store pipeline data for when user switches to canvas mode
      sessionStorage.setItem(
        "pendingPipeline",
        JSON.stringify(orchestrationData)
      );
    }

    showToast("Pipeline created successfully!", "success");
  }

  addMessage(message) {
    // Remove welcome message if it exists
    const welcomeMessage =
      this.messagesContainer.querySelector(".welcome-message");
    if (welcomeMessage) {
      welcomeMessage.remove();
    }

    const messageEl = document.createElement("div");
    messageEl.className = `message ${message.role}`;

    const icon = this.getMessageIcon(message.role);
    const role = message.role.charAt(0).toUpperCase() + message.role.slice(1);

    messageEl.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <span class="message-icon">${icon}</span>
                    <span>${message.agent_id || role}</span>
                </div>
                <div class="message-text">${sanitizeHTML(message.content)}</div>
                <div class="message-timestamp">${formatTimestamp(
                  message.timestamp
                )}</div>
            </div>
        `;

    this.messagesContainer.appendChild(messageEl);
    this.scrollToBottom();
  }

  getMessageIcon(role) {
    const icons = {
      user: "👤",
      assistant: "🤖",
      agent: "⚙️",
      system: "📢",
    };
    return icons[role] || "💬";
  }

  showTypingIndicator() {
    const indicator = document.createElement("div");
    indicator.className = "message assistant typing";
    indicator.id = "typing-indicator";
    indicator.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            </div>
        `;

    this.messagesContainer.appendChild(indicator);
    this.scrollToBottom();
  }

  removeTypingIndicator() {
    const indicator = document.getElementById("typing-indicator");
    if (indicator) {
      indicator.remove();
    }
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  clearMessages() {
    this.messagesContainer.innerHTML = "";
  }

  showWelcomeMessage() {
    if (!this.messagesContainer) return;

    // Remove any previous welcome message to avoid duplicates or bad placement
    const prevWelcome =
      this.messagesContainer.querySelector(".welcome-message");
    if (prevWelcome) prevWelcome.remove();

    const welcomeDiv = document.createElement("div");
    welcomeDiv.className = "welcome-message";
    welcomeDiv.innerHTML = `
      <div class="welcome-content">
        <h2 style="font-family: var(--font-family-display); font-size: var(--font-size-2xl); font-weight: var(--font-weight-bold); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: var(--spacing-md); color: var(--text-primary);">Welcome to Amalia</h2>
        <p style="font-size: var(--font-size-lg); color: var(--text-secondary); margin-bottom: var(--spacing-2xl);">Start a conversation to create your first session</p>
        <div class="welcome-suggestions" style="display: flex; flex-direction: column; gap: var(--spacing-sm); margin-top: var(--spacing-xl);">
          <button class="example-query" style="padding: var(--spacing-md) var(--spacing-lg); background: rgba(255,255,255,0.02); border: var(--border-width) solid var(--border-color); color: var(--text-primary); font-size: var(--font-size-sm); cursor: pointer; transition: all 0.2s ease; text-align: left; font-family: var(--font-family);">"Load and analyze my dataset"</button>
          <button class="example-query" style="padding: var(--spacing-md) var(--spacing-lg); background: rgba(255,255,255,0.02); border: var(--border-width) solid var(--border-color); color: var(--text-primary); font-size: var(--font-size-sm); cursor: pointer; transition: all 0.2s ease; text-align: left; font-family: var(--font-family);">"Build a classification model"</button>
          <button class="example-query" style="padding: var(--spacing-md) var(--spacing-lg); background: rgba(255,255,255,0.02); border: var(--border-width) solid var(--border-color); color: var(--text-primary); font-size: var(--font-size-sm); cursor: pointer; transition: all 0.2s ease; text-align: left; font-family: var(--font-family);">"Visualize data distribution"</button>
        </div>
      </div>
    `;

    this.messagesContainer.appendChild(welcomeDiv);

    // Re-attach event listeners to example queries
    welcomeDiv.querySelectorAll(".example-query").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this.chatInput) {
          this.chatInput.value = btn.textContent.replaceAll('"', "");
          this.handleSubmit(new Event("submit"));
        }
      });
    });
  }
}

export default Chat;
