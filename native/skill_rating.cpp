// skill_rating.cpp (custom, Nov 23): Project Noble's skill ratings (skill_rating.h has the owner's rules).
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <map>
#include "skill_rating.h"
#include "bots_panel.h"

// the owner's bases (Nov 23): Easy 400, Normal 600, Heroic 800, Tactician 950, Legendary and Blind 1300, Mythic 1600,
// Demon 1650, Noble 1700; the ranges about halfway to the next difficulty, Demon's and Noble's his own. Scaling is not
// in his matchmaking: Legendary's
static const sr_range RANGE[HB_TIERS] = {
    { 400, 300, 500 },      // Easy
    { 600, 500, 700 },      // Normal
    { 800, 700, 900 },      // Heroic
    { 1300, 1150, 1450 },   // Legendary
    { 1300, 1150, 1450 },   // Scaling
    { 1650, 1550, 1800 },   // Demon
    { 1300, 1150, 1450 },   // Blind
    { 950, 850, 1100 },     // Tactician
    { 1600, 1500, 1700 },   // Mythic
    { 1700, 1600, 1800 },   // Noble
};
sr_range sr_tier_range(int tier) { return RANGE[tier >= 0 && tier < HB_TIERS ? tier : 3]; }

struct sr_entry { bool bot = false; int tier = -1, team = -1, ffa = -1; std::string name; };
static std::map<std::string, sr_entry> g_tab;           // by name, lower case
static std::map<std::string, int> g_seen;               // the difficulty each bot was last seated at
static std::map<std::string, int> g_shown;              // the newest match: ratings after it
static std::string g_counted, g_shown_match;
static wchar_t g_path[MAX_PATH];
static FILETIME g_stamp;
static bool g_ro;

void sr_readonly(bool on) { g_ro = on; }

static std::string key(const char* name) {
    std::string k = name ? name : "";
    for (char& c : k) c = (char)tolower((unsigned char)c);
    return k;
}
static unsigned fnv(const std::string& s, unsigned h = 2166136261u) {
    for (unsigned char c : s) { h ^= c; h *= 16777619u; }
    return h;
}

static void split(char* line, std::vector<std::string>& c) {
    c.clear();
    char* s = line;
    for (;;) {
        char* t = strchr(s, '\t');
        if (!t) { c.push_back(s); break; }
        *t = 0;
        c.push_back(s);
        s = t + 1;
    }
}

static bool stamp_of(FILETIME* ft) {
    WIN32_FILE_ATTRIBUTE_DATA a;
    if (!GetFileAttributesExW(g_path, GetFileExInfoStandard, &a)) return false;
    *ft = a.ftLastWriteTime;
    return true;
}

static void load() {
    g_tab.clear(); g_shown.clear(); g_counted.clear(); g_shown_match.clear();
    FILE* f = nullptr;
    if (_wfopen_s(&f, g_path, L"rb") || !f) return;
    char line[512];
    std::vector<std::string> c;
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#') continue;
        line[strcspn(line, "\r\n")] = 0;
        split(line, c);
        if (c[0] == "match" && c.size() >= 2) g_counted = c[1];
        else if (c[0] == "bot" && c.size() >= 5) {
            sr_entry& e = g_tab[key(c[1].c_str())];
            e.bot = true; e.name = c[1]; e.tier = atoi(c[2].c_str()); e.team = atoi(c[3].c_str()); e.ffa = atoi(c[4].c_str());
        } else if (c[0] == "person" && c.size() >= 4) {
            sr_entry& e = g_tab[key(c[1].c_str())];
            e.bot = false; e.name = c[1]; e.team = atoi(c[2].c_str()); e.ffa = atoi(c[3].c_str());
        } else if (c[0] == "shown" && c.size() >= 3) {
            if (c[1].empty()) g_shown_match = c[2];
            else g_shown[key(c[1].c_str())] = atoi(c[2].c_str());
        }
    }
    fclose(f);
}

bool sr_open(const wchar_t* dir) {
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%spg_ratings.txt", dir);
    FILETIME ft{};
    bool have = false;
    if (_wcsicmp(p, g_path)) {
        wcscpy_s(g_path, p);
        have = stamp_of(&ft);
        g_stamp = ft;
        load();
        return have;
    }
    have = stamp_of(&ft);
    if (have && CompareFileTime(&ft, &g_stamp)) { g_stamp = ft; load(); }
    return have;
}

static void save() {
    if (g_ro || !g_path[0]) return;
    wchar_t tmp[MAX_PATH];
    swprintf_s(tmp, L"%s.tmp", g_path);
    FILE* f = nullptr;
    if (_wfopen_s(&f, tmp, L"w") || !f) return;
    fprintf(f, "# Project Noble: skill ratings (native/skill_rating.cpp); the game keeps this file, do not edit while it runs.\n"
               "# match id (the last counted); bot name difficulty team-rating ffa-rating; person name team-rating\n"
               "# ffa-rating (-1: not rated yet); shown name rating (the newest match's, for its RATING page)\n");
    fprintf(f, "match\t%s\n", g_counted.c_str());
    for (auto& kv : g_tab) {
        const sr_entry& e = kv.second;
        if (e.bot) fprintf(f, "bot\t%s\t%d\t%d\t%d\n", e.name.c_str(), e.tier, e.team, e.ffa);
        else fprintf(f, "person\t%s\t%d\t%d\n", e.name.c_str(), e.team, e.ffa);
    }
    fprintf(f, "shown\t\t%s\n", g_shown_match.c_str());
    for (auto& kv : g_shown) fprintf(f, "shown\t%s\t%d\n", kv.first.c_str(), kv.second);
    fclose(f);
    MoveFileExW(tmp, g_path, MOVEFILE_REPLACE_EXISTING);
    stamp_of(&g_stamp);
}

int sr_bot_start(const char* name, int tier, bool ffa) {
    sr_range r = sr_tier_range(tier);
    unsigned h = fnv(key(name), fnv(ffa ? "ffa" : "team"));
    h = fnv(std::to_string(tier), h);
    return r.lo + (int)(h % (unsigned)(r.hi - r.lo + 1));
}

int sr_bot(const char* name, int tier, bool ffa) {
    auto it = g_tab.find(key(name));
    if (it != g_tab.end() && it->second.bot && it->second.tier == tier) {
        int v = ffa ? it->second.ffa : it->second.team;
        if (v >= 0) return v;
    }
    return sr_bot_start(name, tier, ffa);
}

int sr_person(const char* name, bool ffa) {
    auto it = g_tab.find(key(name));
    if (it != g_tab.end() && !it->second.bot) {
        int v = ffa ? it->second.ffa : it->second.team;
        if (v >= 0) return v;
    }
    return SR_PERSON_START;
}

void sr_note_tier(const char* name, int tier) { if (name && name[0]) g_seen[key(name)] = tier; }

int sr_tier_of(const char* name) {
    auto s = g_seen.find(key(name));
    if (s != g_seen.end()) return s->second;
    auto it = g_tab.find(key(name));
    return it != g_tab.end() && it->second.bot ? it->second.tier : -1;
}

void sr_reset_person(const char* name) {
    sr_entry& e = g_tab[key(name)];
    e.bot = false; e.name = name; e.team = SR_PERSON_START; e.ffa = SR_PERSON_START;
    save();
}

const char* sr_counted() { return g_counted.c_str(); }
void sr_set_counted(const char* id) { g_counted = id ? id : ""; save(); }
int sr_shown(const char* name) { auto it = g_shown.find(key(name)); return it == g_shown.end() ? -1 : it->second; }
const char* sr_shown_match() { return g_shown_match.c_str(); }

// a player's random draw for this match: the same every time the match is worked out
static int draw(const char* id, const std::string& name, int lo, int hi) {
    return lo + (int)(fnv(key(name.c_str()), fnv(id ? id : "")) % (unsigned)(hi - lo + 1));
}

bool sr_rate(const char* id, bool teams, const char* gametype, std::vector<sr_player>& pl) {
    if (!id || !id[0] || pl.empty() || g_counted == id) return false;
    std::string gt = key(gametype);
    if (gt.find("firefight") != std::string::npos) return false;
    for (sr_player& p : pl) {
        if (p.bot && p.tier < 0) p.tier = sr_tier_of(p.name.c_str());
        if (p.bot && p.tier < 0) p.tier = 3;                 // (a bot never seated here: Legendary)
        p.before = p.bot ? sr_bot(p.name.c_str(), p.tier, !teams) : sr_person(p.name.c_str(), !teams);
        p.after = p.before;
    }
    double kills = 0;
    for (const sr_player& p : pl) kills += p.kills;
    kills /= pl.size();
    if (teams) {
        int best = 1 << 30, worst = -1;
        for (const sr_player& p : pl) { best = p.place < best ? p.place : best; worst = p.place > worst ? p.place : worst; }
        bool draw_game = best == worst;
        for (sr_player& p : pl) {
            double own = 0, opp = 0;
            int no = 0, nop = 0;
            for (const sr_player& q : pl) (q.team == p.team ? (own += q.before, no++) : (opp += q.before, nop++));
            own = no ? own / no : 0;
            opp = nop ? opp / nop : own;
            bool won = p.place == best && !draw_game;
            if (!p.bot && !p.completed) { p.after = p.before + 15; continue; }   // (a person who quit: tougher teams)
            if (draw_game && p.completed) continue;
            if (p.bot) {
                if (won && p.completed) p.after += own - opp > SR_GAP ? 9 : 19;
                else p.after -= opp - own > SR_GAP ? 9 : 19;
            } else if (won) {
                p.after += own - opp > SR_GAP ? draw(id, p.name, 30, 35) : draw(id, p.name, 35, 40);
                if (p.kills > kills) { int b = (int)((p.kills - kills) / 3); p.after += b > 3 ? 3 : b; }
            } else p.after -= opp - own > SR_GAP ? 10 : 15;
        }
    } else {
        for (sr_player& p : pl) {
            if (!p.bot && !p.completed) { p.after = p.before + 15; continue; }
            int place = p.completed ? p.place : 99;
            p.after += place == 1 ? 40 : place == 2 ? 30 : place == 3 ? 20 : -15;
        }
    }
    g_shown.clear();
    g_shown_match = id;
    for (sr_player& p : pl) {
        sr_entry& e = g_tab[key(p.name.c_str())];
        if (p.bot) {
            sr_range r = sr_tier_range(p.tier);
            p.after = p.after < r.lo ? r.lo : p.after > r.hi ? r.hi : p.after;
            if (!e.bot || e.tier != p.tier) { e.team = -1; e.ffa = -1; }   // (a new difficulty: its new range from scratch)
            e.bot = true; e.tier = p.tier;
        } else {
            p.after = p.after < SR_PERSON_FLOOR ? SR_PERSON_FLOOR : p.after;
            if (e.bot) { e.team = -1; e.ffa = -1; }
            e.bot = false;
        }
        e.name = p.name;
        (teams ? e.team : e.ffa) = p.after;
        g_shown[key(p.name.c_str())] = p.after;
    }
    g_counted = id;
    save();
    return true;
}
