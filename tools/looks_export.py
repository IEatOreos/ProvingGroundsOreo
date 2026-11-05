"""Write native/bin/bot_looks.ini: every bot's look as rolled, per game (brain/looks.py export_view), for the Settings
tab's profile view. The panel runs it (native/bots_panel.cpp looks_refresh) when the file is missing or older than
bot_profiles.ini, and after every change in the profile view.

usage: python -I looks_export.py [profiles.ini] [out.ini]      (default: native/bin/bot_profiles.ini -> bot_looks.ini)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from brain import looks  # noqa: E402

if __name__ == "__main__":
    profiles = sys.argv[1] if len(sys.argv) > 1 else looks.PROFILES
    out = sys.argv[2] if len(sys.argv) > 2 else looks.VIEW
    n = looks.export_view(profiles, out)
    print(f"bot looks: {n} lines -> {out}")
