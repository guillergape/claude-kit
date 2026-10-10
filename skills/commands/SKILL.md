---
name: commands
description: List the custom commands the user has built that apply to the folder they are working in (trigger phrases defined in CLAUDE.md files, project slash commands, project skills, plus their personal skills). Use when the user types "/commands", or asks "what commands do I have", "list my commands", "qué comandos tengo", "mis comandos". Read-only. Do NOT use to create or edit a command.
---

# /commands: short list, fast

Read-only. Goal: answer in **one tool call** with a **short list**. No tables, no notes, no preamble.

## Gather (one Bash call)

Run this once from the cwd, nothing else (no Read, no extra Greps). It prints `name :: start of its definition`:

```bash
d="$PWD"; while :; do [ -f "$d/CLAUDE.md" ] && echo "$d/CLAUDE.md"; p=$(dirname "$d"); [ "$p" = "$d" ] && break; d="$p"; done > /tmp/cmdfiles 2>/dev/null
ls "$PWD"/*/CLAUDE.md 2>/dev/null >> /tmp/cmdfiles
grep -v "^$HOME/.claude/CLAUDE.md$" /tmp/cmdfiles | while read f; do grep -E '^\s*(-\s+)?\*\*`[^`]+`\*\*' "$f" | sed -E 's/^\s*(-\s+)?\*\*`([^`]+)`\*\*[^:]*:?\s*/\2 :: /' | cut -c1-160; done | sort -u
sk() { for f in "$@"; do [ -f "$f" ] || continue; n=$(echo "$f" | sed -E 's#.*/skills/([^/]+)/SKILL\.md#\1#; s#.*/commands/([^/]+)\.md#\1#'); echo "/$n :: $(grep -m1 '^description:' "$f" | sed 's/^description: *//' | cut -c1-160)"; done; }
sk "$PWD"/.claude/commands/*.md "$PWD"/.claude/skills/*/SKILL.md
echo "--- personal"; sk ~/.claude/skills/*/SKILL.md ~/.claude/commands/*.md
```

Drop anything that is clearly not something the user would type (file names like `Main sources.md`, tool names like `openpyxl`). If the user added a filter (`/commands HEAT`), keep only matches.

## Output

Only this, nothing before or after. Each description **3–8 words**, written from the text after `::` (the essence, not the whole rule). Reply in the user's language.

```
**This folder**
- `Prog qq >`: pregunta rápida de Prog
- `/foo`: …

**Personal**
- `/md2pdf`: Markdown → PDF with LaTeX math
- …
```

If a group is empty, write `none` under it.
