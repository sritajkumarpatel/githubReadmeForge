// githubReadmeForge Frontend App Controller
let currentStep = 1;
let scanContext = null;
let analysisContext = null;
let providerConfig = {
    provider: '',
    model: '',
    api_key: '',
    ollama_host: 'http://localhost:11434'
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

function _restoreProviderPrefs() {
    try {
        const provider = localStorage.getItem(LS_PROVIDER);
        const model    = localStorage.getItem(LS_MODEL);
        const host     = localStorage.getItem(LS_HOST);

        if (provider) {
            const sel = document.getElementById('provider-select');
            if (sel) {
                sel.value = provider;
                handleProviderChange(); // show/hide api-key / host fields
            }
        }
        if (model) {
            const ms = document.getElementById('model-select');
            if (ms) {
                // Add option if not present (saved model may not be in the default list)
                if (!ms.querySelector(`option[value="${model}"]`)) {
                    const opt = document.createElement('option');
                    opt.value = model;
                    opt.textContent = model;
                    ms.appendChild(opt);
                }
                ms.value = model;
            }
        }
        if (host) {
            const hi = document.getElementById('ollama-host-input');
            if (hi) hi.value = host;
        }
    } catch (e) { /* ignore */ }
}

// ── Contextual error hints from server error_type ─────────────────────────
function _getErrorMessage(data) {
    const hint = data.hint ? `\n\n💡 ${data.hint}` : '';
    return (data.error || 'An unknown error occurred.') + hint;
}

// Initialize marked
marked.setOptions({
    breaks: true,
    gfm: true
});

// Initialize mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark'
});

// Restore saved provider prefs once DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    _restoreProviderPrefs();
});

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
function handleProviderChange() {
    const provider = document.getElementById('provider-select').value;
    const apiKeyGroup = document.getElementById('api-key-group');
    const modelGroup = document.getElementById('model-group');
    const ollamaGroup = document.getElementById('ollama-host-group');
    const opencodeGroup = document.getElementById('opencode-host-group');

    apiKeyGroup.style.display = 'none';
    modelGroup.style.display = 'none';
    ollamaGroup.style.display = 'none';
    opencodeGroup.style.display = 'none';

    if (provider === 'ollama') {
        modelGroup.style.display = 'flex';
        ollamaGroup.style.display = 'flex';
        fetchModels();
    } else if (provider === 'opencode') {
        opencodeGroup.style.display = 'flex';
        modelGroup.style.display = 'flex';
        fetchModels();
    } else {
        apiKeyGroup.style.display = 'flex';
    }
}

async function fetchModels() {
    const provider = document.getElementById('provider-select').value;
    const apiKey = document.getElementById('api-key-input').value.trim();
    const modelGroup = document.getElementById('model-group');
    const modelSelect = document.getElementById('model-select');
    const modelLoading = document.getElementById('model-loading');

    if (provider === 'ollama' || provider === 'opencode') {
        return;
    }

    if (!apiKey) {
        return;
    }

    modelGroup.style.display = 'flex';
    modelLoading.style.display = 'inline-block';
    modelSelect.innerHTML = '<option value="">Loading...</option>';

    try {
        const response = await fetch('/api/models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider, api_key: apiKey })
        });
        const data = await response.json();

        modelLoading.style.display = 'none';

        if (data.success && data.models.length > 0) {
            modelSelect.innerHTML = '<option value="">Select a model...</option>';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
        } else if (data.error) {
            modelSelect.innerHTML = '<option value="">Error loading models</option>';
            showNotification('Failed to fetch models: ' + data.error, 'error');
        } else {
            modelSelect.innerHTML = '<option value="">No models found</option>';
        }
    } catch (err) {
        modelLoading.style.display = 'none';
        modelSelect.innerHTML = '<option value="">Error</option>';
        showNotification('Failed to fetch models: ' + err.message, 'error');
    }
}

// VALIDATE STEP 2 CONFIG
function validateLLMConfig() {
    const provider = document.getElementById('provider-select').value;
    const apiKey = document.getElementById('api-key-input').value.trim();
    const modelSelect = document.getElementById('model-select');
    const model = provider === 'ollama' ? 'llama3' : (provider === 'opencode' ? 'claude-3-5-sonnet-20241022' : (modelSelect.value || ''));
    const ollamaHost = document.getElementById('ollama-host-input').value.trim();
    const opencodeHost = document.getElementById('opencode-host-input').value.trim();

    if (provider !== 'ollama' && provider !== 'opencode' && !apiKey) {
        showNotification('API Key is required for the selected provider.', 'error');
        return;
    }

    if (!model && provider !== 'ollama' && provider !== 'opencode') {
        showNotification('Please select or enter a model.', 'error');
        return;
    }

    providerConfig = {
        provider: provider,
        api_key: apiKey,
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
        showNotification('Please specify a repository link or local directory path.', 'error');
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
    // 1. Score gauge
    const scoreText = document.getElementById('score-text');
    scoreText.textContent = score;
    const scoreCircle = document.querySelector('.score-circle');
    // Calculate degree gradient border (360 degrees * (score/100))
    const deg = Math.round((score / 100) * 360);
    scoreCircle.style.setProperty('--score-deg', deg);

    // 2. Persona summary
    const personaText = document.getElementById('dashboard-persona');
    personaText.textContent = analysis.project_persona || "A codebase repository.";

    // 3. Tech Stack pills
    const techStack = document.getElementById('dashboard-tech-stack');
    techStack.innerHTML = '';
    const stack = analysis.tech_stack || [];
    stack.forEach(tech => {
        const pill = document.createElement('span');
        pill.className = 'tech-pill';
        pill.textContent = tech;
        techStack.appendChild(pill);
    });

    // 4. Improvements table rows
    const tbody = document.getElementById('improvements-tbody');
    tbody.innerHTML = '';
    const improvements = analysis.improvements || [];
    
    if (improvements.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No improvement gaps identified. Your README is in top shape!</td></tr>`;
        return;
    }

    improvements.forEach(imp => {
        const tr = document.createElement('tr');
        const badgeClass = (imp.type || 'general').toLowerCase();
        
        tr.innerHTML = `
            <td><strong style="color: var(--text-secondary);">${imp.id || 'N/A'}</strong></td>
            <td><span class="imp-badge ${badgeClass}">${imp.type || 'General'}</span></td>
            <td><strong>${imp.title || 'Enhancement Opportunity'}</strong></td>
            <td style="color: var(--text-secondary); font-size: 0.9rem;">${imp.description || ''}</td>
        `;
        tbody.appendChild(tr);
    });
}

// // STYLE SELECTION STATE
let selectedStyle = 'visual_rich';

function selectStyle(styleName) {
    selectedStyle = styleName;
    document.querySelectorAll('.style-card').forEach(card => {
        card.classList.remove('active');
        if (card.getAttribute('data-style') === styleName) {
            card.classList.add('active');
        }
    });
}

// GENERATION API CALL
async function startGeneration(isInstant, compiledAnswers = '') {
    // Use dashboard loader on step 4 instead of jumping to ingest
    const loader = document.getElementById('dashboard-loader');
    const loaderStatus = document.getElementById('dashboard-loader-status');
    const dashboardActions = document.getElementById('dashboard-actions');

    // Display loader overlay on dashboard
    loader.style.display = 'flex';
    if (dashboardActions) dashboardActions.style.display = 'none';
    loaderStatus.textContent = "Writer Agent forging markdown README.md & showroom page...";

    const statusMessages = [
        "Writer Agent preparing README structure...",
        "Writer Agent drafting narrative sections...",
        "Writer Agent generating code examples...",
        "Writer Agent building showroom showcase..."
    ];
    let msgIdx = 0;
    const statusInterval = setInterval(() => {
        if (msgIdx < statusMessages.length) {
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
                base_url: providerConfig.provider === 'ollama' ? providerConfig.ollama_host : providerConfig.opencode_host,
                custom_answers: isInstant ? '' : compiledAnswers,
                style: selectedStyle,
                lang: document.getElementById('lang-select').value
            })
        });

        clearInterval(statusInterval);
        const data = await response.json();
        loader.style.display = 'none';
        if (dashboardActions) dashboardActions.style.display = 'flex';

        if (!data.success) {
            showNotification(`Generation failed: ${data.error}`, 'error');
            return;
        }

        // Render preview content
        displayGeneratedOutputs(data.readme, data.showroom);

        goToStep(5);

    } catch (err) {
        clearInterval(statusInterval);
        loader.style.display = 'none';
        if (dashboardActions) dashboardActions.style.display = 'flex';
        showNotification(`Generation request failed: ${err}`, 'error');
    }
}

// DISPLAY PREVIEWS IN STEP 6
function displayGeneratedOutputs(readme, showroom) {
    try {
        // 1. Raw code editor
        const textarea = document.getElementById('raw-readme-text');
        textarea.value = readme;

        // 2. Render markdown visual preview (Marked + post process Mermaid)
        const readmeBody = document.getElementById('rendered-readme-body');
        if (!readmeBody) {
            console.error("Element #rendered-readme-body not found");
            return;
        }

        let html = marked.parse(readme);

        // Convert code blocks with language-mermaid into divs to render
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const mermaidCodes = doc.querySelectorAll('pre code.language-mermaid');

        mermaidCodes.forEach(codeNode => {
            const preNode = codeNode.parentElement;
            const divNode = document.createElement('div');
            divNode.className = 'mermaid';
            divNode.textContent = codeNode.textContent.trim();
            preNode.replaceWith(divNode);
        });

        readmeBody.innerHTML = doc.body.innerHTML;

        // Render mermaid diagrams safely
        const mermaidDivs = readmeBody.querySelectorAll('.mermaid');
        if (mermaidDivs.length > 0) {
            mermaidDivs.forEach(div => {
                try {
                    const id = 'mermaid-' + Math.random().toString(36).substr(2, 9);
                    mermaid.render(id, div.textContent.trim()).then(svg => {
                        div.innerHTML = svg;
                    }).catch(err => {
                        console.warn("Mermaid render failed, showing code:", err);
                        div.innerHTML = '<pre>' + div.textContent.trim() + '</pre>';
                    });
                } catch (err) {
                    console.warn("Mermaid error:", err);
                    div.innerHTML = '<pre>' + div.textContent.trim() + '</pre>';
                }
            });
        }

        // 3. Compute and render diff
        computeAndRenderDiff(readme);

        // 4. Render Showroom webpage inside iframe
        const iframe = document.getElementById('showroom-preview-iframe');
        if (!iframe) {
            console.error("Element #showroom-preview-iframe not found");
            return;
        }
        iframe.srcdoc = showroom || '';
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

    // Render any mermaid blocks in both columns
    if (typeof mermaid !== 'undefined') {
        [bodyOld, bodyNew].forEach(container => {
            container.querySelectorAll('pre code').forEach(block => {
                const lang = block.className || '';
                if (lang.includes('mermaid') || block.textContent.trim().startsWith('flowchart') || block.textContent.trim().startsWith('graph')) {
                    const div = document.createElement('div');
                    div.className = 'mermaid';
                    div.textContent = block.textContent;
                    block.parentElement.replaceWith(div);
                }
            });
            try {
                mermaid.run({ nodes: container.querySelectorAll('.mermaid') }).catch(() => {});
            } catch (e) {}
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
    navigator.clipboard.writeText(rawMarkdown).then(() => {
        showNotification('README markdown copied to clipboard successfully!', 'success');
    }).catch(err => {
        showNotification('Failed to copy: ' + err, 'error');
    });
}

function downloadShowroom() {
    const iframe = document.getElementById('showroom-preview-iframe');
    const htmlContent = iframe.srcdoc;
    if (!htmlContent) {
        showNotification('No showroom HTML content found.', 'error');
        return;
    }

    const blob = new Blob([htmlContent], { type: 'text/html; charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'showroom.html';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// APP RESET
function resetApp() {
    scanContext = null;
    analysisContext = null;
    selectedStyle = 'visual_rich';
    document.getElementById('repo-path-input').value = '.';

    document.querySelectorAll('.style-card').forEach(card => {
        card.classList.remove('active');
        if (card.getAttribute('data-style') === 'visual_rich') {
            card.classList.add('active');
        }
    });

    goToStep(1);
}

// On page load
window.onload = function() {
    handleProviderChange();
};

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
