// githubReadmeForge Frontend App Controller
let currentStep = 1;
let scanContext = null;
let analysisContext = null;
let docPlanContext = null;
let currentDraftId = '.readme_forge_draft'; // updated after each generate call
let providerConfig = {
    provider: '',
    model: '',
    api_key: '',
    ollama_host: 'http://localhost:11434',
    opencode_host: 'http://127.0.0.1:4096'
};

// ── localStorage persistence keys ─────────────────────────────────────────
const LS_PROVIDER = 'rmf_provider';
const LS_MODEL    = 'rmf_model';
const LS_HOST     = 'rmf_ollama_host';
// NOTE: api_key is intentionally NOT persisted for security

function _saveProviderPrefs() {
    try {
        localStorage.setItem(LS_PROVIDER, providerConfig.provider);
        localStorage.setItem(LS_MODEL,    providerConfig.model);
        localStorage.setItem(LS_HOST,     providerConfig.ollama_host || '');
    } catch (e) { /* private browsing — ignore */ }
}

async function _restoreProviderPrefs() {
    try {
        const provider = localStorage.getItem(LS_PROVIDER);
        const savedModel = localStorage.getItem(LS_MODEL);
        const host     = localStorage.getItem(LS_HOST);

        // Restore host first so fetchModels() (triggered by provider change) uses the right URL
        if (host) {
            const hi = document.getElementById('ollama-host-input');
            if (hi) hi.value = host;
        }

        if (provider) {
            const sel = document.getElementById('provider-select');
            if (sel) {
                sel.value = provider;
                // Temporarily store the model to restore on window._pendingModelRestore
                window._pendingModelRestore = savedModel;
                await handleProviderChange();
            }
        }
    } catch (e) { /* ignore */ }
}

// ── Contextual error hints from server error_type ─────────────────────────
function _getErrorMessage(data) {
    const hint = data.hint ? `\n\n💡 ${data.hint}` : '';
    return (data.error || 'An unknown error occurred.') + hint;
}

// ── marked (markdown parser) init ─────────────────────────────────────────
marked.use({
    breaks: true,
    gfm: true
});

// ── Mermaid init — pinned v10, lenient parsing ─────────────────────────────
mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: {
        htmlLabels: true,
        useMaxWidth: true,
        curve: 'basis'
    },
    themeVariables: {
        primaryColor: '#6d5dfc',
        primaryTextColor: '#14213d',
        primaryBorderColor: '#4a3fd4',
        lineColor: '#52627e',
        secondaryColor: '#f7f9fc',
        tertiaryColor: '#e8edf5'
    }
});

// On page load: restore saved prefs first (so host URL is in place),
// then init the provider UI. This prevents fetchModels() from hitting
// the wrong Ollama host on first load.
window.addEventListener('DOMContentLoaded', async () => {
    await _restoreProviderPrefs();
    // If no saved provider, initialise a clean provider UI state
    const savedProvider = localStorage.getItem(LS_PROVIDER);
    if (!savedProvider) {
        handleProviderChange();
    }

    // Wire up the repo path input to enable/disable the Analyze button
    const repoInput = document.getElementById('repo-path-input');
    if (repoInput) {
        const updateAnalyzeState = () => _updateAnalyzeButtonState();
        repoInput.addEventListener('input', updateAnalyzeState);
        // Initial state
        _updateAnalyzeButtonState();
    }
});

// ENABLE / DISABLE the Analyze button based on whether the user has typed a path
function _updateAnalyzeButtonState() {
    const repoInput = document.getElementById('repo-path-input');
    const analyzeBtn = document.querySelector('button[onclick="runAnalysis()"]');
    if (!repoInput || !analyzeBtn) return;
    const hasValue = (repoInput.value || '').trim().length > 0;
    analyzeBtn.disabled = !hasValue;
    analyzeBtn.style.opacity = hasValue ? '1' : '0.5';
    analyzeBtn.style.cursor = hasValue ? 'pointer' : 'not-allowed';
    analyzeBtn.title = hasValue ? '' : 'Please enter a repository link or local path first';
}

// STEP NAVIGATION
function goToStep(step) {
    // Hide all panels
    document.querySelectorAll('.wizard-panel').forEach(panel => {
        panel.classList.remove('active');
    });

    // Show target panel
    const targetPanel = document.getElementById(`panel-${step}`);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }

    // Update step indicator classes
    document.querySelectorAll('.step-item').forEach(item => {
        const itemStep = parseInt(item.getAttribute('data-step'));
        item.classList.remove('active');
        if (itemStep === step) {
            item.classList.add('active');
        }
        if (itemStep < step) {
            item.classList.add('completed');
        } else {
            item.classList.remove('completed');
        }
    });

    currentStep = step;
}

// HANDLE PROVIDER SELECTION INPUTS
async function handleProviderChange() {
    const provider = document.getElementById('provider-select').value;
    const apiKeyGroup = document.getElementById('api-key-group');
    const modelGroup = document.getElementById('model-group');
    const ollamaGroup = document.getElementById('ollama-host-group');
    const opencodeGroup = document.getElementById('opencode-host-group');

    apiKeyGroup.style.display = 'none';
    modelGroup.style.display = 'none';
    ollamaGroup.style.display = 'none';
    opencodeGroup.style.display = 'none';

    const apiKeyInput = document.getElementById('api-key-input');
    if (apiKeyInput) {
        apiKeyInput.value = '';
        apiKeyInput.readOnly = false;
        apiKeyInput.style.opacity = '1.0';
        apiKeyInput.placeholder = 'Enter your provider API Key';
    }

    if (provider === 'ollama') {
        modelGroup.style.display = 'flex';
        ollamaGroup.style.display = 'flex';
        return await fetchModels();
    } else if (provider === 'opencode') {
        opencodeGroup.style.display = 'flex';
        modelGroup.style.display = 'flex';
        apiKeyGroup.style.display = 'flex';
        return await fetchModels();
    } else if (provider === 'mock') {
        // Mock needs no key and has no real model list — skip fetch
        modelGroup.style.display = 'none';
    } else if (provider) {
        // Cloud providers: show API key input and auto-fetch to check env keys
        apiKeyGroup.style.display = 'flex';
        modelGroup.style.display = 'flex';
        return await fetchModels();
    }
}

async function fetchModels() {
    const provider = document.getElementById('provider-select').value;
    const apiKeyInput = document.getElementById('api-key-input');
    const apiKey = apiKeyInput ? apiKeyInput.value.trim() : '';
    const modelGroup = document.getElementById('model-group');
    const modelSelect = document.getElementById('model-select');
    const modelLoading = document.getElementById('model-loading');

    // Determine custom base URL for local providers
    let baseUrl = '';
    if (provider === 'ollama') {
        baseUrl = document.getElementById('ollama-host-input')?.value.trim() || 'http://localhost:11434';
    } else if (provider === 'opencode') {
        baseUrl = document.getElementById('opencode-host-input')?.value.trim() || 'http://127.0.0.1:4096';
    }

    // Cloud providers: don't fetch if no key has been entered yet
    if (provider !== 'ollama' && provider !== 'opencode' && provider !== 'mock' && !apiKey) {
        modelSelect.innerHTML = '<option value="">Enter API key to load models</option>';
        return;
    }

    modelGroup.style.display = 'flex';
    modelLoading.style.display = 'inline-block';
    modelSelect.innerHTML = '<option value="">Loading...</option>';

    // AbortController gives us a hard timeout so a dead Ollama server
    // doesn't leave the spinner running forever.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    try {
        const response = await fetch('/api/models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider, api_key: apiKey, base_url: baseUrl }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        const data = await response.json();

        modelLoading.style.display = 'none';

        if (data.success && data.models && data.models.length > 0) {
            modelSelect.innerHTML = '<option value="">Select a model...</option>';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
            // Restore previously saved model selection if available
            if (window._pendingModelRestore) {
                const saved = window._pendingModelRestore;
                if (modelSelect.querySelector(`option[value="${saved}"]`)) {
                    modelSelect.value = saved;
                }
                window._pendingModelRestore = null;
            }
            // Succeeded with empty input key -> server env key is available
            if (!apiKey && apiKeyInput) {
                apiKeyInput.value = '••••••••';
                apiKeyInput.readOnly = true;
                apiKeyInput.style.opacity = '0.7';
                apiKeyInput.title = 'Using API Key from environment. Click to change.';
                apiKeyInput.onclick = function() {
                    if (apiKeyInput.readOnly) {
                        apiKeyInput.value = '';
                        apiKeyInput.readOnly = false;
                        apiKeyInput.style.opacity = '1.0';
                        apiKeyInput.placeholder = 'Enter your provider API Key';
                        apiKeyInput.onclick = null;
                    }
                };
            }
        } else if (data.models && data.models.length === 0 && provider === 'ollama') {
            // Ollama is reachable but has no models pulled
            modelSelect.innerHTML = '<option value="">No local models found</option>';
            showNotification(
                'Ollama is running but has no models pulled. Run e.g. "ollama pull llama3.2" in your terminal, then click Fetch Models.',
                'info'
            );
        } else if (data.error) {
            if (provider === 'ollama') {
                modelSelect.innerHTML = '<option value="">Ollama unreachable</option>';
                showNotification(
                    `Could not reach Ollama at ${baseUrl}. Make sure Ollama is running ("ollama serve") and try again.`,
                    'error'
                );
            } else if (provider === 'opencode') {
                modelSelect.innerHTML = '<option value="">OpenCode unreachable</option>';
                showNotification(
                    `Could not reach OpenCode at ${baseUrl}. Make sure OpenCode is running and try again.`,
                    'error'
                );
            } else {
                modelSelect.innerHTML = '<option value="">API Key Required</option>';
                if (apiKeyInput) {
                    apiKeyInput.value = '';
                    apiKeyInput.readOnly = false;
                    apiKeyInput.style.opacity = '1.0';
                    apiKeyInput.placeholder = 'Enter your provider API Key';
                }
                if (apiKey && apiKey !== '••••••••') {
                    showNotification('Failed to fetch models: ' + data.error, 'error');
                }
            }
        } else {
            modelSelect.innerHTML = '<option value="">No models found</option>';
        }
    } catch (err) {
        clearTimeout(timeoutId);
        modelLoading.style.display = 'none';
        if (err.name === 'AbortError') {
            modelSelect.innerHTML = '<option value="">Server not reachable</option>';
            if (provider === 'ollama') {
                showNotification(
                    `Ollama server timed out at ${baseUrl}. Make sure Ollama is running ("ollama serve") and the host URL is correct.`,
                    'error'
                );
            } else {
                showNotification('Model fetch timed out. Check your connection.', 'error');
            }
        } else {
            modelSelect.innerHTML = '<option value="">Error loading models</option>';
        }
    }
}

// VALIDATE STEP 2 CONFIG
function validateLLMConfig() {
    const provider = document.getElementById('provider-select').value;
    const apiKeyInput = document.getElementById('api-key-input');
    const apiKey = apiKeyInput ? apiKeyInput.value.trim() : '';
    const modelSelect = document.getElementById('model-select');
    // Always read the actual dropdown value — never hardcode a model name
    const model = modelSelect.value || '';
    const ollamaHost = document.getElementById('ollama-host-input').value.trim();
    const opencodeHost = document.getElementById('opencode-host-input').value.trim();

    const isEnvKey = apiKeyInput && (apiKey === '••••••••' || apiKeyInput.readOnly);
    if (provider !== 'ollama' && provider !== 'opencode' && provider !== 'mock' && !apiKey && !isEnvKey) {
        showNotification('API Key is required for the selected provider.', 'error');
        return;
    }

    // For Ollama/OpenCode, a model must be selected from the fetched list
    if (!model && provider !== 'mock') {
        if (provider === 'ollama') {
            showNotification('Please select a local Ollama model. Use "Fetch Models" to load your pulled models.', 'error');
        } else if (provider === 'opencode') {
            showNotification('Please select an OpenCode model. Use "Fetch Models" to load available models.', 'error');
        } else {
            showNotification('Please select a model.', 'error');
        }
        return;
    }

    providerConfig = {
        provider: provider,
        api_key: apiKey === '••••••••' ? '' : apiKey,
        model: model,
        ollama_host: ollamaHost,
        opencode_host: opencodeHost
    };

    _saveProviderPrefs(); // persist non-sensitive prefs
    goToStep(3);
}

// RUN ANALYZE API
async function runAnalysis() {
    const repoPath = document.getElementById('repo-path-input').value.trim();
    if (!repoPath) {
        showNotification('Please enter a GitHub URL or a local directory path before analyzing.', 'error');
        const input = document.getElementById('repo-path-input');
        if (input) input.focus();
        return;
    }
    // Reject trivial placeholders like a single dot
    if (repoPath === '.' || repoPath === '/' || repoPath === './' || repoPath === '../') {
        showNotification('Please enter a real GitHub URL or a specific directory path (not just "." or "/").', 'error');
        const input = document.getElementById('repo-path-input');
        if (input) input.focus();
        return;
    }

    const loader = document.getElementById('ingest-loader');
    const actions = document.getElementById('ingest-actions');
    const loaderStatus = document.getElementById('loader-status');

    // Show loader, hide buttons
    loader.style.display = 'flex';
    actions.style.display = 'none';
    loaderStatus.textContent = "Reader Agent cloning & scanning repository...";

    // Mock progress messages
    const statusMessages = [
        "Reader Agent scanning directory tree structure...",
        "Reader Agent walking configuration and packages...",
        "Analyzer Agent rating existing README against codebase...",
        "Analyzer Agent building visual structural graph..."
    ];
    let msgIdx = 0;
    const statusInterval = setInterval(() => {
        if (msgIdx < statusMessages.length) {
            loaderStatus.textContent = statusMessages[msgIdx++];
        }
    }, 4000);

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path: repoPath,
                provider: providerConfig.provider,
                api_key: providerConfig.api_key,
                model: providerConfig.model,
                base_url: providerConfig.provider === 'ollama' ? providerConfig.ollama_host : providerConfig.opencode_host
            })
        });

        clearInterval(statusInterval);
        const data = await response.json();
        
        if (!data.success) {
            showNotification(`Analysis Error: ${data.error}`, 'error');
            loader.style.display = 'none';
            actions.style.display = 'flex';
            return;
        }

        // Save scan and analysis context
        scanContext = data.scan;
        analysisContext = data.analysis;
        docPlanContext = data.doc_plan;

        // Populate rating dashboard
        populateDashboard(data.score, data.analysis);
        
        loader.style.display = 'none';
        actions.style.display = 'flex';
        goToStep(4);

    } catch (err) {
        clearInterval(statusInterval);
        showNotification(`Request failed: ${err}`, 'error');
        loader.style.display = 'none';
        actions.style.display = 'flex';
    }
}

// POPULATE DIAGNOSTICS DASHBOARD
function populateDashboard(score, analysis) {
    // Show low confidence warning if applicable
    const confidence = (analysis.classification && analysis.classification.confidence !== undefined)
        ? analysis.classification.confidence
        : 1.0;
    if (analysis.analysis_complete === false || confidence < 0.5) {
        showNotification(
            '⚠ Repository classification confidence is low or incomplete. Manual review recommended.',
            'info'
        );
        const projectTypeBadge = document.getElementById('dashboard-project-type');
        if (projectTypeBadge) {
            projectTypeBadge.style.background = '#f59e0b'; // amber
            projectTypeBadge.style.color = '#fff';
        }
    }

    // Set classification badges
    const projectTypeBadge = document.getElementById('dashboard-project-type');
    const maturityBadge = document.getElementById('dashboard-project-maturity');
    if (projectTypeBadge) projectTypeBadge.textContent = analysis.project_type || 'Unknown';
    if (maturityBadge) maturityBadge.textContent = analysis.project_maturity || 'Unknown';

    // Display the auto-detected README style so the user can see what was chosen
    const styleAutoInfo = document.getElementById('style-auto-info');
    const styleAutoValue = document.getElementById('style-auto-value');
    const recommended = analysis.recommended_style;
    if (recommended && styleAutoInfo && styleAutoValue) {
        const styleDescriptions = {
            reference: 'Reference — User manual (libraries, CLIs, APIs)',
            narrative: 'Narrative — Story-driven (products, frameworks)',
            tutorial: 'Tutorial — Learning path (tutorials, awesome-lists)',
            showcase: 'Showcase — Visual product page (UI apps)',
            minimal: 'Minimal — Trailer (small utilities)',
        };
        styleAutoValue.textContent = ' ' + (styleDescriptions[recommended] || recommended);
        // Only show the auto-detected badge when the user has selected "Auto-detect"
        const styleSelect = document.getElementById('brief-style-select');
        if (styleSelect && (styleSelect.value === '' || styleSelect.value === recommended)) {
            styleAutoInfo.style.display = 'block';
        } else {
            styleAutoInfo.style.display = 'none';
        }
    } else if (styleAutoInfo) {
        styleAutoInfo.style.display = 'none';
    }

    // 1. Score gauge — animate counter and set conic gradient
    const scoreText = document.getElementById('score-text');
    const scoreCircle = document.querySelector('.score-circle');
    const scoreGaugeBox = document.querySelector('.score-gauge-box');

    // Determine status class for colour theming
    const statusClass = score >= 85 ? 'score-excellent'
        : score >= 65 ? 'score-good'
        : score >= 40 ? 'score-fair'
        : 'score-poor';

    if (scoreGaugeBox) {
        scoreGaugeBox.classList.remove('score-excellent', 'score-good', 'score-fair', 'score-poor');
        scoreGaugeBox.classList.add(statusClass);
    }

    // Animate score counter from 0 → score
    if (scoreText) {
        scoreText.classList.remove('animate');
        void scoreText.offsetWidth; // trigger reflow to restart animation
        let current = 0;
        const step = Math.ceil(score / 30);
        const timer = setInterval(() => {
            current = Math.min(current + step, score);
            scoreText.textContent = current;
            if (current >= score) clearInterval(timer);
        }, 30);
        scoreText.classList.add('animate');
    }

    // Set CSS variable for conic gradient arc
    const deg = Math.round((score / 100) * 360);
    if (scoreCircle) scoreCircle.style.setProperty('--score-deg', deg);

    // Show status badge text
    const statusLabel = score >= 85 ? 'Excellent' : score >= 65 ? 'Good' : score >= 40 ? 'Fair' : 'Needs Work';
    const existingStatus = document.querySelector('.score-status');
    if (existingStatus) {
        existingStatus.className = `score-status ${statusClass.replace('score-', '')}`;
        existingStatus.textContent = statusLabel;
    }

    // 2. Persona summary
    const personaText = document.getElementById('dashboard-persona');
    if (personaText) personaText.textContent = analysis.project_persona || "A codebase repository.";

    // 3. Tech Stack pills
    const techStack = document.getElementById('dashboard-tech-stack');
    if (techStack) {
        techStack.innerHTML = '';
        const stack = analysis.tech_stack || [];
        stack.forEach(tech => {
            const pill = document.createElement('span');
            pill.className = 'tech-pill';
            pill.textContent = tech;
            techStack.appendChild(pill);
        });
    }

    // 4. Improvements table rows
    const tbody = document.getElementById('improvements-tbody');
    if (tbody) {
        tbody.innerHTML = '';
        const improvements = analysis.improvements || [];

        if (improvements.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">✅ No gaps identified. Your README is in great shape!</td></tr>`;
        } else {
            improvements.forEach(imp => {
                const tr = document.createElement('tr');
                const badgeClass = (imp.type || 'general').toLowerCase().replace(/\s+/g, '-');
                tr.innerHTML = `
                    <td><strong style="color: var(--text-secondary);">${escapeHtml(String(imp.id || 'N/A'))}</strong></td>
                    <td><span class="imp-badge ${badgeClass}">${escapeHtml(imp.type || 'General')}</span></td>
                    <td><strong>${escapeHtml(imp.title || 'Enhancement Opportunity')}</strong></td>
                    <td style="color: var(--text-secondary); font-size: 0.9rem;">${escapeHtml(imp.description || '')}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    }

    // Update the "X gaps found" pill next to the score
    const gapsPill = document.getElementById('gaps-pill');
    const gapsPillCount = document.getElementById('gaps-pill-count');
    if (gapsPill && gapsPillCount) {
        const count = (analysis.improvements || []).length;
        gapsPillCount.textContent = count;
        if (count === 0) {
            gapsPill.textContent = 'No gaps — looking good';
            gapsPill.classList.add('gaps-pill-clean');
        } else {
            gapsPill.classList.remove('gaps-pill-clean');
        }
    }

    // 5. Trigger documentation drift check
    checkDocumentationDrift();
}

async function checkDocumentationDrift() {
    const container = document.getElementById('dashboard-drift-content');
    const box = document.getElementById('dashboard-drift-box');
    if (!container || !box) return;

    box.style.display = 'block';
    container.innerHTML = '<div style="color: var(--text-secondary); font-size: 0.9rem;"><span class="spinner-small"></span> Checking documentation drift...</div>';

    try {
        // Use the path from the saved scan context if available, fall back to input
        const repoPath = (scanContext && scanContext.path)
            ? scanContext.path
            : (document.getElementById('repo-path-input')?.value.trim() || '');
        const response = await fetch('/api/drift', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scan: scanContext,
                analysis: analysisContext,
                path: repoPath
            })
        });

        if (!response.ok) {
            container.innerHTML = `<div style="color: var(--accent-danger); font-size: 0.9rem;">Check failed: Server returned ${response.status} ${response.statusText}</div>`;
            return;
        }
        const data = await response.json();
        if (!data.success) {
            container.innerHTML = `<div style="color: var(--accent-danger); font-size: 0.9rem;">Check failed: ${escapeHtml(data.error)}</div>`;
            return;
        }

        const drift = data.drift || [];
        if (drift.length === 0) {
            container.innerHTML = `
                <div class="drift-alert-success">
                    <span>✅</span>
                    <span>Documentation matches codebase. No undocumented changes detected.</span>
                </div>
            `;
        } else {
            let listHtml = '';
            drift.forEach(item => {
                listHtml += `<li><strong>[${escapeHtml(item.type)}]</strong> ${escapeHtml(item.message)}</li>`;
            });

            container.innerHTML = `
                <div class="drift-alert-warning">
                    <div class="drift-warning-title">⚠️ Detected Documentation Drift (${drift.length} changes)</div>
                    <ul class="drift-warning-list">
                        ${listHtml}
                    </ul>
                </div>
            `;
        }
    } catch (err) {
        container.innerHTML = `<div style="color: var(--accent-danger); font-size: 0.9rem;">Check failed: ${escapeHtml(err.message)}</div>`;
    }
}

// Maps project intent → default visual asset pack (mirrors INTENT_VISUAL_STRATEGY in contracts.py)
function _intentToVisualPack(intent) {
    const map = {
        application: 'ui_app',
        demo:        'ui_app',
        api:         'api',
        library:     'package',
        cli:         'package',
        learning:    'minimal',
        poc:         'minimal',
        minimal:     'minimal',
        unknown:     'minimal',
    };
    return map[intent] || 'ui_app';
}

// DESIGN BRIEF INTERACTIVE REVIEW
function loadDesignBrief() {
    if (!analysisContext) {
        showNotification("No analysis data found. Please analyze codebase first.", "error");
        return;
    }

    // Set Classification Metadata
    const classification = analysisContext.classification || {};
    const confidence = classification.confidence !== undefined ? classification.confidence : 1.0;

    document.getElementById('brief-primary-intent').textContent =
        classification.primary_intent || analysisContext.project_type || 'Unknown';
    document.getElementById('brief-delivery-surfaces').textContent =
        (classification.delivery_surfaces || []).join(', ') || 'None';
    document.getElementById('brief-confidence').textContent =
        `${Math.round(confidence * 100)}%`;

    // Populate Evidence list
    const evidenceContainer = document.getElementById('brief-evidence-container');
    evidenceContainer.innerHTML = '';

    const evidence = classification.evidence || [];
    if (evidence.length === 0) {
        evidenceContainer.innerHTML = '<div style="color: var(--text-secondary); font-size: 0.9rem;">No deterministic signals detected in repository tree.</div>';
    } else {
        evidence.forEach(item => {
            const card = document.createElement('div');
            card.className = 'evidence-badge';
            card.innerHTML = `
                <div class="evidence-source">${escapeHtml(item.source)}</div>
                <div class="evidence-claim">${escapeHtml(item.claim)}</div>
                <div class="evidence-signal">${escapeHtml(item.signal)}</div>
            `;
            evidenceContainer.appendChild(card);
        });
    }

    // Populate Sections Checklist
    const sectionsContainer = document.getElementById('brief-sections-container');
    sectionsContainer.innerHTML = '';

    const sectionDescriptions = {
        'title': 'Project Title Block & Shields Badges',
        'overview': 'One-liner Tagline & Core Description',
        'problem': 'The Pain Point (omitted for learning/minimal/unknown)',
        'solution': 'The Solution Narrative (omitted for learning/minimal/unknown)',
        'key_concepts': 'Key Concepts & Terminology Table',
        'architecture': 'Architecture Diagram & Subgraphs',
        'features': 'Key Features & Capabilities Grid',
        'installation': 'Copy-Pasteable Installation Steps',
        'usage': 'Quick Start & Usage Examples',
        'configuration': 'Config Variables & Options Table',
        'api_reference': 'API Endpoints & Request Formats',
        'data_models': 'Data Schema & Models Table',
        'testing': 'Test Coverage & Run Instructions',
        'repository_structure': 'Project Directory Tree Structure',
        'contributing_license': 'Contributing Rules & License Details'
    };

    const docPlan = docPlanContext || { sections: ['title', 'overview'] };
    const available = docPlan.available_sections || Object.keys(sectionDescriptions);
    available.forEach(sec => {
        const desc = sectionDescriptions[sec];
        if (!desc) return;
        const checked = docPlan.sections.includes(sec) ? 'checked' : '';
        const label = document.createElement('label');
        label.className = 'checkbox-label';
        label.innerHTML = `
            <input type="checkbox" name="brief-section" value="${sec}" ${checked}>
            <span><strong>${escapeHtml(sec)}</strong> — ${escapeHtml(desc)}</span>
        `;
        sectionsContainer.appendChild(label);
    });

    // Auto-select visual pack from classification suggested strategy
    const visualPackSelect = document.getElementById('brief-visual-pack');
    if (visualPackSelect) {
        const suggestedStrategy =
            classification.suggested_visual_strategy ||
            docPlan.suggested_visual_strategy ||
            _intentToVisualPack(classification.primary_intent || 'application');
        visualPackSelect.value = suggestedStrategy;
    }

    goToStep(5);
}

function handleVisualPackChange() {
    // Optional hook for visual strategy updates
}

function triggerDraftGeneration() {
    // Collect selected sections
    const checkboxes = document.querySelectorAll('input[name="brief-section"]:checked');
    const selectedSections = Array.from(checkboxes).map(cb => cb.value);

    // Collect pack strategy and CDN asset options
    const visualPack = document.getElementById('brief-visual-pack').value;
    const noExternalAssets = document.getElementById('brief-no-external-assets').checked;
    const includeHeaderBanner = document.getElementById('brief-include-header-banner').checked;

    // Read style from the Brief panel selector (Step 5); empty = auto-detect
    const styleSelect = document.getElementById('brief-style-select');
    const chosenStyle = styleSelect ? styleSelect.value : '';

    const briefOptions = {
        sections: selectedSections,
        visual_pack: visualPack,
        no_external_assets: noExternalAssets,
        include_header_banner: includeHeaderBanner,
        style: chosenStyle
    };

    startGeneration(true, '', briefOptions);
}

function regenerateDraft() {
    triggerDraftGeneration();
}

// GENERATION API CALL
async function startGeneration(isInstant, compiledAnswers = '', briefOptions = null) {
    const isBrief = !!briefOptions;
    const loader = document.getElementById(isBrief ? 'brief-loader' : 'dashboard-loader');
    const loaderStatus = document.getElementById(isBrief ? 'brief-loader-status' : 'dashboard-loader-status');
    const actionsBlock = document.getElementById(isBrief ? 'brief-actions' : 'dashboard-actions');

    // Read style: prefer briefOptions.style, then brief-style-select, then analyzer-recommended, then narrative
    let styleToUse;
    if (briefOptions && briefOptions.style) {
        styleToUse = briefOptions.style;
    } else {
        const styleSelectValue = document.getElementById('brief-style-select')?.value;
        if (styleSelectValue) {
            styleToUse = styleSelectValue;
        } else if (analysisContext && analysisContext.recommended_style) {
            styleToUse = analysisContext.recommended_style;
        } else {
            styleToUse = 'narrative';
        }
    }

    // Display loader overlay
    if (loader) loader.style.display = 'flex';
    if (actionsBlock) actionsBlock.style.display = 'none';
    if (loaderStatus) loaderStatus.textContent = "Writer Agent forging markdown README.md...";

    const statusMessages = [
        "Writer Agent preparing README structure...",
        "Writer Agent drafting narrative sections...",
        "Writer Agent generating code examples and diagrams..."
    ];
    let msgIdx = 0;
    const statusInterval = setInterval(() => {
        if (msgIdx < statusMessages.length && loaderStatus) {
            loaderStatus.textContent = statusMessages[msgIdx++];
        }
    }, 4000);

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scan: scanContext,
                analysis: analysisContext,
                provider: providerConfig.provider,
                api_key: providerConfig.api_key,
                model: providerConfig.model,
                base_url: providerConfig.provider === 'ollama'
                    ? providerConfig.ollama_host
                    : providerConfig.opencode_host,
                custom_answers: isInstant ? '' : compiledAnswers,
                style: styleToUse,
                lang: document.getElementById('lang-select')?.value || 'en',
                brief: briefOptions
            })
        });

        clearInterval(statusInterval);
        const data = await response.json();
        if (loader) loader.style.display = 'none';
        if (actionsBlock) actionsBlock.style.display = 'flex';

        if (!data.success) {
            showNotification(_getErrorMessage(data), 'error');
            return;
        }

        // Store draft id for export
        if (data.draft_id) currentDraftId = data.draft_id;

        // Render preview content
        await displayGeneratedOutputs(data.readme);
        goToStep(6);

    } catch (err) {
        clearInterval(statusInterval);
        if (loader) loader.style.display = 'none';
        if (actionsBlock) actionsBlock.style.display = 'flex';
        showNotification(`Generation request failed: ${err}`, 'error');
    }
}



// ── Mermaid text sanitizer — fix node labels without altering shape semantics ──
function sanitizeMermaidText(text) {
    if (!text) return '';

    return text.split('\n').map(line => {
        let sanitized = line;

        // 1. Quote unquoted multi-word square-bracket labels: A[My Label] → A["My Label"]
        //    But leave already-quoted labels alone: A["My Label"] stays
        sanitized = sanitized.replace(
            /([A-Za-z0-9_-]+)\[(?!")([^\]"]+)(?<!")\]/g,
            (match, id, label) => `${id}["${label.trim()}"]`
        );

        // 2. Quote unquoted diamond labels (decision nodes): C{Yes or No} → C{"Yes or No"}
        sanitized = sanitized.replace(
            /([A-Za-z0-9_-]+)\{(?!")([^}"]+)(?<!")\}/g,
            (match, id, label) => `${id}{"${label.trim()}"}`
        );

        // 3. Remove parentheses inside quoted labels that would break Mermaid
        //    e.g. A["foo (bar)"] → A["foo bar"]
        sanitized = sanitized.replace(
            /(\["[^"]*)\(([^)]*)\)([^"]*"\])/g,
            (match, before, content, after) => `${before}${content}${after}`
        );

        // 4. Sanitize edge labels with special chars: -->|label (with parens)| → -->|label|
        sanitized = sanitized.replace(/\|([^|]*)\(([^)]*)\)([^|]*)\|/g, '|$1$2$3|');

        return sanitized;
    }).join('\n');
}

// ── Safe Mermaid renderer — renders one div, falls back to code block on error ──
async function renderMermaidDiv(div) {
    const id = 'mermaid-' + Math.random().toString(36).substr(2, 9);
    const rawText = div.getAttribute('data-raw') || div.textContent.trim();
    const cleanText = sanitizeMermaidText(rawText);

    try {
        const { svg } = await mermaid.render(id, cleanText);
        div.innerHTML = svg;
        div.classList.add('mermaid-rendered');
    } catch (err) {
        console.warn('[Mermaid] Render failed, showing code block:', err.message || err);
        div.innerHTML = `<pre class="mermaid-fallback"><code>${escapeHtml(rawText)}</code></pre>`;
        div.classList.add('mermaid-error');
    }
}


// DISPLAY PREVIEWS IN STEP 6
async function displayGeneratedOutputs(readme) {
    try {
        // 1. Raw code editor
        const textarea = document.getElementById('raw-readme-text');
        textarea.value = readme;

        // 2. Render markdown visual preview (Marked + async Mermaid)
        const readmeBody = document.getElementById('rendered-readme-body');
        if (!readmeBody) {
            console.error("Element #rendered-readme-body not found");
            return;
        }

        // Parse markdown to HTML
        const html = marked.parse(readme);

        // Build a DOM from the parsed HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        // Convert ```mermaid code blocks into .mermaid divs before inserting
        doc.querySelectorAll('pre code.language-mermaid, pre code').forEach(codeNode => {
            const text = codeNode.textContent.trim();
            // Detect mermaid by class name or by content starting with known keywords
            const isMermaid = codeNode.className.includes('language-mermaid') ||
                /^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|gantt|pie|erDiagram)\b/.test(text);
            if (!isMermaid) return;

            const divNode = document.createElement('div');
            divNode.className = 'mermaid';
            divNode.setAttribute('data-raw', text); // preserve original text for renderer
            divNode.textContent = text;
            codeNode.parentElement.replaceWith(divNode);
        });

        readmeBody.innerHTML = doc.body.innerHTML;

        // Async render all mermaid divs
        const mermaidDivs = Array.from(readmeBody.querySelectorAll('.mermaid'));
        await Promise.allSettled(mermaidDivs.map(div => renderMermaidDiv(div)));

        // 3. Compute and render diff
        computeAndRenderDiff(readme);
    } catch (err) {
        console.error("Error in displayGeneratedOutputs:", err);
        showNotification("Error displaying output: " + err.message, 'error');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ─── Compare Tab — Side-by-Side Rendered View ─────────────────────────────

function computeAndRenderDiff(newReadme) {
    const oldReadme = scanContext?.existing_readme || '';
    const bodyOld = document.getElementById('diff-body-old');
    const bodyNew = document.getElementById('diff-body-new');

    // Word-count helper
    const wordCount = str => str.trim() ? str.trim().split(/\s+/).length : 0;

    const wcOld = wordCount(oldReadme);
    const wcNew = wordCount(newReadme);

    // Update stats bar word counts
    document.getElementById('diff-wc-old').textContent = wcOld.toLocaleString() + ' words';
    document.getElementById('diff-wc-new').textContent = wcNew.toLocaleString() + ' words';
    document.getElementById('diff-col-wc-old').textContent = wcOld.toLocaleString() + ' words';
    document.getElementById('diff-col-wc-new').textContent = wcNew.toLocaleString() + ' words';

    // Section extractor: returns array of heading strings (## foo)
    function extractSections(md) {
        return md.split('\n')
            .filter(l => /^#{1,3}\s/.test(l.trim()))
            .map(l => l.trim().replace(/^#+\s*/, '').toLowerCase());
    }

    const oldSections = new Set(extractSections(oldReadme));
    const newSections  = extractSections(newReadme);

    const addedSections   = newSections.filter(s => !oldSections.has(s));
    const removedSections = [...oldSections].filter(s => !newSections.includes(s));

    // Update stats bar counts
    document.getElementById('diff-stat-added-count').textContent   = addedSections.length;
    document.getElementById('diff-stat-removed-count').textContent = removedSections.length;

    // ── Render OLD column ──────────────────────────────────────────────────
    if (!oldReadme || oldReadme.trim() === '') {
        bodyOld.innerHTML = `
            <div class="diff-empty-state">
                <div class="diff-empty-state-icon">📭</div>
                <strong>No original README found</strong>
                <span>This is a freshly generated README — nothing to compare against.</span>
            </div>`;
        document.getElementById('diff-col-wc-old').textContent = '—';
        document.getElementById('diff-wc-old').textContent = '—';
    } else {
        bodyOld.innerHTML = typeof marked !== 'undefined'
            ? marked.parse(oldReadme)
            : '<pre>' + escapeHtml(oldReadme) + '</pre>';
    }

    // ── Render NEW column (with section highlights) ────────────────────────
    // We inject a marker span before each new-only heading so CSS can highlight it
    let annotatedNew = newReadme;
    if (addedSections.length > 0) {
        // Wrap headings that are new with a sentinel comment we'll handle post-render
        annotatedNew = newReadme.split('\n').map(line => {
            const stripped = line.trim().replace(/^#+\s*/, '').toLowerCase();
            if (/^#{1,3}\s/.test(line.trim()) && addedSections.includes(stripped)) {
                return `<!-- NEW_SECTION_START -->\n${line}`;
            }
            return line;
        }).join('\n');
    }

    if (typeof marked !== 'undefined') {
        bodyNew.innerHTML = marked.parse(annotatedNew);
    } else {
        bodyNew.innerHTML = '<pre>' + escapeHtml(newReadme) + '</pre>';
    }

    // Post-process: find comment nodes left in DOM and wrap siblings in highlight span
    // (marked.js strips comments, so we use a different approach: scan headings directly)
    if (addedSections.length > 0) {
        const headings = bodyNew.querySelectorAll('h1, h2, h3');
        headings.forEach(h => {
            const text = h.textContent.trim().toLowerCase();
            if (addedSections.includes(text)) {
                h.classList.add('diff-new-section');
            }
        });
    }

    // Render any mermaid blocks in both columns (async)
    if (typeof mermaid !== 'undefined') {
        [bodyOld, bodyNew].forEach(container => {
            container.querySelectorAll('pre code').forEach(block => {
                const text = block.textContent.trim();
                const isMermaid = (block.className || '').includes('mermaid') ||
                    /^(flowchart|graph|sequenceDiagram|classDiagram)\b/.test(text);
                if (!isMermaid) return;
                const div = document.createElement('div');
                div.className = 'mermaid';
                div.setAttribute('data-raw', text);
                div.textContent = text;
                block.parentElement.replaceWith(div);
            });
            Array.from(container.querySelectorAll('.mermaid'))
                .forEach(div => renderMermaidDiv(div));
        });
    }

    // ── Synchronized scrolling ─────────────────────────────────────────────
    _initDiffSyncScroll(bodyOld, bodyNew);
}

function _initDiffSyncScroll(panelA, panelB) {
    // Remove previous listeners by cloning
    const newA = panelA.cloneNode(true);
    const newB = panelB.cloneNode(true);
    panelA.parentNode.replaceChild(newA, panelA);
    panelB.parentNode.replaceChild(newB, panelB);

    let isSyncing = false;

    newA.addEventListener('scroll', () => {
        if (isSyncing) return;
        isSyncing = true;
        const ratio = newA.scrollTop / Math.max(1, newA.scrollHeight - newA.clientHeight);
        newB.scrollTop = ratio * (newB.scrollHeight - newB.clientHeight);
        requestAnimationFrame(() => { isSyncing = false; });
    });

    newB.addEventListener('scroll', () => {
        if (isSyncing) return;
        isSyncing = true;
        const ratio = newB.scrollTop / Math.max(1, newB.scrollHeight - newB.clientHeight);
        newA.scrollTop = ratio * (newA.scrollHeight - newA.clientHeight);
        requestAnimationFrame(() => { isSyncing = false; });
    });

    document.getElementById('diff-sbs-container')?.classList.add('synced');
}

// Keep computeDiff for any future use but it's no longer called by the UI
function computeDiff(oldLines, newLines) {
    const result = [];
    const m = oldLines.length;
    const n = newLines.length;

    const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));
    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (oldLines[i - 1] === newLines[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    let i = m, j = n;
    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && oldLines[i - 1] === newLines[j - 1]) {
            result.unshift({ type: 'context', value: oldLines[i - 1] });
            i--; j--;
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            result.unshift({ type: 'added', value: newLines[j - 1] });
            j--;
        } else {
            result.unshift({ type: 'removed', value: oldLines[i - 1] });
            i--;
        }
    }

    return result;
}

// OUTPUT TABS SWITCHER
function switchOutputTab(tabId) {
    document.querySelectorAll('.out-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.out-tab-content').forEach(content => content.classList.remove('active'));

    const btnMap = {
        'html-readme': 'preview',
        'diff-readme': 'compare',
        'raw-readme': 'markdown'
    };

    const btn = Array.from(document.querySelectorAll('.out-tab-btn')).find(b =>
        b.textContent.toLowerCase().includes(btnMap[tabId])
    );
    if (btn) btn.classList.add('active');

    const content = document.getElementById(`tab-${tabId}`);
    if (content) content.classList.add('active');
}

// ACTION BUTTON EXPORTS
function copyMarkdown() {
    const rawMarkdown = document.getElementById('raw-readme-text').value;
    if (!rawMarkdown) {
        showNotification('No README to copy. Generate one first.', 'error');
        return;
    }
    navigator.clipboard.writeText(rawMarkdown).then(() => {
        showNotification('Markdown copied to clipboard.', 'success');
    }).catch(err => {
        showNotification('Failed to copy: ' + err, 'error');
    });
}

function downloadReadme() {
    const rawMarkdown = document.getElementById('raw-readme-text').value;
    if (!rawMarkdown) {
        showNotification('No README to download. Generate one first.', 'error');
        return;
    }
    const blob = new Blob([rawMarkdown], { type: 'text/markdown; charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'README.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showNotification('README.md downloaded.', 'success');
}

// TOGGLE EVIDENCE PANEL in step 5
function toggleEvidence() {
    const container = document.getElementById('brief-evidence-container');
    if (!container) return;
    const isHidden = container.style.display === 'none' || container.style.display === '';
    container.style.display = isHidden ? 'block' : 'none';
}

// APP RESET
function resetApp() {
    scanContext = null;
    analysisContext = null;
    currentDraftId = '.readme_forge_draft';
    document.getElementById('repo-path-input').value = '';

    // Reset style selector to default (empty = auto-detect)
    const styleEl = document.getElementById('brief-style-select');
    if (styleEl) styleEl.value = '';

    goToStep(1);
}

// CUSTOM MINIMALIST TOAST NOTIFICATION
function showNotification(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    // Trigger transition animation
    setTimeout(() => toast.classList.add('show'), 50);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
