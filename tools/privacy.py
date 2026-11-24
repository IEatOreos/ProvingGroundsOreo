"""This PC's private terms and the check for them: what the release installer's privacy scan refuses to ship
(tools/build_installer.py privacy_scan) and what a shared LiDAR scan may not carry (tools/lidar_share.py private()).

(custom, Nov 24) Factored out of build_installer.privacy_scan, unchanged: this PC's profile path (USERPROFILE) and the
terms listed in .private_terms (one per line, in the repository's root, never in Git), lower case, 4 letters or more,
found anywhere; and this PC's user name (USERNAME) as a whole word only (a name inside a longer word, like an armor's name, is not a hit).
"""
import os
import re


def load_terms(root):
    """The lower-case terms to find anywhere: this PC's profile path and root/.private_terms."""
    terms = {os.environ.get("USERPROFILE", "")}
    try:
        with open(os.path.join(root, ".private_terms"), encoding="utf-8") as f:
            terms |= {t.strip() for t in f if t.strip()}
    except OSError:
        pass
    return sorted({t.lower() for t in terms if len(t) >= 4})


def user_word():
    """(user name, its whole-word pattern), or (name, None) when the name is shorter than 4 letters."""
    user = os.environ.get("USERNAME", "").lower()
    return user, (re.compile(r"(?<![a-z0-9])" + re.escape(user) + r"(?![a-z0-9])") if len(user) >= 4 else None)


def hits(text, terms, user="", word=None):
    """The terms (and the user name) a text holds, in the order checked; text is compared lower case."""
    text = text.lower()
    found = [t for t in terms if t in text]
    if word is not None and word.search(text):
        found.append(user)
    return found
