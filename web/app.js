// githubReadmeForge Frontend App Controller
let currentStep = 1;
let scanContext = null;
let analysisContext = null;
let providerConfig = {
    provider: 'mock',
    model: '',
    api_key: '',
    ollama_host: 'http://localhost:11434'
};
let isGuidedMode = false;

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

    // Update step dots classes
    document.querySelectorAll('.step-dot').forEach(dot => {
        const dotStep = parseInt(dot.getAttribute('data-step'));
        dot.classList.remove('active');
        if (dotStep === step) {
            dot.classList.add('active');
        }
        if (dotStep < step) {
            dot.classList.add('completed');
        } else {
            dot.classList.remove('completed');
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

    if (provider === 'mock') {
        return;
    }

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

    if (provider === 'mock' || provider === 'ollama' || provider === 'opencode') {
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

    if (provider !== 'mock' && provider !== 'ollama' && provider !== 'opencode' && !apiKey) {
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

// ROUTE SELECT METHOD & TERMINAL CONSOLE VARIABLES
const terminalQuestions = [
    {
        key: 'style_confirmation',
        prompt: (style) => `Agent: You have selected the '${style}' layout style. Do you want to use this layout, or override it now?\n(Type 'yes' to proceed, or specify override: visual_rich, minimalist, enterprise)`
    },
    {
        key: 'custom_persona',
        prompt: () => `Agent: Refine the project description/summary if you'd like. (Type 'no' or press Enter to skip)`
    },
    {
        key: 'custom_sections',
        prompt: () => `Agent: Specify any custom documentation sections to append (e.g. CLI argument table, Docker setups). (Type 'no' or press Enter to skip)`
    },
    {
        key: 'custom_examples',
        prompt: () => `Agent: Provide a code snippet or usage command to feature in the Examples block. (Type 'no' or press Enter to skip)`
    },
    {
        key: 'custom_contact',
        prompt: () => `Agent: Provide support details or contact emails. (Type 'no' or press Enter to skip)`
    }
];

let terminalQIndex = 0;
let terminalAnswers = {};

function printTerminalLine(text, type = 'agent') {
    const log = document.getElementById('terminal-log');
    if (!log) return;
    
    const line = document.createElement('div');
    line.className = `terminal-line ${type}`;
    line.textContent = text;
    log.appendChild(line);
    
    // Scroll to bottom
    const body = document.getElementById('terminal-body');
    if (body) {
        log.scrollTop = log.scrollHeight;
    }
}

function showGuidedSetup() {
    isGuidedMode = true;
    goToStep(5);
    
    // Reset Terminal Console State
    terminalQIndex = 0;
    terminalAnswers = {};
    
    const log = document.getElementById('terminal-log');
    if (log) log.innerHTML = '';
    
    printTerminalLine("Agent: Launching interactive terminal configurations loop. Strict guardrails active.", "system");
    printTerminalLine(terminalQuestions[0].prompt(selectedStyle), "agent");
    
    // Focus input
    setTimeout(() => {
        const input = document.getElementById('terminal-input');
        if (input) input.focus();
    }, 100);
}

// CLIENT-SIDE GUARDRAIL CHECKER
function isOffTopic(input) {
    const text = input.toLowerCase().trim();
    const offTopicKeywords = [
        "write a program", "write a function", "write code to", "write a script",
        "sum program", "calculator program", "write a sum", "solve this", "math program",
        "create a program", "build a program", "coding script", "program that", "math solver"
    ];
    return offTopicKeywords.some(keyword => text.includes(keyword));
}

// PROCESS TERMINAL CONSOLE INPUT
function handleTerminalInput(value) {
    const trimmed = value.trim();
    printTerminalLine(`forge_user $ ${value}`, "user");
    
    if (!trimmed) {
        // Handle empty input as skipping
        processAnswer("");
        return;
    }
    
    // Check Guardrails
    if (isOffTopic(trimmed)) {
        printTerminalLine("Agent [Error]: Rejection - This request is unrelated to README generation. Please ask documentation-related questions.", "error");
        return;
    }
    
    processAnswer(trimmed);
}

function processAnswer(answer) {
    const currentQ = terminalQuestions[terminalQIndex];
    
    if (currentQ.key === 'style_confirmation') {
        const val = answer.toLowerCase();
        if (val === 'visual_rich' || val === 'minimalist' || val === 'enterprise') {
            selectStyle(val);
            printTerminalLine(`[System] Style layout overridden to '${selectedStyle}'.`, "system");
        } else {
            printTerminalLine(`[System] Preserving selected layout style: '${selectedStyle}'.`, "system");
        }
    } else {
        if (answer && answer.toLowerCase() !== 'no') {
            terminalAnswers[currentQ.key] = answer;
        }
    }
    
    // Next question
    terminalQIndex++;
    
    if (terminalQIndex < terminalQuestions.length) {
        // Ask next
        printTerminalLine(terminalQuestions[terminalQIndex].prompt(), "agent");
    } else {
        // Finish Q&A
        printTerminalLine("[System] Submitting configuration parameters. Orchestrating agents...", "system");
        
        // Compile answers block
        const answersList = [];
        if (terminalAnswers.custom_persona) answersList.push(`- Project Summary Override: ${terminalAnswers.custom_persona}`);
        if (terminalAnswers.custom_sections) answersList.push(`- Custom Sections: ${terminalAnswers.custom_sections}`);
        if (terminalAnswers.custom_examples) answersList.push(`- Custom Usage Examples Code:\n\`\`\`\n${terminalAnswers.custom_examples}\n\`\`\``);
        if (terminalAnswers.custom_contact) answersList.push(`- Support Contacts: ${terminalAnswers.custom_contact}`);

        const customAnswers = answersList.join('\n');
        startGeneration(false, customAnswers);
    }
}

// GENERATION API CALL
async function startGeneration(isInstant, compiledAnswers = '') {
    // Prepare loader in current pane or transition to temporary step
    const loader = document.getElementById('ingest-loader');
    const actions = document.getElementById('ingest-actions');
    const loaderStatus = document.getElementById('loader-status');

    // Display loader overlay
    loader.style.display = 'flex';
    actions.style.display = 'none';
    loaderStatus.textContent = "Writer Agent forging markdown README.md & showroom page...";
    
    // Jump to ingest page temporarily to show progress
    goToStep(3);

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

        const data = await response.json();
        loader.style.display = 'none';
        actions.style.display = 'flex';

        if (!data.success) {
            showNotification(`Generation failed: ${data.error}`, 'error');
            goToStep(isInstant ? 4 : 5);
            return;
        }

        // Render preview content
        displayGeneratedOutputs(data.readme, data.showroom);
        
        // Hide Q&A step 5 indicator if instant mode was chosen
        if (isInstant) {
            document.getElementById('qa-indicator').style.display = 'none';
        }

        goToStep(6);

    } catch (err) {
        loader.style.display = 'none';
        actions.style.display = 'flex';
        showNotification(`Generation request failed: ${err}`, 'error');
        goToStep(isInstant ? 4 : 5);
    }
}

// DISPLAY PREVIEWS IN STEP 6
function displayGeneratedOutputs(readme, showroom) {
    // 1. Raw code editor
    const textarea = document.getElementById('raw-readme-text');
    textarea.value = readme;

    // 2. Render markdown visual preview (Marked + post process Mermaid)
    const readmeBody = document.getElementById('rendered-readme-body');
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

    // Trigger mermaid rendering safely
    try {
        mermaid.run({ querySelector: '.mermaid' });
    } catch (err) {
        console.error("Mermaid canvas rendering error:", err);
    }

    // 3. Render Showroom webpage inside iframe
    const iframe = document.getElementById('showroom-preview-iframe');
    iframe.srcdoc = showroom;
}

// OUTPUT TABS SWITCHER
function switchOutputTab(tabId) {
    document.querySelectorAll('.out-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.out-tab-content').forEach(content => content.classList.remove('active'));

    const btn = Array.from(document.querySelectorAll('.out-tab-btn')).find(b => b.textContent.toLowerCase().includes(tabId.split('-')[1]));
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
    isGuidedMode = false;
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
    
    // Terminal input listener
    const termInput = document.getElementById('terminal-input');
    if (termInput) {
        termInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const val = termInput.value;
                termInput.value = '';
                handleTerminalInput(val);
            }
        });
    }
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
