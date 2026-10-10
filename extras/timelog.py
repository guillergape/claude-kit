"""Study-time logger (0 tokens). Usage (from the folder that holds this script's parent, or with the full path):
  python _tools/timelog.py start <subj> <cmd> <ref>        e.g. start Prog study S2
  python _tools/timelog.py lap   <subj> <new label> [--minus N]   close current segment, start a new one
  python _tools/timelog.py mark-end <subj>                 note "session ended now" (used by the hook); `end` then closes at that time
  python _tools/timelog.py end   <subj> [--minus N]        close the session
  python _tools/timelog.py report [subj]                   totals per subj / cmd / ref (+ per label)
--minus N = minutes to subtract from the closing segment (breaks). Log: _tools/timelog.csv
User override (wins over the clock), only on `end`: --total N (whole session = N min) | --from HH:MM (session started then; total = end - that) | --na (unknown; rows logged as NA)
start on a session with the same cmd + ref started < 5 h ago = resume (after /clear): the timer keeps running.
start on a session that was marked ended but never closed = it is logged first (no overrides), then the new one starts.
No PYTHONIOENCODING prefix needed (stdout is set to UTF-8 here), so the command stays `python _tools/timelog.py ...`.
"""
import csv, json, os, sys
from datetime import datetime
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

D = os.environ.get("TIMELOG_DIR") or os.path.dirname(os.path.abspath(__file__))
STATE, LOG = os.path.join(D, "timelog_state.json"), os.path.join(D, "timelog.csv")
now = datetime.now()
RESUME_H = 5


def load():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {}


def end_time(st):
    return datetime.fromisoformat(st["end_t"]) if "end_t" in st else now


def close(st, minus, total=None):
    mins = max(0, round((end_time(st) - datetime.fromisoformat(st["t"])).total_seconds() / 60) - minus)
    if total is not None:
        mins = max(0, total - st.get("acc", 0))
    st.setdefault("rows", []).append([st["label"], mins])
    st["acc"] = st.get("acc", 0) + mins
    return mins


def flush(st, na):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "subj", "cmd", "ref", "label", "min"])
        for l, m in st["rows"]:
            w.writerow([end_time(st).date(), st["subj"], st["cmd"], st["ref"], l, "NA" if na else m])


def main(a):
    if not a:
        return print(__doc__)
    op, s = a[0], load()
    minus = int(a[a.index("--minus") + 1]) if "--minus" in a else 0
    if op == "report":
        if not os.path.exists(LOG):
            return print("No sessions logged yet.")
        tot, lab = defaultdict(int), defaultdict(int)
        for r in csv.DictReader(open(LOG, encoding="utf-8")):
            if len(a) > 1 and r["subj"] != a[1]:
                continue
            m = int(r["min"]) if r["min"].isdigit() else 0
            tot[(r["subj"], r["cmd"], r["ref"])] += m
            lab[(r["subj"], r["cmd"], r["ref"], r["label"])] += m
        for k, v in sorted(tot.items()):
            print(" ".join(k), f"{v // 60}h{v % 60:02d}")
            for l, m in sorted(lab.items()):
                if l[:3] == k and l[3] != "-":
                    print("   ", l[3], f"{m}m")
        return
    subj = a[1]
    if op == "start":
        ref = " ".join(x for x in a[3:] if x != "--force")
        old = s.get(subj)
        if old and "end_t" in old:
            close(old, 0)
            flush(old, False)
            print(f"previous {subj} {old['cmd']} {old['ref']} session (ended {end_time(old):%d %b %H:%M}) was never closed: logged {old['acc']} min, no overrides.")
            old = None
        if old and old["cmd"] == a[2] and old["ref"] == ref and (now - datetime.fromisoformat(old["t"])).total_seconds() < RESUME_H * 3600:
            return print(f"resumed {subj} {a[2]} {ref}: timer running since {datetime.fromisoformat(old['t']):%H:%M} (not restarted)")
        if old and "--force" not in a and (now - datetime.fromisoformat(old["t"])).total_seconds() < RESUME_H * 3600:
            return print(f"CONFLICT: {subj} {old['cmd']} {old['ref']} is still running (started {old['t'][:16]}); NOT started {a[2]} {ref}. "
                         f"Ask the user: close the old one (`end`), or replace it (`start ... --force`, discards its timer), or was {ref} a typo? "
                         f"If that session is still open in another chat, only 'typo' or 'finish that chat first' are safe (its `end` would close this one).")
        if old:
            print(f"WARNING: previous {subj} session ({old['cmd']} {old['ref']}, started {old['t'][:16]}) was never ended; discarded.")
        s[subj] = dict(subj=subj, cmd=a[2], ref=ref, label="-", t=now.isoformat())
        print("started", subj, a[2], ref, now.strftime("%H:%M"))
    elif subj not in s:
        return print("no active session for", subj)
    elif op == "mark-end":
        s[subj]["end_t"] = now.isoformat()
        print(f"{subj} session end marked at {now:%H:%M}; `end` will close it at that time")
    elif op == "lap":
        s[subj].pop("end_t", None)  # the session went on after an end mark
        print(s[subj]["label"], close(s[subj], minus), "min")
        s[subj].update(label=" ".join(a[2:a.index("--minus")] if "--minus" in a else a[2:]), t=now.isoformat())
    elif op == "end":
        tot = None
        if "--total" in a:
            tot = int(a[a.index("--total") + 1])
        elif "--from" in a:
            h, m = map(int, a[a.index("--from") + 1].split(":"))
            e = end_time(s[subj])
            tot = round((e - e.replace(hour=h, minute=m, second=0, microsecond=0)).total_seconds() / 60)
        na = "--na" in a
        r = close(s[subj], minus, tot)
        flush(s[subj], na)
        print("NA (not counted)" if na else f"{s[subj]['acc']} min total", "| last:", s[subj]["label"], r)
        del s[subj]
    json.dump(s, open(STATE, "w", encoding="utf-8"))


if __name__ == "__main__":
    main(sys.argv[1:])
