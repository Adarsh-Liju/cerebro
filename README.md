# Inference Agent — Phase 1

A minimal ReAct agent that can reason and use tools to complete tasks.
Supports both Anthropic (Claude) and local Ollama backends.

## Setup

```bash
cd cerebro
uv sync

cp .env .env.bak   # back up first if needed
# Edit .env and add your ANTHROPIC_API_KEY and TAVILY_API_KEY
```

## Running

```bash
# Interactive mode (Anthropic backend)
python main.py

# Interactive mode (local Ollama backend)
python main.py --backend ollama

# Single task, non-interactive
python main.py --task "What is the GDP of Australia in 2024?"
python main.py --task "Write a Python function to compute Fibonacci numbers and save it to fib.py"

# Quiet mode (no step-by-step output)
python main.py --quiet
```

## Ollama setup (local inference on your RTX 4060)

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

## Project structure

```
cerebro/
├── main.py             # CLI entry point
├── loop.py             # ReAct loop — the core engine
├── tools.py            # tool schemas + handlers + dispatcher
├── prompts.py          # system prompt
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
```# Cerebro
