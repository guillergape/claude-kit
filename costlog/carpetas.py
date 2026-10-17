r"""Folder mode `_<carpeta>:` (the leading "_" is the marker; without it nothing happens) for every project, resolved
in the UserPromptSubmit hook (costlog.py calls hook()), so the model only sees the message once the folder is unique
(0 tokens for lists, not-found and the y/n steps).
Rules: case, accents and extra spaces don't matter; "_" = one folder level down (prog_practicas = Practicas inside
Prog) and levels in between may be skipped (prog_p2 = any P2 inside Prog); each level may be the start of its name
(prac -> Practicas); a name with "_" inside (00_Guia docente) can be typed with its "_"; if some folder has exactly
that name only those count. Folders starting with "_" or "." are skipped. Aliases: "| `alias:` | `ruta/` |" rows in a
root's CLAUDE.md. `_<root>_<folder>:` searches that place directly (root = any name in carpetas.json).
Where it looks (carpetas.json next to this file, see carpetas.example.json): the current project -> "step1" roots ->
(y) "step2" roots -> (y) every drive, in a window. CLI: python carpetas.py "<text>" [root path]; --test = self-check.
`<carpeta> qq >` (also quickq / quickquestion) = the same search for a one-message quick question: same lists, but it
doesn't start folder mode and, if not found in the current project or step1, the prompt goes through as a plain qq.
"""
import json, os, re, sys, threading, time, unicodedata
from itertools import combinations
try:
    from textos import T  # texts in the person's language (textos.json next to this file); Spanish without it
except ImportError:
    T = lambda s, **k: s.format(**k) if k else s

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cfg(path=os.path.join(HERE, "carpetas.json")):
    """-> (projects deepest first, step1, step2) as [(name, path)]. No carpetas.json: only the current folder +
    Downloads, then Documents / Desktop."""
    try:
        c = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        c = {"step1": [[T("Descargas"), "~/Downloads"]],
             "step2": [[T("Documentos"), "~/Documents"], [T("Escritorio"), "~/Desktop"]]}
    rows = lambda k: [(n, os.path.normpath(os.path.expanduser(p))) for n, p in c.get(k, [])]
    return sorted(rows("projects"), key=lambda r: -len(r[1])), rows("step1"), rows("step2")


PROJECTS, STEP1, STEP2 = load_cfg()
NAMED = PROJECTS + STEP1 + STEP2
STATE = os.path.expanduser("~/.claude/costlog-state")
PREFIX = re.compile(r"^_([^\\/:\n?¿!¡,;\"'<>`|*]{1,80}):(?![\\/])")
QQ = re.compile(r"^_?([^\\/:\n?¿!¡,;\"'<>`|*]{1,80}?)\s+(?:qq|quickq|quickquestion)\s*>", re.I)
DRIVES = getattr(os, "listdrives", lambda: [os.path.expanduser("~")])  # Mac/Linux: home, not / (/proc, /sys…)
SKIP_EVERYWHERE = [os.path.expanduser(p) for p in ("~/Library", "~/.Trash")] if os.name != "nt" else []  # Mac: huge + privacy prompts
YES, NO = {"y", "s", "si", "sí", "yes"}, {"n", "no"}


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(s.split())


def walk(root, skip=(), hidden=True):
    skip = {os.path.normcase(s) for s in skip}
    out = []
    for dp, dn, _ in os.walk(root):
        dn[:] = [d for d in dn if (not hidden or not d.startswith(("_", ".")))
                 and os.path.normcase(os.path.join(dp, d)) not in skip]
        rel = os.path.relpath(dp, root)
        if rel != ".":
            out.append((tuple(norm(p) for p in rel.split(os.sep)), rel.replace(os.sep, "/")))
    return sorted(out, key=lambda f: f[1])


def aliases(root):
    try:
        text = open(os.path.join(root, "CLAUDE.md"), encoding="utf-8").read()
    except OSError:
        return {}
    al = {}
    for cell, path in re.findall(r"^\|([^|\n]*:`[^|\n]*)\|\s*`([^`\n]+?)/?`\s*\|", text, re.M):
        if os.path.isdir(os.path.join(root, path)):
            for a in re.findall(r"`([^`]+?):`", cell):
                al[norm(a)] = tuple(norm(p) for p in path.split("/"))
    return al


def expand(typed, al):
    """-> (typed with the alias replaced by its real path, that path: the alias pins it from the root)."""
    for a in sorted(al, key=len, reverse=True):
        real = "_".join(al[a])
        if typed == real or typed.startswith(real + "_"):  # already the real name (cartas_recomendacion)
            return typed, ()
        if typed == a or typed.startswith(a + "_"):
            return real + typed[len(a):], al[a]
    return typed, ()


def fits(comps, levels, eq=False, tail=True, gaps=True):
    # the last typed level is the folder itself; earlier ones are ancestors in order, gaps allowed;
    # a run of levels joined by "_" may fill one name, e.g. "00_syllabus & schedule"
    if not levels:
        return True
    if not comps:
        return False
    for j in range(1, len(levels) + 1):
        run = "_".join(levels[-j:])
        if (comps[-1] == run if eq else comps[-1].startswith(run)) and fits(comps[:-1], levels[:-j], eq, False, gaps):
            return True
    return gaps and not tail and fits(comps[:-1], levels, eq, False)


def resolve(allf, typed, al={}):
    typed, pin = expand(typed, al)
    levels = typed.split("_")
    if not all(levels):
        return []
    found = [f for f in allf if f[0][:len(pin)] == pin and fits(f[0], levels)]
    found = [f for f in found if fits(f[0], levels, eq=True)] or found  # exact names beat starts
    return [f for f in found if fits(f[0], levels, gaps=False)] or found  # no skipped levels beats skipped


def prompt(allf, comps, al={}):
    # shortest "<distinctive ancestors>_<name>" (or alias) that picks this folder alone
    for k in range(len(comps)):
        ps = ["_".join(a + comps[-1:]) for a in combinations(comps[:-1], k)] + (list(al) if k == 0 else [])
        ps = [p for p in ps if [f[0] for f in resolve(allf, p, al)] == [comps]]
        if ps:
            return min(ps, key=len)
    return "_".join(comps)


def current(cwd):
    c = os.path.normcase(os.path.abspath(cwd))
    for name, path in PROJECTS:
        p = os.path.normcase(path)
        if c == p or c.startswith(p + os.sep):
            return name, path
    return os.path.basename(cwd.rstrip("\\/")) or cwd, cwd


def switch(typed):
    for name, path in sorted(NAMED, key=lambda r: -len(r[0])):
        n = norm(name)
        if typed == n or typed.startswith(n + "_"):
            return name, path, typed[len(n) + 1:]
    return None


def search(typed, roots, others):
    """[(name, path, allf, al, hits)] for the roots where typed is found; each walk skips the other searched roots."""
    out = []
    for name, path in roots:
        if not os.path.isdir(path):
            continue
        allf, al = walk(path, [p for _, p in others if p != path]), aliases(path)
        hits = resolve(allf, typed, al)
        if hits:
            out.append((name, path, allf, al, hits))
    return out


def listing(raw, what, lines):
    return (T("⚠ Hay varias carpetas {what} ({n}), por eso sale este listado. Copia el prompt de la que quieres:",
              what=what, n=len(lines)) + "\n\n" + "\n".join(lines))


def enter(raw, root, typed, cur, note="", qq=False):
    """One root: unique -> let the message through with the folder; several -> the list (0 tokens)."""
    name, path, allf, al, hits = root
    pre = "" if path == cur else norm(name) + "_"
    if len(hits) > 1:
        exact = any(fits(c, expand(typed, al)[0].split("_"), eq=True) for c, _ in hits)
        what = T("con el nombre «{raw}»", raw=raw) if exact else T("que empiezan por «{raw}»", raw=raw)
        return block((note + "\n\n" if note else "") + listing(raw, what, [
            f"- {tag(pre + prompt(allf, c, al), qq)} → {name}/{rel}" if pre else f"- {tag(prompt(allf, c, al), qq)} → {rel}"
            for c, rel in hits]))
    rel = hits[0][1]
    full = os.path.normpath(os.path.join(path, rel))
    line1 = T("Modo {f}/ — solo aquí. Salir: exit > · cambiar: _<carpeta>:", f=rel or name)
    ctx = (f"📁 Folder mode, resolved by the hook (don't run carpetas.py): «{raw}» = {full}. Follow the folder-mode "
           f"rules of the CLAUDE.md that applies there, if any; if there are none: first line "
           f"`{line1}`, read that folder's CLAUDE.md if "
           f"it has one, no session start, work only there; the mode lasts until `exit >` or another `_<carpeta>:`.")
    if qq:
        ctx = (f"📁 Quick question about a folder, resolved by the hook (don't run carpetas.py): «{raw}» = {full}. "
               f"Follow the `qq >` rules of the CLAUDE.md that applies there (course folder: `<Asig> qq >`); if there "
               f"are none, the global `qq >` rule for this message only, like a btw: it doesn't start folder mode, and "
               f"an active folder mode carries on after it.")
    if note:
        ctx += f" Start the reply with this line: {note}"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}))
    sys.exit(0)


def tag(p, qq):
    return f"`{p} qq >`" if qq else f"`_{p}:`"


def block(text):
    print(json.dumps({"decision": "block", "reason": text}))
    sys.exit(0)


def found(raw, typed, res, cur, where, qq=False):
    if len(res) == 1:
        enter(raw, res[0], typed, cur, T("📁 «{raw}» no está en {where}; está en {r}.", raw=raw, where=where, r=res[0][0]), qq)
    return block(T("📁 «{raw}» no está en {where}. Está en varios sitios; dime cuál con su prompt:", raw=raw, where=where)
                 + "\n\n" + "\n".join(f"- {tag(norm(n) + '_' + typed, qq)} → {n} ("
                                      + (T("{n} carpetas", n=len(h)) if len(h) > 1 else T("1 carpeta")) + ")"
                                      for n, _, _, _, h in res))


def state_path(sid):
    return os.path.join(STATE, f"carpetas-{sid}.json")


def ask(sid, st, text):
    os.makedirs(STATE, exist_ok=True)
    with open(state_path(sid), "w", encoding="utf-8") as f:
        json.dump(dict(st, t=time.time()), f)
    block(text + "\n\n" + T("`y` = sí · `n` = no, paro"))


def answer(sid, st, a):
    os.remove(state_path(sid))
    raw, typed, cur, cname = st["raw"], st["typed"], st["cur"], st["cname"]
    if a in NO:
        block(T("Vale, no busco más. Te espero."))
    if st["stage"] == 1:
        done = [(cname, cur)] + STEP1
        res = search(typed, [r for r in STEP2 if r[1] != cur], done + STEP2)
        if res:
            found(raw, typed, res, cur, T("{a} ni en {b}", a=cname, b=", ".join(n for n, p in STEP1 if p != cur)))
        ask(sid, dict(st, stage=2), T("📁 «{raw}» tampoco está en {where}. ¿Busco en todo el ordenador ({drives})? Tarda "
                                      "unos minutos y el resultado sale en una ventana.", raw=raw,
                                      where=", ".join(n for n, _ in STEP2) or T("los sitios configurados"),
                                      drives=", ".join(DRIVES())))
    import subprocess
    kw = (dict(creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt"
          else dict(start_new_session=True))
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "--everywhere", raw], **kw,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    block(T("🔎 Buscando «{raw}» en todo el ordenador. Saldrá una ventana con el resultado.", raw=raw))


def hook(h):
    """Called from costlog.py for every ordinary prompt. Returns only when the prompt isn't folder-mode business."""
    p, sid = h.get("prompt", ""), h.get("session_id") or "x"
    try:
        with open(state_path(sid), encoding="utf-8") as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = None
    if st:
        a = norm(p).strip(" .!")
        if a in YES | NO and time.time() - st["t"] < 3600:
            answer(sid, st, a)
        os.remove(state_path(sid))
    m = PREFIX.match(p)
    qq = not m and QQ.match(p)
    m = m or qq
    if not m or not norm(m[1]):
        return
    raw, typed = m[1].strip(), norm(m[1])
    cname, cur = current(h.get("cwd") or os.getcwd())
    sw = switch(typed)
    if sw and os.path.isdir(sw[1]):
        name, path, rest = sw
        if not rest:
            enter(raw, (name, path, [], {}, [((), "")]), typed, cur, qq=qq)
        res = search(rest, [(name, path)], STEP1 + STEP2)  # same skips as the automatic search
        if res:
            enter(raw, res[0], rest, cur, qq=qq)
        block(T("📁 «{raw}» no está en {where}.", raw=rest, where=name))
    first = [(cname, cur)] + [r for r in STEP1 if r[1] != cur]
    res = search(typed, first[:1], first)
    if res:
        enter(raw, res[0], typed, cur, qq=qq)
    res = search(typed, first[1:], first)
    if res:
        found(raw, typed, res, cur, cname, qq)
    if qq:
        return  # "<whatever> qq >" that isn't a folder nearby: plain qq, no y/n search outside
    where2 = f" ({', '.join(n for n, _ in STEP2)})" if STEP2 else ""
    ask(sid, {"stage": 1, "raw": raw, "typed": typed, "cur": cur, "cname": cname},
        T("📁 Carpeta «{raw}» no encontrada en {a} ni en {b}. ¿Busco fuera{c}?", raw=raw, a=cname,
          b=", ".join(n for n, _ in first[1:]), c=where2))


def everywhere(raw):
    """Detached window: every folder on every drive (hidden and `_` ones too)."""
    import tkinter as tk
    typed = norm(raw)
    win = tk.Tk()
    win.title(T("Buscar carpeta «{raw}» en todo el ordenador", raw=raw))
    txt = tk.Text(win, width=110, height=30, font=("Consolas", 10))
    txt.pack(fill="both", expand=True)
    txt.insert("end", T("Buscando «{raw}» en {drives}…", raw=raw, drives=", ".join(DRIVES())) + "\n")
    out = []

    def work():
        allf = []
        for d in DRIVES():
            allf += [((norm(d.rstrip("\\/")),) + c, os.path.join(d, rel)) for c, rel in walk(d, SKIP_EVERYWHERE, hidden=False)]
        out.append(resolve(allf, typed))

    threading.Thread(target=work, daemon=True).start()

    def poll():
        if not out:
            return win.after(500, poll)
        hits = out[0]
        txt.insert("end", (T("Encontrada en {n} sitio(s):", n=len(hits)) + "\n\n" if hits else T("No está en ningún sitio.") + "\n")
                   + "\n".join(rel.replace("/", os.sep) for _, rel in hits[:500]))

    poll()
    win.attributes("-topmost", True)
    win.after(1500, lambda: win.attributes("-topmost", False))
    win.mainloop()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:2] == ["--everywhere"]:
        everywhere(sys.argv[2])
    elif sys.argv[1:] == ["--test"]:
        import tempfile
        tmp = tempfile.mkdtemp()
        for d in ("Prog/Practicas/P1 Punteros", "Prog/Practicas/P2 Listas", "Prog/Teoria/T2", "Calculo/Teoria/T2",
                  "Calculo/00_Guia docente", "Fisica/Labs", "Prog/_privado/Labs", "empresas/acme_corp"):
            os.makedirs(os.path.join(tmp, *d.split("/")))
        allf = walk(tmp)
        assert all([f[1] for f in resolve(allf, prompt(allf, c))] == [rel] for c, rel in allf)
        assert [f[1] for f in resolve(allf, "prog_prac_p1")] == ["Prog/Practicas/P1 Punteros"]
        assert [f[1] for f in resolve(allf, "p2 listas")] == ["Prog/Practicas/P2 Listas"]
        assert len(resolve(allf, "t2")) == 2 and [f[1] for f in resolve(allf, "calculo_t2")] == ["Calculo/Teoria/T2"]
        assert [f[1] for f in resolve(allf, "labs")] == ["Fisica/Labs"]  # "_privado" is skipped
        assert [f[1] for f in resolve(allf, "00_guia docente")] == ["Calculo/00_Guia docente"] and not resolve(allf, "ojo")
        with open(os.path.join(tmp, "CLAUDE.md"), "w", encoding="utf-8") as f:
            f.write("| `acme:` `empresa:` | `empresas/acme_corp/` |\n")
        al = aliases(tmp)
        assert al["acme"] == ("empresas", "acme_corp") and [f[1] for f in resolve(allf, "empresa", al)] == ["empresas/acme_corp"]
        assert all([f[1] for f in resolve(allf, prompt(allf, c, al), al)] == [rel] for c, rel in allf)
        assert PREFIX.match("_p1 punteros: hola")[1] == "p1 punteros" and not PREFIX.match("p1 punteros: hola") \
            and not PREFIX.match("mira esto: x") and not PREFIX.match("_http://x") and not PREFIX.match("_qq > a: b")
        assert QQ.match("Prog qq > hola")[1] == "Prog" and QQ.match("_prog_prac QuickQ> x")[1] == "prog_prac" \
            and QQ.match("p1 punteros quickquestion > x")[1] == "p1 punteros" and not QQ.match("qq > hola") \
            and not PREFIX.match("_prog qq > x: y") and tag("prog", True) == "`prog qq >`"
        cfg = os.path.join(tmp, "c.json")
        with open(cfg, "w", encoding="utf-8") as f:
            json.dump({"projects": [["Uni", tmp], ["Prog", os.path.join(tmp, "Prog")]], "step1": [["Descargas", "~/Downloads"]]}, f)
        pr, s1, s2 = load_cfg(cfg)
        assert [n for n, _ in pr] == ["Prog", "Uni"] and s1[0][1] == os.path.normpath(os.path.expanduser("~/Downloads")) and s2 == []
        PROJECTS, NAMED = pr, pr + s1
        assert switch("uni_prog")[2] == "prog" and switch("prog")[2] == "" and not switch("progr")
        assert current(os.path.join(tmp, "Prog", "Teoria"))[0] == "Prog" and current(os.path.join(tmp, "Fisica"))[0] == "Uni"
        assert load_cfg(os.path.join(tmp, "missing.json"))[0] == []  # no config: still works
        print("ok", len(allf), sorted(al))
    elif sys.argv[1:]:
        root = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
        allf, al = walk(root), aliases(root)
        for c, rel in resolve(allf, norm(sys.argv[1]), al):
            print(f"`_{prompt(allf, c, al)}:` → {rel}")
