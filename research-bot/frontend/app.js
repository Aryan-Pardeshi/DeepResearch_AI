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
// index.html straight off disk is the one case that needs an explicit host.
const API_BASE_URL = window.API_BASE_URL || (
    window.location.protocol === 'file:' ? 'http://localhost:8000' : window.location.origin
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
        activeStage: 'scope_definition'
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

// Nodes that run without their own tile in the tracker grid
const RM_HIDDEN_STAGES = {
    scope_reviser: { label: 'Revising Scope', anchor: 'checkpoint_1' }
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

function applyRMStatePayload(payload) {
    if (!payload) return;
    Object.entries(RM_STATE_KEY_MAP).forEach(([snake, camel]) => {
        const value = payload[snake];
        if (value !== undefined && value !== null && value !== '') {
            state.rm[camel] = value;
        }
    });
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
    if (window.lucide) lucide.createIcons();
});

function cacheDomElements() {
    dom = {
        // App header & settings
        statusBadge: document.getElementById('app-status-badge'),
        statusDot: document.getElementById('app-status-dot'),
        statusText: document.getElementById('app-status-text'),
        themeToggleBtn: document.getElementById('theme-toggle-btn'),
        settingsBtn: document.getElementById('settings-btn'),
        newResearchBtn: document.getElementById('new-research-btn'),
        settingsModal: document.getElementById('settings-modal'),
        settingsClose: document.getElementById('settings-modal-close'),
        saveConfigBtn: document.getElementById('save-config-btn'),
        saveStatus: document.getElementById('save-status'),
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

// Mode Switcher Handler
function switchMode(newMode) {
    state.mode = newMode;
    if (newMode === 'deepsearch') {
        dom.tabDeepSearch.classList.add('active');
        dom.tabResearchMode.classList.remove('active');
        switchPanel(dom.landingPanel);
    } else {
        dom.tabResearchMode.classList.add('active');
        dom.tabDeepSearch.classList.remove('active');
        switchPanel(dom.rmInputPanel);
    }
}

// Setup Event Listeners
function setupEventListeners() {
    // Mode tabs
    dom.tabDeepSearch?.addEventListener('click', () => switchMode('deepsearch'));
    dom.tabResearchMode?.addEventListener('click', () => switchMode('researchmode'));

    // Theme toggle
    dom.themeToggleBtn?.addEventListener('click', toggleTheme);

    // Settings Modal
    dom.settingsBtn?.addEventListener('click', () => dom.settingsModal.style.display = 'flex');
    dom.settingsClose?.addEventListener('click', () => dom.settingsModal.style.display = 'none');
    dom.saveConfigBtn?.addEventListener('click', saveSettingsModal);

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

    dom.planResearchBtn?.addEventListener('click', handlePlanResearch);
    dom.feedbackInput?.addEventListener('input', () => {
        const val = dom.feedbackInput.value.strip ? dom.feedbackInput.value.strip() : dom.feedbackInput.value.trim();
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
    dom.rmExportPdfBtn?.addEventListener('click', handleRMExportPDF);
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

// Save Settings Modal
async function saveSettingsModal() {
    const payload = {
        LLM_BASE_URL: document.getElementById('input-llm-base-url')?.value.trim(),
        LLM_API_KEY: document.getElementById('input-deepseek-key')?.value.trim(),
        TAVILY_API_KEY: document.getElementById('input-tavily-key')?.value.trim(),
        OPENALEX_EMAIL: document.getElementById('input-openalex-email')?.value.trim()
    };

    dom.saveStatus.textContent = 'Saving...';
    try {
        let res = await fetch(`${API_BASE_URL}/health/config`, {
            method: 'POST',
            headers: configHeaders(),
            body: JSON.stringify(payload)
        });
        if (res.status === 401 && await promptForConfigToken()) {
            res = await fetch(`${API_BASE_URL}/health/config`, {
                method: 'POST',
                headers: configHeaders(),
                body: JSON.stringify(payload)
            });
        }
        if (res.ok) {
            dom.saveStatus.textContent = 'Saved successfully!';
            setTimeout(() => dom.settingsModal.style.display = 'none', 1000);
        } else if (res.status === 401 || res.status === 403) {
            localStorage.removeItem('config_api_token');
            const data = await res.json().catch(() => ({}));
            dom.saveStatus.textContent = data.detail || 'Configuration API is locked on this deployment.';
        } else {
            dom.saveStatus.textContent = 'Failed to save settings.';
        }
    } catch (e) {
        dom.saveStatus.textContent = 'Error saving settings.';
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
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    targetPanel.classList.add('active');
}

// Health Check
async function checkBackendHealth() {
    try {
        const res = await fetch(`${API_BASE_URL}/healthz`);
        if (res.ok) {
            dom.backendOfflineBanner.style.display = 'none';
        } else {
            dom.backendOfflineBanner.style.display = 'flex';
        }
    } catch (e) {
        dom.backendOfflineBanner.style.display = 'flex';
    }
}


/* ==========================================================================
   RESEARCH MODE PIPELINE LOGIC & SESSION PERSISTENCE
   ========================================================================== */

function saveRMSession() {
    if (!state.rm.threadId) return;
    try {
        const sessionData = {
            threadId: state.rm.threadId,
            rmState: state.rm,
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

        const res = await fetch(`${API_BASE_URL}/research-mode/result/${session.threadId}`);
        if (!res.ok) {
            if (res.status === 404) {
                clearRMSession();
            }
            return;
        }
        const data = await res.json();
        const values = data.values || {};
        
        state.rm.threadId = session.threadId;
        if (session.rmState) {
            Object.assign(state.rm, session.rmState);
        }
        applyRMStatePayload(values);
        if (data.hitl_checkpoint) state.rm.hitlCheckpoint = data.hitl_checkpoint;
        if (data.status) state.rm.status = data.status;
        if (session.lastSeq !== undefined) state.rm.lastSeq = session.lastSeq;

        // Switch UI to Research Mode tab & workspace panel
        switchMode('researchmode');
        switchPanel(dom.rmWorkspacePanel);

        if (data.is_completed) {
            updateRMPipelineTracker('title', RM_STAGES.map(s => s.id));
            if (dom.rmHitlPanel) dom.rmHitlPanel.style.display = 'none';
            renderRMPaperFinal();
        } else if (data.is_checkpoint || data.hitl_checkpoint) {
            const cp = (data.hitl_checkpoint || 'checkpoint_1').replace(/_(approved|revising)$/, '');
            state.rm.hitlCheckpoint = cp;
            const cpIdx = RM_STAGES.findIndex(s => s.id === cp);
            const completedStages = cpIdx > 0 ? RM_STAGES.slice(0, cpIdx).map(s => s.id) : [];
            updateRMPipelineTracker(cp, completedStages);
            renderRMHitlPanel(cp);
            renderRMPaperLive();
        } else {
            renderRMPaperLive();
        }

        showResumeBanner(data);
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

    if (dom.rmPsInput) dom.rmPsInput.value = '';
    if (dom.rmObjsInput) dom.rmObjsInput.value = '';
    if (dom.rmRqsInput) dom.rmRqsInput.value = '';

    const banner = document.getElementById('rm-resume-banner');
    if (banner) banner.remove();

    if (dom.rmHitlPanel) dom.rmHitlPanel.style.display = 'none';
    if (dom.rmCopyPaperBtn) dom.rmCopyPaperBtn.style.display = 'none';
    if (dom.rmExportPdfBtn) dom.rmExportPdfBtn.style.display = 'none';
    if (dom.rmPaperOutput) dom.rmPaperOutput.innerHTML = `
        <div class="paper-placeholder-state">
            <div class="spinner-ring"></div>
            <p>Academic pipeline executing. Live sections will materialize as agents complete synthesis.</p>
        </div>
    `;

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

function updateRMPipelineTracker(activeStageId, completedStages = []) {
    const hidden = RM_HIDDEN_STAGES[activeStageId];
    const anchoredStageId = hidden ? hidden.anchor : activeStageId;

    RM_STAGES.forEach(stage => {
        const el = document.getElementById(`rm-step-${stage.id}`);
        if (!el) return;

        el.classList.remove('active', 'completed');
        if (completedStages.includes(stage.id)) {
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

        switchPanel(dom.rmWorkspacePanel);
        updateRMPipelineTracker('checkpoint_1', ['scope_definition', 'keyword_extractor']);
        renderRMHitlPanel('checkpoint_1');

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
                <div class="problem-statement-text">${state.rm.problemStatement}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Research Objectives <span class="label-tag">auto-defined</span></label>
                <div class="subtasks-list">
                    ${objectives.map((o, i) => `
                        <div class="subtask-item">
                            <span class="subtask-number">O${i + 1}</span>
                            <span class="subtask-content">${o}</span>
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
                            <span class="subtask-content">${q}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Extracted Academic Keywords (6-10)</label>
                <div class="chips-container">
                    ${(state.rm.keywords || []).map(kw => `<span class="chip active">${kw}</span>`).join('')}
                </div>
            </div>
        `;
    } else if (checkpoint === 'checkpoint_2') {
        dom.rmHitlTitle.textContent = 'Checkpoint 2: Literature Review & Framework Review';
        dom.rmHitlBadge.textContent = 'Checkpoint 2 of 4';

        dom.rmHitlBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">Synthesized Literature Review Snippet</label>
                <div class="problem-statement-text">${(state.rm.literatureReview || '').slice(0, 400)}...</div>
            </div>
            <div class="form-group">
                <label class="form-label">Identified Research Gap</label>
                <div class="problem-statement-text">${state.rm.researchGap}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Proposed Conceptual Framework</label>
                <div class="problem-statement-text">${state.rm.conceptualFramework}</div>
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
                            <span class="subtask-content">${h}</span>
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
                <div class="problem-statement-text">${state.rm.researchDesign}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Data Collection Plan</label>
                <div class="problem-statement-text">${state.rm.dataCollectionPlan}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Data Analysis Plan</label>
                <div class="problem-statement-text">${state.rm.dataAnalysisPlan}</div>
            </div>
        `;
    }
}

async function handleRMApprove(feedback) {
    if (!state.rm.threadId) return;

    dom.rmHitlPanel.style.display = 'none';

    if (activeRMController) activeRMController.abort();
    activeRMController = new AbortController();

    let attempt = 0;
    const maxRetries = 5;
    let isTerminal = false;

    while (attempt <= maxRetries && !isTerminal) {
        try {
            const reqMessage = attempt === 0 ? (feedback || '') : '';
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
                    if (rawEvent.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(rawEvent.slice(6));
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

if (dom.modalCloseBtn) {
    dom.modalCloseBtn.onclick = () => {
        if (dom.paperDetailModal) dom.paperDetailModal.style.display = 'none';
    };
}

function processRMSEEvent(data) {
    if (data.event === 'node_start') {
        updateRMPipelineTracker(data.node);
        appendLogLine(`Node started: ${data.node}`, 'info');
    } else if (data.event === 'node_update') {
        applyRMStatePayload(data.data || {});
        if (data.seq !== undefined) state.rm.lastSeq = data.seq;
        appendLogLine(`Node updated: ${data.node}`, 'success');
        if (data.data && data.data.corpus_stats) updateCorpusStats(data.data.corpus_stats);
        renderRMPaperLive();
        saveRMSession();
    } else if (data.event === 'checkpoint') {
        const cp = (data.hitl_checkpoint || 'checkpoint_1').replace(/_(approved|revising)$/, '');
        state.rm.hitlCheckpoint = cp;
        applyRMStatePayload(data.state);
        if (data.seq !== undefined) state.rm.lastSeq = data.seq;
        appendLogLine(`HITL Checkpoint reached: ${cp}`, 'warn');
        if (data.state && data.state.corpus_stats) updateCorpusStats(data.state.corpus_stats);
        renderRMHitlPanel(cp);
        saveRMSession();
    } else if (data.event === 'completed') {
        applyRMStatePayload(data.state);
        if (data.seq !== undefined) state.rm.lastSeq = data.seq;
        appendLogLine(`Pipeline execution completed!`, 'success');
        if (data.state && data.state.corpus_stats) updateCorpusStats(data.state.corpus_stats);
        updateRMPipelineTracker('title', RM_STAGES.map(s => s.id));
        renderRMPaperFinal();
        saveRMSession();
    } else if (data.event === 'error') {
        appendLogLine(`Pipeline Error: ${data.message}`, 'error');
        showToast(data.message || 'Pipeline error occurred.', 'error');
    }
    return data.event;
}

function renderRMPaperLive() {
    if (dom.rmPaperTitle) dom.rmPaperTitle.textContent = state.rm.title || 'Synthesizing Academic Paper...';
    if (dom.rmPaperOutput) {
        dom.rmPaperOutput.innerHTML = marked.parse(getPaperMarkdown());
    }
}

function renderRMPaperFinal() {
    renderRMPaperLive();
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

async function handlePlanResearch() {
    const query = dom.queryInput.value.trim();
    if (!query) {
        showToast('Please enter a research query.', 'warning');
        return;
    }

    state.query = query;
    dom.approvalQueryDisplay.textContent = `"${query}"`;
    switchPanel(dom.approvalPanel);

    dom.approvalPsText.textContent = 'Generating Problem Statement...';
    dom.approvalSubtasksContainer.innerHTML = '<div class="spinner-ring"></div>';

    try {
        const res = await fetch(`${API_BASE_URL}/research/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: state.query, search_topic: state.searchTopic })
        });
        const data = await res.json();
        if (data.status === 'error') {
            showToast(data.error || 'Failed to create plan.', 'error');
            return;
        }

        state.threadId = data.thread_id;
        state.ps = data.ps;
        state.plan = data.plan || [];
        renderApprovalPanel();

    } catch (e) {
        showToast('Error planning research: ' + e.message, 'error');
    }
}

function renderApprovalPanel() {
    dom.approvalPsText.textContent = state.ps;
    dom.approvalSubtasksContainer.innerHTML = '';
    state.plan.forEach((task, idx) => {
        const item = document.createElement('div');
        item.className = 'subtask-item';
        item.innerHTML = `
            <div class="subtask-number">${idx + 1}</div>
            <div class="subtask-content">${task}</div>
        `;
        dom.approvalSubtasksContainer.appendChild(item);
    });
}

async function handleRevision() {
    const feedback = dom.feedbackInput.value.trim();
    if (!feedback) return;

    dom.approvalSubtasksContainer.innerHTML = '<div class="spinner-ring"></div>';
    await submitPlanApprovalWithMessage(feedback);
}

async function submitPlanApproval() {
    await submitPlanApprovalWithMessage('approve');
}

async function submitPlanApprovalWithMessage(message) {
    if (!state.threadId) return;

    switchPanel(dom.workspacePanel);
    researchTimer.start();

    try {
        const response = await fetch(`${API_BASE_URL}/research/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_id: state.threadId, message: message })
        });

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
                if (rawEvent.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(rawEvent.slice(6));
                        processDeepSearchSSEEvent(data);
                    } catch (e) {}
                }
            }
        }
    } catch (e) {
        showToast('SSE Error: ' + e.message, 'error');
    }
}

function processDeepSearchSSEEvent(data) {
    if (data.event === 'node_start') {
        if (data.node.startsWith('researcher')) {
            state.workers[data.node] = { task: data.task, status: 'running', logs: [] };
            renderWorkers();
        }
    } else if (data.event === 'researcher_search') {
        const wKey = Object.keys(state.workers).find(k => state.workers[k].task === data.task);
        if (wKey) {
            state.workers[wKey].logs.push(data.query);
            renderWorkers();
        }
    } else if (data.event === 'aggregator_token') {
        dom.reportStreamingIndicator.style.display = 'flex';
        state.finalAnswer += data.token;
        dom.reportOutput.innerHTML = marked.parse(state.finalAnswer) + '<span class="streaming-cursor">|</span>';
    } else if (data.event === 'completed') {
        researchTimer.stop();
        dom.reportStreamingIndicator.style.display = 'none';
        state.finalAnswer = data.final_answer || state.finalAnswer;
        dom.reportOutput.innerHTML = marked.parse(state.finalAnswer);
        dom.copyMdBtn.style.display = 'inline-flex';
        dom.downloadMdBtn.style.display = 'inline-flex';
        dom.workspaceNewResearchBtn.style.display = 'inline-flex';
        if (data.citations) renderCitations(data.citations);
    }
}

function renderWorkers() {
    dom.workersListContainer.innerHTML = '';
    Object.entries(state.workers).forEach(([id, w]) => {
        const card = document.createElement('div');
        card.className = 'worker-card';
        card.innerHTML = `
            <div class="worker-header">
                <strong>${id}</strong>
                <span class="worker-status ${w.status}">${w.status}</span>
            </div>
            <div class="worker-task">${w.task}</div>
        `;
        dom.workersListContainer.appendChild(card);
    });
}

function renderCitations(citations) {
    dom.workspaceSourcesContainer.innerHTML = '';
    citations.forEach(url => {
        const card = document.createElement('a');
        card.className = 'source-card';
        card.href = url;
        card.target = '_blank';
        card.innerHTML = `<i data-lucide="link"></i><span>${url}</span>`;
        dom.workspaceSourcesContainer.appendChild(card);
    });
    dom.workspaceSourcesSection.style.display = 'block';
    lucide.createIcons();
}

function resetToLanding() {
    researchTimer.reset();
    state.threadId = null;
    state.finalAnswer = '';
    state.workers = {};
    dom.queryInput.value = '';
    clearRMSession();
    switchPanel(dom.landingPanel);
}

function copyToClipboard(text, btnEl) {
    navigator.clipboard.writeText(text);
    const orig = btnEl.innerHTML;
    btnEl.innerHTML = '<span>Copied!</span>';
    setTimeout(() => btnEl.innerHTML = orig, 2000);
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
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    dom.toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
