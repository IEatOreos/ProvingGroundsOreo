// spawnhook.cpp: Reach's multiplayer spawn check and respawn handler, hooked so bots respawn in Invasion and Firefight
// (reach.cpp hr_bot_solo_spawn, hr_bot_spawn_point).
//
// FUN_1800ffabc(player) (ghidra/hr_spawnchk.c) is the spawn check of the players update's spawn loop
// (ghidra/hr_players_update.c): player index into the 0x490 players, the respawn time +0x1BC. Before it answers,
// hr_bot_solo_spawn clears a bot's co-op spawning byte, so it never waits for a choice it cannot make (it spawns on
// time, then reach.cpp hr_spawn_moves moves it to the spawn the brain picked).
// FUN_18004633c(player) (ghidra/hr_respawn_tick.c) is the per-player respawn handler the players update runs for each
// player after the spawn loop: before it, hr_bot_spawn_point gives a dead Firefight bot the spawn point the person's
// death screen gives him.
// On whenever haloreach.dll is loaded, and only over the functions' own first bytes (MCC 1.3528's haloreach.dll; another
// build is left alone and logged once).
#include <windows.h>
#include <string.h>
#include "shared.h"
#include "third_party/minhook/include/MinHook.h"

extern hb_shared* g_shm;
void logf(const char* fmt, ...);
void hr_bot_solo_spawn(uint32_t player);
void hr_bot_spawn_point(uint32_t player);

typedef char(__fastcall* should_spawn_fn)(uint32_t player);
typedef uint64_t(__fastcall* respawn_tick_fn)(uint32_t player);
static should_spawn_fn o_hr_should_spawn;
static respawn_tick_fn o_hr_respawn_tick;
static const uint8_t HR_SHOULD_SPAWN_HEAD[8] = { 0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x74 };
static const uint8_t HR_RESPAWN_TICK_HEAD[8] = { 0x48, 0x8B, 0xC4, 0x48, 0x89, 0x58, 0x08, 0x48 };

static char __fastcall h_hr_should_spawn(uint32_t player) {
    hr_bot_solo_spawn(player);
    return o_hr_should_spawn(player);
}

static uint64_t __fastcall h_hr_respawn_tick(uint32_t player) {
    hr_bot_spawn_point(player);
    return o_hr_respawn_tick(player);
}

static bool same(const uint8_t* at, const uint8_t* bytes, size_t n) {
    __try { return !memcmp(at, bytes, n); } __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
}

// A hook is made once and only ever enabled / disabled, never removed: MinHook frees a removed hook's
// trampoline, and a game thread inside the hook at that moment would jump into freed memory. A module reloaded at
// the same address has its own bytes back: disable (MinHook writes the original bytes, the same) and enable again.
struct made_hook { uint8_t* at; void* tramp; };
struct game_hook {
    const char* name; uintptr_t rva; const uint8_t* head; void* detour; void** orig;
    made_hook made[16];             // every address the hook was created at (the DLL may load elsewhere next time)
    uint8_t* at;                    // where it is on now
    uint8_t bytes[5];               // the jump it wrote, to see a reloaded module
    bool refused;
};
static game_hook g_hooks[] = {
    { "spawn check", 0xFFABC, HR_SHOULD_SPAWN_HEAD, (void*)&h_hr_should_spawn, (void**)&o_hr_should_spawn },
    { "respawn handler", 0x4633C, HR_RESPAWN_TICK_HEAD, (void*)&h_hr_respawn_tick, (void**)&o_hr_respawn_tick },
};

static void watch_one(game_hook& k, uint8_t* mod) {
    uint8_t* at = mod ? mod + k.rva : nullptr;
    if (at && at == k.at && same(at, k.bytes, 5)) return;            // on, as wanted
    if (!at) { k.at = nullptr; return; }
    made_hook* h = nullptr;
    for (made_hook& m : k.made) if (m.at == at) h = &m;
    if (!h && !same(at, k.head, 8)) {
        if (!k.refused) logf("spawnhook: haloreach.dll+0x%llx (%s) is not the expected function: no hook",
                             (unsigned long long)k.rva, k.name);
        k.refused = true;
        return;
    }
    if (!h) {
        void* tramp = nullptr;
        for (made_hook& m : k.made) if (!m.at) { h = &m; break; }
        if (!h || MH_CreateHook(at, k.detour, &tramp) != MH_OK) {
            logf("spawnhook: %s hook at %p failed", k.name, at);
            return;
        }
        h->at = at; h->tramp = tramp;
    }
    *k.orig = h->tramp;
    MH_DisableHook(at);
    if (MH_EnableHook(at) != MH_OK) { logf("spawnhook: %s hook at %p not enabled", k.name, at); return; }
    k.at = at;
    memcpy(k.bytes, at, 5);
    logf("spawnhook: Reach %s hooked at %p", k.name, at);
}

// botcore's main loop: keep the hooks on while haloreach.dll is loaded, following it through unload / reload
void spawnhook_watch() {
    if (!g_shm) return;
    uint8_t* mod = (uint8_t*)GetModuleHandleW(L"haloreach.dll");
    for (game_hook& k : g_hooks) watch_one(k, mod);
}
