import platform
import readline
import shutil
import subprocess
from pathlib import Path
from typing import Optional


DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",
    "shutdown -h now",
    "reboot",
    "poweroff",
    "halt",
    "chmod -R 777 /",
    "chown -R",
    "> /dev/sda",
    "> /dev/nvme",
]


def is_dangerous_command(cmd: str) -> bool:
    lowered = cmd.lower()
    return any(pattern.lower() in lowered for pattern in DANGEROUS_PATTERNS)


def build_prompt() -> str:
    cwd = Path.cwd()
    home = Path.home()

    try:
        cwd_str = str(cwd)
        home_str = str(home)
        if cwd_str.startswith(home_str):
            cwd_display = cwd_str.replace(home_str, "~", 1)
        else:
            cwd_display = cwd_str
    except Exception:
        cwd_display = str(cwd)

    return f"{cwd_display}$ "


def prefilled_input(prefill: str, prompt: Optional[str] = None) -> str:
    if prompt is None:
        prompt = build_prompt()

    def hook() -> None:
        readline.insert_text(prefill)
        readline.redisplay()

    try:
        readline.set_startup_hook(hook)
        return input(prompt)
    finally:
        readline.set_startup_hook(None)


def extract_command(text: str) -> str:
    cmd = text.strip()

    if cmd.startswith("```"):
        lines = [line for line in cmd.splitlines() if not line.strip().startswith("```")]
        cmd = "\n".join(lines).strip()

    if "\n" in cmd:
        cmd = cmd.splitlines()[0].strip()

    cmd = cmd.strip().strip("`").strip()
    cmd = cmd.strip('"').strip("'").strip()

    return cmd


def copy_to_clipboard(text: str) -> bool:
    system = platform.system()

    try:
        if system == "Darwin" and shutil.which("pbcopy"):
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
            return True

        if shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=text, text=True, check=True)
            return True

        if shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=text, text=True, check=True)
            return True

        return False
    except Exception:
        return False


def run_shell_command(cmd: str) -> int:
    try:
        completed = subprocess.run(cmd, shell=True)
        return completed.returncode
    except KeyboardInterrupt:
        return 130


def yes_no(question: str, default: str = "n") -> bool:
    default = default.lower().strip()
    prompt = " [Y/n] " if default == "y" else " [y/N] "

    answer = input(question + prompt).strip().lower()
    if not answer:
        return default == "y"

    return answer in {"y", "yes"}