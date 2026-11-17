"""The Service Record's editor (custom, Nov 16; the owner: "Allow me to be the only one to edit the site from my end.
Like an edit mode", "Let me edit the clan Names whenever I want"). Serves the built site (logs/service_record) like a
plain web server, and is the one way to change what the owner may edit: today the clans' full names and short descriptions, and a bot's clan tag (written to bot_profiles.ini, the game's own, only while MCC is closed)
(native/bin/service_record/clan_names.json, clan_about.json: service_record.py save_clan_name, save_clan_about), the site rebuilt after each change.

Only the owner can edit: it listens on this PC alone (127.0.0.1), and a save must come from the site itself on this
PC (its Origin), carry the edit header (a page on any other site cannot send one without asking first, and is never
answered) and be small and well formed. The site opened from its folder, or any copy of it elsewhere, has no editor
behind it: there it is read-only.

usage: python -I service_record_edit.py [--port 8766]
"""
import json
import os
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import service_record as sr  # noqa: E402

HEADER = "X-Service-Record-Edit"
MAX_BODY = 2048


def allowed_origin(origin, port):
    """Whether a request's Origin is the site on this PC (or absent: the browser sends one on every POST it makes)."""
    return origin in (None, f"http://localhost:{port}", f"http://127.0.0.1:{port}")


class Handler(SimpleHTTPRequestHandler):
    paths = None
    port = 8766

    def log_message(self, fmt, *args):         # (quiet: the console shows edits only)
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def reply(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def local(self):
        return self.client_address[0] in ("127.0.0.1", "::1")

    def do_GET(self):
        if self.path == "/api/editor":
            return self.reply(200, {"edit": True}) if self.local() else self.reply(403, {"error": "not this PC"})
        return super().do_GET()

    def do_POST(self):
        if not self.local() or not allowed_origin(self.headers.get("Origin"), self.port) or self.headers.get(HEADER) != "1":
            return self.reply(403, {"error": "edits come from the site on this PC only"})
        if self.path == "/api/bot-clan":
            return self.bot_clan()
        edits = {"/api/clan-name": ("name", sr.save_clan_name), "/api/clan-about": ("about", sr.save_clan_about)}
        if self.path not in edits:
            return self.reply(404, {"error": "no such edit"})
        field, save = edits[self.path]
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY or "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("bad request")
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            kept = save(self.paths, data.get("key", ""), data.get(field, ""))
        except (ValueError, UnicodeDecodeError, AttributeError) as e:
            return self.reply(400, {"error": str(e) or "bad request"})
        key = sr.clan_key(data.get("key", ""))
        print(f"clan {field}: {key} -> {kept.get(key, '(cleared)')!r}", flush=True)
        rebuild()
        return self.reply(200, {"key": key, field: kept.get(key, "")})


    def bot_clan(self):
        """A bot's clan tag, written where the game reads it (service_record.py set_bot_clan): only while MCC is
        closed, and only for a bot the site lists."""
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY or "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("bad request")
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            name = data.get("name", "")
            if not isinstance(name, str) or name not in listed_bots(self.paths):
                raise ValueError("not a bot on the site")
            clan = sr.set_bot_clan(self.paths, name, data.get("clan", ""))
        except PermissionError as e:
            return self.reply(409, {"error": str(e)})
        except (ValueError, UnicodeDecodeError, AttributeError, OSError) as e:
            return self.reply(400, {"error": str(e) or "bad request"})
        print(f"bot clan: {name} -> {clan or '(no clan)'}", flush=True)
        rebuild()
        return self.reply(200, {"name": name, "clan": clan})


def listed_bots(paths):
    """The names the built site lists (its data.js): the only bots the editor will touch."""
    try:
        with open(os.path.join(paths.out, "data.js"), encoding="utf-8") as f:
            text = f.read()
        return {p["name"] for p in json.loads(text[text.index("{"):text.rindex("}") + 1])["players"]}
    except (OSError, ValueError, KeyError):
        return set()


def rebuild():
    """The site built again so the change shows (the open page reloads on the new build's stamp)."""
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "service_record.py"), "--quiet"], timeout=600,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def main(argv):
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8766
    paths = sr.Paths()
    if not os.path.exists(os.path.join(paths.out, "index.html")):
        rebuild()
    Handler.paths, Handler.port = paths, port
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=paths.out))
    print(f"Service Record editor: http://localhost:{port}/  (this PC only; Ctrl+C stops it)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
