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
        if self.path.startswith(("/api/emblem", "/api/bot-emblem")):
            return self.emblem_get() if self.local() else self.reply(403, {"error": "not this PC"})
        return super().do_GET()

    def send_file(self, path, kind):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            return self.reply(404, {"error": "not here"})
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def emblem_get(self):
        """(Nov 18, the emblem editor) /api/emblem-editor.js: the editor's script (the site has it only here, in edit
        mode); /api/emblem-catalog: MCC's foregrounds, backgrounds and colours; /api/emblem-art/<layer>.png: a layer's
        shape, only a layer the catalog names; /api/bot-emblem?name=: a listed bot's emblem now, picked or rolled."""
        from urllib.parse import parse_qs, urlsplit
        url = urlsplit(self.path)
        try:
            emblems, looks = brain_emblems()
        except (ImportError, OSError, ValueError) as e:
            return self.reply(500, {"error": f"the emblems are not here ({e.__class__.__name__})"})
        if url.path == "/api/emblem-editor.js":
            return self.send_file(os.path.join(HERE, "service_record_site", "emblem_editor.js"), "text/javascript; charset=utf-8")
        if url.path == "/api/emblem-catalog":
            fgs, bgs, cols = emblems.catalog()
            art = os.path.isdir(emblems.ART)
            return self.reply(200, {"fg": fgs, "bg": bgs, "colours": {str(k): list(v) for k, v in sorted(cols.items())},
                                    "off": emblems.OFF, "art": art})
        if url.path.startswith("/api/emblem-art/") and url.path.endswith(".png"):
            layer = url.path[len("/api/emblem-art/"):-4]
            fgs, bgs, _ = emblems.catalog()
            if layer not in {x[1] for x in fgs} | {x[2] for x in fgs} | {x[1] for x in bgs}:
                return self.reply(404, {"error": "no such layer"})
            return self.send_file(os.path.join(emblems.ART, layer + ".png"), "image/png")
        if url.path == "/api/bot-emblem":
            name = (parse_qs(url.query).get("name") or [""])[0]
            if name not in listed_bots(self.paths):
                return self.reply(400, {"error": "not a bot on the site"})
            seed = looks.seed_of(name)
            pick = emblems.chosen().get(name)
            return self.reply(200, {"name": name, "emblem": pick or emblems.roll(seed), "rolled": emblems.roll(seed),
                                    "custom": pick is not None})
        return self.reply(404, {"error": "no such page"})

    def do_POST(self):
        if not self.local() or not allowed_origin(self.headers.get("Origin"), self.port) or self.headers.get(HEADER) != "1":
            return self.reply(403, {"error": "edits come from the site on this PC only"})
        if self.path == "/api/bot-clan":
            return self.bot_clan()
        if self.path == "/api/reset-all":
            return self.reset_all()
        if self.path == "/api/simulate":
            return self.simulate()
        if self.path in ("/api/clan-rewards", "/api/clan-week", "/api/clan-emblem"):
            return self.clan_reward()
        if self.path == "/api/bot-emblem":
            return self.bot_emblem()
        if self.path == "/api/home-state":
            return self.home_state()
        if self.path == "/api/bot-difficulty":
            return self.bot_difficulty()
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

    def clan_reward(self):
        """(Nov 18, the clan rewards) /api/clan-rewards {"rewards": {key: {"on", "at"}}} ({} the defaults again),
        /api/clan-week {"challenge": key or ""}, /api/clan-emblem {"key": clan, "name": a member or ""}: saved in
        clan_settings.json (service_record.py save_clan_rewards, save_clan_week, save_clan_emblem), the site rebuilt."""
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY or "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("bad request")
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("bad request")
            if self.path == "/api/clan-rewards":
                answer = {"rewards": sr.save_clan_rewards(self.paths, data.get("rewards"))}
                said = "rewards: " + (", ".join(f"{k} {'on' if v.get('on', True) else 'off'}" for k, v in data["rewards"].items()) or "defaults")
            elif self.path == "/api/clan-week":
                pick = data.get("challenge", "")
                if not isinstance(pick, str):
                    raise ValueError("not a clan challenge")
                answer = {"challenge": sr.save_clan_week(self.paths, pick)}
                said = f"this week's clan challenge: {answer['challenge']}" + ("" if pick else " (drawn by the date)")
            else:
                key, name = sr.clan_key(data.get("key", "")), data.get("name", "")
                if name and listed_members(self.paths).get(name) != key:
                    raise ValueError("not a member of this clan")
                answer = {"key": key, "name": sr.save_clan_emblem(self.paths, key, name)}
                said = f"clan emblem: {key} -> {name or '(top member)'}"
        except (ValueError, UnicodeDecodeError, AttributeError, TypeError) as e:
            return self.reply(400, {"error": str(e) or "bad request"})
        print(said, flush=True)
        rebuild()
        return self.reply(200, answer)

    def bot_emblem(self):
        """(Nov 18, the emblem editor) {"name", "fg", "bg", "primary", "secondary", "background"}, or {"name", "reset":
        true} for its roll again: a listed bot's emblem saved (brain/emblems.py save_chosen), its lobby numbers and
        picture written again (export: native/bin/emblems/<name>.ids, .rgba), the site rebuilt. MCC shows it from the
        bot's next lobby or match."""
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY or "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("bad request")
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("bad request")
            name = data.get("name", "")
            if not isinstance(name, str) or name not in listed_bots(self.paths):
                raise ValueError("not a bot on the site")
            emblems, looks = brain_emblems()
            pick = None if data.get("reset") is True else {k: data.get(k) for k in emblems.KEYS}
            emblems.save_chosen(name, pick)
            emblems.export([(name, looks.seed_of(name))])
            now = emblems.emblem_for(name, looks.seed_of(name))
        except (ValueError, UnicodeDecodeError, AttributeError, TypeError, ImportError, OSError) as e:
            return self.reply(400, {"error": str(e) or "bad request"})
        print(f"bot emblem: {name} -> {'its roll' if pick is None else ' '.join(map(str, emblems.ids(now)))}", flush=True)
        rebuild()
        return self.reply(200, {"name": name, "emblem": now, "custom": pick is not None})

    def home_state(self):
        """(Nov 18, the owner) {"name", "state": a code or ""}: a listed bot's or player's home state on the state
        boards, saved in home_states.json (service_record.py save_home_state, "" its name's pick again), the site
        rebuilt (the page reloads)."""
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY or "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("bad request")
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("bad request")
            name, code = data.get("name", ""), data.get("state", "")
            if not isinstance(name, str) or name not in listed_names(self.paths):
                raise ValueError("not a name on the site")
            now = sr.save_home_state(self.paths, name, code)
        except (ValueError, UnicodeDecodeError, AttributeError, TypeError, OSError) as e:
            return self.reply(400, {"error": str(e) or "bad request"})
        print(f"home state: {name} -> {now}" + ("" if code else " (its name's pick)"), flush=True)
        rebuild()
        return self.reply(200, {"name": name, "state": now, "set": bool(code)})

    def bot_difficulty(self):
        """(Nov 18, the owner) {"name", "difficulty": a tier key or ""}: a listed bot's saved difficulty, written where
        the game reads it (service_record.py set_bot_difficulty): only while MCC is closed; the site rebuilt."""
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY or "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("bad request")
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("bad request")
            name, tier = data.get("name", ""), data.get("difficulty", "")
            if not isinstance(name, str) or name not in listed_bots(self.paths):
                raise ValueError("not a bot on the site")
            if not isinstance(tier, str):
                raise ValueError("not a difficulty")
            now = sr.set_bot_difficulty(self.paths, name, tier)
        except PermissionError as e:
            return self.reply(409, {"error": str(e)})
        except (ValueError, UnicodeDecodeError, AttributeError, TypeError, OSError) as e:
            return self.reply(400, {"error": str(e) or "bad request"})
        print(f"bot difficulty: {name} -> {now or '(the lobby difficulty)'}", flush=True)
        rebuild()
        return self.reply(200, {"name": name, "difficulty": now})

    def reset_all(self):
        """Everyone's stats from 0 (service_record.py reset_everyone): only with the body {"confirm": "reset all"},
        which the page sends after the owner confirms, and only while MCC is closed."""
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY or "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("bad request")
            if json.loads(self.rfile.read(size).decode("utf-8")).get("confirm") != "reset all":
                raise ValueError("not confirmed")
            marked = sr.reset_everyone()
        except PermissionError as e:
            return self.reply(409, {"error": str(e)})
        except (ValueError, UnicodeDecodeError, AttributeError, OSError) as e:
            return self.reply(400, {"error": str(e) or "bad request"})
        print(f"reset all: {marked} matches no longer count", flush=True)
        rebuild()
        return self.reply(200, {"matches": marked})


    def simulate(self):
        """(Nov 17, the bot simulation's button) {"rounds": 1..20}: that many rounds of simulated bot-only matches
        (tools/bot_sim.py --rounds), the career totals (bot_career.py), then the site built again."""
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY or "application/json" not in (self.headers.get("Content-Type") or ""):
                raise ValueError("bad request")
            rounds = json.loads(self.rfile.read(size).decode("utf-8")).get("rounds")
            if not isinstance(rounds, int) or isinstance(rounds, bool) or not 1 <= rounds <= 20:
                raise ValueError("rounds: a number from 1 to 20")
        except (ValueError, UnicodeDecodeError, AttributeError) as e:
            return self.reply(400, {"error": str(e) or "bad request"})
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
        try:
            subprocess.run([sys.executable, "-I", os.path.join(HERE, "bot_sim.py"), "--rounds", str(rounds), "--quiet"],
                           timeout=900, creationflags=flags, check=True)
            subprocess.run([sys.executable, "-I", os.path.join(HERE, "bot_career.py"), "--quiet"], timeout=300,
                           creationflags=flags)
        except (OSError, subprocess.SubprocessError) as e:
            return self.reply(500, {"error": f"the simulation did not finish ({e.__class__.__name__})"})
        played = 0
        try:
            with open(os.path.join(self.paths.store, "sim_status.txt"), encoding="utf-8") as f:
                played = next((int(l.split("\t")[1]) for l in f if l.startswith("matches\t")), 0)
        except (OSError, ValueError):
            pass
        print(f"simulated: {rounds} rounds, {played} matches", flush=True)
        rebuild()
        return self.reply(200, {"rounds": rounds, "matches": played})


def listed_bots(paths):
    """The bots the built site lists (its data.js, its people left out): the only bots the editor will touch."""
    try:
        with open(os.path.join(paths.out, "data.js"), encoding="utf-8") as f:
            text = f.read()
        return {p["name"] for p in json.loads(text[text.index("{"):text.rindex("}") + 1])["players"] if not p.get("person")}
    except (OSError, ValueError, KeyError):
        return set()


def listed_names(paths):
    """Every name the built site lists, its bots and its people (its data.js)."""
    try:
        with open(os.path.join(paths.out, "data.js"), encoding="utf-8") as f:
            text = f.read()
        return {p["name"] for p in json.loads(text[text.index("{"):text.rindex("}") + 1])["players"]}
    except (OSError, ValueError, KeyError):
        return set()


def brain_emblems():
    """(brain/emblems.py, brain/looks.py): the bots' emblems and looks, from the repository's brain."""
    root = os.path.normpath(os.path.join(HERE, ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    from brain import emblems, looks
    return emblems, looks


def listed_members(paths):
    """{player name: clan key} for every player the built site lists in a clan (its data.js)."""
    try:
        with open(os.path.join(paths.out, "data.js"), encoding="utf-8") as f:
            text = f.read()
        return {p["name"]: sr.clan_key(p["clan"]) for p in json.loads(text[text.index("{"):text.rindex("}") + 1])["players"]
                if str(p.get("clan") or "").strip()}
    except (OSError, ValueError, KeyError):
        return {}


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
