import { api } from './api.js';

export class ScorecardUI {
  constructor(app) {
    this.app = app;
    this.scorecardData = null;
    this.currentSessionId = null;
    this.initElements();
  }

  initElements() {
    this.overallScoreEl = document.getElementById('sc-overall-score');
    this.verdictEl = document.getElementById('sc-verdict');
    this.summaryEl = document.getElementById('sc-summary');
    this.correctCountEl = document.getElementById('sc-correct-count');
    this.partialCountEl = document.getElementById('sc-partial-count');
    this.incorrectCountEl = document.getElementById('sc-incorrect-count');

    this.topicBarsContainer = document.getElementById('sc-topic-bars');
    this.roadmapContainer = document.getElementById('sc-roadmap-container');
    this.reviewContainer = document.getElementById('sc-review-accordion');
    this.historyBar = document.getElementById('history-bar-container');

    this.exportBtn = document.getElementById('export-report-btn');
    this.retakeBtn = document.getElementById('retake-interview-btn');

    if (this.exportBtn) {
      this.exportBtn.addEventListener('click', () => this.exportMarkdownReport());
    }
    if (this.retakeBtn) {
      this.retakeBtn.addEventListener('click', () => {
        this.app.switchTab('interview');
      });
    }
  }

  async refreshHistory() {
    if (!this.historyBar) return;
    try {
      const data = await api.getInterviewHistory();
      const items = data.history || [];

      if (!items.length) {
        this.historyBar.innerHTML = '<p style="color: var(--text-dim); font-size: 0.85rem; padding: 0.5rem 0;">No prior interviews completed yet.</p>';
        return;
      }

      this.historyBar.innerHTML = '';
      items.forEach((item) => {
        const card = document.createElement('div');
        const isActive = (item.session_id === this.currentSessionId);
        card.className = `history-card-item ${isActive ? 'active' : ''}`;
        
        const scoreColor = item.overall_score >= 80 ? 'var(--success)' : (item.overall_score >= 50 ? 'var(--warning)' : 'var(--danger)');
        const focusTitle = (item.focus_area && item.focus_area !== 'all') ? item.focus_area.toUpperCase() : 'MIXED TOPICS';

        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
            <span class="badge badge-purple">${item.level.toUpperCase()}</span>
            <span style="font-size: 0.75rem; color: var(--text-dim);">${item.date || ''}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 0.4rem;">
            <div class="history-score-val" style="color: ${scoreColor};">${item.overall_score}%</div>
            <span class="badge badge-secondary" style="font-size: 0.7rem;">${focusTitle}</span>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.35rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            ${this.escapeHtml(item.verdict || '')}
          </div>
        `;

        card.addEventListener('click', () => {
          this.currentSessionId = item.session_id;
          this.renderScorecard(item.scorecard, item);
          this.highlightActiveHistoryCard();
        });

        this.historyBar.appendChild(card);
      });
    } catch (err) {
      console.warn('Could not load history:', err);
    }
  }

  highlightActiveHistoryCard() {
    if (!this.historyBar) return;
    const cards = this.historyBar.querySelectorAll('.history-card-item');
    cards.forEach((c) => c.classList.remove('active'));
    // Active styling handled on click
  }

  renderScorecard(scorecard, session) {
    this.scorecardData = scorecard;
    if (session && session.session_id) {
      this.currentSessionId = session.session_id;
    }
    if (!scorecard) return;

    if (this.overallScoreEl) this.overallScoreEl.textContent = `${scorecard.overall_score}%`;
    if (this.verdictEl) this.verdictEl.textContent = scorecard.verdict;
    if (this.summaryEl) this.summaryEl.textContent = scorecard.summary;

    if (this.correctCountEl) this.correctCountEl.textContent = scorecard.correct_count;
    if (this.partialCountEl) this.partialCountEl.textContent = scorecard.partial_count;
    if (this.incorrectCountEl) this.incorrectCountEl.textContent = scorecard.incorrect_count;

    this.renderTopicBreakdown(scorecard.topic_breakdown);
    this.renderRoadmap(scorecard.actionable_roadmap);
    this.renderReviewAccordion(scorecard.evaluations);

    // Refresh history bar to include this latest session
    this.refreshHistory();
  }

  renderTopicBreakdown(topicStats) {
    if (!this.topicBarsContainer) return;
    this.topicBarsContainer.innerHTML = '';

    const entries = Object.entries(topicStats || {});
    if (!entries.length) {
      this.topicBarsContainer.innerHTML = '<p style="color: var(--text-dim);">No topic data available.</p>';
      return;
    }

    entries.forEach(([topic, stats]) => {
      const percentage = Math.round((stats.earned / Math.max(stats.max, 1)) * 100);
      const color = percentage >= 80 ? 'var(--success)' : (percentage >= 50 ? 'var(--warning)' : 'var(--danger)');

      const row = document.createElement('div');
      row.style.marginBottom = '1.25rem';
      row.innerHTML = `
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.35rem;">
          <strong style="color: var(--text-main);">${this.escapeHtml(topic)}</strong>
          <span style="color: ${color}; font-weight: 700;">${percentage}% (${stats.earned.toFixed(1)} / ${stats.max} pts)</span>
        </div>
        <div style="width: 100%; height: 8px; background: var(--bg-tertiary); border-radius: 4px; overflow: hidden;">
          <div style="height: 100%; width: ${percentage}%; background: ${color}; transition: width 0.4s ease;"></div>
        </div>
      `;
      this.topicBarsContainer.appendChild(row);
    });
  }

  renderRoadmap(roadmap) {
    if (!this.roadmapContainer) return;
    this.roadmapContainer.innerHTML = '';

    if (!roadmap || !roadmap.length) {
      this.roadmapContainer.innerHTML = '<p style="color: var(--text-dim);">No improvement recommendations needed!</p>';
      return;
    }

    roadmap.forEach((item, idx) => {
      const card = document.createElement('div');
      card.className = 'roadmap-card';
      card.innerHTML = `
        <h4>🚀 Action Item ${idx + 1}: ${this.escapeHtml(item.area)}</h4>
        <div class="roadmap-step"><strong>What to do:</strong> ${this.escapeHtml(item.what_to_do)}</div>
        <div class="roadmap-step"><strong>How to do:</strong> ${this.escapeHtml(item.how_to_do)}</div>
        <div class="roadmap-step"><strong>How to improve:</strong> ${this.escapeHtml(item.how_to_improve)}</div>
      `;
      this.roadmapContainer.appendChild(card);
    });
  }

  renderReviewAccordion(evaluations) {
    if (!this.reviewContainer) return;
    this.reviewContainer.innerHTML = '';

    (evaluations || []).forEach((ev, idx) => {
      const item = document.createElement('div');
      item.className = 'review-item';

      const statusBadge = ev.score >= 8.5
        ? '<span class="badge badge-success">✓ 10/10 Correct</span>'
        : (ev.score >= 4.0 ? `<span class="badge badge-warning">⚡ ${ev.score}/10 Partial</span>` : `<span class="badge badge-primary">✗ ${ev.score}/10 Needs Focus</span>`);

      const whatToLearn = ev.what_to_learn || `Master core principles, memory footprint, and architectural design of ${ev.topic}.`;
      const howToLearn = ev.how_to_learn || `Review ${ev.source_reference || 'module notes'}. Build an isolated prototype testing concurrency, edge cases, and performance profiling.`;

      item.innerHTML = `
        <div class="review-header">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <span style="font-weight: 700; color: var(--text-dim);">#${idx + 1}</span>
            <strong style="color: var(--text-main); font-size: 0.95rem;">${this.escapeHtml(ev.topic)}</strong>
            <span class="badge badge-secondary">${ev.type.toUpperCase()}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 1rem;">
            ${statusBadge}
            <span style="color: var(--text-dim); font-size: 0.85rem;">▼</span>
          </div>
        </div>
        <div class="review-body">
          <div style="margin-bottom: 1rem;">
            <div style="font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Question Prompt</div>
            <p style="font-weight: 600; margin-top: 0.25rem; line-height: 1.5;">${this.escapeHtml(ev.question)}</p>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
            <div style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 10px; border: 1px solid var(--border-subtle);">
              <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">💬 Candidate Answer Given</div>
              <p style="margin-top: 0.35rem; font-size: 0.9rem; color: var(--text-main);">${this.escapeHtml(ev.user_answer || '[No answer provided]')}</p>
            </div>
            <div style="background: rgba(16, 185, 129, 0.08); padding: 1rem; border-radius: 10px; border: 1px solid rgba(16, 185, 129, 0.25);">
              <div style="font-size: 0.75rem; color: var(--success); font-weight: 700; text-transform: uppercase;">🎯 Expected Standard / Correct Answer</div>
              <p style="margin-top: 0.35rem; font-size: 0.9rem; color: var(--text-main);">${this.escapeHtml(ev.correct_answer || 'Complete architectural coverage')}</p>
            </div>
          </div>

          <!-- Structured Learning Callouts: What & How to Learn -->
          <div class="learn-box learn-box-what">
            <strong style="color: var(--primary);">📚 What to Learn:</strong>
            <p style="margin-top: 0.2rem; color: var(--text-main);">${this.escapeHtml(whatToLearn)}</p>
          </div>

          <div class="learn-box learn-box-how">
            <strong style="color: var(--secondary);">🚀 How to Learn & Master:</strong>
            <p style="margin-top: 0.2rem; color: var(--text-main);">${this.escapeHtml(howToLearn)}</p>
          </div>

          <!-- Feedback & Citations -->
          <div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid var(--border-subtle);">
            <div style="font-size: 0.8rem; color: var(--text-dim); font-weight: 700; margin-bottom: 0.25rem;">Interviewer Assessment:</div>
            <p style="font-size: 0.9rem; color: var(--text-main);">${this.escapeHtml(ev.feedback)}</p>
          </div>

          ${ev.strengths ? `
            <div style="margin-top: 0.5rem; font-size: 0.85rem;">
              <strong style="color: var(--success);">Strengths Demonstrated:</strong> ${this.escapeHtml(ev.strengths)}
            </div>
          ` : ''}

          ${ev.improvements ? `
            <div style="margin-top: 0.5rem; font-size: 0.85rem;">
              <strong style="color: var(--warning);">Growth / Elevation Opportunity:</strong> ${this.escapeHtml(ev.improvements)}
            </div>
          ` : ''}

          ${ev.source_reference ? `
            <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 0.75rem;">
              📖 <em>Derived from Knowledge Base: ${this.escapeHtml(ev.source_reference)}</em>
            </div>
          ` : ''}
        </div>
      `;

      item.querySelector('.review-header').addEventListener('click', () => {
        item.classList.toggle('open');
      });

      this.reviewContainer.appendChild(item);
    });
  }

  exportMarkdownReport() {
    if (!this.scorecardData) {
      this.app.showToast('No scorecard data to export.', 'warning');
      return;
    }

    const sc = this.scorecardData;
    let md = `# Interview Assist - Assessment Report\n\n`;
    md += `**Date:** ${new Date().toLocaleDateString()}\n`;
    md += `**Proficiency Level:** ${sc.level.toUpperCase()}\n`;
    md += `**Overall Score:** ${sc.overall_score}%\n`;
    md += `**Verdict:** ${sc.verdict}\n\n`;
    md += `## Executive Summary\n${sc.summary}\n\n`;

    md += `## Actionable Improvement Roadmap\n\n`;
    (sc.actionable_roadmap || []).forEach((r, i) => {
      md += `### ${i + 1}. ${r.area}\n`;
      md += `- **What to do:** ${r.what_to_do}\n`;
      md += `- **How to do:** ${r.how_to_do}\n`;
      md += `- **How to improve:** ${r.how_to_improve}\n\n`;
    });

    md += `## Question Review & Learning Guides\n\n`;
    (sc.evaluations || []).forEach((ev, i) => {
      md += `### Question ${i + 1} (${ev.type.toUpperCase()}) - ${ev.score}/10 pts\n`;
      md += `**Topic:** ${ev.topic}\n`;
      md += `**Question:** ${ev.question}\n\n`;
      md += `**Candidate Answer:** ${ev.user_answer}\n\n`;
      md += `**Expected Standard:** ${ev.correct_answer}\n\n`;
      md += `**What to Learn:** ${ev.what_to_learn || ''}\n\n`;
      md += `**How to Learn:** ${ev.how_to_learn || ''}\n\n`;
      md += `**Interviewer Feedback:** ${ev.feedback}\n\n`;
      if (ev.source_reference) md += `*Source: ${ev.source_reference}*\n\n`;
      md += `---\n\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `interview_report_${sc.level}_${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
    this.app.showToast('Report downloaded as Markdown!', 'success');
  }

  escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}
