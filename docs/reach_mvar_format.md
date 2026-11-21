# Halo: Reach map variant files (`.mvar`)

Our own notes on the format, worked out for the Reach Forge Printer
(`docs/REACH_FORGE_PRINTER_PLAN.md`, phase 1). The code is
`tools/forge_printer/mvar.py`; the tests are `tools/test_forge_printer.py`.

**How sure this is.** The layout below was checked against the 34 Reach map
variants in one PC's MCC folder (2026-11-21): old Xbox 360 era files and files
MCC itself saved, on seven maps. Each one parses to its last bit, the per-type
object counts agree with the file's own quota table, and each one written back
comes out byte for byte the same. One changed file has been loaded in the game
(2026-11-21): a copy of an MCC-saved Forge World variant with a new title and
one wall lifted 6 units listed in Reach Forge, loaded, and showed the wall
moved. What all of that does not prove is listed under
[Still unknown](#still-unknown).

Where MCC keeps them:
`%USERPROFILE%\AppData\LocalLow\MCC\LocalFiles\<account id>\HaloReach\Map\*.mvar`

## 1. Container

A BLF file: chunks one after another. Each chunk starts with a 12-byte header,
big-endian: 4-character tag, `u32` size (header included), `u16` major version,
`u16` minor version.

| Chunk | Size | Version | Holds |
|---|---|---|---|
| `_blf` | 0x30 | 1.2 | `FF FE`, then zeros |
| `chdr` | 0x2C0 | 10.2 | content header, fixed layout (section 2) |
| `mvar` | 0x7028 | 31.1 | the map variant (section 3) |
| `_eof` | 0x11 | 1.1 | `u32` offset of this chunk in the file, then one zero byte |

Two shapes of file exist:

- **Plain** (what MCC writes when you save in Forge): the four chunks above,
  29,481 bytes (0x7329). Some copies carry zero bytes after `_eof`.
- **Packed** (files that came from an Xbox 360 or the file share): the `mvar`
  chunk is replaced by a `_cmp` chunk, version 1.1. Its payload is one byte
  `0` (the compression kind), a `u32` with the unpacked size (0x7028), then a
  zlib stream that unpacks to the whole `mvar` chunk, header included. The
  file is zero-padded to a multiple of 4,096 bytes.

The `mvar` chunk header says version 31 even when the stream inside says 32.

Python's zlib does not produce the same bytes as the game's packer, so a packed
file can only be written back identically while its `mvar` chunk is unchanged
(the writer then reuses the original packed bytes). A changed one is packed
again with zlib; MCC also reads the plain shape, which is what it writes itself.

## 2. The `chdr` chunk

A fixed-layout copy of the description. MCC writes it **little-endian** with
build number 0xFFFF; files from an Xbox 360 hold it **big-endian** with the
game's build number (0x2F21, 0x2E54). Offsets from the end of the chunk header:

| Offset | Type | Field |
|---|---|---|
| 0x00 | u16 | build number (0xFFFF = MCC, little-endian file) |
| 0x04 | u8 | content type: 5 = map variant |
| 0x08 | u32 | file length (0x7329 even in a packed file) |
| 0x0C | u64 × 4 | ids (an MCC save repeats one value three times; the fourth is 0) |
| 0x2C | u8 | activity (4 in every file) |
| 0x2D | u8 | game mode (3) |
| 0x2E | u8 | engine (0) |
| 0x30 | u32 | map id (3006 = Forge World) |
| 0x34 | u8 | category (0xFF) |
| 0x3C | author | created by |
| 0x60 | author | modified by |
| 0x84 | 128 × u16 | title, UTF-16 in the file's byte order |
| 0x184 | 128 × u16 | description |
| 0x284 | 0x30 bytes | zeros |

An author is 0x24 bytes: `u64` time (seconds since 1970), `u64` XUID, 16 bytes
of name, one byte "is online", three bytes of padding.

In a plain MCC file these fields equal the stream's own header (section 3.1).
In a packed file share copy the ids, dates and sometimes the title differ, so
the two are separate records; the reader keeps the chunk as raw bytes and the
writer only rewrites the title and description.

## 3. The `mvar` chunk

| Offset | Size | Field |
|---|---|---|
| 0x00 | 12 | chunk header |
| 0x0C | 20 | hash (section 5) |
| 0x20 | 4 | `u32` stream length in bytes |
| 0x24 | length | the bit stream |
| after | rest | unused; zeros in new files, leftovers in some old ones |

The stream is read **most significant bit first**: the first field sits in the
top bits of the first byte. Multi-bit numbers are plain unsigned, top bit
first. The stream ends on a partial byte padded with zero bits.

Two idioms recur:

- **Text**: characters one after another, ended by a zero character, with a
  maximum count. Text exactly as long as the maximum has no zero after it.
- **Absent bit**: one bit, then the value only if the bit was 0.

### 3.1 Content header

| Bits | Field |
|---|---|
| 4 | content type: 6 = map variant (`chdr` value plus one) |
| 32 | file length |
| 64 × 4 | ids |
| 3 | activity: 5 (`chdr` value plus one) |
| 3 | game mode: 3 |
| 3 | engine: 0 |
| 32 | map id |
| 8 | category |
| author | created by |
| author | modified by |
| text | title, 16-bit characters, at most 128 |
| text | description, 16-bit characters, at most 128 |

An author here is: 64 bits time, 64 bits XUID, text of 8-bit characters (at
most 16), 1 bit "is online".

### 3.2 Map variant

| Bits | Field |
|---|---|
| 8 | variant version: 31 (Xbox 360 era) or 32 (MCC today) |
| 32 | unknown, 0xFFFFFFFF in every file |
| 32 | map checksum: one value per map and game build |
| 9 | number of quota rows (Forge World: 89 originally, 144 after MCC's added pieces, 145 today) |
| 32 | map id |
| 1 + 1 | two flags, both 0 in every file |
| 32 × 6 | bounds as floats: x min, x max, y min, y max, z min, z max |
| 32 | budget maximum |
| 32 | budget spent |
| … | label table (3.3) |
| 128 | **version 32 only**: unknown block, the same for every file of a map |
| … | 651 object slots (3.4) |
| 24 × rows | quota table (3.5) |

### 3.3 Label table

The Forge labels game types look for ("ctf", "slayer", "ffa_only", …).

| Bits | Field |
|---|---|
| 9 | number of labels |
| per label | 1 bit "present", then a 12-bit byte offset into the text |
| 13 | text size in bytes — only when there is at least one label |
| 1 | packed? |
| 13 | packed size — only when packed |
| bytes | the text: each name ends in a zero byte |

Packed text is a `u32` (big-endian) repeating the unpacked size, then a zlib
stream. In the files seen, text of 128 bytes or more is packed and shorter
text is not; the writer does the same.

### 3.4 Object slot

One bit: is the slot used? An unused slot is just that 0. A used one continues:

| Bits | Field |
|---|---|
| 2 | flags: 1 in every object seen |
| absent + 8 | type: the row of the quota table |
| absent + 5 | which item of that row (the pieces inside one Forge menu entry) |
| 1 | has a position: 1 in every object seen |
| x, y, z | position (section 4.1) |
| 1 | up is the world's up; if 0, 20 bits of up vector follow (4.3) |
| 14 | turn about the up vector (4.2) |
| 10 | unknown, 0 in every object seen |
| 2 | boundary shape: 0 none, 1 sphere, 2 cylinder, 3 box |
| 11 × n | boundary sizes (4.4): sphere 1, cylinder 3, box 4 |
| 8 | spawn sequence (255 = -1) |
| 8 | respawn time, seconds |
| 5 | multiplayer object kind |
| absent + 8 | label: index into the label table |
| 8 | placement flags |
| 4 | team plus one: 1-8 are the teams, 9 is neutral |
| absent + 3 | colour; absent = the team's colour |
| 8 | **kind 1 only (weapons)**: spare clips |
| 5 + 5 | **kinds 12, 13, 14 only (teleporters)**: channel, passability |
| 8 | **kind 19 only**: location name — taken from other people's notes, no sample has one |

Neither "absent" bit before the type and item was ever set, nor was the
"has a position" bit ever clear; what the game does in those cases is a guess.

The files do not name the object types. A type and item pair means "row N of
this map's Forge palette, piece M of it", and the rows changed when MCC added
pieces (89 → 144 → 145 rows on Forge World), so pairs only carry over between
variants with the same map checksum.

### 3.5 Quota table

One row per palette entry, three bytes: minimum count, maximum count, number
placed. "Placed" equals the number of objects of that type in every file.
Prices are not in the file.

## 4. Turning the numbers into world units

### 4.1 Position

Each axis gets its own number of bits, from the map's bounds:

```
steps = ceil((max - min) * 1920)        # 1920 = 120 * 16: a step no coarser than 1/1920 world unit
steps = min(steps, 0x800000)
bits  = ceil(log2(steps)), at most 26
```

Forge World (x 481, y 686, z 143 units) gives 20, 21 and 19 bits. A map whose
variant holds ±20000 bounds gives 23 bits each.

```
raw   = floor((value - min) / (max - min) * 2^bits)
value = min + (raw + 0.5) * (max - min) / 2^bits
```

The half-step in the second line is the best fit to where round coordinates
land in the sample files; the alternative reading differs by under 0.0005
world units.

### 4.2 Turn

14 bits over a full turn: `raw = floor((angle + pi) / (2 pi) * 16384)`, so 8192
is 0°, 4096 is -90°, 12288 is +90°. Which way positive turns, and what 0°
faces when the up vector is tilted, is not confirmed.

### 4.3 Up vector

20 bits: `face * 174762 + u * 417 + v`. `face` (0-5) picks a side of a cube,
`u` and `v` (0-416) a point on it, 208 being the middle. Axis-aligned up
vectors sit at the face centres. Face 2 is the world's up (objects that are
upright but not flagged as such use it); a variant with walls stood on edge
puts faces 1 and 4 on one horizontal axis and face 3 on the other, which fits
the order +X, +Y, +Z, -X, -Y, -Z. Which of u and v is which axis on each face
is not worked out.

### 4.4 Boundary sizes

11 bits over 0 to 200 world units with both ends exact:

```
raw = 0 for 0, 2047 for 200 or more, otherwise 1 + floor(value * 2046 / 200)
```

A box holds width, length, top, bottom; a cylinder radius, top, bottom; a
sphere its radius. (The order within a shape is from the Forge menu's order
and is not confirmed in game.)

## 5. The hash

Files from an Xbox 360 hold `SHA-1(key + u32 stream length + stream)` with a
fixed 34-byte key (`HASH_SALT` in the code); 25 of the 34 sample files check
out. The nine MCC-era files (saved by MCC or made with other people's tools)
hold a different 20 bytes that none of the obvious SHA-1 or MD5 inputs explain.

The writer leaves the hash alone when the stream is unchanged, and writes the
Xbox 360 hash when it changed (`--keep-hash` keeps the old bytes instead).
MCC loaded a changed MCC-saved variant carrying the Xbox 360 hash, so it
accepts that hash on a version 32 file. Whether it checks the field at all is
not known: a file with a deliberately wrong hash has not been tried.

## Still unknown

- Two kinds of change have been through the game: a new title with one
  object's height changed, and (2026-11-21, "It loaded fine") eleven objects
  added in three palette rows with the quota table recounted, the budget
  raised by a guessed amount, and turns and up vectors set. Removing objects
  and changing labels have not. What the game does with a budget figure that
  does not match its own prices is not known; it did not refuse the file.
- What MCC puts in the hash field of the files it saves, and whether it checks
  the field at all.
- The 128-bit block version 32 adds; the 32-bit field that is always
  0xFFFFFFFF; the two flags; the 10-bit field in each object; the 2-bit flags.
- The exact up-vector axes and the direction of the turn (4.2, 4.3).
- Names of the multiplayer object kinds other than weapon and teleporter, and
  the meaning of the placement flag bits.
- Which palette row and item is which Forge piece, and each piece's price
  (needed to fill in "budget spent" for a variant built from scratch).
- Header fields that only appear for other content (films, playlists,
  campaign): the reader refuses anything that is not a map variant.

## Using the tool

```
python\python.exe tools\forge_printer info  FILE --objects
python\python.exe tools\forge_printer check FOLDER_OR_FILE
python\python.exe tools\forge_printer move  FILE OUT --slot 12 --dz 6 --title "FP Move Test A"
```

`move` never changes FILE; it refuses to overwrite OUT. Variants read from the
game and anything made from them stay out of the repository
(`E:\Proving Grounds\re_tools\forge_printer`).
