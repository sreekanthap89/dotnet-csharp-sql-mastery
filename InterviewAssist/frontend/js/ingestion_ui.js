import { api } from './api.js';

export class IngestionUI {
  constructor(app) {
    this.app = app;
    this.initElements();
    this.bindEvents();
  }

  initElements() {
    this.dropzone = document.getElementById('dropzone');
    this.fileInput = document.getElementById('file-input');
    this.urlInput = document.getElementById('url-input');
    this.scrapeBtn = document.getElementById('scrape-url-btn');
    this.docsTableBody = document.getElementById('docs-table-body');
    
    // Stats
    this.statDocs = document.getElementById('stat-total-docs');
    this.statChunks = document.getElementById('stat-total-chunks');
    this.statWords = document.getElementById('stat-total-words');
    this.workspaceIngestBtn = document.getElementById('quick-workspace-btn') || document.getElementById('btn-ingest-workspace');
    this.reindexAllBtn = document.getElementById('btn-reindex-all');

    // RAG Search Tester
    this.ragSearchInput = document.getElementById('rag-test-input');
    this.ragSearchBtn = document.getElementById('rag-test-btn');
    this.ragResultsContainer = document.getElementById('rag-results-container');
  }

  bindEvents() {
    // Dropzone
    if (this.dropzone) {
      this.dropzone.addEventListener('click', () => this.fileInput.click());
      this.dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        this.dropzone.classList.add('dragover');
      });
      this.dropzone.addEventListener('dragleave', () => {
        this.dropzone.classList.remove('dragover');
      });
      this.dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        this.dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          this.handleFileUpload(e.dataTransfer.files);
        }
      });
    }

    if (this.fileInput) {
      this.fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
          this.handleFileUpload(e.target.files);
        }
      });
    }

    // URL Scraper
    if (this.scrapeBtn) {
      this.scrapeBtn.addEventListener('click', () => this.handleUrlScrape());
    }
    if (this.urlInput) {
      this.urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') this.handleUrlScrape();
      });
    }

    // Quick Workspace Ingestion
    if (this.workspaceIngestBtn) {
      this.workspaceIngestBtn.addEventListener('click', () => this.handleWorkspaceIngest());
    }

    // Refresh & Re-index All
    if (this.reindexAllBtn) {
      this.reindexAllBtn.addEventListener('click', () => this.handleReindexAll());
    }

    // RAG Search
    if (this.ragSearchBtn) {
      this.ragSearchBtn.addEventListener('click', () => this.handleRagSearch());
    }
    if (this.ragSearchInput) {
      this.ragSearchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') this.handleRagSearch();
      });
    }
  }

  async refresh() {
    try {
      const data = await api.getDocuments();
      this.renderStats(data.stats);
      this.renderTable(data.documents);
      // Synchronize dynamic focus domain cards in Interview Arena
      if (this.app.interviewUI?.loadKnowledgeAreas) {
        await this.app.interviewUI.loadKnowledgeAreas();
      }
    } catch (err) {
      console.error(err);
      this.app.showToast('Failed to load knowledge base', 'error');
    }
  }

  renderStats(stats) {
    if (!stats) return;
    if (this.statDocs) this.statDocs.textContent = stats.total_documents || 0;
    if (this.statChunks) this.statChunks.textContent = stats.total_chunks || 0;
    if (this.statWords) this.statWords.textContent = (stats.total_words || 0).toLocaleString();
  }

  renderTable(documents) {
    if (!this.docsTableBody) return;
    this.docsTableBody.innerHTML = '';

    if (!documents || documents.length === 0) {
      this.docsTableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--text-dim); padding: 2rem;">
            No documents indexed yet. Upload files, scrape a URL, or click "Quick Ingest Workspace" to begin.
          </td>
        </tr>
      `;
      return;
    }

    documents.forEach((doc) => {
      const tr = document.createElement('tr');
      const badgeClass = doc.file_type === 'pdf' ? 'badge-primary' : (doc.file_type === 'web_url' ? 'badge-secondary' : 'badge-purple');
      
      tr.innerHTML = `
        <td><strong>${this.escapeHtml(doc.title)}</strong></td>
        <td><span class="badge ${badgeClass}">${doc.file_type.toUpperCase()}</span></td>
        <td><span class="badge badge-primary">${doc.chunk_count} Chunks</span></td>
        <td style="color: var(--text-dim); font-size: 0.8rem;">${doc.added_at}</td>
        <td>
          <button class="btn btn-outline-danger" data-id="${doc.id}" style="padding: 0.35rem 0.65rem; font-size: 0.75rem;">
            Delete
          </button>
        </td>
      `;

      tr.querySelector('button').addEventListener('click', async (e) => {
        const id = e.currentTarget.getAttribute('data-id');
        await this.deleteDoc(id);
      });

      this.docsTableBody.appendChild(tr);
    });
  }

  async handleFileUpload(files) {
    this.app.showLoader(
      "Vectorizing Learning Materials...",
      `Parsing ${files.length} file(s), extracting text structure, and generating semantic memory chunks.`
    );
    try {
      const res = await api.uploadFiles(files);
      this.app.showToast(`Indexed ${res.results.length} files successfully!`, 'success');
      this.refresh();
    } catch (err) {
      this.app.showToast(err.message, 'error');
    } finally {
      this.app.hideLoader();
    }
  }

  async handleUrlScrape() {
    const url = this.urlInput.value.trim();
    if (!url) {
      this.app.showToast('Please enter a valid URL', 'warning');
      return;
    }

    this.scrapeBtn.disabled = true;
    this.scrapeBtn.innerHTML = 'Scraping...';
    this.app.showLoader(
      "Scraping & Indexing Web Content...",
      `Fetching URL, stripping boilerplate scripts/ads, and embedding article text into vector memory.`
    );

    try {
      const res = await api.scrapeUrl(url);
      this.app.showToast(`Scraped "${res.title}" (${res.chunks_indexed} chunks)!`, 'success');
      this.urlInput.value = '';
      this.refresh();
    } catch (err) {
      this.app.showToast(err.message, 'error');
    } finally {
      this.app.hideLoader();
      this.scrapeBtn.disabled = false;
      this.scrapeBtn.innerHTML = 'Scrape & Ingest';
    }
  }

  async handleWorkspaceIngest() {
    this.workspaceIngestBtn.disabled = true;
    this.workspaceIngestBtn.innerHTML = 'Ingesting Workspace...';
    this.app.showLoader(
      "Ingesting C#/.NET Learning Workspace...",
      "Reading all 38 Markdown modules, header-aware chunking, and fitting vector indexes."
    );

    try {
      const res = await api.ingestWorkspace();
      this.app.showToast(`Successfully indexed ${res.ingested_count} study modules!`, 'success');
      this.refresh();
    } catch (err) {
      this.app.showToast(err.message, 'error');
    } finally {
      this.app.hideLoader();
      this.workspaceIngestBtn.disabled = false;
      this.workspaceIngestBtn.innerHTML = 'Quick Ingest Workspace';
    }
  }

  async handleReindexAll() {
    if (this.reindexAllBtn) {
      this.reindexAllBtn.disabled = true;
      this.reindexAllBtn.innerHTML = '<span>🔄</span> Re-Indexing...';
    }
    this.app.showLoader(
      "Refreshing & Re-Indexing Knowledge Base...",
      "Rescanning all uploaded files and workspace documents, re-calculating semantic vector embeddings, and discovering domains."
    );

    try {
      const res = await api.reindexAll();
      this.app.showToast(`Re-indexed ${res.reindexed_count} files across ${res.areas.length} domains!`, 'success');
      await this.refresh();
      if (this.app.interviewUI?.loadKnowledgeAreas) {
        await this.app.interviewUI.loadKnowledgeAreas();
      }
    } catch (err) {
      this.app.showToast(err.message, 'error');
    } finally {
      this.app.hideLoader();
      if (this.reindexAllBtn) {
        this.reindexAllBtn.disabled = false;
        this.reindexAllBtn.innerHTML = '<span>🔄</span> Refresh & Re-Index All';
      }
    }
  }

  async deleteDoc(id) {
    if (!confirm('Are you sure you want to remove this document and its semantic chunks?')) return;
    try {
      await api.deleteDocument(id);
      this.app.showToast('Document removed from memory and storage', 'success');
      await this.refresh();
      if (this.app.interviewUI?.loadKnowledgeAreas) {
        await this.app.interviewUI.loadKnowledgeAreas();
      }
    } catch (err) {
      this.app.showToast(err.message, 'error');
    }
  }

  async handleRagSearch() {
    const query = this.ragSearchInput.value.trim();
    if (!query) return;

    this.ragResultsContainer.innerHTML = '<p style="color: var(--text-dim);">Searching semantic vector space...</p>';
    try {
      const res = await api.searchRag(query);
      if (!res.results || res.results.length === 0) {
        this.ragResultsContainer.innerHTML = '<p style="color: var(--text-dim);">No relevant chunks found for this query.</p>';
        return;
      }

      this.ragResultsContainer.innerHTML = res.results.map((r, i) => `
        <div class="glass-card" style="padding: 1rem; margin-bottom: 0.75rem; border-left: 3px solid var(--secondary);">
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.35rem;">
            <strong style="font-size: 0.85rem; color: var(--secondary);">[Match ${i+1}] ${this.escapeHtml(r.doc_title || r.source)}</strong>
            <span class="badge badge-primary">Similarity: ${(r.score * 100).toFixed(1)}%</span>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.5rem;">Section: ${this.escapeHtml(r.header || 'General')}</div>
          <p style="font-size: 0.85rem; color: var(--text-main); line-height: 1.5;">${this.escapeHtml(r.text.substring(0, 240))}...</p>
        </div>
      `).join('');
    } catch (err) {
      this.ragResultsContainer.innerHTML = `<p style="color: var(--danger);">${err.message}</p>`;
    }
  }

  escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}
