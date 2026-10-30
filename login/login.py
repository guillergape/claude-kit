"""`login> <cuenta>`: switch Claude Code's account, 0 tokens.

The hook costlog/costlog.py blocks the prompt and opens this script in its own console window (Windows; on Mac/Linux
the hook gives the command to run in a terminal).
  1. Match <cuenta> to an account of login.json (full email, or just the part before @).
     Exact -> go on. Close (a typo, or @gamil.com…) -> "¿Te referías a X? [y/n]".
     Anything else -> "Has escrito: X" [y/n], then a Gmail-syntax check (gmail.com) or an MX check (other domains).
  2. Already on that account -> say so and stop.
  3. Windows + account in login.json: automatic mode (click.py signs in on an off-screen Edge with its own profile,
     reads claude.ai's sign-in email from that account's Gmail, types the 6-digit code, clicks Authorize). Otherwise
     `claude auth login --claudeai --email X`: you click Authorize in the browser (and the email link if asked).
  4. `claude auth status --json`: right account? Claude subscription (pro/max…)? Says so.
Config: login.json next to this file (copy login.example.json; your accounts and how their Gmail is read).
`login.py --test`: self-check (no login). `login.py --dry-run <cuenta>`: everything except the real login.
`login.py --gmail-auth <email>`: one-time read-only Gmail consent for an account with "gmail": "vault".
"""
import base64, difflib, html, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
GMAIL = "gmail.com"
PAID = {"pro", "max", "team", "enterprise"}
NO_WINDOW = 0x08000000


def config():
    """login.json: {"cuentas": [{"email", "gmail": "send" | "vault" | "no"}], "edge", "perfiles", "oauth_client"}."""
    try:
        with open(os.path.join(HERE, "login.json"), encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError):
        c = {}
    c.setdefault("cuentas", [])
    c.setdefault("edge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    c.setdefault("perfiles", os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "claude-login"))
    return c


CFG = config()
EDGE = CFG["edge"]
LOG = os.path.join(HERE, "login.log")  # click.py's steps, never tokens, links or codes


def accounts():
    return {a["email"].strip().lower(): a for a in CFG["cuentas"] if "@" in a.get("email", "") and "<" not in a["email"]}


def costlog_mod(name):
    sys.path.insert(0, os.path.join(HERE, "..", "costlog"))
    return __import__(name)


def oauth_client():
    """The Google OAuth client (Desktop app) used for --gmail-auth: login.json "oauth_client" (a JSON with client_id /
    client_secret, e.g. one of the google-workspace MCP's credentials files), else the first of those files, else the
    GOOGLE_OAUTH_CLIENT_ID / _SECRET environment variables."""
    paths = [CFG.get("oauth_client") or ""]
    creds = os.path.expanduser("~/.google_workspace_mcp/credentials")
    if os.path.isdir(creds):
        paths += [os.path.join(creds, f) for f in sorted(os.listdir(creds)) if f.endswith(".json")]
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                c = json.load(f)
            if c.get("client_id"):
                return c["client_id"], c.get("client_secret")
        except (OSError, ValueError):
            pass
    return os.environ.get("GOOGLE_OAUTH_CLIENT_ID"), os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")


def gmail_token(email):
    """Access token to read that account's Gmail, or None. "gmail": "send" = send.py's tokens (google-workspace
    MCP); "vault" = the read-only refresh token `--gmail-auth` stored in the vault as gmail-<email>; "no" = None."""
    how = accounts().get(email, {}).get("gmail", "no")
    if how == "send":
        try:
            return costlog_mod("send").token(email)
        except (OSError, ImportError, KeyError, ValueError):
            return None
    if how != "vault":
        return None
    try:
        sys.path.insert(0, os.path.join(HERE, "..", "vault"))
        from vault import get
        rt = get("gmail-" + email)
    except (ImportError, KeyError):
        return None
    cid, sec = oauth_client()
    data = urllib.parse.urlencode({"client_id": cid, "client_secret": sec, "refresh_token": rt,
                                   "grant_type": "refresh_token"}).encode()
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/token", data, timeout=20) as r:
            return json.load(r)["access_token"]
    except (OSError, ValueError, KeyError):
        return None


def gmail_auth(email):
    """One time per account: you allow read-only Gmail in your browser; the refresh token goes to the vault as
    `gmail-<email>` (loopback + PKCE). Never printed."""
    import hashlib, http.server, secrets, threading, webbrowser
    sys.path.insert(0, os.path.join(HERE, "..", "vault"))
    import vault
    send = costlog_mod("send")
    cid, sec = oauth_client()
    if not cid:
        return print("Falta el cliente OAuth de Google: pon \"oauth_client\" en login.json (ver README.md).")
    verifier, state, got = secrets.token_urlsafe(64), secrets.token_urlsafe(16), {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state:
                got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>Listo, ya puedes cerrar esta pestaña.</p>".encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    srv.handle_error = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    redirect = f"http://127.0.0.1:{srv.server_port}/"
    webbrowser.open("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "access_type": "offline",
        "scope": "https://www.googleapis.com/auth/gmail.readonly", "prompt": "consent", "login_hint": email,
        "state": state, "code_challenge_method": "S256",
        "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()}))
    print(f"Navegador abierto: elige {email} y permite leer el correo (solo lectura). Esperando hasta 10 min…")
    end = time.time() + 600
    while "code" not in got and "error" not in got and time.time() < end:
        time.sleep(0.5)
    srv.shutdown()
    if "code" not in got:
        return print(f"No autorizado ({got.get('error') or 'sin respuesta'}).")
    data = urllib.parse.urlencode({"client_id": cid, "client_secret": sec, "code": got["code"],
                                   "code_verifier": verifier, "redirect_uri": redirect,
                                   "grant_type": "authorization_code"}).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data, timeout=20) as r:
        tok = json.load(r)
    seen = send.api(tok["access_token"], "profile")["emailAddress"].lower()
    if seen != email:  # the wrong account picked in Google's chooser
        return print(f"Has autorizado {seen}, no {email}: no guardado. Repite y elige {email}.")
    vault._store("gmail-" + email, tok["refresh_token"], email, "gmail.readonly (login.py)")
    print(f"OK: Gmail de {email} (solo lectura) guardado en el vault como gmail-{email}.")


def mail_link(email, since, log=print, wait=150):
    """The claude.ai magic link sent to <email> after <since> (epoch s), from its Gmail; None if none in <wait> s.
    Never logged or printed."""
    tok = gmail_token(email)
    if not tok:
        log(f"no Gmail token for {email}")
        return None
    send = costlog_mod("send")
    q = urllib.parse.quote("from:mail.anthropic.com newer_than:1h")  # the subject follows the page's language
    end = time.time() + wait
    while time.time() < end:
        for m in send.api(tok, f"messages?maxResults=5&q={q}").get("messages", []):
            d = send.api(tok, f"messages/{m['id']}?format=full")
            if int(d["internalDate"]) / 1000 < since:
                continue
            stack = [d["payload"]]
            while stack:
                p = stack.pop()
                stack += p.get("parts", [])
                if p.get("body", {}).get("data"):
                    txt = base64.urlsafe_b64decode(p["body"]["data"] + "==").decode("utf-8", "replace")
                    hit = re.search(r"https://claude\.ai/magic-link#[^\s\"<>']+", txt)
                    if hit:  # used now: mark it read; a read-only token can't (stays unread)
                        try:
                            send.api(tok, f"messages/{m['id']}/modify", {"removeLabelIds": ["UNREAD"]})
                            log("magic link found in Gmail (marked read)")
                        except OSError:
                            log("magic link found in Gmail (read-only token: left unread)")
                        return html.unescape(hit[0])
        time.sleep(3)
    return None


def resolve(text, known=None):
    """-> (email, kind): kind "exact" (an account of login.json), "typo" (close to one: ask) or "other" (ask)."""
    known = list(accounts()) if known is None else known
    t = text.strip().lower().strip("<>\"' ")
    local, _, domain = t.partition("@")
    local, domain = local.strip(), domain.strip()
    for e in known:
        el, ed = e.split("@")
        if local == el and domain in ("", ed):
            return e, "exact"
    sim = lambda a, b: difflib.SequenceMatcher(None, a, b).ratio()

    def near(e):
        el, ed = e.split("@")
        return sim(local, el) if not domain or sim(domain, ed) >= 0.75 else 0

    best = max(known, key=near, default=None)
    if best and near(best) >= 0.7:
        return best, "typo"
    if domain and domain != GMAIL and sim(domain, GMAIL) >= 0.75:
        domain = GMAIL  # gamil.com, gmial.com… -> shown as gmail.com in "Has escrito", you confirm it
    return f"{local}@{domain or GMAIL}", "other"


def gmail_ok(local):
    """Gmail usernames: 6-30 chars, letters/digits/dots, no dot at the ends, no '..'."""
    return bool(re.fullmatch(r"[a-z0-9.]{6,30}", local)) and not local.startswith(".") \
        and not local.endswith(".") and ".." not in local


def has_mx(domain):
    try:
        out = subprocess.run(["nslookup", "-type=mx", domain], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None  # couldn't check
    return "mail exchanger" in out


def check(email):
    """-> warning text, or "" if nothing wrong. Whether the mailbox itself exists can't be checked here (it would
    need SMTP on port 25, usually blocked on home connections)."""
    local, _, domain = email.rpartition("@")
    if domain in (GMAIL, "googlemail.com"):
        return "" if gmail_ok(local) else "ese nombre no puede ser un Gmail (6-30 letras, números o puntos)."
    mx = has_mx(domain)
    return "" if mx else ("no he podido comprobar el dominio (¿sin red?)." if mx is None
                          else f"el dominio {domain} no recibe correo: esa dirección no existe.")


def status():
    try:
        out = subprocess.run([shutil.which("claude") or "claude", "auth", "status", "--json"],
                             capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
        return json.loads(out)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}


def profile_of(email):
    """Own Edge profile per account: stays signed in to claude.ai, so usually only "Authorize" is needed."""
    return os.path.normpath(os.path.join(CFG["perfiles"], email))


def close_profile_edge(profile, settle=0):
    """Closes only the Edge running on `profile` (the person's own Edge is never touched). `settle` s first: Edge
    writes new cookies to disk only every ~30 s, and killing it sooner loses the sign-in. Then politely, and by force
    only what is left after 15 s. Background mode off for this profile, so a polite close really ends it."""
    time.sleep(settle)
    find = ("$p = Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { $_.CommandLine "
            f"-like '*--user-data-dir=*{profile}*' }}; ")  # Edge's relaunch quotes the path
    subprocess.run(["powershell", "-NoProfile", "-Command", find + "$p | ForEach-Object { (Get-Process -Id "
                    "$_.ProcessId -ErrorAction SilentlyContinue).CloseMainWindow() } | Out-Null; foreach ($i in 1..15) "
                    "{ Start-Sleep 1; " + find + "if (-not $p) { break } }; $p | ForEach-Object { Stop-Process -Id "
                    "$_.ProcessId -Force -ErrorAction SilentlyContinue }"], creationflags=NO_WINDOW, capture_output=True)
    state = os.path.join(profile, "Local State")
    if os.path.exists(state):
        with open(state, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("background_mode", {}).get("enabled") is not False:
            d.setdefault("background_mode", {})["enabled"] = False
            with open(state, "w", encoding="utf-8") as f:
                json.dump(d, f)


def auto_login(email, claude):
    """`claude auth login` with BROWSER = a stub that hands the URL over; click.py does the browser part off-screen
    (sign-in by the email code if needed, then Authorize). If it can't, the same page in a visible window."""
    import tempfile
    tmp = tempfile.mkdtemp()
    url_f, stub = os.path.join(tmp, "url.txt"), os.path.join(tmp, "browser.cmd")
    with open(stub, "w") as f:
        f.write(f'@echo off\necho %* > "{url_f}"\n')
    proc = subprocess.Popen([claude, "auth", "login", "--claudeai", "--email", email], env=dict(os.environ, BROWSER=stub))
    for _ in range(60):
        if os.path.exists(url_f) and os.path.getsize(url_f):
            break
        time.sleep(0.5)
    else:
        return proc.wait()  # no URL: claude prints it itself, the person goes on by hand
    time.sleep(0.3)
    url = open(url_f).read().strip().strip('"').strip()
    prof = profile_of(email)
    print("  Edge oculto: iniciando sesión / Authorize solo (hasta ~3 min)…")
    click = [os.path.join(HERE, "click.py"), url, email, prof, LOG]
    uv = shutil.which("uv")  # uv brings uiautomation (+ keyring) without installing them; else they must be installed
    cmd = ([uv, "run", "--quiet", "--with", "uiautomation", "--with", "keyring", "python", "-I"] if uv else [sys.executable]) + click
    clicker = subprocess.Popen(cmd, creationflags=NO_WINDOW)
    shown = False
    while proc.poll() is None:
        if not shown and clicker.poll() not in (None, 0):
            subprocess.Popen([EDGE, f"--user-data-dir={prof}", "--window-position=100,100", "--window-size=1000,900", url])
            why = "claude.ai dice «demasiados intentos»: espera un rato" if clicker.returncode == 5 else f"detalle: {LOG}"
            print(f"  ⚠ No he podido hacerlo solo ({why}). Termina tú en la ventana de Edge que se ha abierto.")
            shown = True
        time.sleep(0.5)
    if clicker.poll() is None:
        clicker.kill()
    # close that Edge later, politely, once it has saved the claude.ai cookies (~30 s)
    subprocess.Popen([sys.executable, "-I", os.path.abspath(__file__), "--close", prof],
                     creationflags=subprocess.DETACHED_PROCESS | NO_WINDOW)


def yes(question):
    return input(question + " [y/n] ").strip().lower() in ("y", "s", "si", "sí", "yes")


def main(text, dry=False):
    if not text.strip():
        mine = ", ".join(accounts()) or "ninguna en login.json"
        print(f"Uso: login> <cuenta>   (tus cuentas: {mine}; o cualquier email)")
        return
    email, kind = resolve(text)
    if kind == "typo" and not yes(f"Has escrito «{text.strip()}». ¿Te referías a {email}?"):
        return print("Nada hecho.")
    if kind == "other":
        if not yes(f"Has escrito: {email}. ¿Es correcto?"):
            return print("Nada hecho.")
        warn = check(email)
        if warn and not yes(f"⚠ {warn} ¿Seguir igualmente?"):
            return print("Nada hecho.")
        print("(Que el buzón exista y que tenga suscripción Claude solo se sabe al entrar: lo compruebo después.)")
    now = status()
    if now.get("email", "").lower() == email:
        return print(f"Ya estás en {email} ({now.get('subscriptionType') or 'sin suscripción'}). Nada que hacer.")
    print(f"\nCuenta actual: {now.get('email') or '¿?'}  ->  nueva: {email}")
    print("⚠ Cambia la cuenta de TODOS los chats de Claude Code abiertos en este ordenador (comparten credenciales).")
    auto = os.name == "nt" and email in accounts() and os.path.exists(EDGE)
    if not auto:
        print("  En la web: pulsa Authorize; si claude.ai pide el email, mira el correo de esa cuenta y "
              "escribe el código o abre el enlace. Aquí espero.")
    if dry:
        return print(f"[dry-run] ejecutaría: claude auth login --claudeai --email {email}" + (" + click.py" if auto else ""))
    claude = shutil.which("claude") or "claude"
    if auto:
        auto_login(email, claude)
    else:
        subprocess.run([claude, "auth", "login", "--claudeai", "--email", email])
    after = status()
    got, sub = after.get("email", "").lower(), after.get("subscriptionType")
    if got != email:
        print(f"\n✗ No ha cambiado: sigues en {got or '¿?'}. (¿Se canceló, o elegiste otra cuenta en la web?)")
    elif (sub or "").lower() not in PAID:
        print(f"\n⚠ Dentro de {email}, pero sin suscripción Claude ({sub or 'ninguna'}): Claude Code no funcionará "
              "con ella. Vuelve con login> <otra cuenta>.")
    else:
        print(f"\n✅ Ahora en {email} ({sub}). Los chats ya abiertos usan esta cuenta desde su próximo mensaje "
              "(si alguno falla, reinícialo).")


def _test():
    # placeholder addresses only (the kit's privacy check lets these through)
    k = ["usuario@gmail.com", "tucorreo@gmail.com", "nombre@empresa.test"]
    for t, want in [("usuario", ("usuario@gmail.com", "exact")),
                    ("Usuario@gmail.com", ("usuario@gmail.com", "exact")),
                    ("nombre@empresa.test", ("nombre@empresa.test", "exact")),
                    ("nombre", ("nombre@empresa.test", "exact")),
                    ("usuaro", ("usuario@gmail.com", "typo")),
                    ("usuario@gamil.com", ("usuario@gmail.com", "typo")),
                    ("tucorre", ("tucorreo@gmail.com", "typo")),
                    ("nombre@empressa.test", ("nombre@empresa.test", "typo")),
                    ("user@gmail.com", ("user@gmail.com", "other")),
                    ("name@gmial.com", ("name@gmail.com", "other")),
                    ("ejemplo@otra.org", ("ejemplo@otra.org", "other"))]:
        assert resolve(t, k) == want, (t, resolve(t, k), want)
    assert resolve("usuario", []) == ("usuario@gmail.com", "other")
    assert gmail_ok("random.person") and not gmail_ok("pepe") and not gmail_ok("a..bcdef")
    assert check("nombre@nonexistent-domain-zz9q.test") and not check("usuario@gmail.com")
    assert all("<" not in e for e in accounts())  # the example's placeholders never count as accounts
    print("ok")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console in cp1252: "⚠" would crash the print
    a = sys.argv[1:]
    if a == ["--test"]:
        _test()
    elif a[:1] == ["--gmail-auth"] and len(a) == 2:
        gmail_auth(resolve(a[1])[0])
    elif a[:1] == ["--close"]:  # detached, after a login: close that profile's Edge once its cookies are saved
        close_profile_edge(a[1], settle=35)
    elif a[:1] == ["--dry-run"]:
        main(" ".join(a[1:]), dry=True)
    else:
        try:
            main(" ".join(a))
        except (KeyboardInterrupt, EOFError):
            print("\nCancelado.")
        input("\nPulsa Enter para cerrar.")
