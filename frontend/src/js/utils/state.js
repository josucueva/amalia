/**
 * Simple state management
 */
class State {
  constructor() {
    this.state = {
      conversationId: null,
      currentFile: null,
      agents: [],
      messages: [],
      isLoading: false,
      currentSession: null, // Current active session
      sessions: [], // List of all sessions
    };
    this.listeners = [];
  }

  /**
   * Get current state
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Update state
   */
  setState(updates) {
    this.state = { ...this.state, ...updates };
    this.notifyListeners();
  }

  /**
   * Subscribe to state changes
   */
  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  /**
   * Notify all listeners
   */
  notifyListeners() {
    this.listeners.forEach((listener) => listener(this.state));
  }
}

export default new State();
