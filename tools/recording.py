"""Match recordings: how many are kept and how long each may get (the Observer's Recording settings, saved in
user/recording.json: updates and Repair keep the user folder, like user/mcc_folder.txt).

- Games kept (default 5): when a match starts (tools/play.py), the oldest matches not saved are removed so that with
  the new one there are that many. A match is every file in logs/ with its stamp: trace_<map>_<stamp>.jsonl and its
  .carnage.xml, collect_<map>_<stamp>.jsonl (the Data collector), critique_<map>_<stamp>.jsonl / .md. Saved matches
  are never removed: kept in the Observer (logs/saved_games.json), exported (logs/exports/match_<map>_<stamp>.zip) or
  with bug reports (logs/bug_reports/<map>_<stamp>/). Imported games (logs/imported), logs/evidence, hand-named traces
  and the analyses (fluidity_*, human_*) are not in the queue.
- Longest recording (default 15 minutes): a longer match keeps its last that many minutes, trimmed on disk while it is
  played (RollingFile; nothing is held in memory). The header lines (each bot's meta, the Scaling rating, the
  collector's start) are always kept. A bug report keeps its own copy (tools/bug_reports.py catch_up).
- A developer's checkout (a .git folder beside tools/): only matches recorded after the first run here are rotated
  ("since" in the settings file), so the recordings already in logs/ stay.
- Every copy of the mod (an install, a working repo) adds itself to %LOCALAPPDATA%\\ProjectProvingGrounds\\copies.json
  when it records a match or opens the Observer; the Observer lists the other copies' games too (register, other_logs).

    python -I recording.py        self-check: rotation and the time window ("recording OK")
"""
import glob
import json
import os
import re
import shutil
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
LOGS = os.path.join(ROOT, "logs")
SETTINGS = os.path.join(ROOT, "user", "recording.json")
# every copy of the mod that recorded games or opened the Observer here (the install, a working repo): one per-user
# list, like the films (native/botcore.cpp film_dir)
COPIES = os.path.join(os.environ["LOCALAPPDATA"], "ProjectProvingGrounds", "copies.json") \
    if os.environ.get("LOCALAPPDATA") else None
DEFAULTS = dict(games=5, minutes=15)
LIMITS = dict(games=(2, 50), minutes=(1, 600))     # (2 games at least: Scaling reads the last match back at the next)
PART = re.compile(r"^(?:trace|collect|critique)_.+_(\d{8}-\d{6})(?:\.carnage\.xml|\.jsonl|\.md)$")
T_AT = re.compile(rb'\{"t": (-?[0-9.eE+-]+)[,}]')
HEADS = (b'"meta": ', b'"scaling": ', b'"collect": "start"')


# ---------------------------------------------------------------- settings

def _raw(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def settings(path=SETTINGS):
    """{"games", "minutes", ...}: the saved choice within LIMITS, else the defaults."""
    d = _raw(path)
    for k, (lo, hi) in LIMITS.items():
        try:
            d[k] = max(lo, min(hi, int(d.get(k, DEFAULTS[k]))))
        except (TypeError, ValueError):
            d[k] = DEFAULTS[k]
    return d


def save_settings(new, path=SETTINGS):
    """Saves games / minutes from new (other keys in the file kept); returns settings()."""
    d = _raw(path)
    d.update({k: new[k] for k in LIMITS if k in new})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(d, open(path, "w", encoding="utf-8"), indent=1)
    return settings(path)


def since(path=SETTINGS, root=ROOT):
    """A developer's checkout: the stamp of the first run here (matches before it are never rotated), else None."""
    if not os.path.isdir(os.path.join(root, ".git")):
        return None
    d = _raw(path)
    if not d.get("since"):
        d["since"] = time.strftime("%Y%m%d-%H%M%S")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(d, open(path, "w", encoding="utf-8"), indent=1)
    return d["since"]


# ---------------------------------------------------------------- saved games and the queue

def stamp_of(path):
    m = PART.match(os.path.basename(path))
    return m.group(1) if m else None


def saved(logs=LOGS):
    """Stamps of the saved matches: kept in the Observer, exported, or with bug reports."""
    out = {s for s in _raw_list(os.path.join(logs, "saved_games.json"))}
    out |= {m.group(1) for p in glob.glob(os.path.join(logs, "exports", "*.zip"))
            for m in [re.search(r"_(\d{8}-\d{6})(?:_names)?\.zip$", p)] if m}
    out |= {m.group(1) for p in glob.glob(os.path.join(logs, "bug_reports", "*"))
            for m in [re.search(r"_(\d{8}-\d{6})$", p)] if m and os.path.isdir(p)}
    return out


def _raw_list(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        return [str(x) for x in d] if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def keep(stamp, on=True, logs=LOGS):
    """The Observer's Keep game: the match is saved (on) or back in the queue."""
    path = os.path.join(logs, "saved_games.json")
    have = set(_raw_list(path))
    have = have | {stamp} if on else have - {stamp}
    os.makedirs(logs, exist_ok=True)
    json.dump(sorted(have), open(path, "w", encoding="utf-8"), indent=1)


def rotate(logs=LOGS, games=None, after=None):
    """Before a new match: the oldest matches not saved removed so that games - 1 are left (the new one makes games).
    after: only stamps from then on are in the queue (a developer's checkout, since()). Returns the stamps removed."""
    games = settings()["games"] if games is None else games
    for left in glob.glob(os.path.join(logs, "*.trim")):        # a trim the brain was stopped in (RollingFile)
        try:
            os.remove(left)
        except OSError:
            pass
    parts = {}
    for p in glob.glob(os.path.join(logs, "*")):
        s = stamp_of(p)
        if s and os.path.isfile(p):
            parts.setdefault(s, []).append(p)
    if os.path.normcase(os.path.normpath(logs)) == os.path.normcase(LOGS):
        register()                  # (tools/play.py rotates before each recorded match: this copy records games)
    keepers = saved(logs)
    queue = sorted(s for s in parts if s not in keepers and (after is None or s >= after))
    gone = queue[:max(0, len(queue) - (games - 1))]
    for s in gone:
        for p in parts[s]:
            try:
                os.remove(p)
            except OSError:
                pass                # open in the Observer this second: it goes with the next match
    return gone


# ---------------------------------------------------------------- every copy of the mod on this PC

def register(root=ROOT, path=None):
    """This copy of the mod in the per-user list (COPIES), so the Observer of every other copy lists its games too:
    the BOTS panel's brain runs from the copy whose botcore.dll is in MCC, which need not be the copy whose Observer
    is open (Nov 4: an install listed nothing while its games went to the working repo's logs)."""
    path = path or COPIES
    if not path:
        return
    have = _raw_list(path)
    key = os.path.normcase(os.path.normpath(root))
    if key not in {os.path.normcase(os.path.normpath(r)) for r in have}:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(have + [os.path.normpath(root)], open(path, "w", encoding="utf-8"), indent=1)
        except OSError:
            pass


def other_logs(logs=LOGS, path=None):
    """The logs folders of the other copies in the per-user list that are still there (not logs itself)."""
    mine, out = os.path.normcase(os.path.normpath(logs)), []
    for r in _raw_list(path or COPIES) if (path or COPIES) else []:
        d = os.path.normpath(os.path.join(r, "logs"))
        if os.path.normcase(d) != mine and os.path.isdir(d) and d not in out:
            out.append(d)
    return out


# ---------------------------------------------------------------- the time window

def line_t(line):
    m = T_AT.match(line)
    return float(m.group(1)) if m else None


def _line_from(f, pos, end):
    """(start, t) of the first line with a time that starts at or after pos, else (end, inf)."""
    f.seek(max(0, pos - 1))
    if pos > 0 and f.read(1) != b"\n":
        f.readline()                                 # (pos was inside a line)
    while f.tell() < end:
        start = f.tell()
        t = line_t(f.readline())
        if t is not None:
            return start, t
    return end, float("inf")


def first_at(f, lo, end, cutoff):
    """Offset of the first line in [lo, end) with t >= cutoff (rows are in time order: halving, then a short walk)."""
    a, b = lo, end
    while b - a > 1 << 16:
        mid = (a + b) // 2
        if _line_from(f, mid, end)[1] < cutoff:
            a = mid
        else:
            b = mid
    start, t = _line_from(f, a, end)
    while t < cutoff and start < end:
        start, t = _line_from(f, start + 1, end)
    return start


def header_lines(f, lo, hi):
    """The header lines (meta, Scaling rating, collector start) in [lo, hi), as bytes."""
    out, pos, rest = [], lo, b""
    f.seek(lo)
    while pos < hi:
        chunk = rest + f.read(min(4 << 20, hi - pos))
        pos = f.tell()
        cut = chunk.rfind(b"\n") + 1 if pos < hi else len(chunk)     # whole lines; the rest goes with the next
        chunk, rest = chunk[:cut], chunk[cut:]
        found = {}                                                     # line start -> line, in this chunk
        for h in HEADS:
            i = chunk.find(h)
            while i >= 0:
                s = chunk.rfind(b"\n", 0, i) + 1
                e = chunk.find(b"\n", i)
                e = len(chunk) if e < 0 else e + 1
                found[s] = chunk[s:e]
                i = chunk.find(h, e)
        for s in sorted(found):
            try:
                d = json.loads(found[s])
            except ValueError:
                continue
            if isinstance(d, dict) and ("meta" in d or "scaling" in d or d.get("collect") == "start"):
                out.append(found[s])
    return b"".join(out)


class RollingFile:
    """A recording that keeps its last `seconds` of rows (by their "t", the brain's clock) and its header lines. Once
    the file holds a slack (a third of the window, a minute at least) more than the window, a thread copies the part
    kept into <path>.trim and the writer swaps it in at its next tick (the few rows written meanwhile copied first).
    seconds None: a plain file. Same calls as a file: write, flush, close; tick(now) once a pass."""
    def __init__(s, path, seconds=None, encoding=None):
        s.path, s.seconds, s.enc = path, seconds, encoding
        s.slack = max(60.0, seconds / 3) if seconds else None
        s.f = open(path, "w", encoding=encoding)
        s.head, s.due = 0, (seconds + s.slack) if seconds else float("inf")
        s.job, s.done, s.tries = None, None, 0

    def write(s, text):
        return s.f.write(text)

    def writelines(s, lines):        # (live_bots writes the callouts this way: without it a traced brain stopped at once)
        s.f.writelines(lines)

    def flush(s):
        s.f.flush()

    def tick(s, now):
        if s.job is None and now >= s.due:
            s.f.flush()
            try:
                end, cutoff = os.path.getsize(s.path), now - s.seconds
            except OSError:
                return
            s.done, s.due = None, now + s.slack
            s.job = threading.Thread(target=s._copy, args=(end, cutoff), daemon=True)
            s.job.start()
        elif s.job is not None and not s.job.is_alive():
            s._swap()

    def _copy(s, end, cutoff):
        try:
            with open(s.path, "rb") as f, open(s.path + ".trim", "wb") as g:
                head = f.read(s.head)
                cut = first_at(f, s.head, end, cutoff)
                head += header_lines(f, s.head, cut)
                g.write(head)
                f.seek(cut)
                left = end - cut
                while left > 0:
                    b = f.read(min(1 << 20, left))
                    if not b:
                        break
                    g.write(b)
                    left -= len(b)
            s.done = (len(head), end)
        except OSError:
            s.done = None

    def _swap(s):
        """Between two writes: the rows written since the copy appended to it, then it replaces the recording (the
        Observer reading the file this instant: tried again at the next tick, ten times)."""
        tmp = s.path + ".trim"
        if s.done is None:
            s.job = None
            return
        head, end = s.done
        s.f.flush()
        s.f.close()
        try:
            with open(s.path, "rb") as f, open(tmp, "ab") as g:
                f.seek(end)
                shutil.copyfileobj(f, g, 1 << 20)
                s.done = (head, f.tell())
            os.replace(tmp, s.path)
            s.head, s.job, s.tries = head, None, 0
        except OSError:
            s.tries += 1
            if s.tries >= 10:
                s.job, s.tries = None, 0
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        s.f = open(s.path, "a", encoding=s.enc)

    def close(s):
        if s.job is not None:
            s.job.join()
            s._swap()
        s.f.close()


# ---------------------------------------------------------------- self-check

def selftest():
    import tempfile
    tmp = tempfile.mkdtemp(prefix="halo_recording_")
    logs = os.path.join(tmp, "logs")
    os.makedirs(os.path.join(logs, "exports"))
    os.makedirs(os.path.join(logs, "bug_reports", "h3_construct_20261101-120004"))
    stamps = [f"20261101-1200{k:02d}" for k in range(9)]
    for s in stamps:
        for n in (f"trace_h3_construct_{s}.jsonl", f"trace_h3_construct_{s}.carnage.xml",
                  f"collect_h3_construct_{s}.jsonl"):
            open(os.path.join(logs, n), "w").close()
    for n in ("trace_h3_construct.jsonl", "fluidity_h3_construct_20261101-120000.md", "x.jsonl.trim"):
        open(os.path.join(logs, n), "w").close()
    open(os.path.join(logs, "exports", f"match_h3_construct_{stamps[1]}_names.zip"), "w").close()   # exported
    keep(stamps[2], logs=logs)                                                 # kept in the Observer
    keep(stamps[3], logs=logs)
    keep(stamps[3], False, logs=logs)                                          # and back in the queue
    gone = rotate(logs, games=5)
    # unsaved: 0, 3, 5, 6, 7, 8 -> 4 stay (the new match makes 5): 0 and 3 go; 1, 2, 4 saved
    assert gone == [stamps[0], stamps[3]], gone
    left = set(os.listdir(logs))
    assert f"collect_h3_construct_{stamps[0]}.jsonl" not in left and f"trace_h3_construct_{stamps[0]}.carnage.xml" \
        not in left, "a match's paired files stayed"
    assert {"trace_h3_construct.jsonl", "fluidity_h3_construct_20261101-120000.md"} <= left, left
    assert "x.jsonl.trim" not in left
    for s in stamps[1:3] + [stamps[4]]:
        assert f"trace_h3_construct_{s}.jsonl" in left, f"saved match {s} removed"
    # a 6th unsaved match pushes the oldest unsaved out, one at a time
    open(os.path.join(logs, "trace_h3_construct_20261101-130000.jsonl"), "w").close()
    assert rotate(logs, games=5) == [stamps[5]]
    # a developer's checkout: only matches from the first run on
    assert rotate(logs, games=2, after="20261101-120007") == [stamps[7], stamps[8]]
    # settings: defaults, limits, other keys kept
    sp = os.path.join(tmp, "user", "recording.json")
    assert settings(sp) == dict(DEFAULTS)
    assert save_settings(dict(games=99, minutes=0), sp) == dict(games=50, minutes=1)
    os.makedirs(os.path.join(tmp, ".git"))
    first = since(sp, tmp)
    assert first and since(sp, tmp) == first and save_settings(dict(games=7), sp)["since"] == first
    assert since(sp, os.path.join(tmp, "user")) is None
    # every copy of the mod: listed once, the others' logs folders found (not this one's, not a removed copy's)
    cp, other = os.path.join(tmp, "per_user", "copies.json"), os.path.join(tmp, "repo")
    os.makedirs(os.path.join(other, "logs"))
    for r in (tmp, other, other.upper() if os.name == "nt" else other, os.path.join(tmp, "gone")):
        register(r, cp)
    assert len(_raw_list(cp)) == 3, _raw_list(cp)
    assert other_logs(logs, cp) == [os.path.join(other, "logs")], other_logs(logs, cp)
    # the time window: 10 s kept of 40 s at 10 rows a second, header lines kept, the rows in order, whole lines
    path = os.path.join(tmp, "trace_h3_construct_20261101-140000.jsonl")
    r = RollingFile(path, 10.0)
    r.slack = 5.0
    r.due = 15.0
    r.write(json.dumps(dict(t=0.0, scaling=1.5)) + "\n")
    sizes = []
    for k in range(400):
        now = k / 10
        if k == 30:
            r.write(json.dumps(dict(t=now, meta=dict(map="h3_construct", bot=dict(id=9)))) + "\n")
        r.write(json.dumps(dict(t=now, id=9, pos=[k, 0, 0], note="meta")) + "\n")
        r.tick(now)
        if r.job is not None:
            r.job.join()
            r.write(json.dumps(dict(t=now, id=9, pos=[k, 1, 0])) + "\n")   # written while the copy ran
            r.tick(now)                               # the swap
        r.flush()
        sizes.append(os.path.getsize(path))
    r.close()
    rows = [json.loads(x) for x in open(path)]
    assert rows[0] == dict(t=0.0, scaling=1.5) and "meta" in rows[1], rows[:2]
    body = [x["t"] for x in rows if "pos" in x]
    assert body == sorted(body) and body[-1] == 39.9, body[-3:]
    assert sum(x.get("pos", [0, 0])[1] == 1 for x in rows) >= 2, "rows written during a trim were lost"
    assert 10.0 <= body[-1] - body[0] <= 15.0 + 0.1, (body[0], body[-1])            # the window, plus its slack
    assert max(sizes) < 2.2 * min(s for s in sizes[200:]), (max(sizes), sizes[200:210])   # bounded while recording
    assert not os.path.exists(path + ".trim")
    # a plain file when there is no limit
    p2 = os.path.join(tmp, "plain.jsonl")
    r = RollingFile(p2)
    for k in range(100):
        r.write(json.dumps(dict(t=k * 10.0)) + "\n")
        r.tick(k * 10.0)
    r.close()
    assert len(open(p2).readlines()) == 100
    shutil.rmtree(tmp, ignore_errors=True)
    print("recording OK")


if __name__ == "__main__":
    selftest()
