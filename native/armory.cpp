// armory.cpp (custom, Nov 19): Project Noble's Halo: Reach Armory, its data (armory.h).
//
// The owner's design: "make it to where everything on MCC is actually already unlocked, but we make it to where you
// can't equip it until you purchase it through our menu ... when we go to equip an item that we have not purchased or
// locked, it just doesn't do anything. So it's not changing the options inside the MCC menu."
//
// Files (none of them written by MCC):
//  - <repo>\logs\service_record\armory.txt: written with the Service Record site (tools/service_record.py
//    write_game_armory): the player's rank step and credits earned, every item (Reach's own prices and rank gates,
//    maps/_looks/reach_prices.json, the gate as the site's rank step) and the customization table's pieces;
//  - <bin>\service_record\armory_ledger.txt: what was bought, appended here (buy<TAB>name<TAB>id<TAB>cost<TAB>time).
//    The rank stays the credits earned; what is spent comes off them for buying only, as in Reach;
//  - <bin>\service_record\armory_equipped.txt: what is worn, slot<TAB>id (a slot not listed wears its default);
//  - <bin>\service_record\my_look_reach.txt: the player's own configuration as they joined (reach.cpp), for the
//    figure's colours and body;
//  - <bin>\reach_menus.ini [armory] wear=0 turns the match side off (MCC's own choices worn again).
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <map>
#include "armory.h"

const char* const ARM_SLOTS[ARM_NSLOTS] = { "helmet", "left_shoulder", "right_shoulder", "chest", "wrist", "utility",
                                            "visor", "knees", "armor_effect", "elite_armor" };

namespace {
struct me_row { std::string name, rank; int step = 0, earned = 0; };
struct rec { std::string region, perm; int mask = 0; };
struct state {
    bool have = false;
    std::vector<arm_item> items;
    std::vector<me_row> me;
    std::map<int, std::vector<rec>> pieces;     // (offset << 8 | value) -> its records
    std::vector<rec> base[3];                    // spartan, female, elite
    std::vector<int> bytes[2];                   // spartan, elite
    std::vector<std::pair<std::string, int>> bought;   // (name, item) from the ledger
    std::map<std::string, int> spent;            // lower-case name -> credits
    int equipped[ARM_NSLOTS];                    // item index per slot, -1 its default
    bool wear = true;
    bool look_have = false;
    uint8_t look[0xA0] = {};
    char look_name[64] = {};
};
state g;
SRWLOCK g_lock = SRWLOCK_INIT;
int g_try = -1;
ULONGLONG g_checked;
ULONGLONG g_stamp[5];
wchar_t g_root[MAX_PATH], g_bin[MAX_PATH];

void find_dirs() {
    if (g_bin[0]) return;
    HMODULE me = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            (LPCWSTR)&find_dirs, &me))
        return;
    DWORD n = GetModuleFileNameW(me, g_bin, MAX_PATH);
    wchar_t* slash = n && n < MAX_PATH ? wcsrchr(g_bin, L'\\') : nullptr;
    if (!slash) { g_bin[0] = 0; return; }
    *slash = 0;
    wcscpy_s(g_root, g_bin);
    if (wchar_t* s = wcsstr(g_root, L"\\native\\bin")) *s = 0;
}

enum { F_ARMORY, F_LEDGER, F_EQUIPPED, F_LOOK, F_INI };
void path_of(int which, wchar_t* p) {
    switch (which) {
    case F_ARMORY: swprintf_s(p, MAX_PATH, L"%s\\logs\\service_record\\armory.txt", g_root); break;
    case F_LEDGER: swprintf_s(p, MAX_PATH, L"%s\\service_record\\armory_ledger.txt", g_bin); break;
    case F_EQUIPPED: swprintf_s(p, MAX_PATH, L"%s\\service_record\\armory_equipped.txt", g_bin); break;
    case F_LOOK: swprintf_s(p, MAX_PATH, L"%s\\service_record\\my_look_reach.txt", g_bin); break;
    default: swprintf_s(p, MAX_PATH, L"%s\\reach_menus.ini", g_bin); break;
    }
}
ULONGLONG stamp_of(const wchar_t* p) {
    WIN32_FILE_ATTRIBUTE_DATA fa;
    if (!GetFileAttributesExW(p, GetFileExInfoStandard, &fa)) return 0;
    return ((ULONGLONG)fa.ftLastWriteTime.dwHighDateTime << 32 | fa.ftLastWriteTime.dwLowDateTime) ^ fa.nFileSizeLow;
}

void split(char* line, std::vector<std::string>& out) {
    out.clear();
    line[strcspn(line, "\r\n")] = 0;
    char* s = line;
    for (;;) {
        char* t = strchr(s, '\t');
        if (!t) { out.push_back(s); return; }
        *t = 0;
        out.push_back(s);
        s = t + 1;
    }
}
template <class F> void each_line(const wchar_t* p, F f) {
    FILE* fp = nullptr;
    if (_wfopen_s(&fp, p, L"rb") || !fp) return;
    char line[1024];
    std::vector<std::string> c;
    while (fgets(line, sizeof line, fp)) {
        if (line[0] == '#') continue;
        split(line, c);
        if (!c.empty() && !c[0].empty()) f(c);
    }
    fclose(fp);
}
std::string lower(std::string s) { for (auto& ch : s) ch = (char)tolower((unsigned char)ch); return s; }
int slot_of(const std::string& s) {
    for (int k = 0; k < ARM_NSLOTS; k++) if (s == ARM_SLOTS[k]) return k;
    return -1;
}
int find_in(const state& s, const std::string& id) {
    for (size_t i = 0; i < s.items.size(); i++) if (s.items[i].id == id) return (int)i;
    return -1;
}

void read_armory(state& s) {
    wchar_t p[MAX_PATH];
    path_of(F_ARMORY, p);
    s.items.clear(); s.me.clear(); s.pieces.clear();
    for (auto& b : s.base) b.clear();
    for (auto& b : s.bytes) b.clear();
    std::vector<std::string> needs_text;
    each_line(p, [&](const std::vector<std::string>& c) {
        if (c[0] == "me" && c.size() >= 5) {
            s.me.push_back({ c[1], c[3], atoi(c[2].c_str()), atoi(c[4].c_str()) });
        } else if (c[0] == "item" && c.size() >= 12) {
            arm_item it;
            it.id = c[1]; it.slot = c[2]; it.family = atoi(c[3].c_str()); it.variant = atoi(c[4].c_str());
            it.name = c[5]; it.cost = atoi(c[6].c_str()); it.gate_step = atoi(c[7].c_str()); it.gate = c[8];
            it.def = strchr(c[10].c_str(), 'd') != nullptr;
            it.autobuy = strchr(c[10].c_str(), 'a') != nullptr;
            it.ours = strchr(c[10].c_str(), 'o') != nullptr;
            std::string w = c[11];
            size_t at = 0;
            while (at < w.size() && it.nw < 2) {
                size_t comma = w.find(',', at);
                std::string one = w.substr(at, comma == std::string::npos ? std::string::npos : comma - at);
                size_t eq = one.find('=');
                if (eq != std::string::npos) {
                    it.off[it.nw] = atoi(one.c_str()); it.val[it.nw] = atoi(one.c_str() + eq + 1); it.nw++;
                }
                if (comma == std::string::npos) break;
                at = comma + 1;
            }
            if (slot_of(it.slot) >= 0 && it.nw) { s.items.push_back(it); needs_text.push_back(c[9]); }
        } else if (c[0] == "piece" && c.size() >= 6) {
            s.pieces[atoi(c[1].c_str()) << 8 | (atoi(c[2].c_str()) & 0xFF)].push_back({ c[3], c[4], atoi(c[5].c_str()) });
        } else if (c[0] == "base" && c.size() >= 5) {
            int b = c[1] == "female" ? 1 : c[1] == "elite" ? 2 : 0;
            s.base[b].push_back({ c[2], c[3], atoi(c[4].c_str()) });
        } else if (c[0] == "bytes" && c.size() >= 3) {
            auto& v = s.bytes[c[1] == "elite" ? 1 : 0];
            for (const char* q = c[2].c_str(); *q; ) {
                v.push_back(atoi(q));
                const char* comma = strchr(q, ',');
                if (!comma) break;
                q = comma + 1;
            }
        }
    });
    for (size_t i = 0; i < s.items.size(); i++) {      // (the ids it needs, as indexes)
        const std::string& t = needs_text[i];
        if (t == "-") continue;
        size_t at = 0;
        for (;;) {
            size_t comma = t.find(',', at);
            int j = find_in(s, t.substr(at, comma == std::string::npos ? std::string::npos : comma - at));
            if (j >= 0) s.items[i].needs.push_back(j);
            if (comma == std::string::npos) break;
            at = comma + 1;
        }
    }
    s.have = !s.items.empty();
}

void read_ledger(state& s) {
    wchar_t p[MAX_PATH];
    path_of(F_LEDGER, p);
    s.bought.clear(); s.spent.clear();
    each_line(p, [&](const std::vector<std::string>& c) {
        if (c[0] != "buy" || c.size() < 4) return;
        s.spent[lower(c[1])] += atoi(c[3].c_str());
        int i = find_in(s, c[2]);
        if (i >= 0) s.bought.push_back({ lower(c[1]), i });
    });
}

void read_equipped(state& s) {
    wchar_t p[MAX_PATH];
    path_of(F_EQUIPPED, p);
    for (int& e : s.equipped) e = -1;
    each_line(p, [&](const std::vector<std::string>& c) {
        if (c.size() < 2) return;
        int k = slot_of(c[0]), i = find_in(s, c[1]);
        if (k >= 0 && i >= 0 && s.items[i].slot == c[0]) s.equipped[k] = i;
    });
}

void read_look(state& s) {
    wchar_t p[MAX_PATH];
    path_of(F_LOOK, p);
    s.look_have = false;
    each_line(p, [&](const std::vector<std::string>& c) {
        if (c.size() < 2) return;
        if (c[0] == "name") strcpy_s(s.look_name, c[1].c_str());
        if (c[0] == "config" && c[1].size() >= 2 * 0xA0) {
            for (int i = 0; i < 0xA0; i++) {
                char hx[3] = { c[1][2 * i], c[1][2 * i + 1], 0 };
                s.look[i] = (uint8_t)strtoul(hx, nullptr, 16);
            }
            s.look_have = true;
        }
    });
}

const me_row* me_of(const state& s, const char* name) {
    for (const me_row& m : s.me) if (name && !_stricmp(m.name.c_str(), name)) return &m;
    return nullptr;
}
int my_step(const state& s, const char* name) { const me_row* m = me_of(s, name); return m ? m->step : 0; }

bool owned(const state& s, int i, const char* name, int depth = 0) {
    const arm_item& it = s.items[i];
    if (it.def) return true;
    std::string who = lower(name ? name : "");
    for (auto& b : s.bought) if (b.second == i && b.first == who) return true;
    if (it.autobuy && depth < 4 && my_step(s, name) >= it.gate_step) {   // (bought by itself once its rank and the
        for (int n : it.needs) if (!owned(s, n, name, depth + 1)) return false;   // items it needs are there)
        return true;
    }
    return false;
}
int default_of(const state& s, int k) {
    for (size_t i = 0; i < s.items.size(); i++) if (s.items[i].def && s.items[i].slot == ARM_SLOTS[k]) return (int)i;
    return -1;
}
int worn_in(const state& s, int k) { return s.equipped[k] >= 0 ? s.equipped[k] : default_of(s, k); }

void write_equipped(const state& s) {
    wchar_t p[MAX_PATH], tmp[MAX_PATH], dir[MAX_PATH];
    swprintf_s(dir, L"%s\\service_record", g_bin);
    CreateDirectoryW(dir, nullptr);
    path_of(F_EQUIPPED, p);
    swprintf_s(tmp, L"%s.tmp", p);
    FILE* f = nullptr;
    if (_wfopen_s(&f, tmp, L"wb") || !f) return;
    fprintf(f, "# Project Noble's Armory (native/armory.cpp): what the player wears in Halo: Reach matches; slot<TAB>id\n");
    for (int k = 0; k < ARM_NSLOTS; k++)
        if (s.equipped[k] >= 0) fprintf(f, "%s\t%s\n", ARM_SLOTS[k], s.items[s.equipped[k]].id.c_str());
    fclose(f);
    MoveFileExW(tmp, p, MOVEFILE_REPLACE_EXISTING);
}
}  // namespace

bool armory_load() {
    find_dirs();
    ULONGLONG now = GetTickCount64();
    AcquireSRWLockExclusive(&g_lock);
    if (g_checked && now - g_checked < 1500) { bool h = g.have; ReleaseSRWLockExclusive(&g_lock); return h; }
    g_checked = now;
    wchar_t p[MAX_PATH];
    ULONGLONG st[5];
    for (int k = 0; k < 5; k++) { path_of(k, p); st[k] = stamp_of(p); }
    if (st[F_ARMORY] != g_stamp[F_ARMORY]) { read_armory(g); g_stamp[F_LEDGER] = g_stamp[F_EQUIPPED] = ~0ULL; }
    if (st[F_LEDGER] != g_stamp[F_LEDGER]) read_ledger(g);
    if (st[F_EQUIPPED] != g_stamp[F_EQUIPPED]) read_equipped(g);
    if (st[F_LOOK] != g_stamp[F_LOOK]) read_look(g);
    if (st[F_INI] != g_stamp[F_INI]) { path_of(F_INI, p); g.wear = GetPrivateProfileIntW(L"armory", L"wear", 1, p) != 0; }
    memcpy(g_stamp, st, sizeof st);
    bool h = g.have;
    ReleaseSRWLockExclusive(&g_lock);
    return h;
}

// (the UI's thread only reads the item list it loads itself: the game thread never changes it, only reads)
const std::vector<arm_item>& armory_items() { return g.items; }
int armory_find(const char* id) { return find_in(g, id ? id : ""); }

bool armory_me(const char* name, int* step, std::string* rank, int* earned) {
    const me_row* m = me_of(g, name);
    if (step) *step = m ? m->step : 0;
    if (rank) *rank = m ? m->rank : "";
    if (earned) *earned = m ? m->earned : 0;
    return m != nullptr;
}

int armory_balance(const char* name) {
    const me_row* m = me_of(g, name);
    auto s = g.spent.find(lower(name ? name : ""));
    return (m ? m->earned : 0) - (s != g.spent.end() ? s->second : 0);
}

int armory_state(int i, const char* name) {
    if (i < 0 || i >= (int)g.items.size()) return ARM_LOCKED_RANK;
    const arm_item& it = g.items[i];
    int k = slot_of(it.slot);
    if (k >= 0 && worn_in(g, k) == i) return ARM_EQUIPPED;
    if (owned(g, i, name)) return ARM_OWNED;
    if (my_step(g, name) < it.gate_step) return ARM_LOCKED_RANK;
    for (int n : it.needs) if (!owned(g, n, name)) return ARM_LOCKED_NEEDS;
    return ARM_FOR_SALE;
}

bool armory_buy(int i, const char* name) {
    if (armory_state(i, name) != ARM_FOR_SALE) return false;
    const arm_item& it = g.items[i];
    if (it.cost > armory_balance(name)) return false;
    wchar_t p[MAX_PATH], dir[MAX_PATH];
    swprintf_s(dir, L"%s\\service_record", g_bin);
    CreateDirectoryW(dir, nullptr);
    path_of(F_LEDGER, p);
    bool fresh = GetFileAttributesW(p) == INVALID_FILE_ATTRIBUTES;
    FILE* f = nullptr;
    if (_wfopen_s(&f, p, L"ab") || !f) return false;
    if (fresh)
        fprintf(f, "# Project Noble's Armory (native/armory.cpp): what was bought with the Service Record's credits;\n"
                   "# buy<TAB>name<TAB>item id<TAB>credits<TAB>unix time. The rank stays the credits earned.\n");
    fprintf(f, "buy\t%s\t%s\t%d\t%lld\n", name, it.id.c_str(), it.cost, (long long)time(nullptr));
    fclose(f);
    AcquireSRWLockExclusive(&g_lock);
    g.spent[lower(name)] += it.cost;
    g.bought.push_back({ lower(name), i });
    path_of(F_LEDGER, p);
    g_stamp[F_LEDGER] = stamp_of(p);
    ReleaseSRWLockExclusive(&g_lock);
    return true;
}

bool armory_equip(int i, const char* name) {
    int st = armory_state(i, name);
    if (st == ARM_EQUIPPED) return true;
    if (st != ARM_OWNED) return false;                 // (locked or not bought: nothing happens)
    int k = slot_of(g.items[i].slot);
    if (k < 0) return false;
    AcquireSRWLockExclusive(&g_lock);
    g.equipped[k] = g.items[i].def ? -1 : i;
    write_equipped(g);
    wchar_t p[MAX_PATH];
    path_of(F_EQUIPPED, p);
    g_stamp[F_EQUIPPED] = stamp_of(p);
    ReleaseSRWLockExclusive(&g_lock);
    return true;
}

int armory_worn(const char* slot) {
    int k = slot_of(slot ? slot : "");
    return k >= 0 && g.have ? worn_in(g, k) : -1;
}

void armory_try(int i) { g_try = i; }
int armory_trying() { return g_try >= 0 && g_try < (int)g.items.size() ? g_try : -1; }

bool armory_dressed(uint8_t cfg[0xA0], char* name, int cap) {
    if (!g.look_have) return false;
    memcpy(cfg, g.look, 0xA0);
    if (name && cap > 0) strcpy_s(name, cap, g.look_name);
    if (!g.have) return true;
    for (int k = 0; k < ARM_NSLOTS; k++) {
        int i = worn_in(g, k);
        if (g_try >= 0 && g_try < (int)g.items.size() && g.items[g_try].slot == ARM_SLOTS[k]) i = g_try;
        if (i < 0) continue;
        for (int w = 0; w < g.items[i].nw; w++)
            if (g.items[i].off[w] < 0xA0) cfg[g.items[i].off[w]] = (uint8_t)g.items[i].val[w];
    }
    return true;
}

int armory_pieces(const uint8_t* cfg, int body, const char** region, const char** perm, int cap) {
    int bit = body == 2 ? 4 : body == 1 ? 2 : 1;
    std::vector<const rec*> recs;
    for (const rec& r : g.base[body == 2 ? 2 : 0]) recs.push_back(&r);
    if (body == 1) for (const rec& r : g.base[1]) recs.push_back(&r);
    for (int off : g.bytes[body == 2 ? 1 : 0]) {
        if (off < 0 || off >= 0xA0) continue;
        auto it = g.pieces.find(off << 8 | cfg[off]);
        if (it != g.pieces.end()) for (const rec& r : it->second) recs.push_back(&r);
    }
    int n = 0;
    for (const rec* r : recs) {                        // (a region's last record wins; the other body's left out)
        if (r->mask && !(r->mask & bit)) continue;
        int at = -1;
        for (int k = 0; k < n; k++) if (!strcmp(region[k], r->region.c_str())) at = k;
        if (at < 0) { if (n >= cap) continue; at = n++; region[at] = r->region.c_str(); }
        perm[at] = r->perm.c_str();
    }
    return n;
}

// (the game's thread: it loads the files only while nothing is loaded yet, so the menus' thread, which reloads what
// changed, never has the list rebuilt under it; what the menus change it reads under the lock)
int armory_wear(uint8_t* off, uint8_t* val, int cap) {
    if (!g.have) armory_load();
    AcquireSRWLockShared(&g_lock);
    int n = 0;
    if (g.have && g.wear)
        for (int k = 0; k < ARM_NSLOTS; k++) {
            int i = worn_in(g, k);
            if (i < 0) continue;
            for (int w = 0; w < g.items[i].nw && n < cap; w++)
                if (g.items[i].off[w] < 0xA0) { off[n] = (uint8_t)g.items[i].off[w]; val[n] = (uint8_t)g.items[i].val[w]; n++; }
        }
    ReleaseSRWLockShared(&g_lock);
    return n;
}
