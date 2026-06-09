"""
main.py — Entry point. Run the agent interactively from the terminal.

Usage:
    python main.py
    python main.py --backend ollama
    python main.py --task "What is the square root of 12345?"
"""

import argparse
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from loop import run_agent


def parse_args():
    parser = argparse.ArgumentParser(description="Inference Agent - Phase 1")
    parser.add_argument(
        "--backend",
        choices=["anthropic", "ollama"],
        default=None,
        help="LLM backend to use. Overrides LLM_BACKEND env var.",
    )
    parser.add_argument(
        "--task",
        type=str,
        default=None,
        help="Run a single task non-interactively and exit.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=10,
        help="Maximum agent steps per task (default: 10).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress step-by-step verbose output.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Override backend if passed as CLI arg
    if args.backend:
        os.environ["LLM_BACKEND"] = args.backend

    backend = os.getenv("LLM_BACKEND", "anthropic")
    print(f"Inference Agent | Backend: {backend}")
    print("Type 'exit' or Ctrl+C to quit.\n")

    # Single task mode
    if args.task:
        answer = run_agent(
            user_task=args.task,
            max_steps=args.max_steps,
            verbose=not args.quiet,
        )
        print(f"\nAnswer:\n{answer}")
        return

    # Interactive multi-turn mode
    history = []
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Bye.")
            break

        answer = run_agent(
            user_task=user_input,
            history=history,
            max_steps=args.max_steps,
            verbose=not args.quiet,
        )

        print(f"\nAgent: {answer}\n")

        # Carry forward history for multi-turn conversation
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()