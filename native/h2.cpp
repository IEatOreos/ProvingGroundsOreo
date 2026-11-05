// h2.cpp: Halo 2 Classic (halo2.dll, MCC 1.3528) player bots, the CE plan on H2 (docs/H2-01).
// - players update FUN_1806a3910(actions): actions +8 = bitmask of players with an action this
//   tick, +0x100 + index * 0x60 = each player's 0x60-byte action; validated, then applied with
//   unit_control FUN_1808f5800. We hook it (game thread, every tick): run the brain's commands,
//   copy player 0's action for the debug view, write each driven bot's action, call the original.
// - player creation: FUN_18069d2c0(index, config) = player_new_at_index; config +0 valid, +1 "no
//   machine", +2 controller (0xFFFF), +4 (-1), +8 machine id, +0x10 player id, +0x18 the 0x84-byte
//   player configuration (name first), cloned from player 0 (player +0xC0).
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include "shared.h"
#include "third_party/minhook/include/MinHook.h"

extern hb_shared* g_shm;
void logf(const char* fmt, ...);
void report_note_bot(int index, const wchar_t* name, const wchar_t* tag, int team, const wchar_t* clan,
                     const uint16_t* emblem);   // report.cpp
void bot_service_tag(const wchar_t* name, wchar_t tag[4]);                                                // report.cpp

static uint8_t* g_h2;
static uint8_t g_h2_patch[5];
static const uintptr_t H2_PLAYERS_UPDATE = 0x6A3910, H2_PLAYER_NEW_AT = 0x69D2C0, H2_PLAYERS_PTR = 0xE80A28;
static const size_t H2_PLAYER_SIZE = 0x224, H2_ACTION = 0x60;
typedef void(__fastcall* players_update_fn)(uint8_t* actions);
typedef uint32_t(__fastcall* player_new_at_fn)(int index, uint8_t* config);
static players_update_fn o_update;

static uint8_t* h2_player(int index) {
    uint8_t* hdr = *(uint8_t**)(g_h2 + H2_PLAYERS_PTR);
    if (!hdr || index < 0 || index >= *(int32_t*)(hdr + 0x20)) return nullptr;
    int64_t rel = *(int64_t*)(hdr + 0x48);
    return rel ? hdr + rel + (size_t)index * H2_PLAYER_SIZE : nullptr;
}
static bool h2_live(int index) { uint8_t* p = h2_player(index); return p && *(uint16_t*)p != 0; }

// objects: headers [halo2+0x18B7398] (12 bytes: +0 salt, +3 type, +8 offset), pool at
// ([halo2+0x18B7360] + 0x57) & ~0xF. Object +0x14 parent, +0x64 position; unit +0x224 weapon set
// identifier, +0x226 primary / +0x227 secondary weapon index (the action's +0x24..+0x27 layout).
static const uintptr_t H2_OBJ_HEADERS = 0x18B7398, H2_OBJ_POOL = 0x18B7360;
static uint8_t* h2_object(uint32_t handle) {
    uint8_t* hdr = *(uint8_t**)(g_h2 + H2_OBJ_HEADERS);
    if (!hdr || handle == 0xFFFFFFFFu || (int)(handle & 0xFFFF) >= *(int32_t*)(hdr + 0x20)) return nullptr;
    uint8_t* e = hdr + *(int64_t*)(hdr + 0x48) + (size_t)(handle & 0xFFFF) * 12;
    if (*(uint16_t*)e != handle >> 16) return nullptr;
    return (uint8_t*)((*(uintptr_t*)(g_h2 + H2_OBJ_POOL) + 0x57) & ~(uintptr_t)0xF) + *(int32_t*)(e + 8);
}

// the loose weapon (type 2, no parent) nearest the unit within 1.5 units: what a human gets the
// "hold E to pick up" prompt for. ponytail: linear scan of the object table, only while E is held
static uint32_t h2_pickup_target(uint8_t* unit) {
    uint8_t* hdr = *(uint8_t**)(g_h2 + H2_OBJ_HEADERS);
    if (!hdr) return 0xFFFFFFFFu;
    int n = *(int32_t*)(hdr + 0x20);
    uint8_t* ents = hdr + *(int64_t*)(hdr + 0x48);
    const float* p = (const float*)(unit + 0x64);
    uint32_t best = 0xFFFFFFFFu;
    float bd = 1.5f * 1.5f;
    for (int i = 0; i < n; i++) {
        uint8_t* e = ents + (size_t)i * 12;
        if (!*(uint16_t*)e || e[3] != 2) continue;
        uint32_t h = (uint32_t)*(uint16_t*)e << 16 | (uint32_t)i;
        uint8_t* o = h2_object(h);
        if (!o || *(uint32_t*)(o + 0x14) != 0xFFFFFFFFu) continue;
        const float* q = (const float*)(o + 0x64);
        float d = (q[0] - p[0]) * (q[0] - p[0]) + (q[1] - p[1]) * (q[1] - p[1]) + (q[2] - p[2]) * (q[2] - p[2]);
        if (d < bd) { bd = d; best = h; }
    }
    return best;
}

static int h2_free_slot() {
    for (int i = 0; i < HB_MAX_PLAYERS; i++) if (g_shm->bot_player_index[i] < 0) return i;
    return -1;
}

static int64_t h2_add_bot(int arg) {
    uint8_t* me = h2_player(0);
    int slot = h2_free_slot();
    if (!me || slot < 0) return -2;
    int index = -1;
    for (int i = 1; i < HB_MAX_PLAYERS; i++) if (h2_player(i) && !h2_live(i)) { index = i; break; }
    if (index < 0) return -3;
    uint8_t cfg[0x18 + 0x84] = {};
    cfg[0] = 1;                                  // valid
    // Tests: "no machine" (arg bit 16) and an unknown machine both ended the match within seconds
    // (the session counts the player as gone; one player left wins). Default now: a second local
    // player on the host's own machine, like split screen (controller and user index 1..3).
    cfg[1] = (arg >> 16) & 1;
    if (arg & (1 << 17)) {
        *(uint64_t*)(cfg + 8) = 0xB07B07B0B07B07B0ull;     // unknown machine (old test)
    } else {
        *(uint64_t*)(cfg + 8) = *(uint64_t*)(me + 0x14);    // the host's machine identifier
        int local = 1 + slot % 3;
        *(uint16_t*)(cfg + 2) = (uint16_t)local;           // controller index
        *(int32_t*)(cfg + 4) = local;                       // user index
    }
    *(uint16_t*)(cfg + 2) = 0xFFFF;
    *(int32_t*)(cfg + 4) = -1;
    *(uint64_t*)(cfg + 0x10) = 0xB07B07B000000000ull | (uint64_t)index;   // a player identifier
    memcpy(cfg + 0x18, me + 0xC0, 0x84);         // player 0's configuration (looks, team...)
    int team = (arg >> 8) & 0xFF;                // 0xFF = keep player 0's
    if (team != 0xFF) cfg[0x18 + 0x7C] = (uint8_t)team;    // configuration +0x7C: team (testing)
    wchar_t* name = (wchar_t*)(cfg + 0x18);
    wmemset(name, 0, 16);
    if (g_shm->cmd_name[0]) { wcsncpy_s(name, 16, g_shm->cmd_name, 15); g_shm->cmd_name[0] = 0; }
    else swprintf_s(name, 16, L"Bot %d", slot + 1);
    hb_apply_look(g_shm, 2, cfg, sizeof cfg);   // its own species and colours (brain/looks.py)
    // what MCC shows for it (name, tags, emblem: report.cpp), before MCC first looks the new player up
    wchar_t tag[4];                              // its service tag, configuration +0x68 (the scoreboard's tag column
    bot_service_tag(name, tag);                  // in Halo 2 classic)
    memcpy(cfg + 0x68, tag, 8);
    report_note_bot(index, name, tag, team != 0xFF ? team : -1, g_shm->cmd_clan, g_shm->cmd_emblem);
    uint32_t h = ((player_new_at_fn)(g_h2 + H2_PLAYER_NEW_AT))(index, cfg);
    if (h != 0xFFFFFFFFu) {
        g_shm->actions[slot].seq = 0;
        g_shm->bot_player_index[slot] = index;
    }
    logf("h2 add_bot index %d -> %08x", index, h);
    return (int64_t)h;
}

static void h2_run_command() {
    // only commands marked for Halo 2 (cmd_arg bit 24): a CE brain's ADD_BOT must never reach
    // an H2 match (adding a player ends it, docs/H2-01)
    if (g_shm->cmd_seq == g_shm->cmd_done_seq || !(g_shm->cmd_arg & (1 << 24))) return;
    g_shm->cmd_fault = 0;
    __try {
        if (g_shm->cmd == HB_CMD_ADD_BOT) g_shm->cmd_result = h2_add_bot(g_shm->cmd_arg);
        else g_shm->cmd_result = -1;
    } __except (EXCEPTION_EXECUTE_HANDLER) { g_shm->cmd_fault = 1; g_shm->cmd_result = -1; }
    g_shm->cmd_done_seq = g_shm->cmd_seq;
}

static void __fastcall h_update(uint8_t* actions) {
    if (g_shm) {
        g_shm->game_tick++;
        g_shm->game = 2;
        h2_run_command();
        __try {
            if (*(uint32_t*)(actions + 8) & 1) {        // player 0 has an action: copy it for the debug view
                memcpy(g_shm->dbg_action, actions + 0x100, H2_ACTION);
                g_shm->dbg_seq++;
            }
            for (int i = 0; i < HB_MAX_PLAYERS; i++) {
                int index = g_shm->bot_player_index[i];
                const hb_action& a = g_shm->actions[i];
                if (index < 0 || !a.seq || !h2_live(index)) continue;
                uint8_t* act = actions + 0x100 + (size_t)index * H2_ACTION;
                // decoded from player 0's action (tools/h2_action_probe.py): +0 button flags
                // (jump 0x6, fire 0x008C0100), +8 yaw, +0xC pitch, +0x10 throttle forward, +0x14
                // throttle left, +0x18/+0x1C triggers, +0x20 low bits action (0x3); the rest
                // (weapon and grenade slots...) comes from player 0's action as a template
                if (g_shm->h2_raw_valid) memcpy(act, g_shm->h2_raw_action, H2_ACTION);
                else if (*(uint32_t*)(actions + 8) & 1) memcpy(act, actions + 0x100, H2_ACTION);
                // the action's own fields (network decoder FUN_1808abf70, docs/H2-01): +0x24 weapon
                // set, +0x26/+0x27 primary/secondary weapon index, +0x28 grenade index, +0x2A
                // zoom, +0x2C interaction type, +0x2E pickup flags / seat, +0x30 interaction
                // object, +0x34 melee target, +0x38.. aim assist. Player 0's must not leak in (its
                // melee target was often this very bot).
                uint8_t* unit = h2_object(*(uint32_t*)(h2_player(index) + 0x2C));
                memset(act + 0x2C, 0, 4);
                memset(act + 0x30, 0xFF, 0x14);
                // the rest of the aim assist (+0x50 flags, +0x54 / +0x58 weights): the player's, with its target
                // (+0x38) cleared above, fails the action check (FUN_1807586b0 in the players update) and the bot's
                // last action replays (as Halo 3: ghidra/h2_aim_gate.c)
                memset(act + 0x44, 0, 0x18);
                // the red reticle's target (shared.h hb_target), where the action's network decoder carries a player's
                // (FUN_1808abf70 / FUN_1807583d0, ghidra/h2_actdec.c, h2_aimdec.c): +0x34 "melee-target-unit", the
                // autoaim block +0x38 "target-object", +0x3C "model-target", +0x40 "target-player", +0x50 flags,
                // +0x54 "primary-autoaim-level". As Halo 3's (live: no bot sword lunged until it was set). The values
                // a player's input writes are not seen live in Halo 2 yet (INFERRED: H3's, level 1.0)
                int tgt = hb_target(a.buttons);
                if (tgt >= 0 && tgt < HB_MAX_PLAYERS && h2_live(tgt)) {
                    uint32_t th = *(uint32_t*)(h2_player(tgt) + 0x2C);
                    if (th != 0xFFFFFFFFu && h2_object(th)) {
                        *(uint32_t*)(act + 0x34) = th;
                        *(uint32_t*)(act + 0x38) = th;
                        *(float*)(act + 0x54) = 1.0f;
                    }
                }
                hb_set_zoom(2, act, H2_ACTION, a.buttons);          // the scope level it wants (-1 none)
                // the bot's own weapon set, from the field Halo 2's unit control (FUN_1808f5800, ghidra/h2_unit_input.c)
                // checks and the game's own input copies (unit +0x228); +0x224 let a switch through only by chance
                if (unit) memcpy(act + 0x24, unit + 0x228, 4);
                int want = (int)((a.buttons >> HB_WEAPON_SHIFT) & 7) - 1;
                if (want >= 0) act[0x26] = (uint8_t)want;           // switch weapons
                uint32_t b = a.buttons, flags = 0;
                static uint32_t prev[HB_MAX_PLAYERS];
                if (b & HB_BTN_JUMP) flags |= 0x6;
                // fire: 0x008C0000 while held, 0x100 only on the press (the weapon fires on the
                // press edge; a constant 0x100 fired once, verified with projectile counts)
                if (b & HB_BTN_FIRE) flags |= 0x008C0000 | ((prev[i] & HB_BTN_FIRE) ? 0 : 0x100);
                prev[i] = b;
                *(uint32_t*)act = flags;
                *(float*)(act + 0x08) = a.yaw;
                *(float*)(act + 0x0C) = a.pitch;
                *(float*)(act + 0x10) = a.forward;
                *(float*)(act + 0x14) = a.strafe;
                *(float*)(act + 0x18) = (b & HB_BTN_FIRE) ? 1.0f : 0.0f;
                *(float*)(act + 0x1C) = (b & HB_BTN_FIRE) ? 1.0f : 0.0f;
                // action flags +0x20: a human's E is 0x301 on the press tick, 0x201 held, then
                // 0x41FE03 once held long ("hold E to pick up"). The bot sends the long hold plus
                // the weapon at its feet as interaction (type 1 = weapon pickup): verified, the bot
                // took the sniper on Lockout. Taps (reload) keep the low bits only.
                uint32_t w20 = *(uint32_t*)(act + 0x20) & 0xFF000000u;
                if (b & HB_BTN_ACTION) {
                    *(uint32_t*)(act + 0x20) = w20 | 0x0041FE03u;
                    uint32_t target = unit && hb_use_picks_up(b) && *(uint32_t*)(unit + 0x14) == 0xFFFFFFFFu
                                      ? h2_pickup_target(unit) : 0xFFFFFFFFu;   // on foot, no seat asked
                    if (target != 0xFFFFFFFFu) {
                        *(int16_t*)(act + 0x2C) = 1;
                        *(uint32_t*)(act + 0x30) = target;
                    }
                } else {
                    *(uint32_t*)(act + 0x20) = w20 | 0x00400200u;
                }
                // reload: the player's R sets bits 0 and 21 here (tools/decode_buttons.py reload=r); bit 21 alone
                // reloads nothing (tools/reload_probe.py h2: 0 of 7). Set natively, not through the button table: the
                // table clears its mask every tick, and bit 0 is also the action bit written just above
                if (b & HB_BTN_RELOAD) *(uint32_t*)(act + 0x20) |= 0x00200001u;
                static uint32_t map_prev[HB_MAX_PLAYERS];      // v8 decoded buttons (shared.h)
                hb_apply_buttons(g_shm, 2, act, H2_ACTION, b, map_prev[i]);
                map_prev[i] = b;
                *(uint32_t*)(actions + 8) |= 1u << index;
            }
        } __except (EXCEPTION_EXECUTE_HANDLER) { g_shm->cmd_fault = 2; }
    }
    o_update(actions);
}

// called from botcore's main loop: hook halo2.dll when it is loaded (again)
void h2_watch() {
    uint8_t* h2 = (uint8_t*)GetModuleHandleW(L"halo2.dll");
    if (!h2) return;
    bool hooked = false;
    __try { hooked = h2 == g_h2 && !memcmp(h2 + H2_PLAYERS_UPDATE, g_h2_patch, 5); }
    __except (EXCEPTION_EXECUTE_HANDLER) { hooked = false; }
    if (hooked) return;
    Sleep(500);
    if ((uint8_t*)GetModuleHandleW(L"halo2.dll") != h2) return;
    if (g_h2) MH_RemoveHook(g_h2 + H2_PLAYERS_UPDATE);
    g_h2 = h2;
    for (int i = 0; i < HB_MAX_PLAYERS; i++) g_shm->bot_player_index[i] = -1;
    if (MH_CreateHook(h2 + H2_PLAYERS_UPDATE, (void*)&h_update, (void**)&o_update) != MH_OK ||
        MH_EnableHook(h2 + H2_PLAYERS_UPDATE) != MH_OK) {
        logf("h2 hook failed at %p", h2);
        return;
    }
    memcpy(g_h2_patch, h2 + H2_PLAYERS_UPDATE, 5);
    g_shm->game = 2;
    logf("h2 hooks on at halo2 %p: players update +0x%llx", h2, (unsigned long long)H2_PLAYERS_UPDATE);
}
