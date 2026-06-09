# Cerebro

A minimal ReAct agent that reasons step-by-step and uses tools to complete tasks. Supports both Anthropic (Claude) and local Ollama backends.

## Setup

```bash
cd Cerebro
uv sync

cp .env .env.bak   # back up first if needed
# Create .env with your ANTHROPIC_API_KEY and TAVILY_API_KEY (see Environment variables below)
```

Requires Python 3.14+.

## Running

```bash
# Interactive mode (Anthropic backend)
python main.py

# Interactive mode (local Ollama backend)
python main.py --backend ollama

# Single task, non-interactive
python main.py --task "What is the GDP of Australia in 2024?"
python main.py --task "Write a Python function to compute Fibonacci numbers and save it to fib.py"

# Limit agent steps (default: 10)
python main.py --task "..." --max-steps 20

# Quiet mode (no step-by-step output)
python main.py --quiet
```

In interactive mode, type `exit` or press Ctrl+C to quit. Conversation history is carried across turns within a session.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LLM_BACKEND` | `anthropic` | `anthropic` or `ollama` |
| `ANTHROPIC_API_KEY` | — | Required when using Anthropic |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model name |
| `TAVILY_API_KEY` | — | Required for `web_search` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1` | Local model name |

CLI flags override env vars where applicable (e.g. `--backend`).

## Ollama setup (local inference)

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.1        # 8B model, fits in 8GB VRAM at 4-bit
ollama pull qwen2.5         # alternative, strong at coding tasks
ollama serve                # start the server (runs on :11434)
```

Then set in `.env`:

```
LLM_BACKEND=ollama
OLLAMA_MODEL=llama3.1
```

## Tools

The agent can call these tools during a task:

| Tool | Purpose |
|---|---|
| `web_search` | Look up current facts via Tavily |
| `run_python` | Execute Python code in a subprocess (30s timeout) |
| `read_file` | Read a file from disk |
| `write_file` | Write or overwrite a file |
| `calculator` | Evaluate a math expression (`sqrt`, `sin`, etc.) |

## Project structure

```
Cerebro/
├── main.py             # CLI entry point
├── loop.py             # ReAct loop — the core engine
├── tools.py            # Tool schemas, handlers, and dispatcher
├── prompts.py          # System prompt
├── pyproject.toml
├── uv.lock
└── .env
```

## How the ReAct loop works

```
User task
    │
    ▼
LLM reasons about task
    │
    ├── stop_reason = end_turn  ──► return final answer
    │
    └── stop_reason = tool_use
            │
            ▼
        dispatch_tool(name, args)
            │
            ▼
        append tool result to messages
            │
            ▼
        loop again (up to max_steps)
```

## Tests

```bash
uv run pytest
```
