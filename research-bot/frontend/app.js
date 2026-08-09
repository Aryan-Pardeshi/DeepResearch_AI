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
const API_BASE_URL = 'http://localhost:8000';
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
        introduction: '',
        abstract: '',
        title: '',
        activeStage: 'keyword_extractor'
    }
};

// Research Mode Pipeline 18 Stages Metadata
const RM_STAGES = [
    { id: 'keyword_extractor', name: '1. Keywords', role: 'extractor' },
    { id: 'checkpoint_1', name: 'HITL Checkpoint 1', hitl: true },
    { id: 'paper_fetcher', name: '2. Paper Fetcher', role: 'fetcher' },
    { id: 'paper_screener', name: '3. Paper Screener', role: 'screener' },
    { id: 'literature_review', name: '4. Lit Review', role: 'synthesizer' },
    { id: 'gap_analysis', name: '5. Gap Analysis', role: 'analyst' },
    { id: 'framework', name: '6. Framework', role: 'architect' },
    { id: 'checkpoint_2', name: 'HITL Checkpoint 2', hitl: true },
    { id: 'hypotheses', name: '7. Hypotheses', role: 'formulator' },
    { id: 'checkpoint_3', name: 'HITL Checkpoint 3', hitl: true },
    { id: 'methodology', name: '8. Methodology', role: 'methodologist' },
    { id: 'checkpoint_4', name: 'HITL Checkpoint 4', hitl: true },
    { id: 'results', name: '9. Results', role: 'synthesizer' },
    { id: 'discussion', name: '10. Discussion', role: 'interpreter' },
    { id: 'implications', name: '11. Implications', role: 'evaluator' },
    { id: 'limitations', name: '12. Limitations', role: 'critic' },
    { id: 'conclusion', name: '13. Conclusion', role: 'summarizer' },
    { id: 'future_scope', name: '14. Future Scope', role: 'visionary' },
    { id: 'references', name: '15. References', role: 'indexer' },
    { id: 'introduction', name: '16. Introduction', role: 'framer' },
    { id: 'abstract', name: '17. Abstract', role: 'summarizer' },
    { id: 'title', name: '18. Title', role: 'finalizer' }
];

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

        toastContainer: document.getElementById('toast-container')
    };
}

// System Environment Setup Gate Check
async function checkConfigGate() {
    try {
        const res = await fetch(`${API_BASE_URL}/config/status`);
        if (!res.ok) return;
        const data = await res.json();
        
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
    dom.rmHitlReviseBtn?.addEventListener('click', () => handleRMApprove(dom.rmHitlFeedbackInput.value));
    dom.rmHitlApproveBtn?.addEventListener('click', () => handleRMApprove('approve'));
    dom.rmCopyPaperBtn?.addEventListener('click', () => copyToClipboard(getPaperMarkdown(), dom.rmCopyPaperBtn));
    dom.rmExportPdfBtn?.addEventListener('click', handleRMExportPDF);
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
        const res = await fetch(`${API_BASE_URL}/config/setup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
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
        const res = await fetch(`${API_BASE_URL}/health/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            dom.saveStatus.textContent = 'Saved successfully!';
            setTimeout(() => dom.settingsModal.style.display = 'none', 1000);
        }
    } catch (e) {
        dom.saveStatus.textContent = 'Error saving settings.';
    }
}

// Theme handling
function initTheme() {
    const theme = localStorage.getItem('deepresearch_theme') || 'dark';
    if (theme === 'light') document.documentElement.classList.add('light-mode');
}

function toggleTheme() {
    document.documentElement.classList.toggle('light-mode');
    const isLight = document.documentElement.classList.contains('light-mode');
    localStorage.setItem('deepresearch_theme', isLight ? 'light' : 'dark');
}

function switchPanel(targetPanel) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    targetPanel.classList.add('active');
}

// Health Check
async function checkBackendHealth() {
    try {
        const res = await fetch(`${API_BASE_URL}/`);
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
   RESEARCH MODE PIPELINE LOGIC
   ========================================================================== */

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
    RM_STAGES.forEach(stage => {
        const el = document.getElementById(`rm-step-${stage.id}`);
        if (!el) return;

        el.classList.remove('active', 'completed');
        if (completedStages.includes(stage.id)) {
            el.classList.add('completed');
        } else if (stage.id === activeStageId) {
            el.classList.add('active');
        }
    });

    if (dom.rmPipelineStatusTag) {
        const current = RM_STAGES.find(s => s.id === activeStageId);
        dom.rmPipelineStatusTag.textContent = current ? `Active: ${current.name}` : 'Pipeline Running';
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

    dom.rmStartBtn.disabled = true;
    dom.rmStartBtn.innerHTML = '<div class="spinner-ring sm"></div><span>Initializing Academic Agents...</span>';

    try {
        const res = await fetch(`${API_BASE_URL}/research-mode/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ problem_statement: ps, research_objectives: objs, research_questions: rqs })
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

        switchPanel(dom.rmWorkspacePanel);
        updateRMPipelineTracker('keyword_extractor', ['keyword_extractor']);
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

    if (checkpoint === 'checkpoint_1') {
        dom.rmHitlTitle.textContent = 'Checkpoint 1: Problem Statement & Keywords Review';
        dom.rmHitlBadge.textContent = 'Checkpoint 1 of 4';

        dom.rmHitlBody.innerHTML = `
            <div class="form-group">
                <label class="form-label">Problem Statement</label>
                <div class="problem-statement-text">${state.rm.problemStatement}</div>
            </div>
            <div class="form-group">
                <label class="form-label">Extracted Academic Keywords (6-10)</label>
                <div class="chips-container">
                    ${state.rm.keywords.map(kw => `<span class="chip active">${kw}</span>`).join('')}
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

    try {
        const response = await fetch(`${API_BASE_URL}/research-mode/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ thread_id: state.rm.threadId, message: feedback || '' }),
            signal: activeRMController.signal
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
                        processRMSEEvent(data);
                    } catch (e) {
                        console.warn('RM SSE parse error:', e);
                    }
                }
            }
        }
    } catch (e) {
        if (e.name !== 'AbortError') {
            showToast('Error streaming Research Mode pipeline: ' + e.message, 'error');
        }
    }
}

function processRMSEEvent(data) {
    if (data.event === 'node_start') {
        updateRMPipelineTracker(data.node);
    } else if (data.event === 'node_update') {
        const out = data.data || {};
        Object.assign(state.rm, {
            literatureReview: out.literature_review || state.rm.literatureReview,
            researchGap: out.research_gap || state.rm.researchGap,
            conceptualFramework: out.conceptual_framework || state.rm.conceptualFramework,
            hypotheses: out.hypotheses || state.rm.hypotheses,
            researchDesign: out.research_design || state.rm.researchDesign,
            dataCollectionPlan: out.data_collection_plan || state.rm.dataCollectionPlan,
            dataAnalysisPlan: out.data_analysis_plan || state.rm.dataAnalysisPlan,
            results: out.results || state.rm.results,
            discussion: out.discussion || state.rm.discussion,
            implications: out.implications || state.rm.implications,
            limitations: out.limitations || state.rm.limitations,
            conclusion: out.conclusion || state.rm.conclusion,
            futureScope: out.future_scope || state.rm.futureScope,
            references: out.references || state.rm.references,
            introduction: out.introduction || state.rm.introduction,
            abstract: out.abstract || state.rm.abstract,
            title: out.title || state.rm.title
        });
        renderRMPaperLive();
    } else if (data.event === 'checkpoint') {
        const cp = data.hitl_checkpoint || 'checkpoint_1';
        state.rm.hitlCheckpoint = cp;
        if (data.state) Object.assign(state.rm, data.state);
        renderRMHitlPanel(cp);
    } else if (data.event === 'completed') {
        if (data.state) Object.assign(state.rm, data.state);
        updateRMPipelineTracker('title', RM_STAGES.map(s => s.id));
        renderRMPaperFinal();
    } else if (data.event === 'error') {
        showToast(data.message || 'Pipeline error occurred.', 'error');
    }
}

function renderRMPaperLive() {
    if (dom.rmPaperTitle) dom.rmPaperTitle.textContent = state.rm.title || 'Synthesizing Academic Paper...';
    if (dom.rmPaperOutput) {
        dom.rmPaperOutput.innerHTML = marked.parse(getPaperMarkdown());
    }
}

function renderRMPaperFinal() {
    renderRMPaperLive();
    dom.rmCopyPaperBtn.style.display = 'inline-flex';
    dom.rmExportPdfBtn.style.display = 'inline-flex';
    showToast('Academic Paper Synthesis Completed!', 'success');
}

function getPaperMarkdown() {
    const s = state.rm;
    let md = `# ${s.title || 'Academic Research Report'}\n\n`;
    if (s.abstract) md += `## Abstract\n${s.abstract}\n\n`;
    if (s.introduction) md += `## 1. Introduction\n${s.introduction}\n\n`;
    if (s.literatureReview) md += `## 2. Literature Review\n${s.literatureReview}\n\n`;
    if (s.conceptualFramework) md += `## 3. Research Gap & Conceptual Framework\n### Research Gap\n${s.researchGap}\n\n### Conceptual Framework\n${s.conceptualFramework}\n\n`;
    if (s.hypotheses && s.hypotheses.length) md += `## 4. Hypotheses\n${s.hypotheses.map((h, i) => `- **H${i+1}**: ${h}`).join('\n')}\n\n`;
    if (s.researchDesign) md += `## 5. Methodology\n**Design**: ${s.researchDesign}\n\n**Data Collection**: ${s.dataCollectionPlan}\n\n**Data Analysis**: ${s.dataAnalysisPlan}\n\n`;
    if (s.results) md += `## 6. Results\n${s.results}\n\n`;
    if (s.discussion) md += `## 7. Discussion\n${s.discussion}\n\n`;
    if (s.implications) md += `## 8. Implications\n${s.implications}\n\n`;
    if (s.limitations) md += `## 9. Limitations\n${s.limitations}\n\n`;
    if (s.conclusion) md += `## 10. Conclusion & Future Scope\n${s.conclusion}\n\n### Future Directions\n${Array.isArray(s.futureScope) ? s.futureScope.map(f => `- ${f}`).join('\n') : s.futureScope}\n\n`;
    if (s.references && s.references.length) md += `## References\n${s.references.map(r => `- ${r}`).join('\n')}\n\n`;
    return md;
}

async function handleRMExportPDF() {
    if (!state.rm.threadId) return;
    try {
        const res = await fetch(`${API_BASE_URL}/research-mode/export/${state.rm.threadId}`, { method: 'POST' });
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `academic_paper_${state.rm.threadId.slice(0, 8)}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } else {
            showToast('Failed to export PDF.', 'error');
        }
    } catch (e) {
        showToast('Error exporting PDF: ' + e.message, 'error');
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
