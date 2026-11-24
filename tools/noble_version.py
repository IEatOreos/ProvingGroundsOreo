"""Project Noble's version number, the owner's own scheme (custom, Nov 24; upstream 0.3.0's note #67 asked for a
version with a build number, his BUILD_NO is not used):

    X.Y.Z     Y.Z = the number of commits on GitHub's main: Y = commits // 1000, Z = commits % 1000
                    (325 commits: 0.0.325; 1000 commits: 0.1.0)
              X   = the number of releases made under this scheme: 0 until the next release, which is 1, then 2 ...
                    (the four releases before it, v0.2.2-custom.11 to .14, do not count)

At a release, Y.Z keep the all-time commit count of the commit released (e.g. 1.0.340); its tag is "v" + the version.

Where the number comes from:
  - an installed copy (no Git): NOBLE_VERSION beside the project, stamped by tools/build_installer.py at build time;
  - a Git checkout: `git rev-list --count origin/main` (GitHub's main as this checkout last fetched it; when there is
    no origin/main, the current branch's upstream `@{upstream}`), and X = the highest X of this checkout's new-scheme
    release tags (`vX.Y.Z` with X >= 1; `git fetch --tags` brings GitHub's). A dev copy is never ahead of a release
    it has the tag of: its count only grows;
  - neither (an older install): None, and tools/updater.py reads CUSTOM_VERSION ("0.2.2-custom.14") as before.

A release build (tools/build_installer.py): X = the highest release tag's X + 1, Y.Z = the commits of HEAD (the commit
that becomes GitHub's main when it is pushed).

usage: python -I noble_version.py            prints this checkout's version and the next release's
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STAMP = "NOBLE_VERSION"                          # the stamped file of an installed copy (tools/build_installer.py)
RELEASE_TAG = re.compile(r"^v([1-9]\d*)\.(\d+)\.(\d+)$")     # a new-scheme release tag (X >= 1)


def from_counts(commits, releases):
    """The version for this many commits on GitHub's main and this many new-scheme releases: "X.Y.Z"."""
    commits, releases = int(commits), int(releases)
    if commits < 0 or releases < 0:
        raise ValueError("counts cannot be negative")
    return f"{releases}.{commits // 1000}.{commits % 1000}"


def releases_in(tags):
    """The number of new-scheme releases a list of tag names shows: the highest X among vX.Y.Z tags with X >= 1
    (old tags such as v0.2.2-custom.14 and the checkpoint tags do not count)."""
    return max((int(m.group(1)) for m in map(RELEASE_TAG.match, tags) if m), default=0)


def _git(root, *args):
    git = shutil.which("git")
    if not git or not os.path.exists(os.path.join(root, ".git")):
        return None
    try:
        r = subprocess.run([git, "-C", root, *args], capture_output=True, text=True, timeout=10,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def commit_count(root=ROOT, ref=None):
    """Commits on GitHub's main as this checkout knows it (origin/main, else the branch's upstream), or of ref; None
    outside a Git checkout."""
    for r in ([ref] if ref else ["origin/main", "@{upstream}"]):
        n = _git(root, "rev-list", "--count", r)
        if n and n.isdigit():
            return int(n)
    return None


def release_count(root=ROOT):
    tags = _git(root, "tag", "--list", "v*")
    return releases_in(tags.splitlines()) if tags is not None else 0


def stamped(root=ROOT):
    """The version stamped into an installed copy, or None."""
    try:
        with open(os.path.join(root, STAMP), encoding="utf-8") as f:
            v = f.read().strip()
    except OSError:
        return None
    return v if re.fullmatch(r"\d+\.\d+\.\d+", v) else None


def current(root=ROOT):
    """This copy's version under the scheme: stamped (installed), else from Git (a checkout), else None."""
    v = stamped(root)
    if v:
        return v
    n = commit_count(root)
    return from_counts(n, release_count(root)) if n is not None else None


def next_release(root=ROOT):
    """(version, tag) of a release built from HEAD now: X one past the last release tag, Y.Z HEAD's commit count."""
    n = commit_count(root, "HEAD")
    if n is None:
        raise SystemExit("not a Git checkout: the release version comes from its commits")
    v = from_counts(n, release_count(root) + 1)
    return v, "v" + v


if __name__ == "__main__":
    print("this copy:", current() or "no version (not a checkout, nothing stamped)")
    if _git(ROOT, "rev-parse", "HEAD"):
        v, tag = next_release()
        print(f"a release built from HEAD now: {v} (tag {tag})")
    sys.exit(0)
