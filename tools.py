"""
tools.py — Tool definitions (schemas) and handlers (implementations).

Each tool has two parts:
  1. A schema dict that tells the LLM what the tool is and what arguments it takes.
  2. A handler function that actually runs when the LLM decides to call that tool.
"""

import os
import sys
import math
import subprocess
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────
# TOOL SCHEMAS
# These are sent to the LLM so it knows what tools exist.
# The LLM never sees the handler code — only this schema.
# ─────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current information. Use this when you need facts, "
            "news, documentation, or anything that might be outside your training data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "run_python",
        "description": (
            "Execute Python code in a subprocess and return stdout + stderr. "
            "Use this for calculations, data processing, or anything that needs "
            "actual computation. The code runs in an isolated process."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Valid Python 3 code to execute.",
                }
            },
            "required": ["code"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file from disk and return them as a string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write text content to a file on disk. Creates the file if it doesn't "
            "exist; overwrites if it does."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path where the file should be written.",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write into the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "calculator",
        "description": (
            "Evaluate a mathematical expression and return the result. "
            "Supports standard arithmetic and math module functions (sqrt, sin, cos, log, etc.)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A Python-compatible math expression, e.g. '2 ** 10' or 'sqrt(144)'.",
                }
            },
            "required": ["expression"],
        },
    },
]


# ─────────────────────────────────────────────
# TOOL HANDLERS
# ─────────────────────────────────────────────

def handle_web_search(query: str) -> str:
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "Error: TAVILY_API_KEY not set in environment."
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=5)
        results = []
        for r in response.get("results", []):
            results.append(f"[{r['title']}]\n{r['url']}\n{r['content']}\n")
        return "\n---\n".join(results) if results else "No results found."
    except ImportError:
        return "Error: tavily-python not installed. Run: pip install tavily-python"
    except Exception as e:
        return f"Web search error: {e}"


def handle_run_python(code: str) -> str:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp_path = f.name
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out after 30 seconds."
    except Exception as e:
        return f"Execution error: {e}"
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass


def handle_read_file(path: str) -> str:
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"Error: File not found at '{path}'"
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"File read error: {e}"


def handle_write_file(path: str, content: str) -> str:
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to '{path}'"
    except Exception as e:
        return f"File write error: {e}"


def handle_calculator(expression: str) -> str:
    try:
        allowed_names = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        allowed_names["__builtins__"] = {}
        result = eval(expression, allowed_names)
        return str(result)
    except Exception as e:
        return f"Calculator error: {e}"


# ─────────────────────────────────────────────
# DISPATCHER
# ─────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    handlers = {
        "web_search": lambda i: handle_web_search(i["query"]),
        "run_python":  lambda i: handle_run_python(i["code"]),
        "read_file":   lambda i: handle_read_file(i["path"]),
        "write_file":  lambda i: handle_write_file(i["path"], i["content"]),
        "calculator":  lambda i: handle_calculator(i["expression"]),
    }
    handler = handlers.get(tool_name)
    if not handler:
        return f"Error: Unknown tool '{tool_name}'"
    return handler(tool_input)