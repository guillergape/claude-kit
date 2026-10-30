"""Password / token vault for Claude: scripts use secrets without anyone printing them.

Secrets live in the system's credential store through `keyring` (Windows Credential Manager, macOS Keychain,
Linux Secret Service), service `claude-vault`: never in a file, Drive or git. No command prints a password: Claude
only sees names, usernames and URLs.

  vault.py add <name> [--user U] [--url URL]   window for the person to type the password (masked)
  vault.py new <name> --user U [--url URL]     generate a strong password, store it, copy it (sign-ups)
  vault.py copy <name>                         password -> clipboard, cleared after 30 s (Windows: kept out of Win+V history)
  vault.py user <name>                         print the username (not secret)
  vault.py list                                names, users, URLs
  vault.py rm <name>
  vault.py open                                window for the person: see entries, show/copy/delete passwords
  vault.py --test                              self-check with a throw-away entry (stores and deletes it)

From Python scripts: `from vault import get; tok = get("my-api")` (never print or log it).
Needs: `pip install keyring` (and tkinter for the windows). Tested on Windows; Mac/Linux untested.
"""
import json, os, secrets, string, subprocess, sys, time
import keyring

SVC = "claude-vault"
INDEX = "__index__"  # json {name: {"user":..., "url":...}}; passwords stored separately
CLEAR_AFTER = 30


def _index():
    return json.loads(keyring.get_password(SVC, INDEX) or "{}")


def _save_index(ix):
    keyring.set_password(SVC, INDEX, json.dumps(ix))


def get(name):
    pw = keyring.get_password(SVC, name)
    if pw is None:
        raise KeyError(f"no secret '{name}' (vault.py list)")
    return pw


def _store(name, pw, user, url):
    keyring.set_password(SVC, name, pw)
    ix = _index()
    ix[name] = {"user": user or ix.get(name, {}).get("user", ""), "url": url or ix.get(name, {}).get("url", "")}
    _save_index(ix)


# --- clipboard. Windows: ctypes, so the copy can be kept out of clipboard history / cloud sync.
#     Mac: pbcopy/pbpaste. Linux: wl-copy/wl-paste or xclip (untested). ---
if os.name == "nt":
    import ctypes, ctypes.wintypes as w
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    u32.GetClipboardData.restype = k32.GlobalLock.restype = k32.GlobalAlloc.restype = w.HANDLE
    k32.GlobalLock.argtypes = k32.GlobalUnlock.argtypes = [w.HANDLE]
    u32.SetClipboardData.argtypes = [w.UINT, w.HANDLE]
    CF_UNICODETEXT = 13

    def _open():
        for _ in range(20):
            if u32.OpenClipboard(None):
                return
            time.sleep(0.05)
        raise RuntimeError("clipboard busy")

    def _set_clip(text):
        data = text.encode("utf-16-le") + b"\0\0"
        _open()
        try:
            u32.EmptyClipboard()
            h = k32.GlobalAlloc(0x2, len(data))  # GMEM_MOVEABLE
            ctypes.memmove(k32.GlobalLock(h), data, len(data))
            k32.GlobalUnlock(h)
            u32.SetClipboardData(CF_UNICODETEXT, h)
            # Win+V history and cloud clipboard skip content carrying these formats
            for fmt in ("ExcludeClipboardContentFromMonitorProcessing", "CanIncludeInClipboardHistory", "CanUploadToCloudClipboard"):
                z = k32.GlobalAlloc(0x2, 4)
                ctypes.memmove(k32.GlobalLock(z), b"\0\0\0\0", 4)
                k32.GlobalUnlock(z)
                u32.SetClipboardData(u32.RegisterClipboardFormatW(fmt), z)
        finally:
            u32.CloseClipboard()

    def _get_clip():
        _open()
        try:
            h = u32.GetClipboardData(CF_UNICODETEXT)
            if not h:
                return None
            s = ctypes.wstring_at(k32.GlobalLock(h))
            k32.GlobalUnlock(h)
            return s
        finally:
            u32.CloseClipboard()
else:
    _COPY = [["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]]
    _PASTE = [["pbpaste"], ["wl-paste", "-n"], ["xclip", "-selection", "clipboard", "-o"]]

    def _run(cmds, data=None):
        for c in cmds:
            try:
                r = subprocess.run(c, input=data, capture_output=True, timeout=5)
                if r.returncode == 0:
                    return r.stdout
            except (OSError, subprocess.SubprocessError):
                pass
        return None

    def _set_clip(text):
        if _run(_COPY, text.encode("utf-8")) is None:
            raise RuntimeError("no clipboard tool (pbcopy / wl-copy / xclip)")

    def _get_clip():
        out = _run(_PASTE)
        return None if out is None else out.decode("utf-8", "replace")


def _copy(name):
    pw = get(name)
    _set_clip(pw)
    # detached clearer: wipes the clipboard only if it still holds this password
    if os.name == "nt":
        kw = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        kw = {"start_new_session": True}
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "_clear", name], close_fds=True, **kw)


def _clear(name):
    time.sleep(CLEAR_AFTER)
    if _get_clip() == get(name):
        _set_clip("")


def _dialog(name, user):
    import tkinter as tk
    root = tk.Tk()
    root.title(f"Vault: {name}")
    root.attributes("-topmost", True)
    out = {}
    tk.Label(root, text=f"Secret '{name}' — Claude will not see it").grid(columnspan=2, padx=10, pady=6)
    tk.Label(root, text="User").grid(row=1, column=0, sticky="e")
    eu = tk.Entry(root, width=34); eu.insert(0, user or ""); eu.grid(row=1, column=1, padx=8)
    tk.Label(root, text="Password").grid(row=2, column=0, sticky="e")
    ep = tk.Entry(root, width=34, show="•"); ep.grid(row=2, column=1, padx=8)
    tk.Label(root, text="Repeat").grid(row=3, column=0, sticky="e")
    ep2 = tk.Entry(root, width=34, show="•"); ep2.grid(row=3, column=1, padx=8)
    msg = tk.Label(root, fg="red"); msg.grid(row=4, columnspan=2)

    def ok(_=None):
        if not ep.get() or ep.get() != ep2.get():
            msg.config(text="Empty or not matching")
            return
        out.update(user=eu.get(), pw=ep.get())
        root.destroy()

    tk.Button(root, text="Save", command=ok).grid(row=5, columnspan=2, pady=8)
    root.bind("<Return>", ok)
    (ep if user else eu).focus_force()
    root.mainloop()
    return out


def _viewer():
    """Window for the person: list entries, show/copy/delete. Nothing is printed to the console."""
    import tkinter as tk
    root = tk.Tk()
    root.title("Vault")
    root.attributes("-topmost", True)

    from tkinter import simpledialog, messagebox

    def ask(what):
        return (simpledialog.askstring("Vault", what, parent=root) or "").strip()

    def add():
        name = ask("Name (e.g. my-api, moodle):")
        if not name:
            return
        r = _dialog(name, "")
        if r:
            _store(name, r["pw"], r["user"], ask("URL (optional):"))
        draw()

    def generate():
        name = ask("Name for the new generated password:")
        if not name:
            return
        if keyring.get_password(SVC, name):
            return messagebox.showerror("Vault", f"'{name}' already exists", parent=root)
        _store(name, _gen(), ask("User / email:"), ask("URL (optional):"))
        _copy(name)
        messagebox.showinfo("Vault", f"Generated '{name}', on the clipboard for {CLEAR_AFTER} s", parent=root)
        draw()

    def draw():
        for c in root.winfo_children():
            c.destroy()
        top = tk.Frame(root); top.grid(row=0, columnspan=7, sticky="w", padx=6, pady=6)
        tk.Button(top, text="Add", command=add).pack(side="left")
        tk.Button(top, text="Generate", command=generate).pack(side="left", padx=4)
        ix = _index()
        if not ix:
            tk.Label(root, text="Vault is empty").grid(row=1, padx=20, pady=20)
        for r, (k, v) in enumerate(sorted(ix.items()), start=1):
            tk.Label(root, text=k, font=("Segoe UI", 9, "bold")).grid(row=r, column=0, sticky="w", padx=6)
            tk.Label(root, text=v["user"]).grid(row=r, column=1, sticky="w", padx=6)
            tk.Label(root, text=v["url"], fg="gray").grid(row=r, column=2, sticky="w", padx=6)
            pw = tk.Entry(root, width=24); pw.insert(0, "••••••••"); pw.config(state="readonly"); pw.grid(row=r, column=3, padx=4)

            def show(e=pw, k=k):
                e.config(state="normal"); e.delete(0, "end"); e.insert(0, get(k)); e.config(state="readonly")

            def rm(k=k):
                if messagebox.askyesno("Vault", f"Delete '{k}'?", parent=root):
                    main(["rm", k]); draw()

            tk.Button(root, text="Show", command=show).grid(row=r, column=4)
            tk.Button(root, text="Copy", command=lambda k=k: _copy(k)).grid(row=r, column=5)
            tk.Button(root, text="Delete", command=rm).grid(row=r, column=6, padx=(0, 6))

    draw()
    root.mainloop()


def _gen(n=20):
    alpha = string.ascii_letters + string.digits + "!#%*+-_=?"
    while True:
        p = "".join(secrets.choice(alpha) for _ in range(n))
        if all(any(c in s for c in p) for s in (string.ascii_lowercase, string.ascii_uppercase, string.digits, "!#%*+-_=?")):
            return p


def _test():
    """Stores, reads and deletes a throw-away entry in a separate service (claude-vault-test): never touches the
    person's entries, their index or the clipboard."""
    global SVC
    SVC, name = SVC + "-test", "__vault_test__"
    p = _gen()
    assert len(p) == 20 and any(c.isdigit() for c in p) and any(c in "!#%*+-_=?" for c in p)
    _store(name, p, "test-user", "")
    try:
        assert get(name) == p and _index()[name]["user"] == "test-user"
    finally:
        keyring.delete_password(SVC, name)
        keyring.delete_password(SVC, INDEX)
    try:
        get(name)
        raise AssertionError("deleted entry still readable")
    except KeyError:
        pass
    print(f"ok vault ({keyring.get_keyring().__class__.__name__})")


def main(a):
    opt = lambda k: a[a.index(k) + 1] if k in a else ""
    cmd, name = a[0], (a[1] if len(a) > 1 else "")
    if cmd == "list":
        for k, v in sorted(_index().items()):
            print(f"{k}\t{v['user']}\t{v['url']}")
    elif cmd == "add":
        r = _dialog(name, opt("--user"))
        if not r:
            sys.exit("cancelled, nothing stored")
        _store(name, r["pw"], r["user"], opt("--url"))
        print(f"stored '{name}' (user {r['user']})")
    elif cmd == "new":
        if keyring.get_password(SVC, name):
            sys.exit(f"'{name}' exists; rm it first if you really mean to replace it")
        _store(name, _gen(), opt("--user"), opt("--url"))
        _copy(name)
        print(f"generated + stored '{name}'; on clipboard for {CLEAR_AFTER} s")
    elif cmd == "copy":
        _copy(name)
        print(f"'{name}' on clipboard for {CLEAR_AFTER} s" + (" (not in Win+V history)" if os.name == "nt" else ""))
    elif cmd == "user":
        print(_index()[name]["user"])
    elif cmd == "rm":
        keyring.delete_password(SVC, name)
        ix = _index(); ix.pop(name, None); _save_index(ix)
        print(f"removed '{name}'")
    elif cmd == "open":
        _viewer()
    elif cmd == "_clear":
        _clear(name)
    elif cmd == "--test":
        _test()
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:] or ["help"])
