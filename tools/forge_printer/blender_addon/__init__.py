"""Reach Forge Printer, phase 4: the Blender add-on.

Install it once (it stays linked to this folder, so it is always the repository's version):

    python\\python.exe tools\\forge_printer\\blender_addon\\install.py

Then in Blender: the 3D view's sidebar (press N), tab "Forge". README.md beside this file says
how to use it.

Only `ui.py` needs Blender. `convert.py` and `export.py` are plain modules the test suite
imports; this file imports nothing from Blender until Blender calls register().

Phase 4 of docs/REACH_FORGE_PRINTER_PLAN.md. Nothing in the bot imports this.
"""

import os
import sys

bl_info = {
    "name": "Reach Forge Printer",
    "author": "Project Reach",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar (N) > Forge",
    "description": "Open a fit.json as Forge pieces, edit them, count them against Reach's limits, export a .mvar",
    "category": "Import-Export",
}

# Blender loads this folder through a link in its add-ons folder; the printer's own modules
# (mvar, fit, pieces) are two folders up, in tools/forge_printer.
_TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
if _TOOLS not in sys.path:
    sys.path.append(_TOOLS)


def register():
    from . import ui
    ui.register()


def unregister():
    from . import ui
    ui.unregister()
