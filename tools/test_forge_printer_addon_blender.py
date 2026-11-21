"""Reach Forge Printer, phase 4: the add-on inside a real Blender, run headless.

Runs tools/forge_printer/blender_addon/headless_check.py (no game files needed: enabling the
add-on, the slope-test orientations, the export refusals) and skips where Blender is not
installed. The Guardian round trip needs the local reference and a template from the owner's
MCC; its command is in the add-on's README.md.
"""

import os
import subprocess
import unittest

from forge_printer.blender_addon import install

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "forge_printer", "blender_addon", "headless_check.py")


class HeadlessBlender(unittest.TestCase):
    def test_the_addon_in_blender(self):
        blender = install.find_blender()
        if not blender:
            self.skipTest("Blender is not installed")
        run = subprocess.run([blender, "--background", "--factory-startup", "--python-exit-code", "1",
                              "--python", CHECK], capture_output=True, text=True, errors="replace", timeout=600)
        lines = [line for line in run.stdout.splitlines() if line.startswith(("check:", "checks:", "registered:"))]
        failed = [line for line in lines if line.startswith("check: FAIL")]
        self.assertEqual(failed, [], "\n".join(lines))
        self.assertEqual(run.returncode, 0, (run.stdout + run.stderr)[-3000:])
        self.assertIn("checks: 0 failed", lines)
        self.assertTrue(any(line.startswith("registered: FORGE_PRINTER_OT_open_fit") for line in lines))
        self.assertGreaterEqual(sum(1 for line in lines if line.startswith("check: ok")), 20)


if __name__ == "__main__":
    unittest.main()
