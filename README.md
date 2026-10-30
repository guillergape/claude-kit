# Claude Code kit

[![GitHub stars](https://img.shields.io/github/stars/guillergape/claude-kit?style=social)](https://github.com/guillergape/claude-kit/stargazers)

> **Experimental.** A small hobby project: guides and scripts may change or break without notice (Mac is the least tested). *Versión en español: [LEEME.md](LEEME.md).*

Tools and habits for working with Claude Code, with nothing personal from anyone. Most of the useful parts cost **0 tokens** (hooks and scripts do the work, not the model). Works on **Windows, Mac and Linux**: the install detects your system, asks for your details (name, email, university, Moodle, subjects…), saves them in one data file and fills everything in from there.

**Language:** the kit files are written in Spanish, but you don't need to read them: your Claude reads them, talks to you in your language (English, German, …) and installs everything translated. The script windows and messages (e.g. `costlog>`, `send>`) come out in your language too (a small `textos.json` that Claude writes at install).

## Getting started
1. Open a terminal (Windows: PowerShell; Mac/Linux: Terminal) and paste this line. It creates a **fixed** folder for your Claude "lab" and starts Claude in it (if the folder already exists, ignore the `mkdir` error):
   ```
   mkdir ~/claude-lab; cd ~/claude-lab; claude
   ```
2. Choose **Opus with high effort** (`/model`) and paste this message. Claude downloads the kit and puts it in place (no GitHub account needed):

> I want to install the Claude Code kit from https://github.com/guillergape/claude-kit in this folder. Put it in the subfolder `kit/` (if it's already there, skip this): if I have git, `git clone https://github.com/guillergape/claude-kit kit` (so it can be updated later with `git pull`); if I don't, offer to install it, and if I say no, use the zip someone sent me (`kit-claude-*.zip`, look in Downloads) or download https://github.com/guillergape/claude-kit/archive/refs/heads/main.zip, and unzip it so it ends up exactly as `kit/` here (no extra folder in between). It comes from a safe source: it was made as a hobby, so it may have small bugs (not security ones). Then follow `kit/CLAUDE.md` from phase 0, and first ask me which language I want: talk to me in it and install everything translated into it. Check my system, ask me your questions, list what the kit includes and ask me what I want to install; ask me too whenever you're not sure something will work for me. Don't change anything global without showing me the change first. Keep notes of everything in INFORME_MIGRACION.md.

3. When it's done, your Claude fills in `INFORME_MIGRACION.md` (in English: what you took, what you didn't, what didn't work), shows it to you and, if you say yes, sends it to the kit's author itself through a private form (no account or email needed; your user folder shows up as `<HOME>`). If that doesn't work, reply to the author's email with it.

## Afterwards
- **`actualiza kit >`** ("update kit"): fetches the new version, shows you what changed and applies only that, without overwriting your own changes.
- **`desinstalar kit >`** ("uninstall kit"): removes the kit's parts (all or some) without touching yours.

## Helping it grow
- **Star the repo** (button at the top of the GitHub page): the only public number of how many people use it.
- **Bugs and ideas:** your Claude sends them with `kit/tools/feedback.py` (after showing you; no account). With a GitHub account you can also open an *issue* or a *pull request*.
- **Updates:** after `actualiza kit >` your Claude offers to tell the author you updated (only your name and the version). Nothing is counted or sent without your OK.

## The most useful bits
- **Status line**: model, $ spent, % of the 5-hour and weekly limits, and % of context, always visible.
- **`costlog> 4 5 note`** at the end of a session: logs cost, time, model and your rating to a CSV, with no tokens. Over time you learn which model/effort each task deserves.
- **blocklog**: auto-mode permission blocks of all your chats are logged to a CSV by themselves, with the exact error (`blocklog> how it was fixed` adds the fix). **`allow>`**: puts on the clipboard your consent for the last denial, naming the exact action, for you to paste.
- **vault** (`vault>`): your scripts' tokens and API keys in the system's credential store; Claude never sees them. **`login> account`**: switches Claude Code's account (on Windows, without typing the email code).
- **`_<folder>: task`**: work only in that folder (a script finds it by name, also nested: `_prog_p2:`).
- **`qq > question`**: quick question that changes nothing (`prog_p2 qq > …` = question about that folder).
- **md2pdf**: Markdown notes with formulas → nice PDF.
- **moodle** (module): `moodle >` shows what's new, announcements, assignments and deadlines without opening the browser.
- **asignaturas** (module): one "tutor" per subject, with exam-oriented study commands.
- **keep-awake** (Windows): the laptop doesn't sleep while Claude is working (it dims the screen instead).
- **transcribe**: voice messages or lecture recordings → text, locally and free.
- **guias/**: what was learned about permissions, calendar, email, Instinct, Overleaf…
