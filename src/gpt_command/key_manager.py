import argparse
import getpass
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from .config import CONFIG_FILE, get_api_key, load_config, save_config, set_default_model

CONFIG_MARKER = "gptc shell integration"


def detect_shell() -> Tuple[Optional[str], Optional[Path]]:
    shell_path = os.environ.get("SHELL", "").strip()
    shell_name = Path(shell_path).name if shell_path else ""

    if shell_name == "zsh":
        return "zsh", Path.home() / ".zshrc"
    if shell_name == "bash":
        return "bash", Path.home() / ".bashrc"

    return None, None


def get_integration_block(shell_name: str) -> str:
    if shell_name == "zsh":
        return f"""# >>> {CONFIG_MARKER} >>>
gptc() {{
  local arg

  for arg in "$@"; do
    if [[ "$arg" == --* ]]; then
      gptc-gen "$@"
      return $?
    fi
  done

  local cmd
  cmd="$(GPTC_CAPTURE_MODE=1 gptc-gen "$@")" || return $?
  [[ -z "$cmd" ]] && return 0
  print -z -- "$cmd"
}}
# <<< {CONFIG_MARKER} <<<
"""

    if shell_name == "bash":
        return f"""# >>> {CONFIG_MARKER} >>>
gptc() {{
  local arg

  for arg in "$@"; do
    if [[ "$arg" == --* ]]; then
      gptc-gen "$@"
      return $?
    fi
  done

  local cmd
  cmd="$(GPTC_CAPTURE_MODE=1 gptc-gen "$@")" || return $?
  [[ -z "$cmd" ]] && return 0
  history -s -- "$cmd"
  printf '%s\\n' "$cmd"
}}
# <<< {CONFIG_MARKER} <<<
"""

    raise ValueError(f"Unsupported shell: {shell_name}")


def replace_or_append_block(rc_file: Path, new_block: str) -> str:
    if not rc_file.exists():
        rc_file.touch()

    try:
        content = rc_file.read_text(encoding="utf-8")
    except Exception:
        content = ""

    pattern = re.compile(
        rf"# >>> {re.escape(CONFIG_MARKER)} >>>.*?# <<< {re.escape(CONFIG_MARKER)} <<<\n?",
        re.DOTALL,
    )

    if pattern.search(content):
        updated = pattern.sub(new_block.rstrip() + "\n", content)
        action = "updated"
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        updated = content + "\n" + new_block.rstrip() + "\n"
        action = "installed"

    rc_file.write_text(updated, encoding="utf-8")
    return action


def install_shell_integration() -> bool:
    shell_name, rc_file = detect_shell()

    if not shell_name or not rc_file:
        print("Unsupported shell. Only zsh and bash are supported for automatic integration.")
        return False

    block = get_integration_block(shell_name)
    action = replace_or_append_block(rc_file, block)

    print(f"Shell integration {action} in {rc_file}.")
    attempt_reload_shell(shell_name, rc_file)
    return True


def attempt_reload_shell(shell_name: str, rc_file: Path) -> None:
    source_cmd = f"source {shlex.quote(str(rc_file))}"

    try:
        result = subprocess.run(
            [shell_name, "-ic", source_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            print("Shell reload check completed.")
        else:
            print("Shell reload check failed. You may need to reload your shell manually.")
    except Exception:
        print("Automatic shell reload check could not be performed.")

    print(f"Apply it to your current shell with: source {rc_file}")


def set_api_key() -> None:
    print("Enter your OpenAI API key. Input will be hidden.")
    key = getpass.getpass("API Key: ").strip()

    if not key:
        print("No key entered.")
        return

    config = load_config()
    config["OPENAI_API_KEY"] = key
    save_config(config)

    print(f"API key saved to {CONFIG_FILE}")
    install_shell_integration()


def delete_api_key() -> None:
    config = load_config()
    if "OPENAI_API_KEY" in config:
        del config["OPENAI_API_KEY"]
        save_config(config)
        print("Stored API key deleted.")
    else:
        print("No stored API key found.")


def show_status() -> None:
    key = get_api_key()
    if key:
        masked = key[:7] + "*" * max(0, len(key) - 11) + key[-4:]
        print("API key is configured.")
        print(f"Key preview: {masked}")
    else:
        print("API key is not configured.")

    config = load_config()
    model = config.get("DEFAULT_MODEL", "gpt-4.1")
    print(f"Default model: {model}")

    shell_name, rc_file = detect_shell()
    if shell_name and rc_file:
        print(f"Detected shell: {shell_name}")
        print(f"RC file: {rc_file}")
    else:
        print("Detected shell: unsupported")


def set_model(model: str) -> None:
    set_default_model(model)
    print(f"Default model saved: {model}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gptc-key",
        description="Manage gptc API key and shell integration.",
    )
    parser.add_argument("--set", action="store_true", help="Set the API key.")
    parser.add_argument("--delete", action="store_true", help="Delete the stored API key.")
    parser.add_argument("--status", action="store_true", help="Show current status.")
    parser.add_argument("--model", type=str, help="Set the default model.")

    args = parser.parse_args()
    acted = False

    if args.set:
        set_api_key()
        acted = True

    if args.delete:
        delete_api_key()
        acted = True

    if args.status:
        show_status()
        acted = True

    if args.model:
        set_model(args.model)
        acted = True

    if not acted:
        set_api_key()