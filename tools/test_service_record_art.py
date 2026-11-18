"""tools/service_record_art.py: the rank chart's tiles found and cut in the rank table's order, a chart that is not
the table's refused with nothing written; MCC's medal numbers decoded from a made-up exe, their names and kinds."""
import importlib.util
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("service_record_art", os.path.join(HERE, "service_record_art.py"))
art = importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)


def chart(rows, side=28, key_tile=True):
    """A made-up rank chart: black, one row of framed square tiles per rank, each tile's inside lit a shade that
    tells its place (so a cut can be told from its neighbours); a bigger framed tile in a key, as the real chart."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (60 + 41 * max(rows) + 90, 40 + 31 * len(rows)), (0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((70, 8), "RANKS", fill=(160, 170, 190))
    step = 0
    for r, n in enumerate(rows):
        d.text((4, 44 + 31 * r), f"RANK {r}", fill=(230, 230, 230))
        for g in range(n):
            x, y = 60 + 41 * g, 36 + 31 * r
            d.rectangle((x, y, x + side - 1, y + side - 1), outline=(95, 100, 110))
            d.rectangle((x + 8, y + 8, x + side - 9, y + side - 9), fill=(60 + 3 * step, 200 - 3 * step, 120))
            step += 1
    if key_tile:
        x, y = 60 + 41 * max(rows) + 20, 36 + 31 * (len(rows) - 6)
        d.rectangle((x, y, x + 39, y + 39), outline=(95, 100, 110))
        d.rectangle((x + 10, y + 10, x + 29, y + 29), fill=(250, 250, 0))
    return img


def test_tiles_found_in_the_tables_order():
    import numpy as np
    rows = art.rank_rows()
    assert rows == [1, 1, 2, 3, 4, 4, 4, 4, 4, 4, 4, 5] + [1] * 10 and sum(rows) == 50, rows
    found = art.find_tiles(np.asarray(chart(rows).convert("L")))
    assert [len(r) for r in found] == rows, [len(r) for r in found]
    assert found[0] == [(60, 36, 28)] and found[2] == [(60, 98, 28), (101, 98, 28)], found[:3]
    assert found[11][4] == (60 + 41 * 4, 36 + 31 * 11, 28), found[11]
    assert all(s == 28 for row in found for _, _, s in row)          # (the key's 40 px tile is not one of them)


def test_ranks_cut_and_named_by_step():
    from PIL import Image
    rows = art.rank_rows()
    with tempfile.TemporaryDirectory() as tmp:
        picture = os.path.join(tmp, "chart.png")
        chart(rows).save(picture)
        assert art.ranks(picture, os.path.join(tmp, "art")) == 50
        folder = os.path.join(tmp, "art", "ranks")
        assert sorted(os.listdir(folder), key=lambda f: int(f[:-4])) == [f"{i}.png" for i in range(50)]
        assert os.path.exists(os.path.join(tmp, "art", "rank_chart.png"))
        for step in (0, 3, 39, 49):
            tile = Image.open(os.path.join(folder, f"{step}.png"))
            assert tile.mode == "RGBA" and tile.size == (art.INSIGNIA, art.INSIGNIA), (tile.mode, tile.size)
            r, g, b, a = tile.getpixel((48, 48))                   # the tile's lit middle: this step's own shade
            assert abs(r - (60 + 3 * step)) <= 2 and abs(g - (200 - 3 * step)) <= 2 and a == 255, (step, r, g, b, a)
            assert tile.getpixel((6, 6))[3] == 0                   # the tile's black: see-through, its frame cut off


def test_a_chart_that_is_not_the_tables_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        picture = os.path.join(tmp, "chart.png")
        rows = art.rank_rows()
        chart(rows[:-1]).save(picture)                              # (a rank short)
        try:
            art.ranks(picture, os.path.join(tmp, "art"))
        except ValueError as e:
            assert "are not the rank table's" in str(e), e
        else:
            raise AssertionError("a chart with a rank missing was cut")
        assert not os.path.exists(os.path.join(tmp, "art")), os.listdir(tmp)
        from PIL import Image
        Image.new("RGB", (200, 200), (0, 0, 0)).save(picture)      # (no tiles at all)
        try:
            art.ranks(picture, os.path.join(tmp, "art"))
        except ValueError:
            pass
        else:
            raise AssertionError("a black picture was cut")


def test_ranks_from_a_folder_of_numbered_pictures():
    """One picture a step, named by its number: written by step with its own see-through parts kept, one that is
    not square centred on a square; a missing or a doubled number refused with nothing written."""
    from PIL import Image
    steps = sum(art.rank_rows())
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "icons"), os.path.join(tmp, "art")
        os.makedirs(src)
        for n in range(steps):
            size = (91, 88) if n == 39 else (91, 91)
            img = Image.new("RGBA", size, (0, 0, 0, 0))
            img.paste((10 + 4 * n, 90, 200, 255), (20, 20, 70, 70))
            img.save(os.path.join(src, f"{n:02d}_HR_Rank_{n}_Icon.png"))
        open(os.path.join(src, "notes.txt"), "w").close()                  # (not a picture: left alone)
        assert art.ranks(src, out) == steps == 50
        assert not os.path.exists(os.path.join(out, "rank_chart.png"))
        for n in (0, 7, 39, 49):
            tile = Image.open(os.path.join(out, "ranks", f"{n}.png"))
            assert tile.mode == "RGBA" and tile.size == (91, 91), (n, tile.mode, tile.size)
            assert tile.getpixel((45, 45)) == (10 + 4 * n, 90, 200, 255) and tile.getpixel((2, 2))[3] == 0, n
        assert Image.open(os.path.join(out, "ranks", "39.png")).getpixel((20, 21))[3] == 255     # (moved down 1)
        for break_it in ("missing", "doubled"):
            bad, bad_out = os.path.join(tmp, break_it), os.path.join(tmp, break_it + "_art")
            os.makedirs(bad)
            for n in range(steps):
                if not (break_it == "missing" and n == 12):
                    Image.new("RGBA", (8, 8)).save(os.path.join(bad, f"{n:02d}_x.png"))
            if break_it == "doubled":
                Image.new("RGBA", (8, 8)).save(os.path.join(bad, "12_again.png"))
            try:
                art.ranks(bad, bad_out)
            except ValueError as e:
                assert ("not one for each step" in str(e)) == (break_it == "missing"), e
            else:
                raise AssertionError(break_it)
            assert not os.path.exists(bad_out)
    big = art.squared(Image.new("RGB", (1024, 512), (9, 9, 9)))
    assert big.size == (256, 256) and big.getpixel((128, 128)) == (9, 9, 9, 255) and big.getpixel((128, 10))[3] == 0


def texture_pack(base, pictures):
    """A made-up MCC texture pack (<base>.perm.bin / .temp.bin): pictures = {name: (width, height, lit blocks)}, a
    BC3 picture of 4 x 4 blocks, see-through but for the (column, row) blocks listed, which are one solid colour."""
    perm, temp = b"", b""
    for name, (w, h, lit) in pictures.items():
        data = b""
        for row in range(h // 4):
            for col in range(w // 4):
                a = 255 if (col, row) in lit else 0
                data += bytes([a, a, 0, 0, 0, 0, 0, 0]) + struct.pack("<HHI", 0x65BF, 0x65BF, 0)
        e = bytearray(480)
        e[0x44:0x44 + len(name)] = name.encode()
        struct.pack_into("<I", e, 0x68, 3)
        struct.pack_into("<HH", e, 0x74, w, h)
        struct.pack_into("<QQ", e, 0x88, len(data), len(temp))
        perm, temp = perm + bytes(e), temp + data
    os.makedirs(os.path.dirname(base), exist_ok=True)
    with open(base + ".perm.bin", "wb") as f:
        f.write(perm)
    with open(base + ".temp.bin", "wb") as f:
        f.write(temp)


def test_weapon_pictures_from_mcc():
    """Each damage type number gets the picture MCC's own table names for it (or the picture named after an @), cut
    to what is drawn; a number whose picture this MCC lacks is left out; the site copies only safe names."""
    import json
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        mcc, out = os.path.join(tmp, "mcc"), os.path.join(tmp, "art")
        os.makedirs(os.path.join(mcc, os.path.dirname(art.CAREERDB)))
        with open(os.path.join(mcc, art.CAREERDB), "w", encoding="utf-8") as f:
            f.write('<db>\n<Weapons>\n<!-- <Weapon id="_damage_reporting_type_cut" image="pgcr_cut" /> -->\n'
                    '<Weapon id="_damage_reporting_type_marksman_rifle" image="pgcr_DMR" name="$weapon_marksman_rifle" />\n'
                    '<Weapon id="_damage_reporting_type_banshee" image="wod_banshee" name="$b" />\n'
                    '<Weapon id="_damage_reporting_type_wasp" name="$no_image" />\n</Weapons>\n</db>\n')
        texture_pack(os.path.join(mcc, art.WEAPON_PACKS[0]), {"PGCR_DMR": (32, 16, {(3, 1), (4, 1), (3, 2), (4, 2)})})
        texture_pack(os.path.join(mcc, art.WEAPON_PACKS[1]), {"WOD_BANSHEE": (16, 8, {(0, 0)}), "PGCR_Guardians": (8, 8, {(0, 0), (1, 1)})})
        table = os.path.join(tmp, "weapon_art.json")
        with open(table, "w", encoding="utf-8") as f:
            json.dump({"note": "made up", "reach": {"0": "@PGCR_Guardians", "6": "marksman_rifle", "29": "banshee",
                                                    "30": "banshee", "40": "wasp", "41": "not_in_mcc", "42": "@NoSuchPicture"}}, f)
        assert art.weapon_catalog(open(os.path.join(mcc, art.CAREERDB), encoding="utf-8").read()) == {
            "marksman_rifle": "pgcr_DMR", "banshee": "wod_banshee"}
        assert art.weapons(mcc, out, table) == 4
        index = json.load(open(os.path.join(out, "weapons.json"), encoding="utf-8"))
        assert index == {"reach": {"0": "pgcr_guardians.png", "6": "pgcr_dmr.png", "29": "wod_banshee.png",
                                   "30": "wod_banshee.png"}}, index
        assert sorted(os.listdir(os.path.join(out, "weapons"))) == ["pgcr_dmr.png", "pgcr_guardians.png", "wod_banshee.png"]
        dmr = Image.open(os.path.join(out, "weapons", "pgcr_dmr.png"))
        assert dmr.mode == "RGBA" and dmr.size == (16, 16), dmr.size        # (8 x 8 drawn, 4 kept round it)
        assert dmr.getpixel((8, 8))[3] == 255 and dmr.getpixel((1, 1))[3] == 0
        # the site's side: the earned ones copied in, by safe names only
        spec2 = importlib.util.spec_from_file_location("service_record", os.path.join(HERE, "service_record.py"))
        sr = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(sr)
        store, site = os.path.join(tmp, "store"), os.path.join(tmp, "site")
        os.makedirs(store)
        os.rename(out, os.path.join(store, "art"))
        index["reach"].update({"7": "../../secret.png", "8": "gone.png", "9": 5})
        with open(os.path.join(store, "art", "weapons.json"), "w", encoding="utf-8") as f:
            json.dump(index, f)
        got = sr.weapon_pictures(["reach:6", "reach:29", "reach:7", "reach:8", "reach:9", "reach:99", "h4:6", "reach:?"],
                                 sr.Paths(store=store, out=site))
        assert got == {"reach:6": "weapons/pgcr_dmr.png", "reach:29": "weapons/wod_banshee.png"}, got
        assert sorted(os.listdir(os.path.join(site, "weapons"))) == ["pgcr_dmr.png", "wod_banshee.png"]
        assert sr.weapon_pictures(["reach:6"], sr.Paths(store=os.path.join(tmp, "none"), out=site)) == {}
    assert art.weapons(os.path.join(tempfile.gettempdir(), "no_such_mcc_folder"), "unused") == 0


def test_menu_pictures_from_mcc():
    """`pictures`: MCC's body-type drawings (BC3) and Reach's large map previews (BC1, half a byte a pixel) are
    written by their own names, other pictures passed over; the site copies the ones it names, by safe names only,
    and finds a map's preview by its name."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        mcc, out = os.path.join(tmp, "mcc"), os.path.join(tmp, "art")
        tp = os.path.join(mcc, "data", "ui", "texturepacks")
        texture_pack(os.path.join(tp, "mainmenutexturepack"), {"BODYTYPE_MALE": (16, 16, {(1, 1)}), "BODYTYPE_ELITE": (8, 8, {(0, 0)}),
                                                               "SOMETHING_ELSE": (8, 8, {(0, 0)})})
        perm, temp = b"", b""
        for name, w, h in (("HREACHMP_BONEYARDLARGE", 16, 8), ("HREACHMP_FORGEWORLDLARGE", 8, 4), ("HREACHMP_SPIRE", 8, 4)):
            data = struct.pack("<HHI", 0xF800, 0xF800, 0) * (w * h // 16)       # BC1: solid red
            e = bytearray(480)
            e[0x44:0x44 + len(name)] = name.encode()
            struct.pack_into("<I", e, 0x68, 3)
            struct.pack_into("<HH", e, 0x74, w, h)
            struct.pack_into("<QQ", e, 0x88, len(data), len(temp))
            perm, temp = perm + bytes(e), temp + data
        for x, b in ((".perm.bin", perm), (".temp.bin", temp)):
            with open(os.path.join(tp, "levelstexturepack" + x), "wb") as f:
                f.write(b)
        assert art.pictures(mcc, out) == (2, 2)
        assert sorted(os.listdir(os.path.join(out, "figures"))) == ["elite.png", "spartan.png"]
        assert sorted(os.listdir(os.path.join(out, "maps"))) == ["boneyard.jpg", "forgeworld.jpg"]
        board = Image.open(os.path.join(out, "maps", "boneyard.jpg"))
        assert board.size == (16, 8) and board.getpixel((8, 4))[0] > 200 and board.getpixel((8, 4))[1] < 40, board.getpixel((8, 4))
        spec2 = importlib.util.spec_from_file_location("service_record", os.path.join(HERE, "service_record.py"))
        sr = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(sr)
        assert sr.preview_name("reach_70_boneyard") == "boneyard.jpg" and sr.preview_name("reach_forge_halo") == "forgeworld.jpg"
        store, site = os.path.join(tmp, "store"), os.path.join(tmp, "site")
        os.makedirs(store)
        os.rename(out, os.path.join(store, "art"))
        got = sr.menu_pictures("figures", {"spartan.png", "spartan_female.png", "../x.png"}, sr.Paths(store=store, out=site))
        assert got == {"spartan.png": "figures/spartan.png"} and os.listdir(os.path.join(site, "figures")) == ["spartan.png"], got
    assert art.pictures(os.path.join(tempfile.gettempdir(), "no_such_mcc_folder")) == (0, 0)


def test_tier_frames_from_a_sheet():
    """Six glowing frames on black, three a row, are cut in tier order with their black made see-through, and the
    opening (the Iron frame's dark middle) is written for every tier; a sheet without six frames is refused."""
    import json
    from PIL import Image, ImageDraw
    with tempfile.TemporaryDirectory() as tmp:
        sheet = Image.new("RGB", (660, 280), (0, 0, 0))
        d = ImageDraw.Draw(sheet)
        cols = [(150, 150, 150), (200, 120, 60), (180, 200, 230), (230, 180, 50), (160, 80, 220), (220, 40, 40)]
        for i, c in enumerate(cols):
            x, y = 20 + (i % 3) * 220, 20 + (i // 3) * 130
            d.rectangle((x, y, x + 180, y + 100), outline=c, width=6)
        path = os.path.join(tmp, "frames.png")
        sheet.save(path)
        assert art.frames(path, tmp) == 6
        folder = os.path.join(tmp, "commendations", "frames")
        meta = json.load(open(os.path.join(folder, "frames.json"), encoding="utf-8"))
        x0, y0, x1, y1 = meta["gold"]
        assert set(meta) == set(art.FRAME_TIERS) and 6 < x0 < 20 and 6 < y0 < 20 and 160 < x1 < 180 and 80 < y1 < 100, meta
        gold = Image.open(os.path.join(folder, "gold.png"))
        assert gold.getpixel((gold.width // 2, gold.height // 2))[3] == 0                  # (the middle see-through)
        edge = gold.getpixel((gold.width // 2, 9))                                         # (6 px of margin, then the line)
        assert edge[3] > 200 and edge[0] > 200 and edge[2] < 120, edge                       # (the gold line kept)
        Image.new("RGB", (300, 100)).save(path)
        try:
            art.frames(path, tmp)
            raise AssertionError("an empty sheet was cut")
        except ValueError:
            pass


def test_tier_emblems_from_a_sheet():
    """(Nov 17) A title over six emblems in a row, each named under it, on night blue: the six are cut left to right as
    Iron to Max on 448 squares, the blue made see-through and each emblem's own colour kept; a grey "not started"
    banner is made from Victor's when there is none; a sheet without six emblems is refused."""
    from PIL import Image, ImageDraw
    with tempfile.TemporaryDirectory() as tmp:
        bg = (4, 12, 19)
        sheet = Image.new("RGB", (1200, 400), bg)
        d = ImageDraw.Draw(sheet)
        d.rectangle((300, 20, 900, 50), fill=(220, 225, 230))                          # (the title: wide, low)
        d.line((40, 370, 1160, 370), fill=(150, 150, 150), width=3)                     # (a rule under it all)
        cols = [(150, 150, 150), (200, 120, 60), (190, 205, 230), (230, 180, 50), (160, 80, 220), (220, 40, 40)]
        for i, c in enumerate(cols):
            x = 40 + i * 190
            d.ellipse((x, 90, x + 150, 240), outline=c, width=10)
            d.rectangle((x + 60, 120, x + 90, 210), fill=c)
            d.rectangle((x + 40, 300, x + 110, 318), fill=(200, 200, 200))           # (its name under it)
        path = os.path.join(tmp, "sheet.png")
        sheet.save(path)
        comm = os.path.join(tmp, "commendations")
        os.makedirs(comm)
        banner = Image.new("RGBA", (286, 90), (64, 95, 128, 255))                       # (Victor's: a grey emblem on blue)
        ImageDraw.Draw(banner).ellipse((40, 15, 100, 75), fill=(200, 200, 200, 255))
        banner.save(os.path.join(comm, "victor.png"))
        assert art.emblems(path, "test_award", tmp) == 6
        for tier, c in zip(art.FRAME_TIERS, cols):
            e = Image.open(os.path.join(comm, "tiers", tier, f"test_award_{tier}.png"))
            assert e.size == (art.EMBLEM_SIDE, art.EMBLEM_SIDE) and e.mode == "RGBA"
            assert e.getpixel((2, 2))[3] == 0                                           # (the blue see-through)
            mid = e.getpixel((e.width // 2, e.height // 2))                            # (the bar in its middle)
            assert mid[3] > 200 and all(abs(mid[k] - c[k]) < 25 for k in range(3)), (tier, mid, c)
        grey = Image.open(os.path.join(comm, "test_award.png")).convert("RGB")
        r, g, b = grey.getpixel((70, 45))
        assert abs(r - g) < 12 and abs(g - b) < 12 and r > 120, (r, g, b)               # (a grey emblem where Victor's was)
        assert os.path.exists(os.path.join(comm, "sheets", "test_award.png"))
        Image.new("RGB", (600, 200), bg).save(path)
        try:
            art.emblems(path, "test_award", tmp)
            raise AssertionError("an empty sheet was cut")
        except ValueError:
            pass


def test_every_reach_damage_type_has_a_picture_entry():
    """weapon_art.json names a picture for every number weapons.json names, and nothing else."""
    import json
    with open(art.WEAPON_ART, encoding="utf-8") as f:
        pictures = json.load(f)["reach"]
    with open(os.path.join(HERE, "service_record_site", "weapons.json"), encoding="utf-8") as f:
        names = json.load(f)["reach"]["names"]
    assert set(pictures) == set(names), sorted(set(pictures) ^ set(names), key=int)
    assert all(isinstance(v, str) and v and " " not in v for v in pictures.values())


def exe(ids):
    """A made-up 64-bit PE whose code looks a name up as MCC's does: ids = [(number, text), ...] in the code's
    order; the first is number 0, the last is coded as MCC codes its last."""
    text_rva, rdata_rva, text_raw, rdata_raw = 0x1000, 0x3000, 0x400, 0x2400
    strings, at = b"\0", {}
    for _, name in ids:
        at[name] = rdata_rva + len(strings)
        strings += name.encode() + b"\0"
    code = b"\x48\x89\x5c\x24\x08\x83\xcf\xff"                      # (something before the first entry)
    for k, (number, name) in enumerate(ids):
        lea_at = text_rva + len(code)
        code += b"\x48\x8d\x15" + struct.pack("<i", at[name] - (lea_at + 7))
        code += b"\x48\x8b\xce\xe8" + struct.pack("<i", 0x1234) + b"\x85\xc0"
        if k == 0:
            code += b"\x0f\x84" + struct.pack("<i", 0x2000)         # je: ebx stays 0
        elif k == len(ids) - 1:
            code += b"\xb9" + struct.pack("<i", number) + b"\x0f\x44\xf9\x8b\xdf\xc3"
        elif k == 1:
            code += b"\x75\x08\x8d\x5f" + struct.pack("<b", number + 1) + b"\xe9" + struct.pack("<i", 0x100)
        elif number < 128:
            code += b"\x75\x08\x8d\x58" + struct.pack("<b", number) + b"\xe9" + struct.pack("<i", 0x100)
        else:
            code += b"\x75\x07\xbb" + struct.pack("<i", number) + b"\xeb\x10"
        code += b"\x44\x8b\xc7"
    head = bytearray(0x400)
    head[0:2], head[0x3C:0x40] = b"MZ", struct.pack("<I", 0x80)
    head[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", head, 0x84, 0x8664, 2)                  # machine, 2 sections
    struct.pack_into("<H", head, 0x80 + 20, 0xF0)                   # the optional header's size
    table = 0x80 + 24 + 0xF0
    for i, (name, rva, raw, size) in enumerate(((b".text", text_rva, text_raw, 0x2000), (b".rdata", rdata_rva, rdata_raw, 0x2000))):
        head[table + 40 * i:table + 40 * i + 8] = name.ljust(8, b"\0")
        struct.pack_into("<IIII", head, table + 40 * i + 8, size, rva, size, raw)
    assert len(code) <= 0x2000 and len(strings) <= 0x2000
    return bytes(head) + code.ljust(0x2000, b"\xcc") + strings.ljust(0x2000, b"\0")


def test_medal_numbers_from_the_exe():
    ids = [(0, "medal_first_place"), (1, "medal_airborne_transmission")]
    ids += [(n, "medal_assist" if n == 8 else f"medal_made_up_{n}") for n in range(2, 140)]
    ids += [(310, "medal_campaign_emp")]
    numbers = art.medal_numbers(exe(ids))
    assert numbers == dict(ids), sorted(set(numbers.items()) ^ set(ids))[:6]
    assert numbers[8] == "medal_assist" and numbers[127] == "medal_made_up_127" and numbers[139] == "medal_made_up_139"
    wrong = [(n, "medal_wrong" if n == 8 else name) for n, name in ids]     # (number 8 is no longer the assist)
    for data, why in ((exe(wrong), "not as decoded"), (b"MZ" + bytes(0x400), "not a PE"), (exe(ids)[:0x400] + bytes(0x4000), "no medal ids")):
        try:
            art.medal_numbers(data)
        except (ValueError, struct.error) as e:
            assert why in str(e), (why, e)
        else:
            raise AssertionError(why)


def test_medal_names_and_kinds():
    assert art.pretty("$medal_Killing_Spree_name", "medal_killing_spree") == "Killing Spree"
    assert art.pretty("$medal_ArmAssist_name", "medal_arm_assist") == "Arm Assist"
    assert art.pretty("$MEDAL_VISITING_NAME", "medal_visiting") == "Visiting"
    assert art.pretty("", "medal_buck_wild") == "Buck Wild"
    cat = art.catalog(
        '<x><MPMedals>\n<!--SPREE--><!-- <Medal id="medal_hidden" name="$medal_Hidden_name"/> -->\n'
        '<Medal id="medal_killing_spree" name="$medal_Killing_Spree_name" smallIcon="Medal_KillingSpree" '
        'inHR="true" type="eMedalType_Spree" />\n</MPMedals>\n<MissionMedals>\n'
        '<Medal id="medal_campaign_headshot" name="$MEDAL_CAMPAIGN_HEADSHOT_name" smallIcon="Medal_HeadShot" '
        'type="eMedalType_Style" />\n</MissionMedals></x>')
    assert cat == {"medal_killing_spree": {"name": "Killing Spree", "icon": "Medal_KillingSpree", "kind": "Spree"},
                   "medal_campaign_headshot": {"name": "Campaign Headshot", "icon": "Medal_HeadShot", "kind": "Style"}}, cat


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"ok ({len(tests)} tests)")
    sys.exit(0)
