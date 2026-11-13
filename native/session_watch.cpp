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
#include <windows.h>
#include <intrin.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "third_party/minhook/include/MinHook.h"

void logf(const char* fmt, ...);

static const uintptr_t SW_NOTIFY = 0x24E4B0, SW_ROSTER = 0x2F4E84, SW_ROSTER_AT = 0x24ED27;
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

static void __fastcall h_roster(void* mgr, uint8_t* msg) {
    __try {
        if (msg && *(const uint32_t*)(msg + 0x28) == SW_MSG_ID) log_members(msg);
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
    logf("session list: watch on (logs MCC's session players when they change)");
}
