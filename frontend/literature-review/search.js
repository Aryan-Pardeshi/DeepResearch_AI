/**
 * Literature Review - Search & Screening UI Module
 */

let currentCorpus = null;
let currentPapers = [];
let paperScreeningMap = {}; // paper_id -> "included" | "excluded"

export function initLiteratureSearch(apiBase = '') {
    const searchBtn = document.getElementById('lr-search-btn');
    const queryInput = document.getElementById('lr-query-input');
    const depthSelect = document.getElementById('lr-depth-select');

    if (searchBtn && queryInput) {
        searchBtn.addEventListener('click', () => performLiteratureSearch(apiBase));
        queryInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') performLiteratureSearch(apiBase);
        });
    }

    const extractBtn = document.getElementById('lr-extract-btn');
    if (extractBtn) {
        extractBtn.addEventListener('click', () => extractEvidence(apiBase));
    }

    const bridgeBtn = document.getElementById('lr-bridge-btn');
    if (bridgeBtn) {
        bridgeBtn.addEventListener('click', () => bridgeToResearchMode(apiBase));
    }
}

export async function performLiteratureSearch(apiBase = '') {
    const queryInput = document.getElementById('lr-query-input');
    const depthSelect = document.getElementById('lr-depth-select');
    const query = queryInput ? queryInput.value.trim() : '';
    const mode = depthSelect ? depthSelect.value : 'standard';

    if (!query) {
        alert('Please enter a research query.');
        return;
    }

    const searchBtn = document.getElementById('lr-search-btn');
    if (searchBtn) {
        searchBtn.disabled = true;
        searchBtn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width:16px;height:16px;"></i> Searching...`;
    }

    try {
        const resp = await fetch(`${apiBase}/api/literature-review/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, mode })
        });
        if (!resp.ok) throw new Error(`Search failed: HTTP ${resp.status}`);
        const data = await resp.json();

        // Initialize corpus in backend
        const corpusResp = await fetch(`${apiBase}/api/literature-review/corpus`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: data.query,
                domain_profile: data.domain_profile,
                papers: data.papers
            })
        });
        if (!corpusResp.ok) throw new Error(`Corpus init failed: HTTP ${corpusResp.status}`);
        currentCorpus = await corpusResp.json();
        currentPapers = data.papers;

        renderPaperCards(currentPapers, currentCorpus, apiBase);

        const workspaceContainer = document.getElementById('lr-workspace-container');
        if (workspaceContainer) workspaceContainer.style.display = 'block';

    } catch (err) {
        console.error('Literature search error:', err);
        alert(`Error searching literature: ${err.message}`);
    } finally {
        if (searchBtn) {
            searchBtn.disabled = false;
            searchBtn.innerHTML = `<i data-lucide="search" style="width:16px;height:16px;"></i> Search Literature`;
            if (window.lucide) window.lucide.createIcons();
        }
    }
}

export function renderPaperCards(papers, corpus) {
    const grid = document.getElementById('lr-papers-grid');
    if (!grid) return;
    grid.innerHTML = '';

    const includedCount = (corpus.included_paper_ids || []).length;
    const excludedCount = (corpus.excluded_paper_ids || []).length;

    papers.forEach(p => {
        const isIncluded = (corpus.included_paper_ids || []).includes(p.paper_id);
        const isExcluded = (corpus.excluded_paper_ids || []).includes(p.paper_id);

        const card = document.createElement('div');
        card.className = `lr-paper-card ${isExcluded ? 'excluded' : ''}`;

        // Paper Header
        const header = document.createElement('div');
        header.className = 'lr-paper-header';

        const providerTag = document.createElement('span');
        providerTag.className = `provider-tag badge-${(p.retrieval_source || 'openalex').toLowerCase()}`;
        providerTag.textContent = p.retrieval_source || 'openalex';
        header.appendChild(providerTag);

        const oaBadge = document.createElement('span');
        oaBadge.className = p.pdf_url ? 'oa-badge gold' : 'oa-badge closed';
        oaBadge.textContent = p.pdf_url ? 'Open Access' : 'Subscription';
        header.appendChild(oaBadge);

        if (p.authors && p.authors.some(a => (typeof a === 'object' && a.orcid) || (typeof a === 'string' && a.includes('orcid')))) {
            const orcidBadge = document.createElement('span');
            orcidBadge.className = 'orcid-badge';
            orcidBadge.title = 'ORCID Verified';
            orcidBadge.textContent = 'ORCID';
            header.appendChild(orcidBadge);
        }

        const yearSpan = document.createElement('span');
        yearSpan.className = 'lr-paper-year';
        yearSpan.textContent = p.year || 'n.d.';
        header.appendChild(yearSpan);

        card.appendChild(header);

        // Title
        const titleEl = document.createElement('h3');
        titleEl.className = 'lr-paper-title';
        titleEl.textContent = p.title || 'Untitled Paper';
        card.appendChild(titleEl);

        // Authors
        const authorsEl = document.createElement('div');
        authorsEl.className = 'lr-paper-authors';
        const authorsList = (p.authors || []).map(a => typeof a === 'string' ? a : (a.name || 'Anon')).join(', ');
        authorsEl.textContent = authorsList || 'Unknown Authors';
        card.appendChild(authorsEl);

        // Venue & DOI
        const venueEl = document.createElement('div');
        venueEl.className = 'lr-paper-venue';
        venueEl.textContent = `${p.venue || 'Academic Output'} ${p.doi ? `• DOI: ${p.doi}` : ''}`;
        card.appendChild(venueEl);

        // Abstract
        const abstractEl = document.createElement('p');
        abstractEl.className = 'lr-paper-abstract';
        abstractEl.textContent = (p.abstract || 'No abstract available.').substring(0, 300) + '...';
        card.appendChild(abstractEl);

        // Actions
        const actionsEl = document.createElement('div');
        actionsEl.className = 'lr-paper-actions';

        const includeBtn = document.createElement('button');
        includeBtn.className = `btn-secondary btn-sm btn-include ${isIncluded ? 'active' : ''}`;
        includeBtn.textContent = 'Include';
        includeBtn.addEventListener('click', () => window.screenPaperAction(corpus.corpus_id, p.paper_id, 'included'));
        actionsEl.appendChild(includeBtn);

        const excludeBtn = document.createElement('button');
        excludeBtn.className = `btn-secondary btn-sm btn-exclude ${isExcluded ? 'active' : ''}`;
        excludeBtn.textContent = 'Exclude';
        excludeBtn.addEventListener('click', () => window.screenPaperAction(corpus.corpus_id, p.paper_id, 'excluded'));
        actionsEl.appendChild(excludeBtn);

        if (p.source_url && /^https?:\/\//i.test(p.source_url)) {
            const linkBtn = document.createElement('a');
            linkBtn.href = p.source_url;
            linkBtn.target = '_blank';
            linkBtn.rel = 'noopener noreferrer';
            linkBtn.className = 'btn-secondary btn-sm';
            linkBtn.style.textDecoration = 'none';
            linkBtn.textContent = 'Link';
            actionsEl.appendChild(linkBtn);
        }

        card.appendChild(actionsEl);
        grid.appendChild(card);
    });

    // Update stats
    document.getElementById('lr-stat-found').textContent = papers.length;
    document.getElementById('lr-stat-included').textContent = includedCount;
    document.getElementById('lr-stat-excluded').textContent = excludedCount;
    document.getElementById('lr-count-included').textContent = includedCount;
    document.getElementById('lr-count-total').textContent = papers.length;

    if (window.lucide) window.lucide.createIcons();
}

window.screenPaperAction = async function (corpusId, paperId, status) {
    let exclusionReason = null;
    if (status === 'excluded') {
        exclusionReason = prompt('Reason for exclusion (optional):', 'Low relevance to research topic');
    }
    try {
        const resp = await fetch(`${storedApiBase}/api/literature-review/corpus/${corpusId}/screen`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId, status, exclusion_reason: exclusionReason })
        });
        if (resp.ok) {
            currentCorpus = await resp.json();
            renderPaperCards(currentPapers, currentCorpus);
        }
    } catch (e) {
        console.error('Screening error:', e);
    }
};

export async function extractEvidence(apiBase = '') {
    if (!currentCorpus) return;
    const extractBtn = document.getElementById('lr-extract-btn');
    if (extractBtn) {
        extractBtn.disabled = true;
        extractBtn.innerHTML = `<i data-lucide="loader-2" class="spin" style="width:14px;height:14px;"></i> Extracting...`;
    }
    try {
        const resp = await fetch(`${apiBase}/api/literature-review/corpus/${currentCorpus.corpus_id}/extract`, {
            method: 'POST'
        });
        if (!resp.ok) throw new Error(`Extraction failed: HTTP ${resp.status}`);
        const data = await resp.json();
        alert(`Extracted ${data.evidence_records.length} structured evidence records!`);
    } catch (e) {
        alert(`Error extracting evidence: ${e.message}`);
    } finally {
        if (extractBtn) {
            extractBtn.disabled = false;
            extractBtn.innerHTML = `<i data-lucide="sparkles" style="width:14px;height:14px;"></i> Extract Evidence`;
            if (window.lucide) window.lucide.createIcons();
        }
    }
}

export async function bridgeToResearchMode(apiBase = '') {
    if (!currentCorpus) return;
    try {
        const resp = await fetch(`${apiBase}/api/literature-review/corpus/${currentCorpus.corpus_id}/bridge-to-research`, {
            method: 'POST'
        });
        if (!resp.ok) throw new Error(`Bridge failed: HTTP ${resp.status}`);
        const rmState = await resp.json();

        // Persist bridged corpus state globally so handleRMStart supplies it to Research Mode start contract
        window.bridgedCorpusState = rmState;
        window.bridgedCorpusId = currentCorpus.corpus_id;

        // Switch UI to Research Mode tab and pre-fill problem statement
        const rmTab = document.getElementById('tab-researchmode');
        if (rmTab) rmTab.click();

        const psInput = document.getElementById('rm-ps-input');
        if (psInput) {
            psInput.value = rmState.problem_statement;
            alert('Successfully bridged Literature Review corpus into Research Mode!');
        }
    } catch (e) {
        alert(`Error bridging to Research Mode: ${e.message}`);
    }
}
