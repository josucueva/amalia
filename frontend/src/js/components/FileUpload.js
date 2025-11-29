/**
 * File Upload Component
 */
import api from "../api.js";
import state from "../utils/state.js";
import { showToast } from "../utils/helpers.js";

class FileUpload {
  constructor() {
    this.uploadBtn = document.getElementById("upload-btn");
    this.uploadModal = document.getElementById("upload-modal");
    this.closeModalBtn = document.getElementById("close-upload-modal");
    this.uploadArea = document.getElementById("upload-area");
    this.fileInput = document.getElementById("file-input");
    this.selectFileBtn = document.getElementById("select-file-btn");
    this.filePreview = document.getElementById("file-preview");
    this.removeFileBtn = document.getElementById("remove-file-btn");

    this.init();
  }

  init() {
    // Open modal (only if upload button exists)
    if (this.uploadBtn) {
      this.uploadBtn.addEventListener("click", () => this.openModal());
    }

    // Close modal
    if (this.closeModalBtn) {
      this.closeModalBtn.addEventListener("click", () => this.closeModal());
    }

    if (this.uploadModal) {
      this.uploadModal.addEventListener("click", (e) => {
        if (e.target === this.uploadModal) {
          this.closeModal();
        }
      });
    }

    // File selection
    if (this.selectFileBtn) {
      this.selectFileBtn.addEventListener("click", () =>
        this.fileInput.click()
      );
    }

    if (this.fileInput) {
      this.fileInput.addEventListener("change", (e) =>
        this.handleFileSelect(e)
      );
    }

    // Drag and drop
    if (this.uploadArea) {
      this.uploadArea.addEventListener("dragover", (e) =>
        this.handleDragOver(e)
      );
      this.uploadArea.addEventListener("dragleave", (e) =>
        this.handleDragLeave(e)
      );
      this.uploadArea.addEventListener("drop", (e) => this.handleDrop(e));
    }

    // Remove file
    if (this.removeFileBtn) {
      this.removeFileBtn.addEventListener("click", () => this.removeFile());
    }
  }

  openModal() {
    this.uploadModal.style.display = "flex";
  }

  closeModal() {
    this.uploadModal.style.display = "none";
  }

  handleDragOver(e) {
    e.preventDefault();
    this.uploadArea.classList.add("drag-over");
  }

  handleDragLeave(e) {
    e.preventDefault();
    this.uploadArea.classList.remove("drag-over");
  }

  handleDrop(e) {
    e.preventDefault();
    this.uploadArea.classList.remove("drag-over");

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      this.uploadFile(files[0]);
    }
  }

  handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
      this.uploadFile(files[0]);
    }
  }

  async uploadFile(file) {
    console.log("[DEBUG] uploadFile called with:", file.name, file.size);

    // Validate file type
    if (!file.name.endsWith(".csv")) {
      console.log("[DEBUG] File validation failed: not CSV");
      showToast("Only CSV files are supported", "error");
      return;
    }

    // Validate file size (50MB)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      console.log("[DEBUG] File validation failed: too large");
      showToast("File size exceeds 50MB limit", "error");
      return;
    }

    try {
      console.log("[DEBUG] Starting file upload...");
      showToast("Uploading file...", "info");

      const response = await api.uploadFile(file);
      console.log("[DEBUG] Upload response:", response);

      // Update state
      state.setState({ currentFile: response });
      console.log("[DEBUG] State updated with currentFile:", response);

      // Verify state was set
      const currentState = state.getState();
      console.log(
        "[DEBUG] Verified state.currentFile:",
        currentState.currentFile
      );

      // Show file preview
      this.showFilePreview(file.name, response.size_mb);

      // Close modal
      this.closeModal();

      showToast(`File "${file.name}" uploaded successfully`, "success");
    } catch (error) {
      console.error("[DEBUG] Upload error:", error);
      showToast("File upload failed. Please try again.", "error");
    }
  }

  showFilePreview(filename, sizeMB) {
    const fileNameEl = this.filePreview.querySelector(".file-name");
    fileNameEl.textContent = `📄 ${filename} (${sizeMB} MB)`;
    this.filePreview.style.display = "flex";
  }

  removeFile() {
    console.log("[DEBUG] Removing file from state");
    state.setState({ currentFile: null });
    this.filePreview.style.display = "none";
    this.fileInput.value = "";
    console.log(
      "[DEBUG] File removed, state.currentFile:",
      state.getState().currentFile
    );
  }
}

export default FileUpload;
