/**
 * Literature Review Mode Orchestrator
 */

import { initLiteratureSearch } from '../literature-review/search.js';
import { initMatrixUI } from '../literature-review/matrix.js';
import { initAskCorpusUI } from '../literature-review/ask.js';
import { initSynthesisUI } from '../literature-review/synthesis.js';
import { initCompilationUI } from '../literature-review/compilation.js';

let activeCorpusId = null;

export function getActiveCorpusId() {
    return activeCorpusId;
}

export function setActiveCorpusId(id) {
    activeCorpusId = id;
}

window.getActiveCorpusId = getActiveCorpusId;
window.setActiveCorpusId = setActiveCorpusId;
window.getCurrentCorpusId = getActiveCorpusId;

export function setupLiteratureReviewMode(apiBase = '') {
    initLiteratureSearch(apiBase);
    initMatrixUI(apiBase);
    initAskCorpusUI(apiBase);
    initSynthesisUI(apiBase);
    initCompilationUI(apiBase);

    // Workspace tab switching inside Literature Review workspace
    const tabs = document.querySelectorAll('.lr-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const targetTab = tab.getAttribute('data-lr-tab');
            const contents = document.querySelectorAll('.lr-tab-content');
            contents.forEach(c => c.classList.remove('active'));

            const activeContent = document.getElementById(`lr-tab-${targetTab}`);
            if (activeContent) activeContent.classList.add('active');
        });
    });
}
