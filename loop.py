"""
loop.py — The core ReAct agent loop.

This is the heart of the agent. It:
  1. Sends the user message + conversation history to the LLM.
  2. If the LLM calls a tool, runs the tool and feeds the result back.
  3. Repeats until the LLM gives a final text response or max steps is hit.

Supports both Anthropic and Ollama backends, switchable via LLM_BACKEND env var.
"""

import os
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT
from tools import TOOL_SCHEMAS, dispatch_tool

load_dotenv()


# ─────────────────────────────────────────────
# BACKEND: ANTHROPIC
# ─────────────────────────────────────────────

def _run_anthropic(messages: list, verbose: bool) -> tuple[str, list]:
    """
    Single pass through the Anthropic API.
    Returns (final_text, updated_messages).
    Handles tool calls internally if the model requests them.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOL_SCHEMAS,
        messages=messages,
    )

    if verbose:
        print(f"  [stop_reason: {response.stop_reason}]")

    # Append the assistant's full response to history
    messages.append({"role": "assistant", "content": response.content})

    # If the model is done — return the text
    if response.stop_reason == "end_turn":
        text = " ".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        return text, messages

    # If the model wants to use tools — run them and return results
    if response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if verbose:
                    print(f"  → Tool call: {block.name}({block.input})")

                result = dispatch_tool(block.name, block.input)

                if verbose:
                    preview = result[:200] + "..." if len(result) > 200 else result
                    print(f"  ← Tool result: {preview}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "user", "content": tool_results})
        return None, messages  # None = not done yet, loop again

    # Unexpected stop reason
    return f"Unexpected stop_reason: {response.stop_reason}", messages


# ─────────────────────────────────────────────
# BACKEND: OLLAMA (OpenAI-compatible)
# ─────────────────────────────────────────────

def _run_ollama(messages: list, verbose: bool) -> tuple[str, list]:
    """
    Single pass through a local Ollama model using the OpenAI-compatible API.
    Ollama must be running: `ollama serve`
    Model must be pulled: `ollama pull llama3.1`
    """
    import json
    from openai import OpenAI

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.1")

    client = OpenAI(base_url=f"{base_url}/v1", api_key="ollama")

    # Convert Anthropic-style tool schemas to OpenAI-style
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOL_SCHEMAS
    ]

    # Prepend system message for OpenAI-style API
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    response = client.chat.completions.create(
        model=model,
        messages=full_messages,
        tools=openai_tools,
        tool_choice="auto",
    )

    choice = response.choices[0]
    message = choice.message

    if verbose:
        print(f"  [finish_reason: {choice.finish_reason}]")

    # Append assistant message to history
    assistant_msg = {"role": "assistant", "content": message.content or ""}
    if message.tool_calls:
        assistant_msg["tool_calls"] = message.tool_calls
    messages.append(assistant_msg)

    if choice.finish_reason == "stop":
        return message.content or "", messages

    if choice.finish_reason == "tool_calls":
        tool_results = []
        for tc in message.tool_calls:
            args = json.loads(tc.function.arguments)
            if verbose:
                print(f"  → Tool call: {tc.function.name}({args})")

            result = dispatch_tool(tc.function.name, args)

            if verbose:
                preview = result[:200] + "..." if len(result) > 200 else result
                print(f"  ← Tool result: {preview}")

            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        messages.extend(tool_results)
        return None, messages

    return f"Unexpected finish_reason: {choice.finish_reason}", messages


# ─────────────────────────────────────────────
# PUBLIC: run_agent
# ─────────────────────────────────────────────

def run_agent(
    user_task: str,
    history: list | None = None,
    max_steps: int = 10,
    verbose: bool = True,
) -> str:
    """
    Run the agent on a task and return the final answer as a string.

    Args:
        user_task:  The user's request.
        history:    Optional prior conversation messages (enables multi-turn use).
        max_steps:  Maximum number of LLM calls before giving up.
        verbose:    Print tool calls and results to stdout.

    Returns:
        The agent's final answer as a string.
    """
    backend = os.getenv("LLM_BACKEND", "anthropic").lower()
    step_fn = _run_anthropic if backend == "anthropic" else _run_ollama

    messages = list(history or [])
    messages.append({"role": "user", "content": user_task})

    if verbose:
        print(f"\n[Agent] Backend: {backend} | Max steps: {max_steps}")
        print(f"[Agent] Task: {user_task}\n")

    for step in range(1, max_steps + 1):
        if verbose:
            print(f"[Step {step}]")

        result, messages = step_fn(messages, verbose)

        if result is not None:
            if verbose:
                print(f"\n[Agent] Done in {step} step(s).")
            return result

    return "Error: Agent reached maximum steps without completing the task."