"""MCC's account ranks for the bots (custom, Nov 11): the badge MCC shows beside a player's name (a tour's shield with
the level's insignia on it, "Tour 6, Level 26 Colonel"), drawn from MCC's own files.

MCC keeps them in its Unreal pak, <MCC>\\MCC\\Content\\Paks\\MCC-WindowsNoEditor.pak (version 7, index not encrypted):
UI/Shared/Textures/AccountLevelProgression/T_Im_<rank>.uasset / .uexp (512 x 512 PF_B8G8R8A8, stored uncompressed)
and UI/Features/Nameplate/DA_AccountProgression (MCCAccountProgressionData): PrestigeTiers, 11 tours (Prestige 0-10,
the icon T_Im_Tier11 down to T_Im_Tier01; the last, the gold eagle, has no levels) and PrestigeLevels, 30 levels (1
Rookie .. 26 Colonel .. 30 General, each its icon).

extract writes <out>/tour_NN.rgba (NN 01-11: tour = prestige + 1), <out>/level_NN.rgba (01-30), 128 x 128, and
<out>/index.txt (tour=<n>|levels or max; level=<n>|<name>). Game data: native/bin/ranks, not in git. The BOTS panel runs
it when the folder is missing (native/bots_panel.cpp ranks_frame).

usage: python -I mcc_ranks.py extract <MCC folder> <out folder>
"""
import os
import re
import struct
import sys

PAK = os.path.join("MCC", "Content", "Paks", "MCC-WindowsNoEditor.pak")
TEX = "MCC/Content/UI/Shared/Textures/AccountLevelProgression/"
DA = "MCC/Content/UI/Features/Nameplate/DA_AccountProgression"
SIZE = 128
# (what DA_AccountProgression held, MCC Nov 2026: the fallback when it cannot be read)
LEVELS = ["Rookie", "Recruit", "Private", "Private2ndClass", "Private1stClass", "LanceCorporal", "Corporal", "Sergeant",
          "Sergeant2ndClass", "Sergeant1stClass", "StaffSergent", "GunerySergent", "FirstSergent", "SergentMajor",
          "CommandSergentMajor", "Warrantofficer", "WarrantOfficer3rdClass", "WarrantOfficer2ndClass",
          "WarrantOfficer1stClass", "ChiefWarrantOfficer", "2ndLieutenant", "1stLieutenant", "Captain", "Major",
          "Lieutenant-Colonel", "Colonel", "BrigadierGeneral", "MajorGeneral", "LieutenantGeneral", "General"]
TOURS = [(f"Tier{11 - p:02d}", p < 10) for p in range(11)]


def pretty(icon):
    """"T_Im_GunerySergent" -> "Gunnery Sergeant" (the icons' names, their spelling put right)."""
    s = icon.replace("T_Im_", "").replace("Sergent", "Sergeant").replace("Gunery", "Gunnery")
    s = s.replace("Warrantofficer", "WarrantOfficer").replace("-", "")
    s = re.sub(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9][a-z]{2})(?=[A-Z])", " ", s)
    return s.strip()


class Pak:
    """An Unreal pak's index (version 7) and its uncompressed entries."""

    def __init__(s, path):
        s.f = open(path, "rb")
        size = os.path.getsize(path)
        s.f.seek(size - 512)
        tail = s.f.read(512)
        i = tail.rfind(struct.pack("<I", 0x5A6F12E1))
        if i < 0:
            raise ValueError("not a pak")
        s.version = struct.unpack_from("<I", tail, i + 4)[0]
        if tail[i - 1]:
            raise ValueError("its index is encrypted")
        off, n = struct.unpack_from("<QQ", tail, i + 8)
        s.f.seek(off)
        idx = s.f.read(n)
        o = [0]

        def fstr():
            k = struct.unpack_from("<i", idx, o[0])[0]
            o[0] += 4
            if k < 0:
                v = idx[o[0]:o[0] - 2 * k].decode("utf-16le").rstrip("\0"); o[0] += -2 * k
            else:
                v = idx[o[0]:o[0] + k].decode("latin1").rstrip("\0"); o[0] += k
            return v

        fstr()                                               # (its mount point)
        count = struct.unpack_from("<i", idx, o[0])[0]; o[0] += 4
        s.entries = {}
        for _ in range(count):
            name = fstr()
            e_off, e_size, e_usize, comp = struct.unpack_from("<qqqi", idx, o[0]); o[0] += 28 + 20
            if comp:
                nb = struct.unpack_from("<i", idx, o[0])[0]; o[0] += 4 + 16 * nb
            o[0] += 5                                        # (encrypted flag, block size)
            s.entries[name] = (e_off, e_size, comp)

    def read(s, name):
        off, size, comp = s.entries[name]
        if comp:
            raise ValueError(f"{name} is compressed")
        s.f.seek(off)
        hdr = s.f.read(53)                                   # (the entry's header again, before its data)
        if struct.unpack_from("<q", hdr, 8)[0] != size:
            raise ValueError(f"{name}: unexpected entry header")
        return s.f.read(size)


def texture(pak, icon):
    """The icon as a PIL picture: its .uexp holds one 512 x 512 BGRA mip after the bulk data header."""
    from PIL import Image
    ux = pak.read(TEX + icon + ".uexp")
    n = 512 * 512 * 4
    at = ux.find(struct.pack("<ii", n, n))
    if at < 0:
        raise ValueError(f"{icon}: no 512x512 BGRA mip")
    px = ux[at + 16:at + 16 + n]
    return Image.frombuffer("RGBA", (512, 512), px, "raw", "BGRA", 0, 1)


def progression(pak):
    """([level icons 1..30], [(tour icon, has levels) 1..11]) from DA_AccountProgression's tagged properties."""
    ua, ux = pak.read(DA + ".uasset"), pak.read(DA + ".uexp")
    k = ua.find(b"/Game/UI/Features/Nameplate/DA_AccountProgression") - 4
    names, o = [], k
    while o < len(ua) - 4:
        n = struct.unpack_from("<i", ua, o)[0]
        if n <= 0 or n > 300 or ua[o + 3 + n:o + 4 + n] != b"\0":
            break
        names.append(ua[o + 4:o + 3 + n].decode("latin1"))
        o += 4 + n + 4                                       # (its hash)
    nm = lambda i: names[i] if 0 <= i < len(names) else ""
    levels, tours = {}, []
    o = 0
    cur = {}

    def walk(end):
        nonlocal o, cur
        while o < end:
            name = nm(struct.unpack_from("<i", ux, o)[0]); o += 8
            if name == "None":
                return
            typ = nm(struct.unpack_from("<i", ux, o)[0]); o += 8
            size = struct.unpack_from("<i", ux, o)[0]; o += 8
            if typ == "ArrayProperty":
                inner = nm(struct.unpack_from("<i", ux, o)[0]); o += 9
                start = o
                count = struct.unpack_from("<i", ux, o)[0]; o += 4
                if inner == "StructProperty":
                    o += 24
                    o += 8 + 16 + 1
                    for _ in range(count):
                        cur = {}
                        walk(start + size)
                        (tours.append((cur.get("PrestigeIcon"), cur.get("HasLevels", True))) if name == "PrestigeTiers"
                         else levels.__setitem__(cur.get("Level"), cur.get("LevelIcon")))
                o = start + size
            elif typ == "StructProperty":
                o += 8 + 16 + 1 + size
            else:
                bv = None
                if typ == "BoolProperty":
                    bv = ux[o]; o += 1
                o += 1
                if typ == "IntProperty":
                    cur[name] = struct.unpack_from("<i", ux, o)[0]
                elif typ == "BoolProperty":
                    cur[name] = bool(bv)
                elif typ == "SoftObjectProperty":
                    cur[name] = nm(struct.unpack_from("<i", ux, o)[0]).split(".")[-1].replace("T_Im_", "")
                o += size

    walk(len(ux))
    lv = [levels.get(i) for i in range(1, 31)]
    if len(tours) != 11 or None in lv or any(t[0] is None for t in tours):
        raise ValueError("DA_AccountProgression not as decoded")
    return lv, tours


def extract(mcc, out):
    from PIL import Image
    path = os.path.join(mcc, PAK)
    if not os.path.exists(path):
        print(f"ranks skipped: no {path}")
        return 0
    pak = Pak(path)
    try:
        levels, tours = progression(pak)
    except (ValueError, struct.error, KeyError) as e:
        print(f"ranks: MCC's progression not read ({e}): its Nov 2026 order")
        levels, tours = LEVELS, TOURS
    os.makedirs(out, exist_ok=True)
    lines = ["; MCC's account ranks (tools/mcc_ranks.py, from MCC's pak): tour=<n>|levels or max, level=<n>|<name>"]

    def write(img, name):
        img = img.resize((SIZE, SIZE), Image.LANCZOS)
        tmp = os.path.join(out, name + ".tmp")
        with open(tmp, "wb") as fh:
            fh.write(struct.pack("<II", SIZE, SIZE) + img.tobytes())
        os.replace(tmp, os.path.join(out, name + ".rgba"))

    for t, (icon, has_levels) in enumerate(tours, 1):
        write(texture(pak, "T_Im_" + icon), f"tour_{t:02d}")
        lines.append(f"tour={t}|{'levels' if has_levels else 'max'}")
    for n, icon in enumerate(levels, 1):
        write(texture(pak, "T_Im_" + icon), f"level_{n:02d}")
        lines.append(f"level={n}|{pretty(icon)}")
    pak.f.close()
    tmp = os.path.join(out, "index.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.replace(tmp, os.path.join(out, "index.txt"))           # (last: the panel reads the folder once this is there)
    print(f"ranks: {len(tours)} tours, {len(levels)} levels -> {out}")
    return len(tours) + len(levels)


if __name__ == "__main__":
    if sys.argv[1:2] == ["extract"] and len(sys.argv) == 4:
        extract(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
