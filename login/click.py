"""Clicks through claude.ai's OAuth page in a normal Edge window on this account's own profile, off-screen, with UI
Automation (no mouse, no keyboard). Windows only. Run by login.py (via `uv run --with uiautomation`, or with
`pip install uiautomation`), never by hand, except `--observe` to try it without switching the account.

  click.py <url> <email> <profile> <log> [--observe]

Your data (accounts, how each Gmail is read, Edge path, profile folder) lives in login.json, not here. The only thing
to adapt here is the block «TEXTOS DE CLAUDE.AI» below, if claude.ai shows its sign-in page in another language.

Sign-in page (profile without a claude.ai session): types <email> (never a password: claude.ai has none), clicks
"Continue with email", then opens the magic link login.mail_link() reads from that account's Gmail. Then "Authorize".
--observe = sign in if needed, log the pages, but never click Authorize (the Claude Code account doesn't change).
Exit: 0 = window gone or page says it's done · 4 = couldn't sign in (no link in Gmail…) · 5 = claude.ai says too
many attempts · 2 = stuck.
"""
import ctypes, os, re, subprocess, sys, threading, time
from datetime import datetime
import uiautomation as auto

url, email, profile, logf = sys.argv[1:5]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import login  # mail_link(), close_profile_edge(), EDGE (from login.json)
observe = "--observe" in sys.argv
EDGE = login.EDGE
u = ctypes.windll.user32

# ==== TEXTOS DE CLAUDE.AI (rellenar si tu claude.ai sale en otro idioma) ==========================================
# Names of the buttons / texts of claude.ai's sign-in and authorize pages, as UI Automation reads them (login.log
# lists every page's controls: look there for the exact names). The page follows the browser's language.
AUTH = ("Authorize", "Autorizar")
CONTINUE = ("Continue with email", "Continuar con correo electrónico")
ENTER_CODE = ("Enter verification code", "Ingrese el código de verificación")
VERIFY = r"verif"  # regex: the button after typing the code ("Verify email address" / "Verificar dirección…")
DONE = ("successful", "you can close", "correctamente")  # lower-case pieces of the final "signed in" page
TOO_MANY = ("too many", "demasiados intentos")
HUMAN = ("human", "ser humano")  # Cloudflare's check
# ===================================================================================================================


def log(m):
    with open(logf, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} click: {m}\n")


def idle_s():
    class LII(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    i = LII(ctypes.sizeof(LII), 0)
    u.GetLastInputInfo(ctypes.byref(i))
    return (ctypes.windll.kernel32.GetTickCount() - i.dwTime) / 1000


def owner(h):
    pid = ctypes.c_ulong()
    u.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return pid.value


def refocus(prev):
    for _ in range(30):
        fg = u.GetForegroundWindow()
        if fg == prev or not prev:
            return
        a = u.GetWindowThreadProcessId(fg, None)
        me = ctypes.windll.kernel32.GetCurrentThreadId()
        u.AttachThreadInput(me, a, True); u.BringWindowToTop(prev); u.SetForegroundWindow(prev)
        u.AttachThreadInput(me, a, False)
        time.sleep(0.01)


ours, last_fg, paused = set(), [u.GetForegroundWindow()], [False]


def guard():  # Edge grabs the focus on opening and on each click: hand it back
    while True:
        fg = u.GetForegroundWindow()
        if paused[0]:  # Edge is meant to have it now
            pass
        elif fg and owner(fg) in ours:
            refocus(last_fg[0])
        elif fg:
            last_fg[0] = fg
        time.sleep(0.01)


def gap(secs=0.5):
    end = time.time() + 1800
    while idle_s() < secs and time.time() < end:
        time.sleep(0.05)


def edge_pids():
    out = subprocess.run(["tasklist", "/fi", "imagename eq msedge.exe", "/fo", "csv", "/nh"], capture_output=True, text=True).stdout
    return {int(l.split('","')[1]) for l in out.splitlines() if '","' in l}


def window(new):
    # Edge relaunches itself on a new profile, so the window's pid isn't Popen's: any Edge window of a process that
    # didn't exist before the launch is ours (the user's own Edge windows belong to its older processes; VS Code etc.
    # are Chrome_WidgetWin_1 too, hence msedge only)
    return next((c for c in auto.GetRootControl().GetChildren() if c.ClassName == "Chrome_WidgetWin_1"
                 and c.ProcessId in new and c.Name and not c.Name.startswith("Untitled")), None)


def tabs(w):
    return [c for c, _ in auto.WalkControl(w, maxDepth=25) if c.ControlTypeName == "TabItemControl"]


def page(w):
    docs = [c for c, _ in auto.WalkControl(w, maxDepth=30) if c.ControlTypeName == "DocumentControl"]
    docs = [d for d in docs if d.Name and d.BoundingRectangle.width() > 0]
    if not docs:
        return None, []
    return docs[-1], [c for c, _ in auto.WalkControl(docs[-1], maxDepth=40) if c.Name or c.ControlTypeName == "EditControl"]


login.close_profile_edge(profile)  # a leftover instance would take the URL and ignore the start flags
gap()
threading.Thread(target=guard, daemon=True).start()
w, before = None, edge_pids()
for attempt in (1, 2):
    p = subprocess.Popen([EDGE, f"--user-data-dir={profile}", "--no-first-run", "--force-renderer-accessibility",
                          "--disable-features=CalculateNativeWinOcclusion", "--disable-backgrounding-occluded-windows",
                          "--window-position=-32000,-32000", "--window-size=900,900", "--new-window", url])
    t0 = time.time()
    while not w and time.time() - t0 < 40:
        time.sleep(0.3)
        ours.update(edge_pids() - before)
        w = window(ours)
    if w:
        break
if not w:
    log(f"no Edge window (new Edge pids {sorted(ours)})")
    sys.exit(2)
log(f"window {w.Name[:60]!r}")

end, last, sent, linked, reopened, otp, typed = time.time() + 180, "", 0, 0, False, None, False
focused, shown = 0, None  # focus attempts for Authorize · the user's window while the Cloudflare check is shown
hwnd = w.NativeWindowHandle
while time.time() < end:
    time.sleep(0.5)
    if not u.IsWindow(w.NativeWindowHandle):
        sys.exit(0)
    try:
        doc, els = page(w)
        if not doc:
            continue
        txt = re.sub(r"\b\d{6}\b", "######", " | ".join(f"{c.ControlTypeName[:-7]}:{c.Name[:40]}"
                     + ("" if c.ControlTypeName != "ButtonControl" or c.IsEnabled else " (off)") for c in els))[:1500]  # never log the code
        if txt != last:
            log(f"page {doc.Name[:50]!r}: {txt}")
            last = txt
        names = {c.Name for c in els}
        if any(x in n.lower() for n in names for x in DONE):
            log("done")
            sys.exit(0)
        btn = lambda *ns: next((c for c in els if c.ControlTypeName == "ButtonControl" and c.Name in ns and c.IsEnabled), None)
        edit = next((c for c in els if c.ControlTypeName == "EditControl"), None)
        auth = btn(*AUTH)
        off = next((c for c in els if c.ControlTypeName == "ButtonControl" and c.Name in AUTH), None)
        if off and not auth and focused < 3:
            # claude.ai keeps Authorize disabled while its page has no focus (29 Oct), and guard() hands the focus
            # back to the user: give it to this (off-screen) Edge for a moment, once the user isn't typing
            focused += 1
            gap()
            prev, paused[0] = last_fg[0], True
            refocus(hwnd)
            got = u.GetForegroundWindow() == hwnd
            t1, state = time.time(), "still disabled"
            while time.time() - t1 < 6:  # the button also waits ~2 s after the page loads
                time.sleep(0.2)
                # found again each time (the page redraws it) and clicked at once: it doesn't stay enabled for long
                off = next((c for c in page(w)[1] if c.ControlTypeName == "ButtonControl" and c.Name in AUTH), off)
                if off.IsEnabled:
                    if not observe:
                        off.GetInvokePattern().Invoke()
                    state = "enabled (observe)" if observe else "clicked"
                    break
            paused[0] = False
            refocus(prev)
            log(f"gave Edge the focus: Authorize {state}"
                + ("" if got else " (Edge didn't get the focus)"))
            time.sleep(1.5)
            continue
        if auth and not observe:
            gap()
            auth.GetInvokePattern().Invoke()
            log("clicked 'Authorize'")
            time.sleep(1.5)
            continue
        if "Checking your Browser" in doc.Name or any(x in n.lower() for n in names for x in HUMAN):
            # Cloudflare's "are you human" check. "Verificando..." often passes alone: only a real checkbox is shown to
            # the person, who ticks it (never the script); then on we go
            if not shown and any(c.ControlTypeName == "CheckBoxControl" for c in els):
                shown, paused[0] = last_fg[0], True
                sw, sh = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
                size = min(900, sh - 80)
                u.ShowWindow(hwnd, 9)  # SW_RESTORE
                u.SetWindowPos(hwnd, 0, (sw - size) // 2, (sh - size) // 2, size, size, 0x40)  # SWP_SHOWWINDOW
                refocus(hwnd)
                end = max(end, time.time() + 300)
                log("Cloudflare check: window shown in front for the person to tick it")
            continue
        if shown:  # check passed: off-screen again, focus back
            u.SetWindowPos(hwnd, 0, -32000, -32000, 900, 900, 0x10)  # SWP_NOACTIVATE
            paused[0] = False
            refocus(shown)
            shown = None
            log("Cloudflare check passed: hidden again")
        if any(x in n.lower() for n in names for x in TOO_MANY):
            log("claude.ai: too many sign-in attempts, try again later")
            sys.exit(5)
        cont = btn(*CONTINUE)
        if edit and cont:  # sign-in page: the email (never a password), then "Continue with email"
            if sent:  # ONE email per run, never more: on 29 Oct a loop sent ~10 and claude.ai said "too many attempts"
                log("still the sign-in page after the magic link: giving up (no second email)")
                sys.exit(4)
            gap()
            if edit.GetValuePattern().Value.strip().lower() != email:
                edit.GetValuePattern().SetValue(email)
            time.sleep(0.5)
            sent = time.time()
            # remember this tab: the profile may also restore an old sign-in tab (29 Oct), and the code goes here
            home = next((i for i, t in enumerate(tabs(w)) if t.GetSelectionItemPattern().IsSelected), 0)
            cont.GetInvokePattern().Invoke()
            log("typed the email, clicked 'Continue with email'")
            time.sleep(2)
            continue
        # the "check your email" page shows the address; its buttons vary (Reenviar email / Try sending again…)
        waiting = email in {n.strip().lower() for n in names}
        if sent and not linked and waiting:  # open the magic link from that account's Gmail, same profile
            link = login.mail_link(email, sent - 5, log)
            if not link:
                log("no link in Gmail")
                sys.exit(4)
            gap()
            subprocess.Popen([EDGE, f"--user-data-dir={profile}", link])
            linked = time.time()
            log("opened the magic link")
            continue
        # the link opens as "another browser" (29 Oct): its page only shows a 6-digit code to type in the first tab
        # ("sign in here instead" just restarts the sign-in, tested)
        code = next((c.Name for c in els if c.ControlTypeName == "TextControl" and re.fullmatch(r"\d{6}", c.Name)), None)
        if linked and code and not otp:
            otp = code
            ts = tabs(w)  # the link opened in a new tab at the end, so the sign-in tab's index still holds
            tab = ts[home] if home < len(ts) else None
            if not tab:
                log("code page but no tab strip")
                sys.exit(4)
            gap()
            tab.GetSelectionItemPattern().Select()
            log("got the code, back to the first tab")
            time.sleep(1)
            continue
        enter = btn(*ENTER_CODE)
        if otp and enter and not typed:
            gap()
            enter.GetInvokePattern().Invoke()
            log("clicked 'Enter verification code'")
            time.sleep(1)
            continue
        if otp and edit and not cont and not typed:
            gap()
            edit.GetValuePattern().SetValue(otp)
            typed, linked = True, time.time()  # restarts the wait before reopening the authorize page
            time.sleep(0.5)
            ok = next((c for c in page(w)[1] if c.ControlTypeName == "ButtonControl" and c.IsEnabled
                       and re.match(VERIFY, c.Name, re.I)), None)
            if ok:
                ok.GetInvokePattern().Invoke()
            log(f"typed the code, clicked {ok.Name if ok else 'nothing'!r}")
            time.sleep(2)
            continue
        if linked and not reopened and time.time() - linked > 25:  # signed in by now: back to the authorize page, once
            gap()
            subprocess.Popen([EDGE, f"--user-data-dir={profile}", url])
            reopened = True
            log("reopened the authorize page")
            continue
    except Exception as e:
        if not u.IsWindow(w.NativeWindowHandle):
            sys.exit(0)
        log(f"retry ({e.__class__.__name__})")
log("stuck" if not observe else "observed")
sys.exit(2 if not observe else 0)
