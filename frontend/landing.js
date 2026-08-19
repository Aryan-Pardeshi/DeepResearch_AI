/* ==========================================================================
   DEEPRESEARCH MARKETING LANDING PAGE LOGIC
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initGitHubStars();
    initInspectorTabs();
    initSmoothScroll();
    initMobileNav();
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
    }
});

/* ==========================================================================
   1. LIVE GITHUB STARS FETCHER & CACHE
   ========================================================================== */
const GITHUB_REPO_API = 'https://api.github.com/repos/Aryan-Pardeshi/DeepResearch_AI';
const GITHUB_STARS_CACHE_KEY = 'deepresearch_github_stars';
const GITHUB_STARS_CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour

async function initGitHubStars() {
    const starBadges = document.querySelectorAll('.gh-star-count-badge');
    if (!starBadges.length) return;

    function renderStarCount(count) {
        const formatted = count >= 1000 ? `${(count / 1000).toFixed(1)}k` : String(count);
        starBadges.forEach(badge => {
            badge.textContent = `★ ${formatted}`;
            badge.style.display = 'inline-block';
        });
    }

    // 1. Check local cache first
    try {
        const cached = localStorage.getItem(GITHUB_STARS_CACHE_KEY);
        if (cached) {
            const parsed = JSON.parse(cached);
            if (parsed && typeof parsed.count === 'number' && (Date.now() - (parsed.timestamp || 0)) < GITHUB_STARS_CACHE_TTL_MS) {
                renderStarCount(parsed.count);
                return;
            }
        }
    } catch (e) {
        console.warn('LocalStorage error reading GitHub stars cache:', e);
    }

    // 2. Fetch live count from GitHub API
    try {
        const response = await fetch(GITHUB_REPO_API);
        if (response.ok) {
            const data = await response.json();
            if (data && typeof data.stargazers_count === 'number') {
                renderStarCount(data.stargazers_count);
                try {
                    localStorage.setItem(GITHUB_STARS_CACHE_KEY, JSON.stringify({
                        count: data.stargazers_count,
                        timestamp: Date.now()
                    }));
                } catch (e) {
                    // Safe ignore
                }
            }
        }
    } catch (e) {
        console.warn('GitHub API rate limit or network issue:', e);
    }
}

/* ==========================================================================
   2. THEME CONTROLLER (SYNCED WITH WORKSPACE)
   ========================================================================== */
function initTheme() {
    const savedTheme = localStorage.getItem('deepresearch_theme') || 'dark';
    const isLight = savedTheme === 'light';
    document.documentElement.classList.toggle('light-mode', isLight);
    updateThemeToggleIcons(isLight);

    const themeBtn = document.getElementById('theme-toggle-btn');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const currentlyLight = document.documentElement.classList.toggle('light-mode');
            localStorage.setItem('deepresearch_theme', currentlyLight ? 'light' : 'dark');
            updateThemeToggleIcons(currentlyLight);
        });
    }
}

function updateThemeToggleIcons(isLight) {
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (!themeBtn) return;
    themeBtn.innerHTML = isLight 
        ? '<i data-lucide="sun" style="width: 17px; height: 17px;"></i>' 
        : '<i data-lucide="moon" style="width: 17px; height: 17px;"></i>';
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons();
    }
}

/* ==========================================================================
   3. HERO WORKFLOW & OUTPUT INSPECTOR TABS
   ========================================================================== */
function initInspectorTabs() {
    const tabButtons = document.querySelectorAll('.inspector-tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            tabButtons.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const targetPane = document.getElementById(`tab-pane-${targetTab}`);
            if (targetPane) {
                targetPane.classList.add('active');
            }

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        });
    });
}

/* ==========================================================================
   4. SMOOTH SCROLL FOR IN-PAGE ANCHORS
   ========================================================================== */
function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (!targetId || targetId === '#') return;
            const targetEl = document.querySelector(targetId);
            if (targetEl) {
                e.preventDefault();
                const headerOffset = 80;
                const elementPosition = targetEl.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/* ==========================================================================
   5. MOBILE NAVIGATION
   ========================================================================== */
function initMobileNav() {
    const toggleBtn = document.getElementById('mobile-nav-toggle');
    const navMenu = document.getElementById('nav-menu');

    if (toggleBtn && navMenu) {
        toggleBtn.addEventListener('click', () => {
            const isOpened = navMenu.classList.toggle('mobile-open');
            toggleBtn.innerHTML = isOpened 
                ? '<i data-lucide="x" style="width: 20px; height: 20px;"></i>' 
                : '<i data-lucide="menu" style="width: 20px; height: 20px;"></i>';
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        });
    }
}
