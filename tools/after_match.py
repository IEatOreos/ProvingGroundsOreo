"""As a recorded match ends: what tools/play.py does when the NEXT match starts, done now (custom, Nov 15), so the last
match of an evening is in the career totals and on the Service Record without starting another one.

tools/live_bots.py starts this in the background as the brain stops. play.py cannot do it: botcore stops play.py the
moment a match ends, while the brain ends on its own a few seconds later, after MCC has written its report (live, three
matches of Nov 15: the report 14 to 17 s before the recording's last line). In play.py's order:

  1. MCC's post-game report beside the match's recording, as <trace>.carnage.xml (play.keep_carnage: its own rule,
     asked about this match's recording only, so a match already started after it is never given the report)
  2. tools/bot_career.py        the ledger and the totals
  3. tools/service_record.py    the site, with this match's map, medals and kill rows

A match with no report (quit before the end) gets nothing done. The next match's start finds the report kept and the
match counted, and repeats nothing.

usage: python -I after_match.py <trace file> [--wait S]     S: seconds to wait for MCC's report (default 20)
       python -I after_match.py                             self-check ("after match OK")
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import play  # noqa: E402  (keep_carnage and where MCC writes its report)

STEPS = (("bot_career.py", ["--quiet"]), ("service_record.py", ["--quiet", "--wait-ledger", "30"]))


def finish(trace, wait=20.0, run=subprocess.run, sleep=time.sleep):
    """The report's copy beside this match's recording, then the totals and the site. Returns the copy's path, or None
    when there was nothing to do: no report of this match within `wait` seconds, or one kept already."""
    kept = trace[:-len(".jsonl")] + ".carnage.xml"
    end = time.time() + wait
    while True:
        dest = play.keep_carnage([trace]) if os.path.exists(trace) and not os.path.exists(kept) else None
        if dest or os.path.exists(kept) or not os.path.exists(trace) or time.time() >= end:
            break
        sleep(1.0)
    if not dest:
        return None
    for script, args in STEPS:              # one after the other: the site reads the ledger the first one writes
        run([sys.executable, "-I", os.path.join(HERE, script), *args],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return dest


def selftest():
    import tempfile
    real = play.CARNAGE
    try:
        with tempfile.TemporaryDirectory() as tmp:
            play.CARNAGE = os.path.join(tmp, "mcc_report.xml")
            ran = []
            run = lambda cmd, **kw: ran.append([os.path.basename(cmd[2])] + cmd[3:])      # noqa: E731
            trace = os.path.join(tmp, "trace_reach_70_boneyard_20261115-190000.jsonl")
            open(trace, "w").close()
            now = time.time()
            # no report at all, then one from a match minutes before this one: nothing is done
            assert finish(trace, wait=0, run=run) is None and ran == []
            with open(play.CARNAGE, "w") as f:
                f.write("<report/>")
            os.utime(play.CARNAGE, (now - 400, now - 400))
            os.utime(trace, (now, now))
            assert finish(trace, wait=0, run=run) is None and ran == [], ran
            # this match's report, written 15 s before the recording's last line: kept, then the totals, then the site
            os.utime(play.CARNAGE, (now - 15, now - 15))
            dest = finish(trace, wait=0, run=run)
            assert dest == trace[:-len(".jsonl")] + ".carnage.xml" and open(dest).read() == "<report/>", dest
            assert ran == [["bot_career.py", "--quiet"], ["service_record.py", "--quiet", "--wait-ledger", "30"]], ran
            # kept already (the next match's start, or this run twice): nothing again
            assert finish(trace, wait=0, run=run) is None and len(ran) == 2
            # a report MCC writes a moment late is waited for
            late = os.path.join(tmp, "trace_reach_70_boneyard_20261115-191500.jsonl")
            open(late, "w").close()
            os.utime(late, (now + 300, now + 300))

            def write_late(_):
                os.utime(play.CARNAGE, (now + 310, now + 310))
            assert finish(late, wait=30, run=run, sleep=write_late) and len(ran) == 4, ran
            # a recording that is gone: nothing, and no wait
            assert finish(os.path.join(tmp, "trace_gone_20261115-200000.jsonl"), wait=30, run=run, sleep=None) is None
    finally:
        play.CARNAGE = real
    print("after match OK")


def main(argv):
    if not argv:
        selftest()
        return 0
    wait = float(argv[argv.index("--wait") + 1]) if "--wait" in argv else 20.0
    finish(os.path.abspath(argv[0]), wait)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
