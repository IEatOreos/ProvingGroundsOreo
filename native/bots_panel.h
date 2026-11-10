// bots_panel.h: the BOTS panel and the roster it edits: the exact bots that join the next match, by
// name, team, difficulty and play style. Saved in botcore.ini (bot=team,tier,style,name lines);
// tools/play.py adds them when the match loads and tools/live_bots.py gives each its difficulty and
// style. Pure Dear ImGui: botcore's overlay draws it over the lobby, native/panel_preview.cpp draws it
// offscreen for checks.
#pragma once
#include <stdint.h>
#include <stdio.h>

struct ImFont;

#define HB_ROSTER_MAX 15        // the game holds 16 players: you and 15 bots
#define HB_TEAMS_MAX 8
#define HB_STYLE_ANY 7          // the brain deals a play style
#define HB_TIER_SCALING 4       // hb_bot.tier: Scaling (brain/scaling.py)
#define HB_TIER_DEMON 5         // hb_bot.tier: Demon (custom: fixed Legendary under its own name)
#define HB_TIER_BLIND 6         // hb_bot.tier: Blind (custom, Nov 10: Legendary, its aim and hands drawn per bot)
#define HB_TIERS 7

struct hb_bot {
    char name[16];              // up to 15 characters, the game's name field
    uint8_t team;               // 0 red, 1 blue, 2.. (Halo 3 / Reach colour order)
    uint8_t tier;               // 0 Easy (novice) .. 3 Legendary (top), 4 Scaling (brain/scaling.py), 5 Demon (custom:
                                // fixed Legendary under its own name, brain/profiles.py)
    uint8_t style;              // 0..6 brain/profiles.py PERSONALITIES order, 7 any
};

struct hb_roster {
    int n;
    int teams;                  // team cards shown (2..8); bots keep their team when cards are hidden
    hb_bot bot[HB_ROSTER_MAX];
};

struct bots_panel_env {
    hb_roster* roster;
    uint32_t* enabled;          // bots join at all
    uint32_t* difficulty;       // the last "for everyone" choice, 0..3, 4 mixed, 5 scaling, 6 demon, 7 blind
    uint32_t* lidar_mode;       // mapping bots instead of fighters
    uint32_t* lidar_players;    // players in all in LiDAR mode (2..16)
    uint32_t* collector;        // records the player each match for the Observer (tools/collector.py); may be null
    int title;                  // the lobby's game: 1 CE, 2 H2, 3 H3, 5 Reach, 6 H2A, 7 H4
    float scale;                // px per 1080p unit: MCC's fitted menu page (ui_layout.h mcc_content)
    ImFont *f_title, *f_head, *f_body, *f_small;
    bool* open;
    // makes a texture from RGBA pixels for the profile view's pictures (game logos, bot looks); null: no pictures
    unsigned long long (*make_texture)(int w, int h, const unsigned char* rgba);   // (an ImTextureID: the SRV)
    // draws a character model (native/model_view.h mv_render on the caller's device) for the profile view's 3D bot;
    // and whether a model has a region's permutation (mv_has). null: no 3D view
    unsigned long long (*render_model)(const wchar_t* path, const struct mv_pick* picks, int n, const struct mv_colors& c,
                                       float yaw, int w, int h);
    bool (*model_has)(const wchar_t* path, const char* region, const char* perm);
    void (*model_zoom)(float zoom);      // mv_set_zoom: how close the profile view frames the bot (null: whole figure)
    void (*model_head)(float out[3]);    // mv_head: where the last model draw put the head (the armor effects; null: none)
    void (*model_headroom)(float share); // mv_set_headroom: room above the head for an armor effect (null: none)
    uint32_t* sounds;           // the panel's sound volume, 0-100 (0: off; botcore.ini sounds=); may be null
    void (*play_sound)(int kind, uint32_t volume);   // plays a PS_ sound (overlay.cpp: from memory); null: none
    bool pad;                   // the last input was the pad: prompts name its buttons (B, not Esc)
    uint32_t* scale_games;      // Scaling difficulty: how many of his last games it averages (1-20); may be null
};

// the panel's sounds (bots_panel.cpp panel_sounds): the focus moved (keys or pad), a control pressed, back (Esc, the
// pad's B), the panel opened, a save that failed
enum { PS_MOVE, PS_SELECT, PS_BACK, PS_OPEN, PS_ERROR };
int panel_sound_wav(int kind, uint32_t volume, char* out, int cap);   // the WAV in out; its bytes (0: none)

// Draws the panel (call between ImGui::NewFrame and Render); true when the settings changed.
bool bots_panel(bots_panel_env& e);
// The Python that runs the brain and the tools, as a command: an install's own (<root>\python\python.exe, quoted),
// else "python" from PATH (a developer's copy)
void hb_python(const wchar_t* root, wchar_t* out, size_t cap);

// roster operations (also used by botcore.cpp's settings migration and the preview's self-test)
int  roster_max_teams(int title);              // Halo: CE team games have two teams
void roster_fill(hb_roster& r, int teams, int per_team, int tier, int style, uint32_t seed);
bool roster_add(hb_roster& r, int team, int tier, int style, uint32_t seed);
void roster_remove(hb_roster& r, int i);
void roster_balance(hb_roster& r);
void roster_shuffle(hb_roster& r, uint32_t seed);
void roster_rename_all(hb_roster& r, uint32_t seed);
void roster_name(hb_roster& r, int i, uint32_t seed);   // a fresh name, unique in the roster: a free one of the
                                                         // install's 15 bots first (bots_panel_profiles), else made up
void bots_panel_profiles(const wchar_t* path);           // load native\bin\bot_profiles.ini (brain/looks.py)
// The Settings tab's re-roll: this install's bots drawn again, 15 new names, look seeds and clan tags, with how they
// suit up: experience 0 Original (only what each game shipped with, docs/research/13) or 1 Modern (everything MCC
// adds), and how many wear armor effects: 0 none, 1 rare, 2 common, 3 frequent. Writes bot_profiles.ini (lines
// experience=, effects=, bot=<name>,<seed>,<clan>) and loads it; the brain (brain/looks.py) dresses the bots from it.
bool profiles_reroll(const wchar_t* path, int experience, int effects, uint32_t seed, int species = 1,
                     int elite_share = -1);   // species: 0 Spartans only, 1 mixed (elite_share %, -1 each game's own), 2 Elites only
int  profiles_count();
const char* profile_name(int i);
const char* profile_clan(int i);                        // "" for a bot in no clan
const char* profile_clan_of(const char* name);          // the clan tag of the profile of that name, or ""
int  profile_over_get(int i, const char* key);          // a look set by hand in the bot editor ("h3.primary"), or -1
void profile_over_set(int i, const char* key, int v);   // set it (v >= 0) or clear it (v < 0); not saved
bool profiles_save();                                   // write the profiles as held (names, clans, hand-set looks)
int  profiles_experience();                             // 0 Original, 1 Modern
int  profiles_effects();                                // 0 none, 1 rare, 2 common, 3 frequent
int  profiles_species();                                // 0 Spartans only, 1 mixed, 2 Elites only (the re-roll)
int  profiles_elite_share();                            // mixed: the percent rolled Elite, -1 each game's own mix
int  roster_on_team(const hb_roster& r, int team);
int  roster_mixed_tier(int k);                          // "Mixed": Heroic, Normal, Legendary, Easy in turn
int  roster_difficulty_tier(uint32_t difficulty, int k); // a "for everyone" difficulty as the k-th bot's tier
const char* team_name(int team);
const char* tier_name(int tier);
const char* tier_key(int tier);                         // novice average strong top (brain/profiles.py), scaling, demon
const char* style_name(int style);                      // rusher .. sniper, any (brain/profiles.py)

// botcore.ini lines: "roster=1", "teams=N", "bot=<team>,<tier key>,<style key>,<name>" (tools/botctl.py reads
// them too); parse returns true when the line was a roster line. Firefight's own list (3 bots, your team) is written
// with the prefix "ff": "ffroster=1", "ffbot=..." (no teams line)
bool roster_parse_line(const char* line, hb_roster& r);
void roster_write(FILE* f, const hb_roster& r, const char* prefix = "");

// The bug report over a match: with MCC's pause menu up, a "Report bot bug" button; it (or F9) opens the report window.
// overlay.cpp saves what was typed (logs/bug_reports/<time>/report.json); the brain adds the match recording.
struct bug_report_env {
    float scale;                // px per 1080p unit: MCC's fitted menu page (ui_layout.h mcc_content)
    ImFont* font;
    bool show_button;           // the pause menu is up
    bool* open;                 // the report window
    char* text; int text_n;     // the description being typed
    bool hovered;               // out: the mouse is on the button or the window (its clicks are ours)
    float bb_w, bb_h;           // MCC's back buffer (its menus are laid out on it; 0 = the window's size)
};
// Draws the button and the window (between ImGui::NewFrame and Render); true when Save report was pressed.
bool bug_report_ui(bug_report_env& e);
