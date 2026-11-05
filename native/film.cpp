// film.cpp: bot matches in Theater.
//
// A saved film replays the match from its start: the game rebuilds the starting state and re-runs every recorded tick.
// Bots are not in it: botcore makes them outside the game's recorded player list (the film's header names only the
// the player, tools/film_info.py) and drives them by writing their input into each tick's actions in the players-update
// hook. So in Theater the simulation goes another way than the match did and MCC drops the film; and the brain, started
// by the menus giving way to a "game", added bots into the film itself (haloreach.dll+0x86EB1C).
//
// So botcore records, for every live match, what it gives the game each tick: the commands it runs (adding a bot, a
// loadout) and the bots' input as the hook used it (bot slots -> player index, hb_action), plus the decoded-button
// table. Keyed by the game's own tick count and filed by the match's game options (the same bytes in the match and in
// its film; the random seed differs between matches). In a film of a recorded match, the same commands run and the
// same input goes in at the same ticks, so the bots come back and do what they did. The brain never runs in a film
// (botcore.cpp: g_playback).
//
// Files: %LOCALAPPDATA%\ProjectProvingGrounds\films\<key>.hbf (every copy of the mod; a film is replayed from
// <project>\logs\films too, where each copy kept its own before), the newest KEEP kept. Record: u32 tick, u16 type, u16 length, bytes.
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "shared.h"
#include "film.h"

extern hb_shared* g_shm;
void logf(const char* fmt, ...);
void film_dir(wchar_t* out);                  // botcore.cpp: %LOCALAPPDATA%\ProjectProvingGrounds\films, every copy's
void film_old_dir(wchar_t* out);              // botcore.cpp: <project>\logs\films, this copy's before (read only)

enum : uint16_t { R_CMD = 1, R_BOTS = 2, R_BUTTONS = 3, R_SPAWN = 4 };
static const int KEEP = 30;

#pragma pack(push, 1)
struct rec_hdr { uint32_t tick; uint16_t type, len; };
struct cmd_rec {                              // the shared memory a command reads
    uint32_t cmd; int32_t arg; wchar_t name[16];
    uint32_t look_game, look_off; uint8_t look[64], look_mask[64]; wchar_t clan[8];
};
struct spawn_rec { int32_t index; float at[4]; };   // a bot moved to its spawn (reach.cpp hr_spawn_moves)
#pragma pack(pop)

static FILE* g_out;                           // recording
static FILE* g_in;                            // replaying
static int g_mode;                            // 0 none, 1 recording, 2 replaying, 3 film with no recording
static uint64_t g_key;
static uint32_t g_last_tick;
static film_frame g_frame, g_rec_last;        // this tick's input; the last one written
static bool g_rec_any;
static uint32_t g_btn_seq;
static rec_hdr g_next;                        // replay: the record read ahead
static uint8_t g_buf[sizeof(film_frame) + sizeof(cmd_rec) + 64];
static bool g_have;

static void close_all() {
    if (g_out) { fclose(g_out); g_out = nullptr; }
    if (g_in) { fclose(g_in); g_in = nullptr; }
    g_mode = 0; g_have = false; g_rec_any = false;
}

static void path_of(uint64_t key, wchar_t* out, bool old = false) {
    wchar_t dir[MAX_PATH]; if (old) film_old_dir(dir); else film_dir(dir);
    swprintf_s(out, MAX_PATH, L"%s\\%016llx.hbf", dir, (unsigned long long)key);
}

// the newest KEEP recordings stay
static void prune() {
    wchar_t dir[MAX_PATH], pat[MAX_PATH]; film_dir(dir);
    swprintf_s(pat, L"%s\\*.hbf", dir);
    struct ent { FILETIME t; wchar_t name[64]; } all[256]; int n = 0;
    WIN32_FIND_DATAW fd; HANDLE h = FindFirstFileW(pat, &fd);
    if (h == INVALID_HANDLE_VALUE) return;
    do { if (n < 256) { all[n].t = fd.ftLastWriteTime; wcsncpy_s(all[n].name, fd.cFileName, _TRUNCATE); n++; } }
    while (FindNextFileW(h, &fd));
    FindClose(h);
    for (int i = 0; i < n; i++) {                     // older than KEEP others: deleted
        int newer = 0;
        for (int k = 0; k < n; k++) newer += CompareFileTime(&all[k].t, &all[i].t) > 0;
        if (newer >= KEEP) { wchar_t p[MAX_PATH]; swprintf_s(p, L"%s\\%s", dir, all[i].name); DeleteFileW(p); }
    }
}

static void put(uint32_t tick, uint16_t type, const void* data, uint16_t len) {
    rec_hdr h{ tick, type, len };
    fwrite(&h, sizeof h, 1, g_out);
    fwrite(data, len, 1, g_out);
}

static bool read_next() {
    g_have = g_in && fread(&g_next, sizeof g_next, 1, g_in) == 1 && g_next.len <= sizeof g_buf
             && fread(g_buf, g_next.len, 1, g_in) == 1;
    return g_have;
}

static void apply(bool commands) {
    if (g_next.type == R_BOTS && g_next.len == sizeof(film_frame)) {
        memcpy(&g_frame, g_buf, sizeof g_frame);
        memcpy(g_shm->bot_player_index, g_frame.index, sizeof g_frame.index);   // (other readers: the spawn hook)
        memcpy(g_shm->actions, g_frame.act, sizeof g_frame.act);
    } else if (g_next.type == R_BUTTONS && g_next.len == sizeof g_shm->btn_map) {
        memcpy(g_shm->btn_map, g_buf, sizeof g_shm->btn_map);
    } else if (g_next.type == R_CMD && g_next.len == sizeof(cmd_rec) && commands) {
        const cmd_rec& c = *(const cmd_rec*)g_buf;
        g_shm->cmd = c.cmd; g_shm->cmd_arg = c.arg;
        memcpy(g_shm->cmd_name, c.name, sizeof c.name);
        g_shm->cmd_look_game = c.look_game; g_shm->cmd_look_off = c.look_off;
        memcpy(g_shm->cmd_look, c.look, sizeof c.look); memcpy(g_shm->cmd_look_mask, c.look_mask, sizeof c.look_mask);
        memcpy(g_shm->cmd_clan, c.clan, sizeof c.clan);
        g_shm->cmd_seq = g_shm->cmd_done_seq + 1;     // the hook's command runner takes it this tick
    } else if (g_next.type == R_SPAWN && g_next.len == sizeof(spawn_rec) && commands) {
        const spawn_rec& s = *(const spawn_rec*)g_buf;
        if (s.index >= 0 && s.index < HB_MAX_PLAYERS) {
            memcpy(g_shm->spawn_at[s.index], s.at, sizeof s.at);
            g_shm->spawn_seq[s.index] = g_shm->spawn_done[s.index] + 1;   // the move check takes it this tick
        }
    }
}

void film_spawn(uint32_t tick, int index, const float at[4]) {
    if (g_mode != 1 || !g_out) return;
    spawn_rec s{ index, { at[0], at[1], at[2], at[3] } };
    __try { put(tick, R_SPAWN, &s, sizeof s); } __except (EXCEPTION_EXECUTE_HANDLER) {}
}

const film_frame* film_tick(uint64_t key, uint32_t tick, bool playback, uint32_t cmd_bit) {
    if (!g_shm) return nullptr;
    __try {
        if (!playback) {
            if (g_mode != 1 || key != g_key || tick < g_last_tick) {     // a new match: a new recording
                close_all();
                prune();
                wchar_t p[MAX_PATH]; path_of(key, p);
                if (_wfopen_s(&g_out, p, L"wb") == 0 && g_out) { g_mode = 1; logf("film: recording %ls", p); }
                g_key = key; g_btn_seq = ~0u;
            }
            memcpy(g_frame.index, g_shm->bot_player_index, sizeof g_frame.index);   // frozen for this tick
            memcpy(g_frame.act, g_shm->actions, sizeof g_frame.act);
            if (g_out) {
                if (g_shm->cmd_seq != g_shm->cmd_done_seq && (g_shm->cmd_arg & cmd_bit)) {
                    cmd_rec c{};
                    c.cmd = g_shm->cmd; c.arg = g_shm->cmd_arg;
                    memcpy(c.name, g_shm->cmd_name, sizeof c.name);
                    c.look_game = g_shm->cmd_look_game; c.look_off = g_shm->cmd_look_off;
                    memcpy(c.look, g_shm->cmd_look, sizeof c.look); memcpy(c.look_mask, g_shm->cmd_look_mask, sizeof c.look_mask);
                    memcpy(c.clan, g_shm->cmd_clan, sizeof c.clan);
                    put(tick, R_CMD, &c, sizeof c);
                }
                if (g_shm->btn_map_seq != g_btn_seq) {
                    g_btn_seq = g_shm->btn_map_seq;
                    put(tick, R_BUTTONS, g_shm->btn_map, sizeof g_shm->btn_map);
                }
                if (!g_rec_any || memcmp(&g_frame, &g_rec_last, sizeof g_frame)) {
                    put(tick, R_BOTS, &g_frame, sizeof g_frame);
                    g_rec_last = g_frame; g_rec_any = true;
                }
            }
            g_last_tick = tick;
            return &g_frame;
        }
        // a film
        if (g_mode < 2 || key != g_key) {
            close_all();
            g_key = key;
            wchar_t p[MAX_PATH]; path_of(key, p);
            if (_wfopen_s(&g_in, p, L"rb") != 0) {    // (a match recorded before the shared folder)
                g_in = nullptr; path_of(key, p, true);
                if (_wfopen_s(&g_in, p, L"rb") != 0) g_in = nullptr;
            }
            if (g_in) { g_mode = 2; logf("film: replaying the bots from %ls", p); }
            else { g_mode = 3; logf("film: no recording for this film (%016llx): no bots in it", (unsigned long long)key); }
            for (int i = 0; i < HB_MAX_PLAYERS; i++) g_frame.index[i] = -1;
            memset(g_frame.act, 0, sizeof g_frame.act);
            g_last_tick = 0;
            read_next();
        }
        if (g_mode == 3) { for (int i = 0; i < HB_MAX_PLAYERS; i++) g_frame.index[i] = -1; return &g_frame; }
        if (tick < g_last_tick) {                     // rewound: from the start, the state at this tick (no commands
            fseek(g_in, 0, SEEK_SET);                 // again: the bots made before it are in the rewound game)
            for (int i = 0; i < HB_MAX_PLAYERS; i++) g_frame.index[i] = -1;
            while (read_next() && g_next.tick < tick) apply(false);
        }
        while (g_have && g_next.tick <= tick) { apply(true); read_next(); }
        g_last_tick = tick;
        return &g_frame;
    } __except (EXCEPTION_EXECUTE_HANDLER) { close_all(); return nullptr; }
}

void film_end() { close_all(); }
