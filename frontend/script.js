/**
 * ═══════════════════════════════════════════════
 * SkillForge Game Engine v4.0
 * Production-grade gamified coding platform
 * ═══════════════════════════════════════════════
 */

const API = '/api/v1';

// ── Global Game State ──
const state = {
    sessionId: null,       // Browser session for guest fallback
    token: null,           // JWT Token
    gameSessionId: null,   // Active game session ID from Django
    currentLevel: null,    // Current level number being played
    activeDomain: 'dsa',   // Selected Domain
    levels: [],
    user: { lives: 3, coins: 1000, xp: 0, username: 'Guest' },
    timerInterval: null,
    timeRemaining: 0,
    originalCode: '',      // For reset button
    initializing: false,
};

// ═══════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    initGuestSession();
    setupEditorLineNumbers();
    updateTheme(); // Initial theme apply
    await bootGame();
});

function initGuestSession() {
    state.sessionId = localStorage.getItem('skillforge_sid');
    if (!state.sessionId) {
        state.sessionId = 'sf_' + crypto.randomUUID().replace(/-/g, '').slice(0, 16);
        localStorage.setItem('skillforge_sid', state.sessionId);
    }
}

async function apiFetch(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'X-Session-ID': state.sessionId,
        ...options.headers,
    };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    try {
        const res = await fetch(url, { ...options, headers });
        return res;
    } catch (err) {
        console.error('API Error:', err);
        throw err;
    }
}

async function waitForDomainReady(domain, maxMs = 600000) {
    const start = Date.now();
    const el = document.getElementById('loading-status');
    while (Date.now() - start < maxMs) {
        const r = await apiFetch(`${API}/domain/readiness/?domain=${encodeURIComponent(domain)}`);
        if (!r.ok) break;
        const j = await r.json();
        if (el) {
            el.textContent = `Loading ${String(domain).toUpperCase()} challenges: ${j.tasks_ready}/${j.target}...`;
        }
        if (j.ready) return true;
        await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    return false;
}

/** Ensures 100 tasks exist for domain: starts server fill if needed, then polls readiness. */
async function ensureDomainPrepared(domain) {
    const maxWait = 600000;
    const el = document.getElementById('loading-status');
    const r = await apiFetch(`${API}/domain/readiness/?domain=${encodeURIComponent(domain)}`);
    if (!r.ok) {
        if (el) el.textContent = 'Could not check domain readiness. Opening map...';
        return false;
    }
    const j = await r.json();
    if (j.ready) return true;
    if (el) el.textContent = `Preparing ${String(domain).toUpperCase()} (0/${j.target})...`;
    const pr = await apiFetch(`${API}/domain/set/`, {
        method: 'POST',
        body: JSON.stringify({ domain }),
    });
    if (!pr.ok) {
        if (el) el.textContent = 'Waiting for challenges to generate...';
        return waitForDomainReady(domain, maxWait);
    }
    return waitForDomainReady(domain, maxWait);
}

async function bootGame() {
    state.token = localStorage.getItem('skillforge_token');
    const savedDomain = localStorage.getItem('skillforge_domain');
    if (savedDomain) state.activeDomain = savedDomain;
    try {
        showLoading(true);
        const st = document.getElementById('loading-status');
        if (st) st.textContent = 'Connecting...';
        if (state.token) {
            await loadProfile(true);
        } else {
            await loadProfile(false);
        }
        if (state.user && state.user.selected_domain) {
            state.activeDomain = state.user.selected_domain;
            localStorage.setItem('skillforge_domain', state.activeDomain);
        } else if (state.token && !state.user.selected_domain) {
            // New user, no domain selected - redirect to selection page
            window.location.href = '/domain-selection/';
            return;
        }
        const ok = await ensureDomainPrepared(state.activeDomain);
        if (!ok) {
            showToast('Some challenges are still generating — you can play available levels.', 'info');
        }
        await loadLevels();
        showLoading(false);
        showView('map');
    } catch (err) {
        showLoading(false);
        showToast('Connection error. Retrying...', 'error');
        setTimeout(bootGame, 3000);
    }
}

// ═══════════════════════════════════════════════
// PROFILE & HUD
// ═══════════════════════════════════════════════

async function loadProfile(isAuth = false) {
    try {
        const url = isAuth ? `${API}/auth/me/` : `${API}/user/profile/`;
        const res = await apiFetch(url);
        if (res.ok) {
            const data = await res.json();
            const old = { ...state.user };
            state.user = { ...state.user, ...data };
            if (data.selected_domain) {
                state.activeDomain = data.selected_domain;
                localStorage.setItem('skillforge_domain', data.selected_domain);
            }
            updateHUD(old);
            if (isAuth) {
                document.getElementById('btn-login-hud').innerHTML = `<i class="fas fa-user-circle"></i> ${data.username}`;
            }
        }
    } catch (e) {
        console.warn('Profile load failed');
    }
}

function updateHUD(oldState = null) {
    const livesEl = document.getElementById('hud-lives');
    const coinsEl = document.getElementById('hud-coins');
    const xpEl = document.getElementById('hud-xp');

    if (livesEl) livesEl.textContent = state.user.lives;
    if (coinsEl) coinsEl.textContent = state.user.coins;
    if (xpEl) xpEl.textContent = state.user.xp;

    // Bounce animation on change
    if (oldState) {
        if (oldState.lives !== state.user.lives) bounceEl('hud-lives-badge');
        if (oldState.coins !== state.user.coins) {
            bounceEl('hud-coins-badge');
            if (state.user.coins > oldState.coins) showFloatingStat(`+${state.user.coins - oldState.coins}`, 'coins', 'hud-coins-badge');
        }
        if (oldState.xp !== state.user.xp) {
            bounceEl('hud-xp-badge');
            if (state.user.xp > oldState.xp) showFloatingStat(`+${state.user.xp - oldState.xp}`, 'xp', 'hud-xp-badge');
        }
    }
}

function showFloatingStat(text, type, anchorId) {
    const anchor = document.getElementById(anchorId);
    if (!anchor) return;
    const rect = anchor.getBoundingClientRect();
    
    const el = document.createElement('div');
    el.className = `floating-stat ${type}`;
    el.textContent = text;
    el.style.left = `${rect.left + rect.width/2}px`;
    el.style.top = `${rect.top}px`;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1200);
}

function bounceEl(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('bounce');
    void el.offsetWidth; // Force reflow
    el.classList.add('bounce');
    setTimeout(() => el.classList.remove('bounce'), 600);
}

// ═══════════════════════════════════════════════
// LEVEL MAP RENDERING
// ═══════════════════════════════════════════════

async function loadLevels() {
    updateTheme();
    document.getElementById('hud-season').textContent = `DOMAIN: ${state.activeDomain.toUpperCase()}`;
    const res = await apiFetch(`${API}/levels/?domain=${state.activeDomain}`);
    if (!res.ok) throw new Error('Failed to load levels');
    state.levels = await res.json();
    renderMap();
}

async function setDomain(domain) {
    state.activeDomain = domain;
    localStorage.setItem('skillforge_domain', domain);
    updateTheme();
    showLoading(true);
    const st = document.getElementById('loading-status');
    if (st) st.textContent = `Switching to ${domain.toUpperCase()}...`;
    try {
        const res = await apiFetch(`${API}/domain/set/`, { method: 'POST', body: JSON.stringify({ domain }) });
        const data = await res.json();
        showToast(data.message || 'Domain selected.', 'info');
        await waitForDomainReady(domain);
        await loadLevels();
        showLoading(false);
    } catch (e) {
        showToast('Failed to set domain.', 'error');
        showLoading(false);
    }
}

function updateTheme() {
    // Remove all theme classes first
    const mainDomains = ['dsa', 'frontend', 'backend', 'sql', 'debugging'];
    mainDomains.forEach(d => document.body.classList.remove(`theme-${d}`));
    
    // Add active theme
    document.body.classList.add(`theme-${state.activeDomain}`);
}

function renderMap() {
    const container = document.getElementById('map-path');
    if (!container) return;
    container.innerHTML = '';

    const levels = state.levels;
    const COLS = 5; // Nodes per row
    const rows = [];

    // Group levels into rows
    for (let i = 0; i < levels.length; i += COLS) {
        rows.push(levels.slice(i, i + COLS));
    }

    rows.forEach((row, rowIdx) => {
        // Reverse odd rows for zigzag effect
        const displayRow = rowIdx % 2 === 1 ? [...row].reverse() : row;

        // Vertical connector between rows
        if (rowIdx > 0) {
            const vc = document.createElement('div');
            vc.className = 'map-vconnector';
            // Check if previous row's last node and this row's first node are both unlocked/completed
            const prevRow = rows[rowIdx - 1];
            const prevLast = rowIdx % 2 === 1 ? prevRow[prevRow.length - 1] : prevRow[prevRow.length - 1];
            if (prevLast && (prevLast.stars > 0 || prevLast.is_unlocked)) {
                vc.classList.add('active');
            }
            container.appendChild(vc);
        }

        const rowEl = document.createElement('div');
        rowEl.className = 'map-row';

        displayRow.forEach((lvl, colIdx) => {
            // Connector before node (not for first)
            if (colIdx > 0) {
                const conn = document.createElement('div');
                conn.className = 'map-connector';
                if (lvl.is_unlocked || lvl.stars > 0) conn.classList.add('active');
                rowEl.appendChild(conn);
            }

            const node = createNode(lvl);
            rowEl.appendChild(node);
        });

        container.appendChild(rowEl);
    });

    // Scroll to current level
    setTimeout(() => {
        const currentNode = document.querySelector('.lvl-node.current');
        if (currentNode) {
            currentNode.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, 200);
}

function createNode(lvl) {
    const node = document.createElement('div');
    node.className = 'lvl-node';
    node.id = `node-${lvl.level_number}`;

    const isCompleted = lvl.stars > 0;
    const isCurrent = lvl.is_unlocked && !isCompleted;
    const isLocked = !lvl.is_unlocked;

    if (isLocked) node.classList.add('locked');
    else if (isCurrent) node.classList.add('current');
    else if (isCompleted) node.classList.add('completed');
    else node.classList.add('unlocked');

    // Stars display for completed
    let starsHtml = '';
    if (isCompleted) {
        starsHtml = '<div class="node-stars">';
        for (let i = 1; i <= 3; i++) {
            starsHtml += `<i class="fas fa-star ${i <= lvl.stars ? 'filled' : 'empty'}"></i>`;
        }
        starsHtml += '</div>';
    }

    node.innerHTML = `
        <span class="node-num">${lvl.level_number}</span>
        ${starsHtml}
    `;

    if (!isLocked) {
        node.onclick = (e) => {
            sparkBurst(e);
            selectLevel(lvl.level_number);
        };
    }

    return node;
}

// ═══════════════════════════════════════════════
// LEVEL SELECTION & FORGE LOADING
// ═══════════════════════════════════════════════

async function selectLevel(levelNum) {
    if (state.initializing) return;
    state.initializing = true;
    showLoading(true);

    try {
        // 1. Start a level attempt (deducts life)
        const startRes = await apiFetch(`${API}/levels/${levelNum}/start/`, { method: 'POST' });
        const startData = await startRes.json();

        if (startRes.status === 403) {
            showLoading(false);
            state.initializing = false;
            showModal('modal-no-hearts');
            return;
        }

        if (!startRes.ok) {
            throw new Error(startData.error || 'Failed to start level');
        }

        state.gameSessionId = startData.session_id;
        state.user.lives = startData.lives_left;
        updateHUD();

        // 2. Get the task for this level
        const taskRes = await apiFetch(`${API}/levels/${levelNum}/task/`);
        const taskData = await taskRes.json();

        if (!taskRes.ok) {
            throw new Error(taskData.error || 'Failed to load task');
        }

        state.currentLevel = levelNum;
        renderForge(taskData);
        showView('forge');
        startTimer(taskData.tier);

    } catch (err) {
        console.error('selectLevel error:', err);
        showToast(err.message || 'Failed to load level. Try again.', 'error');
    } finally {
        showLoading(false);
        state.initializing = false;
    }
}

function renderForge(data) {
    const task = data.task;

    // Title & description
    document.getElementById('forge-title').textContent = task.title || 'Untitled Quest';
    document.getElementById('forge-description').textContent = task.description || 'Solve the challenge!';
    document.getElementById('forge-level-num').textContent = `Level ${data.level}`;

    // Tier badge
    const tierEl = document.getElementById('forge-tier');
    tierEl.textContent = (data.tier || 'beginner').toUpperCase();
    tierEl.className = 'quest-tier ' + (data.tier || 'beginner');

    // Code editor
    const editor = document.getElementById('code-editor');
    editor.value = task.starter_code || '# Write your code here\n';
    state.originalCode = editor.value;
    updateLineNumbers();

    // Terminal
    document.getElementById('terminal-content').textContent = '>>> Forge initialized. Write your solution and click Run or Submit.';

    // Hearts
    updateHeartsDisplay();

    // Update power button states
    updatePowerStates();

    // Show back button
    document.getElementById('btn-back-to-map').style.display = 'flex';
}

function updateHeartsDisplay() {
    const container = document.getElementById('forge-hearts');
    if (!container) return;
    const maxHearts = 3;
    let html = '';
    for (let i = 0; i < maxHearts; i++) {
        html += `<i class="fas fa-heart heart-icon ${i < state.user.lives ? 'active' : 'lost'}"></i>`;
    }
    container.innerHTML = html;
}

function updatePowerStates() {
    document.querySelectorAll('.power-btn').forEach(btn => {
        const cost = parseInt(btn.dataset.cost);
        if (state.user.coins < cost) {
            btn.classList.add('disabled');
        } else {
            btn.classList.remove('disabled');
        }
    });
}

// ═══════════════════════════════════════════════
// CODE EXECUTION (Run Button)
// ═══════════════════════════════════════════════

async function runCode() {
    if (!state.gameSessionId) {
        showToast('No active session. Select a level first.', 'warning');
        return;
    }

    const code = document.getElementById('code-editor').value;
    const terminal = document.getElementById('terminal-content');
    terminal.textContent = '>>> Running code...\n';

    const runBtn = document.getElementById('btn-run');
    runBtn.disabled = true;
    runBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';

    try {
        const res = await apiFetch(`${API}/game/run/${state.gameSessionId}/`, {
            method: 'POST',
            body: JSON.stringify({ code }),
        });
        const data = await res.json();

        terminal.textContent = '>>> RUN RESULT:\n\n' + (data.output || 'No output.');

        if (data.passed) {
            terminal.style.color = '#4ade80';
            showToast('✅ Sample test passed!', 'success');
        } else {
            terminal.style.color = '#f87171';
        }
    } catch (err) {
        terminal.textContent = '>>> Error: Could not execute code. Try again.';
        terminal.style.color = '#f87171';
    } finally {
        runBtn.disabled = false;
        runBtn.innerHTML = '<i class="fas fa-play"></i> Run';
    }
}

// ═══════════════════════════════════════════════
// CODE SUBMISSION (Submit Button)
// ═══════════════════════════════════════════════

async function submitCode() {
    if (!state.gameSessionId) {
        showToast('No active session.', 'warning');
        return;
    }

    const code = document.getElementById('code-editor').value;
    const terminal = document.getElementById('terminal-content');
    const submitBtn = document.getElementById('btn-submit');

    terminal.textContent = '>>> Evaluating against all test cases...\n';
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Evaluating...';

    try {
        const res = await apiFetch(`${API}/game/submit/${state.gameSessionId}/`, {
            method: 'POST',
            body: JSON.stringify({ code }),
        });
        const data = await res.json();

        if (data.status === 'success') {
            // Update user stats
            state.user.xp += data.xp_gained || 0;
            state.user.coins += data.coins_gained || 0;
            updateHUD();

            stopTimer();

            // Show results in terminal
            terminal.style.color = '#4ade80';
            terminal.textContent = `>>> SUBMISSION ACCEPTED!\n\n${data.message || ''}\nScore: ${data.score}%\nStars: ${'⭐'.repeat(data.stars)}`;

            // Show result modal after a beat
            setTimeout(() => showResultModal(data), 500);

        } else {
            // Failure
            state.user.lives = data.lives_remaining ?? state.user.lives;
            updateHUD();
            updateHeartsDisplay();
            animateHeartLoss();

            terminal.style.color = '#f87171';
            let output = `>>> SUBMISSION FAILED\n\n${data.message || ''}\nScore: ${data.score}%`;
            if (data.results) {
                output += '\n\n--- Test Results ---';
                data.results.forEach((r, i) => {
                    output += `\nTest ${i + 1}: ${r.passed ? '✅ PASS' : '❌ FAIL'}`;
                    output += `\n  Input:    ${r.input}`;
                    output += `\n  Expected: ${r.expected}`;
                    output += `\n  Actual:   ${r.actual}`;
                });
            }
            terminal.textContent = output;

            if (data.lives_remaining <= 0) {
                setTimeout(() => showModal('modal-no-hearts'), 1000);
            } else {
                setTimeout(() => showFailModal(data), 800);
            }
        }
    } catch (err) {
        terminal.textContent = '>>> System error. Please try again.';
        terminal.style.color = '#f87171';
        showToast('Submission failed. Try again.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-rocket"></i> Submit';
    }
}

// ═══════════════════════════════════════════════
// RESULT & FAIL MODALS
// ═══════════════════════════════════════════════

function showResultModal(data) {
    document.getElementById('result-title').textContent = data.stars >= 3 ? '🏆 Perfect!' : data.stars >= 2 ? '🎉 Great Job!' : '✅ Quest Complete!';
    document.getElementById('result-message').textContent = data.message || `You scored ${data.score}%`;
    document.getElementById('reward-xp').textContent = data.xp_gained || 0;
    document.getElementById('reward-coins').textContent = data.coins_gained || 0;
    document.getElementById('reward-score').textContent = (data.score || 0) + '%';

    // Animate stars
    for (let i = 1; i <= 3; i++) {
        const star = document.getElementById(`star-${i}`);
        star.classList.remove('earned', 'animating');
    }

    showModal('modal-result');
    showRewardSplash(data.xp_gained, data.coins_gained);

    // Stagger star animations
    for (let i = 1; i <= data.stars; i++) {
        setTimeout(() => {
            const star = document.getElementById(`star-${i}`);
            star.classList.add('earned', 'animating');
        }, i * 300);
    }
}

function showRewardSplash(xp, coins) {
    const splash = document.createElement('div');
    splash.className = 'reward-splash';
    splash.innerHTML = `
        <div class="splash-item" style="animation-delay: 0s;">+${xp} XP</div>
        <div class="splash-item" style="animation-delay: 0.2s;">+${coins} COINS</div>
    `;
    document.getElementById('view-forge').appendChild(splash);
    setTimeout(() => splash.remove(), 2000);
}

function showFailModal(data) {
    document.getElementById('fail-title').textContent = data.score >= 30 ? 'Almost There!' : 'Not Quite!';
    document.getElementById('fail-message').textContent = data.message || 'Some tests didn\'t pass.';
    document.getElementById('fail-tests').textContent = `${data.passed || 0}/${data.total || 0} tests passed`;
    document.getElementById('fail-hearts').textContent = `❤️ ${data.lives_remaining} lives remaining`;
    showModal('modal-fail');
}

function closeFailModal() {
    hideModal('modal-fail');
}

function nextLevel() {
    hideModal('modal-result');
    const nextLvl = (state.currentLevel || 1) + 1;
    if (nextLvl <= 100) {
        // Reload levels and go to next
        loadLevels().then(() => {
            selectLevel(nextLvl);
        });
    } else {
        showToast('🏆 You\'ve completed all levels!', 'success');
        goToMap();
    }
}

function retryLevel() {
    hideModal('modal-result');
    if (state.currentLevel) {
        selectLevel(state.currentLevel);
    }
}

// ═══════════════════════════════════════════════
// TIMER SYSTEM
// ═══════════════════════════════════════════════

function startTimer(tier) {
    stopTimer();
    const limits = { beginner: 5, elementary: 8, intermediate: 10, advanced: 15, expert: 20 };
    state.timeRemaining = (limits[tier] || 5) * 60;

    updateTimerDisplay();
    state.timerInterval = setInterval(() => {
        state.timeRemaining--;
        updateTimerDisplay();

        if (state.timeRemaining <= 0) {
            stopTimer();
            showToast('⏱ Time expired! Level failed.', 'error');
            state.user.lives = Math.max(0, state.user.lives - 1);
            updateHUD();
            updateHeartsDisplay();
            animateHeartLoss();

            if (state.user.lives <= 0) {
                setTimeout(() => showModal('modal-no-hearts'), 500);
            } else {
                setTimeout(() => goToMap(), 1500);
            }
        }
    }, 1000);
}

function stopTimer() {
    if (state.timerInterval) {
        clearInterval(state.timerInterval);
        state.timerInterval = null;
    }
}

function updateTimerDisplay() {
    const el = document.getElementById('forge-timer');
    if (!el) return;
    const m = Math.floor(state.timeRemaining / 60);
    const s = state.timeRemaining % 60;
    el.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;

    if (state.timeRemaining < 60) {
        el.classList.add('danger');
    } else {
        el.classList.remove('danger');
    }
}

// ═══════════════════════════════════════════════
// POWER-UPS
// ═══════════════════════════════════════════════

async function usePower(type) {
    if (!state.gameSessionId) {
        showToast('Start a level first!', 'warning');
        return;
    }

    const btn = document.querySelector(`[data-power="${type}"]`);
    const cost = parseInt(btn?.dataset.cost || 0);

    if (state.user.coins < cost) {
        showToast('Not enough coins!', 'warning');
        return;
    }

    try {
        const res = await apiFetch(`${API}/game/powers/${state.gameSessionId}/`, {
            method: 'POST',
            body: JSON.stringify({ power: type }),
        });
        const data = await res.json();

        if (!res.ok) {
            showToast(data.error || 'Power-up failed.', 'error');
            return;
        }

        state.user.coins = data.coins_left;
        updateHUD();
        updatePowerStates();

        // Visual feedback
        if (btn) {
            btn.classList.add('used');
            setTimeout(() => btn.classList.remove('used'), 700);
        }
        sparkBurst({ clientX: btn?.getBoundingClientRect().left + 30, clientY: btn?.getBoundingClientRect().top + 20 });

        const terminal = document.getElementById('terminal-content');

        switch (type) {
            case 'hint':
                terminal.textContent = `>>> POWER: HINT\n\n${data.message}`;
                terminal.style.color = '#fbbf24';
                showToast('💡 Hint activated!', 'info');
                break;
            case 'fix':
                terminal.textContent = `>>> POWER: AUTO FIX\n\n${data.message}`;
                terminal.style.color = '#a78bfa';
                showToast('🛠️ Code fix applied!', 'info');
                break;
            case 'logic':
                terminal.textContent = `>>> POWER: LOGIC REVEAL\n\n${data.message}`;
                terminal.style.color = '#38bdf8';
                showToast('🧠 Logic revealed!', 'info');
                break;
            case 'time':
                state.timeRemaining += data.extra_time || 120;
                updateTimerDisplay();
                terminal.textContent = `>>> POWER: TIME EXTENSION\n\n+2 minutes added!`;
                terminal.style.color = '#4ade80';
                showToast('⏱️ +2 minutes!', 'success');
                break;
            case 'skip':
                showToast('⏭️ Level skipped!', 'info');
                if (data.skipped) {
                    setTimeout(() => goToMap(), 1000);
                }
                break;
        }

    } catch (err) {
        showToast('Power-up failed.', 'error');
    }
}

// ═══════════════════════════════════════════════
// VIEW MANAGEMENT
// ═══════════════════════════════════════════════

function showView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const view = document.getElementById(`view-${name}`);
    if (view) view.classList.add('active');

    // Show/hide back button
    const backBtn = document.getElementById('btn-back-to-map');
    if (backBtn) backBtn.style.display = name === 'forge' ? 'flex' : 'none';
}

function goToMap() {
    stopTimer();
    hideAllModals();
    state.gameSessionId = null;
    state.currentLevel = null;
    showView('map');
    loadProfile();
    loadLevels();
}

function showModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
}

function hideModal(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}

function hideAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.add('hidden'));
}

function showLoading(show) {
    const el = document.getElementById('modal-loading');
    if (el) {
        if (show) el.classList.remove('hidden');
        else el.classList.add('hidden');
    }
}

// ═══════════════════════════════════════════════
// EDITOR UTILITIES
// ═══════════════════════════════════════════════

function setupEditorLineNumbers() {
    const editor = document.getElementById('code-editor');
    if (!editor) return;

    editor.addEventListener('input', updateLineNumbers);
    editor.addEventListener('scroll', syncScroll);
    editor.addEventListener('keydown', handleTab);

    updateLineNumbers();
}

function updateLineNumbers() {
    const editor = document.getElementById('code-editor');
    const lineNums = document.getElementById('line-numbers');
    if (!editor || !lineNums) return;

    const lines = editor.value.split('\n').length;
    let html = '';
    for (let i = 1; i <= Math.max(lines, 20); i++) {
        html += i + '\n';
    }
    lineNums.textContent = html;
}

function syncScroll() {
    const editor = document.getElementById('code-editor');
    const lineNums = document.getElementById('line-numbers');
    if (editor && lineNums) {
        lineNums.scrollTop = editor.scrollTop;
    }
}

function handleTab(e) {
    if (e.key === 'Tab') {
        e.preventDefault();
        const editor = e.target;
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        editor.value = editor.value.substring(0, start) + '    ' + editor.value.substring(end);
        editor.selectionStart = editor.selectionEnd = start + 4;
        updateLineNumbers();
    }
}

function resetCode() {
    const editor = document.getElementById('code-editor');
    if (editor && state.originalCode) {
        editor.value = state.originalCode;
        updateLineNumbers();
        document.getElementById('terminal-content').textContent = '>>> Code reset to original.';
        document.getElementById('terminal-content').style.color = '#94a3b8';
        showToast('Code reset!', 'info');
    }
}

function clearTerminal() {
    const terminal = document.getElementById('terminal-content');
    if (terminal) {
        terminal.textContent = '>>> Console cleared.';
        terminal.style.color = '#94a3b8';
    }
}

// ═══════════════════════════════════════════════
// ANIMATIONS & EFFECTS
// ═══════════════════════════════════════════════

function animateHeartLoss() {
    const hearts = document.querySelectorAll('.heart-icon.active');
    if (hearts.length > 0) {
        const lastHeart = hearts[hearts.length - 1];
        lastHeart.classList.add('breaking');
        setTimeout(() => {
            lastHeart.classList.remove('active', 'breaking');
            lastHeart.classList.add('lost');
        }, 500);
    }
}

function sparkBurst(e) {
    const colors = ['#38bdf8', '#a78bfa', '#4ade80', '#fbbf24', '#f472b6'];
    const x = e.clientX || e.pageX || 0;
    const y = e.clientY || e.pageY || 0;

    for (let i = 0; i < 12; i++) {
        const spark = document.createElement('div');
        spark.className = 'spark';
        const angle = Math.random() * Math.PI * 2;
        const dist = 30 + Math.random() * 80;
        spark.style.cssText = `
            left: ${x}px; top: ${y}px;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            --sx: ${Math.cos(angle) * dist}px;
            --sy: ${Math.sin(angle) * dist}px;
        `;
        document.body.appendChild(spark);
        setTimeout(() => spark.remove(), 800);
    }
}

// Global spark on button clicks
document.addEventListener('click', (e) => {
    if (e.target.closest('.btn-action, .btn-result, .power-btn')) {
        sparkBurst(e);
    }
});

// ═══════════════════════════════════════════════
// TOAST NOTIFICATION SYSTEM
// ═══════════════════════════════════════════════

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ═══════════════════════════════════════════════
// AUTH & LEADERBOARD
// ═══════════════════════════════════════════════

async function loginUser() {
    const un = document.getElementById('auth-username').value;
    const pw = document.getElementById('auth-password').value;
    if (!un || !pw) return showToast("Enter credentials", "error");
    
    try {
        const res = await apiFetch(`${API}/auth/login/`, { method: "POST", body: JSON.stringify({username: un, password: pw}) });
        const data = await res.json();
        if (res.ok) {
            state.token = data.access;
            localStorage.setItem('skillforge_token', state.token);
            hideModal("modal-auth");
            showToast("Logged in successfully!", "success");
            bootGame();
        } else {
            showToast(data.detail || "Login failed", "error");
        }
    } catch(e) {
        showToast("Error connecting.", "error");
    }
}

async function registerUser() {
    const un = document.getElementById('auth-username').value;
    const em = document.getElementById('auth-email').value;
    const pw = document.getElementById('auth-password').value;
    if (!un || !pw) return showToast("Enter credentials", "error");
    
    try {
        const res = await apiFetch(`${API}/auth/register/`, { method: "POST", body: JSON.stringify({username: un, email: em, password: pw}) });
        const data = await res.json();
        if (res.ok) {
            state.token = data.token || data.access; // Support both register/login token formats
            localStorage.setItem('skillforge_token', state.token);
            hideModal("modal-auth");
            showToast("Registered & Logged in!", "success");
            
            // Redirect to domain selection if newly registered
            setTimeout(() => {
                window.location.href = '/domain-selection/';
            }, 1000);
        } else {
            showToast(data.error || "Registration failed", "error");
        }
    } catch(e) {
        showToast("Error connecting.", "error");
    }
}

async function showLeaderboard() {
    showModal('modal-leaderboard');
    const container = document.getElementById('leaderboard-content');
    container.innerHTML = "Fetching top forgers...";
    try {
        const res = await apiFetch(`${API}/leaderboard/`);
        const data = await res.json();
        if (res.ok) {
            container.innerHTML = data.map((u, i) => `
                <div style="display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #334155;">
                    <span style="color:#e2e8f0; font-weight:bold;">#${i+1} ${u.username}</span>
                    <span style="color:#fbbf24;">${u.xp} XP</span>
                </div>
            `).join('');
        }
    } catch (e) {
        container.innerHTML = "Failed to load leaderboard.";
    }
}
