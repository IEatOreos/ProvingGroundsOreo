// (custom, Nov 13) Watch only: the players MCC's menus are told are in the session (the owner: bots as rows in MCC's
// own MY GAME SESSION list; first prove which list that is). Nothing is changed: the list is logged when it changes.
// MCC-Win64-Shipping.exe (Oct 31 2026 file; static read, dumpbin):
//  - FUN_14024E4B0 "NotifyUIOfSessionMemberUpdate" builds a UIMessageSessionMembersUpdate (message id 0x044563CE): a
//    list at +0x38 (sentinel; first node at +0x40, a node's next at +8) of 0x80-byte SessionMemberDescription nodes;
//    node +0x18 the player's id, +0x20 a wide string (the name), +0x40 a second wide string, +0x10..+0x17 flags
//    (+0x10 the local player), +0x60..+0x6C four ints, +0x70 a byte (FUN_14024EEB0 / FUN_14024F054 fill them);
//  - it hands that message to the UI roster system (FUN_1402F4E84(manager, message), at +0x877 in it), then posts
//    it to the menus (FUN_1408AD688). It is one-way: the menus receive the list, they never act back on the session.
// The roster hook logs the list; the notify hook notes which of its 12 callers sent it. Any byte mismatch (another
// MCC build) leaves MCC untouched.
// (custom, Nov 13, the owner: "Yes, try one bot") Live, the list held the lobby's people (the player, a second
// person: only a friend on the friends list, the owner said) and, as the match loaded, the player alone; never the
// bots. botcore.ini sessionbots=1 or 2 (off by default; 2 also the player's session flags, below) adds
// the lobby's first bot to that list, in the menus only, before the roster system and the menus get it: a node made
// by MCC's own builder FUN_14024F054 (in MCC's own memory, operator new FUN_1409300F4, so MCC frees it with the
// message), id 0xB07B07B00000000F (report.cpp report_note_lobby_bot: its name, clan tag, service tag, nameplate, MCC's
// default emblem), numbers as the non-player person's (-1, -1, -1, 0). The mod's own drawn rows step aside meanwhile
// (overlay.cpp). A test: what MCC draws, and what its count, Start and the bot's menu do with it.
#include <windows.h>
#include <intrin.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "third_party/minhook/include/MinHook.h"
#include "shared.h"
#include "bots_panel.h"

void logf(const char* fmt, ...);
extern hb_shared* g_shm;
extern hb_roster g_roster, g_ff_roster;          // botcore.cpp
extern int hb_panel_firefight;                   // bots_panel.cpp
extern uint32_t g_sessionbots;                   // botcore.cpp (botcore.ini sessionbots=)
int mcc_menu_state();                            // overlay.cpp: 0 menus
void report_note_lobby_bot(int index, const char* name, int team);   // report.cpp

static const uintptr_t SW_NOTIFY = 0x24E4B0, SW_ROSTER = 0x2F4E84, SW_ROSTER_AT = 0x24ED27;
static const uintptr_t SW_NEW = 0x9300F4, SW_DESC = 0x24F054;
static const uint8_t SW_NEW_HEAD[] = {0x33, 0xD2, 0xE9};                // (xor edx,edx; jmp: MCC's allocator)
static const uint8_t SW_DESC_HEAD[] = {0x48, 0x8B, 0xC4, 0x48, 0x89, 0x48, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x30};
static const int SW_BOT_INDEX = 15;                                      // its made-up id's player index
static const uint32_t SW_MSG_ID = 0x044563CE;
static const uint8_t SW_NOTIFY_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57,
                                         0x48, 0x8D, 0x6C, 0x24, 0x80, 0x48, 0x81, 0xEC, 0x80, 0x01, 0x00, 0x00};
static const uint8_t SW_ROSTER_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56,
                                         0x41, 0x57, 0x48, 0x8D, 0x68, 0xA1, 0x48, 0x81, 0xEC, 0xF0, 0x00, 0x00, 0x00};

typedef void(__fastcall* notify_fn)(void* session);
typedef void(__fastcall* roster_fn)(void* mgr, uint8_t* msg);
static notify_fn o_notify;
static roster_fn o_roster;
static uint8_t* g_mcc;
static __declspec(thread) uintptr_t t_caller;   // the notify's caller (offset in MCC), this thread
static uint64_t g_last_hash;
static volatile LONG g_lines;                   // log lines written (a cap: never floods the log)

// an MSVC std::wstring at p (buffer 16 bytes, size +0x10, capacity +0x18; capacity 8+ means a pointer)
static void wstr(const uint8_t* p, char* out, int cap) {
    out[0] = 0;
    uint64_t n = *(const uint64_t*)(p + 0x10), c = *(const uint64_t*)(p + 0x18);
    if (n > 64 || c < n) { sprintf_s(out, cap, "?(%llu)", (unsigned long long)n); return; }
    const wchar_t* s = c >= 8 ? *(const wchar_t* const*)p : (const wchar_t*)p;
    if (!n) return;
    int k = WideCharToMultiByte(CP_UTF8, 0, s, (int)n, out, cap - 1, nullptr, nullptr);
    out[k > 0 ? k : 0] = 0;
}

static void log_members(const uint8_t* msg) {
    char line[2048];
    int at = 0, n = 0;
    uint64_t h = 1469598103934665603ull;
    const uint8_t* head = msg + 0x38;
    const uint8_t* node = *(const uint8_t* const*)(msg + 0x40);
    at += sprintf_s(line + at, sizeof line - at, "session list: from +%llX, flag %u:", (unsigned long long)t_caller,
                    msg[0x48]);
    for (; node && node != head && n < 32; node = *(const uint8_t* const*)(node + 8), n++) {
        char a[80], b[80];
        wstr(node + 0x20, a, sizeof a);
        wstr(node + 0x40, b, sizeof b);
        uint64_t id = *(const uint64_t*)(node + 0x18);
        const int32_t* v = (const int32_t*)(node + 0x60);
        if (at < (int)sizeof line - 200)
            at += sprintf_s(line + at, sizeof line - at, " [%d %llx \"%s\" \"%s\" f%02x%02x%02x%02x%02x%02x%02x%02x v%d,%d,%d,%d,%u]",
                            n, (unsigned long long)id, a, b, node[0x10], node[0x11], node[0x12], node[0x13], node[0x14],
                            node[0x15], node[0x16], node[0x17], v[0], v[1], v[2], v[3], node[0x70]);
        for (int k = 0x10; k < 0x80; k++)
            if (k < 0x20 || k >= 0x60) { h ^= node[k]; h *= 1099511628211ull; }
        h ^= id; h *= 1099511628211ull;
        for (const char* c = a; *c; c++) { h ^= (uint8_t)*c; h *= 1099511628211ull; }
    }
    at += sprintf_s(line + at, sizeof line - at, " (%d)", n);
    if (h == g_last_hash) return;                   // only when it changed
    g_last_hash = h;
    if (InterlockedIncrement(&g_lines) > 400) return;
    logf("%s", line);
}

static void __fastcall h_notify(void* session) {
    uintptr_t prev = t_caller;
    t_caller = (uintptr_t)((uint8_t*)_ReturnAddress() - g_mcc);
    o_notify(session);
    t_caller = prev;
}

// MCC's std::wstring as FUN_14024F054 reads its name argument: a pointer (capacity 8+), the size at +0x10
struct sw_wstr { const wchar_t* p; uint64_t pad; uint64_t size; uint64_t cap; };
typedef void*(__fastcall* new_fn)(size_t n);
typedef void*(__fastcall* desc_fn)(void* node, uint64_t id, const sw_wstr* name, void* unused, uint64_t a5, uint64_t a6,
                                   int64_t a7, int64_t a8, int64_t a9, uint64_t a10);
static bool g_add_ok;                            // the allocator and the builder are the ones decoded
static char g_added[16];                         // the bot last added (logged when it changes)

// the lobby's first bot onto the list's end, in the menus only (sessionbots=1)
static void add_lobby_bot(uint8_t* msg) {
    if (!g_add_ok || g_sessionbots < 1 || g_sessionbots > 2 || mcc_menu_state() != 0 || !g_shm || !g_shm->bots_enabled ||
        g_shm->lidar_mode)
        return;
    const hb_roster& R = hb_panel_firefight ? g_ff_roster : g_roster;
    if (R.n < 1) return;
    char name[16];
    strncpy_s(name, R.bot[0].name, _TRUNCATE);
    int team = R.bot[0].team;
    if (!name[0]) return;
    uint8_t* head = msg + 0x38;
    const uint64_t id = 0xB07B07B000000000ull | (uint64_t)SW_BOT_INDEX;
    int n = 0;
    uint8_t* me = nullptr;                                // the player's own node (+0x10 set)
    for (uint8_t* node = *(uint8_t**)(msg + 0x40); node && node != head && n < 32; node = *(uint8_t**)(node + 8), n++) {
        if (*(uint64_t*)(node + 0x18) == id) return;    // (already on it)
        if (node[0x10] && !me) me = node;
    }
    if (!n || !me) return;                                // (no player yet: not a lobby's list)
    report_note_lobby_bot(SW_BOT_INDEX, name, team);      // (MCC's lookups by its id: report.cpp)
    wchar_t w[16];
    int k = MultiByteToWideChar(CP_UTF8, 0, name, -1, w, 16);
    if (k < 2) return;
    sw_wstr s = {w, 0, (uint64_t)(k - 1), 8};
    uint8_t* node = (uint8_t*)((new_fn)(g_mcc + SW_NEW))(0x80);
    if (!node) return;
    memset(node, 0, 0x80);
    ((desc_fn)(g_mcc + SW_DESC))(node, id, &s, nullptr, 0, 0, -1, -1, -1, 0);
    if (g_sessionbots == 2) {
        // (Nov 13, live: a friend only on the friends list came as flags 00000000 01, numbers -1, -1, -1; the player as
        // 01010101 0001, numbers 0, -1, 0) mode 2: the player's two "in this session" flags (+0x11, +0x12) and +0x15,
        // +0x64 its team (the player's 0 on Red: a guess), +0x6C the player's
        node[0x11] = me[0x11]; node[0x12] = me[0x12]; node[0x15] = me[0x15];
        *(int32_t*)(node + 0x64) = team;
        *(int32_t*)(node + 0x6C) = *(int32_t*)(me + 0x6C);
    }
    uint8_t* last = *(uint8_t**)head;                     // at the end, as MCC adds them
    *(uint8_t**)(last + 8) = node;
    *(uint8_t**)node = last;
    *(uint8_t**)(node + 8) = head;
    *(uint8_t**)head = node;
    if (strcmp(g_added, name)) {
        strcpy_s(g_added, name);
        logf("session list: added %s (team %d) as player %d, mode %u", name, team, SW_BOT_INDEX, g_sessionbots);
    }
}

static void __fastcall h_roster(void* mgr, uint8_t* msg) {
    __try {
        if (msg && *(const uint32_t*)(msg + 0x28) == SW_MSG_ID) {
            add_lobby_bot(msg);
            log_members(msg);
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) { logf("session list: unreadable"); }
    o_roster(mgr, msg);
}

void session_watch_hooks() {
    g_mcc = (uint8_t*)GetModuleHandleW(nullptr);
    bool ok = false;
    __try {
        ok = !memcmp(g_mcc + SW_NOTIFY, SW_NOTIFY_HEAD, sizeof SW_NOTIFY_HEAD) &&
             !memcmp(g_mcc + SW_ROSTER, SW_ROSTER_HEAD, sizeof SW_ROSTER_HEAD) && g_mcc[SW_ROSTER_AT] == 0xE8 &&
             SW_ROSTER_AT + 5 + *(int32_t*)(g_mcc + SW_ROSTER_AT + 1) == SW_ROSTER;
    } __except (EXCEPTION_EXECUTE_HANDLER) { ok = false; }
    if (!ok) { logf("session list: MCC build not the one decoded (Oct 31 2026): watch off"); return; }
    if (MH_CreateHook(g_mcc + SW_NOTIFY, (void*)&h_notify, (void**)&o_notify) != MH_OK ||
        MH_CreateHook(g_mcc + SW_ROSTER, (void*)&h_roster, (void**)&o_roster) != MH_OK ||
        MH_EnableHook(g_mcc + SW_NOTIFY) != MH_OK || MH_EnableHook(g_mcc + SW_ROSTER) != MH_OK) {
        logf("session list: hooks failed");
        return;
    }
    __try {
        g_add_ok = !memcmp(g_mcc + SW_NEW, SW_NEW_HEAD, sizeof SW_NEW_HEAD) &&
                   !memcmp(g_mcc + SW_DESC, SW_DESC_HEAD, sizeof SW_DESC_HEAD);
    } __except (EXCEPTION_EXECUTE_HANDLER) { g_add_ok = false; }
    logf("session list: watch on (logs MCC's session players when they change); one lobby bot %s", !g_add_ok
         ? "off (not the builder decoded)" : g_sessionbots == 1 ? "added (sessionbots=1, as a plain entry)"
         : g_sessionbots == 2 ? "added (sessionbots=2, with the player's session flags)" : "off (sessionbots=0)");
}
