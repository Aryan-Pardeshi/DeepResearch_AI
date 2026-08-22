/**
 * Literature Review - Synthesis UI Module (Themes, Contradictions & Gaps)
 */

export function initSynthesisUI(apiBase = '') {
    const runBtn = document.getElementById('lr-run-synthesis-btn');
    if (runBtn) {
        runBtn.addEventListener('click', () => runSynthesis(apiBase));
    }
}

export async function runSynthesis(apiBase = '') {
    const corpusId = window.getCurrentCorpusId ? window.getCurrentCorpusId() : null;
    if (!corpusId) return;

    const runBtn = document.getElementById('lr-run-synthesis-btn');
    if (runBtn) {
        runBtn.disabled = true;
        runBtn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width:15px;height:15px;"></i> Synthesizing...`;
    }

    try {
        const resp = await fetch(`${apiBase}/api/literature-review/corpus/${corpusId}/synthesis`, {
            method: 'POST'
        });
        if (!resp.ok) throw new Error(`Synthesis failed: HTTP ${resp.status}`);
        const synthesis = await resp.json();
        renderSynthesis(synthesis);
    } catch (e) {
        console.error('Synthesis error:', e);
        alert(`Error running synthesis: ${e.message}`);
    } finally {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.innerHTML = `<i data-lucide="cpu" style="width:15px;height:15px;"></i> Run Synthesis Engine`;
            if (window.lucide) window.lucide.createIcons();
        }
    }
}

function escapeHTML(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

export function renderSynthesis(synthesis) {
    const themesEl = document.getElementById('lr-themes-container');
    const contradictionsEl = document.getElementById('lr-contradictions-container');
    const gapsEl = document.getElementById('lr-gaps-container');

    if (themesEl) {
        themesEl.innerHTML = (synthesis.themes || []).map(t => `
            <div class="synthesis-item theme-item">
                <strong style="color:var(--accent-purple);">${escapeHTML(t.theme_name)}</strong>
                <p style="font-size:0.85rem;margin:0.25rem 0;">${escapeHTML(t.description)}</p>
                <div style="font-size:0.75rem;color:var(--text-muted);">Papers: ${(t.paper_ids || []).length}</div>
            </div>
        `).join('') || '<p>No themes generated yet.</p>';
    }

    if (contradictionsEl) {
        contradictionsEl.innerHTML = (synthesis.contradictions || []).map(c => `
            <div class="synthesis-item contradiction-item">
                <strong style="color:var(--accent-red);">${escapeHTML(c.topic || 'Contradiction / Moderator')}</strong>
                <div class="quote-compare" style="font-size:0.8rem;margin-top:0.35rem;">
                    <div><strong>Paper A (${escapeHTML(c.paper_a_id || 'Ref A')}):</strong> ${escapeHTML(c.claim_a || 'Finding A')}</div>
                    <div><strong>Paper B (${escapeHTML(c.paper_b_id || 'Ref B')}):</strong> ${escapeHTML(c.claim_b || 'Finding B')}</div>
                </div>
                <p style="font-size:0.8rem;color:var(--text-secondary);margin-top:0.25rem;"><em>Moderator: ${escapeHTML(c.moderator_explanation || 'Varying conditions')}</em></p>
            </div>
        `).join('') || '<p>No explicit contradictions detected.</p>';
    }

    if (gapsEl) {
        gapsEl.innerHTML = (synthesis.research_gaps || []).map(g => `
            <div class="synthesis-item gap-item">
                <strong style="color:var(--accent-orange);">${escapeHTML(g.gap_title || 'Research Gap')}</strong>
                <p style="font-size:0.85rem;margin:0.25rem 0;">${escapeHTML(g.description)}</p>
            </div>
        `).join('') || '<p>No research gaps identified yet.</p>';
    }
}
