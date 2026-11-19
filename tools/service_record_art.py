"""The Service Record's medal names and icons, read from this PC's own copy of MCC (custom, Nov 15: the owner asked
for "all the medals from mcc"). MCC's post-game report counts medals by MCC's own number (Medal mId, 0..383) and
names none of them; three of MCC's files do:

  MCC\\Binaries\\Win64\\MCC-Win64-Shipping.exe   the number of each medal id: one function compares a name with every
        id in turn (lea rdx,[the id's text]; call; test eax,eax; jne; then ebx = the number: lea ebx,[rax+n],
        lea ebx,[rdi+n] with rdi -1, or mov ebx,n; the last id: mov ecx,n; cmove). Found from the text
        "medal_first_place", so a new MCC build is read the same way; when the function is not as decoded, nothing
        is written.
  data\\careerdb\\careerdb.xml                    each id's name key, icon and kind (MPMedals, MissionMedals)
  data\\ui\\texturepacks\\medalstexturepack      the icons, 80 x 80 BC3 (the texture pack format of tools/emblems.py)

Writes native/bin/service_record/art/medals/<number>.png and art/medals.json ({number: {key, name, icon, kind}});
tools/service_record.py copies the earned ones into the site. Game data: not in git. A medal with no icon in the
pack keeps its name and the site's own placeholder.

The rank insignia (the owner, Nov 15: "extract every insignia rank from the photo for each rank"): `ranks` cuts
them from his picture of the rank chart, a black sheet with one row of square framed tiles per rank, a tile per
Grade. The tiles are found by their lit frames; their rows must hold exactly the tiles the rank table holds
(service_record_site/ranks.json: 1, 1, 2, 3, 4 ... 5, then 1 each), else nothing is written and the site keeps
its own numbered placeholders. Writes art/ranks/<step>.png (the step's place in the table, 0 = Recruit; the
tile's black made see-through) and keeps a copy of the picture beside them. Not in git either.

Sharper ones (the owner then gave a page that shows each rank's own 91 x 91 picture; those 50, downloaded once with
his OK into art/rank_icons as <step>_<the page's file name>): `ranks <folder>` takes a folder of one picture a
step instead, each file's name starting with its step's number, 0 to the table's last, each once (else nothing is
written). A picture keeps its own see-through parts and is centred on a square. No address is kept here: this tool
never downloads.

The weapons' pictures (the owner, Nov 15: "Make all the weapons have their png picture like the original website"):
`weapons` reads the ones MCC itself draws on its post-game Tools of Destruction, 352 x 100 line drawings, one for
every damage type of careerdb.xml's Weapons list, kept in globaluitexturepack and mainmenuandcampaigntexturepack.
service_record_site/weapon_art.json says which damage type each recorded number is. Writes art/weapons/<picture>
.png, cut to what is drawn, and art/weapons.json ({game: {number: file}}). Not in git either.

The player pages' pictures (the owner, Nov 16, a mockup of the old service record): `pictures` reads MCC's own
body-type drawings (mainmenutexturepack BODYTYPE_MALE, _FEMALE, _ELITE: the figure on a record's Overview, by the
bot's species and body) and Reach's map previews (levelstexturepack HREACHMP_<map>LARGE, 668 x 292: the recent
games' pictures). MCC has no picture of each armor piece: its armory draws the 3D model. Not in git either.

usage: python -I service_record_art.py medals [MCC folder]
       python -I service_record_art.py weapons [MCC folder]
       python -I service_record_art.py pictures [MCC folder]
       python -I service_record_art.py frames <the owner's tier frame sheet>
       python -I service_record_art.py emblems <the owner's tier emblem sheet> <commendation key>   (e.g. mvp)
       python -I service_record_art.py video [MCC folder]      (needs native\build_bink_to_mp4.bat first)
       python -I service_record_art.py ranks <the rank chart picture>
       python -I service_record_art.py ranks <a folder of one picture a step, each named <step>_...>
"""
import json
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "native", "bin", "service_record", "art")
RANKS_JSON = os.path.join(HERE, "service_record_site", "ranks.json")
WEAPON_ART = os.path.join(HERE, "service_record_site", "weapon_art.json")
WEAPON_PACKS = (os.path.join("data", "ui", "texturepacks", "globaluitexturepack"),
                os.path.join("data", "ui", "texturepacks", "mainmenuandcampaigntexturepack"))
TILE_SIZES = range(20, 49)     # a tile's side in the picture, pixels (the owner's chart: 28)
FRAME_LIT = 38                 # every pixel of a tile's frame is at least this bright (0-255); the sheet is black
INSIGNIA = 96                  # the side of each insignia written
EXE = os.path.join("MCC", "Binaries", "Win64", "MCC-Win64-Shipping.exe")
CAREERDB = os.path.join("data", "careerdb", "careerdb.xml")
PACK = os.path.join("data", "ui", "texturepacks", "medalstexturepack")
FIRST = b"medal_first_place"
LEA = re.compile(rb"[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]")
NUMBER = re.compile(rb"\x85\xc0(?:\x75.(?:\x8d\x58(.)|\x8d\x5f(.)|\xbb(.{4})|\x8d\x98(.{4}))|\xb9(.{4})\x0f\x44)", re.S)


def sections(data):
    """[(rva, virtual size, file offset, raw size)] of a 64-bit PE."""
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE file")
    count, = struct.unpack_from("<H", data, pe + 6)
    opt, = struct.unpack_from("<H", data, pe + 20)
    out = []
    for i in range(count):
        vsize, va, rsize, raw = struct.unpack_from("<IIII", data, pe + 24 + opt + 40 * i + 8)
        out.append((va, vsize, raw, rsize))
    return out


def medal_numbers(data):
    """{number: "medal_assist", ...} from MCC's exe (its bytes). ValueError when the lookup is not as decoded."""
    secs = sections(data)

    def to_rva(off):
        return next((va + off - raw for va, _, raw, rsize in secs if raw <= off < raw + rsize), None)

    def to_off(rva):
        return next((raw + rva - va for va, vsize, raw, rsize in secs if va <= rva < va + rsize), None)

    def text_at(rva):
        off = to_off(rva)
        if off is None:
            return None
        end = data.find(b"\0", off, off + 96)
        s = data[off:end] if end > off else b""
        return s.decode("ascii") if s and all(33 <= c < 127 for c in s) else None

    at = data.find(b"\0" + FIRST + b"\0")
    if at < 0:
        raise ValueError("no medal ids in this file")
    first_rva = to_rva(at + 1)
    code_va, _, code_raw, code_size = secs[0]
    code = data[code_raw:code_raw + code_size]
    start = None
    for m in LEA.finditer(code):
        k = m.start()
        if code_va + k + 7 + struct.unpack_from("<i", code, k + 3)[0] == first_rva:
            start = k
            break
    if start is None:
        raise ValueError("no code refers to the first medal id")
    out, k = {0: FIRST.decode()}, start + 7                   # (the first id leaves ebx at 0)
    while True:
        m = LEA.search(code, k, k + 96)
        if not m:
            break
        j = m.start()
        name = text_at(code_va + j + 7 + struct.unpack_from("<i", code, j + 3)[0])
        if not name or not name.startswith("medal_"):
            k = j + 1
            if k > start + 64 * 1024:
                break
            continue
        n = NUMBER.search(code, j + 7, j + 48)
        if not n:
            raise ValueError(f"{name}: its number is not where the others are")
        a, b, c, d, last = n.groups()
        number = (struct.unpack("<b", a)[0] if a else struct.unpack("<b", b)[0] - 1 if b else
                  struct.unpack("<i", c or d or last)[0])
        if number in out or not 0 < number < 4096:
            raise ValueError(f"{name}: number {number} is not a new medal number")
        out[number] = name
        k = n.end()
        if last:                                               # (the last id: mov ecx,n; cmove)
            break
    if len(out) < 100 or out.get(8) != "medal_assist":         # (medal 8 equals a player's assists in every report)
        raise ValueError(f"the medal lookup is not as decoded ({len(out)} ids)")
    return out


def pretty(name_key, medal_id):
    """ "$medal_Killing_Spree_name" -> "Killing Spree"; "$medal_ArmAssist_name" -> "Arm Assist"; the id when the
    key is missing."""
    s = re.sub(r"^\$?medal_|_name$", "", name_key or medal_id, flags=re.I)
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s.replace("_", " "))
    words = [w if (w.isupper() and len(w) <= 3 and len(s.split()) > 1) else w.capitalize() if (w.islower() or w.isupper()) else w
             for w in s.split()]
    return " ".join(words)


def catalog(xml_text):
    """{medal id: {"name", "icon", "kind"}} from careerdb.xml's MPMedals and MissionMedals (comments dropped)."""
    out = {}
    for block in ("MPMedals", "MissionMedals"):
        a, b = xml_text.find(f"<{block}>"), xml_text.find(f"</{block}>")
        if a < 0 or b < 0:
            continue
        body = re.sub(r"<!--.*?-->", "", xml_text[a:b], flags=re.S)
        for attrs in re.findall(r"<Medal\s([^>]*)>", body):
            m = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
            if m.get("id"):
                out.setdefault(m["id"].lower(), {
                    "name": pretty(m.get("name", ""), m["id"]), "icon": m.get("smallIcon", ""),
                    "kind": m.get("type", "").replace("eMedalType_", "")})
    return out


def icons(mcc, pack=PACK):
    """{TEXTURE NAME: (width, height, BC3 bytes)} from one of MCC's texture packs, medalstexturepack unless another
    is named (480-byte entries: name at +0x44, format +0x68 (3 = BC3), size +0x74, data size +0x88 and offset +0x90
    in .temp.bin). The first of a name is kept."""
    out = {}
    with open(os.path.join(mcc, pack + ".perm.bin"), "rb") as f:
        perm = f.read()
    with open(os.path.join(mcc, pack + ".temp.bin"), "rb") as temp:
        for k in range(len(perm) // 480):
            e = perm[k * 480:(k + 1) * 480]
            name = e[0x44:0x64].split(b"\0")[0].decode("latin1").upper()
            fmt = struct.unpack_from("<I", e, 0x68)[0]
            w, h = struct.unpack_from("<HH", e, 0x74)
            size, at = struct.unpack_from("<QQ", e, 0x88)
            if name and name not in out and fmt == 3 and size == w * h:
                temp.seek(at)
                out[name] = (w, h, temp.read(size))
    return out


def bc3(w, h, data, fourcc=0x35545844):
    """A BC3 (DXT5) picture as PIL RGBA, through a DDS header (as tools/emblems.py); fourcc DXT1 for a BC1 one."""
    import io
    from PIL import Image
    hdr = struct.pack("<4sIIIIIII44sIII20sIIIII", b"DDS ", 124, 0x81007, h, w, len(data), 0, 1, b"\0" * 44,
                      32, 4, fourcc, b"\0" * 20, 0x1000, 0, 0, 0, 0)
    return Image.open(io.BytesIO(hdr + data)).convert("RGBA")


def textures(mcc, pack, wanted):
    """{TEXTURE NAME: PIL RGBA} for the names `wanted(name)` accepts, from one of MCC's texture packs (the layout of
    icons()); a picture whose data is half its pixel count is BC1, one byte a pixel BC3; others are passed over."""
    out = {}
    with open(os.path.join(mcc, pack + ".perm.bin"), "rb") as f:
        perm = f.read()
    with open(os.path.join(mcc, pack + ".temp.bin"), "rb") as temp:
        for k in range(len(perm) // 480):
            e = perm[k * 480:(k + 1) * 480]
            name = e[0x44:0x64].split(b"\0")[0].decode("latin1").upper()
            if not name or name in out or not wanted(name):
                continue
            w, h = struct.unpack_from("<HH", e, 0x74)
            size, at = struct.unpack_from("<QQ", e, 0x88)
            fourcc = {w * h: 0x35545844, w * h // 2: 0x31545844}.get(size)
            if fourcc and w and h:
                temp.seek(at)
                out[name] = bc3(w, h, temp.read(size), fourcc)
    return out


MOVIE = os.path.join("MCC", "Content", "Movies", "NOBLE.bk2")
MOVIE_STILL = os.path.join("data", "ui", "BackgroundVideos", "Images", "Noble.png")
BINK = os.path.join("MCC", "Binaries", "Win64", "bink2w64.dll")


def video(mcc, out=OUT, tool=os.path.join(ROOT, "native", "bin", "bink_to_mp4.exe")):
    """The landing page's background: MCC's Noble main-menu movie (a Bink 2 file) as <out>/video/noble.mp4, decoded by
    MCC's own bink2w64.dll and encoded by Windows (native/bink_to_mp4.exe, native/build_bink_to_mp4.bat), and its
    still from MCC's menu, noble.png. Returns True when the movie was written."""
    os.makedirs(os.path.join(out, "video"), exist_ok=True)
    still = os.path.join(mcc, MOVIE_STILL)
    if os.path.exists(still):
        shutil.copyfile(still, os.path.join(out, "video", "noble.png"))
    need = [os.path.join(mcc, BINK), os.path.join(mcc, MOVIE), tool]
    lost = [p for p in need if not os.path.exists(p)]
    if lost:
        print("video skipped: no " + lost[0])
        return False
    import subprocess
    r = subprocess.run([tool, need[0], need[1], os.path.join(out, "video", "noble.mp4"), "1280"], capture_output=True, text=True)
    print((r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else "video: no output")
    return r.returncode == 0


FRAME_TIERS = ("iron", "bronze", "silver", "gold", "onyx", "max")


def frames(sheet, out=OUT):
    """The owner's commendation tier frames (Nov 16: one sheet, glowing frames on black, three a row, Iron Bronze
    Silver / Gold Onyx Max) cut into art/commendations/frames/<tier>.png on transparency (each pixel's alpha from its
    brightest channel, its colour unmixed from the black) and frames.json {tier: the opening [x0, y0, x1, y1]}, where
    the banner goes (service_record.py framed). The opening is found on the Iron frame (the dark inside around its
    middle) and used for all six: the frames share their shape. Returns how many were cut."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    a = np.asarray(Image.open(sheet).convert("RGB")).astype(np.float32)
    bright = a.max(axis=2) > 60
    lab, n = ndimage.label(ndimage.binary_dilation(bright, iterations=6))
    boxes = [b for b in ndimage.find_objects(lab) if (b[0].stop - b[0].start) * (b[1].stop - b[1].start) > a.size / 3 / 60]
    if len(boxes) != 6:
        raise ValueError(f"expected 6 frames on the sheet, found {len(boxes)}")
    rows = sorted(boxes, key=lambda b: b[0].start)
    boxes = sorted(rows[:3], key=lambda b: b[1].start) + sorted(rows[3:], key=lambda b: b[1].start)
    folder = os.path.join(out, "commendations", "frames")
    os.makedirs(folder, exist_ok=True)
    opening = None
    for tier, (ys, xs) in zip(FRAME_TIERS, boxes):
        part = a[ys, xs]
        alpha = np.clip((part.max(axis=2) - 8) / 120, 0, 1)
        rgb = np.where(alpha[..., None] > 0.01, np.clip(part / np.maximum(alpha[..., None], 0.01), 0, 255), 0)
        Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA").save(os.path.join(folder, tier + ".png"))
        if opening is None:                                     # (the Iron frame: its dark middle)
            dark = part.max(axis=2) < 40
            lab2, _ = ndimage.label(dark)
            mid = lab2[part.shape[0] // 2, part.shape[1] // 2]
            yy, xx = np.nonzero(lab2 == mid)
            opening = [int(xx.min()) + 3, int(yy.min()) + 3, int(xx.max()) - 3, int(yy.max()) - 3]
    with open(os.path.join(folder, "frames.json"), "w", encoding="utf-8") as f:
        json.dump({t: opening for t in FRAME_TIERS}, f)
    print(f"frames: 6 cut, opening {opening} -> {folder}")
    return 6


EMBLEM_SIDE = 448                # the tier emblems' square (service_record.py tier_banners)


def emblems(sheet, key, out=OUT):
    """A commendation's tier emblems from the owner's sheet (Nov 17: MVP, Game Changer, Positive Thinking, Loyal
    Soldier; a title over six emblems in a row, Iron to Max, each named under it, on black or night blue) cut into
    art/commendations/tiers/<tier>/<key>_<tier>.png: each emblem lifted off the sheet's own background (its alpha from
    how far its brightest channel stands above it, its colour unmixed, the glow kept), centred on a 448 square. The six
    are the sheet's six biggest lit shapes that are not much wider than tall, left to right; any other count: nothing
    is written. Also its "not started" banner (art/commendations/<key>.png) when there is none: Victor's Reach banner
    (victor.png) with its emblem painted out and the Silver one there in grey, as the earlier ones have. A copy of the
    sheet is kept (art/commendations/sheets). Returns how many emblems were cut.
    (Nov 19, Denied and Mission First: six emblems already cut out, the sheet see-through around them and no title or
    names.) A sheet that is see-through over a fifth of it or more gives its emblems by its own transparency: each one
    keeps its pixels as they are, and nothing is lifted off a background."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    if not re.fullmatch(r"[a-z0-9_]+", key):
        raise ValueError(f"not a commendation key: {key!r}")
    with Image.open(sheet) as im:
        full = np.asarray(im.convert("RGBA")).astype(np.float32)
    a, own = full[..., :3], full[..., 3]
    cut_out = (own < 8).mean() >= 0.2                           # (the sheet's own transparency around its emblems)
    if cut_out:
        full[own < 8] = 0                                       # (whatever colour lies under the see-through part)
        lit = own > 32
    else:
        edge = np.concatenate([a[:8].reshape(-1, 3), a[-8:].reshape(-1, 3), a[:, :8].reshape(-1, 3), a[:, -8:].reshape(-1, 3)])
        bg = np.median(edge, axis=0)                            # (the sheet's black or night blue)
        lit = np.clip(a - bg, 0, 255).max(axis=2) > 45
    lab, _ = ndimage.label(ndimage.binary_dilation(lit, iterations=5))
    shapes = []
    for b in ndimage.find_objects(lab):
        h, w = b[0].stop - b[0].start, b[1].stop - b[1].start
        if w <= 1.6 * h and h > a.shape[0] / 8:                 # (not the title, its lines, the names under)
            shapes.append(b)
    shapes = sorted(sorted(shapes, key=lambda b: -(b[0].stop - b[0].start) * (b[1].stop - b[1].start))[:6],
                    key=lambda b: b[1].start)
    if len(shapes) != 6:
        raise ValueError(f"expected 6 emblems on the sheet, found {len(shapes)}")
    art = os.path.join(out, "commendations")
    made = {}
    for tier, (ys, xs) in zip(FRAME_TIERS, shapes):
        if cut_out:
            img = Image.fromarray(full[ys, xs].astype(np.uint8), "RGBA")
        else:
            part = a[ys, xs]
            alpha = np.clip((np.clip(part - bg, 0, 255).max(axis=2) - 10) / 90, 0, 1)
            rgb = np.clip(bg + (part - bg) / np.maximum(alpha[..., None], 0.02), 0, 255)
            img = Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")
        img = img.crop(img.getbbox() or (0, 0, img.width, img.height))
        s = EMBLEM_SIDE * 0.94 / max(img.width, img.height)
        img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
        sq = Image.new("RGBA", (EMBLEM_SIDE, EMBLEM_SIDE), (0, 0, 0, 0))
        sq.alpha_composite(img, ((EMBLEM_SIDE - img.width) // 2, (EMBLEM_SIDE - img.height) // 2))
        folder = os.path.join(art, "tiers", tier)
        os.makedirs(folder, exist_ok=True)
        sq.save(os.path.join(folder, f"{key}_{tier}.png"))
        made[tier] = sq
    os.makedirs(os.path.join(art, "sheets"), exist_ok=True)
    shutil.copyfile(sheet, os.path.join(art, "sheets", key + os.path.splitext(sheet)[1].lower()))
    base, victor = os.path.join(art, key + ".png"), os.path.join(art, "victor.png")
    if not os.path.exists(base) and os.path.exists(victor):
        sys.path.insert(0, HERE)
        from service_record import clean_banner                 # (the banners' own emblem box)
        banner, box = clean_banner(victor)
        grey = made["silver"].convert("LA").convert("RGBA")
        g = np.asarray(grey).astype(np.float32)
        g[..., :3] = np.clip(g[..., :3] * 1.1 + 18, 0, 255)       # (Reach's banners: a light grey emblem)
        grey = Image.fromarray(g.astype(np.uint8), "RGBA")
        grey = grey.crop(grey.getbbox() or (0, 0, grey.width, grey.height))
        bw, bh = box[2] - box[0], box[3] - box[1]
        s = min(bw / grey.width, bh / grey.height) * 1.04
        grey = grey.resize((max(1, round(grey.width * s)), max(1, round(grey.height * s))), Image.LANCZOS)
        banner.alpha_composite(grey, (box[0] + (bw - grey.width) // 2, box[1] + (bh - grey.height) // 2))
        banner.save(base)
    print(f"emblems: {key}: 6 tiers cut -> {os.path.join(art, 'tiers')}")
    return 6


FIGURES = {"BODYTYPE_MALE": "spartan.png", "BODYTYPE_FEMALE": "spartan_female.png", "BODYTYPE_ELITE": "elite.png"}
MAP_PREVIEW = re.compile(r"HREACHMP_([A-Z0-9]+)LARGE")


def pictures(mcc, out=OUT):
    """The player pages' pictures from MCC's own menus: its body-type drawings (a Spartan, a female Spartan, an
    Elite: <out>/figures/*.png, cut to what is drawn) and Reach's map previews (<out>/maps/<map>.jpg, the map's
    name lower-case without spaces: forgeworld.jpg). Returns (figures, maps) written."""
    menus = os.path.join("data", "ui", "texturepacks", "mainmenutexturepack")
    levels = os.path.join("data", "ui", "texturepacks", "levelstexturepack")
    need = [os.path.join(mcc, p + x) for p in (menus, levels) for x in (".perm.bin", ".temp.bin")]
    lost = [p for p in need if not os.path.exists(p)]
    if lost:
        print("pictures skipped: this copy of MCC has no " + lost[0])
        return 0, 0
    figs = textures(mcc, menus, FIGURES.__contains__)
    os.makedirs(os.path.join(out, "figures"), exist_ok=True)
    for name, img in figs.items():
        path = os.path.join(out, "figures", FIGURES[name])
        trimmed(img).save(path + ".tmp", "PNG")
        os.replace(path + ".tmp", path)
    maps = textures(mcc, levels, lambda n: bool(MAP_PREVIEW.fullmatch(n)))
    os.makedirs(os.path.join(out, "maps"), exist_ok=True)
    for name, img in maps.items():
        path = os.path.join(out, "maps", MAP_PREVIEW.fullmatch(name).group(1).lower() + ".jpg")
        img.convert("RGB").save(path + ".tmp", "JPEG", quality=86)
        os.replace(path + ".tmp", path)
    print(f"pictures: {len(figs)} figures, {len(maps)} map previews -> {out}")
    return len(figs), len(maps)


def medals(mcc, out=OUT):
    """Write the medals' names and icons. Returns (how many named, how many with an icon)."""
    need = [os.path.join(mcc, p) for p in (EXE, CAREERDB, PACK + ".perm.bin", PACK + ".temp.bin")]
    lost = [p for p in need if not os.path.exists(p)]
    if lost:
        print("medals skipped: this copy of MCC has no " + lost[0])
        return 0, 0
    with open(need[0], "rb") as f:
        numbers = medal_numbers(f.read())
    with open(need[1], encoding="utf-8", errors="replace") as f:
        cat = catalog(f.read())
    pics = icons(mcc)
    os.makedirs(os.path.join(out, "medals"), exist_ok=True)
    table, drawn = {}, 0
    for number, medal_id in sorted(numbers.items()):
        info = cat.get(medal_id, {})
        entry = {"key": medal_id, "name": info.get("name") or pretty("", medal_id), "kind": info.get("kind", ""),
                 "icon": None}
        pic = pics.get(info.get("icon", "").upper())
        if pic:
            path = os.path.join(out, "medals", f"{number}.png")
            bc3(*pic).save(path + ".tmp", "PNG")
            os.replace(path + ".tmp", path)
            entry["icon"] = f"{number}.png"
            drawn += 1
        table[str(number)] = entry
    tmp = os.path.join(out, "medals.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(table, f, indent=1)
    os.replace(tmp, os.path.join(out, "medals.json"))
    print(f"medals: {len(table)} named, {drawn} with an icon -> {out}")
    return len(table), drawn


def weapon_catalog(xml_text):
    """{"marksman_rifle": "pgcr_DMR", ...}: the picture MCC's careerdb.xml gives each damage type (its Weapons list,
    comments dropped; an id is _damage_reporting_type_<the key>)."""
    a, b = xml_text.find("<Weapons>"), xml_text.find("</Weapons>")
    if a < 0 or b < 0:
        return {}
    out = {}
    for attrs in re.findall(r"<Weapon\s([^>]*)>", re.sub(r"<!--.*?-->", "", xml_text[a:b], flags=re.S)):
        m = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
        key = m.get("id", "").replace("_damage_reporting_type_", "")
        if key and m.get("image"):
            out.setdefault(key, m["image"])
    return out


def trimmed(img, margin=4):
    """A picture cut to what is drawn on it (its see-through edges off, `margin` pixels kept), so every weapon sits
    centred in its card whatever corner of MCC's canvas it was drawn in."""
    box = img.getchannel("A").getbbox()
    if not box:
        return img
    return img.crop((max(0, box[0] - margin), max(0, box[1] - margin),
                     min(img.width, box[2] + margin), min(img.height, box[3] + margin)))


def weapons(mcc, out=OUT, table=WEAPON_ART):
    """Write the picture of everything that kills: <out>/weapons/<picture>.png, and <out>/weapons.json,
    {game: {damage type number: file}} for the numbers of weapon_art.json whose picture this MCC has. Returns how
    many numbers got a picture."""
    need = [os.path.join(mcc, CAREERDB)] + [os.path.join(mcc, p + x) for p in WEAPON_PACKS for x in (".perm.bin", ".temp.bin")]
    lost = [p for p in need if not os.path.exists(p)]
    if lost:
        print("weapons skipped: this copy of MCC has no " + lost[0])
        return 0
    with open(need[0], encoding="utf-8", errors="replace") as f:
        cat = weapon_catalog(f.read())
    with open(table, encoding="utf-8") as f:
        wanted = {g: t for g, t in json.load(f).items() if isinstance(t, dict)}
    pics = {}
    for pack in WEAPON_PACKS:
        for name, pic in icons(mcc, pack).items():
            pics.setdefault(name, pic)
    os.makedirs(os.path.join(out, "weapons"), exist_ok=True)
    index, written = {}, set()
    for game, numbers in wanted.items():
        for number, value in numbers.items():
            picture = value[1:] if value.startswith("@") else cat.get(value, "")
            file = picture.lower() + ".png"
            if picture.upper() not in pics or not re.fullmatch(r"[a-z0-9_]+\.png", file):
                continue
            if file not in written:
                path = os.path.join(out, "weapons", file)
                trimmed(bc3(*pics[picture.upper()])).save(path + ".tmp", "PNG")
                os.replace(path + ".tmp", path)
                written.add(file)
            index.setdefault(game, {})[str(number)] = file
    tmp = os.path.join(out, "weapons.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1)
    os.replace(tmp, os.path.join(out, "weapons.json"))
    count = sum(len(v) for v in index.values())
    print(f"weapons: {count} of {sum(len(v) for v in wanted.values())} damage types pictured, {len(written)} pictures -> {out}")
    return count


def find_tiles(lum, sizes=TILE_SIZES, lit=FRAME_LIT):
    """[[(x, y, side), ...], ...]: every square of the usual side whose four edges are lit all along and brighter than
    the pixels just outside them, as rows top to bottom, each row left to right. `lum` is the picture's brightness,
    a 2D array."""
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view as window
    lum = np.asarray(lum, dtype=np.float32)
    h, w = lum.shape
    found = []
    for s in sizes:
        if s + 2 > min(h, w):
            break
        across, down = window(lum, s, axis=1), window(lum, s, axis=0)     # [y, x]: s pixels right of / below (x, y)
        hmin, hmean, vmin, vmean = across.min(axis=2), across.mean(axis=2), down.min(axis=2), down.mean(axis=2)
        rows, cols = h - s + 1, w - s + 1
        ok = ((hmin[:rows, :cols] >= lit) & (hmin[s - 1:, :cols] >= lit) &
              (vmin[:rows, :cols] >= lit) & (vmin[:rows, s - 1:] >= lit))
        for y, x in np.argwhere(ok):
            if not (0 < y < rows - 1 and 0 < x < cols - 1):
                continue
            edge = hmean[y, x] + hmean[y + s - 1, x] + vmean[y, x] + vmean[y, x + s - 1]
            outside = hmean[y - 1, x] + hmean[y + s, x] + vmean[y, x - 1] + vmean[y, x + s]
            found.append((float(edge - outside), int(x), int(y), s))
    kept = []
    for score, x, y, s in sorted(found, reverse=True):          # (the clearest frame of each overlapping bunch)
        if score > 0 and all(abs(x - kx) > ks // 2 or abs(y - ky) > ks // 2 for kx, ky, ks in kept):
            kept.append((x, y, s))
    if kept:                                                    # (the chart's tiles are one size: its key's bigger
        sides = [s for _, _, s in kept]                         # sample tile, and any other frame, is not one of them)
        usual = max(set(sides), key=sides.count)
        kept = [t for t in kept if abs(t[2] - usual) <= max(1, usual // 12)]
    out = []
    for x, y, s in sorted(kept, key=lambda t: (t[1], t[0])):
        if out and abs(y - out[-1][0][1]) <= s * 0.4:
            out[-1].append((x, y, s))
        else:
            out.append([(x, y, s)])
    return [sorted(row) for row in out]


def rank_rows(path=RANKS_JSON):
    """How many tiles each rank's row holds: the rank and its Grades, from the rank table."""
    with open(path, encoding="utf-8") as f:
        return [len(r["cr"]) for r in json.load(f)["ranks"]]


def insignia(img, x, y, s, side=INSIGNIA):
    """One tile's inside (its frame left off) as an RGBA picture `side` wide; the tile's black is see-through."""
    import numpy as np
    from PIL import Image
    frame = max(1, round(s / 14))
    inner = img.crop((x + frame, y + frame, x + s - frame, y + s - frame)).resize((side, side), Image.LANCZOS)
    rgb = np.asarray(inner.convert("RGB"), dtype=np.float32)
    alpha = np.clip((rgb.max(axis=2) - 14) / 40, 0, 1) * 255     # (under 14 of 255: the sheet; over 54: solid)
    return Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")


def rank_pictures(folder):
    """The folder's pictures in the rank table's order: each file's name starts with its step's number
    ("00_...png" is Recruit's). ValueError unless they are numbered 0 to the table's last step, each once."""
    by_step = {}
    for name in os.listdir(folder):
        m = re.match(r"(\d+)(?=\D)", name)
        if not m or not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
            continue
        if int(m.group(1)) in by_step:
            raise ValueError(f"two pictures are numbered {int(m.group(1))}")
        by_step[int(m.group(1))] = os.path.join(folder, name)
    steps = sum(rank_rows())
    if sorted(by_step) != list(range(steps)):
        raise ValueError(f"the folder has {len(by_step)} numbered pictures, not one for each step 0 to {steps - 1}")
    return [by_step[n] for n in range(steps)]


def squared(img, most=256):
    """A picture as RGBA, centred on a see-through square of its longer side (made smaller when over `most`); its
    own see-through parts kept."""
    from PIL import Image
    img = img.convert("RGBA")
    if max(img.size) > most:
        k = most / max(img.size)
        img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    side = max(img.size)
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    return out


def ranks(source, out=OUT):
    """Every rank's insignia into <out>/ranks/<step>.png, from the chart picture (cut tile by tile) or from a folder
    of one picture a step (rank_pictures). Returns how many were written; ValueError, with nothing written, when
    the picture's tiles or the folder's pictures are not the rank table's."""
    import numpy as np
    from PIL import Image
    if os.path.isdir(source):
        made = [squared(Image.open(p)) for p in rank_pictures(source)]
    else:
        img = Image.open(source).convert("RGB")
        rows = find_tiles(np.asarray(img.convert("L")))
        want, got = rank_rows(), [len(r) for r in rows]
        if got != want:
            raise ValueError(f"the picture's rows of tiles {got} are not the rank table's {want}")
        made = [insignia(img, x, y, s) for row in rows for x, y, s in row]
    folder = os.path.join(out, "ranks")
    os.makedirs(folder, exist_ok=True)
    for step, picture in enumerate(made):
        path = os.path.join(folder, f"{step}.png")
        picture.save(path + ".tmp", "PNG")
        os.replace(path + ".tmp", path)
    if not os.path.isdir(source):
        keep = os.path.join(out, "rank_chart" + os.path.splitext(source)[1].lower())
        if os.path.abspath(source) != os.path.abspath(keep):
            shutil.copyfile(source, keep)
    print(f"ranks: {len(made)} insignia -> {folder}")
    return len(made)


if __name__ == "__main__":
    if sys.argv[1:2] == ["frames"] and len(sys.argv) == 3:
        try:
            frames(sys.argv[2])
        except (ValueError, OSError) as e:
            sys.exit(f"frames not cut: {e}")
    elif sys.argv[1:2] == ["emblems"] and len(sys.argv) == 4:
        try:
            emblems(sys.argv[2], sys.argv[3])
        except (ValueError, OSError) as e:
            sys.exit(f"emblems not cut: {e}")
    elif sys.argv[1:2] == ["ranks"] and len(sys.argv) == 3:
        try:
            ranks(sys.argv[2])
        except (ValueError, OSError) as e:
            sys.exit(f"ranks not cut: {e}")
    elif sys.argv[1:2] in (["medals"], ["weapons"], ["pictures"], ["video"]):
        sys.path.insert(0, ROOT)
        from brain import paths                                 # (where MCC is)
        folder = sys.argv[2] if len(sys.argv) > 2 else paths.mcc()
        if not folder:
            sys.exit("MCC was not found: give its folder")
        try:
            {"medals": medals, "weapons": weapons, "pictures": pictures, "video": video}[sys.argv[1]](folder)
        except (ValueError, struct.error, OSError) as e:
            sys.exit(f"{sys.argv[1]} not read: {e}")
    else:
        sys.exit(__doc__)
