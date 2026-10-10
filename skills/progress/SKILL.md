---
name: progress
description: Save a checkpoint of the progress made so far in the current conversation, into whichever places it belongs (project memory, the project's own status/progress files, CLAUDE.md conventions). Use when the user types "/progress", or sends "progress >", "progreso >", "guarda el progreso >", "guarda progreso >", "save progress >", "checkpoint >" (commands end with ">"; without it, e.g. a bare "progress", don't save: ask in one line if they meant the command). Do NOT use when the user is only asking how something is progressing.
---

# Save progress (manual checkpoint)

This is an **extra, on-demand checkpoint**. It does not replace or switch off any rule that already saves things automatically (memory rules, "update the Status line when I confirm", etc.). Keep following those as usual; this just forces a full save right now.

If the user added text after the command (e.g. `/progress only the Prog part`), treat it as the focus or an extra note to save.

## 1. Work out what happened in this conversation

Go through the conversation (since the start, or since the last `/progress`) and list:
- **Where we stopped**: the exact point to resume (section, step, file, page, "resume at …").
- **Done**: what was finished, decided or confirmed by the user.
- **Pending**: what is half-done, queued, or promised for later, and anything blocked (and on what).
- **Things learned** that future sessions need: user preferences/corrections (feedback), facts about the project, pointers to external resources.

Leave out what is only useful inside this chat, and what the files or git history already record.

## 2. Save each item where it belongs

Check what already exists before writing: **update the existing file for the same thread instead of creating a new one**, and don't re-save what was already saved earlier in this session.

1. **The project's own conventions first.** If the workspace `CLAUDE.md` or a memory says where a kind of progress goes (a status line, a PROGRESS/TODO file in the repo…), put it there, in that format.
2. **Project memory** (the memory directory given in the system prompt), following its rules (one fact per file, frontmatter, `MEMORY.md` pointer line, `[[links]]`):
   - Work state / where we stopped → a `project` memory. Reuse the existing progress memory for that thread if there is one; otherwise name it like the existing ones (e.g. `<topic>-progress.md`). Update its `MEMORY.md` hook line too, so the index shows the current stopping point.
   - Preferences or corrections the user gave → `feedback` memory (with **Why:** / **How to apply:**).
   - External links, IDs, dashboards → `reference` memory.
   - Always absolute dates (today's date is in the context), never "today"/"yesterday".
3. **Global `~/.claude/CLAUDE.md`**: only if the user stated a rule meant for every project and it isn't there yet. Don't rewrite it on your own initiative; if unsure, mention it in the report as a suggestion instead.
4. If something fits nowhere above but matters, put it in the progress memory for this thread.

## 3. What a checkpoint must NOT do

- It is **not** "end of session": don't apply edits that are queued for the end of a session, don't rebuild PDFs, don't run long jobs. Record them as **pending** instead.
- No git commits, no emails/drafts, no calendar changes, nothing outward-facing. Only local notes/memory files.
- Don't delete or rewrite other memories except to update the same thread, or to fix one that turned out to be wrong in this conversation.

## 4. Report

Reply in the user's language, short:
- One line per file written or updated: `file` — what was saved.
- One line with where to resume.
- If nothing new needed saving (everything was already saved), say so in one line.
