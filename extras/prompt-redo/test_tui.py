# Self-check of the installed prompt-redo setup in a real, hidden Claude Code TUI (pywinpty; no prompt sent = no tokens).
# Types "hello world", ctrl+z twice, ctrl+y twice; passes when the band counts 2 and the text comes back.
# Needs CLAUDE_CODE_PLUGIN_DIRS (settings.json env) and the ctrl+y Global binding in ~/.claude/keybindings.json.
# Run: python test_tui.py   (not with -I if pywinpty is in the user site-packages). Windows only (pywinpty: pip install pywinpty).
import os, re, sys, threading, time
import winpty

env = {k: v for k, v in os.environ.items() if not k.startswith('CLAUDE')}  # a fresh chat, not this one's
p = winpty.PtyProcess.spawn(['claude'], dimensions=(40, 140), cwd=os.path.dirname(os.path.abspath(__file__)), env=env)  # argv list: a string gets its quotes mangled
buf = []
def pump():
    while True:
        try: buf.append(p.read(65536))
        except Exception: break
threading.Thread(target=pump, daemon=True).start()

def step(keys, wait=3):
    p.write(keys); time.sleep(wait); raw = ''.join(buf); buf.clear()
    return re.sub(r'\s+', ' ', re.sub(r'\x1b\][^\x07]*\x07', '', re.sub(r'\x1b\[[0-9;?<>=]*[ -/]*[@-~]', ' ', raw)))

try:
    step('', 15)  # startup
    for ch in 'hello world': p.write(ch); time.sleep(0.05)
    step('')
    step('\x1a')
    z2 = step('\x1a')
    y1 = step('\x19')
    y2 = step('\x19')
finally:
    p.terminate(force=True)

print('after 2nd ctrl+z:', z2[:80]); print('after ctrl+y:', y1[:80]); print('after ctrl+y 2:', y2[:80])
assert '2' in z2, 'redo band did not count 2 (mod not loaded? check CLAUDE_CODE_PLUGIN_DIRS)'
assert 'hello worl' in y1, 'ctrl+y did not redo (check the Global ctrl+y binding)'
assert 'd' in y2, 'second ctrl+y did not redo'
print('ok')
