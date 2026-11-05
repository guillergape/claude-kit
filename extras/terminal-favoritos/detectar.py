"""Find the person's favourite `cd "<folder>"; claude` commands in their PowerShell (PSReadLine) history.

  python detectar.py                      list the top N (default 4) -> nothing is written
  python detectar.py --history <file>     use another history file
  python detectar.py --folders A B C      fallback (no history): build the lines from these folders
  python detectar.py ... --write [file]   also write the list (default: favoritos.txt next to this script)
  python detectar.py --test               self-check (fake history, no real files touched)

Rule for Claude: ALWAYS show the list to the person and wait for their OK (or changes) before using --write.
Recognised: cd / Set-Location / sl / chdir / pushd [-Path|-LiteralPath] <folder> ; or && or | ... claude [args].
Only absolute folders (or ~/...) that exist today are kept; relative ones depend on where the shell was.
"""
import argparse, collections, os, re, subprocess, sys, tempfile

CMD = re.compile(r'^\s*(?:cd|chdir|sl|set-location|pushd)\s+(?:-(?:literal)?path\s+)?(.+?)\s*(?:;|&&)\s*claude(\s.*)?$', re.I)


def default_history():
    try:
        out = subprocess.run(['pwsh', '-NoProfile', '-Command', '(Get-PSReadLineOption).HistorySavePath'],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        if out: return out
    except Exception: pass
    if os.name == 'nt':
        return os.path.join(os.environ.get('APPDATA', ''), 'Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt')
    return os.path.expanduser('~/.local/share/powershell/PSReadLine/ConsoleHost_history.txt')


def parse(line):
    """-> (folder, args) or None."""
    m = CMD.match(line)
    if not m: return None
    f = m.group(1).strip()
    if len(f) > 1 and f[0] == f[-1] and f[0] in '"\'': f = f[1:-1]
    f = os.path.expanduser(f)
    if not os.path.isabs(f): return None
    return f, (m.group(2) or '').rstrip()


def top(history, n=4):
    """Most repeated commands whose folder exists, as ready-to-use lines (+ counts)."""
    count, first = collections.Counter(), {}
    with open(history, encoding='utf-8-sig', errors='replace') as fh:
        for raw in fh:
            p = parse(raw)
            if p and os.path.isdir(p[0]):
                key = (os.path.normcase(os.path.normpath(p[0])), p[1])
                count[key] += 1
                first.setdefault(key, p)
    return [(line(*first[k]), c) for k, c in count.most_common(n)]


def line(folder, args=''):
    return 'cd "%s"; claude%s' % (os.path.normpath(folder).replace('\\', '/'), args)


def test():
    d = tempfile.mkdtemp(prefix='fav_detect_')
    dirs = {x: os.path.join(d, x, 'with space' if x == 'A' else x) for x in 'ABCDE'}
    for p in dirs.values(): os.makedirs(p)
    miss = os.path.join(d, 'gone')
    A, B, C, D, E = (dirs[x] for x in 'ABCDE')
    h = os.path.join(d, 'h.txt')
    lines = ([f'cd "{A}"; claude'] * 3 + [f"Set-Location '{A}'; claude", f'cd {A} && claude'] +      # variants of A: 5
             [f'cd {B}; claude'] * 4 + [f'sl -Path "{C}" ; claude --resume'] * 3 + [f'cd "{D}"; claude'] * 2 +
             [f'cd "{E}"; claude'] + [f'cd "{miss}"; claude'] * 9 + ['cd relative; claude', 'ls', 'claude', 'cd ~; ls'])
    open(h, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    got = top(h)
    assert [c for _, c in got] == [5, 4, 3, 2], got
    assert got[0][0] == line(A) and got[1][0] == line(B) and got[2][0] == line(C, ' --resume'), got
    assert not any('gone' in g for g, _ in got) and not any(g.endswith('E"; claude') for g, _ in got), got
    assert len(top(h, 2)) == 2
    open(h, 'w').write('')
    assert top(h) == []                                    # empty history -> empty list (fallback: ask)
    open(h, 'w').write(f'cd "{miss}"; claude\nls\n')
    assert top(h) == []                                    # only missing folders
    assert parse('cd ~; claude')[0] == os.path.expanduser('~')
    print('ok')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--history'); ap.add_argument('-n', type=int, default=4)
    ap.add_argument('--folders', nargs='*'); ap.add_argument('--write', nargs='?', const=True)
    ap.add_argument('--test', action='store_true')
    a = ap.parse_args()
    if a.test: test(); sys.exit(0)
    if a.folders is not None:
        bad = [f for f in a.folders if not os.path.isdir(os.path.expanduser(f))]
        if bad: sys.exit('Folders that do not exist: %s' % bad)
        res = [line(os.path.abspath(os.path.expanduser(f))) for f in a.folders]
    else:
        h = a.history or default_history()
        if not os.path.isfile(h): sys.exit('No history file at %s: ask the person which folders they want (--folders).' % h)
        top_ = top(h, a.n)
        if not top_: sys.exit('Nothing useful in %s: ask the person which folders they want (--folders).' % h)
        res = [l for l, _ in top_]
        for l, c in top_: print('%3dx  %s' % (c, l))
    if a.folders is not None:
        for l in res: print(l)
    if a.write:
        out = a.write if isinstance(a.write, str) else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'favoritos.txt')
        open(out, 'w', encoding='utf-8').write('\n'.join(res) + '\n')
        print('written:', out)
    else:
        print('(nothing written: show this to the person, wait for their OK, then repeat with --write)')
