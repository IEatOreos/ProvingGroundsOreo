"""Pictures for the LiDAR view's maps list, read from the user's own MCC install (data/ui/texturepacks): the game logos
MCC's menus use (globaluitexturepack: HALOCEGAMEICON...) and each map's menu thumbnail (ingamechapterpack:
H1MP_BATTLECREEK, HREACHMP_SPIRELARGE...). Writes tools/view_art/games/<game>.png and tools/view_art/maps/<map>.jpg.

Real map names come from tools/view_art/names.json ({map folder: name}, kept with the project). A map's thumbnail is
the texture with its game's prefix and its name in capitals without spaces or punctuation (an optional S3D_ before
the name, an optional LARGE after it; the small one is preferred). Maps MCC has no picture for get their own top-down
picture. Pack layout: 16-byte segment headers (size at +8); a texture's 464-byte name record has its name at +52, its
data size at +120 and its offset into the .temp.bin at +128; streamed packs keep the data three segments before the
name record. Thumbnails are BC1, 316x158 or 668x292.

usage: python -I map_art.py [--mcc <MCC install folder>]
"""
import io
import json
import os
import re
import struct
import sys

from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from brain import paths  # noqa: E402  (where MCC is installed)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(HERE, "view_art")
MCC = paths.mcc()
PREFIX = {"ce": ("H1MP_",), "h2": ("H2MP_",), "h2a": ("H2MPA_",), "h3": ("H3MP_",), "h4": ("H4MP_",),
          "reach": ("HREACHMP_", "REACHFIREFIGHT_"), "odst": ("ODSTFIREFIGHT_",)}
ICONS = {"ce": "HALOCEGAMEICON", "h2": "HALO2GAMEICON", "h2a": "HALO2AGAMEICON", "h3": "HALO3GAMEICON",
         "odst": "HALO3ODSTGAMEICON", "reach": "HALOREACHGAMEICON", "h4": "HALO4GAMEICON"}
THUMB_SIZES = {25280: (316, 158), 97528: (668, 292)}      # BC1 data size -> pixels
THUMB_W = 316
INFO_DIR = {"h3": "halo3", "odst": "halo3odst", "reach": "haloreach", "h4": "halo4", "h2a": "groundhog"}
# thumbnails not named after the map (Halo 2 Anniversary's are named after the Halo 2 original, its folder name)
ODD_THUMBS = {"h2_foundation": "H2MP_FOUNDATIONS", "odst_h100": "ODSTFIREFIGHT_RALLYPOINTNIGHT_LARGE",
              "odst_sc100": "ODSTFIREFIGHT_CRATERDAY_LARGE", "odst_sc120": "ODSTFIREFIGHT_RALLYPOINTDAY_LARGE"}


def dds(data, w, h, fourcc):
    """A BC1/BC3 block image as a PIL image (wrapped in a minimal DDS header)."""
    hdr = struct.pack("<4sIIIIIII44sII4s20sIIIII", b"DDS ", 124, 0x81007, h, w, len(data), 0, 0, b"\0" * 44,
                      32, 4, fourcc, b"\0" * 20, 0x1000, 0, 0, 0, 0)
    return Image.open(io.BytesIO(hdr + data))


def pack(path):
    """{texture name: (bytes, data size)}: the data from the .temp.bin when the pack has one, else from the
    segment three before the name record (streamed packs)."""
    b = open(path + ".perm.bin", "rb").read()
    temp = open(path + ".temp.bin", "rb").read() if os.path.exists(path + ".temp.bin") else None
    segs, p = [], 0
    while p + 16 <= len(b):
        size = struct.unpack_from("<i", b, p + 8)[0]
        segs.append((p + 16, size))
        p += 16 + size
    out = {}
    for i, (st, size) in enumerate(segs):
        m = re.match(rb"([A-Za-z0-9_]+)\x00", b[st + 52:st + 120]) if size == 464 else None
        if not m:
            continue
        n, off = struct.unpack_from("<ii", b, st + 120)[0], struct.unpack_from("<i", b, st + 128)[0]
        if temp is not None:
            out[m.group(1).decode()] = temp[off:off + n]
        elif i >= 3 and segs[i - 3][1] == n:
            st3 = segs[i - 3][0]
            out[m.group(1).decode()] = b[st3:st3 + n]
    return out


def info_name(mcc, folder):
    """A map's English name from MCC's maps/info/<map>.mapinfo (UTF-16, 32 characters at byte 69), "" without one
    (Halo: CE and Halo 2 have no .mapinfo files: their names are all in names.json)."""
    game = folder.split("_")[0]
    if game not in INFO_DIR:
        return ""
    try:
        b = open(os.path.join(mcc, INFO_DIR[game], "maps", "info", folder[len(game) + 1:] + ".mapinfo"), "rb").read()
    except OSError:
        return ""
    name = b[69:133].decode("utf-16-le", "ignore").split("\0")[0].strip()
    return "" if name.startswith("$") else name          # ("$s3d_turf": a placeholder, no name)


def thumbnail(folder, name, thumbs):
    """The thumbnail texture of a map folder with this real name (None: MCC has none), the small one before LARGE."""
    if folder in ODD_THUMBS:
        return ODD_THUMBS[folder] if ODD_THUMBS[folder] in thumbs else None
    if not name:
        return None
    game = folder.split("_")[0] if folder.split("_")[0] in PREFIX else "ce"
    keys = [re.sub(r"[^A-Z0-9]", "", s.upper()) for s in (name, folder.removeprefix(game + "_ca_"))]
    rx = re.compile("(?:" + "|".join(PREFIX[game]) + r")(?:S3D_)?(?:" + "|".join(keys) + ")(_?LARGE)?$")
    hits = sorted((t for t in thumbs if rx.match(t)), key=lambda t: ("LARGE" in t, t))
    return hits[0] if hits else None


def drawn_logo(game):
    """A plain logo (the game's short name in a frame) where MCC's own is not on this PC."""
    from PIL import ImageDraw, ImageFont
    text = {"ce": "CE", "h2": "H2", "h2a": "H2A", "h3": "H3", "odst": "ODST", "reach": "REACH", "h4": "H4"}[game]
    im = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 24, 115, 95), 12, outline=(222, 230, 240, 255), width=4)
    try:
        font = ImageFont.truetype("segoeuib.ttf", 34 if len(text) < 4 else 24)
    except OSError:
        font = ImageFont.load_default(28)
    d.text((60, 60), text, font=font, fill=(222, 230, 240, 255), anchor="mm")
    return im


def main():
    mcc =sys.argv[sys.argv.index("--mcc") + 1] if "--mcc" in sys.argv else MCC
    tex = os.path.join(mcc, "data", "ui", "texturepacks")
    for sub in ("games", "maps"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    # MCC's menu art; a copy of MCC without it (files missing or damaged) gets plain logos and top-down pictures
    have = lambda name: os.path.exists(os.path.join(tex, name + ".perm.bin"))   # noqa: E731
    ui = pack(os.path.join(tex, "globaluitexturepack")) if have("globaluitexturepack") else {}
    for game, name in ICONS.items():
        if name in ui:
            im = dds(ui[name], 120, 120, b"DXT5").convert("RGBA")     # 14400 bytes of BC3 = 120x120
        else:
            im = drawn_logo(game)
        im.crop(im.getchannel("A").point(lambda a: 255 if a > 24 else 0).getbbox()).save(os.path.join(OUT, "games", game + ".png"))
    thumbs = {k: v for k, v in pack(os.path.join(tex, "ingamechapterpack")).items()
              if len(v) in THUMB_SIZES} if have("ingamechapterpack") else {}
    names = json.load(open(os.path.join(OUT, "names.json"), encoding="utf-8"))
    missing = []
    for folder in sorted(os.listdir(os.path.join(ROOT, "maps"))):
        if folder not in names and info_name(mcc, folder):
            names[folder] = info_name(mcc, folder)
    json.dump(dict(sorted(names.items())), open(os.path.join(OUT, "names.json"), "w", encoding="utf-8"), indent=1)
    for folder in sorted(os.listdir(os.path.join(ROOT, "maps"))):
        d = os.path.join(ROOT, "maps", folder)
        if folder.startswith("_") or not os.path.exists(os.path.join(d, "heightmap.npz")):
            continue
        t = thumbnail(folder, names.get(folder), thumbs)
        im = dds(thumbs[t], *THUMB_SIZES[len(thumbs[t])], b"DXT1").convert("RGB") if t else None
        if im is None:                                     # not in MCC: the map's own top-down picture
            missing.append(folder)
            im = Image.new("RGB", (THUMB_W, THUMB_W // 2), (11, 15, 20))
            if os.path.exists(os.path.join(d, "topdown.png")):
                top = Image.open(os.path.join(d, "topdown.png")).convert("RGB")
                top.thumbnail((THUMB_W, THUMB_W // 2))
                im.paste(top, ((THUMB_W - top.width) // 2, (THUMB_W // 2 - top.height) // 2))
        if im.width > THUMB_W:
            im = im.resize((THUMB_W, round(im.height * THUMB_W / im.width)), Image.LANCZOS)
        im.save(os.path.join(OUT, "maps", folder + ".jpg"), quality=85)
    if not ui or not thumbs:
        print("MCC's menu art (data\\ui\\texturepacks) is missing from this copy of MCC: plain logos and top-down "
              "pictures instead (Steam can repair it: MCC > Properties > Installed Files > Verify integrity)")
    else:
        print(f"{len(ICONS)} game logos; MCC has no picture for: {', '.join(missing) or 'none'}")


if __name__ == "__main__":
    main()
