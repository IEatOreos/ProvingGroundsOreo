// pool_test.cpp (custom, Nov 10): Bot Matchmaking's pool checks. Links the real bots_panel.cpp and drives the pool
// functions on a scratch folder. Build and run: native\build_pool_test.bat (needs Visual Studio's C++ tools, as build.bat).
// pool_test.exe <dir> make: makes <dir>'s bot_pool.txt as botcore does at MCC start (when it is missing).
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bots_panel.h"

static int fails = 0;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

static void write(const wchar_t* path, const char* text) {
    FILE* f = nullptr; _wfopen_s(&f, path, L"wb"); fputs(text, f); fclose(f);
}

static hb_roster seats(int n) {
    hb_roster r{}; r.teams = 2;
    for (int i = 0; i < n; i++) { r.bot[i].team = (uint8_t)(i % 2); r.bot[i].tier = 2; r.bot[i].style = HB_STYLE_ANY; sprintf_s(r.bot[i].name, "Old%d", i); }
    r.n = n;
    return r;
}

int main(int argc, char** argv) {
    wchar_t dir[MAX_PATH];
    swprintf_s(dir, L"%S\\", argv[1]);
    if (argc > 2 && !strcmp(argv[2], "make")) {        // make <dir>'s pool as botcore does at MCC start (if missing)
        wchar_t prof[MAX_PATH];
        swprintf_s(prof, L"%sbot_profiles.ini", dir);
        bots_panel_profiles(prof);
        bot_pool_load(dir);
        printf("pool: %d bots (%d profiles first)\n", bot_pool_size(), profiles_count());
        return 0;
    }
    wchar_t pool[MAX_PATH], saved[MAX_PATH];
    swprintf_s(pool, L"%sbot_pool.txt", dir);
    swprintf_s(saved, L"%sbot_pool_saved.ini", dir);
    DeleteFileW(pool); DeleteFileW(saved);

    // 1. a missing pool is made: 60 unique names
    bot_pool_load(dir);
    CHECK(bot_pool_size() == 60, "new pool size %d", bot_pool_size());

    // 2. the file's rules: BOM, comments, blank lines, a long name cut to 15, commas dropped; (Nov 11) a repeat (any case)
    // kept in the queue, as the owner's Call of Duty name file has them
    write(pool, "\xEF\xBB\xBF" "Alpha\r\n# a note\r\n; another\r\n\r\n  Bravo  \r\nxX_DeadlyAssassin_Xx\r\nCh,arlie\r\nDelta\r\nEcho\r\nalpha\r\n");
    DeleteFileW(saved);
    bot_pool_load(dir);
    CHECK(bot_pool_size() == 7, "pool size %d (want 7)", bot_pool_size());
    CHECK(!strcmp(bot_pool_upcoming(6), "alpha"), "repeat kept '%s'", bot_pool_upcoming(6));
    CHECK(!strcmp(bot_pool_upcoming(0), "Alpha"), "first '%s'", bot_pool_upcoming(0));
    CHECK(!strcmp(bot_pool_upcoming(1), "Bravo"), "second '%s'", bot_pool_upcoming(1));
    CHECK(!strcmp(bot_pool_upcoming(2), "xX_DeadlyAssass"), "cut '%s'", bot_pool_upcoming(2));
    CHECK(!strcmp(bot_pool_upcoming(3), "Charlie"), "comma '%s'", bot_pool_upcoming(3));

    // 3. rotation fills seats in queue order, teams kept, the seats' shared difficulty (Heroic) for unsaved bots
    hb_roster r = seats(3);
    CHECK(bot_pool_rotate(r, 4) == 3, "filled");
    CHECK(!strcmp(r.bot[0].name, "Alpha") && !strcmp(r.bot[1].name, "Bravo") && !strcmp(r.bot[2].name, "xX_DeadlyAssass"),
          "rotation 1: %s %s %s", r.bot[0].name, r.bot[1].name, r.bot[2].name);
    // (Nov 13: the teams are dealt by points now; the team sizes are kept)
    CHECK(roster_on_team(r, 0) == 2 && roster_on_team(r, 1) == 1, "team sizes kept: %d %d", roster_on_team(r, 0), roster_on_team(r, 1));
    CHECK(r.bot[0].tier == 2 && r.bot[1].tier == 2, "shared Heroic kept: %d %d", r.bot[0].tier, r.bot[1].tier);
    CHECK(!strcmp(bot_pool_upcoming(0), "Charlie"), "next up '%s'", bot_pool_upcoming(0));

    // 4. a saved bot keeps its difficulty and style; the queue wraps round
    r.bot[1].tier = HB_TIER_DEMON; r.bot[1].style = 2;
    bot_pool_remember(r.bot[1]);                      // Bravo: Demon flanker
    CHECK(bot_pool_saved_count() == 1, "saved count");
    bot_pool_rotate(r, 4);                            // Charlie, Delta, Echo
    CHECK(!strcmp(r.bot[0].name, "Charlie") && !strcmp(r.bot[2].name, "Echo"), "rotation 2: %s %s %s", r.bot[0].name, r.bot[1].name, r.bot[2].name);
    bot_pool_rotate(r, 4);                            // alpha (the repeat), then Alpha skipped (seated), Bravo, xX...
    CHECK(!strcmp(r.bot[0].name, "alpha"), "the repeat seated: %s", r.bot[0].name);
    for (int i = 0; i < r.n; i++) for (int j = i + 1; j < r.n; j++)
        CHECK(_stricmp(r.bot[i].name, r.bot[j].name) != 0, "one name in two seats: %s", r.bot[i].name);
    CHECK(!strcmp(r.bot[1].name, "Bravo"), "Bravo back: %s", r.bot[1].name);
    CHECK(r.bot[1].tier == HB_TIER_DEMON && r.bot[1].style == 2, "Bravo saved: tier %d style %d", r.bot[1].tier, r.bot[1].style);
    CHECK(r.bot[0].tier == 2 && r.bot[0].style == HB_STYLE_ANY, "Alpha default: tier %d style %d", r.bot[0].tier, r.bot[0].style);

    // 5. the queue position and saved settings survive a reload (a new MCC start)
    const char* next = bot_pool_upcoming(0);
    char want[16]; strcpy_s(want, next);
    bot_pool_load(dir);
    CHECK(!strcmp(bot_pool_upcoming(0), want), "after reload next '%s' want '%s'", bot_pool_upcoming(0), want);
    int t = -1, st = -1;
    CHECK(bot_pool_saved_of("bravo", &t, &st) && t == HB_TIER_DEMON && st == 2, "saved after reload %d %d", t, st);

    // 6. forget: back to defaults
    bot_pool_forget("Bravo");
    CHECK(!bot_pool_saved_of("Bravo", nullptr, nullptr) && bot_pool_saved_count() == 0, "forgotten");

    // 7. names added to the file while running count at the next rotation
    write(pool, "Alpha\nBravo\nCharlie\nDelta\nEcho\nFoxtrot\nGolf\nHotel\n");
    hb_roster r2 = seats(2);
    bot_pool_rotate(r2, 0);
    CHECK(bot_pool_size() == 8, "re-read size %d", bot_pool_size());

    // 8. a pool smaller than the seats: every pool name seated once, the rest made up, no repeats
    write(pool, "Solo\nDuo\n");
    hb_roster r3 = seats(4);
    CHECK(bot_pool_rotate(r3, 1) == 2, "small pool fills 2");
    for (int i = 0; i < r3.n; i++) for (int j = i + 1; j < r3.n; j++)
        CHECK(_stricmp(r3.bot[i].name, r3.bot[j].name) != 0, "repeat %s", r3.bot[i].name);
    CHECK(r3.bot[0].name[0] && r3.bot[3].name[0], "names set");

    // 9. mixed seats (a saved Demon among Heroics): the newcomers take the unsaved seats' Heroic, not a Mixed deal
    write(pool, "A1\nA2\nA3\nA4\nA5\nA6\n");
    DeleteFileW(saved);
    bot_pool_load(dir);
    hb_roster r4 = seats(3);
    bot_pool_rotate(r4, 2);                           // A1 A2 A3, all Heroic
    r4.bot[0].tier = HB_TIER_DEMON; bot_pool_remember(r4.bot[0]);
    bot_pool_rotate(r4, 4);                           // A4 A5 A6: difficulty 4 is Mixed, the unsaved seats share Heroic
    for (int i = 0; i < 3; i++) CHECK(r4.bot[i].tier == 2, "seat %d tier %d (want Heroic)", i, r4.bot[i].tier);

    // 10. roster_name draws from the pool while it is on, made-up names when off
    hb_matchmaking = 1;
    hb_roster r5{}; r5.teams = 2;
    roster_add(r5, 0, 1, HB_STYLE_ANY, 77);
    CHECK(!strncmp(r5.bot[0].name, "A", 1) && strlen(r5.bot[0].name) == 2, "add from pool: %s", r5.bot[0].name);
    hb_matchmaking = 0;
    roster_add(r5, 1, 1, HB_STYLE_ANY, 78);
    CHECK(!(r5.bot[1].name[0] == 'A' && strlen(r5.bot[1].name) == 2), "off: not from pool: %s", r5.bot[1].name);

    // 11. (Nov 11) a pool bot's look seed is brain/looks.py seed_of's: zlib.crc32(name.lower()) (tools/test_bot_matchmaking.py)
    CHECK(name_look_seed("MadPistol") == 999176086u, "seed MadPistol %u", name_look_seed("MadPistol"));
    CHECK(name_look_seed("Sword117") == 4220511441u, "seed Sword117 %u", name_look_seed("Sword117"));
    CHECK(name_look_seed("xX_DeadlyAssass") == 2723695146u, "seed xX %u", name_look_seed("xX_DeadlyAssass"));

    // 12. any bot gets a profile for the editor, with the look it has now, written at once; one profile a name
    wchar_t prof[MAX_PATH];
    swprintf_s(prof, L"%sbot_profiles.ini", dir);
    write(prof, "experience=original\neffects=none\nbot=Alpha,111,TBK\nbot=Bravo,222,\n");
    bots_panel_profiles(prof);
    CHECK(profiles_count() == 2, "profiles %d", profiles_count());
    int k = profile_ensure("MadPistol");
    CHECK(k == 2 && profiles_count() == 3 && !strcmp(profile_clan(k), ""), "ensure new: %d %d", k, profiles_count());
    CHECK(profile_ensure("madpistol") == 2 && profile_ensure("Alpha") == 0 && profiles_count() == 3, "ensure existing");
    bots_panel_profiles(prof);                       // written: read back
    CHECK(profile_index("MadPistol") == 2, "written %d", profile_index("MadPistol"));
    {
        FILE* f = nullptr; _wfopen_s(&f, prof, L"rb"); char all[4096] = ""; size_t n = fread(all, 1, sizeof all - 1, f); all[n] = 0; fclose(f);
        const char* at = strstr(all, "bot=MadPistol,999176086,");   // (no clan, nothing set by hand: the line ends)
        CHECK(at && (at[24] == '\r' || at[24] == '\n'), "line: %s", all);
    }

    // 13. a re-roll draws the 15 again and keeps every bot dressed beyond them, its hand-set look too
    {
        char text[4096] = "experience=original\neffects=none\n";
        for (int i = 0; i < 15; i++) { char l[64]; sprintf_s(l, "bot=Install%d,%d,\n", i, 1000 + i); strcat_s(text, l); }
        strcat_s(text, "bot=MadPistol,999176086,ODST,h4.primary=3;h4.helmet=12\n");
        write(prof, text);
        bots_panel_profiles(prof);
        CHECK(profiles_count() == 16, "16 profiles: %d", profiles_count());
        CHECK(profiles_reroll(prof, 0, 0, 12345, 1, -1), "reroll");
        CHECK(profiles_count() == 16, "after re-roll %d", profiles_count());
        int m = profile_index("MadPistol");
        CHECK(m == 15 && !strcmp(profile_clan(m), "ODST") && profile_over_get(m, "h4.helmet") == 12, "kept: %d", m);
        CHECK(profile_index("Install0") < 0, "the 15 drawn again");
    }

    // 14. the editor's rename: the bot's pool line (others and notes as written) and saved settings follow
    write(pool, "# my bots\r\nAlpha\r\nBravo\r\nCharlie\r\n");
    DeleteFileW(saved);
    bot_pool_load(dir);
    hb_bot br{}; strcpy_s(br.name, "Bravo"); br.tier = HB_TIER_DEMON; br.style = 1;
    bot_pool_remember(br);
    bot_pool_rename("bravo", "BravoTwo");
    CHECK(bot_pool_has("BravoTwo") && !bot_pool_has("Bravo") && bot_pool_size() == 3, "renamed in the pool");
    t = -1;
    CHECK(bot_pool_saved_of("BravoTwo", &t, nullptr) && t == HB_TIER_DEMON, "saved follows");
    {
        FILE* f = nullptr; _wfopen_s(&f, pool, L"rb"); char all[256] = ""; size_t n = fread(all, 1, sizeof all - 1, f); all[n] = 0; fclose(f);
        CHECK(!strcmp(all, "# my bots\r\nAlpha\r\nBravoTwo\r\nCharlie\r\n"), "file: [%s]", all);
    }

    // 15. (Nov 11) the lobby's bot menu, "Swap for next bot": one seat gets the next pool bot (never itself or a seated
    // one), its saved settings, else the other unsaved seats' shared difficulty; nothing free: the seat kept
    write(pool, "S1\nS2\nS3\nS4\nS5\n");
    DeleteFileW(saved);
    bot_pool_load(dir);
    hb_roster r6 = seats(3);
    bot_pool_rotate(r6, 2);                          // S1 S2 S3, Heroic
    hb_bot s5{}; strcpy_s(s5.name, "S5"); s5.tier = HB_TIER_BLIND; s5.style = 3;
    bot_pool_remember(s5);
    CHECK(bot_pool_swap(r6, 1, 4) && !strcmp(r6.bot[1].name, "S4"), "swap 1: %s", r6.bot[1].name);
    CHECK(r6.bot[1].tier == 2 && r6.bot[1].style == HB_STYLE_ANY, "S4 takes the table's Heroic: %d", r6.bot[1].tier);
    CHECK(bot_pool_swap(r6, 1, 4) && !strcmp(r6.bot[1].name, "S5"), "swap 2: %s", r6.bot[1].name);
    CHECK(r6.bot[1].tier == HB_TIER_BLIND && r6.bot[1].style == 3, "S5 saved: %d %d", r6.bot[1].tier, r6.bot[1].style);
    CHECK(bot_pool_swap(r6, 1, 4) && !strcmp(r6.bot[1].name, "S2"), "swap 3 wraps past the seated S1: %s", r6.bot[1].name);
    write(pool, "S1\nS2\nS3\n");
    bot_pool_load(dir);
    hb_roster r7 = seats(3);
    bot_pool_rotate(r7, 2);
    char was0[16]; strcpy_s(was0, r7.bot[0].name);
    CHECK(!bot_pool_swap(r7, 0, 2) && !strcmp(r7.bot[0].name, was0), "nothing free: kept %s (was %s)", r7.bot[0].name, was0);

    // 16. (Nov 11) MCC's folder from its exe's path in any case: live, Steam ran it in lower case and none was read
    {
        wchar_t root[320];
        CHECK(mcc_root_of(L"F:\\SteamLibrary\\steamapps\\common\\Halo The Master Chief Collection\\mcc\\binaries\\win64\\"
                          L"mcc-win64-shipping.exe", root, 320) &&
              !wcscmp(root, L"F:\\SteamLibrary\\steamapps\\common\\Halo The Master Chief Collection\\"), "lower case: %ls", root);
        CHECK(mcc_root_of(L"C:\\Games\\MCC\\MCC\\Binaries\\Win64\\MCC-Win64-Shipping.exe", root, 320) &&
              !wcscmp(root, L"C:\\Games\\MCC\\"), "as written: %ls", root);
        CHECK(!mcc_root_of(L"C:\\Other\\game.exe", root, 320), "not MCC");
    }

    // 17. (Nov 11) MCC's nameplates from its own folder (the env MCC_ROOT, else this machine's Steam copy; none: skipped):
    // the catalog, a bot's own (never the blank one, the same every time), one picked in the editor, the PNGs read
    {
        wchar_t mcc[300];
        DWORD n = GetEnvironmentVariableW(L"MCC_ROOT", mcc, 300);
        if (!n) wcscpy_s(mcc, L"F:\\SteamLibrary\\steamapps\\common\\Halo The Master Chief Collection\\");
        else if (mcc[n - 1] != L'\\') wcscat_s(mcc, L"\\");
        nameplates_load(mcc);
        if (!nameplates_count()) printf("nameplates: no MCC at %ls, skipped\n", mcc);
        else {
            CHECK(nameplates_count() > 500, "nameplates %d", nameplates_count());
            CHECK(nameplate_index(1) == 0 && nameplate_team(1), "the blank one first, team-tinted");
            int a = bot_nameplate("MadPistol"), b2 = bot_nameplate("madpistol"), c = bot_nameplate("Sword117");
            CHECK(a > 1 && a == b2 && nameplate_index(a) >= 0, "MadPistol's %d %d", a, b2);
            CHECK(c > 1 && nameplate_index(c) >= 0, "Sword117's %d", c);
            int w = 0, h = 0;
            CHECK(nameplate_decode(a, &w, &h) && w == 360 && h == 52, "its PNG %dx%d", w, h);
            write(prof, "experience=original\neffects=none\nbot=MadPistol,999176086,,mcc.nameplate=42\n");
            bots_panel_profiles(prof);
            CHECK(bot_nameplate("MadPistol") == 42, "picked %d", bot_nameplate("MadPistol"));
            write(prof, "experience=original\neffects=none\nbot=MadPistol,999176086,,mcc.nameplate=99999\n");
            bots_panel_profiles(prof);
            CHECK(bot_nameplate("MadPistol") == a, "a picked one MCC does not have: its own %d", bot_nameplate("MadPistol"));
            printf("nameplates: %d from MCC, MadPistol wears %d\n", nameplates_count(), a);
        }
    }

    // 18. (Nov 11) MCC ranks by difficulty: Demon the top two tours (the eagle has no level, tour 10 at level 20+), Easy
    // the first two, each tier in its own tours, levels 1-30, the same for the same bot every time
    {
        const char* names[] = { "MadPistol", "Sword117", "Reaper343", "Oreo", "MS3S", "Lucky117", "Pixelated", "Ice" };
        for (const char* nmx : names) {
            int t, l, t2, l2;
            bot_rank(nmx, HB_TIER_DEMON, &t, &l);
            CHECK((t == 11 && l == 0) || (t == 10 && l >= 20 && l <= 30), "Demon %s: tour %d level %d", nmx, t, l);
            bot_rank(nmx, HB_TIER_DEMON, &t2, &l2);
            CHECK(t == t2 && l == l2, "Demon %s the same", nmx);
            bot_rank(nmx, 0, &t, &l);
            CHECK(t >= 1 && t <= 2 && l >= 1 && l <= 30, "Easy %s: tour %d level %d", nmx, t, l);
            bot_rank(nmx, 3, &t, &l);
            CHECK(t >= 6 && t <= 9 && l >= 1 && l <= 30, "Legendary %s: tour %d level %d", nmx, t, l);
            bot_rank(nmx, 2, &t, &l);
            CHECK(t >= 4 && t <= 6, "Heroic %s: tour %d", nmx, t);
        }
    }

    // 19. (Nov 13) "Name*3": one bot, 3 turns spread through the queue (line 1 of 6: at 1, 3 and 5, before the line
    // standing there); the editor's rename keeps the turns
    write(pool, "A\nB*3\nC\nD\nE\nF\n");
    DeleteFileW(saved);
    bot_pool_load(dir);
    {
        const char* want19[] = { "A", "B", "C", "B", "D", "E", "B", "F" };
        CHECK(bot_pool_size() == 8, "Name*3 size %d", bot_pool_size());
        for (int k = 0; k < 8; k++) CHECK(!strcmp(bot_pool_upcoming(k), want19[k]), "turn %d: %s want %s", k, bot_pool_upcoming(k), want19[k]);
        bot_pool_rename("b", "Bee");
        FILE* f = nullptr; _wfopen_s(&f, pool, L"rb"); char all[128] = ""; size_t n = fread(all, 1, sizeof all - 1, f); all[n] = 0; fclose(f);
        CHECK(!strcmp(all, "A\nBee*3\nC\nD\nE\nF\n"), "renamed keeps *3: [%s]", all);
        write(pool, "Long_Name_Over_15*2\nX*abc\n");
        bot_pool_load(dir);
        CHECK(bot_pool_size() == 3 && !strcmp(bot_pool_upcoming(0), "Long_Name_Over_") && !strcmp(bot_pool_upcoming(2), "X*abc"),
              "a long name's *2 kept, *abc a name: %d %s %s", bot_pool_size(), bot_pool_upcoming(0), bot_pool_upcoming(2));
    }

    // 20. (Nov 13) the owner's points: Easy 1, Normal 2, Heroic 3, Legendary 8, Scaling 8, Demon 12, Blind 8, Tactician 5;
    // a human 20
    {
        const int want20[HB_TIERS] = { 1, 2, 3, 8, 8, 12, 8, 5 };
        for (int t = 0; t < HB_TIERS; t++) CHECK(tier_points(t) == want20[t], "tier %d points %d", t, tier_points(t));
        CHECK(HB_HUMAN_POINTS == 20, "human points");
    }

    // 21. two teams: the smallest gap with the team sizes kept; of the even splits, Demons stacked about 60% of the time.
    // The owner's lobby: you, 2 Demon, Blind, Legendary, 3 Tactician, 3 Heroic, Normal, 4 Easy (45 vs 45)
    bots_panel_profiles(prof);                        // (whatever profiles: none of these bots has a clan)
    {
        const int tiers[15] = { HB_TIER_DEMON, HB_TIER_DEMON, HB_TIER_BLIND, 3, HB_TIER_TACTICIAN, HB_TIER_TACTICIAN,
                                HB_TIER_TACTICIAN, 2, 2, 2, 1, 0, 0, 0, 0 };
        int humans[HB_TEAMS_MAX] = { 1 };
        int stacked = 0, runs = 2000;
        for (int k = 0; k < runs; k++) {
            hb_roster b{}; b.teams = 2; b.n = 15;
            for (int i = 0; i < 15; i++) { b.bot[i].tier = (uint8_t)tiers[i]; b.bot[i].team = (uint8_t)(i < 7 ? 0 : 1); sprintf_s(b.bot[i].name, "T%d", i); }
            uint32_t rng = 1000u + 7u * k;
            roster_point_balance(b, humans, rng);
            int red = 20, blue = 0, dr = 0;
            for (int i = 0; i < 15; i++) {
                (b.bot[i].team == 0 ? red : blue) += tier_points(b.bot[i].tier);
                if (b.bot[i].tier == HB_TIER_DEMON && b.bot[i].team == 0) dr++;
            }
            if (k < 3 || red != blue) CHECK(red == 45 && blue == 45 && roster_on_team(b, 0) == 7, "run %d: %d vs %d, %d red", k, red, blue, roster_on_team(b, 0));
            stacked += dr != 1;
        }
        CHECK(stacked > runs * 55 / 100 && stacked < runs * 65 / 100, "Demons stacked %d of %d (want about 60%%)", stacked, runs);
        printf("points: the owner's 8v8 even every time, Demons stacked in %d of %d\n", stacked, runs);
        // the 4v4 from the queue sim: you, Demon, Legendary, Blind, Tactician, Heroic, Normal, Easy (59: a gap of 1)
        const int t4[7] = { HB_TIER_DEMON, 3, HB_TIER_BLIND, HB_TIER_TACTICIAN, 2, 1, 0 };
        hb_roster b{}; b.teams = 2; b.n = 7;
        for (int i = 0; i < 7; i++) { b.bot[i].tier = (uint8_t)t4[i]; b.bot[i].team = (uint8_t)(i < 3 ? 0 : 1); sprintf_s(b.bot[i].name, "F%d", i); }
        uint32_t rng = 5;
        roster_point_balance(b, humans, rng);
        int red = 20, blue = 0;
        for (int i = 0; i < 7; i++) (b.bot[i].team == 0 ? red : blue) += tier_points(b.bot[i].tier);
        CHECK(abs(red - blue) == 1 && roster_on_team(b, 0) == 3, "4v4: %d vs %d", red, blue);
        // three teams: sizes kept, totals close (12 8 8 8 5 3 3 2 1: 50, 16-17 each)
        const int t3[9] = { HB_TIER_DEMON, 3, 3, HB_TIER_BLIND, HB_TIER_TACTICIAN, 2, 2, 1, 0 };
        int none[HB_TEAMS_MAX] = {};
        hb_roster c{}; c.teams = 3; c.n = 9;
        for (int i = 0; i < 9; i++) { c.bot[i].tier = (uint8_t)t3[i]; c.bot[i].team = (uint8_t)(i % 3); sprintf_s(c.bot[i].name, "G%d", i); }
        rng = 9;
        roster_point_balance(c, none, rng);
        int lo = 999, hi = 0;
        for (int t = 0; t < 3; t++) {
            int p = 0;
            for (int i = 0; i < 9; i++) if (c.bot[i].team == t) p += tier_points(c.bot[i].tier);
            lo = p < lo ? p : lo; hi = p > hi ? p : hi;
            CHECK(roster_on_team(c, t) == 3, "3 teams: team %d has %d", t, roster_on_team(c, t));
        }
        CHECK(hi - lo <= 2, "3 teams: %d to %d", lo, hi);
    }

    // 22. parties: one clan's bots always on one team; the next seats pull clanmates about 70% of the time
    write(prof, "experience=original\neffects=none\nbot=P1,1,XO\nbot=P2,2,XO\nbot=P3,3,XO\nbot=Solo,4,ZZ\n");
    bots_panel_profiles(prof);
    {
        hb_roster b{}; b.teams = 2; b.n = 6;
        const char* nm[6] = { "P1", "N1", "P2", "N2", "P3", "N3" };
        for (int i = 0; i < 6; i++) { strcpy_s(b.bot[i].name, nm[i]); b.bot[i].tier = (uint8_t)(i == 1 ? HB_TIER_DEMON : 2); b.bot[i].team = (uint8_t)(i % 2); }
        int humans[HB_TEAMS_MAX] = { 1 };
        for (int k = 0; k < 50; k++) {
            uint32_t rng = 31u + k;
            roster_point_balance(b, humans, rng);
            CHECK(b.bot[0].team == b.bot[2].team && b.bot[2].team == b.bot[4].team, "party split: %d %d %d", b.bot[0].team, b.bot[2].team, b.bot[4].team);
            CHECK(roster_on_team(b, 0) == 3, "sizes with a party");
        }
        write(pool, "P1\nN1\nN2\nN3\nN4\nP2\nN5\nP3\nN6\n");
        int pulled = 0, runs = 300;
        for (int k = 0; k < runs; k++) {
            DeleteFileW(saved);
            bot_pool_load(dir);
            bot_pool_seed(4242u + 13u * k);
            hb_roster s = seats(6);
            bot_pool_rotate(s, 2);
            bool p23 = !strcmp(s.bot[1].name, "P2") && !strcmp(s.bot[2].name, "P3");
            if (p23) {
                pulled++;
                CHECK(!strcmp(s.bot[3].name, "N1") && !strcmp(bot_pool_upcoming(0), "N4"), "after the pull: %s, next %s", s.bot[3].name, bot_pool_upcoming(0));
                CHECK(s.bot[0].team == s.bot[1].team && s.bot[1].team == s.bot[2].team, "pulled party on one team");
            } else CHECK(!strcmp(s.bot[1].name, "N1"), "no pull: queue order %s", s.bot[1].name);
        }
        CHECK(pulled > runs * 62 / 100 && pulled < runs * 78 / 100, "party pulled %d of %d (want about 70%%)", pulled, runs);
        printf("parties: pulled in %d of %d\n", pulled, runs);
    }

    // 23. the people of the last match (tools/play.py's bot_pool_humans.txt) count on their team; none: you on Red
    {
        wchar_t hum[MAX_PATH];
        swprintf_s(hum, L"%sbot_pool_humans.txt", dir);
        DeleteFileW(hum);
        bot_pool_load(dir);
        CHECK(bot_pool_humans(0) == 1 && bot_pool_humans(1) == 0, "default: you on Red");
        write(hum, "human=1\nhuman=1\nhuman=0\n");
        bot_pool_load(dir);
        CHECK(bot_pool_humans(0) == 1 && bot_pool_humans(1) == 2, "read: %d %d", bot_pool_humans(0), bot_pool_humans(1));
        hb_roster b = seats(2);                       // Old0 red, Old1 blue, Heroic
        CHECK(roster_team_points(b, 1) == 43 && roster_team_points(b, 0) == 23, "team points %d %d", roster_team_points(b, 0), roster_team_points(b, 1));
        DeleteFileW(hum);
    }

    // 24. "Group parties": each clan's lines together where its first stood, a round per repeat, notes and the rest kept
    write(pool, "# note\nP1\nN1\nN2\nP2*2\nN3\nP3\nP1\nSolo\n");
    bot_pool_load(dir);
    {
        CHECK(bot_pool_group_parties() == 1, "one party grouped (ZZ has one bot)");
        FILE* f = nullptr; _wfopen_s(&f, pool, L"rb"); char all[256] = ""; size_t n = fread(all, 1, sizeof all - 1, f); all[n] = 0; fclose(f);
        CHECK(!strcmp(all, "# note\nP1\nP2*2\nP3\nN1\nN2\nN3\nP1\nSolo\n"), "grouped file: [%s]", all);
        wchar_t bak[MAX_PATH]; swprintf_s(bak, L"%s.bak", pool);
        CHECK(GetFileAttributesW(bak) != INVALID_FILE_ATTRIBUTES, "backup kept");
        CHECK(bot_pool_size() == 9, "pool re-read %d", bot_pool_size());
        CHECK(bot_pool_group_parties() == 1, "again: the same");
    }

    printf(fails ? "%d FAILED\n" : "all pool checks passed\n", fails);
    return fails ? 1 : 0;
}
