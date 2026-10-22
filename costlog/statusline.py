"""Status line: shows model · $ · 5 h % · weekly % · context %, and saves per-session usage snapshots
(start + last) in ~/.claude/costlog-state/ so `costlog>` (costlog.py) can log usage start→end with no tokens."""
import json, os, sys, time
from textos import T  # texts in the person's language (textos.json next to this file); Spanish without it

STATE = os.path.expanduser("~/.claude/costlog-state")
LAST_LIMITS = os.path.join(STATE, "_last_limits.json")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def pct(x):
    return f"{x:.0f}%" if isinstance(x, (int, float)) else "?"


d = json.loads(sys.stdin.buffer.read() or b"{}")
os.makedirs(STATE, exist_ok=True)
rl = d.get("rate_limits") or {}
cost = d.get("cost") or {}
snap = {"t": time.time(), "cost": cost.get("total_cost_usd"), "dur_ms": cost.get("total_duration_ms"),
        "5h": rl.get("five_hour"), "7d": rl.get("seven_day")}
if rl:  # t/sid/cost let `costlog.py --mark/--leftover` measure a subagent step (cost delta only within one session)
    save(LAST_LIMITS, {"t": snap["t"], "sid": d.get("session_id"), "cost": snap["cost"], "5h": snap["5h"], "7d": snap["7d"]})

sid = d.get("session_id")
if sid:
    path = os.path.join(STATE, sid + ".json")
    s = load(path)
    if s is None:  # first sighting (chat opened); costlog.py retakes it at the first prompt. Payload limits, else last known
        last = {} if rl else (load(LAST_LIMITS) or {})
        s = {"start": dict(snap, **{k: last[k] for k in ("5h", "7d") if k in last})}
    for k in ("5h", "7d"):  # no limits known at start: take the first ones seen
        if not s["start"].get(k) and snap[k]:
            s["start"][k] = snap[k]
        # window reset since the last refresh: keep the last % before it, so costlog.py can estimate usage across it
        # ponytail: only the first reset is kept; a session spanning two 5 h resets gets a low estimate
        old, new = ((s.get("last") or {}).get(k) or {}).get("resets_at"), (snap[k] or {}).get("resets_at")
        if isinstance(old, (int, float)) and isinstance(new, (int, float)) and abs(old - new) > 300:
            s.setdefault("pre", {}).setdefault(k, s["last"][k])
    prev = (s.get("last") or {}).get("cost")  # this chat just spent: costlog.py spots parallel chats with it
    if isinstance(snap["cost"], (int, float)) and isinstance(prev, (int, float)) and snap["cost"] > prev:
        s["active"] = snap["t"]
        s["end"] = snap  # usage as of this chat's last answer: chats used after it don't count
        spans = s.setdefault("spans", [])  # [first, last] spend times; spends < 2 min apart merge
        if spans and snap["t"] - spans[-1][1] < 120:
            spans[-1][1] = snap["t"]
        else:
            spans.append([snap["t"], snap["t"]])
        del spans[:-50]
    s["last"] = snap
    save(path, s)

sys.stdout.reconfigure(encoding="utf-8")
model = (d.get("model") or {}).get("display_name", "?")
ctx = (d.get("context_window") or {}).get("used_percentage")
c = snap["cost"]
print(f"{model} · ${c:.2f}" if isinstance(c, (int, float)) else model,
      f"· 5h {pct((snap['5h'] or {}).get('used_percentage'))}",
      f"· {T('sem')} {pct((snap['7d'] or {}).get('used_percentage'))}",
      f"· ctx {pct(ctx)}")
