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
    return open(os.path.join(HERE, name), encoding="utf-8").read()


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


if __name__ == "__main__":
    unittest.main()
