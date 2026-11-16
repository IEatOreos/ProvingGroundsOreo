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
