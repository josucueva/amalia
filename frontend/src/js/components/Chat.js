/**
 * Chat Component
 */
import api from "../api.js";
import state from "../utils/state.js";
import { formatTimestamp, sanitizeHTML, showToast } from "../utils/helpers.js";
import { ChatTemplates } from "../templates/chatTemplates.js";

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

    // Handle example queries in any existing welcome message
    this.attachExampleQueryListeners(document);
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

    // Save pipeline to current session
    const currentSession = state.getState().currentSession;
    if (currentSession) {
      try {
        await api.addPipelineToSession(
          currentSession.id,
          orchestrationData.nodes,
          orchestrationData.connections
        );

        // Update session in state with new pipeline
        const updatedSession = await api.getSession(currentSession.id);
        state.setState({ currentSession: updatedSession });

        console.log("✓ Pipeline saved to session:", currentSession.id);
      } catch (error) {
        console.error("Error saving pipeline to session:", error);
        showToast("Failed to save pipeline to session", "error");
      }
    }

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

    messageEl.innerHTML = ChatTemplates.message(
      icon,
      role,
      message.agent_id,
      sanitizeHTML(message.content),
      formatTimestamp(message.timestamp)
    );

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
    indicator.innerHTML = ChatTemplates.typingIndicator();

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
    welcomeDiv.innerHTML = ChatTemplates.welcomeMessage();

    this.messagesContainer.appendChild(welcomeDiv);

    // Re-attach event listeners to example queries
    this.attachExampleQueryListeners(welcomeDiv);
  }

  /**
   * Attach event listeners to example query buttons
   * @param {HTMLElement} container - Container element with example queries
   */
  attachExampleQueryListeners(container) {
    container.querySelectorAll(".example-query").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this.chatInput) {
          this.chatInput.value = btn.textContent.trim();
          this.handleSubmit(new Event("submit"));
        }
      });
    });
  }
}

export default Chat;
