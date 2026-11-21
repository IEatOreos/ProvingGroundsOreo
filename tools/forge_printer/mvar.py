"""Reader and writer for Halo: Reach map variant files (.mvar), as MCC loads them.

The layout is written up in docs/reach_mvar_format.md. Every field is kept
as the raw number the file holds, so a file that is read and written back
without changes comes out byte for byte the same; helper functions turn the
raw numbers into world units and back.
"""

import hashlib
import math
import struct
import zlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .bitstream import BitReader, BitWriter

OBJECT_SLOTS = 651          # object entries in every variant, used or not
MVAR_CHUNK_SIZE = 0x7028    # the mvar chunk, header included
PADDED_FILE_LENGTH = 0x7329  # _blf + chdr + mvar + _eof, the size the headers quote

# The key Reach mixes into the SHA-1 of a variant's stream.
HASH_SALT = bytes.fromhex("EDD43009666D5C4A5C3657FAB40E022F535AC6C9EE471F01F1A44756B7714F1C36EC")

POSITION_STEP = 1.0 / 120.0 / 16.0   # coarsest step a position axis may have, world units
MAX_AXIS_BITS = 26
MAX_AXIS_STEPS = 0x800000

ANGLE_BITS = 14
UP_BITS = 20
UP_FACE_SPAN = (1 << UP_BITS) // 6   # 174762 values per cube face
UP_GRID = 417                        # grid points per face edge

DIMENSION_BITS = 11
DIMENSION_MAX = 200.0

SHAPE_NONE, SHAPE_SPHERE, SHAPE_CYLINDER, SHAPE_BOX = 0, 1, 2, 3
SHAPE_DIMENSIONS = {SHAPE_NONE: 0, SHAPE_SPHERE: 1, SHAPE_CYLINDER: 3, SHAPE_BOX: 4}

MP_TYPE_WEAPON = 1
MP_TYPE_TELEPORTERS = (12, 13, 14)
MP_TYPE_LOCATION_NAME = 19   # from other people's notes; no sample file has one

LABEL_PACK_FROM = 128        # label text of this many bytes or more is stored zlib-packed


class FormatError(ValueError):
    """The file is not a Reach map variant this module understands."""


# ---- value conversions ------------------------------------------------------

def axis_bit_count(low, high):
    """How many bits one position axis takes for a map whose bounds run low..high."""
    steps = int(math.ceil((high - low) / POSITION_STEP))
    steps = min(steps, MAX_AXIS_STEPS)
    return min(max(steps - 1, 0).bit_length(), MAX_AXIS_BITS)


def decode_axis(raw, low, high, bits):
    """World coordinate at the middle of the raw value's cell."""
    return low + (raw + 0.5) * (high - low) / (1 << bits)


def encode_axis(value, low, high, bits):
    if not low <= value <= high:
        raise ValueError("coordinate %r is outside the map bounds %r..%r" % (value, low, high))
    raw = int(math.floor((value - low) / (high - low) * (1 << bits)))
    return min(max(raw, 0), (1 << bits) - 1)


def decode_angle(raw):
    """Radians, -pi..pi."""
    return (raw + 0.5) * (2.0 * math.pi) / (1 << ANGLE_BITS) - math.pi


def encode_angle(radians):
    turn = (radians + math.pi) / (2.0 * math.pi)
    turn -= math.floor(turn)
    return min(int(math.floor(turn * (1 << ANGLE_BITS))), (1 << ANGLE_BITS) - 1)


def decode_dimension(raw):
    """A boundary size in world units. 0 and the top value are exact."""
    top = (1 << DIMENSION_BITS) - 1
    if raw <= 0:
        return 0.0
    if raw >= top:
        return DIMENSION_MAX
    return (raw - 0.5) * DIMENSION_MAX / (top - 1)


def encode_dimension(value):
    top = (1 << DIMENSION_BITS) - 1
    if value <= 0.0:
        return 0
    if value >= DIMENSION_MAX:
        return top
    return min(1 + int(math.floor(value * (top - 1) / DIMENSION_MAX)), top - 1)


def split_up(raw):
    """A raw up vector as (cube face 0..5, u, v), u and v running -1..1 across the face."""
    face, rest = divmod(raw, UP_FACE_SPAN)
    u, v = divmod(rest, UP_GRID)
    half = (UP_GRID - 1) / 2.0
    return face, u / half - 1.0, v / half - 1.0


# ---- the pieces of a variant ------------------------------------------------

@dataclass
class Author:
    timestamp: int = 0      # seconds since 1970
    xuid: int = 0
    name: bytes = b""       # up to 16 bytes
    is_online: bool = False


@dataclass
class ContentHeader:
    """The description block at the start of the stream (a copy also sits in the chdr chunk)."""
    content_type: int = 6   # 6 = map variant (the chdr chunk holds this minus one)
    file_length: int = PADDED_FILE_LENGTH
    ids: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    activity: int = 5       # the chdr chunk holds this minus one
    game_mode: int = 3
    engine: int = 0
    map_id: int = 0
    category: int = 255
    created: Author = field(default_factory=Author)
    modified: Author = field(default_factory=Author)
    title: str = ""
    description: str = ""


@dataclass
class LabelTable:
    """Forge label names. An object's `label` is an index into `offsets`."""
    offsets: List[Optional[int]] = field(default_factory=list)   # byte offset of each name in `data`
    data: bytes = b""                                           # the names, each ending in a zero byte
    packed: Optional[bytes] = None    # the zlib-packed form as the file held it, when it was packed

    def names(self):
        out = []
        for offset in self.offsets:
            if offset is None:
                out.append(None)
            else:
                out.append(self.data[offset:].split(b"\0", 1)[0].decode("latin-1"))
        return out

    @classmethod
    def from_names(cls, names):
        data = bytearray()
        offsets = []
        for name in names:
            offsets.append(len(data))
            data += name.encode("latin-1") + b"\0"
        return cls(offsets=offsets, data=bytes(data))


@dataclass
class Quota:
    """One row of the map's object palette: how many of that entry the variant holds."""
    minimum: int = 0
    maximum: int = 0
    placed: int = 0


@dataclass
class ForgeObject:
    """One placed object. Every field is the raw number from the file."""
    flags: int = 1                                   # 2 bits; 1 in every file seen
    type_index: Optional[int] = 0                    # row of the quota table (8 bits)
    variant_index: Optional[int] = 0                 # which item of that row (5 bits)
    position: Optional[Tuple[int, int, int]] = (0, 0, 0)   # see MapVariant.world_position
    up: Optional[int] = None                         # 20 bits; None = the world's up
    angle: int = 1 << (ANGLE_BITS - 1)               # 14 bits, turn about the up vector
    spawn_relative: int = 0                          # 10 bits; 0 in every file seen
    shape: int = SHAPE_NONE
    shape_dimensions: Tuple[int, ...] = ()           # 11 bits each; see decode_dimension
    spawn_sequence: int = 0                          # 8 bits (255 is -1)
    respawn_time: int = 0                            # 8 bits, seconds
    mp_type: int = 0                                 # 5 bits, the kind of multiplayer object
    label: Optional[int] = None                      # index into the label table
    placement_flags: int = 0                         # 8 bits
    team: int = 9                                    # 4 bits: team number plus one, 9 = neutral
    color: Optional[int] = None                      # 3 bits; None = the team's colour
    spare_clips: Optional[int] = None                # weapons only
    teleporter_channel: Optional[int] = None         # teleporters only
    teleporter_passability: Optional[int] = None     # teleporters only
    location_name: Optional[int] = None              # location-name objects only


@dataclass
class MapVariant:
    header: ContentHeader = field(default_factory=ContentHeader)
    version: int = 32
    unknown_32: int = 0xFFFFFFFF
    map_checksum: int = 0            # changes with the map and the game build
    map_id: int = 0
    flag_a: bool = False
    flag_b: bool = False
    bounds_raw: Tuple[int, ...] = (0,) * 6   # x min, x max, y min, y max, z min, z max as float bits
    budget_max: int = 0
    budget_spent: int = 0
    labels: LabelTable = field(default_factory=LabelTable)
    v32_block: Optional[int] = None  # 128 bits MCC's version 32 adds before the objects
    objects: List[Optional[ForgeObject]] = field(default_factory=lambda: [None] * OBJECT_SLOTS)
    quotas: List[Quota] = field(default_factory=list)

    # -- bounds and positions --

    @property
    def bounds(self):
        return tuple(struct.unpack(">f", struct.pack(">I", raw))[0] for raw in self.bounds_raw)

    @bounds.setter
    def bounds(self, values):
        self.bounds_raw = tuple(struct.unpack(">I", struct.pack(">f", value))[0] for value in values)

    def axis_bits(self):
        b = self.bounds
        return tuple(axis_bit_count(b[i * 2], b[i * 2 + 1]) for i in range(3))

    def world_position(self, obj):
        b = self.bounds
        bits = self.axis_bits()
        return tuple(decode_axis(obj.position[i], b[i * 2], b[i * 2 + 1], bits[i]) for i in range(3))

    def set_world_position(self, obj, x, y, z):
        b = self.bounds
        bits = self.axis_bits()
        obj.position = tuple(encode_axis(value, b[i * 2], b[i * 2 + 1], bits[i]) for i, value in enumerate((x, y, z)))

    def placed_objects(self):
        """(slot, object) for each used slot."""
        return [(slot, obj) for slot, obj in enumerate(self.objects) if obj is not None]

    def recount_quotas(self):
        """Set each quota row's placed count from the objects (and lift its maximum to match)."""
        counts = {}
        for _, obj in self.placed_objects():
            counts[obj.type_index] = counts.get(obj.type_index, 0) + 1
        for index, quota in enumerate(self.quotas):
            quota.placed = counts.get(index, 0)
            quota.maximum = max(quota.maximum, quota.placed)

    def problems(self):
        """Things about this variant the game would likely reject. Empty when it looks sound."""
        out = []
        if len(self.objects) != OBJECT_SLOTS:
            out.append("%d object slots, expected %d" % (len(self.objects), OBJECT_SLOTS))
        if (self.v32_block is None) != (self.version < 32):
            out.append("the 128-bit block belongs to version 32 and later only")
        if len(self.quotas) >= 512:
            out.append("too many quota rows")
        bits = self.axis_bits()
        counts = {}
        for slot, obj in self.placed_objects():
            if obj.type_index is None or obj.type_index >= len(self.quotas):
                out.append("object %d: type %r has no quota row" % (slot, obj.type_index))
            counts[obj.type_index] = counts.get(obj.type_index, 0) + 1
            if obj.position is not None:
                for axis in range(3):
                    if obj.position[axis] >> bits[axis]:
                        out.append("object %d: position does not fit the map bounds" % slot)
                        break
            if obj.label is not None and obj.label >= len(self.labels.offsets):
                out.append("object %d: label %d is not in the label table" % (slot, obj.label))
            if len(obj.shape_dimensions) != SHAPE_DIMENSIONS.get(obj.shape, -1):
                out.append("object %d: shape %d with %d sizes" % (slot, obj.shape, len(obj.shape_dimensions)))
        for index, quota in enumerate(self.quotas):
            if quota.placed != counts.get(index, 0):
                out.append("quota %d says %d placed, the objects number %d" % (index, quota.placed, counts.get(index, 0)))
        return out

    # -- stream --

    @classmethod
    def from_stream(cls, stream):
        """Parse the bit stream of an mvar chunk (the bytes its length field covers)."""
        r = BitReader(stream)
        try:
            variant = cls._read(r)
        except EOFError as error:
            raise FormatError("the variant stream ends early: %s" % error)
        if r.remaining >= 8 or r.read(r.remaining):
            raise FormatError("%d bits left over after the quota table" % r.remaining)
        return variant

    @classmethod
    def _read(cls, r):
        v = cls()
        v.header = _read_header(r)
        v.version = r.read(8)
        if v.version not in (31, 32):
            raise FormatError("map variant version %d is not one this module knows (31, 32)" % v.version)
        v.unknown_32 = r.read(32)
        v.map_checksum = r.read(32)
        quota_count = r.read(9)
        v.map_id = r.read(32)
        v.flag_a = r.read_bool()
        v.flag_b = r.read_bool()
        v.bounds_raw = tuple(r.read(32) for _ in range(6))
        v.budget_max = r.read(32)
        v.budget_spent = r.read(32)
        v.labels = _read_labels(r)
        v.v32_block = r.read(128) if v.version >= 32 else None
        bits = v.axis_bits()
        v.objects = [_read_object(r, bits) if r.read_bool() else None for _ in range(OBJECT_SLOTS)]
        v.quotas = [Quota(r.read(8), r.read(8), r.read(8)) for _ in range(quota_count)]
        return v

    def to_stream(self):
        """The bit stream for an mvar chunk, zero-padded to a whole byte."""
        if len(self.objects) != OBJECT_SLOTS:
            raise ValueError("a variant has exactly %d object slots" % OBJECT_SLOTS)
        if (self.v32_block is None) != (self.version < 32):
            raise ValueError("the 128-bit block belongs to version 32 and later only")
        w = BitWriter()
        _write_header(w, self.header)
        w.write(self.version, 8)
        w.write(self.unknown_32, 32)
        w.write(self.map_checksum, 32)
        w.write(len(self.quotas), 9)
        w.write(self.map_id, 32)
        w.write_bool(self.flag_a)
        w.write_bool(self.flag_b)
        for raw in self.bounds_raw:
            w.write(raw, 32)
        w.write(self.budget_max, 32)
        w.write(self.budget_spent, 32)
        _write_labels(w, self.labels)
        if self.v32_block is not None:
            w.write(self.v32_block, 128)
        bits = self.axis_bits()
        for obj in self.objects:
            if obj is None:
                w.write_bool(False)
            else:
                w.write_bool(True)
                _write_object(w, obj, bits)
        for quota in self.quotas:
            w.write(quota.minimum, 8)
            w.write(quota.maximum, 8)
            w.write(quota.placed, 8)
        return w.to_bytes()


def _read_text(r, unit_bits, limit):
    units = []
    for _ in range(limit):
        unit = r.read(unit_bits)
        if unit == 0:
            break
        units.append(unit)
    return units


def _write_text(w, units, unit_bits, limit):
    if len(units) > limit:
        raise ValueError("text of %d characters is over the limit of %d" % (len(units), limit))
    if 0 in units:
        raise ValueError("text holds a zero character")
    for unit in units:
        w.write(unit, unit_bits)
    if len(units) < limit:
        w.write(0, unit_bits)


def _read_author(r):
    timestamp = r.read(64)
    xuid = r.read(64)
    name = bytes(_read_text(r, 8, 16))
    return Author(timestamp, xuid, name, r.read_bool())


def _write_author(w, author):
    w.write(author.timestamp, 64)
    w.write(author.xuid, 64)
    _write_text(w, list(author.name), 8, 16)
    w.write_bool(author.is_online)


def _read_header(r):
    h = ContentHeader()
    h.content_type = r.read(4)
    h.file_length = r.read(32)
    h.ids = [r.read(64) for _ in range(4)]
    h.activity = r.read(3)
    h.game_mode = r.read(3)
    h.engine = r.read(3)
    h.map_id = r.read(32)
    h.category = r.read(8)
    h.created = _read_author(r)
    h.modified = _read_author(r)
    h.title = "".join(map(chr, _read_text(r, 16, 128)))
    h.description = "".join(map(chr, _read_text(r, 16, 128)))
    if h.content_type != 6:
        raise FormatError("content type %d is not a map variant" % h.content_type)
    return h


def _write_header(w, h):
    w.write(h.content_type, 4)
    w.write(h.file_length, 32)
    if len(h.ids) != 4:
        raise ValueError("a content header has four ids")
    for value in h.ids:
        w.write(value, 64)
    w.write(h.activity, 3)
    w.write(h.game_mode, 3)
    w.write(h.engine, 3)
    w.write(h.map_id, 32)
    w.write(h.category, 8)
    _write_author(w, h.created)
    _write_author(w, h.modified)
    _write_text(w, [ord(c) for c in h.title], 16, 128)
    _write_text(w, [ord(c) for c in h.description], 16, 128)


def _read_labels(r):
    table = LabelTable()
    count = r.read(9)
    table.offsets = [r.read(12) if r.read_bool() else None for _ in range(count)]
    if count:
        size = r.read(13)
        if r.read_bool():
            packed = r.read_bytes(r.read(13))
            try:
                data = zlib.decompress(packed[4:])
            except zlib.error as error:
                raise FormatError("the label table does not unpack: %s" % error)
            if len(packed) < 4 or struct.unpack(">I", packed[:4])[0] != size or len(data) != size:
                raise FormatError("the label table's sizes disagree")
            table.data = data
            table.packed = packed
        else:
            table.data = r.read_bytes(size)
    return table


def _write_labels(w, table):
    w.write(len(table.offsets), 9)
    for offset in table.offsets:
        if offset is None:
            w.write_bool(False)
        else:
            w.write_bool(True)
            w.write(offset, 12)
    if not table.offsets:
        if table.data:
            raise ValueError("label text without any label")
        return
    w.write(len(table.data), 13)
    packed = table.packed
    if packed is not None:
        # keep the file's own packed bytes while they still hold this text
        try:
            if zlib.decompress(packed[4:]) != table.data:
                packed = None
        except zlib.error:
            packed = None
    if packed is None and len(table.data) >= LABEL_PACK_FROM:
        packed = struct.pack(">I", len(table.data)) + zlib.compress(table.data, 9)
    if packed is None:
        w.write_bool(False)
        w.write_bytes(table.data)
    else:
        w.write_bool(True)
        w.write(len(packed), 13)
        w.write_bytes(packed)


def _read_optional(r, bits):
    """A field behind an 'absent' bit: 1 = not there, 0 = the value follows."""
    return None if r.read_bool() else r.read(bits)


def _write_optional(w, value, bits):
    if value is None:
        w.write_bool(True)
    else:
        w.write_bool(False)
        w.write(value, bits)


def _read_object(r, axis_bits):
    o = ForgeObject()
    o.flags = r.read(2)
    o.type_index = _read_optional(r, 8)
    o.variant_index = _read_optional(r, 5)
    if r.read_bool():
        o.position = tuple(r.read(bits) for bits in axis_bits)
        o.up = None if r.read_bool() else r.read(UP_BITS)
        o.angle = r.read(ANGLE_BITS)
    else:
        o.position = None
        o.up = None
        o.angle = 0
    o.spawn_relative = r.read(10)
    o.shape = r.read(2)
    o.shape_dimensions = tuple(r.read(DIMENSION_BITS) for _ in range(SHAPE_DIMENSIONS[o.shape]))
    o.spawn_sequence = r.read(8)
    o.respawn_time = r.read(8)
    o.mp_type = r.read(5)
    o.label = _read_optional(r, 8)
    o.placement_flags = r.read(8)
    o.team = r.read(4)
    o.color = _read_optional(r, 3)
    if o.mp_type == MP_TYPE_WEAPON:
        o.spare_clips = r.read(8)
    elif o.mp_type in MP_TYPE_TELEPORTERS:
        o.teleporter_channel = r.read(5)
        o.teleporter_passability = r.read(5)
    elif o.mp_type == MP_TYPE_LOCATION_NAME:
        o.location_name = r.read(8)
    return o


def _write_object(w, o, axis_bits):
    w.write(o.flags, 2)
    _write_optional(w, o.type_index, 8)
    _write_optional(w, o.variant_index, 5)
    if o.position is None:
        w.write_bool(False)
    else:
        w.write_bool(True)
        for value, bits in zip(o.position, axis_bits):
            w.write(value, bits)
        if o.up is None:
            w.write_bool(True)
        else:
            w.write_bool(False)
            w.write(o.up, UP_BITS)
        w.write(o.angle, ANGLE_BITS)
    w.write(o.spawn_relative, 10)
    if len(o.shape_dimensions) != SHAPE_DIMENSIONS[o.shape]:
        raise ValueError("shape %d takes %d sizes" % (o.shape, SHAPE_DIMENSIONS[o.shape]))
    w.write(o.shape, 2)
    for value in o.shape_dimensions:
        w.write(value, DIMENSION_BITS)
    w.write(o.spawn_sequence, 8)
    w.write(o.respawn_time, 8)
    w.write(o.mp_type, 5)
    _write_optional(w, o.label, 8)
    w.write(o.placement_flags, 8)
    w.write(o.team, 4)
    _write_optional(w, o.color, 3)
    if o.mp_type == MP_TYPE_WEAPON:
        w.write(o.spare_clips or 0, 8)
    elif o.mp_type in MP_TYPE_TELEPORTERS:
        w.write(o.teleporter_channel or 0, 5)
        w.write(o.teleporter_passability or 0, 5)
    elif o.mp_type == MP_TYPE_LOCATION_NAME:
        w.write(o.location_name or 0, 8)


# ---- the chdr chunk ---------------------------------------------------------
#
# A second, fixed-layout copy of the content header. MCC writes it little-endian
# with build number 0xFFFF; files that came from an Xbox 360 hold it big-endian.

CHDR_SIZE = 0x2C0
_CHDR_TITLE = 12 + 0x84
_CHDR_DESCRIPTION = 12 + 0x184
_CHDR_TEXT_BYTES = 256


def _chdr_little_endian(chunk):
    return chunk[12:14] == b"\xff\xff"


def read_chdr(chunk):
    """The chdr chunk's fields as a dict (for display and cross-checks)."""
    if len(chunk) != CHDR_SIZE or chunk[:4] != b"chdr":
        raise FormatError("not a chdr chunk")
    little = _chdr_little_endian(chunk)
    e = "<" if little else ">"
    text = "utf-16-le" if little else "utf-16-be"
    p = chunk[12:]

    def author(at):
        timestamp, xuid = struct.unpack(e + "QQ", p[at:at + 16])
        return Author(timestamp, xuid, p[at + 16:at + 32].split(b"\0", 1)[0], bool(p[at + 32]))

    def string(at):
        return p[at:at + _CHDR_TEXT_BYTES].decode(text, "replace").split("\0", 1)[0]

    return {
        "little_endian": little,
        "build": struct.unpack(e + "H", p[0:2])[0],
        "content_type": p[4],
        "file_length": struct.unpack(e + "I", p[8:12])[0],
        "ids": list(struct.unpack(e + "4Q", p[12:44])),
        "activity": p[0x2C],
        "game_mode": p[0x2D],
        "engine": p[0x2E],
        "map_id": struct.unpack(e + "I", p[0x30:0x34])[0],
        "category": p[0x34],
        "created": author(0x3C),
        "modified": author(0x60),
        "title": string(0x84),
        "description": string(0x184),
    }


def build_chdr(header, little_endian=True, build=0xFFFF):
    """A chdr chunk that mirrors a stream content header."""
    e = "<" if little_endian else ">"
    text = "utf-16-le" if little_endian else "utf-16-be"
    p = bytearray(CHDR_SIZE - 12)
    struct.pack_into(e + "H", p, 0, build)
    p[4] = header.content_type - 1
    struct.pack_into(e + "I", p, 8, header.file_length)
    struct.pack_into(e + "4Q", p, 12, *header.ids)
    p[0x2C] = header.activity - 1
    p[0x2D] = header.game_mode
    p[0x2E] = header.engine
    struct.pack_into(e + "I", p, 0x30, header.map_id)
    p[0x34] = header.category
    for at, author in ((0x3C, header.created), (0x60, header.modified)):
        struct.pack_into(e + "QQ", p, at, author.timestamp, author.xuid)
        p[at + 16:at + 16 + len(author.name)] = author.name
        p[at + 32] = 1 if author.is_online else 0
    for at, value in ((0x84, header.title), (0x184, header.description)):
        raw = value.encode(text)
        p[at:at + len(raw)] = raw
    return struct.pack(">4sIHH", b"chdr", CHDR_SIZE, 10, 2) + bytes(p)


def _chdr_with_text(chunk, title, description):
    text = "utf-16-le" if _chdr_little_endian(chunk) else "utf-16-be"
    out = bytearray(chunk)
    for at, value in ((_CHDR_TITLE, title), (_CHDR_DESCRIPTION, description)):
        raw = value.encode(text)
        if len(raw) > _CHDR_TEXT_BYTES - 2:
            raise ValueError("text is over 127 characters")
        out[at:at + _CHDR_TEXT_BYTES] = raw + bytes(_CHDR_TEXT_BYTES - len(raw))
    return bytes(out)


# ---- the file ---------------------------------------------------------------

BLF_HEADER = struct.pack(">4sIHH", b"_blf", 0x30, 1, 2) + b"\xff\xfe" + bytes(0x22)


def stream_hash(stream):
    """The SHA-1 Reach stores ahead of a variant stream."""
    return hashlib.sha1(HASH_SALT + struct.pack(">I", len(stream)) + stream).digest()


def _split_chunks(data):
    chunks = []
    at = 0
    while True:
        if at + 12 > len(data):
            raise FormatError("the file ends before its _eof chunk")
        tag, size, major, minor = struct.unpack(">4sIHH", data[at:at + 12])
        if size < 12 or at + size > len(data):
            raise FormatError("chunk %r at %d has a bad size" % (tag, at))
        chunks.append((tag, major, minor, data[at:at + size]))
        at += size
        if tag == b"_eof":
            return chunks, data[at:]


@dataclass
class MvarFile:
    """A whole .mvar file: its chunks around one MapVariant."""
    variant: MapVariant = field(default_factory=MapVariant)
    blf: bytes = BLF_HEADER
    chdr: bytes = b""
    chunk_version: Tuple[int, int] = (31, 1)
    chunk_size: int = MVAR_CHUNK_SIZE
    stored_hash: bytes = bytes(20)
    stream_tail: bytes = b""          # whatever sat in the chunk after the stream
    compressed: bool = False          # the mvar chunk is wrapped in a _cmp chunk
    eof_flag: int = 0
    padding: bytes = b""              # zero bytes after _eof
    # what the file held, so an unchanged file writes back byte for byte
    _source_stream: Optional[bytes] = field(default=None, repr=False, compare=False)
    _source_chunk: Optional[bytes] = field(default=None, repr=False, compare=False)
    _source_packed: Optional[bytes] = field(default=None, repr=False, compare=False)

    @classmethod
    def from_bytes(cls, data):
        if data[:4] != b"_blf":
            raise FormatError("not a BLF file (no _blf chunk)")
        chunks, padding = _split_chunks(data)
        tags = [c[0] for c in chunks]
        if tags not in ([b"_blf", b"chdr", b"mvar", b"_eof"], [b"_blf", b"chdr", b"_cmp", b"_eof"]):
            raise FormatError("unexpected chunks %r" % (tags,))
        f = cls()
        f.blf = chunks[0][3]
        f.chdr = chunks[1][3]
        if len(f.chdr) != CHDR_SIZE:
            raise FormatError("chdr chunk of %d bytes, expected %d" % (len(f.chdr), CHDR_SIZE))
        body = chunks[2][3]
        if tags[2] == b"_cmp":
            f.compressed = True
            if len(body) < 17 or body[12] != 0:
                raise FormatError("unknown compression kind in the _cmp chunk")
            f._source_packed = body[17:]
            try:
                chunk = zlib.decompress(f._source_packed)
            except zlib.error as error:
                raise FormatError("the _cmp chunk does not unpack: %s" % error)
            if len(chunk) != struct.unpack(">I", body[13:17])[0]:
                raise FormatError("the _cmp chunk's size field is wrong")
        else:
            chunk = body
        if len(chunk) < 36 or chunk[:4] != b"mvar":
            raise FormatError("no mvar chunk inside")
        tag, size, major, minor = struct.unpack(">4sIHH", chunk[:12])
        if size != len(chunk):
            raise FormatError("the mvar chunk's size field is wrong")
        f.chunk_version = (major, minor)
        f.chunk_size = size
        f.stored_hash = chunk[12:32]
        length = struct.unpack(">I", chunk[32:36])[0]
        if 36 + length > size:
            raise FormatError("the variant stream runs past its chunk")
        stream = chunk[36:36 + length]
        f.stream_tail = chunk[36 + length:]
        f.variant = MapVariant.from_stream(stream)
        eof = chunks[3][3]
        if len(eof) != 17:
            raise FormatError("_eof chunk of %d bytes, expected 17" % len(eof))
        f.eof_flag = eof[16]
        f.padding = padding
        f._source_stream = stream
        f._source_chunk = chunk
        return f

    @classmethod
    def read(cls, path):
        with open(path, "rb") as handle:
            return cls.from_bytes(handle.read())

    def hash_is_valid(self):
        """Whether the stored hash is the Xbox 360 game's hash of the stream as it was read."""
        return self._source_stream is not None and stream_hash(self._source_stream) == self.stored_hash

    def set_text(self, title, description=None):
        """Change the name (and description) in both copies of the header."""
        if description is None:
            description = self.variant.header.description
        self.chdr = _chdr_with_text(self.chdr, title, description)
        self.variant.header.title = title
        self.variant.header.description = description

    def _chunk(self, rehash):
        stream = self.variant.to_stream()
        room = self.chunk_size - 36
        if len(stream) > room:
            raise ValueError("the variant needs %d bytes, the chunk holds %d" % (len(stream), room))
        changed = stream != self._source_stream
        if rehash is None:
            rehash = changed               # untouched: keep whatever the file had
        digest = stream_hash(stream) if rehash else self.stored_hash
        tail = b"" if changed else self.stream_tail
        tail = tail[:room - len(stream)].ljust(room - len(stream), b"\0")
        head = struct.pack(">4sIHH", b"mvar", self.chunk_size, *self.chunk_version)
        return head + digest + struct.pack(">I", len(stream)) + stream + tail

    def to_bytes(self, rehash=None):
        """The file's bytes. `rehash`: True writes the Xbox 360 hash of the stream, False keeps
        the stored hash, None (the default) rehashes only when the stream changed."""
        chunk = self._chunk(rehash)
        if self.compressed:
            if chunk == self._source_chunk and self._source_packed is not None:
                packed = self._source_packed   # the game's own packing, byte for byte
            else:
                packed = zlib.compress(chunk, 6)
            body = struct.pack(">4sIHHBI", b"_cmp", 17 + len(packed), 1, 1, 0, len(chunk)) + packed
        else:
            body = chunk
        out = self.blf + self.chdr + body
        out += struct.pack(">4sIHHIB", b"_eof", 17, 1, 1, len(out), self.eof_flag)
        padding = self.padding
        if chunk != self._source_chunk and self.compressed and padding:
            # MCC rounds these files up to a whole number of 4096-byte blocks
            padding = bytes(-len(out) % 4096)
        return out + padding

    def write(self, path, rehash=None):
        data = self.to_bytes(rehash)
        with open(path, "wb") as handle:
            handle.write(data)
        return data
