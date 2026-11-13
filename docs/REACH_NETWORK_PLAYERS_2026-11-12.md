# Reach: how a joined machine learns its players (bots in a friend's custom game)

Static reading of `haloreach.dll` (MCC build in use on 2026-11-12, image base 0x180000000; addresses below are
absolute, RVA = address - 0x180000000). Disassembled with Visual Studio's `dumpbin /disasm`; nothing here was run
in game yet. Same build as `native/reach.cpp` (`HR_PLAYER_NEW_AT` 0x43DC8, `HR_PLAYERS_UPDATE` 0x47050).

## The problem, measured

The owner hosted a 4v4 with 6 bots and a friend joined (anti-cheat off custom game). `hr_net_watch` in both logs:

| | host | friend |
|---|---|---|
| live players | `00ff`: 2 people and 6 bots | `0003`: the 2 people only |
| bot bodies | each unit's +0x1CC holds its bot's player handle | there (objects replicate), +0x1CC empty: no player |

So the friend saw bodies with no player: no team (all shown as enemies), and no animation.
The unit's player link is unit **+0x1CC**. A dead body keeps the last one at +0x1D0. Player +0xAC reads -1 for
everyone in multiplayer, so it is not the team there.

## Where players come from

- **Match start** `1800A411C`: sets the machine table from game globals +0x264 (mask) / +0x268 (17 x 6-byte
  machine ids) through `1800453A8`. Then, for each of the 16 configurations at game globals +0x2D8 (0xA0 each)
  whose first byte is set, it calls `player_new_at(i, cfg, 0)`. This runs on every machine.
- **During the match**: the simulation queue. Entry type **9** is "player update". Every machine (the host too)
  decodes and applies queue entries: `1803C4004` switches on the entry type and sends type 9 to `1803A4648`.
  - `1803A4648` decodes the bitstream into a 0xB8-byte record.
  - `180418FF8` applies it by the record's +0xC type: 0 remove (`180052514`), 1 move (`1804191E4`),
    2 (`1800451EC`), **3 add** (`1804192C4`), 4 configuration change (`1800440A4`).
- **The host's sender** `1803AAFA4` (from `1803C034C`), each update:
  1. `18041F510` diffs the session membership against what was last sent and fills up to 64 records.
  2. Each record is encoded by `1803C7CE0`.
  3. A type-9 element is allocated with `1803C414C(queue, 9, bytes, &elem)`, the bytes are copied into
     `elem+0x10`, and it is queued with `1803C4290(queue, elem)`.

  The queue is `*(0x184E0E908)`. It only sends when the session object `*(0x184E0E910)` is in states 4..9 and the
  membership update number changed.

### The player update record (0xB8 bytes), as encoded

| offset | bits | meaning |
|---|---|---|
| +0x00 | 4 | player index (0..15) |
| +0x04 | 64 | player identifier |
| +0x0C | 3 | type: 0 remove, 1 move, 2 ?, 3 add, 4 configuration |
| +0x10 | 48 | machine id (add, when +0x20 is 0) |
| +0x18 | 2 | controller (add) |
| +0x1C | 2 | user index (add) |
| +0x20 | 1 | no machine (add) |
| +0x21 | 1 | add flag, passed to player_new_at's third argument |
| +0x28 | | client configuration, 0x58 bytes (encoder `1803A1BA8`, decoder `1803A1EB8`) |
| +0x80 | | server configuration, 0x28 bytes (encoder `1803A21B4`, decoder `1803A2338`) |
| +0xA8 / +0xAC | 4 / 64 | type 1 only: the other index and its identifier |

+0x28..+0xA7 is the same 0x80 bytes as the player configuration (game globals +0x2D8 + 0x20).

### What an add must pass (`1804192C4`)

- The player identifier must not already be in use.
- With a machine (+0x20 = 0): the machine id must be in the machine table (TLS +0x118: +4 mask of 17, +8 ids of 6
  bytes), and controller and user must be 0..3 and not taken by another player of that machine. So **at most 4
  players per machine**: the host's machine can carry 3 bots besides the host.
- With no machine (+0x20 = 1): those checks are skipped. The player is made machine-less. In our tests that
  showed as "gone": the team lost, and its "present" bit (player +4 bit 0) is cleared. The mod already re-sets it
  every tick on the host.

The session's diff always sends adds with a real machine (+0x20 = 0) and that machine's controller/user. The
"present" bit is also sent, as type 8 (`1803A44F0`). The machine table is part of the per-tick update (update
+0xCED8 flag, +0xCEDC mask, +0xCEE0 ids, applied by `1803AB220`). The same function applies the per-unit
controls (update +0xAAD0 mask of 64, 0x90 bytes each, `180483468`): the likely source of a remote unit's
animation state on a client.

## Why our bots never reach the friend

`hr_add_bot` calls `player_new_at` directly on the host. It never puts a type-9 add into the queue, and the bot
is not in the session membership, so the host's own diff never sends one either. The friend's game gets the bodies
(objects replicate on their own) but never the players.

## Fix options, simplest first

1. **The host queues a type-9 add for each bot** in place of (or right after) its own `player_new_at`. Same index,
   identifier and configuration, and `+0x21` as the session sends it. Every machine then makes the same player.
   - Machine: no machine (+0x20 = 1) avoids the 4-per-machine limit, but needs the "present" bit kept on
     everywhere (does a client need it?). The host's machine allows 3 bots. Fake machines would also need entries
     in the replicated machine table (the per-tick update's +0xCED8).
   - The host applies its own queue too. So either let the queue make the bot on the host (and drop the direct
     call), or skip the add on the host when the slot is already filled (`1804192C4` refuses a used identifier).
   - Must be sent while the session is in a state the sender accepts, and only by the host.
2. **Add the bots to the session membership** (`r13` in `18041F510`: +0x173C mask, 16 players of 0xB0 from
   +0x1744, each tied to a peer). The game then sends everything itself, but the membership also drives MCC's
   lobby, scoreboard and peers. That is riskier.
3. **A client-side mod** that makes the players from a list the host sends. It needs the mod on every machine and a
   channel between them, so it is the last resort.

## Next experiment (needs both PCs)

Built as `botcore.ini` `netbots=` (`native/reach.cpp` `hr_net_add` / `hr_net_pump`; CUSTOM_CHANGELOG.md, 2026-11-12).
`netbots=2` covers both cases in one match: bot slots 0-2 on the host's machine, the rest with no machine.

A host-only, opt-in build: after each bot's `player_new_at`, also queue a type-9 add for it (no machine), and log
the queue result. Then check in the friend's netwatch log: do players 2..7 appear, does unit +0x1CC point at them,
and do the bots animate with the right teams on his screen? If the friend's game refuses it or drops it, try the
host's machine with controller/user 1..3 for up to 3 bots.
