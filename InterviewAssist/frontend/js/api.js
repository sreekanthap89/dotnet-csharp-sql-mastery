/* API Client for Interview Assist */

const API_BASE = "";

export const api = {
  async getDocuments() {
    const res = await fetch(`${API_BASE}/api/documents`);
    if (!res.ok) throw new Error("Failed to fetch documents");
    return res.json();
  },

  async uploadFiles(files) {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    const res = await fetch(`${API_BASE}/api/ingest/files`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Failed to upload files");
    return res.json();
  },

  async scrapeUrl(url) {
    const res = await fetch(`${API_BASE}/api/ingest/url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to scrape URL" }));
      throw new Error(err.detail || "Failed to scrape URL");
    }
    return res.json();
  },

  async ingestWorkspace() {
    const res = await fetch(`${API_BASE}/api/ingest/workspace`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to ingest workspace files");
    return res.json();
  },

  async reindexAll() {
    const res = await fetch(`${API_BASE}/api/ingest/reindex-all`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to re-index knowledge base");
    return res.json();
  },

  async deleteDocument(docId) {
    const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete document");
    return res.json();
  },

  async searchRag(query, topK = 4) {
    const res = await fetch(`${API_BASE}/api/rag/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK }),
    });
    if (!res.ok) throw new Error("Semantic search failed");
    return res.json();
  },

  async startInterview({ level, totalQuestions, focusArea, questionTypes, docIds }) {
    const res = await fetch(`${API_BASE}/api/interview/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        level,
        total_questions: totalQuestions,
        focus_area: focusArea || "all",
        question_types: questionTypes,
        doc_ids: docIds,
      }),
    });
    if (!res.ok) throw new Error("Failed to start interview");
    return res.json();
  },

  async getKnowledgeAreas() {
    const res = await fetch(`${API_BASE}/api/knowledge/areas`);
    if (!res.ok) throw new Error("Failed to fetch knowledge areas");
    return res.json();
  },

  async getInterviewHistory() {
    const res = await fetch(`${API_BASE}/api/interview/history/all`);
    if (!res.ok) throw new Error("Failed to fetch interview history");
    return res.json();
  },

  async getHistoricalInterview(sessionId) {
    const res = await fetch(`${API_BASE}/api/interview/history/${sessionId}`);
    if (!res.ok) throw new Error("Failed to fetch historical session");
    return res.json();
  },

  async submitAnswer(sessionId, questionId, userAnswer, timeTakenSeconds = 0) {
    const res = await fetch(`${API_BASE}/api/interview/${sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question_id: questionId,
        user_answer: userAnswer,
        time_taken_seconds: timeTakenSeconds,
      }),
    });
    if (!res.ok) throw new Error("Failed to record answer");
    return res.json();
  },

  async completeInterview(sessionId) {
    const res = await fetch(`${API_BASE}/api/interview/${sessionId}/complete`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to evaluate interview");
    return res.json();
  },

  async getOllamaStatus() {
    const res = await fetch(`${API_BASE}/api/ollama/status`);
    if (!res.ok) throw new Error("Failed to fetch Ollama status");
    return res.json();
  },

  async selectOllamaModel(model) {
    const res = await fetch(`${API_BASE}/api/ollama/select-model`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    if (!res.ok) throw new Error("Failed to select Ollama model");
    return res.json();
  },

  async getLlmConfig() {
    const res = await fetch(`${API_BASE}/api/llm/config`);
    if (!res.ok) throw new Error("Failed to fetch LLM configuration");
    return res.json();
  },

  async updateLlmConfig(config) {
    const res = await fetch(`${API_BASE}/api/llm/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error("Failed to update LLM configuration");
    return res.json();
  },

  async testLlmProvider(provider, configOverride = null) {
    const res = await fetch(`${API_BASE}/api/llm/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, config_override: configOverride }),
    });
    if (!res.ok) throw new Error("Test request failed");
    return res.json();
  },

  async fetchLlmModels(provider, configOverride = null) {
    const res = await fetch(`${API_BASE}/api/llm/models`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, config_override: configOverride }),
    });
    if (!res.ok) throw new Error("Failed to query models from provider");
    return res.json();
  },

  async selectActiveLlm(provider, model) {
    const res = await fetch(`${API_BASE}/api/llm/select`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, model }),
    });
    if (!res.ok) throw new Error("Failed to select active LLM");
    return res.json();
  },

  async getSettings() {
    const res = await fetch(`${API_BASE}/api/settings`);
    if (!res.ok) throw new Error("Failed to load settings");
    return res.json();
  },

  async updateSettings(settings) {
    const res = await fetch(`${API_BASE}/api/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    });
    if (!res.ok) throw new Error("Failed to save settings");
    return res.json();
  },
};

