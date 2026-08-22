/**
 * Literature Review - Ask Corpus Q&A UI Module
 */

export function initAskCorpusUI(apiBase = '') {
    const askBtn = document.getElementById('lr-qa-submit-btn');
    const input = document.getElementById('lr-qa-input');

    if (askBtn && input) {
        askBtn.addEventListener('click', () => submitAskCorpus(apiBase));
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') submitAskCorpus(apiBase);
        });
    }
}

export async function submitAskCorpus(apiBase = '') {
    const corpusId = window.getCurrentCorpusId ? window.getCurrentCorpusId() : null;
    if (!corpusId) {
        alert('Please perform a search and initialize a corpus first.');
        return;
    }

    const input = document.getElementById('lr-qa-input');
    const question = input ? input.value.trim() : '';
    if (!question) return;

    const area = document.getElementById('lr-qa-response-area');
    const answerEl = document.getElementById('lr-qa-answer-text');
    const badgeEl = document.getElementById('lr-qa-validation-badge');
    const askBtn = document.getElementById('lr-qa-submit-btn');

    if (area) area.style.display = 'block';
    if (answerEl) answerEl.innerHTML = `<em>Thinking &amp; grounding in corpus evidence...</em>`;
    if (badgeEl) badgeEl.innerHTML = '';
    if (askBtn) askBtn.disabled = true;

    try {
        const resp = await fetch(`${apiBase}/api/literature-review/corpus/${corpusId}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        if (!resp.ok) throw new Error(`Q&A failed: HTTP ${resp.status}`);
        const data = await resp.json();

        if (answerEl) answerEl.innerText = data.answer;
        if (badgeEl) {
            const isGrounded = data.validation ? data.validation.is_grounded : true;
            badgeEl.className = `lr-qa-validation-badge ${isGrounded ? 'verified' : 'warning'}`;
            badgeEl.innerHTML = isGrounded
                ? `<i data-lucide="shield-check" style="width:14px;height:14px;"></i> Grounded in Corpus (${data.validation.verified_citations} verified citations)`
                : `<i data-lucide="alert-triangle" style="width:14px;height:14px;"></i> Caution: Some citations unverified`;
        }

        if (window.lucide) window.lucide.createIcons();

    } catch (e) {
        console.error('Ask Corpus error:', e);
        if (answerEl) answerEl.innerText = `Error: ${e.message}`;
    } finally {
        if (askBtn) askBtn.disabled = false;
    }
}
