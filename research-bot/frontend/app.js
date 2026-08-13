// Inject cursor blinking keyframes dynamically
const cursorStyle = document.createElement('style');
cursorStyle.innerHTML = `
.streaming-cursor {
    color: var(--accent-purple);
    font-weight: bold;
    display: inline-block;
    margin-left: 2px;
    animation: cursor-blink 0.8s infinite steps(2);
}
@keyframes cursor-blink {
    0%, 100% { opacity: 0; }
    50% { opacity: 1; }
}
`;
document.head.appendChild(cursorStyle);

// Configuration
// The backend serves this page, so the API lives on the same origin. Opening
// index.html straight off disk or from a dev server on another port (e.g. 5500)
// falls back to the default backend port (http://localhost:8000).
const API_BASE_URL = window.API_BASE_URL || (
    (window.location.protocol === 'file:' || (window.location.port && window.location.port !== '8000'))
        ? 'http://localhost:8000'
        : window.location.origin
);
let activeResearchController = null;
let activeRMController = null;

// Application State
const state = {
    mode: 'deepsearch', // 'deepsearch' | 'researchmode'
    threadId: null,
    status: 'idle', 
    query: '',
    searchTopic: ['all'],
    ps: '',
    plan: [],
    workers: {},
    finalAnswer: '',
    citations: [],
    error: null,
    
    // Research Mode State
    rm: {
        threadId: null,
        status: 'idle',
        hitlCheckpoint: null,
        problemStatement: '',
        researchObjectives: [],
        researchQuestions: [],
        keywords: [],
        rawPapersCount: 0,
        screenedPapersCount: 0,
        literatureReview: '',
        researchGap: '',
        conceptualFramework: '',
        hypotheses: [],
        researchDesign: '',
        dataCollectionPlan: '',
        dataAnalysisPlan: '',
        results: '',
        discussion: '',
        implications: '',
        limitations: '',
        conclusion: '',
        futureScope: [],
        references: [],
        appendices: '',
        introduction: '',
        abstract: '',
        title: '',
        activeStage: 'scope_definition',
        completedStages: [],
        screenedPapers: []
    }
};

// Research Mode Pipeline Stage Metadata (agent research flow order)
const RM_STAGES = [
    { id: 'scope_definition', name: '1-3. Scope Definition', role: 'scoper' },
    { id: 'keyword_extractor', name: 'Keyword Extraction', role: 'extractor' },
    { id: 'checkpoint_1', name: 'HITL Checkpoint 1', hitl: true },
    { id: 'paper_fetcher', name: 'Corpus Retrieval', role: 'fetcher' },
    { id: 'paper_screener', name: 'Corpus Screening', role: 'screener' },
    { id: 'literature_review', name: '4. Literature Review', role: 'synthesizer' },
    { id: 'gap_analysis', name: '5. Research Gap', role: 'analyst' },
    { id: 'framework', name: '6. Conceptual Framework', role: 'architect' },
    { id: 'checkpoint_2', name: 'HITL Checkpoint 2', hitl: true },
    { id: 'hypotheses', name: '7. Hypotheses', role: 'formulator' },
    { id: 'checkpoint_3', name: 'HITL Checkpoint 3', hitl: true },
    { id: 'research_design', name: '8. Research Design', role: 'methodologist' },
    { id: 'data_collection', name: '9. Data Collection', role: 'methodologist' },
    { id: 'data_analysis', name: '10. Data Analysis', role: 'methodologist' },
    { id: 'checkpoint_4', name: 'HITL Checkpoint 4', hitl: true },
    { id: 'results', name: '11. Results', role: 'synthesizer' },
    { id: 'discussion', name: '12. Discussion + Implications', role: 'interpreter' },
    { id: 'limitations', name: '13. Limitations', role: 'critic' },
    { id: 'conclusion', name: '14. Conclusion', role: 'summarizer' },
    { id: 'future_scope', name: '15. Future Scope', role: 'visionary' },
    { id: 'references', name: '16. References', role: 'indexer' },
    { id: 'appendices', name: '17. Appendices', role: 'archivist' },
    { id: 'introduction', name: '18. Introduction', role: 'framer' },
    { id: 'abstract', name: '19. Abstract', role: 'summarizer' },
    { id: 'title', name: '20. Title', role: 'finalizer' }
];

// Graph nodes that run without their own tile in the tracker grid. Every node in
// research_mode_builder.py must appear either in RM_STAGES or here, otherwise the
// tracker cannot resolve the node and falls back to a bare "Pipeline Running".
const RM_HIDDEN_STAGES = {
    scope_reviser: { label: 'Revising Scope', anchor: 'checkpoint_1' },
    fulltext_fetcher: { label: 'Fetching Full Text', anchor: 'paper_screener' },
    citation_verifier: { label: 'Verifying Citations', anchor: 'literature_review' },
    figures: { label: 'Generating Figures', anchor: 'references' }
};

// Maps the snake_case state payload from the backend onto the camelCase UI state
const RM_STATE_KEY_MAP = {
    problem_statement: 'problemStatement',
    research_objectives: 'researchObjectives',
    research_questions: 'researchQuestions',
    keywords: 'keywords',
    raw_papers_count: 'rawPapersCount',
    screened_papers_count: 'screenedPapersCount',
    literature_review: 'literatureReview',
    research_gap: 'researchGap',
    conceptual_framework: 'conceptualFramework',
    hypotheses: 'hypotheses',
    research_design: 'researchDesign',
    data_collection_plan: 'dataCollectionPlan',
    data_analysis_plan: 'dataAnalysisPlan',
    results: 'results',
    discussion: 'discussion',
    implications: 'implications',
    limitations: 'limitations',
    conclusion: 'conclusion',
    future_scope: 'futureScope',
    references: 'references',
    appendices: 'appendices',
    introduction: 'introduction',
    abstract: 'abstract',
    title: 'title'
};

// Keys copied through under their own name because the UI reads them directly.
const RM_PASSTHROUGH_KEYS = ['corpus_stats', 'status', 'hitl_checkpoint'];

// Single mapper for every snake_case payload the backend sends (SSE node_update,
// SSE checkpoint/completed state, and the /research-mode/result rehydrate call).
// Unknown keys are ignored on purpose: the raw graph state carries large arrays
// (raw_papers, screened_papers, messages) that used to be copied verbatim into
// state.rm and then straight into localStorage, blowing the storage quota.
function applyRMStatePayload(payload) {
    if (!payload || typeof payload !== 'object') return;
    Object.entries(RM_STATE_KEY_MAP).forEach(([snake, camel]) => {
        const value = payload[snake];
        if (value !== undefined && value !== null && value !== '') {
            state.rm[camel] = value;
        }
    });
    RM_PASSTHROUGH_KEYS.forEach(key => {
        const value = payload[key];
        if (value !== undefined && value !== null && value !== '') {
            state.rm[key] = value;
        }
    });
    // paper_fetcher sends raw_papers before screening; paper_screener and
    // fulltext_fetcher both send screened_papers (the latter adds
    // content_excerpt). Whichever arrives most recently wins — screened_papers
    // is always the more complete list once it exists.
    if (Array.isArray(payload.screened_papers)) {
        state.rm.screenedPapers = payload.screened_papers;
    } else if (Array.isArray(payload.raw_papers) && state.rm.screenedPapers.length === 0) {
        state.rm.screenedPapers = payload.raw_papers;
    }
    // The backend sends counts under different names depending on the endpoint:
    // SSE sends raw_papers_count, the rehydrate endpoint sends the arrays.
    if (Array.isArray(payload.raw_papers)) state.rm.rawPapersCount = payload.raw_papers.length;
    if (Array.isArray(payload.screened_papers)) state.rm.screenedPapersCount = payload.screened_papers.length;
}

// Papers arrive from the backend already relevance-ranked in practice, but
// don't rely on that — sort explicitly so the checkpoint strip and library
// panel always show the strongest matches first regardless of arrival order.
function getScreenedPapers() {
    return [...state.rm.screenedPapers].sort(
        (a, b) => (b.relevance_score || 0) - (a.relevance_score || 0)
    );
}

// Escapes model- and user-authored text before it goes into an innerHTML string.
// Titles, objectives and hypotheses regularly contain <, > and & (e.g. "p < 0.05"),
// which silently swallowed the rest of the panel before this existed.
function escapeHtml(value) {
    if (value === undefined || value === null) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// marked and lucide come from a CDN. If that request is blocked the page must
// still work instead of throwing on every render.
function renderMarkdown(md) {
    if (window.marked && typeof window.marked.parse === 'function') {
        return window.marked.parse(md || '');
    }
    return `<pre class="markdown-fallback">${escapeHtml(md || '')}</pre>`;
}

// Same as renderMarkdown but HTML-escapes first, so model text that contains
// `<`, `>` or `&` (e.g. "p < 0.05") can't inject markup, while **bold**,
// lists and other markdown still render. When marked wraps the result in a
// single <p>, the tags are dropped so one-line fields (e.g. a checkpoint
// summary) sit flush without picking up block margins.
function renderMarkdownSafe(md) {
    const safe = escapeHtml(md || '');
    if (window.marked && typeof window.marked.parse === 'function') {
        const html = window.marked.parse(safe).trim();
        const single = html.match(/^<p>([\s\S]*)<\/p>$/);
        return single ? single[1] : html;
    }
    return `<pre class="markdown-fallback">${safe}</pre>`;
}

const SOURCE_BADGE_MAP = {
    openalex: { src: 'assets/openalex.png', label: 'OpenAlex', cls: 'index-mark-openalex' },
    semantic_scholar: { src: 'assets/semantic-scholar.png', label: 'Semantic Scholar', cls: '' },
    arxiv: { src: 'assets/arxiv.png', label: 'arXiv', cls: '' }
};

// Reuses the same brand marks the landing page already downloaded (see
// assets/*.png) so a paper's origin index is visually recognizable instead
// of a plain text label like "openalex".
function sourceBadgeHtml(source) {
    const entry = SOURCE_BADGE_MAP[source];
    if (!entry) return '';
    return `<img class="source-badge ${entry.cls}" src="${entry.src}" alt="${entry.label}" title="${entry.label}" width="14" height="14" loading="lazy">`;
}

let truncatableIdCounter = 0;

// Checkpoint 2 was showing researchGap/conceptualFramework in full — observed
// at ~2500 words on screen in one live test run. literatureReview already had
// a hard 400-char cut with no way to read past it. This gives every long
// snippet the same collapsed-by-default treatment with an actual way out.
function renderTruncatable(text, opts = {}) {
    const charLimit = opts.charLimit || 400;
    const safeText = text || '';
    const id = `trunc-${++truncatableIdCounter}`;
    const rendered = renderMarkdownSafe(safeText);

    if (safeText.length <= charLimit) {
        return `<div class="problem-statement-text">${rendered}</div>`;
    }

    return `
        <div class="problem-statement-text truncatable" id="${id}">${rendered}</div>
        <button type="button" class="truncate-toggle" data-truncate-target="${id}">Show full text</button>
    `;
}

function refreshIcons() {
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
    }
}

// Activity & Timer Monitors
const researchTimer = {
    startTime: null,
    timerId: null,
    elapsedSeconds: 0,
    isPaused: false,
    start() {
        this.stop();
        this.startTime = Date.now() - (this.elapsedSeconds * 1000);
        this.isPaused = false;
        this.updateDisplay();
        this.timerId = setInterval(() => {
            if (!this.isPaused) {
                this.elapsedSeconds = Math.floor((Date.now() - this.startTime) / 1000);
                this.updateDisplay();
            }
        }, 1000);
    },
    stop() {
        if (this.timerId) { clearInterval(this.timerId); this.timerId = null; }
    },
    reset() {
        this.stop(); this.startTime = null; this.elapsedSeconds = 0; this.updateDisplay();
    },
    updateDisplay() {
        const timerEl = document.getElementById('research-timer');
        if (timerEl) {
            const minutes = Math.floor(this.elapsedSeconds / 60);
            const seconds = this.elapsedSeconds % 60;
            timerEl.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }
    }
};

// DOM Cache
let dom = {};

document.addEventListener('DOMContentLoaded', () => {
    cacheDomElements();
    initTheme();
    setupEventListeners();
    checkBackendHealth();
    checkConfigGate();
    renderRMPipelineTracker();
    restoreRMSessionOnLoad();
    rmPlaceholderCycle = initCyclingPlaceholder(dom.rmPsInput, RM_PLACEHOLDER_EXAMPLES);
    dsPlaceholderCycle = initCyclingPlaceholder(dom.queryInput, DS_PLACEHOLDER_EXAMPLES);
    updateNewRunVisibility();
    refreshIcons();
});

// A single unhandled render error used to leave the page frozen with no clue why.
window.addEventListener('error', (e) => {
    console.error('Unhandled error:', e.error || e.message);
});
window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
});

let rmPlaceholderCycle = null;
let dsPlaceholderCycle = null;

// Example prompts the Core Problem Statement box types out when idle and empty.
const RM_PLACEHOLDER_EXAMPLES = [
    'Efficacy of cognitive behavioral therapy interventions for healthcare worker burnout...',
    'Impact of generative AI code assistants on software developer productivity...',
    'Macroeconomic predictors of digital health platform adoption in rural systems...',
    'Comparative analysis of transformer architectures for financial time-series forecasting...'
];

// Same idea for the DeepSearch query box.
const DS_PLACEHOLDER_EXAMPLES = [
    'What would you like to research today?',
    'Latest developments in solid-state EV battery chemistry...',
    'Competitive landscape for open-weight LLM inference providers...',
    'Regulatory shifts affecting cross-border crypto payments in 2026...'
];

// Types each example into the placeholder, pauses, deletes it, moves to the next.
// Stops while the field has focus or real content so it never fights the user.
function initCyclingPlaceholder(el, examples, opts = {}) {
    if (!el || !examples.length) return;
    const typeSpeed = opts.typeSpeed || 32;
    const deleteSpeed = opts.deleteSpeed || 16;
    const holdMs = opts.holdMs || 1800;
    const gapMs = opts.gapMs || 400;

    let exampleIndex = 0;
    let timerId = null;
    let running = false;

    function step(charIndex, deleting) {
        const text = examples[exampleIndex];
        el.placeholder = text.slice(0, charIndex);

        if (!deleting && charIndex < text.length) {
            timerId = setTimeout(() => step(charIndex + 1, false), typeSpeed);
        } else if (!deleting) {
            timerId = setTimeout(() => step(charIndex, true), holdMs);
        } else if (deleting && charIndex > 0) {
            timerId = setTimeout(() => step(charIndex - 1, true), deleteSpeed);
        } else {
            exampleIndex = (exampleIndex + 1) % examples.length;
            timerId = setTimeout(() => step(0, false), gapMs);
        }
    }

    function start() {
        if (running || el.value) return;
        running = true;
        step(0, false);
    }

    function stop() {
        running = false;
        if (timerId) { clearTimeout(timerId); timerId = null; }
    }

    el.addEventListener('focus', stop);
    el.addEventListener('input', () => { if (el.value) stop(); });
    el.addEventListener('blur', () => { if (!el.value) start(); });

    start();
    return { start, stop };
}

function cacheDomElements() {
    dom = {
        // App header & settings
        themeToggleBtn: document.getElementById('theme-toggle-btn'),
        newResearchBtn: document.getElementById('new-research-btn'),
        backendOfflineBanner: document.getElementById('backend-offline-banner'),
        
        // Mode Tabs
        tabDeepSearch: document.getElementById('tab-deepsearch'),
        tabResearchMode: document.getElementById('tab-researchmode'),

        // Setup Gate Modal
        setupGateModal: document.getElementById('setup-gate-modal'),
        gateLlmBaseUrl: document.getElementById('gate-llm-base-url'),
        gateLlmApiKey: document.getElementById('gate-llm-api-key'),
        gateModelPlanner: document.getElementById('gate-llm-model-planner'),
        gateModelResearcher: document.getElementById('gate-llm-model-researcher'),
        gateModelAggregator: document.getElementById('gate-llm-model-aggregator'),
        gateTavilyKey: document.getElementById('gate-tavily-key'),
        gateOpenalexEmail: document.getElementById('gate-openalex-email'),
        gateSubmitBtn: document.getElementById('gate-submit-btn'),
        gateSaveStatus: document.getElementById('gate-save-status'),

        // Panels
        landingPanel: document.getElementById('landing-panel'),
        approvalPanel: document.getElementById('approval-panel'),
        workspacePanel: document.getElementById('workspace-panel'),
        rmInputPanel: document.getElementById('rm-input-panel'),
        rmWorkspacePanel: document.getElementById('rm-workspace-panel'),

        // DeepSearch Inputs & Elements
        queryInput: document.getElementById('query-input'),
        planResearchBtn: document.getElementById('plan-research-btn'),
        filterChips: document.getElementById('filter-chips'),
        approvalQueryDisplay: document.getElementById('approval-query-display'),
        approvalPsText: document.getElementById('approval-ps-text'),
        approvalSubtasksContainer: document.getElementById('approval-subtasks-container'),
        feedbackInput: document.getElementById('feedback-input'),
        submitFeedbackBtn: document.getElementById('submit-feedback-btn'),
        approvePlanBtn: document.getElementById('approve-plan-btn'),
        approvalNewResearchBtn: document.getElementById('approval-new-research-btn'),
        workersListContainer: document.getElementById('workers-list-container'),
        reportOutput: document.getElementById('report-output'),
        reportStreamingIndicator: document.getElementById('report-streaming-indicator'),
        workspaceProgressBar: document.getElementById('workspace-progress-bar'),
        workspaceSourcesSection: document.getElementById('workspace-sources-section'),
        workspaceSourcesContainer: document.getElementById('workspace-sources-container'),
        copyMdBtn: document.getElementById('copy-md-btn'),
        downloadMdBtn: document.getElementById('download-md-btn'),
        workspaceNewResearchBtn: document.getElementById('workspace-new-research-btn'),

        // Research Mode Elements
        rmPsInput: document.getElementById('rm-ps-input'),
        rmObjsInput: document.getElementById('rm-objs-input'),
        rmRqsInput: document.getElementById('rm-rqs-input'),
        rmModelPlanner: document.getElementById('rm-model-planner'),
        rmModelResearcher: document.getElementById('rm-model-researcher'),
        rmModelAggregator: document.getElementById('rm-model-aggregator'),
        rmStartBtn: document.getElementById('rm-start-btn'),
        rmPipelineStepsGrid: document.getElementById('rm-pipeline-steps-grid'),
        rmPipelineStatusTag: document.getElementById('rm-pipeline-status-tag'),
        rmHitlPanel: document.getElementById('rm-hitl-panel'),
        rmHitlTitle: document.getElementById('rm-hitl-title'),
        rmHitlBadge: document.getElementById('rm-hitl-checkpoint-badge'),
        rmHitlBody: document.getElementById('rm-hitl-body'),
        rmHitlFeedbackInput: document.getElementById('rm-hitl-feedback-input'),
        rmHitlReviseBtn: document.getElementById('rm-hitl-revise-btn'),
        rmHitlApproveBtn: document.getElementById('rm-hitl-approve-btn'),
        rmPaperTitle: document.getElementById('rm-paper-title'),
        rmPaperOutput: document.getElementById('rm-paper-output'),
        rmCopyPaperBtn: document.getElementById('rm-copy-paper-btn'),
        rmExportPdfBtn: document.getElementById('rm-export-pdf-btn'),
        rmExportDropdown: document.getElementById('rm-export-dropdown'),

        statRetrieved: document.getElementById('stat-retrieved'),
        statDedup: document.getElementById('stat-dedup'),
        statScreened: document.getElementById('stat-screened'),
        statIncluded: document.getElementById('stat-included'),
        statFulltext: document.getElementById('stat-fulltext'),
        rmCorpusStatsBar: document.getElementById('rm-corpus-stats-bar'),
        rmLogDrawer: document.getElementById('rm-log-drawer'),
        rmLogBody: document.getElementById('rm-log-body'),
        rmLogCount: document.getElementById('rm-log-count'),
        rmEvidenceCard: document.getElementById('rm-evidence-card'),
        rmEvidenceMatrixView: document.getElementById('rm-evidence-matrix-view'),
        paperDetailModal: document.getElementById('paper-detail-modal'),
        modalPaperTitle: document.getElementById('modal-paper-title'),
        modalPaperBody: document.getElementById('modal-paper-body'),
        modalCloseBtn: document.getElementById('modal-close-btn'),

        toastContainer: document.getElementById('toast-container')

    };
}

// System Environment Setup Gate Check
async function checkConfigGate() {
    try {
        const res = await fetch(`${API_BASE_URL}/config/status`);
        if (!res.ok) return;
        const data = await res.json();
        
        if (dom.rmModelPlanner && data.llm_model_planner) dom.rmModelPlanner.placeholder = data.llm_model_planner;
        if (dom.rmModelResearcher && data.llm_model_researcher) dom.rmModelResearcher.placeholder = data.llm_model_researcher;
        if (dom.rmModelAggregator && data.llm_model_aggregator) dom.rmModelAggregator.placeholder = data.llm_model_aggregator;

        if (!data.ok || (data.missing_required && data.missing_required.length > 0)) {
            // The gate writes to the server's own .env, so it only makes sense where
            // that is allowed. On a deployment with the config API locked it could
            // neither save nor honour its "stored locally" promise, so it stays hidden
            // and the operator is told to set the environment variables instead.
            if (!data.config_writable) {
                showToast(
                    `Server is missing ${(data.missing_required || []).join(', ')}. ` +
                    `Set them as environment variables on the host.`,
                    'error'
                );
                return;
            }

            // Populate form defaults if present
            if (dom.gateLlmBaseUrl) dom.gateLlmBaseUrl.value = data.llm_base_url || 'https://api.deepseek.com';
            if (dom.gateModelPlanner) dom.gateModelPlanner.value = data.llm_model_planner || 'deepseek-chat';
            if (dom.gateModelResearcher) dom.gateModelResearcher.value = data.llm_model_researcher || 'deepseek-chat';
            if (dom.gateModelAggregator) dom.gateModelAggregator.value = data.llm_model_aggregator || 'deepseek-chat';
            if (dom.gateOpenalexEmail) dom.gateOpenalexEmail.value = data.openalex_email || '';
            
            dom.setupGateModal.style.display = 'flex';
        }
    } catch (e) {
        console.warn('Config check failed:', e);
    }
}

// Remembers the panel each mode was last on. Switching tabs used to hard-reset
// to the landing/input panel, so flipping to the other mode and back during a
// live run threw away the workspace view and looked like the run had vanished.
const lastPanelByMode = { deepsearch: null, researchmode: null };

function switchMode(newMode) {
    const previous = state.mode;
    const currentPanel = document.querySelector('.panel.active');
    if (currentPanel && previous) lastPanelByMode[previous] = currentPanel;

    state.mode = newMode;
    if (newMode === 'deepsearch') {
        dom.tabDeepSearch.classList.add('active');
        dom.tabResearchMode.classList.remove('active');
        switchPanel(lastPanelByMode.deepsearch || dom.landingPanel);
    } else {
        dom.tabResearchMode.classList.add('active');
        dom.tabDeepSearch.classList.remove('active');
        switchPanel(lastPanelByMode.researchmode || dom.rmInputPanel);
    }
    updateNewRunVisibility();
}

// Setup Event Listeners
function setupEventListeners() {
    // Mode tabs
    dom.tabDeepSearch?.addEventListener('click', () => switchMode('deepsearch'));
    dom.tabResearchMode?.addEventListener('click', () => switchMode('researchmode'));

    // Theme toggle
    dom.themeToggleBtn?.addEventListener('click', toggleTheme);

    // Collapsible tracker toggle label update
    const trackerDetails = document.getElementById('rm-tracker-details');
    const trackerToggleLbl = document.getElementById('tracker-toggle-lbl');
    trackerDetails?.addEventListener('toggle', () => {
        if (trackerToggleLbl) {
            trackerToggleLbl.textContent = trackerDetails.open ? 'Collapse' : 'Expand';
        }
    });

    // Settings Modal

    // Gate Modal Submit
    dom.gateSubmitBtn?.addEventListener('click', submitSetupGate);

    // DeepSearch Filters & Actions
    dom.filterChips?.addEventListener('click', (e) => {
        if (e.target.classList.contains('chip')) {
            document.querySelectorAll('#filter-chips .chip').forEach(c => c.classList.remove('active'));
            e.target.classList.add('active');
            state.searchTopic = [e.target.dataset.topic];
        }
    });

    // Delegated so it works for truncatable blocks rendered at any point
    // after this listener is attached (checkpoint panels, library panel).
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.truncate-toggle');
        if (!btn) return;
        const target = document.getElementById(btn.dataset.truncateTarget);
        if (!target) return;
        const expanded = target.classList.toggle('expanded');
        btn.textContent = expanded ? 'Show less' : 'Show full text';
    });

    dom.planResearchBtn?.addEventListener('click', handlePlanResearch);
    dom.feedbackInput?.addEventListener('input', () => {
        const val = dom.feedbackInput.value.trim();
        dom.submitFeedbackBtn.style.display = val ? 'flex' : 'none';
        dom.approvePlanBtn.style.display = val ? 'none' : 'flex';
    });

    dom.submitFeedbackBtn?.addEventListener('click', handleRevision);
    dom.approvePlanBtn?.addEventListener('click', submitPlanApproval);
    dom.approvalNewResearchBtn?.addEventListener('click', resetToLanding);
    dom.workspaceNewResearchBtn?.addEventListener('click', resetToLanding);
    dom.newResearchBtn?.addEventListener('click', resetToLanding);

    dom.copyMdBtn?.addEventListener('click', () => copyToClipboard(state.finalAnswer, dom.copyMdBtn));
    dom.downloadMdBtn?.addEventListener('click', downloadMarkdownReport);

    // Research Mode Actions
    dom.rmStartBtn?.addEventListener('click', handleRMStart);
    dom.rmHitlReviseBtn?.addEventListener('click', () => {
        const feedback = dom.rmHitlFeedbackInput.value.trim();
        if (!feedback) {
            showToast('Type what you want changed, then request revisions.', 'warning');
            return;
        }
        handleRMApprove(feedback);
    });
    dom.rmHitlApproveBtn?.addEventListener('click', () => handleRMApprove('approve'));
    dom.rmCopyPaperBtn?.addEventListener('click', () => copyToClipboard(getPaperMarkdown(), dom.rmCopyPaperBtn));

    // Paper inspector modal. This was wired at module scope, before
    // cacheDomElements() had run, so dom.modalCloseBtn was always undefined and
    // the modal could never be dismissed once opened.
    dom.modalCloseBtn?.addEventListener('click', closePaperInspector);
    dom.paperDetailModal?.addEventListener('click', (e) => {
        if (e.target === dom.paperDetailModal) closePaperInspector();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        if (dom.paperDetailModal && dom.paperDetailModal.style.display !== 'none') {
            closePaperInspector();
        }
    });
}

function closePaperInspector() {
    if (dom.paperDetailModal) dom.paperDetailModal.style.display = 'none';
}

// Admin token for the config API. The backend rejects config writes without it
// unless the deployment explicitly opted into open access for local use.
function getConfigToken() {
    return window.CONFIG_API_TOKEN || localStorage.getItem('config_api_token') || '';
}

function configHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const token = getConfigToken();
    if (token) headers['X-Config-Token'] = token;
    return headers;
}

async function promptForConfigToken() {
    const token = window.prompt('This deployment requires an admin token to change configuration. Enter X-Config-Token:');
    if (token && token.trim()) {
        localStorage.setItem('config_api_token', token.trim());
        return true;
    }
    return false;
}

// Setup Gate Submit
async function submitSetupGate() {
    const payload = {
        LLM_BASE_URL: dom.gateLlmBaseUrl.value.trim(),
        LLM_API_KEY: dom.gateLlmApiKey.value.trim(),
        LLM_MODEL_PLANNER: dom.gateModelPlanner.value.trim(),
        LLM_MODEL_RESEARCHER: dom.gateModelResearcher.value.trim(),
        LLM_MODEL_AGGREGATOR: dom.gateModelAggregator.value.trim(),
        TAVILY_API_KEY: dom.gateTavilyKey.value.trim(),
        OPENALEX_EMAIL: dom.gateOpenalexEmail.value.trim()
    };

    dom.gateSaveStatus.textContent = 'Saving configuration locally...';
    try {
        let res = await fetch(`${API_BASE_URL}/config/setup`, {
            method: 'POST',
            headers: configHeaders(),
            body: JSON.stringify(payload)
        });
        if (res.status === 401 && await promptForConfigToken()) {
            res = await fetch(`${API_BASE_URL}/config/setup`, {
                method: 'POST',
                headers: configHeaders(),
                body: JSON.stringify(payload)
            });
        }
        const data = await res.json();
        if (res.status === 401 || res.status === 403) {
            localStorage.removeItem('config_api_token');
            dom.gateSaveStatus.textContent = data.detail || 'Configuration API is locked on this deployment.';
            return;
        }
        if (data.ok) {
            dom.gateSaveStatus.textContent = 'Configuration saved!';
            setTimeout(() => {
                dom.setupGateModal.style.display = 'none';
                showToast('Environment successfully configured!', 'success');
            }, 800);
        } else {
            dom.gateSaveStatus.textContent = data.detail || 'Failed to save.';
        }
    } catch (e) {
        dom.gateSaveStatus.textContent = 'Error connecting to backend.';
    }
}


// Theme handling
function initTheme() {
    const theme = localStorage.getItem('deepresearch_theme') || 'dark';
    if (theme === 'light') {
        document.documentElement.classList.add('light-mode');
    } else {
        document.documentElement.classList.remove('light-mode');
    }
    updateThemeIcon();
}

function toggleTheme() {
    document.documentElement.classList.toggle('light-mode');
    const isLight = document.documentElement.classList.contains('light-mode');
    localStorage.setItem('deepresearch_theme', isLight ? 'light' : 'dark');
    updateThemeIcon();
}

function updateThemeIcon() {
    const isLight = document.documentElement.classList.contains('light-mode');
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) {
        btn.innerHTML = `<i data-lucide="${isLight ? 'sun' : 'moon'}" style="width: 18px; height: 18px;"></i>`;
        if (window.lucide) lucide.createIcons();
    }
}

function switchPanel(targetPanel) {
    if (!targetPanel) return;
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    targetPanel.classList.add('active');
    lastPanelByMode[state.mode] = targetPanel;
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Health Check. This ran exactly once at load, so a host that was still waking
// up (Render free instances cold-start for ~30-60s) pinned the offline banner on
// screen for the whole session even after the backend came up.
let healthPollTimer = null;

async function checkBackendHealth() {
    let online = false;
    try {
        const res = await fetch(`${API_BASE_URL}/healthz`, { cache: 'no-store' });
        online = res.ok;
    } catch (e) {
        online = false;
    }

    if (dom.backendOfflineBanner) {
        dom.backendOfflineBanner.style.display = online ? 'none' : 'flex';
    }

    // Poll fast while it is down (cold start), slowly once it is up.
    clearTimeout(healthPollTimer);
    healthPollTimer = setTimeout(checkBackendHealth, online ? 60000 : 5000);
    return online;
}


/* ==========================================================================
   RESEARCH MODE PIPELINE LOGIC & SESSION PERSISTENCE
   ========================================================================== */

function saveRMSession() {
    if (!state.rm.threadId) return;
    try {
        const { screenedPapers, ...persistableRmState } = state.rm;
        const sessionData = {
            threadId: state.rm.threadId,
            rmState: persistableRmState,
            lastSeq: state.rm.lastSeq || 0,
            timestamp: Date.now()
        };
        localStorage.setItem('rm_session', JSON.stringify(sessionData));
    } catch (e) {
        console.warn('Failed to save RM session:', e);
    }
}

function clearRMSession() {
    try {
        localStorage.removeItem('rm_session');
    } catch (e) {
        console.warn('Failed to clear RM session:', e);
    }
}

async function restoreRMSessionOnLoad() {
    try {
        const raw = localStorage.getItem('rm_session');
        if (!raw) return;
        const session = JSON.parse(raw);
        if (!session || !session.threadId) return;

        // 1. Immediately restore state from localStorage so progress is NEVER wiped on page reload
        state.rm.threadId = session.threadId;
        if (session.rmState) {
            Object.assign(state.rm, session.rmState);
        }
        if (session.lastSeq !== undefined) state.rm.lastSeq = session.lastSeq;

        // 2. Switch view to Research Mode workspace panel
        switchMode('researchmode');
        switchPanel(dom.rmWorkspacePanel);

        // 3. Render current progress from restored local state. This local cache
        // can only say "the last checkpoint we knew about was X" — it cannot tell
        // us whether the pipeline is still paused there or has since moved past
        // it (see the /research-mode/result fix below for why). So this pass
        // shows the paper/tracker as last known, but leaves the HITL panel alone;
        // step 4 below is the only thing authorized to decide whether that panel
        // should actually be visible.
        const currentCp = (state.rm.hitlCheckpoint || 'checkpoint_1').replace(/_(approved|revising)$/, '');
        const cpIdx = RM_STAGES.findIndex(s => s.id === currentCp);
        const completedStages = cpIdx > 0 ? RM_STAGES.slice(0, cpIdx).map(s => s.id) : [];
        updateRMPipelineTracker(currentCp, completedStages);
        if (dom.rmHitlPanel) dom.rmHitlPanel.style.display = 'none';
        if (state.rm.status === 'completed') {
            renderRMPaperFinal();
        } else if (typeof getPaperMarkdown === 'function' && getPaperMarkdown().trim().length > 50) {
            renderRMPaperLive(false);
        }

        showResumeBanner({ hitl_checkpoint: currentCp, is_completed: state.rm.status === 'completed' });
        updateNewRunVisibility();

        // 4. Ask the backend for ground truth and reconcile. values["hitl_checkpoint"]
        // and a non-empty state.next are both true for the entire rest of the run
        // after a checkpoint is passed, not just while paused there — so this now
        // relies on the backend's is_checkpoint, which is only true when the graph
        // is genuinely blocked inside interrupt() (see research_mode.py). Three
        // outcomes: finished, genuinely paused, or still executing.
        try {
            const res = await fetch(`${API_BASE_URL}/research-mode/result/${session.threadId}`);
            if (res.ok) {
                const data = await res.json();
                // This endpoint returns the raw graph state in snake_case. Copying it
                // straight onto state.rm (which is camelCase) meant a rehydrated
                // session rendered an empty paper and empty checkpoint panels.
                applyRMStatePayload(data.values || {});
                if (data.status) state.rm.status = data.status;

                if (data.is_completed) {
                    state.rm.hitlCheckpoint = 'title';
                    updateRMPipelineTracker('title', RM_STAGES.map(s => s.id));
                    if (dom.rmHitlPanel) dom.rmHitlPanel.style.display = 'none';
                    renderRMPaperFinal();
                } else if (data.is_checkpoint && data.hitl_checkpoint) {
                    const cp = data.hitl_checkpoint.replace(/_(approved|revising)$/, '');
                    state.rm.hitlCheckpoint = cp;
                    state.rm.hitlCheckpointPending = true;
                    state.rm.hitlApproved = false;
                    const idx = RM_STAGES.findIndex(s => s.id === cp);
                    const doneStages = idx > 0 ? RM_STAGES.slice(0, idx).map(s => s.id) : [];
                    updateRMPipelineTracker(cp, doneStages);
                    renderRMHitlPanel(cp);
                    if (typeof getPaperMarkdown === 'function' && getPaperMarkdown().trim().length > 50) {
                        renderRMPaperLive(false);
                    }
                } else {
                    // Not finished, not paused: a node is actively running on the
                    // backend right now. Show live progress and reopen the event
                    // stream so it keeps updating instead of sitting frozen.
                    if (dom.rmHitlPanel) dom.rmHitlPanel.style.display = 'none';
                    state.rm.hitlApproved = true;
                    state.rm.hitlCheckpointPending = false;
                    if (typeof getPaperMarkdown === 'function' && getPaperMarkdown().trim().length > 50) {
                        renderRMPaperLive(true);
                    }
                    reconnectRMStream();
                }
                saveRMSession();
            }
        } catch (syncErr) {
            console.warn('Backend session sync skipped (using local cache):', syncErr);
        }

    } catch (e) {
        console.warn('Error restoring session on load:', e);
    }
}

function showResumeBanner(data) {
    let banner = document.getElementById('rm-resume-banner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'rm-resume-banner';
        banner.className = 'original-query-banner';
        banner.style.display = 'flex';
        banner.style.justifyContent = 'space-between';
        banner.style.alignItems = 'center';
        banner.style.marginBottom = '1.25rem';

        const workspace = document.getElementById('rm-workspace-panel');
        if (workspace && workspace.firstChild) {
            workspace.insertBefore(banner, workspace.firstChild);
        }
    }

    const shortId = state.rm.threadId ? state.rm.threadId.slice(0, 8) : '';
    const statusText = data.is_completed
        ? 'Completed Academic Paper'
        : (data.hitl_checkpoint ? `Checkpoint (${data.hitl_checkpoint})` : 'In Progress');

    banner.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.6rem;">
            <i data-lucide="rotate-ccw" style="width: 18px; height: 18px; color: var(--academic-blue);"></i>
            <span><strong>Session Resumed:</strong> Rehydrated session <code>${shortId}</code> — Status: <em>${statusText}</em></span>
        </div>
        <button id="rm-banner-reset-btn" class="btn-secondary" style="padding: 0.3rem 0.75rem; font-size: 0.8rem; display: flex; align-items: center; gap: 0.35rem;">
            <i data-lucide="plus" style="width: 14px; height: 14px;"></i>
            <span>New Research</span>
        </button>
    `;

    if (window.lucide) lucide.createIcons();

    document.getElementById('rm-banner-reset-btn')?.addEventListener('click', resetResearchModeForm);
}

function resetResearchModeForm() {
    clearRMSession();
    state.rm.threadId = null;
    state.rm.status = 'idle';
    state.rm.hitlCheckpoint = null;
    state.rm.problemStatement = '';
    state.rm.researchObjectives = [];
    state.rm.researchQuestions = [];
    state.rm.keywords = [];
    state.rm.rawPapersCount = 0;
    state.rm.screenedPapersCount = 0;
    state.rm.literatureReview = '';
    state.rm.researchGap = '';
    state.rm.conceptualFramework = '';
    state.rm.hypotheses = [];
    state.rm.researchDesign = '';
    state.rm.dataCollectionPlan = '';
    state.rm.dataAnalysisPlan = '';
    state.rm.results = '';
    state.rm.discussion = '';
    state.rm.implications = '';
    state.rm.limitations = '';
    state.rm.conclusion = '';
    state.rm.futureScope = [];
    state.rm.references = [];
    state.rm.appendices = '';
    state.rm.introduction = '';
    state.rm.abstract = '';
    state.rm.title = '';
    state.rm.lastSeq = 0;
    state.rm.completedStages = [];
    state.rm.screenedPapers = [];
    state.rm.hitlApproved = false;
    state.rm.hitlCheckpointPending = false;
    state.rm.corpus_stats = null;

    if (dom.rmCorpusStatsBar) dom.rmCorpusStatsBar.style.display = 'none';
    if (dom.rmHitlPanel) dom.rmHitlPanel.style.display = 'none';
    if (dom.rmCopyPaperBtn) dom.rmCopyPaperBtn.style.display = 'none';
    if (dom.rmExportDropdown) dom.rmExportDropdown.style.display = 'none';

    if (dom.rmPsInput) { dom.rmPsInput.value = ''; rmPlaceholderCycle?.start(); }
    if (dom.rmObjsInput) dom.rmObjsInput.value = '';
    if (dom.rmRqsInput) dom.rmRqsInput.value = '';

    const banner = document.getElementById('rm-resume-banner');
    if (banner) banner.remove();

    if (dom.rmPaperTitle) dom.rmPaperTitle.textContent = 'Academic Paper Workspace';
    if (dom.rmPaperOutput) dom.rmPaperOutput.innerHTML = `
        <div class="paper-placeholder-state" id="rm-paper-placeholder">
            <div class="paper-idle-icon" style="margin-bottom: 0.5rem;">
                <i data-lucide="file-clock" style="width: 36px; height: 36px; color: var(--academic-blue); opacity: 0.7;"></i>
            </div>
            <p style="color: var(--text-secondary); font-weight: 600; font-size: 0.95rem;">
                Awaiting Checkpoint Approval
            </p>
            <p style="margin-top: 0.35rem; color: var(--text-muted); font-size: 0.82rem; max-width: 440px; line-height: 1.5; text-align: center;">
                Review the problem statement and objectives above, then click <strong style="color: var(--text-secondary);">Approve &amp; Continue Pipeline</strong> to start paper synthesis.
            </p>
        </div>
    `;
    if (window.lucide) lucide.createIcons();

    renderRMPipelineTracker();
    switchPanel(dom.rmInputPanel);
    showToast('Research session reset.', 'info');
}

function renderRMPipelineTracker() {
    if (!dom.rmPipelineStepsGrid) return;
    dom.rmPipelineStepsGrid.innerHTML = '';

    RM_STAGES.forEach((stage, idx) => {
        const stepEl = document.createElement('div');
        stepEl.className = 'pipeline-step';
        stepEl.id = `rm-step-${stage.id}`;

        if (stage.hitl) {
            stepEl.classList.add('hitl');
        }

        stepEl.innerHTML = `
            <span class="step-number">${stage.hitl ? 'REVIEW' : `STEP ${idx + 1}`}</span>
            <span class="step-label">${stage.name}</span>
        `;
        dom.rmPipelineStepsGrid.appendChild(stepEl);
    });
}

function updateRMPipelineTracker(activeStageId, completedStages) {
    const hidden = RM_HIDDEN_STAGES[activeStageId];
    const anchoredStageId = hidden ? hidden.anchor : activeStageId;
    const activeIdx = RM_STAGES.findIndex(s => s.id === anchoredStageId);

    // Completion is cumulative. It used to default to an empty array, so every
    // node_start event cleared the ticks off all previously finished steps and
    // the tracker appeared to restart from zero on each node.
    const done = new Set(state.rm.completedStages || []);
    if (Array.isArray(completedStages)) {
        completedStages.forEach(id => done.add(id));
    } else if (activeIdx > 0) {
        RM_STAGES.slice(0, activeIdx).forEach(s => done.add(s.id));
    }
    state.rm.completedStages = Array.from(done);

    RM_STAGES.forEach(stage => {
        const el = document.getElementById(`rm-step-${stage.id}`);
        if (!el) return;

        el.classList.remove('active', 'completed');
        if (done.has(stage.id)) {
            el.classList.add('completed');
        } else if (stage.id === anchoredStageId) {
            el.classList.add('active');
        }
    });

    if (dom.rmPipelineStatusTag) {
        const current = RM_STAGES.find(s => s.id === anchoredStageId);
        const label = hidden ? hidden.label : (current ? current.name : null);
        dom.rmPipelineStatusTag.textContent = label ? `Active: ${label}` : 'Pipeline Running';
    }
}

// Human-readable name for a raw graph node id, for the event log.
function rmStageLabel(nodeId) {
    if (!nodeId) return 'unknown';
    const hidden = RM_HIDDEN_STAGES[nodeId];
    if (hidden) return hidden.label;
    const stage = RM_STAGES.find(s => s.id === nodeId);
    return stage ? stage.name : nodeId;
}

// Some nodes stream for minutes with no node_update in between. Without this the
// tracker sat on a static label and the run looked hung.
let rmTokenActivityTimer = null;
function noteRMTokenActivity(nodeId) {
    if (!dom.rmPipelineStatusTag) return;
    dom.rmPipelineStatusTag.textContent = `Writing: ${rmStageLabel(nodeId)}…`;
    dom.rmPipelineStatusTag.classList.add('streaming');
    clearTimeout(rmTokenActivityTimer);
    rmTokenActivityTimer = setTimeout(() => {
        dom.rmPipelineStatusTag?.classList.remove('streaming');
    }, 2500);
}

async function handleRMStart() {
    const ps = dom.rmPsInput.value.trim();
    if (!ps) {
        showToast('Please enter a core Problem Statement to start Research Mode.', 'warning');
        return;
    }

    const objs = dom.rmObjsInput.value.split('\n').map(s => s.trim()).filter(Boolean);
    const rqs = dom.rmRqsInput.value.split('\n').map(s => s.trim()).filter(Boolean);

    const plannerModel = dom.rmModelPlanner?.value.trim();
    const researcherModel = dom.rmModelResearcher?.value.trim();
    const aggregatorModel = dom.rmModelAggregator?.value.trim();
    const models = {};
    if (plannerModel) models.planner = plannerModel;
    if (researcherModel) models.researcher = researcherModel;
    if (aggregatorModel) models.aggregator = aggregatorModel;

    dom.rmStartBtn.disabled = true;
    dom.rmStartBtn.innerHTML = '<div class="spinner-ring sm"></div><span>Defining research scope...</span>';

    try {
        const res = await fetch(`${API_BASE_URL}/research-mode/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ problem_statement: ps, research_objectives: objs, research_questions: rqs, models })
        });

        const contentType = res.headers.get('content-type') || '';
        if (!res.ok || !contentType.includes('application/json')) {
            throw new Error(`Server returned ${res.status} (${res.statusText || 'Non-JSON response'}). Make sure the backend server is running on ${API_BASE_URL}.`);
        }

        const data = await res.json();
        if (data.error || data.status === 'error') {
            showToast(data.error || 'Failed to start Research Mode.', 'error');
            dom.rmStartBtn.disabled = false;
            dom.rmStartBtn.innerHTML = '<span>Launch Autonomous Academic Pipeline</span>';
            return;
        }

        state.rm.threadId = data.thread_id;
        state.rm.problemStatement = data.problem_statement;
        state.rm.researchObjectives = data.research_objectives || [];
        state.rm.researchQuestions = data.research_questions || [];
        state.rm.keywords = data.keywords || [];
        state.rm.hitlCheckpoint = data.hitl_checkpoint;
        saveRMSession();

        state.rm.completedStages = [];
        switchPanel(dom.rmWorkspacePanel);
        updateRMPipelineTracker('checkpoint_1', ['scope_definition', 'keyword_extractor']);
        renderRMHitlPanel('checkpoint_1');
        updateNewRunVisibility();

    } catch (e) {
        showToast('Error connecting to Research Mode service: ' + e.message, 'error');
    } finally {
        dom.rmStartBtn.disabled = false;
        dom.rmStartBtn.innerHTML = '<span>Launch Autonomous Academic Pipeline</span>';
    }
}

function renderRMHitlPanel(checkpoint) {
    dom.rmHitlPanel.style.display = 'block';
    dom.rmHitlBody.innerHTML = '';
    dom.rmHitlFeedbackInput.value = '';
    dom.rmHitlFeedbackInput.placeholder = 'Specify any edits or revisions for this phase...';

    if (checkpoint === 'checkpoint_1') {
        dom.rmHitlTitle.textContent = 'Checkpoint 1: Scope Review — Problem, Objectives & Questions';
        dom.rmHitlBadge.textContent = 'Checkpoint 1 of 4';
        dom.rmHitlFeedbackInput.placeholder = 'e.g. Make objective 2 focus on cost, not latency. Add a question about long-term stability.';

        const objectives = state.rm.researchObjectives || [];
        const questions = state.rm.researchQuestions || [];

        dom.rmHitlBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">Problem Statement</label>
                <div class="problem-statement-text">${renderMarkdownSafe(state.rm.problemStatement)}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Research Objectives <span class="label-tag">auto-defined</span></label>
                <div class="subtasks-list">
                    ${objectives.map((o, i) => `
                        <div class="subtask-item">
                            <span class="subtask-number">O${i + 1}</span>
                            <span class="subtask-content">${renderMarkdownSafe(o)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Research Questions <span class="label-tag">auto-defined</span></label>
                <div class="subtasks-list">
                    ${questions.map((q, i) => `
                        <div class="subtask-item">
                            <span class="subtask-number">RQ${i + 1}</span>
                            <span class="subtask-content">${renderMarkdownSafe(q)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Extracted Academic Keywords (6-10)</label>
                <div class="chips-container">
                    ${(state.rm.keywords || []).map(kw => `<span class="chip active">${escapeHtml(kw)}</span>`).join('')}
                </div>
            </div>
        `;
    } else if (checkpoint === 'checkpoint_2') {
        dom.rmHitlTitle.textContent = 'Checkpoint 2: Literature Review & Framework Review';
        dom.rmHitlBadge.textContent = 'Checkpoint 2 of 4';

        dom.rmHitlBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">Synthesized Literature Review Snippet</label>
                <div class="problem-statement-text">${renderMarkdownSafe((state.rm.literatureReview || '').slice(0, 400))}...</div>
            </div>
            <div class="form-group">
                <label class="form-label">Identified Research Gap</label>
                <div class="problem-statement-text">${renderMarkdownSafe(state.rm.researchGap)}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Proposed Conceptual Framework</label>
                <div class="problem-statement-text">${renderMarkdownSafe(state.rm.conceptualFramework)}</div>
            </div>
        `;
    } else if (checkpoint === 'checkpoint_3') {
        dom.rmHitlTitle.textContent = 'Checkpoint 3: Hypotheses Review';
        dom.rmHitlBadge.textContent = 'Checkpoint 3 of 4';

        dom.rmHitlBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">Formulated Research Hypotheses</label>
                <div class="subtasks-list">
                    ${(state.rm.hypotheses || []).map((h, i) => `
                        <div class="subtask-item">
                            <span class="subtask-number">H${i+1}</span>
                            <span class="subtask-content">${renderMarkdownSafe(h)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } else if (checkpoint === 'checkpoint_4') {
        dom.rmHitlTitle.textContent = 'Checkpoint 4: Research Methodology Review';
        dom.rmHitlBadge.textContent = 'Checkpoint 4 of 4';

        dom.rmHitlBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">Research Design</label>
                <div class="problem-statement-text">${renderMarkdownSafe(state.rm.researchDesign)}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Data Collection Plan</label>
                <div class="problem-statement-text">${renderMarkdownSafe(state.rm.dataCollectionPlan)}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Data Analysis Plan</label>
                <div class="problem-statement-text">${renderMarkdownSafe(state.rm.dataAnalysisPlan)}</div>
            </div>
        `;
    } else {
        // Guards against an unrecognised checkpoint id silently rendering an
        // empty review panel with nothing but an approve button.
        dom.rmHitlTitle.textContent = 'Checkpoint Review Required';
        dom.rmHitlBadge.textContent = 'Review';
        dom.rmHitlBody.innerHTML = `
            <p class="rm-hint">The pipeline is paused at <code>${escapeHtml(checkpoint)}</code>.
            Approve to continue, or describe the changes you want first.</p>
        `;
    }

    refreshIcons();
}

async function handleRMApprove(feedback) {
    if (!state.rm.threadId) return;

    state.rm.hitlApproved = true;
    state.rm.hitlCheckpointPending = false;
    dom.rmHitlPanel.style.display = 'none';

    const currentCp = (state.rm.hitlCheckpoint || 'checkpoint_1').replace(/_(approved|revising)$/, '');
    const cpIdx = RM_STAGES.findIndex(s => s.id === currentCp);
    const completedStages = cpIdx >= 0 ? RM_STAGES.slice(0, cpIdx + 1).map(s => s.id) : ['scope_definition', 'keyword_extractor', 'checkpoint_1'];
    const nextStage = cpIdx >= 0 && cpIdx + 1 < RM_STAGES.length ? RM_STAGES[cpIdx + 1].id : 'paper_fetcher';

    updateRMPipelineTracker(nextStage, completedStages);
    appendLogLine(`Checkpoint '${currentCp}' approved. Resuming pipeline...`, 'info');
    saveRMSession();

    if (dom.rmPaperTitle) dom.rmPaperTitle.textContent = state.rm.title || 'Synthesizing Paper...';
    if (dom.rmPaperOutput && !getPaperMarkdown().trim()) {
        dom.rmPaperOutput.innerHTML = `
            <div class="paper-placeholder-state" id="rm-paper-placeholder">
                <div class="orbital-loader-container">
                    <div class="orbital-ring"></div>
                    <p style="margin-top: 1rem; color: var(--text-secondary); font-weight: 500; display: flex; align-items: center;">
                        <span>Academic pipeline active &amp; synthesizing</span>
                        <span class="ai-wave-container">
                            <span class="ai-wave-bar"></span>
                            <span class="ai-wave-bar"></span>
                            <span class="ai-wave-bar"></span>
                            <span class="ai-wave-bar"></span>
                        </span>
                    </p>
                </div>
            </div>
        `;
    }

    await openRMEventStream(feedback);
}

// Opens (or reconnects to) the Research Mode SSE stream. Shared by handleRMApprove
// (after the user acts on a checkpoint) and reconnectRMStream (page reload while
// the pipeline is still running server-side) so both get the same retry and
// event-parsing behavior instead of two copies drifting apart.
async function openRMEventStream(message) {
    if (activeRMController) activeRMController.abort();
    activeRMController = new AbortController();

    let attempt = 0;
    const maxRetries = 5;
    let isTerminal = false;
    let receivedEventsCount = 0;

    while (attempt <= maxRetries && !isTerminal) {
        try {
            const reqMessage = attempt === 0 ? (message || '') : '';
            const reqPayload = { thread_id: state.rm.threadId, message: reqMessage };
            if (state.rm.lastSeq !== undefined && state.rm.lastSeq !== null) {
                reqPayload.from_seq = state.rm.lastSeq;
            }
            const reqHeaders = { 'Content-Type': 'application/json' };
            if (state.rm.lastSeq !== undefined && state.rm.lastSeq !== null) {
                reqHeaders['Last-Event-ID'] = String(state.rm.lastSeq);
            }

            const response = await fetch(`${API_BASE_URL}/research-mode/approve`, {
                method: 'POST',
                headers: reqHeaders,
                body: JSON.stringify(reqPayload),
                signal: activeRMController.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                const events = buffer.split('\n\n');
                buffer = events.pop();

                for (const rawEvent of events) {
                    // Every buffered event (node_start, node_update, checkpoint,
                    // completed, error, resume) is prefixed with its own "id: N"
                    // line before "data: ", so rawEvent never actually starts with
                    // "data: " for those. Only token_stream (unbuffered, no id:
                    // line) ever matched here — every other event was silently
                    // dropped, which is why the tracker/paper/checkpoint panel
                    // never advanced past the very first node_start.
                    for (const line of rawEvent.split('\n')) {
                        if (!line.startsWith('data: ')) continue;
                        try {
                            const data = JSON.parse(line.slice(6));
                            receivedEventsCount++;
                            const evt = processRMSEEvent(data);
                            if (evt === 'checkpoint' || evt === 'completed' || evt === 'error') {
                                isTerminal = true;
                            }
                            attempt = 0;
                        } catch (e) {
                            console.warn('RM SSE parse error:', e);
                        }
                    }
                }
            }

            if (isTerminal) break;

            // Fallback sync if stream ended cleanly without events
            if (receivedEventsCount === 0 && state.rm.threadId) {
                try {
                    const syncRes = await fetch(`${API_BASE_URL}/research-mode/result/${state.rm.threadId}`);
                    if (syncRes.ok) {
                        const syncData = await syncRes.json();
                        if (syncData.values) applyRMStatePayload(syncData.values);
                        if (syncData.is_checkpoint) {
                            const cp = (syncData.hitl_checkpoint || 'checkpoint_1').replace(/_(approved|revising)$/, '');
                            renderRMHitlPanel(cp);
                        }
                    }
                } catch (e) {
                    console.warn('RM result sync failed:', e);
                }
            }
            break;

        } catch (e) {
            if (e.name === 'AbortError') {
                console.log('RM SSE stream aborted by user.');
                break;
            }
            attempt++;
            if (attempt > maxRetries) {
                showToast('Connection lost. Auto-reconnect failed: ' + e.message, 'error');
                break;
            }
            showToast(`Connection dropped. Auto-reconnecting (attempt ${attempt}/${maxRetries})...`, 'warning');
            await new Promise(res => setTimeout(res, 1000 * Math.pow(1.5, attempt - 1)));
        }
    }
}

// Re-attaches to an already-running pipeline after a page reload. The backend
// keeps executing in its own asyncio task regardless of whether any browser is
// listening, so without this the frontend was permanently frozen on whatever it
// last saw before the reload — new node_update/checkpoint/completed events had
// nowhere to land until the user manually clicked something. from_seq (read from
// state.rm.lastSeq, restored from localStorage) makes the backend replay only
// what was missed instead of restreaming from the start.
async function reconnectRMStream() {
    if (!state.rm.threadId) return;
    appendLogLine('Reconnecting to live pipeline…', 'info');
    await openRMEventStream('');
}

function appendLogLine(msg, level = 'info') {
    if (!dom.rmLogBody) return;
    const timeStr = new Date().toLocaleTimeString();
    const div = document.createElement('div');
    div.className = `rm-log-line ${level}`;
    div.style.color = level === 'warn' ? '#fbbf24' : (level === 'success' ? '#34d399' : (level === 'error' ? '#f87171' : '#38bdf8'));
    div.textContent = `[${timeStr}] ${msg}`;
    dom.rmLogBody.appendChild(div);
    dom.rmLogBody.scrollTop = dom.rmLogBody.scrollHeight;

    const count = dom.rmLogBody.children.length;
    if (dom.rmLogCount) dom.rmLogCount.textContent = `${count} events`;
}

function updateCorpusStats(stats) {
    if (!stats) return;
    if (dom.statRetrieved) dom.statRetrieved.textContent = stats.retrieved || 0;
    if (dom.statDedup) dom.statDedup.textContent = stats.after_dedup || 0;
    if (dom.statScreened) dom.statScreened.textContent = stats.screened || 0;
    if (dom.statIncluded) dom.statIncluded.textContent = stats.included || 0;
    if (dom.statFulltext) dom.statFulltext.textContent = stats.fulltext_fetched || 0;
    if (dom.rmCorpusStatsBar) dom.rmCorpusStatsBar.style.display = 'flex';
}

function openPaperInspector(paper) {
    if (!paper || !dom.paperDetailModal) return;
    if (dom.modalPaperTitle) dom.modalPaperTitle.textContent = paper.title || 'Paper Details';
    if (dom.modalPaperBody) {
        dom.modalPaperBody.innerHTML = `
            <div style="margin-bottom: 1rem;">
                <h4 style="margin: 0 0 0.5rem 0; color: var(--academic-blue); font-size: 1.05rem;">${paper.title || 'Untitled'}</h4>
                <p style="margin: 0.25rem 0; color: var(--text-muted);"><strong>Authors:</strong> ${Array.isArray(paper.authors) ? paper.authors.join(', ') : (paper.authors || 'N/A')}</p>
                <p style="margin: 0.25rem 0; color: var(--text-muted);"><strong>Venue / Year:</strong> ${paper.venue || paper.journal || 'Academic Index'} (${paper.year || 'N/A'})</p>
                <p style="margin: 0.25rem 0;"><strong>DOI:</strong> ${paper.doi ? `<a href="https://doi.org/${paper.doi}" target="_blank" style="color: var(--academic-blue);">${paper.doi}</a>` : 'N/A'}</p>
                <p style="margin: 0.25rem 0;"><strong>PDF Source:</strong> ${paper.pdf_url ? `<a href="${paper.pdf_url}" target="_blank" style="color: var(--emerald-accent);">[Open Access PDF Link]</a>` : '<span style="color: var(--text-muted);">No PDF Direct Link</span>'}</p>
            </div>
            <div style="background: var(--bg-surface); padding: 0.75rem; border-radius: 8px; border: 1px solid var(--border-color); margin-bottom: 1rem;">
                <p style="margin: 0 0 0.25rem 0; font-weight: 600;">Relevance Score: <span style="color: var(--academic-blue);">${paper.relevance_score || 'N/A'}/10</span></p>
                <p style="margin: 0; color: var(--text-secondary);"><strong>Inclusion Rationale:</strong> ${paper.inclusion_reason || paper.rationale || 'Selected based on topic alignment.'}</p>
            </div>
            <div style="margin-top: 1rem;">
                <h5 style="margin: 0 0 0.5rem 0; font-size: 0.95rem; font-weight: 600;">Extracted Full-Text Excerpt</h5>
                <pre style="white-space: pre-wrap; font-family: monospace; font-size: 0.82rem; background: #0f172a; color: #f8fafc; padding: 0.85rem; border-radius: 8px; max-height: 250px; overflow-y: auto;">${paper.fulltext_excerpt || paper.abstract || 'No full-text excerpt extracted for this paper.'}</pre>
            </div>
        `;
    }
    dom.paperDetailModal.style.display = 'flex';
}

function processRMSEEvent(data) {
    const trackerContainer = document.querySelector('.pipeline-tracker-container');
    const paperCard = document.getElementById('rm-paper-card');

    // Every buffered event carries a seq. Only some of them used to update
    // lastSeq, so a reconnect asked the server to replay from a stale point and
    // the tracker jumped backwards through nodes it had already passed.
    if (data.seq !== undefined && data.seq !== null) state.rm.lastSeq = data.seq;

    if (data.event === 'node_start') {
        updateRMPipelineTracker(data.node);
        appendLogLine(`Node started: ${rmStageLabel(data.node)}`, 'info');
        if (trackerContainer) trackerContainer.classList.add('active-execution');
        if (paperCard) paperCard.classList.add('active-execution');
        saveRMSession();
    } else if (data.event === 'token_stream') {
        // Not buffered server-side and not part of the paper state; it is the only
        // signal that a long node is still alive, so it drives the status tag.
        noteRMTokenActivity(data.node);
    } else if (data.event === 'resume') {
        appendLogLine('Pipeline resumed.', 'info');
    } else if (data.event === 'node_update') {
        applyRMStatePayload(data.data || {});
        appendLogLine(`Node updated: ${rmStageLabel(data.node)}`, 'success');
        if (data.data && data.data.corpus_stats) updateCorpusStats(data.data.corpus_stats);
        renderRMPaperLive();
        saveRMSession();
    } else if (data.event === 'checkpoint') {
        const cp = (data.hitl_checkpoint || 'checkpoint_1').replace(/_(approved|revising)$/, '');
        state.rm.hitlCheckpoint = cp;
        state.rm.hitlCheckpointPending = true;
        state.rm.hitlApproved = false;
        applyRMStatePayload(data.state || {});
        appendLogLine(`HITL Checkpoint reached: ${cp}`, 'warn');
        if (data.state && data.state.corpus_stats) updateCorpusStats(data.state.corpus_stats);
        updateRMPipelineTracker(cp);
        if (trackerContainer) trackerContainer.classList.remove('active-execution');
        if (paperCard) paperCard.classList.remove('active-execution');
        renderRMHitlPanel(cp);
        // The pipeline blocks here until the user acts, and the panel can be far
        // below the fold on a long paper, so it has to announce itself.
        showToast('Checkpoint reached — your review is required to continue.', 'warning');
        dom.rmHitlPanel?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        saveRMSession();
    } else if (data.event === 'completed') {
        state.rm.status = 'completed';
        state.rm.hitlCheckpointPending = false;
        state.rm.hitlApproved = true;
        applyRMStatePayload(data.state || {});
        appendLogLine(`Pipeline execution completed!`, 'success');
        if (data.state && data.state.corpus_stats) updateCorpusStats(data.state.corpus_stats);
        updateRMPipelineTracker('title', RM_STAGES.map(s => s.id));
        if (trackerContainer) trackerContainer.classList.remove('active-execution');
        if (paperCard) paperCard.classList.remove('active-execution');
        renderRMPaperFinal();
        saveRMSession();
    } else if (data.event === 'error') {
        appendLogLine(`Pipeline Error: ${data.message}`, 'error');
        if (trackerContainer) trackerContainer.classList.remove('active-execution');
        if (paperCard) paperCard.classList.remove('active-execution');
        if (dom.rmPipelineStatusTag) dom.rmPipelineStatusTag.textContent = 'Pipeline stopped — error';
        // The run is dead, so the "synthesizing" spinner must not keep spinning
        // forever. Show whatever was produced before the failure instead.
        state.rm.status = 'error';
        renderRMPaperLive(false);
        showToast(data.message || 'Pipeline error occurred.', 'error');
        saveRMSession();
    }
    return data.event;
}

function renderRMPaperLive(isStreaming = true) {
    if (dom.rmPaperTitle) dom.rmPaperTitle.textContent = state.rm.title || 'Synthesizing Academic Paper...';
    if (dom.rmPaperOutput) {
        // Re-rendering the whole document threw away the reader's scroll position
        // on every node_update, yanking them back to the top mid-read.
        const scroller = dom.rmPaperOutput;
        const prevScroll = scroller.scrollTop;
        const wasAtBottom = scroller.scrollHeight - scroller.clientHeight - prevScroll < 40;

        let content = renderMarkdown(getPaperMarkdown());
        if (isStreaming) {
            content += '<span class="typing-cursor"></span>';
        }
        scroller.innerHTML = content;
        scroller.scrollTop = wasAtBottom ? scroller.scrollHeight : prevScroll;
    }
}

function renderRMPaperFinal() {
    renderRMPaperLive(false);
    if (dom.rmCopyPaperBtn) dom.rmCopyPaperBtn.style.display = 'inline-flex';
    if (dom.rmExportDropdown) dom.rmExportDropdown.style.display = 'inline-flex';
    if (dom.rmExportPdfBtn) dom.rmExportPdfBtn.style.display = 'inline-flex';
    showToast('Academic Paper Synthesis Completed!', 'success');
}

function getPaperMarkdown() {
    const s = state.rm;
    let md = `# ${s.title || 'Academic Research Report'}\n\n`;
    if (s.abstract) md += `## Abstract\n${s.abstract}\n\n`;
    if (s.introduction) md += `## 1. Introduction\n${s.introduction}\n\n`;
    if (s.literatureReview) md += `## 2. Literature Review\n${s.literatureReview}\n\n`;
    if (s.researchGap) md += `## 3. Research Gap\n${s.researchGap}\n\n`;
    if (s.researchObjectives && s.researchObjectives.length) md += `## 4. Research Objectives\n${s.researchObjectives.map((o, i) => `${i+1}. ${o}`).join('\n')}\n\n`;
    if (s.researchQuestions && s.researchQuestions.length) md += `## 5. Research Questions\n${s.researchQuestions.map((q, i) => `**RQ${i+1}**: ${q}`).join('\n\n')}\n\n`;
    if (s.conceptualFramework) md += `## 6. Conceptual Framework\n${s.conceptualFramework}\n\n`;
    if (s.hypotheses && s.hypotheses.length) md += `## 7. Hypotheses\n${s.hypotheses.map((h, i) => `- **H${i+1}**: ${h}`).join('\n')}\n\n`;
    if (s.researchDesign) md += `## 8. Methodology\n### 8.1 Research Design\n${s.researchDesign}\n\n### 8.2 Data Collection\n${s.dataCollectionPlan}\n\n### 8.3 Data Analysis\n${s.dataAnalysisPlan}\n\n`;
    if (s.results) md += `## 9. Results\n${s.results}\n\n`;
    if (s.discussion) md += `## 10. Discussion\n${s.discussion}\n\n${s.implications ? `### 10.1 Implications\n${s.implications}\n\n` : ''}`;
    if (s.limitations) md += `## 11. Limitations\n${s.limitations}\n\n`;
    if (s.conclusion) md += `## 12. Conclusion\n${s.conclusion}\n\n`;
    if (s.futureScope && s.futureScope.length) md += `## 13. Future Scope\n${Array.isArray(s.futureScope) ? s.futureScope.map(f => `- ${f}`).join('\n') : s.futureScope}\n\n`;
    if (s.references && s.references.length) md += `## 14. References\n${s.references.map(r => `- ${r}`).join('\n')}\n\n`;
    if (s.appendices) md += `## 15. Appendices\n${s.appendices}\n\n`;
    return md;
}


function toggleExportMenu(event) {
    if (event) event.stopPropagation();
    const menu = document.getElementById("rm-export-menu");
    if (menu) {
        menu.classList.toggle("show");
    }
}

document.addEventListener("click", () => {
    const menu = document.getElementById("rm-export-menu");
    if (menu && menu.classList.contains("show")) {
        menu.classList.remove("show");
    }
});

async function exportReport(format = 'pdf') {
    if (!state.rm.threadId) return;
    const menu = document.getElementById("rm-export-menu");
    if (menu) menu.classList.remove("show");

    const endpoint = format === 'docx' 
        ? `${API_BASE_URL}/research-mode/export/docx/${state.rm.threadId}` 
        : `${API_BASE_URL}/research-mode/export/${state.rm.threadId}`;
    const ext = format === 'docx' ? 'docx' : 'pdf';

    try {
        const res = await fetch(endpoint, { method: 'POST' });
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `academic_paper_${state.rm.threadId.slice(0, 8)}.${ext}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            showToast(`Exported ${ext.toUpperCase()} successfully!`, 'success');
        } else {
            showToast(`Failed to export ${ext.toUpperCase()}.`, 'error');
        }
    } catch (e) {
        showToast(`Error exporting ${ext.toUpperCase()}: ` + e.message, 'error');
    }
}



/* ==========================================================================
   DEEPSEARCH MODE HANDLERS & HELPERS
   ========================================================================== */

// Shimmering placeholders while the planner works. The skeleton styles already
// existed but nothing ever rendered them, so the panel just showed bare text.
function renderPlanSkeleton() {
    if (dom.approvalPsText) {
        dom.approvalPsText.innerHTML =
            '<span class="skeleton skeleton-ps" style="width:92%"></span>' +
            '<span class="skeleton skeleton-ps" style="width:85%"></span>' +
            '<span class="skeleton skeleton-ps"></span>';
    }
    if (dom.approvalSubtasksContainer) {
        dom.approvalSubtasksContainer.innerHTML =
            '<span class="skeleton skeleton-task" style="width:100%"></span>'.repeat(4);
    }
}

async function handlePlanResearch() {
    const query = dom.queryInput.value.trim();
    if (!query) {
        showToast('Please enter a research query.', 'warning');
        return;
    }

    state.query = query;
    dom.approvalQueryDisplay.textContent = `"${query}"`;
    switchPanel(dom.approvalPanel);

    setDeepSearchBusy(true);
    renderPlanSkeleton();

    try {
        const res = await fetch(`${API_BASE_URL}/research/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: state.query, search_topic: state.searchTopic })
        });
        const contentType = res.headers.get('content-type') || '';
        if (!res.ok || !contentType.includes('application/json')) {
            throw new Error(`Server returned ${res.status} (${res.statusText || 'Non-JSON response'}). Make sure the backend server is running on ${API_BASE_URL}.`);
        }
        const data = await res.json();
        if (data.status === 'error') {
            showToast(data.error || 'Failed to create plan.', 'error');
            return;
        }

        state.threadId = data.thread_id;
        state.ps = data.ps;
        state.plan = data.plan || [];
        renderApprovalPanel();
        updateNewRunVisibility();

    } catch (e) {
        showToast('Error planning research: ' + e.message, 'error');
        // The panel already switched and is showing shimmer placeholders that
        // will never resolve, so send the user back to the query box.
        switchPanel(dom.landingPanel);
    } finally {
        setDeepSearchBusy(false);
    }
}

function renderApprovalPanel() {
    dom.approvalPsText.innerHTML = '';
    dom.approvalPsText.innerHTML = renderMarkdownSafe(state.ps);
    dom.approvalSubtasksContainer.innerHTML = '';
    state.plan.forEach((task, idx) => {
        const item = document.createElement('div');
        item.className = 'subtask-item';
        item.innerHTML = `
            <div class="subtask-number">${idx + 1}</div>
            <div class="subtask-content">${renderMarkdownSafe(task)}</div>
        `;
        dom.approvalSubtasksContainer.appendChild(item);
    });
}

async function handleRevision() {
    const feedback = dom.feedbackInput.value.trim();
    if (!feedback) return;

    renderPlanSkeleton();
    // A revision keeps the user on the approval panel: the graph loops back to the
    // planner and interrupts again. Sending them to the execution workspace (as
    // this used to) left them staring at an empty report that never filled in.
    await submitPlanApprovalWithMessage(feedback, { isRevision: true });
}

async function submitPlanApproval() {
    await submitPlanApprovalWithMessage('approve', { isRevision: false });
}

async function submitPlanApprovalWithMessage(message, { isRevision = false } = {}) {
    if (!state.threadId) return;

    setDeepSearchBusy(true);

    if (!isRevision) {
        state.finalAnswer = '';
        state.workers = {};
        renderWorkers();
        if (dom.reportOutput) dom.reportOutput.innerHTML = '';
        switchPanel(dom.workspacePanel);
        researchTimer.start();
    }

    try {
        const response = await fetch(`${API_BASE_URL}/research/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_id: state.threadId, message: message })
        });

        // Without this a 500 from the backend produced an unreadable body, no
        // events, and a workspace that sat blank with the timer still running.
        if (!response.ok || !response.body) {
            throw new Error(`Server returned ${response.status} ${response.statusText || ''}`.trim());
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const events = buffer.split('\n\n');
            buffer = events.pop();

            for (const rawEvent of events) {
                for (const line of rawEvent.split('\n')) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        processDeepSearchSSEEvent(JSON.parse(line.slice(6)));
                    } catch (e) {
                        console.warn('DeepSearch SSE parse error:', e);
                    }
                }
            }
        }
    } catch (e) {
        researchTimer.stop();
        if (dom.reportStreamingIndicator) dom.reportStreamingIndicator.style.display = 'none';
        showToast('Research stream failed: ' + e.message, 'error');
        // Nothing arrived, so put the user back where they can retry instead of
        // stranding them on an empty workspace.
        if (isRevision || !state.finalAnswer) switchPanel(dom.approvalPanel);
    } finally {
        setDeepSearchBusy(false);
    }
}

// Disables the approve/revise controls while a stream is open so a double click
// cannot start two concurrent runs against the same thread.
function setDeepSearchBusy(busy) {
    [dom.approvePlanBtn, dom.submitFeedbackBtn, dom.planResearchBtn].forEach(btn => {
        if (btn) btn.disabled = busy;
    });
}

function processDeepSearchSSEEvent(data) {
    if (data.event === 'node_start') {
        if (data.node && data.node.startsWith('researcher')) {
            const existing = state.workers[data.node];
            state.workers[data.node] = {
                task: data.task,
                status: 'running',
                logs: existing ? existing.logs : []
            };
            renderWorkers();
        }
    } else if (data.event === 'node_update') {
        // The backend sends node_update for every finished node. Nothing consumed
        // it, so researcher cards stayed pinned at "running" for the whole run.
        if (data.node && data.node.startsWith('researcher') && state.workers[data.node]) {
            state.workers[data.node].status = 'completed';
            renderWorkers();
        }
        if (data.node === 'aggregator' && dom.reportStreamingIndicator) {
            dom.reportStreamingIndicator.style.display = 'none';
        }
    } else if (data.event === 'researcher_search') {
        // data.task is the researcher's query string, which is what node_start
        // stored on the worker record.
        const wKey = Object.keys(state.workers).find(k => state.workers[k].task === data.task);
        if (wKey && data.query) {
            state.workers[wKey].logs.push(data.query);
            renderWorkers();
        }
    } else if (data.event === 'aggregator_token') {
        if (dom.reportStreamingIndicator) dom.reportStreamingIndicator.style.display = 'flex';
        state.finalAnswer += data.token;
        dom.reportOutput.innerHTML = renderMarkdown(state.finalAnswer) + '<span class="streaming-cursor">|</span>';
    } else if (data.event === 'awaiting_approval') {
        // The planner revised the plan and interrupted again. This event had no
        // handler at all, so "Request Revision" simply hung forever.
        researchTimer.stop();
        state.ps = data.ps || state.ps;
        state.plan = data.plan || state.plan;
        renderApprovalPanel();
        switchPanel(dom.approvalPanel);
        if (dom.feedbackInput) dom.feedbackInput.value = '';
        if (dom.submitFeedbackBtn) dom.submitFeedbackBtn.style.display = 'none';
        if (dom.approvePlanBtn) dom.approvePlanBtn.style.display = 'flex';
        showToast('Plan revised. Review it and approve when ready.', 'info');
    } else if (data.event === 'completed') {
        researchTimer.stop();
        if (dom.reportStreamingIndicator) dom.reportStreamingIndicator.style.display = 'none';
        state.finalAnswer = data.final_answer || state.finalAnswer;
        dom.reportOutput.innerHTML = renderMarkdown(state.finalAnswer);
        // Any researcher still marked running finished with the graph.
        Object.values(state.workers).forEach(w => { if (w.status === 'running') w.status = 'completed'; });
        renderWorkers();
        dom.copyMdBtn.style.display = 'inline-flex';
        dom.downloadMdBtn.style.display = 'inline-flex';
        dom.workspaceNewResearchBtn.style.display = 'inline-flex';
        if (data.citations) renderCitations(data.citations);
    } else if (data.event === 'error') {
        researchTimer.stop();
        if (dom.reportStreamingIndicator) dom.reportStreamingIndicator.style.display = 'none';
        showToast(data.message || 'Research pipeline error.', 'error');
    }
}

function renderWorkers() {
    if (!dom.workersListContainer) return;
    dom.workersListContainer.innerHTML = '';
    Object.entries(state.workers).forEach(([id, w]) => {
        const card = document.createElement('div');
        card.className = 'worker-card';
        const searches = (w.logs || []).slice(-3);
        card.innerHTML = `
            <div class="worker-header">
                <strong>${escapeHtml(id.replace('_', ' '))}</strong>
                <span class="worker-status ${w.status}">${w.status}</span>
            </div>
            <div class="worker-task">${escapeHtml(w.task)}</div>
            ${searches.length ? `<div class="worker-queries">${
                searches.map(q => `<span class="worker-query">${escapeHtml(q)}</span>`).join('')
            }</div>` : ''}
        `;
        dom.workersListContainer.appendChild(card);
    });
}

function renderCitations(citations) {
    if (!dom.workspaceSourcesContainer) return;
    dom.workspaceSourcesContainer.innerHTML = '';
    citations.forEach(url => {
        const card = document.createElement('a');
        card.className = 'source-card';
        card.href = url;
        card.target = '_blank';
        card.rel = 'noopener noreferrer';
        card.innerHTML = `<i data-lucide="link"></i><span>${escapeHtml(url)}</span>`;
        dom.workspaceSourcesContainer.appendChild(card);
    });
    dom.workspaceSourcesSection.style.display = 'block';
    refreshIcons();
}

// "New Run" is shared by both modes. It used to always wipe the Research Mode
// session and drop the user on the DeepSearch landing page, so pressing it from
// a live Research Mode run destroyed that run.
function resetToLanding() {
    if (state.mode === 'researchmode') {
        resetResearchModeForm();
        updateNewRunVisibility();
        return;
    }
    researchTimer.reset();
    state.threadId = null;
    state.ps = '';
    state.plan = [];
    state.finalAnswer = '';
    state.workers = {};
    renderWorkers();
    if (dom.reportOutput) dom.reportOutput.innerHTML = '';
    if (dom.workspaceSourcesSection) dom.workspaceSourcesSection.style.display = 'none';
    [dom.copyMdBtn, dom.downloadMdBtn, dom.workspaceNewResearchBtn].forEach(b => {
        if (b) b.style.display = 'none';
    });
    dom.queryInput.value = '';
    dsPlaceholderCycle?.start();
    switchPanel(dom.landingPanel);
    updateNewRunVisibility();
}

// The header button is markup-hidden and nothing ever revealed it, so there was
// no way out of a run except a reload.
function updateNewRunVisibility() {
    if (!dom.newResearchBtn) return;
    const active = state.mode === 'researchmode' ? !!state.rm.threadId : !!state.threadId;
    dom.newResearchBtn.style.display = active ? 'flex' : 'none';
}

async function copyToClipboard(text, btnEl) {
    const orig = btnEl.innerHTML;
    try {
        // navigator.clipboard is undefined on insecure origins; this threw and
        // left the button showing "Copied!" for a copy that never happened.
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
        } else {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            ta.remove();
        }
        btnEl.innerHTML = '<span>Copied!</span>';
    } catch (e) {
        btnEl.innerHTML = '<span>Copy failed</span>';
        showToast('Could not copy to clipboard: ' + e.message, 'error');
    }
    setTimeout(() => { btnEl.innerHTML = orig; refreshIcons(); }, 2000);
}

function downloadMarkdownReport() {
    const blob = new Blob([state.finalAnswer], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research_report_${state.threadId ? state.threadId.slice(0,8) : 'export'}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
}

function showToast(msg, type = 'info') {
    // showToast is called from error paths that can fire before the DOM cache is
    // built. Throwing here used to mask the original error.
    const container = dom.toastContainer || document.getElementById('toast-container');
    if (!container) {
        console.warn(`[toast:${type}] ${msg}`);
        return;
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
