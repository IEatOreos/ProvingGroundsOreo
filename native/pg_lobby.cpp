// pg_lobby.cpp (custom, Nov 16): Project Noble's side of MCC's Halo: Reach custom game lobby (proving_grounds.h).
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
// its Start). Any byte mismatch (another MCC build) leaves MCC untouched and Project Noble says so.
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
    fprintf(f, "MCC's Halo: Reach variant library as Project Noble read it (pg_lobby.cpp), title index %d.\n"
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
        fail("MCC did not start the game. Leave Project Noble to see any message its lobby shows.");
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

// ---- (Nov 23, the owner: the other lobbies "full, like Custom"; Firefight after Theater) MCC's Firefight custom game
// lobby (static read with Ghidra, Nov 23; not yet proved live): the registry's "FirefightCustomGame" (factory 0x14329AA50,
// create FUN_14031F4D8) is the custom game lobby's own class (its constructor FUN_1404D3D7C, 0x1860 bytes) with the
// vtable 0x1432BE518: the same Update (FUN_1404DECDC, hooked above), the same fields (+0x16C8 the title index, +0x16D8 the
// gametype, +0x16E0 FUN_1404E1188(title, gametype), +0x16E8 the map's content id) and +0x1840 the difficulty (a byte;
// its commit FUN_1404D01D8 hands it to the lobby's settings). Its init (FUN_1404CCC24) loads the variant library in
// Firefight's mode (FUN_14043CDB8(lib, title, title, 4)), so while it is open the library's lists for the title are
// Firefight's maps and gametypes. Its START tile (its pick handler FUN_1404CF934, step 5): FUN_1404D070C (MCC's party
// size message: true = stop), the host's +0x48 = the gametype's category, the apply step FUN_1404D4C8C, then its Start
// FUN_1404D03A8 (its vtable +0x1B8). Done here the same way, on MCC's thread, for Halo: Reach (title index 6) only.
static const uintptr_t FF_SCREEN_VT = 0x32BE518, FF_START = 0x4D03A8, FF_BUSY = 0x4D070C;
static const uint8_t FF_START_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0x68, 0xA1, 0x48, 0x81, 0xEC, 0x00};
static const uint8_t FF_BUSY_HEAD[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x74, 0x24, 0x10, 0x57, 0x48, 0x83, 0xEC, 0x30, 0x48};
static const int FF_TITLE = 6, SCR_DIFF = 0x1840;
typedef bool(__fastcall* busy_fn)(uint8_t* screen);
static bool g_ff_ok;
static volatile ULONGLONG g_ff_live_at;
static pg_entry g_ff_maps[MAX_ENTRIES], g_ff_gts[MAX_ENTRIES];
static int g_ff_nmaps, g_ff_ngts, g_ff_diff = -1, g_ff_cur_map = -1, g_ff_cur_gt = -1;
static volatile uint32_t g_ff_seq;
static ULONGLONG g_ff_copied_at;
static bool g_ff_dumped;
static int g_ff_state, g_ff_map, g_ff_gt, g_ff_want_diff;   // (state: 0 none, 1 waiting, 2 started, -1 failed)
static char g_ff_why[160];

static void ff_fail(const char* why) {
    g_ff_state = -1;
    strcpy_s(g_ff_why, why);
    logf("firefight: launch failed: %s", why);
}

static void ff_copy(uint8_t* lib, uint8_t* screen) {
    pg_entry maps[MAX_ENTRIES], gts[MAX_ENTRIES];
    int nm = 0, ng = 0, n = 0;
    for (uint8_t* e = first(lib, LIST_MAP, FF_TITLE); more(lib, LIST_MAP, FF_TITLE, e, n) && nm < MAX_ENTRIES; e = *(uint8_t**)(e + 8), n++)
        if (*(int32_t*)(e + 0x14) != 4) fill(maps[nm++], e, false);
    n = 0;
    for (uint8_t* e = first(lib, LIST_GT, FF_TITLE); more(lib, LIST_GT, FF_TITLE, e, n) && ng < MAX_ENTRIES; e = *(uint8_t**)(e + 8), n++)
        if (*(int32_t*)(e + 0x14) != 4) { fill(gts[ng], e, false); gts[ng].category = *(int32_t*)(e + 0x450); ng++; }
    int cur_map = -1;                            // (MCC's own picks: the map by its content id)
    n = 0;
    for (uint8_t* e = first(lib, LIST_MAP, FF_TITLE); more(lib, LIST_MAP, FF_TITLE, e, n); e = *(uint8_t**)(e + 8), n++)
        if (!memcmp(e + 0x3E8, screen + SCR_MAP_ID, 16)) { cur_map = *(int32_t*)(e + 0x1C); break; }
    EnterCriticalSection(&g_lock);
    memcpy(g_ff_maps, maps, sizeof(pg_entry) * nm); g_ff_nmaps = nm;
    memcpy(g_ff_gts, gts, sizeof(pg_entry) * ng); g_ff_ngts = ng;
    g_ff_diff = (int8_t)screen[SCR_DIFF];
    g_ff_cur_map = cur_map;
    g_ff_cur_gt = *(int32_t*)(screen + SCR_GT);
    g_ff_seq++;
    LeaveCriticalSection(&g_lock);
    if (!g_ff_dumped) {                          // (native\bin\firefight_library.txt, once a session: the evidence)
        g_ff_dumped = true;
        logf("firefight: MCC's Firefight lists: %d maps, %d gametypes; difficulty %d", nm, ng, g_ff_diff);
        wchar_t path[MAX_PATH];
        swprintf_s(path, L"%s\\firefight_library.txt", g_bin);
        FILE* f = nullptr;
        if (!_wfopen_s(&f, path, L"w") && f) {
            fprintf(f, "MCC's Halo: Reach Firefight lists as Project Noble read them (pg_lobby.cpp); difficulty %d, map #%d, gametype #%d.\n\n== maps\n",
                    g_ff_diff, cur_map, g_ff_cur_gt);
            for (int i = 0; i < nm; i++) fprintf(f, "  #%d kind %d \"%s\" %s\n", maps[i].id, maps[i].kind, maps[i].name, maps[i].key);
            fprintf(f, "\n== gametypes (category)\n");
            for (int i = 0; i < ng; i++) fprintf(f, "  #%d kind %d category %d \"%s\" %s\n", gts[i].id, gts[i].kind, gts[i].category, gts[i].name, gts[i].key);
            fclose(f);
        }
    }
}

static void ff_launch(uint8_t* screen, uint8_t* lib, uint8_t* host) {
    void* settings = ((settings_fn)(g_mcc + LT_SETTINGS))(1);
    if (!settings) { ff_fail("MCC's lobby settings were not there."); return; }
    if (((counting_fn)(g_mcc + LT_COUNTING))(settings)) { ff_fail("MCC's Firefight lobby was already counting down."); return; }
    uint8_t* gt = by_id(lib, LIST_GT, FF_TITLE, g_ff_gt);
    uint8_t* map = by_id(lib, LIST_MAP, FF_TITLE, g_ff_map);
    if (!gt || !map) { ff_fail("That mission or game type is no longer in MCC's Firefight lists."); return; }
    if (g_ff_want_diff < 0 || g_ff_want_diff > 3) { ff_fail("That difficulty is not one of Halo: Reach's."); return; }
    memcpy(screen + SCR_MAP_ID, map + 0x3E8, 16);
    *(int32_t*)(screen + SCR_GT) = g_ff_gt;
    *(uint8_t**)(screen + SCR_GT_ENTRY) = ((gt_entry_fn)(g_mcc + LT_GT_ENTRY))(FF_TITLE, g_ff_gt);
    screen[SCR_DIFF] = (uint8_t)g_ff_want_diff;
    if (((busy_fn)(g_mcc + FF_BUSY))(screen)) { ff_fail("MCC says the party is too big for Firefight (its message is on screen)."); return; }
    *(int32_t*)(host + HOST_CAT) = *(int32_t*)(gt + 0x450);
    ((apply_fn)(g_mcc + LT_APPLY))(screen);
    ((start_fn)(g_mcc + FF_START))(screen);      // (its Start: MCC's checks, its commit, the launch)
    char m[64], g[64];
    entry_text(map, 0x58, m, sizeof m);
    entry_text(gt, 0x58, g, sizeof g);
    bool counting = ((counting_fn)(g_mcc + LT_COUNTING))(settings);
    g_ff_state = 2;                              // (Start ran: the screen going away is the start, counted by the screens)
    g_ff_why[0] = 0;
    logf("firefight: MCC's Start pressed: map #%d (%s), gametype #%d (%s), difficulty %d; countdown %d; host gametype #%d",
         g_ff_map, m, g_ff_gt, g, g_ff_want_diff, (int)counting, *(int32_t*)(host + HOST_GT));
}

static void ff_tick(uint8_t* screen) {
    if (!g_ff_ok || *(uint8_t**)screen != g_mcc + FF_SCREEN_VT) return;
    uint8_t* lib = *(uint8_t**)(g_mcc + LT_LIB);
    uint8_t* host = *(uint8_t**)(g_mcc + LT_HOST);
    if (!lib || !host || *(int32_t*)(screen + SCR_TITLE) != FF_TITLE) return;
    ULONGLONG now = GetTickCount64();
    bool back = !g_ff_live_at || now - g_ff_live_at > 1000;
    g_ff_live_at = now;
    if (back || !g_ff_copied_at || now - g_ff_copied_at > 2000) { g_ff_copied_at = now; ff_copy(lib, screen); }
    EnterCriticalSection(&g_lock);
    bool go = g_ff_state == 1;
    LeaveCriticalSection(&g_lock);
    if (go) {
        __try { ff_launch(screen, lib, host); } __except (EXCEPTION_EXECUTE_HANDLER) { ff_fail("MCC's Firefight lobby could not be read."); }
    }
}

// (Nov 21) MCC's custom game lobby screen ran its Update (any title): the overlay keeps the BOTS and Project Noble tiles
// up while it runs, even when MCC greys its top row (the focus on the maps or the session list)
static volatile ULONGLONG g_screen_at;
bool pg_lobby_screen_live() { return g_ok && g_screen_at && GetTickCount64() - g_screen_at < 500; }

static void __fastcall h_update(uint8_t* screen, float dt) {
    o_update(screen, dt);
    __try { if (*(uint8_t**)screen == g_mcc + LT_SCREEN_VT) g_screen_at = GetTickCount64(); }
    __except (EXCEPTION_EXECUTE_HANDLER) {}
    __try { tick(screen); } __except (EXCEPTION_EXECUTE_HANDLER) {
        static int told;
        if (told++ < 3) logf("proving grounds: lobby unreadable this frame");
    }
    __try { ff_tick(screen); } __except (EXCEPTION_EXECUTE_HANDLER) {   // (Nov 23: the Firefight lobby, the same Update)
        static int told;
        if (told++ < 3) logf("firefight: lobby unreadable this frame");
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
    if (!g_ok) { if (why) strcpy_s(why, cap, "This MCC build is not the one Project Noble was made for."); return -1; }
    EnterCriticalSection(&g_lock);
    int s = g_launch_state;
    if (why) strcpy_s(why, cap, g_launch_why);
    LeaveCriticalSection(&g_lock);
    return s;
}

// ---- (Nov 23) the Firefight lobby, for the screens (any thread)
bool pg_ff_live() { return g_ff_ok && g_ff_live_at && GetTickCount64() - g_ff_live_at < 500; }
bool pg_ff_ready() { return g_ff_ok; }
uint32_t pg_ff_seq() { return g_ff_ok ? g_ff_seq : 0; }
int pg_ff_lists(pg_entry* maps, int* nmaps, pg_entry* gts, int* ngts, int cap, int* difficulty, int* cur_map, int* cur_gt) {
    if (!g_ff_ok) { *nmaps = *ngts = 0; return 0; }
    EnterCriticalSection(&g_lock);
    *nmaps = g_ff_nmaps < cap ? g_ff_nmaps : cap;
    *ngts = g_ff_ngts < cap ? g_ff_ngts : cap;
    memcpy(maps, g_ff_maps, sizeof(pg_entry) * *nmaps);
    memcpy(gts, g_ff_gts, sizeof(pg_entry) * *ngts);
    *difficulty = g_ff_diff; *cur_map = g_ff_cur_map; *cur_gt = g_ff_cur_gt;
    uint32_t s = g_ff_seq;
    LeaveCriticalSection(&g_lock);
    return (int)s;
}
void pg_ff_launch(int map, int gametype, int difficulty) {
    if (!g_ff_ok) return;
    EnterCriticalSection(&g_lock);
    g_ff_map = map; g_ff_gt = gametype; g_ff_want_diff = difficulty;
    g_ff_state = 1;
    g_ff_why[0] = 0;
    LeaveCriticalSection(&g_lock);
    logf("firefight: a game asked of MCC's Firefight lobby: map #%d, gametype #%d, difficulty %d", map, gametype, difficulty);
}
int pg_ff_launch_state(char* why, int cap) {
    if (!g_ff_ok) { if (why) strcpy_s(why, cap, "This MCC build is not the one Project Noble was made for."); return -1; }
    EnterCriticalSection(&g_lock);
    int s = g_ff_state;
    if (why) strcpy_s(why, cap, g_ff_why);
    LeaveCriticalSection(&g_lock);
    return s;
}
void pg_ff_reset() {
    EnterCriticalSection(&g_lock);
    g_ff_state = 0; g_ff_why[0] = 0;
    LeaveCriticalSection(&g_lock);
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
    __try {                                      // (Nov 23: the Firefight lobby, on the same Update)
        g_ff_ok = !memcmp(g_mcc + FF_START, FF_START_HEAD, sizeof FF_START_HEAD) &&
                  !memcmp(g_mcc + FF_BUSY, FF_BUSY_HEAD, sizeof FF_BUSY_HEAD) &&
                  *(uint8_t**)(g_mcc + FF_SCREEN_VT + 0x58) == g_mcc + LT_UPDATE &&
                  *(uint8_t**)(g_mcc + FF_SCREEN_VT + 0x1B8) == g_mcc + FF_START;
    } __except (EXCEPTION_EXECUTE_HANDLER) { g_ff_ok = false; }
    logf(g_ff_ok ? "firefight: on MCC's Firefight lobby (the same Update)" : "firefight: MCC's Firefight lobby not as decoded: off");
}
