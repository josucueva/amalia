/**
 * Theme Manager
 * Handles dark/light mode switching and persistence
 */

class ThemeManager {
  constructor() {
    // Check for saved theme preference or default to 'light'
    this.currentTheme = localStorage.getItem("theme") || "light";
    this.listeners = [];
    this.apply();
  }

  /**
   * Toggle between light and dark themes
   */
  toggle() {
    this.currentTheme = this.currentTheme === "light" ? "dark" : "light";
    this.apply();
    this.save();
    this.notifyListeners();
  }

  /**
   * Set specific theme
   * @param {string} theme - 'light' or 'dark'
   */
  setTheme(theme) {
    if (theme !== "light" && theme !== "dark") {
      console.warn(`Invalid theme: ${theme}. Using 'light' instead.`);
      theme = "light";
    }
    this.currentTheme = theme;
    this.apply();
    this.save();
    this.notifyListeners();
  }

  /**
   * Apply the current theme to the document
   */
  apply() {
    document.documentElement.dataset.theme = this.currentTheme;
  }

  /**
   * Save theme preference to localStorage
   */
  save() {
    localStorage.setItem("theme", this.currentTheme);
  }

  /**
   * Get current theme
   * @returns {string} 'light' or 'dark'
   */
  getTheme() {
    return this.currentTheme;
  }

  /**
   * Check if dark mode is active
   * @returns {boolean}
   */
  isDark() {
    return this.currentTheme === "dark";
  }

  /**
   * Subscribe to theme changes
   * @param {Function} callback - Called when theme changes
   * @returns {Function} Unsubscribe function
   */
  subscribe(callback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((cb) => cb !== callback);
    };
  }

  /**
   * Notify all listeners of theme change
   */
  notifyListeners() {
    this.listeners.forEach((callback) => callback(this.currentTheme));
  }
}

// Export singleton instance
export default new ThemeManager();
