// theater.cpp (custom, Nov 23): Project Noble's Theater lobby driving MCC's own Theatre screen (proving_grounds.h).
// The owner: "Start making all of the other menus that arent Matchmaking work accordingly"; asked, he chose the full
// way (as Custom Game: the picks set in MCC's own screen and its own start) and Theater first.
// MCC-Win64-Shipping.exe (Oct 31 2026 file; static read with Ghidra, Nov 23, not yet proved live):
//  - the screen registry (FUN_1402FAA20) names "Theatre" with the factory 0x14329A950, whose create (FUN_14031EBA4)
//    makes a 0x1050-byte screen with the vtable 0x143296FB0: its Update at +0x58 (FUN_14035B0E0, each frame on MCC's UI
//    thread), its event handler at +0x60 (FUN_14035B1D8, live only while its step +0xFF0 is 5, the screen set up);
//  - +0x250 the category list (its first entry films, id 0xAE3A39B4), +0x920 the film list: a list object whose vtable
//    +0x118 (this, -1) counts its items and +0x120 (this, index, 0) gives one; a film's item (vtable 0x14329EC90, made
//    in FUN_14035AB00 from MCC's content library) holds the film's 16-byte content id at +0x2A0; +0x240 is 1 once the
//    film list is filled;
//  - +0xFF4 the chosen film's content id; FUN_14035B3EC(screen) starts it (MCC's own START FILM, unless the lobby's
//    settings (FUN_14034CEF8(1)) say a countdown runs, FUN_14034D1E4): it finds the film in the content library
//    [0x1440016C0] (FUN_14047E21C(lib, &id, 0, 2, 0): kind 2 films), checks it, sets the game-launch host up for theater
//    (FUN_14035C3E0) and asks MCC's UI to launch;
//  - a library entry: the content id at +0x24, its name a text record at +0x68 (0x30 bytes: 0x01020304 at +0x10, the
//    length at +0x14, the text at +0x18), its game mode at +0x468, its map at +0x46C.
// How a film file on disk (Temporary\UserContent\HaloReach\Movie, LocalFiles\<id>\HaloReach\Movie) maps to a content
// id is not known yet: each entry's text records are matched against the file's name and its header's unique id (its
// _blf chdr: 8 bytes at 0x60), and the first time MCC's list is read it is written to native\bin\theater_library.txt
// (the evidence for the next step). Any byte mismatch (another MCC build) leaves MCC untouched and Project Noble says so.
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "third_party/minhook/include/MinHook.h"
#include "proving_grounds.h"

void logf(const char* fmt, ...);

static const uintptr_t TH_UPDATE = 0x35B0E0, TH_START = 0x35B3EC, TH_SCREEN_VT = 0x3296FB0, TH_ITEM_VT = 0x329EC90;
static const uintptr_t TH_LIB = 0x40016C0, TH_FIND = 0x47E21C, TH_SETTINGS = 0x34CEF8, TH_COUNTING = 0x34D1E4;
static const uint8_t TH_UPDATE_HEAD[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x50, 0x8B, 0x81, 0xF0, 0x0F, 0x00, 0x00, 0x48, 0x8B, 0xD9, 0x0F};
static const uint8_t TH_START_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x48, 0x8D, 0x68, 0xA1, 0x48, 0x81, 0xEC, 0xC0, 0x00, 0x00, 0x00, 0x48};
static const uint8_t TH_FIND_HEAD[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x48, 0x89, 0x6C, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18, 0x57};
static const uint8_t TH_SETTINGS_HEAD[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x20, 0x48, 0x8B, 0x15, 0x13, 0x46, 0xCB, 0x03, 0x8B, 0xD9, 0x48};
static const uint8_t TH_COUNTING_HEAD[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x20, 0x33, 0xDB, 0x39, 0x19, 0x75, 0x08, 0xFF, 0x15, 0xEA, 0xD3};
static const int SCR_STEP = 0xFF0, SCR_FILM = 0xFF4, SCR_FILLED = 0x240, SCR_FILMS = 0x920, ITEM_ID = 0x2A0;
static const int ENTRY_ID = 0x24, ENTRY_NAME = 0x68, ENTRY_MODE = 0x468, ENTRY_SCAN = 0x600;

typedef void(__fastcall* update_fn)(uint8_t* screen, float dt);
typedef void(__fastcall* start_fn)(uint8_t* screen);
typedef uint8_t*(__fastcall* find_fn)(uint8_t* lib, const uint8_t* id, int from, int kind, void* extra);
typedef void*(__fastcall* settings_fn)(int which);
typedef bool(__fastcall* counting_fn)(void* settings);
typedef uint32_t(__fastcall* count_fn)(void* list, int which);
typedef uint8_t*(__fastcall* item_fn)(void* list, int index, int flag);

static update_fn o_update;
static uint8_t* g_mcc;
static bool g_ok;
static wchar_t g_bin[MAX_PATH];
static CRITICAL_SECTION g_lock;
static volatile ULONGLONG g_live_at;

static pg_film g_films[PG_MAX_FILMS];
static int g_nfilms;
static volatile uint32_t g_seq;
static ULONGLONG g_read_at;
static bool g_dumped;

// the films on disk as the screens hand them over: each one's file name and its header's unique id, to match
static pg_film_file g_files[PG_MAX_FILMS];
static int g_nfiles;

static int g_state;                              // 0 none, 1 asked, 2 started (waiting for the screen to go), 3 done, -1 failed
static uint8_t g_want[16];
static char g_why[200];
static ULONGLONG g_asked_at, g_started_at;

// a text record of an entry (narrow or wide, whichever reads as text); false when there is none at rec
static bool rec_text(const uint8_t* e, int rec, char* out, int cap) {
    out[0] = 0;
    const uint8_t* p = e + rec;
    if (*(const uint32_t*)(p + 0x10) != 0x01020304) return false;
    uint32_t n = *(const uint32_t*)(p + 0x14);
    const uint8_t* s = *(const uint8_t* const*)(p + 0x18);
    if (!n || n > 400 || !s) return false;
    bool narrow = true;
    for (uint32_t i = 0; i < n && narrow; i++) narrow = s[i] >= 32 && s[i] != 127;
    if (narrow) {
        int k = (int)n < cap - 1 ? (int)n : cap - 1;
        memcpy(out, s, k);
        out[k] = 0;
        return true;
    }
    const wchar_t* w = (const wchar_t*)s;
    for (uint32_t i = 0; i < n; i++) if (w[i] < 32) return false;
    int k = WideCharToMultiByte(CP_UTF8, 0, w, (int)n, out, cap - 1, nullptr, nullptr);
    out[k > 0 ? k : 0] = 0;
    return k > 0;
}

static bool icontains(const char* hay, const char* needle) {
    size_t n = strlen(needle);
    if (!n) return false;
    for (const char* p = hay; *p; p++) if (!_strnicmp(p, needle, n)) return true;
    return false;
}

// which file on disk an entry is: one of its text records holds the file's name, or its bytes the header's unique id
// (the entry's texts and 8-byte values read once, then each file looked for in them)
static int match_file(const uint8_t* e, const pg_film_file* files, int nfiles, char* how, int cap) {
    how[0] = 0;
    static char texts[16][420];
    int tat[16], nt = 0;
    for (int rec = 0; rec + 0x20 <= ENTRY_SCAN && nt < 16; rec += 8) {
        bool got = false;
        __try { got = rec_text(e, rec, texts[nt], sizeof texts[nt]); } __except (EXCEPTION_EXECUTE_HANDLER) { got = false; }
        if (got) tat[nt++] = rec;
    }
    for (int i = 0; i < nfiles; i++) {
        const pg_film_file& f = files[i];
        for (int k = 0; k < nt && f.file[0]; k++)
            if (icontains(texts[k], f.file)) { sprintf_s(how, cap, "name at +0x%X", tat[k]); return i; }
    }
    for (int off = 0; off + 8 <= ENTRY_SCAN; off += 4) {
        uint64_t v = *(const uint64_t*)(e + off), w = _byteswap_uint64(v);
        if (!v) continue;
        for (int i = 0; i < nfiles; i++)
            if (files[i].uid && (v == files[i].uid || w == files[i].uid)) { sprintf_s(how, cap, "unique id at +0x%X", off); return i; }
    }
    return -1;
}

static void dump_entry(FILE* f, const uint8_t* e) {
    for (int rec = 0; rec + 0x20 <= ENTRY_SCAN; rec += 8) {
        char t[420];
        if (rec_text(e, rec, t, sizeof t)) fprintf(f, "    text +0x%03X \"%s\"\n", rec, t);
    }
    for (int i = 0; i < ENTRY_SCAN; i += 32) {
        fprintf(f, "    %03X:", i);
        for (int k = 0; k < 32; k++) fprintf(f, " %02X", e[i + k]);
        fprintf(f, "\n");
    }
}

// MCC's film list as its screen has it (MCC's thread): each film's id, name, mode and the file it is when matched.
// (MCC is only called with the lock free: a fault in its code then leaves nothing held)
static pg_film_file s_files[PG_MAX_FILMS];
static pg_film s_films[PG_MAX_FILMS];
static void read_films(uint8_t* screen, uint8_t* lib) {
    EnterCriticalSection(&g_lock);
    int nfiles = g_nfiles;
    memcpy(s_files, g_files, sizeof(pg_film_file) * nfiles);
    LeaveCriticalSection(&g_lock);
    void* list = screen + SCR_FILMS;
    void** vt = *(void***)list;
    uint32_t n = ((count_fn)vt[0x118 / 8])(list, -1);
    if (n > PG_MAX_FILMS) n = PG_MAX_FILMS;
    pg_film* films = s_films;
    int nf = 0;
    FILE* f = nullptr;
    if (!g_dumped && nfiles) {                   // (Nov 23, the first live run: written before the files came, no matches)
        wchar_t path[MAX_PATH];
        swprintf_s(path, L"%s\\theater_library.txt", g_bin);
        if (!_wfopen_s(&f, path, L"w") && f)
            fprintf(f, "MCC's Theatre film list as Project Noble read it (theater.cpp), %u items; %d film files on disk.\n\n", n, nfiles);
    }
    for (uint32_t i = 0; i < n; i++) {
        uint8_t* item = ((item_fn)vt[0x120 / 8])(list, (int)i, 0);
        if (!item || *(uint8_t**)item != g_mcc + TH_ITEM_VT) continue;
        pg_film& m = films[nf];
        memset(&m, 0, sizeof m);
        memcpy(m.id, item + ITEM_ID, 16);
        m.file = -1;
        uint8_t* e = ((find_fn)(g_mcc + TH_FIND))(lib, m.id, 0, 2, nullptr);
        if (e) {
            rec_text(e, ENTRY_NAME, m.name, sizeof m.name);
            m.mode = *(int32_t*)(e + ENTRY_MODE);
            char how[64];
            m.file = match_file(e, s_files, nfiles, how, sizeof how);
            if (f) {
                fprintf(f, "#%d \"%s\" mode %d, file %d (%s), id", nf, m.name, m.mode, m.file, m.file >= 0 ? how : "no match");
                for (int k = 0; k < 16; k++) fprintf(f, " %02X", m.id[k]);
                fprintf(f, "\n");
                if (nf < 3) dump_entry(f, e);
            }
        }
        nf++;
    }
    EnterCriticalSection(&g_lock);
    memcpy(g_films, films, sizeof(pg_film) * nf);
    g_nfilms = nf;
    g_seq++;
    LeaveCriticalSection(&g_lock);
    if (f) {
        fprintf(f, "\n== the film files the screens handed over\n");
        for (int i = 0; i < nfiles; i++) fprintf(f, "  %d %s uid %016llX\n", i, s_files[i].file, (unsigned long long)s_files[i].uid);
        fclose(f);
        g_dumped = true;
        int matched = 0;
        for (int i = 0; i < nf; i++) matched += films[i].file >= 0;
        logf("theater: MCC's film list read: %d films, %d matched to files on disk (theater_library.txt)", nf, matched);
    }
}

static void fail(const char* why) {
    g_state = -1;
    strcpy_s(g_why, why);
    logf("theater: start failed: %s", why);
}

// the chosen film into the screen as MCC's own list sets it, then MCC's own START FILM
static void start(uint8_t* screen, uint8_t* lib) {
    if (*(int32_t*)(screen + SCR_STEP) != 5) return;          // (not set up yet: asked again next frame)
    void* settings = ((settings_fn)(g_mcc + TH_SETTINGS))(1);
    if (settings && ((counting_fn)(g_mcc + TH_COUNTING))(settings)) { fail("MCC's Theater was already starting a film."); return; }
    if (!((find_fn)(g_mcc + TH_FIND))(lib, g_want, 0, 2, nullptr)) { fail("That film is not in MCC's Theater list."); return; }
    memcpy(screen + SCR_FILM, g_want, 16);
    ((start_fn)(g_mcc + TH_START))(screen);
    g_state = 2;
    g_started_at = GetTickCount64();
    logf("theater: MCC's START FILM pressed for the chosen film");
}

static void tick(uint8_t* screen) {
    if (*(uint8_t**)screen != g_mcc + TH_SCREEN_VT) return;
    uint8_t* lib = *(uint8_t**)(g_mcc + TH_LIB);
    if (!lib) return;
    ULONGLONG now = GetTickCount64();
    bool back = !g_live_at || now - g_live_at > 1000;
    g_live_at = now;
    // read again when the screen comes back, the files are handed over (g_read_at 0) or MCC's list changes size
    static uint32_t last_n = 0xFFFFFFFF;
    if (*(int32_t*)(screen + SCR_STEP) == 5 && screen[SCR_FILLED]) {
        void* list = screen + SCR_FILMS;
        uint32_t n = ((count_fn)(*(void***)list)[0x118 / 8])(list, -1);
        if (back || !g_read_at || n != last_n) {
            g_read_at = now;
            last_n = n;
            read_films(screen, lib);
        }
    }
    EnterCriticalSection(&g_lock);
    bool go = g_state == 1;
    LeaveCriticalSection(&g_lock);
    if (go) {
        __try { start(screen, lib); } __except (EXCEPTION_EXECUTE_HANDLER) { fail("MCC's Theater could not be read."); }
    }
}

static void __fastcall h_update(uint8_t* screen, float dt) {
    o_update(screen, dt);
    __try { tick(screen); } __except (EXCEPTION_EXECUTE_HANDLER) {
        static int told;
        if (told++ < 3) logf("theater: MCC's Theatre unreadable this frame");
    }
}

// ---- the screens' side (any thread)
bool pg_theater_live() { return g_ok && g_live_at && GetTickCount64() - g_live_at < 500; }
bool pg_theater_ready() { return g_ok; }

void pg_theater_files(const pg_film_file* files, int n) {
    if (!g_ok) return;
    if (n > PG_MAX_FILMS) n = PG_MAX_FILMS;
    EnterCriticalSection(&g_lock);
    memcpy(g_files, files, sizeof(pg_film_file) * n);
    g_nfiles = n;
    g_read_at = 0;                               // (matched again on MCC's next frame)
    LeaveCriticalSection(&g_lock);
}

int pg_theater_films(pg_film* out, int cap) {
    if (!g_ok) return 0;
    EnterCriticalSection(&g_lock);
    int n = g_nfilms < cap ? g_nfilms : cap;
    memcpy(out, g_films, sizeof(pg_film) * n);
    LeaveCriticalSection(&g_lock);
    return n;
}
uint32_t pg_theater_seq() { return g_ok ? g_seq : 0; }

void pg_theater_start(const uint8_t id[16]) {
    if (!g_ok) return;
    EnterCriticalSection(&g_lock);
    memcpy(g_want, id, 16);
    g_state = 1;
    g_why[0] = 0;
    g_asked_at = GetTickCount64();
    LeaveCriticalSection(&g_lock);
    logf("theater: a film asked of MCC's Theater");
}

// 2 while MCC goes from its Theater into the film (its screen gone within 10 s: done, 3); -1 with why
int pg_theater_state(char* why, int cap) {
    if (!g_ok) { if (why) strcpy_s(why, cap, "This MCC build is not the one Project Noble was made for."); return -1; }
    EnterCriticalSection(&g_lock);
    ULONGLONG now = GetTickCount64();
    if (g_state == 2 && !pg_theater_live()) { g_state = 3; logf("theater: MCC's Theater screen closed: the film is loading"); }
    else if (g_state == 2 && now - g_started_at > 10000) fail("MCC did not start the film. Leave Project Noble to see any message its Theater shows.");
    int s = g_state;
    if (why) strcpy_s(why, cap, g_why);
    LeaveCriticalSection(&g_lock);
    return s;
}
void pg_theater_reset() {
    if (!g_ok) return;
    EnterCriticalSection(&g_lock);
    g_state = 0;
    g_why[0] = 0;
    LeaveCriticalSection(&g_lock);
}

void theater_hooks() {                           // (session_watch.cpp calls it at start, after lobby_test_hooks)
    InitializeCriticalSection(&g_lock);
    g_mcc = (uint8_t*)GetModuleHandleW(nullptr);
    HMODULE me = nullptr;
    if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCWSTR)&theater_hooks, &me)) {
        DWORD n = GetModuleFileNameW(me, g_bin, MAX_PATH);
        wchar_t* slash = n && n < MAX_PATH ? wcsrchr(g_bin, L'\\') : nullptr;
        if (slash) *slash = 0;
    }
    bool ok = false;
    __try {
        ok = !memcmp(g_mcc + TH_UPDATE, TH_UPDATE_HEAD, sizeof TH_UPDATE_HEAD) &&
             !memcmp(g_mcc + TH_START, TH_START_HEAD, sizeof TH_START_HEAD) &&
             !memcmp(g_mcc + TH_FIND, TH_FIND_HEAD, sizeof TH_FIND_HEAD) &&
             !memcmp(g_mcc + TH_SETTINGS, TH_SETTINGS_HEAD, sizeof TH_SETTINGS_HEAD) &&
             !memcmp(g_mcc + TH_COUNTING, TH_COUNTING_HEAD, sizeof TH_COUNTING_HEAD) &&
             *(uint8_t**)(g_mcc + TH_SCREEN_VT + 0x58) == g_mcc + TH_UPDATE;   // (the Theatre screen's Update)
    } __except (EXCEPTION_EXECUTE_HANDLER) { ok = false; }
    if (!ok) { logf("theater: MCC build not the one decoded (Oct 31 2026): off"); return; }
    if (MH_CreateHook(g_mcc + TH_UPDATE, (void*)&h_update, (void**)&o_update) != MH_OK ||
        MH_EnableHook(g_mcc + TH_UPDATE) != MH_OK) {
        logf("theater: hook failed: off");
        return;
    }
    g_ok = true;
    logf("theater: on MCC's Theatre screen (its Update)");
}
