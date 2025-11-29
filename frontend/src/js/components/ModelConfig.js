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
    this.onModelAdded = null; // Callback when a model is added
    this.providers = [
      { value: "openai", label: "OpenAI" },
      { value: "anthropic", label: "Anthropic" },
      { value: "groq", label: "Groq" },
      { value: "gemini", label: "Gemini" },
      { value: "ollama", label: "Ollama" },
      { value: "together", label: "Together AI" },
      { value: "azure", label: "Azure OpenAI" },
      { value: "custom", label: "Custom" },
    ];
    this.init();
  }

  init() {
    // Create the model configuration panel
    this.createPanel();
  }

  createPanel() {
    const panel = document.createElement("div");
    panel.className = "model-config-panel";
    panel.innerHTML = `
      <div class="model-config-overlay"></div>
      <div class="model-config-content">
        <div class="model-config-header">
          <h3>
            <i data-lucide="plus-circle"></i>
            Add New Model
          </h3>
          <button class="close-btn" id="close-model-panel">
            <i data-lucide="x"></i>
          </button>
        </div>
        
        <form id="model-config-form" class="model-config-form">
          <div class="form-group">
            <label for="model-display-name">
              Display Name
              <span class="required">*</span>
            </label>
            <input
              type="text"
              id="model-display-name"
              name="display_name"
              placeholder="e.g., Groq Llama 3.3 70B"
              required
            />
            <small>Human-readable name shown in the dropdown</small>
          </div>

          <div class="form-group">
            <label for="model-provider">
              Provider
              <span class="required">*</span>
            </label>
            <select id="model-provider" name="provider" required>
              <option value="">Select a provider</option>
              ${this.providers
                .map((p) => `<option value="${p.value}">${p.label}</option>`)
                .join("")}
            </select>
          </div>

          <div class="form-group">
            <label for="model-name">
              Model Name
              <span class="required">*</span>
            </label>
            <input
              type="text"
              id="model-name"
              name="model_name"
              placeholder="e.g., groq/llama-3.3-70b-versatile"
              required
            />
            <small>Full model identifier for LiteLLM (e.g., provider/model-name)</small>
          </div>

          <div class="form-group">
            <label for="model-api-key-name">
              API Key Environment Variable
            </label>
            <input
              type="text"
              id="model-api-key-name"
              name="api_key_name"
              placeholder="e.g., GROQ_API_KEY"
            />
            <small>Name of the environment variable containing the API key</small>
          </div>

          <div class="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                id="model-supports-functions"
                name="supports_function_calling"
                checked
              />
              Supports Function Calling
            </label>
            <small>Check if this model supports tool/function calling</small>
          </div>

          <div class="form-group">
            <label for="model-max-tokens">Max Tokens</label>
            <input
              type="number"
              id="model-max-tokens"
              name="max_tokens"
              placeholder="e.g., 8000"
              min="1"
            />
            <small>Maximum token limit for the model (optional)</small>
          </div>

          <div class="form-group">
            <label for="model-description">Description</label>
            <textarea
              id="model-description"
              name="description"
              placeholder="Brief description of the model"
              rows="3"
            ></textarea>
          </div>

          <div class="form-actions">
            <button type="button" class="btn btn-secondary" id="cancel-model-btn">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary">
              <i data-lucide="save"></i>
              Add Model
            </button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(panel);
    this.modelPanel = panel;

    // Add event listeners
    this.attachEventListeners();
  }

  attachEventListeners() {
    const closeBtn = this.modelPanel.querySelector("#close-model-panel");
    const cancelBtn = this.modelPanel.querySelector("#cancel-model-btn");
    const overlay = this.modelPanel.querySelector(".model-config-overlay");
    const form = this.modelPanel.querySelector("#model-config-form");

    closeBtn?.addEventListener("click", () => this.close());
    cancelBtn?.addEventListener("click", () => this.close());
    overlay?.addEventListener("click", () => this.close());
    form?.addEventListener("submit", (e) => this.handleSubmit(e));

    // Auto-fill model name based on provider
    const providerSelect = this.modelPanel.querySelector("#model-provider");
    const modelNameInput = this.modelPanel.querySelector("#model-name");

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
    this.modelPanel.classList.add("open");

    // Reset form
    const form = this.modelPanel.querySelector("#model-config-form");
    form?.reset();

    // Re-initialize Lucide icons
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  close() {
    this.isOpen = false;
    this.modelPanel.classList.remove("open");
    this.onModelAdded = null;
  }
}

// Export singleton instance
export default new ModelConfig();
