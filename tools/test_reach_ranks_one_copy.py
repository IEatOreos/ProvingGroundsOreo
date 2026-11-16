"""(custom, Nov 15) The Reach rank table has one copy: tools/service_record_site/ranks.json. The owner, on the Service
Record's ranks: "make sure it stays flush if we end up adding ranks into the game for bots". The site reads that
file; anything in the game that shows a bot's Reach rank must read it too (or a file made from it), never its own
list of credits, or the two drift apart the first time a figure changes.

This fails when another source file holds three or more of the table's telling credit figures (26,250, 1,180,000,
5,650,000 and the like: figures no code would hold for another reason), unless the file's first lines say it was
made from ranks.json (a generated header may hold them)."""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
TABLE = os.path.join(HERE, "service_record_site", "ranks.json")
SOURCES = ("brain/*.py", "tools/*.py", "tools/service_record_site/*", "native/*.cpp", "native/*.h", "native/*.hpp")


def telling(table):
    """The table's credit figures with three or more digits before their trailing zeros: 26250, 111000, 1180000."""
    figures = {cr for r in table["ranks"] for cr in r["cr"]}
    return sorted(cr for cr in figures if len(str(cr).rstrip("0")) >= 3)


def pattern(figure):
    """The figure as code or text writes it: 1180000, 1,180,000, 1_180_000, 1 180 000."""
    s, groups = str(figure), []
    while s:
        groups.insert(0, s[-3:])
        s = s[:-3]
    return re.compile(r"(?<![\d.])" + "[,_ ]?".join(groups) + r"(?![\d.])")


def copied(text, figures):
    """The telling figures a text holds; none when its first lines say it was made from ranks.json."""
    if "ranks.json" in text[:400]:
        return []
    return [f for f in figures if pattern(f).search(text)]


def test_the_detector():
    with open(TABLE, encoding="utf-8") as f:
        figures = telling(json.load(f))
    assert len(figures) >= 15 and {26250, 1180000, 5650000, 16500000} <= set(figures), figures
    assert 20000 not in figures and 7500 not in figures and 3000000 not in figures, figures
    a_copy = "static const int REACH_CR[] = { 0, 7500, 10000, 15000, 20000, 26250, 32500, 45000, 78000, 111000, 144000 };"
    assert copied(a_copy, figures) == [26250, 32500, 111000, 144000], copied(a_copy, figures)
    assert copied("cr = [1_180_000, 5,650,000, 16 500 000]", figures) == [1180000, 5650000, 16500000]
    assert copied("// Generated from tools/service_record_site/ranks.json (do not edit)\n" + a_copy, figures) == []
    assert copied("timeout_ms = 26250; port = 11100; big = 1180000123; ratio = 0.26250", figures) == [26250]


def test_no_other_source_holds_the_table():
    with open(TABLE, encoding="utf-8") as f:
        figures = telling(json.load(f))
    scanned, copies = 0, {}
    for spec in SOURCES:
        for path in glob.glob(os.path.join(ROOT, *spec.split("/"))):
            name = os.path.basename(path)
            if not os.path.isfile(path) or os.path.abspath(path) == os.path.abspath(TABLE) or name.startswith("test_"):
                continue
            with open(path, encoding="utf-8", errors="replace") as f:
                found = copied(f.read(), figures)
            scanned += 1
            if len(found) >= 3:
                copies[os.path.relpath(path, ROOT)] = found
    assert scanned > 50, f"only {scanned} source files looked at: the folders have moved"
    assert not copies, (
        f"a second copy of the Reach rank table: {copies}. Read tools/service_record_site/ranks.json instead (or a "
        "file the Service Record build writes from it), so the site and the game show the same rank.")


if __name__ == "__main__":
    test_the_detector()
    test_no_other_source_holds_the_table()
    print("ok")
    sys.exit(0)
