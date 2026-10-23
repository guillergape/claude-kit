---
name: moodle
description: Check the university Moodle through its REST API, no browser. New or updated material, teacher notices (avisos), pending deliverables and deadlines, downloading course files, and adding Moodle dates to Google Calendar. Use for the commands `moodle >` / `moodle <Asig> >` and `/moodle`, and whenever the user asks things like "¿qué hay nuevo en Moodle?", "entregas pendientes de Prog", "descárgame los apuntes nuevos de Cálculo", "mete en el calendario las fechas de entrega de Moodle".
---

# Moodle (API)

Script: `<PY> "<HOME>/.claude/skills/moodle/moodle.py" <cmd>` (stdlib only, ~2 s per subject). Config in `moodle.json` next to the script (copy `moodle.example.json`): `site` (Moodle base URL), `root` (folder with one subfolder per subject, named like the keys of `courses`), `token_file`, `courses` (`{"Prog": 12345, …}`; get the ids with `courses`). Subject names are case-insensitive; none = all.

| cmd | what it prints |
|---|---|
| `courses` | my enrolled courses: `id \| short name \| full name` (to fill `courses` in moodle.json) |
| `new [Asig…]` | `[new]`/`[UPDATED]` file modules not on disk yet (`cm<id>`), new non-file activities, unseen notices from the last 30 days (`d<id>`) |
| `due [Asig…] [--all]` | Moodle timeline: pending to-dos with due dates (`--all` adds courses not in moodle.json) |
| `dates [Asig…] [--all]` | upcoming course calendar events not yet handled (`ev<id>`); `--all` includes handled ones |
| `get <Asig> cm<id>…` | downloads those modules' files to the inbox (`<root>/_moodle/inbox/<Asig>/`) and marks them seen |
| `post d<id>` | full text of one notice |
| `seen <Asig>:cm<id>\|d<id>\|ev<id>…` | dismisses items (state in `<root>/_moodle/seen.json`) |
| `token` | saves the token from a `moodlemobile://token=…` the user copied (clipboard), prints only "saved", clears the clipboard |

"On disk" = same file name (ignoring the extension) or same byte size anywhere in the subject folder, so renamed and converted files still count. The first `new` of a subject lists every file not on disk yet: that is normal.

## `moodle >` / "¿qué hay nuevo?" (all subjects) · `moodle <Asig> >` (one subject)
1. Run `new`, `due` and `dates` (with the subject if given). Read with `post` only the notices whose title suggests dates, cancellations, groups, exams or action required.
2. Reply in the chat, short, per subject: **new material** (each item with importance: slides/notes/problem sheets/exam material = important; schedules and lists = only if they affect me), **notices** (one line each with what matters: dates, cancellations, what I must do), **pending deliverables** (from `due`), **new dates** (from `dates`).
3. End by offering, in one line: download the important files? add the new dates to the calendar? Do neither until I say yes.
4. After replying, `seen` the notices you summarised. Files and dates stay listed until downloaded/added or I say to ignore them (then `seen` them).

## Downloads ("descárgame…", or yes to the offer)
1. `get <Asig> cm<id>…`. Files land in `<root>/_moodle/inbox/<Asig>/`, which is **temporary**.
2. File each one in its place in the subject folder (Teoría, Problemas, Prácticas, Exámenes…), matching the naming of the files already there. Use the Moodle section and the file name.
3. **Never overwrite.** If a file with that name exists and differs, or the destination is unclear, leave it in the inbox and ask. Remove empty inbox folders.
4. Say in one line per file where it went.

## Calendar ("mete las fechas…", or yes to the offer)
Only after my yes, following the calendar rules in `~/.claude/CLAUDE.md`: subject calendar, no notifications to anyone, deadlines **at their time** (e.g. 23:30–23:59 for a 23:59 deadline), not all-day; exams/labs with their reminders; doubtful dates marked `¿…?` with the source in the description. Search the calendar for the same event first to avoid duplicates. After adding (or if I say no), `seen <Asig>:ev<id>`.

## VPN
Some Moodles only answer from the university network: from outside, everything (even the login page) is `HTTP 403`, and `moodle.py` says so. If `moodle.json` has `"vpn"` (a command), `moodle.py` runs it once on a 403 and, if it exits 0, carries on (lines starting `VPN:`). On Windows with **GlobalProtect**, that command is `vpn-globalprotect.ps1` (`powershell -NoProfile -ExecutionPolicy Bypass -File "<HOME>/.claude/skills/moodle/vpn-globalprotect.ps1" -Site <site>`): it clicks GlobalProtect's own Connect without touching mouse or keyboard, and with SSO the sign-in completes by itself in a browser already signed in. Give `moodle.py` a timeout of ≥ 3 min. If it still ends with `HTTP 403 …`, tell me in one line to connect the VPN myself; never click or type in the sign-in page.

## Token
In the file `token_file` points to (default `~/.moodle-token`). **Never print it.** If the script says `TOKEN EXPIRED/INVALID` or there is no token yet:
- **If the university login is SSO** (a "log in with your university account" page; the usual case), the token comes from `<site>/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=12345&urlscheme=moodlemobile`, opened in the browser where the user is logged in to Moodle. Two ways (the installation asks which one the user prefers):
  - **Claude never sees it (default):** the user opens the browser's DevTools → Network tab, opens that URL, copies the `moodlemobile://token=…` it tries to open, and says so. Then run `moodle.py token`: it reads the clipboard, keeps only the token and clears the clipboard.
  - **Automatic, with the Claude in Chrome extension:** `read_network_requests` on the tab once (starts tracking), navigate it to that URL, then `read_network_requests` with pattern `mobile` shows `moodlemobile://token=<base64>` (decodes to `sitesig:::token[:::privatetoken]`). Write only the token (2nd part) to the file without printing it. The token does pass through Claude's context and the local chat transcript.
  Say it was renewed and check it with `courses`.
- **If the Moodle has its own username/password** (no SSO): `<site>/login/token.php?service=moodle_mobile_app` with username and password works, but **the user types them**, never Claude, and the password is never stored.
- If neither works, the mobile web service may be off on that Moodle: then use the browser without screenshots (global rule *Websites and forms*).
