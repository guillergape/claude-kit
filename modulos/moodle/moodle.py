"""Moodle via the mobile-app REST API (any university Moodle with the mobile service on). Stdlib only.
Config: moodle.json next to this file (or $MOODLE_CONFIG), see moodle.example.json.

  moodle.py courses                 list my enrolled courses (id | short name | full name), to fill moodle.json
  moodle.py new   [SUBJ...]         new/updated material + unseen notices
  moodle.py due   [SUBJ...] [--all] pending to-dos (timeline); --all adds courses not in moodle.json
  moodle.py dates [SUBJ...] [--all] upcoming calendar events not yet seen (--all: seen ones too)
  moodle.py get   SUBJ CMID...      download those modules' files to the inbox
  moodle.py post  DID               print one notice (discussion) as text
  moodle.py seen  KEY...            mark SUBJ:cm<id> / SUBJ:d<id> / SUBJ:ev<id> as seen
  moodle.py token                   save the token from a copied moodlemobile://token=… (clipboard), never printed
"""
import base64, html, json, os, pathlib, re, sys, time, urllib.error, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
CONFIG = pathlib.Path(os.environ.get("MOODLE_CONFIG") or pathlib.Path(__file__).with_name("moodle.json"))
try:
    CFG = json.loads(CONFIG.read_text(encoding="utf-8"))
except (OSError, ValueError) as e:
    sys.exit(f"Missing or broken {CONFIG} ({e}). Copy moodle.example.json to moodle.json and fill it in.")
SITE = CFG["site"].rstrip("/")
TOKEN_FILE = pathlib.Path(os.path.expanduser(CFG.get("token_file", "~/.moodle-token")))
ROOT = pathlib.Path(os.path.expanduser(CFG.get("root", "~")))  # one subfolder per subject, named like the keys below
INBOX = ROOT / "_moodle" / "inbox"
STATE = ROOT / "_moodle" / "seen.json"
COURSES = CFG.get("courses", {})  # {"Prog": 12345, ...}
BY_ID = {v: k for k, v in COURSES.items()}
FILE_MODS = {"resource", "folder"}
NOTICE_DAYS = 30


def ws(fn, **kw):
    if not TOKEN_FILE.exists():
        sys.exit(f"No token in {TOKEN_FILE}: get one (see SKILL.md, 'Token').")
    data = urllib.parse.urlencode({"wstoken": TOKEN_FILE.read_text().strip(), "wsfunction": fn,
                                   "moodlewsrestformat": "json", **kw}).encode()
    try:
        r = json.load(urllib.request.urlopen(SITE + "/webservice/rest/server.php", data, timeout=60))
    except urllib.error.HTTPError as e:
        if e.code != 403:
            raise
        sys.exit(f"HTTP 403: {SITE} is blocking this network, not the token (some Moodles only allow the campus "
                 f"network or VPN). Open {SITE} in a browser to read its notice, then retry from there.")
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e.reason):
            raise
        sys.exit(f"SSL: this Python doesn't trust {SITE}'s root certificate yet ({e.reason}). Windows: run once in "
                 f"PowerShell `Invoke-WebRequest -UseBasicParsing -Method Head {SITE}` (Windows fetches the missing root), "
                 "then retry. Mac (python.org Python): run `Install Certificates.command` in its Applications folder.")
    if isinstance(r, dict) and "exception" in r:
        if r.get("errorcode") in ("invalidtoken", "accessexception"):
            sys.exit("TOKEN EXPIRED/INVALID: renew it (see SKILL.md, 'Token').")
        raise SystemExit(f"API error in {fn}: {r.get('errorcode')}: {r.get('message')}")
    return r


def load():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=0, sort_keys=True), encoding="utf-8")


def subjects(args):
    if not COURSES:
        sys.exit("No courses in moodle.json yet: run `moodle.py courses` and add them.")
    if not args:
        return list(COURSES)
    lower = {k.lower(): k for k in COURSES}
    try:
        return [lower[a.lower()] for a in args]
    except KeyError as e:
        sys.exit(f"Unknown subject {e}. Known: {', '.join(COURSES)}")


def when(ts):
    return time.strftime("%a %d %b %H:%M", time.localtime(ts))


def on_disk(subj):
    # lowercase stems (a .ppt converted to .pdf still counts) + byte sizes (files get renamed when filed)
    # ponytail: rescans the subject folder on every call; cache it if it gets slow
    files = [p for p in [*(ROOT / subj).rglob("*"), *(INBOX / subj).glob("*")] if p.is_file()]
    return {p.stem.lower() for p in files} | {p.stat().st_size for p in files}


def had(c, disk):
    return pathlib.Path(c["filename"]).stem.lower() in disk or c.get("filesize") in disk


def modules(cid):
    for sec in ws("core_course_get_contents", courseid=cid):
        for m in sec["modules"]:
            yield html.unescape(sec["name"]), m


def cmd_courses(args):
    me = ws("core_webservice_get_site_info")
    print(f"# {me.get('sitename')} · {me.get('fullname')} (userid {me.get('userid')})")
    for c in ws("core_enrol_get_users_courses", userid=me["userid"]):
        tag = f"  <- {BY_ID[c['id']]}" if c["id"] in BY_ID else ""
        print(f"{c['id']} | {c.get('shortname', '')} | {c.get('fullname', '')}{tag}")


def cmd_new(args):
    state = load()
    for subj in subjects(args):
        cid, disk, first = COURSES[subj], on_disk(subj), not any(k.startswith(subj + ":") for k in state)
        files, others, notices = [], [], []
        for sec, m in modules(cid):
            key = f"{subj}:cm{m['id']}"
            if m["modname"] in FILE_MODS:
                fs = [c for c in m.get("contents", []) if c.get("type") == "file"]
                newest = max((c["timemodified"] for c in fs), default=0)
                if key in state:
                    if newest > state[key]:
                        files.append((sec, m, fs, "UPDATED"))
                elif not all(had(c, disk) for c in fs):
                    files.append((sec, m, fs, "new"))
            elif m["modname"] == "forum":
                for d in ws("mod_forum_get_forum_discussions", forumid=m["instance"], perpage=15)["discussions"]:
                    dk = f"{subj}:d{d['discussion']}"
                    if d["timemodified"] > state.get(dk, 0) and d["timemodified"] > time.time() - NOTICE_DAYS * 86400:
                        notices.append(d)
            elif m["modname"] not in ("label", "subsection") and key not in state:
                if first:
                    state[key] = 1  # baseline: links/quizzes already there aren't news
                else:
                    others.append((sec, m))
        print(f"## {subj} (course {cid})")
        for sec, m, fs, tag in files:
            names = ", ".join(c["filename"] for c in fs[:4]) + (f" +{len(fs) - 4}" if len(fs) > 4 else "")
            print(f"  [{tag}] cm{m['id']} | {sec} | {html.unescape(m['name'])} | {names} | {when(max(c['timemodified'] for c in fs)) if fs else '-'}")
        for sec, m in others:
            print(f"  [new {m['modname']}] cm{m['id']} | {sec} | {html.unescape(m['name'])}")
        for d in notices:
            print(f"  [notice] d{d['discussion']} | {when(d['timemodified'])} | {d['userfullname']} | {html.unescape(d['name'])}")
        if not (files or others or notices):
            print("  nothing new")
    save(state)


def cmd_due(args):
    show_all = "--all" in args
    wanted = {COURSES[s] for s in subjects([a for a in args if a != "--all"])}
    for e in ws("core_calendar_get_action_events_by_timesort", timesortfrom=int(time.time()), limitnum=50)["events"]:
        cid = e["course"]["id"]
        if cid in wanted or (show_all and cid not in BY_ID):
            print(f"{when(e['timesort'])} | {BY_ID.get(cid, e['course']['fullname'][:30])} | {html.unescape(e['name'])} | {e.get('modulename')}")


def cmd_dates(args):
    show_all = "--all" in args
    state = load()
    cids = [COURSES[s] for s in subjects([a for a in args if a != "--all"])]
    q = {f"events[courseids][{i}]": c for i, c in enumerate(cids)}
    q.update({"options[timestart]": int(time.time()), "options[userevents]": 0, "options[siteevents]": 0})
    for e in sorted(ws("core_calendar_get_calendar_events", **q)["events"], key=lambda e: e["timestart"]):
        subj = BY_ID.get(e["courseid"], str(e["courseid"]))
        key = f"{subj}:ev{e['id']}"
        if show_all or key not in state:
            end = f" -> {when(e['timestart'] + e['timeduration'])}" if e["timeduration"] else ""
            print(f"ev{e['id']} | {subj} | {when(e['timestart'])}{end} | {e['eventtype']}/{e.get('modulename') or '-'} | {html.unescape(e['name'])}")


def cmd_get(args):
    subj, cms = subjects(args[:1])[0], {int(a.lstrip("cm")) for a in args[1:]}
    state, out = load(), INBOX / subj
    out.mkdir(parents=True, exist_ok=True)
    for _, m in modules(COURSES[subj]):
        if m["id"] not in cms:
            continue
        fs = [c for c in m.get("contents", []) if c.get("type") == "file"]
        for c in fs:
            dest = out / c["filename"]
            if dest.exists():
                print(f"skip (already in inbox): {dest.name}")
                continue
            if not c["fileurl"].startswith(SITE + "/"):  # the token only ever goes to our own Moodle
                print(f"skip (not on {SITE}): {c['filename']} -> {c['fileurl']}")
                continue
            url = c["fileurl"] + ("&" if "?" in c["fileurl"] else "?") + "token=" + TOKEN_FILE.read_text().strip()
            dest.write_bytes(urllib.request.urlopen(url, timeout=120).read())
            print(f"got: {dest}")
        state[f"{subj}:cm{m['id']}"] = max((c["timemodified"] for c in fs), default=1)
        cms.discard(m["id"])
    save(state)
    if cms:
        print("not found in course:", ", ".join(f"cm{i}" for i in cms))


def cmd_post(args):
    for p in ws("mod_forum_get_discussion_posts", discussionid=int(args[0].lstrip("d")))["posts"]:
        text = html.unescape(re.sub(r"<[^>]+>", " ", p["message"]))
        print(f"--- {p['author']['fullname']} | {when(p['timecreated'])} | {p['subject']}\n{re.sub(r'[ \t]+', ' ', text).strip()}\n")


def cmd_seen(args):
    state, now = load(), int(time.time())
    for k in args:  # SUBJ:cm123 / SUBJ:d456 / SUBJ:ev789
        if ":" not in k:
            sys.exit(f"Use SUBJ:key, e.g. Prog:{k}")
        state[k] = now
    save(state)
    print("marked:", ", ".join(args))


def cmd_token(args):
    # the person copies moodlemobile://token=<base64> (SKILL.md, 'Token'); only "saved" is printed, so Claude never sees it
    try:
        import tkinter
        tk = tkinter.Tk()
        tk.withdraw()
        clip = tk.clipboard_get()
    except Exception as e:
        sys.exit(f"Couldn't read the clipboard ({type(e).__name__}).")
    m = re.search(r"token=([A-Za-z0-9+/=]+)", clip)
    try:
        token = base64.b64decode(m.group(1) + "=" * (-len(m.group(1)) % 4)).decode().split(":::")[1]
    except (AttributeError, ValueError, IndexError):
        sys.exit("The clipboard has no moodlemobile://token=… : copy it first (SKILL.md, 'Token').")
    tk.clipboard_clear()  # don't leave it in the clipboard
    tk.update()
    tk.destroy()
    TOKEN_FILE.write_text(token)
    print(f"token saved to {TOKEN_FILE} (not shown); clipboard cleared")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("courses", "new", "due", "dates", "get", "post", "seen", "token"):
        sys.exit(__doc__)
    globals()["cmd_" + sys.argv[1]](sys.argv[2:])
