"""UserPromptSubmit hook for `costlog>` and `blocklog>`: appends one row to costlog.csv / blocklog.csv, with no model
tokens (the prompt is blocked, Claude never sees it).
- `costlog> <nota sesión> <nota PDF> [nota libre]` (e.g. `costlog> 4 5 se dejó X`, `costlog> 4 - bien`) -> logged directly.
  `costlog> 4` alone -> logged directly with the defaults: Nota PDF "—", Correcciones 0 (also the form's defaults).
- `costlog>` alone, anything that doesn't fit that order, a limit reset mid-session, or costlog.csv locked (open in
  Excel) -> a window (separate process, so it can stay minimized as long as needed; usage data frozen at `costlog>`)
  asks for each field, pre-filled. It doesn't close until the row is really written.
Nota PDF: 1–5, or -, —, NA, n/a, no -> "—" (no PDF to grade); `pendiente` is kept as is.
- `costlog> par 4 5 …` (or nousage / solo$): other chats ran at the same time, so the 5 h / weekly % aren't this chat's
  alone. Also detected automatically (another chat of the same account spent $ meanwhile). Row gets parallel=True and
  usage_manual ≈ this chat's $ × median 5 h %/$ of single-chat sessions; `par?` opens the form to correct it.
Automatic: task (chat title), project, model + effort, nº questions, time (transcript); $ and 5 h / weekly %
start→end (snapshots written by statusline.py). `python costlog.py --test` runs the self-check.
`--mark` / `--leftover --task … --project … --model … --tokens … --minutes … [--note …]`: log a `leftover n>` subagent step.
blocklog (automatic): on any prompt, at most every 10 min, a detached `--blockscan` logs every chat's blocked tool
  calls (subagents too, read from disk; auto-mode classifier outage or denial, safety check, PreToolUse hook…) to
  blocklog.csv, one row per incident (blocks < 30 min apart), deduped by tool_use id (column `ids`), solución
  «pendiente» until the same call later goes through. `blocklog> [solución]`: logs this chat's now and puts the text
  as solución of its pending rows; nothing found -> a window to log one by hand (e.g. a hung shell).
  `--blockscan --dry`: what would be logged. Works during a classifier outage too: hooks don't go through the classifier.
`allow>` / `allow N>`: the person's consent for this chat's last (Nth last) classifier denial -> clipboard; they read
  it, paste it and send it themselves (the hook never sends it).
`vault>`: opens the vault window (<LAB>/vault/vault.py, optional). `login> <cuenta>`: switches Claude Code's account
  (<LAB>/login/login.py, optional). Both only if that script is installed; otherwise the prompt goes through.
"""
import csv, glob, json, os, re, statistics, subprocess, sys
try:
    import send  # `send>` window lives in send.py (same folder); optional: delete send.py if you don't use send>
except ImportError:
    send = None
import carpetas  # folder mode `_<carpeta>:` (same folder, configured in carpetas.json)
try:
    import wait  # `wait>` / `go>` / `trigger>` (same folder); optional: delete wait.py if you don't use them
except ImportError:
    wait = None
try:
    from textos import T  # texts in the person's language (textos.json next to this file); Spanish without it
except ImportError:
    T = lambda s, **k: s.format(**k) if k else s
from collections import Counter
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_CSV = os.path.join(HERE, "..", "costlog.csv")
STATE = os.path.expanduser("~/.claude/costlog-state")
TRIGGER = re.compile(r"^\s*costlog\s*>(.*)$", re.I | re.S)
NA = {"-", "—", "–", "na", "n/a", "n.a.", "no", "x"}
CSV_COLS = ["date", "session_id", "project", "task", "model_effort", "n_questions", "n_corrected", "nota_sesion",
            "nota_pdf", "h5_start", "h5_end", "h5_reset", "week_start", "week_end", "week_reset", "parallel", "cost_usd",
            "minutes", "usage_manual", "note"]
BLOG_CSV = os.path.join(HERE, "..", "blocklog.csv")
BTRIGGER = re.compile(r"^\s*blocklog\s*>(.*)$", re.I | re.S)
BLOG_COLS = ["date", "time", "session_id", "project", "model_effort", "n_blocks", "tipo", "bloqueado", "error",
             "intento", "solucion", "ids"]  # ids = tool_use ids of the blocked calls (dedupe)
ATRIGGER = re.compile(r"^\s*allow\s*(\d*)\s*>(.*)$", re.I | re.S)  # `allow>` / `allow N>`: consent text -> clipboard
VTRIGGER = re.compile(r"^\s*vault\s*>\s*$", re.I)  # `vault>`: opens the vault window
VAULT = os.path.join(HERE, "..", "vault", "vault.py")
LTRIGGER = re.compile(r"^\s*login\s*>(.*)$", re.I | re.S)  # `login> <cuenta>`: switch account
LOGIN = os.path.join(HERE, "..", "login", "login.py")
PROJECTS = os.path.expanduser("~/.claude/projects")
SCAN = os.path.join(STATE, "blocklog-scan.json")  # {"t": start of the last full scan}
START = ""  # ISO date: blocks before it are ignored ("" = all; e.g. "2026-11-01" to skip the ones before installing)
GAP = 30 * 60  # blocks of one transcript less than 30 min apart = one incident = one row
PEND = "pendiente"
BLOCK = re.compile(r"auto mode classifier|safety check|protected from removal|^<tool_use_error>Blocked|"
                   r"Tool permission request failed|Permission denied for .+ on this domain|PreToolUse:\w+ hook error")


def locked(path):
    return T("{f} está abierto (¿Excel?) y no se puede escribir: ciérralo y pulsa Apuntar otra vez.",
             f=os.path.basename(path))


LOCKED = locked(LOG_CSV)
WINDOWS = (("5h", "5h", T("el de 5 h")), ("7d", "sem", T("el semanal")))


def grade(t, pdf=False):
    t = (t or "").strip()
    if re.fullmatch(r"[1-5]([.,]5)?", t):
        return t.replace(",", ".")
    if pdf and t.lower() in NA:
        return "—"
    if pdf and t.lower() == "pendiente":
        return "pendiente"
    return None


def parse(args):
    """-> (prefill dict, ok). ok=False means: open the form."""
    toks = args.split(maxsplit=2)
    s = grade(toks[0]) if toks else None
    if s and len(toks) == 1:  # `costlog> 4` alone: no PDF, 0 corrections
        return {"ses": s, "pdf": "—", "corr": "0", "note": ""}, True
    p = grade(toks[1], pdf=True) if len(toks) > 1 else None
    if s and p:
        return {"ses": s, "pdf": p, "note": toks[2] if len(toks) > 2 else ""}, True
    if s:
        return {"ses": s, "note": args.split(maxsplit=1)[1] if len(toks) > 1 else ""}, False
    return {"note": args.strip()}, False


def pretty(model):
    m = re.match(r"claude-([a-z]+)-(\d+)-(\d+)", model)
    return f"{m[1].capitalize()} {m[2]}.{m[3]}" if m else model


# slash commands that only change settings / the session: never a chat title
SETTING_CMDS = {"model", "effort", "fast", "config", "clear", "compact", "rename", "resume", "status", "cost", "usage",
                "help", "permissions", "memory", "context", "theme", "color", "output-style", "login", "logout", "mcp", "doctor"}


def transcript_stats(path):
    combos, prompts, title, custom, first, slash, times = Counter(), 0, "", "", "", "", []
    try:
        f = open(path, encoding="utf-8")
    except OSError:
        return {"title": "", "model_effort": "?", "prompts": "?", "minutes": None}
    with f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            t = d.get("type")
            if t == "ai-title":
                title = d.get("aiTitle") or title
            elif t == "custom-title":  # /rename
                custom = d.get("customTitle") or custom
            if t not in ("user", "assistant") or d.get("isSidechain"):
                continue
            if d.get("timestamp"):
                times.append(d["timestamp"])
            msg = d.get("message") or {}
            if t == "assistant" and str(msg.get("model", "")).startswith("claude"):
                name = pretty(msg["model"])
                combos[(name, d.get("effort") or ("no effort" if name.startswith("Haiku") else "?"))] += 1
            elif t == "user" and not d.get("isMeta") and not d.get("isCompactSummary"):
                c = msg.get("content")
                text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if x.get("type") == "text")
                text = text.strip()
                if text and not text.startswith(("<", "[Request interrupted")):
                    prompts += 1
                    first = first or " ".join(text.split())[:60]
                elif m := re.search(r"<command-name>/([\w:.-]+)</command-name>", text):
                    if m[1] not in SETTING_CMDS:
                        slash = slash or "/" + m[1]
    mins = None
    if len(times) > 1:
        ts = sorted(datetime.fromisoformat(x.replace("Z", "+00:00")) for x in times)
        mins = round((ts[-1] - ts[0]).total_seconds() / 60, 1)
    me = " + ".join(f"{m} {e}" for (m, e), _ in combos.most_common()) or "?"
    # /rename > ai-title > first prompt > first non-setting slash command (a chat opened with a bare `prog>` /
    # slash command never gets an ai-title; `/model` + `/progress-report` only -> "/progress-report")
    return {"title": custom or title or first or slash, "model_effort": me, "prompts": prompts, "minutes": mins}


def limits_from(s):
    """statusline.py snapshot {start, last} -> start/end % per window, mid-session reset flags and cost.
    The start limits can be stale (taken from the last session's values): a window whose old reset time had already
    passed when this session began reset *before* it, so it starts at 0% and is not a mid-session reset."""
    a, b = s.get("start") or {}, s.get("end") or s.get("last") or {}
    out = {"cost": b.get("cost")}
    for k in ("5h", "7d"):
        x, y = a.get(k) or {}, b.get(k) or {}
        x0, rx, ry = x.get("used_percentage"), x.get("resets_at"), y.get("resets_at")
        if isinstance(rx, (int, float)) and isinstance(ry, (int, float)):
            changed = abs(rx - ry) > 300
            if changed and rx <= (a.get("t") or 0):
                x0, changed = 0, False
        else:
            changed = bool(rx and ry and rx != ry)
        out[k] = (x0, y.get("used_percentage"))
        out[k + "_reset"] = changed
        out[k + "_pre"] = ((s.get("pre") or {}).get(k) or {}).get("used_percentage") if changed else None
    return out


def limits(sid):
    try:
        with open(os.path.join(STATE, sid + ".json"), encoding="utf-8") as f:
            s = json.load(f)
        return dict(limits_from(s), others=others(sid, s))
    except (OSError, ValueError, TypeError):
        return {}


def others(sid, s):
    """Nº of other chats of the same account (same weekly reset time) that spent $ between this one's first prompt and
    its last answer ("spans", written by statusline.py): they also moved the 5 h / weekly %, so start→end isn't this
    chat's usage. A chat used only before or after this one doesn't count. Old state files (only "active", the last
    spend) count if that spend is in the window."""
    t0 = (s.get("start") or {}).get("t") or 0
    t1 = (s.get("end") or {}).get("t") or float("inf")
    week = lambda d: ((d.get("last") or {}).get("7d") or {}).get("resets_at")
    mine, n = week(s), 0
    for name in os.listdir(STATE):
        p = os.path.join(STATE, name)
        if name == sid + ".json" or not name.endswith(".json") or name.startswith(("_", "pending-")) or os.path.getmtime(p) <= t0:
            continue
        try:
            o = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        w = week(o)
        same = not (isinstance(w, (int, float)) and isinstance(mine, (int, float)) and abs(w - mine) > 300)
        spans = o.get("spans") or [[o.get("active") or 0] * 2]
        n += same and any(a <= t1 and b > t0 for a, b in spans)
    return n


PAR = {"par", "nousage", "solo$"}


def par_flag(args):
    """`costlog> par 4 5 nota` (also nousage / solo$): other chats ran at the same time. `par?` also opens the form.
    -> (par, ask, rest of the args)."""
    t = args.split(maxsplit=1)
    if not t or t[0].lower().rstrip("?") not in PAR:
        return False, False, args
    return True, t[0].endswith("?"), t[1] if len(t) > 1 else ""


def pct_per_usd(path=None):
    """Median 5 h % per $ of the logged single-chat sessions (≥ $0.30, no reset, not parallel); None if < 5 of them."""
    try:
        rows = list(csv.DictReader(open(path or LOG_CSV, encoding="utf-8-sig")))
    except OSError:
        return None
    r = []
    for x in rows:
        try:
            c, d = float(x["cost_usd"]), float(x["h5_end"]) - float(x["h5_start"])
        except (KeyError, TypeError, ValueError):
            continue
        if c >= 0.3 and d >= 0 and x.get("h5_reset") != "True" and x.get("parallel") != "True":
            r.append(d / c)
    return statistics.median(r) if len(r) >= 5 else None


def par_estimate(u):
    """5 h % this chat probably used, from its own $ (unaffected by other chats) -> (value, ratio) or (None, None)."""
    k, c = pct_per_usd(), u.get("cost")
    return (round(c * k, 1), k) if k and isinstance(c, (int, float)) else (None, None)


def par_fields(u):
    v, k = par_estimate(u)
    n = u.get("others")
    who = T("{n} chat(s) más", n=n) if n else T("Otros chats")
    est = T("{k:.2f} %/$ (mediana de las sesiones sin paralelo)", k=k) if k else T("? (aún no hay datos)")
    return [("u5h", "Usage 5h (%)", "" if v is None else f"{v:g}", T(
        "{who} a la vez: el % medido no es solo de este. Estimación = $ de este chat × {est}. Opcional.", who=who, est=est), True)]


def num(x):
    return "?" if x is None else f"{x:g}"


def usage_text(u, mins):
    parts = []
    for k, lab, _ in WINDOWS:
        x, y = u.get(k, (None, None))
        if x is not None or y is not None:
            parts.append(f"{lab} {num(x)}%→{num(y)}%" + (" " + T("⚠reinicio a mitad") if u.get(k + "_reset") else ""))
    if u.get("cost") is not None:
        parts.append(f"${u['cost']:.2f}")
    if mins is not None:
        parts.append(f"{mins:g} min")
    if u.get("parallel"):
        n = u.get("others")
        parts.append(T("⚠{who} en paralelo: % no fiable", who=f"{n} chat(s)" if n else "chats"))
    return ", ".join(parts) or "?"


def usage_fields(u):
    """Form fields for the usage estimate when a limit reset mid-session ([] if none): one per window, 5 h first.
    The window that didn't reset is pre-filled with its measured difference."""
    if not any(u.get(k + "_reset") for k, *_ in WINDOWS):
        return []
    fields = []
    for k, lab, name in WINDOWS:
        x, y = u.get(k, (None, None))
        p = u.get(k + "_pre")
        if u.get(k + "_reset") and None not in (p, x, y):
            fields.append(("u" + k, f"Usage {lab} (%)", f"{p - x + y:g}", T(
                "Se reinició {name} a mitad de la sesión: {x}%→{p}% antes y 0%→{y}% después. Estimación = la suma; "
                "aproximada si había otros chats a la vez. Cámbiala si quieres (opcional).",
                name=name, x=num(x), p=num(p), y=num(y)), True))
        elif u.get(k + "_reset"):
            fields.append(("u" + k, f"Usage {lab} (%)", "", T(
                "Se reinició {name} a mitad de la sesión: lo medido ({x}%→{y}%) no dice cuánto gastó. Pon tu "
                "estimación (opcional).", name=name, x=num(x), y=num(y)), True))
        else:
            d = f"{y - x:g}" if x is not None and y is not None else ""
            fields.append(("u" + k, f"Usage {lab} (%)", d, T(
                "No se reinició: relleno con lo medido ({x}%→{y}%). Opcional.", x=num(x), y=num(y)), False))
    return fields


def form(title, fields, check, save, error=""):
    """fields: (key, label, prefill, hint, red). check(values) -> error text, or None (it may normalise values).
    save(values) writes the row; the window only closes once it succeeds (e.g. the CSV open in Excel -> stays open
    with the error)."""
    import tkinter as tk
    root = tk.Tk()
    root.title(title)
    root.attributes("-topmost", True)  # appear in front once, then behave like a normal window (minimizable)
    root.after(500, lambda: root.attributes("-topmost", False))
    v, entries = {}, []
    for i, (k, lab, val, hint, red) in enumerate(fields):
        tk.Label(root, text=lab, font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="nw", padx=10, pady=8)
        v[k] = tk.StringVar(value=val)
        e = tk.Entry(root, textvariable=v[k], width=60)
        e.grid(row=i, column=1, sticky="n", padx=10, pady=8)
        entries.append(e)
        tk.Label(root, text=hint, fg="red" if red else "gray", wraplength=340, justify="left").grid(
            row=i, column=2, sticky="nw", padx=10, pady=8)
    err = tk.Label(root, fg="red", text=error, wraplength=700)
    err.grid(row=20, column=0, columnspan=3)

    def ok(*_):
        vals = {k: x.get().strip() for k, x in v.items()}
        msg = check(vals)
        if msg:
            err["text"] = msg
            return
        try:
            save(vals)
        except OSError as e:
            err["text"] = locked(e.filename or T("el CSV"))
            return
        root.destroy()

    bar = tk.Frame(root)
    bar.grid(row=21, column=0, columnspan=3, pady=10)
    tk.Button(bar, text=T("Apuntar (Enter)"), command=ok).pack(side="left", padx=5)
    tk.Button(bar, text=T("Cancelar (Esc)"), command=root.destroy).pack(side="left", padx=5)
    root.bind("<Return>", ok)
    root.bind("<Escape>", lambda e: root.destroy())
    first_empty = next((e for f, e in zip(fields, entries) if not f[2]), entries[0])
    root.after(100, lambda: (root.focus_force(), first_empty.focus_set()))
    root.mainloop()


def cost_form(pre, extra, save):
    """extra: additional fields, e.g. the usage estimate after a mid-session reset."""
    fields = [("task", T("Tarea"), pre.get("task", ""), T("Viene del título del chat; cámbialo si no dice qué se hizo. "
               "Corto: área/asignatura + comando + ref, p. ej. «Prog práctica 2», «Gmail: borrador al profe de Cálculo»."), False),
              ("ses", T("Nota sesión"), pre.get("ses", ""), T("1–5 (vale 4.5)."), False),
              ("pdf", T("Nota PDF"), pre.get("pdf", "-"), T("1–5 · - o NA si no hay PDF que valorar · pendiente."), False),
              ("corr", T("Correcciones"), pre.get("corr", "0"),
               T("Nº de respuestas que tuviste que corregir o repedir (? si no lo sabes)."), False),
              ("note", T("Nota libre"), pre.get("note", ""), T("Qué fue bien / mal (opcional)."), False)] + extra

    def check(f):
        s, p = grade(f["ses"]), grade(f["pdf"], pdf=True)
        if not s:
            return T("Nota sesión: un número del 1 al 5")
        if not p:
            return T("Nota PDF: 1–5, o - / NA si no hay PDF, o pendiente")
        f.update(ses=s, pdf=p)

    form(f"costlog> — {pre.get('task') or T('apuntar en costlog')}", fields, check, save, pre.get("err", ""))


def gather(hook):
    """Everything automatic, frozen at the moment of `costlog>` (later work in the session doesn't count)."""
    return {"date": datetime.now().strftime("%Y-%m-%d"), "sid": hook.get("session_id", ""),
            "project": os.path.basename(os.path.normpath(hook.get("cwd") or "")) or "?",
            "st": transcript_stats(hook.get("transcript_path", "")), "u": limits(hook.get("session_id"))}


def manual_usage(f):
    """The two form boxes (u5h, u7d) -> e.g. "6% 5h, 1% sem" ("" if both empty)."""
    return ", ".join(f"{f[k].rstrip('%').strip()}% {lab}" for k, lab in (("u5h", "5h"), ("u7d", "sem")) if f.get(k))


def build(ctx, f):
    """f: task, ses, pdf, corr, note[, u5h, u7d] -> (one-line summary for the reply, csv row)."""
    st, u, project, date = ctx["st"], ctx["u"], ctx["project"], ctx["date"]
    task = f.get("task") or st["title"] or "?"
    corr = f.get("corr") or "?"
    note = f.get("note") or "—"
    manual = manual_usage(f)
    if not manual and u.get("parallel"):
        v, k = par_estimate(u)
        manual = f"≈{v:g}% 5h (${u['cost']:.2f} × {k:.2f} %/$, paralelo)" if v is not None else ""
    usage = usage_text(u, st["minutes"]) + (" · " + T("tu estimación: {m}", m=manual) if manual else "")
    line = f"{date} · {task} ({project}) · {st['model_effort']} · {st['prompts']} · {corr} · {f['ses']} · {f['pdf']} · {usage} · {note}"
    h5, wk = u.get("5h", (None, None)), u.get("7d", (None, None))
    row = [date, ctx["sid"], project, task, st["model_effort"], st["prompts"], corr, f["ses"], f["pdf"],
           h5[0], h5[1], u.get("5h_reset", ""), wk[0], wk[1], u.get("7d_reset", ""), u.get("parallel", ""), u.get("cost"), st["minutes"], manual, note]
    return line, ["" if x is None else x for x in row]


def append(row, path=None, cols=None):
    """Raises OSError (PermissionError) if the CSV is locked, e.g. open in Excel; nothing is written then."""
    path = path or LOG_CSV
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8-sig" if new else "utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(cols or CSV_COLS)
        w.writerow(row)


MARK = os.path.join(STATE, "_leftover_mark.json")


def leftover(argv):
    """`--mark` before a `leftover n>` subagent step, `--leftover --task … ` after it: one costlog.csv row with
    session_id "leftover", 5 h / weekly % and $ from the status line's last limits at mark vs now.
    ponytail: limits are as fresh as the last status-line refresh; check the first real rows look right."""
    import argparse
    p = argparse.ArgumentParser(prog="costlog.py --leftover")
    for a in ("task", "project", "model"):
        p.add_argument("--" + a, required=True)
    p.add_argument("--tokens", required=True)
    p.add_argument("--minutes", type=float, required=True)
    p.add_argument("--note", default="")
    a = p.parse_args(argv)
    load = lambda path: json.load(open(path, encoding="utf-8"))
    try:
        start, now = load(MARK), load(os.path.join(STATE, "_last_limits.json"))
    except (OSError, ValueError):
        start, now = {}, {}
    u = limits_from({"start": start, "last": now})
    c0, c1 = start.get("cost"), now.get("cost")
    same = start.get("sid") and start.get("sid") == now.get("sid") and None not in (c0, c1)
    u["cost"] = round(c1 - c0, 4) if same else None
    st = {"title": a.task, "model_effort": a.model, "prompts": "—", "minutes": a.minutes}
    ctx = {"date": datetime.now().strftime("%Y-%m-%d"), "sid": "leftover", "project": a.project, "st": st, "u": u}
    line, row = build(ctx, {"task": a.task, "corr": "—", "ses": "", "pdf": "", "note": a.note})
    row[CSV_COLS.index("usage_manual")] = f"{a.tokens} tokens (subagent)"
    try:
        append(row)
    except OSError:
        sys.exit(f"NOT LOGGED: {os.path.basename(LOG_CSV)} is open (Excel?) and can't be written.\n{line}")
    print("logged:", line)


def reply(text):
    print(json.dumps({"decision": "block", "reason": text}))
    sys.exit(0)


def form_later(path):
    """Detached process: show the form (as long as needed, e.g. minimized while I check the PDF), then log."""
    with open(path, encoding="utf-8") as f:
        job = json.load(f)
    if job.get("kind") == "block":
        block_form(job["ctx"], job["pre"])
    else:
        u = job["ctx"]["u"]
        cost_form(job["pre"], par_fields(u) if u.get("parallel") else usage_fields(u), lambda f: append(build(job["ctx"], f)[1]))
    os.remove(path)


def spawn(job):
    """Open the form in a separate process that outlives the hook, so it can stay minimized as long as needed."""
    path = os.path.join(STATE, f"pending-{job['kind']}-{job['ctx']['sid']}-{datetime.now():%H%M%S}.json")
    os.makedirs(STATE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(job, f)
    detach([sys.executable, os.path.abspath(__file__), "--form", path])


def detach(cmd):
    args = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    if os.name != "nt":  # Mac / Linux: own session, so it survives the hook
        subprocess.Popen(cmd, start_new_session=True, **args)
        return
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:  # outlive the hook even if Claude Code kills its process tree
        subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **args)
    except OSError:
        subprocess.Popen(cmd, creationflags=flags, **args)


def blocks(path, since="", oks=None):
    """Blocked tool calls in the transcript after `since` (ISO timestamp) -> [{ts, id, tool, cmd, full, err, model, cwd}].
    oks (dict): filled with "tool: cmd" -> [(ts, path)] of the calls that went through (a later success = solved)."""
    uses, out = {}, []
    try:
        f = open(path, encoding="utf-8")
    except OSError:
        return []
    with f:
        for line in f:
            if '"tool_use"' not in line and '"is_error":true' not in line and (oks is None or '"tool_result"' not in line):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            for x in (d.get("message") or {}).get("content") or []:
                if not isinstance(x, dict):
                    continue
                if x.get("type") == "tool_use":
                    i = x.get("input") or {}
                    cmd = i.get("command") or i.get("file_path") or i.get("url") or json.dumps(i, ensure_ascii=False)
                    m = str((d.get("message") or {}).get("model", ""))
                    uses[x.get("id")] = {"tool": x.get("name", "?"), "cmd": " ".join(str(cmd).split())[:150], "full": str(cmd),
                                         "model": f"{pretty(m)} {d.get('effort') or '?'}" if m.startswith("claude") else "?",
                                         "cwd": d.get("cwd") or ""}
                elif x.get("type") == "tool_result" and d.get("timestamp", "") > since:
                    c = x.get("content")
                    t = c if isinstance(c, str) else " ".join(y.get("text", "") for y in c or [] if isinstance(y, dict))
                    u = uses.get(x.get("tool_use_id")) or {"tool": "?", "cmd": "", "full": "", "model": "?", "cwd": ""}
                    # a call that ran and failed ("Exit code 1" + output quoting these words) isn't a block
                    if x.get("is_error") and BLOCK.search(t[:400]) and not t.lstrip().startswith("Exit code"):
                        out.append(dict(u, ts=d["timestamp"], id=x.get("tool_use_id", ""), err=t))
                    elif oks is not None and not x.get("is_error") and u["cmd"]:
                        oks.setdefault(f"{u['tool']}: {u['cmd']}", []).append((d["timestamp"], path))
    return out


def kind(t):
    if "no verdict" in t:
        return "outage clasificador"
    m = re.search(r"classifier\. Reason: \[([^\]]+)\]", t)
    if m:
        return f"denegado [{m[1]}]"
    if "auto mode classifier" in t:
        return "denegado clasificador"
    if "PreToolUse:" in t:
        return "hook PreToolUse"
    if re.search(r"safety check|protected from removal|Blocked:", t):
        return "safety check"
    if "on this domain" in t:
        return "Chrome: dominio sin permiso"
    return "otro"


def short(t):
    """First two sentences of the error (the rest is advice to the model)."""
    t = re.sub(r"</?tool_use_error>", "", t).strip()
    return " ".join(re.split(r"(?<=[.!])\s+", t)[:2])[:300]


def local(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()


def block_pre(bs):
    """Blocks of one incident -> row values."""
    if not bs:
        return {}
    a, b = (local(x["ts"]).strftime("%H:%M") for x in (bs[0], bs[-1]))
    uniq = lambda xs: " | ".join(dict.fromkeys(xs))
    return {"date": local(bs[0]["ts"]).strftime("%Y-%m-%d"), "until": bs[-1]["ts"], "time": a if a == b else f"{a}–{b}",
            "tipo": uniq(kind(x["err"]) for x in bs), "bloqueado": uniq(f"{x['tool']}: {x['cmd']}" for x in bs)[:600],
            "error": uniq(short(x["err"]) for x in bs)[:900]}


def transcripts(sid=None, since=0.0):
    """(path, chat id, is_subagent) of every chat's transcript and its subagents' (or only chat `sid`'s), modified
    after `since` (epoch). Read from disk, so closed and idle chats count too."""
    sub = os.path.join(PROJECTS, "*", sid or "*", "subagents", "*.jsonl")
    for p in glob.glob(os.path.join(PROJECTS, "*", (sid or "*") + ".jsonl")) + glob.glob(sub):
        try:
            if os.path.getmtime(p) <= since:
                continue
        except OSError:  # deleted between glob and here (a chat being cleaned up)
            continue
        s = os.path.basename(os.path.dirname(p)) == "subagents"
        yield p, os.path.basename(os.path.dirname(os.path.dirname(p))) if s else os.path.basename(p)[:-6], s


def blog_rows():
    try:
        with open(BLOG_CSV, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def blog_write(rows):
    """Rewrites blocklog.csv (atomic). Raises OSError if it's locked (open in Excel): nothing written then."""
    tmp = BLOG_CSV + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, BLOG_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    try:
        os.replace(tmp, BLOG_CSV)
    except OSError:
        os.remove(tmp)
        raise


def logged_test(rows):
    """-> f(chat id, block): True if a row already has it: by tool_use id, or (rows from before the ids column, some
    written by hand like "20:3x") same chat + date + time within the row's span ±15 min, or the per-chat mark that
    `blocklog>` wrote before the automatic scan (blocklog-<chat>.json)."""
    ids, spans, until = set(), [], {}
    for r in rows:
        if r.get("ids"):
            ids.update(r["ids"].split())
            continue
        t = re.findall(r"(\d{1,2}):(\d)([\dx])", r.get("time") or "")
        if t:
            at = lambda h, m, s, x: datetime.fromisoformat(f"{r['date']}T{int(h):02}:{m}{s.replace('x', x)}")
            spans.append((r["session_id"].split(" ")[0], at(*t[0], "0").timestamp() - 900, at(*t[-1], "9").timestamp() + 960))
    for p in glob.glob(os.path.join(STATE, "blocklog-*-*.json")):
        try:
            until[os.path.basename(p)[9:-5]] = json.load(open(p, encoding="utf-8"))["until"]
        except (OSError, ValueError, KeyError):
            pass

    def test(sid, b):
        t = local(b["ts"]).timestamp()
        return b["id"] in ids or b["ts"] <= until.get(sid, "") or any(s == sid and a <= t <= z for s, a, z in spans)
    return test


def chat_of(path):
    s = os.path.basename(os.path.dirname(path)) == "subagents"
    return os.path.basename(os.path.dirname(os.path.dirname(path))) if s else os.path.basename(path)[:-6]


def scan(rows, files, close_all=False, now=None):
    """Adds to `rows` one row per unlogged incident (solución «pendiente») from `files` (transcripts()), and marks
    pending rows solved when the same tool + command later went through. Open incidents (last block < GAP ago) wait
    for a later scan unless close_all. -> (new rows, updated rows)."""
    now = now or datetime.now().timestamp()
    seen, oks, new = logged_test(rows), {}, []
    for path, sid, sub in files:
        bs = [b for b in blocks(path, START, oks) if not seen(sid, b)]
        groups = []
        for b in bs:
            if groups and local(b["ts"]).timestamp() - local(groups[-1][-1]["ts"]).timestamp() <= GAP:
                groups[-1].append(b)
            else:
                groups.append([b])
        if groups and not close_all and now - local(groups[-1][-1]["ts"]).timestamp() < GAP:
            groups.pop()  # still going on: a later scan logs it whole
        for g in groups:
            pre = block_pre(g)
            new.append({"date": pre["date"], "time": pre["time"], "session_id": sid + (" (subagent)" if sub else ""),
                        "project": os.path.basename(os.path.normpath(g[0]["cwd"])) if g[0]["cwd"] else "?",
                        "model_effort": g[-1]["model"], "n_blocks": len(g), "tipo": pre["tipo"],
                        "bloqueado": pre["bloqueado"], "error": pre["error"], "intento": "", "solucion": PEND,
                        "ids": " ".join(x["id"] for x in g), "_end": local(pre["until"]).timestamp()})
    rows += new
    upd = []
    for r in rows:
        end = r.pop("_end", None)
        if r.get("solucion") != PEND:
            continue
        hm = re.findall(r"\d{1,2}:\d\d", r.get("time") or "")
        if end is None and hm:  # pending row from an earlier scan: its last HH:MM
            end = datetime.fromisoformat(f"{r['date']}T{hm[-1]:0>5}").timestamp()
        if end is None:
            continue
        later = [(ts, p) for k in r["bloqueado"].split(" | ") for ts, p in oks.get(k, []) if local(ts).timestamp() > end]
        if later:
            ts, p = min(later)
            when = local(ts).strftime("%Y-%m-%d %H:%M")
            r["solucion"] = (T("funcionó al reintentarlo en este chat ({w})", w=when)
                             if chat_of(p) == r["session_id"].split(" ")[0]
                             else T("funcionó después en el chat {c} ({w})", c=chat_of(p)[:8], w=when))
            upd.append(r)
    return new, upd


def autoscan():
    """At most every 10 min (on any prompt of any chat), a detached `costlog.py --blockscan`: 0 tokens, no wait."""
    p = os.path.join(STATE, "blocklog-spawn")
    try:
        if datetime.now().timestamp() - os.path.getmtime(p) < 600:
            return
    except OSError:
        pass
    try:
        os.makedirs(STATE, exist_ok=True)
        open(p, "w").close()
        detach([sys.executable, os.path.abspath(__file__), "--blockscan"])
    except OSError:
        pass


def blockscan(now=None):
    """Every chat's transcripts changed since the last scan (minus GAP + 10 min, so incidents open then are re-read).
    The first scan reads them all (in the background; ~30 s for a few GB)."""
    t0 = now or datetime.now().timestamp()
    try:
        since = json.load(open(SCAN, encoding="utf-8"))["t"] - GAP - 600
    except (OSError, ValueError, KeyError):
        since = 0.0
    rows = blog_rows()
    new, upd = scan(rows, transcripts(since=since), now=t0)
    if new or upd:
        blog_write(rows)  # locked (Excel) -> OSError, SCAN not moved: the next scan retries
    os.makedirs(STATE, exist_ok=True)
    with open(SCAN, "w", encoding="utf-8") as f:
        json.dump({"t": t0}, f)
    return new, upd


def block_save(ctx, f):
    """Manual row from the form (a block the transcripts don't show, e.g. a hung shell) -> one-line summary."""
    row = [ctx["date"], f.get("time", ""), ctx["sid"], ctx["project"], ctx["model_effort"], ctx["n"], f.get("tipo", ""),
           f.get("bloqueado", ""), f.get("error", ""), f.get("intento", ""), f.get("solucion", ""), ""]
    append(row, BLOG_CSV, BLOG_COLS)
    return (f"{ctx['date']} {f.get('time', '')} · {ctx['project']} · {ctx['model_effort']} · {ctx['n']}× "
            f"{f.get('tipo', '')} · {f.get('bloqueado', '')[:80]} · {f.get('solucion', '')}")


def block_form(ctx, pre):
    fields = [("time", T("Cuándo"), pre.get("time", ""), T("Hora (HH:MM).") + " " + T("Si no fue hoy ({d}), pon también el día.", d=ctx["date"]), True),
              ("tipo", T("Tipo"), pre.get("tipo", ""), T("outage clasificador (no verdict) · denegado [motivo] · "
               "safety check · shell colgado · otro."), True),
              ("bloqueado", T("Qué se bloqueó"), pre.get("bloqueado", ""), T("Herramienta: comando."), True),
              ("error", T("Error"), pre.get("error", ""), T("Texto exacto del error (primeras frases)."), True),
              ("intento", T("Qué se intentó"), pre.get("intento", ""), T("Reintentos, ! comando, Shift+Tab a modo "
               "manual, regla en settings… (opcional)."), False),
              ("solucion", T("Solución"), pre.get("solucion", ""), T("Cómo se arregló, o «sin resolver»."), False)]

    def check(f):
        if not f["bloqueado"]:
            return T("Qué se bloqueó: pon al menos la herramienta o el comando.")
        if not f["solucion"]:
            return T("Solución: cómo se arregló, o «sin resolver».")

    form(T("blocklog> — apuntar a mano ({p})", p=ctx["project"]), fields, check, lambda f: block_save(ctx, f),
         pre.get("err", ""))


def block_main(hook, args):
    """`blocklog> [solución]`: logs this chat's unlogged blocks now (its subagents' too, open incidents included) and
    puts the text as solución of this chat's pending rows. Nothing found and nothing pending -> the manual form."""
    sid, text = hook.get("session_id", ""), args.strip()
    rows = blog_rows()
    new, upd = scan(rows, transcripts(sid), close_all=True) if sid else ([], [])
    mine = [r for r in rows if sid and r["session_id"].split(" ")[0] == sid and r.get("solucion") == PEND]
    if text:
        for r in mine:
            r["solucion"] = text
    if new or upd or (text and mine):
        try:
            blog_write(rows)
        except OSError:
            reply(T("⚠ blocklog.csv está abierto (¿Excel?): ciérralo y vuelve a escribir el blocklog>. "
                    "No se pierde nada: los bloqueos siguen en el transcript."))
    if new or mine:
        reply(T("✅ blocklog.csv: {n} incidente(s) nuevo(s) de este chat", n=len(new))
              + (T("; solución «{t}» en {k} fila(s)", t=text, k=len(mine)) if text and mine else
                 T("; {k} fila(s) de este chat siguen «pendiente» (blocklog> <solución> la rellena)", k=len(mine)) if mine else "")
              + "".join(f"\n· {r['date']} {r['time']} · {r['tipo']} · {r['bloqueado'][:80]} · {r['solucion']}"
                        for r in (mine or new)[-5:]))
    g = gather(hook)
    ctx = {"date": g["date"], "sid": sid, "project": g["project"], "model_effort": g["st"]["model_effort"], "n": 0}
    spawn({"kind": "block", "ctx": ctx, "pre": {"solucion": text}})
    reply(T("📝 blocklog>: no hay bloqueos sin apuntar ni pendientes en este chat (se apuntan solos, de todos los chats, "
            "como mucho cada 10 min): ventana abierta para apuntar uno a mano."))


def clip(text):
    """Text -> clipboard: Windows clip.exe (reads UTF-16LE as Unicode); Mac pbcopy; Linux wl-copy or xclip
    (Mac/Linux untested). -> True if copied."""
    if os.name == "nt":
        cmds, data = [["clip"]], text.encode("utf-16-le")
    else:
        cmds, data = [["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]], text.encode("utf-8")
    for c in cmds:
        try:
            if subprocess.run(c, input=data, timeout=5, capture_output=True).returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    return False


def allow_text(b):
    """Standard consent sentence for one denied call: the exact action, the classifier's reason, the scope."""
    why = kind(b["err"]).removeprefix("denegado ")
    cmd = " ".join(b["full"].split())  # one line: readable in the prompt box
    cmd = cmd if len(cmd) <= 600 else cmd[:600] + " […]"
    return T("Autorizo explícitamente la acción que el clasificador de auto mode te denegó a las {hm} ({why}): "
             "{tool}: {cmd} — solo esa acción, solo en este chat y una vez: reinténtala tal cual. Si necesitas "
             "cambiarla, no la hagas y pregúntame.", hm=f"{local(b['ts']):%H:%M}",
             why=why if why.startswith("[") else T("sin motivo"), tool=b["tool"], cmd=cmd)


def allow_main(hook, n, extra, copy=clip):
    """`allow>` / `allow N>`: the consent sentence for this chat's last (or Nth last) classifier denial, subagents
    included, goes to the clipboard; the person pastes it and sends it. The hook never sends or injects it: consent
    has to be the person's own message (a script writing it alone = forged consent, refused as [Auto-Mode Bypass])."""
    if extra.strip():
        reply(T("🔁 ¿Te referías a `allow {n}>`?", n=extra.strip()) if extra.strip().isdigit() else
              T("🛡 Uso: `allow>` (última denegación de este chat) o `allow N>` (la N-ésima más reciente)."))
    sid = hook.get("session_id") or ""
    bs = sorted((b for p, _, _ in transcripts(sid) if sid for b in blocks(p) if kind(b["err"]).startswith("denegado")),
                key=lambda b: b["ts"], reverse=True)[:5]
    if not bs:
        reply(T("🛡 allow>: no hay denegaciones del clasificador en este chat. Un outage («no verdict») se arregla "
                "reintentando; un hook o un safety check no se saltan con permiso."))
    i = int(n or 1)
    if i > len(bs):
        reply(T("🛡 allow>: este chat solo tiene {n} denegación(es) recientes; usa `allow 1>`…`allow {n}>`.", n=len(bs)))
    t = allow_text(bs[i - 1])
    reply((T("📋 Copiado al portapapeles: léelo, pégalo (Ctrl+V) y envíalo tú.") if copy(t) else
           T("⚠ No pude copiarlo: selecciónalo abajo, cópialo y envíalo tú."))
          + " " + T("Alternativa sin pegar: /permissions → Recently denied.") + "\n"
          + "".join(f"\n{'→' if k == i else ' '} {k}. {local(b['ts']):%H:%M} · {kind(b['err'])} · {b['tool']}: {b['cmd'][:90]}"
                    for k, b in enumerate(bs, 1))
          + "\n\n" + t)


def first_prompt(sid):
    """A chat's usage counts from its first prompt, not from when it was opened (chats opened and left idle showed
    false mid-session resets): retake the start snapshot from the latest limits any session saw."""
    path = os.path.join(STATE, f"{sid}.json")
    try:
        s = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
        if not sid or s.get("prompted"):
            return
        last = json.load(open(os.path.join(STATE, "_last_limits.json"), encoding="utf-8"))
        s.pop("pre", None)  # a reset while idle doesn't count
        start = {"t": datetime.now().timestamp(), "cost": 0, "5h": last.get("5h"), "7d": last.get("7d")}
        s.update(prompted=True, start=start, last=start)  # last too: statusline.py spots resets against it
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(s, f)
        os.replace(path + ".tmp", path)
    except (OSError, ValueError):
        pass  # never block a prompt over this


def main():
    hook = json.loads(sys.stdin.buffer.read() or b"{}")
    held = wait and wait.hook(hook)  # blocks `wait>` and its listings; `go>` / `trigger>` / `wait plan>` -> output for Claude
    s = send and send.TRIGGER.match(hook.get("prompt", ""))
    if s:
        detach([sys.executable, send.__file__, "--window", s[1] or ""])
        kw = (s[1] or "").strip()
        reply(T("📨 send>: ventana de borradores abierta (primero los que contienen «{kw}»). Envías tú con el botón.", kw=kw)
              if kw else T("📨 send>: ventana de borradores abierta. Envías tú con el botón."))
    if VTRIGGER.match(hook.get("prompt", "")) and os.path.exists(VAULT):
        detach([sys.executable, VAULT, "open"])
        reply(T("🔐 vault>: ventana abierta (Show / Copy / Add / Generate / Delete). Claude no ve nada de lo que hagas ahí."))
    lg = LTRIGGER.match(hook.get("prompt", ""))
    if lg and os.path.exists(LOGIN):
        if os.name != "nt":  # no console of its own to open here: login.py asks y/n, so it needs a terminal
            reply(T("🔑 login>: en una terminal: {cmd}", cmd=f'"{sys.executable}" "{os.path.abspath(LOGIN)}" {lg[1].strip()}'))
        flags = subprocess.CREATE_NEW_CONSOLE  # own window: login.py asks y/n and `claude auth login` waits there
        try:  # outlive the hook even if Claude Code kills its process tree (as detach())
            subprocess.Popen([sys.executable, LOGIN, lg[1].strip()], creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB)
        except OSError:
            subprocess.Popen([sys.executable, LOGIN, lg[1].strip()], creationflags=flags)
        reply(T("🔑 login>: ventana abierta. Confirma allí la cuenta; cambia la cuenta de todos los chats abiertos."))
    b = BTRIGGER.match(hook.get("prompt", ""))
    if b:
        block_main(hook, b[1])
    a = ATRIGGER.match(hook.get("prompt", ""))
    if a:
        allow_main(hook, a[1], a[2])
    m = TRIGGER.match(hook.get("prompt", ""))
    if not m:
        first_prompt(hook.get("session_id"))
        autoscan()  # blocklog: logs every chat's blocks by itself (detached, at most every 10 min)
        carpetas.hook(hook)  # blocks or adds the folder when the prompt is `<carpeta>:` (or a y/n/m answer to it)
        if held:
            print(json.dumps(held))
        return
    par, ask, args = par_flag(m[1])
    pre, ok = parse(args)
    ctx = gather(hook)
    u = ctx["u"]
    u["parallel"] = bool(par or u.get("others"))
    reset = not u["parallel"] and bool(usage_fields(u))  # parallel: the $-based estimate beats the reset one
    if ok and not reset and not ask:
        line, row = build(ctx, pre)
        try:
            append(row)
            reply(T("✅ apuntado en {f}:", f="costlog.csv") + "\n" + line)
        except OSError:
            pre["err"] = LOCKED
    pre["task"] = ctx["st"]["title"]
    spawn({"kind": "cost", "ctx": ctx, "pre": pre})
    reply(T("📝 costlog>: ventana abierta (puedes minimizarla y rellenarla cuando quieras); los datos de uso quedan "
            "congelados ahora. Se apunta en costlog.csv al pulsar Apuntar.")
          + (" " + T("⚠ Hubo un reinicio de límite: pon el usage aproximado.") if reset else "")
          + (" " + T("⚠ Otros chats a la vez: usage estimado a partir del $ de este chat.") if u["parallel"] else "")
          + (" " + T("⚠ {f} está abierto (¿Excel?): ciérralo antes de pulsar Apuntar.", f="costlog.csv")
             if pre.get("err") else ""))


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        if "textos" in sys.modules:
            sys.modules["textos"].TX.clear()  # the asserts below expect the Spanish texts
        assert parse("4 5 se dejó X") == ({"ses": "4", "pdf": "5", "note": "se dejó X"}, True)
        assert parse("4 NA") == ({"ses": "4", "pdf": "—", "note": ""}, True)
        assert parse("4,5 - bien") == ({"ses": "4.5", "pdf": "—", "note": "bien"}, True)
        assert parse("3 pendiente") == ({"ses": "3", "pdf": "pendiente", "note": ""}, True)
        assert parse("") == ({"note": ""}, False)
        assert parse("4") == ({"ses": "4", "pdf": "—", "corr": "0", "note": ""}, True)
        assert parse("4 bien") == ({"ses": "4", "note": "bien"}, False)
        assert parse("4 bien hecho") == ({"ses": "4", "note": "bien hecho"}, False)
        assert parse("bien 4 5") == ({"note": "bien 4 5"}, False)
        assert parse("7 5") == ({"note": "7 5"}, False)
        assert pretty("claude-haiku-4-5-20251001") == "Haiku 4.5" and pretty("claude-opus-5-5") == "Opus 5.5"
        assert TRIGGER.match("costlog >") and TRIGGER.match("Costlog> 4 5") and not TRIGGER.match("trial> 4 5") and not TRIGGER.match("HEAT study W3 costlog >")
        assert usage_text({"5h": (22, 27), "5h_reset": True, "cost": 1.284}, 4.0) == "5h 22%→27% ⚠reinicio a mitad, $1.28, 4 min"
        # real 5 h reset mid-session (30cd5a99): only the 5 h one is flagged
        mid = limits_from({"start": {"t": 1791189337, "5h": {"used_percentage": 10, "resets_at": 1791195000},
                                     "7d": {"used_percentage": 1, "resets_at": 1791579600}},
                           "last": {"5h": {"used_percentage": 1, "resets_at": 1791213000},
                                    "7d": {"used_percentage": 2, "resets_at": 1791579600}}})
        assert mid["5h_reset"] and not mid["7d_reset"] and mid["5h"] == (10, 1)
        uf = usage_fields(mid)
        assert [f[0] for f in uf] == ["u5h", "u7d"] and uf[0][2] == "" and uf[1][2] == "1" and uf[0][4] and not uf[1][4]
        # same, with the last % before the reset saved by statusline.py: 10→14 before + 0→1 after = 5
        mid_pre = limits_from({"start": {"t": 1791189337, "5h": {"used_percentage": 10, "resets_at": 1791195000}},
                               "pre": {"5h": {"used_percentage": 14, "resets_at": 1791195000}},
                               "last": {"5h": {"used_percentage": 1, "resets_at": 1791213000}}})
        assert usage_fields(mid_pre)[0][2] == "5"
        # stale start (1e9dfc13): the 5 h window had already reset before the session -> 0%, not a mid-session reset
        stale = limits_from({"start": {"t": 1791214084, "5h": {"used_percentage": 37, "resets_at": 1791213000}},
                             "last": {"5h": {"used_percentage": 9, "resets_at": 1791231600}}})
        assert stale["5h"] == (0, 9) and not stale["5h_reset"] and usage_fields(stale) == []
        assert manual_usage({"u5h": "6", "u7d": "1%"}) == "6% 5h, 1% sem" and manual_usage({"u5h": "", "u7d": ""}) == ""
        # locked csv: append raises, the form catches OSError and stays open
        import tempfile
        LOG_CSV = os.path.join(tempfile.mkdtemp(), "x.csv")
        append(["a"])
        try:
            os.chmod(LOG_CSV, 0o444)
            append(["b"])
            raise AssertionError("append to a read-only csv should fail")
        except PermissionError:
            pass
        # blocklog: real error texts (outage, denial) found in the transcript, matched to their tool call
        assert BTRIGGER.match("Blocklog > se arregló") and not BTRIGGER.match("mira el blocklog>")
        out = "The server-side auto mode classifier gave no verdict (error), so auto mode cannot determine the safety " \
              "of PowerShell. This is a transient failure of the check. You may try the action again once, as-is."
        den = "Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Auto-Mode " \
              "Bypass]. If you have other tasks that don't depend on this action, continue working on those."
        hk = 'PreToolUse:Bash hook error: [python "C:/hooks/guard.py"]: BLOQUEADO por guard: solo con su script.'
        assert BLOCK.search(hk) and kind(hk) == "hook PreToolUse"
        assert kind(out) == "outage clasificador" and kind(den) == "denegado [Auto-Mode Bypass]" and kind("x") == "otro"
        assert short(den).endswith("[Auto-Mode Bypass].") and "try the action again" not in short(out)
        tmp = tempfile.mkdtemp()
        tr = os.path.join(tmp, "t.jsonl")
        use = lambda i, c: {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": i, "name": "PowerShell", "input": {"command": c}}]}}
        res = lambda i, ts, t: {"type": "user", "timestamp": ts, "message": {"content": [
            {"type": "tool_result", "tool_use_id": i, "is_error": True, "content": t}]}}
        with open(tr, "w", encoding="utf-8") as f:
            for d in (use("a", "python  md2pdf.py"), res("a", "2026-10-06T08:00:00Z", out),
                      use("b", "ls"), res("b", "2026-10-06T08:01:00Z", "Exit code 1"),
                      use("c", "python md2pdf.py"), res("c", "2026-10-06T08:05:00Z", den)):
                f.write(json.dumps(d, separators=(",", ":")) + "\n")
        # title: /rename > ai-title > first real prompt (slash-command lines start with "<" and are skipped)
        up = lambda c: {"type": "user", "message": {"content": c}}
        for recs, want in (([up("<command-name>/model</command-name>"), up("prog>")], "prog>"),
                           ([up("<command-name>/model</command-name>"),
                             up("<command-message>progress-report</command-message> "
                                "<command-name>/progress-report</command-name>")], "/progress-report"),
                           ([up("prog>"), {"type": "ai-title", "aiTitle": "AI"}], "AI"),
                           ([{"type": "ai-title", "aiTitle": "AI"}, {"type": "custom-title", "customTitle": "mine"}], "mine")):
            with open(os.path.join(tmp, "tt.jsonl"), "w", encoding="utf-8") as f:
                f.writelines(json.dumps(d) + "\n" for d in recs)
            assert transcript_stats(os.path.join(tmp, "tt.jsonl"))["title"] == want, want
        bs = blocks(tr)
        assert [(x["tool"], x["cmd"]) for x in bs] == [("PowerShell", "python md2pdf.py")] * 2  # "Exit code 1" isn't a block
        bp = block_pre(bs)
        assert bp["tipo"] == "outage clasificador | denegado [Auto-Mode Bypass]" and bp["bloqueado"] == "PowerShell: python md2pdf.py"
        assert "–" in bp["time"] and bp["until"] == "2026-10-06T08:05:00Z"
        # automatic log: every chat + its subagents from disk, one row per incident, deduped by tool_use id
        PROJECTS, STATE = os.path.join(tmp, "projects"), os.path.join(tmp, "state")
        BLOG_CSV, SCAN = os.path.join(tmp, "b.csv"), os.path.join(tmp, "state", "blocklog-scan.json")
        os.makedirs(os.path.join(PROJECTS, "p", "c1", "subagents"))
        ok = lambda i, ts: {"type": "user", "timestamp": ts, "message": {"content": [
            {"type": "tool_result", "tool_use_id": i, "content": "done"}]}}
        sub = lambda d: dict(d, cwd="C:/x/mi-lab", effort="high", message=dict(d["message"], model="claude-opus-5-5"))
        put = lambda path, recs: open(path, "w", encoding="utf-8").writelines(json.dumps(d) + "\n" for d in recs)
        put(os.path.join(PROJECTS, "p", "c1.jsonl"), [  # 3 blocks > 30 min apart = 3 incidents, then one succeeds
            use("a", "python x.py"), res("a", "2026-10-07T08:00:00Z", den), use("b", "rm -r y"), res("b", "2026-10-07T09:00:00Z", out),
            use("e", "cat z"), res("e", "2026-10-07T09:30:00Z", "Exit code 1\nauto mode classifier"),  # ran: not a block
            use("c", "git push"), res("c", "2026-10-07T10:00:00Z", den), use("d", "python x.py"), ok("d", "2026-10-07T11:00:00Z")])
        put(os.path.join(PROJECTS, "p", "c1", "subagents", "agent-1.jsonl"), [sub(use("s", "reg add")), res("s", "2026-10-07T12:00:00Z", den)])
        put(os.path.join(PROJECTS, "p", "c2.jsonl"), [use("h", "ls"), res("h", "2026-10-07T08:31:00Z", den)])
        h2 = local("2026-10-07T08:31:00Z").strftime("%H")  # a row from before the ids column, time written by hand
        append(["2026-10-07", f"~{h2}:3x", "c2", "p", "?", 1, "t", "by hand", "", "", "x"], BLOG_CSV, BLOG_COLS[:-1])
        new, upd = blockscan(now=local("2026-10-08T00:00:00Z").timestamp())
        rows = blog_rows()
        assert len(new) == 4 and len(rows) == 5 and rows[0]["ids"] == "", (new, rows)  # hand row recognised: c2 not logged again
        assert [r["ids"] for r in rows[1:]] == ["a", "b", "c", "s"] and rows[4]["session_id"] == "c1 (subagent)"
        assert rows[4]["model_effort"] == "Opus 5.5 high" and rows[4]["project"] == "mi-lab"
        assert rows[1]["solucion"].startswith("funcionó al reintentarlo en este chat (2026-10-07") and rows[2]["solucion"] == PEND and upd == [new[0]]
        assert blockscan(now=local("2026-10-08T00:00:00Z").timestamp()) == ([], []) and len(blog_rows()) == 5  # re-run
        # a later success in another chat solves a pending row; a block < GAP old waits unless blocklog> closes it
        now = datetime.now().timestamp()
        recent = datetime.fromtimestamp(now - 300).astimezone().isoformat()
        put(os.path.join(PROJECTS, "p", "c3.jsonl"), [use("r", "rm -r y"), ok("r", recent), use("q", "curl x"), res("q", recent, den)])
        new, upd = blockscan(now=now)
        assert new == [] and [r["ids"] for r in upd] == ["b"] and upd[0]["solucion"].startswith("funcionó después en el chat c3")
        import contextlib, io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                block_main({"session_id": "c3"}, " regla puesta ")
        except SystemExit:
            pass
        rows = blog_rows()
        assert "1 incidente(s) nuevo(s)" in buf.getvalue() and rows[-1]["ids"] == "q" and rows[-1]["solucion"] == "regla puesta"
        assert blockscan(now=now + 3600) == ([], [])
        # allow>: this chat's denials (subagents too, outages not), newest first -> clipboard
        assert ATRIGGER.match("Allow 2 >")[1] == "2" and ATRIGGER.match("allow> 2")[2] == " 2" and not ATRIGGER.match("allowance> x")
        assert VTRIGGER.match(" Vault > ") and not VTRIGGER.match("vault> add x") and LTRIGGER.match("login> ana")[1].strip() == "ana"
        got = []
        for p, _, _ in transcripts("c1"):  # compact JSON like real transcripts (blocks() prefilters on '"is_error":true')
            recs = [json.loads(x) for x in open(p, encoding="utf-8")]
            open(p, "w", encoding="utf-8").writelines(json.dumps(d, separators=(",", ":")) + "\n" for d in recs)

        def allow_run(sid, n, extra=""):
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    allow_main({"session_id": sid}, n, extra, copy=lambda t: got.append(t) or True)
            except SystemExit:
                pass
            return json.loads(buf.getvalue())["reason"]
        r = allow_run("c1", "")
        assert "Copiado" in r and r.endswith(got[-1]) and "→ 1." in r and " 3." in r and " 4." not in r, r
        assert got[-1].startswith("Autorizo explícitamente") and "PowerShell: reg add — solo esa acción" in got[-1]
        assert "[Auto-Mode Bypass]" in got[-1]
        allow_run("c1", "3")
        assert "PowerShell: python x.py" in got[-1] and len(got) == 2
        assert "allow 3>" in allow_run("c1", "", " 3") and "solo tiene 3" in allow_run("c1", "9")
        assert "no hay denegaciones" in allow_run("zz", "") and "no hay denegaciones" in allow_run("", "") and len(got) == 2
        # parallel chats: keyword, detection (same account only, spent after my first prompt), $-based estimate
        assert par_flag("par 4 5 x") == (True, False, "4 5 x") and par_flag("Solo$? 4") == (True, True, "4")
        assert par_flag("4 5 par") == (False, False, "4 5 par") and par_flag("nousage") == (True, False, "")
        STATE = tempfile.mkdtemp()
        wk = lambda r: {"last": {"7d": {"resets_at": r}}}
        me = dict(wk(1000), start={"t": 100})
        for name, d in (("busy", dict(wk(1000), active=200)), ("before", dict(wk(1000), active=50)),
                        ("otra_cuenta", dict(wk(1000 + 6 * 3600), active=200)), ("_last_limits", {"active": 200})):
            json.dump(d, open(os.path.join(STATE, name + ".json"), "w"))
        json.dump(dict(me, active=200), open(os.path.join(STATE, "me.json"), "w"))
        assert others("me", me) == 1
        # only spends between my first prompt (100) and my last answer (300) count
        me["end"] = {"t": 300}
        for name, sp in (("busy", [[400, 450]]), ("before", [[50, 90], [500, 600]]), ("during", [[90, 150], [700, 800]])):
            json.dump(dict(wk(1000), spans=sp), open(os.path.join(STATE, name + ".json"), "w"))
        assert others("me", me) == 1  # only "during"
        assert limits_from({"start": {}, "end": {"cost": 1}, "last": {"cost": 2}})["cost"] == 1
        LOG_CSV = os.path.join(STATE, "c.csv")
        with open(LOG_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["cost_usd", "h5_start", "h5_end", "h5_reset", "parallel"])
            w.writerows([[1, 0, 2, "False", ""]] * 4 + [[2, 0, 6, "False", ""], [1, 0, 9, "True", ""],
                                                        [1, 0, 9, "", "True"], [0.1, 0, 5, "", ""]])
        assert pct_per_usd() == 2 and par_estimate({"cost": 2.5}) == (5, 2)
        ctx = {"date": "d", "sid": "s", "project": "p", "u": {"cost": 2.5, "parallel": True, "others": 1, "5h": (10, 30)},
               "st": {"title": "t", "model_effort": "m", "prompts": 3, "minutes": 9}}
        line, row = build(ctx, {"ses": "4", "pdf": "—"})
        assert row[CSV_COLS.index("parallel")] is True and row[CSV_COLS.index("usage_manual")].startswith("≈5% 5h")
        assert "1 chat(s) en paralelo" in line and par_fields(ctx["u"])[0][2] == "5"
        # whole hook, home in a temp dir (no real state touched): allow> is answered by main(), never passed to Claude
        env = dict(os.environ, USERPROFILE=tmp, HOME=tmp)
        out = subprocess.run([sys.executable, os.path.abspath(__file__)], env=env, capture_output=True, text=True,
                             input=json.dumps({"prompt": "allow>", "session_id": "t15"})).stdout
        assert '"decision": "block"' in out and "allow>" in out, out
        print("ok")
    elif sys.argv[1:2] == ["--form"]:
        form_later(sys.argv[2])
    elif sys.argv[1:2] == ["--blockscan"]:  # `--blockscan --dry`: count what would be logged, write nothing
        sys.stdout.reconfigure(encoding="utf-8")
        if sys.argv[2:] == ["--dry"]:
            rs = blog_rows()
            n, u = scan(rs, transcripts())
            print(f"{len(n)} new, {len(u)} solved", *(f"{r['date']} {r['time']} {r['session_id'][:8]} {r['tipo']} | "
                                                        f"{r['bloqueado'][:70]} | {r['solucion'][:50]}" for r in n + u), sep="\n")
        else:
            print("{} new, {} solved".format(*map(len, blockscan())))
    elif sys.argv[1:] == ["--mark"]:
        import shutil
        shutil.copy(os.path.join(STATE, "_last_limits.json"), MARK)
    elif sys.argv[1:2] == ["--leftover"]:
        leftover(sys.argv[2:])
    else:
        main()
