"""(Nov 18) A bot's difficulty set on the Service Record site: service_record.py set_bot_difficulty (bot_pool_saved.ini's
saved= line as the BOTS panel writes it, its style kept, Demon never Wheelman, the lobby list's bot=/ffbot= tier, ""
its saved line out, the rest of both files as they were, refused while MCC runs) and the editor's /api/bot-difficulty
route (403 without the edit header, 400 for a bad difficulty or a name the site does not list, 409 while MCC runs).
Only made-up copies of the files are touched.

usage: python -I tools/test_bot_difficulty.py
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

POOL = sr.POOL_HEADER + "next4=12\r\nnext8=0\r\nsalt=7\r\nsaved=demon,objector,Wheezy\r\nsaved=blind,wheelman,Lone Fox\r\n"
POOL = POOL.replace("\r\n", "\n").replace("\n", "\r\n")
BOTCORE = "roster=1\r\nteams=2\r\nbot=1,top,wheelman,Lone Fox\r\nbot=0,novice,any,Girthquake\r\nffbot=0,strong,any,lone fox\r\nother=5\r\n"


def setup(tmp):
    paths = sr.Paths(out=os.path.join(tmp, "site"), store=tmp, pool=os.path.join(tmp, "bot_pool_saved.ini"),
                     botcore=os.path.join(tmp, "botcore.ini"))
    for p, text in ((paths.pool, POOL), (paths.botcore, BOTCORE)):
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    return paths


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def test_set():
    with tempfile.TemporaryDirectory() as tmp:
        paths = setup(tmp)
        try:
            sr.set_bot_difficulty(paths, "Lone Fox", "demon", running=True)
            raise AssertionError("written while MCC runs")
        except PermissionError:
            pass
        assert read(paths.pool) == POOL and read(paths.botcore) == BOTCORE
        for name, tier in (("Lone Fox", "hard"), ("Lone,Fox", "top"), ("x" * 16, "top"), ("", "top")):
            try:
                sr.set_bot_difficulty(paths, name, tier, running=False)
                raise AssertionError((name, tier))
            except ValueError:
                pass
        # an existing line: the difficulty changed, its style kept unless Demon would drive (then any); the lobby list too
        assert sr.set_bot_difficulty(paths, "lone fox", "demon", running=False) == "demon"
        assert read(paths.pool) == POOL.replace("saved=blind,wheelman,Lone Fox", "saved=demon,any,lone fox")
        assert read(paths.botcore) == BOTCORE.replace("bot=1,top,wheelman,Lone Fox", "bot=1,demon,any,Lone Fox") \
            .replace("ffbot=0,strong,any,lone fox", "ffbot=0,demon,any,lone fox")
        assert os.path.exists(paths.pool + ".before_site_edit") and os.path.exists(paths.botcore + ".before_site_edit")
        assert sr.read_pool(paths.pool)["lone fox"] == ("demon", "any")
        # a bot with no line gets one at the end (any style); one not on the lobby list leaves botcore.ini alone
        before = read(paths.botcore)
        assert sr.set_bot_difficulty(paths, "New Bot", "mythic", running=False) == "mythic"
        assert read(paths.pool).endswith("saved=mythic,any,New Bot\r\n") and read(paths.botcore) == before
        # "": the saved line out, the lobby list left
        assert sr.set_bot_difficulty(paths, "Wheezy", "", running=False) == ""
        assert "Wheezy" not in read(paths.pool) and read(paths.pool).startswith(sr.POOL_HEADER.replace("\n", "\r\n") + "next4=12\r\n")
        assert sr.read_pool(paths.pool) == {"lone fox": ("demon", "any"), "New Bot": ("mythic", "any")}


def test_route():
    keep = ed.rebuild, sr.mcc_running
    with tempfile.TemporaryDirectory() as tmp:
        paths = setup(tmp)
        os.makedirs(paths.out)
        with open(os.path.join(paths.out, "data.js"), "w", encoding="utf-8") as f:
            f.write("window.SR_DATA = " + json.dumps({"players": [{"name": "Wheezy"}, {"name": "Me", "person": True}]}) + ";\n")
        running = [True]
        ed.rebuild, sr.mcc_running = (lambda: None), (lambda: running[0])
        ed.Handler.paths = paths
        server = ed.ThreadingHTTPServer(("127.0.0.1", 0), partial(ed.Handler, directory=paths.out))
        port = server.server_address[1]
        ed.Handler.port = port
        threading.Thread(target=server.serve_forever, daemon=True).start()

        def call(body, header=True):
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
            h = {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"}
            if header:
                h["X-Service-Record-Edit"] = "1"
            c.request("POST", "/api/bot-difficulty", json.dumps(body), h)
            r = c.getresponse()
            d = json.loads(r.read())
            c.close()
            return r.status, d
        try:
            assert call({"name": "Wheezy", "difficulty": "top"}, header=False)[0] == 403
            assert call({"name": "Me", "difficulty": "top"})[0] == 400          # (a person: not a bot)
            assert call({"name": "Nobody", "difficulty": "top"})[0] == 400
            assert call({"name": "Wheezy", "difficulty": "hard"})[0] == 400
            assert call({"name": "Wheezy", "difficulty": "top"})[0] == 409      # (MCC runs)
            assert read(paths.pool) == POOL
            running[0] = False
            assert call({"name": "Wheezy", "difficulty": "top"}) == (200, {"name": "Wheezy", "difficulty": "top"})
            assert sr.read_pool(paths.pool)["Wheezy"] == ("top", "objector")
            assert call({"name": "Wheezy", "difficulty": ""}) == (200, {"name": "Wheezy", "difficulty": ""})
            assert "Wheezy" not in sr.read_pool(paths.pool)
        finally:
            server.shutdown()
            server.server_close()
            ed.rebuild, sr.mcc_running = keep


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")
