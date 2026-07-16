---
name: improve-generation-prompt
description: Guide to improving the quality and depth of generated README output by modifying the writer system prompt, analyzer schema, and reader context extraction.
---

# Improve README Generation Quality

The quality of generated READMEs is controlled by three interconnected components. Changes should flow bottom-up: Reader → Analyzer → Writer.

## Understanding the Data Pipeline

```
ReaderAgent (scan_results)
    ↓ tree, configs, code_context, existing_readme
AnalyzerAgent (analysis JSON)
    ↓ tech_stack, project_persona, features, connections, config_variables
WriterAgent (system_prompt + user_prompt)
    ↓ Final README markdown
```

The Writer can only generate content that the Analyzer extracted, and the Analyzer can only work with what the Reader scanned. **If the output is missing something, trace backward to find where the data was lost.**

## Adding a New Section to Generated READMEs

### 1. Ensure the Reader Captures the Data

In `readme_forge/agents/reader.py`:
- If the section needs data from specific file types (e.g., `.env` files for config docs), add them to `_read_config_files()`
- If it needs deeper code context, increase `max_files` or `content[:N]` limits in `_read_primary_source_files()`

### 2. Add Fields to the Analyzer JSON Schema

In `readme_forge/agents/analyzer.py`, update the JSON schema in the `system_prompt`:

```python
"new_field": [
    {"name": "...", "description": "..."}
]
```

Also update the fallback structure in the `except` block to include a default value for the new field.

### 3. Pass the Data to the Writer Prompt

In `readme_forge/agents/writer.py`, update the `user_prompt` construction to include the new analysis field:

```python
f"New Field Data: {analysis.get('new_field')}\n"
```

### 4. Instruct the Writer to Use It

In the `system_prompt` within `writer.py`, add the section to the **Visitor-First Layout Hierarchy**:

```python
"N. **New Section**: Description of what to write and how to format it.\n"
```

### 5. Update the Mock Template

In `readme_forge/llm.py`, update both:
- `_mock_generate()` analyzer JSON response — add sample data for the new field
- `_mock_generate()` README template — add the rendered section

## Prompt Engineering Tips

- **Be specific**: "Write a 2-paragraph narrative explaining the problem this tool solves" > "Describe what the project does"
- **Provide format examples**: Show the exact markdown structure you want
- **Use the analysis data**: Reference specific fields: "Use the `key_features` array to create a feature grid"
- **Mandate depth**: "Each feature must have a title, description, and concrete example"
- **Forbid shallowness**: "Do NOT use generic descriptions. Extract specific details from the code context."

## Testing Changes

1. **Mock mode first**: Run `python main.py --path . --instant --provider mock` to verify the template renders correctly
2. **Real LLM**: Set `GEMINI_API_KEY` and run with `--provider gemini` to verify the prompt produces good output
3. **Web UI**: Start `python server.py` and test through the browser dashboard
