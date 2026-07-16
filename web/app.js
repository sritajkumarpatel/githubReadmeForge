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

function computeAndRenderDiff(newReadme) {
    const oldReadme = scanContext?.existing_readme || '';
    const oldSide = document.getElementById('diff-old');
    const newSide = document.getElementById('diff-new');
    const summaryContent = document.getElementById('diff-summary-content');

    if (!oldReadme || oldReadme.trim() === '') {
        document.getElementById('diff-summary-content').innerHTML =
            '<div style="padding: 20px; color: var(--text-secondary);">No existing README found to compare. This is a new README generation.</div>';
        oldSide.innerHTML = '<div style="padding: 20px; color: var(--text-secondary);">No original README.</div>';
        newSide.innerHTML = escapeHtml(newReadme);
        return;
    }

    // Render both versions
    oldSide.innerHTML = escapeHtml(oldReadme);
    newSide.innerHTML = escapeHtml(newReadme);

    // Compute diff for summary
    const diff = computeDiff(oldReadme.split('\n'), newReadme.split('\n'));
    const summary = summarizeChanges(diff);
    renderSummary(summary, summaryContent);
}

function summarizeChanges(diff) {
    const changes = [];
    let currentSection = null;
    const sectionKeywords = ['#', '##', '###', '**', 'Features', 'Installation', 'Usage', 'Configuration', 'License', 'Contributing', 'FAQ', 'Getting Started', 'Prerequisites', 'Setup'];

    diff.forEach(part => {
        if (part.type === 'removed' || part.type === 'added') {
            const text = part.value.trim();
            // Check if it's a header
            const isHeader = sectionKeywords.some(kw => text.startsWith(kw));
            if (isHeader) {
                if (currentSection) {
                    changes.push(currentSection);
                }
                currentSection = {
                    title: text.substring(0, 60),
                    type: part.type,
                    lines: []
                };
            } else if (currentSection) {
                currentSection.lines.push({ type: part.type, text: text.substring(0, 80) });
            } else {
                currentSection = {
                    title: 'Other changes',
                    type: part.type,
                    lines: [{ type: part.type, text: text.substring(0, 80) }]
                };
            }
        }
    });

    if (currentSection) {
        changes.push(currentSection);
    }

    return changes.slice(0, 10);
}

function renderSummary(summary, container) {
    if (!summary || summary.length === 0) {
        container.innerHTML = '<div style="color: var(--text-secondary);">No significant changes detected.</div>';
        return;
    }

    let html = '';
    summary.forEach(item => {
        const icon = item.type === 'added' ? '+' : '-';
        const cls = item.type === 'added' ? 'added' : 'removed';
        html += `<div class="change-item ${cls}">
            <div class="change-title">${icon} ${escapeHtml(item.title)}</div>`;
        if (item.lines && item.lines.length > 0) {
            html += `<div class="change-desc">${escapeHtml(item.lines[0].text)}</div>`;
        }
        html += '</div>';
    });

    container.innerHTML = html;
}

function switchDiffTab(tab) {
    const oldSide = document.getElementById('diff-old');
    const newSide = document.getElementById('diff-new');
    const tabs = document.querySelectorAll('.diff-tab');

    tabs.forEach(t => t.classList.remove('active'));
    if (tab === 'old') {
        oldSide.style.display = 'block';
        newSide.style.display = 'none';
        tabs[0].classList.add('active');
    } else {
        oldSide.style.display = 'none';
        newSide.style.display = 'block';
        tabs[1].classList.add('active');
    }
}

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
            i--;
            j--;
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
