// h3.cpp: Halo 3 (halo3.dll, MCC 1.3528) player bots, the Halo 2 plan on Halo 3 (docs/H3-01).
// - Engine globals live in thread-local storage: game thread's TLS block for halo3.dll
//   (ThreadLocalStoragePointer[_tls_index]) +0x10 players array header, +0x38 object header
//   array, +0x48 game globals (+0x200: 16 player configurations of 0xB8 bytes, the match's
//   players). Array header: +0x20 max, +0x24 element size, +0x48 data pointer.
// - players update FUN_1800e444c(actions): actions +8 = bitmask of players with an action,
//   +0x10 + index * 0x88 = each player's action (FUN_1800e8dd8 turns it into unit control).
//   We hook it (game thread, every tick): run the brain's commands, copy player 0's action for
//   the debug view, write each driven bot's action, call the original.
// - player_new_at_index FUN_1800e20dc(index, config, 0): config +0 valid, +1 no machine, +2
//   controller, +4 user, +8 machine (6 bytes), +0x10 player identifier, +0x18 configuration
//   (0xA0 bytes, copied to player +0x58 and +0xF8: name at +0x18 and +0x90, team int at +0xB0).
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include <intrin.h>
#include "shared.h"
#include "third_party/minhook/include/MinHook.h"

extern hb_shared* g_shm;
void logf(const char* fmt, ...);
void report_note_bot(int index, const wchar_t* name, const wchar_t* tag, int team, const wchar_t* clan,
                     const uint16_t* emblem);   // report.cpp
void bot_service_tag(const wchar_t* name, wchar_t tag[4]);                                                // report.cpp

static uint8_t* g_h3;
static uint8_t g_h3_patch[5];
static DWORD g_h3_tls_index;
static const uintptr_t H3_PLAYERS_UPDATE = 0xE444C, H3_PLAYER_NEW_AT = 0xE20DC;
static const size_t H3_PLAYER_SIZE = 0x2F8, H3_ACTION = 0x88, H3_CONFIG = 0xB8;
typedef void(__fastcall* h3_update_fn)(uint8_t* actions);
typedef int(__fastcall* h3_new_at_fn)(int index, uint8_t* config, char flag);
static h3_update_fn o_h3_update;

static uint8_t* h3_tls() {                    // game thread only
    void** arr = (void**)__readgsqword(0x58);
    return arr ? (uint8_t*)arr[g_h3_tls_index] : nullptr;
}

static uint8_t* h3_player(uint8_t* tls, int index) {
    uint8_t* hdr = *(uint8_t**)(tls + 0x10);
    if (!hdr || index < 0 || index >= *(int32_t*)(hdr + 0x20)) return nullptr;
    uint8_t* data = *(uint8_t**)(hdr + 0x48);
    return data ? data + (size_t)index * H3_PLAYER_SIZE : nullptr;
}
static bool h3_live(uint8_t* tls, int index) { uint8_t* p = h3_player(tls, index); return p && *(uint16_t*)p != 0; }

// objects: [tls+0x38] header, data +0x48: 0x18-byte entries (+0 salt, +3 type, +0x10 object
// address). Object +0x10 parent, +0x50 position; unit +0x260 weapon set / primary / secondary
// index (the action's +0x44..+0x47), +0x268 4 weapon handles.
static uint8_t* h3_object(uint8_t* tls, uint32_t handle) {
    uint8_t* hdr = *(uint8_t**)(tls + 0x38);
    if (!hdr || handle == 0xFFFFFFFFu || (int)(handle & 0xFFFF) >= *(int32_t*)(hdr + 0x20)) return nullptr;
    uint8_t* e = *(uint8_t**)(hdr + 0x48) + (size_t)(handle & 0xFFFF) * 0x18;
    return *(uint16_t*)e == handle >> 16 ? *(uint8_t**)(e + 0x10) : nullptr;
}

// the loose weapon nearest the unit within 1.5 units (what "hold E to pick up" offers).
// ponytail: linear scan of the object table, only while E is held
static uint32_t h3_pickup_target(uint8_t* tls, uint8_t* unit) {
    uint8_t* hdr = *(uint8_t**)(tls + 0x38);
    int n = *(int32_t*)(hdr + 0x20);
    uint8_t* ents = *(uint8_t**)(hdr + 0x48);
    const float* p = (const float*)(unit + 0x50);
    uint32_t best = 0xFFFFFFFFu;
    float bd = 1.5f * 1.5f;
    for (int i = 0; i < n; i++) {
        uint8_t* e = ents + (size_t)i * 0x18;
        if (!*(uint16_t*)e || e[3] != 2) continue;
        uint8_t* o = *(uint8_t**)(e + 0x10);
        if (!o) continue;
        float q[3] = { ((const float*)(o + 0x50))[0], ((const float*)(o + 0x50))[1], ((const float*)(o + 0x50))[2] };
        uint32_t parent = *(uint32_t*)(o + 0x10);
        if (parent != 0xFFFFFFFFu) {
            // a weapon on something: Halo 3's CTF flag hangs on its stand (a type 10 object, 0.31 above it; live: every
            // bot's press at the flag found no target, the flag never moved). Its place is the stand's plus the offset;
            // never a gun in someone's hands or seat (biped 0, vehicle 1). Sandtrap's stands ride on the Elephants
            // (live: two bots 0.48 u from a flag for minutes, pressing, no target, no pull in 24 min): a stand on a
            // vehicle puts both offsets along the vehicle's axes, as brain/live.py reads the flag
            int pi = (int)(parent & 0xFFFF);
            if (pi >= n) continue;
            uint8_t* pe = ents + (size_t)pi * 0x18;
            uint8_t* po = *(uint8_t**)(pe + 0x10);
            if (pe[3] == 0 || pe[3] == 1 || !po) continue;
            const float* s = (const float*)(po + 0x50);
            uint32_t gp = *(uint32_t*)(po + 0x10);
            if (gp == 0xFFFFFFFFu) {
                for (int k = 0; k < 3; k++) q[k] += s[k];
            } else {
                uint8_t* top = h3_object(tls, gp);
                if (!top || pe[3] != 10 || ents[(size_t)(gp & 0xFFFF) * 0x18 + 3] != 1 || *(uint32_t*)(top + 0x10) != 0xFFFFFFFFu)
                    continue;
                const float* b = (const float*)(top + 0x50), * f = (const float*)(top + 0x5C), * u = (const float*)(top + 0x68);
                float l[3] = { u[1] * f[2] - u[2] * f[1], u[2] * f[0] - u[0] * f[2], u[0] * f[1] - u[1] * f[0] };
                float r[3] = { s[0] + q[0], s[1] + q[1], s[2] + q[2] };
                for (int k = 0; k < 3; k++) q[k] = b[k] + r[0] * f[k] + r[1] * l[k] + r[2] * u[k];
            }
        }
        float d = (q[0] - p[0]) * (q[0] - p[0]) + (q[1] - p[1]) * (q[1] - p[1]) + (q[2] - p[2]) * (q[2] - p[2]);
        if (d < bd) { bd = d; best = (uint32_t)*(uint16_t*)e << 16 | (uint32_t)i; }
    }
    return best;
}

// boarding (Sandtrap Multi Flag, all 15 bots stood by vehicles pressing Use with a seat asked for, about 12,000
// presses, none got in: a bot's interaction was empty). Halo 3's Use handler (FUN_1800eaf24, ghidra/h3_interact.c)
// takes interaction types 4, 5 and 8 as a seat: the vehicle at +0x50, the seat at +0x4E, checked against the vehicle
// tag's seats and the unit's own test (FUN_180353774), then unit action 0x11 into it. Seats as the brain asks
// (vehicles.reach_seat; live, Sandtrap): the driver's is seat 0 of every vehicle, a Warthog's or Mongoose's passenger
// seat 1, a gunner's seat 0 of the gun riding on the vehicle (an object of its own, placed relative to it). The nearest
// within 3 u standing up (object +0x68 the up vector, +0x5C forward: live)
static uint32_t h3_near_vehicle(uint8_t* tls, uint8_t* unit, bool turret) {
    uint8_t* hdr = *(uint8_t**)(tls + 0x38);
    int n = *(int32_t*)(hdr + 0x20);
    uint8_t* ents = *(uint8_t**)(hdr + 0x48);
    const float* me = (const float*)(unit + 0x50);
    uint32_t best = 0xFFFFFFFFu;
    float bd = 3.0f * 3.0f;
    for (int i = 0; i < n; i++) {
        uint8_t* e = ents + (size_t)i * 0x18;
        uint8_t* o = *(uint8_t**)(e + 0x10);
        if (!*(uint16_t*)e || e[3] != 1 || !o) continue;
        uint32_t parent = *(uint32_t*)(o + 0x10);
        if ((parent != 0xFFFFFFFFu) != turret) continue;
        const float* r = (const float*)(o + 0x50);
        float q[3] = { r[0], r[1], r[2] };
        uint8_t* top = turret ? h3_object(tls, parent) : o;
        if (!top || ((const float*)(top + 0x68))[2] < 0.5f) continue;   // on its side or roof: no ride
        if ((o[0x110] & 4) || (top[0x110] & 4)) continue;   // destroyed (damage flags bit 2, ghidra/h3_object_get_health.c)
        if (turret) {
            // a gun's place is the vehicle's plus its offset along the vehicle's axes (left = up x forward)
            const float* b = (const float*)(top + 0x50), * f = (const float*)(top + 0x5C), * u = (const float*)(top + 0x68);
            float l[3] = { u[1] * f[2] - u[2] * f[1], u[2] * f[0] - u[0] * f[2], u[0] * f[1] - u[1] * f[0] };
            for (int k = 0; k < 3; k++) q[k] = b[k] + r[0] * f[k] + r[1] * l[k] + r[2] * u[k];
        }
        float dx = q[0] - me[0], dy = q[1] - me[1], dz = q[2] - me[2], d2 = dx * dx + dy * dy;
        if (d2 < bd && dz > -2.0f && dz < 2.5f) { bd = d2; best = (uint32_t)*(uint16_t*)e << 16 | (uint32_t)i; }
    }
    return best;
}

// a bot on foot holding Use with a seat asked for (shared.h HB_SEAT_SHIFT): that seat of the nearest vehicle as its
// interaction (types 4, 5, 8 in FUN_1800eaf24; the action's Use bit 2 hands it over)
static void h3_board(uint8_t* tls, uint8_t* act, uint8_t* unit, uint32_t b) {
    int seat = (int)((b >> HB_SEAT_SHIFT) & 15) - 1;
    if (!(b & HB_BTN_ACTION) || seat < 0 || *(uint32_t*)(unit + 0x10) != 0xFFFFFFFFu) return;
    uint32_t veh = h3_near_vehicle(tls, unit, (b & HB_BTN_TURRET) != 0);
    if (veh == 0xFFFFFFFFu) return;
    *(int16_t*)(act + 0x4C) = 4;
    *(int16_t*)(act + 0x4E) = (int16_t)seat;
    *(uint32_t*)(act + 0x50) = veh;
}

static int h3_free_slot() {
    for (int i = 0; i < HB_MAX_PLAYERS; i++) if (g_shm->bot_player_index[i] < 0) return i;
    return -1;
}

static int64_t h3_add_bot(uint8_t* tls, int arg) {
    uint8_t* globals = *(uint8_t**)(tls + 0x48);
    uint8_t* me = h3_player(tls, 0);
    int slot = h3_free_slot();
    if (!globals || !me || slot < 0) return -2;
    int index = -1;
    for (int i = 1; i < HB_MAX_PLAYERS; i++) if (h3_player(tls, i) && !h3_live(tls, i)) { index = i; break; }
    if (index < 0) return -3;
    uint8_t cfg[H3_CONFIG];
    memcpy(cfg, globals + 0x200, H3_CONFIG);         // player 0's configuration as it joined
    cfg[0] = 1;
    // the machine: a player on the host's machine (arg bit 17) becomes a local user and H3
    // splits the screen for it; a machine-less one (bit 16) shows as gone and its team loses
    // (both verified). Default: an unknown machine identifier, so the machine index is -1 and
    // FUN_1800e2928 maps no local user, but the player is not flagged machine-less.
    cfg[1] = (arg & (1 << 16)) ? 1 : 0;
    if (!(arg & ((1 << 16) | (1 << 17)))) {
        *(uint32_t*)(cfg + 8) = 0xB07B0000u | (uint32_t)index;
        *(uint16_t*)(cfg + 0xC) = 0xB07B;
    }
    *(uint16_t*)(cfg + 2) = 0xFFFF;                   // no controller
    *(int32_t*)(cfg + 4) = -1;                        // no user
    // a player identifier, in every place the player's was: the configuration holds a second copy at +0x78, the
    // one MCC's post-game report names the player by (before: every bot carried the host's name)
    uint64_t owner_id = *(uint64_t*)(cfg + 0x10), bot_id = 0xB07B07B000000000ull | (uint64_t)index;
    hb_replace_id(cfg, sizeof cfg, owner_id, bot_id);
    *(uint64_t*)(cfg + 0x10) = bot_id;
    int team = (arg >> 8) & 0xFF;                     // 0xFF = keep player 0's
    // team: int at configuration +0x98 (config +0xB0, player +0xF0; FUN_1800e2370). Player 0's
    // team on a bot leaves one team in free for all and the match ends at once (as in H2)
    if (team != 0xFF) *(int32_t*)(cfg + 0xB0) = team;
    wchar_t name[16] = {};
    if (g_shm->cmd_name[0]) { wcsncpy_s(name, 16, g_shm->cmd_name, 15); g_shm->cmd_name[0] = 0; }
    else swprintf_s(name, 16, L"Bot %d", slot + 1);
    memcpy(cfg + 0x18, name, 32);
    memcpy(cfg + 0x90, name, 32);
    wchar_t tag[4];                                   // its service tag (+0x56, 4 characters; the host's before)
    bot_service_tag(name, tag);
    memcpy(cfg + 0x56, tag, 8);
    hb_apply_look(g_shm, 3, cfg, sizeof cfg);   // its own armor and colours (brain/looks.py)
    // what MCC shows for it (name, tags, emblem: report.cpp), before MCC first looks the new player up
    report_note_bot(index, name, tag, team != 0xFF ? team : -1, g_shm->cmd_clan, g_shm->cmd_emblem);
    int h = ((h3_new_at_fn)(g_h3 + H3_PLAYER_NEW_AT))(index, cfg, 0);
    if (h != -1) {
        // flags bit 0: what the session sets for a joined player (H2's "present" bit); a player of
        // an unknown machine never gets it and never spawns. Set, the engine spawns the bot and
        // clears the bits (verified on Construct)
        *(uint32_t*)(h3_player(tls, index) + 4) |= 1;
        // the host's machine identifier (player +0x14, 6 bytes), set after creation (at creation
        // it maps a local user and splits the screen): the server applies damage of a player's
        // shots only when his own machine is this one, else it waits for that machine's hit
        // report, which a bot never sends (verified live: hit rate 13% -> 53%, as on Reach)
        memcpy(h3_player(tls, index) + 0x14, h3_player(tls, 0) + 0x14, 6);
        g_shm->actions[slot].seq = 0;
        g_shm->bot_player_index[slot] = index;
    }
    logf("h3 add_bot index %d team %d -> %08x", index, team, h);
    return (int64_t)h;
}

static void h3_run_command(uint8_t* tls) {
    // only commands marked for Halo 3 (cmd_arg bit 25), like H2's bit 24
    if (g_shm->cmd_seq == g_shm->cmd_done_seq || !(g_shm->cmd_arg & (1 << 25))) return;
    g_shm->cmd_fault = 0;
    __try {
        if (g_shm->cmd == HB_CMD_ADD_BOT) g_shm->cmd_result = h3_add_bot(tls, g_shm->cmd_arg);
        else g_shm->cmd_result = -1;
    } __except (EXCEPTION_EXECUTE_HANDLER) { g_shm->cmd_fault = 1; g_shm->cmd_result = -1; }
    g_shm->cmd_done_seq = g_shm->cmd_seq;
}

static void __fastcall h_h3_update(uint8_t* actions) {
    if (g_shm) {
        g_shm->game_tick++;
        g_shm->game = 3;
        __try {
            uint8_t* tls = h3_tls();
            if (tls) {
                h3_run_command(tls);
                if (*(uint32_t*)(actions + 8) & 1) {        // player 0's action, for decoding
                    memcpy(g_shm->dbg_action, actions + 0x10, H3_ACTION);
                    g_shm->dbg_seq++;
                }
                for (int i = 0; i < HB_MAX_PLAYERS; i++) {
                    int index = g_shm->bot_player_index[i];
                    // flags bit 0 every tick: the players update spawns (and respawns) a player
                    // without a unit only while it is set (FUN_1800e444c's spawn loop), and the
                    // session clears it for a player of no known machine between ticks
                    if (index >= 0 && h3_live(tls, index)) *(uint32_t*)(h3_player(tls, index) + 4) |= 1;
                    const hb_action& a = g_shm->actions[i];
                    if (index < 0 || !a.seq || !h3_live(tls, index)) continue;
                    uint8_t* act = actions + 0x10 + (size_t)index * H3_ACTION;
                    // no action for a bot waiting to respawn (no unit): while one was dead, every other bot's
                    // view stopped turning and they replayed their last move until it respawned, then all
                    // snapped at once
                    if (!h3_object(tls, *(uint32_t*)(h3_player(tls, index) + 0x28))) continue;
                    *(uint32_t*)(actions + 8) |= 1u << index;
                    if (g_shm->h2_raw_valid == 2) { memcpy(act, g_shm->h2_raw_action, H3_ACTION); continue; }   // decoding
                    if (*(uint32_t*)(actions + 8) & 1) memcpy(act, actions + 0x10, H3_ACTION);
                    // decoded live (tools/h2_action_record.py, docs/H3-01): +0x08 control flags
                    // (jump 0x2, fire 0x00080040), +0x10 yaw, +0x14 pitch, +0x18 throttle forward,
                    // +0x1C throttle left, +0x30 trigger, +0x38 jump (1.0), +0x40 action flags
                    // (E: 1 held, 3 held long), +0x44 weapon set / +0x46 primary / +0x47 secondary
                    // index, +0x4A zoom, +0x4C interaction type, +0x50 interaction object, +0x54..
                    // targets (player 0's must not leak in), +0x80 input history (template)
                    uint8_t* unit = h3_object(tls, *(uint32_t*)(h3_player(tls, index) + 0x28));
                    memset(act + 0x4C, 0, 4);
                    memset(act + 0x50, 0xFF, 0x14);
                    // and player 0's aim assist (+0x64 / +0x68 weights, +0x78 flags): with them set and the target
                    // (+0x5C) cleared above, the action check FUN_1800e4254 drops the action and the game replays the
                    // bot's last one. Every time the player fired on someone all bots froze, view and walk, 0.5-4.7 s
                    memset(act + 0x64, 0, 0x1C);
                    // the red reticle's target (shared.h hb_target), as the player's own action carries it: his sword
                    // red on a man (live, Rat's Nest, logs/tmp/host_hunt.py) read +0x5C = that man's unit, +0x60 1,
                    // +0x64 weight 1.0, +0x68 0, +0x78 flags 4, and through the lunge +0x54 = the man too; he lunged
                    // 1.4 u in 0.15 s and killed. Cleared (as before), no bot press ever lunged (issue #3)
                    int tgt = hb_target(a.buttons);
                    if (tgt >= 0 && tgt < HB_MAX_PLAYERS && h3_live(tls, tgt)) {
                        uint32_t th = *(uint32_t*)(h3_player(tls, tgt) + 0x28);
                        if (th != 0xFFFFFFFFu && h3_object(tls, th)) {
                            *(uint32_t*)(act + 0x54) = th;          // (the melee request's target, FUN_1800e7efc)
                            *(uint32_t*)(act + 0x5C) = th;
                            *(uint32_t*)(act + 0x60) = 1;
                            *(float*)(act + 0x64) = 1.0f;
                            act[0x78] = 4;
                        }
                    }
                    hb_set_zoom(3, act, H3_ACTION, a.buttons);      // the scope level it wants (-1 none)
                    // the weapon set the unit checks: unit_control (FUN_180350ed4, ghidra/h3_unit_control.c) takes the
                    // action's +0x44..+0x47 only when its set (u16) equals the unit's +0x264; +0x260 (s94 and before)
                    // rarely did: 557 AR -> BR switch requests in the player's Construct match, 11 switches (as
                    // Reach's +0x348 / +0x34C)
                    if (unit) memcpy(act + 0x44, unit + 0x264, 4);
                    // the players update applies an action only when +0 is 1 and +1 equals the
                    // unit's life counter (unit +0x20C; FUN_1800e444c): player 0's template carries
                    // his, so a bot that respawned (new counter) ignored every action
                    act[0] = 1;
                    if (unit) act[1] = unit[0x20C];
                    int want = (int)((a.buttons >> HB_WEAPON_SHIFT) & 7) - 1;
                    if (want >= 0) act[0x46] = (uint8_t)want;
                    uint32_t b = a.buttons;
                    uint64_t flags = 0;
                    if (b & HB_BTN_JUMP) flags |= 0x2;
                    if (b & HB_BTN_FIRE) flags |= 0x00080040;
                    *(uint64_t*)(act + 0x08) = flags;
                    *(float*)(act + 0x10) = a.yaw;
                    *(float*)(act + 0x14) = a.pitch;
                    *(float*)(act + 0x18) = a.forward;
                    *(float*)(act + 0x1C) = a.strafe;
                    *(float*)(act + 0x30) = (b & HB_BTN_FIRE) ? 1.0f : 0.0f;
                    *(float*)(act + 0x34) = 0.0f;
                    *(float*)(act + 0x38) = (b & HB_BTN_JUMP) ? 1.0f : 0.0f;
                    *(uint32_t*)(act + 0x40) = 0;
                    if (b & HB_BTN_ACTION) {
                        *(uint32_t*)(act + 0x40) = 3;               // held long: "hold E to pick up"
                        uint32_t target = unit && hb_use_picks_up(b) && *(uint32_t*)(unit + 0x10) == 0xFFFFFFFFu
                                          ? h3_pickup_target(tls, unit) : 0xFFFFFFFFu;   // on foot, no seat asked
                        if (target != 0xFFFFFFFFu) {
                            *(int16_t*)(act + 0x4C) = 1;            // weapon pickup (as in H2)
                            *(uint32_t*)(act + 0x50) = target;
                        }
                        if (unit) h3_board(tls, act, unit, b);
                    }
                    static uint32_t map_prev[HB_MAX_PLAYERS];  // v8 decoded buttons (shared.h)
                    hb_apply_buttons(g_shm, 3, act, H3_ACTION, b, map_prev[i]);
                    map_prev[i] = b;
                }
            }
        } __except (EXCEPTION_EXECUTE_HANDLER) { g_shm->cmd_fault = 2; }
    }
    o_h3_update(actions);
}

static DWORD tls_index_of(uint8_t* mod) {
    IMAGE_NT_HEADERS64* nt = (IMAGE_NT_HEADERS64*)(mod + ((IMAGE_DOS_HEADER*)mod)->e_lfanew);
    DWORD rva = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_TLS].VirtualAddress;
    if (!rva) return 0;
    IMAGE_TLS_DIRECTORY64* t = (IMAGE_TLS_DIRECTORY64*)(mod + rva);
    return *(DWORD*)t->AddressOfIndex;
}

// called from botcore's main loop: hook halo3.dll when it is loaded (again)
void h3_watch() {
    uint8_t* h3 = (uint8_t*)GetModuleHandleW(L"halo3.dll");
    if (!h3) return;
    bool hooked = false;
    __try { hooked = h3 == g_h3 && !memcmp(h3 + H3_PLAYERS_UPDATE, g_h3_patch, 5); }
    __except (EXCEPTION_EXECUTE_HANDLER) { hooked = false; }
    if (hooked) return;
    Sleep(500);
    if ((uint8_t*)GetModuleHandleW(L"halo3.dll") != h3) return;
    if (g_h3) MH_RemoveHook(g_h3 + H3_PLAYERS_UPDATE);
    g_h3 = h3;
    g_h3_tls_index = tls_index_of(h3);
    for (int i = 0; i < HB_MAX_PLAYERS; i++) g_shm->bot_player_index[i] = -1;
    if (MH_CreateHook(h3 + H3_PLAYERS_UPDATE, (void*)&h_h3_update, (void**)&o_h3_update) != MH_OK ||
        MH_EnableHook(h3 + H3_PLAYERS_UPDATE) != MH_OK) {
        logf("h3 hook failed at %p", h3);
        return;
    }
    memcpy(g_h3_patch, h3 + H3_PLAYERS_UPDATE, 5);
    logf("h3 hooks on at halo3 %p: players update +0x%llx, tls index %lu", h3,
         (unsigned long long)H3_PLAYERS_UPDATE, g_h3_tls_index);
}
