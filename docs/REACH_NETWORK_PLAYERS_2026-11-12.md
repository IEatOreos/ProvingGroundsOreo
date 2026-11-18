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

## Results (2026-11-15)

- **netbots=2 with an Xbox friend** (5 Reach matches, SnypeShee on their own machine): every add was queued and none
  was refused or dropped. The friend still saw every bot skate, and his team's bots got a red reticle. That
  includes the three on the host's machine.
- **netcheck, the host alone** (`botcore_netcheck1.log`): each add came back through `FUN_1803c4004` as a type-9
  entry and decoded exactly as sent: index, identifier, machine, controller/user 1-3 or no machine, and team. Each
  was then `refused` on the host, as expected, since the slot was already the bot's. Every entry had sequence 0 and
  was applied within the same few log lines as it was queued.
- So the encoding is right and the host applies the entries. They most likely never reach the other machines: this
  queue appears to be per machine in a networked custom game. Each machine probably runs the sender
  (`FUN_1803aafa4` / `FUN_18041f510`) itself, from its own copy of the session membership. Not proven: that needs a
  PC client's log.
- Next lead: the session membership (`r13` in `FUN_18041f510`: +0x173C mask, 16 players of 0xB0 from +0x1744, each
  tied to a peer), and how it reaches the other machines (MCC's session, not the simulation queue).

## The session membership (static, 2026-11-15)

The session is `*(0x184E0E910)` + 0x18 (call it S). Its membership object is S + 0x30 (M), and code that takes M
uses offsets 0x30 lower than S.

- **It is a network message.** `membership-update` is registered at `180427E93`: body 0x2550 bytes, encoder
  `18042675C`, decoder `180427140`. The host sends the membership to the peers. Each machine then builds its game
  players from its own copy, through the diff `18041F510`, the type-9 records and `1804192C4`. That explains the
  results: our type-9 adds were local only.
- **Layout (S offsets)**:
  - +0x5C: peers mask (17). Peers are 0x158 bytes each from +0x60. In each peer, +0x170 is its player count and
    +0x174 + user*4 maps user slot 0..3 to a player index: **4 players per peer**.
  - +0x173C: players mask (16). Player entries are 0xB0 bytes from +0x1740:
    - +4: identifier
    - +0xC: peer
    - +0x10: user slot (the record's "controller")
    - +0x14: join number
    - +0x18: flag
    - +0x1C: -1 (the record's "user")
    - +0x20: the 0x80-byte configuration (team at +0x98)
  - +0x4464: this machine's peer. +0x4468: membership update number (bumped on every change).
- **Adding a player**: `18039D620(M, peer, user, &ids, ...)` takes the first free player slot. It fills the entry
  with `18039D8A8(M, index, &ids, peer, user, join number, flag)`, sets flags, and bumps M+0x2210 (join numbers) and
  the update number. Callers: session creation (`180391F0C`, the host's local users 0..3), `180395340` (a peer's
  "session add players" request) and `18039FB34`.
- **The host removes its own members that aren't real users**: `18038F49C` checks each local user slot (table
  `0x182A1E948`, 0x2F0 each: +0 signed in, +4 identifier). When this machine's peer has a player in a slot whose user
  is not signed in, or has another identifier, it calls `180394D48(S, user)` after a timeout (`0x180D1FD40`), and
  that removes the player (`18039D7F8`).

### Plan: bots as members of the host's peer (up to 3), then more peers

1. For each of the first 3 bots, after `hr_add_bot` makes it: write a member entry at **the same index** as the
   bot's game player, on this machine's peer (S+0x4464) as user slot 1..3. Use its identifier and configuration.
   Then bump the update number, as `18039D620` does. On the host, the diff's add for that slot is refused (the slot
   is already the bot's, with the same identifier), so the bot stays non-local: no split screen.
2. Hook `180394D48` so it does not remove a member whose identifier is a bot's (0xB07B07B0...).
3. The friend's machine should get the members through `membership-update` and make the players itself, on the
   host's machine with user slots 1..3. Those are the same records that decoded correctly in netcheck.
4. If that works: more bots need more peers (17 at most). Each would be a made-up peer with no connection, which
   the host and MCC may drop or reject. That is a separate investigation.

Risks: MCC watches the session (lobby counts, invites), a bad membership could disconnect the friend, and an Xbox
client may check the membership more strictly. Test with the host alone first, then with a friend.

## Why the member bots skated, and the relay (2026-11-15)

netmembers2 result: with SnypeShee (Xbox) joined, the 3 member bots were on his scoreboard on the right team, but
they still slid. The host's netwatch showed them as players of the host's machine id with machine slot (+0x1A),
controller (+0x1C) and user (+0x20) all -1, units linked.

How a joined machine gets a remote player's input (all static, haloreach.dll):

- **The simulation world** `W = *(0x184E0E908)` (botcore's `HR_SQ_QUEUE`). +0x10 state (7/8: a distributed network
  game; 3-6 synchronous). +0x80: 16 view pointers (view +4 type: 4 = a joined machine's view; view +0x24/+0x28 its
  machine id; view +0x10 -> +0x63E0 its channel).
- **Simulation players** at W+0x100 + i * 0xE0, one per player index (`FUN_1803c0ad8`): +0 index, +4 player
  handle, +8 state, +0xC identifier, +0x14 machine id (6 bytes, copied at creation), +0x20 the world, +0x30 the
  last action, +0xD8 its time. The state comes from the game kind (game globals +0x11) and whether the player's
  machine id is this machine's (`FUN_1800532d8`): 0/1 local, 3/4/5 remote. Made by `FUN_1803aa1b0` (from
  `player_new_at` and the type-9 add) and `FUN_1803c30b8` (rebuilt from the player list). Freed when a player
  leaves (`FUN_180052514`).
- **The tick** (`FUN_1800575ac`):
  1. `FUN_1803aabd0` -> `FUN_1803c034c` -> `FUN_1803bff80` builds the tick's update (+8 mask, +0x10 + i * 0xA8 the
     actions, +0xCF48/+0xCF4C the remote control records, +0xD68C/+0xD690 per-machine latency).
  2. `FUN_1803ab59c` -> `FUN_1803c0804` -> (state 7/8) `FUN_1803c16ec(W, mask, actions)` sends each player's
     action to every type-4 view except one on the player's own machine: `FUN_180419b4c` packs it (0x4C bytes),
     `FUN_1804212c0` puts it in the channel at +0x88 + i * 0x4C and sets bit i of +0x20. The channel's encoder
     (`FUN_1804215e8`) sends both masks (+0x20 actions, +0x28 0x74-byte control records at +0x548).
  3. `FUN_1803ab220` applies the update's control records.
  4. `FUN_180047050`, the players update: **botcore writes the bots' input here**, after step 2.
  5. `FUN_1803bfd8c` sends the local users' 0x74-byte control records (found by `FUN_1803c2c38`: player +0x1A this
     machine's slot and +0x1C the user 0..3).
- **On the joined machine**, `FUN_1803bff80` -> `FUN_180418a7c`: a simulation player in state 4/5 takes the action
  from the host's channel (bit i of +0x30, the 0x4C record at +0x88 + i * 0x4C) and holds it for a short time.
  That action drives the remote player's unit there, so its animation.

So the bots' actions were never sent: the host relays at step 2, and botcore writes them at step 4. The bots'
positions still reached the friend through the unit's state, hence the sliding.

**The fix** (`hr_net_relay`, netbots=3/4): at the end of botcore's step-4 hook, call `FUN_1803c16ec(W, mask,
actions + 0x10)` again with the mask of the member bots that have input this tick. Host only, state 7/8. A bot
without a simulation player gets one by `FUN_1803aa1b0(handle)`. The packing (`FUN_180419b4c` ->
`FUN_18041adb8`) only reads game state and writes the record.

Not done: the 0x74-byte control record is sent only for local users (step 5); remote people get only the action
too, so the action alone should be enough.

### More than 3 bots without made-up peers (netbots=4)

The membership message (`FUN_18042675c`) packs each member's peer in 5 bits, its user slot in 2 bits and the
record's user in 3 bits, with no per-peer player count. A joined machine fills members with `FUN_18039d8a8`, which
sets the peer's slot -> player entry and count without checking for a duplicate. So bots can share user slots 1-3
of the host's peer. On a joined machine a remote player's controller number is not used for input.

The catches, handled in `hr_mb_remove_bot` / `hr_mb_sweep`:

- The game's remove (`FUN_18039d950`) clears the slot -> player entry of the removed member's (peer, slot) even if
  another member has it. The entry is pointed back at a remaining bot.
- The game's drop after a match (`FUN_180394d48`) removes the one member in that entry. netbots=4 removes every bot
  member at that moment, so none reaches the lobby (where a host-peer member could become a split-screen user).
- Every member counts against the session's 16 players.

### Tested 2026-11-17, and why more than 3 bots needs more machines

With Sakallis joined (his launcher, bots off), netbots=3 plus the relay worked: the 3 member bots animated from their
first life, and his bot teammate showed friendly. netbots=4 did not. The type-9 player record keeps the user in 2 bits
(users 4, 5, 6 arrived as 0, 1, 2), and a machine makes a player for a member only if none of that machine's
players has its user (`FUN_18041f510`). So a machine holds 4 players: the host's person plus 3 bots.

Stand-in peers (more machines), static only:

- A machine's id is a hash of its peer entry's first 8 bytes, its network address (`FUN_1803a922c`). The same
  address means the same machine, so a stand-in needs its own address.
- Adding a peer (`FUN_18039cf80`) finds or makes an observer (a network connection) to that address
  (`FUN_1803f6fc0`, 34 slots), unless it is this machine's own address. A joined machine adds each peer of the
  membership this way (`FUN_18039e47c`). If an add fails, it stops applying and leaves the session (`FUN_1803951ac`).
- When an observer to a peer closes, `FUN_18042b164` -> `FUN_1803958cc` removes that peer (and on a joined machine
  sends a message about it).
- So every joined machine would try to connect to each stand-in address. If that fails, the likely results are that
  machine dropping the stand-in and its bots after the connection times out, possibly back and forth as the host
  keeps listing it, or its copy of the membership diverging from the host's. A diverged copy may make it leave the
  session. Not built.

## Next experiment (needs both PCs)

Built as `botcore.ini` `netbots=` (`native/reach.cpp` `hr_net_add` / `hr_net_pump`; CUSTOM_CHANGELOG.md, 2026-11-12).
`netbots=2` covers both cases in one match: bot slots 0-2 on the host's machine, the rest with no machine.

A host-only, opt-in build: after each bot's `player_new_at`, also queue a type-9 add for it (no machine), and log
the queue result. Then check in the friend's netwatch log: do players 2..7 appear, does unit +0x1CC point at them,
and do the bots animate with the right teams on his screen? If the friend's game refuses it or drops it, try the
host's machine with controller/user 1..3 for up to 3 bots.
