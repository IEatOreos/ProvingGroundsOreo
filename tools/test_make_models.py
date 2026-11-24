"""(custom, Nov 24) Upstream 0.3.0's note #29 (build 20261114-2230): in the setup's 3D bots step (tools/make_models.py)
one model that fails to pack is left out and named, and the rest are still made; his ODST squad and Dare models are in
the list (the owner: "his ODST models included"). No MCC, map tools or model is touched: every tool run is faked."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_argv, sys.argv = sys.argv, ["make_models.py"]
try:
    import make_models  # noqa: E402
finally:
    sys.argv = _argv


class OneFailedModelTests(unittest.TestCase):
    def test_the_rest_are_made(self):
        with tempfile.TemporaryDirectory() as tmp:
            mcc, out = os.path.join(tmp, "mcc"), os.path.join(tmp, "models")
            os.makedirs(os.path.join(mcc, "g"))
            os.makedirs(out)
            open(os.path.join(mcc, "g", "a.map"), "w").close()
            models = [(n, "spartan", "g" + n, r"g\a.map", "tag", "gun", []) for n in ("one", "two", "three")]

            def run(cmd, **kw):
                if cmd[0] == "model2obj":                    # an export: its file written
                    open(cmd[3], "w").close()
                    return SimpleNamespace(returncode=0, stdout="", stderr="")
                if any(str(c).endswith("model_pack2.py") for c in cmd):
                    bad = os.path.basename(cmd[6]) == "two.mdl"
                    return SimpleNamespace(returncode=1 if bad else 0, stdout="", stderr="Traceback: broken" if bad else "")
                return SimpleNamespace(returncode=0, stdout="", stderr="")   # (emblems.py)
            with mock.patch.object(make_models, "MODELS", models), mock.patch.object(make_models, "MCC", mcc), \
                    mock.patch.object(make_models, "OUT", out), mock.patch.object(make_models, "ROOT", tmp), \
                    mock.patch.object(make_models, "ONLY", None), mock.patch.object(make_models, "GEAR", {}), \
                    mock.patch.object(make_models.paths, "need", lambda p, what: "model2obj"), \
                    mock.patch.object(make_models.paths, "map_tool", lambda n: "model2obj"), \
                    mock.patch.object(make_models.subprocess, "run", side_effect=run), \
                    mock.patch("builtins.print"):
                make_models.main()
            with open(os.path.join(out, "made.txt"), encoding="utf-8") as f:
                made = f.read()
        self.assertIn("made: one three\n", made)
        self.assertIn("not packed: two", made)

    def test_odst_models_listed(self):
        names = {m[0]: m for m in make_models.MODELS}
        self.assertIn("odst_spartan", names)
        self.assertIn("odst_dare", names)
        self.assertEqual(make_models.body_obj("T", "odst_dare", "spartan", "odst"), os.path.join("T", "odst_dare.obj"))
        self.assertEqual(make_models.body_obj("T", "odst_spartan", "spartan", "odst"), os.path.join("T", "spartan.obj"))
        self.assertIn("spin_l=", names["odst_spartan"][6][1])           # (model_pack2's left-hand spin, his too)
        import model_pack2
        self.assertIn("spin_l", open(model_pack2.__file__, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
