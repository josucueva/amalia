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

    this.init();
  }

  init() {
    if (this.chatForm) {
      this.chatForm.addEventListener("submit", (e) => this.handleSubmit(e));
    }

    // Handle example queries
    const exampleQueries = document.querySelectorAll(".example-query");
    exampleQueries.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (this.chatInput) {
          this.chatInput.value = btn.textContent.replace(/"/g, "");
          if (this.chatForm) {
            this.chatForm.dispatchEvent(new Event("submit"));
          }
        }
      });
    });
  }

  async handleSubmit(e) {
    e.preventDefault();

    const message = this.chatInput.value.trim();
    if (!message) return;

    // Clear input
    this.chatInput.value = "";

    // Add user message to chat
    this.addMessage({
      role: "user",
      content: message,
      timestamp: new Date().toISOString(),
    });

    // Show typing indicator
    this.showTypingIndicator();

    try {
      // Send message to backend
      const response = await api.sendMessage(
        message,
        state.getState().conversationId
      );

      // Update conversation ID
      state.setState({ conversationId: response.conversation_id });

      // Remove typing indicator
      this.removeTypingIndicator();

      // Check if response contains an action in metadata
      const action = response.message.metadata?.action;

      if (action && action.action === "build_pipeline") {
        // Handle build pipeline action
        await this.handleBuildCommand(action.message || "Building pipeline...");
      } else {
        // Add normal assistant response
        this.addMessage(response.message);
      }
    } catch (error) {
      this.removeTypingIndicator();
      showToast("Failed to send message. Please try again.", "error");
      console.error("Error sending message:", error);
    }
  }

  async handleBuildCommand(agentMessage) {
    // Show the agent's message first
    this.addMessage({
      role: "assistant",
      content: agentMessage,
      timestamp: new Date().toISOString(),
    });

    this.showTypingIndicator();

    try {
      // Call build pipeline endpoint
      const response = await api.buildPipeline("BUILD");

      this.removeTypingIndicator();

      // Add system message
      this.addMessage({
        role: "assistant",
        content: `✅ ${response.message}\n\nSwitch to Canvas Mode to see your pipeline!`,
        timestamp: new Date().toISOString(),
      });

      // Trigger canvas update if in canvas mode
      if (window.app && window.app.canvasMode) {
        window.app.createPipelineFromData(response.nodes, response.connections);
      } else {
        // Store pipeline data for when user switches to canvas mode
        sessionStorage.setItem("pendingPipeline", JSON.stringify(response));
      }

      showToast("Pipeline created successfully!", "success");
    } catch (error) {
      this.removeTypingIndicator();
      this.addMessage({
        role: "assistant",
        content: `❌ Failed to build pipeline: ${error.message}\n\nMake sure the backend is running.`,
        timestamp: new Date().toISOString(),
      });
      showToast("Failed to build pipeline", "error");
      console.error("Error building pipeline:", error);
    }
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
}

export default Chat;
