// odst.cpp: Halo 3: ODST Firefight (halo3odst.dll, MCC 1.3528) bot teammates, the Halo 3 plan
// (h3.cpp) with ODST's offsets (docs/NEXT-01).
// - TLS block: +0x10 players (header +0x20 max, +0x24 element size 0x418, +0x48 data), +0x20
//   objects (0x18-byte entries: +0 salt, +3 type, +0x10 object address), +0x40 game globals
//   (+0x200: player configurations; the player's is the first).
// - players update FUN_1800fea10(actions): +8 bitmask of players with an action, +0x10 +
//   index * 0x240 each player's action.
// - player_new_at_index FUN_1800fbfe4(index, config, 0): config header as Halo 3 (+0 valid, +1
//   no machine, +2 controller, +4 user, +8 machine 6 bytes, +0x10 player identifier), +0x18 the
//   0x80-byte configuration (name at +0 and +0x58; copied to player +0xD8). Cloning the player's
//   configuration keeps his team: Firefight teammates.
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

static uint8_t* g_od;
static uint8_t g_od_patch[5];
static DWORD g_od_tls_index;
static const uintptr_t OD_PLAYERS_UPDATE = 0xFEA10, OD_PLAYER_NEW_AT = 0xFBFE4;
static const size_t OD_PLAYER_SIZE = 0x418, OD_ACTION = 0x240, OD_CONFIG = 0x98;
typedef void(__fastcall* od_update_fn)(uint8_t* actions);
typedef int(__fastcall* od_new_at_fn)(int index, uint8_t* config, char flag);
static od_update_fn o_od_update;

static uint8_t* od_tls() {
    void** arr = (void**)__readgsqword(0x58);
    return arr ? (uint8_t*)arr[g_od_tls_index] : nullptr;
}

static uint8_t* od_player(uint8_t* tls, int index) {
    uint8_t* hdr = *(uint8_t**)(tls + 0x10);
    if (!hdr || index < 0 || index >= *(int32_t*)(hdr + 0x20)) return nullptr;
    uint8_t* data = *(uint8_t**)(hdr + 0x48);
    return data ? data + (size_t)index * OD_PLAYER_SIZE : nullptr;
}
static bool od_live(uint8_t* tls, int index) { uint8_t* p = od_player(tls, index); return p && *(uint16_t*)p != 0; }

static uint8_t* od_object(uint8_t* tls, uint32_t handle) {
    uint8_t* hdr = *(uint8_t**)(tls + 0x20);
    if (!hdr || handle == 0xFFFFFFFFu || (int)(handle & 0xFFFF) >= *(int32_t*)(hdr + 0x20)) return nullptr;
    uint8_t* e = *(uint8_t**)(hdr + 0x48) + (size_t)(handle & 0xFFFF) * 0x18;
    return *(uint16_t*)e == handle >> 16 ? *(uint8_t**)(e + 0x10) : nullptr;
}

static int64_t od_add_bot(uint8_t* tls, int arg) {
    uint8_t* globals = *(uint8_t**)(tls + 0x40);
    int slot = -1;
    for (int i = 0; i < HB_MAX_PLAYERS; i++) if (g_shm->bot_player_index[i] < 0) { slot = i; break; }
    if (!globals || !od_player(tls, 0) || slot < 0) return -2;
    int index = -1;
    for (int i = 1; i < HB_MAX_PLAYERS; i++) if (od_player(tls, i) && !od_live(tls, i)) { index = i; break; }
    if (index < 0) return -3;
    uint8_t cfg[OD_CONFIG];
    memcpy(cfg, globals + 0x200, OD_CONFIG);         // the player's configuration as he joined
    cfg[0] = 1;
    cfg[1] = 0;
    *(uint32_t*)(cfg + 8) = 0xB07B0000u | (uint32_t)index;   // an unknown machine (no local user)
    *(uint16_t*)(cfg + 0xC) = 0xB07B;
    *(uint16_t*)(cfg + 2) = 0xFFFF;
    *(int32_t*)(cfg + 4) = -1;
    uint64_t bot_id = 0xB07B07B000000000ull | (uint64_t)index;      // in every place the player's id was (H3 has a
    hb_replace_id(cfg, sizeof cfg, *(uint64_t*)(cfg + 0x10), bot_id);   // second copy MCC's report goes by)
    *(uint64_t*)(cfg + 0x10) = bot_id;
    wchar_t name[16] = {};
    if (g_shm->cmd_name[0]) { wcsncpy_s(name, 16, g_shm->cmd_name, 15); g_shm->cmd_name[0] = 0; }
    else swprintf_s(name, 16, L"Bot %d", slot + 1);
    memcpy(cfg + 0x18, name, 32);
    memcpy(cfg + 0x18 + 0x58, name, 32);
    wchar_t tag[4];                                   // its service tag (+0x4E; before: every bot carried the host's)
    bot_service_tag(name, tag);
    memcpy(cfg + 0x4E, tag, 8);
    hb_apply_look(g_shm, 5, cfg, sizeof cfg);   // its own character and colours (brain/looks.py)
    // what MCC shows for it (name, tags, emblem: report.cpp), before MCC first looks the new player up
    report_note_bot(index, name, tag, -1, g_shm->cmd_clan, g_shm->cmd_emblem);
    int h = ((od_new_at_fn)(g_od + OD_PLAYER_NEW_AT))(index, cfg, 0);
    if (h != -1) {
        *(uint32_t*)(od_player(tls, index) + 4) |= 1;                         // "present": spawns
        memcpy(od_player(tls, index) + 0x14, od_player(tls, 0) + 0x14, 6);    // host's machine
        g_shm->actions[slot].seq = 0;
        g_shm->bot_player_index[slot] = index;
    }
    logf("odst add_bot index %d -> %08x", index, h);
    return (int64_t)h;
}

static void __fastcall h_od_update(uint8_t* actions) {
    if (g_shm) {
        g_shm->game_tick++;
        g_shm->game = 5;
        __try {
            uint8_t* tls = od_tls();
            if (tls) {
                if (g_shm->cmd_seq != g_shm->cmd_done_seq && (g_shm->cmd_arg & (1 << 27))) {
                    g_shm->cmd_fault = 0;
                    __try {
                        g_shm->cmd_result = g_shm->cmd == HB_CMD_ADD_BOT ? od_add_bot(tls, g_shm->cmd_arg) : -1;
                    } __except (EXCEPTION_EXECUTE_HANDLER) { g_shm->cmd_fault = 1; g_shm->cmd_result = -1; }
                    g_shm->cmd_done_seq = g_shm->cmd_seq;
                }
                if (*(uint32_t*)(actions + 8) & 1) {          // the player's action, for decoding
                    memcpy(g_shm->dbg_action, actions + 0x10, 0x100);
                    memcpy(g_shm->dbg_big, actions + 0x10, OD_ACTION);
                    g_shm->dbg_seq++;
                }
                for (int i = 0; i < HB_MAX_PLAYERS; i++) {
                    int index = g_shm->bot_player_index[i];
                    if (index >= 0 && od_live(tls, index)) *(uint32_t*)(od_player(tls, index) + 4) |= 1;
                    const hb_action& a = g_shm->actions[i];
                    if (index < 0 || !a.seq || !od_live(tls, index)) continue;
                    uint8_t* act = actions + 0x10 + (size_t)index * OD_ACTION;
                    *(uint32_t*)(actions + 8) |= 1u << index;
                    if (g_shm->h2_raw_valid == 2) { memcpy(act, g_shm->h2_raw_action, 0x100); continue; }
                    // the player's action as the template (input history and the rest), then the bot's
                    // fields
                    if (*(uint32_t*)(actions + 8) & 1) memcpy(act, actions + 0x10, OD_ACTION);
                    void od_fill(uint8_t* tls, uint8_t* act, int index, const hb_action& a, int slot);
                    od_fill(tls, act, index, a, i);
                    static uint32_t map_prev[HB_MAX_PLAYERS];  // v8 decoded buttons (shared.h)
                    hb_apply_buttons(g_shm, 5, act, OD_ACTION, a.buttons, map_prev[i]);
                    map_prev[i] = a.buttons;
                }
            }
        } __except (EXCEPTION_EXECUTE_HANDLER) { g_shm->cmd_fault = 2; }
    }
    o_od_update(actions);
}

// decoded live with tools/h2_action_record.py: the Halo 3 layout. +0 1 and +1 the unit's life
// counter (unit +0x204; the players update drops an action whose counter differs), +0x08 control
// flags (jump 0x2, fire 0x00080040), +0x10 yaw, +0x14 pitch, +0x18 throttle forward, +0x1C
// throttle left, +0x30 trigger, +0x38 jump (1.0), +0x40 action (E: 1, held long 3), +0x44 weapon
// set / +0x46 primary / +0x47 secondary index (unit +0x274; weapons at unit +0x27C), +0x4A zoom,
// +0x4C interaction type, +0x50 interaction object, +0x54.. targets
void od_fill(uint8_t* tls, uint8_t* act, int index, const hb_action& a, int slot) {
    (void)slot;
    uint8_t* unit = od_object(tls, *(uint32_t*)(od_player(tls, index) + 0x28));
    act[0] = 1;
    if (unit) act[1] = unit[0x204];
    memset(act + 0x4C, 0, 4);
    memset(act + 0x50, 0xFF, 0x14);
    // the player's aim assist (+0x68 / +0x6C weights, +0x7C flags) with its target (+0x58) cleared fails the
    // action check FUN_1800fe624 and the bot's last action replays (as Halo 3: ghidra/od_action_gate.c, h3.cpp)
    memset(act + 0x64, 0, 0x1C);
    *(int16_t*)(act + 0x4A) = -1;
    // the weapon set ODST's unit control (FUN_18039557c, ghidra/od_unit_control.c) checks is the unit's +0x278 (as
    // Halo 3's +0x264): from +0x274 a switch request was taken only by chance
    if (unit) memcpy(act + 0x44, unit + 0x278, 4);
    int want = (int)((a.buttons >> HB_WEAPON_SHIFT) & 7) - 1;
    if (want >= 0) { act[0x46] = (uint8_t)want; if (act[0x47] == act[0x46]) act[0x47] = 0xFF; }
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
    *(uint32_t*)(act + 0x40) = (b & HB_BTN_ACTION) ? 3u : 0u;
}

static DWORD tls_index_of(uint8_t* mod) {
    IMAGE_NT_HEADERS64* nt = (IMAGE_NT_HEADERS64*)(mod + ((IMAGE_DOS_HEADER*)mod)->e_lfanew);
    DWORD rva = nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_TLS].VirtualAddress;
    if (!rva) return 0;
    IMAGE_TLS_DIRECTORY64* t = (IMAGE_TLS_DIRECTORY64*)(mod + rva);
    return *(DWORD*)t->AddressOfIndex;
}

void odst_watch() {
    uint8_t* m = (uint8_t*)GetModuleHandleW(L"halo3odst.dll");
    if (!m) return;
    bool hooked = false;
    __try { hooked = m == g_od && !memcmp(m + OD_PLAYERS_UPDATE, g_od_patch, 5); }
    __except (EXCEPTION_EXECUTE_HANDLER) { hooked = false; }
    if (hooked) return;
    Sleep(500);
    if ((uint8_t*)GetModuleHandleW(L"halo3odst.dll") != m) return;
    if (g_od) MH_RemoveHook(g_od + OD_PLAYERS_UPDATE);
    g_od = m;
    g_od_tls_index = tls_index_of(m);
    for (int i = 0; i < HB_MAX_PLAYERS; i++) g_shm->bot_player_index[i] = -1;
    if (MH_CreateHook(m + OD_PLAYERS_UPDATE, (void*)&h_od_update, (void**)&o_od_update) != MH_OK ||
        MH_EnableHook(m + OD_PLAYERS_UPDATE) != MH_OK) {
        logf("odst hook failed at %p", m);
        return;
    }
    memcpy(g_od_patch, m + OD_PLAYERS_UPDATE, 5);
    logf("odst hooks on at halo3odst %p: players update +0x%llx, tls index %lu", m,
         (unsigned long long)OD_PLAYERS_UPDATE, g_od_tls_index);
}
