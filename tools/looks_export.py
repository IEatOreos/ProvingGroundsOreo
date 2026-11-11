"""Write native/bin/bot_looks.ini: every bot's look as rolled, per game (brain/looks.py export_view), for the Settings
tab's profile view. The panel runs it (native/bots_panel.cpp looks_refresh) when the file is missing or older than
bot_profiles.ini, and after every change in the profile view.

usage: python -I looks_export.py [profiles.ini] [out.ini]      (default: native/bin/bot_profiles.ini -> bot_looks.ini)
       python -I looks_export.py --emblems profiles.ini NAME...   (custom, Nov 11: those bots' emblem pictures only,
       native/bin/emblems/<name>.rgba, for the lobby's bot rows: a pool bot with no profile gets its own emblem, the
       one MCC shows for it, by brain/looks.py seed_of)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from brain import looks  # noqa: E402

def export_emblems(profiles, names):
    """The named bots' emblem pictures (brain/emblems.py export); how many were written (0: no emblem art extracted)."""
    from brain import emblems
    try:
        return emblems.export([(n, looks.seed_of(n, profiles)) for n in names if n])
    except (OSError, ImportError, ValueError):
        return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--emblems"]:
        n = export_emblems(sys.argv[2], sys.argv[3:])
        print(f"bot emblems: {n} of {len(sys.argv) - 3}")
        sys.exit(0)
    profiles = sys.argv[1] if len(sys.argv) > 1 else looks.PROFILES
    out = sys.argv[2] if len(sys.argv) > 2 else looks.VIEW
    n = looks.export_view(profiles, out)
    print(f"bot looks: {n} lines -> {out}")
