# Self-check of favoritos.ps1 in a real hidden PowerShell (pywinpty; no tokens; never touches your profile or history).
# Makes a fake history in a temp dir, generates favoritos.txt from it with detectar.py, dot-sources a COPY of favoritos.ps1
# next to it and drives the arrows. Windows only (pywinpty).   Run: python test_tui.py   (pip install pywinpty)
import os, shutil, subprocess, sys, tempfile, threading, time
import winpty

here = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.mkdtemp(prefix='fav_')
ps = shutil.which('pwsh') or shutil.which('powershell')
assert ps, 'no pwsh / powershell found'

# fake history -> generated list (what the install does, minus the person's OK)
dirs = [os.path.join(tmp, 'dirs', n) for n in 'abcde']
for d in dirs: os.makedirs(d)
hist = [f'cd "{d}"; claude' for d, k in zip(dirs, (5, 4, 3, 2, 1)) for _ in range(k)] + [f'cd "{tmp}/gone"; claude'] * 9
open(f'{tmp}/fake_history.txt', 'w', encoding='utf-8').write('\n'.join(hist) + '\n')
shutil.copy(f'{here}/favoritos.ps1', tmp)
out = subprocess.run([sys.executable, '-I', f'{here}/detectar.py', '--history', f'{tmp}/fake_history.txt', '--write', f'{tmp}/favoritos.txt'],
                     capture_output=True, text=True)
assert out.returncode == 0, out.stderr
fav = [l for l in open(f'{tmp}/favoritos.txt', encoding='utf-8').read().splitlines() if l]
assert len(fav) == 4 and 'gone' not in ''.join(fav), fav

init = (f"Set-PSReadLineOption -HistorySavePath '{tmp}/h.txt'; . '{tmp}/favoritos.ps1'; "
        "$global:FavTraceHook = { $l=$null;$c=0;[Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$l,[ref]$c); "
        "[IO.File]::WriteAllText('@DUMP@',\"$l\") }")
UP, DOWN = chr(27) + '[A', chr(27) + '[B'

def session():
    # history path set at spawn, BEFORE any typed line: otherwise test lines leak into the real history
    p = winpty.PtyProcess.spawn([ps, '-NoProfile', '-NoLogo', '-NoExit', '-Command',
                                 f"Set-PSReadLineOption -HistorySavePath '{tmp}/h.txt'"], dimensions=(30, 200))
    threading.Thread(target=lambda: [p.read(65536) for _ in iter(int, 1)], daemon=True).start()
    time.sleep(4)
    p.dump = os.path.join(tmp, f'buf{len(os.listdir(tmp))}.txt').replace(chr(92), '/')
    p.write(init.replace('@DUMP@', p.dump) + f"; Clear-Host; [IO.File]::WriteAllText('{tmp}/ready{id(p)}','1')" + chr(13))
    return p

def key(p, k, wait=0.5):
    if k in (UP, DOWN) and os.path.exists(p.dump): os.remove(p.dump)   # a stale trace would hide a handler that did not run
    p.write(k); time.sleep(wait)
def buf(p):   # buffer as left by the last Up/Down handler (an extra handler, e.g. F12, would reset PSReadLine's history position)
    return open(p.dump, encoding='utf-8').read() if os.path.exists(p.dump) else None
def run(p, cmd):
    for ch in cmd: p.write(ch); time.sleep(0.03)
    time.sleep(0.3); p.write('\r'); time.sleep(1.5)

a, b = session(), session()
try:
    t0 = time.time()
    while len([f for f in os.listdir(tmp) if f.startswith('ready')]) < 2 and time.time() - t0 < 60: time.sleep(0.5)
    time.sleep(3)
    run(a, 'echo H1'); run(a, 'echo H2'); run(a, 'echo FROM_A_ONLY')
    seen = []
    for i in range(4): key(a, UP); seen.append(buf(a))
    assert seen == fav, seen
    key(a, UP); assert buf(a) == 'echo FROM_A_ONLY', buf(a)
    key(a, UP); assert buf(a) == 'echo H2', buf(a)
    key(a, DOWN); assert buf(a) == 'echo FROM_A_ONLY', buf(a)
    key(a, DOWN); assert buf(a) == fav[3], buf(a)
    key(a, DOWN); assert buf(a) == fav[2], buf(a)
    key(a, DOWN); key(a, DOWN); assert buf(a) == fav[0], buf(a)
    key(a, DOWN); assert buf(a) == '', repr(buf(a))
    key(a, DOWN); assert buf(a) == '', 'down on empty'
    # Ctrl+C mid-navigation, then Up starts at favourite 1 again
    key(a, UP); key(a, UP); key(a, '\x03', 1.0); key(a, UP); assert buf(a) == fav[0], buf(a)
    key(a, '\x03', 1.0)
    # text typed: Up = plain history (last command), no favourites
    for ch in 'echo H': a.write(ch)
    time.sleep(0.5); key(a, UP); got = buf(a); assert got == 'echo FROM_A_ONLY', got
    key(a, '\x03', 1.0)
    # Enter on a history entry (never on a favourite: it would launch claude): state is fresh afterwards
    for _ in range(5): key(a, UP)
    key(a, '\r', 2.5); key(a, UP, 1.0); assert buf(a) == fav[0], buf(a)
    key(a, '\x03', 1.0)
    # other terminal: does not see A's commands among favourites/history
    seen_b = []
    for i in range(5): key(b, UP); seen_b.append(buf(b))
    assert seen_b[:4] == fav and 'FROM_A_ONLY' not in seen_b[4:], seen_b
    print('ok')
finally:
    a.terminate(force=True); b.terminate(force=True); shutil.rmtree(tmp, ignore_errors=True)
