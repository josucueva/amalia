/**
 * Model Configuration Component
 * Manages LLM model configurations
 */
import api from "../api.js";
import { showToast } from "../utils/helpers.js";

class ModelConfig {
  constructor() {
    this.modelPanel = null;
    this.isOpen = false;
    this.onModelAdded = null;
    this.init();
  }

  init() {
    // Get references to existing HTML elements
    this.modelPanel = document.getElementById("model-config-panel");
    this.closeBtn = document.getElementById("close-model-config");
    this.cancelBtn = document.getElementById("cancel-model-btn");
    this.form = document.getElementById("model-config-form");
    this.agentModal = document.querySelector(".agent-modal-container");

    this.attachEventListeners();
  }

  attachEventListeners() {
    if (!this.modelPanel || !this.form) return;

    // Close button
    this.closeBtn?.addEventListener("click", () => this.close());

    // Cancel button
    this.cancelBtn?.addEventListener("click", () => this.close());

    // Form submission
    this.form.addEventListener("submit", (e) => this.handleSubmit(e));

    // Auto-fill model name based on provider
    const providerSelect = document.getElementById("model-provider");
    const modelNameInput = document.getElementById("model-name");

    providerSelect?.addEventListener("change", (e) => {
      const provider = e.target.value;
      const currentValue = modelNameInput.value;

      // Only auto-fill if empty or if it's a provider-prefixed value
      if (!currentValue || currentValue.includes("/")) {
        if (provider && provider !== "custom") {
          modelNameInput.placeholder = `${provider}/model-name`;
        }
      }
    });
  }

  async handleSubmit(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
      display_name: formData.get("display_name"),
      model_name: formData.get("model_name"),
      provider: formData.get("provider"),
      api_key_name: formData.get("api_key_name") || null,
      supports_function_calling:
        formData.get("supports_function_calling") === "on",
      max_tokens: formData.get("max_tokens")
        ? parseInt(formData.get("max_tokens"))
        : null,
      description: formData.get("description") || null,
    };

    try {
      const result = await api.addModel(data);
      showToast(`Model "${data.display_name}" added successfully`, "success");

      // Call the callback if provided
      if (this.onModelAdded) {
        this.onModelAdded(result);
      }

      this.close();
    } catch (error) {
      console.error("Error adding model:", error);
      showToast(error.message || "Failed to add model", "error");
    }
  }

  open(onModelAdded = null) {
    this.onModelAdded = onModelAdded;
    this.isOpen = true;

    // Add class to agent modal container to show the panel
    if (this.agentModal) {
      this.agentModal.classList.add("model-panel-active");
    }

    // Reset form
    if (this.form) {
      this.form.reset();
    }

    // Re-initialize Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  close() {
    this.isOpen = false;

    // Remove class from agent modal container to hide the panel
    if (this.agentModal) {
      this.agentModal.classList.remove("model-panel-active");
    }

    this.onModelAdded = null;
  }
}

// Export singleton instance
export default new ModelConfig();
