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
const API_BASE_URL = 'http://127.0.0.1:8000';

// Activity Monitor — detects stalls in SSE/researcher activity
const activityMonitor = {
    lastEventTime: Date.now(),
    warningsShown: {},
    checkTimer: null,
    STALL_THRESHOLD: 45000,

    markActivity() {
        this.lastEventTime = Date.now();
    },

    start() {
        this.stop();
        this.lastEventTime = Date.now();
        this.warningsShown = {};
        this.checkTimer = setInterval(() => {
            const elapsed = Date.now() - this.lastEventTime;
            if (elapsed > this.STALL_THRESHOLD && state.status === 'researching') {
                const bucket = Math.floor(elapsed / 30000) * 30;
                if (!this.warningsShown[bucket]) {
                    this.warningsShown[bucket] = true;
                    const stuckResearchers = Object.entries(state.workers)
                        .filter(([, w]) => w.status === 'running')
                        .map(([task]) => task);
                    const msg = `No activity for ${Math.round(elapsed / 1000)}s. Stuck researchers: ${stuckResearchers.join(', ') || 'unknown'}`;
                    showToast(msg);
                    dom.statusText.innerText = `⚠ ${Math.round(elapsed / 1000)}s stall — ${stuckResearchers.length} researchers stuck`;
                }
            }
        }, 10000);
    },

    stop() {
        if (this.checkTimer) {
            clearInterval(this.checkTimer);
            this.checkTimer = null;
        }
    }
};

// Application State
const state = {
    threadId: null,
    status: 'idle', // 'idle' | 'validating' | 'planning' | 'awaiting_approval' | 'researching' | 'aggregating' | 'completed' | 'error'
    query: '',
    searchTopic: ['all'], // array of selected topics: 'all', 'news', 'academic', 'finance', 'patent'
    ps: '',
    plan: [],
    workers: {}, // Maps query -> { id, status: 'pending'|'running'|'completed', result, citations: [] }
    finalAnswer: '',
    citations: [],
    error: null
};

// DOM Cache
const dom = {
    // Header
    statusDot: document.getElementById('app-status-dot'),
    statusText: document.getElementById('app-status-text'),
    
    // Panels
    landingPanel: document.getElementById('landing-panel'),
    approvalPanel: document.getElementById('approval-panel'),
    workspacePanel: document.getElementById('workspace-panel'),
    
    // Views - Landing
    queryInput: document.getElementById('query-input'),
    filterChips: document.getElementById('filter-chips'),
    planBtn: document.getElementById('plan-research-btn'),
    
    // Views - Approval
    approvalQueryDisplay: document.getElementById('approval-query-display'),
    approvalPsText: document.getElementById('approval-ps-text'),
    approvalSubtasksContainer: document.getElementById('approval-subtasks-container'),
    feedbackInput: document.getElementById('feedback-input'),
    submitFeedbackBtn: document.getElementById('submit-feedback-btn'),
    approvePlanBtn: document.getElementById('approve-plan-btn'),
    
    // Views - Workspace
    workersListContainer: document.getElementById('workers-list-container'),
    workspaceProgressBar: document.getElementById('workspace-progress-bar'),
    reportOutput: document.getElementById('report-output'),
    reportStreamingIndicator: document.getElementById('report-streaming-indicator'),
    workspaceSourcesSection: document.getElementById('workspace-sources-section'),
    workspaceSourcesContainer: document.getElementById('workspace-sources-container'),
    
    // Toast Container
    toastContainer: document.getElementById('toast-container'),
    
    // New Research
    newResearchBtn: document.getElementById('new-research-btn')
};

const STORAGE_KEY = 'deepresearch_session';

function saveSession() {
    try {
        const data = {
            threadId: state.threadId,
            status: state.status,
            query: state.query,
            searchTopic: state.searchTopic,
            ps: state.ps,
            plan: state.plan,
            finalAnswer: state.finalAnswer,
            citations: state.citations
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        dom.newResearchBtn.style.display = state.threadId ? 'flex' : 'none';
    } catch (e) {}
}

function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
    state.threadId = null;
    state.status = 'idle';
    state.query = '';
    state.plan = [];
    state.workers = {};
    state.finalAnswer = '';
    state.citations = [];
    state.ps = '';
}

function restoreSession() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const saved = JSON.parse(raw);
        if (!saved.threadId) return;

        state.threadId = saved.threadId;
        state.query = saved.query || '';
        state.searchTopic = saved.searchTopic || ['all'];
        state.ps = saved.ps || '';
        state.plan = saved.plan || [];
        state.finalAnswer = saved.finalAnswer || '';
        state.citations = saved.citations || [];

        state.workers = {};
        state.plan.forEach(task => {
            state.workers[task] = { id: null, status: 'pending', result: null, citations: [] };
        });

        dom.queryInput.value = state.query;

        if (saved.status === 'awaiting_approval') {
            renderApprovalPanel();
            setStatus('awaiting_approval');
            showPanel('approval-panel');
        } else if (saved.status === 'completed') {
            renderWorkers();
            renderReportFinal();
            renderCitations();
            setStatus('completed');
            showPanel('workspace-panel');
        }
    } catch (e) {}
}

// Initialize Icons
document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initEventListeners();
    checkBackendHealth().then(ok => {
        if (ok) restoreSession();
        else startHealthPolling();
    });
});

// Backend Health Check
async function checkBackendHealth() {
    const banner = document.getElementById('backend-offline-banner');
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        const response = await fetch(`${API_BASE_URL}/`, {
            method: 'GET',
            signal: controller.signal
        });
        clearTimeout(timeout);
        if (!response.ok) throw new Error('Not healthy');
        banner.style.display = 'none';
        setStatus('idle');
        dom.statusText.innerText = 'Ready for query';
        return true;
    } catch {
        banner.style.display = 'flex';
        setStatus('error');
        dom.statusText.innerText = 'Backend Offline';
        return false;
    }
}

// Poll until backend is reachable
let healthCheckInterval = null;
function startHealthPolling() {
    if (healthCheckInterval) return;
    healthCheckInterval = setInterval(async () => {
        const ok = await checkBackendHealth();
        if (ok) {
            clearInterval(healthCheckInterval);
            healthCheckInterval = null;
        }
    }, 5000);
}

// Event Listeners Binding
function initEventListeners() {
    // Tavily Filter Chips Multi-select
    dom.filterChips.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip');
        if (!chip) return;
        
        const topic = chip.dataset.topic;
        
        if (topic === 'all') {
            // Select 'all', clear others
            state.searchTopic = ['all'];
            Array.from(dom.filterChips.children).forEach(el => {
                if (el.dataset.topic === 'all') el.classList.add('active');
                else el.classList.remove('active');
            });
        } else {
            // Select other chips, remove 'all'
            const allChip = dom.filterChips.querySelector('[data-topic="all"]');
            allChip.classList.remove('active');
            state.searchTopic = state.searchTopic.filter(t => t !== 'all');
            
            if (chip.classList.contains('active')) {
                chip.classList.remove('active');
                state.searchTopic = state.searchTopic.filter(t => t !== topic);
                // If nothing selected, default back to 'all'
                if (state.searchTopic.length === 0) {
                    state.searchTopic = ['all'];
                    allChip.classList.add('active');
                }
            } else {
                chip.classList.add('active');
                state.searchTopic.push(topic);
            }
        }
    });

    // Start Research / Plan Button
    dom.planBtn.addEventListener('click', handlePlanResearch);
    
    // Suggest Revision Button
    dom.submitFeedbackBtn.addEventListener('click', handleRevision);
    
    // Approve Plan Button
    dom.approvePlanBtn.addEventListener('click', () => {
        submitPlanApproval('Looks good, run the research!');
    });
    
    // Toggle approve/revision buttons based on feedback input
    dom.feedbackInput.addEventListener('input', toggleFeedbackButtons);
    
    // New Research Button
    dom.newResearchBtn.addEventListener('click', () => {
        activityMonitor.stop();
        clearSession();
        dom.queryInput.value = '';
        resetLandingControls();
        dom.reportOutput.innerHTML = '';
        dom.workspaceSourcesContainer.innerHTML = '';
        dom.workspaceSourcesSection.style.display = 'none';
        dom.newResearchBtn.style.display = 'none';
        setStatus('idle');
        showPanel('landing-panel');
    });
}

function toggleFeedbackButtons() {
    const hasText = dom.feedbackInput.value.trim().length > 0;
    dom.submitFeedbackBtn.style.display = hasText ? '' : 'none';
    dom.approvePlanBtn.style.display = hasText ? 'none' : '';
}

// Handle Revision Submission (stays on approval panel)
async function handleRevision() {
    const feedback = dom.feedbackInput.value.trim();
    if (!feedback) {
        showToast('Please type your revisions request in the console.');
        return;
    }

    const btn = dom.submitFeedbackBtn;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<i data-lucide="loader-2" class="revising-spinner" style="width: 16px; height: 16px;"></i><span>Revising...</span>';
    btn.disabled = true;
    dom.approvePlanBtn.disabled = true;
    dom.feedbackInput.disabled = true;
    dom.approvalPsText.closest('.card').classList.add('revising');
    lucide.createIcons();

    try {
        const response = await fetch(`${API_BASE_URL}/research/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                thread_id: state.threadId,
                message: feedback
            })
        });

        if (!response.ok) {
            throw new Error(`Server returned code ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop();

            for (const part of parts) {
                if (part.startsWith('data: ')) {
                    const dataStr = part.slice(6).trim();
                    if (dataStr) {
                        try {
                            const data = JSON.parse(dataStr);
                            handleSSEEvent(data, true);
                        } catch (e) {
                            console.error('Failed to parse SSE data stream packet:', e);
                        }
                    }
                }
            }
        }
    } catch (e) {
        showToast(`Revision request failed: ${e.message}`);
        setStatus('error');
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
        dom.approvePlanBtn.disabled = false;
        dom.feedbackInput.disabled = false;
        dom.approvalPsText.closest('.card').classList.remove('revising');
        lucide.createIcons();
    }
}

// Show Panel Helper
function showPanel(panelId) {
    dom.landingPanel.classList.remove('active');
    dom.approvalPanel.classList.remove('active');
    dom.workspacePanel.classList.remove('active');
    
    document.getElementById(panelId).classList.add('active');
}

// Update Status Badge Helper
function setStatus(status) {
    state.status = status;
    
    // Reset status badge classes
    dom.statusDot.className = 'status-dot';
    
    let text = 'Ready for query';
    
    switch (status) {
        case 'idle':
            text = 'Ready for query';
            break;
        case 'validating':
            dom.statusDot.classList.add('planning');
            text = 'Validating query...';
            break;
        case 'planning':
            dom.statusDot.classList.add('planning');
            text = 'Designing research plan...';
            break;
        case 'awaiting_approval':
            dom.statusDot.classList.add('planning');
            text = 'Awaiting design review';
            break;
        case 'researching':
            dom.statusDot.classList.add('researching');
            text = 'Parallel researchers active';
            break;
        case 'aggregating':
            dom.statusDot.classList.add('researching');
            text = 'Synthesizing report...';
            break;
        case 'completed':
            text = 'Research completed';
            break;
        case 'error':
            dom.statusDot.classList.add('error');
            text = 'Execution error';
            break;
    }
    
    dom.statusText.innerText = text;
}

// Show Toast Error Notification
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <i data-lucide="alert-triangle" class="toast-icon" style="width: 20px; height: 20px;"></i>
        <span class="toast-message">${message}</span>
    `;
    dom.toastContainer.appendChild(toast);
    lucide.createIcons();
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Action: POST to Start Research
async function handlePlanResearch() {
    const query = dom.queryInput.value.trim();
    if (!query) {
        showToast('Please type a research query first.');
        return;
    }
    
    clearSession();
    state.query = query;
    setStatus('validating');
    
    // Lock controls
    dom.queryInput.disabled = true;
    dom.planBtn.disabled = true;
    dom.planBtn.querySelector('span').innerText = 'Validating...';
    
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 15000);
        const response = await fetch(`${API_BASE_URL}/research/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: state.query,
                search_topic: state.searchTopic
            }),
            signal: controller.signal
        });
        clearTimeout(timeout);
        
        if (!response.ok) {
            throw new Error(`Server returned code ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'error') {
            showToast(data.error || 'Query validation failed. Please provide a specific topic.');
            resetLandingControls();
            setStatus('error');
            return;
        }
        
        // Save plan data
        state.threadId = data.thread_id;
        state.ps = data.ps || '';
        state.plan = data.plan || [];
        
        // Setup initial workers list
        state.workers = {};
        state.plan.forEach(task => {
            state.workers[task] = {
                id: null,
                status: 'pending',
                result: null,
                citations: []
            };
        });
        
        // Render View
        renderApprovalPanel();
        setStatus('awaiting_approval');
        showPanel('approval-panel');
        saveSession();
        
    } catch (e) {
        showToast(`Failed to establish API connection: ${e.message}`);
        resetLandingControls();
        setStatus('error');
    }
}

function resetLandingControls() {
    dom.queryInput.disabled = false;
    dom.planBtn.disabled = false;
    dom.planBtn.querySelector('span').innerText = 'Plan Research';
}

// Render Approval Screen
function renderApprovalPanel() {
    dom.approvalQueryDisplay.innerText = `"${state.query}"`;
    dom.approvalPsText.innerText = state.ps;
    
    dom.approvalSubtasksContainer.innerHTML = '';
    state.plan.forEach((task, index) => {
        const item = document.createElement('div');
        item.className = 'subtask-item';
        item.innerHTML = `
            <div class="subtask-number">${index + 1}</div>
            <div class="subtask-content">${task}</div>
        `;
        dom.approvalSubtasksContainer.appendChild(item);
    });
    
    // Clear feedback input
    dom.feedbackInput.value = '';
    toggleFeedbackButtons();
}

// Action: Approve & Stream SSE
async function submitPlanApproval(feedbackMessage) {
    setStatus('researching');
    
    // If we're executing, initialize Workspace Panel state
    dom.reportOutput.innerHTML = '';
    dom.workspaceProgressBar.classList.remove('active');
    dom.reportStreamingIndicator.style.display = 'none';
    dom.workspaceSourcesSection.style.display = 'none';
    dom.workspaceSourcesContainer.innerHTML = '';
    state.finalAnswer = '';
    state.citations = [];
    
    // Render initial workspace workers sidebar
    renderWorkers();
    showPanel('workspace-panel');
    activityMonitor.start();
    
    // Clear controls on approval panel
    dom.feedbackInput.value = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/research/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                thread_id: state.threadId,
                message: feedbackMessage
            })
        });
        
        if (!response.ok) {
            throw new Error(`Server returned code ${response.status}: ${response.statusText}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop();
            
            for (const part of parts) {
                if (part.startsWith('data: ')) {
                    const dataStr = part.slice(6).trim();
                    if (dataStr) {
                        try {
                            const data = JSON.parse(dataStr);
                            handleSSEEvent(data);
                        } catch (e) {
                            console.error('Failed to parse SSE data stream packet:', e);
                        }
                    }
                }
            }
        }
        
    } catch (e) {
        showToast(`SSE Connection broken: ${e.message}`);
        setStatus('error');
        activityMonitor.stop();
    }
}

// SSE Events Dispatcher
function handleSSEEvent(data, isRevision = false) {
    console.log("SSE Event Received:", data);
    activityMonitor.markActivity();
    
    switch (data.event) {
        case 'resume':
            if (isRevision) {
                setStatus('planning');
            } else {
                setStatus('researching');
            }
            break;
            
        case 'node_start':
            const workerNode = data.node;
            const workerTask = data.task;
            
            // Map node_start for research workers
            if (workerNode.startsWith('researcher_') && workerTask) {
                // Transition to workspace if still on approval panel
                if (!dom.workspacePanel.classList.contains('active')) {
                    dom.reportOutput.innerHTML = '';
                    dom.workspaceProgressBar.classList.remove('active');
                    dom.reportStreamingIndicator.style.display = 'none';
                    dom.workspaceSourcesSection.style.display = 'none';
                    dom.workspaceSourcesContainer.innerHTML = '';
                    state.finalAnswer = '';
                    state.citations = [];
                    renderWorkers();
                    showPanel('workspace-panel');
                    dom.feedbackInput.value = '';
                    toggleFeedbackButtons();
                }
                if (state.workers[workerTask]) {
                    state.workers[workerTask].id = workerNode;
                    state.workers[workerTask].status = 'running';
                    renderWorkers();
                }
            } else if (workerNode === 'aggregator') {
                setStatus('aggregating');
                dom.workspaceProgressBar.classList.add('active');
                dom.reportStreamingIndicator.style.display = 'flex';
            } else if (workerNode === 'planner') {
                setStatus('planning');
            }
            break;
            
        case 'node_update':
            const updateNode = data.node;
            const updateTask = data.task;
            const updateData = data.data;
            
            if (updateNode.startsWith('researcher_') && updateTask && updateData) {
                if (state.workers[updateTask]) {
                    state.workers[updateTask].status = 'completed';
                    state.workers[updateTask].result = updateData.results ? updateData.results[0] : '';
                    state.workers[updateTask].citations = updateData.citations || [];
                    renderWorkers();
                }
            }
            break;
            
        case 'aggregator_token':
            // Stream token to final report
            state.finalAnswer += data.token;
            renderReportStreaming();
            dom.reportOutput.closest('.report-container').scrollTop = dom.reportOutput.closest('.report-container').scrollHeight;
            saveSession();
            break;
            
        case 'completed':
            setStatus('completed');
            state.finalAnswer = data.final_answer || '';
            state.citations = data.citations || [];
            
            dom.workspaceProgressBar.classList.remove('active');
            dom.reportStreamingIndicator.style.display = 'none';
            activityMonitor.stop();
            
            // Render final markdown and citations
            renderReportFinal();
            renderCitations();
            saveSession();
            break;
            
        case 'awaiting_approval':
            // The plan classification looped back due to feedback revision
            state.plan = data.plan || [];
            state.ps = data.ps || '';
            
            // Reinitialize workers dictionary
            state.workers = {};
            state.plan.forEach(task => {
                state.workers[task] = {
                    id: null,
                    status: 'pending',
                    result: null,
                    citations: []
                };
            });
            
            renderApprovalPanel();
            setStatus('awaiting_approval');
            showPanel('approval-panel');
            activityMonitor.stop();
            saveSession();
            break;
            
        case 'error':
            showToast(`Execution failure reported by graph: ${data.message}`);
            setStatus('error');
            dom.reportStreamingIndicator.style.display = 'none';
            dom.workspaceProgressBar.classList.remove('active');
            activityMonitor.stop();
            break;
    }
}

// Render Workers Sidebar
function renderWorkers() {
    dom.workersListContainer.innerHTML = '';
    
    state.plan.forEach((task, index) => {
        const worker = state.workers[task] || { status: 'pending', citations: [] };
        
        const card = document.createElement('div');
        card.className = `worker-card ${worker.status}`;
        
        let statusIcon = '<i data-lucide="circle-dashed" class="worker-status-icon pending" style="width: 18px; height: 18px;"></i>';
        let detailText = 'Queue pending...';
        
        if (worker.status === 'running') {
            statusIcon = '<i data-lucide="loader-2" class="worker-status-icon running" style="width: 18px; height: 18px;"></i>';
            detailText = 'Retrieving web insights...';
        } else if (worker.status === 'completed') {
            statusIcon = '<i data-lucide="check-circle" class="worker-status-icon completed" style="width: 18px; height: 18px;"></i>';
            detailText = `<span class="worker-search-count"><i data-lucide="link-2" style="width: 12px; height: 12px;"></i> ${worker.citations.length} sources found</span>`;
        }
        
        card.innerHTML = `
            <div class="worker-header">
                <span class="worker-title">${task}</span>
                ${statusIcon}
            </div>
            <div class="worker-details">
                <span>Researcher #${index + 1}</span>
                <span>•</span>
                <span>${detailText}</span>
            </div>
            <div class="worker-card-toggle" data-index="${index}">
                <span>View Findings</span>
                <i data-lucide="chevron-down" style="width: 12px; height: 12px;"></i>
            </div>
            <div class="worker-preview-content" id="worker-preview-${index}">
                ${worker.result || ''}
            </div>
        `;
        
        dom.workersListContainer.appendChild(card);
    });
    
    // Bind Worker toggles
    dom.workersListContainer.querySelectorAll('.worker-card-toggle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = btn.dataset.index;
            const preview = document.getElementById(`worker-preview-${index}`);
            const icon = btn.querySelector('[data-lucide]');
            
            if (preview.classList.contains('expanded')) {
                preview.classList.remove('expanded');
                btn.querySelector('span').innerText = 'View Findings';
                icon.style.transform = 'rotate(0deg)';
            } else {
                preview.classList.add('expanded');
                btn.querySelector('span').innerText = 'Hide Findings';
                icon.style.transform = 'rotate(180deg)';
            }
        });
    });
    
    lucide.createIcons();
}

// Render Streaming Text
function renderReportStreaming() {
    // Basic Markdown streaming view (append a blinking cursor)
    const cursor = '<span class="streaming-cursor">|</span>';
    dom.reportOutput.innerHTML = marked.parse(state.finalAnswer) + cursor;
}

// Render Final Report
function renderReportFinal() {
    dom.reportOutput.innerHTML = marked.parse(state.finalAnswer);
}

// Render Citations
function renderCitations() {
    if (!state.citations || state.citations.length === 0) {
        dom.workspaceSourcesSection.style.display = 'none';
        return;
    }
    
    dom.workspaceSourcesContainer.innerHTML = '';
    
    // Deduplicate citations
    const uniqueCitations = [...new Set(state.citations)];
    
    uniqueCitations.forEach(url => {
        let domain = 'Web Source';
        try {
            const urlObj = new URL(url);
            domain = urlObj.hostname.replace('www.', '');
        } catch (e) {}
        
        const card = document.createElement('a');
        card.className = 'source-card';
        card.href = url;
        card.target = '_blank';
        card.innerHTML = `
            <div class="source-icon">
                <i data-lucide="globe" style="width: 16px; height: 16px;"></i>
            </div>
            <div class="source-info">
                <span class="source-domain">${domain}</span>
                <span class="source-url">${url}</span>
            </div>
        `;
        dom.workspaceSourcesContainer.appendChild(card);
    });
    
    dom.workspaceSourcesSection.style.display = 'block';
    lucide.createIcons();
}
