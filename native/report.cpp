// What MCC shows for the bots: their names, clan tags, service tags, emblems and teams (the player: "post scoreboard
// names";: "ensure these bot profiles clan tags, and emblems appear in each respective game and scoreboard").
// MCC knows a player by Xbox id (MCC-Win64-Shipping.exe, MCC 1.3528; ghidra: import_mcc_exe.bat, tools/pe_xref.py):
//  - its player lookup FUN_140249bec(manager, id, out) gives the emblem (foreground, background, three colours),
//    avatar, nameplate, clan tag (MCC string at +0x20) and service tag (+0x50); FUN_140249418 is its "unknown player"
//    fill (emblem 49 / 505, colours 2 3 1, clan "UNSC", tag "117"). Its callers: the post-game report's rows
//    (FUN_140365d4c), the emblem renderer that draws every player's emblem for the games' scoreboards
//    (FUN_1403374b0 -> FUN_140331920 by id, the PlayerEmblemTarget<n> textures: why bots had none in Halo 2 and a red
//    cross in Halo 3), the roster and the player cards;
//  - its gamertag lookup FUN_1402486e4 gives the name;
//  - the post-game builder takes the team from the game's results (entry +0x4C, 0x1C8 bytes a player).
// A bot's made-up id (0xB07B07B0000000<player index>, every game's add) is unknown to MCC, so:
//  - the lookup hook answers for a bot: MCC's own unknown-player fill, then the bot's emblem, clan tag and service tag
//    (strings set by MCC's own assign FUN_1405a2960: its allocator owns them), found; every other id goes to MCC;
//  - the builder hook writes each bot's real team into its results entry before the build, bot ids only;
//  - the gamertag hook notes which bot a report row is for, only when called from the builder's two row loops;
//  - the string-constructor hook gives that row the bot's name, not a blank, only at the builder's two name call
//    sites (by return address).
// Every function prologue and call site is checked against the file first; any mismatch (another MCC build)
// leaves MCC untouched.
#include <windows.h>
#include <intrin.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <wctype.h>
#include "third_party/minhook/include/MinHook.h"
#include "shared.h"

void logf(const char* fmt, ...);
extern hb_shared* g_shm;     // botcore.cpp: which game ticks (CE's post-game rows)
bool ce_player_numbers(int index, int out[5]);   // botcore.cpp: kills, assists, deaths, suicides, engine

static const uintptr_t MR_BUILD = 0x365D4C, MR_GAMERTAG = 0x2486E4, MR_STRING = 0x5A2574;
static const uintptr_t MR_PROFILE = 0x249BEC, MR_DEFAULTS = 0x249418, MR_ASSIGN = 0x5A2960;
// (call site, callee) pairs: the builder's two row loops (tools: builder call listing)
static const uintptr_t MR_LOOKUP_AT[] = {0x366C37, 0x367A87}, MR_NAME_AT[] = {0x366CCE, 0x367AE5};
static const uint8_t MR_BUILD_HEAD[] = {0x48, 0x8B, 0xC4, 0x55, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57};
static const uint8_t MR_GT_HEAD[] = {0x48, 0x89, 0x5C, 0x24, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x20, 0x49, 0x8B, 0xF8};
static const uint8_t MR_STR_HEAD[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x30, 0x48, 0xC7, 0x44, 0x24, 0x20, 0xFE, 0xFF, 0xFF, 0xFF};
static const uint8_t MR_PROFILE_HEAD[] = {0x40, 0x55, 0x53, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x57, 0x48, 0x8D, 0x6C,
                                          0x24, 0x90};
static const uint8_t MR_DEFAULTS_HEAD[] = {0x40, 0x53, 0x48, 0x83, 0xEC, 0x20, 0xB8, 0x01, 0x00, 0x00, 0x00, 0xC7, 0x01,
                                           0x31, 0x00, 0x00, 0x00};   // (... mov dword [out], 49: the default emblem)
static const uint8_t MR_ASSIGN_HEAD[] = {0x48, 0x83, 0xEC, 0x38, 0x48, 0x85, 0xD2, 0x74, 0x21};
static const uint32_t BOT_ID_HI = 0xB07B07B0u;
static const uint32_t LOBBY_ID_HI = 0xB07B07B1u;   // (Nov 13) the lobby's bots in MCC's session list: their own ids
// (custom, Nov 13, the owner: "Which ever you can make way on first", the rank badges) The lookup's +0x80 is the
// player's HaloStatsPlayerXP (the key names: FUN_1400C6CB0; MCC's unknown-player fill leaves it 0, the lowest badge).
// MCC turns XP into its account rank with a table it loads at start: manager [0x144001500] (FUN_140499908 +0x43),
// ready when its +0x138 is set, entries from +0xD8 to +0xE0 of 0x88 bytes: +0x20 the XP the rank starts at, +0x24
// the level, +0x28 the prestige (FUN_140347264 / FUN_1403472E4: the last entry at or under the XP). A lobby bot's
// rank is the one the mod draws for it (bots_panel.cpp bot_rank: tour = prestige + 1, level 1-30, the eagle level 0),
// so the lookup gives the XP that rank starts at
static const uintptr_t MR_RANKS_AT = 0x49994B, MR_RANK_LEVEL = 0x347264;
static const uint8_t MR_RANK_LEVEL_HEAD[] = {0x41, 0x83, 0xC9, 0xFF, 0x80, 0xB9, 0x38, 0x01, 0x00, 0x00, 0x00, 0x74, 0x32,
                                             0x48, 0x8B, 0x81, 0xD8, 0x00, 0x00, 0x00};
static uintptr_t g_ranks_global;          // MCC's rank table manager's global (0: not the build decoded)

struct bot_row { char name[32]; char tag[8]; char clan[16]; int team; int32_t emblem[5]; int tour, level; bool set; };
static bot_row g_rows[16];
static bot_row g_lobby[16];                // the lobby's bots (session_watch.cpp), never a match's rows
static uint32_t g_rows_game;               // botcore's game id when the bots were noted (report_note_bot)
static uint8_t* g_mcc;
static volatile LONG g_pending = -1;      // the bot whose row is being built (its id looked up last)

typedef void(__fastcall* build_fn)(int* report, uint8_t* results);
typedef char(__fastcall* gamertag_fn)(void* mgr, uint64_t xuid, void* out);
typedef void*(__fastcall* string_fn)(void* out, const char* s);
typedef char(__fastcall* profile_fn)(void* mgr, uint64_t xuid, int32_t* out);
typedef void(__fastcall* defaults_fn)(int32_t* out);
typedef void(__fastcall* assign_fn)(void* str, const char* s);
static build_fn o_build;
static gamertag_fn o_gamertag;
static string_fn o_string;
static profile_fn o_profile;

static bool is_bot(uint64_t xuid) {
    return (uint32_t)(xuid >> 32) == BOT_ID_HI && (xuid & 0xFFFFFFFFull) < 16 && g_rows[xuid & 0xFF].set;
}

// a match's bot or a lobby's bot by its made-up id; its row number for g_pending: 0-15 a match's, 16-31 a lobby's
static int row_number(uint64_t xuid) {
    if (is_bot(xuid)) return (int)(xuid & 0xFF);
    if ((uint32_t)(xuid >> 32) == LOBBY_ID_HI && (xuid & 0xFFFFFFFFull) < 16 && g_lobby[xuid & 0xFF].set)
        return 16 + (int)(xuid & 0xFF);
    return -1;
}

static const bot_row& row_at(int n) { return n < 16 ? g_rows[n] : g_lobby[n - 16]; }

static bool returns_to(void* ra, const uintptr_t* sites, int n) {
    for (int k = 0; k < n; k++)
        if ((uint8_t*)ra == g_mcc + sites[k] + 5) return true;
    return false;
}

// a bot's service tag from its name: its capitals and digits (Hawk983 -> H983), topped up with the letters after
// the first when that gives under three (Teabag -> TEA). Every game's bot gets it (MCC's post-game report; Reach
// shows it in game too)
void bot_service_tag(const wchar_t* name, wchar_t tag[4]) {
    int n = 0;
    for (int k = 0; k < 4; k++) tag[k] = 0;
    for (const wchar_t* c = name; *c && n < 4; c++)
        if (iswupper(*c) || iswdigit(*c)) tag[n++] = *c;
    for (const wchar_t* c = name + (*name ? 1 : 0); *c && n < 3; c++)
        if (iswlower(*c)) tag[n++] = towupper(*c);
}

// a bot's name, service tag, clan tag, MCC emblem (foreground 0: MCC's default) and team by player index (every
// game's add: reach.cpp, h3.cpp, odst.cpp, h4f.cpp, h2.cpp, before the game makes the player); team -1 leaves the
// results' team as the game wrote it
void report_note_bot(int index, const wchar_t* name, const wchar_t* tag, int team, const wchar_t* clan,
                     const uint16_t* emblem) {
    if (index < 0 || index >= 16) return;
    bot_row& r = g_rows[index];
    r.set = false;
    WideCharToMultiByte(CP_UTF8, 0, name, -1, r.name, sizeof r.name - 1, nullptr, nullptr);
    WideCharToMultiByte(CP_UTF8, 0, tag, 4, r.tag, sizeof r.tag - 1, nullptr, nullptr);
    r.tag[4] = 0;
    r.clan[0] = 0;
    if (clan && clan[0]) WideCharToMultiByte(CP_UTF8, 0, clan, -1, r.clan, sizeof r.clan - 1, nullptr, nullptr);
    for (int k = 0; k < 5; k++) r.emblem[k] = emblem ? emblem[k] : 0;
    r.team = team;
    r.tour = r.level = 0;
    r.set = true;
    g_rows_game = g_shm ? g_shm->game : 0;
}

// (custom, Nov 13) a lobby bot in MCC's session list (session_watch.cpp, sessionbots=): MCC looks it up by the same
// made-up id, so it gets a row too: its name, service tag, clan tag (bots_panel.cpp), MCC's default emblem.
// (Nov 13, "Yes add all the bots") A table of its own, ids 0xB07B07B1000000<index>, so the lobby's names never
// replace a finished match's rows (the post-game report is opened from the menus too)
const char* profile_clan_of(const char* name);             // bots_panel.cpp
void bot_rank(const char* name, int tier, int* tour, int* level);   // bots_panel.cpp
void report_note_lobby_bot(int index, const char* name, int team, int tier) {
    if (index < 0 || index >= 16 || !name) return;
    bot_row& r = g_lobby[index];
    int tour = 0, level = 0;
    bot_rank(name, tier, &tour, &level);
    if (r.set && !strcmp(r.name, name) && r.team == team && r.tour == tour && r.level == level) return;
    wchar_t w[32], tag[4];
    MultiByteToWideChar(CP_UTF8, 0, name, -1, w, 32);
    bot_service_tag(w, tag);
    r.set = false;
    r.tour = tour;
    r.level = level;
    strncpy_s(r.name, name, _TRUNCATE);
    WideCharToMultiByte(CP_UTF8, 0, tag, 4, r.tag, sizeof r.tag - 1, nullptr, nullptr);
    r.tag[4] = 0;
    strncpy_s(r.clan, profile_clan_of(name), _TRUNCATE);
    for (int k = 0; k < 5; k++) r.emblem[k] = 0;
    r.team = team;
    r.set = true;
}

// Halo CE hands MCC only the player's results row (live, s117: "report: results 0:1:<the player>"), so its bots were
// missing from the post-game report. Each bot noted here gets a free row: the player's row as the template, then in
// use, the bot's id, its team and its numbers (below). MCC finds its name, tags and emblem by the id (h_profile)
static void ce_rows(uint8_t* results) {
    uint8_t* person = nullptr;
    bool listed[16] = {};
    for (int i = 0; i < 16; i++) {
        uint8_t* e = results + (size_t)i * 0x1C8;
        uint64_t id = *(uint64_t*)(e + 0x28);
        if (is_bot(id)) listed[id & 0xFF] = true;
        else if (e[0x20] && !person) person = e;
    }
    if (!person) return;
    for (int k = 0; k < 16; k++) {
        if (!g_rows[k].set || listed[k]) continue;
        uint8_t* row = nullptr;
        for (int i = 0; i < 16 && !row; i++) {
            uint8_t* e = results + (size_t)i * 0x1C8;
            if (!e[0x20] && !*(uint64_t*)(e + 0x28)) row = e;
        }
        if (!row) return;
        memcpy(row, person, 0x1C8);
        *(uint64_t*)(row + 0x28) = 0xB07B07B000000000ull | (uint64_t)k;
        if (g_rows[k].team >= 0) *(int32_t*)(row + 0x4C) = g_rows[k].team;
        // its numbers, where MCC reads them (live, a Halo 2 post-game's 8 rows against MCC's own screen: row +0x54
        // score; the row's area, results + row * 0x5448: +0x1D04 kills, +0x1D08 and +0x1DAC assists, +0x1D0C deaths),
        // from halo1's own counters (botcore.cpp ce_player_numbers); score in Slayer is kills less suicides (the Halo 2
        // rows: 6 kills and a suicide scored 5), 0 in the other modes (their points are not read)
        int n[5] = {};
        bool got = ce_player_numbers(k, n);
        uint8_t* area = results + (size_t)(row - results) / 0x1C8 * 0x5448;
        *(int32_t*)(row + 0x54) = got && n[4] == 2 ? n[0] - n[3] : 0;
        *(int32_t*)(area + 0x1D04) = got ? n[0] : 0;
        *(int32_t*)(area + 0x1D08) = got ? n[1] : 0;
        *(int32_t*)(area + 0x1DAC) = got ? n[1] : 0;
        *(int32_t*)(area + 0x1D0C) = got ? n[2] : 0;
    }
}

static void __fastcall h_build(int* report, uint8_t* results) {
    __try {
        if (g_rows_game == 1 && results) ce_rows(results);        // (the game the bots were added in: 1 = Halo CE)
        char line[640];
        int at = 0;
        line[0] = 0;
        for (int i = 0; results && i < 16; i++) {           // the 16 results entries the builder indexes
            uint8_t* e = results + (size_t)i * 0x1C8;
            uint64_t id = *(uint64_t*)(e + 0x28);
            if ((e[0x20] || id) && at < (int)sizeof line - 40)  // (in the log: which rows MCC was given, entry +0x20 in use)
                at += sprintf_s(line + at, sizeof line - at, " %d:%d:%llx", i, e[0x20], (unsigned long long)id);
            if (is_bot(id) && g_rows[id & 0xFF].team >= 0 && g_rows[id & 0xFF].team < 16)
                *(int32_t*)(e + 0x4C) = g_rows[id & 0xFF].team;
        }
        logf("report: results%s", line);
    } __except (EXCEPTION_EXECUTE_HANDLER) { logf("report: results unreadable"); }
    o_build(report, results);
    InterlockedExchange(&g_pending, -1);
}

static char __fastcall h_gamertag(void* mgr, uint64_t xuid, void* out) {
    if (returns_to(_ReturnAddress(), MR_LOOKUP_AT, 2))
        InterlockedExchange(&g_pending, (LONG)row_number(xuid));
    return o_gamertag(mgr, xuid, out);
}

static void* __fastcall h_string(void* out, const char* s) {
    LONG b = g_pending;
    if (b >= 0 && b < 32 && returns_to(_ReturnAddress(), MR_NAME_AT, 2)) s = row_at(b).name;   // its name, not a blank
    return o_string(out, s);
}

// a bot as MCC keeps a player: MCC's own unknown-player fill (avatar, nameplate and the rest), then the bot's emblem,
// nameplate, clan tag and service tag; found. (Custom, Nov 11) The fill FUN_140249418 writes the emblem's five at +0x00
// to +0x10, then 6 at +0x14 and 1 at +0x18: avatar 6 is MCC's free default (PlayerIDAvatar_001) and nameplate 1 its
// blank one (playercustomization.xml), so +0x18 is the nameplate: the bot's own (bots_panel.cpp bot_nameplate, MCC's
// catalog read from its folder), which MCC's screens draw behind its name
int bot_nameplate(const char* name);                       // bots_panel.cpp

// the XP MCC's account rank (tour 1-11, level 1-30; the eagle 0) starts at, from MCC's own table; -1 not known
static int64_t rank_xp(int tour, int level) {
    if (!g_ranks_global || tour < 1 || tour > 11) return -1;
    const uint8_t* mgr = *(const uint8_t* const*)(g_mcc + g_ranks_global);
    if (!mgr || !mgr[0x138]) return -1;
    const uint8_t* e = *(const uint8_t* const*)(mgr + 0xD8);
    const uint8_t* end = *(const uint8_t* const*)(mgr + 0xE0);
    if (!e || end < e || (end - e) % 0x88 || (end - e) / 0x88 > 4000) return -1;
    int n = (int)((end - e) / 0x88), base = 1 << 30;
    for (int i = 0; i < n; i++)                                    // (the levels' first: 0 or 1)
        if (*(const int32_t*)(e + i * 0x88 + 0x24) < base) base = *(const int32_t*)(e + i * 0x88 + 0x24);
    static bool told;
    if (!told) {
        told = true;
        logf("report: MCC's rank table: %d ranks, levels from %d; first %u xp (%d, %d), last %u xp (%d, %d)", n, base,
             *(const uint32_t*)(e + 0x20), *(const int32_t*)(e + 0x28), *(const int32_t*)(e + 0x24),
             *(const uint32_t*)(e + (n - 1) * 0x88 + 0x20), *(const int32_t*)(e + (n - 1) * 0x88 + 0x28),
             *(const int32_t*)(e + (n - 1) * 0x88 + 0x24));
    }
    for (int i = 0; i < n; i++) {
        const uint8_t* x = e + i * 0x88;
        if (*(const int32_t*)(x + 0x28) != tour - 1) continue;
        if (level < 1 || *(const int32_t*)(x + 0x24) == level - 1 + base) return *(const uint32_t*)(x + 0x20);
    }
    return -1;
}

static char __fastcall h_profile(void* mgr, uint64_t xuid, int32_t* out) {
    int rn = out ? row_number(xuid) : -1;
    if (rn < 0) return o_profile(mgr, xuid, out);
    const bot_row& r = row_at(rn);
    ((defaults_fn)(g_mcc + MR_DEFAULTS))(out);
    if (r.emblem[0] > 0) memcpy(out, r.emblem, sizeof r.emblem);   // foreground, background, primary, secondary, back
    int np = r.name[0] ? bot_nameplate(r.name) : -1;
    if (np > 0) out[6] = np;                                       // +0x18: its nameplate
    ((assign_fn)(g_mcc + MR_ASSIGN))(out + 8, r.clan);             // +0x20: its clan tag, "" for none
    ((assign_fn)(g_mcc + MR_ASSIGN))(out + 0x14, r.tag);           // +0x50: its service tag
    if (r.tour > 0) {                                               // +0x80: its XP, for its rank's badge
        int64_t xp = -1;
        __try { xp = rank_xp(r.tour, r.level); } __except (EXCEPTION_EXECUTE_HANDLER) { xp = -1; }
        if (xp >= 0) out[0x20] = (int32_t)xp;
    }
    return 1;
}

static bool calls(const uintptr_t at, uintptr_t callee) {
    return g_mcc[at] == 0xE8 && at + 5 + *(int32_t*)(g_mcc + at + 1) == callee;
}

static bool hook(uintptr_t at, void* fn, void** orig) {
    return MH_CreateHook(g_mcc + at, fn, orig) == MH_OK && MH_EnableHook(g_mcc + at) == MH_OK;
}

void report_hooks() {
    g_mcc = (uint8_t*)GetModuleHandleW(nullptr);
    bool ok = false;
    __try {
        ok = !memcmp(g_mcc + MR_BUILD, MR_BUILD_HEAD, sizeof MR_BUILD_HEAD) &&
             !memcmp(g_mcc + MR_GAMERTAG, MR_GT_HEAD, sizeof MR_GT_HEAD) &&
             !memcmp(g_mcc + MR_STRING, MR_STR_HEAD, sizeof MR_STR_HEAD) &&
             !memcmp(g_mcc + MR_PROFILE, MR_PROFILE_HEAD, sizeof MR_PROFILE_HEAD) &&
             !memcmp(g_mcc + MR_DEFAULTS, MR_DEFAULTS_HEAD, sizeof MR_DEFAULTS_HEAD) &&
             !memcmp(g_mcc + MR_ASSIGN, MR_ASSIGN_HEAD, sizeof MR_ASSIGN_HEAD);
        for (int k = 0; ok && k < 2; k++)
            ok = calls(MR_LOOKUP_AT[k], MR_GAMERTAG) && calls(MR_NAME_AT[k], MR_STRING);
    } __except (EXCEPTION_EXECUTE_HANDLER) { ok = false; }
    if (!ok) { logf("report: MCC build not the one decoded (1.3528): bots' names, tags and emblems in MCC off"); return; }
    if (!hook(MR_BUILD, (void*)&h_build, (void**)&o_build) || !hook(MR_GAMERTAG, (void*)&h_gamertag, (void**)&o_gamertag) ||
        !hook(MR_STRING, (void*)&h_string, (void**)&o_string) || !hook(MR_PROFILE, (void*)&h_profile, (void**)&o_profile)) {
        logf("report: hooks failed");
        return;
    }
    __try {
        // the table's manager: mov rbx,[rip+disp] at FUN_140499908 +0x43, and the level lookup's head
        if (g_mcc[MR_RANKS_AT] == 0x48 && g_mcc[MR_RANKS_AT + 1] == 0x8B && g_mcc[MR_RANKS_AT + 2] == 0x1D &&
            !memcmp(g_mcc + MR_RANK_LEVEL, MR_RANK_LEVEL_HEAD, sizeof MR_RANK_LEVEL_HEAD))
            g_ranks_global = MR_RANKS_AT + 7 + *(int32_t*)(g_mcc + MR_RANKS_AT + 3);
    } __except (EXCEPTION_EXECUTE_HANDLER) { g_ranks_global = 0; }
    logf("report: bots' names, clan tags, service tags and emblems in MCC on; lobby bots' rank badges %s",
         g_ranks_global == 0x4001500 ? "on" : "off (not the table decoded)");
    if (g_ranks_global != 0x4001500) g_ranks_global = 0;
}
