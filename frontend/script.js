const API_BASE = '/api/v1'; // Standardized versioned API base for Django Proxy
let currentTaskId = null;
let currentTask = null;
let lastRawOutput = "System initialized. No AI trace captured yet.";
let currentHints = [];
let revealedHintCount = 0;

document.addEventListener("DOMContentLoaded", () => {
    // Ping health dynamically every 10 seconds and immediately on boot
    checkAPIStatus();
    setInterval(checkAPIStatus, 10000);
    
    // Attempt to load an existing task. If DB is empty, it will auto-generate.
    fetchNextTask();
});

async function checkAPIStatus() {
    const badge = document.getElementById('api-status-badge');
    if (!badge) return;
    
    try {
        console.groupCollapsed("GSDS: Periodic Health Check");
        console.log(`Pinging: ${API_BASE}/health/`);
        const response = await fetch(`${API_BASE}/health/`);
        console.log("Status Code:", response.status);
        console.groupEnd();
        
        if (response.ok) {
            badge.innerText = 'API ONLINE';
            badge.style.background = 'green';
            badge.style.border = '1px solid darkgreen';
        } else {
            throw new Error("API Offline");
        }
    } catch(err) {
        badge.innerText = 'API OFFLINE';
        badge.style.background = 'red';
        badge.style.border = '1px solid darkred';
    }
}

// Explicitly calls Django to proxy an AI generation
async function generateAndFetchAITask(domain='python', difficulty='medium', topic='algorithms') {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) overlay.classList.remove("hidden");
    
    try {
        console.log("Requesting new task from AI Engine via Django Proxy...");
        document.getElementById("t-title").innerText = 'Generating via FLAN-T5...';
        
        const response = await fetch(`${API_BASE}/tasks/generate/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ domain, difficulty, topic })
        });
        
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            console.error("Backend proxy rejected generation:", errData);
            showFeedback("Service Error", errData.error || "The AI Engine is currently unreachable.");
            
            // Trigger a shallow UI reset so the user isn't stuck on "Generating..."
            document.getElementById("t-title").innerText = 'Service Temporarily Unavailable';
            return;
        }

        const data = await response.json();
        console.log("Django returned AI Wrapper:", data);
        
        lastRawOutput = data.raw_output || "No raw output returned from AI engine.";
        
        // ALWAYS extract usable task per fallback constraints!
        const task = data.final_task || data.parsed || data;
        
        if (data.raw_output) {
            console.log("Raw LLM Dump (Debugging): \n", data.raw_output);
        }
        
        if (data.success === false && data.error) {
            console.warn("AI Generation Non-Fatal Warning -> Resorted to Fallback Payload:", data.error);
        }

        renderTaskToUI(task);

    } catch (err) {
        console.error("System timeout or disconnect:", err);
        showFeedback("Error", "Generation timeout or system offline.");
        
        // Provide an ultimate hardcoded frontend fallback so UI never completely bricks!
        renderTaskToUI({
            title: "Frontend Network Failure Recovery",
            domain: "python", difficulty: "medium",
            scenario: "The backend server completely disconnected.",
            given_code: "# Please restart python manage.py runserver 8000\npass",
            expected_output: "None", constraints: ["None"], evaluation_criteria: ["None"]
        });
    } finally {
        if (overlay) overlay.classList.add("hidden");
    }
}

async function fetchNextTask() {
    try {
        console.log(`fetching next task from: ${API_BASE}/tasks/next/`);
        const response = await fetch(`${API_BASE}/tasks/next/`);
        
        if (response.status === 404) {
            console.log("Database empty. Auto-triggering AI logic...");
            return generateAndFetchAITask();
        }
        
        const data = await response.json();
        const task = data.final_task || data.parsed || data;
        renderTaskToUI(task);
        
    } catch (err) {
        console.error("Failed to fetch task:", err);
        showFeedback("Error", "Could not connect to the backend server.");
    }
}

function renderTaskToUI(task) {
    if (!task) return;
    
    currentTask = task;
    currentTaskId = task.id || null;
    
    // Core Layout
    document.getElementById("t-title").innerText = task.title || 'Untitled Challenge';
    document.getElementById("u-domain").innerText = task.domain || 'General';
    document.getElementById("u-difficulty").innerText = task.difficulty || 'Normal';
    
    document.getElementById("t-scenario").innerText = task.scenario || 'No environmental context provided for this session.';
    document.getElementById("t-output").innerText = task.expected_output || 'Result format not specified.';
    document.getElementById("t-code").value = task.given_code || '# No starter code available';
    
    // Populate Constraints Array
    const constraintList = document.getElementById("t-constraints");
    if (constraintList) {
        constraintList.innerHTML = '';
        const cons = Array.isArray(task.constraints) ? task.constraints : [];
        if (cons.length > 0) {
            cons.forEach(c => {
                const li = document.createElement("li");
                li.innerText = c;
                constraintList.appendChild(li);
            });
        } else {
            constraintList.innerHTML = '<li>None</li>';
        }
    }
    
    // Populate Validation Array
    const criteriaList = document.getElementById("t-criteria");
    if (criteriaList) {
        criteriaList.innerHTML = '';
        const evals = Array.isArray(task.evaluation_criteria) ? task.evaluation_criteria : [];
        if (evals.length > 0) {
            evals.forEach(c => {
                const li = document.createElement("li");
                li.innerText = c;
                criteriaList.appendChild(li);
            });
        } else {
            criteriaList.innerHTML = '<li>None</li>';
        }
    }
    
    // Pedagogy Setup
    currentHints = task.hints || [];
    revealedHintCount = 0;
    document.getElementById("t-hints").innerHTML = "";
    document.getElementById("btn-reveal-hint").classList.remove("hidden");
    document.getElementById("btn-reveal-hint").innerText = "Reveal Logic Hint (" + currentHints.length + " available)";
    document.getElementById("approach-container").classList.add("hidden");
    document.getElementById("t-approach").innerText = task.solution_approach || "No expert briefing available for this session.";
}

async function submitTask() {
    if (!currentTaskId) {
        showFeedback("Demo", "Simulating fake evaluation! No ID active.");
        return;
    }

    const modifiedCode = document.getElementById("t-code").value;

    try {
        console.log(`Submitting solution to: ${API_BASE}/tasks/submit/`);
        const response = await fetch(`${API_BASE}/tasks/submit/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, code: modifiedCode })
        });

        if (!response.ok) throw new Error("Submission Failed");

        const data = await response.json();
        showFeedback(data.score, data.feedback, data.actual_output, currentTask?.expected_output, data);

    } catch (err) {
        console.error(err);
        showFeedback("Error", "Submission could not be processed.");
    }
}

function showFeedback(score, text, actual, expected, data) {
    document.getElementById("f-score").innerText = `Score: ${score}`;
    document.getElementById("f-text").innerText = data ? data.feedback : text;
    
    document.getElementById("f-expected").innerText = currentTask.expected_output;
    document.getElementById("f-actual").innerText = data ? data.actual_output : (actual || 'N/A');
    
    // Creative Reveal: Show Expert approach on Success
    if (data && data.is_correct) {
        document.getElementById("approach-container").classList.remove("hidden");
        document.getElementById("approach-container").style.animation = "slideIn 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards";
    }
    
    document.getElementById("feedback-overlay").classList.remove("hidden");
}

function closeFeedback() {
    document.getElementById("feedback-overlay").classList.add("hidden");
}

function showDiagnostics() {
    const logEl = document.getElementById("d-log");
    if (logEl) logEl.innerText = lastRawOutput;
    document.getElementById("diagnostic-overlay").classList.remove("hidden");
}

function closeDiagnostics() {
    document.getElementById("diagnostic-overlay").classList.add("hidden");
}

/**
 * Creative Reveal Logic
 */
function revealHint() {
    if (revealedHintCount < currentHints.length) {
        const li = document.createElement("li");
        li.innerText = "💡 " + currentHints[revealedHintCount];
        li.className = "hint-item";
        li.style.background = "rgba(255, 204, 0, 0.1)";
        li.style.border = "1px solid rgba(255, 204, 0, 0.2)";
        li.style.padding = "10px";
        li.style.borderRadius = "4px";
        li.style.marginBottom = "5px";
        li.style.fontSize = "0.85rem";
        li.style.opacity = "0";
        li.style.transition = "all 0.5s ease";
        
        document.getElementById("t-hints").appendChild(li);
        
        // Trigger reflow for animation
        setTimeout(() => {
            li.style.opacity = "1";
            li.style.transform = "translateX(5px)";
        }, 10);
        
        revealedHintCount++;
        
        const btn = document.getElementById("btn-reveal-hint");
        const remaining = currentHints.length - revealedHintCount;
        if (remaining > 0) {
            btn.innerText = "Unlock Next Hint (" + remaining + " left)";
        } else {
            btn.classList.add("hidden");
        }
    }
}
