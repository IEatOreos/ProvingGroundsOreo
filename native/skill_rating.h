// skill_rating.h (custom, Nov 23): Project Noble's skill ratings, Halo: Reach's RATING, in place of the team points.
// The owner's rules, agreed one question at a time on Nov 23:
//  - the teams are dealt by their total rating (bots_panel.cpp's balancer, as the points were);
//  - each bot has its own rating, saved by name, kept inside its difficulty's range, starting at a random place in it;
//    a win +19 (+9 beating a team whose average is more than 150 lower), a loss -19 (-9 losing to one more than 150
//    higher); no kill bonus;
//  - each person (the player and each friend who joins) their own, starting at 1600, never under 1500: a win +35 to +40
//    (+30 to +35 beating a team more than 150 lower), a loss -15 (-10 losing to a team more than 150 higher), and in a
//    win up to +3 more for kills above the lobby's average; quitting +15 (so the next teams are tougher), nothing else;
//  - a draw changes nothing; a bot that quits takes a loss; Firefight is not rated;
//  - free for all has a rating of its own: 1st +40, 2nd +30, 3rd +20, the rest -15.
// Kept in native\bin\pg_ratings.txt (the game's own file: it is the only one that writes it).
#pragma once
#include <string>
#include <vector>

#define SR_PERSON_START 1600
#define SR_PERSON_FLOOR 1500
#define SR_GAP 150                  // a team average this much apart: the smaller win, the smaller loss
#define SR_TIE 50                   // (the balancer) splits this close to the most even one count as even

struct sr_range { int base, lo, hi; };
sr_range sr_tier_range(int tier);   // a difficulty's base and range (bots_panel.h's tiers)

// the file in dir (ending in a backslash); read again whenever it changes on disk. False: there is none yet
bool sr_open(const wchar_t* dir);
void sr_readonly(bool on);          // (the preview, the tests) ratings worked out but never written

int  sr_bot(const char* name, int tier, bool ffa = false);   // its saved rating; none (or another tier's): its start
int  sr_bot_start(const char* name, int tier, bool ffa = false);
int  sr_person(const char* name, bool ffa = false);          // saved, else 1600
void sr_note_tier(const char* name, int tier);               // a bot seated at this difficulty (for rating it later)
int  sr_tier_of(const char* name);                           // the difficulty it was last seated or rated at, else -1
void sr_reset_person(const char* name);                      // back to 1600, teams and free for all

// a match: each player as the carnage report has them. sr_rate fills before and after, saves, and keeps after for the
// RATING page (sr_shown). False when the match was counted already or is not rated (Firefight, no players)
struct sr_player {
    std::string name;
    bool bot = false, completed = true;
    int tier = -1, team = 0, place = 1, kills = 0;
    int before = 0, after = 0;
};
bool sr_rate(const char* id, bool teams, const char* gametype, std::vector<sr_player>& pl);
const char* sr_counted();           // the last match counted
void sr_set_counted(const char* id);    // (the first time: the match already played is not counted)
int  sr_shown(const char* name);    // the newest match's rating after it, -1 not in it
const char* sr_shown_match();
