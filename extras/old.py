"""Old versions + a trash that empties itself, with no model tokens.
  old.py archive <file>...           copy to <its folder>/old/<name>_YYYY-MM-DD<ext> (history, kept forever)
  old.py trash <file>...             move to <its folder>/_papelera/ (recoverable until the purge)
  old.py purge <root> [--days 60]    delete files in every _papelera/ under <root> moved there more than N days ago
  old.py --test                      self-check
Run `purge` from a SessionStart hook (or the Task Scheduler) so it happens by itself. Prints nothing if nothing
was purged, so the hook adds nothing to Claude's context."""
import os, shutil, sys, time
from datetime import date

TRASH = "_papelera"


def free(path):
    """path, or 'name (2).ext', 'name (3).ext'… if it exists: never overwrite."""
    stem, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(path):
        path, i = f"{stem} ({i}){ext}", i + 1
    return path


def archive(f):
    stem, ext = os.path.splitext(os.path.basename(f))
    dest = free(os.path.join(os.path.dirname(os.path.abspath(f)), "old", f"{stem}_{date.today()}{ext}"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    (shutil.copytree if os.path.isdir(f) else shutil.copy2)(f, dest)
    return dest


def trash(f):
    dest = free(os.path.join(os.path.dirname(os.path.abspath(f)), TRASH, os.path.basename(f)))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(f, dest)
    os.utime(dest)  # mtime = day it was moved here: the purge counts from it
    return dest


def purge(root, days=60):
    limit, gone = time.time() - days * 86400, []
    for dp, dn, fn in os.walk(root):
        if os.path.basename(dp) != TRASH:
            continue
        for name in fn + dn:
            p = os.path.join(dp, name)
            if os.path.getmtime(p) < limit:
                (shutil.rmtree if os.path.isdir(p) else os.remove)(p)
                gone.append(p)
        dn[:] = []  # a folder inside the trash goes as a whole
        if not os.listdir(dp):
            os.rmdir(dp)
    return gone


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.stdout.reconfigure(encoding="utf-8")
    if a == ["--test"]:
        import tempfile
        t = tempfile.mkdtemp()
        f = os.path.join(t, "informe.md")
        open(f, "w").write("v1")
        assert archive(f).endswith(os.path.join("old", f"informe_{date.today()}.md")) and os.path.exists(f)
        assert archive(f).endswith(f"informe_{date.today()} (2).md")  # same day twice: no overwrite
        d = trash(f)
        assert not os.path.exists(f) and os.path.dirname(d).endswith(TRASH)
        open(f, "w").write("v2")
        d2 = trash(f)
        assert d2.endswith("informe (2).md")
        os.utime(d, (0, time.time() - 61 * 86400))
        assert purge(t) == [d] and os.path.exists(d2)  # only the one older than 60 days
        os.utime(d2, (0, 0))
        assert purge(t) == [d2] and not os.path.exists(os.path.join(t, TRASH))  # empty trash folder removed
        print("ok")
    elif a[:1] in (["archive"], ["trash"]) and a[1:]:
        for f in a[1:]:
            print(f"{a[0]}: {f} -> {(archive if a[0] == 'archive' else trash)(f)}")
    elif a[:1] == ["purge"] and len(a) in (2, 4) and (len(a) == 2 or a[2] == "--days"):
        for p in purge(a[1], int(a[3]) if len(a) == 4 else 60):
            print("purged (trash older than the limit):", p)
    else:
        sys.exit(__doc__)
