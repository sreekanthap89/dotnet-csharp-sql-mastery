import { api } from './api.js';
import { IngestionUI } from './ingestion_ui.js';
import { InterviewUI } from './interview_ui.js';
import { ScorecardUI } from './scorecard_ui.js';

class InterviewAssistApp {
  constructor() {
    this.activeTab = 'knowledge';
    this.init();
  }

  async init() {
    this.initTabs();
    this.initSettingsModal();

    this.ingestionUI = new IngestionUI(this);
    this.interviewUI = new InterviewUI(this);
    this.scorecardUI = new ScorecardUI(this);

    // Initial load
    await this.ingestionUI.refresh();
    await this.loadSettings();
  }

  initTabs() {
    const tabBtns = document.querySelectorAll('.nav-tab-btn');
    tabBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-tab');
        this.switchTab(target);
      });
    });
  }

  switchTab(tabName) {
    this.activeTab = tabName;

    // Update tab button styles
    document.querySelectorAll('.nav-tab-btn').forEach((btn) => {
      if (btn.getAttribute('data-tab') === tabName) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Toggle views
    document.querySelectorAll('.view-section').forEach((view) => {
      view.classList.remove('active');
    });

    const targetView = document.getElementById(`view-${tabName}`);
    if (targetView) {
      targetView.classList.add('active');
    }

    if (tabName === 'knowledge') {
      this.ingestionUI.refresh();
    } else if (tabName === 'interview') {
      this.interviewUI.loadKnowledgeAreas();
    } else if (tabName === 'scorecard') {
      this.scorecardUI.refreshHistory();
    }
  }

  showLoader(title = "Processing...", subtext = "Please wait a moment...") {
    const overlay = document.getElementById('global-loader');
    const titleEl = document.getElementById('loader-title');
    const subtextEl = document.getElementById('loader-subtext');
    if (titleEl) titleEl.textContent = title;
    if (subtextEl) subtextEl.textContent = subtext;
    if (overlay) overlay.classList.add('active');
  }

  hideLoader() {
    const overlay = document.getElementById('global-loader');
    if (overlay) overlay.classList.remove('active');
  }

  async loadSettings() {
    await this.loadLlmConfig();
  }

  async loadLlmConfig() {
    try {
      const data = await api.getLlmConfig();
      this.llmConfig = data;
      this.renderLlmSettingsUI();
    } catch (err) {
      console.warn('Could not load LLM config:', err);
    }
  }

  renderLlmSettingsUI() {
    if (!this.llmConfig) return;
    const { active_provider, active_model, providers, interview_preferences } = this.llmConfig;

    // 1. Update Header Badge & Footer
    this.updateHeaderBadge(active_provider, active_model);
    const footerProviderEl = document.getElementById('footer-active-provider');
    if (footerProviderEl) {
      footerProviderEl.textContent = `${active_provider} (${active_model || 'default'})`;
    }

    // 2. Update Provider Tab Dots and Status Tags
    ['ollama', 'lm_studio', 'gemini', 'claude', 'openrouter'].forEach((p) => {
      const dot = document.getElementById(`tab-dot-${p}`);
      const tag = document.getElementById(`status-tag-${p}`);
      const activateBtn = document.getElementById(`activate-btn-${p}`);
      const isActive = active_provider === p;

      if (dot) {
        dot.className = isActive ? 'tab-status-dot active-dot' : 'tab-status-dot';
      }
      if (tag) {
        tag.textContent = isActive ? 'ACTIVE LLM' : 'STANDBY';
        tag.className = isActive ? 'active-status-tag is-active' : 'active-status-tag';
      }
      if (activateBtn) {
        if (isActive) {
          activateBtn.textContent = '✓ Active Model';
          activateBtn.className = 'btn btn-sm btn-secondary';
          activateBtn.disabled = true;
        } else {
          activateBtn.textContent = '⚡ Set as Active LLM';
          activateBtn.className = 'btn btn-sm btn-accent activate-provider-btn';
          activateBtn.disabled = false;
        }
      }
    });

    // 3. Populate Ollama Form
    if (providers?.ollama) {
      const urlInput = document.getElementById('cfg-ollama-url');
      if (urlInput) urlInput.value = providers.ollama.base_url || 'http://localhost:11434';
      this.populateModelDropdown('ollama', providers.ollama.models || [], providers.ollama.model);
    }

    // 4. Populate LM Studio Form
    if (providers?.lm_studio) {
      const urlInput = document.getElementById('cfg-lm_studio-url');
      if (urlInput) urlInput.value = providers.lm_studio.base_url || 'http://localhost:1234/v1';
      this.populateModelDropdown('lm_studio', providers.lm_studio.models || ['local-model'], providers.lm_studio.model);
    }

    // 5. Populate Gemini Form
    if (providers?.gemini) {
      const keyInput = document.getElementById('cfg-gemini-key');
      if (keyInput) {
        keyInput.placeholder = providers.gemini.has_key ? '•••••••••••••••••••• (API Key Configured)' : 'AIzaSy...';
      }
      const modelSelect = document.getElementById('cfg-gemini-model');
      if (modelSelect && providers.gemini.model) {
        modelSelect.value = providers.gemini.model;
      }
    }

    // 6. Populate Claude Form
    if (providers?.claude) {
      const keyInput = document.getElementById('cfg-claude-key');
      if (keyInput) {
        keyInput.placeholder = providers.claude.has_key ? '•••••••••••••••••••• (API Key Configured)' : 'sk-ant-api...';
      }
      const modelSelect = document.getElementById('cfg-claude-model');
      if (modelSelect && providers.claude.model) {
        modelSelect.value = providers.claude.model;
      }
    }

    // 7. Populate OpenRouter Form
    if (providers?.openrouter) {
      const keyInput = document.getElementById('cfg-openrouter-key');
      if (keyInput) {
        keyInput.placeholder = providers.openrouter.has_key ? '•••••••••••••••••••• (API Key Configured)' : 'sk-or-v1-...';
      }
      const urlInput = document.getElementById('cfg-openrouter-url');
      if (urlInput) urlInput.value = providers.openrouter.base_url || 'https://openrouter.ai/api/v1';
      this.populateModelDropdown('openrouter', providers.openrouter.models || [], providers.openrouter.model);
    }

    // 8. Populate Preferences
    if (interview_preferences) {
      const tempRange = document.getElementById('cfg-pref-temperature');
      const tempVal = document.getElementById('temp-val-display');
      if (tempRange && interview_preferences.temperature !== undefined) {
        tempRange.value = interview_preferences.temperature;
        if (tempVal) tempVal.textContent = interview_preferences.temperature;
      }
      const fallbackCheck = document.getElementById('cfg-pref-fallback');
      if (fallbackCheck && interview_preferences.fallback_to_curated !== undefined) {
        fallbackCheck.checked = interview_preferences.fallback_to_curated;
      }
    }
  }

  populateModelDropdown(provider, models, selectedModel) {
    const select = document.getElementById(`cfg-${provider}-model`);
    if (!select) return;
    select.innerHTML = '';

    if (!models || models.length === 0) {
      const defaultOpt = document.createElement('option');
      defaultOpt.value = selectedModel || '';
      defaultOpt.textContent = selectedModel || '(Click Query Models to fetch)';
      select.appendChild(defaultOpt);
      return;
    }

    models.forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      if (m === selectedModel) opt.selected = true;
      select.appendChild(opt);
    });

    if (selectedModel && !models.includes(selectedModel)) {
      const customOpt = document.createElement('option');
      customOpt.value = selectedModel;
      customOpt.textContent = `${selectedModel} (custom)`;
      customOpt.selected = true;
      select.appendChild(customOpt);
    }
  }

  updateHeaderBadge(provider, model) {
    const badge = document.getElementById('active-llm-badge');
    const iconEl = document.getElementById('active-llm-icon');
    const labelEl = document.getElementById('active-llm-label');
    if (!badge || !iconEl || !labelEl) return;

    const icons = {
      ollama: '🦙',
      lm_studio: '🖥️',
      gemini: '✨',
      claude: '🧠',
      openrouter: '🌐',
    };

    const icon = icons[provider] || '🤖';
    const shortModel = model ? (model.includes('/') ? model.split('/')[1] : model.split(':')[0]) : 'Ready';
    iconEl.textContent = icon;
    labelEl.textContent = `${provider || 'AI'}: ${shortModel}`;
    badge.className = 'badge badge-success';
    badge.title = `Active AI: ${provider} (${model}) - Click to configure`;
  }

  initSettingsModal() {
    this.settingsModal = document.getElementById('settings-modal');
    this.openSettingsBtn = document.getElementById('open-settings-btn');
    this.closeSettingsBtn = document.getElementById('close-settings-btn');
    this.cancelSettingsBtn = document.getElementById('cancel-settings-btn');
    this.saveSettingsBtn = document.getElementById('save-settings-btn');
    this.activeBadge = document.getElementById('active-llm-badge');

    // 1. Open / Close Modal
    if (this.openSettingsBtn) {
      this.openSettingsBtn.addEventListener('click', () => {
        this.settingsModal.classList.add('active');
        this.loadLlmConfig();
      });
    }
    if (this.activeBadge) {
      this.activeBadge.addEventListener('click', () => {
        this.settingsModal.classList.add('active');
        this.loadLlmConfig();
      });
    }
    if (this.closeSettingsBtn) {
      this.closeSettingsBtn.addEventListener('click', () => {
        this.settingsModal.classList.remove('active');
      });
    }
    if (this.cancelSettingsBtn) {
      this.cancelSettingsBtn.addEventListener('click', () => {
        this.settingsModal.classList.remove('active');
      });
    }
    if (this.settingsModal) {
      this.settingsModal.addEventListener('click', (e) => {
        if (e.target === this.settingsModal) {
          this.settingsModal.classList.remove('active');
        }
      });
    }

    // 2. Tab Navigation
    const tabBtns = document.querySelectorAll('.settings-tab-btn');
    tabBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-provider-tab');
        tabBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');

        document.querySelectorAll('.settings-panel').forEach((p) => p.classList.remove('active'));
        const targetPanel = document.getElementById(`panel-${tabId}`);
        if (targetPanel) targetPanel.classList.add('active');
      });
    });

    // 3. Eye Toggle Password Visibility
    document.querySelectorAll('.btn-toggle-eye').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        const input = document.getElementById(targetId);
        if (!input) return;
        if (input.type === 'password') {
          input.type = 'text';
          btn.textContent = '🙈';
        } else {
          input.type = 'password';
          btn.textContent = '👁️';
        }
      });
    });

    // 4. Reset Default URL Buttons
    document.querySelectorAll('.reset-url-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        const defaultVal = btn.getAttribute('data-default');
        const input = document.getElementById(targetId);
        if (input && defaultVal) {
          input.value = defaultVal;
          this.showToast(`Reset to ${defaultVal}`, 'info');
        }
      });
    });

    // 5. Temperature Range Feedback
    const tempRange = document.getElementById('cfg-pref-temperature');
    const tempVal = document.getElementById('temp-val-display');
    if (tempRange && tempVal) {
      tempRange.addEventListener('input', () => {
        tempVal.textContent = tempRange.value;
      });
    }

    // 6. Fetch / Query Models Buttons
    document.querySelectorAll('.fetch-models-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const provider = btn.getAttribute('data-provider');
        await this.handleFetchModels(provider, btn);
      });
    });

    // 7. Test Connection Buttons
    document.querySelectorAll('.test-provider-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const provider = btn.getAttribute('data-provider');
        await this.handleTestConnection(provider, btn);
      });
    });

    // 8. Set as Active LLM Buttons
    document.querySelectorAll('.activate-provider-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const provider = btn.getAttribute('data-provider');
        await this.handleActivateProvider(provider);
      });
    });

    // 9. Save All Settings Button
    if (this.saveSettingsBtn) {
      this.saveSettingsBtn.addEventListener('click', async () => {
        await this.handleSaveAllSettings();
      });
    }
  }

  getSelectedModelForProvider(provider) {
    const customInput = document.getElementById(`cfg-${provider}-custom-model`);
    if (customInput && customInput.value.trim()) {
      return customInput.value.trim();
    }
    const select = document.getElementById(`cfg-${provider}-model`);
    return select ? select.value : '';
  }

  collectProviderConfigOverride(provider) {
    const cfg = {};
    if (provider === 'ollama') {
      const url = document.getElementById('cfg-ollama-url')?.value.trim();
      const model = this.getSelectedModelForProvider('ollama');
      if (url) cfg.base_url = url;
      if (model) cfg.model = model;
    } else if (provider === 'lm_studio') {
      const url = document.getElementById('cfg-lm_studio-url')?.value.trim();
      const model = this.getSelectedModelForProvider('lm_studio');
      if (url) cfg.base_url = url;
      if (model) cfg.model = model;
    } else if (provider === 'gemini') {
      const key = document.getElementById('cfg-gemini-key')?.value.trim();
      const model = document.getElementById('cfg-gemini-model')?.value.trim();
      if (key) cfg.api_key = key;
      if (model) cfg.model = model;
    } else if (provider === 'claude') {
      const key = document.getElementById('cfg-claude-key')?.value.trim();
      const model = document.getElementById('cfg-claude-model')?.value.trim();
      if (key) cfg.api_key = key;
      if (model) cfg.model = model;
    } else if (provider === 'openrouter') {
      const key = document.getElementById('cfg-openrouter-key')?.value.trim();
      const url = document.getElementById('cfg-openrouter-url')?.value.trim();
      const model = this.getSelectedModelForProvider('openrouter');
      if (key) cfg.api_key = key;
      if (url) cfg.base_url = url;
      if (model) cfg.model = model;
    }
    return cfg;
  }

  async handleTestConnection(provider, btn) {
    const resultBox = document.getElementById(`test-result-${provider}`);
    if (!resultBox) return;

    // Set UI to testing
    const originalBtnText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ Testing...';

    resultBox.className = 'test-result-box testing';
    resultBox.innerHTML = `
      <span class="test-status-pill pill-testing">Testing</span>
      <span class="test-msg">Sending verification ping to ${provider}...</span>
    `;

    try {
      const configOverride = this.collectProviderConfigOverride(provider);
      const res = await api.testLlmProvider(provider, configOverride);

      if (res.status === 'success') {
        resultBox.className = 'test-result-box success';
        resultBox.innerHTML = `
          <span class="test-status-pill pill-success">✓ Online</span>
          <span class="latency-badge">⚡ ${res.latency_ms.toLocaleString()} ms</span>
          <span class="test-msg">Verified: <strong>${this.escapeHtml(res.model)}</strong> ready. Response: "${this.escapeHtml(res.reply)}"</span>
        `;
        this.showToast(`${provider.toUpperCase()} responded in ${res.latency_ms}ms!`, 'success');
      } else {
        resultBox.className = 'test-result-box error';
        resultBox.innerHTML = `
          <span class="test-status-pill pill-error">✗ Failed</span>
          <span class="test-msg">${this.escapeHtml(res.error || 'Connection failed')}</span>
        `;
        this.showToast(`Test failed for ${provider}`, 'error');
      }
    } catch (err) {
      resultBox.className = 'test-result-box error';
      resultBox.innerHTML = `
        <span class="test-status-pill pill-error">✗ Network Error</span>
        <span class="test-msg">${this.escapeHtml(err.message)}</span>
      `;
      this.showToast(`Error testing ${provider}: ${err.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = originalBtnText;
    }
  }

  async handleFetchModels(provider, btn) {
    const originalBtnText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '🔄 Querying...';

    try {
      const configOverride = this.collectProviderConfigOverride(provider);
      const res = await api.fetchLlmModels(provider, configOverride);
      if (res.models && res.models.length > 0) {
        const currentSelected = this.getSelectedModelForProvider(provider);
        this.populateModelDropdown(provider, res.models, currentSelected);
        this.showToast(`Found ${res.models.length} models for ${provider}!`, 'success');
      } else {
        this.showToast(`No models discovered from ${provider}`, 'info');
      }
    } catch (err) {
      this.showToast(`Failed to query models: ${err.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = originalBtnText;
    }
  }

  async handleActivateProvider(provider) {
    const model = this.getSelectedModelForProvider(provider);
    try {
      // Also save any newly typed credentials/URL for this provider first
      const configOverride = this.collectProviderConfigOverride(provider);
      if (Object.keys(configOverride).length > 0 && this.llmConfig?.providers?.[provider]) {
        Object.assign(this.llmConfig.providers[provider], configOverride);
        await api.updateLlmConfig(this.llmConfig);
      }

      const res = await api.selectActiveLlm(provider, model);
      if (this.llmConfig) {
        this.llmConfig.active_provider = res.active_provider;
        this.llmConfig.active_model = res.active_model;
      }
      this.renderLlmSettingsUI();
      this.showToast(`Active LLM switched to ${provider} (${res.active_model || 'default'})!`, 'success');
    } catch (err) {
      this.showToast(`Failed to activate provider: ${err.message}`, 'error');
    }
  }

  async handleSaveAllSettings() {
    try {
      const fullConfig = {
        active_provider: this.llmConfig?.active_provider || 'ollama',
        active_model: this.llmConfig?.active_model || 'qwen3-coder:30b',
        providers: {
          ollama: {
            base_url: document.getElementById('cfg-ollama-url')?.value.trim() || 'http://localhost:11434',
            model: this.getSelectedModelForProvider('ollama'),
          },
          lm_studio: {
            base_url: document.getElementById('cfg-lm_studio-url')?.value.trim() || 'http://localhost:1234/v1',
            model: this.getSelectedModelForProvider('lm_studio'),
          },
          gemini: {
            api_key: document.getElementById('cfg-gemini-key')?.value.trim() || undefined,
            model: document.getElementById('cfg-gemini-model')?.value.trim() || 'gemini-2.5-flash',
          },
          claude: {
            api_key: document.getElementById('cfg-claude-key')?.value.trim() || undefined,
            model: document.getElementById('cfg-claude-model')?.value.trim() || 'claude-3-7-sonnet-20250219',
          },
          openrouter: {
            api_key: document.getElementById('cfg-openrouter-key')?.value.trim() || undefined,
            base_url: document.getElementById('cfg-openrouter-url')?.value.trim() || 'https://openrouter.ai/api/v1',
            model: this.getSelectedModelForProvider('openrouter'),
          },
        },
        interview_preferences: {
          temperature: parseFloat(document.getElementById('cfg-pref-temperature')?.value || '0.7'),
          fallback_to_curated: document.getElementById('cfg-pref-fallback')?.checked ?? true,
        },
      };

      const updated = await api.updateLlmConfig(fullConfig);
      this.llmConfig = updated;
      this.renderLlmSettingsUI();
      this.showToast('All LLM configurations & credentials saved successfully!', 'success');
      this.settingsModal.classList.remove('active');
    } catch (err) {
      this.showToast(`Failed to save settings: ${err.message}`, 'error');
    }
  }

  showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✓' : (type === 'error' ? '✗' : 'ℹ');
    toast.innerHTML = `<span style="font-weight: 700;">${icon}</span> <span>${this.escapeHtml(message)}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}

// Instantiate on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.app = new InterviewAssistApp();
});
