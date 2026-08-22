/**
 * Literature Review - Review Document Compilation & Audit UI Module
 */

export function initCompilationUI(apiBase = '') {
    const compileBtn = document.getElementById('lr-compile-doc-btn');
    if (compileBtn) {
        compileBtn.addEventListener('click', () => compileReviewDocument(apiBase));
    }
}

export async function compileReviewDocument(apiBase = '') {
    const corpusId = window.getCurrentCorpusId ? window.getCurrentCorpusId() : null;
    if (!corpusId) return;

    const compileBtn = document.getElementById('lr-compile-doc-btn');
    if (compileBtn) {
        compileBtn.disabled = true;
        compileBtn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width:15px;height:15px;"></i> Compiling...`;
    }

    try {
        const resp = await fetch(`${apiBase}/api/literature-review/corpus/${corpusId}/generate`, {
            method: 'POST'
        });
        if (!resp.ok) throw new Error(`Compilation failed: HTTP ${resp.status}`);
        const review = await resp.json();
        renderReviewDocument(review);
    } catch (e) {
        console.error('Compilation error:', e);
        alert(`Error compiling review: ${e.message}`);
    } finally {
        if (compileBtn) {
            compileBtn.disabled = false;
            compileBtn.innerHTML = `<i data-lucide="file-plus" style="width:15px;height:15px;"></i> Compile Review Document`;
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

export function renderReviewDocument(review) {
    const badgeContainer = document.getElementById('lr-audit-badge-container');
    const proseContainer = document.getElementById('lr-doc-prose-container');

    if (badgeContainer) {
        const audit = review.consistency_audit || {};
        const isClean = audit.is_consistent !== false;
        const scoreVal = audit.score ?? 1.0;
        badgeContainer.className = `lr-audit-badge ${isClean ? 'clean' : 'flagged'}`;
        badgeContainer.innerHTML = `
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <i data-lucide="${isClean ? 'shield-check' : 'alert-circle'}" style="width:18px;height:18px;"></i>
                <strong>Cross-Section Consistency Audit: ${isClean ? 'Passed' : 'Issues Flagged'}</strong>
                <span>(Score: ${Math.round(scoreVal * 100)}%)</span>
            </div>
            <p style="font-size:0.8rem;margin:0.25rem 0 0 0;">${escapeHTML(audit.summary || 'Consistency audit completed.')}</p>
        `;
    }

    if (proseContainer) {
        let html = `<h2>${escapeHTML(review.title || 'Literature Review')}</h2>`;
        const sections = review.sections || {};
        Object.keys(sections).forEach(secTitle => {
            html += `<h3>${escapeHTML(secTitle)}</h3>`;
            html += `<p>${escapeHTML(sections[secTitle]).replace(/\n/g, '<br>')}</p>`;
        });
        proseContainer.innerHTML = html;
    }

    if (window.lucide) window.lucide.createIcons();
}
