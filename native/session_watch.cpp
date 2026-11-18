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
// (custom, Nov 13, the owner: "Instant refresh first") Live, Wheezy came up under MY GAME SESSION (with the player,
// above the friends; MCC's clan tag, nameplate and rank) but only some 90 s in: MCC sends the list only when something
// changes (that time, the friend's status). Now, in the menus, when the bot on MCC's last list is not the one wanted, the
// mod asks MCC for a new list with MCC's own request, FUN_14024E458(session [0x144000D08], urgent 0): it stamps the
// session's +0x1D8 (and +0x1E0 when urgent), and MCC's own session update (FUN_140246070, its +0xBFB) sends the list
// on its own thread a moment later. The UI roster system asks the same way (its +0xA0). Once a second at most, 3 s
// apart, 5 tries for each change.
// (custom, Nov 13, the owner: "Yes add all the bots", up to 15) Every bot in the lobby now, in roster order, ids
// 0xB07B07B1000000<place> (report.cpp's own lobby table, so a finished match's post-game rows keep their names).
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
void report_note_lobby_bot(int index, const char* name, int team, int tier);   // report.cpp

static const uintptr_t SW_NOTIFY = 0x24E4B0, SW_ROSTER = 0x2F4E84, SW_ROSTER_AT = 0x24ED27;
static const uintptr_t SW_NEW = 0x9300F4, SW_DESC = 0x24F054;
static const uint8_t SW_NEW_HEAD[] = {0x33, 0xD2, 0xE9};                // (xor edx,edx; jmp: MCC's allocator)
static const uint8_t SW_DESC_HEAD[] = {0x48, 0x8B, 0xC4, 0x48, 0x89, 0x48, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x30};
static const uintptr_t SW_REQUEST = 0x24E458, SW_SESSION = 0x4000D08;   // MCC's "send the list again", its session
static const uint8_t SW_REQUEST_HEAD[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x30};
static const uint8_t SW_REQUEST_STAMP[] = {0x48, 0x83, 0xB9, 0xD8, 0x01, 0x00, 0x00, 0x00};   // at +0x23: cmp [rcx+1D8h],0
static const uint64_t SW_LOBBY_ID = 0xB07B07B100000000ull;              // + its place (report.cpp's lobby rows)
static const int SW_LOBBY_ROWS = 16;                                            // report.cpp's lobby rows
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
static bool g_request_ok;                        // MCC's list request is the one decoded
static uint64_t g_added;                         // the bots last added (a hash: logged when it changes)
static volatile uint64_t g_listed;               // the bots on the last list MCC sent (a hash; 0 none)

// (Nov 13, "Yes add all the bots", up to 15) every bot in the lobby: the roster holds up to 15 (the game's 16
// players), so the list holds up to 16 with the player
struct sw_want { int n; char name[SW_LOBBY_ROWS][16]; int team[SW_LOBBY_ROWS], tier[SW_LOBBY_ROWS]; bool emb[SW_LOBBY_ROWS]; };
bool report_lobby_emblem(const char* name, int32_t out[5]);   // report.cpp: its emblem's numbers are there

// the bots wanted on the list: the lobby's, in the menus, with bots on; their hash (0 none)
static uint64_t wanted_bots(sw_want& w) {
    w.n = 0;
    if (!g_add_ok || g_sessionbots < 1 || g_sessionbots > 2 || mcc_menu_state() != 0 || !g_shm || !g_shm->bots_enabled ||
        g_shm->lidar_mode)
        return 0;
    const hb_roster& R = hb_panel_firefight ? g_ff_roster : g_roster;
    uint64_t h = 1469598103934665603ull;
    for (int k = 0; k < R.n && k < HB_ROSTER_MAX && w.n < SW_LOBBY_ROWS; k++) {
        strncpy_s(w.name[w.n], R.bot[k].name, _TRUNCATE);
        if (!w.name[w.n][0]) continue;
        w.team[w.n] = R.bot[k].team;
        w.tier[w.n] = R.bot[k].tier;
        for (const char* c = w.name[w.n]; *c; c++) { h ^= (uint8_t)*c; h *= 1099511628211ull; }
        h ^= 0x100u + (uint32_t)w.team[w.n]; h *= 1099511628211ull;
        h ^= 0x200u + (uint32_t)w.tier[w.n]; h *= 1099511628211ull;   // (its badge: its difficulty's rank)
        int32_t e[5];
        w.emb[w.n] = report_lobby_emblem(w.name[w.n], e);             // (its emblem: a new list once it is there)
        h ^= 0x300u + (uint32_t)w.emb[w.n]; h *= 1099511628211ull;
        w.n++;
    }
    return w.n ? h : 0;
}

// the lobby's bots onto the list's end, in the menus only (sessionbots=1 or 2), as MCC adds people: each in a node
// from MCC's own builder, id 0xB07B07B1000000<its place> (report.cpp's lobby rows answer for it)
static void add_lobby_bots(uint8_t* msg) {
    sw_want w;
    uint64_t want = wanted_bots(w);
    if (!w.n) return;
    uint8_t* head = msg + 0x38;
    bool on[SW_LOBBY_ROWS] = {};
    int n = 0;
    uint8_t* me = nullptr;                                // the player's own node (+0x10 set)
    for (uint8_t* node = *(uint8_t**)(msg + 0x40); node && node != head && n < 40; node = *(uint8_t**)(node + 8), n++) {
        uint64_t id = *(uint64_t*)(node + 0x18);
        if ((id & ~0xFFull) == SW_LOBBY_ID && (id & 0xFF) < SW_LOBBY_ROWS) on[id & 0xFF] = true;   // (already on it)
        if (node[0x10] && !me) me = node;
    }
    if (!n || !me) return;                                // (no player yet: not a lobby's list)
    int added = 0;
    for (int i = 0; i < w.n; i++) {
        if (on[i]) continue;
        report_note_lobby_bot(i, w.name[i], w.team[i], w.tier[i]);   // (MCC's lookups by its id: report.cpp)
        wchar_t ws[16];
        int k = MultiByteToWideChar(CP_UTF8, 0, w.name[i], -1, ws, 16);
        if (k < 2) continue;
        sw_wstr s = {ws, 0, (uint64_t)(k - 1), 8};
        uint8_t* node = (uint8_t*)((new_fn)(g_mcc + SW_NEW))(0x80);
        if (!node) break;
        memset(node, 0, 0x80);
        ((desc_fn)(g_mcc + SW_DESC))(node, SW_LOBBY_ID | (uint64_t)i, &s, nullptr, 0, 0, -1, -1, -1, 0);
        if (g_sessionbots == 2) {
            // (Nov 13, live: a friend only on the friends list came as flags 00000000 01, numbers -1, -1, -1; the
            // player as 01010101 0001, numbers 0, -1, 0) mode 2: the player's two "in this session" flags (+0x11,
            // +0x12) and +0x15, +0x64 its team (the player's 0 on Red: a guess), +0x6C the player's
            node[0x11] = me[0x11]; node[0x12] = me[0x12]; node[0x15] = me[0x15];
            *(int32_t*)(node + 0x64) = w.team[i];
            *(int32_t*)(node + 0x6C) = *(int32_t*)(me + 0x6C);
        }
        uint8_t* last = *(uint8_t**)head;                 // at the end, as MCC adds them
        *(uint8_t**)(last + 8) = node;
        *(uint8_t**)node = last;
        *(uint8_t**)(node + 8) = head;
        *(uint8_t**)head = node;
        added++;
    }
    g_listed = want;
    if (added && want != g_added) {
        g_added = want;
        char names[400];
        int at = 0;
        names[0] = 0;
        for (int i = 0; i < w.n && at < (int)sizeof names - 24; i++)
            at += sprintf_s(names + at, sizeof names - at, "%s%s (%d)", i ? ", " : "", w.name[i], w.team[i]);
        logf("session list: added %d bots, mode %u: %s", added, g_sessionbots, names);
    }
}

// (custom, Nov 16) the person's own name, from MCC's list (their node: +0x10 set), for Proving Grounds' lobby rows
static char g_me_name[64];
static volatile uint64_t g_me_id;                // (Nov 17) their id (+0x18): report.cpp keeps their emblem and nameplate
const char* mcc_player_name() { return g_me_name; }
uint64_t mcc_player_id() { return g_me_id; }

// (custom, Nov 17, the owner: a friend in the lobby, "balance him to a team like normal matchmaking would") the other
// people in the session, for Proving Grounds. From the logs of real lobbies (two friends who joined, two only on
// the friends list): a person in the session has +0x12 and +0x13 set (the player 01 01 01 01 00 01, a joined
// friend 00 00 01 01 01, a friends-list entry only +0x14); +0x6C is the team (the player 0, a friend MCC put on Blue 1,
// and in a match's list each bot its own team: 0, 1, 1 as dealt; -1 not yet set); +0x64 the machine (the host 0, a
// friend 1). Bots (ids 0xB07B07B0... in a match, 0xB07B07B1... the mod's lobby rows) are never people. Kept from the
// last list that holds the player (the list as a match loads holds no one: it changes nothing)
static const int SW_PEOPLE = 8;
struct sw_person { uint64_t id; char name[32]; int team; };
static SRWLOCK g_people_lock = SRWLOCK_INIT;
static sw_person g_people[SW_PEOPLE];
static int g_npeople, g_me_team = -1;
static bool is_bot_id(uint64_t id) { return (id & 0xFFFFFFF000000000ull) == 0xB07B07B000000000ull; }
int mcc_player_team() {
    AcquireSRWLockShared(&g_people_lock);
    int t = g_me_team;
    ReleaseSRWLockShared(&g_people_lock);
    return t;
}
int mcc_session_people(uint64_t* ids, char (*names)[32], int* teams, int cap) {
    AcquireSRWLockShared(&g_people_lock);
    int n = g_npeople < cap ? g_npeople : cap;
    for (int i = 0; i < n; i++) {
        if (ids) ids[i] = g_people[i].id;
        if (names) strcpy_s(names[i], 32, g_people[i].name);
        if (teams) teams[i] = g_people[i].team;
    }
    ReleaseSRWLockShared(&g_people_lock);
    return n;
}
bool mcc_session_has(uint64_t id) {                     // (report.cpp: their emblem and nameplate kept too)
    AcquireSRWLockShared(&g_people_lock);
    bool in = false;
    for (int i = 0; i < g_npeople && !in; i++) in = g_people[i].id == id;
    ReleaseSRWLockShared(&g_people_lock);
    return in;
}

static void note_me(const uint8_t* msg) {
    const uint8_t* head = msg + 0x38;
    int n = 0, me_team = -1;
    bool me = false;
    sw_person people[SW_PEOPLE];
    int np = 0;
    for (const uint8_t* node = *(const uint8_t* const*)(msg + 0x40); node && node != head && n < 40;
         node = *(const uint8_t* const*)(node + 8), n++) {
        uint64_t id = *(const uint64_t*)(node + 0x18);
        if (node[0x10]) {
            if (me) continue;
            me = true;
            char a[64];
            wstr(node + 0x20, a, sizeof a);
            if (a[0] && a[0] != '?') strcpy_s(g_me_name, a);
            if (id && !is_bot_id(id)) g_me_id = id;
            me_team = *(const int32_t*)(node + 0x6C);
        } else if (node[0x12] && node[0x13] && id && !is_bot_id(id) && np < SW_PEOPLE) {
            sw_person& p = people[np];
            p.id = id;
            wstr(node + 0x20, p.name, sizeof p.name);
            if (!p.name[0] || p.name[0] == '?') strcpy_s(p.name, "Player");
            int t = *(const int32_t*)(node + 0x6C);
            p.team = t >= 0 && t < 8 ? t : -1;
            np++;
        }
    }
    if (!me) return;                                      // (not a list with the player in it: nothing learnt)
    AcquireSRWLockExclusive(&g_people_lock);
    bool changed = np != g_npeople || (me_team >= 0 && me_team < 8 ? me_team : -1) != g_me_team;
    for (int i = 0; i < np && !changed; i++)
        changed = people[i].id != g_people[i].id || people[i].team != g_people[i].team;
    memcpy(g_people, people, sizeof(sw_person) * np);
    g_npeople = np;
    g_me_team = me_team >= 0 && me_team < 8 ? me_team : -1;
    ReleaseSRWLockExclusive(&g_people_lock);
    if (changed && InterlockedIncrement(&g_lines) <= 400) {
        char s[400];
        int at = sprintf_s(s, "session list: people: you on team %d", g_me_team);
        for (int i = 0; i < np && at < 340; i++) at += sprintf_s(s + at, sizeof s - at, ", %s on team %d", people[i].name, people[i].team);
        logf("%s", s);
    }
}

static void __fastcall h_roster(void* mgr, uint8_t* msg) {
    __try {
        if (msg && *(const uint32_t*)(msg + 0x28) == SW_MSG_ID) {
            g_listed = 0;
            note_me(msg);
            add_lobby_bots(msg);
            log_members(msg);
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) { logf("session list: unreadable"); }
    o_roster(mgr, msg);
}

// (Nov 13, the bots' emblems) the lobby bots whose emblem numbers are not there yet, asked of brain/looks.py in the
// background (tools/looks_export.py --emblems: native\bin\emblems\<name>.ids, the emblem a match sends for it), 20 s
// apart at most; a name asked three times is not asked again
void hb_python(const wchar_t* root, wchar_t* out, size_t cap);   // bots_panel.cpp
static void ask_emblems(const sw_want& w) {
    static ULONGLONG asked;
    static char tried[64][16];
    static int tries[64], ntried;
    ULONGLONG now = GetTickCount64();
    if (asked && now - asked < 20000) return;
    wchar_t bin[MAX_PATH], root[MAX_PATH], py[MAX_PATH + 2];
    HMODULE me = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            (LPCWSTR)&ask_emblems, &me))
        return;
    DWORD n = GetModuleFileNameW(me, bin, MAX_PATH);
    wchar_t* slash = n && n < MAX_PATH ? wcsrchr(bin, L'\\') : nullptr;
    if (!slash) return;
    *slash = 0;                                               // native\bin
    wcscpy_s(root, bin);
    wchar_t* s = wcsstr(root, L"\\native\\bin");
    if (!s) return;
    *s = 0;                                                   // the repo
    wchar_t cmd[2048];
    hb_python(root, py, MAX_PATH + 2);
    int at = swprintf_s(cmd, L"%s -I \"%s\\tools\\looks_export.py\" --emblems \"%s\\bot_profiles.ini\"", py, root, bin);
    int names = 0;
    for (int i = 0; i < w.n && at > 0 && at < 1900; i++) {
        if (w.emb[i] || strchr(w.name[i], '"')) continue;
        int t = 0;
        while (t < ntried && strcmp(tried[t], w.name[i])) t++;
        if (t == ntried) {
            if (ntried == 64) continue;
            strcpy_s(tried[ntried], w.name[i]);
            tries[ntried++] = 0;
        }
        if (tries[t] >= 3) continue;
        tries[t]++;
        wchar_t wn[40];
        MultiByteToWideChar(CP_UTF8, 0, w.name[i], -1, wn, 40);
        at += swprintf_s(cmd + at, 2048 - at, L" \"%s\"", wn);
        names++;
    }
    if (!names || at <= 0) return;
    asked = now;
    STARTUPINFOW si{}; si.cb = sizeof si;
    PROCESS_INFORMATION pi{};
    if (CreateProcessW(nullptr, cmd, nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi)) {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        if (InterlockedIncrement(&g_lines) <= 400) logf("session list: asked for %d bots' emblems", names);
    }
}

// once a second: when the bot on MCC's last list is not the one wanted, MCC's own request for a new list
typedef void(__fastcall* request_fn)(void* session, uint8_t urgent);
static void refresh_tick() {
    static uint64_t want_was;
    static int tries;
    static ULONGLONG asked;
    sw_want w;
    uint64_t want = wanted_bots(w);
    if (w.n) ask_emblems(w);
    if (mcc_menu_state() != 0) g_listed = 0;              // (the next lobby gets a new list)
    if (want != want_was) { want_was = want; tries = 0; }
    if (want == g_listed || tries >= 5) return;
    ULONGLONG now = GetTickCount64();
    if (now - asked < 3000) return;
    void* session = *(void**)(g_mcc + SW_SESSION);
    if (!session) return;
    asked = now;
    if (!tries++ && InterlockedIncrement(&g_lines) <= 400)
        logf("session list: asked MCC for a new list (%d bots wanted)", w.n);
    ((request_fn)(g_mcc + SW_REQUEST))(session, 0);
}

static DWORD WINAPI refresh_thread(void*) {
    for (;;) {
        Sleep(1000);
        __try { refresh_tick(); } __except (EXCEPTION_EXECUTE_HANDLER) {}
    }
    return 0;
}

void career_hooks();                             // career.cpp (Nov 13: the bots' numbers on MCC's Career page)

void lobby_test_hooks();                         // lobby_test.cpp (Nov 16: Proving Grounds, the lobby's own picks)

void session_watch_hooks() {
    career_hooks();
    lobby_test_hooks();
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
    __try {
        g_request_ok = !memcmp(g_mcc + SW_REQUEST, SW_REQUEST_HEAD, sizeof SW_REQUEST_HEAD) &&
                       !memcmp(g_mcc + SW_REQUEST + 0x23, SW_REQUEST_STAMP, sizeof SW_REQUEST_STAMP);
    } __except (EXCEPTION_EXECUTE_HANDLER) { g_request_ok = false; }
    logf("session list: watch on (logs MCC's session players when they change); the lobby's bots %s%s", !g_add_ok
         ? "off (not the builder decoded)" : g_sessionbots == 1 ? "added (sessionbots=1, as a plain entry)"
         : g_sessionbots == 2 ? "added (sessionbots=2, with the player's session flags)" : "off (sessionbots=0)",
         g_add_ok && g_sessionbots ? g_request_ok ? ", MCC asked for the list at once" : ", not asked (request not decoded)" : "");
    if (g_add_ok && g_request_ok && g_sessionbots) {
        HANDLE t = CreateThread(nullptr, 0, refresh_thread, nullptr, 0, nullptr);
        if (t) CloseHandle(t);
    }
}
