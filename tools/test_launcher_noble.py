"""The in-repo launcher's Project Noble pieces (custom, Nov 24): its links, and what upstream 0.3.0's launcher notes
brought in (each test names its note)."""
import io
import json
import os
import re
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import launcher  # noqa: E402

UPSTREAM = "https://github.com/AyoItzKye/project-proving-grounds"
OURS = "https://github.com/IEatOreos/ProvingGroundsOreo"


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def call(method, path, body=None):
    """One request to the launcher's Handler, without a server: (code, answer)."""
    h = launcher.Handler.__new__(launcher.Handler)
    data = json.dumps(body).encode() if body is not None else b""
    h.path, h.rfile = path, io.BytesIO(data)
    h.headers = {"X-Launcher": "1", "Content-Length": str(len(data))}
    got = {}
    h.send = lambda answer, ctype="application/json", code=200: got.update(answer=answer, code=code)
    getattr(h, "do_" + method)()
    return got["code"], got["answer"]


class Links(unittest.TestCase):
    """(custom, Nov 24) the guide's and the notes' links go to our repository; one credit link to the original."""

    def test_guide_links_are_ours_but_one_credit(self):
        hrefs = re.findall(r'href="(https?://[^"]+)"', read("guide.html"))
        theirs = [h for h in hrefs if "AyoItzKye" in h]
        self.assertEqual(theirs, [UPSTREAM])                  # the one credit link
        self.assertTrue(all(h.startswith(OURS + "/") for h in hrefs if h not in theirs), hrefs)
        for h in hrefs:
            self.assertTrue(launcher.link_ok(h), h)          # every one of them opens (/open)

    def test_launcher_notes_docs_are_ours(self):
        page = read("launcher.html")
        self.assertIn('const DOCS = REPO + "/blob/main/docs/"', page)
        self.assertIn(f'REPO = "{OURS}"', page)

    def test_open_allowlist(self):
        self.assertTrue(launcher.link_ok(OURS + "/releases/latest"))
        self.assertTrue(launcher.link_ok(UPSTREAM))
        self.assertTrue(launcher.link_ok(UPSTREAM + "/issues/12"))
        for bad in ("https://github.com/AyoItzKye/proving-grounds-map-tools", OURS + "Evil/releases",
                    "https://projectprovinggrounds.com/", "file:///C:/Windows", ""):
            self.assertFalse(launcher.link_ok(bad), bad)


class OpenFolder(unittest.TestCase):
    """(upstream 0.3.0 note #79) Open the install folder: the folder's explore verb, never a plain open."""

    def test_explore_verb(self):
        with mock.patch.object(launcher.os, "startfile", create=True) as sf:
            self.assertEqual(call("POST", "/folder", {}), (200, {"ok": True}))
        sf.assert_called_once_with(os.path.normpath(launcher.ROOT), "explore")



class FolderWarning(unittest.TestCase):
    """(upstream 0.3.0 note #18) Setup for the current user only, and the launcher says when its folder takes no files."""

    def setUp(self):
        launcher.FOLDER.clear()
        self.addCleanup(launcher.FOLDER.clear)

    def test_locked_folder_refuses_tasks_with_project_noble_words(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d, mock.patch.object(launcher, "LOGS", os.path.join(d, "logs")), \
                mock.patch("builtins.open", side_effect=PermissionError("denied")):
            why = launcher.folder_problem()
        self.assertIn("Project Noble", why)
        self.assertNotIn("Proving Grounds", why.replace(launcher.ROOT, ""))   # (the folder's own name aside)
        with mock.patch.object(launcher.subprocess, "Popen") as run:
            self.assertEqual(launcher.start("play"), (False, why))
        run.assert_not_called()

    def test_writable_folder_is_fine_and_leaves_no_probe(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d, mock.patch.object(launcher, "LOGS", d):
            self.assertIsNone(launcher.folder_problem())
            self.assertEqual(os.listdir(d), [])

    def test_installer_no_all_users_choice(self):
        iss = read(os.path.join("..", "installer", "ProjectProvingGrounds.iss"))
        self.assertIn("PrivilegesRequired=lowest", iss)
        self.assertNotIn("PrivilegesRequiredOverridesAllowed", iss)
        self.assertIn("AppName=Project Noble", iss)

    def test_page_shows_it(self):
        self.assertIn('$("banner").textContent = s.readonly || ""', read("launcher.html"))


class CompactLog(unittest.TestCase):
    """(upstream 0.3.0 note #50) the Play log folds to one line; our follow() stays and feeds it."""

    def test_page(self):
        page = read("launcher.html")
        for bit in ('id="log-toggle"', 'id="log-last"', 'id="log-play" aria-live="polite" hidden', 'id="play-card"',
                    "function setLog(open, chosen)", "function playLine(line)",
                    'if (task === "play") playLine(line);', 'if (task === "play" && r.code !== 0) setLog(true);',
                    'localStorage.setItem("play-log-open"', "async function follow(task, box, stateEl)"):
            self.assertIn(bit, page)
        play = page[page.index('$("play").onclick'):]
        self.assertLess(play.index("setLog(true);"), play.index('post("/run/play"'))   # (opens as Play starts)


def fake_studio(folder, runtime=True):
    """A copy of MCC Map Studio as the launcher recognises it (package.json, main.js, its own Electron when runtime)."""
    os.makedirs(folder, exist_ok=True)
    for f in ("package.json", "main.js"):
        open(os.path.join(folder, f), "w").close()
    if runtime:
        exe = os.path.join(folder, "node_modules", "electron", "dist")
        os.makedirs(exe)
        open(os.path.join(exe, "electron.exe"), "w").close()
    return folder


class MapStudio(unittest.TestCase):
    """(upstream 0.3.0 notes #49 + #78) the Map Studio tile: located and opened only, never downloaded."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.saved = os.path.join(self.d, "user", "map_studio.txt")
        # (nothing of this PC's own copies: no home, no wide search)
        for name, value in (("MAP_STUDIO_HOME", os.path.join(self.d, "nohome")),):
            p = mock.patch.object(launcher, name, value)
            p.start()
            self.addCleanup(p.stop)
        launcher._ELSEWHERE.update(at=0.0, found=None, busy=False)
        self.addCleanup(launcher._ELSEWHERE.update, at=0.0, found=None, busy=False)

    def test_no_download_anywhere(self):
        src = read("launcher.py")
        for gone in ("map_studio_install", "_studio_asset", "_studio_unzip", "STUDIO_JOB", "updater.SITE",
                     "release.json", "/mapstudio_install"):
            self.assertNotIn(gone, src)
        self.assertNotIn("/mapstudio_install", read("launcher.html"))

    def test_links_name_the_app_folder(self):
        lnk = "C:\\Tools\\MCC Map Studio\\node_modules\\electron\\dist\\electron.exe".encode("utf-16-le")
        bat = b"\x00junk D:\\Apps\\Studio\\start.bat\x00"
        self.assertEqual(launcher.map_studio_links([lnk, bat]), ["C:\\Tools\\MCC Map Studio", "D:\\Apps\\Studio"])

    def test_elsewhere_top_folders_only(self):
        drive = os.path.join(self.d, "drive")
        deep = fake_studio(os.path.join(drive, "a", "b", "MCC Map Studio"))       # too deep: not looked for
        os.makedirs(os.path.join(drive, "Games"))
        top = os.path.join(drive, "Games", "mcc-map-studio-main")
        got = launcher.map_studio_elsewhere(appdata=self.d, links=[], homes=[], drives=[drive])
        self.assertIn(top, got)
        self.assertNotIn(deep, got)

    def test_status_never_waits_for_the_wide_search(self):
        calls = []
        with mock.patch.object(launcher, "map_studio_elsewhere", side_effect=lambda: calls.append(1) or []), \
                mock.patch.object(launcher.threading, "Thread") as thread:
            self.assertIsNone(launcher.map_studio(env={}, saved=self.saved, root=self.d))
            self.assertEqual(calls, [])                        # (in the background, not now)
            thread.assert_called_once()
            launcher._ELSEWHERE.update(at=launcher.time.time())
            launcher.map_studio(env={}, saved=self.saved, root=self.d)
            thread.assert_called_once()                        # (kept MAP_STUDIO_WIDE_EVERY: not again)

    def test_saved_folder_found_first(self):
        studio = fake_studio(os.path.join(self.d, "here"))
        os.makedirs(os.path.dirname(self.saved))
        with open(self.saved, "w", encoding="utf-8") as f:
            f.write(studio)
        self.assertEqual(launcher.map_studio(env={}, saved=self.saved, root=self.d, wide=False), os.path.abspath(studio))

    def browse(self, picked):
        with mock.patch.object(launcher, "pick_folder", return_value=picked) as pick, \
                mock.patch.object(launcher, "map_studio_elsewhere", return_value=[]), \
                mock.patch.object(launcher.subprocess, "Popen") as run:
            got = launcher.open_map_studio({"browse": True}, saved=self.saved)
        self.assertEqual(pick.call_args.kwargs.get("title"), "Choose the MCC Map Studio folder")
        return got, run

    def test_locate_accepts_the_unzipped_folder(self):
        unzipped = os.path.join(self.d, "Downloads", "zip")
        studio = fake_studio(os.path.join(unzipped, "mcc-map-studio-main"))
        (ok, msg), run = self.browse(unzipped)
        self.assertTrue(ok, msg)
        with open(self.saved, encoding="utf-8") as f:
            self.assertEqual(f.read(), studio)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[1], os.path.abspath(studio))
        self.assertEqual(run.call_args.kwargs["creationflags"], 0x00000008)    # (its own program, not waited on)

    def test_locate_says_when_the_runtime_is_missing(self):
        (ok, msg), run = self.browse(fake_studio(os.path.join(self.d, "src"), runtime=False))
        self.assertFalse(ok)
        self.assertIn("no runtime", msg)
        self.assertNotIn("Download", msg)
        run.assert_not_called()
        (ok, msg), _ = self.browse(os.path.join(self.d))
        self.assertEqual((ok, msg), (False, "MCC Map Studio is not in that folder."))

    def test_not_found_opens_nothing(self):
        with mock.patch.object(launcher, "map_studio", return_value=None), \
                mock.patch.object(launcher.subprocess, "Popen") as run:
            self.assertEqual(call("POST", "/mapstudio", {})[1]["ok"], False)
        run.assert_not_called()

    def test_badge_and_tile(self):
        code, png = call("GET", "/studio.png")
        self.assertEqual(code, 200)
        self.assertTrue(png.startswith(b"\x89PNG"))
        page = read("launcher.html")
        for bit in ('id="mapstudio"', 'src="/studio.png"', 'id="mapstudio-locate"', 'post("/mapstudio"'):
            self.assertIn(bit, page)


class LoadingBanner(unittest.TestCase):
    """(upstream 0.3.0 note #73) the loading banner says PROJECT NOBLE; #60's loading message is not anywhere."""

    def test_banner_draws_project_noble(self):
        import loading_banner
        self.assertEqual(loading_banner.NAME, "PROJECT NOBLE")
        self.assertFalse(hasattr(loading_banner, "HINT"))
        self.assertTrue(loading_banner.BADGE.endswith(os.path.join("installer", "linux", "icon.png")))
        self.assertIsNotNone(loading_banner.badge(68))               # (our Noble logo is there)
        for scale, fade in ((1.0, 1.0), (2.0, 0.5), (0.75, 0.0)):
            img = loading_banner.frame(1.3, scale, fade)
            self.assertEqual(img.size, (int(loading_banner.W * scale), int(loading_banner.H * scale)))
            self.assertEqual(img.mode, "RGBA")

    def test_no_open_multiplayer_message(self):
        import loading_tag
        for name in ("loading_banner.py", "loading_tag.py", "launch.py"):
            text = read(name).lower()
            self.assertNotIn("open multiplayer once", text, name)
            self.assertNotIn('"project proving grounds"', text, name)
        self.assertIn("Project Noble", loading_tag.TEXT)
        self.assertEqual(loading_tag.READY_EVENT, "Local\\PPG_overlay_ready")

    def test_play_starts_and_closes_it_not_under_linux(self):
        src = read("launch.py")
        self.assertIn("if not exe:", src)
        self.assertLess(src.index("tag = loading_tag.LoadingTag()"), src.index("for _ in range(180):"))
        self.assertLess(src.index("subprocess.run([inj"), src.index("tag.wait_ready(120)"))
        self.assertLess(src.index("tag.wait_ready(120)"), src.index('print("Bots are ready'))

    def test_overlay_says_ready(self):
        cpp = read(os.path.join("..", "native", "overlay.cpp"))
        at = cpp.index('L"Local\\\\PPG_overlay_ready"')
        self.assertLess(cpp.rindex("g_ready = true;", 0, at), at)


if __name__ == "__main__":
    unittest.main()
