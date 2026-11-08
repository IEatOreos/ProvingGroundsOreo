// film.h: recording and replaying the bots for Theater (film.cpp)
#pragma once
#include <stdint.h>
#include "shared.h"

struct film_frame {                       // the bots' input for one tick, as the hook uses it
    int32_t index[HB_MAX_PLAYERS];        // bot slot -> player index, -1 = none
    hb_action act[HB_MAX_PLAYERS];
};

// Call at the start of a game's players-update hook, on the game thread, before its command runner. key: the match's
// game options hashed (the same in its film); tick: the game's own tick count; playback: a Theater film is running;
// cmd_bit: the game's bit in cmd_arg. Returns this tick's input to use (live: frozen from shared memory and recorded;
// a film: from the match's recording, with its commands put into shared memory to run now), or null on a fault.
const film_frame* film_tick(uint64_t key, uint32_t tick, bool playback, uint32_t cmd_bit);
void film_end();
// For a command runner that can take several commands in one tick (H2A / Halo 4: a match's first tick waits for the
// bots, h4f.cpp f_prejoin), so film_tick gets cmd_bit 0 there: a live match records each command as the runner takes
// it, at this tick
void film_command(uint32_t tick);
// A film: the next recorded command of this tick into shared memory once the runner took the last one (each replayed
// command waits for the runner); false when this tick has no more. Two commands at one tick overwrote each other, so a
// Halo 4 film would have made only the last of its first tick's bots
bool film_more(uint32_t tick);
// A bot moved to its spawn (reach.cpp hr_spawn_moves) at this tick: recorded in a live match; a film puts the same
// spawn target into shared memory at that tick, before the move check
void film_spawn(uint32_t tick, int index, const float at[4]);

// FNV-1a of a block of bytes (the film key)
static inline uint64_t film_hash(const uint8_t* p, size_t n) {
    uint64_t h = 1469598103934665603ull;
    for (size_t i = 0; i < n; i++) { h ^= p[i]; h *= 1099511628211ull; }
    return h;
}
