"""(Nov 18) The bots' emblem editor: brain/emblems.py's saved picks (emblem_for, save_chosen, valid; export and
brain/looks.py emblem_of use them) and the Service Record editor's emblem routes (tools/service_record_edit.py):
save, back to the roll, bad ids, a bot the site does not list, a request without the edit header, the catalog, a
layer's art only by the catalog's names.

usage: python -I tools/test_bot_emblem.py
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
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))
from brain import emblems, looks  # noqa: E402
import service_record_edit as ed  # noqa: E402


def a_pick():
    fgs, bgs, cols = emblems.catalog()
    ids = sorted(cols)
    return {"fg": fgs[3][0], "bg": bgs[5][0], "primary": ids[0], "secondary": emblems.OFF, "background": ids[-1]}


def test_picks():
    """A saved pick is the bot's emblem (any case of its name), everywhere the roll was; reset brings the roll back;
    an emblem MCC does not have is refused and a bad saved entry is left out."""
    keep = emblems.OUT
    with tempfile.TemporaryDirectory() as tmp:
        emblems.OUT = tmp
        try:
            seed = looks.seed_of("Test Bot")
            assert emblems.emblem_for("Test Bot", seed) == emblems.roll(seed) and emblems.chosen() == {}
            pick = a_pick()
            emblems.save_chosen("Test Bot", pick)
            assert emblems.emblem_for("Test Bot", seed) == pick and emblems.emblem_for("test bot", seed) == pick
            assert looks.emblem_of("Test Bot") == emblems.ids(pick)
            emblems.export([("Test Bot", seed)])
            with open(os.path.join(tmp, "Test Bot.ids"), encoding="utf-8") as f:
                assert f.read().split() == [str(v) for v in emblems.ids(pick)]
            fgs, bgs, cols = emblems.catalog()
            for bad in ({**pick, "fg": -5}, {**pick, "bg": fgs[0][0] * 0 - 1}, {**pick, "primary": emblems.OFF},
                        {**pick, "background": 999}, {**pick, "secondary": True}, {k: pick[k] for k in ("fg", "bg")}, None):
                assert not emblems.valid(bad), bad
                if bad is not None:
                    try:
                        emblems.save_chosen("Test Bot", bad)
                        raise AssertionError(bad)
                    except ValueError:
                        pass
            assert emblems.chosen() == {"Test Bot": pick}
            with open(emblems.chosen_path(), "w", encoding="utf-8") as f:
                json.dump({"Test Bot": pick, "Broken": {"fg": 1}}, f)
            assert emblems.chosen() == {"Test Bot": pick}
            emblems.save_chosen("Test Bot", None)
            assert emblems.emblem_for("Test Bot", seed) == emblems.roll(seed) and emblems.chosen() == {}
        finally:
            emblems.OUT = keep


def test_editor_routes():
    """The editor's emblem routes on a made-up site that lists one bot (and one person)."""
    keep_out, keep_rebuild = emblems.OUT, ed.rebuild
    with tempfile.TemporaryDirectory() as tmp:
        site, store = os.path.join(tmp, "site"), os.path.join(tmp, "emblems")
        os.makedirs(site)
        with open(os.path.join(site, "data.js"), "w", encoding="utf-8") as f:
            f.write("window.SR_DATA = " + json.dumps({"players": [{"name": "Test Bot"}, {"name": "Me", "person": True}]}) + ";\n")
        emblems.OUT, ed.rebuild = store, (lambda: None)
        ed.Handler.paths = ed.sr.Paths(out=site, store=os.path.join(tmp, "store"))
        server = ed.ThreadingHTTPServer(("127.0.0.1", 0), partial(ed.Handler, directory=site))
        port = server.server_address[1]
        ed.Handler.port = port
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def call(method, path, body=None, header=True):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
            h = {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"}
            if header:
                h["X-Service-Record-Edit"] = "1"
            c.request(method, path, json.dumps(body) if body is not None else None, h)
            r = c.getresponse()
            data = r.read()
            c.close()
            return r.status, (json.loads(data) if r.getheader("Content-Type", "").startswith("application/json") else data)
        try:
            pick = a_pick()
            st, d = call("GET", "/api/emblem-catalog")
            assert st == 200 and len(d["fg"]) == len(emblems.catalog()[0]) and d["off"] == emblems.OFF and "31" not in d["colours"]
            assert call("GET", "/api/emblem-art/..%2F..%2Fsecret.png")[0] == 404 and call("GET", "/api/emblem-art/nope.png")[0] == 404
            if d["art"]:
                st, png = call("GET", f"/api/emblem-art/{d['fg'][0][1]}.png")
                assert st == 200 and png[:8] == b"\x89PNG\r\n\x1a\n"
            st, js = call("GET", "/api/emblem-editor.js")
            assert st == 200 and b"SREmblemEditor" in js
            st, d = call("GET", "/api/bot-emblem?name=Test%20Bot")
            assert st == 200 and d["custom"] is False and d["emblem"] == d["rolled"] == emblems.roll(looks.seed_of("Test Bot"))
            assert call("GET", "/api/bot-emblem?name=Me")[0] == 400               # (a person: their own, in the game)
            assert call("POST", "/api/bot-emblem", {"name": "Test Bot", **pick}, header=False)[0] == 403
            assert call("POST", "/api/bot-emblem", {"name": "Nobody", **pick})[0] == 400
            assert call("POST", "/api/bot-emblem", {"name": "Test Bot", **pick, "fg": 99999})[0] == 400
            assert emblems.chosen() == {}
            st, d = call("POST", "/api/bot-emblem", {"name": "Test Bot", **pick})
            assert st == 200 and d["custom"] is True and d["emblem"] == pick and emblems.chosen() == {"Test Bot": pick}
            with open(os.path.join(store, "Test Bot.ids"), encoding="utf-8") as f:
                assert f.read().split() == [str(v) for v in emblems.ids(pick)]
            st, d = call("GET", "/api/bot-emblem?name=Test%20Bot")
            assert d["custom"] is True and d["emblem"] == pick
            st, d = call("POST", "/api/bot-emblem", {"name": "Test Bot", "reset": True})
            assert st == 200 and d["custom"] is False and emblems.chosen() == {}
            with open(os.path.join(store, "Test Bot.ids"), encoding="utf-8") as f:
                assert f.read().split() == [str(v) for v in emblems.ids(emblems.roll(looks.seed_of("Test Bot")))]
        finally:
            server.shutdown()
            server.server_close()
            emblems.OUT, ed.rebuild = keep_out, keep_rebuild


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")
