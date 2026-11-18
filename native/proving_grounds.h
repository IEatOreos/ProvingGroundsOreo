// proving_grounds.h: Proving Grounds (custom, Nov 16). The owner: an offline copy of Halo: Reach's Social Games over
// MCC's own Halo: Reach custom game lobby: pick 4v4 (Arena) or 8v8 (Big Team Battle), a short search that fills the
// lobby with Bot Matchmaking's bots (clans together), teams dealt fair every match, then Reach's vote (three games and
// None of the Above) where every bot votes by its own taste, and the winner launched by MCC's own lobby. Invited bots
// stay in your party, always on your team.
//  - pg_lobby.cpp: MCC's side (its variant library, its pairing check, its Start), on MCC's own UI thread;
//  - proving_grounds.cpp: the screens, the playlists, the bots' votes, the lobby between matches.
#pragma once
#include <stdint.h>

struct ImFont;
struct hb_roster;

// ---- pg_lobby.cpp
struct pg_entry {
    int id;                     // MCC's library id
    int kind;                   // 1 built in, 2 shipped, 3 the player's (4, the session's copies, are left out)
    int category;               // a gametype's: 0 CTF, 1 Slayer, 2 Oddball, 3 King, 4 Juggernaut, 5 Infection, 7 Race,
                                // 15 Territories, 16 Assault, 21 Stockpile, 22 Headhunter, 23 Invasion, 24 Insane
    int teams;                  // a gametype's: 1 a team game, 0 free for all, -1 not known
    char name[64];              // MCC's name ("$HReach_MPMap_R-7_Title" for a shipped map: pg_map_name)
    char key[40];               // its picture's name ("HReachMP_SwordBase", "CG_Slayer")
};
bool pg_lobby_live();                                    // MCC's Halo: Reach custom game lobby ran in the last 0.5 s
int  pg_lobby_maps(pg_entry* out, int cap);             // the library's maps (a copy made on MCC's thread)
int  pg_lobby_gametypes(pg_entry* out, int cap);        // its gametypes
uint32_t pg_lobby_seq();                                 // changes when a new copy is made (0: none yet)
// MCC's own pairing check for up to 64 (map, gametype) pairs, answered on MCC's thread: pg_lobby_check returns a
// ticket, pg_lobby_checked fills ok[] once answered (true) for that ticket
int  pg_lobby_check(const int* map, const int* gametype, int n);
bool pg_lobby_checked(int ticket, uint8_t* ok, int n);
// the picks into MCC's lobby and its Start pressed, on MCC's thread as its own Start tile does
void pg_lobby_launch(int map, int gametype);
int  pg_lobby_launch_state(char* why, int cap);          // 0 none, 1 waiting, 2 MCC's countdown started, -1 failed

// ---- proving_grounds.cpp
struct pg_env {
    hb_roster* roster;          // the lobby's bots (botcore.ini's main list)
    uint32_t difficulty;        // the "for everyone" difficulty a bot without saved settings takes
    float scale;                // px per 1080p unit (ui_layout.h mcc_content)
    float W, H;                 // the window, px
    ImFont *f_label, *f_small;  // Bahnschrift, large and small
    unsigned long long (*make_texture)(int w, int h, const unsigned char* rgba);
    void (*play_sound)(int kind, uint32_t volume);
    uint32_t sounds;            // volume 0-100
    bool pad;                   // the last input was the pad
    bool lobby_visible;         // MCC's custom game lobby is on screen (not a match, not the carnage report); during
                                // the launch (pg_launching), drawn over MCC's countdown till the game: true then too
    bool in_game;               // (Nov 18) MCC's menus gave way to a game (overlay.cpp mcc_menu_state 1)
    uint32_t* bots_enabled;     // turned on for a search (bots join at all)
    uint32_t* lidar_mode;       // turned off for a search
    // (Nov 17) a player's Reach figure in 3D for the player card: a bot's own look (bots_panel.cpp bot_figure), a
    // person Reach's default Spartan (person_figure); null or 0: none
    unsigned long long (*figure)(const char* name, bool bot, float yaw, int w, int h);
};
bool pg_running();              // a Proving Grounds session: between matches the lobby comes back to it
bool pg_visible();              // its screens are up (they take the mouse, keys and pad)
bool pg_launching();            // (Nov 18) the vote's winner sent to MCC's lobby, its game not started yet
void pg_open();                 // the lobby's PROVING GROUNDS tile
void pg_back();                 // Esc / the pad's B
// each frame over the lobby (between ImGui::NewFrame and Render); true when the roster changed (save it)
bool pg_frame(pg_env& e);
// a match ended (botcore.cpp g_pool_due): the lobby between matches (some bots leave, new ones come, teams dealt
// again); true when the roster changed
bool pg_after_match(hb_roster& r, uint32_t difficulty);
const char* pg_map_name(const char* mcc_name, const char* key, char* out, int cap);   // "Sword Base"
// (Nov 18) a joined PC friend's copy shows the host's screens (pg_link.cpp): following them now (its own session shut)
bool pg_following();
void pg_follow_poll();          // the overlay's every frame: a host's state starts (or ends) the following

// ---- pg_link.cpp (Nov 18): the host's Proving Grounds to a joined PC friend's, over MCC's Party text chat
#define PGS_MAX 4096             // a state's bytes at most (60000 went through live)
#define PGS_MAGIC "PGS2"
void pg_link_watch();                                    // botcore.cpp's loop: hooks MCC's Party once it is loaded
void pg_link_set_state(const void* data, uint32_t n);    // the host: its state, sent to linked friends
uint32_t pg_link_state(void* out, uint32_t cap, uint64_t* age_ms);   // the friend: the newest state (0: none)
void pg_link_send_vote(uint32_t key, int vote, const char* name);    // the friend: its vote, to the host
bool pg_link_vote(char* name, int cap, uint32_t* key, int* vote);    // the host: a friend's vote came (one a call)
