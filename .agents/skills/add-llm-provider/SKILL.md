---
name: add-llm-provider
description: Step-by-step guide to add a new LLM provider (e.g., Mistral, Cohere, Groq) to the githubReadmeForge multi-provider architecture.
---

# Add a New LLM Provider

Follow these steps to integrate a new LLM backend into the system.

## Step 1: Add Provider Method in `llm.py`

Open `readme_forge/llm.py` and add a new method following the existing pattern:

```python
def _generate_newprovider(self, system_prompt, user_prompt, response_format_json):
    # Import the provider's SDK
    from newprovider import Client
    client = Client(api_key=self.api_key)
    
    # Make the API call
    response = client.chat(
        model=self.model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.text
```

## Step 2: Register in `__init__` Auto-Configuration

In the `__init__` method of `LLMClient`, add an `elif` block:

```python
elif self.provider == "newprovider":
    self.api_key = self.api_key or os.getenv("NEWPROVIDER_API_KEY")
    self.model = self.model or "default-model-name"
```

## Step 3: Add to `generate()` Dispatcher

In the `generate()` method, add the routing:

```python
elif self.provider == "newprovider":
    return self._generate_newprovider(system_prompt, user_prompt, response_format_json)
```

## Step 4: Register in CLI Choices

In `readme_forge/cli.py`, update the `--provider` argument's `choices` list:

```python
choices=["gemini", "openai", "claude", "ollama", "newprovider", "mock"],
```

## Step 5: Register in Server Environment Map

In `server.py`, update the `env_map` dictionary in both `_handle_analyze` and `_handle_generate`:

```python
env_map = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "newprovider": "NEWPROVIDER_API_KEY"
}
```

## Step 6: Update `.env.example`

Add the new environment variable to `.env.example`:

```bash
# New Provider
NEWPROVIDER_API_KEY=your-newprovider-key
```

## Step 7: Add SDK to `requirements.txt`

```
newprovider-sdk>=1.0.0
```

## Key Rules

- The `generate()` method must always fall back to `_mock_generate()` on any exception
- Never log or print API keys
- If the provider supports JSON response format, honor the `response_format_json` parameter
- Add the provider to the Web UI dropdown in `web/index.html` if applicable
