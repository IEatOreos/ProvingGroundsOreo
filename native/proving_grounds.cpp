// proving_grounds.cpp (custom, Nov 16): Proving Grounds, an offline copy of Halo: Reach's Social Games (proving_grounds.h).
// The owner: "recreate the Social games menu for my own offline experience. We will name the new selection Proving
// Grounds", "the ability to select either 4v4 or 8v8", "when I click play ... a random 4-10 seconds of fake searching
// and then we connect to our lobby", "the voting ... where I can openly vote and the bots in my lobby will (vote)", "an
// 'invite player' function, to invite certain bots to our team so they're always paired with us", and his friend's:
// "Random lobbies broken up to balance teams every match (unless they're a stack/clan). Three maps/gametypes to vote for
// each pre game lobby and the bots each get a vote -- they have preferences based on their player traits/personality/
// skill level", "Roll a weighted dice on what they want to play".
//  - the playlists: Arena (4v4) and Big Team Battle (8v8), each a list of MCC's own Halo: Reach gametypes (team games
//    only: MCC's own flag, pg_lobby.cpp) and maps; native\bin\proving_grounds.ini can replace either list;
//  - the lobby: Bot Matchmaking's pool (bots_panel.cpp bot_pool_matchmake): the person's invited party on their team,
//    clans whole, teams dealt by points every match; between matches about 7 in 10 stay (a clan stays or goes together);
//  - the vote: three gametype-on-map options MCC's pairing check accepts and None of the Above (once a lobby, as Reach:
//    more than half the lobby on it brings three new options with no veto); each bot's taste comes from its name (its
//    favourite and least favourite maps, how much it likes each kind of game, vehicles, small or big maps) and its
//    difficulty (the higher, the sweatier: Slayer and the competitive maps); it rolls its vote on those odds;
//  - the winner: put into MCC's own lobby and its Start pressed (pg_lobby.cpp), so the lobby, the match and its carnage
//    report are MCC's own.
// Pictures: the map previews and gametype icons this PC has (native\bin\service_record\art, from MCC's own files and the
// owner's sheet: tools/service_record_art.py; not in git); without them the screens draw their own panels.
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <stdint.h>
#include <time.h>
#include <algorithm>
#include <deque>
#include <string>
#include <vector>
#include "third_party/imgui/imgui.h"
#include "bots_panel.h"
#include "proving_grounds.h"
#include "ui_layout.h"

void logf(const char* fmt, ...);
const char* mcc_player_name();                   // session_watch.cpp: the person's name in MCC's list ("" not yet)
bool mcc_player_look(int32_t emblem[5], int* nameplate);   // report.cpp: the person's emblem and nameplate (false: not yet)
bool mcc_person_look(uint64_t id, int32_t emblem[5], int* nameplate);   // report.cpp: a joined friend's
// session_watch.cpp (Nov 17): the other people in MCC's session (friends who joined: ids, names, MCC's team or -1),
// and the team MCC has the player on (-1 not known)
int mcc_session_people(uint64_t* ids, char (*names)[32], int* teams, int cap);
int mcc_player_team();

// ------------------------------------------------------------------ tables
static const char* R_MAPS[26] = { "", "Boardwalk", "Boneyard", "Countdown", "Powerhouse", "Reflection", "Spire",
    "Sword Base", "Zealot", "Anchor 9", "Breakpoint", "Tempest", "Condemned", "Highlands", "Battle Canyon", "Penance",
    "Ridgeline", "Solitary", "High Noon", "Breakneck", "Forge World",
    // R-21 to R-25: MCC's haloreach\map_variants hr_forgeWorld_* in the folder's order (the library lists them in it)
    "Asylum", "Hemorrhage", "Paradiso", "Pinnacle", "The Cage" };

// a map's feel, for the bots' tastes: size 0 small .. 2 big, vehicles 0 none .. 2 many, competitive 0 casual .. 2 arena
struct map_feel { const char* name; int size, vehicles, comp; };
static const map_feel FEEL[] = {
    {"Boardwalk", 1, 0, 1}, {"Boneyard", 2, 2, 0}, {"Countdown", 1, 0, 2}, {"Powerhouse", 1, 0, 1}, {"Reflection", 1, 0, 2},
    {"Spire", 2, 2, 1}, {"Sword Base", 1, 0, 2}, {"Zealot", 1, 0, 2}, {"Anchor 9", 1, 0, 1}, {"Breakpoint", 2, 2, 0},
    {"Tempest", 2, 2, 0}, {"Condemned", 1, 0, 1}, {"Highlands", 2, 2, 0}, {"Battle Canyon", 0, 0, 1}, {"Penance", 0, 0, 1},
    {"Ridgeline", 2, 1, 0}, {"Solitary", 0, 0, 1}, {"High Noon", 1, 0, 1}, {"Breakneck", 2, 2, 0}, {"Forge World", 2, 2, 0},
    {"Asylum", 1, 0, 2}, {"Hemorrhage", 2, 2, 1}, {"Paradiso", 2, 2, 0}, {"Pinnacle", 1, 0, 1}, {"The Cage", 1, 0, 2},
    {"Beaver Creek", 0, 0, 2}, {"Damnation", 0, 0, 1}, {"Hang 'Em High", 1, 0, 1}, {"Headlong", 2, 2, 0},
    {"Prisoner", 0, 0, 1}, {"Timberland", 2, 1, 0} };

// gametype families: MCC's category numbers (a gametype's +0x450) and the gametype icons' names
// (tools/service_record_site/modes.json)
enum { F_SLAYER, F_CTF, F_ASSAULT, F_KING, F_ODDBALL, F_TERR, F_STOCK, F_HH, F_JUGG, F_INFECTION, F_RACE, F_INVASION,
       F_INSANE, F_N };
static const char* FAMILY_KEY[F_N] = { "slayer", "ctf", "assault", "koth", "oddball", "territories", "stockpile",
                                       "headhunter", "juggernaut", "infection", "race", "invasion", "insane" };
static const char* FAMILY_NAME[F_N] = { "Slayer", "Capture the Flag", "Assault", "King of the Hill", "Oddball",
                                        "Territories", "Stockpile", "Headhunter", "Juggernaut", "Infection", "Race",
                                        "Invasion", "Insane" };
static int family_of(int category) {
    switch (category) {
    case 0: return F_CTF; case 1: return F_SLAYER; case 2: return F_ODDBALL; case 3: return F_KING; case 4: return F_JUGG;
    case 5: return F_INFECTION; case 7: return F_RACE; case 15: return F_TERR; case 16: return F_ASSAULT;
    case 21: return F_STOCK; case 22: return F_HH; case 23: return F_INVASION; default: return F_INSANE;
    }
}

// gametypes' names as the vote shows them (MCC's own names otherwise, in title case)
static const char* GT_SHOW[][2] = {
    {"TU TEAM SLAYER DMR", "Team Slayer"}, {"SWAT", "Team SWAT"}, {"CAPTURE THE FLAG", "Capture the Flag"},
    {"ONE FLAG CTF", "One Flag CTF"}, {"MULTI FLAG CTF", "Multi Flag CTF"}, {"NEUTRAL FLAG CTF", "Neutral Flag"},
    {"TU MULTI FLAG CTF", "Multi Flag CTF"}, {"TU ONE FLAG CTF", "One Flag CTF"},
    // (Nov 16) the owner's own TU gametypes
    {"TU MULTI FLAG CTF (4-10)", "Multi Flag CTF"}, {"TU ONE FLAG CTF (4-10)", "One Flag CTF"},
    {"TU NEUTRAL BOMB ASSAULT (4-10)", "Neutral Bomb"}, {"TU TEAM CRAZY KING (4-10)", "Team Crazy King"},
    {"TU TEAM ODDBALL", "Team Oddball"}, {"TU FFA CRAZY KING", "Crazy King"}, {"CTU 5-PLOT TERRITORIES", "Territories"},
    {"KING OF THE HILL", "Team King"}, {"CRAZY KING", "Team Crazy King"}, {"TU CRAZY KING", "Team Crazy King (TU)"},
    {"ODDBALL", "Team Oddball"}, {"TU ODDBALL", "Team Oddball (TU)"}, {"HEADHUNTER", "Team Headhunter"},
    {"ONE BOMB ASSAULT", "One Bomb"}, {"NEUTRAL BOMB ASSAULT", "Neutral Bomb"}, {"TU ONE BOMB ASSAULT", "One Bomb (TU)"},
    {"TU MULTI BOMB ASSAULT", "Multi Bomb (TU)"}, {"3-PLOT TERRITORIES", "3 Plot Territories"},
    {"TU 3-PLOT TERRITORIES", "3 Plot Territories (TU)"}, {"TU STOCKPILE", "Stockpile (TU)"},
    {"TU TERRITORIES", "Territories (TU)"}, {"TU HEADHUNTER", "Team Headhunter (TU)"} };
// team games when MCC's own flag could not be read (pg_lobby.cpp: its SLAYER and CAPTURE THE FLAG check)
static const char* TEAM_GAMES[] = { "TU TEAM SLAYER DMR", "SWAT", "CAPTURE THE FLAG", "ONE FLAG CTF", "MULTI FLAG CTF",
    "NEUTRAL FLAG CTF", "TU MULTI FLAG CTF", "TU ONE FLAG CTF", "ASSAULT", "ONE BOMB ASSAULT", "NEUTRAL BOMB ASSAULT",
    "TU MULTI BOMB ASSAULT", "TU ONE BOMB ASSAULT", "STOCKPILE", "TU STOCKPILE", "TERRITORIES", "3-PLOT TERRITORIES",
    "TU TERRITORIES", "TU 3-PLOT TERRITORIES" };

// ------------------------------------------------------------------ playlists
struct pl_gametype { std::string name; int weight; };
struct playlist {
    const char* key;             // proving_grounds.ini prefix
    const char* title;           // "ARENA"
    const char* blurb;
    int size;                    // players a team
    std::vector<pl_gametype> gametypes;
    std::vector<std::string> maps;
};
static playlist g_pl[2];

static void default_playlists() {
    playlist& a = g_pl[0];
    a.key = "arena"; a.title = "ARENA"; a.size = 4;
    a.blurb = "Four on four on Reach's tightest maps. Team Slayer most of all, with objective games in the mix.";
    a.gametypes = { {"TU TEAM SLAYER DMR", 5}, {"SWAT", 1}, {"ONE FLAG CTF", 1}, {"MULTI FLAG CTF", 1},
                    {"CAPTURE THE FLAG", 1}, {"KING OF THE HILL", 1}, {"CRAZY KING", 1}, {"ODDBALL", 1},
                    {"HEADHUNTER", 1}, {"ONE BOMB ASSAULT", 1}, {"NEUTRAL BOMB ASSAULT", 1}, {"STOCKPILE", 1},
                    {"3-PLOT TERRITORIES", 1} };
    a.maps = { "Sword Base", "Countdown", "Zealot", "Powerhouse", "Reflection", "Boardwalk", "Anchor 9", "Condemned",
               "Asylum", "The Cage", "Pinnacle", "Beaver Creek", "Damnation", "Hang 'Em High", "Prisoner" };
    playlist& b = g_pl[1];
    b.key = "btb"; b.title = "BIG TEAM BATTLE"; b.size = 8;
    b.blurb = "Eight on eight on Reach's biggest battlefields. Vehicles, objectives and Team Slayer.";
    b.gametypes = { {"TU TEAM SLAYER DMR", 5}, {"MULTI FLAG CTF", 1}, {"CAPTURE THE FLAG", 1}, {"ONE BOMB ASSAULT", 1},
                    {"NEUTRAL BOMB ASSAULT", 1}, {"STOCKPILE", 1}, {"TERRITORIES", 1}, {"HEADHUNTER", 1} };
    b.maps = { "Boneyard", "Spire", "Breakpoint", "Tempest", "Highlands", "Hemorrhage", "Paradiso", "Ridgeline",
               "Breakneck", "Headlong", "Timberland" };
}

// ------------------------------------------------------------------ settings (native\bin\proving_grounds.ini)
static wchar_t g_bin[MAX_PATH], g_root[MAX_PATH];
static int g_size = 4;                           // 4 Arena, 8 Big Team Battle
static int g_vote_s = 15;
static char g_party[8][16];
static int g_nparty;
static bool g_loaded;

static void find_dirs() {
    HMODULE me = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            (LPCWSTR)&find_dirs, &me))
        return;
    DWORD n = GetModuleFileNameW(me, g_bin, MAX_PATH);
    wchar_t* slash = n && n < MAX_PATH ? wcsrchr(g_bin, L'\\') : nullptr;
    if (!slash) { g_bin[0] = 0; return; }
    *slash = 0;
    wcscpy_s(g_root, g_bin);
    wchar_t* s = wcsstr(g_root, L"\\native\\bin");
    if (s) *s = 0;
}

static void ini_path(wchar_t* out) {
#ifdef PG_PREVIEW
    if (GetEnvironmentVariableW(L"PG_INI", out, MAX_PATH)) return;   // (the preview's checks: a scratch file)
#endif
    swprintf_s(out, MAX_PATH, L"%s\\proving_grounds.ini", g_bin);
}

static void trim(char* s) {
    size_t n = strlen(s);
    while (n && (s[n - 1] == '\r' || s[n - 1] == '\n' || s[n - 1] == ' ' || s[n - 1] == '\t')) s[--n] = 0;
    size_t k = 0;
    while (s[k] == ' ' || s[k] == '\t') k++;
    if (k) memmove(s, s + k, n - k + 1);
}

static void squash(const char* in, char* out, int cap);

static void load_settings() {
    g_loaded = true;
    find_dirs();
    default_playlists();
    wchar_t p[MAX_PATH];
    ini_path(p);
    FILE* f = nullptr;
    if (_wfopen_s(&f, p, L"r") || !f) return;
    bool replaced[2][2] = {};                    // (a playlist's gametype / map lines replace its defaults)
    // (Nov 16, the owner: "Can I add my own maps and modes") addgametype= / addmap= add to a list, removegametype= /
    // removemap= take out of it; applied after every line is read
    std::vector<pl_gametype> add_gt[2];
    std::vector<std::string> add_map[2], drop_gt[2], drop_map[2];
    char line[256];
    g_nparty = 0;
    while (fgets(line, sizeof line, f)) {
        trim(line);
        if (!line[0] || line[0] == '#' || line[0] == ';') continue;
        int v;
        if (sscanf_s(line, "size=%d", &v) == 1) { g_size = v >= 8 ? 8 : 4; continue; }
        if (sscanf_s(line, "vote_seconds=%d", &v) == 1) { g_vote_s = v < 5 ? 5 : v > 60 ? 60 : v; continue; }
        if (!strncmp(line, "party=", 6)) {
            if (g_nparty < 8 && line[6]) strncpy_s(g_party[g_nparty++], line + 6, _TRUNCATE);
            continue;
        }
        for (int k = 0; k < 2; k++) {
            size_t kl = strlen(g_pl[k].key);
            if (_strnicmp(line, g_pl[k].key, kl) || line[kl] != '.') continue;
            const char* rest = line + kl + 1;
            bool add = !_strnicmp(rest, "add", 3), drop = !_strnicmp(rest, "remove", 6);
            const char* what = add ? rest + 3 : drop ? rest + 6 : rest;
            if (!_strnicmp(what, "gametype=", 9)) {
                char name[96];
                strncpy_s(name, what + 9, _TRUNCATE);
                int w = 1;
                char* star = strrchr(name, '*');
                if (star) { w = atoi(star + 1); *star = 0; trim(name); if (w < 1) w = 1; }
                if (!name[0]) continue;
                if (add) add_gt[k].push_back({ name, w });
                else if (drop) drop_gt[k].push_back(name);
                else {
                    if (!replaced[k][0]) { g_pl[k].gametypes.clear(); replaced[k][0] = true; }
                    g_pl[k].gametypes.push_back({ name, w });
                }
            } else if (!_strnicmp(what, "map=", 4)) {
                if (!what[4]) continue;
                if (add) add_map[k].push_back(what + 4);
                else if (drop) drop_map[k].push_back(what + 4);
                else {
                    if (!replaced[k][1]) { g_pl[k].maps.clear(); replaced[k][1] = true; }
                    g_pl[k].maps.push_back(what + 4);
                }
            }
        }
    }
    fclose(f);
    for (int k = 0; k < 2; k++) {
        playlist& pl = g_pl[k];
        for (const std::string& d : drop_gt[k])
            pl.gametypes.erase(std::remove_if(pl.gametypes.begin(), pl.gametypes.end(),
                               [&](const pl_gametype& g) { return !_stricmp(g.name.c_str(), d.c_str()); }), pl.gametypes.end());
        for (const pl_gametype& a : add_gt[k]) {
            bool have = false;
            for (pl_gametype& g : pl.gametypes) if (!_stricmp(g.name.c_str(), a.name.c_str())) { g.weight = a.weight; have = true; }
            if (!have) pl.gametypes.push_back(a);
        }
        for (const std::string& d : drop_map[k]) {
            char a[64], b[64];
            squash(d.c_str(), a, sizeof a);
            pl.maps.erase(std::remove_if(pl.maps.begin(), pl.maps.end(),
                          [&](const std::string& m) { squash(m.c_str(), b, sizeof b); return !strcmp(a, b); }), pl.maps.end());
        }
        for (const std::string& a : add_map[k]) pl.maps.push_back(a);
    }
}

// size, vote_seconds and the party written; every other line (the playlists) kept as it was
static void save_settings() {
    wchar_t p[MAX_PATH];
    ini_path(p);
    std::vector<std::string> keep;
    FILE* f = nullptr;
    bool had = false;
    if (_wfopen_s(&f, p, L"r") == 0 && f) {
        had = true;
        char line[256];
        while (fgets(line, sizeof line, f)) {
            char t[256];
            strcpy_s(t, line);
            trim(t);
            if (!strncmp(t, "size=", 5) || !strncmp(t, "vote_seconds=", 13) || !strncmp(t, "party=", 6)) continue;
            line[strcspn(line, "\r\n")] = 0;
            keep.push_back(line);
        }
        fclose(f);
    }
    if (_wfopen_s(&f, p, L"w") || !f) return;
    if (!had) {
        fprintf(f, "# Proving Grounds (native/proving_grounds.cpp): your playlist, vote time and invited party.\n"
                   "# The playlists (arena = 4v4, btb = 8v8) can be changed here, names as in lobby_library.txt:\n"
                   "#   arena.addmap=HEMORRHAGE btb           (adds a map; your own Forge maps too)\n"
                   "#   arena.addgametype=MLG Team Slayer v7*2 (adds a gametype; *2 = twice as likely; team games only)\n"
                   "#   arena.removemap=Condemned             (takes one out)\n"
                   "#   arena.removegametype=SWAT\n"
                   "#   arena.map=Sword Base                  (map= / gametype= lines replace the whole list instead)\n");
    }
    fprintf(f, "size=%d\nvote_seconds=%d\n", g_size, g_vote_s);
    for (int i = 0; i < g_nparty; i++) fprintf(f, "party=%s\n", g_party[i]);
    for (const std::string& s : keep) fprintf(f, "%s\n", s.c_str());
    fclose(f);
}

// ------------------------------------------------------------------ names, pictures
static void squash(const char* in, char* out, int cap) {        // lower case, letters and digits only
    int k = 0;
    for (; *in && k < cap - 1; in++) {
        char c = *in;
        if (c >= 'A' && c <= 'Z') c += 32;
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) out[k++] = c;
    }
    out[k] = 0;
}

const char* pg_map_name(const char* mcc_name, const char* key, char* out, int cap) {
    int n = 0;
    if (sscanf_s(mcc_name, "$HReach_MPMap_R-%d", &n) == 1 && n >= 1 && n <= 25) strcpy_s(out, cap, R_MAPS[n]);
    else {
        strcpy_s(out, cap, mcc_name);
        for (const char* tail : { " Anniversary", " Anniv" }) {
            size_t a = strlen(out), b = strlen(tail);
            if (a > b && !_stricmp(out + a - b, tail)) out[a - b] = 0;
        }
        if (!out[0] && key[0]) strcpy_s(out, cap, key);
    }
    return out;
}

static void gametype_show(const char* mcc_name, char* out, int cap) {
    for (auto& g : GT_SHOW) if (!strcmp(g[0], mcc_name)) { strcpy_s(out, cap, g[1]); return; }
    int k = 0;
    bool start = true;
    for (const char* c = mcc_name; *c && k < cap - 1; c++) {
        char ch = *c;
        if (ch >= 'A' && ch <= 'Z' && !start) ch += 32;
        start = ch == ' ' || ch == '-';
        out[k++] = ch;
    }
    out[k] = 0;
}

static const map_feel* feel_of(const char* shown) {
    char a[64], b[64];
    squash(shown, a, sizeof a);
    for (const map_feel& m : FEEL) { squash(m.name, b, sizeof b); if (!strcmp(a, b)) return &m; }
    static const map_feel other = { "", 1, 0, 1 };
    return &other;
}

struct pic { std::wstring path; unsigned long long tex; int w, h; bool tried; };
static std::deque<pic> g_pics;                   // (a deque: a picture's place never moves)
static unsigned long long (*g_make)(int, int, const unsigned char*);

static const pic* picture(const wchar_t* path) {
    for (const pic& p : g_pics) if (p.path == path) return p.tex ? &p : nullptr;
    pic p{ path, 0, 0, 0, true };
    int w = 0, h = 0;
    unsigned char* px = g_make ? hb_image_rgba(path, &w, &h) : nullptr;
    if (px) { p.tex = g_make(w, h, px); p.w = w; p.h = h; free(px); }
    g_pics.push_back(p);
    return p.tex ? &g_pics.back() : nullptr;
}

// a map's preview (MCC's own, tools/service_record_art.py pictures): its picture name without "HReachMP_"
static const pic* map_picture(const char* key) {
    if (!key || !key[0]) return nullptr;
    const char* k = strncmp(key, "HReachMP_", 9) == 0 ? key + 9 : key;
    char low[64];
    squash(k, low, sizeof low);
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\service_record\\art\\maps\\%S.jpg", g_bin, low);
    return picture(p);
}

static int g_family_icon[F_N];                   // the owner's gametype icon numbers (modes.json), 0 none
static bool g_icons_read;
static void read_icons() {
    g_icons_read = true;
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\tools\\service_record_site\\modes.json", g_root);
    FILE* f = nullptr;
    if (_wfopen_s(&f, p, L"r") || !f) return;
    std::string s;
    char buf[1024];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, f)) > 0) s.append(buf, n);
    fclose(f);
    size_t at = s.find("\"icons\"");
    if (at == std::string::npos) return;
    for (int k = 0; k < F_N; k++) {
        std::string want = std::string("\"") + FAMILY_KEY[k] + "\":";
        size_t q = s.find(want, at);
        if (q != std::string::npos) g_family_icon[k] = atoi(s.c_str() + q + want.size());
    }
}
static const pic* family_picture(int fam) {
    if (!g_icons_read) read_icons();
    if (fam < 0 || fam >= F_N || !g_family_icon[fam]) return nullptr;
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\service_record\\art\\modes\\%d.png", g_bin, g_family_icon[fam]);
    return picture(p);
}

// ------------------------------------------------------------------ MCC's library, as the playlists use it
struct option { int map, gametype; char map_name[48], gt_name[48], map_key[40]; int family; const map_feel* feel; };
static pg_entry g_lmaps[160], g_lgts[160];
static int g_nlmaps, g_nlgts;
static uint32_t g_lseq;

static void library() {
    uint32_t s = pg_lobby_seq();
    if (s == g_lseq) return;
    g_lseq = s;
    g_nlmaps = pg_lobby_maps(g_lmaps, 160);
    g_nlgts = pg_lobby_gametypes(g_lgts, 160);
}

static bool team_game(const pg_entry& g) {
    if (g.teams >= 0) return g.teams == 1;
    for (const char* t : TEAM_GAMES) if (!strcmp(t, g.name)) return true;
    return false;
}

// the playlist's gametypes MCC has (team games), weights kept; its maps MCC has
struct pool_gt { const pg_entry* e; int weight; };
static void playlist_pool(const playlist& pl, std::vector<pool_gt>& gts, std::vector<const pg_entry*>& maps) {
    gts.clear(); maps.clear();
    // (Nov 16, the owner added his own TU gametypes, two with MCC's built-in names) a name MCC has twice: the player's
    // own (kind 3) wins over MCC's built-in
    for (const pl_gametype& w : pl.gametypes) {
        const pg_entry* pick = nullptr;
        for (int i = 0; i < g_nlgts; i++)
            if (!_stricmp(g_lgts[i].name, w.name.c_str()) && team_game(g_lgts[i]) && (!pick || (g_lgts[i].kind == 3 && pick->kind != 3)))
                pick = &g_lgts[i];
        if (pick) gts.push_back({ pick, w.weight });
    }
    for (const std::string& want : pl.maps) {
        char a[64], b[64], shown[64];
        squash(want.c_str(), a, sizeof a);
        for (int i = 0; i < g_nlmaps; i++) {
            pg_map_name(g_lmaps[i].name, g_lmaps[i].key, shown, sizeof shown);
            squash(shown, b, sizeof b);
            if (!strcmp(a, b)) { maps.push_back(&g_lmaps[i]); break; }
        }
    }
}

static void make_option(option& o, const pg_entry* m, const pg_entry* g) {
    memset(&o, 0, sizeof o);
    o.map = m->id; o.gametype = g->id;
    pg_map_name(m->name, m->key, o.map_name, sizeof o.map_name);
    gametype_show(g->name, o.gt_name, sizeof o.gt_name);
    strcpy_s(o.map_key, m->key);
    o.family = family_of(g->category);
    o.feel = feel_of(o.map_name);
}

// ------------------------------------------------------------------ randomness, the bots' tastes
// (Nov 16, the owner: "is the starting votes always the same three at the restart of the mod?" They were: a fixed
// seed) seeded from the clock on first use, so each MCC start draws its own options, searches and bots' rolls
static uint32_t g_rng = 0;
static uint32_t rnd() {
    if (!g_rng) {
        LARGE_INTEGER q;
        QueryPerformanceCounter(&q);
        g_rng = ((uint32_t)q.QuadPart ^ (uint32_t)(q.QuadPart >> 32) ^ (uint32_t)GetTickCount64() * 2654435761u ^
                 GetCurrentProcessId() * 40503u) | 1;
    }
    g_rng ^= g_rng << 13; g_rng ^= g_rng >> 17; g_rng ^= g_rng << 5; return g_rng;
}
static float frnd() { return (rnd() & 0xFFFFFF) / 16777216.0f; }
static uint32_t hash_of(const char* s, uint32_t salt) {
    uint32_t h = 2166136261u ^ salt;
    for (; *s; s++) { char c = *s; if (c >= 'A' && c <= 'Z') c += 32; h = (h ^ (uint8_t)c) * 16777619u; }
    h ^= h >> 13; h *= 0x5bd1e995; h ^= h >> 15;
    return h;
}
static float hfloat(const char* name, uint32_t salt) { return (hash_of(name, salt) & 0xFFFF) / 65535.0f; }

// how much a bot leans into competitive play: its difficulty's, a little of its own
static float sweat_of(const hb_bot& b) {
    static const float BY_TIER[HB_TIERS] = { -0.7f, -0.35f, 0.0f, 0.45f, 0.2f, 0.85f, 0.45f, 0.3f, 0.65f };
    return (b.tier < HB_TIERS ? BY_TIER[b.tier] : 0.0f) + (hfloat(b.name, 7) - 0.5f) * 0.4f;
}

// a bot's liking of an option (higher better): its own taste in kinds of game, its favourite and least favourite
// maps (from its name: the same every evening), its play style, how sweaty it is
static float liking(const hb_bot& b, const option& o, const std::vector<const pg_entry*>& maps) {
    float s = (hfloat(b.name, 100 + o.family) - 0.45f) * 1.1f;            // its kinds of game
    if (o.family == F_SLAYER) s += 0.35f;                                  // (most players' favourite)
    float sweat = sweat_of(b);
    const map_feel* f = o.feel;
    s += sweat * (f->comp - 1) * 0.55f;
    if (o.family == F_SLAYER) s += sweat * 0.35f;
    if (o.family == F_INVASION || o.family == F_INFECTION) s -= sweat * 0.3f;
    const char* style = style_name(b.style);
    float wheels = (hfloat(b.name, 11) - 0.4f) * 0.8f, big = (hfloat(b.name, 12) - 0.5f) * 0.7f;
    if (!_stricmp(style, "wheelman")) wheels += 0.9f;
    if (!_stricmp(style, "sniper")) big += 0.6f;
    if (!_stricmp(style, "rusher")) big -= 0.5f;
    s += wheels * (f->vehicles - 1) * 0.45f + big * (f->size - 1) * 0.35f;
    if (!maps.empty()) {                                                   // its favourite and least favourite map
        int n = (int)maps.size();
        int fav = (int)(hash_of(b.name, 21) % n), fav2 = (int)(hash_of(b.name, 22) % n), hate = (int)(hash_of(b.name, 23) % n);
        if (maps[fav]->id == o.map) s += 1.25f;
        else if (maps[fav2]->id == o.map) s += 0.5f;
        if (maps[hate]->id == o.map && hate != fav) s -= 0.9f;
    }
    return s;
}

// its odds for each option (and None of the Above, last), then its roll
static int bot_vote(const hb_bot& b, const option* opt, int n, bool nota, const std::vector<const pg_entry*>& maps) {
    float p[4], sum = 0, best = 0;
    for (int i = 0; i < n; i++) { p[i] = expf(liking(b, opt[i], maps) / 0.45f); sum += p[i]; }
    for (int i = 0; i < n; i++) { p[i] /= sum; if (p[i] > best) best = p[i]; }
    float pn = 0;
    if (nota) {
        pn = 0.04f + 0.6f * (0.45f - best > 0 ? 0.45f - best : 0) + (sweat_of(b) < -0.4f ? 0.03f : 0);
        if (pn > 0.3f) pn = 0.3f;
        for (int i = 0; i < n; i++) p[i] *= 1 - pn;
    }
    float r = frnd(), acc = 0;
    for (int i = 0; i < n; i++) { acc += p[i]; if (r < acc) return i; }
    return nota ? n : n - 1;
}

// ------------------------------------------------------------------ the session
enum stage { S_OFF, S_MENU, S_SEARCH, S_VOTE, S_RESULT, S_LAUNCH, S_PLAYING, S_ERROR, S_CREDITS };
static stage g_stage = S_OFF;
static bool g_invite;                            // the invite list over the menu
static bool g_chal;                              // (Nov 17) the Challenges page in place of the menu
static bool g_comm;                              // (Nov 19) the Commendations page in place of the menu
static int g_focus_after = -1;                   // (Nov 19) the focus to give the next frame (-1 none)
static bool g_lobby_vis;                         // MCC's lobby on screen, last frame
static double g_t0;                              // the stage's start
static bool g_between;                           // the search screen as the lobby between matches
static float g_search_s;
static float g_arrive[HB_ROSTER_MAX];            // when each seat's bot comes into the lobby (search)
static bool g_was_seated[HB_ROSTER_MAX];         // (between matches: stayed from the last one)
static uint8_t g_pinned[HB_ROSTER_MAX];
static char g_error[200];
static double g_lobby_seen_at;                   // (playing: the lobby back without a match's end)
static bool g_after_due;

// the vote
static option g_opt[3];
static int g_nopt;
static bool g_nota_open;                         // None of the Above offered (the first round)
static int g_round;
static int g_vote_me = -1;                       // the person's vote (3: None of the Above)
static int g_vote_bot[HB_ROSTER_MAX];            // each seat's (-1 not yet)
static float g_vote_at[HB_ROSTER_MAX];           // when it votes (-1 never)
static int g_winner;
static int g_check_ticket;
static std::vector<std::pair<int, int>> g_cands;
static int g_last_map = -1, g_last_gt = -1;
static double g_launch_t;
static bool g_need_votes;                        // (the second round: the bots decide once its options are in)
static int g_redraws;                            // the options drawn again since MCC last accepted some
enum { RETRY_SEARCH, RETRY_VOTE, RETRY_LAUNCH };
static int g_retry = RETRY_SEARCH;               // what the error screen's TRY AGAIN does
static int g_pool_count;                         // the pool's bots, each once
static uint32_t g_vote_key;                      // (Nov 18) a new number each vote round: a friend's vote names it

// (Nov 17, the owner: a friend in the lobby, "Just balance him to a team like normal matchmaking would") the other
// people in MCC's lobby as the last deal counted them: each takes a bot's seat on the team MCC has them on (one not
// yet on a team: the team with fewer people), and the bots are dealt by points around everyone. Proving Grounds cannot
// move a real player between MCC's teams; it builds the teams around where MCC put them. Dealt again (the bots kept)
// when someone joins, leaves or changes team before the game starts
static const int PG_PEOPLE = 8;
static int g_npeople;
static uint64_t g_people_id[PG_PEOPLE];
static char g_people_name[PG_PEOPLE][32];
static int g_people_team[PG_PEOPLE];             // the team the deal counted them on
static int g_me_team;                            // the player's, as dealt
static uint64_t g_people_sig;                    // the people and MCC's teams as last dealt
static double g_people_check;
// (Nov 18, pg_link.cpp) each person's vote this round (-1 none): the host's copy has a joined friend's from the link,
// a friend's copy (following) the host's and the others' from the host's state
static int g_people_vote[PG_PEOPLE] = { -1, -1, -1, -1, -1, -1, -1, -1 };
static bool g_follow;                            // this PC shows the host's screens (a joined friend's copy)
static hb_roster g_f_roster;                     // (following) the host's lobby bots
static char g_f_clan[HB_ROSTER_MAX][8];          // (following) their clan tags, as the host's profiles have them
static const char* seat_clan(const hb_roster& r, int i) { return g_follow ? g_f_clan[i] : profile_clan_of(r.bot[i].name); }

static const playlist& cur_pl() { return g_pl[g_size >= 8 ? 1 : 0]; }

static uint64_t people_now(uint64_t* ids, char (*names)[32], int* teams, int* n) {   // MCC's list now, and its sig
    *n = mcc_session_people(ids, names, teams, PG_PEOPLE);
    uint64_t h = 1469598103934665603ull ^ (uint64_t)(mcc_player_team() + 2);
    for (int i = 0; i < *n; i++) { h ^= ids[i]; h *= 1099511628211ull; h ^= (uint64_t)(teams[i] + 2); h *= 1099511628211ull; }
    return h;
}

static bool g_f_hide;                            // (following) Esc / B put the host's screens away till its next stage
bool pg_running() { return g_stage != S_OFF; }
bool pg_visible() { return g_lobby_vis && g_stage != S_OFF && g_stage != S_PLAYING && !(g_follow && g_f_hide); }
bool pg_launching() { return g_stage == S_LAUNCH; }
bool pg_following() { return g_follow; }

static char g_pool_names[4096][16];
static int g_npool_names;

void pg_open() {
    if (g_follow) { g_f_hide = false; return; }  // (Nov 18: following the host: its screens back, no session here)
    load_settings();                             // (each time: proving_grounds.ini edits apply on the next open)
    g_npool_names = bot_pool_names(g_pool_names, 4096);
    g_pool_count = g_npool_names;
    g_stage = S_MENU;
    g_invite = false;
    g_chal = false;
    g_comm = false;
    g_t0 = ImGui::GetTime();
    logf("proving grounds: opened (%s)", cur_pl().title);
}

static void to_menu() { g_stage = S_MENU; g_invite = false; g_t0 = ImGui::GetTime(); }

void pg_back() {
    if (g_follow) {                              // (Nov 18: following: the host's screens away till its next stage;
        if (g_stage == S_CREDITS) { g_stage = S_SEARCH; return; }   // this PC's own credits: on to the host's lobby)
        g_f_hide = true;
        return;
    }
    if (g_invite) { g_invite = false; return; }
    if (g_chal) { g_chal = false; return; }
    if (g_comm) { g_comm = false; g_focus_after = 4; return; }   // (back on the menu's COMMENDATIONS)
    switch (g_stage) {
    case S_MENU: g_stage = S_OFF; logf("proving grounds: closed"); break;
    case S_SEARCH: case S_VOTE: case S_ERROR: to_menu(); break;
    case S_CREDITS: g_stage = S_SEARCH; g_t0 = ImGui::GetTime(); break;   // (Nov 17: the credits: on to the lobby)
    default: break;                              // (the result and the countdown: MCC's lobby is starting the game)
    }
}

// three options MCC accepts: candidates drawn by weight (not the last game, a map at most twice), checked by MCC
static void draw_candidates() {
    library();
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    playlist_pool(cur_pl(), gts, maps);
    g_cands.clear();
    g_nopt = 0;
    if (gts.empty() || maps.empty()) { g_check_ticket = 0; return; }
    int total = 0;
    for (auto& g : gts) total += g.weight;
    for (int tries = 0; tries < 200 && (int)g_cands.size() < 24; tries++) {
        int r = (int)(rnd() % (uint32_t)total), k = 0;
        while (r >= gts[k].weight) { r -= gts[k].weight; k++; }
        const pg_entry* m = maps[rnd() % maps.size()];
        int gid = gts[k].e->id;
        if (m->id == g_last_map && gid == g_last_gt) continue;
        bool dup = false;
        for (auto& c : g_cands) dup |= c.first == m->id && c.second == gid;
        if (!dup) g_cands.push_back({ m->id, gid });
    }
    int mp[64], gt[64], n = (int)g_cands.size();
    for (int i = 0; i < n; i++) { mp[i] = g_cands[i].first; gt[i] = g_cands[i].second; }
    g_check_ticket = pg_lobby_check(mp, gt, n);
}

// the checked candidates into three options (a map at most once when there is a choice)
static bool take_options() {
    if (g_nopt) return true;
    if (!g_check_ticket) return false;
    uint8_t ok[64] = {};
    if (!pg_lobby_checked(g_check_ticket, ok, (int)g_cands.size())) return false;
    std::vector<int> good;
    for (int i = 0; i < (int)g_cands.size(); i++) if (ok[i]) good.push_back(i);
    for (int pass = 0; pass < 2 && g_nopt < 3; pass++)
        for (int i : good) {
            if (g_nopt >= 3) break;
            bool used = false;
            for (int k = 0; k < g_nopt; k++)
                used |= pass == 0 ? g_opt[k].map == g_cands[i].first || g_opt[k].gametype == g_cands[i].second
                                  : g_opt[k].map == g_cands[i].first && g_opt[k].gametype == g_cands[i].second;
            if (used) continue;
            const pg_entry *m = nullptr, *g = nullptr;
            for (int j = 0; j < g_nlmaps; j++) if (g_lmaps[j].id == g_cands[i].first) m = &g_lmaps[j];
            for (int j = 0; j < g_nlgts; j++) if (g_lgts[j].id == g_cands[i].second) g = &g_lgts[j];
            if (m && g) make_option(g_opt[g_nopt++], m, g);
        }
    if (g_nopt) { g_redraws = 0; return true; }
    // (Nov 16, live: the second game's vote had none) MCC answered with no pair it accepts: drawn again from MCC's
    // lists as they are now (after a match MCC reloads them when its lobby comes back), a few times
    if (g_redraws < 8) {
        logf("proving grounds: MCC accepted none of %d options: drawing again (%d)", (int)g_cands.size(), g_redraws + 1);
        g_redraws++;
        draw_candidates();
    }
    return false;
}

static void start_vote(const hb_roster& r, bool new_round) {
    g_stage = S_VOTE;
    g_t0 = ImGui::GetTime();
    g_vote_me = -1;
    g_vote_key++;
    if (!new_round) { g_round = 1; g_nota_open = true; }
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    playlist_pool(cur_pl(), gts, maps);
    for (int i = 0; i < r.n && i < HB_ROSTER_MAX; i++) {
        float at = 0.8f + powf(frnd(), 1.6f) * (g_vote_s - 3.0f);       // (most early, some late)
        g_vote_at[i] = frnd() < 0.05f ? -1.0f : at;                       // (one in twenty never votes)
        int v = bot_vote(r.bot[i], g_opt, g_nopt, g_nota_open, maps);
        g_vote_bot[i] = -2 - (v >= g_nopt ? 3 : v);                       // (decided, shown at its time; 3 None of the Above)
    }
}

static int shown_vote(int seat, float t) {        // a seat's vote as the screen shows it at t s into the round
    if (g_vote_at[seat] < 0 || t < g_vote_at[seat]) return -1;
    return -2 - g_vote_bot[seat];
}

static void counts(const hb_roster& r, float t, int out[4]) {
    memset(out, 0, sizeof(int) * 4);
    for (int i = 0; i < r.n && i < HB_ROSTER_MAX; i++) { int v = shown_vote(i, t); if (v >= 0 && v < 4) out[v]++; }
    if (g_vote_me >= 0 && g_vote_me < 4) out[g_vote_me]++;
    for (int k = 0; k < g_npeople && k < PG_PEOPLE; k++)  // (Nov 18: a joined friend's vote, over the link)
        if (g_people_vote[k] >= 0 && g_people_vote[k] < 4) out[g_people_vote[k]]++;
}

static void tally(const hb_roster& r) {
    int c[4];
    counts(r, 1e9f, c);
    int players = r.n + 1 + g_npeople;                   // (a friend votes over the link, Nov 18; without it, as one not voting)
    if (g_nota_open && c[3] * 2 > players) {     // (Reach: a majority on None of the Above, new options, no veto)
        logf("proving grounds: None of the Above (%d of %d): new options", c[3], players);
        g_nota_open = false;
        g_round = 2;
        g_nopt = 0;
        draw_candidates();
        g_stage = S_VOTE;
        g_t0 = ImGui::GetTime();
        for (int i = 0; i < HB_ROSTER_MAX; i++) { g_vote_bot[i] = -1; g_vote_at[i] = -1; }
        g_vote_me = -1;
        g_vote_key++;
        g_need_votes = true;
        return;
    }
    int best = -1;
    std::vector<int> tied;
    for (int i = 0; i < g_nopt; i++) {
        if (c[i] > best) { best = c[i]; tied.clear(); }
        if (c[i] == best) tied.push_back(i);
    }
    g_winner = tied.empty() ? 0 : tied[rnd() % tied.size()];
    logf("proving grounds: vote: %s on %s (%d %d %d, none %d)", g_opt[g_winner].gt_name, g_opt[g_winner].map_name, c[0],
         g_nopt > 1 ? c[1] : 0, g_nopt > 2 ? c[2] : 0, c[3]);
    g_stage = S_RESULT;
    g_t0 = ImGui::GetTime();
}

// the lobby's arrivals: kept bots (between matches) and the party at once, the rest over the search, a clan together
static void schedule(const hb_roster& r, float total, const bool* seated_before) {
    std::vector<std::vector<int>> groups;
    std::vector<std::string> keys;
    for (int i = 0; i < r.n; i++) {
        if (g_pinned[i] || (seated_before && seated_before[i])) { g_arrive[i] = 0; continue; }
        const char* c = profile_clan_of(r.bot[i].name);
        int k = -1;
        if (c[0]) for (int j = 0; j < (int)keys.size(); j++) if (!_stricmp(keys[j].c_str(), c)) k = j;
        if (k < 0) { groups.push_back({}); keys.push_back(c); k = (int)groups.size() - 1; }
        groups[k].push_back(i);
    }
    for (int j = (int)groups.size() - 1; j > 0; j--) std::swap(groups[j], groups[rnd() % (j + 1)]);
    int n = (int)groups.size();
    std::vector<float> at(n);
    for (int j = 0; j < n; j++) at[j] = 1.2f + frnd() * (total - 1.8f);
    std::sort(at.begin(), at.end());
    for (int j = 0; j < n; j++) for (int i : groups[j]) g_arrive[i] = at[j];
}

// the person's team: the one MCC's lobby has them on (session_watch.cpp, Nov 17), else tools/play.py's
// bot_pool_humans.txt from the last team match (Red when none yet)
static int person_team() {
    int t = mcc_player_team();
    if (t == 0 || t == 1) return t;
    wchar_t dir[MAX_PATH];
    swprintf_s(dir, L"%s\\", g_bin);
    bot_pool_load(dir);
    return bot_pool_humans(1) > bot_pool_humans(0) ? 1 : 0;
}

// (Nov 17) the lobby dealt: the player, the friends who joined (each a bot's seat), the party, the bots by points
static int deal(hb_roster& r, int keep_pct, uint32_t difficulty) {
    int party_team = person_team(), teams[PG_PEOPLE];
    g_people_sig = people_now(g_people_id, g_people_name, teams, &g_npeople);
    int fresh = bot_pool_matchmake(r, g_size, g_party, g_nparty, party_team, keep_pct, difficulty, g_pinned, teams, g_npeople);
    g_me_team = party_team;
    for (int i = 0; i < g_npeople; i++) g_people_team[i] = teams[i];
    if (g_npeople) {
        char s[300];
        int at = sprintf_s(s, "proving grounds: people: you on team %d", party_team);
        for (int i = 0; i < g_npeople && at < 260; i++)
            at += sprintf_s(s + at, sizeof s - at, ", %s on team %d", g_people_name[i], g_people_team[i]);
        logf("%s (%d bots)", s, r.n);
    }
    return fresh;
}


static bool start_search(pg_env& e) {
    library();
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    playlist_pool(cur_pl(), gts, maps);
    g_retry = RETRY_SEARCH;
    if (!pg_lobby_live() || !g_nlmaps) {
        strcpy_s(g_error, "Proving Grounds needs MCC's Halo: Reach custom game lobby open behind it (Custom Multiplayer, Halo: Reach).");
        g_stage = S_ERROR; return false;
    }
    if (gts.empty() || maps.empty()) {
        sprintf_s(g_error, "None of the %s playlist's gametypes or maps were found in MCC's lists (see native\\bin\\lobby_library.txt).",
                  cur_pl().title);
        g_stage = S_ERROR; return false;
    }
    if (e.bots_enabled) *e.bots_enabled = 1;
    if (e.lidar_mode) *e.lidar_mode = 0;
    bot_pool_set_format((uint32_t)g_size);
    int fresh = deal(*e.roster, 0, e.difficulty);
    g_search_s = 4.0f + frnd() * 6.0f;
    schedule(*e.roster, g_search_s, nullptr);
    g_between = false;
    g_redraws = 0;
    draw_candidates();
    g_stage = S_SEARCH;
    g_t0 = ImGui::GetTime();
    logf("proving grounds: search (%s, %d bots, %d new, %.1f s)", cur_pl().title, e.roster->n, fresh, g_search_s);
    return true;
}

bool pg_after_match(hb_roster& r, uint32_t difficulty) {
    if (!pg_running() || g_stage == S_MENU || g_follow) return false;   // (following: the host deals its lobby)
    if (!g_loaded) load_settings();
    bool before[HB_ROSTER_MAX] = {};
    hb_roster old = r;
    bot_pool_set_format((uint32_t)g_size);
    int fresh = deal(r, 70, difficulty);                 // (the people as MCC's list has them; dealt again if that changes)
    for (int i = 0; i < r.n; i++)
        for (int k = 0; k < old.n; k++) if (!_stricmp(r.bot[i].name, old.bot[k].name)) before[i] = true;
    memcpy(g_was_seated, before, sizeof before);
    g_search_s = fresh ? 2.5f + frnd() * 3.0f : 1.5f;
    schedule(r, g_search_s, before);
    g_between = true;
    g_after_due = true;
    g_nopt = 0;
    g_check_ticket = 0;                                  // (the vote is drawn once MCC's lobby is back: pg_frame)
    logf("proving grounds: between matches: %d stayed, %d new", r.n - fresh, fresh);
    return true;
}

// ------------------------------------------------------------------ the Service Record's matches
// (Nov 17, the owner: the site's stats from "Matchmaking only") each match Proving Grounds started, named by MCC's own
// GameUniqueId in native\bin\service_record\matchmaking.txt once MCC's post-game report has it. tools/service_record.py
// counts only the matches that file names: a custom game played without Proving Grounds is not on the site.
static bool g_mark_due;                          // a match started here, its report not read yet
static uint64_t g_mark_from;                     // when it started (FILETIME, 10 s early)
static double g_mark_back, g_mark_check;         // the lobby back (ImGui time, 0: not yet); the last look at the report
static char g_credit_id[64];                     // (Nov 17) the match marked: its credits screen waits for its report

static uint64_t ft_u64(FILETIME f) { return ((uint64_t)f.dwHighDateTime << 32) | f.dwLowDateTime; }

static void mark_start() {
    FILETIME f;
    GetSystemTimeAsFileTime(&f);
    g_mark_due = true;
    g_mark_from = ft_u64(f) - 10ull * 10000000ull;
    g_mark_back = 0;
    g_credit_id[0] = 0;
}

// (Nov 17, the credits screen) the match counted now, not as the next one starts: tools/bot_career.py adds MCC's report
// to the ledger, then tools/service_record.py builds the site and last_match.txt, in the background.
// (Nov 18, the bot simulation; the owner: "have the simulation run as soon as my active match ends. So that it wont
// affect anything while voting and loading into another game") then tools/bot_sim.py plays the round of bot-only
// matches alongside it, and the two build again so the site has them; below normal priority, so MCC comes first.
// Returns the process (the caller closes it), or nullptr
static HANDLE run_tools(const wchar_t* steps) {
    wchar_t cmd[4096];
    swprintf_s(cmd, L"cmd.exe /c \"%s\"", steps);
    STARTUPINFOW si{};
    si.cb = sizeof si;
    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(nullptr, cmd, nullptr, nullptr, FALSE, CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS, nullptr,
                        nullptr, &si, &pi)) {
        logf("proving grounds: could not start the Service Record's tools (%lu)", GetLastError());
        return nullptr;
    }
    CloseHandle(pi.hThread);
    return pi.hProcess;
}

static void stats_build() {
    wchar_t py[MAX_PATH + 2], steps[3072], id[64];
    hb_python(g_root, py, MAX_PATH + 2);
    size_t n = 0;
    for (; g_credit_id[n] && n < 63; n++) {
        char c = g_credit_id[n];
        id[n] = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c == '-' ? (wchar_t)c : L'_';
    }
    id[n] = 0;
    swprintf_s(steps, L"%s -I \"%s\\tools\\bot_career.py\" --quiet & %s -I \"%s\\tools\\service_record.py\" --quiet"
                      L" & %s -I \"%s\\tools\\bot_sim.py\" --after %s --quiet & %s -I \"%s\\tools\\bot_career.py\" --quiet"
                      L" & %s -I \"%s\\tools\\service_record.py\" --quiet",
               py, g_root, py, g_root, py, g_root, id[0] ? id : L"none", py, g_root, py, g_root);
    HANDLE h = run_tools(steps);
    if (h) {
        CloseHandle(h);
        logf("proving grounds: counting the match for the Service Record, then the bots' round alongside it");
    }
}

// (Nov 18, the bot simulation's menu row; the owner: "a manual button ... ask each time") rounds played now, in the
// background: tools/bot_sim.py --rounds, then the career totals and the site; its sim_status.txt says how many matches
static HANDLE g_sim_proc;                        // the run, while it runs
static int g_sim_rounds = 1;                     // the rounds the row asks for (1 to 20)
static double g_sim_done_at = -1;                // when the last run ended (ImGui time; -1: not to show)
static int g_sim_made = -1;                      // its matches

static void sim_start() {
    wchar_t py[MAX_PATH + 2], steps[3072];
    hb_python(g_root, py, MAX_PATH + 2);
    swprintf_s(steps, L"%s -I \"%s\\tools\\bot_sim.py\" --rounds %d --quiet & %s -I \"%s\\tools\\bot_career.py\" --quiet"
                      L" & %s -I \"%s\\tools\\service_record.py\" --quiet",
               py, g_root, g_sim_rounds, py, g_root, py, g_root);
    g_sim_done_at = -1;
    g_sim_made = -1;
    g_sim_proc = run_tools(steps);
    if (g_sim_proc) logf("proving grounds: the bots play %d round(s) for the Service Record", g_sim_rounds);
}

static void sim_poll(double now) {
    if (!g_sim_proc || WaitForSingleObject(g_sim_proc, 0) != WAIT_OBJECT_0) return;
    CloseHandle(g_sim_proc);
    g_sim_proc = nullptr;
    g_sim_done_at = now;
    g_sim_made = -1;
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\service_record\\sim_status.txt", g_bin);
    FILE* f = nullptr;
    if (!_wfopen_s(&f, p, L"r") && f) {
        char line[128];
        while (fgets(line, sizeof line, f)) {
            int n;
            if (sscanf_s(line, "matches\t%d", &n) == 1) g_sim_made = n;
        }
        fclose(f);
    }
    logf("proving grounds: the bots' rounds are done (%d matches)", g_sim_made);
}

// once a second while due: MCC's report written since the match started, its id added to matchmaking.txt
static void mark_check(double now) {
    if (!g_mark_due || now - g_mark_check < 1.0) return;
    g_mark_check = now;
    if (g_mark_back && now - g_mark_back > 30.0) {           // (the lobby back 30 s with no report: a quit game)
        g_mark_due = false;
        logf("proving grounds: no post-game report of the last match: not on the Service Record");
        return;
    }
    wchar_t home[MAX_PATH], rp[MAX_PATH];
    if (!GetEnvironmentVariableW(L"USERPROFILE", home, MAX_PATH)) return;
    swprintf_s(rp, L"%s\\AppData\\LocalLow\\MCC\\Temporary\\mpcarnagereport1_3528_0_0.xml", home);
    WIN32_FILE_ATTRIBUTE_DATA a;
    if (!GetFileAttributesExW(rp, GetFileExInfoStandard, &a) || ft_u64(a.ftLastWriteTime) < g_mark_from) return;
    FILE* f = nullptr;
    char head[4096];
    if (_wfopen_s(&f, rp, L"rb") || !f) return;
    size_t n = fread(head, 1, sizeof head - 1, f);
    fclose(f);
    head[n] = 0;
    const char* k = strstr(head, "GameUniqueId=\"");
    const char* q = k ? strchr(k + 14, '"') : nullptr;
    if (!q || q - (k + 14) < 8 || q - (k + 14) > 63) return;   // (MCC still writing it: the next look)
    char id[64];
    memcpy(id, k + 14, q - (k + 14));
    id[q - (k + 14)] = 0;
    wchar_t dir[MAX_PATH], mp[MAX_PATH];
    swprintf_s(dir, L"%s\\service_record", g_bin);
    CreateDirectoryW(dir, nullptr);
    swprintf_s(mp, L"%s\\matchmaking.txt", dir);
    bool fresh = GetFileAttributesW(mp) == INVALID_FILE_ATTRIBUTES;
    if (_wfopen_s(&f, mp, L"a") || !f) return;
    if (fresh)
        fprintf(f, "# The matches Proving Grounds started (native/proving_grounds.cpp), by MCC's GameUniqueId: the Service\n"
                   "# Record (tools/service_record.py) counts only these. id<TAB>when<TAB>playlist\n");
    SYSTEMTIME st;
    GetLocalTime(&st);
    fprintf(f, "%s\t%04d-%02d-%02d %02d:%02d\t%s\n", id, st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, cur_pl().title);
    fclose(f);
    g_mark_due = false;
    logf("proving grounds: match %s on the Service Record (matchmaking.txt)", id);
    strcpy_s(g_credit_id, id);
    stats_build();
}

// (Nov 17) someone joined, left or changed team in MCC's lobby before the game starts: the lobby dealt again with every
// bot that still has a seat kept (a friend in: a bot of that team goes; out: one comes), each kept bot's arrival and
// vote kept with it, a new one arriving now and deciding its vote now. Checked once a second
static void redeal_if_people_changed(hb_roster& r, uint32_t difficulty, float t) {
    double now = ImGui::GetTime();
    if (now - g_people_check < 1.0) return;
    g_people_check = now;
    uint64_t ids[PG_PEOPLE];
    char names[PG_PEOPLE][32];
    int teams[PG_PEOPLE], n;
    if (people_now(ids, names, teams, &n) == g_people_sig) return;
    hb_roster old = r;
    float arrive[HB_ROSTER_MAX], vote_at[HB_ROSTER_MAX];
    int vote[HB_ROSTER_MAX];
    memcpy(arrive, g_arrive, sizeof arrive);
    memcpy(vote_at, g_vote_at, sizeof vote_at);
    memcpy(vote, g_vote_bot, sizeof vote);
    deal(r, 100, difficulty);
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    playlist_pool(cur_pl(), gts, maps);
    int fresh = 0;
    for (int i = 0; i < r.n; i++) {
        int was = -1;
        for (int k = 0; k < old.n && was < 0; k++) if (!_stricmp(r.bot[i].name, old.bot[k].name)) was = k;
        if (was >= 0) { g_arrive[i] = arrive[was]; g_vote_at[i] = vote_at[was]; g_vote_bot[i] = vote[was]; continue; }
        fresh++;
        g_arrive[i] = t + 0.4f;                          // (comes in now)
        g_vote_at[i] = -1;
        g_vote_bot[i] = -1;
        if (g_stage == S_VOTE && g_nopt) {               // (votes in a moment, as the others did)
            g_vote_at[i] = t + 0.8f + frnd() * 2.0f;
            int v = bot_vote(r.bot[i], g_opt, g_nopt, g_nota_open, maps);
            g_vote_bot[i] = -2 - (v >= g_nopt ? 3 : v);
        }
    }
    logf("proving grounds: the lobby's people changed: dealt again (%d bots, %d new)", r.n, fresh);
}

// ------------------------------------------------------------------ drawing
static ui_page g_pg;                             // MCC's 1920x1080 page in window px
static ImDrawList* g_dl;
static ImFont *g_fl, *g_fs;
static float g_alpha = 1;

static ImVec2 P(float x, float y) { return ImVec2(g_pg.x0 + x * g_pg.s, g_pg.y0 + y * g_pg.s); }
static float U(float v) { return v * g_pg.s; }
static ImU32 A(ImU32 c) { return (c & 0x00FFFFFFu) | ((ImU32)(((c >> 24) & 255) * g_alpha) << 24); }

// (Nov 19, the owner: "I want the vibe of reach as much as possible") every screen in Halo: Reach's steel grey, as the
// roster and credits already were (C_REACH_*): grey see-through panels, light grey text, a lit grey focus with a white
// edge; the colour comes from the maps, nameplates, emblems, team colours and gold. C_BLUE is now Reach's pale steel
// accent (the name kept: it marks the same places it did in MCC's navy)
// (Nov 19, later: the owner's pictures of Reach's menus) see-through as Reach's are, the painting behind flowing under
// them: the panels lighter, a plain list row nearly clear, the focus Reach's light band with a white line at its left
static const ImU32 C_TEXT = IM_COL32(238, 240, 242, 255), C_DIM = IM_COL32(176, 182, 188, 255),
                   C_BLUE = IM_COL32(200, 212, 222, 255), C_PANEL = IM_COL32(18, 20, 23, 176),
                   C_EDGE = IM_COL32(110, 118, 126, 120), C_FOCUS = IM_COL32(196, 202, 208, 66),
                   C_GOLD = IM_COL32(255, 204, 92, 255), C_ROW = IM_COL32(14, 16, 18, 70),
                   C_LIT = IM_COL32(240, 244, 248, 255);

static float text_w(ImFont* f, float size, const char* s) { return f->CalcTextSizeA(U(size), 1e9f, 0, s).x; }
static void text(ImFont* f, float size, float x, float y, ImU32 c, const char* s, int align = 0) {
    float w = align ? text_w(f, size, s) : 0;
    ImVec2 p = P(x, y);
    if (align == 1) p.x -= w * 0.5f;
    if (align == 2) p.x -= w;
    g_dl->AddText(f, U(size), ImVec2(p.x + 1, p.y + 1), A(IM_COL32(0, 0, 0, 140)), s);
    g_dl->AddText(f, U(size), p, A(c), s);
}
static void panel(float x0, float y0, float x1, float y1, ImU32 fill = C_PANEL) {
    // (Nov 19) as Reach's: lighter at the top, darker toward the bottom, a faint steel edge
    int r = fill & 255, g = (fill >> 8) & 255, b = (fill >> 16) & 255, a = (fill >> 24) & 255;
    ImU32 top = IM_COL32(r + (255 - r) / 14, g + (255 - g) / 14, b + (255 - b) / 14, a),
          bot = IM_COL32(r * 62 / 100, g * 62 / 100, b * 62 / 100, a);
    g_dl->AddRectFilledMultiColor(P(x0, y0), P(x1, y1), A(top), A(top), A(bot), A(bot));
    g_dl->AddRect(P(x0, y0), P(x1, y1), A(C_EDGE), 0, 0, 1.0f);
}
static void image(const pic* p, float x0, float y0, float x1, float y1, float a = 1.0f) {
    if (!p) return;
    float bw = x1 - x0, bh = y1 - y0, pr = (float)p->w / p->h, br = bw / bh;   // (cover: cropped, not stretched)
    ImVec2 uv0(0, 0), uv1(1, 1);
    if (pr > br) { float k = br / pr; uv0.x = (1 - k) * 0.5f; uv1.x = 1 - uv0.x; }
    else { float k = pr / br; uv0.y = (1 - k) * 0.5f; uv1.y = 1 - uv0.y; }
    g_dl->AddImage((ImTextureID)p->tex, P(x0, y0), P(x1, y1), uv0, uv1, A(IM_COL32(255, 255, 255, (int)(255 * a))));
}
// the header: MCC's small blue line over its big white title, and its three-step bar
static void header(const char* over, const char* big, int step) {   // ("small" is a Windows macro)
    text(g_fl, 22, 96, 44, C_BLUE, over);
    text(g_fl, 58, 92, 64, C_TEXT, big);
    for (int k = 0; k < 3; k++)
        g_dl->AddRectFilled(P(100 + k * 44.0f, 170), P(136 + k * 44.0f, 174), A(k == step ? C_LIT : IM_COL32(84, 90, 96, 200)));
}
// our own crest for the playlist's card: a chevron over a ring, the name beside it (no game art)
static void crest(float cx, float cy, float r, ImU32 c) {
    g_dl->AddCircle(P(cx, cy), U(r), A(c), 48, U(r * 0.09f));
    ImVec2 pts[5] = { P(cx - r * 0.55f, cy - r * 0.05f), P(cx, cy - r * 0.6f), P(cx + r * 0.55f, cy - r * 0.05f),
                      P(cx + r * 0.55f, cy + r * 0.25f), P(cx - r * 0.55f, cy + r * 0.25f) };
    g_dl->AddPolyline(pts, 3, A(c), 0, U(r * 0.12f));
    g_dl->AddLine(P(cx - r * 0.42f, cy + r * 0.38f), P(cx + r * 0.42f, cy + r * 0.38f), A(c), U(r * 0.1f));
}

// focus and clicks: each frame the items register; the mouse focuses what it moves over, the arrows and the pad's
// d-pad move the focus, a click, Enter, Space or A presses it
struct item_rect { float x0, y0, x1, y1; };
static std::vector<item_rect> g_items;
static int g_focus, g_pressed = -1, g_left_right;
static ImVec2 g_mouse_was;
static void (*g_sound)(int, uint32_t);
static uint32_t g_volume;
static void sound(int k) { if (g_sound) g_sound(k, g_volume); }

static bool g_inert;                             // (drawn under the invite list: no focus, no presses)
static bool item(float x0, float y0, float x1, float y1) {     // registers an item; true when it has the focus
    if (g_inert) return false;
    int id = (int)g_items.size();
    g_items.push_back({ x0, y0, x1, y1 });
    ImVec2 m = ImGui::GetIO().MousePos, a = P(x0, y0), b = P(x1, y1);
    bool over = m.x >= a.x && m.x <= b.x && m.y >= a.y && m.y <= b.y;
    bool moved = fabsf(m.x - g_mouse_was.x) + fabsf(m.y - g_mouse_was.y) > 0.5f;
    if (over && moved && g_focus != id) { g_focus = id; sound(PS_MOVE); }
    if (over && ImGui::IsMouseClicked(0)) { g_focus = id; g_pressed = id; }
    return g_focus == id;
}
static bool pressed(int id) { return !g_inert && g_pressed == id; }

static void frame_keys() {
    int n = (int)g_items.size();
    bool up = ImGui::IsKeyPressed(ImGuiKey_UpArrow) || ImGui::IsKeyPressed(ImGuiKey_GamepadDpadUp) ||
              ImGui::IsKeyPressed(ImGuiKey_GamepadLStickUp);
    bool down = ImGui::IsKeyPressed(ImGuiKey_DownArrow) || ImGui::IsKeyPressed(ImGuiKey_GamepadDpadDown) ||
                ImGui::IsKeyPressed(ImGuiKey_GamepadLStickDown);
    bool ok = ImGui::IsKeyPressed(ImGuiKey_Enter, false) || ImGui::IsKeyPressed(ImGuiKey_Space, false) ||
              ImGui::IsKeyPressed(ImGuiKey_KeypadEnter, false) || ImGui::IsKeyPressed(ImGuiKey_GamepadFaceDown, false);
    g_left_right = (ImGui::IsKeyPressed(ImGuiKey_RightArrow) || ImGui::IsKeyPressed(ImGuiKey_GamepadDpadRight) ||
                    ImGui::IsKeyPressed(ImGuiKey_GamepadLStickRight)) ? 1      // (Nov 19: the left stick too)
                 : (ImGui::IsKeyPressed(ImGuiKey_LeftArrow) || ImGui::IsKeyPressed(ImGuiKey_GamepadDpadLeft) ||
                    ImGui::IsKeyPressed(ImGuiKey_GamepadLStickLeft)) ? -1 : 0;
    if (n) {
        if (up) { g_focus = (g_focus + n - 1) % n; sound(PS_MOVE); }
        if (down) { g_focus = (g_focus + 1) % n; sound(PS_MOVE); }
        if (g_focus >= n) g_focus = n - 1;
        if (ok) g_pressed = g_focus;
    }
    g_mouse_was = ImGui::GetIO().MousePos;
}

// Reach's focus (the owner's pictures of its menus): a light see-through band, a faint edge, a white line at its left
static void focus_band(float x0, float y0, float x1, float y1) {
    g_dl->AddRectFilled(P(x0, y0), P(x1, y1), A(C_FOCUS));
    g_dl->AddRect(P(x0, y0), P(x1, y1), A(IM_COL32(214, 218, 222, 70)), 0, 0, U(1));
    g_dl->AddRectFilled(P(x0, y0), P(x0 + 3, y1), A(C_LIT));
}
// a menu row, as Reach's lists (Nov 19): nearly clear over the painting, the focused one Reach's band (focus_band); a
// label, an optional value at its right
static void row(float x0, float y0, float x1, float y1, bool focus, const char* label, const char* value = nullptr,
                bool arrows = false) {
    if (focus) focus_band(x0, y0, x1, y1);
    else g_dl->AddRectFilled(P(x0, y0), P(x1, y1), A(C_ROW));
    float h = y1 - y0, fs = h * 0.46f;
    text(g_fl, fs, x0 + 22, y0 + (h - fs * 1.2f) * 0.5f, focus ? C_TEXT : C_DIM, label);
    if (value) {
        float vx = x1 - (arrows ? 210 : 24);
        text(g_fl, fs * 0.82f, arrows ? (x1 - 205 + 190 * 0.5f) : vx, y0 + (h - fs) * 0.5f, C_TEXT, value, arrows ? 1 : 2);
        if (arrows) {
            text(g_fl, fs, x1 - 222, y0 + (h - fs * 1.2f) * 0.5f, C_DIM, "<");
            text(g_fl, fs, x1 - 22, y0 + (h - fs * 1.2f) * 0.5f, C_DIM, ">", 2);
        }
    }
}

// (Nov 17, the owner: "add whatever rank we are from our service record website to beside our names like in the
// original halo reach") each player's Reach rank as the Service Record shows it: <repo>\logs\service_record\ranks.txt
// (name, rank step, rank; tools/service_record.py writes it with the site from the one table, ranks.json) and the
// site's own insignia, ranks\<step>.png beside it. Read again when the site is rebuilt. A bot the site has no record
// for has no credits: Recruit (step 0), as the site would show it. -1: no rank (the file not built, or not a bot of it)
// (Nov 17) then the player card's numbers (games, K/D, win %, commendation progress %, credits, daily and weekly
// challenges completed; "" where none)
struct sr_rank { std::string name; int step; std::string label, games, kd, win, comm, cr, daily, weekly; };
static std::vector<sr_rank> g_sr;
static ULONGLONG g_sr_check, g_sr_stamp;
static bool g_sr_have;
static int sr_rank_of(const char* name, bool bot) {
    ULONGLONG now = GetTickCount64();
    if (!g_sr_check || now - g_sr_check > 3000) {
        g_sr_check = now;
        wchar_t p[MAX_PATH];
        swprintf_s(p, L"%s\\logs\\service_record\\ranks.txt", g_root);
        WIN32_FILE_ATTRIBUTE_DATA fa;
        ULONGLONG stamp = GetFileAttributesExW(p, GetFileExInfoStandard, &fa)
                              ? ((ULONGLONG)fa.ftLastWriteTime.dwHighDateTime << 32 | fa.ftLastWriteTime.dwLowDateTime) : 0;
        if (stamp != g_sr_stamp) {
            g_sr_stamp = stamp;
            g_sr.clear();
            g_sr_have = false;
            FILE* f = nullptr;
            if (stamp && _wfopen_s(&f, p, L"rb") == 0 && f) {
                char line[512];
                while (fgets(line, sizeof line, f)) {
                    if (line[0] == '#') continue;
                    line[strcspn(line, "\r\n")] = 0;
                    std::string col[10];
                    int n = 0;
                    for (char *s = line, *tab; n < 10; n++) {
                        tab = strchr(s, '\t');
                        if (tab) *tab = 0;
                        col[n] = s;
                        if (!tab) { n++; break; }
                        s = tab + 1;
                    }
                    if (n < 2) continue;
                    g_sr.push_back({ col[0], atoi(col[1].c_str()), col[2], col[3], col[4], col[5], col[6], col[7], col[8],
                                     col[9] });
                }
                fclose(f);
                g_sr_have = true;
            }
        }
    }
    if (!name || !name[0]) return -1;
    for (const sr_rank& r : g_sr) if (!_stricmp(r.name.c_str(), name)) return r.step;
    return g_sr_have && bot ? 0 : -1;
}
static const sr_rank* sr_record(const char* name) {     // the site's line for that name (nullptr: none)
    sr_rank_of(name, false);
    for (const sr_rank& r : g_sr) if (name && !_stricmp(r.name.c_str(), name)) return &r;
    return nullptr;
}
static const pic* sr_rank_picture(int step) {
    if (step < 0) return nullptr;
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\logs\\service_record\\ranks\\%d.png", g_root, step);
    return picture(p);
}

// (Nov 17, the owner: "port the same size nameplate and emblems to our version") a player's row at MCC's own MY GAME
// SESSION size, the numbers overlay.cpp's bot rows use (ui_layout.h mcc_session_row / _bar_x, from the owner's
// recordings): the nameplate box 332 x 44 ending at x1, the team's bar 12 wide 14 left of it, the rank badge (46) left
// of the bar, the emblem 32 square at (9, 6) in the nameplate's own square, [clan] (15) over the name (21) at 55.
// Rows are 44 high and 50 apart; y1 - y0 scales them (u = (y1 - y0) / 44). x0 is not used: the row is MCC's width.
// (Nov 17, the owner's Halo: Reach roster picture: "the ranks next to the player cards in its own little sub space")
// past the nameplate, 3 apart, the rank's own cell, a 44 square in the row's shade, as Reach drew it: the row ends at
// x1, the nameplate at x1 - 47.
static const float ROW_H = 44, ROW_STEP = 50, ROW_W = 332, ROW_CELL = 47, ROW_SPAN = 346 + 47;   // (bar to cell end)
// you: a person (the player; with pid, a friend who joined: their look by their id, report.cpp mcc_person_look)
static void player_row(float x0, float y0, float x1, float y1, const char* name, const char* clan, int team, int tier,
                       bool you, bool party, float a, uint64_t pid = 0) {
    (void)x0;
    float keep = g_alpha;
    g_alpha *= a < 0 ? 0 : a > 1 ? 1 : a;
    float u = (y1 - y0) / ROW_H, cx1 = x1;
    x1 -= ROW_CELL * u;                                  // (from here x1 is the nameplate's end; cx1 the cell's)
    float bx0 = x1 - ROW_W * u;
    ImU32 tc = team >= 0 ? team_colour(team) : IM_COL32(140, 148, 156, 255);
    int r = tc & 255, g = (tc >> 8) & 255, b = (tc >> 16) & 255;
    g_dl->AddRectFilled(P(x1 - 346 * u, y0), P(x1 - 334 * u, y1), A(tc));
    // the nameplate, MCC's own card (the plain ones in the team's colour): a bot's, and the person's own as MCC's player
    // lookup gives it (report.cpp); the team's shade where there is none
    int32_t me_emb[5];
    int me_np = -1;
    bool me_known = you && (pid ? mcc_person_look(pid, me_emb, &me_np) : mcc_player_look(me_emb, &me_np));
    int np = !g_make ? -1 : you ? (me_known ? me_np : -1) : bot_nameplate(name);
    unsigned long long npt = np > 0 ? nameplate_tex(np, g_make) : 0;
    if (npt) {
        ImU32 tint = nameplate_team(np) ? IM_COL32(r * 70 / 100 + 76, g * 70 / 100 + 76, b * 70 / 100 + 76, 255)
                                        : IM_COL32(255, 255, 255, 255);
        g_dl->AddImage((ImTextureID)npt, P(bx0, y0), P(x1, y1), ImVec2(0, 0), ImVec2(1, 1), A(tint));
        g_dl->AddRect(P(bx0, y0), P(x1, y1), A(IM_COL32(0, 0, 0, 150)), 0, 0, 1.0f);
    } else {
        g_dl->AddRectFilledMultiColor(P(bx0, y0), P(x1, y1), A(IM_COL32(r * 55 / 100, g * 55 / 100, b * 55 / 100, 235)),
                                      A(IM_COL32(r * 30 / 100, g * 30 / 100, b * 30 / 100, 225)),
                                      A(IM_COL32(r * 30 / 100, g * 30 / 100, b * 30 / 100, 225)),
                                      A(IM_COL32(r * 55 / 100, g * 55 / 100, b * 55 / 100, 235)));
        g_dl->AddRect(P(bx0, y0), P(x1, y1), A(IM_COL32(r * 85 / 100 + 30, g * 85 / 100 + 30, b * 85 / 100 + 30, 200)), 0, 0, 1.0f);
    }
    // the emblem: the bot's, or the person's own drawn from MCC's numbers for it (bots_panel.cpp player_emblem)
    unsigned long long em = !g_make ? 0 : you ? (me_known ? player_emblem(me_emb, g_make) : 0) : bot_emblem(name, g_make);
    float ex0 = bx0 + 9 * u, ey0 = y0 + 6 * u, ex1 = bx0 + 41 * u, ey1 = y0 + 38 * u;
    if (em) g_dl->AddImage((ImTextureID)em, P(ex0, ey0), P(ex1, ey1), ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
    else {
        g_dl->AddRectFilled(P(ex0, ey0), P(ex1, ey1), A(IM_COL32(24, 27, 30, 220)));
        if (you) crest((ex0 + ex1) * 0.5f, (ey0 + ey1) * 0.5f, 11 * u, C_BLUE);
        else g_dl->AddRect(P(ex0, ey0), P(ex1, ey1), A(IM_COL32(r * 85 / 100 + 30, g * 85 / 100 + 30, b * 85 / 100 + 30, 200)), 0, 0, 1.0f);
    }
    float tx = bx0 + 55 * u;
    auto edged = [&](float size, float x, float y, ImU32 c, const char* s) {   // (a dark edge: the light nameplates)
        for (int k = 0; k < 4; k++)
            g_dl->AddText(g_fl, U(size), P(x + (k & 1 ? 1.2f : -1.2f) * u, y + (k & 2 ? 1.2f : -1.2f) * u + 0.6f * u),
                          A(IM_COL32(0, 0, 0, 120)), s);
        text(g_fl, size, x, y, c, s);
    };
    if (!clan || !clan[0])                               // (no tag (the person's is not read): the name alone, centred)
        edged(21 * u, tx, y0 + 11 * u, C_TEXT, name);
    else {
        char tag[24];
        sprintf_s(tag, "[%s]", clan);
        edged(15 * u, tx, y0 + 4 * u, IM_COL32(222, 228, 234, 235), tag);
        edged(21 * u, tx, y0 + 19 * u, C_TEXT, name);
    }
    // the Reach rank in its own cell past the nameplate, as Halo: Reach drew a player's insignia (the Service Record's
    // own): the cell in the row's shade (the team's in a team game, else dark), there with or without a rank
    {
        float c0 = cx1 - ROW_H * u;
        ImU32 cf = team >= 0 ? IM_COL32(r * 62 / 100, g * 62 / 100, b * 62 / 100, 240) : IM_COL32(26, 29, 32, 235);
        g_dl->AddRectFilled(P(c0, y0), P(cx1, y1), A(cf));
        g_dl->AddRect(P(c0, y0), P(cx1, y1), A(team >= 0 ? IM_COL32(r * 85 / 100 + 30, g * 85 / 100 + 30, b * 85 / 100 + 30, 200)
                                                         : IM_COL32(84, 90, 96, 200)), 0, 0, 1.0f);
        if (const pic* rp = sr_rank_picture(sr_rank_of(name, !you))) {
            float s = 36 * u, cx = (c0 + cx1) * 0.5f, cy = (y0 + y1) * 0.5f;
            g_dl->AddImage((ImTextureID)rp->tex, P(cx - s * 0.5f, cy - s * 0.5f), P(cx + s * 0.5f, cy + s * 0.5f), ImVec2(0, 0),
                           ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
        }
    }
    if (party) text(g_fl, 14 * u, x1 - 8 * u, y0 + 3 * u, C_GOLD, "PARTY", 2);
    if (!you && tier >= 0) {                             // (left of the bar, where MCC puts a player's rank)
        int tour, level;
        bot_rank(name, tier, &tour, &level);
        rank_badge(g_dl, P(x1 - 370 * u, (y0 + y1) * 0.5f), U(46 * u), tour, level, g_alpha);
    }
    g_alpha = keep;
}

static const char* me_name() { const char* n = mcc_player_name(); return n && n[0] ? n : "You"; }

// (Nov 17) MCC's footer, from its own Find Game screen: a line of help over its button prompts, each a glyph (the pad's
// lettered circle, or the key) and its action. Back is clickable; the hint is the focused control's.
static bool g_footer_back;                       // the footer's Back clicked this frame
static bool g_pad_in;                            // the last input was the pad: the prompts name its buttons
// (Nov 19) on the pad, the buttons as Reach showed them: A green, B red, X blue, Y yellow, each a lit disc with its
// letter; a bumper or trigger (LB, RB, LT+RT) a dark pill with its name. On the keys, the key's outline as before.
static ImU32 pad_colour(const char* g) {
    if (!g[0] || g[1]) return 0;
    switch (g[0]) {
    case 'A': return IM_COL32(96, 184, 58, 255);
    case 'B': return IM_COL32(222, 58, 44, 255);
    case 'X': return IM_COL32(48, 118, 226, 255);
    case 'Y': return IM_COL32(242, 190, 26, 255);
    }
    return 0;
}
static float pad_glyph_w(const char* g) { return pad_colour(g) ? 30 : text_w(g_fs, 16, g) / g_pg.s + 20; }
static void pad_glyph(float x, float y, const char* g, ImU32 edge) {   // (x, y: its box's top left, 30 high)
    if (ImU32 c = pad_colour(g)) {
        int r = c & 255, gg = (c >> 8) & 255, b = (c >> 16) & 255;
        g_dl->AddCircleFilled(P(x + 15, y + 15), U(13.5f), A(IM_COL32(r * 45 / 100, gg * 45 / 100, b * 45 / 100, 255)), 32);
        g_dl->AddCircleFilled(P(x + 15, y + 14), U(12), A(c), 32);
        g_dl->AddCircleFilled(P(x + 15, y + 10), U(7), A(IM_COL32(255, 255, 255, 46)), 24);   // (its shine)
        g_dl->AddText(g_fs, U(18), P(x + 15 - text_w(g_fs, 18, g) / g_pg.s * 0.5f, y + 4), A(IM_COL32(255, 255, 255, 255)), g);
        return;
    }
    float w = pad_glyph_w(g);
    g_dl->AddRectFilled(P(x, y + 3), P(x + w, y + 27), A(IM_COL32(40, 44, 48, 240)), U(11));
    g_dl->AddRect(P(x, y + 3), P(x + w, y + 27), A(edge), U(11), 0, U(1.4f));
    text(g_fs, 16, x + w * 0.5f, y + 6, IM_COL32(236, 238, 240, 255), g, 1);
}
static float prompt(float x, float y, const char* pad, const char* key, const char* label, bool* clicked) {
    const char* g = g_pad_in ? pad : key;
    float gw = g_pad_in ? pad_glyph_w(pad) : text_w(g_fs, 18, g) / g_pg.s + 16, w = gw + 10 + text_w(g_fl, 22, label) / g_pg.s;
    ImVec2 m = ImGui::GetIO().MousePos, a = P(x - 6, y - 4), b = P(x + w + 8, y + 34);
    bool over = clicked && m.x >= a.x && m.x <= b.x && m.y >= a.y && m.y <= b.y;
    if (over) g_dl->AddRectFilled(a, b, A(IM_COL32(96, 102, 108, 170)));
    ImU32 gc = over ? C_TEXT : IM_COL32(214, 218, 222, 255);
    if (g_pad_in) pad_glyph(x, y, g, IM_COL32(150, 156, 162, 220));
    else {
        g_dl->AddRect(P(x, y + 2), P(x + gw, y + 28), A(gc), U(3), 0, U(1.4f));
        text(g_fs, 18, x + gw * 0.5f, y + 4, gc, g, 1);
    }
    text(g_fl, 22, x + gw + 10, y + 2, over ? C_TEXT : IM_COL32(222, 226, 230, 255), label);
    if (over && ImGui::IsMouseClicked(0)) *clicked = true;
    return x + w + 34;
}
// (Nov 19) the screens with the roster beside them also name the way into it: RB on the pad (or Right), Right on the keys
static bool g_footer_players;                    // the footer's Players clicked this frame
static void footer_line() {                      // (Nov 19) Reach's thin line over its button prompts
    g_dl->AddLine(P(96, 981), P(1240, 981), A(IM_COL32(206, 212, 218, 90)), U(1));
}
static void footer(const char* hint = nullptr, const char* select = nullptr, bool players = false) {
    footer_line();
    if (hint && hint[0]) text(g_fs, 21, 100, 948, IM_COL32(200, 206, 212, 255), hint);
    float x = prompt(100, 992, "B", "Esc", "Back", &g_footer_back);
    if (select) x = prompt(x, 992, "A", "Enter", select, nullptr);
    if (players) prompt(x, 992, "RB", "Right", "Players", &g_footer_players);
}

// (Nov 17) the screens' own ground, opaque: MCC's custom game lobby is not seen behind them. A playlist's map, faint and
// slowly changing, under a deep blue wash, as MCC's menus have their art behind; a slow light across.
// (Nov 19, the owner's pictures of Halo: Reach's own menus: "The background is more seemless and fluid ... I want the
// background to be like that") Reach's backgrounds, the owner's upscales of its menu art: one painting across the whole
// screen, bright, the menus over it. This PC's only, in native\bin\pg_backgrounds (git-ignored: Reach's art is never
// committed): menu.png Proving Grounds' own screens (the Halo over Reach), matchmaking.png Find Game, the vote and the
// next game (Reach's main menu, the Covenant over the glassing), postgame.png the credits after a game (an Elite and a
// Spartan); .jpg too. Without one: the playlist's maps, faint, as before (background below).
enum { BG_MENU, BG_MATCH, BG_POST, BG_N };
static const pic* bg_picture(int k) {
    static const wchar_t* N[BG_N] = { L"menu", L"matchmaking", L"postgame" };
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\pg_backgrounds\\%s.png", g_bin, N[k]);
    if (const pic* q = picture(p)) return q;
    swprintf_s(p, L"%s\\pg_backgrounds\\%s.jpg", g_bin, N[k]);
    return picture(p);
}
// a painting over the whole window, as Reach's drift: 8-10% larger than the screen, slowly moving about in that room
static void painting(const pic* art, float a, float t) {
    ImVec2 d = ImGui::GetIO().DisplaySize;
    float pr = (float)art->w / art->h, br = d.x / d.y, uw = 1, vh = 1;
    if (pr > br) uw = br / pr; else vh = pr / br;            // (cover: cropped, not stretched)
    float z = 1.09f + 0.02f * sinf(t * 0.021f);
    uw /= z; vh /= z;
    float px = 0.5f + 0.42f * sinf(t * 0.017f), py = 0.5f + 0.42f * sinf(t * 0.011f + 1.3f);
    ImVec2 uv0((1 - uw) * px, (1 - vh) * py);
    g_dl->AddImage((ImTextureID)art->tex, ImVec2(0, 0), d, uv0, ImVec2(uv0.x + uw, uv0.y + vh),
                   IM_COL32(255, 255, 255, (int)(255 * a)));
}
static void painted_background(float t, const pic* art) {
    static const pic *cur, *was;
    static float since = -100, drawn = -100;
    // (a new screen's painting fades in over the last; not when the screens were just put up again, or in the preview's
    // few frames a screen)
    bool fresh = t - drawn > 0.5f;
#ifdef PG_PREVIEW
    fresh = true;
#endif
    drawn = t;
    if (art != cur) { was = cur; cur = art; since = fresh ? t - 10 : t; }
    ImVec2 d = ImGui::GetIO().DisplaySize;
    g_dl->AddRectFilled(ImVec2(0, 0), d, IM_COL32(6, 7, 9, 255));        // (never faded: the lobby stays hidden)
    float k = (t - since) / 0.9f;
    k = k < 0 ? 0 : k > 1 ? 1 : k;
    if (was && k < 1) painting(was, 1, t);
    painting(cur, k * k * (3 - 2 * k), t);
    // Reach's own treatment: the painting bright, a little dimmed; darker where the menu stands (left) and under the
    // prompts (bottom), a touch at the top and behind the roster (right)
    g_dl->AddRectFilled(ImVec2(0, 0), d, IM_COL32(6, 7, 9, 56));
    g_dl->AddRectFilledMultiColor(ImVec2(0, 0), ImVec2(d.x * 0.58f, d.y), IM_COL32(6, 7, 9, 165), IM_COL32(6, 7, 9, 0),
                                  IM_COL32(6, 7, 9, 0), IM_COL32(6, 7, 9, 165));
    g_dl->AddRectFilledMultiColor(ImVec2(0, d.y * 0.68f), d, IM_COL32(6, 7, 9, 0), IM_COL32(6, 7, 9, 0),
                                  IM_COL32(6, 7, 9, 200), IM_COL32(6, 7, 9, 200));
    g_dl->AddRectFilledMultiColor(ImVec2(0, 0), ImVec2(d.x, d.y * 0.2f), IM_COL32(6, 7, 9, 90), IM_COL32(6, 7, 9, 90),
                                  IM_COL32(6, 7, 9, 0), IM_COL32(6, 7, 9, 0));
    g_dl->AddRectFilledMultiColor(ImVec2(d.x * 0.72f, 0), d, IM_COL32(6, 7, 9, 0), IM_COL32(6, 7, 9, 80),
                                  IM_COL32(6, 7, 9, 80), IM_COL32(6, 7, 9, 0));
}

// (Nov 19) Reach's grey in place of MCC's navy, and the art about twice as bright: kept at near its own colours under
// a light steel wash, the left side and the bottom darkened less, so the maps' colour shows through
static void background(float t, const pic* art, float art_a) {
    ImVec2 d = ImGui::GetIO().DisplaySize;
    g_dl->AddRectFilled(ImVec2(0, 0), d, IM_COL32(9, 10, 12, 255));      // (never faded: the lobby stays hidden)
    if (art && art_a > 0) {
        float pr = (float)art->w / art->h, br = d.x / d.y;
        ImVec2 uv0(0, 0), uv1(1, 1);
        if (pr > br) { float k = br / pr; uv0.x = (1 - k) * 0.5f; uv1.x = 1 - uv0.x; }
        else { float k = pr / br; uv0.y = (1 - k) * 0.5f; uv1.y = 1 - uv0.y; }
        g_dl->AddImage((ImTextureID)art->tex, ImVec2(0, 0), d, uv0, uv1, IM_COL32(222, 228, 234, (int)(255 * art_a)));
    }
    g_dl->AddRectFilledMultiColor(ImVec2(0, 0), ImVec2(d.x, d.y * 0.55f), IM_COL32(52, 56, 60, 70), IM_COL32(40, 44, 48, 40),
                                  IM_COL32(9, 10, 12, 0), IM_COL32(9, 10, 12, 0));
    g_dl->AddRectFilledMultiColor(ImVec2(0, d.y * 0.62f), d, IM_COL32(5, 6, 7, 0), IM_COL32(5, 6, 7, 0),
                                  IM_COL32(5, 6, 7, 170), IM_COL32(5, 6, 7, 170));
    g_dl->AddRectFilledMultiColor(ImVec2(0, 0), ImVec2(d.x * 0.5f, d.y), IM_COL32(5, 6, 8, 95), IM_COL32(5, 6, 8, 0),
                                  IM_COL32(5, 6, 8, 0), IM_COL32(5, 6, 8, 95));
    float sweep = fmodf(t * 0.05f, 1.6f) - 0.3f;                   // (a slow light across, as the menus drift)
    g_dl->AddRectFilledMultiColor(ImVec2(d.x * sweep, 0), ImVec2(d.x * (sweep + 0.25f), d.y), IM_COL32(236, 240, 244, 0),
                                  IM_COL32(236, 240, 244, 10), IM_COL32(236, 240, 244, 10), IM_COL32(236, 240, 244, 0));
}

// the playlist's stats, as MCC's PLAYLIST STATS panel
static void stats_panel(float x0, float y0, float w = 415) {
    const playlist& pl = cur_pl();
    panel(x0, y0, x0 + w, y0 + 268);
    text(g_fl, 26, x0 + 14, y0 + 10, C_BLUE, "PLAYLIST STATS");
    char v[6][24];
    sprintf_s(v[0], "%d", pl.size * 2);
    sprintf_s(v[1], "%d", pl.size);
    sprintf_s(v[2], "%d", pl.size);
    sprintf_s(v[3], "Clans together");
    sprintf_s(v[4], "%d s", g_vote_s);
    sprintf_s(v[5], "%d", g_pool_count);                    // (each bot once: Name*N lines are one bot)
    const char* k[6] = { "Player Count", "Max Party Size", "Team Size", "Team Matching", "Voting", "Bots in pool" };
    for (int i = 0; i < 6; i++) {
        text(g_fl, 22, x0 + 14, y0 + 52 + i * 35, C_TEXT, k[i]);
        text(g_fl, 22, x0 + w - 15, y0 + 52 + i * 35, C_DIM, v[i], 2);
    }
}

static void category_tiles(float x0, float y0, float tile) {
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    playlist_pool(cur_pl(), gts, maps);
    bool shown[F_N] = {};
    float x = x0;
    for (auto& g : gts) {
        int f = family_of(g.e->category);
        if (shown[f]) continue;
        shown[f] = true;
        panel(x, y0, x + tile, y0 + tile, IM_COL32(18, 20, 23, 170));
        const pic* p = family_picture(f);
        if (p) image(p, x + tile * 0.12f, y0 + tile * 0.08f, x + tile * 0.88f, y0 + tile * 0.84f);
        else text(g_fl, tile * 0.16f, x + tile * 0.5f, y0 + tile * 0.4f, C_BLUE, FAMILY_NAME[f], 1);
        g_dl->AddRectFilled(P(x + 6, y0 + tile - 22), P(x + 22, y0 + tile - 6), A(C_BLUE));
        x += tile + 6;
    }
    if (gts.empty()) text(g_fs, 22, x0, y0 + 10, C_DIM, "MCC's gametypes are read once its Halo: Reach custom game lobby is open.");
}

// ------------------------------------------------------------------ the roster, as Halo: Reach's party list
// (Nov 17, the owner's three Halo: Reach pictures: the full party list; its header picked, MY PARTY DETAILS beside it;
// a player picked, their Spartan, emblem, rank and numbers; "Only if its super similar if not spot on") Right (the
// arrow, the d-pad) or a click on the list gives it the focus. As in Reach the list slides from its place to the
// middle left and the screen's own content steps aside; the focused entry's panel stands at its right: the header's
// details, a player's card. Up and down move through it; Left, Esc, B or a click away bring the screen back. Measured
// from the owner's pictures on the 1920 x 1080 page: the list ends at x 990 (its tab 62-100, header 104-148, rows from
// 156), the panel 1017-1758 x 69-971 (its title at 84, the details 43 apart from 190; a card's emblem 70 square at
// 1046,78, the name beside it at 32 over the rank at 25, the emblem again large and faint behind the Spartan, which
// stands from 1240 to 1850, the four numbers from 620, 72 apart, each label over its value with a line between).
enum { RK_ME, RK_PERSON, RK_BOT, RK_EMPTY };
struct ros_row { int kind; const char* name; const char* clan; int team, tier; bool party; float a; uint64_t pid; float gap; };
struct ros_head {
    const char* mcc;            // the header at MCC's place ("MY GAME SESSION", "IN LOBBY 3/8")
    const char* mcc_count;      // its count at the right (nullptr: in the words)
    const char* reach;          // at Reach's place ("In Matchmaking Lobby"), its count at the right
    const char* count;
    const char* tab;            // the tab over it ("MY PARTY")
    const char* details;        // the header's panel ("MY PARTY DETAILS") and its five values
    const char* v[5];
};
static bool g_ros_on;                            // the roster has the focus
static float g_ros_k;                            // its slide: 0 MCC's place, 1 Reach's
static int g_ros_click = -1;                     // (at MCC's place) the entry clicked: where the focus starts
static int g_ros_keep = 0;                       // the screen's focus before (given back)
static bool g_lr_taken;                          // a control used Left / Right this frame (the menu's GAME SIZE)
static float g_ros_x0, g_ros_x1, g_ros_y0, g_ros_y1;   // the list's box as last drawn (a click away from it)
static char g_ros_hint[64];                      // the footer's line while the roster has the focus
static const float RX1 = 990, RHEAD = 104, RROW = 156, RP0 = 1017, RP1 = 1758, RPY0 = 69, RPY1 = 971;
static const ImU32 C_REACH_TEXT = IM_COL32(236, 238, 240, 255), C_REACH_DIM = IM_COL32(176, 182, 188, 255);
static bool ros_up() { return g_ros_on || g_ros_k > 0; }   // the list away from its place: the screen's content aside

static bool ros_clicked(float x0, float y0, float x1, float y1) {
    if (g_inert || !ImGui::IsMouseClicked(0)) return false;
    ImVec2 m = ImGui::GetIO().MousePos, a = P(x0, y0), b = P(x1, y1);
    return m.x >= a.x && m.x <= b.x && m.y >= a.y && m.y <= b.y;
}
// Reach's pointer on the picked entry: its right end drawn out to a point toward the panel
static void ros_tip(float x, float y0, float y1, ImU32 c) {
    g_dl->AddTriangleFilled(P(x, y0), P(x + 22, (y0 + y1) * 0.5f), P(x, y1), A(c));
}
// Reach's panel: dark and see-through, a faint edge
static void reach_panel(float x0, float y0, float x1, float y1) {
    g_dl->AddRectFilledMultiColor(P(x0, y0), P(x1, y1), A(IM_COL32(26, 30, 34, 214)), A(IM_COL32(20, 24, 28, 200)),
                                  A(IM_COL32(10, 12, 15, 214)), A(IM_COL32(14, 17, 20, 220)));
    g_dl->AddRect(P(x0, y0), P(x1, y1), A(IM_COL32(96, 104, 112, 110)), 0, 0, 1.0f);
}

static void ros_details(const ros_head& h) {
    reach_panel(RP0, RPY0, RP1, RPY1);
    text(g_fl, 46, RP0 + 21, RPY0 + 15, C_REACH_TEXT, h.details);
    static const char* K[5] = { "Party Leader:", "Playlist:", "Player Count:", "Max Player Count:", "Game Mode:" };
    for (int i = 0; i < 5; i++) {
        float y = 190 + 43.0f * i;
        text(g_fl, 26, RP0 + 23, y, C_REACH_DIM, K[i]);
        text(g_fl, 26, RP1 - 22, y, C_REACH_TEXT, h.v[i] ? h.v[i] : "...", 2);
    }
}

static void ros_card(pg_env& e, const ros_row& w) {
    reach_panel(RP0, RPY0, RP1, RPY1);
    g_dl->AddRectFilledMultiColor(P(RP0 + 1, RPY0 + 1), P(RP1 - 1, RPY0 + 96), A(IM_COL32(70, 74, 78, 150)),
                                  A(IM_COL32(46, 50, 54, 110)), A(IM_COL32(46, 50, 54, 110)), A(IM_COL32(70, 74, 78, 150)));
    bool bot = w.kind == RK_BOT;
    int32_t emb[5];
    int np;
    unsigned long long em = !g_make ? 0 : bot ? bot_emblem(w.name, g_make)
                          : ((w.pid ? mcc_person_look(w.pid, emb, &np) : mcc_player_look(emb, &np)) ? player_emblem(emb, g_make) : 0);
    if (em)                                              // (the emblem again, large and faint, behind the Spartan)
        g_dl->AddImage((ImTextureID)em, P(1040, 190), P(1470, 620), ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 58)));
    if (e.figure) {
        ImVec2 f0 = P(1230, 60), f1 = P(1860, 1010);     // (the figure fills about 86% of the height: 120 to 950)
        unsigned long long fig = e.figure(w.name, bot, 0.42f, (int)(f1.x - f0.x), (int)(f1.y - f0.y));
        if (fig) g_dl->AddImage((ImTextureID)fig, f0, f1, ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
    }
    if (em) g_dl->AddImage((ImTextureID)em, P(1046, 78), P(1116, 148), ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
    else { g_dl->AddRectFilled(P(1046, 78), P(1116, 148), A(IM_COL32(20, 26, 32, 230))); crest(1081, 113, 24, C_REACH_DIM); }
    const sr_rank* s = sr_record(w.name);
    text(g_fl, 32, 1134, 82, C_REACH_TEXT, w.name);
    text(g_fl, 25, 1135, 121, C_REACH_DIM, s && !s->label.empty() ? s->label.c_str() : "...");
    // Reach's own four: the daily and weekly challenges completed, its Armory Completion (none here: the kills per
    // death in its place) and the Overall Commendation Progress, the Service Record's; "..." where it has none
    bool played = s && !s->games.empty() && s->games != "0";
    char v[4][24];
    sprintf_s(v[0], "%s", s && !s->daily.empty() ? s->daily.c_str() : "...");
    sprintf_s(v[1], "%s", s && !s->weekly.empty() ? s->weekly.c_str() : "...");
    sprintf_s(v[2], "%s", played && !s->kd.empty() ? s->kd.c_str() : "...");
    if (s && !s->comm.empty()) sprintf_s(v[3], "%s%%", s->comm.c_str()); else strcpy_s(v[3], "...");
    static const char* K[4] = { "Daily Challenges Completed:", "Weekly Challenges Completed:", "Kill/Death Ratio:",
                                "Overall Commendation Progress:" };
    for (int i = 0; i < 4; i++) {
        float y = 620 + 72.0f * i;
        text(g_fl, 25, 1036, y, C_REACH_DIM, K[i]);
        text(g_fl, 25, 1038, y + 31, C_REACH_TEXT, v[i]);
        if (i < 3) g_dl->AddLine(P(1036, y + 66), P(1500, y + 66), A(IM_COL32(120, 128, 136, 120)), U(1));
    }
}

// The list: its header and rows at MCC's place (nx1, the header at ny0, the first row at nrow0), or sliding to and
// standing at Reach's with the focus. An RK_EMPTY row: a seat still searching (empty_text and dots, dots_t its clock)
static void roster(pg_env& e, const std::vector<ros_row>& rows, const ros_head& h, float nx1, float ny0, float nrow0,
                   float dots_t, const char* empty_text) {
    float k = g_ros_k, ek = k * k * (3 - 2 * k);
    float x1 = nx1 + (RX1 - nx1) * ek, x0 = x1 - ROW_SPAN;
    float hy = ny0 + (RHEAD - ny0) * ek, hh = 36 + 8 * ek;
    bool reach = ek > 0.5f, live = g_ros_on && k >= 1.0f;
    if (ek > 0.01f) {                                    // Reach's tab over the list
        float keep = g_alpha;
        g_alpha *= ek;
        g_dl->AddRectFilled(P(x0 - 48, hy - 42), P(x0 + 330, hy - 4), A(IM_COL32(18, 22, 26, 230)));
        text(g_fl, 22, x0 - 38, hy - 36, C_REACH_TEXT, h.tab);
        g_alpha = keep;
    }
    int idx = 0, base = (int)g_items.size();
    // the header
    bool hf = live && item(x0, hy, x1, hy + hh);
    if (!g_ros_on && ros_clicked(x0, hy, x1, hy + hh)) g_ros_click = idx;
    idx++;
    if (!reach) panel(x0, hy, x1, hy + hh, IM_COL32(32, 36, 40, 228));
    else {
        ImU32 hc = hf ? IM_COL32(150, 156, 162, 226) : IM_COL32(30, 34, 38, 220);
        g_dl->AddRectFilled(P(x0, hy), P(x1, hy + hh), A(hc));
        if (hf) ros_tip(x1, hy, hy + hh, hc);
    }
    text(g_fl, 22, x0 + 12, hy + (hh - 26) * 0.5f, reach ? C_REACH_TEXT : C_TEXT, reach ? h.reach : h.mcc);
    const char* cnt = reach ? h.count : h.mcc_count;
    if (cnt) text(g_fl, 22, x1 - 12, hy + (hh - 26) * 0.5f, reach ? C_REACH_TEXT : C_DIM, cnt, 2);
    // the rows (the focused one drawn last, over its neighbours)
    float y = nrow0 + (RROW - nrow0) * ek;
    const ros_row* fr = nullptr;
    float fy = 0;
    int empty_i = 0;
    for (const ros_row& w : rows) {
        y += w.gap * (1 - ek) + (w.gap >= 10 ? 12.0f : 0.0f) * ek;   // (Reach's: the teams' gap only)
        if (w.kind == RK_EMPTY) {
            // (Nov 19) an empty seat is an outline, a soft light passing down the seats while the lobby fills; the words
            // once, on the first (the status over the screen says the rest)
            g_dl->AddRectFilled(P(x0, y), P(x1, y + ROW_H), A(IM_COL32(18, 20, 23, 120)));
            g_dl->AddRect(P(x0, y), P(x1, y + ROW_H), A(IM_COL32(74, 80, 86, 130)), 0, 0, 1.0f);
            float ph = fmodf(dots_t * 0.9f - empty_i * 0.11f, 1.6f);
            if (ph > 0 && ph < 1)
                g_dl->AddRectFilled(P(x0, y), P(x1, y + ROW_H), A(IM_COL32(220, 226, 232, (int)(34 * sinf(ph * 3.14159f)))));
            if (empty_i == 0 && empty_text && empty_text[0]) {
                int dots = 1 + ((int)(dots_t * 2.5f) % 3);
                char s[48];
                sprintf_s(s, "%s%.*s", empty_text, dots, "...");
                text(g_fl, ROW_H * 0.40f, x0 + 14, y + ROW_H * 0.26f, C_DIM, s);
            }
            empty_i++;
            y += ROW_STEP;
            continue;
        }
        bool f = live && item(x0, y, x1, y + ROW_H);
        if (!g_ros_on && ros_clicked(x0, y, x1, y + ROW_H)) g_ros_click = idx;
        idx++;
        if (f) { fr = &w; fy = y; }
        else {
            // (Nov 19) a bot just found slides in from the right as it lights, a white flash fading into its nameplate
            float ia = w.a < 0 ? 0 : w.a > 1 ? 1 : w.a, dx = (1 - ia) * (1 - ia) * 90;
            player_row(x0 + dx, y, x1 + dx, y + ROW_H, w.name, w.clan, w.team, w.tier, w.kind != RK_BOT, w.party, w.a, w.pid);
            if (ia > 0 && ia < 1)
                g_dl->AddRectFilled(P(x1 + dx - ROW_SPAN + 14, y), P(x1 + dx, y + ROW_H),
                                    A(IM_COL32(236, 240, 244, (int)(90 * (1 - ia) * (ia * 4 < 1 ? ia * 4 : 1)))));
        }
        y += ROW_STEP;
    }
    if (fr) {                                            // (Reach's pick: the row a little larger toward the panel, lit,
        float g = 2, gx = 18;                            // its pointer reaching the panel's edge)
        player_row(x0, fy - g, x1 + gx, fy + ROW_H + g, fr->name, fr->clan, fr->team, fr->tier, fr->kind != RK_BOT,
                   fr->party, 1, fr->pid);
        float u = (ROW_H + 2 * g) / ROW_H, l = x1 + gx - (ROW_W + ROW_CELL) * u;
        g_dl->AddRectFilled(P(l, fy - g), P(x1 + gx, fy + ROW_H + g), A(IM_COL32(255, 255, 255, 30)));
        g_dl->AddRect(P(l, fy - g), P(x1 + gx, fy + ROW_H + g), A(IM_COL32(244, 247, 250, 255)), 0, 0, U(1.6f));
        g_dl->AddTriangleFilled(P(x1 + gx, fy - g), P(x1 + gx + 16, fy + ROW_H * 0.5f), P(x1 + gx, fy + ROW_H + g),
                                A(IM_COL32(232, 236, 240, 240)));
    }
    g_ros_x0 = x0 - 48; g_ros_x1 = x1 + 30; g_ros_y0 = hy - 42; g_ros_y1 = y;
    // the focused entry's panel (while it slides in: the header's)
    if (ek > 0.01f) {
        float keep = g_alpha;
        g_alpha *= ek;
        if (fr) ros_card(e, *fr);
        else ros_details(h);
        g_alpha = keep;
    }
    (void)base;
}

// MY GAME SESSION: the person, the friends who joined (Nov 17) and their invited party
static void session_panel(pg_env& e) {
    const hb_roster& r = *e.roster;
    uint64_t ids[PG_PEOPLE];
    char names[PG_PEOPLE][32];
    int teams[PG_PEOPLE], np = mcc_session_people(ids, names, teams, PG_PEOPLE);
    int tiers[8];
    std::vector<ros_row> rows;                           // (MCC's: its header 36..72, the player 82, others 137 + 50 k)
    rows.push_back({ RK_ME, me_name(), "", -1, -1, false, 1, 0, 0 });
    for (int k = 0; k < np; k++) rows.push_back({ RK_PERSON, names[k], "", -1, -1, false, 1, ids[k], k ? 0.0f : 5.0f });
    for (int i = 0; i < g_nparty; i++) {
        tiers[i] = 3;
        for (int k = 0; k < r.n; k++) if (!_stricmp(r.bot[k].name, g_party[i])) tiers[i] = r.bot[k].tier;
        int t, st;
        if (bot_pool_saved_of(g_party[i], &t, &st)) tiers[i] = t;
        rows.push_back({ RK_BOT, g_party[i], profile_clan_of(g_party[i]), -1, tiers[i], true, 1, 0, (np || i) ? 0.0f : 5.0f });
    }
    char cnt[16], now[8], max[8];
    sprintf_s(cnt, "%d/%d", g_nparty + 1 + np, cur_pl().size * 2);
    sprintf_s(now, "%d", g_nparty + 1 + np);
    sprintf_s(max, "%d", cur_pl().size * 2);
    // (Nov 19) one name for the list wherever it stands: Reach's own ("MY GAME SESSION" before)
    ros_head h = { "IN PROVING GROUNDS LOBBY", cnt, "In Proving Grounds Lobby", cnt, "MY PARTY", "MY PARTY DETAILS",
                   { me_name(), cur_pl().title, now, max, "Proving Grounds" } };
    roster(e, rows, h, 1830, 34, 82, 0, nullptr);
}

// ------------------------------------------------------------------ the screens
static float g_invite_scroll;

static void invite_list(pg_env& e) {
    if (!g_npool_names) g_npool_names = bot_pool_names(g_pool_names, 4096);
    float x0 = 600, y0 = 150, x1 = 1320, y1 = 930;
    float rx1 = x0 + 84 + ROW_W + ROW_CELL, bt0 = x1 - 200;          // (each row at MCC's size, its rank left of it; the button)
    g_dl->AddRectFilled(ImVec2(0, 0), ImGui::GetIO().DisplaySize, A(IM_COL32(0, 0, 0, 120)));
    panel(x0, y0, x1, y1, IM_COL32(20, 22, 25, 245));
    text(g_fl, 34, x0 + 24, y0 + 16, C_TEXT, "INVITE PLAYER");
    if (g_npool_names > 0) {                             // (Nov 19: where in the pool the page is)
        char at[32];
        int f0 = (int)g_invite_scroll + 1, f1 = (int)g_invite_scroll + (int)((y1 - 70 - (y0 + 104)) / ROW_STEP);
        sprintf_s(at, "%d-%d of %d", f0, f1 < g_npool_names ? f1 : g_npool_names, g_npool_names);
        text(g_fs, 20, x1 - 24, y0 + 26, C_DIM, at, 2);
    }
    char sub[96];
    sprintf_s(sub, "Your party: %d of %d. Party members are always on your team.", g_nparty, cur_pl().size - 1);
    text(g_fs, 22, x0 + 26, y0 + 64, C_DIM, sub);
    float list0 = y0 + 104, list1 = y1 - 70, rowh = ROW_STEP;
    int visible = (int)((list1 - list0) / rowh);
    float wheel = ImGui::GetIO().MouseWheel;
    g_invite_scroll -= wheel * 3;
    int maxs = g_npool_names - visible;
    if (g_invite_scroll > maxs) g_invite_scroll = (float)(maxs > 0 ? maxs : 0);
    if (g_invite_scroll < 0) g_invite_scroll = 0;
    int first = (int)g_invite_scroll;
    int base = (int)g_items.size();
    for (int k = 0; k < visible && first + k < g_npool_names; k++) {
        const char* nm = g_pool_names[first + k];
        float y = list0 + k * rowh;
        bool f = item(x0 + 20, y, x1 - 20, y + rowh - 6);
        bool in = false;
        for (int p = 0; p < g_nparty; p++) in |= !_stricmp(g_party[p], nm);
        int tier = 3, t, st;
        if (bot_pool_saved_of(nm, &t, &st)) tier = t;
        player_row(x0, y, rx1, y + ROW_H, nm, profile_clan_of(nm), -1, tier, false, in, 1);
        g_dl->AddRectFilled(P(bt0, y), P(x1 - 24, y + ROW_H), A(f ? C_FOCUS : C_ROW));
        if (f) g_dl->AddRect(P(bt0, y), P(x1 - 24, y + ROW_H), A(C_LIT), 0, 0, U(1.6f));
        text(g_fl, 20, (bt0 + x1 - 24) * 0.5f, y + 10, in ? C_GOLD : C_TEXT, in ? "REMOVE" : "INVITE", 1);
        if (pressed(base + k)) {
            if (in) {
                for (int p = 0; p < g_nparty; p++)
                    if (!_stricmp(g_party[p], nm)) { for (int q = p; q < g_nparty - 1; q++) strcpy_s(g_party[q], g_party[q + 1]); g_nparty--; break; }
                sound(PS_BACK);
            } else if (g_nparty < cur_pl().size - 1 && g_nparty < 8) {
                strcpy_s(g_party[g_nparty++], nm);
                sound(PS_SELECT);
            } else sound(PS_ERROR);
            save_settings();
        }
    }
    // keys: at the list's edge the list moves instead of the focus (frame_keys moves the focus after this)
    int fk = g_focus - base;
    bool down = ImGui::IsKeyPressed(ImGuiKey_DownArrow) || ImGui::IsKeyPressed(ImGuiKey_GamepadDpadDown) ||
                ImGui::IsKeyPressed(ImGuiKey_GamepadLStickDown);           // (Nov 19: the left stick too)
    bool up = ImGui::IsKeyPressed(ImGuiKey_UpArrow) || ImGui::IsKeyPressed(ImGuiKey_GamepadDpadUp) ||
              ImGui::IsKeyPressed(ImGuiKey_GamepadLStickUp);
    if (down && fk == visible - 1 && first + visible < g_npool_names) { g_invite_scroll += 1; g_focus--; }
    if (up && fk == 0 && first > 0) { g_invite_scroll -= 1; g_focus++; }
    // (Nov 19) a page at a time: RB / Page Down, LB / Page Up (the focus keeps its place on the page)
    int page = (ImGui::IsKeyPressed(ImGuiKey_GamepadR1) || ImGui::IsKeyPressed(ImGuiKey_PageDown)) ? 1
             : (ImGui::IsKeyPressed(ImGuiKey_GamepadL1) || ImGui::IsKeyPressed(ImGuiKey_PageUp)) ? -1 : 0;
    if (page && g_npool_names > visible) {
        float s = g_invite_scroll + page * visible, top = (float)(g_npool_names - visible);
        s = s < 0 ? 0 : s > top ? top : s;
        if (s != g_invite_scroll) { g_invite_scroll = s; sound(PS_MOVE); }
    }
    char more[96];
    sprintf_s(more, g_pad_in ? "%d bots in your pool  (LB / RB: a page at a time)"
                             : "%d bots in your pool  (wheel, arrows or Page Up / Down to scroll)", g_npool_names);
    text(g_fs, 20, x0 + 26, y1 - 52, C_DIM, more);
    footer("Invite a bot to your party. Party members are always on your team.", "Invite");
    (void)e;
}

// ------------------------------------------------------------------ the challenges, as Bungie.net's Reach page
// (Nov 17: the challenges in game (the Service Record session's note), the owner's picture of Bungie.net's Halo: Reach
// Challenges page, then "Make it correlate to our website as well. They have to be connected") The menu's CHALLENGES:
// this week's weekly, then today's 4 dailies, each a dark row: the icon, the name, what to do, the time left (its
// seconds in orange) and the cR, the bar with its tick and n/need, or Completed; each section's header with how many
// the player has completed. Everything comes from <repo>\logs\service_record\challenges.txt, which the Service Record's
// own build writes with the site (tools/service_record.py write_game_challenges): the same challenges, progress and
// counts as the site's Challenges page, nothing worked out here; read again whenever the site is rebuilt. The icons are
// the site's own pictures (logs\service_record\icons, the names app.js NEON gives each kind). The time left runs out
// here as on the site: "Ended" until the next build draws new ones. Y opens the player's Challenges page on the site.
static void split_tabs(char* s, std::vector<std::string>& out) {   // a line's tab-separated fields
    out.clear();
    for (char* tab; ; s = tab + 1) {
        tab = strchr(s, '\t');
        if (tab) *tab = 0;
        out.push_back(s);
        if (!tab) break;
    }
}
static std::string cr_text(int v) {                       // 12,345 (as the site writes credits)
    char s[24];
    sprintf_s(s, "%d", v < 0 ? -v : v);
    std::string o;
    int n = (int)strlen(s);
    for (int i = 0; i < n; i++) { o += s[i]; if ((n - i - 1) % 3 == 0 && i < n - 1) o += ','; }
    return v < 0 ? "-" + o : o;
}
struct chal_item { std::string period, key, name, what, icon; int need, cr; };
static std::vector<chal_item> g_chal_items;
static long long g_chal_ends[2];                 // weekly, daily: when they end (seconds since 1970)
static std::string g_chal_who;                   // the person whose progress it shows
static int g_chal_done[2], g_chal_cr;            // weekly, daily completed; challenge cR
static std::vector<std::pair<std::string, int>> g_chal_now;   // progress on the live ones
static ULONGLONG g_chal_check, g_chal_stamp;
static bool g_chal_have;

static void chal_load() {
    ULONGLONG now = GetTickCount64();
    if (g_chal_check && now - g_chal_check < 2000) return;
    g_chal_check = now;
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\logs\\service_record\\challenges.txt", g_root);
    WIN32_FILE_ATTRIBUTE_DATA fa;
    ULONGLONG stamp = GetFileAttributesExW(p, GetFileExInfoStandard, &fa) ? ft_u64(fa.ftLastWriteTime) : 0;
    if (stamp == g_chal_stamp) return;
    g_chal_stamp = stamp;
    g_chal_items.clear(); g_chal_now.clear(); g_chal_who.clear();
    g_chal_ends[0] = g_chal_ends[1] = 0; g_chal_done[0] = g_chal_done[1] = 0; g_chal_cr = 0;
    g_chal_have = false;
    FILE* f = nullptr;
    if (!stamp || _wfopen_s(&f, p, L"rb") || !f) return;
    std::vector<std::vector<std::string>> rows;
    char line[1024];
    std::vector<std::string> c;
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#') continue;
        line[strcspn(line, "\r\n")] = 0;
        split_tabs(line, c);
        rows.push_back(c);
    }
    fclose(f);
    g_chal_have = true;
    for (auto& r : rows) {
        if (r[0] == "period" && r.size() >= 4) g_chal_ends[r[1] == "weekly" ? 0 : 1] = _atoi64(r[3].c_str());
        else if (r[0] == "challenge" && r.size() >= 8)
            g_chal_items.push_back({ r[1], r[2], r[3], r[4], r[7], atoi(r[5].c_str()), atoi(r[6].c_str()) });
        else if (r[0] == "person" && r.size() >= 5 && (g_chal_who.empty() || !_stricmp(r[1].c_str(), me_name()))) {
            g_chal_who = r[1];                               // (the player by MCC's name, else the first listed)
            g_chal_done[1] = atoi(r[2].c_str()); g_chal_done[0] = atoi(r[3].c_str()); g_chal_cr = atoi(r[4].c_str());
        }
    }
    for (auto& r : rows)
        if (r[0] == "progress" && r.size() >= 4 && r[1] == g_chal_who) g_chal_now.push_back({ r[2], atoi(r[3].c_str()) });
}

// a challenge kind's icon: the site's own picture (app.js NEON), assists its drawn one (app.js ICONS.assists)
static void chal_icon(const std::string& kind, float cx, float cy, float s) {
    static const char* K[][2] = { {"games", "s_controller"}, {"win", "s_star"}, {"kills", "s_crosshair"},
                                  {"deaths", "s_skull"}, {"stat-medals", "s_medal"}, {"spree", "s_layers"},
                                  {"weapons", "s_dmr"} };
    for (auto& k : K)
        if (kind == k[0]) {
            wchar_t p[MAX_PATH];
            swprintf_s(p, L"%s\\logs\\service_record\\icons\\%S.png", g_root, k[1]);
            if (const pic* pc = picture(p)) {
                g_dl->AddImage((ImTextureID)pc->tex, P(cx - s * 0.5f, cy - s * 0.5f), P(cx + s * 0.5f, cy + s * 0.5f),
                               ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
                return;
            }
        }
    // the drawn ones (a 24-unit box): assists, and any kind without its picture on this PC
    float u = s / 24.0f, x0 = cx - 12 * u, y0 = cy - 12 * u;
    auto pt = [&](float x, float y) { return P(x0 + x * u, y0 + y * u); };
    if (kind == "assists") {
        ImVec2 a[5] = { pt(4, 13), pt(8, 17), pt(11, 15.5f), pt(14, 18), pt(20, 12) };
        ImVec2 b[5] = { pt(4, 13), pt(9, 8), pt(12, 10), pt(15, 7), pt(20, 12) };
        g_dl->AddPolyline(a, 5, A(IM_COL32(255, 255, 255, 255)), 0, U(1.7f * u));
        g_dl->AddPolyline(b, 5, A(IM_COL32(255, 255, 255, 255)), 0, U(1.7f * u));
    } else crest(cx, cy, s * 0.42f, IM_COL32(255, 255, 255, 255));
}

static std::string url_part(const std::string& s) {      // encodeURIComponent
    std::string o;
    for (unsigned char ch : s) {
        if (isalnum(ch) || strchr("-_.!~*'()", ch)) o += (char)ch;
        else { char h[4]; sprintf_s(h, "%%%02X", ch); o += h; }
    }
    return o;
}
// the player's Challenges page on the site, in the browser: the Service Record's editor started first if it is not
// running (tools/service_record_editor.cmd /startup), a moment for it to listen, then
// http://localhost:8766/#/p/<name>/challenges (Nov 19: or another of the player's pages, /commendations)
static void open_site_page(const std::string& who, const char* page) {
    std::string u = "http://localhost:8766/#/p/" + url_part(who.empty() ? me_name() : who) + "/" + page;
    wchar_t cmd[2048];
    swprintf_s(cmd, L"cmd.exe /c \"\"%s\\tools\\service_record_editor.cmd\" /startup & ping -n 3 127.0.0.1 >nul & start \"\" \"%S\"\"",
               g_root, u.c_str());
    STARTUPINFOW si{};
    si.cb = sizeof si;
    PROCESS_INFORMATION pi{};
    if (CreateProcessW(nullptr, cmd, nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi)) {
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        logf("proving grounds: opening the Service Record's %s", page);
    }
}
static void open_site_challenges() { open_site_page(g_chal_who, "challenges"); }

static void challenges_screen(pg_env& e, float t) {
    (void)e; (void)t;
    chal_load();
    header("PROVING GROUNDS", "CHALLENGES", 0);
    float x0 = 410, x1 = 1510;
    long long now = (long long)time(nullptr);
    if (!g_chal_have || g_chal_items.empty()) {
        reach_panel(x0, 300, x1, 520);
        text(g_fl, 30, (x0 + x1) * 0.5f, 360, C_REACH_TEXT, "NO CHALLENGES YET", 1);
        text(g_fs, 22, (x0 + x1) * 0.5f, 420, C_REACH_DIM, "The Service Record draws them when it is next built (a match starting or ending).", 1);
    } else {
        float y = 150;
        for (int sec = 0; sec < 2; sec++) {                  // the weekly, then the dailies
            const char* per = sec == 0 ? "weekly" : "daily";
            g_dl->AddRectFilled(P(x0, y), P(x1, y + 40), A(IM_COL32(12, 14, 17, 215)));
            text(g_fl, 22, x0 + 18, y + 8, C_REACH_TEXT, sec == 0 ? "Weekly Challenge:" : "Daily Challenges:");
            char cnt[64];
            sprintf_s(cnt, "%s Challenges Completed:  %d", sec == 0 ? "Weekly" : "Daily", g_chal_done[sec]);
            text(g_fl, 22, x1 - 18, y + 8, C_REACH_TEXT, cnt, 2);
            y += 48;
            long long left = g_chal_ends[sec] - now;
            for (const chal_item& c : g_chal_items) {
                if (c.period != per) continue;
                float rh = 112;
                g_dl->AddRectFilled(P(x0, y), P(x1, y + rh), A(IM_COL32(24, 26, 30, 232)));
                chal_icon(c.icon, x0 + 72, y + rh * 0.5f, 84);
                int n = 0;
                for (auto& kv : g_chal_now) if (kv.first == c.key) n = kv.second;
                bool done = c.need > 0 && n >= c.need;
                float tx = x0 + 150;
                text(g_fl, 25, tx, y + 12, C_REACH_TEXT, c.name.c_str());
                text(g_fs, 19, tx + 2, y + 46, C_REACH_DIM, c.what.c_str());
                // the cR at the right, the time left before it (its seconds in orange)
                char crs[24];
                sprintf_s(crs, "%scR", cr_text(c.cr).c_str());
                text(g_fl, 23, x1 - 18, y + 13, C_REACH_TEXT, crs, 2);
                float rx = x1 - 18 - text_w(g_fl, 23, crs) / g_pg.s - 28;
                if (left <= 0) text(g_fl, 23, rx, y + 13, C_REACH_DIM, "Ended", 2);
                else {
                    char secs[8], rest[32];
                    sprintf_s(secs, "%llds", left % 60);
                    sprintf_s(rest, "%lldd %lldh %lldm ", left / 86400, left % 86400 / 3600, left % 3600 / 60);
                    text(g_fl, 23, rx, y + 13, IM_COL32(236, 108, 64, 255), secs, 2);
                    text(g_fl, 23, rx - text_w(g_fl, 23, secs) / g_pg.s, y + 13, C_REACH_TEXT, rest, 2);
                }
                // the bar: its share lit, a tick where it ends, n/need (or Completed) at its right
                float bx0 = tx, bx1 = x1 - 18, by = y + rh - 34;
                float share = c.need > 0 ? (float)(n < c.need ? n : c.need) / c.need : 0;
                g_dl->AddRectFilled(P(bx0, by), P(bx1, by + 20), A(IM_COL32(78, 86, 96, 235)));
                float fx = bx0 + (bx1 - bx0) * share;
                if (share > 0)
                    g_dl->AddRectFilled(P(bx0, by), P(fx, by + 20), A(done ? IM_COL32(120, 176, 214, 245) : IM_COL32(138, 150, 162, 245)));
                if (!done) g_dl->AddRectFilled(P(fx - 1, by - 5), P(fx + 2, by + 25), A(IM_COL32(245, 248, 250, 255)));
                char num[32];
                if (done) strcpy_s(num, "Completed"); else sprintf_s(num, "%d/%d", n, c.need);
                text(g_fs, 17, bx1 - 8, by + 1, C_REACH_TEXT, num, 2);
                y += rh + 8;
            }
            y += 14;
        }
        char cr[64];
        sprintf_s(cr, "Challenge cR:  %s", cr_text(g_chal_cr).c_str());
        text(g_fl, 22, x1, 112, C_REACH_DIM, cr, 2);
    }
    // the footer: Back, and Y: the same page on the Service Record site
    footer_line();
    float x = prompt(100, 992, "B", "Esc", "Back", &g_footer_back);
    bool site = false;
    prompt(x, 992, "Y", "Tab", "Challenges on the Service Record", &site);
    if (site || ImGui::IsKeyPressed(ImGuiKey_GamepadFaceUp, false) || ImGui::IsKeyPressed(ImGuiKey_Tab, false)) {
        sound(PS_SELECT);
        open_site_challenges();
    }
}

// ------------------------------------------------------------------ the commendations, as Reach's Service Record
// (Nov 19, the owner's picture of Halo: Reach's Service Record: Commendations, "add it to ours with its own menu option,
// and keep it connected to the service record site") The menu's COMMENDATIONS: Reach's page. Its lists at the left
// (Top Commendations, then the site's two sets: Multiplayer, Proving Grounds' own), the list at the right (each its
// banner, the tier reached, the bar toward the next tier with n/need, sorted as the site's Commendations page sorts
// them: tier, then progress), the player's band along the bottom (emblem, rank insignia, name, rank, credits, the next
// rank). Everything from <repo>\logs\service_record\commendations.txt, which the Service Record's build writes with the
// site (tools/service_record.py write_game_commendations; the tier reached is the site's, not worked out here); read
// again whenever the site is rebuilt. Up / Down move through the list, Left / Right or LB / RB change list, Y (Tab)
// opens the player's Commendations page on the site.
struct comm_item { std::string key, set, name, what, banner; std::vector<int> need, cr; std::vector<std::string> tier_art; };
struct comm_now { int n, tier; };                // n -1: not recorded yet
static std::vector<comm_item> g_comm_items;
static std::vector<comm_now> g_comm_now;         // (one for each item, in its order)
static std::vector<std::string> g_comm_tiers;
static std::string g_comm_who, g_comm_rank, g_comm_next;
static float g_comm_pct;
static int g_comm_cr, g_comm_next_cr = -1, g_comm_tab;
static float g_comm_scroll;
static ULONGLONG g_comm_check, g_comm_stamp;
static bool g_comm_have;
static const ImU32 TIER_COL[7] = { IM_COL32(150, 156, 162, 255), IM_COL32(142, 149, 157, 255), IM_COL32(192, 132, 76, 255),
                                   IM_COL32(207, 219, 230, 255), IM_COL32(232, 178, 60, 255), IM_COL32(155, 92, 217, 255),
                                   IM_COL32(216, 50, 58, 255) };   // (none, then the site's own: style.css --tier-*)

static void comm_load() {
    ULONGLONG now = GetTickCount64();
    if (g_comm_check && now - g_comm_check < 2000) return;
    g_comm_check = now;
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\logs\\service_record\\commendations.txt", g_root);
    WIN32_FILE_ATTRIBUTE_DATA fa;
    ULONGLONG stamp = GetFileAttributesExW(p, GetFileExInfoStandard, &fa) ? ft_u64(fa.ftLastWriteTime) : 0;
    if (stamp == g_comm_stamp) return;
    g_comm_stamp = stamp;
    g_comm_items.clear(); g_comm_now.clear(); g_comm_tiers.clear(); g_comm_who.clear();
    g_comm_rank.clear(); g_comm_next.clear(); g_comm_pct = 0; g_comm_cr = 0; g_comm_next_cr = -1;
    g_comm_have = false;
    FILE* f = nullptr;
    if (!stamp || _wfopen_s(&f, p, L"rb") || !f) return;
    std::vector<std::vector<std::string>> rows;
    char line[4096];
    std::vector<std::string> c;
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#') continue;
        line[strcspn(line, "\r\n")] = 0;
        split_tabs(line, c);
        rows.push_back(c);
    }
    fclose(f);
    g_comm_have = true;
    auto list = [](const std::string& s) {               // "a,b,c" (empties kept)
        std::vector<std::string> v;
        for (size_t a = 0;;) { size_t b = s.find(',', a); v.push_back(s.substr(a, b == std::string::npos ? b : b - a)); if (b == std::string::npos) break; a = b + 1; }
        return v;
    };
    for (auto& r : rows) {
        if (r[0] == "tiers") g_comm_tiers.assign(r.begin() + 1, r.end());
        else if (r[0] == "commendation" && r.size() >= 9) {
            comm_item it{ r[1], r[2], r[3], r[4], r[7] };
            for (auto& s : list(r[5])) it.need.push_back(atoi(s.c_str()));
            for (auto& s : list(r[6])) it.cr.push_back(atoi(s.c_str()));
            it.tier_art = list(r[8]);
            if (!it.need.empty()) g_comm_items.push_back(it);
        } else if (r[0] == "person" && r.size() >= 7 && (g_comm_who.empty() || !_stricmp(r[1].c_str(), me_name()))) {
            g_comm_who = r[1];                               // (the player by MCC's name, else the first listed)
            g_comm_pct = (float)atof(r[2].c_str()); g_comm_cr = atoi(r[3].c_str());
            g_comm_rank = r[4]; g_comm_next = r[5]; g_comm_next_cr = r[6].empty() ? -1 : atoi(r[6].c_str());
        }
    }
    g_comm_now.assign(g_comm_items.size(), comm_now{ -1, 0 });
    for (auto& r : rows)
        if (r[0] == "count" && r.size() >= 5 && r[1] == g_comm_who)
            for (size_t i = 0; i < g_comm_items.size(); i++)
                if (g_comm_items[i].key == r[2]) g_comm_now[i] = { r[3].empty() ? -1 : atoi(r[3].c_str()), atoi(r[4].c_str()) };
}

// a picture whole inside the box (contained, not cropped), centred
static void image_fit(const pic* p, float x0, float y0, float x1, float y1, float a = 1.0f) {
    float bw = x1 - x0, bh = y1 - y0, s = bw / p->w < bh / p->h ? bw / p->w : bh / p->h, w = p->w * s, h = p->h * s;
    float cx = (x0 + x1) * 0.5f, cy = (y0 + y1) * 0.5f;
    g_dl->AddImage((ImTextureID)p->tex, P(cx - w * 0.5f, cy - h * 0.5f), P(cx + w * 0.5f, cy + h * 0.5f), ImVec2(0, 0),
                   ImVec2(1, 1), A(IM_COL32(255, 255, 255, (int)(255 * a))));
}
static const pic* site_picture(const std::string& rel) {   // a picture of the site's, by its path under the site
    if (rel.empty()) return nullptr;
    std::wstring w(rel.begin(), rel.end());
    for (auto& ch : w) if (ch == L'/') ch = L'\\';
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\logs\\service_record\\%s", g_root, w.c_str());
    return picture(p);
}

static void comm_screen(pg_env& e, float t) {
    (void)e; (void)t;
    comm_load();
    header("PROVING GROUNDS", "SERVICE RECORD", 0);
    static const char* TAB[3] = { "TOP COMMENDATIONS", "MULTIPLAYER", "PROVING GROUNDS" };
    static const char* TITLE[3] = { "Top Commendations", "Multiplayer Commendations", "Proving Grounds Commendations" };
    // the lists, at the left: Left / Right, LB / RB or a click change them
    int tab_was = g_comm_tab;
    for (int k = 0; k < 3; k++) {
        float y = 196 + 46.0f * k;
        if (k == g_comm_tab) focus_band(96, y, 520, y + 40);
        text(g_fl, 22, 112, y + 8, k == g_comm_tab ? C_TEXT : C_DIM, TAB[k]);
        ImVec2 m = ImGui::GetIO().MousePos, a = P(96, y), b = P(520, y + 40);
        if (ImGui::IsMouseClicked(0) && m.x >= a.x && m.x <= b.x && m.y >= a.y && m.y <= b.y) g_comm_tab = k;
    }
    if (g_left_right) { g_lr_taken = true; g_comm_tab = (g_comm_tab + 3 + g_left_right) % 3; }
    if (ImGui::IsKeyPressed(ImGuiKey_GamepadR1, false)) g_comm_tab = (g_comm_tab + 1) % 3;
    if (ImGui::IsKeyPressed(ImGuiKey_GamepadL1, false)) g_comm_tab = (g_comm_tab + 2) % 3;
    if (g_comm_tab != tab_was) { g_comm_scroll = 0; g_focus = 0; sound(PS_MOVE); }
    const float lx0 = 600, lx1 = 1500;
    if (!g_comm_have || g_comm_items.empty()) {
        reach_panel(lx0, 300, lx1, 520);
        text(g_fl, 30, (lx0 + lx1) * 0.5f, 360, C_REACH_TEXT, "NO COMMENDATIONS YET", 1);
        text(g_fs, 22, (lx0 + lx1) * 0.5f, 420, C_REACH_DIM, "The Service Record writes them when it is next built (a match starting or ending).", 1);
        footer_line();
        prompt(100, 992, "B", "Esc", "Back", &g_footer_back);
        return;
    }
    // this list, as the site sorts it: the tier reached, then the share toward the next, then the name
    auto share = [&](int i) {
        const comm_item& c = g_comm_items[i];
        const comm_now& s = g_comm_now[i];
        if (s.n < 0) return 0.0f;
        if (s.tier >= (int)c.need.size()) return 1.0f;
        int from = s.tier ? c.need[s.tier - 1] : 0, to = c.need[s.tier];
        float k = to > from ? (float)(s.n - from) / (to - from) : 1.0f;
        return k < 0 ? 0 : k > 1 ? 1 : k;
    };
    std::vector<int> order;
    for (int i = 0; i < (int)g_comm_items.size(); i++)
        if (g_comm_tab == 0 || g_comm_items[i].set == (g_comm_tab == 1 ? "mp" : "pg")) order.push_back(i);
    std::stable_sort(order.begin(), order.end(), [&](int a, int b) {
        if (g_comm_now[a].tier != g_comm_now[b].tier) return g_comm_now[a].tier > g_comm_now[b].tier;
        float sa = share(a), sb = share(b);
        if (sa != sb) return sa > sb;
        return _stricmp(g_comm_items[a].name.c_str(), g_comm_items[b].name.c_str()) < 0;
    });
    text(g_fl, 24, lx0, 190, C_TEXT, TITLE[g_comm_tab]);
    char pct[48];
    sprintf_s(pct, "Overall Progress: %.1f%%", g_comm_pct);
    text(g_fs, 20, lx1, 194, C_DIM, pct, 2);
    g_dl->AddLine(P(lx0, 226), P(lx1, 226), A(IM_COL32(206, 212, 218, 110)), U(1));
    // the rows: six at a time, the list moving at its edges (wheel, Up / Down, the left stick)
    const float ry0 = 236, rh = 84, rs = 90;
    const int visible = 6, total = (int)order.size();
    g_comm_scroll -= ImGui::GetIO().MouseWheel * 2;
    int maxs = total - visible;
    if (g_comm_scroll > maxs) g_comm_scroll = (float)(maxs > 0 ? maxs : 0);
    if (g_comm_scroll < 0) g_comm_scroll = 0;
    int first = (int)g_comm_scroll, base = (int)g_items.size(), focused = -1;
    for (int k = 0; k < visible && first + k < total; k++) {
        int i = order[first + k];
        const comm_item& c = g_comm_items[i];
        const comm_now& s = g_comm_now[i];
        float y = ry0 + k * rs;
        bool f = item(lx0, y, lx1, y + rh);
        if (f) { focus_band(lx0, y, lx1, y + rh); focused = i; }
        else g_dl->AddRectFilled(P(lx0, y), P(lx1, y + rh), A(C_ROW));
        // its banner: the tier reached's own (the owner's emblem of that tier), else Reach's
        const pic* bp = s.tier > 0 && s.tier <= (int)c.tier_art.size() ? site_picture(c.tier_art[s.tier - 1]) : nullptr;
        if (!bp) bp = site_picture(c.banner);
        if (bp) image_fit(bp, lx0 + 8, y + 4, lx0 + 252, y + rh - 4, s.n < 0 ? 0.45f : 1.0f);
        else { panel(lx0 + 8, y + 6, lx0 + 252, y + rh - 6, IM_COL32(40, 70, 104, 200)); crest(lx0 + 130, y + rh * 0.5f, 26, C_DIM); }
        float tx = lx0 + 272, bx1 = lx1 - 16;
        text(g_fl, 25, tx, y + 8, s.n < 0 ? C_DIM : C_TEXT, c.name.c_str());
        bool done = s.tier >= (int)c.need.size();
        const char* tl = s.n < 0 ? "Not recorded yet" : s.tier > 0 && s.tier <= (int)g_comm_tiers.size() ? g_comm_tiers[s.tier - 1].c_str() : "Not started";
        text(g_fl, 21, bx1, y + 11, s.tier > 0 ? TIER_COL[s.tier < 7 ? s.tier : 6] : C_DIM, tl, 2);
        // the bar toward the next tier, in the colour of the tier reached (the owner, Nov 19: "the color of the tier it's
        // at currently"; grey before Iron)
        float by = y + 46, sh = share(i), fx = tx + (bx1 - tx) * sh;
        g_dl->AddRectFilled(P(tx, by), P(bx1, by + 22), A(IM_COL32(34, 38, 42, 215)));
        if (sh > 0) {
            ImU32 tc = TIER_COL[s.tier < 7 ? s.tier : 6];
            int r = tc & 255, g = (tc >> 8) & 255, b = (tc >> 16) & 255;
            g_dl->AddRectFilledMultiColor(P(tx, by), P(fx, by + 22), A(IM_COL32(r * 70 / 100, g * 70 / 100, b * 70 / 100, 235)),
                                          A(tc), A(tc), A(IM_COL32(r * 70 / 100, g * 70 / 100, b * 70 / 100, 235)));
        }
        g_dl->AddRect(P(tx, by), P(bx1, by + 22), A(IM_COL32(120, 128, 136, 130)), 0, 0, U(1));
        if (s.n >= 0) {
            std::string nums = done ? cr_text(s.n) : cr_text(s.n) + "/" + cr_text(c.need[s.tier]);
            text(g_fs, 17, bx1 - 8, by + 1, C_TEXT, nums.c_str(), 2);
        }
        g_dl->AddLine(P(lx0, y + rs - 3), P(lx1, y + rs - 3), A(IM_COL32(150, 158, 166, 60)), U(1));
    }
    // more above or below: Reach's small chevrons
    auto chevron = [&](float y, bool down) {
        float cx = (lx0 + lx1) * 0.5f, d = down ? 7.0f : -7.0f;
        ImVec2 v[3] = { P(cx - 12, y - d), P(cx, y + d), P(cx + 12, y - d) };
        g_dl->AddPolyline(v, 3, A(IM_COL32(220, 226, 232, 220)), 0, U(2));
    };
    if (first > 0) chevron(230 - 14, false);
    if (first + visible < total) chevron(ry0 + visible * rs + 4, true);
    int fk = g_focus - base;
    bool down = ImGui::IsKeyPressed(ImGuiKey_DownArrow) || ImGui::IsKeyPressed(ImGuiKey_GamepadDpadDown) ||
                ImGui::IsKeyPressed(ImGuiKey_GamepadLStickDown);
    bool up = ImGui::IsKeyPressed(ImGuiKey_UpArrow) || ImGui::IsKeyPressed(ImGuiKey_GamepadDpadUp) ||
              ImGui::IsKeyPressed(ImGuiKey_GamepadLStickUp);
    if (down && fk == visible - 1 && first + visible < total) { g_comm_scroll += 1; g_focus--; }
    if (up && fk == 0 && first > 0) { g_comm_scroll -= 1; g_focus++; }
    // the player's band, as Reach's: the emblem, the rank insignia, the name over the rank, the credits and the next rank
    const float py0 = 800, py1 = 916;
    g_dl->AddRectFilledMultiColor(P(96, py0), P(lx1, py1), A(IM_COL32(46, 50, 54, 205)), A(IM_COL32(22, 25, 28, 150)),
                                  A(IM_COL32(22, 25, 28, 150)), A(IM_COL32(46, 50, 54, 205)));
    g_dl->AddLine(P(96, py0), P(lx1, py0), A(IM_COL32(214, 220, 226, 110)), U(1));
    int32_t emb[5];
    int np = -1;
    unsigned long long em = g_make && mcc_player_look(emb, &np) ? player_emblem(emb, g_make) : 0;
    if (em) g_dl->AddImage((ImTextureID)em, P(108, py0 + 8), P(208, py0 + 108), ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
    else crest(158, py0 + 58, 40, C_TEXT);
    const char* who = g_comm_who.empty() ? me_name() : g_comm_who.c_str();
    if (const pic* rp = sr_rank_picture(sr_rank_of(who, false))) image_fit(rp, 224, py0 + 14, 288, py0 + 78);
    text(g_fl, 34, 304, py0 + 12, C_TEXT, who);
    g_dl->AddRectFilled(P(300, py0 + 64), P(1100, py0 + 100), A(IM_COL32(255, 255, 255, 20)));
    text(g_fl, 23, 308, py0 + 69, C_DIM, g_comm_rank.empty() ? "..." : g_comm_rank.c_str());
    std::string crs = cr_text(g_comm_cr) + " cR";
    text(g_fl, 40, lx1 - 16, py0 + 8, C_TEXT, crs.c_str(), 2);
    if (!g_comm_next.empty()) {
        std::string nx = "Next: " + g_comm_next;
        if (g_comm_next_cr > g_comm_cr) nx += " in " + cr_text(g_comm_next_cr - g_comm_cr) + " cR";
        text(g_fl, 21, lx1 - 16, py0 + 70, C_DIM, nx.c_str(), 2);
    }
    // the footer: the focused one's what and its next tier, as the site words it; Back, the lists, the site
    std::string hint;
    if (focused >= 0) {
        const comm_item& c = g_comm_items[focused];
        const comm_now& s = g_comm_now[focused];
        hint = c.what + "  ";
        if (s.n < 0) hint += "Not recorded yet.";
        else if (s.tier >= (int)c.need.size()) hint += cr_text(s.n) + ": every tier reached.";
        else {
            hint += cr_text(s.n) + " of " + cr_text(c.need[s.tier]) + " for " +
                    (s.tier < (int)g_comm_tiers.size() ? g_comm_tiers[s.tier] : std::string("the next tier"));
            if (s.tier < (int)c.cr.size() && c.cr[s.tier]) hint += " (+" + cr_text(c.cr[s.tier]) + " cR)";
            hint += ".";
        }
    }
    footer_line();
    if (!hint.empty()) text(g_fs, 21, 100, 948, IM_COL32(200, 206, 212, 255), hint.c_str());
    float x = prompt(100, 992, "B", "Esc", "Back", &g_footer_back);
    x = prompt(x, 992, "LB/RB", "Left/Right", "Lists", nullptr);
    bool site = false;
    prompt(x, 992, "Y", "Tab", "Commendations on the Service Record", &site);
    if (site || ImGui::IsKeyPressed(ImGuiKey_GamepadFaceUp, false) || ImGui::IsKeyPressed(ImGuiKey_Tab, false)) {
        sound(PS_SELECT);
        open_site_page(g_comm_who, "commendations");
    }
}

static void menu_screen(pg_env& e, float t) {
    if (ros_up()) { session_panel(e); return; }          // (the roster has the focus: Reach's list and its panel)
    header("MULTIPLAYER", "PROVING GROUNDS", 0);
    text(g_fl, 24, 96, 188, C_TEXT, "COMPOSE YOUR MATCH");
    // the card: a map of the playlist behind our crest
    panel(96, 215, 880, 340, IM_COL32(18, 20, 23, 190));
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    library();
    playlist_pool(cur_pl(), gts, maps);
    if (!maps.empty()) {
        const pic* p = map_picture(maps[(int)(t / 6) % maps.size()]->key);
        if (p) image(p, 330, 217, 878, 338, 0.85f);      // (Nov 19: brighter, 0.55 before)
        g_dl->AddRectFilledMultiColor(P(97, 216), P(879, 339), A(IM_COL32(18, 20, 23, 235)), A(IM_COL32(18, 20, 23, 20)),
                                      A(IM_COL32(18, 20, 23, 20)), A(IM_COL32(18, 20, 23, 235)));
    }
    crest(170, 278, 44, IM_COL32(232, 236, 240, 255));
    text(g_fl, 40, 238, 236, C_TEXT, "PROVING GROUNDS");
    text(g_fl, 24, 240, 286, C_BLUE, cur_pl().title);
    const char* desc[7] = { "Find a game: a lobby of bots from your pool, then the vote.",
                            "Arena is 4v4, Big Team Battle 8v8.",
                            "Bots who play on your team every game, whatever the lobby.",
                            "Today's and this week's challenges, as your Service Record has them.",
                            "Your commendations, tiers and progress, as your Service Record has them.",
                            "Bots play matches of their own for the Service Record. Left / Right: how many rounds (a round is about 25 lobbies).",
                            "Leave Proving Grounds for MCC's own lobby." };
    int base = (int)g_items.size();
    // (Nov 18: the rows 48 tall, 8 apart, so SIMULATE MATCHES fits above the games and categories; Nov 19: 44 tall, 6
    // apart, for COMMENDATIONS too)
    auto ry = [](int k) { return 352.0f + 50.0f * k; };
    const float RH = 44;
    bool f0 = item(96, ry(0), 880, ry(0) + RH);
    row(96, ry(0), 880, ry(0) + RH, f0, "PLAY");
    bool f1 = item(96, ry(1), 880, ry(1) + RH);
    char sz[32];
    sprintf_s(sz, "%dV%d (TEAM)", cur_pl().size, cur_pl().size);
    row(96, ry(1), 880, ry(1) + RH, f1, "GAME SIZE", sz, true);
    bool f2 = item(96, ry(2), 880, ry(2) + RH);
    char inv[32];
    sprintf_s(inv, "%d / %d", g_nparty, cur_pl().size - 1);
    row(96, ry(2), 880, ry(2) + RH, f2, "INVITE PLAYER", inv);
    bool f3 = item(96, ry(3), 880, ry(3) + RH);          // (Nov 17: the challenges, as the Service Record has them)
    chal_load();
    int live = 0, done = 0;
    for (const chal_item& c : g_chal_items) {
        live++;
        for (auto& kv : g_chal_now) if (kv.first == c.key && kv.second >= c.need) done++;
    }
    char chs[32];
    sprintf_s(chs, "%d / %d", done, live);
    row(96, ry(3), 880, ry(3) + RH, f3, "CHALLENGES", live ? chs : nullptr);
    bool f4 = item(96, ry(4), 880, ry(4) + RH);          // (Nov 19: the commendations, as the Service Record has them)
    comm_load();
    char cms[32];
    sprintf_s(cms, "%.1f%%", g_comm_pct);
    row(96, ry(4), 880, ry(4) + RH, f4, "COMMENDATIONS", g_comm_have && !g_comm_items.empty() ? cms : nullptr);
    bool f5 = item(96, ry(5), 880, ry(5) + RH);          // (Nov 18: the bot simulation, a round at a time)
    double now = ImGui::GetTime();
    sim_poll(now);
    char sims[48];
    bool sim_arrows = false;
    if (g_sim_proc) strcpy_s(sims, "PLAYING...");
    else if (g_sim_done_at >= 0 && now - g_sim_done_at < 10.0 && g_sim_made >= 0) sprintf_s(sims, "DONE: %d MATCHES", g_sim_made);
    else { sprintf_s(sims, "%d ROUND%s", g_sim_rounds, g_sim_rounds == 1 ? "" : "S"); sim_arrows = true; }
    row(96, ry(5), 880, ry(5) + RH, f5, "SIMULATE MATCHES", sims, sim_arrows);
    text(g_fl, 24, 96, 660, C_BLUE, "GAMES INCLUDED");   // (Nov 19: these a little smaller, under six rows)
    panel(96, 688, 236, 776, IM_COL32(18, 20, 23, 170));
    text(g_fl, 30, 166, 716, C_TEXT, "REACH", 1);
    g_dl->AddRectFilled(P(102, 756), P(116, 770), A(C_BLUE));
    text(g_fl, 24, 96, 788, C_BLUE, "GAME CATEGORIES INCLUDED");
    category_tiles(96, 816, 106);
    stats_panel(1000, 215);                              // (Nov 17: level with the card, clear of the category tiles)
    session_panel(e);
    int focus = g_focus - base;
    if (!g_invite) footer(desc[focus >= 0 && focus < 6 ? focus : 6], "Select", true);   // (the invite list: its own)
    if (f1 && g_left_right) {
        g_lr_taken = true;                               // (Right here is the size, not the roster)
        g_size = g_size >= 8 ? 4 : 8;
        while (g_nparty > cur_pl().size - 1) g_nparty--;
        save_settings(); sound(PS_MOVE);
    }
    if (f5 && g_left_right) {                            // (Right here is the rounds, not the roster)
        g_lr_taken = true;
        if (!g_sim_proc) {
            int r = g_sim_rounds + g_left_right;
            g_sim_rounds = r < 1 ? 1 : r > 20 ? 20 : r;
            g_sim_done_at = -1;
            sound(PS_MOVE);
        }
    }
    if (pressed(base + 0)) { sound(PS_SELECT); start_search(e); }
    if (pressed(base + 1)) { g_size = g_size >= 8 ? 4 : 8; while (g_nparty > cur_pl().size - 1) g_nparty--; save_settings(); sound(PS_SELECT); }
    if (pressed(base + 2)) { g_invite = true; g_npool_names = 0; g_invite_scroll = 0; g_focus = 0; sound(PS_SELECT); }
    if (pressed(base + 3)) { g_chal = true; g_chal_check = 0; sound(PS_SELECT); }
    if (pressed(base + 4)) { g_comm = true; g_comm_check = 0; g_comm_tab = 0; g_comm_scroll = 0; g_focus = 0; sound(PS_SELECT); }
    if (pressed(base + 5) && !g_sim_proc) {
        // (a click on the row's < or >: the rounds; anywhere else, or A / Enter: play them)
        float mx = ImGui::GetIO().MousePos.x;
        bool by_mouse = ImGui::IsMouseReleased(0) || ImGui::IsMouseClicked(0);
        if (by_mouse && sim_arrows && mx >= P(880 - 240, 0).x && mx <= P(880 - 190, 0).x) {
            if (g_sim_rounds > 1) g_sim_rounds--;
            sound(PS_MOVE);
        } else if (by_mouse && sim_arrows && mx >= P(880 - 45, 0).x) {
            if (g_sim_rounds < 20) g_sim_rounds++;
            sound(PS_MOVE);
        } else { sim_start(); sound(PS_SELECT); }
    }
}

// the lobby's list (the search, the vote): the player, the friends who joined (Nov 17: there from the start), the bots
// as they arrive (an empty seat searching until then); in a team game each team together, the teams 12 apart
static void lobby_rows(pg_env& e, float t, bool teams, float x1, float y0, const char* empty_text) {
    const hb_roster& r = *e.roster;
    int n = r.n + 1 + g_npeople, filled = 1 + g_npeople;
    for (int i = 0; i < r.n; i++) filled += t >= g_arrive[i];
    std::vector<ros_row> rows;
    int party_team = g_me_team == 1 ? 1 : 0;             // (the team the deal put the player on: MCC's)
    float gap = 0;
    auto me = [&](int team) { rows.push_back({ RK_ME, me_name(), "", team, -1, false, 1, 0, gap }); gap = 0; };
    auto person = [&](int k, int team) {                 // a friend who joined: their own look, no bot's rank
        rows.push_back({ RK_PERSON, g_people_name[k], "", team, -1, false, 1, g_people_id[k], gap });
        gap = 0;
    };
    auto bot = [&](int i) {
        float a = (t - g_arrive[i]) * 3.0f;
        if (a <= 0 && !teams) rows.push_back({ RK_EMPTY, "", "", -1, -1, false, 1, 0, gap });
        else rows.push_back({ RK_BOT, r.bot[i].name, seat_clan(r, i), teams ? r.bot[i].team : -1,
                              r.bot[i].tier, g_pinned[i] != 0, teams ? 1.0f : a, 0, gap });
        gap = 0;
    };
    if (!teams) {
        me(-1);
        for (int k = 0; k < g_npeople; k++) person(k, -1);
        for (int i = 0; i < r.n; i++) if (g_pinned[i]) bot(i);
        // (arrived first, then the empty seats)
        std::vector<int> order;
        for (int i = 0; i < r.n; i++) if (!g_pinned[i]) order.push_back(i);
        std::stable_sort(order.begin(), order.end(), [&](int a, int b) { return g_arrive[a] < g_arrive[b]; });
        for (int i : order) bot(i);
    } else {
        for (int team : { 0, 1 }) {
            if (team == party_team) me(team);
            for (int k = 0; k < g_npeople; k++) if (g_people_team[k] == team) person(k, team);
            for (int i = 0; i < r.n; i++) if (r.bot[i].team == team) bot(i);
            gap = 2 * (ROW_STEP - ROW_H);
        }
    }
    char cnt[16], now[8], max[8];
    sprintf_s(cnt, "%d/%d", filled, n);
    sprintf_s(now, "%d", filled);
    sprintf_s(max, "%d", n);
    // (Nov 19) one name for the list wherever it stands: Reach's own ("IN LOBBY", "SETTING UP MATCH..." before)
    ros_head h = { "IN MATCHMAKING LOBBY", cnt, "In Matchmaking Lobby", cnt, "MATCHMAKING", "LOBBY DETAILS",
                   { me_name(), cur_pl().title, now, max, teams ? "Voting" : "Searching for Players" } };
    roster(e, rows, h, x1, y0, y0 + 44, t, empty_text);
}

static void search_screen(pg_env& e, float t) {
    const hb_roster& r = *e.roster;
    int n = r.n + 1 + g_npeople, filled = 1 + g_npeople;
    for (int i = 0; i < r.n; i++) filled += t >= g_arrive[i];
    bool done = t >= g_search_s;
    {   // (Nov 19) a tick as each player is found (a clan arriving together: one)
        static int was = 0;
        if (t < 0.15f) was = filled;
        else if (filled > was) { if (!done) sound(PS_MOVE); was = filled; }
    }
    if (ros_up()) {                                      // (the roster has the focus: Reach's list and its panel)
        lobby_rows(e, t, false, 1830, 34, "SEARCHING FOR PLAYERS");
        strcpy_s(g_ros_hint, done ? "Players found. Setting up the vote." : "Finding players for your match.");
    } else {
    // (Nov 17) laid out as MCC's own Find Game: the status over the middle, the playlist's card left with its words
    // under it, its games and stats in the middle column, the lobby filling at the right
    header("MULTIPLAYER", g_between ? "POSTGAME LOBBY" : "FIND GAME", 1);
    const char* status = done ? "MATCH FOUND" : g_between ? "PLAYERS LEAVING AND JOINING" : t < 1.3f ? "CHECKING FOR REJOINS"
                                                                                                    : "SEARCHING FOR PLAYERS";
    text(g_fl, 22, 1070, 52, done ? C_GOLD : IM_COL32(214, 218, 222, 255), status, 1);
    char clock[48];
    int secs = (int)(done ? g_search_s : t);
    sprintf_s(clock, "%s  %d:%02d", cur_pl().title, secs / 60, secs % 60);
    text(g_fs, 19, 1070, 82, C_DIM, clock, 1);
    char lbl[48];
    sprintf_s(lbl, done ? "MATCH FOUND: %d/%d" : "SEARCHING FOR PLAYERS: %d/%d", filled, n);
    text(g_fl, 20, 100, 184, C_TEXT, lbl);
    if (!done) {                                         // (the search's spinner, beside its count)
        float cx = 100 + text_w(g_fl, 20, lbl) / g_pg.s + 22, cy = 196;
        for (int k = 0; k < 8; k++) {
            float a = k * 0.785f + t * 4.0f;
            g_dl->AddCircleFilled(P(cx + cosf(a) * 9, cy + sinf(a) * 9), U(2.2f), A(IM_COL32(232, 236, 240, 60 + k * 24)));
        }
    }
    // the playlist's card: its maps turning behind its name, the name low on the picture
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    playlist_pool(cur_pl(), gts, maps);
    panel(100, 222, 800, 500, IM_COL32(26, 29, 32, 235));
    if (!maps.empty()) {
        const pic* p = map_picture(maps[(int)(t / 2.5f) % maps.size()]->key);
        if (p) image(p, 101, 223, 799, 499, 1.0f);
    }
    g_dl->AddRectFilledMultiColor(P(101, 390), P(799, 499), A(IM_COL32(8, 9, 11, 0)), A(IM_COL32(8, 9, 11, 0)),
                                  A(IM_COL32(8, 9, 11, 220)), A(IM_COL32(8, 9, 11, 220)));
    text(g_fl, 34, 120, 446, C_TEXT, cur_pl().title);
    g_dl->AddText(g_fs, U(20), P(102, 512), A(IM_COL32(206, 222, 232, 255)), cur_pl().blurb, nullptr, U(690));
    // the middle column: the games, a line of the playlist's numbers, the stats
    float mx = 850, mw = 470;
    panel(mx, 222, mx + mw, 372);
    text(g_fl, 20, mx + 14, 230, C_BLUE, "GAMES IN THIS PLAYLIST");
    panel(mx + 14, 262, mx + 110, 360, IM_COL32(40, 44, 48, 200));
    crest(mx + 62, 296, 22, IM_COL32(230, 234, 238, 255));
    text(g_fl, 18, mx + 62, 330, C_TEXT, "REACH", 1);
    panel(mx, 380, mx + mw, 424, IM_COL32(24, 27, 30, 190));
    char nums[64];
    sprintf_s(nums, "%d MAPS  /  %d GAME TYPES IN THIS PLAYLIST", (int)maps.size(), (int)gts.size());
    text(g_fl, 19, mx + 14, 390, C_TEXT, nums);
    stats_panel(mx, 432, mw);
    lobby_rows(e, t, false, 1830, 34, "SEARCHING FOR PLAYERS");
    footer(done ? "Players found. Setting up the vote." : "Finding players for your match.", nullptr, true);
    }
    if (g_follow) return;                                // (Nov 18: following: the host moves the stages)
    if (done && t >= g_search_s + 1.4f && take_options()) start_vote(r, false);
    else if (done && t >= g_search_s + 16.0f && !take_options()) {
        strcpy_s(g_error, "MCC's lobby did not accept any of the playlist's games on its maps. Is its Halo: Reach custom game lobby open?");
        g_retry = RETRY_VOTE;
        g_stage = S_ERROR;
    }
}

static void vote_screen(pg_env& e, float t) {
    const hb_roster& r = *e.roster;
    if (!g_nopt && (g_follow || !take_options())) {
        header("MULTIPLAYER", "MATCH FOUND", 2);
        text(g_fl, 26, 100, 200, C_DIM, "Setting up the vote...");
        if (t > 16 && !g_follow) {
            strcpy_s(g_error, "MCC's lobby did not accept any of the playlist's games on its maps.");
            g_retry = RETRY_VOTE;
            g_stage = S_ERROR;
        }
        return;
    }
    if (g_need_votes && !g_follow) { g_need_votes = false; start_vote(r, true); return; }   // (its clock starts now)
    float left = g_vote_s - t;
    if (left <= 0 && g_follow) left = 0;                 // (following: the host counts the votes)
    else if (left <= 0) { tally(r); return; }
    int c[4];
    counts(r, t, c);
    if (ros_up()) {                                      // (the roster has the focus: Reach's list and its panel)
        lobby_rows(e, 1e9f, true, 1830, 34, "");
        sprintf_s(g_ros_hint, "Voting round ends in 0:%02d.", (int)ceilf(left));
        return;
    }
    int base = (int)g_items.size();
    int rows = g_nopt + (g_nota_open ? 1 : 0);
    // the focused option's picture, large, top left
    int fo = g_focus - base;
    if (fo < 0 || fo >= rows) fo = g_vote_me >= 0 ? (g_vote_me == 3 ? g_nopt : g_vote_me) : 0;
    // (Nov 17) as MCC's own vote: the focused option's map over its game's name, MATCH FOUND with its chevron, the
    // options as plain rows (a thin picture, the game over the map, the votes, a box), the round's clock under a line
    panel(96, 90, 820, 400, IM_COL32(26, 29, 32, 235));
    if (fo < g_nopt) {
        const pic* p = map_picture(g_opt[fo].map_key);
        if (p) image(p, 97, 91, 819, 399);
        g_dl->AddRectFilledMultiColor(P(97, 300), P(819, 399), A(IM_COL32(8, 9, 11, 0)), A(IM_COL32(8, 9, 11, 0)),
                                      A(IM_COL32(8, 9, 11, 235)), A(IM_COL32(8, 9, 11, 235)));
        char big[96];
        int k = 0;
        for (const char* s = g_opt[fo].gt_name; *s && k < 95; s++) big[k++] = (char)toupper((unsigned char)*s);
        big[k] = 0;
        text(g_fl, 36, 116, 322, C_TEXT, big);
        text(g_fl, 22, 118, 362, C_BLUE, g_opt[fo].map_name);
    } else {
        text(g_fl, 38, 458, 206, C_TEXT, "NONE OF THE ABOVE", 1);
        text(g_fs, 22, 458, 260, C_DIM, "A majority brings three new choices. Once a lobby.", 1);
    }
    // MATCH FOUND, its chevron
    ImVec2 ch[3] = { P(100, 428), P(122, 450), P(100, 472) };
    g_dl->AddPolyline(ch, 3, A(C_BLUE), 0, U(5));
    text(g_fl, 48, 136, 416, C_TEXT, "MATCH FOUND");
    text(g_fl, 20, 138, 470, IM_COL32(214, 218, 222, 255),
         g_round == 2 ? "VOTE FOR GAME AND MAP (NO VETO)" : "VOTE FOR GAME AND MAP");
    float rh = 62, rs = 66, ry = 512;
    int all = 0, most = 0;                               // (Nov 19: the votes cast, and the most any option has)
    for (int i = 0; i < rows; i++) { int n = c[i < g_nopt ? i : 3]; all += n; most = n > most ? n : most; }
    for (int i = 0; i < rows; i++) {
        float y = ry + i * rs;
        bool f = item(116, y, 820, y + rh);
        bool mine = g_vote_me == (i < g_nopt ? i : 3);
        if (f) {                                         // (Reach's focus band, the chevron before it)
            focus_band(116, y, 820, y + rh);
            ImVec2 fc[3] = { P(98, y + rh * 0.5f - 11), P(108, y + rh * 0.5f), P(98, y + rh * 0.5f + 11) };
            g_dl->AddPolyline(fc, 3, A(C_TEXT), 0, U(2.4f));
        } else g_dl->AddRectFilled(P(116, y), P(820, y + rh), A(IM_COL32(14, 16, 18, 110)));
        // (Nov 19) the option's share of the votes, a bar along the row's foot: yours gold, the others steel; the
        // option ahead brighter
        int n = c[i < g_nopt ? i : 3];
        if (all > 0 && n > 0) {
            float bx1 = 116 + (820 - 116) * (float)n / all;
            ImU32 bc = mine ? IM_COL32(255, 204, 92, 235) : n == most ? IM_COL32(232, 236, 240, 200) : IM_COL32(150, 156, 162, 170);
            g_dl->AddRectFilled(P(116, y + rh - 5), P(bx1, y + rh), A(bc));
        }
        if (i < g_nopt) {
            const pic* p = map_picture(g_opt[i].map_key);
            if (p) image(p, 124, y + 8, 254, y + rh - 8);
            else panel(124, y + 8, 254, y + rh - 8, IM_COL32(40, 44, 48, 240));
            text(g_fl, 23, 270, y + 6, f ? C_TEXT : IM_COL32(222, 226, 230, 255), g_opt[i].gt_name);
            text(g_fl, 18, 271, y + 34, f ? IM_COL32(214, 218, 222, 255) : C_DIM, g_opt[i].map_name);
        } else {
            text(g_fl, 23, 132, y + (rh - 28) * 0.5f, f ? C_TEXT : IM_COL32(222, 226, 230, 255), "NONE OF THE ABOVE");
        }
        char num[8];
        sprintf_s(num, "%d", n);
        text(g_fl, 28, 744, y + (rh - 34) * 0.5f, C_TEXT, num, 2);
        float by = y + rh * 0.5f - 13;
        g_dl->AddRect(P(764, by), P(790, by + 26), A(IM_COL32(220, 232, 240, 230)), 0, 0, 1.6f);
        if (mine) g_dl->AddRectFilled(P(769, by + 5), P(785, by + 21), A(IM_COL32(245, 250, 252, 255)));
        if (pressed(base + i)) {
            int v = i < g_nopt ? i : 3;
            g_vote_me = g_vote_me == v ? -1 : v;
            sound(PS_SELECT);
        }
    }
    float ty = ry + rows * rs + 14;
    g_dl->AddLine(P(116, ty), P(820, ty), A(IM_COL32(130, 136, 142, 150)), U(1));
    text(g_fl, 21, 120, ty + 24, IM_COL32(214, 218, 222, 255), "Voting round ends in:");
    char tm[16];
    int secs = (int)ceilf(left);
    sprintf_s(tm, "0:%02d", secs);
    // (Nov 19) the last five seconds gold, each one a beat: the number swells as it comes and a tick sounds
    float beat = secs <= 5 ? left - floorf(left) : 0, ts = 50 + 10 * beat * beat;
    text(g_fl, ts, 820, ty + 6 - (ts - 50) * 0.6f, secs <= 5 ? C_GOLD : C_TEXT, tm, 2);
    static int ticked = -1;
    if (secs <= 5 && secs != ticked && left < g_vote_s - 0.5f) sound(PS_MOVE);
    ticked = secs;
    lobby_rows(e, 1e9f, true, 1830, 34, "");
    footer("Vote for the game you want to play. Select it again to take your vote back.", "Vote", true);
}

static void result_screen(pg_env& e, float t) {
    const option& o = g_opt[g_winner];
    const pic* p = map_picture(o.map_key);
    // (Nov 18) faded in once, after the vote: the launch (its clock started again) keeps it as it is, no blink
    float a = g_stage == S_LAUNCH || t * 2.0f > 1 ? 1 : t * 2.0f;
    float keep = g_alpha;
    g_alpha *= a;
    panel(360, 220, 1560, 820, IM_COL32(20, 22, 25, 240));
    if (p) image(p, 362, 222, 1558, 742);
    g_dl->AddRectFilledMultiColor(P(362, 560), P(1558, 818), A(IM_COL32(8, 9, 11, 0)), A(IM_COL32(8, 9, 11, 0)),
                                  A(IM_COL32(8, 9, 11, 245)), A(IM_COL32(8, 9, 11, 245)));
    text(g_fl, 26, 400, 600, C_GOLD, g_stage == S_LAUNCH ? "GAME STARTING" : "NEXT GAME");
    text(g_fl, 62, 398, 632, C_TEXT, o.gt_name);
    text(g_fl, 36, 402, 712, C_BLUE, o.map_name);
    const char* sub = g_stage == S_LAUNCH ? "Loading..." : "The lobby voted.";   // (Nov 18: up till the game now)
    text(g_fs, 22, 1520, 770, C_DIM, sub, 2);
    g_alpha = keep;
    (void)e;
}

static void error_screen(pg_env& e, float t) {
    header("MULTIPLAYER", "PROVING GROUNDS", 0);
    panel(460, 360, 1460, 640, IM_COL32(20, 22, 25, 245));
    text(g_fl, 34, 490, 384, C_GOLD, "GAME DIDN'T START");   // (Nov 19: what happened, the reason under it)
    // the reason, wrapped
    ImVec2 p = P(492, 440);
    g_dl->AddText(g_fs, U(24), p, A(C_TEXT), g_error, nullptr, U(940));
    int base = (int)g_items.size();
    bool f0 = item(490, 560, 850, 615);
    row(490, 560, 850, 615, f0, "TRY AGAIN");
    bool f1 = item(870, 560, 1430, 615);
    row(870, 560, 1430, 615, f1, "BACK TO PROVING GROUNDS");
    if (g_left_right && (f0 || f1)) {                    // (Nov 19: side by side, so Left / Right move between them too)
        g_lr_taken = true;
        g_focus = base + (g_left_right > 0 ? 1 : 0);
        if ((g_left_right > 0) != f1) sound(PS_MOVE);
    }
    if (pressed(base)) {
        sound(PS_SELECT);
        if (g_retry == RETRY_VOTE && e.roster->n) {      // (the same lobby: its vote set up again)
            g_round = 1; g_nota_open = true; g_nopt = 0; g_redraws = 0;
            draw_candidates();
            g_need_votes = true;
            g_stage = S_VOTE;
            g_t0 = ImGui::GetTime();
        } else if (g_retry == RETRY_LAUNCH && g_nopt) {  // (the same winner, MCC's Start again)
            pg_lobby_launch(g_opt[g_winner].map, g_opt[g_winner].gametype);
            g_stage = S_LAUNCH;
            g_t0 = ImGui::GetTime();
        } else start_search(e);
    }
    if (pressed(base + 1)) { sound(PS_BACK); to_menu(); }
    footer(nullptr, "Select");
    (void)t;
}

// ------------------------------------------------------------------ the credits a match earned
// (Nov 17, the owner: "add this level up bar after each game showing what earned you your xp. Before the carnage
// report? Or after whichever is cleaner") After: the carnage report is MCC's own screen, so when Proving Grounds' lobby
// comes back from a match it marked, this comes first. The match is counted as it is marked (stats_build), and
// tools/service_record.py writes logs\service_record\last_match.txt: the player's credits before and after, what
// earned them, the rank steps between. The lines come in one by one, then the total, then the bar fills from where the
// rank stood (a promotion on the way: PROMOTED and the new insignia). A, Enter, a click, Esc or B go on to the lobby;
// 6 s after the bar it goes on by itself. No report of this match in 20 s (or none for the player): straight on.
struct credit_line { std::string what, n; int cr; };
struct credit_step { int step; std::string label; int cr; };
static bool g_credit_have;                       // last_match.txt read for g_credit_id
static std::string g_credit_who;                 // the player it shows ("" none in it)
static int g_credit_before, g_credit_after;
static std::vector<credit_line> g_credit_lines;
static std::vector<credit_step> g_credit_steps;
static double g_credit_read, g_promoted_at;
static int g_promoted_to = -1;                   // (the step its PROMOTED sounded for)

static void credit_load() {
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\logs\\service_record\\last_match.txt", g_root);
    FILE* f = nullptr;
    if (_wfopen_s(&f, p, L"rb") || !f) return;
    std::vector<std::vector<std::string>> rows;
    std::string match;
    char line[512];
    std::vector<std::string> c;
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#') continue;
        line[strcspn(line, "\r\n")] = 0;
        split_tabs(line, c);
        if (c[0] == "match" && c.size() > 1) match = c[1];
        else if (c.size() >= 2) rows.push_back(c);
    }
    fclose(f);
    if (match != g_credit_id) return;                     // (not this match's yet: the build is still at it)
    g_credit_have = true;
    g_credit_who.clear();
    for (auto& r : rows)                                  // (the player by MCC's name, else the first person in it)
        if (r[0] == "person" && (g_credit_who.empty() || !_stricmp(r[1].c_str(), me_name()))) g_credit_who = r[1];
    g_credit_lines.clear();
    g_credit_steps.clear();
    for (auto& r : rows) {
        if (r[1] != g_credit_who) continue;
        if (r[0] == "person" && r.size() >= 4) { g_credit_before = atoi(r[2].c_str()); g_credit_after = atoi(r[3].c_str()); }
        else if (r[0] == "line" && r.size() >= 5) g_credit_lines.push_back({ r[2], r[3], atoi(r[4].c_str()) });
        else if (r[0] == "step" && r.size() >= 5) g_credit_steps.push_back({ atoi(r[2].c_str()), r[3], atoi(r[4].c_str()) });
    }
}

static void credits_screen(pg_env& e, float t, double now) {
    (void)e;
    if (!g_credit_have && now - g_credit_read > 0.5) { g_credit_read = now; credit_load(); }
    bool go = false;
    float t_end = 0;                                      // (when Reach's sequence below has run its course)
    if (!g_credit_have) {                                 // (the build still counting)
        reach_panel(560, 400, 1360, 640);
        text(g_fl, 34, 960, 448, C_REACH_TEXT, "COUNTING YOUR CREDITS", 1);
        for (int k = 0; k < 8; k++) {
            float a = k * 0.785f + t * 4.0f;
            g_dl->AddCircleFilled(P(960 + cosf(a) * 14, 540 + sinf(a) * 14), U(3), A(IM_COL32(200, 206, 212, 60 + k * 24)));
        }
        text(g_fs, 21, 960, 584, C_REACH_DIM, "The Service Record is adding the game you just played.", 1);
        if (t > 20) go = true;
    } else if (g_credit_who.empty()) go = true;           // (no one listed played it: nothing to show)
    else {
        // (Nov 19, the owner's frames of Halo: Reach's own screen after a game) Reach's sequence, over its dark slate
        // and fine hex pattern, the player's Spartan standing at the right:
        //   1. each line in turn: its name and "+n" counting up in the middle, a huge faint word behind it ("TIME
        //      SPENT"), then into the list at the bottom left;
        //   2. CREDITS EARNED at the top, the list risen under it, TOTAL counting up;
        //   3. the total going to the player's band along the bottom, its credits counting up (and the owner's
        //      level-up bar under it, Nov 17, filling toward the next rank);
        //   4. a promotion: PROMOTED, the list dimmed, "<RANK> PROMOTED" faint behind, the new insignia large with
        //      its name under it.
        // A (Enter, a click) skips to the end, then goes on; B goes on; 6 s after the end it goes on by itself.
        int L = (int)g_credit_lines.size(), total = g_credit_after - g_credit_before;
        const float T_LINE = 1.0f, t_b = 0.3f + T_LINE * L + 0.2f, t_c = t_b + 1.6f, t_d = t_c + 1.8f;
        int s0 = 0, s1 = 0;
        for (int i = 0; i < (int)g_credit_steps.size(); i++) {
            if (g_credit_steps[i].cr <= g_credit_before) s0 = i;
            if (g_credit_steps[i].cr <= g_credit_after) s1 = i;
        }
        bool promoted = s1 > s0;
        t_end = promoted ? t_d + 2.0f : t_c + 1.8f;     // (Nov 19: the insignia slower, so the end a little later)
        bool promo = promoted && t >= t_d;
        auto clamp01 = [](float v) { return v < 0 ? 0.0f : v > 1 ? 1.0f : v; };
        auto smooth = [&](float v) { v = clamp01(v); return v * v * (3 - 2 * v); };
        auto upper = [](const std::string& s) { std::string o; for (char ch : s) o += (char)toupper((unsigned char)ch); return o; };
        auto faded = [&](float a, auto draw) { float keep = g_alpha; g_alpha *= clamp01(a); draw(); g_alpha = keep; };
        // the ground: Reach's slate over the painting, its fine hex pattern brightest in the middle
        {
            ImVec2 d = ImGui::GetIO().DisplaySize;
            g_dl->AddRectFilled(ImVec2(0, 0), d, IM_COL32(10, 16, 24, 165));   // (the painting kept faint behind)
            const float r = 20, hw = r * 1.5f, hh = r * 1.732f;
            for (int col = 0; col * hw < 1940; col++)
                for (int rw = 0; rw * hh < 1100; rw++) {
                    float cx = col * hw, cy = rw * hh + (col & 1 ? hh * 0.5f : 0);
                    float dx = (cx - 960) / 960, dy = (cy - 540) / 540, a = 15 * (1 - (dx * dx + dy * dy) * 0.8f);
                    if (a < 2) continue;
                    ImU32 lc = A(IM_COL32(200, 220, 240, (int)a));
                    ImVec2 p0 = P(cx + r, cy), p1 = P(cx + r * 0.5f, cy - hh * 0.5f), p2 = P(cx - r * 0.5f, cy - hh * 0.5f),
                           p3 = P(cx - r, cy);
                    g_dl->AddLine(p0, p1, lc); g_dl->AddLine(p1, p2, lc); g_dl->AddLine(p2, p3, lc);
                }
        }
        // the Spartan at the right (a person: Reach's default Spartan, bots_panel.cpp person_figure), turning toward
        // the camera once promoted
        if (e.figure) {
            ImVec2 f0 = P(1140, 100), f1 = P(1780, 900);
            unsigned long long fig = e.figure(g_credit_who.c_str(), false, promo ? 0.12f : 0.42f, (int)(f1.x - f0.x), (int)(f1.y - f0.y));
            if (fig) g_dl->AddImage((ImTextureID)fig, f0, f1, ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
        }
        // a huge faint word or two behind, as Reach's ("TIME" over "SPENT"), fitted to the left of the Spartan
        auto big_words = [&](const std::string& s, float x, float y, float a) {
            std::string w1 = s, w2;
            size_t sp = s.find(' ');
            if (sp != std::string::npos) { w1 = s.substr(0, sp); w2 = s.substr(sp + 1); }
            float sz = 150, wmax = text_w(g_fl, sz, w1.c_str()) / g_pg.s;
            if (!w2.empty()) { float w = text_w(g_fl, sz, w2.c_str()) / g_pg.s + 100; wmax = w > wmax ? w : wmax; }
            if (wmax > 920) sz *= 920 / wmax;
            ImU32 c = A(IM_COL32(214, 224, 236, (int)(30 * clamp01(a))));
            g_dl->AddText(g_fl, U(sz), P(x, y), c, w1.c_str());
            if (!w2.empty()) g_dl->AddText(g_fl, U(sz), P(x + 100, y + sz * 0.78f), c, w2.c_str());
        };
        static const char* WORD[][2] = { {"Game Completed", "TIME SPENT"}, {"Victory", "VICTORY"}, {"Kills", "KILLS"},
                                         {"Assists", "TEAM PLAYER"}, {"Medals", "MEDALS"}, {"Commendations", "COMMENDATIONS"},
                                         {"Challenges", "CHALLENGES"} };
        auto word_of = [&](const std::string& what) {
            for (auto& w : WORD) if (!_stricmp(what.c_str(), w[0])) return std::string(w[1]);
            return upper(what);
        };
        // 1. the line in the middle
        int li = (int)((t - 0.3f) / T_LINE);
        if (t >= 0.3f && t < t_b - 0.2f && li >= 0 && li < L) {
            const credit_line& c = g_credit_lines[li];
            float u = t - (0.3f + li * T_LINE), a = smooth(u / 0.15f) * (1 - smooth((u - 0.8f) / 0.2f));
            big_words(word_of(c.what), 200, 300, a);
            faded(a, [&] {
                float dx = (1 - smooth(u / 0.2f)) * 40;
                text(g_fl, 36, 410 + dx, 440, C_TEXT, upper(c.what).c_str());
                std::string n = "+" + cr_text((int)(c.cr * smooth(u / 0.45f)));
                text(g_fl, 66, 372 + dx, 482, C_TEXT, n.c_str());
                if (!c.n.empty() && c.n != "1") text(g_fs, 22, 412 + dx, 564, C_DIM, ("x" + c.n).c_str());
            });
        }
        // the list: at the bottom left as the lines come, then risen under CREDITS EARNED with the total
        const float RW = 30, top_up = 316, top_down = 836 - RW * L;
        float rise = smooth((t - t_b) / 0.5f), ly = top_down + (top_up - top_down) * rise;
        float dim = promo ? 1 - 0.75f * smooth((t - t_d) / 0.4f) : 1.0f;
        if (t >= t_b) faded(smooth((t - t_b) / 0.3f) * (promo ? 1 : 1), [&] {
            text(g_fl, 50, 192, 252, C_TEXT, promo ? "PROMOTED" : "CREDITS EARNED");
        });
        for (int i = 0; i < L; i++) {
            float a = smooth((t - (0.3f + i * T_LINE + 0.55f)) / 0.25f) * dim;
            if (a <= 0) continue;
            faded(a, [&] {
                const credit_line& c = g_credit_lines[i];
                float y = ly + RW * i;
                text(g_fs, 20, 198, y, IM_COL32(206, 214, 222, 255), upper(c.what).c_str());
                text(g_fs, 20, 640, y, IM_COL32(206, 214, 222, 255), cr_text(c.cr).c_str(), 2);
                g_dl->AddLine(P(198, y + RW - 4), P(640, y + RW - 4), A(IM_COL32(200, 210, 220, 70)), U(1));
            });
        }
        // 2. the total, counting up
        float ty = top_up + RW * L + 6;
        if (t >= t_b + 0.3f) faded(smooth((t - t_b - 0.3f) / 0.2f) * dim, [&] {
            text(g_fl, 34, 194, ty, C_TEXT, "TOTAL:");
            std::string n = "+" + cr_text((int)(total * smooth((t - t_b - 0.4f) / 1.0f)));
            text(g_fl, 34, 640, ty, C_TEXT, n.c_str(), 2);
        });
        if (t >= t_b && !promo) big_words("TOTAL CREDITS", 300, 560, smooth((t - t_b) / 0.3f) * (1 - smooth((t - t_c - 1.6f) / 0.3f)));
        // 3. the band: the total flies to it, its credits count up, the level-up bar fills
        float kc = smooth((t - t_c - 0.5f) / 1.2f);
        int v = g_credit_before + (int)(total * kc);
        int sv = 0;
        for (int i = 0; i < (int)g_credit_steps.size(); i++) if (g_credit_steps[i].cr <= v) sv = i;
        const credit_step* shown = g_credit_steps.empty() ? nullptr : &g_credit_steps[promo ? s1 : s0];
        const credit_step* at = g_credit_steps.empty() ? nullptr : &g_credit_steps[sv];
        const credit_step* nxt = sv + 1 < (int)g_credit_steps.size() ? &g_credit_steps[sv + 1] : nullptr;
        const float by0 = 846, by1 = 922, bx0 = 252, bx1 = 1500;
        int32_t emb[5];
        int np = -1;
        unsigned long long em = g_make && mcc_player_look(emb, &np) ? player_emblem(emb, g_make) : 0;
        if (em) g_dl->AddImage((ImTextureID)em, P(166, by0 + 2), P(240, by0 + 76), ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
        else crest(203, by0 + 38, 30, C_TEXT);
        g_dl->AddRectFilledMultiColor(P(bx0, by0), P(bx1, by1), A(IM_COL32(62, 68, 74, 220)), A(IM_COL32(30, 34, 38, 190)),
                                      A(IM_COL32(30, 34, 38, 190)), A(IM_COL32(62, 68, 74, 220)));
        g_dl->AddLine(P(bx0, by0), P(bx1, by0), A(IM_COL32(220, 226, 232, 120)), U(1));
        if (shown) if (const pic* rp = sr_rank_picture(shown->step)) image_fit(rp, bx0 + 8, by0 + 4, bx0 + 52, by0 + 48);
        text(g_fl, 30, bx0 + 62, by0 + 4, C_TEXT, g_credit_who.c_str());
        text(g_fs, 20, bx0 + 64, by0 + 44, C_DIM, shown ? shown->label.c_str() : "");
        std::string crs = cr_text(v) + " cR";
        text(g_fl, 32, bx1 - 14, by0 + 2, C_TEXT, crs.c_str(), 2);
        text(g_fs, 18, bx1 - 14, by0 + 44, C_DIM, nxt ? ("Next: " + nxt->label + " in " + cr_text(nxt->cr - v) + " cR").c_str() : "MAX RANK", 2);
        {   // (the owner's level-up bar, Nov 17: the rank now, filling toward the next)
            float share = 1;
            if (at && nxt && nxt->cr > at->cr) share = clamp01((float)(v - at->cr) / (float)(nxt->cr - at->cr));
            float fx = bx0 + (bx1 - bx0) * share;
            g_dl->AddRectFilled(P(bx0, by1), P(bx1, by1 + 6), A(IM_COL32(20, 24, 28, 220)));
            g_dl->AddRectFilledMultiColor(P(bx0, by1), P(fx, by1 + 6), A(IM_COL32(70, 140, 200, 255)), A(IM_COL32(150, 210, 250, 255)),
                                          A(IM_COL32(150, 210, 250, 255)), A(IM_COL32(70, 140, 200, 255)));
        }
        if (t >= t_c) {                                   // (the total, on its way to the band, then over it)
            float k = smooth((t - t_c) / 0.5f);
            float x = 640 + (bx1 - 14 - 640) * k, y = ty + (by0 - 52 - ty) * k;
            std::string n = "+" + cr_text(total);
            faded(1 - smooth((t - t_c - 2.4f) / 0.4f), [&] { text(g_fl, 40, x, y, C_TEXT, n.c_str(), 2); });
        }
        // 4. the promotion
        if (promo) {
            if (g_promoted_to != s1) { g_promoted_to = s1; g_promoted_at = now; sound(PS_OPEN); }
            float pa = (float)(now - g_promoted_at);
            std::string rank = upper(g_credit_steps[s1].label);
            big_words(rank + " PROMOTED", 200, 500, smooth(pa / 0.4f));
            // (Nov 19, the owner: "a tad slower ... feels a little too instant") the insignia a beat after PROMOTED
            // (0.35 s), fading in over 0.6 s while it settles from larger over 0.8 s; its name and the ring after it
            float pi = pa - 0.35f, ks = clamp01(pi / 0.8f);
            float k = 1.0f + 0.35f * (1 - ks) * (1 - ks), cx = 760, cy = 520, hs = 92 * k;
            if (pi > 0) {
                faded(smooth(pi / 0.6f), [&] {
                    if (const pic* rp = sr_rank_picture(g_credit_steps[s1].step)) image_fit(rp, cx - hs, cy - hs, cx + hs, cy + hs);
                });
                faded(smooth((pi - 0.4f) / 0.4f), [&] { text(g_fl, 28, cx, cy + 108, C_TEXT, rank.c_str(), 1); });
                float pr = pi - 0.3f;
                if (pr > 0 && pr < 1.0f) g_dl->AddCircle(P(cx, cy), U(90 + 110 * pr), A(IM_COL32(255, 204, 92, (int)(200 * (1 - pr)))), 48, U(3));
            }
        }
        if (t > t_end + 6) go = true;
    }
    bool running = g_credit_have && !g_credit_who.empty() && t < t_end;
    footer(nullptr, running ? "Skip" : "Continue");
    if (ImGui::IsKeyPressed(ImGuiKey_Enter, false) || ImGui::IsKeyPressed(ImGuiKey_Space, false) ||
        ImGui::IsKeyPressed(ImGuiKey_KeypadEnter, false) || ImGui::IsKeyPressed(ImGuiKey_GamepadFaceDown, false) ||
        (ImGui::IsMouseClicked(0) && t > 0.3f && !g_footer_back)) {  // (the footer's Back: pg_back goes on)
        if (running) { g_t0 = now - t_end; sound(PS_MOVE); }   // (Reach's Skip: straight to the end)
        else go = true;
    }
    if (go) {
        sound(PS_SELECT);
        g_credit_id[0] = 0;
        g_stage = S_SEARCH;
        g_t0 = now;
    }
}

// ------------------------------------------------------------------ the link to a joined PC friend (Nov 18)
// (the owner: PC friends who run the mod see Proving Grounds' search, vote and loading, following the host) The host's
// copy puts its screens' state into a pgs_state each frame and pg_link.cpp sends it over MCC's Party text chat to a
// friend whose copy linked (on a change, and every second). A friend's copy that gets one follows: the same screens drawn
// from the host's state, nothing of its own run (no search, no deal, no MCC launch: the host's MCC starts the game), its
// vote sent back and counted in the host's tally. Its own credits screen comes after a match it followed from the
// launch (this PC's own MCC report, its own Service Record). Esc / B put the host's screens away till its next stage; the
// PROVING GROUNDS tile brings them back. No word from the host in 4 s, or the host out of a match's stages: this PC's
// own Proving Grounds again.
#pragma pack(push, 1)
struct pgs_seat { char name[16]; char clan[8]; uint8_t team, tier, party, pad; float arrive, vote_at; int32_t vote; };
struct pgs_person { char name[32]; int8_t team, vote; uint8_t pad[2]; };
struct pgs_opt { char map_name[48], gt_name[48], map_key[40]; int32_t map, gametype, family; };
struct pgs_state {
    char magic[4];                               // PGS_MAGIC
    uint16_t version, bytes;
    uint8_t stage, size, round, nota_open, between, nopt, winner, nseats, npeople, host_team, pad[2];
    int32_t host_vote;
    uint32_t vote_key;
    float t, search_s, vote_s;                   // t: seconds into the stage when made
    char host[32];
    pgs_opt opt[3];
    pgs_seat seat[HB_ROSTER_MAX];
    pgs_person people[PG_PEOPLE];
};
#pragma pack(pop)
static_assert(sizeof(pgs_state) <= PGS_MAX, "pgs_state too big for the link");

// the host's side: a friend's votes in, the state out
static pgs_state g_ls_sent;
static double g_ls_at = -10;
static void link_host(const pg_env& e, double now) {
    static struct { char name[32]; uint32_t key; int v; } votes[PG_PEOPLE];
    static int nv;
    char name[32];
    uint32_t key;
    int v;
    while (pg_link_vote(name, sizeof name, &key, &v)) {
        int k = 0;
        while (k < nv && _stricmp(votes[k].name, name)) k++;
        if (k == nv) { if (nv >= PG_PEOPLE) continue; nv++; }
        if (votes[k].key != key || votes[k].v != v) logf("proving grounds: %s's vote over the link: %d", name, v);
        strcpy_s(votes[k].name, name);
        votes[k].key = key;
        votes[k].v = v;
    }
    for (int i = 0; i < PG_PEOPLE; i++) {
        g_people_vote[i] = -1;
        if (i >= g_npeople || g_stage != S_VOTE) continue;
        for (int k = 0; k < nv; k++)
            if (!_stricmp(votes[k].name, g_people_name[i]) && votes[k].key == g_vote_key) g_people_vote[i] = votes[k].v;
    }
    pgs_state s;
    memset(&s, 0, sizeof s);
    memcpy(s.magic, PGS_MAGIC, 4);
    s.version = 1;
    s.bytes = (uint16_t)sizeof s;
    s.stage = (uint8_t)g_stage;
    s.size = (uint8_t)g_size;
    s.round = (uint8_t)g_round;
    s.nota_open = g_nota_open;
    s.between = g_between;
    s.nopt = (uint8_t)g_nopt;
    s.winner = (uint8_t)g_winner;
    const hb_roster& r = *e.roster;
    s.nseats = (uint8_t)(r.n < HB_ROSTER_MAX ? r.n : HB_ROSTER_MAX);
    for (int i = 0; i < s.nseats; i++) {
        pgs_seat& w = s.seat[i];
        strncpy_s(w.name, r.bot[i].name, _TRUNCATE);
        strncpy_s(w.clan, profile_clan_of(r.bot[i].name), _TRUNCATE);
        w.team = r.bot[i].team;
        w.tier = r.bot[i].tier;
        w.party = g_pinned[i] != 0;
        w.arrive = g_arrive[i];
        w.vote_at = g_vote_at[i];
        w.vote = g_vote_bot[i];
    }
    s.npeople = (uint8_t)(g_npeople < PG_PEOPLE ? g_npeople : PG_PEOPLE);
    for (int k = 0; k < s.npeople; k++) {
        strncpy_s(s.people[k].name, g_people_name[k], _TRUNCATE);
        s.people[k].team = (int8_t)g_people_team[k];
        s.people[k].vote = (int8_t)g_people_vote[k];
    }
    s.host_team = (uint8_t)(g_me_team == 1 ? 1 : 0);
    s.host_vote = g_vote_me;
    s.vote_key = g_vote_key;
    s.search_s = g_search_s;
    s.vote_s = (float)g_vote_s;
    strncpy_s(s.host, me_name(), _TRUNCATE);
    for (int i = 0; i < 3; i++) {
        strncpy_s(s.opt[i].map_name, g_opt[i].map_name, _TRUNCATE);
        strncpy_s(s.opt[i].gt_name, g_opt[i].gt_name, _TRUNCATE);
        strncpy_s(s.opt[i].map_key, g_opt[i].map_key, _TRUNCATE);
        s.opt[i].map = g_opt[i].map;
        s.opt[i].gametype = g_opt[i].gametype;
        s.opt[i].family = g_opt[i].family;
    }
    // (sent on a change, else once a second with the clock: t is left out of the comparison)
    if (memcmp(&s, &g_ls_sent, sizeof s) || now - g_ls_at >= 1.0) {
        g_ls_sent = s;
        g_ls_at = now;
        s.t = (float)(now - g_t0);
        pg_link_set_state(&s, sizeof s);
    }
}

// the friend's side
static pgs_state g_f_last;
static bool g_f_have;
static int g_f_host_stage = -1;
static int g_own_size = 4, g_own_vote_s = 15;    // this PC's own settings, kept while following
static uint32_t g_f_key;
static int g_f_sent_vote = -9;
static double g_f_vote_at;

static void follow_leave(const char* why) {
    if (!g_follow) return;
    g_follow = false;
    g_f_hide = false;
    g_f_have = false;
    g_stage = S_OFF;
    g_nopt = 0;
    g_npeople = 0;
    g_size = g_own_size;
    g_vote_s = g_own_vote_s;
    for (int k = 0; k < PG_PEOPLE; k++) g_people_vote[k] = -1;
    logf("proving grounds: stopped following the host (%s)", why);
}

static void follow_update(double now) {
    pgs_state s;
    uint64_t age = ~0ull;
    uint32_t n = pg_link_state(&s, sizeof s, &age);
    if (n != sizeof s || age > 4000 || s.version != 1 || s.bytes != sizeof s) { follow_leave("no word from the host"); return; }
    int hs = s.stage;
    if (hs != S_SEARCH && hs != S_VOTE && hs != S_RESULT && hs != S_LAUNCH && hs != S_PLAYING && hs != S_CREDITS) {
        follow_leave("the host is out of a match's stages");
        g_f_host_stage = hs;
        return;
    }
    if (!g_follow) {
        if (g_stage != S_OFF && g_stage != S_MENU) return;   // (this PC's own session under way: not now)
        g_follow = true;
        g_f_hide = false;
        g_f_have = false;
        g_own_size = g_size;
        g_own_vote_s = g_vote_s;
        g_f_host_stage = -1;
        g_f_key = 0;
        g_vote_me = -1;
        g_stage = S_OFF;
        logf("proving grounds: following %s's Proving Grounds", s.host);
    }
    if (g_f_have && !memcmp(&s, &g_f_last, sizeof s) && (g_stage == hs || g_stage == S_CREDITS)) return;
    g_f_have = true;
    g_f_last = s;
    bool moved = hs != g_f_host_stage;
    if (moved) {
        if (hs == S_PLAYING && g_f_host_stage == S_LAUNCH) mark_start();   // (this PC's own report of the match)
        if (g_f_host_stage == S_PLAYING && (g_mark_due || g_credit_id[0])) {   // (back from it: this PC's credits first)
            if (g_mark_due) g_mark_back = now;
            g_stage = S_CREDITS;
            g_t0 = now;
            g_credit_have = false;
            g_credit_read = 0;
            g_promoted_to = -1;
        }
        g_f_hide = false;
        g_f_host_stage = hs;
    }
    g_size = s.size >= 8 ? 8 : 4;
    g_vote_s = (int)s.vote_s;
    g_round = s.round;
    g_nota_open = s.nota_open != 0;
    g_between = s.between != 0;
    g_nopt = s.nopt > 3 ? 3 : s.nopt;
    g_winner = s.winner < 3 ? s.winner : 0;
    g_search_s = s.search_s;
    for (int i = 0; i < 3; i++) {
        option& o = g_opt[i];
        strncpy_s(o.map_name, s.opt[i].map_name, _TRUNCATE);
        strncpy_s(o.gt_name, s.opt[i].gt_name, _TRUNCATE);
        strncpy_s(o.map_key, s.opt[i].map_key, _TRUNCATE);
        o.map = s.opt[i].map;
        o.gametype = s.opt[i].gametype;
        o.family = s.opt[i].family;
        o.feel = feel_of(o.map_name);
    }
    g_f_roster.n = s.nseats > HB_ROSTER_MAX ? HB_ROSTER_MAX : s.nseats;
    g_f_roster.teams = 2;
    for (int i = 0; i < g_f_roster.n; i++) {
        const pgs_seat& w = s.seat[i];
        hb_bot& b = g_f_roster.bot[i];
        memcpy(b.name, w.name, sizeof b.name);
        b.name[15] = 0;
        b.team = w.team;
        b.tier = w.tier;
        b.style = HB_STYLE_ANY;
        memcpy(g_f_clan[i], w.clan, sizeof g_f_clan[i]);
        g_f_clan[i][7] = 0;
        g_pinned[i] = w.party;
        g_arrive[i] = w.arrive;
        g_vote_at[i] = w.vote_at;
        g_vote_bot[i] = w.vote;
    }
    // the people as this PC sees them: the host, then the host's others but this PC's player (that one is "me")
    uint64_t ids[PG_PEOPLE];
    char names[PG_PEOPLE][32];
    int teams[PG_PEOPLE];
    int nmcc = mcc_session_people(ids, names, teams, PG_PEOPLE);
    auto id_of = [&](const char* nm) {
        for (int j = 0; j < nmcc; j++) if (!_stricmp(names[j], nm)) return ids[j];
        return ~0ull;                                    // (not in MCC's list here: no look, never this PC's own)
    };
    const char* me = me_name();
    g_npeople = 0;
    g_me_team = s.host_team ? 0 : 1;
    auto add = [&](const char* nm, int team, int vote) {
        if (g_npeople >= PG_PEOPLE) return;
        strncpy_s(g_people_name[g_npeople], nm, _TRUNCATE);
        g_people_id[g_npeople] = id_of(nm);
        g_people_team[g_npeople] = team;
        g_people_vote[g_npeople] = vote;
        g_npeople++;
    };
    add(s.host, s.host_team, s.host_vote);
    for (int k = 0; k < s.npeople && k < PG_PEOPLE; k++) {
        char nm[32];
        memcpy(nm, s.people[k].name, sizeof nm);
        nm[31] = 0;
        if (!_stricmp(nm, me)) { g_me_team = s.people[k].team == 1 ? 1 : 0; continue; }
        add(nm, s.people[k].team, s.people[k].vote);
    }
    if (s.vote_key != g_f_key) { g_f_key = s.vote_key; g_vote_me = -1; g_f_sent_vote = -9; }
    if (g_stage != S_CREDITS) {
        bool stage_now = g_stage != hs;
        g_stage = (stage)hs;
        float t = (float)(now - g_t0);
        if (stage_now || fabsf(t - s.t) > 0.3f) g_t0 = now - s.t;
    }
}

// (the overlay's every frame, Proving Grounds on or not: a host's state may start the following)
void pg_follow_poll() {
    if (!g_loaded) load_settings();
    follow_update(ImGui::GetTime());
}

#ifdef PG_PREVIEW
// (native/pg_preview.cpp only) a screen set up as it would be t seconds into it, for the offscreen pictures
void pg_preview_stage(int which, float t, pg_env& e) {
    if (!g_loaded) load_settings();
    double now = ImGui::GetTime();
    g_invite = false;
    switch (which) {
    case 0: pg_open(); break;
    case 1: pg_open(); g_invite = true; g_npool_names = 0; break;
    case 2: pg_open(); start_search(e); break;
    case 3: pg_open(); start_search(e); take_options(); start_vote(*e.roster, false); g_vote_me = 0; break;
    case 4: pg_open(); start_search(e); take_options(); g_winner = 0; g_stage = S_RESULT; break;
    case 5: pg_open(); strcpy_s(g_error, "MCC did not start the game. Leave Proving Grounds to see any message its lobby shows."); g_stage = S_ERROR; break;
    // (Nov 17) the roster at Reach's place: the menu's party with its header picked; the vote's lobby with a bot picked,
    // then the player (PG_FOCUS: another entry)
    case 6: case 7: case 8: {
        pg_open();
        if (which >= 7) { start_search(e); take_options(); start_vote(*e.roster, false); }
        g_ros_on = true;
        g_ros_k = 1;
        char f[8];
        g_focus = GetEnvironmentVariableA("PG_FOCUS", f, sizeof f) && which == 7 ? atoi(f) : which == 6 ? 0 : which == 7 ? 2 : 1;
        break;
    }
    case 9: case 12: case 13:                            // (Nov 17) the credits screen: a made-up match, a promotion
        pg_open();
        g_stage = S_CREDITS;
        strcpy_s(g_credit_id, "preview");
        g_credit_have = true;
        g_credit_who = me_name();
        g_credit_before = 6200;
        g_credit_after = 9925;
        g_credit_lines = { {"Game Completed", "1", 1000}, {"Victory", "1", 1000}, {"Kills", "12", 1200},
                           {"Assists", "3", 150}, {"Medals", "5", 125}, {"Commendations", "", 0} };
        g_credit_lines.back().cr = 9925 - 6200 - 3475;
        g_credit_steps = { {0, "Recruit", 0}, {1, "Private", 7500}, {2, "Corporal", 10000} };
        g_promoted_to = which == 13 ? 1 : -1;            // (Nov 19: the promotion 2 s on, its insignia settled)
        g_promoted_at = now - 2;
        break;
    case 10: pg_open(); g_chal = true; break;            // (Nov 17) the Challenges page, from the site's last build
    case 11: pg_open(); g_comm = true; g_comm_check = 0; break;   // (Nov 19) the Commendations page, the same
    case 14:                                             // (Nov 18) a friend's copy following the host's vote
        pg_open(); start_search(e); take_options(); start_vote(*e.roster, false); g_vote_me = 1;
        g_t0 = now - t;
        link_host(e, now);                               // (the host's state, as pg_link.cpp sends it; a loopback here)
        g_stage = S_OFF;
        g_vote_me = -1;
        follow_update(now);                              // (this copy as the friend's: following it)
        g_vote_me = 2;                                   // (the friend's own vote, a box of its own)
        printf("friend's copy: following %s, stage %d, %d options, %d bots, %d people, host voted %d\n",
               g_follow ? "yes" : "NO", (int)g_stage, g_nopt, g_f_roster.n, g_npeople, g_npeople ? g_people_vote[0] : -9);
        return;
    }
    g_t0 = now - t;
}
// the playlists as read (proving_grounds.ini's add / remove lines applied)
void pg_preview_lists() {
    load_settings();
    for (int k = 0; k < 2; k++) {
        printf("%s:", g_pl[k].key);
        for (auto& g : g_pl[k].gametypes) printf(" [%s*%d]", g.name.c_str(), g.weight);
        printf("\n  maps:");
        for (auto& m : g_pl[k].maps) printf(" [%s]", m.c_str());
        printf("\n");
        library();
        std::vector<pool_gt> gts;
        std::vector<const pg_entry*> maps;
        playlist_pool(g_pl[k], gts, maps);
        printf("  in the vote:");
        for (auto& g : gts) { char s[64]; gametype_show(g.e->name, s, sizeof s); printf(" [%s #%d kind %d *%d]", s, g.e->id, g.e->kind, g.weight); }
        printf("\n");
    }
}
// each seat's odds on the vote's options (None of the Above last), and 400 rolls each (a check of the weighted dice)
void pg_preview_odds(const hb_roster& r) {
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    playlist_pool(cur_pl(), gts, maps);
    printf("options:");
    for (int i = 0; i < g_nopt; i++) printf("  [%d] %s on %s", i, g_opt[i].gt_name, g_opt[i].map_name);
    printf("  [3] None of the Above\n");
    for (int s = 0; s < r.n; s++) {
        int c[4] = {};
        for (int k = 0; k < 400; k++) { int v = bot_vote(r.bot[s], g_opt, g_nopt, true, maps); c[v >= g_nopt ? 3 : v]++; }
        printf("  %-16s %-10s %-9s  %3d%% %3d%% %3d%%  none %2d%%\n", r.bot[s].name, tier_name(r.bot[s].tier),
               style_name(r.bot[s].style), c[0] / 4, c[1] / 4, c[2] / 4, c[3] / 4);
    }
}
#endif

// ------------------------------------------------------------------ each frame
static bool pg_frame_body(pg_env& e) {
    if (!g_loaded) load_settings();
    g_make = e.make_texture;
    g_sound = e.play_sound;
    g_volume = e.sounds;
    bool was_vis = g_lobby_vis;
    g_lobby_vis = e.lobby_visible;
    double now = ImGui::GetTime();
    float t = (float)(now - g_t0);
    bool changed = false;
    mark_check(now);                                     // (the match just played: on the Service Record)
    // stages that move without the screens: the launch, the match, back in the lobby (following: the host moves them)
    if (g_stage == S_LAUNCH && !g_follow) {
        char why[160];
        int s = pg_lobby_launch_state(why, sizeof why);
        // (Nov 18, the owner: "leave the bot matchmaking screen up as the game starts") MCC's countdown greys its OPTIONS
        // tile, so its lobby read as gone and this screen dropped, MCC's lobby showing till the load. The launch screen now
        // stays till MCC is in the game (overlay.cpp draws it over the countdown); a minute without one, as before
        if (s == -1) { strcpy_s(g_error, why); g_retry = RETRY_LAUNCH; g_stage = S_ERROR; }
        else if (s == 2 && (e.in_game || (t > 60 && !e.lobby_visible))) {
            if (!e.in_game) logf("proving grounds: no game a minute after MCC's countdown started");
            g_stage = S_PLAYING; g_after_due = false; g_lobby_seen_at = 0; mark_start();
        }
        else if (s == 1 && t > 6) {
            strcpy_s(g_error, "MCC's Halo: Reach custom game lobby did not take the game. Leave Proving Grounds to check it is still open.");
            g_retry = RETRY_LAUNCH;
            g_stage = S_ERROR;
        }
    }
    if (g_stage == S_PLAYING && !g_follow) {
        if (!e.lobby_visible) g_lobby_seen_at = 0;
        else {
            if (!g_lobby_seen_at) g_lobby_seen_at = now;
            if (g_after_due || now - g_lobby_seen_at > 4.0) {   // (back from the match: the lobby between games)
                if (!g_after_due) {                              // (no match end heard, a game quit: the same lobby)
                    bool all[HB_ROSTER_MAX];
                    for (int i = 0; i < HB_ROSTER_MAX; i++) all[i] = true;
                    g_between = true; g_search_s = 1.0f; schedule(*e.roster, 1.0f, all);
                }
                if (g_mark_due) g_mark_back = now;               // (its report: 30 s more to come, mark_check)
                g_nopt = 0;                                      // (the vote drawn now, from MCC's lists as they are back)
                g_redraws = 0;
                draw_candidates();
                // (Nov 17) a match marked for the Service Record: what it earned first (credits_screen), then the lobby
                g_stage = g_credit_id[0] ? S_CREDITS : S_SEARCH;
                g_credit_have = false;
                g_credit_read = 0;
                g_promoted_to = -1;
                g_t0 = now;
                t = 0;
                changed = g_after_due;
                g_after_due = false;
            }
        }
    }
    if (!pg_visible()) return changed;
    if (!was_vis) g_mouse_was = ImGui::GetIO().MousePos;
    g_dl = ImGui::GetForegroundDrawList();
    g_fl = e.f_label; g_fs = e.f_small;
    g_pg = mcc_content(e.W, e.H);
    g_alpha = 1;
    g_items.clear();
    if (g_focus_after >= 0) { g_focus = g_focus_after; g_focus_after = -1; }
    int pressed_before = g_pressed;
    (void)pressed_before;
    g_pad_in = e.pad;
    // (Nov 19) Reach's own painting for the screen when this PC has it (bg_picture): Proving Grounds' menu, matchmaking
    // (Find Game, the vote, the next game), the credits after a game
    int bgk = g_stage == S_CREDITS ? BG_POST
            : (g_stage == S_SEARCH || g_stage == S_VOTE || g_stage == S_RESULT || g_stage == S_LAUNCH) ? BG_MATCH : BG_MENU;
    if (const pic* painted = bg_picture(bgk)) painted_background((float)now, painted);
    else {  // the ground's art: the vote's options and the winner, else the playlist's maps in turn (faded between)
        const pic* art = nullptr;
        float art_a = 0.30f;                             // (Nov 19: 0.16 before, under a heavier wash)
        if ((g_stage == S_RESULT || g_stage == S_LAUNCH) && g_nopt) art = map_picture(g_opt[g_winner].map_key);
        else if (g_stage == S_VOTE && g_nopt) art = map_picture(g_opt[g_vote_me >= 0 && g_vote_me < g_nopt ? g_vote_me : 0].map_key);
        else if (g_stage != S_ERROR) {
            std::vector<pool_gt> gts;
            std::vector<const pg_entry*> maps;
            playlist_pool(cur_pl(), gts, maps);
            if (!maps.empty()) {
                const double period = 12.0;
                double ph = fmod(now, period);
                art = map_picture(maps[(size_t)(now / period) % maps.size()]->key);
                float edge = (float)(ph < period - ph ? ph : period - ph);       // (a second's fade at each change)
                art_a *= edge > 1 ? 1 : edge;
            }
        }
        background((float)now, art, art_a);
    }
    if (!g_follow && (g_stage == S_SEARCH || g_stage == S_VOTE || (g_stage == S_RESULT && t < 2.5f)))   // (Nov 17: before
        redeal_if_people_changed(*e.roster, e.difficulty, t);                                           // the launch)
    switch (g_stage) {
    case S_MENU:
        if (g_chal) { challenges_screen(e, t); break; }  // (Nov 17: the Challenges page)
        if (g_comm) { comm_screen(e, t); break; }        // (Nov 19: the Commendations page)
        g_inert = g_invite;
        menu_screen(e, t);
        g_inert = false;
        if (g_invite) invite_list(e);
        break;
    case S_SEARCH: search_screen(e, t); break;
    case S_VOTE: vote_screen(e, t); break;
    case S_RESULT:
        result_screen(e, t);
        if (t > 3.0f && !g_follow) {
            const option& o = g_opt[g_winner];
            g_last_map = o.map; g_last_gt = o.gametype;
            pg_lobby_launch(o.map, o.gametype);
            g_stage = S_LAUNCH;
            g_launch_t = now;
            g_t0 = now;
        }
        break;
    case S_LAUNCH: result_screen(e, t); break;
    case S_ERROR: error_screen(e, t); break;
    case S_CREDITS: credits_screen(e, t, now); break;
    default: break;
    }
    // (Nov 17) the roster, as Reach's party list: into it with Right or a click on it, out with Left, Esc, B or a click
    // away from it and its panel; the list slides between MCC's place and Reach's in 0.22 s
    bool ros_here = (g_stage == S_MENU && !g_invite && !g_chal && !g_comm) || g_stage == S_SEARCH || g_stage == S_VOTE, ros_out = false;
    if (!ros_here) { g_ros_on = false; g_ros_k = 0; }
    else if (!g_ros_on) {
        // (Nov 19) RB (the footer's Players prompt) as well as Right: Right is GAME SIZE's and the rounds' on those rows
        bool rb = ImGui::IsKeyPressed(ImGuiKey_GamepadR1, false) || g_footer_players;
        if (g_ros_click >= 0 || (g_left_right == 1 && !g_lr_taken) || rb) {
            g_ros_keep = g_focus;
            g_focus = g_ros_click >= 0 ? g_ros_click : 0;
            g_ros_on = true;
            sound(PS_SELECT);
        }
    } else if (g_left_right == -1 || ImGui::IsKeyPressed(ImGuiKey_GamepadL1, false)) ros_out = true;
    else if (ImGui::IsMouseClicked(0)) {
        ImVec2 m = ImGui::GetIO().MousePos, l0 = P(g_ros_x0, g_ros_y0), l1 = P(g_ros_x1, g_ros_y1),
               p0 = P(RP0, RPY0), p1 = P(RP1, RPY1), f0 = P(0, 940);
        bool in_list = m.x >= l0.x && m.x <= l1.x && m.y >= l0.y && m.y <= l1.y;
        bool in_panel = m.x >= p0.x && m.x <= p1.x && m.y >= p0.y && m.y <= p1.y;
        if (!in_list && !in_panel && m.y < f0.y) ros_out = true;
    }
    if (ros_here && ros_up()) footer(g_ros_hint[0] ? g_ros_hint : nullptr);
    g_ros_hint[0] = 0;
    g_ros_click = -1;
    g_lr_taken = false;
    if (g_footer_back || ImGui::IsKeyPressed(ImGuiKey_Escape, false) || ImGui::IsKeyPressed(ImGuiKey_GamepadFaceRight, false)) {
        if (g_ros_on) ros_out = true;
        else { sound(PS_BACK); pg_back(); }
    }
    if (ros_out) { g_ros_on = false; g_focus = g_ros_keep; sound(PS_BACK); }
    if (ros_here) {
        g_ros_k += (g_ros_on ? 1.0f : -1.0f) * ImGui::GetIO().DeltaTime / 0.22f;
        g_ros_k = g_ros_k < 0 ? 0 : g_ros_k > 1 ? 1 : g_ros_k;
    }
    g_footer_back = false;
    g_footer_players = false;
    g_pressed = -1;
    frame_keys();
    static int last_n = -1;
    static uint32_t last_sig;
    uint32_t sig = 2166136261u;
    for (int i = 0; i < e.roster->n; i++) {
        for (const char* c = e.roster->bot[i].name; *c; c++) sig = (sig ^ (uint8_t)*c) * 16777619u;
        sig = (sig ^ e.roster->bot[i].team) * 16777619u;
    }
    if (sig != last_sig || e.roster->n != last_n) { last_sig = sig; last_n = e.roster->n; changed = true; }
    return changed;
}

bool pg_frame(pg_env& e) {
    double now = ImGui::GetTime();
    follow_update(now);
    if (g_follow) {                                      // (Nov 18) the host's screens, from its state (pg_link.cpp)
        pg_env fe = e;
        fe.roster = &g_f_roster;                         // (this PC's own bot list is never touched)
        if (g_stage == S_VOTE && (g_vote_me != g_f_sent_vote || now - g_f_vote_at > 2.0)) {   // (again every 2 s)
            pg_link_send_vote(g_f_key, g_vote_me, me_name());
            g_f_sent_vote = g_vote_me;
            g_f_vote_at = now;
        }
        pg_frame_body(fe);
        return false;
    }
    bool changed = pg_frame_body(e);
    if (g_stage != S_OFF) link_host(e, now);             // (a linked friend's copy follows these screens)
    return changed;
}
