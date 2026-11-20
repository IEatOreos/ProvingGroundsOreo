// armory.h (custom, Nov 19): Proving Grounds' Halo: Reach Armory (native/armory.cpp). The owner: every item bought
// with credits, as in the 2010 Armory; MCC keeps everything unlocked and untouched, and only what was bought here can
// be worn. Read by the Reach menus (proving_grounds_reach.inc), the 3D figure (bots_panel.cpp person_figure) and the
// match (reach.cpp, which lays the equipped pieces over the player's configuration).
#pragma once
#include <stdint.h>
#include <string>
#include <vector>

struct arm_item {
    std::string id, slot, name, gate;          // gate: the rank it needs, as the Service Record names it
    int family = 0, variant = 0, cost = 0, gate_step = 0;
    std::vector<int> needs;                    // the items to own first (indexes into armory_items)
    bool def = false, autobuy = false, ours = false;
    int nw = 0, off[2] = {}, val[2] = {};      // the configuration bytes it sets
};
enum { ARM_LOCKED_RANK, ARM_LOCKED_NEEDS, ARM_FOR_SALE, ARM_OWNED, ARM_EQUIPPED };
static const int ARM_NSLOTS = 10;
extern const char* const ARM_SLOTS[ARM_NSLOTS];   // helmet, left_shoulder, ... elite_armor (reach_prices.json's)

bool armory_load();                            // reads what changed; false: no armory.txt yet (the site not built)
const std::vector<arm_item>& armory_items();
int armory_find(const char* id);
// the player: their rank step and credits earned (the Service Record's), what the Armory spent of them
bool armory_me(const char* name, int* step, std::string* rank, int* earned);
int armory_balance(const char* name);
int armory_state(int i, const char* name);    // ARM_*
bool armory_buy(int i, const char* name);     // false (nothing changes): locked, already owned or too few credits
bool armory_equip(int i, const char* name);   // false (nothing changes): not owned
int armory_worn(const char* slot);             // the item index worn in a slot (its default when none was equipped)
void armory_try(int i);                        // the figure shows item i on (-1: only what is equipped)
int armory_trying();
// the figure: the player's own configuration as they last joined a match (my_look_reach.txt), with the Armory's
// pieces laid over it, and the model pieces those bytes put on (body 0 male, 1 female, 2 Elite)
bool armory_dressed(uint8_t cfg[0xA0], char* name, int cap);
int armory_pieces(const uint8_t* cfg, int body, const char** region, const char** perm, int cap);
// the match: the bytes to lay over the player's configuration (0: the Armory is off or not set up)
int armory_wear(uint8_t* off, uint8_t* val, int cap);
