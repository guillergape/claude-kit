"""`wait>` family (asked 2026-10-21): hold prompts on disk, out of Claude's sight (a VS Code crash can't lose them),
and send them later by hand, in a chain, at the 5 h reset or when an event happens. The hook part runs from costlog.py
(0 tokens); the rest are commands Claude runs. Items: ~/.claude/wait/<n>.json (+ <n>.sent once delivered or dropped,
<n>.fired when a scheduled trigger went off, <n>.log for its watcher). Only the exact forms in HELP run; a near miss
(`go all> x`, `wait drop> x`…) is blocked with the help; anything else passes untouched.
- `wait> <prompt>` -> saved as #n, blocked. `wait>` alone lists them. `wait drop>` cancels this chat's only one (with
  several it lists them with their text), `wait drop n>` #n, `wait drop all>` all of this chat's (kept on disk).
- Numbers go before the `>` (`go 3>`, `wait drop 3>`), so whatever follows a `>` is always text; `go> 3` gets a hint.
- `wait plan[ go| trigger]> <prompt>` -> not blocked: Claude splits it into self-contained phases (or keeps it whole),
  holds them with `add` and then stops and recommends a start (plain), starts the chain (`go`), or arms the event the
  prompt names on the first one, chained (`trigger`). The prompt itself is kept as an already-sent item.
- `wait go> <prompt>` = `wait>` + `go>`: saved (a crash can't lose it) and sent now.
- `wait trigger> <prompt>` -> held whole and not blocked: Claude reads the event in it and arms it as `trigger>` does
  (asks the user if it names none). `wait plan trigger>` without the splitting.
- `wait next> <prompt>` -> the chat is busy: held and blocked, and the Stop hook (`stop`) hands it to Claude as the next
  instruction when the turn ends (one per turn end). The chat is idle: sent now.
- `wait edit>` / `wait edit n>` -> a window to edit this chat's only waiting prompt (or #n) and Save.
- `go> [text]` / `go n> [text]` -> this chat's waiting prompt (or #n, from any chat) goes to Claude as hook context,
  as if typed now, with the text appended.
- `go all>` -> this chat's first waiting prompt with a chain footer: once it's done OK, Claude runs `next <sid>` for the
  following one (all in one turn); if it failed, Claude stops and the rest keep waiting.
- `go reset>` -> the same (chained if several) at the 5 h reset: a scheduled `daemon` fires at the reset time.
- `trigger> <event>` -> Claude gets the event, never the prompt: picks the chat (`chats`), `arm`s and runs `watch` in
  the background. At that chat's turn end a --check decides, or Claude judges its last message and runs `fire` or re-arms.
- `trigger auto> <event>` -> same set-up, but the scheduled `daemon` watches: fires on a normal turn end (+ --check),
  waits out a full 5 h / weekly limit and delivers into the chat's `watch`; if nobody takes it in 90 s, a new window
  resumes the chat with `go n>` (a --fork-session copy when the chat is still open).
- 0 tokens at the reset into the same open chat isn't possible: only a background task the model starts can wake an idle
  chat; injecting a message into its local messaging pipe is denied by the auto-mode classifier ([Auto-Mode Bypass],
  21 Oct) and undocumented. So go reset> costs one small turn when there's limit left, and opens a window when there isn't.
- `add <file.json>`: Claude holds prompts it wrote itself (a JSON list) for its own chat, ready for `go all>`.
CLI: chats [n] · arm n [--chat ID] [--check CMD] [--next|--now] [--auto] [--chain] [--event TEXT] | arm n --reset
[--chain] · watch n · fire n · next SID · add FILE · daemon n · edit n (the window) · stop (Stop hook, JSON on stdin)
· --test
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time
from datetime import datetime, timezone

DIR = os.path.expanduser("~/.claude/wait")
PROJECTS = os.path.expanduser("~/.claude/projects")
LIMITS = os.path.expanduser("~/.claude/costlog-state/_last_limits.json")  # written by statusline.py
AWAKE = os.path.expanduser("~/.claude/hooks/keep-awake.ps1")
W = os.path.abspath(__file__).replace("\\", "/")
PYW = '"{}" "{}"'.format(sys.executable.replace("\\", "/").replace("pythonw.exe", "python.exe"), W)  # this same Python
PS = "pwsh" if shutil.which("pwsh") else "powershell"  # Windows: PowerShell 7 if installed, else the built-in 5.1
WAIT = re.compile(r"^\s*wait\s*>(.*)$", re.I | re.S)
DROP = re.compile(r"^\s*wait\s+drop(?:\s+(?:#?(\d+)|(all)))?\s*>\s*$", re.I)
EDIT = re.compile(r"^\s*wait\s+edit(?:\s+#?(\d+))?\s*>\s*$", re.I)
PLAN = re.compile(r"^\s*wait\s+plan(?:\s+(go|trigger))?\s*>(.*)$", re.I | re.S)
WAITX = re.compile(r"^\s*wait\s+(go|trigger|next)\s*>(.*)$", re.I | re.S)
GO = re.compile(r"^\s*go(?:\s+#?(\d+))?\s*>(.*)$", re.I | re.S)  # the number before the >: what follows is always text
NUMAFTER = re.compile(r"^\s*(go|wait\s+(?:drop|edit))\s*>\s*#?(\d+)\s*$", re.I)  # `go> 3`: old form, ambiguous
GOALL = re.compile(r"^\s*go\s+all\s*>\s*$", re.I)
GORESET = re.compile(r"^\s*go\s+reset\s*>\s*$", re.I)
TRIG = re.compile(r"^\s*trigger(\s+auto)?\s*>(.*)$", re.I | re.S)
# looks like one of them, exact or not ("go to the shop > now" doesn't: 3 words before the >)
NEAR = re.compile(r"^\s*(?:(?:wait|go|trigger)(?:\s+\w+){0,2}|wait\s+plan\b[^>\n]{0,30})\s*>", re.I)
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # the daemon runs windowless: no console flashes
HELP = ("`wait> <prompt>` hold it: saved, Claude doesn't see it · `wait>` list · `wait drop>` cancel this chat's "
        "only one (several: lists them) · `wait drop n>` cancel #n · `wait drop all>` cancel all of this chat's\n"
        "`wait plan> <prompt>` Claude splits it into phases (or keeps it whole), holds them and stops · "
        "`wait plan go>` the same, then starts them · `wait plan trigger>` the same, then waits for the event the "
        "prompt names\n"
        "`wait go> <prompt>` = `wait>` + `go>`: saved and sent now · `wait trigger> <prompt>` held; Claude takes the "
        "event from it and arms it (asks if it names none) · `wait next> <prompt>` goes in when this chat finishes what "
        "it's doing · `wait edit>` / `wait edit n>` edit it in a window\n"
        "`go>` send it to this chat now · `go> <text>` the same, with the text appended · `go n> [text]` send #n\n"
        "`go all>` send all of this chat's, one after another, each only if the previous one went OK\n"
        "`go reset>` the same, when the 5 h limit resets\n"
        "`trigger> <event>` send it when the event happens, e.g. another chat finishes its task OK (Claude judges)\n"
        "`trigger auto> <event>` the same, judged by a script: survives VS Code closing, waits out the usage limit")


def path(n, ext="json"):
    return os.path.join(DIR, f"{n}.{ext}")


def load(n):
    try:
        with open(path(n), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(it):
    with open(path(it["n"]) + ".tmp", "w", encoding="utf-8") as f:
        json.dump(it, f, ensure_ascii=False)
    os.replace(path(it["n"]) + ".tmp", path(it["n"]))


def sent(n):
    return os.path.exists(path(n, "sent"))


def items():
    ns = sorted(int(f[:-5]) for f in os.listdir(DIR) if re.fullmatch(r"\d+\.json", f)) if os.path.isdir(DIR) else []
    return [i for i in map(load, ns) if i]


def pending(sid):
    """A chat's waiting prompts, oldest first: chats never see each other's."""
    return [i for i in items() if i["sid"] == sid and not sent(i["n"])]


def new(sid, cwd, prompt, by=None, **extra):
    os.makedirs(DIR, exist_ok=True)
    n = max((i["n"] for i in items()), default=0) + 1
    while True:  # O_EXCL: two chats saving at once can't get the same number
        try:
            fd = os.open(path(n), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            n += 1
    it = dict({"n": n, "sid": sid, "cwd": cwd, "t": time.time(), "prompt": prompt}, **({"by": by} if by else {}), **extra)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(it, f, ensure_ascii=False)
    return it


def claim(n, how, sid):
    """Only one deliverer wins (go>, watch, fire, next, drop): whoever creates <n>.sent first."""
    try:
        fd = os.open(path(n, "sent"), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w") as f:
        json.dump({"t": time.time(), "how": how, "sid": sid}, f)
    return True


def preview(s, k=70):
    s = " ".join(s.split())
    return s if len(s) <= k else s[:k - 1] + "…"


def when(t):
    d = datetime.fromtimestamp(t)
    return f"{d:%H:%M}" if d.date() == datetime.now().date() else f"{d:%d %b %H:%M}"


def when_iso(ts):
    return when(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()) if ts else "?"


def now_iso():  # same format as the transcripts' timestamps, so they compare as strings
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def base(cwd):
    return os.path.basename((cwd or "").rstrip("\\/")) or "?"


def released(it, how, extra="", chain=False, ctx=""):
    """The text Claude gets. Call it after claim(): the chain footer counts what's still waiting."""
    who = "a prompt you wrote earlier at the user's request" if it.get("by") == "claude" else "the user's own prompt"
    foot, left = "", len(pending(it["sid"]))
    if chain:
        foot = (f"\n\n[wait] Chain: {left} more after this one. When this one is done correctly, run "
                f"`{PYW} next {it['sid']}` and do what it prints. If it failed or needs the user, stop and say "
                f"so: the rest keep waiting (`go all>` resumes)." if left else "\n\n[wait] Last one of the chain.")
    return (f"[wait #{it['n']}] {how}. Below is {who}, saved with `wait>` {when(it['t'])} in {base(it['cwd'])}: do it "
            f"now exactly as if the user had just typed it.\n\n{it['prompt']}" + (f"\n\n{extra}" if extra else "")
            + (f"\n\n{ctx}" if ctx else "") + foot)


def folder(prompt, sid, cwd):
    """A held `_<carpeta>: …` / `<carpeta> qq > …` is resolved only now, by carpetas.py, as if just typed.
    -> (context, None) · (None, why it couldn't) · (None, None) when the prompt isn't one."""
    import io, carpetas
    from contextlib import redirect_stdout
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            carpetas.hook({"prompt": prompt, "session_id": sid, "cwd": cwd})
    except SystemExit:
        pass
    if not buf.getvalue().strip():
        return None, None
    d = json.loads(buf.getvalue())
    if "decision" in d:  # ambiguous / not found: its y/n question would grab the user's next answer
        try:
            os.remove(carpetas.state_path(sid))
        except OSError:
            pass
        return None, re.sub(r"\n\n¿[^\n]*\n\n`y` = sí.*$", "", d["reason"], flags=re.S)  # that question is gone
    return d["hookSpecificOutput"]["additionalContext"], None


def release(it, how, sid, cwd, extra="", chain=False):
    """Hook side: folder first (one that doesn't resolve isn't sent), then claim and hand it to Claude."""
    ctx, why = folder(it["prompt"], sid, cwd)
    if why:
        block(f"⏸ wait #{it['n']} not sent: its folder didn't resolve.\n{why}\nFix: `wait drop {it['n']}>` and save it "
              f"again with the right `_<carpeta>:`.")
    claim(it["n"], how, sid)  # an explicit `go> n` may resend one already sent
    return released(it, f"Released by {how}", extra, chain, ctx or "")


def deliver(it, how, chain=False):
    """watch / fire / next (already claimed): the prompt plus its folder, resolved now."""
    ctx, why = folder(it["prompt"], it["sid"], it["cwd"])
    return released(it, how, chain=chain, ctx=ctx or (
        f"[wait] Its folder couldn't be resolved ({why}). Ask the user which folder before working." if why else ""))


def listing():
    its = items()
    pend, done = [i for i in its if not sent(i["n"])], [i for i in its if sent(i["n"])][-3:]
    out = ["Waiting prompts:" if pend else "No waiting prompts."]
    for i in pend:
        tg, st = i.get("trigger"), "at this chat's turn end · " if i.get("next") else ""
        if tg:
            st = ("🔥 fired, not delivered · " if os.path.exists(path(i["n"], "fired")) else "") + \
                 f"trigger{' auto' if tg.get('auto') else ''} «{preview(tg['event'], 40)}»{'' if tg.get('armed') else ' (not armed)'} · "
        out.append(f"#{i['n']} · {base(i['cwd'])} · {when(i['t'])} · {'by Claude · ' if i.get('by') else ''}{st}"
                   f"«{preview(i['prompt'])}»")
    if done:
        how = lambda n: json.load(open(path(n, "sent"), encoding="utf-8")).get("how", "?")
        out.append("Latest sent: " + " · ".join(f"#{i['n']} ({how(i['n'])}) «{preview(i['prompt'], 40)}»" for i in done))
    return "\n".join(out)


def block(text):
    print(json.dumps({"decision": "block", "reason": text,  # without the "Original prompt: …" echo
                      "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "suppressOriginalPrompt": True}}))
    sys.exit(0)


def say(ctx, msg=None):
    """Hook output that lets the prompt through: context for Claude, plus a line shown to the user."""
    d = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}
    return dict(d, systemMessage=msg) if msg else d


def limit(k):
    try:
        with open(LIMITS, encoding="utf-8") as f:
            return json.load(f).get(k) or {}
    except (OSError, ValueError, AttributeError):
        return {}


def arm_reset(it, chain):
    """go reset> / arm --reset: fire at the 5 h reset, by the scheduled daemon. -> (time, error or None)"""
    at = limit("5h").get("resets_at") or 0
    if at <= time.time():
        return 0, "no 5 h window is running now, so there's no reset to wait for"
    it["trigger"] = {"event": f"5 h reset at {when(at)}", "auto": True, "at": at + 60, "chain": chain, "since": "",
                     "armed": time.time()}
    save(it)
    return at + 60, schedule(it["n"])


PLAN_MSG = {None: "start them with `go all>`, `go reset>` or `trigger> <event>`",
            "go": "starts them right away, one after another",
            "trigger": "arms the start for the event your prompt names"}


def plan_ctx(src, mode, sid):
    end = {None: ("Show the list, one line each, and end with the start you recommend as the exact command: `go all>` "
                  f"(now), `go reset>` (heavy work and the 5 h window is at {limit('5h').get('used_percentage', '?')}%), "
                  "or `trigger> <event>` (if it has to wait for something). Then stop: don't start them."),
           "go": (f"Show the list, one line each, then start right away: run `{PYW} next {sid}` and do what it "
                  "prints (each one says how to go on)."),
           "trigger": arm_steps("<first n>", True)}[mode]
    return (f"[wait hook] `wait plan{' ' + mode if mode else ''}>`: organize the user's prompt (this message, also saved "
            f"as #{src}) into held prompts. Don't do any of the work now; read only what you need to split it well.\n"
            "1. One single prompt if the task is small or can't be checked in parts; otherwise 2–6 phases in order, each "
            "ending in something checkable (a file, a build, a passing check), so that a failed phase stops the rest.\n"
            "2. Each one self-contained: «Phase k/N — <goal>:», absolute paths, the project rules to follow, what the "
            "earlier phases left and where, what \"done\" means. If the prompt starts with `_<carpeta>:`, start each "
            "one with it.\n"
            f"3. Put them in a JSON list in the scratchpad and run `{PYW} add <file>`.\n4. {end}")


def arm_steps(n, chain):
    """wait plan trigger> / wait trigger>: the event is in the prompt Claude just read."""
    c = " --chain" if chain else ""
    return ("The prompt says when to start: take that event (if it doesn't say, ask the user and stop). For the 5 h "
            f"reset: `{PYW} arm {n} --reset{c}`. Otherwise arm it as `trigger>` does (add `--auto` only if the "
            "prompt wants it script-judged or to survive VS Code closing):\n"
            + steps(n, False, (c + ' --event "<event>"').strip()))


def busy(tr):
    """The chat is mid-turn: its last prompt (or background wake-up) has no turn end yet. A prompt typed now isn't in
    the transcript yet (blocked ones never get there)."""
    t = Tail(tr).read() if tr else None
    return bool(t and t.prompt_t and not t.idle and not t.cut)


def steps(n, auto, flags=""):
    check = ("Needed, deterministic: a command that exits 0 only once the task is really done (e.g. `python -c \"…\"` "
             "checking the output file exists and is newer than now). The script also requires the chat's turn to end "
             "normally (no API error, no interrupt). If no check is possible, say so: it would then fire on any normal "
             "turn end, which doesn't prove success; ask the user whether that's OK or to use `trigger>` instead."
             if auto else
             "Optional: a command that exits 0 only once the task is really done. Without one, you'll judge the chat's "
             "last message when its turn ends.")
    return (f"1. Run `{PYW} chats {n}` and pick the chat the event is about. Not exactly one clear match -> ask "
            f"the user (show the candidates) and stop; never guess. An event that isn't a chat (a file appears, a time, "
            f"a process ends) -> no --chat, only --check (polled every 30 s).\n"
            f"2. Success check: {check}\n"
            f"3. Run `{PYW} arm {n} --chat <session id> [--check \"<cmd>\"]{' --auto' if auto else ''}"
            f"{' ' + flags if flags else ''}`. If it "
            f"says the chat already finished, ask the user: fire now (add --now) or wait for its next task (--next).\n"
            f"4. Run in the background (run_in_background): `{PYW} watch {n}`. When it ends, do what it prints.\n"
            f"5. Tell the user in 1–2 lines what's armed (which chat, what counts as done"
            f"{', and that it survives VS Code closing' if auto else ''}) and that `go>` sends it now.")


def trigger_ctx(it, auto):
    return (f"[wait hook] `trigger{' auto' if auto else ''}>` for the user's waiting prompt #{it['n']}. Its text is "
            f"hidden from you on purpose: don't read ~/.claude/wait/ or guess it. Event: «{it['trigger']['event']}».\n"
            + steps(it["n"], auto))


def hook(h):
    """Called from costlog.py for every prompt. Blocks wait>, listings and near misses; go… / trigger… / wait plan…
    -> the hook output to print (context for Claude); anything else -> None."""
    p, sid, cwd = h.get("prompt", ""), h.get("session_id") or "?", h.get("cwd") or ""
    none = lambda: block("⏸ No waiting prompt in this chat.\n" + listing())

    def only(cmd):  # this chat's only waiting prompt; several -> shown in full enough to pick one
        mine = pending(sid) or none()
        if len(mine) > 1:
            block(f"⏸ Several waiting prompts in this chat; pick one with `wait {cmd} n>`"
                  + (" (or `wait drop all>`)" if cmd == "drop" else "") + ":\n"
                  + "\n".join(f"#{i['n']} «{preview(i['prompt'], 300)}»" for i in mine))
        return mine[0]["n"]

    if m := NUMAFTER.match(p):
        block(f"🔁 Not run: the number goes before the `>`: `{' '.join(m[1].lower().split())} {m[2]}>`.")
    if d := DROP.match(p):
        if d[2]:  # all of this chat's
            gone = [i["n"] for i in pending(sid) or none() if claim(i["n"], "dropped", sid)]
            block(f"🗑 Dropped {', '.join(f'#{n}' for n in gone)} (kept on disk; `go n>` still sends one).")
        n = int(d[1]) if d[1] else only("drop")
        if not load(n):
            block(f"⏸ There's no wait #{n}.")
        block(f"🗑 wait #{n} dropped (kept on disk; `go {n}>` still sends it)." if claim(n, "dropped", sid)
              else f"⏸ wait #{n} was already sent or dropped.")
    if m := EDIT.match(p):
        n = int(m[1]) if m[1] else only("edit")
        if not load(n):
            block(f"⏸ There's no wait #{n}.\n" + listing())
        editor(n)
        block(f"✏️ wait #{n} is open in a window: edit it and press Save (Ctrl+S)."
              + (f" It was already sent or dropped: `go {n}>` sends the edited one." if sent(n) else ""))
    if m := WAITX.match(p):
        cmd, body = m[1].lower(), m[2].strip()
        if not body:
            block(f"⏸ Write the prompt: `wait {cmd}> <prompt>`.")
        if cmd == "go" or cmd == "next" and not busy(h.get("transcript_path")):
            return say(release(new(sid, cwd, body), f"wait {cmd}>", sid, cwd))
        if cmd == "next":  # the Stop hook hands it over at this turn's end
            n = new(sid, cwd, body, next=True)["n"]
            block(f"⏭ Saved as wait #{n}: it goes in when this chat finishes what it's doing. `wait edit {n}>` edits "
                  f"it, `wait drop {n}>` cancels it, `go {n}>` sends it now.")
        n = new(sid, cwd, body)["n"]
        return say(f"[wait hook] `wait trigger>`: the user's prompt (this message) is saved as waiting prompt #{n} of "
                   f"this chat. Don't do it now: only set up when it starts.\n" + arm_steps(n, False),
                   f"⏱ wait trigger>: saved as #{n}; Claude arms the event your prompt names (and asks if it names none).")
    if m := PLAN.match(p):
        mode, body = (m[1] or "").lower() or None, m[2].strip()
        if not body:
            block(f"⏸ Write the prompt: `wait plan{' ' + mode if mode else ''}> <prompt>`.")
        src = new(sid, cwd, body)["n"]
        claim(src, "wait plan>", sid)  # kept on disk as the source; the phases are what waits
        return say(plan_ctx(src, mode, sid), f"📋 wait plan>: Claude splits this prompt into phases (or keeps it "
                                             f"whole) and holds them for this chat; then {PLAN_MSG[mode]}.")
    if m := WAIT.match(p):
        body = m[1].strip()
        if not body:
            block("⏸ " + listing() + "\n\n" + HELP)
        if NEAR.match(body):
            block("⏸ Not saved: first `wait> <prompt>`, then `go>` / `trigger> <event>` as a message of its own.")
        n = new(sid, cwd, body)["n"]
        block(f"⏸ Saved as wait #{n}; Claude didn't see it. Then:\n" + HELP)
    if GOALL.match(p):
        mine = pending(sid) or none()
        return say(release(mine[0], "go all>", sid, cwd, chain=True))
    if GORESET.match(p):
        mine = pending(sid) or none()
        it, more = mine[0], len(mine) - 1
        at, err = arm_reset(it, more > 0)
        if err:
            block(f"⏸ go reset> not armed: {err}." + ("" if at else " `go>` / `go all>` send it now."))
        what = f"#{it['n']}" + (f" (+{more} more, chained)" if more else "")
        if (limit("5h").get("used_percentage") or 0) >= 100:
            block(f"⏰ {what} goes at {when(at)}, when the 5 h limit resets. This chat is out of limit and can't "
                  f"listen, so then a new window opens with it (a copy of this chat if this one is still open).")
        return say(f"[wait hook] go reset>: the user's waiting prompt {what} goes when the 5 h limit resets ({when(at)}); "
                   f"a scheduled task watches the clock. Don't do it now and don't read ~/.claude/wait/. Only run in the "
                   f"background (run_in_background) `{PYW} watch {it['n']}`, which delivers it here then, and "
                   f"say in one line what goes and when.")
    if m := GO.match(p):
        if m[1]:  # `go n>`: #n from any chat (even one already sent)
            it = load(int(m[1])) or block(f"⏸ There's no wait #{m[1]}.\n" + listing())
        else:
            mine = pending(sid)
            if len(mine) != 1:
                block("⏸ Several waiting prompts in this chat: `go n>` picks one, `go all>` sends them all.\n"
                      + listing()) if mine else none()
            it = mine[0]
        return say(release(it, "go>", sid, cwd, m[2].strip(), chain=bool((it.get("trigger") or {}).get("chain"))))
    if m := TRIG.match(p):
        mine = pending(sid)
        if not mine:
            block("⏸ No waiting prompt in this chat: first `wait> <prompt>`, then `trigger> <event>`.\n" + listing())
        if not m[2].strip():
            block("⏸ Say the event: `trigger> <event>` (e.g. `trigger> when the HEAT lab chat finishes the report`).")
        it = mine[-1]
        it["trigger"] = {"event": m[2].strip(), "auto": bool(m[1])}
        save(it)
        return say(trigger_ctx(it, bool(m[1])))
    if NEAR.match(p):
        block("🔁 Not run: that isn't one of the `wait>` commands, which are exactly:\n" + HELP)
    return None


class Tail:
    """Reads a chat's transcript incrementally: last real prompt, last turn end and how it ended, last answer, title."""

    def __init__(self, tr):
        self.tr, self.pos, self.idle, self.cut, self.normal = tr, 0, False, False, False
        self.prompt_t = self.end_t = self.stop = self.last = self.title = self.ai = self.first = self.cwd = ""
        self.prompt = ""
        self.err = False

    def read(self):
        try:
            with open(self.tr, "rb") as f:
                f.seek(self.pos)
                for line in f:
                    if not line.endswith(b"\n"):
                        break  # still being written
                    self.pos += len(line)
                    try:
                        self.feed(json.loads(line))
                    except ValueError:
                        pass
        except OSError:
            pass
        return self

    def feed(self, d):
        t, ts, msg = d.get("type"), d.get("timestamp") or "", d.get("message") or {}
        if t == "custom-title":  # /rename
            self.title = d.get("customTitle") or self.title
        elif t == "ai-title":
            self.ai = d.get("aiTitle") or self.ai
        if d.get("isSidechain"):
            return
        self.cwd = self.cwd or d.get("cwd") or ""  # the folder it was opened in, not where a later `cd` left it
        if t == "user" and not d.get("isMeta"):
            c = msg.get("content")
            text = (c if isinstance(c, str) else
                    " ".join(x.get("text", "") for x in c or [] if x.get("type") == "text")).strip()
            if text.startswith("[Request interrupted"):
                self.cut = True
            elif text and not text.startswith("<"):  # a real prompt (not a /command or a tool result)
                self.prompt_t, self.cut, self.idle, self.prompt = ts, False, False, preview(text, 110)
                self.first = self.first or preview(text)
            elif text.startswith("<task-notification>"):  # a background task woke it up
                self.idle = False
        elif t == "assistant":
            self.stop, self.err, self.idle = msg.get("stop_reason") or "", bool(d.get("isApiErrorMessage")), False
            text = " ".join(x.get("text", "") for x in msg.get("content") or []
                            if isinstance(x, dict) and x.get("type") == "text").strip()
            self.last = text or self.last
        elif t == "system" and d.get("subtype") == "turn_duration":  # one per finished turn
            self.end_t, self.idle = ts, True
            self.normal = self.stop == "end_turn" and not self.err and not self.cut

    def name(self):
        return self.title or self.ai or self.first or "(untitled)"


def is_open(sid):
    """Claude Code's own registry of running chats (~/.claude/sessions/<pid>.json, any terminal): its pid still runs."""
    try:
        import psutil
        for f in glob.glob(os.path.expanduser("~/.claude/sessions/*.json")):
            with open(f, encoding="utf-8") as fh:
                r = json.load(fh)
            if r.get("sessionId") == sid and psutil.pid_exists(int(r["pid"])):
                return True
    except Exception:
        pass
    return False


def chats(n=None):
    me = (load(n) or {}).get("sid") if n else None
    rows, cut = [], time.time() - 48 * 3600
    for tr in sorted(glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")), key=os.path.getmtime, reverse=True)[:40]:
        sid = os.path.basename(tr)[:-6]
        if os.path.getmtime(tr) < cut or len(rows) == 15:
            break
        if sid == me:
            continue
        t = Tail(tr).read()
        if not t.prompt_t:
            continue
        state = (f"idle since {when_iso(t.end_t)}, last answer «{preview(t.last, 110)}»" if t.idle else
                 f"busy since {when_iso(t.prompt_t)} on «{t.prompt}»")
        rows.append(f"- {sid} · {base(t.cwd)} · «{t.name()}» · {state}{' · open' if is_open(sid) else ''}")
    return (f"Chats active in the last 48 h, newest first{' (this one left out)' if me else ''}:\n" + "\n".join(rows)
            if rows else "No chats active in the last 48 h.")


def chat_cwd(sid):
    for tr in glob.glob(os.path.join(PROJECTS, "*", sid + ".jsonl")):
        with open(tr, encoding="utf-8") as f:
            for line in f:
                if '"cwd"' in line:
                    try:
                        return json.loads(line).get("cwd")
                    except ValueError:
                        pass
    return None


def passes(check, cwd, why=None):
    """why: a list that gets the end of a failing check's output (2026-10-23: a check that could never pass, a
    redirect loop in urllib, went unnoticed because arm only said "fails")."""
    if not check:
        return True
    try:
        r = subprocess.run(check, shell=True, cwd=cwd or None, capture_output=True, timeout=300, creationflags=NOWIN)
    except (OSError, subprocess.TimeoutExpired) as e:
        r = subprocess.CompletedProcess(check, 1, b"", str(e).encode())
    if r.returncode and why is not None:
        why.append(" ".join((r.stderr or r.stdout).decode("utf-8", "replace").split())[-300:])
    return r.returncode == 0


def until_event(it, judge):
    """Blocks until the trigger's event -> (why, tail). judge=True and no --check: ("judge", tail) at the chat's first
    turn end, for Claude to decide. None if the prompt got sent or dropped meanwhile."""
    n, tg = it["n"], it["trigger"]
    if tg.get("at"):  # go reset>: a time
        while not sent(n) and time.time() < tg["at"]:
            time.sleep(max(1, min(30, tg["at"] - time.time())))
        return None if sent(n) else ("the 5 h limit reset", None)
    tail = Tail(tg["transcript"]) if tg.get("chat") else None
    while not sent(n):
        if not tail:
            if passes(tg.get("check"), it["cwd"]):
                return "its check passed", None
            time.sleep(30)
            continue
        tail.read()
        if tail.end_t > tg["since"]:
            tg["since"] = tail.end_t  # this turn end is used up: a re-armed watch waits for the next one
            save(it)
            if judge and not tg.get("check"):
                return "judge", tail
            why = []
            if tail.normal and passes(tg.get("check"), it["cwd"], why):
                return f"«{tail.name()}» finished", tail
            print(f"{datetime.now():%H:%M:%S} turn end at {when_iso(tail.end_t)} doesn't count (normal={tail.normal}"
                  + (f"; check failed: {why[0]}" if why else "") + ")", flush=True)
        time.sleep(10)
    return None


def task(n):
    return f"Claude wait {n}"


def schedule(n):
    """Task Scheduler, not Popen: survives VS Code closing and Claude Code reaping shells. -> None, or the error."""
    if os.name != "nt":  # ponytail: Mac/Linux get a detached process (dies with a reboot); launchd/systemd if it matters
        subprocess.Popen([sys.executable, W, "daemon", str(n)], start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return None
    exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = exe if os.path.exists(exe) else sys.executable
    ps = (f"Stop-ScheduledTask -TaskName '{task(n)}' -ErrorAction SilentlyContinue; "
          f"Register-ScheduledTask -TaskName '{task(n)}' -Force -Action (New-ScheduledTaskAction -Execute '{exe}' "
          f"-Argument '\"{W}\" daemon {n}') -Settings (New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
          f"-DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -MultipleInstances IgnoreNew) | Out-Null; "
          f"Start-ScheduledTask -TaskName '{task(n)}'")
    r = subprocess.run([PS, "-NoProfile", "-Command", ps], capture_output=True, text=True, creationflags=NOWIN)
    return ("couldn't start the scheduled task: " + (r.stderr or r.stdout).strip()) if r.returncode else None


def arm(argv):
    ap = argparse.ArgumentParser(prog="wait.py arm")
    ap.add_argument("n", type=int)
    ap.add_argument("--chat")
    ap.add_argument("--check")
    ap.add_argument("--next", action="store_true", help="wait for the chat's next task, not the current one")
    ap.add_argument("--now", action="store_true", help="the chat already finished: that end counts")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--chain", action="store_true", help="this chat's waiting prompts after it follow it (go all>)")
    ap.add_argument("--event", help="the event in the user's words, for the listing")
    ap.add_argument("--reset", action="store_true", help="at the 5 h reset, like go reset>")
    o = ap.parse_args(argv)
    it = load(o.n)
    if not it or sent(o.n):
        sys.exit(f"#{o.n}: no such waiting prompt, or already sent.")
    if o.reset:
        at, err = arm_reset(it, o.chain)
        if err:
            sys.exit(err)
        return print(f"#{o.n}{' and the ones after it' if o.chain else ''} go at {when(at)}, the 5 h reset; a scheduled "
                     f"task watches the clock.\nNow run in the background: {PYW} watch {o.n}")
    if not (o.chat or o.check):
        sys.exit("Give --chat and/or --check (or --reset).")
    tg = it.setdefault("trigger", {"event": "?"})
    tg.update(chat=o.chat, check=o.check, auto=o.auto, chain=o.chain, since="", armed=time.time())
    tg["event"] = o.event or tg.get("event") or "?"
    out = []
    if o.chat:
        tr = glob.glob(os.path.join(PROJECTS, "*", o.chat + ".jsonl"))
        if not tr:
            sys.exit(f"No transcript for chat {o.chat}: take the id from `chats`.")
        t = Tail(tr[0]).read()
        done = t.idle and t.end_t > t.prompt_t
        if done and not (o.next or o.now):
            sys.exit(f"Not armed: «{t.name()}» already finished its last task at {when_iso(t.end_t)}. Ask the user: "
                     f"fire now (--now) or wait for its next task (--next).")
        # busy on a background-task wake-up: its earlier turn end is stale, count from it
        tg.update(transcript=tr[0], since=now_iso() if o.next else "" if o.now else
                  t.end_t if t.end_t > t.prompt_t else t.prompt_t)
        out.append(f"Watching «{t.name()}» ({base(t.cwd)}, {'idle' if t.idle else 'busy'}): "
                   + ("its next task." if o.next else "the task it got at " + when_iso(t.prompt_t) + "."))
    if o.check:
        why = []
        out.append(f"Check right now: passes." if passes(o.check, it["cwd"], why) else
                   f"Check right now: fails. Its output: {why[0] or '(none)'}\nIf the event already happened, the check "
                   "is wrong: fix it and arm again.")
    save(it)
    if o.auto:
        err = schedule(o.n)
        if err:
            sys.exit(err)
        out.append(f"Scheduled task «{task(o.n)}» watches it (log: {path(o.n, 'log')}).")
    out.append(f'Now run in the background: {PYW} watch {o.n}')
    print("\n".join(out))


def judge_text(it, t):
    n, last = it["n"], t.last if len(t.last) <= 4000 else t.last[:1500] + "\n[…]\n" + t.last[-2500:]
    return (f"[wait #{n}] The chat «{t.name()}» ({base(t.cwd)}) ended a turn "
            f"{'normally' if t.normal else 'abnormally (API error, limit or interrupted)'} at {when_iso(t.end_t)}. "
            f"Its last message:\n---\n{last}\n---\nTrigger event: «{it['trigger']['event']}». Did that chat really "
            f"complete it (no errors, not half-way, not just asking a question)?\n"
            f"- Yes: run `{PYW} fire {n}` and do what it prints.\n"
            f"- No or unsure: tell the user in one line why, then run in the background `{PYW} watch {n}` "
            f"(waits for its next turn end). They can send it anyway with `go>`.")


def watch(n):
    it = load(n)
    tg = (it or {}).get("trigger") or {}
    if not tg.get("armed"):
        sys.exit(f"#{n} isn't armed: run arm first.")
    if tg.get("auto"):  # the daemon watches; this only delivers into this chat
        while not sent(n):
            if os.path.exists(path(n, "fired")) and claim(n, "trigger auto", it["sid"]):
                return print(deliver(it, "Released by its scheduled trigger", tg.get("chain")))
            time.sleep(5)
    else:
        r = until_event(it, judge=True)
        if r and r[0] == "judge":
            return print(judge_text(it, r[1]))
        if r and claim(n, "trigger", it["sid"]):
            return print(deliver(it, f"Released by its trigger: {r[0]}", tg.get("chain")))
    print(f"[wait #{n}] Already sent or dropped (go>, wait drop> or another trigger): nothing to do.")


def fire(n):
    it = load(n)
    if it and claim(n, "trigger, judged done", it["sid"]):
        print(deliver(it, "Released by its trigger, judged done", (it.get("trigger") or {}).get("chain")))
    else:
        print(f"[wait #{n}] Already sent, dropped, or doesn't exist: nothing to do.")


def stop(h):
    """Stop hook: this chat finished its turn -> its oldest `wait next>` prompt goes in as the next instruction."""
    sid = h.get("session_id") or "?"
    for it in pending(sid):
        if it.get("next") and claim(it["n"], "wait next>", sid):
            if os.path.exists(AWAKE):
                from costlog import detach
                detach([sys.executable, W, "awake", sid, h.get("transcript_path") or ""])
            return {"decision": "block", "reason": deliver(it, "Released at this chat's turn end (wait next>)")}
    return None


def awake(sid, tr):
    """keep-awake.ps1's own Stop hook lets the PC sleep at this turn end, but the chat goes on with a wait next>."""
    time.sleep(5)  # ponytail: after that Stop hook (they run in parallel); one slower than 5 s would win the race
    subprocess.run([PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", AWAKE, "start"],
                   input=json.dumps({"session_id": sid, "transcript_path": tr}), text=True, creationflags=NOWIN)


def editor(n):
    from costlog import detach  # the window outlives the hook
    detach([sys.executable, W, "edit", str(n)])


def edit_window(n):
    import tkinter as tk
    root = tk.Tk()
    root.title(f"wait #{n}")
    root.attributes("-topmost", True)  # appear in front once, then behave like a normal window
    root.after(500, lambda: root.attributes("-topmost", False))
    txt = tk.Text(root, width=100, height=24, wrap="word", undo=True, font=("Segoe UI", 10))
    txt.insert("1.0", load(n)["prompt"])
    txt.pack(fill="both", expand=True, padx=10, pady=(10, 0))
    err = tk.Label(root, fg="red", text=f"Already sent or dropped: `go {n}>` sends the edited one." if sent(n) else "")
    err.pack()

    def ok(*_):
        body = txt.get("1.0", "end").strip()
        if not body:
            err["text"] = f"Empty. To cancel it use `wait drop {n}>`."
            return "break"
        it = load(n)  # fresh: a trigger may have been armed meanwhile
        it["prompt"] = body
        save(it)
        root.destroy()

    bar = tk.Frame(root)
    bar.pack(pady=10)
    tk.Button(bar, text="Save (Ctrl+S)", command=ok).pack(side="left", padx=5)
    tk.Button(bar, text="Cancel (Esc)", command=root.destroy).pack(side="left", padx=5)
    root.bind("<Control-s>", ok)
    root.bind("<Escape>", lambda e: root.destroy())
    root.after(100, lambda: (root.focus_force(), txt.focus_set()))
    root.mainloop()


def next_(sid):
    for it in pending(sid):
        if claim(it["n"], "go all>", os.environ.get("CLAUDE_CODE_SESSION_ID") or "?"):
            return print(deliver(it, "Next in the chain (go all>)", chain=True))
    print("[wait] Chain finished: nothing left waiting for that chat.")


def add(argv):
    ap = argparse.ArgumentParser(prog="wait.py add")
    ap.add_argument("file", help="JSON list of prompts, in order")
    ap.add_argument("--sid", default=os.environ.get("CLAUDE_CODE_SESSION_ID"), help="default: this chat")
    o = ap.parse_args(argv)
    if not o.sid:
        sys.exit("No session id: pass --sid.")
    with open(o.file, encoding="utf-8") as f:
        ps = json.load(f)
    if not (isinstance(ps, list) and ps and all(isinstance(x, str) and x.strip() for x in ps)):
        sys.exit("The file must be a JSON list of non-empty prompts.")
    cwd = chat_cwd(o.sid) or os.getcwd()
    ns = [new(o.sid, cwd, x.strip(), by="claude")["n"] for x in ps]
    print(f"Held {'#' + str(ns[0]) if len(ns) == 1 else f'#{ns[0]}–#{ns[-1]}'} for this chat. Tell the user: `go all>` "
          f"runs them in order (each only if the previous one went OK), `go reset>` the same at the 5 h reset, "
          f"`wait>` lists them.")


def limit_wait():
    """A full 5 h / weekly window -> sleep until it resets."""
    # ponytail: statusline.py's last snapshot, from whichever account drew a status line last
    ends = [w.get("resets_at") or 0 for w in (limit("5h"), limit("7d")) if (w.get("used_percentage") or 0) >= 100]
    t = max(ends, default=0) - time.time()
    if t > 0:
        print(f"{datetime.now():%H:%M:%S} usage limit full: waiting {t / 60:.0f} min for the reset")
        time.sleep(t + 60)


def deliver_elsewhere(it):
    """Nobody in the chat took it: resume the chat in a new window with `go n>` (a fork if it's still open there)."""
    if os.name != "nt":  # ponytail: no new terminal window on Mac/Linux; `wait>` shows it as fired, `go n>` sends it
        return print(f"{datetime.now():%H:%M:%S} not delivered: no new window on this OS; `go {it['n']}>` sends it")
    fork = " --fork-session" if is_open(it["sid"]) else ""
    subprocess.Popen([PS, "-NoExit", "-Command", f"claude --resume {it['sid']}{fork} 'go {it['n']}>'"],
                     cwd=it["cwd"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    print(f"{datetime.now():%H:%M:%S} delivered in a new window{' (fork)' if fork else ''}")


def daemon(n):
    os.makedirs(DIR, exist_ok=True)
    sys.stdout = sys.stderr = open(path(n, "log"), "a", encoding="utf-8", buffering=1)
    print(f"{datetime.now():%d %b %H:%M:%S} daemon #{n} started")
    try:
        it = load(n)
        r = until_event(it, judge=False)
        if r:
            print(f"{datetime.now():%H:%M:%S} event: {r[0]}")
            limit_wait()
            if not sent(n):
                open(path(n, "fired"), "w").close()
                for _ in range(18):  # 90 s for the chat's own `watch` to take it
                    if sent(n):
                        break
                    time.sleep(5)
                else:
                    deliver_elsewhere(it)
    finally:
        print(f"{datetime.now():%H:%M:%S} daemon #{n} done")
        if os.name == "nt":
            subprocess.run(["schtasks", "/Delete", "/TN", task(n), "/F"], capture_output=True, creationflags=NOWIN)


def test():
    global DIR, LIMITS, AWAKE, schedule, editor
    import io, tempfile
    from contextlib import redirect_stdout
    DIR = tempfile.mkdtemp()
    LIMITS = os.path.join(DIR, "limits.json")
    AWAKE = os.path.join(DIR, "none.ps1")  # no real keep-awake restart here
    armed, opened = [], []
    schedule = lambda n: armed.append(n)  # no real scheduled task here
    editor = lambda n: opened.append(n)  # nor windows

    msgs = []  # the lines shown to the user when the prompt goes through

    def run(p, sid="A", tr=None):
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                r = hook({"prompt": p, "session_id": sid, "cwd": DIR, "transcript_path": tr})
        except SystemExit:
            d = json.loads(buf.getvalue())
            assert d["hookSpecificOutput"]["suppressOriginalPrompt"]
            return d["reason"]
        msgs.append(r and r.get("systemMessage"))
        return r and r["hookSpecificOutput"]["additionalContext"]

    def out(f, *a):
        buf = io.StringIO()
        with redirect_stdout(buf):
            f(*a)
        return buf.getvalue()

    # only the exact forms run; a near miss gets the help; anything else passes untouched
    for p in ("wait, I meant", "waiting> x", "await> x", "go ahead and do it", "go to the shop > now", "Gone> x",
              "trigger the alarm", "please go>", "x wait> y", "_heat: go> x", "hello"):
        assert run(p) is None, p
    for p in ("go all> x", "go reset> 3", "wait drop> x", "go alll>", "trigger autoo> x", "wait plan trigger auto> x",
              "wait plann> x"):
        assert run(p).startswith("🔁 Not run"), p
    # two chats at once never mix
    assert "wait #1" in run("wait> hola\nmundo") and "wait #2" in run("Wait > otro", "B")
    assert "`go all>`" in run("wait> uno más")  # #3; the help comes with every save
    assert run("wait> go> 1").startswith("⏸ Not saved") and run("wait> trigger auto> x").startswith("⏸ Not saved")
    assert "«hola mundo»" in run("wait>")
    assert run("go>", "B").endswith("\n\notro") and "Several waiting prompts" in run("go>")
    assert run("go 3> y en inglés").endswith("uno más\n\ny en inglés")  # #3 + appended text
    assert run("go> 2 ejercicios más").endswith("hola\nmundo\n\n2 ejercicios más")  # after `go>` it's always text
    assert run("go #2>").endswith("\n\notro") and "No waiting prompt in this chat" in run("go>")  # B's, resent here
    assert "There's no wait #9" in run("go 9>") and "`go 9>`" in run("go> 9") and "`wait drop 9>`" in run("Wait drop> 9")
    # wait drop n>
    n = new("A", DIR, "x")["n"]
    assert "dropped" in run(f"wait drop {n}>") and "already sent" in run(f"wait drop #{n}>") and not pending("A")
    # trigger: the event goes to Claude, never the prompt
    assert "No waiting prompt" in run("trigger> x") and "wait #5" in run("wait> otro2", "B")
    assert "Say the event" in run("trigger>", "B")
    ctx = run("trigger auto> when the HEAT chat ends", "B")
    assert "#5" in ctx and "otro2" not in ctx and "--auto" in ctx and load(5)["trigger"]["auto"]
    # chat end: judge mode never shows the prompt; fire does, once
    tr = os.path.join(DIR, "t.jsonl")
    ev = [{"type": "user", "timestamp": "2026-10-21T10:00:00.000Z", "cwd": "C:/x/lab", "message": {"content": "do X"}},
          {"type": "assistant", "message": {"stop_reason": "end_turn", "content": [{"type": "text", "text": "X done"}]}},
          {"type": "system", "subtype": "turn_duration", "timestamp": "2026-10-21T10:05:00.000Z"}]
    with open(tr, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(d) + "\n" for d in ev)
        f.write('{"type": "user", "timest')  # half-written line: skipped until complete
    it = load(5)
    it["trigger"].update(chat="c", transcript=tr, since="2026-10-21T10:00:00.000Z", check=None, auto=False, armed=1)
    save(it)
    why, t = until_event(it, judge=True)
    assert why == "judge" and t.normal and t.name() == "do X" and t.idle and t.cwd == "C:/x/lab"
    jt = judge_text(it, t)
    assert "X done" in jt and "otro2" not in jt and load(5)["trigger"]["since"] == "2026-10-21T10:05:00.000Z"
    o = out(fire, 5) + out(fire, 5)
    assert o.count("\n\notro2") == 1 and "Already sent" in o
    # deterministic: an API-error end doesn't count; a normal one with a passing check does
    t = Tail(tr)
    for d in (ev[0], dict(ev[1], isApiErrorMessage=True), ev[2]):
        t.feed(d)
    assert not t.normal
    assert passes(f'"{sys.executable}" -c "import sys; sys.exit(0)"', DIR) and not passes("exit 1", DIR)
    n = new("C", DIR, "tercero")["n"]  # the check runs in the chat's folder: it must exist
    it = dict(load(n), trigger={"event": "e", "chat": "c", "transcript": tr, "since": "", "check": "exit 0"})
    assert until_event(it, judge=False)[0] == "«do X» finished"
    assert "dropped" in run(f"wait drop {n}>") and until_event(it, judge=False) is None  # dropped: watcher stops
    # Claude holds its own prompts; go all> chains them, each released only after the previous one
    with open(os.path.join(DIR, "p.json"), "w", encoding="utf-8") as f:
        json.dump(["fase 1", "fase 2", "fase 3"], f)
    assert "#7–#9" in out(add, [os.path.join(DIR, "p.json"), "--sid", "D"]) and load(7)["by"] == "claude"
    c1 = run("go all>", "D")
    assert "\n\nfase 1" in c1 and "you wrote earlier" in c1 and "2 more" in c1 and "next D" in c1 and "fase 2" not in c1
    c2, c3, c4 = out(next_, "D"), out(next_, "D"), out(next_, "D")
    assert "fase 2" in c2 and "1 more" in c2 and "fase 3" in c3 and "Last one" in c3 and "Chain finished" in c4
    # go reset>: armed for the reset time; out of limit -> blocked (0 tokens), a window will open then
    json.dump({"5h": {"used_percentage": 40, "resets_at": time.time() + 3600}}, open(LIMITS, "w"))
    run("wait> r1", "E")
    run("wait> r2", "E")
    ctx = run("go reset>", "E")
    tg = load(10)["trigger"]
    assert "watch 10" in ctx and armed == [10] and tg["chain"] and tg["at"] > time.time() + 3600
    json.dump({"5h": {"used_percentage": 100, "resets_at": time.time() + 600}}, open(LIMITS, "w"))
    run("wait> r3", "F")
    assert run("go reset>", "F").startswith("⏰ #12 goes at")
    json.dump({"5h": {"used_percentage": 100, "resets_at": time.time() - 60}}, open(LIMITS, "w"))
    assert "no 5 h window is running" in run("go reset>", "F")
    it = dict(load(12), trigger={"at": time.time() - 1})
    assert until_event(it, judge=False) == ("the 5 h limit reset", None)
    # a held `_carpeta:` resolves only when sent; one that doesn't resolve isn't sent
    run("wait> _zzqxnoexiste: hola", "G")
    assert "not sent: its folder didn't resolve" in run("go>", "G") and pending("G")
    # wait drop> with no n: this chat's only one; several -> listed with their text, nothing dropped
    assert "No waiting prompt" in run("wait drop>", "I")
    n = new("I", DIR, "solo uno")["n"]
    assert f"#{n} dropped" in run("wait drop>", "I") and not pending("I")
    a, b = new("I", DIR, "primero largo " * 30)["n"], new("I", DIR, "segundo")["n"]
    lst = run("wait drop>", "I")
    assert "Several" in lst and f"#{b} «segundo»" in lst and lst.count("primero largo") > 15 and len(pending("I")) == 2
    assert run("wait drop all>", "I") == f"🗑 Dropped #{a}, #{b} (kept on disk; `go n>` still sends one)."
    assert not pending("I") and "No waiting prompt" in run("wait drop all>", "I")
    # wait plan: Claude sees it (not blocked), the source is kept as sent, the user gets a line saying what it does
    ctx = run("wait plan> haz el informe entero del lab 3", "H")
    s = max(i["n"] for i in items())
    assert "add <file>" in ctx and f"#{s}" in ctx and "Then stop" in ctx and sent(s) and msgs[-1].startswith("📋")
    assert "next H" in run("wait plan go> x", "H") and "starts them right away" in msgs[-1]
    ctx = run("wait plan trigger> x cuando acabe el otro chat", "H")
    assert "--reset --chain" in ctx and '--chain --event "<event>"' in ctx and "chats <first n>" in ctx
    assert "Write the prompt" in run("wait plan>", "H") and not pending("H")
    # arm from the CLI: --reset (as go reset>), --chain and --event
    json.dump({"5h": {"used_percentage": 10, "resets_at": time.time() + 600}}, open(LIMITS, "w"))
    n = new("H", DIR, "fase 1")["n"]
    assert "5 h reset" in out(arm, [str(n), "--reset", "--chain"]) and load(n)["trigger"]["chain"] and armed[-1] == n
    n = new("H", DIR, "fase 2")["n"]
    o = out(arm, [str(n), "--check", "exit 1", "--chain", "--event", "cuando X"])
    assert "fails" in o and load(n)["trigger"]["event"] == "cuando X" and load(n)["trigger"]["chain"]
    # wait go>: saved and sent at once
    assert run("wait go> uno y ya", "J").endswith("\n\nuno y ya") and not pending("J")
    assert "`wait go> <prompt>`" in run("wait go>", "J")
    # wait next>: idle chat -> now; busy -> held, and the Stop hook hands it over at the turn end, once
    bz = os.path.join(DIR, "busy.jsonl")
    with open(bz, "w", encoding="utf-8") as f:
        f.write(json.dumps(ev[0]) + "\n")
    assert run("wait next> ahora", "J", tr).endswith("\n\nahora") and run("wait next> sin chat", "J").endswith("chat")
    assert run("wait next> luego", "J", bz).startswith("⏭ Saved") and "at this chat's turn end" in run("wait>")
    assert stop({"session_id": "K"}) is None
    r = stop({"session_id": "J"})
    assert r["decision"] == "block" and r["reason"].endswith("\n\nluego") and stop({"session_id": "J"}) is None
    # wait trigger>: held whole, Claude sees it and arms the event in it
    ctx = run("wait trigger> cuando acabe el chat del lab, haz el informe", "J")
    n = pending("J")[0]["n"]
    assert f"#{n}" in ctx and f"chats {n}" in ctx and f'arm {n} --chat' in ctx and '--event "<event>"' in ctx
    assert "--chain" not in ctx and msgs[-1].startswith("⏱")
    # wait edit [n]>: this chat's only one, or #n; several -> pick
    assert f"#{n} is open" in run("wait edit>", "J") and opened == [n]
    new("J", DIR, "otro")
    assert "pick one with `wait edit n>`" in run("wait edit>", "J") and "There's no wait #99" in run("wait edit 99>")
    assert "already sent" in run("wait edit 1>") and opened == [n, 1] and "`wait edit 3>`" in run("wait edit> 3")
    print("ok")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["daemon"]:  # first: under pythonw there is no stdout to reconfigure
        daemon(int(a[1]))
        sys.exit()
    sys.stdout.reconfigure(encoding="utf-8")
    if a == ["--test"]:
        test()
    elif a[:1] == ["chats"]:
        print(chats(int(a[1]) if a[1:] else None))
    elif a[:1] == ["arm"]:
        arm(a[1:])
    elif a[:1] == ["watch"]:
        watch(int(a[1]))
    elif a[:1] == ["fire"]:
        fire(int(a[1]))
    elif a[:1] == ["next"]:
        next_(a[1])
    elif a[:1] == ["add"]:
        add(a[1:])
    elif a[:1] == ["edit"]:
        edit_window(int(a[1]))
    elif a == ["stop"]:
        r = stop(json.loads(sys.stdin.buffer.read() or b"{}"))
        if r:
            print(json.dumps(r))
    elif a[:1] == ["awake"]:
        awake(a[1], a[2])
    else:
        sys.exit(__doc__)
