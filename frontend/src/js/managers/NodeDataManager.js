import { showToast } from "../utils/helpers.js";
import api from "../api.js";
import config from "../config.js";

const { API_BASE_URL } = config;

export default class NodeDataManager {
  constructor(app) {
    this.app = app;
  }

  showNodeDataViewer(instanceId, agentInstance) {
    const result = this.app.pipelineManager.executionResults.get(instanceId);
    const hasExecutionData = !!result;

    if (!hasExecutionData && !agentInstance.filePath) {
      const connections = this.app.connectionManager.getConnectionsData();
      const inputConnections = connections.filter(
        (conn) => conn.to.instanceId === instanceId
      );
      if (inputConnections.length === 0) {
        showToast("No data available - agent not executed and no inputs connected", "info");
        return;
      }
    }

    const connections = this.app.connectionManager.getConnectionsData();
    const inputConnections = connections.filter(
      (conn) => conn.to.instanceId === instanceId
    );
    const inputData = inputConnections.map((conn) => {
      const inputResult = this.app.pipelineManager.executionResults.get(conn.from.instanceId);
      return {
        fromAgent: conn.from.agentId,
        fromInstance: conn.from.instanceId,
        data: inputResult || null,
      };
    });

    const hasFileInput = agentInstance.filePath;
    const totalInputs = inputData.length + (hasFileInput ? 1 : 0);

    const modal = document.createElement("div");
    modal.className = "modal";
    modal.id = "node-data-viewer-modal";
    modal.style.display = "flex";

    modal.innerHTML = `
      <div class="modal-content data-viewer-modal-content">
        <div class="modal-header">
          <h2>Node Data: ${agentInstance.config?.name || agentInstance.id}</h2>
          <button class="modal-close" onclick="document.getElementById('node-data-viewer-modal').remove()">
            <i data-lucide="x"></i>
          </button>
        </div>
        <div class="modal-body data-viewer-body">
          <div class="data-section">
            <h3>Execution Metadata</h3>
            <div class="data-grid">
              <div class="data-field">
                <label>Instance ID:</label>
                <span class="data-value monospace">${hasExecutionData ? result.instanceId : instanceId}</span>
              </div>
              <div class="data-field">
                <label>Agent Type:</label>
                <span class="data-value">${hasExecutionData ? result.agentType : agentInstance.config?.name || agentInstance.id}</span>
              </div>
              ${hasExecutionData ? `
              <div class="data-field">
                <label>Timestamp:</label>
                <span class="data-value">${new Date(result.timestamp).toLocaleString()}</span>
              </div>
              <div class="data-field">
                <label>Input Count:</label>
                <span class="data-value badge-count">${result.inputs}</span>
              </div>
              <div class="data-field">
                <label>Status:</label>
                <span class="data-value status-${result.error ? "error" : "success"}">${result.error ? "Error" : "Success"}</span>
              </div>
              ` : `
              <div class="data-field">
                <label>Status:</label>
                <span class="data-value status-pending">Not Executed</span>
              </div>
              `}
            </div>
          </div>

          <div class="data-section">
            <h3>Input Data (${totalInputs} source${totalInputs === 1 ? "" : "s"})</h3>
            ${hasFileInput ? `
              <div class="data-connections">
                <div class="connection-data">
                  <div class="connection-header">
                    <span class="connection-label">File Input</span>
                    <span class="connection-id monospace">Attached File</span>
                  </div>
                  <pre class="data-preview file-path-display">File Path: ${agentInstance.filePath}\n\nNote: Agent should use MCP filesystem tools to read this file.</pre>
                </div>
              </div>
            ` : ""}
            ${inputData.length > 0 ? `
              <div class="data-connections">
                ${inputData.map((input) => `
                  <div class="connection-data">
                    <div class="connection-header">
                      <span class="connection-label">From: ${input.fromAgent}</span>
                      <span class="connection-id monospace">${input.fromInstance}</span>
                    </div>
                    ${input.data ? `<pre class="data-preview">${this.formatDataForDisplay(input.data.output)}</pre>` : '<p class="no-data">No data available</p>'}
                  </div>
                `).join("")}
              </div>
            ` : !hasFileInput ? '<p class="no-data">No input connections</p>' : ""}
          </div>

          <div class="data-section">
            <h3>Output Data</h3>
            ${!hasExecutionData ? '<p class="no-data">Agent has not been executed yet</p>' : result.error ? `
              <div class="error-display"><span>ERROR: ${result.error}</span></div>
            ` : `
              <pre class="data-preview output-preview">${this.formatDataForDisplay(result.output)}</pre>
            `}
          </div>

          ${hasExecutionData ? `
          <div class="data-section data-actions">
            <button class="btn btn-secondary" id="copy-output-btn">COPY OUTPUT</button>
            <button class="btn btn-secondary" id="download-output-btn">DOWNLOAD JSON</button>
          </div>
          ` : ""}
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" onclick="document.getElementById('node-data-viewer-modal').remove()">Close</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    if (hasExecutionData && !result.error) {
      const copyBtn = modal.querySelector("#copy-output-btn");
      if (copyBtn) {
        copyBtn.addEventListener("click", () => {
          navigator.clipboard.writeText(JSON.stringify(result.output, null, 2))
            .then(() => showToast("Output copied to clipboard", "success"))
            .catch(() => showToast("Failed to copy output", "error"));
        });
      }

      const downloadBtn = modal.querySelector("#download-output-btn");
      if (downloadBtn) {
        downloadBtn.addEventListener("click", () => {
          this.downloadData(result);
        });
      }
    }

    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }

    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.remove();
    });
  }

  formatDataForDisplay(data) {
    if (data === null || data === undefined) return "(no data)";
    if (typeof data === "string") {
      if (data.length > 2000) return data.substring(0, 2000) + "\n... (truncated)";
      return data;
    }
    try {
      return JSON.stringify(data, null, 2);
    } catch (error) {
      return String(data);
    }
  }

  downloadData(result) {
    const dataStr = JSON.stringify(result, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `execution-${result.instanceId}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Data downloaded', 'success');
  }

  showExecutionLogs(instanceId) {
    const result = this.app.pipelineManager.executionResults.get(instanceId);

    if (!result) {
      showToast("No execution logs available for this agent", "info");
      return;
    }

    const modal = document.createElement("div");
    modal.className = "modal-overlay";
    modal.id = "execution-logs-modal";

    modal.innerHTML = `
      <div class="modal-content execution-logs-modal-content">
        <div class="modal-header">
          <h2>Execution Logs</h2>
          <button class="modal-close" onclick="document.getElementById('execution-logs-modal').remove()">
            <i data-lucide="x"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="execution-logs-info">
            <div class="log-field"><label>Instance ID:</label><span>${result.instanceId}</span></div>
            <div class="log-field"><label>Agent Type:</label><span>${result.agentType}</span></div>
            <div class="log-field"><label>Timestamp:</label><span>${new Date(result.timestamp).toLocaleString()}</span></div>
            <div class="log-field"><label>Input Count:</label><span>${result.inputs}</span></div>
          </div>
          <div class="execution-logs-output">
            <h3>Output</h3>
            <pre>${result.error ? `ERROR: ${result.error}` : JSON.stringify(result.output, null, 2)}</pre>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="document.getElementById('execution-logs-modal').remove()">Close</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    if (globalThis.lucide) globalThis.lucide.createIcons();
    modal.addEventListener("click", (e) => { if (e.target === modal) modal.remove(); });
  }

  async showFileAttachmentModal(node, agentInstance) {
    try {
      const response = await api.listFiles();
      const files = response.files || [];

      const modal = document.createElement("div");
      modal.className = "modal";
      modal.id = "file-attachment-modal";
      modal.style.display = "flex";

      modal.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <h2>Attach File to Data Loader</h2>
            <button class="modal-close" onclick="document.getElementById('file-attachment-modal').remove()">
              <i data-lucide="x"></i>
            </button>
          </div>
          <div class="modal-body">
            ${agentInstance.filePath ? `
              <div class="current-file-info">
                <h3>Current File</h3>
                <div class="file-path-display">
                  <i data-lucide="file-text"></i>
                  <span>${agentInstance.filePath}</span>
                </div>
                <button class="btn btn-secondary" id="remove-file-attachment">
                  <i data-lucide="x"></i> Remove Attachment
                </button>
              </div>
              <div class="divider"></div>
            ` : ""}
            <h3>Available Files</h3>
            ${files.length === 0 ? '<p class="no-data">No files uploaded yet.</p>' : `
              <div class="file-list">
                ${files.map(file => `
                  <div class="file-item" data-filename="${file.filename}">
                    <div class="file-info">
                      <i data-lucide="file-text"></i>
                      <div class="file-details">
                        <span class="file-name">${file.filename}</span>
                        <span class="file-meta">${file.size_mb} MB • ${new Date(file.created_at * 1000).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <button class="btn btn-primary btn-sm attach-file-btn" data-filename="${file.filename}">ATTACH</button>
                  </div>
                `).join("")}
              </div>
            `}
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" onclick="document.getElementById('file-attachment-modal').remove()">Cancel</button>
          </div>
        </div>
      `;

      document.body.appendChild(modal);
      if (globalThis.lucide) globalThis.lucide.createIcons();

      modal.querySelectorAll(".attach-file-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const filename = btn.dataset.filename;
          this.attachFileToNode(node, agentInstance, filename);
          modal.remove();
        });
      });

      const removeBtn = modal.querySelector("#remove-file-attachment");
      if (removeBtn) {
        removeBtn.addEventListener("click", () => {
          this.removeFileFromNode(node, agentInstance);
          modal.remove();
        });
      }

      modal.addEventListener("click", (e) => { if (e.target === modal) modal.remove(); });
    } catch (error) {
      console.error("Error loading files:", error);
      showToast("Failed to load files", "error");
    }
  }

  attachFileToNode(node, agentInstance, filename) {
    const filePath = `/app/data/uploads/${filename}`;
    const updatedInstance = { ...agentInstance, filePath: filePath };
    node.dataset.agentData = JSON.stringify(updatedInstance);

    let fileIndicator = node.querySelector(".node-file-indicator");
    if (!fileIndicator) {
      fileIndicator = document.createElement("div");
      fileIndicator.className = "node-file-indicator";
      node.appendChild(fileIndicator);
    }

    fileIndicator.setAttribute("title", `File attached: ${filename}`);
    fileIndicator.innerHTML = '<i data-lucide="file-text"></i>';
    if (globalThis.lucide) globalThis.lucide.createIcons();

    this.app.pipelineManager.updateNodeDataBadges(node, { inputs: 0 }); // Trigger badge update
    showToast(`File "${filename}" attached successfully`, "success");
  }

  removeFileFromNode(node, agentInstance) {
    const updatedInstance = { ...agentInstance, filePath: null };
    node.dataset.agentData = JSON.stringify(updatedInstance);

    const fileIndicator = node.querySelector(".node-file-indicator");
    if (fileIndicator) fileIndicator.remove();

    this.app.pipelineManager.updateNodeDataBadges(node, { inputs: 0 }); // Trigger badge update
    showToast("File attachment removed", "success");
  }
}
