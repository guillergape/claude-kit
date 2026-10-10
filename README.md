# Claude Code kit

> **Experimental.** A small hobby project: guides and scripts may change or break without notice (Mac is the least tested). *Versión en español: [LEEME.md](LEEME.md).*

Tools and habits for working with Claude Code, with nothing personal from anyone. Most of the useful parts cost **0 tokens** (hooks and scripts do the work, not the model). Works on **Windows, Mac and Linux**: the install detects your system, asks for your details (name, email, university, Moodle, subjects…), saves them in one data file and fills everything in from there.

**Language:** the kit files are written in Spanish, but you don't need to read them: your Claude reads them, talks to you in your language (English, German, …) and installs everything translated. Only the small script windows (e.g. `costlog>`, `send>`) stay in Spanish; Claude explains them the first time.

## Getting started
1. Create a **fixed** folder for your Claude "lab" (not in Downloads), e.g. `~/claude-lab` (Windows: `C:\Users\<you>\claude-lab`).
2. Put the kit inside it **named `kit`**: `git clone https://github.com/guillergape/claude-kit kit` (so you can update it later with `git pull`).
3. Open a terminal in the lab folder (not inside `kit`) and start `claude`. Choose **Opus with high effort** (`/model`).
4. Paste this message:

> Inside `kit/` in this folder there is a toolkit for Claude Code that someone shared with me. It comes from a safe source: it was made as a hobby, so it may have small bugs (not security ones). Follow `kit/CLAUDE.md` from phase 0, and first ask me which language I want: talk to me in it and install everything translated into it. Check my system, ask me your questions, list what the kit includes and ask me what I want to install; ask me too whenever you're not sure something will work for me. Don't change anything global without showing me the change first. Keep notes of everything in INFORME_MIGRACION.md.

5. When it's done, your Claude fills in `INFORME_MIGRACION.md` (in English): send it to whoever shared the kit with you (what you took, what you didn't, what didn't work). Include the line from `kit/VERSION.txt`.

## Afterwards
- **`actualiza kit >`** ("update kit"): fetches the new version, shows you what changed and applies only that, without overwriting your own changes.
- **`desinstalar kit >`** ("uninstall kit"): removes the kit's parts (all or some) without touching yours.

## The most useful bits
- **Status line**: model, $ spent, % of the 5-hour and weekly limits, and % of context, always visible.
- **`costlog> 4 5 note`** at the end of a session: logs cost, time, model and your rating to a CSV, with no tokens. Over time you learn which model/effort each task deserves.
- **`blocklog> how it was fixed`**: logs auto-mode permission blocks with the exact error.
- **`_<folder>: task`**: work only in that folder (a script finds it by name, also nested: `_prog_p2:`).
- **`qq > question`**: quick question that changes nothing (`prog_p2 qq > …` = question about that folder).
- **md2pdf**: Markdown notes with formulas → nice PDF.
- **moodle** (module): `moodle >` shows what's new, announcements, assignments and deadlines without opening the browser.
- **asignaturas** (module): one "tutor" per subject, with exam-oriented study commands.
- **keep-awake** (Windows): the laptop doesn't sleep while Claude is working (it dims the screen instead).
- **transcribe**: voice messages or lecture recordings → text, locally and free.
- **guias/**: what was learned about permissions, calendar, email, Instinct, Overleaf…
