"""Re-signs the "Claude in Chrome" extension (Windows + Microsoft Edge) when it got logged out, so a chat can use it.

  uv run --quiet --with uiautomation python -I chrome_relogin.py [--dump] [--dry-run] [--loop SECS]

How: opens the extension's own page (chrome-extension://<id>/sidepanel.html) in a NEW Edge window of the user's
profile, moved off-screen at once, with a focus guard (see "focus" below) so the person never loses theirs (its login gate wraps the whole page, so it shows "Log in" when the session expired), finds the button BY
TEXT (EN/ES/FR/DE/IT/PT, never by position or pixel), invokes it through UI Automation (no mouse, no screenshots),
handles claude.ai's "Authorize" page if it appears, waits until the button is gone, closes the tab it opened (through
the tab's own close button, never Ctrl+W) and gives the focus back. Already signed in: does nothing (exit 0).
--dump: print what UIA sees on that page, click nothing. --dry-run: detect only. --loop N: repeat every N seconds.
Exit: 0 = signed in (or already was) · 2 = couldn't (see chrome_relogin.log) · 3 = needs the person (captcha / code).
Never authorises a page that shows an email other than the configured one (chrome_relogin.json). Never types anything, never clicks anything but the sign-in / authorize buttons. Why it works like this: README.md.
"""
import ctypes, ctypes.wintypes, json, os, re, subprocess, sys, threading, time, traceback
from datetime import datetime
import uiautomation as auto

EXT = "fcoeoabgfenejglbffodgkkbkcdhcgfn"  # Claude extension id (Chrome Web Store)
HERE = os.path.dirname(os.path.abspath(__file__))
try:  # optional chrome_relogin.json next to this file: {"profile": "Profile 1", "email": "you@example.com"}
    CFG = json.load(open(os.path.join(HERE, "chrome_relogin.json"), encoding="utf-8"))
except Exception:
    CFG = {}


def detect_profile():
    """The Edge profile folder that has the Claude extension installed (the config file wins if it names one)."""
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "User Data")
    try:
        found = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d, "Extensions", EXT)))
    except OSError:
        found = []
    return found[0] if found else "Default"


PROFILE = CFG.get("profile") or detect_profile()  # Edge profile where the extension is installed
EXPECT = (CFG.get("email") or "").strip().lower()  # the Claude account of the extension; "" = don't check the account
TITLE = "Claude for Chrome"                # <title> of sidepanel.html
EDGE = next((p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe") if os.path.exists(p)), "msedge.exe")
PAGE = f"chrome-extension://{EXT}/sidepanel.html"
LOG = os.path.join(HERE, "chrome_relogin.log")
LOGIN = re.compile(r"^(log ?in|sign ?in|iniciar sesi[oó]n|inicia sesi[oó]n|se connecter|connexion|anmelden|einloggen|"
                   r"accedi|entrar|fazer login|login)\b", re.I)
AUTH = re.compile(r"^(authorize|allow|autorizar|permitir|autoriser|autorisieren|autorizza|approve|aprobar)\b", re.I)
CLOSE = re.compile(r"close|cerrar|fermer|schlie|chiudi|fechar", re.I)  # the tab also has "Mute tab"…
HUMAN = re.compile(r"verify you are human|ser humano|are you human|captcha|verification code|c[oó]digo de verificaci", re.I)
u = ctypes.windll.user32
dump, dry = "--dump" in sys.argv, "--dry-run" in sys.argv


def log(m):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {m}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def edge_windows():
    out = []
    for h in edge_hwnds():
        try:
            out.append(auto.ControlFromHandle(h))
        except Exception:
            pass
    return out


def visible_docs():
    """(window, document) of every visible web page in every Edge window. Re-read each time: Edge redraws."""
    for w in edge_windows():
        try:
            for d, _ in auto.WalkControl(w, maxDepth=30):
                if d.ControlTypeName == "DocumentControl" and d.BoundingRectangle.width() > 0:
                    yield w, d
        except Exception:
            pass


def ext_page(wait):
    end = time.time() + wait
    while True:
        for w, d in visible_docs():
            if d.Name == TITLE:
                return w, d
        if time.time() >= end:
            return None, None
        time.sleep(0.5)


def els(doc):
    return [c for c, _ in auto.WalkControl(doc, maxDepth=40) if c.Name]


def view(doc):
    return " | ".join(f"{c.ControlTypeName[:-7]}:{c.Name[:50]}" for c in els(doc))[:1500]


def find_btn(doc, rx, enabled=True):
    return next((c for c in els(doc) if c.ControlTypeName in ("ButtonControl", "HyperlinkControl")
                 and rx.search(c.Name.strip()) and (c.IsEnabled or not enabled)), None)


def press(c):
    try:
        c.GetInvokePattern().Invoke()
    except Exception:  # some web buttons lack InvokePattern
        c.GetLegacyIAccessiblePattern().DoDefaultAction()


def tab_ids():
    """UIA runtime ids of every tab (stable while the tab lives, unlike its title: Gmail's changes by itself)."""
    out = set()
    for w in edge_windows():
        try:
            out |= {tuple(c.GetRuntimeId()) for c, _ in auto.WalkControl(w, maxDepth=25) if c.ControlTypeName == "TabItemControl"}
        except Exception:
            pass
    return out


def close_tabs(before=None, keep_ext=False):
    """Closes (with each tab's own close button) our extension-page tabs, also leftovers of a crashed run (unless
    keep_ext), and, when `before` (ids of the tabs that existed when we started) is given, tabs NEW since then whose
    title mentions Claude = what the sign-in opened. Never touches any other tab. UIA elements go stale while tabs
    change, so every tab is handled alone and the pass is repeated."""
    n = 0
    for _ in range(3):
        again = False
        for w in edge_windows():
            try:
                tabs = [c for c, _ in auto.WalkControl(w, maxDepth=25) if c.ControlTypeName == "TabItemControl"]
            except Exception:
                again = True
                continue
            for t in tabs:
                try:
                    ours = t.Name.startswith(TITLE)
                    new = before is not None and tuple(t.GetRuntimeId()) not in before and "claude" in t.Name.lower()
                    if not ((ours and not keep_ext) or (new and not ours)):
                        continue
                    x = next((b for b, _ in auto.WalkControl(t, maxDepth=3) if b.ControlTypeName == "ButtonControl"
                              and CLOSE.search(b.Name)), None)
                    if x:
                        press(x); n += 1; again = True
                except Exception:
                    again = True
        if not again:
            break
        time.sleep(0.5)
    return n


CLAUDEISH = re.compile(r"claude|anthropic|authori[sz]|autoriz", re.I)


def new_tabs(before):
    """[(window, tab)] of tabs that did not exist when we started AND whose title looks like claude.ai's: the page the
    sign-in opened. Our own extension tab is excluded. Nothing else in the browser is ever looked at or clicked."""
    out = []
    for w in edge_windows():
        try:
            for t, _ in auto.WalkControl(w, maxDepth=25):
                if t.ControlTypeName == "TabItemControl" and tuple(t.GetRuntimeId()) not in before \
                        and CLAUDEISH.search(t.Name) and not t.Name.startswith(TITLE):
                    out.append((w, t))
                    if w.NativeWindowHandle not in state_["ours"]:
                        state_["touched"].add(w.NativeWindowHandle)  # the sign-in put a tab in the person's window
        except Exception:
            pass
    return out


def new_pages(before):
    """[(window, document)] for the new claude.ai tabs that are in front in their window (only the front tab of a
    window has a readable document). The document may be blank until the window has been woken (see wake())."""
    out = []
    for w, t in new_tabs(before):
        try:
            if not t.GetSelectionItemPattern().IsSelected:
                continue
            docs = [d for d, _ in auto.WalkControl(w, maxDepth=30)
                    if d.ControlTypeName == "DocumentControl" and d.BoundingRectangle.width() > 0]
            named = [d for d in docs if d.Name]
            if named or docs:
                out.append((w, (named or docs)[-1]))
        except Exception:
            pass
    return out


def select_new_tab(before):
    """Brings the tab the sign-in opened to the front (if our extension tab still says signed out, it may need us)."""
    for _, t in new_tabs(before):
        try:
            t.GetSelectionItemPattern().Select()
            return True
        except Exception:
            pass
    return False


def select_ext_tab():
    """Brings our extension tab to the front (a new tab hides it and only the front tab can be read)."""
    for w in edge_windows():
        try:
            for c, _ in auto.WalkControl(w, maxDepth=25):
                if c.ControlTypeName == "TabItemControl" and c.Name.startswith(TITLE):
                    c.GetSelectionItemPattern().Select()
                    return True
        except Exception:
            pass
    return False


# ---- focus: never steal it (guard thread + off-screen window, like the kit's login/click.py) -----------------
# Edge grabs the foreground when a window opens and on page loads. A guard thread polls every 5 ms and hands the
# focus back to whatever the person had (a few ms, measured), unless the person themselves just chose an
# Edge window (input in the last 0.5 s). Our window is moved off-screen the moment it appears.
OFF = (-32000, -32000, 900, 900)
state_ = {"last": 0, "paused": False, "stop": False, "before_h": set(), "ours": set(), "touched": set()}
_pid_exe = {}


def is_edge(h):
    pid = ctypes.c_ulong()
    u.GetWindowThreadProcessId(h, ctypes.byref(pid))
    if pid.value not in _pid_exe:
        k = ctypes.windll.kernel32
        ph = k.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
        buf, n = ctypes.create_unicode_buffer(520), ctypes.c_ulong(520)
        ok = ph and k.QueryFullProcessImageNameW(ph, 0, buf, ctypes.byref(n))
        if ph:
            k.CloseHandle(ph)
        _pid_exe[pid.value] = bool(ok) and buf.value.lower().endswith("msedge.exe")
    return _pid_exe[pid.value]


def idle_s():
    class LII(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    i = LII(ctypes.sizeof(LII), 0)
    u.GetLastInputInfo(ctypes.byref(i))
    return (ctypes.windll.kernel32.GetTickCount() - i.dwTime) / 1000


def gap(secs=0.5):
    """Wait until the person has not touched keyboard/mouse for `secs` (before anything that needs the focus)."""
    end = time.time() + 600
    while idle_s() < secs and time.time() < end:
        time.sleep(0.05)


def refocus(prev):
    for _ in range(30):
        fg = u.GetForegroundWindow()
        if not prev or fg == prev or not u.IsWindow(prev):
            return
        a = u.GetWindowThreadProcessId(fg, None)
        me = ctypes.windll.kernel32.GetCurrentThreadId()
        u.AttachThreadInput(me, a, True); u.BringWindowToTop(prev); u.SetForegroundWindow(prev)
        u.AttachThreadInput(me, a, False)
        time.sleep(0.01)


def guard():
    st = state_
    while not st["stop"]:
        fg = u.GetForegroundWindow()
        if st["paused"]:  # the script itself has the focus on purpose: touch nothing, remember nothing
            pass
        elif fg and fg != st["last"]:
            if is_edge(fg) and (fg not in st["before_h"] or idle_s() > 0.5):
                refocus(st["last"])  # a window of ours (or Edge raising itself): give it back
            else:
                st["last"] = fg      # the person's own choice
        time.sleep(0.005)


def selected_tabs():
    """{window handle: runtime id of the tab in front} for every Edge window, to put the person's view back."""
    out = {}
    for w in edge_windows():
        try:
            for c, _ in auto.WalkControl(w, maxDepth=25):
                if c.ControlTypeName == "TabItemControl" and c.GetSelectionItemPattern().IsSelected:
                    out[w.NativeWindowHandle] = tuple(c.GetRuntimeId())
        except Exception:
            pass
    return out


def restore_tabs(snap):
    for w in edge_windows():
        want = snap.get(w.NativeWindowHandle)
        if not want or w.NativeWindowHandle in state_["ours"] or w.NativeWindowHandle not in state_["touched"]:
            continue  # only windows where WE changed something: never undo a tab switch the person made themselves
        try:
            for c, _ in auto.WalkControl(w, maxDepth=25):
                if c.ControlTypeName == "TabItemControl" and tuple(c.GetRuntimeId()) == want:
                    if not c.GetSelectionItemPattern().IsSelected:
                        c.GetSelectionItemPattern().Select()
                    break
        except Exception:
            pass


_ENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


def edge_hwnds():
    """Handles of every top-level Edge browser window, visible or not (EnumWindows: microseconds, unlike UIA)."""
    out = []

    def cb(h, _):
        b = ctypes.create_unicode_buffer(40)
        u.GetClassNameW(h, b, 40)
        if b.value == "Chrome_WidgetWin_1" and u.GetWindowTextLengthW(h) and is_edge(h):
            out.append(h)
        return True
    u.EnumWindows(_ENUM(cb), 0)
    return set(out)


def open_window():
    """Opens the extension page in a NEW Edge window (never as a tab in the person's window) and parks it off-screen
    the instant it exists (1 ms polling) and keeps it there for a moment in case Edge re-places it when it shows it."""
    seen = edge_hwnds()
    subprocess.Popen([EDGE, f"--profile-directory={PROFILE}", "--new-window", f"--window-position={OFF[0]},{OFF[1]}",
                      f"--window-size={OFF[2]},{OFF[3]}", PAGE])
    end = time.time() + 25
    while time.time() < end:
        new = edge_hwnds() - seen
        if new:
            h = next(iter(new))
            state_["ours"].add(h)
            t1 = time.time()
            while time.time() - t1 < 1.5:  # Edge may maximise/re-place it right after creating it: put it back
                r = ctypes.wintypes.RECT()
                u.GetWindowRect(h, ctypes.byref(r))
                if r.left > -30000 and not u.IsIconic(h):
                    u.SetWindowPos(h, 0, *OFF, 0x14)  # SWP_NOACTIVATE | SWP_NOZORDER
                time.sleep(0.002)
            return h
        time.sleep(0.001)
    return None


BLANK = ("New tab", "Nueva pestaña", "Nouvel onglet", "Neuer Tab", "Nuova scheda", "Nova guia")


def close_window(h, wait=3.0):
    """WM_CLOSE (graceful), then check it is really gone; retry once. Returns True if the window no longer exists."""
    for _ in range(2):
        u.PostMessageW(h, 0x10, 0, 0)
        end = time.time() + wait
        while time.time() < end:
            if not u.IsWindow(h):
                return True
            time.sleep(0.1)
    return not u.IsWindow(h)


def sweep(before_h=None):
    """Close every window that is ours or a leftover of ours, and nothing else:
      - parked off-screen (we use -32000; minimised windows also report it, hence the IsIconic test) or new since the
        run started (`before_h`), AND
      - every tab in it is blank / our extension page / a claude.ai-looking page.
    A window with any other tab is the person's and is never touched."""
    n = 0
    for w in edge_windows():
        try:
            h = w.NativeWindowHandle
            if h in state_["ours"]:
                pass
            else:
                parked = w.BoundingRectangle.left <= -30000 and not u.IsIconic(h)
                new = before_h is not None and h not in before_h
                if not (parked or new):
                    continue
            tabs = [c.Name for c, _ in auto.WalkControl(w, maxDepth=25) if c.ControlTypeName == "TabItemControl"]
            if tabs and all(t.startswith(BLANK) or t.startswith(TITLE) or CLAUDEISH.search(t) for t in tabs):
                if close_window(h):
                    n += 1
                else:
                    log(f"window {hex(h)} would not close")
        except Exception:
            pass
    return n


def show_for_person(w):
    """The only case where we WANT the focus: a human step (captcha, code, wrong account). Window centred in front."""
    h = w.NativeWindowHandle
    state_["paused"] = True
    sw, sh = u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    size = min(900, sh - 80)
    u.ShowWindow(h, 9)  # SW_RESTORE
    u.SetWindowPos(h, 0, (sw - size) // 2, (sh - size) // 2, size, size, 0x40)  # SWP_SHOWWINDOW
    refocus(h)
    log("window brought to the front for you")


def _readable(h):
    try:
        return any(True for _ in _first_els(auto.ControlFromHandle(h)))
    except Exception:
        return False


def nudge(h):
    """Wakes an off-screen window of ours WITHOUT touching the focus: minimise it without activating it and restore it
    without activating it. That visibility change makes Edge build the page's accessibility tree (tested:
    3/3, foreground never moved; SetWindowPos/ShowWindow variants alone did not work). Then park it off-screen again."""
    u.ShowWindow(h, 7)   # SW_SHOWMINNOACTIVE
    time.sleep(0.15)
    u.ShowWindow(h, 4)   # SW_SHOWNOACTIVATE
    r = ctypes.wintypes.RECT()
    u.GetWindowRect(h, ctypes.byref(r))
    if r.left > -30000:
        u.SetWindowPos(h, 0, *OFF, 0x14)


def wake(h, tries=3):
    """A window that was never visible shows UIA an empty page (known Edge/UIA limitation). 1st choice: nudge() (no focus change at
    all). Last resort, only if that fails: a short slot in front, with the person idle for 1 s, cut off within 20 ms of
    any keyboard/mouse input (then retried); it keeps its accessibility tree afterwards."""
    if h in state_["ours"]:
        for _ in range(3):
            nudge(h)
            end = time.time() + 3
            while time.time() < end:
                if _readable(h):
                    return True
                time.sleep(0.1)
        log("nudge did not wake the window: using a short focus slot")
    for _ in range(tries):
        gap(1.0)
        state_["paused"] = True
        ok = False
        try:
            refocus(h)
            t0 = time.time()
            while time.time() - t0 < 4:
                time.sleep(0.02)
                if idle_s() < 0.1:  # the person is typing: give the focus back right now
                    break
                if _readable(h):
                    ok = True
                    time.sleep(0.3)
                    break
        finally:
            state_["paused"] = False
            refocus(state_["last"])
        if ok:
            return True
    return False


def _first_els(w):
    for d, _ in auto.WalkControl(w, maxDepth=30):
        if d.ControlTypeName == "DocumentControl" and d.BoundingRectangle.width() > 0 and d.Name and any(
                c.Name for c, _ in auto.WalkControl(d, maxDepth=40)):
            yield d
            return


def state(doc):
    """'out' = sign-in button shown · 'in' = page rendered without it · None = nothing readable yet."""
    if not els(doc):
        return None
    return "out" if find_btn(doc, LOGIN) else "in"


def authorise(w, ad):
    """Press the Authorize button. claude.ai keeps it disabled while its page has no focus (seen in practice), so
    if it is disabled: wait for the person to be idle, give that window the focus for a moment, press, hand it back."""
    a = find_btn(ad, AUTH)
    nm = a.Name if a else None
    if not a:
        off = find_btn(ad, AUTH, enabled=False)
        if not off:
            return False
        nm = off.Name
        gap(1.0)
        state_["paused"] = True
        refocus(w.NativeWindowHandle)
        t1 = time.time()
        typing = False
        while time.time() - t1 < 6 and not a and not typing:  # it also waits ~2 s after the page loads
            for _ in range(15):
                time.sleep(0.02)
                if idle_s() < 0.1:  # the person is typing: hand the focus back at once, retry next second
                    typing = True
                    break
            if not typing:
                a = find_btn(ad, AUTH)
    try:
        if a:
            press(a)
    except Exception as e:  # the page often rebuilds itself on click and the button vanishes mid-call
        log(f"press raised {e.__class__.__name__} (normal if the page changed)")
    finally:
        state_["paused"] = False
        refocus(state_["last"])
    log(f"clicked {nm!r}" if a else f"{nm!r} stayed disabled")
    return bool(a)


def run():
    st = state_
    st.update(stop=False, paused=False, last=u.GetForegroundWindow(), before_h=edge_hwnds(), ours=set(), touched=set())
    threading.Thread(target=guard, daemon=True).start()
    snap = selected_tabs()
    n = sweep()  # windows an earlier (crashed / killed) run left behind
    close_tabs()  # and leftover tabs of ours in the person's own windows
    if n:
        log(f"closed {n} leftover window(s) from an earlier run")
    before = tab_ids()
    w, doc, keep, h = None, None, False, None
    try:
        h = open_window()
        if not h:
            log("no Edge window appeared (is Edge installed at the expected path?)")
            return 2
        if not wake(h):
            log("could not wake the off-screen window (the person kept typing?)")
            return 2
        w, doc = ext_page(25)
        if not doc:
            log("the extension page never showed up (Edge not running, or another profile has the extension?)")
            return 2
        before = tab_ids()  # now includes our own extension tab: whatever else appears is the sign-in's
        stt = None
        for _ in range(20):  # React needs a moment to render
            w, doc = ext_page(2)
            stt = state(doc) if doc else None
            if stt:
                break
            time.sleep(0.5)
        if dump:
            log("DUMP " + (view(doc) if doc else "no page"))
            return 0
        if not stt:
            log("page rendered nothing UIA can read: " + (view(doc) if doc else "no page"))
            return 2
        if stt == "in":
            log("already signed in (no sign-in button): " + view(doc)[:200])
            return 0
        log("signed out: " + view(doc)[:300])
        if dry:
            return 0
        btn = find_btn(doc, LOGIN)
        press(btn)
        log(f"clicked {btn.Name!r}")
        t_click, t_close, blank = time.time(), 0, 0
        end, last = time.time() + 120, ""
        while time.time() < end:
            time.sleep(1)
            new_docs = new_pages(before)  # the page the sign-in opened, if it is in front
            if new_docs and not any(els(d) for _, d in new_docs) and blank < 3 and time.time() - t_click > 3:
                blank += 1
                wake(new_docs[0][0].NativeWindowHandle)  # blank = its window never was in front: one short slot
            for aw, ad in new_docs:
              try:
                names = view(ad)
                if not names:
                    continue
                if names != last:
                    log(f"page {ad.Name[:40]!r}: {names[:300]}")
                    last = names
                if HUMAN.search(names):
                    log("needs the person (captcha / verification code): tab left open")
                    keep = True
                    show_for_person(aw)
                    return 3
                other = {m.lower() for m in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", names)} - {EXPECT} if EXPECT else set()
                if other:  # the page names another account: authorising would link the extension to it
                    log(f"the page shows another account {sorted(other)}, not {EXPECT}: not clicking; tab left open")
                    keep = True
                    show_for_person(aw)
                    return 3
                if authorise(aw, ad):
                    time.sleep(2)
                    break
              except Exception as e:  # stale element while the page changes: look again next second
                log(f"retry ({e.__class__.__name__})")
            w2, d2 = ext_page(0)
            if d2 and state(d2) == "in":
                log("signed in")
                return 0
            if d2 and state(d2) is None:
                nudge(h)  # our tab is in front again but blank (it was hidden): wake it, no focus involved
            if time.time() - t_click > 4 and time.time() - t_close > 3:
                # only the front tab can be read: alternate between the sign-in page and our tab every few seconds
                t_close = time.time()
                if d2:
                    select_new_tab(before)  # ours says signed out: maybe the other page still needs its button
                else:
                    select_ext_tab()        # the other page has nothing left to press: check ours
                    nudge(h)                # (it may come back blank: wake it, no focus involved)
        log("timed out: still signed out")
        return 2
    finally:
        try:
            if not keep:
                close_tabs(before)    # tabs the sign-in opened in the person's own windows
                for hw in list(st["ours"]):  # our window (also holds Edge's blank "New tab"): close it whole
                    close_window(hw)
                sweep(st["before_h"])  # catch-all: anything else we caused (blank windows) goes too
            restore_tabs(snap)    # the tab each of the person's windows had in front
            time.sleep(1.0)       # Edge raises another window when ours closes: the guard is still running
            if not keep:
                sweep(st["before_h"])
                refocus(st["last"])
        finally:
            st["stop"] = True


def _bye(*_):
    raise KeyboardInterrupt  # SIGTERM / Ctrl+Break: unwind through run()'s finally so the windows get closed


if __name__ == "__main__":
    import signal
    for sg in (signal.SIGTERM, getattr(signal, "SIGBREAK", signal.SIGTERM)):
        signal.signal(sg, _bye)
    if "--loop" in sys.argv:
        secs = int(sys.argv[sys.argv.index("--loop") + 1])
        while True:
            try:
                run()
            except Exception as e:
                log(f"error {e.__class__.__name__}: {e}")
            time.sleep(secs)
    try:
        sys.exit(run())
    except Exception as e:
        log(f"error {e.__class__.__name__}: {e} @ our line {[f.lineno for f in traceback.extract_tb(e.__traceback__) if f.filename.endswith('.py') and 'uiautomation' not in f.filename]}")
        sys.exit(2)
