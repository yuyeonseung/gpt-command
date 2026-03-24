# gpt-command (gptc)

> Turn natural language into ready-to-use terminal commands.

`gptc` is a lightweight CLI tool that converts plain English (or any language) into executable shell commands for macOS and Linux.

---

## 🚀 Installation

```bash
pip install gpt-command

---

🔑 Setup API Key

Run once to store your OpenAI API key securely:

gptc-key

Check status:

gptc-key --status

Set default model (optional):

gptc-key --model gpt-4.1

---

💡 Usage
gptc <your question>
Example
gptc find and delete all txt files in current directory recursively

Output:

find . -type f -name "*.txt" -delete

Then it will automatically prefill your terminal input:

~/current/path$ find . -type f -name "*.txt" -delete

⚠️ The command is NOT executed automatically.

---

⚙️ Options
📋 Copy to clipboard
gptc --copy compress current folder into tar.gz
📖 Show explanation
gptc --explain find process using port 8000
▶️ Execute command (with confirmation)
gptc --run check disk usage
🧠 Show history
gptc --history
🤖 Specify model
gptc --model gpt-4.1 list all running processes

---

🔐 Security

API key is stored locally at:

~/.config/gptc/config.json
File permissions are restricted to the user (600)
Dangerous commands are automatically detected and blocked from execution

---

⚠️ Disclaimer
Always review generated commands before running them
Some commands may modify or delete system data
Use with caution, especially with elevated privileges (sudo)
🖥️ Supported Platforms
macOS
Linux (Ubuntu, etc.)

---

✨ Features
Natural language → shell command
Auto-prefilled terminal input (no copy-paste needed)
Optional execution with confirmation
Clipboard copy support
Command explanation
History tracking
Local API key management (no environment variable required)
📌 Summary

Stop Googling terminal commands. Just ask.

---

📄 License

MIT License