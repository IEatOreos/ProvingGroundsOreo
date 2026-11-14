// (custom, Nov 13) A bot's numbers on MCC's Career page (Player Details > Career > Multiplayer). The owner: "can we
// just fake their stats? What can that hurt?", then "Yes, build it". A bot's page showed zeros: MCC finds no stats
// for its made-up id. Nothing is sent anywhere: only the text MCC is about to draw on a bot's page is changed.
// MCC-Win64-Shipping.exe (Oct 31 2026 file; static read, dumpbin):
//  - FUN_1404A0EA4(page) fills the Multiplayer tab (and the summary of it): the shown player's id is page +0x16F0,
//    its stats come from FUN_14024B924(session, id, set, out) (MCC's player records, FUN_1402483F0: none for a bot);
//    then each row (FUN_1404A342C) by its stat code at row +0x200: 0x0EC28B21 games won, 0x6AD86331 kills, 0x75D204D0
//    deaths, 0x539C9E21 assists (the $SR_TOTAL_ labels FUN_1404A0CC4 builds them with);
//  - FUN_140318E94(row, text) sets the row's number: it copies the text (an MCC string: +0x14 its length, +0x18 its
//    bytes) into the row with MCC's own copy (FUN_1405A2868), and reads nothing else of it.
// So, while FUN_1404A0EA4 fills a bot's page (thread-local), the number text of those four rows is the bot's own, from
// native/bin/career/totals.txt (tools/bot_career.py: MCC's post-game reports of the matches played with it; read
// again when the file changes). "Compared to you" is MCC's own (your numbers). Matchmaking and Custom Games show the
// same numbers (a bot plays custom games only). A first try hooked FUN_140527A50 (another stats screen): it never ran
// for this page. Any byte mismatch (another MCC build) leaves MCC untouched.
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include "third_party/minhook/include/MinHook.h"

void logf(const char* fmt, ...);
bool report_bot_name(uint64_t xuid, char* out, int cap);   // report.cpp

static const uintptr_t CR_FILL = 0x4A0EA4, CR_TEXT = 0x318E94;
static const uint8_t CR_FILL_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D,
                                       0xA8, 0x58, 0xFE, 0xFF, 0xFF, 0x48, 0x81, 0xEC, 0x80, 0x02, 0x00, 0x00};
static const uint8_t CR_TEXT_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0x68, 0xA1, 0x48, 0x81,
                                       0xEC, 0xB0, 0x00, 0x00, 0x00};
// (FUN_1404A0EA4 +0x2B2: mov rdx,[rbx+16F0h]; FUN_140318E94 +0x43: mov r8d,[rdx+14h]; mov rdx,[rdx+18h])
static const uintptr_t CR_ID_AT = 0x4A1156, CR_LEN_AT = 0x318ED7;
static const uint8_t CR_ID_BYTES[] = {0x48, 0x8B, 0x93, 0xF0, 0x16, 0x00, 0x00};
static const uint8_t CR_LEN_BYTES[] = {0x44, 0x8B, 0x42, 0x14, 0x48, 0x8B, 0x52, 0x18};
enum { CR_WON, CR_KILLS, CR_DEATHS, CR_ASSISTS, CR_STATS };
static const uint32_t CR_CODE[CR_STATS] = {0x0EC28B21u, 0x6AD86331u, 0x75D204D0u, 0x539C9E21u};

typedef void(__fastcall* fill_fn)(uint8_t* page);
typedef void(__fastcall* text_fn)(uint8_t* row, const uint8_t* text);
static fill_fn o_fill;
static text_fn o_text;

struct cr_player { char name[32]; long long n[CR_STATS]; };
static cr_player* g_players;                     // totals.txt (read on the UI thread only)
static int g_count;
static FILETIME g_stamp;
static ULONGLONG g_checked;
static __declspec(thread) const cr_player* t_bot;   // the bot whose page FUN_1404A0EA4 is filling (this thread)
static char g_text[CR_STATS][32];                // the texts handed to MCC (MCC copies them; kept for good measure)

static void totals_path(wchar_t* out, int cap) {
    out[0] = 0;
    HMODULE me = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            (LPCWSTR)&totals_path, &me))
        return;
    DWORD n = GetModuleFileNameW(me, out, cap);
    if (!n || n >= (DWORD)cap) { out[0] = 0; return; }
    wchar_t* slash = wcsrchr(out, L'\\');
    if (!slash) { out[0] = 0; return; }
    wcscpy_s(slash + 1, cap - (slash + 1 - out), L"career\\totals.txt");
}

// totals.txt again when it changed (looked at once a second at most)
static void totals_load() {
    ULONGLONG now = GetTickCount64();
    if (g_checked && now - g_checked < 1000) return;
    g_checked = now;
    wchar_t p[MAX_PATH];
    totals_path(p, MAX_PATH);
    WIN32_FILE_ATTRIBUTE_DATA a;
    if (!p[0] || !GetFileAttributesExW(p, GetFileExInfoStandard, &a)) return;
    if (!CompareFileTime(&a.ftLastWriteTime, &g_stamp) && g_players) return;
    FILE* f = nullptr;
    if (_wfopen_s(&f, p, L"r, ccs=UTF-8") != 0 || !f) return;
    int cap = 64, n = 0;
    cr_player* list = (cr_player*)malloc(sizeof(cr_player) * cap);
    wchar_t wl[256];
    while (list && fgetws(wl, 256, f)) {
        char line[512];
        WideCharToMultiByte(CP_UTF8, 0, wl, -1, line, sizeof line, nullptr, nullptr);
        char* tab = strchr(line, '\t');
        if (!tab) continue;
        *tab = 0;
        long long games = 0, v[CR_STATS] = {};
        if (sscanf_s(tab + 1, "%lld %lld %lld %lld %lld", &games, &v[CR_WON], &v[CR_KILLS], &v[CR_DEATHS],
                     &v[CR_ASSISTS]) != 5)
            continue;
        if (n == cap) {
            cr_player* more = (cr_player*)realloc(list, sizeof(cr_player) * cap * 2);
            if (!more) break;
            list = more;
            cap *= 2;
        }
        strncpy_s(list[n].name, line, _TRUNCATE);
        memcpy(list[n].n, v, sizeof v);
        n++;
    }
    fclose(f);
    cr_player* old = g_players;
    g_players = list;
    g_count = list ? n : 0;
    g_stamp = a.ftLastWriteTime;
    free(old);
    static int told = -1;
    if (told != g_count) { told = g_count; logf("career: %d players' totals read (bots' Career pages)", g_count); }
}

static const cr_player* find(const char* name) {
    for (int i = 0; i < g_count; i++)
        if (!strcmp(g_players[i].name, name)) return &g_players[i];
    return nullptr;
}

// 25045 -> "25,045", as MCC shows its numbers
static void with_commas(long long v, char* out, int cap) {
    char d[32];
    sprintf_s(d, "%lld", v < 0 ? -v : v);
    int len = (int)strlen(d), at = 0;
    if (v < 0 && at < cap - 1) out[at++] = '-';
    for (int i = 0; i < len && at < cap - 1; i++) {
        if (i && (len - i) % 3 == 0 && at < cap - 2) out[at++] = ',';
        out[at++] = d[i];
    }
    out[at] = 0;
}

static void __fastcall h_fill(uint8_t* page) {
    const cr_player* bot = nullptr;
    __try {
        char name[32];
        totals_load();
        if (page && report_bot_name(*(const uint64_t*)(page + 0x16F0), name, sizeof name)) {
            bot = find(name);
            static char told[32];
            if (strcmp(told, name)) {
                strcpy_s(told, name);
                logf("career: %s's page%s", name, bot ? "" : " (no matches with it yet: MCC's zeros)");
            }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) { bot = nullptr; }
    const cr_player* was = t_bot;
    t_bot = bot;
    o_fill(page);
    t_bot = was;
}

static void __fastcall h_text(uint8_t* row, const uint8_t* text) {
    const cr_player* bot = t_bot;
    if (bot && row && text) {
        int k = -1;
        __try {
            uint32_t code = *(const uint32_t*)(row + 0x200);
            for (int i = 0; i < CR_STATS; i++)
                if (code == CR_CODE[i]) k = i;
        } __except (EXCEPTION_EXECUTE_HANDLER) { k = -1; }
        if (k >= 0) {
            with_commas(bot->n[k], g_text[k], sizeof g_text[k]);
            uint8_t copy[0x30];                       // MCC's string, its length and bytes the bot's number
            memcpy(copy, text, sizeof copy);
            *(int32_t*)(copy + 0x14) = (int32_t)strlen(g_text[k]);
            *(const char**)(copy + 0x18) = g_text[k];
            o_text(row, copy);
            return;
        }
    }
    o_text(row, text);
}

void career_hooks() {
    uint8_t* mcc = (uint8_t*)GetModuleHandleW(nullptr);
    bool ok = false;
    __try {
        ok = !memcmp(mcc + CR_FILL, CR_FILL_HEAD, sizeof CR_FILL_HEAD) &&
             !memcmp(mcc + CR_TEXT, CR_TEXT_HEAD, sizeof CR_TEXT_HEAD) &&
             !memcmp(mcc + CR_ID_AT, CR_ID_BYTES, sizeof CR_ID_BYTES) &&
             !memcmp(mcc + CR_LEN_AT, CR_LEN_BYTES, sizeof CR_LEN_BYTES);
    } __except (EXCEPTION_EXECUTE_HANDLER) { ok = false; }
    if (!ok) { logf("career: MCC build not the one decoded (Oct 31 2026): bots' Career numbers off"); return; }
    if (MH_CreateHook(mcc + CR_FILL, (void*)&h_fill, (void**)&o_fill) != MH_OK ||
        MH_CreateHook(mcc + CR_TEXT, (void*)&h_text, (void**)&o_text) != MH_OK ||
        MH_EnableHook(mcc + CR_FILL) != MH_OK || MH_EnableHook(mcc + CR_TEXT) != MH_OK) {
        logf("career: hooks failed");
        return;
    }
    logf("career: bots' Career numbers on (games won, kills, deaths, assists from native\\bin\\career\\totals.txt)");
}
