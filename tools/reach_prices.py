"""(custom, Nov 19) Project Reach's Reach Armory price list: maps/_looks/reach_prices.json.

The owner: every Reach item purchasable with credits, as in the 2010 Armory; MCC keeps everything unlocked and
untouched, and Project Reach's own Armory decides what the player may wear. The prices and rank gates are Halo: Reach's
own, read from the Halo: Reach Editing Kit's ui/supply_depot.cookie_purchase_globals (each item's credit cost, its
minimum rank as a grade and sub grade, the items it needs bought first, its default / auto-buy flags). Each priced
family lines up one to one with the Armory's catalog botcore logged (maps/_looks/reach_armory.json "writes": per slot,
family and variant the configuration bytes the game's own equip sets), so each item gets the exact bytes it puts on.
Names: native/look_names.h (the Armory's own names, by table index).

The 2010 Armory left some items without a credit price (pre-order, Waypoint, Bungie and limited-edition unlocks), and
MCC added helmets, chests and a utility the 2010 list never had. They get prices of our own (OURS below, "source":
"ours" in the file), so that every item can be bought; change them here and run this again.

The rank gate stays a grade here (1 Recruit .. 21 Reclaimer, the sub grade 1 the rank itself, 2 its Grade 1, ...):
tools/service_record.py turns it into the Service Record's rank step with ranks.json, the one rank table.

usage: python -I tools/reach_prices.py [--tag <supply_depot.cookie_purchase_globals>] [--hrek <HREK folder>]
Without --tag, the tag is taken from the Editing Kit's HREK.7z (7-Zip, into a temporary folder)."""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOKS = os.path.join(ROOT, "maps", "_looks")
OUT = os.path.join(LOOKS, "reach_prices.json")
NAMES = os.path.join(ROOT, "native", "look_names.h")
TAG = r"tags\ui\supply_depot.cookie_purchase_globals"
HREK = r"C:\Program Files (x86)\Steam\steamapps\common\HREK"
SEVEN = r"C:\Program Files\7-Zip\7z.exe"

# the Armory's slots in the tag's order, as reach_armory.json "writes" numbers them: (tag family block, our key, the
# look_names.h list). Config offsets are the appearance block's (+0x20) plus the writes' offset.
SLOTS = [("helmet", "helmet", "ED_REACH_HELMET"), ("left shoulder", "left_shoulder", "ED_REACH_LEFT_SHOULDER"),
         ("right shoulder", "right_shoulder", "ED_REACH_RIGHT_SHOULDER"), ("chest", "chest", "ED_REACH_CHEST"),
         ("wrist", "wrist", "ED_REACH_WRIST"), ("utility", "utility", "ED_REACH_UTILITY"),
         ("visor tint", "visor", "ED_REACH_VISOR"), ("paint scheme", "knees", "ED_REACH_KNEES"),
         ("armor effect", "armor_effect", "ED_REACH_ARMOR_EFFECT"), ("elite armor", "elite_armor", "ED_REACH_ELITE_ARMOR")]
APPEARANCE = 0x20

# Our prices for what the 2010 Armory did not sell for credits. (cost, grade, needs): needs the ids bought first.
# Unlock-only originals: priced near their family's neighbours; the two flame effects as the dearest effects.
OURS_UNLOCKS = {
    "helmet_20_b": (100000, 9, ["helmet_20_a"]),             # Recon / UA/HUL(3): the pre-order bonus
    "helmet_17_base": (75000, 6, []), "helmet_17_a": (25000, 6, ["helmet_17_base"]),
    "helmet_17_b": (25000, 6, ["helmet_17_a"]),              # Military Police: Waypoint
    "helmet_18_base": (60000, 5, []), "helmet_18_a": (20000, 5, ["helmet_18_base"]),
    "helmet_18_b": (20000, 5, ["helmet_18_a"]),              # CQB: Waypoint
    "chest_14": (50000, 6, []),                              # UA/Multi-Threat [W]: a store bonus
    "chest_15": (50000, 6, []),                              # UA/Base Security [W]: Waypoint
    "armor_fx_legendary": (1500000, 13, []),                 # Legendary (Flaming Helmet): the Legendary Edition
    "armor_fx_blue": (2500000, 15, []),                      # Eternal (blue flames): Bungie's own
    "elite_limited": (100000, 8, []),                        # Officer: the Limited Edition
}
# MCC's additions, by table index (look_names.h): helmet sets (base, then its variants, each needing the one before),
# the [R] chests (each needing its plain chest's table index), Condemned, the Vacuum Flask
MCC_HELMET_SETS = [(64, [65, 66, 67]), (68, [69, 70, 71]), (72, [73, 74, 75, 76, 77]), (78, [79, 80, 81, 82, 83]),
                   (84, [85, 86, 87, 88, 89])]
MCC_HELMET = (150000, 10, 40000)                            # a set's base: cost, grade; each variant's cost
MCC_CHEST = {1: (400, 1, None), 2: (400, 1, None),        # (cost, grade, needs: the chest's table index)
             20: (100000, 10, 0), 21: (100000, 10, 8), 22: (100000, 10, 6), 23: (100000, 10, 13),
             24: (100000, 10, 4), 25: (150000, 11, None)}
MCC_UTILITY = {6: (75000, 8)}


# ---------------------------------------------------------------------------------------------- the tag file
class Tag:
    """An editing-kit tag file (MCC's layout v3 + data stream), read by its own layout: blocks, structs, fields."""

    def __init__(self, data):
        self.b = data
        blay = self._find(b"yalb")
        tgly = data.find(b"ylgt", blay)
        _, _, size, d = self._chunk(tgly)
        self.L = {}
        o = d
        while o < d + size:
            sig, _, csize, cd = self._chunk(o)
            self.L[sig] = (cd, csize)
            o = cd + csize
        self.types = [(self._s(n), sz, flag) for n, sz, flag in self._rows("tgft", 3)]
        self.fields = [(self._s(n), t, df) for n, t, df in self._rows("gras", 3)]
        self.blocks = [(self._s(n), mx, st) for n, mx, st in self._rows("blv2", 3)]
        sd, ss = self.L["stv2"]
        self.structs = [(self._s(struct.unpack_from("<i", data, sd + i + 16)[0]),
                         struct.unpack_from("<i", data, sd + i + 20)[0]) for i in range(0, ss, 24)]
        self.szx = [v[0] for v in self._rows("sz+x", 1)]
        self.lists = [(self._s(n), cnt, first) for n, cnt, first in self._rows("sz[]", 3)]
        self.arrays = self._rows("arr!", 3) if "arr!" in self.L else []
        self.end_layout = d + size

    def _find(self, sig):
        o = self.b.find(sig)
        if o < 0:
            raise ValueError("not an editing-kit tag file (no layout)")
        return o

    def _chunk(self, o):
        sig = self.b[o:o + 4][::-1].decode("latin1")
        a, size = struct.unpack_from("<II", self.b, o + 4)
        return sig, a, size, o + 12

    def _s(self, off):
        sd = self.L["str*"][0]
        e = self.b.index(b"\0", sd + off)
        return self.b[sd + off:e].decode("latin1")

    def _rows(self, sig, n):
        d, size = self.L[sig]
        return [struct.unpack_from("<" + "i" * n, self.b, d + i) for i in range(0, size, 4 * n)]

    def fields_of(self, si):
        out, i = [], self.structs[si][1]
        while True:
            nm, t, df = self.fields[i]
            tn, sz, flag = self.types[t]
            if tn == "terminator X":
                return out
            out.append((nm, tn, sz, flag, df))
            i += 1

    def size_of(self, si):
        total = 0
        for nm, tn, sz, flag, df in self.fields_of(si):
            if tn == "struct":
                total += self.size_of(df)
            elif tn == "array":
                total += self.arrays[df][1] * self.size_of(self.arrays[df][2])
            elif tn in ("pad", "skip", "useless pad"):
                total += df
            else:
                total += sz
        return total

    def _raw(self, si, o):
        vals = {}
        for nm, tn, sz, flag, df in self.fields_of(si):
            if tn == "struct":
                vals[nm] = self._raw(df, o)
                o += self.size_of(df)
                continue
            if tn == "array":
                _, cnt, st = self.arrays[df]
                vals[nm] = []
                for _ in range(cnt):
                    vals[nm].append(self._raw(st, o))
                    o += self.size_of(st)
                continue
            if tn in ("pad", "skip", "useless pad"):
                o += df
                continue
            raw = self.b[o:o + sz]
            if sz == 4 and tn != "real":
                v = struct.unpack("<i", raw)[0]
            elif sz == 2:
                v = struct.unpack("<h", raw)[0]
            elif sz == 1:
                v = struct.unpack("<b", raw)[0]
            elif tn == "real":
                v = struct.unpack("<f", raw)[0]
            else:
                v = raw.hex()
            if tn.endswith("enum"):
                name, cnt, first = self.lists[df]
                v = self._s(self.szx[first + v]) if 0 <= v < cnt else v
            if sz:
                vals[nm] = v
            o += sz
        return vals

    def _children(self, si, vals, o):
        for nm, tn, sz, flag, df in self.fields_of(si):
            if tn == "struct":
                sig, _, size, d = self._chunk(o)
                assert sig == "tgst", (sig, nm, hex(o))
                self._children(df, vals[nm], d)
                o = d + size
                continue
            if tn == "array":
                _, cnt, st = self.arrays[df]
                for k in range(cnt):
                    o = self._children(st, vals[nm][k], o)
                continue
            if not flag:
                continue
            sig, _, size, d = self._chunk(o)
            if tn == "block":
                assert sig == "tgbl", (sig, nm, hex(o))
                vals[nm] = self.block(self.blocks[df][2], d, size)
            else:                                            # string ids (tgsi), tag references (tgrf): their text
                vals[nm] = self.b[d:d + size].decode("latin1")
            o = d + size
        return o

    def block(self, si, d, size):
        count = struct.unpack_from("<I", self.b, d)[0]
        o, step = d + 8, self.size_of(si)
        elems = []
        for _ in range(count):
            elems.append(self._raw(si, o))
            o += step
        for e in elems:
            if o >= d + size:
                break
            sig, _, csize, cd = self._chunk(o)
            if sig != "tgst":
                break
            self._children(si, e, cd)
            o = cd + csize
        return elems

    def root(self, block_name):
        bi = [i for i, bl in enumerate(self.blocks) if bl[0] == block_name][0]
        tadb = self.b.find(b"tadb", self.end_layout)
        _, _, _, td = self._chunk(tadb)
        sig, _, size, d = self._chunk(td)
        assert sig == "tgbl", sig
        return self.block(self.blocks[bi][2], d, size)


# ---------------------------------------------------------------------------------------------- the price list
def look_names(path=NAMES):
    """{list name: {table index: name}} from native/look_names.h."""
    with open(path, encoding="utf-8") as f:
        h = f.read()
    out = {}
    for m in re.finditer(r"static const piece (ED_\w+)\[\] = \{(.*?)\};", h, re.S):
        out[m.group(1)] = {int(v): n for v, n in re.findall(r'\{(\d+), "([^"]*)"\}', m.group(2))}
    return out


def grade(item):
    """(grade, sub grade) the item's purchase needs; (1, 1) none."""
    g = item["purchasable prerequisites"]["prerequisite grades"]
    if not g:
        return 1, 1
    return int(g[0]["minimum grade"].split()[-1]), int(g[0]["minimum sub grade"].split()[-1])


def build(cookie, writes, names):
    items = cookie["purchasable items"]
    unlocks = {}
    for kind in ("DLC unlockables", "Waypoint unlockables"):
        for u in cookie[kind]:
            for q in u["purchasable items"]:
                unlocks[q["purchasable item reference"]["item reference"]] = kind.split()[0].lower()
    out = []
    by_tag = {}                                              # tag item index -> our id
    for s, (fam_key, key, nl) in enumerate(SLOTS):
        for f, fam in enumerate(cookie[fam_key + " purchasable families"]):
            for v, ref in enumerate(fam["purchasable items"]):
                i = ref["purchasable item reference"]["item reference"]
                by_tag[i] = items[i]["purchase id"]
    for s, (fam_key, key, nl) in enumerate(SLOTS):
        for f, fam in enumerate(cookie[fam_key + " purchasable families"]):
            for v, ref in enumerate(fam["purchasable items"]):
                i = ref["purchasable item reference"]["item reference"]
                x = items[i]
                w = {int(off) + APPEARANCE: val for off, val in writes[s][f][v].items()}
                first = min(w)
                g, sub = grade(x)
                needs = [by_tag[p["item reference"]["item reference"]]
                         for p in x["purchasable prerequisites"]["prerequisite purchased items"]]
                unl = [u["unlockable name"] for u in x["purchasable prerequisites"]["prerequisite unlockables"]]
                flags = x["flags"]
                it = {"id": x["purchase id"], "slot": key, "family": f, "variant": v,
                      "name": names[nl].get(w[first], "Item %d" % w[first]), "writes": {str(o): w[o] for o in sorted(w)},
                      "cost": x["cookie cost"], "grade": g, "sub": sub, "needs": needs,
                      "default": bool(flags & 2), "auto": bool(flags & 1) and not (flags & 2), "source": "2010"}
                if unl or i in unlocks:
                    it["unlock"] = (unl[0] if unl else unlocks[i])
                if it["id"] in OURS_UNLOCKS:
                    cost, gr, nd = OURS_UNLOCKS[it["id"]]
                    it.update(cost=cost, grade=gr, sub=1, needs=nd, auto=False, source="ours")
                elif "unlock" in it and not it["default"] and not it["auto"]:
                    raise ValueError("an unlock-only item without our price: " + it["id"])
                out.append(it)
    # MCC's additions (none of them in the 2010 tag's families)
    fam0 = 1 + max(it["family"] for it in out if it["slot"] == "helmet")
    hcost, hgrade, vcost = MCC_HELMET
    for k, (base, variants) in enumerate(MCC_HELMET_SETS):
        prev = None
        for v, idx in enumerate([base] + variants):
            iid = "mcc_helmet_%d" % idx
            out.append({"id": iid, "slot": "helmet", "family": fam0 + k, "variant": v,
                        "name": names["ED_REACH_HELMET"][idx], "writes": {str(0x38 + APPEARANCE): idx},
                        "cost": hcost if v == 0 else vcost, "grade": hgrade, "sub": 1, "needs": [prev] if prev else [],
                        "default": False, "auto": False, "source": "ours"})
            prev = iid
    chest_ids = {list(it["writes"].values())[0]: it["id"] for it in out if it["slot"] == "chest"}
    for idx, (cost, gr, need) in MCC_CHEST.items():
        tag_id = {1: "chest_01", 2: "chest_02"}.get(idx)     # (the tag's own two, outside its families)
        out.append({"id": tag_id or "mcc_chest_%d" % idx, "slot": "chest", "family": 0,
                    "variant": 100 + idx, "name": names["ED_REACH_CHEST"][idx], "writes": {str(0x3B + APPEARANCE): idx},
                    "cost": cost, "grade": gr, "sub": 1, "needs": [chest_ids[need]] if need is not None else [],
                    "default": False, "auto": False, "source": "ours"})
    for idx, (cost, gr) in MCC_UTILITY.items():
        out.append({"id": "mcc_utility_%d" % idx, "slot": "utility", "family": 0, "variant": 100 + idx,
                    "name": names["ED_REACH_UTILITY"][idx], "writes": {str(0x3D + APPEARANCE): idx},
                    "cost": cost, "grade": gr, "sub": 1, "needs": [], "default": False, "auto": False, "source": "ours"})
    ids = [it["id"] for it in out]
    if len(set(ids)) != len(ids):
        raise ValueError("an item id twice")
    for it in out:
        for n in it["needs"]:
            if n not in ids:
                raise ValueError(it["id"] + " needs an item not in the list: " + n)
    return out


def tag_bytes(args):
    if args.tag:
        with open(args.tag, "rb") as f:
            return f.read()
    archive = os.path.join(args.hrek, "HREK.7z")
    tmp = tempfile.mkdtemp(prefix="reach_prices_")
    try:
        subprocess.run([SEVEN, "e", archive, "-o" + tmp, "-y", TAG], check=True, stdout=subprocess.DEVNULL)
        with open(os.path.join(tmp, os.path.basename(TAG)), "rb") as f:
            return f.read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tag")
    ap.add_argument("--hrek", default=HREK)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    cookie = Tag(tag_bytes(args)).root("cookie_purchase_globals_block")[0]
    with open(os.path.join(LOOKS, "reach_armory.json"), encoding="utf-8") as f:
        writes = json.load(f)["writes"]
    items = build(cookie, writes, look_names())
    doc = {"how": __doc__.split("\n\n")[1].replace("\n", " ") + " Made by tools/reach_prices.py; do not edit.",
           "grades": "1 Recruit, 2 Private, 3 Corporal, 4 Sergeant, 5 Warrant Officer, 6 Captain, 7 Major, "
                     "8 Lt. Colonel, 9 Commander, 10 Colonel, 11 Brigadier, 12 General, 13 Field Marshal, 14 Hero, "
                     "15 Legend, 16 Mythic, 17 Noble, 18 Eclipse, 19 Nova, 20 Forerunner, 21 Reclaimer; sub 1 the "
                     "rank, 2 its Grade 1, ...",
           "items": items}
    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    os.replace(tmp, args.out)
    print("%d items (%d priced by the 2010 Armory, %d ours) -> %s" % (
        len(items), sum(it["source"] == "2010" for it in items), sum(it["source"] == "ours" for it in items), args.out))


if __name__ == "__main__":
    sys.exit(main())
