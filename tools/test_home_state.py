"""(Nov 18) Home states set by hand in edit mode: service_record.py save_home_state / load_home_states and the
Service Record editor's /api/home-state route (tools/service_record_edit.py): a bot and a person can be moved, ""
goes back to the name's pick, a state the table does not list and a name the site does not list are refused, and a
request without the edit header is refused.

usage: python -I tools/test_home_state.py
"""
import http.client
import json
import os
import sys
import tempfile
import threading
from functools import partial

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import service_record as sr  # noqa: E402
import service_record_edit as ed  # noqa: E402


def other_state(name, states):
    """A state that is not the one the name picks."""
    picked = sr.home_state(name, states)
    return next(s[0] for s in states if s[0] != picked)


def test_save():
    _, states = sr.load_states()
    with tempfile.TemporaryDirectory() as tmp:
        paths = sr.Paths(out=os.path.join(tmp, "site"), store=tmp)
        code = other_state("Test Bot", states)
        assert sr.load_home_states(paths, states) == {}
        assert sr.save_home_state(paths, "Test Bot", code) == code
        assert sr.load_home_states(paths, states) == {"Test Bot": code}
        for name, bad in (("Test Bot", "ZZ"), ("Test Bot", 5), ("", code), ("x" * 65, code)):
            try:
                sr.save_home_state(paths, name, bad)
                raise AssertionError((name, bad))
            except ValueError:
                pass
        with open(os.path.join(tmp, "home_states.json"), "w", encoding="utf-8") as f:
            json.dump({"Test Bot": code, "Broken": "ZZ", "Also": 3}, f)
        assert sr.load_home_states(paths, states) == {"Test Bot": code}
        assert sr.save_home_state(paths, "Test Bot", "") == sr.home_state("Test Bot", states)
        assert sr.load_home_states(paths, states) == {}


def test_route():
    _, states = sr.load_states()
    keep = ed.rebuild
    with tempfile.TemporaryDirectory() as tmp:
        site = os.path.join(tmp, "site")
        os.makedirs(site)
        with open(os.path.join(site, "data.js"), "w", encoding="utf-8") as f:
            f.write("window.SR_DATA = " + json.dumps({"players": [{"name": "Test Bot"}, {"name": "Me", "person": True}]}) + ";\n")
        ed.rebuild = lambda: None
        ed.Handler.paths = paths = sr.Paths(out=site, store=tmp)
        server = ed.ThreadingHTTPServer(("127.0.0.1", 0), partial(ed.Handler, directory=site))
        port = server.server_address[1]
        ed.Handler.port = port
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def call(body, header=True):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
            h = {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"}
            if header:
                h["X-Service-Record-Edit"] = "1"
            c.request("POST", "/api/home-state", json.dumps(body), h)
            r = c.getresponse()
            d = json.loads(r.read())
            c.close()
            return r.status, d
        try:
            bot, me = other_state("Test Bot", states), other_state("Me", states)
            assert call({"name": "Test Bot", "state": bot}, header=False)[0] == 403
            assert call({"name": "Nobody", "state": bot})[0] == 400
            assert call({"name": "Test Bot", "state": "ZZ"})[0] == 400
            assert sr.load_home_states(paths, states) == {}
            assert call({"name": "Test Bot", "state": bot}) == (200, {"name": "Test Bot", "state": bot, "set": True})
            assert call({"name": "Me", "state": me}) == (200, {"name": "Me", "state": me, "set": True})
            assert sr.load_home_states(paths, states) == {"Test Bot": bot, "Me": me}
            st, d = call({"name": "Test Bot", "state": ""})
            assert st == 200 and d["state"] == sr.home_state("Test Bot", states) and d["set"] is False
            assert sr.load_home_states(paths, states) == {"Me": me}
        finally:
            server.shutdown()
            server.server_close()
            ed.rebuild = keep


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")
