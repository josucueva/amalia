import { showToast } from "../utils/helpers.js";
import config from "../config.js";

const { API_BASE_URL } = config;

export default class PipelineManager {
  constructor(app) {
    this.app = app;
    this.isExecuting = false;
    this.executionPaused = false;
    this.executionCancelled = false;
    this.currentExecutingNode = null;
    this.executionResults = new Map();
    this.executionOrder = [];
  }

  async runPipeline() {
    if (this.isExecuting) {
      console.warn("Pipeline already executing");
      return;
    }

    const nodes = Array.from(document.querySelectorAll(".agent-node"));
    const allConnections = this.app.connectionManager.getConnectionsData();
    const connections = allConnections.filter((conn) => conn.enabled !== false);

    const disabledCount = allConnections.length - connections.length;
    if (disabledCount > 0) {
      console.log(`ℹ️ Skipping ${disabledCount} disabled connection(s)`);
    }

    if (nodes.length === 0) {
      showToast("No agents on canvas to execute", "warning");
      return;
    }

    this.executionOrder = this.calculateExecutionOrder(nodes, connections);

    if (!this.executionOrder) {
      showToast("Cannot execute: Circular dependencies detected", "error");
      return;
    }

    this.isExecuting = true;
    this.executionPaused = false;
    this.executionCancelled = false;
    this.executionResults.clear();

    showToast(`Executing ${this.executionOrder.length} agents...`, "info");

    await this.executeSequentialPipeline();

    this.isExecuting = false;
    this.currentExecutingNode = null;

    if (this.executionCancelled) {
      showToast("Pipeline execution cancelled", "warning");
    } else {
      showToast("Pipeline execution completed", "success");
    }
  }

  calculateExecutionOrder(nodes, connections) {
    const graph = new Map();
    const inDegree = new Map();
    const nodeMap = new Map();

    for (const node of nodes) {
      const instanceId = node.dataset.instanceId;
      graph.set(instanceId, []);
      inDegree.set(instanceId, 0);
      nodeMap.set(instanceId, node);
    }

    for (const conn of connections) {
      const fromId = conn.from.instanceId;
      const toId = conn.to.instanceId;

      if (graph.has(fromId) && graph.has(toId)) {
        graph.get(fromId).push(toId);
        inDegree.set(toId, inDegree.get(toId) + 1);
      }
    }

    const queue = [];
    const order = [];

    for (const [instanceId, degree] of inDegree) {
      if (degree === 0) {
        queue.push(instanceId);
      }
    }

    while (queue.length > 0) {
      const current = queue.shift();
      order.push(nodeMap.get(current));

      for (const dependent of graph.get(current)) {
        inDegree.set(dependent, inDegree.get(dependent) - 1);
        if (inDegree.get(dependent) === 0) {
          queue.push(dependent);
        }
      }
    }

    if (order.length !== nodes.length) {
      console.error("Circular dependency detected in pipeline");
      return null;
    }

    return order;
  }

  async executeSequentialPipeline() {
    for (const node of this.executionOrder) {
      if (this.executionCancelled) {
        this.setNodeExecutionState(node, "cancelled");
        continue;
      }

      while (this.executionPaused && !this.executionCancelled) {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      if (this.executionCancelled) {
        this.setNodeExecutionState(node, "cancelled");
        continue;
      }

      this.currentExecutingNode = node;
      this.setNodeExecutionState(node, "running");

      try {
        const result = await this.executeNode(node);
        this.executionResults.set(node.dataset.instanceId, result);
        this.setNodeExecutionState(node, "completed");
        this.updateNodeDataBadges(node, result);
      } catch (error) {
        console.error(`Error executing node ${node.dataset.instanceId}:`, error);
        this.executionResults.set(node.dataset.instanceId, { error: error.message });
        this.setNodeExecutionState(node, "error");
        showToast(`Execution failed: ${error.message}`, "error");
        this.executionCancelled = true;
      }
    }
  }

  async executeNode(node) {
    const instanceId = node.dataset.instanceId;
    const agentId = node.dataset.agentId;
    const agentData = JSON.parse(node.dataset.agentData || "{}");
    const instanceConfig = agentData.config || null;

    const allConnections = this.app.connectionManager.getConnectionsData();
    const enabledConnections = allConnections.filter((conn) => conn.enabled !== false);

    const inputs = enabledConnections
      .filter((conn) => conn.to.instanceId === instanceId)
      .map((conn) => this.executionResults.get(conn.from.instanceId))
      .filter((result) => result !== undefined);

    try {
      const response = await fetch(`${API_BASE_URL}/api/canvas/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instanceId,
          agentType: agentId,
          inputs,
          config: instanceConfig,
          mcpServerIds: agentData.mcpServerIds || [],
          filePath: agentData.filePath || null,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to execute agent: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      return result;
    } catch (error) {
      console.error("Error executing node:", error);
      throw error;
    }
  }

  setNodeExecutionState(node, state) {
    node.classList.remove("node-running", "node-completed", "node-error", "node-cancelled", "node-loading");

    if (state === "running") {
      node.classList.add("node-running", "node-loading");
    } else if (state === "completed") {
      node.classList.add("node-completed");
    } else if (state === "error") {
      node.classList.add("node-error");
    } else if (state === "cancelled") {
      node.classList.add("node-cancelled");
    }
  }

  updateNodeDataBadges(node, executionData) {
    if (!node || !executionData) return;

    const inputBadge = node.querySelector(".input-badge");
    const outputBadge = node.querySelector(".output-badge");
    const agentData = JSON.parse(node.dataset.agentData || "{}");

    if (inputBadge) {
      const hasInputs = executionData.inputs > 0;
      const hasFile = agentData.filePath;

      if (hasInputs || hasFile) {
        inputBadge.style.display = "flex";
        if (hasFile && executionData.inputs === 0) {
          inputBadge.title = "File input attached";
        } else {
          inputBadge.title = `${executionData.inputs} input(s) received`;
        }
      }
    }

    if (outputBadge && executionData.output) {
      outputBadge.style.display = "flex";
      outputBadge.title = "Output generated";
    }

    if (globalThis.lucide) {
      globalThis.lucide.createIcons();
    }
  }

  pauseExecution() {
    this.executionPaused = true;
    showToast("Execution paused", "info");
  }

  resumeExecution() {
    this.executionPaused = false;
    showToast("Execution resumed", "info");
  }

  cancelExecution() {
    this.executionCancelled = true;
    showToast("Cancelling execution...", "warning");
  }
}
