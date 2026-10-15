"""`send> [palabras clave]` / `enviar> [...]` / `lo envío yo`: window to review and send Gmail drafts of every account
authorised in the google-workspace MCP (~/.google_workspace_mcp/credentials), with no model tokens. costlog.py's
UserPromptSubmit hook blocks the prompt and opens this window as a detached process.
- Drafts containing all the keywords (to/cc/subject/body/attachment names, accents and case ignored) come first; the
  rest sit in a collapsed "Otros borradores" node (opened when nothing matches). No keywords -> all, newest first.
- Clicking an attachment downloads it to a temp folder and opens it with its default app.
- Enviar (after a yes/no) = Gmail API drafts.send: the draft exactly as saved in Gmail, attachments included. The
  MCP tokens' gmail.compose scope allows it. Testing-mode refresh tokens expire every 7 days: re-authorise through
  any google-workspace call for that account.
CLI for Claude ("envíalo tú"): `--list [kw]` prints account, draft id, to, subject; `--send <email> <draftId>`."""
import base64, html, json, os, re, subprocess, sys, tempfile, unicodedata, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from glob import glob
try:
    from textos import T  # texts in the person's language (textos.json next to this file); Spanish without it
except ImportError:
    T = lambda s, **k: s.format(**k) if k else s

CREDS = os.path.expanduser("~/.google_workspace_mcp/credentials")
API = "https://gmail.googleapis.com/gmail/v1/users/me/"
TRIGGER = re.compile(r"\s*(?:send|enviar)\s*>\s*(.*)$|\s*lo env[ií]o yo[\s.!]*$", re.I | re.S)


def token(email):
    with open(os.path.join(CREDS, email + ".json"), encoding="utf-8") as f:
        c = json.load(f)
    data = urllib.parse.urlencode({
        "client_id": c.get("client_id") or os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
        "client_secret": c.get("client_secret") or os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
        "refresh_token": c["refresh_token"], "grant_type": "refresh_token"}).encode()
    with urllib.request.urlopen(c.get("token_uri") or "https://oauth2.googleapis.com/token", data, timeout=20) as r:
        return json.load(r)["access_token"]


def api(tok, path, body=None):
    req = urllib.request.Request(API + path, None if body is None else json.dumps(body).encode(),
                                 {"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def b64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def untag(s):
    s = re.sub(r"(?i)<br\s*/?>|</(?:div|p|li|tr|h\d)>", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()


def parse(email, tok, d):
    m = d["message"]
    h = {x["name"].lower(): x["value"] for x in m["payload"].get("headers", [])}
    plain, rich, att = [], [], []

    def walk(part):
        b = part.get("body", {})
        if part.get("filename"):
            att.append((part["filename"], b.get("attachmentId"), b.get("data")))
        elif b.get("data") and part.get("mimeType") == "text/plain":
            plain.append(b64(b["data"]).decode("utf-8", "replace"))
        elif b.get("data") and part.get("mimeType") == "text/html":
            rich.append(b64(b["data"]).decode("utf-8", "replace"))
        for q in part.get("parts", []):
            walk(q)

    walk(m["payload"])
    return {"email": email, "tok": tok, "id": d["id"], "msg": m["id"], "to": h.get("to", ""), "cc": h.get("cc", ""),
            "bcc": h.get("bcc", ""), "subject": h.get("subject") or T("(sin asunto)"),
            "date": int(m.get("internalDate", 0)) // 1000, "body": "\n".join(plain) or untag("\n".join(rich)),
            "att": att}


def account_drafts(email):
    tok = token(email)
    ids = [d["id"] for d in api(tok, "drafts?maxResults=50").get("drafts", [])]
    with ThreadPoolExecutor(8) as ex:
        return [parse(email, tok, d) for d in ex.map(lambda i: api(tok, f"drafts/{i}?format=full"), ids)]


def all_drafts():
    """-> (drafts newest first, {email: error}) over every authorised account."""
    emails = [os.path.basename(p)[:-5] for p in glob(os.path.join(CREDS, "*@*.json"))]
    out, errs = [], {}
    with ThreadPoolExecutor(len(emails) or 1) as ex:
        for e, fut in [(e, ex.submit(account_drafts, e)) for e in emails]:
            try:
                out += fut.result()
            except Exception as x:  # one dead token mustn't hide the other accounts
                errs[e] = f"{type(x).__name__}: {x}"
    return sorted(out, key=lambda d: -d["date"]), errs


def norm(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def matches(d, kw):
    hay = norm(" ".join([d["to"], d["cc"], d["subject"], d["body"]] + [a[0] for a in d["att"]]))
    return all(w in hay for w in norm(kw).split())


def open_att(d, a):
    name, att_id, data = a
    if att_id:
        data = api(d["tok"], f"messages/{d['msg']}/attachments/{att_id}")["data"]
    path = os.path.join(tempfile.mkdtemp(prefix="send-"), os.path.basename(name) or "adjunto")
    with open(path, "wb") as f:
        f.write(b64(data))
    if os.name == "nt":
        os.startfile(path)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])


def send(email, draft_id, tok=None):
    return api(tok or token(email), "drafts/send", {"id": draft_id})


def window(kw):
    import tkinter as tk
    from tkinter import messagebox, ttk
    root = tk.Tk()
    root.title(("send> " + kw).strip())
    root.geometry("1000x700")
    pane = ttk.PanedWindow(root, orient="vertical")
    pane.pack(fill="both", expand=True, padx=6, pady=6)
    tree = ttk.Treeview(pane, columns=("acc", "to", "date"), show="tree headings", height=8)
    for c, t, w in (("#0", T("Asunto"), 380), ("acc", T("Cuenta"), 190), ("to", T("Para"), 260), ("date", T("Fecha"), 110)):
        tree.heading(c, text=t, anchor="w")
        tree.column(c, width=w, anchor="w")
    pane.add(tree, weight=1)
    low = ttk.Frame(pane)
    pane.add(low, weight=3)
    text = tk.Text(low, wrap="word", height=14)
    text.pack(fill="both", expand=True)
    atts = ttk.Frame(low)
    atts.pack(fill="x", pady=4)
    bar = ttk.Frame(low)
    bar.pack(fill="x")
    status = tk.StringVar(value=T("Cargando borradores…"))
    ttk.Label(bar, textvariable=status, wraplength=780).pack(side="left", fill="x", expand=True)
    btn = ttk.Button(bar, text=T("Enviar"), state="disabled")
    btn.pack(side="right")
    rows = {}

    def show(_=None):
        d = rows.get((tree.selection() or [""])[0])
        text.delete("1.0", "end")
        for w in atts.winfo_children():
            w.destroy()
        btn["state"] = "normal" if d else "disabled"
        if not d:
            return
        head = [T("De: {x}", x=d["email"]), T("Para: {x}", x=d["to"])] + [f"{k}: {d[k.lower()]}" for k in ("Cc", "Bcc") if d[k.lower()]]
        text.insert("end", "\n".join(head + [T("Asunto: {x}", x=d["subject"]), "", d["body"]]))
        if d["att"]:
            ttk.Label(atts, text=T("Adjuntos (clic = abrir):")).pack(side="left")
        for a in d["att"]:
            ttk.Button(atts, text="📎 " + a[0], command=lambda a=a: guard(lambda: open_att(d, a))).pack(side="left", padx=2)

    def guard(f):
        try:
            f()
        except Exception as x:
            messagebox.showerror("send>", f"{type(x).__name__}: {x}", parent=root)

    def do_send():
        iid = tree.selection()[0]
        d = rows[iid]
        if not messagebox.askyesno("send>", T("¿Enviar «{s}»\na {to}\ndesde {de}?", s=d["subject"], to=d["to"],
                                                de=d["email"]), parent=root):
            return
        try:
            send(d["email"], d["id"], d["tok"])
        except Exception as x:
            return messagebox.showerror("send>", T("No se ha enviado.\n{e}", e=f"{type(x).__name__}: {x}"), parent=root)
        nxt = tree.next(iid) or tree.prev(iid)
        tree.delete(iid)
        rows.pop(iid)
        if nxt in rows:
            tree.selection_set(nxt)
        show()
        status.set(T("✅ Enviado «{s}» a {to}.", s=d["subject"], to=d["to"]))

    def load():
        ds, errs = all_drafts()
        add = lambda parent, d: rows.setdefault(tree.insert(parent, "end", text=d["subject"], values=(
            d["email"], d["to"], datetime.fromtimestamp(d["date"]).strftime("%d/%m %H:%M"))), d)
        if kw:
            hits = [d for d in ds if matches(d, kw)]
            g = tree.insert("", "end", open=True, text=T("Con «{kw}» ({n})", kw=kw, n=len(hits)) if hits
                            else T("⚠ Ningún borrador contiene «{kw}»", kw=kw))
            for d in hits:
                add(g, d)
            rest = [d for d in ds if d not in hits]
            o = tree.insert("", "end", open=not hits, text=T("Otros borradores ({n})", n=len(rest)))
            for d in rest:
                add(o, d)
        else:
            for d in ds:
                add("", d)
        first = next(iter(rows), None)
        if first:
            tree.selection_set(first)
            tree.see(first)
        status.set(T("{n} borrador(es). Se envía la versión guardada en Gmail (cierra el borrador allí si lo estás "
                     "editando).", n=len(ds)) + "".join("\n⚠ " + T("{e}: {x}  (¿token caducado? reautoriza con "
                                                                  "google-workspace)", e=e, x=x) for e, x in errs.items()))

    tree.bind("<<TreeviewSelect>>", show)
    btn["command"] = do_send
    root.after(50, lambda: guard(load))
    root.mainloop()


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--test"]:
        assert TRIGGER.match("send>")[1] == "" and TRIGGER.match("Enviar > acme cv")[1] == "acme cv"
        assert TRIGGER.match("Lo envío yo.") and TRIGGER.match("lo envio yo")[1] is None
        assert not TRIGGER.match("lo envío yo mañana") and not TRIGGER.match("mira el send>")
        d = {"to": "rrhh@acme.example", "cc": "", "subject": "CV y lo que me gustaría hacer", "body": "Hola",
             "att": [("CV Nombre.pdf", "x", None)]}
        assert matches(d, "ACME gustaria") and matches(d, "cv.pdf".replace(".pdf", "")) and not matches(d, "heat")
        assert untag("<div>a&amp;b</div><div><br></div><div>c</div>") == "a&b\n\nc"
        print("ok")
    elif a[:1] == ["--list"]:
        ds, errs = all_drafts()
        for d in ds:
            if not a[1:] or matches(d, " ".join(a[1:])):
                print(d["email"], d["id"], d["to"], "|", d["subject"], "|", ", ".join(x[0] for x in d["att"]))
        for e, x in errs.items():
            print("ERROR", e, x)
    elif a[:1] == ["--send"] and len(a) == 3:
        print("sent", send(a[1], a[2])["id"])
    elif a[:1] == ["--window"]:
        window(" ".join(a[1:]).strip())
    else:
        sys.exit(__doc__)
