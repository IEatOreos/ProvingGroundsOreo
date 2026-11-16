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

usage: python -I service_record_art.py medals [MCC folder]
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


def icons(mcc):
    """{TEXTURE NAME: (width, height, BC3 bytes)} from medalstexturepack (480-byte entries: name at +0x44, format
    +0x68 (3 = BC3), size +0x74, data size +0x88 and offset +0x90 in .temp.bin). The first of a name is kept."""
    out = {}
    with open(os.path.join(mcc, PACK + ".perm.bin"), "rb") as f:
        perm = f.read()
    with open(os.path.join(mcc, PACK + ".temp.bin"), "rb") as temp:
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


def bc3(w, h, data):
    """A BC3 (DXT5) picture as PIL RGBA, through a DDS header (as tools/emblems.py)."""
    import io
    from PIL import Image
    hdr = struct.pack("<4sIIIIIII44sIII20sIIIII", b"DDS ", 124, 0x81007, h, w, len(data), 0, 1, b"\0" * 44,
                      32, 4, 0x35545844, b"\0" * 20, 0x1000, 0, 0, 0, 0)
    return Image.open(io.BytesIO(hdr + data)).convert("RGBA")


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
    if sys.argv[1:2] == ["ranks"] and len(sys.argv) == 3:
        try:
            ranks(sys.argv[2])
        except (ValueError, OSError) as e:
            sys.exit(f"ranks not cut: {e}")
    elif sys.argv[1:2] == ["medals"]:
        sys.path.insert(0, ROOT)
        from brain import paths                                 # (where MCC is)
        folder = sys.argv[2] if len(sys.argv) > 2 else paths.mcc()
        if not folder:
            sys.exit("MCC was not found: give its folder")
        try:
            medals(folder)
        except (ValueError, struct.error, OSError) as e:
            sys.exit(f"medals not read: {e}")
    else:
        sys.exit(__doc__)
