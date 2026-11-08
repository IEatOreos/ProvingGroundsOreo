"""The GitHub release's text from docs/UPDATES.md: the download line, the newest version's whole section (every update of
it, each with its <!-- build: ... --> stamp, which tools/updater.py reads to tell an in-place update), and where the
known bugs and the status sheet are. One source for the release page, the launcher's What's new and UPDATES.md.

usage: python -I release_notes.py <out.md>      (the version from VERSION; fails when UPDATES.md has no section for it,
                                                 or its newest update's stamp is not BUILD's)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import updater  # noqa: E402

REPO_URL = "https://github.com/AyoItzKye/project-proving-grounds"


def notes(md, version, build):
    """The release text for version (and build) from UPDATES.md's text md; raises ValueError when they do not match."""
    sec = next((s for s in updater.parse_updates(md) if s["key"] == updater.version_key(version)), None)
    if sec is None:
        raise ValueError(f"docs/UPDATES.md has no section for {version}")
    stamps = [b for b, _ in sec["batches"] if b]
    if build and (not stamps or max(stamps) != build):
        raise ValueError(f"the newest update of {version} in docs/UPDATES.md is {max(stamps) if stamps else 'unstamped'},"
                         f" BUILD says {build}")
    body = re.search(r"<summary><b>" + re.escape(sec["name"]) + r"</b>.*?</summary>(.*?)</details>", md, re.S).group(1)
    v = version.replace("v", "")
    head = (f"Download **ProjectProvingGrounds-Setup-{v}.exe** and run it (it updates an existing install in place). "
            f"Steam Deck / Linux: **ProjectProvingGrounds-Linux-{v}.tar.gz**. The map pack zip is optional.\n\n"
            f"## {sec['name']} {sec['title']}\n\n")
    tail = (f"\n\nEvery version's changes are on the [Updates]({REPO_URL}/blob/main/docs/UPDATES.md) page. Everything "
            f"still known to be broken is on the [Known bugs]({REPO_URL}/blob/main/docs/KNOWN_BUGS.md) page; every "
            f"game and mode is rated on the bot status sheet (the PDF below).\n")
    return head + body.strip() + tail


def main():
    out = sys.argv[1]
    md = open(os.path.join(ROOT, "docs", "UPDATES.md"), encoding="utf-8").read()
    version = open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()
    build = updater.build()
    text = notes(md, version, build)
    open(out, "w", encoding="utf-8").write(text)
    print(f"release notes for {version} build {build or '(none)'}: {out} ({len(text)} chars)")


if __name__ == "__main__":
    main()
