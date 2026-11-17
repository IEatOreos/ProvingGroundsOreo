"""native/figure_snap.cpp draws each bot's Reach figure as the bots panel does: its colour and visor tables must be the
panel's (native/bots_panel.cpp REACH_COL, REACH_VISOR), value for value. And the site's side (service_record.py
bot_figures): the program's index read, safe file names only, a missing picture or program left out."""
import importlib.util
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
NATIVE = os.path.join(HERE, "..", "native")


def read(name):
    with open(os.path.join(NATIVE, name), encoding="utf-8", errors="replace") as f:
        return f.read()


def block(text, start):
    at = text.index(start)
    return text[at:text.index("};", at)]


def test_colours_are_the_panels():
    panel, snap = read("bots_panel.cpp"), read("figure_snap.cpp")
    want = [tuple(map(int, m)) for m in re.findall(r"IM_COL32\((\d+), (\d+), (\d+), 255\)", block(panel, "static const swatch REACH_COL[30]"))]
    got = [tuple(map(int, m)) for m in re.findall(r"\{(\d+), (\d+), (\d+)\}", block(snap, "static const unsigned char REACH_RGB[30][3]"))]
    assert len(want) == 30 and got == want, (got, want)
    visor = re.compile(r"\{([\d.]+)f, ([\d.]+)f, ([\d.]+)f\}")
    assert visor.findall(block(snap, "static const float REACH_VISOR")) == visor.findall(block(panel, "static const float REACH_VISOR"))


def test_site_reads_the_index():
    """Each turntable strip (its angles side by side) becomes a WebP, the PNG then goes; a row naming a missing or
    unsafe file, or without its angles and sizes, is left out."""
    from PIL import Image
    spec = importlib.util.spec_from_file_location("service_record", os.path.join(HERE, "service_record.py"))
    sr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sr)
    with tempfile.TemporaryDirectory() as tmp:
        store, site = os.path.join(tmp, "store"), os.path.join(tmp, "site")
        folder = os.path.join(store, "art", "figures", "bots")
        os.makedirs(folder)
        for f in ("oreo_1234abcd.png", "lilwraith_00000001.png", "old_00000002.png"):
            Image.new("RGBA", (24 * 4, 10), (200, 30, 30, 255)).save(os.path.join(folder, f))
        with open(os.path.join(folder, "figures.tsv"), "w", encoding="utf-8") as fh:
            fh.write("Oreo\toreo_1234abcd.png\tspartan\t24\t4\t10\nLilWraith\tlilwraith_00000001.png\tspartan\t24\t4\t10\n"
                     "Old\told_00000002.png\tspartan\n"                       # (a still from before the turntable)
                     "Ghost\tghost_ffffffff.png\tspartan\t24\t4\t10\nSneaky\t..\\..\\x.png\tspartan\t24\t4\t10\nshort line\n")
        paths = sr.Paths(store=store, out=site, looks=os.path.join(tmp, "none.ini"), snap=os.path.join(tmp, "none.exe"))
        got = sr.bot_figures(paths)
        assert got == {"Oreo": {"src": "figures/bots/oreo_1234abcd.webp", "n": 24, "w": 4, "h": 10},
                       "LilWraith": {"src": "figures/bots/lilwraith_00000001.webp", "n": 24, "w": 4, "h": 10}}, got
        assert sorted(os.listdir(os.path.join(site, "figures", "bots"))) == ["lilwraith_00000001.webp", "oreo_1234abcd.webp"]
        assert sorted(os.listdir(folder)) == ["figures.tsv", "lilwraith_00000001.webp", "old_00000002.png", "oreo_1234abcd.webp"]
        assert Image.open(os.path.join(folder, "oreo_1234abcd.webp")).size == (96, 10)
        assert sr.bot_figures(paths) == got                                  # (again: the WebP kept, nothing redone)
        assert sr.bot_figures(sr.Paths(store=os.path.join(tmp, "empty"), out=site, snap=os.path.join(tmp, "none.exe"))) == {}


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")
    sys.exit(0)
