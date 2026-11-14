// (custom, Nov 13) Watch only: MCC's Career page (Player Details > Career > Stats), the numbers it shows for a player
// (the owner: fake stats for the bots on their Career page, "Yes, build it": first see what the page holds).
// MCC-Win64-Shipping.exe (Oct 31 2026 file; static read, dumpbin):
//  - FUN_140527A50(page, column) fills the multiplayer stats ("populateContentMultiplayer"); its one caller is
//    FUN_14052DA08. column (0 or 1) * 0x38 picks one of two columns of each stat;
//  - the page holds the stats as 0x70-byte entries (two 0x38 columns), each column a byte at +0 (handed to the
//    formatter with the value) and the value, a qword at +0x20: +0x1988 games played, +0x19F8 games won, +0x1A68 first
//    place finishes, +0x1AD8 kills, +0x1B48 headshots, +0x1BB8 assists, +0x1C28 betrayals, +0x1C98 best spree,
//    +0x2218 deaths (and more: the $SR_ / $CAREER_ labels after each);
//  - page +0x1008 picks the game (0..7).
// This logs, when they change: the column, the game, each of those stats' two columns (byte, value as an integer
// and as a double), and the offsets in the page that hold an Xbox id or a bot's made-up id (which player the page
// shows). Nothing is changed. Any byte mismatch (another MCC build) leaves MCC untouched.
#include <windows.h>
#include <intrin.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "third_party/minhook/include/MinHook.h"

void logf(const char* fmt, ...);

static const uintptr_t CW_FILL = 0x527A50;
static const uint8_t CW_FILL_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57,
                                       0x48, 0x8B, 0xEC, 0x48, 0x83, 0xEC, 0x70};
static const struct { uint32_t at; const char* name; } CW_STATS[] = {
    {0x1988, "games"}, {0x19F8, "won"}, {0x1A68, "first"}, {0x1AD8, "kills"}, {0x1B48, "headshots"},
    {0x1BB8, "assists"}, {0x1C28, "betrayals"}, {0x1C98, "spree"}, {0x2218, "deaths"}};
static const uint32_t CW_SCAN = 0x4400;          // the page's bytes scanned for player ids

typedef void(__fastcall* fill_fn)(uint8_t* page, uint8_t column);
static fill_fn o_fill;
static uint64_t g_cw_hash;
static volatile LONG g_cw_lines;

static void cw_log(const uint8_t* page, uint8_t column) {
    char line[1600];
    int at = sprintf_s(line, "career: column %u, game %d:", column, *(const int32_t*)(page + 0x1008));
    uint64_t h = 1469598103934665603ull;
    for (const auto& s : CW_STATS) {
        at += sprintf_s(line + at, sizeof line - at, " %s", s.name);
        for (int c = 0; c < 2; c++) {
            const uint8_t* e = page + s.at + c * 0x38;
            uint64_t v = *(const uint64_t*)(e + 0x20);
            double d;
            memcpy(&d, &v, 8);
            at += sprintf_s(line + at, sizeof line - at, " [%u %lld %.6g]", e[0], (long long)v,
                            (d == d && d > -1e15 && d < 1e15) ? d : 0.0);
            h ^= e[0] ^ v; h *= 1099511628211ull;
        }
    }
    at += sprintf_s(line + at, sizeof line - at, "; ids:");
    int ids = 0;
    for (uint32_t o = 0; o + 8 <= CW_SCAN && ids < 12; o += 8) {
        uint64_t q = *(const uint64_t*)(page + o);
        uint32_t hi = (uint32_t)(q >> 32);
        if ((q >> 48) == 0x0009 || hi == 0xB07B07B0u || hi == 0xB07B07B1u) {
            at += sprintf_s(line + at, sizeof line - at, " +%X=%s%llx", o, hi >= 0xB07B07B0u ? "bot " : "",
                            (unsigned long long)q & 0xFFFFFFFFFFFFull);
            h ^= q + o; h *= 1099511628211ull;
            ids++;
        }
    }
    h ^= column; h *= 1099511628211ull;
    if (h == g_cw_hash) return;                      // only when it changed
    g_cw_hash = h;
    if (InterlockedIncrement(&g_cw_lines) > 200) return;
    logf("%s", line);
}

static void __fastcall h_fill(uint8_t* page, uint8_t column) {
    __try {
        if (page) cw_log(page, column);
    } __except (EXCEPTION_EXECUTE_HANDLER) { logf("career: page unreadable"); }
    o_fill(page, column);
}

void career_watch_hooks() {
    uint8_t* mcc = (uint8_t*)GetModuleHandleW(nullptr);
    bool ok = false;
    __try { ok = !memcmp(mcc + CW_FILL, CW_FILL_HEAD, sizeof CW_FILL_HEAD); }
    __except (EXCEPTION_EXECUTE_HANDLER) { ok = false; }
    if (!ok) { logf("career: MCC build not the one decoded (Oct 31 2026): watch off"); return; }
    if (MH_CreateHook(mcc + CW_FILL, (void*)&h_fill, (void**)&o_fill) != MH_OK || MH_EnableHook(mcc + CW_FILL) != MH_OK) {
        logf("career: hook failed");
        return;
    }
    logf("career: watch on (logs the Career page's multiplayer stats when they change)");
}
