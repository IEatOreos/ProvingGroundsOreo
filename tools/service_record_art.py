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

usage: python -I service_record_art.py medals [MCC folder]
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "native", "bin", "service_record", "art")
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


if __name__ == "__main__":
    if sys.argv[1:2] == ["medals"]:
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
