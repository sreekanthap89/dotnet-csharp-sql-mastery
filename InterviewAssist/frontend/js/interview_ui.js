import { api } from './api.js';

export class InterviewUI {
  constructor(app) {
    this.app = app;
    this.currentSession = null;
    this.currentIndex = 0;
    this.timerInterval = null;
    this.elapsedSeconds = 0;

    // Config state
    this.selectedLevel = 'intermediate';
    this.selectedFocusArea = 'all';
    this.selectedQuestionCount = 10;
    this.selectedTypes = ['mcq', 'true_false', 'descriptive'];

    this.initElements();
    this.bindEvents();
  }

  initElements() {
    // Config View
    this.configView = document.getElementById('interview-config-view');
    this.arenaView = document.getElementById('interview-arena-view');
    this.startBtn = document.getElementById('start-interview-btn');
    this.levelCards = document.querySelectorAll('.level-card');
    this.areaContainer = document.getElementById('area-selection-container');
    this.refreshDomainsBtn = document.getElementById('btn-refresh-domains');
    this.countBtns = document.querySelectorAll('.count-btn');
    this.customCountInput = document.getElementById('custom-count-input');

    // Arena View
    this.qProgressText = document.getElementById('q-progress-text');
    this.qProgressBar = document.getElementById('q-progress-bar');
    this.qTimer = document.getElementById('q-timer');
    this.qNavGrid = document.getElementById('q-nav-grid');
    this.qBadgeType = document.getElementById('q-badge-type');
    this.qBadgeLevel = document.getElementById('q-badge-level');
    this.qBadgeTopic = document.getElementById('q-badge-topic');
    this.qStem = document.getElementById('q-stem');
    this.qAnswerContainer = document.getElementById('q-answer-container');
    this.qHintBox = document.getElementById('q-hint-box');

    // Controls
    this.prevBtn = document.getElementById('prev-q-btn');
    this.nextBtn = document.getElementById('next-q-btn');
    this.submitBtn = document.getElementById('submit-q-btn');
    this.hintBtn = document.getElementById('hint-q-btn');
    this.finishBtn = document.getElementById('finish-interview-btn');

    // Initial load of dynamic technology domains
    this.loadKnowledgeAreas();
  }

  async loadKnowledgeAreas(showToast = false) {
    if (!this.areaContainer) return;
    try {
      const data = await api.getKnowledgeAreas();
      const areas = data.areas || [];

      this.areaContainer.innerHTML = '';
      if (!areas.length) {
        this.areaContainer.innerHTML = '<div style="grid-column: 1 / -1; color: var(--text-dim); text-align: center; padding: 1rem;">No topics available yet. Ingest documents to populate domains.</div>';
        return;
      }

      // Check if current selected area still exists
      const areaExists = areas.some((a) => a.id === this.selectedFocusArea);
      if (!areaExists) {
        this.selectedFocusArea = 'all';
      }

      areas.forEach((area) => {
        const card = document.createElement('div');
        const isSelected = area.id === this.selectedFocusArea;
        card.className = `area-card ${isSelected ? 'selected' : ''}`;
        card.setAttribute('data-area', area.id);

        const icon = area.icon || '📖';
        const countBadge = area.count > 0 ? `<span class="badge badge-secondary" style="font-size: 0.7rem; margin-left: 0.5rem;">${area.count} doc${area.count > 1 ? 's' : ''}</span>` : '';

        card.innerHTML = `
          <div class="area-icon">${icon}</div>
          <div class="area-info" style="flex: 1;">
            <div style="display: flex; align-items: center;">
              <h4 style="margin: 0; font-size: 0.95rem;">${this.escapeHtml(area.name)}</h4>
              ${countBadge}
            </div>
            <p style="margin-top: 0.25rem; font-size: 0.8rem; color: var(--text-dim); line-height: 1.35;">
              ${this.escapeHtml(area.description || '')}
            </p>
          </div>
        `;

        card.addEventListener('click', () => {
          this.areaContainer.querySelectorAll('.area-card').forEach((c) => c.classList.remove('selected'));
          card.classList.add('selected');
          this.selectedFocusArea = area.id;
        });

        this.areaContainer.appendChild(card);
      });

      if (showToast) {
        this.app.showToast(`Domains updated (${areas.length} available)`, 'info');
      }
    } catch (err) {
      console.warn('Failed to load knowledge areas:', err);
    }
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  bindEvents() {
    // Level selection
    this.levelCards.forEach((card) => {
      card.addEventListener('click', () => {
        this.levelCards.forEach((c) => c.classList.remove('selected'));
        card.classList.add('selected');
        this.selectedLevel = card.getAttribute('data-level');
      });
    });

    // Refresh domains button
    if (this.refreshDomainsBtn) {
      this.refreshDomainsBtn.addEventListener('click', async () => {
        const origHtml = this.refreshDomainsBtn.innerHTML;
        this.refreshDomainsBtn.disabled = true;
        this.refreshDomainsBtn.innerHTML = '<span>🔄</span> Syncing...';
        await this.loadKnowledgeAreas(true);
        this.refreshDomainsBtn.disabled = false;
        this.refreshDomainsBtn.innerHTML = origHtml;
      });
    }

    // Count selection
    this.countBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        this.countBtns.forEach((b) => b.classList.remove('selected'));
        btn.classList.add('selected');
        const count = parseInt(btn.getAttribute('data-count'), 10);
        if (count > 0) {
          this.selectedQuestionCount = count;
          if (this.customCountInput) this.customCountInput.value = '';
        }
      });
    });

    if (this.customCountInput) {
      this.customCountInput.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        if (val && val >= 3 && val <= 50) {
          this.countBtns.forEach((b) => b.classList.remove('selected'));
          this.selectedQuestionCount = val;
        }
      });
    }

    // Start Interview
    if (this.startBtn) {
      this.startBtn.addEventListener('click', () => this.handleStartInterview());
    }

    // Question navigation
    if (this.prevBtn) {
      this.prevBtn.addEventListener('click', () => this.goToQuestion(this.currentIndex - 1));
    }
    if (this.nextBtn) {
      this.nextBtn.addEventListener('click', () => this.goToQuestion(this.currentIndex + 1));
    }
    if (this.submitBtn) {
      this.submitBtn.addEventListener('click', () => this.saveCurrentAnswer(true));
    }
    if (this.hintBtn) {
      this.hintBtn.addEventListener('click', () => this.toggleHint());
    }
    if (this.finishBtn) {
      this.finishBtn.addEventListener('click', () => this.handleFinishInterview());
    }
  }

  async handleStartInterview() {
    // Collect question type checkboxes
    const types = [];
    if (document.getElementById('type-mcq')?.checked) types.push('mcq');
    if (document.getElementById('type-tf')?.checked) types.push('true_false');
    if (document.getElementById('type-desc')?.checked) types.push('descriptive');

    if (types.length === 0) {
      this.app.showToast('Please select at least one question format (MCQ, True/False, or Descriptive).', 'warning');
      this.startBtn.disabled = false;
      this.startBtn.innerHTML = '🚀 Begin Interview Round';
      return;
    }

    // Show contextual loader
    // Show contextual loader with active LLM information
    const areaTitle = this.selectedFocusArea.toUpperCase();
    const typeLabel = types.length === 1 ? `[${types[0].toUpperCase()} ONLY]` : `[${types.join(', ').toUpperCase()}]`;
    const activeProvider = (this.app.llmConfig?.active_provider || 'AI Engine').toUpperCase();
    const activeModel = this.app.llmConfig?.active_model ? ` (${this.app.llmConfig.active_model})` : '';

    this.app.showLoader(
      `Synthesizing Questions with ${activeProvider}${activeModel}...`,
      `Generating ${this.selectedQuestionCount} ${typeLabel} questions for [${areaTitle}] at [${this.selectedLevel.toUpperCase()}] level via ${activeProvider}.`
    );

    try {
      const session = await api.startInterview({
        level: this.selectedLevel,
        totalQuestions: this.selectedQuestionCount,
        focusArea: this.selectedFocusArea,
        questionTypes: types,
      });

      this.currentSession = session;
      this.currentIndex = 0;
      this.elapsedSeconds = 0;
      this.startTimer();

      // Switch to Arena view
      this.configView.style.display = 'none';
      this.arenaView.style.display = 'block';

      this.renderNavGrid();
      this.renderCurrentQuestion();
      this.app.showToast('Interview started! Good luck.', 'success');
    } catch (err) {
      this.app.showToast(err.message, 'error');
    } finally {
      this.app.hideLoader();
      this.startBtn.disabled = false;
      this.startBtn.innerHTML = 'Begin Interview Round';
    }
  }

  startTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds++;
      const mins = String(Math.floor(this.elapsedSeconds / 60)).padStart(2, '0');
      const secs = String(this.elapsedSeconds % 60).padStart(2, '0');
      if (this.qTimer) this.qTimer.textContent = `${mins}:${secs}`;
    }, 1000);
  }

  stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  renderNavGrid() {
    if (!this.qNavGrid || !this.currentSession) return;
    this.qNavGrid.innerHTML = '';

    this.currentSession.questions.forEach((q, idx) => {
      const btn = document.createElement('button');
      btn.className = 'q-nav-btn';
      btn.textContent = idx + 1;

      if (idx === this.currentIndex) {
        btn.classList.add('active');
      }

      btn.addEventListener('click', () => {
        this.saveCurrentAnswer(false);
        this.goToQuestion(idx);
      });

      this.qNavGrid.appendChild(btn);
    });
  }

  updateNavGridStates() {
    const btns = this.qNavGrid.querySelectorAll('.q-nav-btn');
    btns.forEach((btn, idx) => {
      btn.classList.remove('active');
      if (idx === this.currentIndex) {
        btn.classList.add('active');
      }
      const q = this.currentSession.questions[idx];
      const hasAnswer = this.currentSession.answers && this.currentSession.answers[q.id];
      if (hasAnswer) {
        btn.classList.add('answered');
      }
    });
  }

  goToQuestion(index) {
    if (!this.currentSession || index < 0 || index >= this.currentSession.questions.length) return;
    this.currentIndex = index;
    this.renderCurrentQuestion();
    this.updateNavGridStates();
  }

  renderCurrentQuestion() {
    const q = this.currentSession.questions[this.currentIndex];
    const total = this.currentSession.questions.length;

    // Badges & metadata
    if (this.qProgressText) this.qProgressText.textContent = `Question ${this.currentIndex + 1} of ${total}`;
    if (this.qProgressBar) this.qProgressBar.style.width = `${((this.currentIndex + 1) / total) * 100}%`;
    if (this.qBadgeType) this.qBadgeType.textContent = q.type.replace('_', ' ').toUpperCase();
    if (this.qBadgeLevel) this.qBadgeLevel.textContent = q.level.toUpperCase();
    if (this.qBadgeTopic) this.qBadgeTopic.textContent = q.topic;
    if (this.qStem) this.qStem.innerHTML = this.formatQuestionStem(q.question);

    // Reset hint box
    if (this.qHintBox) {
      this.qHintBox.style.display = 'none';
      this.qHintBox.innerHTML = '';
    }

    // Get current answer if exists
    const existingAnswer = (this.currentSession.answers && this.currentSession.answers[q.id])
      ? this.currentSession.answers[q.id].user_answer
      : '';

    // Render Answer Input according to question type
    this.qAnswerContainer.innerHTML = '';

    if (q.type === 'mcq') {
      this.renderMcqOptions(q, existingAnswer);
    } else if (q.type === 'true_false') {
      this.renderTrueFalseOptions(q, existingAnswer);
    } else {
      this.renderDescriptiveInput(q, existingAnswer);
    }

    // Navigation buttons state
    this.prevBtn.disabled = (this.currentIndex === 0);
    this.nextBtn.textContent = (this.currentIndex === total - 1) ? 'Review / Finish' : 'Next Question';
  }

  formatQuestionStem(text) {
    // Preserve linebreaks and highlight code if present
    const escaped = this.escapeHtml(text);
    return escaped.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  }

  renderMcqOptions(q, existingAnswer) {
    const container = document.createElement('div');
    container.className = 'options-list';

    (q.options || []).forEach((opt, idx) => {
      const letter = String.fromCharCode(65 + idx);
      const isSelected = existingAnswer && (existingAnswer.startsWith(letter) || existingAnswer === opt);

      const item = document.createElement('div');
      item.className = `option-item ${isSelected ? 'selected' : ''}`;
      item.setAttribute('data-letter', letter);
      item.setAttribute('data-option', opt);

      item.innerHTML = `
        <div class="option-indicator">${letter}</div>
        <div class="option-text">${this.escapeHtml(opt)}</div>
      `;

      item.addEventListener('click', () => {
        container.querySelectorAll('.option-item').forEach((i) => i.classList.remove('selected'));
        item.classList.add('selected');
        this.recordLocalAnswer(q.id, opt);
      });

      container.appendChild(item);
    });

    this.qAnswerContainer.appendChild(container);
  }

  renderTrueFalseOptions(q, existingAnswer) {
    const container = document.createElement('div');
    container.className = 'tf-group';

    const trueBtn = document.createElement('button');
    trueBtn.className = `tf-btn ${existingAnswer.toLowerCase() === 'true' ? 'selected-true' : ''}`;
    trueBtn.innerHTML = '<span>✓</span> TRUE';

    const falseBtn = document.createElement('button');
    falseBtn.className = `tf-btn ${existingAnswer.toLowerCase() === 'false' ? 'selected-false' : ''}`;
    falseBtn.innerHTML = '<span>✗</span> FALSE';

    trueBtn.addEventListener('click', () => {
      trueBtn.classList.add('selected-true');
      falseBtn.classList.remove('selected-false');
      this.recordLocalAnswer(q.id, 'True');
    });

    falseBtn.addEventListener('click', () => {
      falseBtn.classList.add('selected-false');
      trueBtn.classList.remove('selected-true');
      this.recordLocalAnswer(q.id, 'False');
    });

    container.appendChild(trueBtn);
    container.appendChild(falseBtn);
    this.qAnswerContainer.appendChild(container);
  }

  renderDescriptiveInput(q, existingAnswer) {
    const textarea = document.createElement('textarea');
    textarea.className = 'descriptive-area';
    textarea.placeholder = 'Structure your response clearly. Detail your architectural approach, concurrency considerations, design patterns, and edge cases...';
    textarea.value = existingAnswer || '';

    const helper = document.createElement('div');
    helper.className = 'descriptive-helper';
    helper.innerHTML = `
      <span>💡 Markdown and code snippets supported</span>
      <span id="desc-word-counter">Words: ${existingAnswer ? existingAnswer.split(/\s+/).filter(Boolean).length : 0}</span>
    `;

    textarea.addEventListener('input', (e) => {
      const val = e.target.value;
      const counter = document.getElementById('desc-word-counter');
      if (counter) counter.textContent = `Words: ${val.split(/\s+/).filter(Boolean).length}`;
      this.recordLocalAnswer(q.id, val);
    });

    this.qAnswerContainer.appendChild(textarea);
    this.qAnswerContainer.appendChild(helper);
  }

  recordLocalAnswer(questionId, answer) {
    if (!this.currentSession.answers) this.currentSession.answers = {};
    this.currentSession.answers[questionId] = {
      question_id: questionId,
      user_answer: answer,
    };
    this.updateNavGridStates();
  }

  async saveCurrentAnswer(showFeedback = true) {
    const q = this.currentSession.questions[this.currentIndex];
    const ansObj = this.currentSession.answers ? this.currentSession.answers[q.id] : null;
    const userAnswer = ansObj ? ansObj.user_answer : '';

    if (!userAnswer && showFeedback) {
      this.app.showToast('No answer entered yet for this question.', 'warning');
      return;
    }

    try {
      await api.submitAnswer(this.currentSession.session_id, q.id, userAnswer, this.elapsedSeconds);
      if (showFeedback) this.app.showToast('Answer recorded!', 'success');
      this.updateNavGridStates();

      // Auto-advance if not last
      if (showFeedback && this.currentIndex < this.currentSession.questions.length - 1) {
        this.goToQuestion(this.currentIndex + 1);
      }
    } catch (err) {
      console.error(err);
    }
  }

  toggleHint() {
    const q = this.currentSession.questions[this.currentIndex];
    if (!this.qHintBox) return;

    if (this.qHintBox.style.display === 'block') {
      this.qHintBox.style.display = 'none';
      return;
    }

    const hintText = q.key_points
      ? `Key Focus Areas to address: ${q.key_points.join(' • ')}`
      : `Reference context: Consider the architecture documented in ${q.source_reference}.`;

    this.qHintBox.innerHTML = `
      <div class="glass-card" style="padding: 1rem; border-left: 3px solid var(--warning); margin-bottom: 1rem;">
        <strong style="color: var(--warning); font-size: 0.85rem;">🔍 Interviewer Clarification / Hint:</strong>
        <p style="font-size: 0.9rem; margin-top: 0.35rem;">${this.escapeHtml(hintText)}</p>
      </div>
    `;
    this.qHintBox.style.display = 'block';
  }

  async handleFinishInterview() {
    this.saveCurrentAnswer(false);
    this.stopTimer();

    this.finishBtn.disabled = true;
    this.finishBtn.innerHTML = 'Analyzing & Scoring Responses...';

    // Show Loader with active LLM information
    const evalProvider = (this.app.llmConfig?.active_provider || 'AI Engine').toUpperCase();
    this.app.showLoader(
      `Evaluating Responses with ${evalProvider}...`,
      "Grading submitted answers against engineering criteria and compiling your actionable improvement roadmap."
    );

    try {
      const res = await api.completeInterview(this.currentSession.session_id);
      this.app.showToast('Interview evaluation complete!', 'success');
      
      // Pass scorecard to scorecard UI and switch tab
      this.app.scorecardUI.renderScorecard(res.scorecard, this.currentSession);
      this.app.switchTab('scorecard');

      // Reset arena
      this.arenaView.style.display = 'none';
      this.configView.style.display = 'block';
    } catch (err) {
      this.app.showToast(err.message, 'error');
    } finally {
      this.app.hideLoader();
      this.finishBtn.disabled = false;
      this.finishBtn.innerHTML = 'Finish & Grade Interview';
    }
  }

  escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}
