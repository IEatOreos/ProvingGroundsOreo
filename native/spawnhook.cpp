// spawnhook.cpp: Reach's multiplayer spawn check, hooked so bots respawn in Invasion (reach.cpp hr_bot_solo_spawn).
//
// FUN_1800ffabc(player) (ghidra/hr_spawnchk.c) is the spawn check of the players update's spawn loop
// (ghidra/hr_players_update.c): player index into the 0x490 players, the respawn time +0x1BC. Before it answers,
// hr_bot_solo_spawn clears a bot's co-op spawning byte, so it never waits for a choice it cannot make (it spawns on
// time, then reach.cpp hr_spawn_moves moves it to the spawn the brain picked). On whenever haloreach.dll is loaded, and only over the function's own first bytes
// (MCC 1.3528's haloreach.dll; another build is left alone and logged once).
#include <windows.h>
#include <string.h>
#include "shared.h"
#include "third_party/minhook/include/MinHook.h"

extern hb_shared* g_shm;
void logf(const char* fmt, ...);
void hr_bot_solo_spawn(uint32_t player);

typedef char(__fastcall* should_spawn_fn)(uint32_t player);
static should_spawn_fn o_hr_should_spawn;
static const uintptr_t HR_SHOULD_SPAWN = 0xFFABC;
static const uint8_t HR_SHOULD_SPAWN_HEAD[8] = { 0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x74 };

static char __fastcall h_hr_should_spawn(uint32_t player) {
    hr_bot_solo_spawn(player);
    return o_hr_should_spawn(player);
}

static bool same(const uint8_t* at, const uint8_t* bytes, size_t n) {
    __try { return !memcmp(at, bytes, n); } __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
}

// The hook is made once and only ever enabled / disabled, never removed: MinHook frees a removed hook's
// trampoline, and a game thread inside the hook at that moment would jump into freed memory. A module reloaded at
// the same address has its own bytes back: disable (MinHook writes the original bytes, the same) and enable again.
struct made_hook { uint8_t* at; void* tramp; };
static made_hook g_made[16];        // every address the hook was created at (the DLL may load elsewhere next time)
static uint8_t* g_at;               // where it is on now
static uint8_t g_bytes[5];          // the jump it wrote, to see a reloaded module
static bool g_refused;

// botcore's main loop: keep the hook on while haloreach.dll is loaded, following it through unload / reload
void spawnhook_watch() {
    if (!g_shm) return;
    uint8_t* mod = (uint8_t*)GetModuleHandleW(L"haloreach.dll");
    uint8_t* at = mod ? mod + HR_SHOULD_SPAWN : nullptr;
    if (at && at == g_at && same(at, g_bytes, 5)) return;            // on, as wanted
    if (!at) { g_at = nullptr; return; }
    made_hook* h = nullptr;
    for (made_hook& m : g_made) if (m.at == at) h = &m;
    if (!h && !same(at, HR_SHOULD_SPAWN_HEAD, 8)) {
        if (!g_refused) logf("spawnhook: haloreach.dll+0x%llx is not the expected function: no hook",
                             (unsigned long long)HR_SHOULD_SPAWN);
        g_refused = true;
        return;
    }
    if (!h) {
        void* tramp = nullptr;
        for (made_hook& m : g_made) if (!m.at) { h = &m; break; }
        if (!h || MH_CreateHook(at, (void*)&h_hr_should_spawn, &tramp) != MH_OK) {
            logf("spawnhook: hook at %p failed", at);
            return;
        }
        h->at = at; h->tramp = tramp;
    }
    o_hr_should_spawn = (should_spawn_fn)h->tramp;
    MH_DisableHook(at);
    if (MH_EnableHook(at) != MH_OK) { logf("spawnhook: hook at %p not enabled", at); return; }
    g_at = at;
    memcpy(g_bytes, at, 5);
    logf("spawnhook: Reach spawn check hooked at %p", at);
}
