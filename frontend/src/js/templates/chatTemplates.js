/**
 * Chat HTML Templates
 * Centralized template management for chat components
 */

export const ChatTemplates = {
  /**
   * Create message element HTML
   */
  message(icon, role, agentId, content, timestamp) {
    return `
      <div class="message-content">
        <div class="message-header">
          <span class="message-icon">${icon}</span>
          <span>${agentId || role}</span>
        </div>
        <div class="message-text">${content}</div>
        <div class="message-timestamp">${timestamp}</div>
      </div>
    `;
  },

  /**
   * Create typing indicator HTML
   */
  typingIndicator() {
    return `
      <div class="message-content">
        <div class="typing-indicator">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      </div>
    `;
  },

  /**
   * Create welcome message HTML
   */
  welcomeMessage() {
    return `
      <div class="welcome-content">
        <h2>Welcome to Amalia</h2>
        <p>Let's get started by asking a question or selecting an example below</p>
        <div class="welcome-suggestions">
          <button class="example-query">Load and analyze my dataset</button>
          <button class="example-query">Build a classification model</button>
          <button class="example-query">Visualize data distribution</button>
        </div>
      </div>
    `;
  },
};
