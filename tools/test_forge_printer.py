"""Reach Forge Printer, phase 1: the .mvar reader and writer.

Every variant here is built by hand in this file. One last test round-trips
the map variants in this PC's own MCC folder when there are any, reading
them where they are; it skips on a PC without them.
"""

import glob
import math
import os
import struct
import unittest
import zlib

from forge_printer import mvar
from forge_printer.bitstream import BitReader, BitWriter


def _unit(v):
    size = math.sqrt(sum(c * c for c in v))
    return tuple(c / size for c in v)


def sample_variant(version=32, label_names=("ctf", "slayer", "ffa_only")):
    v = mvar.MapVariant()
    v.version = version
    v.header = mvar.ContentHeader(
        ids=[0x1111, 0x2222, 0x3333, 0],
        map_id=3006,
        created=mvar.Author(1284641796, 0x0009000000000001, b"Builder One", True),
        modified=mvar.Author(1700000000, 0x0009000000000002, b"Builder Two", True),
        title="Test Yard",
        description="A hand-built sample",
    )
    v.map_checksum = 0x12345678
    v.map_id = 3006
    v.bounds = (-50.0, 50.0, -40.0, 40.0, -10.0, 30.0)
    v.budget_max = 10000
    v.budget_spent = 245
    v.labels = mvar.LabelTable.from_names(label_names)
    v.v32_block = 0xD1 << 120 if version >= 32 else None
    v.quotas = [mvar.Quota() for _ in range(6)]

    block = mvar.ForgeObject(type_index=4, variant_index=2, placement_flags=204)
    v.set_world_position(block, 1.0, -2.0, 3.0)

    tilted = mvar.ForgeObject(type_index=4, variant_index=8, placement_flags=204, up=261289, angle=4096)
    v.set_world_position(tilted, -12.5, 20.25, 0.5)

    weapon = mvar.ForgeObject(type_index=1, variant_index=0, mp_type=mvar.MP_TYPE_WEAPON, spare_clips=2,
                              respawn_time=30, placement_flags=12, label=1)
    v.set_world_position(weapon, 10.0, 10.0, 1.0)

    sender = mvar.ForgeObject(type_index=2, variant_index=1, mp_type=13, teleporter_channel=3,
                              teleporter_passability=1, placement_flags=12, team=1, color=0)
    v.set_world_position(sender, -30.0, 5.0, 2.0)

    zone = mvar.ForgeObject(type_index=5, variant_index=0, mp_type=16, placement_flags=204, team=2,
                            shape=mvar.SHAPE_BOX, spawn_sequence=255, label=0,
                            shape_dimensions=tuple(mvar.encode_dimension(d) for d in (10.0, 3.0, 5.0, 1.0)))
    v.set_world_position(zone, 0.0, 0.0, 0.0)

    hill = mvar.ForgeObject(type_index=5, variant_index=1, mp_type=26, placement_flags=204,
                            shape=mvar.SHAPE_CYLINDER, label=2,
                            shape_dimensions=tuple(mvar.encode_dimension(d) for d in (4.0, 2.0, 0.5)))
    v.set_world_position(hill, 25.0, -25.0, 4.0)

    for slot, obj in ((0, block), (1, tilted), (2, weapon), (7, sender), (300, zone), (650, hill)):
        v.objects[slot] = obj
    v.recount_quotas()
    return v


def sample_file(compressed=False, **kwargs):
    f = mvar.MvarFile(variant=sample_variant(**kwargs))
    f.chdr = mvar.build_chdr(f.variant.header)
    f.compressed = compressed
    return f


class BitStreamTest(unittest.TestCase):
    def test_first_value_lands_in_the_top_bits(self):
        w = BitWriter()
        w.write(1, 1)
        w.write(0b01, 2)
        w.write(0x4A, 8)
        self.assertEqual(w.to_bytes(), bytes([0b10101001, 0b01000000]))
        r = BitReader(w.to_bytes())
        self.assertEqual((r.read(1), r.read(2), r.read(8)), (1, 1, 0x4A))
        self.assertEqual(r.remaining, 5)

    def test_values_come_back_at_every_width(self):
        w = BitWriter()
        values = [(n, (0x9E3779B97F4A7C15 >> 3) & ((1 << n) - 1)) for n in range(0, 65)]
        for count, value in values:
            w.write(value, count)
        r = BitReader(w.to_bytes())
        for count, value in values:
            self.assertEqual(r.read(count), value)

    def test_bytes_cross_byte_borders(self):
        w = BitWriter()
        w.write(1, 3)
        w.write_bytes(b"ctf\0")
        r = BitReader(w.to_bytes())
        r.read(3)
        self.assertEqual(r.read_bytes(4), b"ctf\0")

    def test_bad_writes_and_reads_are_refused(self):
        w = BitWriter()
        with self.assertRaises(ValueError):
            w.write(8, 3)
        with self.assertRaises(ValueError):
            w.write(-1, 3)
        with self.assertRaises(EOFError):
            BitReader(b"\x00").read(9)


class ConversionTest(unittest.TestCase):
    def test_axis_bits_follow_the_map_size(self):
        # the bit counts the local Forge World, Zealot-sized and unbounded variants parse with
        self.assertEqual(mvar.axis_bit_count(-203.6, 277.66), 20)
        self.assertEqual(mvar.axis_bit_count(-360.83, 324.92), 21)
        self.assertEqual(mvar.axis_bit_count(-25.01, 117.79), 19)
        self.assertEqual(mvar.axis_bit_count(-26.85, 26.85), 17)
        self.assertEqual(mvar.axis_bit_count(-7.7, 14.29), 16)
        self.assertEqual(mvar.axis_bit_count(-20000.0, 20000.0), 23)

    def test_position_comes_back_within_half_a_step(self):
        low, high = -203.6, 277.66
        bits = mvar.axis_bit_count(low, high)
        step = (high - low) / (1 << bits)
        for value in (low, -27.049, 0.0, 100.0, 277.0, high):
            raw = mvar.encode_axis(value, low, high, bits)
            self.assertLess(raw, 1 << bits)
            self.assertLessEqual(abs(mvar.decode_axis(raw, low, high, bits) - value), step)
        with self.assertRaises(ValueError):
            mvar.encode_axis(high + 1.0, low, high, bits)

    def test_angles_match_the_values_files_hold(self):
        self.assertEqual(mvar.encode_angle(0.0), 8192)
        self.assertEqual(mvar.encode_angle(-math.pi / 2), 4096)
        self.assertEqual(mvar.encode_angle(math.pi / 2), 12288)
        self.assertEqual(mvar.encode_angle(-math.pi), 0)
        self.assertEqual(mvar.encode_angle(math.pi), 0)
        self.assertAlmostEqual(mvar.decode_angle(8192), 0.0, delta=2 * math.pi / 16384)

    def test_boundary_sizes_match_the_values_files_hold(self):
        # sizes the Forge menu shows as 1, 2, 3, 10, 30 and 40 are stored as these numbers
        for size, raw in ((0.0, 0), (1.0, 11), (2.0, 21), (3.0, 31), (10.0, 103), (30.0, 307), (40.0, 410), (200.0, 2047)):
            self.assertEqual(mvar.encode_dimension(size), raw)
            self.assertAlmostEqual(mvar.decode_dimension(raw), size, delta=0.06)

    def test_axis_aligned_up_vectors_sit_at_face_centres(self):
        for face in range(6):
            got_face, u, v = mvar.split_up(face * mvar.UP_FACE_SPAN + 208 * mvar.UP_GRID + 208)
            self.assertEqual(got_face, face)
            self.assertAlmostEqual(u, 0.0)
            self.assertAlmostEqual(v, 0.0)

    def near(self, got, want, places=3):
        for g, w in zip(got, want):
            self.assertAlmostEqual(g, w, places=places)

    def test_up_vectors_as_seen_in_the_game(self):
        # the six face middles
        for face, want in enumerate(((1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0), (0, 0, -1))):
            self.near(mvar.up_vector(mvar.join_up(face)), want)
            self.assertEqual(mvar.up_raw(want), mvar.join_up(face))
        # the tilt test's four antennas (2026-11-21): half way across a face is a lean of atan(1/2), the edge 45
        half = 1 / math.sqrt(5)
        self.near(mvar.up_vector(mvar.join_up(2, 208 + 208, 208)), (math.sqrt(0.5), 0, math.sqrt(0.5)))   # measured 47
        self.near(mvar.up_vector(mvar.join_up(2, 208 + 104, 208)), (half, 0, 2 * half))                 # measured 25
        self.near(mvar.up_vector(mvar.join_up(0, 208 + 104, 208)), (2 * half, half, 0))                 # 29, to +y
        self.near(mvar.up_vector(mvar.join_up(0, 208, 208 + 104)), (2 * half, 0, half))                 # 28, to +z
        self.near(mvar.up_vector(mvar.join_up(2, 208, 208 + 90)), _unit((0, 90 / 208.0, 1)))             # +v leans to +y
        with self.assertRaises(ValueError):
            mvar.up_vector(mvar.join_up(1, 300, 208))            # u and v on +Y are not worked out
        with self.assertRaises(ValueError):
            mvar.up_raw((0.1, 0.9, 0.2))

    def test_up_raw_is_the_nearest_grid_point(self):
        for degrees, heading in ((5, 0), (13.9, 90), (26.6, 200), (44, 315), (30, 37)):
            lean, around = math.radians(degrees), math.radians(heading)
            want = (math.sin(lean) * math.cos(around), math.sin(lean) * math.sin(around), math.cos(lean))
            got = mvar.up_vector(mvar.up_raw(want))
            off = math.degrees(math.acos(min(1.0, sum(g * w for g, w in zip(got, want)))))
            self.assertLess(off, 0.25, (degrees, heading))       # a grid step is about a quarter of a degree
            self.assertEqual(mvar.split_up(mvar.up_raw(want))[0], 2)

    def test_a_pieces_axes_as_seen_in_the_game(self):
        quarter = math.pi / 2
        # upright: turn 0 has the piece's +x to the east, turn +90 to the north
        self.near(mvar.axes((0, 0, 1), 0.0)[0], (1, 0, 0))
        self.near(mvar.axes((0, 0, 1), quarter)[0], (0, 1, 0))
        self.near(mvar.axes((0, 0, 1), 0.0)[1], (0, 1, 0))
        # the tilt test's three ramps: up +X turn 0, up +X turn +90, up +Y turn 0
        x, y, z = mvar.axes((1, 0, 0), 0.0)
        self.near(x, (0, 0, -1)); self.near(y, (0, 1, 0)); self.near(z, (1, 0, 0))
        x, y, z = mvar.axes((1, 0, 0), quarter)
        self.near(x, (0, 1, 0)); self.near(y, (0, 0, 1))
        x, y, z = mvar.axes((0, 1, 0), 0.0)
        self.near(x, (0, 0, -1)); self.near(y, (-1, 0, 0)); self.near(z, (0, 1, 0))
        # the turn test's leaning antennas: leaning east the +x stays east, leaning north it is to the north
        self.assertGreater(mvar.axes(mvar.up_vector(mvar.join_up(2, 208 + 90, 208)), 0.0)[0][0], 0.9)
        self.assertGreater(mvar.axes(mvar.up_vector(mvar.join_up(2, 208, 208 + 90)), 0.0)[0][1], 0.9)

    def test_turn_for_points_a_piece_up_a_slope(self):
        for degrees, heading in ((13.9, 0), (13.9, 90), (20, 113), (26.6, 225), (35, 300), (10, 44)):
            lean, around = math.radians(degrees), math.radians(heading)
            uphill = (math.cos(around), math.sin(around))
            up = (-math.sin(lean) * uphill[0], -math.sin(lean) * uphill[1], math.cos(lean))      # the slope's normal
            along = (math.cos(lean) * uphill[0], math.cos(lean) * uphill[1], math.sin(lean))     # up the slope
            x, y, z = mvar.axes(up, mvar.turn_for(up, along))
            self.near(x, along)
            self.near(z, up)
            self.near(y, (-uphill[1], uphill[0], 0.0))           # across the slope, level


class VariantStreamTest(unittest.TestCase):
    def test_hand_built_variant_survives_the_stream(self):
        for version in (31, 32):
            v = sample_variant(version=version)
            self.assertEqual(v.problems(), [])
            stream = v.to_stream()
            back = mvar.MapVariant.from_stream(stream)
            self.assertEqual(back, v)
            self.assertEqual(back.to_stream(), stream)

    def test_stream_starts_with_the_content_header(self):
        r = BitReader(sample_variant().to_stream())
        self.assertEqual(r.read(4), 6)                      # map variant
        self.assertEqual(r.read(32), mvar.PADDED_FILE_LENGTH)
        self.assertEqual([r.read(64) for _ in range(4)], [0x1111, 0x2222, 0x3333, 0])
        self.assertEqual((r.read(3), r.read(3), r.read(3)), (5, 3, 0))
        self.assertEqual(r.read(32), 3006)

    def test_an_empty_variant_is_one_bit_per_slot(self):
        v = sample_variant(label_names=())
        full = len(v.to_stream())
        v.objects = [None] * mvar.OBJECT_SLOTS
        v.recount_quotas()
        back = mvar.MapVariant.from_stream(v.to_stream())
        self.assertEqual(back.placed_objects(), [])
        self.assertLess(len(v.to_stream()), full)

    def test_positions_read_back_in_world_units(self):
        v = mvar.MapVariant.from_stream(sample_variant().to_stream())
        self.assertEqual(v.axis_bits(), (18, 18, 17))
        for got, want in zip(v.world_position(v.objects[1]), (-12.5, 20.25, 0.5)):
            self.assertAlmostEqual(got, want, delta=0.001)

    def test_type_specific_fields_are_kept(self):
        v = mvar.MapVariant.from_stream(sample_variant().to_stream())
        self.assertEqual(v.objects[2].spare_clips, 2)
        self.assertEqual((v.objects[7].teleporter_channel, v.objects[7].teleporter_passability), (3, 1))
        self.assertIsNone(v.objects[0].spare_clips)
        self.assertEqual(v.objects[300].shape, mvar.SHAPE_BOX)
        self.assertEqual(len(v.objects[300].shape_dimensions), 4)
        self.assertEqual(v.objects[650].label, 2)
        self.assertEqual(v.labels.names(), ["ctf", "slayer", "ffa_only"])

    def test_long_label_text_is_packed_and_short_text_is_not(self):
        short = sample_variant()
        self.assertIsNone(mvar.MapVariant.from_stream(short.to_stream()).labels.packed)
        names = tuple("label_number_%02d" % i for i in range(12))
        long = sample_variant(label_names=names)
        self.assertGreaterEqual(len(long.labels.data), mvar.LABEL_PACK_FROM)
        back = mvar.MapVariant.from_stream(long.to_stream())
        self.assertEqual(back.labels.names(), list(names))
        self.assertIsNotNone(back.labels.packed)
        self.assertEqual(struct.unpack(">I", back.labels.packed[:4])[0], len(long.labels.data))
        self.assertEqual(zlib.decompress(back.labels.packed[4:]), long.labels.data)
        self.assertEqual(back.to_stream(), long.to_stream())

    def test_problems_names_what_is_wrong(self):
        v = sample_variant()
        v.quotas[4].placed += 1
        v.objects[0].label = 9
        v.objects[2].type_index = 40
        text = " | ".join(v.problems())
        self.assertIn("quota 4", text)
        self.assertIn("label 9", text)
        self.assertIn("type 40", text)
        # a row's counts are 8 bits: 256 pieces of one palette row cannot be written, and problems() says so first
        v = sample_variant()
        v.quotas[0].maximum = mvar.ROW_MAX + 1
        self.assertIn("a palette row holds 255 at most", " | ".join(v.problems()))
        with self.assertRaises(ValueError):
            v.to_stream()

    def test_broken_streams_are_refused(self):
        stream = sample_variant().to_stream()
        with self.assertRaises(mvar.FormatError):
            mvar.MapVariant.from_stream(stream[:-40])
        with self.assertRaises(mvar.FormatError):
            mvar.MapVariant.from_stream(stream + b"\x00\x01")
        with self.assertRaises(mvar.FormatError):
            mvar.MapVariant.from_stream(bytes([0x70]) + stream[1:])   # content type 7
        with self.assertRaises(ValueError):
            bad = sample_variant()
            bad.objects.append(None)
            bad.to_stream()


class FileTest(unittest.TestCase):
    def test_plain_file_layout(self):
        data = sample_file().to_bytes()
        self.assertEqual(len(data), mvar.PADDED_FILE_LENGTH)
        self.assertEqual(data[:4], b"_blf")
        self.assertEqual(data[0x30:0x34], b"chdr")
        self.assertEqual(data[0x2F0:0x2F4], b"mvar")
        self.assertEqual(struct.unpack(">I", data[0x2F4:0x2F8])[0], mvar.MVAR_CHUNK_SIZE)
        self.assertEqual(data[-17:-13], b"_eof")
        self.assertEqual(struct.unpack(">I", data[-5:-1])[0], len(data) - 17)

    def test_file_round_trip_is_byte_identical(self):
        for compressed in (False, True):
            data = sample_file(compressed=compressed).to_bytes()
            back = mvar.MvarFile.from_bytes(data)
            self.assertEqual(back.compressed, compressed)
            self.assertEqual(back.variant, sample_variant())
            self.assertEqual(back.to_bytes(), data)

    def test_a_new_file_carries_the_xbox_360_hash(self):
        f = mvar.MvarFile.from_bytes(sample_file().to_bytes())
        self.assertTrue(f.hash_is_valid())
        stream = f.variant.to_stream()
        self.assertEqual(f.stored_hash, mvar.stream_hash(stream))

    def test_an_untouched_file_keeps_its_hash_and_tail_as_they_were(self):
        # files MCC saved hold a hash this module cannot make, and old ones hold leftovers after the stream
        data = bytearray(sample_file().to_bytes())
        data[0x2F0 + 12:0x2F0 + 32] = bytes(range(20))
        data[0x2F0 + mvar.MVAR_CHUNK_SIZE - 8:0x2F0 + mvar.MVAR_CHUNK_SIZE] = b"leftover"
        f = mvar.MvarFile.from_bytes(bytes(data))
        self.assertFalse(f.hash_is_valid())
        self.assertEqual(f.to_bytes(), bytes(data))

    def test_moving_one_object_changes_only_that_object(self):
        data = sample_file().to_bytes()
        f = mvar.MvarFile.from_bytes(data)
        v = f.variant
        x, y, z = v.world_position(v.objects[0])
        v.set_world_position(v.objects[0], x + 2.0, y, z + 1.0)
        f.set_text("Test Yard moved")
        out = f.to_bytes()
        self.assertEqual(len(out), len(data))
        back = mvar.MvarFile.from_bytes(out)
        self.assertTrue(back.hash_is_valid())
        self.assertEqual(back.variant.header.title, "Test Yard moved")
        self.assertEqual(mvar.read_chdr(back.chdr)["title"], "Test Yard moved")
        moved = back.variant.world_position(back.variant.objects[0])
        self.assertAlmostEqual(moved[0], x + 2.0, delta=0.001)
        self.assertAlmostEqual(moved[2], z + 1.0, delta=0.001)
        original = sample_variant()
        for slot in range(1, mvar.OBJECT_SLOTS):
            self.assertEqual(back.variant.objects[slot], original.objects[slot])
        self.assertEqual(back.variant.quotas, original.quotas)
        self.assertEqual(back.variant.problems(), [])

    def test_the_stored_hash_can_be_kept_or_forced(self):
        data = bytearray(sample_file().to_bytes())
        data[0x2F0 + 12:0x2F0 + 32] = bytes(range(20))
        f = mvar.MvarFile.from_bytes(bytes(data))
        f.variant.budget_spent += 5
        kept = mvar.MvarFile.from_bytes(f.to_bytes(rehash=False))
        self.assertEqual(kept.stored_hash, bytes(range(20)))
        self.assertEqual(kept.variant.budget_spent, 250)
        self.assertTrue(mvar.MvarFile.from_bytes(f.to_bytes()).hash_is_valid())
        untouched = mvar.MvarFile.from_bytes(bytes(data))
        self.assertTrue(mvar.MvarFile.from_bytes(untouched.to_bytes(rehash=True)).hash_is_valid())

    def test_a_changed_packed_file_still_reads(self):
        f = mvar.MvarFile.from_bytes(sample_file(compressed=True).to_bytes() + bytes(100))
        f.variant.objects[1] = None
        f.variant.recount_quotas()
        out = f.to_bytes()
        self.assertEqual(len(out) % 4096, 0)
        back = mvar.MvarFile.from_bytes(out)
        self.assertIsNone(back.variant.objects[1])
        self.assertTrue(back.hash_is_valid())

    def test_chdr_mirrors_the_stream_header_in_both_byte_orders(self):
        header = sample_variant().header
        for little in (True, False):
            fields = mvar.read_chdr(mvar.build_chdr(header, little_endian=little, build=0xFFFF if little else 0x2F21))
            self.assertEqual(fields["little_endian"], little)
            self.assertEqual(fields["content_type"], header.content_type - 1)
            self.assertEqual(fields["activity"], header.activity - 1)
            self.assertEqual(fields["file_length"], header.file_length)
            self.assertEqual(fields["ids"], header.ids)
            self.assertEqual(fields["map_id"], header.map_id)
            self.assertEqual(fields["created"], header.created)
            self.assertEqual(fields["modified"], header.modified)
            self.assertEqual((fields["title"], fields["description"]), (header.title, header.description))

    def test_files_that_are_not_variants_are_refused(self):
        data = sample_file().to_bytes()
        for bad in (b"", b"not a blf file at all", data[:500], data[:0x2F0] + b"gvar" + data[0x2F4:]):
            with self.assertRaises(mvar.FormatError):
                mvar.MvarFile.from_bytes(bad)

    def test_a_variant_too_big_for_its_chunk_is_refused(self):
        f = sample_file()
        f.chunk_size = 36 + len(f.variant.to_stream()) - 1
        with self.assertRaises(ValueError):
            f.to_bytes()


class LocalFilesTest(unittest.TestCase):
    def test_this_pcs_own_variants_round_trip(self):
        root = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "LocalLow", "MCC", "LocalFiles")
        paths = glob.glob(os.path.join(root, "*", "HaloReach", "Map", "*.mvar"))
        if not paths:
            self.skipTest("no Reach map variants in this PC's MCC folder")
        for path in paths:
            with open(path, "rb") as handle:
                data = handle.read()
            f = mvar.MvarFile.from_bytes(data)
            self.assertEqual(f.to_bytes(), data, os.path.basename(path))
            self.assertEqual(f.variant.problems(), [], os.path.basename(path))


if __name__ == "__main__":
    unittest.main()
