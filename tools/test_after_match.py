"""tools/after_match.py: as a recorded match ends, MCC's report is kept beside its recording by play.py's own rule, then
the career totals and the Service Record are rebuilt, in that order; nothing is done for a match with no report, for
one kept already or for a recording that is gone; a report written a moment late is waited for. And the brain starts
it as it stops."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("after_match", os.path.join(HERE, "after_match.py"))
am = importlib.util.module_from_spec(spec)
spec.loader.exec_module(am)


def test_after_match():
    am.selftest()


def test_steps_are_play_pys_own():
    """The two rebuilds are the tools play.py starts at a match's start, and both exist."""
    with open(os.path.join(HERE, "play.py"), encoding="utf-8") as f:
        play_src = f.read()
    for script, args in am.STEPS:
        assert os.path.isfile(os.path.join(HERE, script)) and f'"{script}"' in play_src, script
        assert "--quiet" in args, args


def test_the_brain_starts_it_as_it_stops():
    """tools/live_bots.py starts after_match.py with the match's recording, after the recording is closed."""
    with open(os.path.join(HERE, "live_bots.py"), encoding="utf-8") as f:
        src = f.read()
    start, close = src.index('"after_match.py"), o.trace]'), src.index("trace.close()")
    assert close < start and "finally:" in src[:close], (close, start)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")
    sys.exit(0)
