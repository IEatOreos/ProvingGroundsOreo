"""MCC's own emblems for the bots (brain/emblems.py). Every game's scoreboard and MCC's post-game report draw a player's
MCC emblem (MCC renders one per player, PlayerEmblemTarget<n>, from its player lookup by Xbox id, which botcore
answers for the bots: native/report.cpp), so a bot's emblem is one of MCC's.

extract: MCC's catalog (Data/UI/playercustomization.xml: the foregrounds with both layers, the backgrounds, the 31
emblem colours) -> maps/_looks/mcc_emblems.json, and its art (the 256 x 256 layers in Data/UI/texturepacks/
mainmenuandcampaigntexturepack: 480-byte entries in .perm.bin, name at +0x44, format +0x68 (3 = BC3), width and
height +0x74, data size +0x88 and offset +0x90 in .temp.bin) -> maps/_models/emblems_mcc/<layer>.png, each layer's
shape (game data: not in git).

usage: python -I emblems.py extract [MCC folder]     once per install (tools/make_models.py runs it)
       python -I emblems.py sheet <out.png>          every bot's emblem on one picture (a check)
"""
import io
import json
import os
import re
import struct
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from brain import paths  # noqa: E402  (where MCC, the mod kits and Visual Studio are)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
from brain import emblems  # noqa: E402


def pretty(key):
    """"$EMBLEM_FORE_SPARTAN_SWORDS" -> "Spartan Swords" (the name key, for reading the catalog)."""
    w = [x for x in key.lstrip("$").split("_") if x and x.upper() not in ("EMBLEM", "FORE", "BACK")]
    return " ".join(x.capitalize() for x in w)


def catalog(xml):
    """{"foregrounds": [[id, primary layer, secondary layer, name]], "backgrounds": [[id, layer, name]],
    "colours": {id: [r, g, b, a]}} from MCC's playercustomization.xml (comments dropped)."""
    s = re.sub(r"<!--.*?-->", "", open(xml, encoding="utf-8", errors="replace").read(), flags=re.S)
    fg, bg = [], []
    for attrs in re.findall(r"<Emblem\s([^>]*)>", s[s.index("<Emblems>"):s.index("</Emblems>")]):
        a = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
        if all(k in a for k in ("image1", "image2", "image1_small", "image2_small")):
            fg.append([int(a["id"]), a["image1"].upper(), a["image2"].upper(), pretty(a.get("name", ""))])
        elif "background" in a and "background_small" in a:
            bg.append([int(a["id"]), a["background"].upper(), pretty(a.get("name", ""))])
    colours = {}
    for attrs in re.findall(r"<Color\s([^>]*)>", s[s.index("<Colors>"):s.index("</Colors>")]):
        a = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
        colours[int(a["id"])] = [float(a["r"]), float(a["g"]), float(a["b"]), float(a.get("a", 1))]
    return {"foregrounds": fg, "backgrounds": bg, "colours": colours}


def bc3(w, h, data):
    """A BC3 (DXT5) picture as PIL RGBA, through a DDS header."""
    from PIL import Image
    hdr = struct.pack("<4sIIIIIII44sIII20sIIIII", b"DDS ", 124, 0x81007, h, w, len(data), 0, 1, b"\0" * 44,
                      32, 4, 0x35545844, b"\0" * 20, 0x1000, 0, 0, 0, 0)
    return Image.open(io.BytesIO(hdr + data)).convert("RGBA")


def layers(mcc, wanted):
    """{layer name: PIL picture} for the wanted names found in MCC's main menu texture pack (BC3 only)."""
    pack = os.path.join(mcc, "Data", "UI", "texturepacks", "mainmenuandcampaigntexturepack")
    perm, out = open(pack + ".perm.bin", "rb").read(), {}
    with open(pack + ".temp.bin", "rb") as temp:
        for k in range(len(perm) // 480):
            e = perm[k * 480:(k + 1) * 480]
            name = e[0x44:0x64].split(b"\0")[0].decode("latin1")
            fmt = struct.unpack_from("<I", e, 0x68)[0]
            w, h = struct.unpack_from("<HH", e, 0x74)
            size, at = struct.unpack_from("<QQ", e, 0x88)
            if name in wanted and name not in out and fmt == 3 and size == w * h:
                temp.seek(at)
                out[name] = bc3(w, h, temp.read(size))
    return out


def extract(mcc):
    need = [os.path.join(mcc, "Data", "UI", "playercustomization.xml")] + [
        os.path.join(mcc, "Data", "UI", "texturepacks", "mainmenuandcampaigntexturepack" + x) for x in (".perm.bin", ".temp.bin")]
    if not all(os.path.exists(p) for p in need):     # (a copy of MCC with its menu files missing: no emblems, no stop)
        print("emblems skipped: MCC's menu files (Data\\UI) are missing from this copy of MCC")
        return
    cat = catalog(need[0])
    wanted = {n for f in cat["foregrounds"] for n in f[1:3]} | {b[1] for b in cat["backgrounds"]}
    pics = layers(mcc, wanted)
    # only emblems whose every layer is there (MCC's renderer refuses one with a layer missing)
    cat["foregrounds"] = [f for f in cat["foregrounds"] if f[1] in pics and f[2] in pics]
    cat["backgrounds"] = [b for b in cat["backgrounds"] if b[1] in pics]
    os.makedirs(emblems.ART, exist_ok=True)
    for name, img in pics.items():
        img.getchannel("A").save(os.path.join(emblems.ART, name + ".png"))     # the shape: MCC tints it
    with open(emblems.CATALOG, "w", encoding="utf-8", newline="\n") as f:
        f.write('{"foregrounds": [\n' + ",\n".join("  " + json.dumps(x) for x in cat["foregrounds"]) + "],\n")
        f.write(' "backgrounds": [\n' + ",\n".join("  " + json.dumps(x) for x in cat["backgrounds"]) + "],\n")
        f.write(' "colours": {\n' + ",\n".join(f'  "{k}": {json.dumps(v)}' for k, v in cat["colours"].items()) + "}}\n")
    print(f"{len(cat['foregrounds'])} foregrounds, {len(cat['backgrounds'])} backgrounds, {len(cat['colours'])} colours,"
          f" {len(pics)} layers -> {emblems.ART}")


def sheet(out):
    from PIL import Image, ImageDraw
    from brain import looks
    bots = looks.profiles(looks.PROFILES)
    S = 112
    img = Image.new("RGB", (S * 8, (S + 16) * ((len(bots) + 7) // 8)), (24, 28, 34))
    d = ImageDraw.Draw(img)
    for k, (name, _) in enumerate(bots):
        e = emblems.compose(emblems.roll(looks.seed_of(name, looks.PROFILES)), S)
        x, y = (k % 8) * S, (k // 8) * (S + 16)
        if e is not None:
            img.paste(e, (x, y), e)
        d.text((x + 4, y + S), name[:16], fill=(220, 220, 220))
    img.save(out)
    print(out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["extract"]:
        extract(sys.argv[2] if len(sys.argv) > 2 else paths.mcc())
    elif sys.argv[1:2] == ["sheet"]:
        sheet(sys.argv[2])
    else:
        sys.exit(__doc__)
