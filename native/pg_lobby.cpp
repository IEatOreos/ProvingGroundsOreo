// pg_lobby.cpp (custom, Nov 16): Project Reach's side of MCC's Halo: Reach custom game lobby (proving_grounds.h).
// The owner: "Yes, study it", "Yes, build the test", then "Build the entire thing start to finish Map voting and all".
// MCC-Win64-Shipping.exe (Oct 31 2026 file; static read with dumpbin, proved by three live runs of the lobby test,
// Nov 16: the third launched SLAYER on Sword Base from a lobby set to CTF on Boardwalk):
//  - the variant library [0x144001650], per title index (Halo: Reach 6): gametypes at +0x28 (FUN_14043DC94), maps at
//    +0x108 (FUN_14043DD10); a list's first node at +8 of its head, a node's next at +8, an entry's id at +0x1C, its kind
//    at +0x14 (1 built in, 2 shipped, 3 the player's, 4 the copy the session last used), a gametype's category at
//    +0x450, its game object at +0x3E8 (whose method +0x70 MCC's apply step reads, FUN_1404D4C8C: true for a team
//    game, checked here against SLAYER and CAPTURE THE FLAG), a map's content id (16 bytes) at +0x3E8; text records of
//    0x30 bytes from +0x28 (length +0x14, text +0x18): the name at +0x58, the picture names at +0xB8 and +0xE8;
//  - the MultiplayerCustomGame screen (vtable 0x1432BE1C0): +0x16C8 the title index, +0x16D0 the map, +0x16D4 the
//    gametype's category, +0x16D8 the gametype, +0x16E0 FUN_1404E1188(title, gametype), +0x16E8 the map's content id;
//    its Update (vtable +0x58, FUN_1404DECDC, each frame on MCC's UI thread), its Start (vtable +0x1B8,
//    FUN_1404DC994). MCC's Start tile (FUN_1404D7160) sets [0x144001658]+0x48 to the gametype's category, calls the
//    apply step, then Start unless the lobby's settings (FUN_14034CEF8(1)) say a countdown runs (FUN_14034D1E4).
// Everything here that touches MCC runs inside that Update: the library copied every 2 s, the pairing checks
// (FUN_14043E768(lib, title, map, gametype)) and the launch (the picks set as MCC's own picks set them, its apply step,
// its Start). Any byte mismatch (another MCC build) leaves MCC untouched and Project Reach says so.
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "third_party/minhook/include/MinHook.h"
#include "proving_grounds.h"

void logf(const char* fmt, ...);
int mcc_lobby_title();                           // overlay.cpp: the custom game lobby's title (5 Halo: Reach)

static const uintptr_t LT_UPDATE = 0x4DECDC, LT_START = 0x4DC994, LT_SCREEN_VT = 0x32BE1C0;
static const uintptr_t LT_LIB = 0x4001650, LT_HOST = 0x4001658;
static const uintptr_t LT_FIND_GT = 0x43DC94, LT_FIND_MAP = 0x43DD10, LT_GT_ENTRY = 0x4E1188;
static const uintptr_t LT_FITS = 0x43E768, LT_APPLY = 0x4D4C8C, LT_SETTINGS = 0x34CEF8, LT_COUNTING = 0x34D1E4;
static const uint8_t LT_UPDATE_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0x68, 0xA1, 0x48, 0x81, 0xEC, 0xA0};
static const uint8_t LT_START_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x57, 0x41, 0x54, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0x68, 0xA1, 0x48};
static const uint8_t LT_GT_ENTRY_HEAD[] = {0x48, 0x83, 0xEC, 0x28, 0x83, 0xFA, 0xFF, 0x75, 0x07, 0x33, 0xC0, 0x48, 0x83, 0xC4, 0x28, 0xC3};
// the library lookups: their list offsets ((index + 3) * 16, + 0x11) are the ones below
static const uint8_t LT_FIND_GT_HEAD[] = {0x45, 0x33, 0xD2, 0x83, 0xFA, 0x06, 0x77, 0x2F, 0x48, 0x63, 0xD2, 0x48, 0x8D, 0x42, 0x03, 0x48};
static const uint8_t LT_FIND_MAP_HEAD[] = {0x45, 0x33, 0xD2, 0x83, 0xFA, 0x06, 0x77, 0x32, 0x48, 0x63, 0xD2, 0x48, 0x8D, 0x42, 0x11, 0x48};
static const uint8_t LT_FITS_HEAD[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x6C, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18, 0x57};
static const uint8_t LT_APPLY_HEAD[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x6C, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18, 0x57};
static const uint8_t LT_SETTINGS_HEAD[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x20, 0x48, 0x8B, 0x15, 0x13, 0x46, 0xCB, 0x03, 0x8B, 0xD9, 0x48};
static const uint8_t LT_COUNTING_HEAD[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x20, 0x33, 0xDB, 0x39, 0x19, 0x75, 0x08, 0xFF, 0x15, 0xEA, 0xD3};
static const int LIST_GT = 0x28, LIST_MAP = 0x108;
static const int SCR_TITLE = 0x16C8, SCR_MAP = 0x16D0, SCR_CAT = 0x16D4, SCR_GT = 0x16D8, SCR_GT_ENTRY = 0x16E0,
                 SCR_MAP_ID = 0x16E8;
static const int HOST_CAT = 0x48, HOST_GT = 0x2C090, HOST_MAP = 0x2C094;
static const int MAX_ENTRIES = 160;

typedef void(__fastcall* update_fn)(uint8_t* screen, float dt);
typedef void(__fastcall* start_fn)(uint8_t* screen);
typedef void(__fastcall* apply_fn)(uint8_t* screen);
typedef uint8_t*(__fastcall* gt_entry_fn)(int title, int gametype);
typedef bool(__fastcall* fits_fn)(uint8_t* lib, int title, int map, int gametype);
typedef void*(__fastcall* settings_fn)(int which);
typedef bool(__fastcall* counting_fn)(void* settings);
typedef bool(__fastcall* teams_fn)(void* game);           // the game object's method +0x70

static update_fn o_update;
static start_fn o_start;
static uint8_t* g_mcc;
static bool g_ok;                                // the build is the one decoded, the hooks are in
static wchar_t g_bin[MAX_PATH];
static CRITICAL_SECTION g_lock;                  // the copy, the checks and the launch, between MCC's UI thread and ours
static volatile ULONGLONG g_live_at;             // MCC's Reach lobby ran its Update at this tick

static pg_entry g_maps[MAX_ENTRIES], g_gts[MAX_ENTRIES];
static int g_nmaps, g_ngts;
static volatile uint32_t g_seq;
static ULONGLONG g_copied_at;
static bool g_dumped;

static int g_check_ticket, g_check_done, g_check_n;
static int g_check_map[64], g_check_gt[64];
static uint8_t g_check_ok[64];

static int g_launch_state;                       // 0 none, 1 waiting, 2 started, -1 failed
static int g_launch_map, g_launch_gt;
static char g_launch_why[160];
static ULONGLONG g_launch_at;

// an entry's text record: narrow or wide, whichever reads as text; "" when neither does
static void entry_text(const uint8_t* e, int rec, char* out, int cap) {
    out[0] = 0;
    const uint8_t* p = e + rec;
    if (*(const uint32_t*)(p + 0x10) != 0x01020304) return;
    uint32_t n = *(const uint32_t*)(p + 0x14);
    const uint8_t* s = *(const uint8_t* const*)(p + 0x18);
    if (!n || n > 200 || !s) return;
    bool narrow = true;
    for (uint32_t i = 0; i < n && narrow; i++) narrow = s[i] >= 32 && s[i] != 127;
    if (narrow) {
        int k = (int)n < cap - 1 ? (int)n : cap - 1;
        memcpy(out, s, k);
        out[k] = 0;
        return;
    }
    const wchar_t* w = (const wchar_t*)s;
    for (uint32_t i = 0; i < n; i++) if (w[i] < 32) return;
    int k = WideCharToMultiByte(CP_UTF8, 0, w, (int)n, out, cap - 1, nullptr, nullptr);
    out[k > 0 ? k : 0] = 0;
}

static uint8_t* first(uint8_t* lib, int list, int t) { return *(uint8_t**)(lib + list + t * 16 + 8); }
static bool more(uint8_t* lib, int list, int t, uint8_t* node, int n) { return node && node != lib + list + t * 16 && n < 4000; }

static uint8_t* by_id(uint8_t* lib, int list, int t, int id) {
    int n = 0;
    for (uint8_t* e = first(lib, list, t); more(lib, list, t, e, n); e = *(uint8_t**)(e + 8), n++)
        if (*(int32_t*)(e + 0x1C) == id) return e;
    return nullptr;
}

static int game_teams(uint8_t* e) {              // the gametype's own "team game" (MCC's apply step reads it), -1 unread
    __try {
        void* game = *(void**)(e + 0x3E8);
        if (!game) return -1;
        teams_fn f = (teams_fn)(*(void***)game)[0x70 / 8];
        return f(game) ? 1 : 0;
    } __except (EXCEPTION_EXECUTE_HANDLER) { return -1; }
}

static void fill(pg_entry& p, uint8_t* e, bool gametype) {
    memset(&p, 0, sizeof p);
    p.id = *(int32_t*)(e + 0x1C);
    p.kind = *(int32_t*)(e + 0x14);
    p.category = gametype ? *(int32_t*)(e + 0x450) : -1;
    p.teams = gametype ? game_teams(e) : -1;
    entry_text(e, 0x58, p.name, sizeof p.name);
    entry_text(e, 0xE8, p.key, sizeof p.key);
}

static void dump(int t) {                        // native\bin\lobby_library.txt, once a session (the evidence)
    wchar_t path[MAX_PATH];
    swprintf_s(path, L"%s\\lobby_library.txt", g_bin);
    FILE* f = nullptr;
    if (_wfopen_s(&f, path, L"w") || !f) return;
    fprintf(f, "MCC's Halo: Reach variant library as Project Reach read it (pg_lobby.cpp), title index %d.\n"
               "kind: 1 built in, 2 shipped, 3 the player's. teams: 1 team game, 0 free for all, -1 not read.\n\n== maps\n", t);
    for (int i = 0; i < g_nmaps; i++) fprintf(f, "  #%d kind %d \"%s\" %s\n", g_maps[i].id, g_maps[i].kind, g_maps[i].name, g_maps[i].key);
    fprintf(f, "\n== gametypes (category, teams)\n");
    for (int i = 0; i < g_ngts; i++)
        fprintf(f, "  #%d kind %d category %d teams %d \"%s\" %s\n", g_gts[i].id, g_gts[i].kind, g_gts[i].category, g_gts[i].teams,
                g_gts[i].name, g_gts[i].key);
    fclose(f);
}

// the library's maps and gametypes, copied for the screens (MCC's thread); team flags kept only when MCC's own
// SLAYER reads free for all and its CAPTURE THE FLAG a team game (else -1: the screens use their own list)
static void copy_library(uint8_t* lib, int t) {
    pg_entry maps[MAX_ENTRIES], gts[MAX_ENTRIES];
    int nm = 0, ng = 0, n = 0;
    for (uint8_t* e = first(lib, LIST_MAP, t); more(lib, LIST_MAP, t, e, n) && nm < MAX_ENTRIES; e = *(uint8_t**)(e + 8), n++)
        if (*(int32_t*)(e + 0x14) != 4) fill(maps[nm++], e, false);
    n = 0;
    int slayer = -2, ctf = -2;
    for (uint8_t* e = first(lib, LIST_GT, t); more(lib, LIST_GT, t, e, n) && ng < MAX_ENTRIES; e = *(uint8_t**)(e + 8), n++) {
        if (*(int32_t*)(e + 0x14) == 4) continue;
        pg_entry& g = gts[ng++];
        fill(g, e, true);
        if (!strcmp(g.name, "SLAYER")) slayer = g.teams;
        if (!strcmp(g.name, "CAPTURE THE FLAG")) ctf = g.teams;
    }
    bool known = slayer == 0 && ctf == 1;
    if (!known) for (int i = 0; i < ng; i++) gts[i].teams = -1;
    EnterCriticalSection(&g_lock);
    memcpy(g_maps, maps, sizeof(pg_entry) * nm); g_nmaps = nm;
    memcpy(g_gts, gts, sizeof(pg_entry) * ng); g_ngts = ng;
    g_seq++;
    LeaveCriticalSection(&g_lock);
    if (!g_dumped) {
        g_dumped = true;
        int teams = 0;
        for (int i = 0; i < ng; i++) teams += gts[i].teams == 1;
        logf("proving grounds: MCC's library: %d maps, %d gametypes (%d team games; team flags %s)", nm, ng, teams,
             known ? "read" : "not read: the list's own");
        dump(t);
    }
}

static void answer_checks(uint8_t* lib, int t) {
    EnterCriticalSection(&g_lock);
    if (g_check_ticket != g_check_done) {
        for (int i = 0; i < g_check_n; i++) {
            bool ok = false;
            __try {
                ok = by_id(lib, LIST_MAP, t, g_check_map[i]) && by_id(lib, LIST_GT, t, g_check_gt[i]) &&
                     ((fits_fn)(g_mcc + LT_FITS))(lib, t, g_check_map[i], g_check_gt[i]);
            } __except (EXCEPTION_EXECUTE_HANDLER) { ok = false; }
            g_check_ok[i] = ok;
        }
        g_check_done = g_check_ticket;
    }
    LeaveCriticalSection(&g_lock);
}

static void fail(const char* why) {
    g_launch_state = -1;
    strcpy_s(g_launch_why, why);
    logf("proving grounds: launch failed: %s", why);
}

// the picks into the lobby as MCC's own map pick, gametype pick and Start tile set them, then its Start
static void launch(uint8_t* screen, uint8_t* lib, uint8_t* host, int t) {
    if (mcc_lobby_title() != 5) { fail("This lobby is not Halo: Reach's."); return; }
    void* settings = ((settings_fn)(g_mcc + LT_SETTINGS))(1);
    if (!settings) { fail("MCC's lobby settings were not there."); return; }
    if (((counting_fn)(g_mcc + LT_COUNTING))(settings)) { fail("MCC's lobby was already counting down."); return; }
    uint8_t* gt = by_id(lib, LIST_GT, t, g_launch_gt);
    uint8_t* map = by_id(lib, LIST_MAP, t, g_launch_map);
    if (!gt || !map) { fail("That map or gametype is no longer in MCC's lists."); return; }
    if (!((fits_fn)(g_mcc + LT_FITS))(lib, t, g_launch_map, g_launch_gt)) { fail("MCC says that gametype does not go on that map."); return; }
    *(int32_t*)(screen + SCR_MAP) = g_launch_map;
    memcpy(screen + SCR_MAP_ID, map + 0x3E8, 16);
    *(int32_t*)(screen + SCR_CAT) = *(int32_t*)(gt + 0x450);
    *(int32_t*)(screen + SCR_GT) = g_launch_gt;
    *(uint8_t**)(screen + SCR_GT_ENTRY) = ((gt_entry_fn)(g_mcc + LT_GT_ENTRY))(t, g_launch_gt);
    *(int32_t*)(host + HOST_CAT) = *(int32_t*)(gt + 0x450);
    ((apply_fn)(g_mcc + LT_APPLY))(screen);
    ((start_fn)(*(void***)screen)[0x1B8 / 8])(screen);   // (the screen's own Start: MCC's checks, its commit, its countdown)
    if (((counting_fn)(g_mcc + LT_COUNTING))(settings)) {
        g_launch_state = 2;
        g_launch_why[0] = 0;
        char m[64], g[64];
        entry_text(map, 0xE8, m, sizeof m);
        entry_text(gt, 0x58, g, sizeof g);
        logf("proving grounds: MCC's countdown started: map #%d (%s), gametype #%d (%s); host map #%d, gametype #%d",
             g_launch_map, m, g_launch_gt, g, *(int32_t*)(host + HOST_MAP), *(int32_t*)(host + HOST_GT));
    } else {
        fail("MCC did not start the game. Leave Project Reach to see any message its lobby shows.");
    }
}

static void tick(uint8_t* screen) {
    if (*(uint8_t**)screen != g_mcc + LT_SCREEN_VT) return;
    uint8_t* lib = *(uint8_t**)(g_mcc + LT_LIB);
    uint8_t* host = *(uint8_t**)(g_mcc + LT_HOST);
    int t = *(int32_t*)(screen + SCR_TITLE);
    if (!lib || !host || t < 0 || t > 6 || mcc_lobby_title() != 5) return;
    ULONGLONG now = GetTickCount64();
    bool back = !g_live_at || now - g_live_at > 1000;   // (Nov 16: the lobby back after a match: MCC's lists reloaded)
    g_live_at = now;
    if (back || !g_copied_at || now - g_copied_at > 2000) { g_copied_at = now; copy_library(lib, t); }
    answer_checks(lib, t);
    EnterCriticalSection(&g_lock);
    bool go = g_launch_state == 1;
    LeaveCriticalSection(&g_lock);
    if (go) {
        __try { launch(screen, lib, host, t); } __except (EXCEPTION_EXECUTE_HANDLER) { fail("MCC's lobby could not be read."); }
    }
}

static void __fastcall h_update(uint8_t* screen, float dt) {
    o_update(screen, dt);
    __try { tick(screen); } __except (EXCEPTION_EXECUTE_HANDLER) {
        static int told;
        if (told++ < 3) logf("proving grounds: lobby unreadable this frame");
    }
}

// (the lobby's Start, whoever pressed it: logged, for the evidence)
static void __fastcall h_start(uint8_t* screen) {
    __try {
        uint8_t* host = *(uint8_t**)(g_mcc + LT_HOST);
        if (*(uint8_t**)screen == g_mcc + LT_SCREEN_VT && host)
            logf("proving grounds: lobby Start: screen map #%d, gametype #%d, category %d", *(int32_t*)(screen + SCR_MAP),
                 *(int32_t*)(screen + SCR_GT), *(int32_t*)(screen + SCR_CAT));
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
    o_start(screen);
}

// ---- the screens' side (any thread)
bool pg_lobby_live() { return g_ok && g_live_at && GetTickCount64() - g_live_at < 500; }

int pg_lobby_maps(pg_entry* out, int cap) {
    if (!g_ok) return 0;
    EnterCriticalSection(&g_lock);
    int n = g_nmaps < cap ? g_nmaps : cap;
    memcpy(out, g_maps, sizeof(pg_entry) * n);
    LeaveCriticalSection(&g_lock);
    return n;
}
int pg_lobby_gametypes(pg_entry* out, int cap) {
    if (!g_ok) return 0;
    EnterCriticalSection(&g_lock);
    int n = g_ngts < cap ? g_ngts : cap;
    memcpy(out, g_gts, sizeof(pg_entry) * n);
    LeaveCriticalSection(&g_lock);
    return n;
}
uint32_t pg_lobby_seq() { return g_ok ? g_seq : 0; }

int pg_lobby_check(const int* map, const int* gametype, int n) {
    if (!g_ok) return 0;
    if (n > 64) n = 64;
    EnterCriticalSection(&g_lock);
    for (int i = 0; i < n; i++) { g_check_map[i] = map[i]; g_check_gt[i] = gametype[i]; }
    g_check_n = n;
    int t = ++g_check_ticket;
    LeaveCriticalSection(&g_lock);
    return t;
}
bool pg_lobby_checked(int ticket, uint8_t* ok, int n) {
    if (!g_ok) return false;
    EnterCriticalSection(&g_lock);
    bool done = ticket && g_check_done == ticket;
    if (done) for (int i = 0; i < n && i < g_check_n; i++) ok[i] = g_check_ok[i];
    LeaveCriticalSection(&g_lock);
    return done;
}

void pg_lobby_launch(int map, int gametype) {
    if (!g_ok) return;
    EnterCriticalSection(&g_lock);
    g_launch_map = map; g_launch_gt = gametype;
    g_launch_state = 1;
    g_launch_why[0] = 0;
    g_launch_at = GetTickCount64();
    LeaveCriticalSection(&g_lock);
}
int pg_lobby_launch_state(char* why, int cap) {
    if (!g_ok) { if (why) strcpy_s(why, cap, "This MCC build is not the one Project Reach was made for."); return -1; }
    EnterCriticalSection(&g_lock);
    int s = g_launch_state;
    if (why) strcpy_s(why, cap, g_launch_why);
    LeaveCriticalSection(&g_lock);
    return s;
}

void lobby_test_hooks() {                        // (session_watch.cpp calls it at start; the name kept)
    InitializeCriticalSection(&g_lock);
    g_mcc = (uint8_t*)GetModuleHandleW(nullptr);
    HMODULE me = nullptr;
    if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCWSTR)&lobby_test_hooks, &me)) {
        DWORD n = GetModuleFileNameW(me, g_bin, MAX_PATH);
        wchar_t* slash = n && n < MAX_PATH ? wcsrchr(g_bin, L'\\') : nullptr;
        if (slash) *slash = 0;
    }
    bool ok = false;
    __try {
        ok = !memcmp(g_mcc + LT_UPDATE, LT_UPDATE_HEAD, sizeof LT_UPDATE_HEAD) &&
             !memcmp(g_mcc + LT_START, LT_START_HEAD, sizeof LT_START_HEAD) &&
             !memcmp(g_mcc + LT_GT_ENTRY, LT_GT_ENTRY_HEAD, sizeof LT_GT_ENTRY_HEAD) &&
             !memcmp(g_mcc + LT_FIND_GT, LT_FIND_GT_HEAD, sizeof LT_FIND_GT_HEAD) &&
             !memcmp(g_mcc + LT_FIND_MAP, LT_FIND_MAP_HEAD, sizeof LT_FIND_MAP_HEAD) &&
             !memcmp(g_mcc + LT_FITS, LT_FITS_HEAD, sizeof LT_FITS_HEAD) &&
             !memcmp(g_mcc + LT_APPLY, LT_APPLY_HEAD, sizeof LT_APPLY_HEAD) &&
             !memcmp(g_mcc + LT_SETTINGS, LT_SETTINGS_HEAD, sizeof LT_SETTINGS_HEAD) &&
             !memcmp(g_mcc + LT_COUNTING, LT_COUNTING_HEAD, sizeof LT_COUNTING_HEAD) &&
             *(uint8_t**)(g_mcc + LT_SCREEN_VT + 0x58) == g_mcc + LT_UPDATE &&   // (that screen's Update and Start)
             *(uint8_t**)(g_mcc + LT_SCREEN_VT + 0x1B8) == g_mcc + LT_START;
    } __except (EXCEPTION_EXECUTE_HANDLER) { ok = false; }
    if (!ok) { logf("proving grounds: MCC build not the one decoded (Oct 31 2026): off"); return; }
    if (MH_CreateHook(g_mcc + LT_UPDATE, (void*)&h_update, (void**)&o_update) != MH_OK ||
        MH_CreateHook(g_mcc + LT_START, (void*)&h_start, (void**)&o_start) != MH_OK ||
        MH_EnableHook(g_mcc + LT_UPDATE) != MH_OK || MH_EnableHook(g_mcc + LT_START) != MH_OK) {
        logf("proving grounds: lobby hooks failed: off");
        return;
    }
    g_ok = true;
    logf("proving grounds: on MCC's Halo: Reach custom game lobby (its Update and Start)");
}
