// First person passenger (the BOTS panel's Experimental tab; upstream 0.3.0, build 20261115-0215): a vehicle's
// passenger seats see from the rider's own eyes, as Halo: CE's do. (custom, Nov 24, owner: "with #53 (Reach), off by
// default") only Halo: Reach's reach.cpp hr_passenger_fp hands seats here. A seat definition's first dword is its
// flags: 0x4 driver, 0x8 gunner, 0x10 third person camera, 0x40 third person on entering, and a boarding spot
// 0x08000000 in Reach (reach.cpp passes its keep mask: those bits and the driver's and gunner's). A passenger seat is
// one with none of them; it loses 0x10 and 0x40 while the switch is on and gets them back when it goes off. Live Nov
// 15 (his): Reach's Warthog driver 04020014, passenger 00000870, a gun 00080818; a Mongoose's passenger 02008270.
#include <windows.h>
#include <stdint.h>

void logf(const char* fmt, ...);
bool bots_panel_passenger_fp();

namespace {
const uint32_t FP_CLEAR = 0x50u;
uint8_t* g_defs[512];
uint32_t g_was[512];
uint32_t g_key[512];                              // (custom) where each was found: the vehicle's tag index and seat
int g_seat[512];
int g_n;
}  // namespace

bool fp_on() { return bots_panel_passenger_fp(); }

// one seat definition: a passenger's loses its third person bits (remembered once, put back by fp_restore)
void fp_seat(uint8_t* def, uint32_t keep, const char* tag, uint32_t key, int seat) {
    if (!def) return;
    uint32_t fl = *(uint32_t*)def;
    if ((fl & keep) || !(fl & FP_CLEAR)) return;
    bool seen = false;
    for (int i = 0; i < g_n && !seen; i++) seen = g_defs[i] == def;
    if (!seen) {
        if (g_n >= 512) return;                   // (never patched unless it can be put back)
        g_defs[g_n] = def;
        g_key[g_n] = key;
        g_seat[g_n] = seat;
        g_was[g_n++] = fl;
    }
    *(uint32_t*)def = fl & ~FP_CLEAR;
    logf("%s first person passenger: seat %p %08x -> %08x", tag, def, fl, fl & ~FP_CLEAR);
}

// a vehicle tag's seat block (n seats, stride bytes apart, flags first in each)
void fp_seats(uint8_t* first, int n, int stride, uint32_t keep, const char* tag, uint32_t key) {
    if (!first || n <= 0 || n > 32) return;
    for (int k = 0; k < n; k++) fp_seat(first + (size_t)k * stride, keep, tag, key, k);
}

// A vehicle tag's seat block at its game's known place in the tag's data (off: the block's count, off + 4 its packed
// address; stride bytes a seat), measured live (Reach +0x444 / 0x12C). Never searched for at run time: once a
// passenger seat has lost its third person bit, a search would no longer know the block and could take another for it
// (Halo 2, Nov 15). The block is used only when its count is 1..16 and its first seat is the driver's (bit 0x4).
typedef uint8_t* (*fp_unpack_fn)(uint32_t packed);
// key: the vehicle tag's index (fp_check finds the seat again by it)
bool fp_tag_seats(uint8_t* data, int off, int stride, uint32_t keep, fp_unpack_fn unpack, const char* game, uint32_t key) {
    int n = 0;
    uint8_t* first = nullptr;
    __try {
        n = *(int32_t*)(data + off);
        if (n < 1 || n > 16) return false;
        first = unpack(*(uint32_t*)(data + off + 4));
        if (!first || !(*(uint32_t*)first & 0x4u)) return false;
        fp_seats(first, n, stride, keep, game, key);
    } __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
    return true;
}

// the switch off: every seat back as it was. (custom, Nov 24) a seat is written back only while it still reads what we
// made of it, so memory that changed under us is never written
void fp_restore(const char* tag) {
    if (!g_n) return;
    int back = 0;
    for (int i = 0; i < g_n; i++) {
        __try {
            if (*(uint32_t*)g_defs[i] == (g_was[i] & ~FP_CLEAR)) { *(uint32_t*)g_defs[i] = g_was[i]; back++; }
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
    }
    logf("%s first person passenger: off, %d of %d seats back to third person", tag, back, g_n);
    g_n = 0;
}
void fp_forget() { g_n = 0; }   // (the game's dll reloaded: its tags are gone)

// (custom, Nov 24) a new match: a new map loads its tags afresh, but a seat kept from the last match (the same map's tags
// left in place) must still be put back when the switch goes off, so the list is not simply dropped (his dropped it):
// a seat stays on it only while its vehicle's tag (`seat_at`: the game's tag table, by the tag index and seat it was
// found at) still leads to the same address and it still reads what we made of it; any other is dropped, never written
void fp_check(uint8_t* (*seat_at)(uint32_t key, int seat), const char* tag) {
    int kept = 0, was = g_n;
    for (int i = 0; i < g_n; i++) {
        bool same = false;
        __try { same = seat_at(g_key[i], g_seat[i]) == g_defs[i] && *(uint32_t*)g_defs[i] == (g_was[i] & ~FP_CLEAR); }
        __except (EXCEPTION_EXECUTE_HANDLER) { same = false; }
        if (!same) continue;
        g_defs[kept] = g_defs[i];
        g_was[kept] = g_was[i];
        g_key[kept] = g_key[i];
        g_seat[kept++] = g_seat[i];
    }
    g_n = kept;
    if (was) logf("%s first person passenger: a new match, %d of %d patched seats still the map's", tag, kept, was);
}
