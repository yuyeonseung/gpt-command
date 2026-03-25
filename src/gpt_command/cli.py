import argparse
import os
import sys
from typing import TextIO

from openai import OpenAI

from .config import get_api_key, get_default_model
from .history import print_history, save_history_item
from .utils import (
    copy_to_clipboard,
    extract_command,
    is_dangerous_command,
    run_shell_command,
    yes_no,
)
import platform


def detect_os() -> str:
    system = platform.system().lower()

    # macOS
    if system == "darwin":
        return "macOS"

    # Linux 계열
    if system == "linux":
        try:
            with open("/etc/os-release") as f:
                content = f.read().lower()

                if "ubuntu" in content:
                    return "Ubuntu"
                if "centos" in content:
                    return "CentOS"
                if "debian" in content:
                    return "Debian"
                if "fedora" in content:
                    return "Fedora"
                if "arch" in content:
                    return "Arch Linux"
        except Exception:
            pass

        return "Linux"

    # Windows (WSL 포함 가능)
    if system == "windows":
        return "Windows"

    return system.capitalize()

def build_system_prompt() -> str:
    current_os = detect_os()
    shell = os.environ.get("SHELL", "").split("/")[-1]

    return f"""You are a {current_os} {shell} terminal expert.

Follow these rules exactly:
1. Output only one executable shell command on a single line.
2. Do not output explanations, code fences, quotes, or extra text.
3. Generate commands optimized for {current_os} using {shell}.
4. If the user's request is risky or destructive, suggest the safest practical command possible.
5. If multiple steps are needed, combine them into a single one-liner using && when appropriate.
6. Return only the command string.
"""
SYSTEM_PROMPT = build_system_prompt()

EXPLAIN_PROMPT = """You are a Linux/macOS terminal command explainer.
Explain the given command in up to 3 short lines:
1. What it does
2. What the important options mean
3. Any caution the user should know
"""


def ask_model_for_command(question: str, model: str, stream_out: TextIO) -> str:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "No OpenAI API key found. Run `gptc-key` first to store your API key."
        )

    client = OpenAI(api_key=api_key)

    stream = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=f"Convert this natural language request into a single shell command:\n{question}",
        stream=True,
    )

    chunks = []
    printed_any = False

    for event in stream:
        event_type = getattr(event, "type", "")

        if event_type == "response.output_text.delta":
            delta = getattr(event, "delta", "")
            if delta:
                print(delta, end="", flush=True, file=stream_out)
                chunks.append(delta)
                printed_any = True
        elif hasattr(event, "delta") and isinstance(getattr(event, "delta"), str):
            delta = getattr(event, "delta", "")
            if delta:
                print(delta, end="", flush=True, file=stream_out)
                chunks.append(delta)
                printed_any = True

    if printed_any:
        print(file=stream_out, flush=True)

    command = extract_command("".join(chunks))

    if not command:
        raise RuntimeError("Failed to extract a command from the streamed response.")

    return command


def ask_model_for_explanation(command: str, model: str) -> str:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError(
            "No OpenAI API key found. Run `gptc-key` first to store your API key."
        )

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model=model,
        instructions=EXPLAIN_PROMPT,
        input=command,
    )

    text = getattr(response, "output_text", "") or ""
    return text.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gptc-gen",
        description="Convert natural language into terminal commands for macOS and Linux.",
    )
    parser.add_argument("question", nargs="*", help="Your natural language request.")
    parser.add_argument("--copy", action="store_true", help="Copy the result to the clipboard.")
    parser.add_argument("--explain", action="store_true", help="Show a short explanation of the command.")
    parser.add_argument("--run", action="store_true", help="Run the generated command after confirmation.")
    parser.add_argument("--model", type=str, default=None, help="Specify the model to use.")
    parser.add_argument("--history", action="store_true", help="Show recent command history.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.history:
        print_history(limit=10)
        return

    if not args.question:
        parser.print_help()
        sys.exit(1)

    question = " ".join(args.question).strip()
    model = args.model or get_default_model()
    capture_mode = os.environ.get("GPTC_CAPTURE_MODE") == "1"
    stream_out = sys.stderr if capture_mode else sys.stdout

    try:
        command = ask_model_for_command(question, model=model, stream_out=stream_out)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    explained = False
    if args.explain:
        try:
            explanation = ask_model_for_explanation(command, model=model)
            if explanation:
                print("\n[Explanation]")
                print(explanation)
                explained = True
        except Exception as e:
            print(f"\nExplanation failed: {e}", file=sys.stderr)

    copied = False
    if args.copy:
        copied = copy_to_clipboard(command)
        if copied:
            print("\nCopied to clipboard.")
        else:
            print("\nFailed to copy to clipboard. Check pbcopy, xclip, or wl-copy.", file=sys.stderr)

    if is_dangerous_command(command):
        print(
            "\n[Warning] A potentially dangerous command pattern was detected. "
            "Auto-run and shell insertion have been blocked.",
            file=sys.stderr,
        )
        save_history_item(
            question=question,
            command=command,
            executed=False,
            copied=copied,
            explained=explained,
        )
        sys.exit(2)

    if args.run:
        print()
        if yes_no("Do you want to run this command?", default="n"):
            code = run_shell_command(command)
            print(f"\nExit code: {code}")
            save_history_item(
                question=question,
                command=command,
                executed=True,
                copied=copied,
                explained=explained,
            )
            sys.exit(code)
        else:
            print("Execution cancelled.")
            save_history_item(
                question=question,
                command=command,
                executed=False,
                copied=copied,
                explained=explained,
            )
            sys.exit(0)

    save_history_item(
        question=question,
        command=command,
        executed=False,
        copied=copied,
        explained=explained,
    )

    # shell integration mode:
    # - stream was already shown on stderr
    # - emit final command only once on stdout so the shell wrapper can capture it
    if capture_mode:
        print(command)