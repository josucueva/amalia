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

      // Check if response contains orchestration data
      const orchestration = response.message.metadata?.orchestration;

      if (orchestration && orchestration.orchestration) {
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
    if (window.app && window.app.canvasMode) {
      window.app.createPipelineFromData(
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
}

export default Chat;
