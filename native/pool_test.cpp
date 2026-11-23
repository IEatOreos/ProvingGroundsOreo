// pool_test.cpp (custom, Nov 10): Bot Matchmaking's pool checks. Links the real bots_panel.cpp and drives the pool
// functions on a scratch folder. Build and run: native\build_pool_test.bat (needs Visual Studio's C++ tools, as build.bat).
// pool_test.exe <dir> make: makes <dir>'s bot_pool.txt as botcore does at MCC start (when it is missing).
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include "bots_panel.h"
#include "skill_rating.h"

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

    // 20. (Nov 13) the owner's points; (Nov 23) now skill ratings (27 checks the bases and ranges): a person 1600
    CHECK(SR_PERSON_START == 1600 && SR_PERSON_FLOOR == 1500, "a person 1600, never under 1500");
    { wchar_t rf[MAX_PATH]; swprintf_s(rf, L"%spg_ratings.txt", dir); DeleteFileW(rf); sr_open(dir); }   // (every bot at its start)

    // 21. two teams: the smallest gap with the team sizes kept; of the even splits (Nov 23: within SR_TIE of the
    // smallest), Demons stacked about 60% of the time. The owner's lobby: you, 2 Demon, Blind, Legendary, 3 Tactician,
    // 3 Heroic, Normal, 4 Easy
    bots_panel_profiles(prof);                        // (whatever profiles: none of these bots has a clan)
    {
        const int tiers[15] = { HB_TIER_DEMON, HB_TIER_DEMON, HB_TIER_BLIND, 3, HB_TIER_TACTICIAN, HB_TIER_TACTICIAN,
                                HB_TIER_TACTICIAN, 2, 2, 2, 1, 0, 0, 0, 0 };
        int humans[HB_TEAMS_MAX] = { 1 };
        int stacked = 0, runs = 2000, worst = 0;
        for (int k = 0; k < runs; k++) {
            hb_roster b{}; b.teams = 2; b.n = 15;
            for (int i = 0; i < 15; i++) { b.bot[i].tier = (uint8_t)tiers[i]; b.bot[i].team = (uint8_t)(i < 7 ? 0 : 1); sprintf_s(b.bot[i].name, "T%d", i); }
            uint32_t rng = 1000u + 7u * k;
            roster_point_balance(b, humans, rng);
            int red = SR_PERSON_START, blue = 0, dr = 0;
            for (int i = 0; i < 15; i++) {
                (b.bot[i].team == 0 ? red : blue) += sr_bot(b.bot[i].name, b.bot[i].tier);
                if (b.bot[i].tier == HB_TIER_DEMON && b.bot[i].team == 0) dr++;
            }
            CHECK(roster_on_team(b, 0) == 7, "run %d: %d red", k, roster_on_team(b, 0));
            worst = abs(red - blue) > worst ? abs(red - blue) : worst;
            stacked += dr != 1;
        }
        CHECK(worst <= SR_TIE + 20, "the owner's 8v8: gaps up to %d", worst);
        CHECK(stacked > runs * 45 / 100 && stacked < runs * 75 / 100, "Demons stacked %d of %d (want about 60%%)", stacked, runs);
        printf("ratings: the owner's 8v8 within %d every time, Demons stacked in %d of %d\n", worst, stacked, runs);
        // the 4v4 from the queue sim: you, Demon, Legendary, Blind, Tactician, Heroic, Normal, Easy (59: a gap of 1)
        const int t4[7] = { HB_TIER_DEMON, 3, HB_TIER_BLIND, HB_TIER_TACTICIAN, 2, 1, 0 };
        hb_roster b{}; b.teams = 2; b.n = 7;
        for (int i = 0; i < 7; i++) { b.bot[i].tier = (uint8_t)t4[i]; b.bot[i].team = (uint8_t)(i < 3 ? 0 : 1); sprintf_s(b.bot[i].name, "F%d", i); }
        uint32_t rng = 5;
        roster_point_balance(b, humans, rng);
        int red = SR_PERSON_START, blue = 0;
        for (int i = 0; i < 7; i++) (b.bot[i].team == 0 ? red : blue) += sr_bot(b.bot[i].name, b.bot[i].tier);
        CHECK(abs(red - blue) <= 300 && roster_on_team(b, 0) == 3, "4v4: %d vs %d", red, blue);
        printf("ratings: the queue sim's 4v4 %d vs %d\n", red, blue);
        // three teams: sizes kept, totals close
        const int t3[9] = { HB_TIER_DEMON, 3, 3, HB_TIER_BLIND, HB_TIER_TACTICIAN, 2, 2, 1, 0 };
        int none[HB_TEAMS_MAX] = {};
        hb_roster c{}; c.teams = 3; c.n = 9;
        for (int i = 0; i < 9; i++) { c.bot[i].tier = (uint8_t)t3[i]; c.bot[i].team = (uint8_t)(i % 3); sprintf_s(c.bot[i].name, "G%d", i); }
        rng = 9;
        roster_point_balance(c, none, rng);
        int lo = 1 << 30, hi = 0;
        for (int t = 0; t < 3; t++) {
            int p = 0;
            for (int i = 0; i < 9; i++) if (c.bot[i].team == t) p += sr_bot(c.bot[i].name, c.bot[i].tier);
            lo = p < lo ? p : lo; hi = p > hi ? p : hi;
            CHECK(roster_on_team(c, t) == 3, "3 teams: team %d has %d", t, roster_on_team(c, t));
        }
        CHECK(hi - lo <= 400, "3 teams: %d to %d", lo, hi);
        printf("ratings: three teams %d to %d\n", lo, hi);
    }

    // 22. parties: one clan's bots always on one team, (Nov 16) the team without people when it fits
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
            CHECK(b.bot[0].team == 1, "party on the team without people: %d", b.bot[0].team);
            CHECK(roster_on_team(b, 0) == 3, "sizes with a party");
        }
        // (Nov 14) the lobby's "Balance teams": the sizes evened (Nov 16: you counted: 3 bots with you, 3 without), then
        // the points dealt with the party together
        for (int k = 0; k < 20; k++) {
            hb_roster c = b;
            for (int i = 0; i < 6; i++) c.bot[i].team = 0;
            roster_balance(c);
            CHECK(roster_on_team(c, 0) == 3 && roster_on_team(c, 1) == 3, "balance sizes %d %d", roster_on_team(c, 0), roster_on_team(c, 1));
            CHECK(c.bot[0].team == c.bot[2].team && c.bot[2].team == c.bot[4].team, "balance split the party");
            CHECK(!roster_balance_note()[0], "no note: %s", roster_balance_note());
        }
        // (Nov 16) the 4v4 file: the clan's bots together, the other lines in their order
        write(pool, "P1\nN1\nN2\nN3\nN4\nP2\nN5\nP3\nN6\n");
        DeleteFileW(saved);
        bot_pool_load(dir);
        {
            char q[10][16]; int at = -1, nq = bot_pool_size(), nn = 0;
            for (int k = 0; k < nq; k++) strcpy_s(q[k], bot_pool_upcoming(k));
            for (int k = 0; k < nq; k++) if (!strcmp(q[k], "P1")) at = k;
            CHECK(nq == 9 && at >= 0 && at + 2 < nq && !strcmp(q[at + 1], "P2") && !strcmp(q[at + 2], "P3"), "party together at %d", at);
            for (int k = 0; k < nq; k++) if (q[k][0] == 'N') { char w[4]; sprintf_s(w, "N%d", ++nn); CHECK(!strcmp(q[k], w), "solo order %s want %s", q[k], w); }
            wchar_t f4[MAX_PATH]; swprintf_s(f4, L"%sbot_pool_4v4.txt", dir);
            CHECK(GetFileAttributesW(f4) != INVALID_FILE_ATTRIBUTES, "bot_pool_4v4.txt made");
        }
    }

    // 22b. (Nov 16) a clan of 6 in a 4v4 file: parties of 4 and 2 apart; the 2 pull the others in about 85% of the time,
    // up to 4 (the team without people has 4 seats), never more; the party on that team. 8v8: still 4 (the seats)
    {
        char text[2048] = "experience=original\neffects=none\n";
        for (int i = 1; i <= 6; i++) { char l[32]; sprintf_s(l, "bot=Q%d,%d,QQ\n", i, i); strcat_s(text, l); }
        write(prof, text);
        bots_panel_profiles(prof);
        char pl[4096] = "";
        for (int i = 1; i <= 6; i++) { char l[16]; sprintf_s(l, "Q%d\n", i); strcat_s(pl, l); }
        for (int i = 1; i <= 40; i++) { char l[16]; sprintf_s(l, "M%d\n", i); strcat_s(pl, l); }
        write(pool, pl);
        for (uint32_t fmt : { 4u, 8u }) {
            bot_pool_set_format(fmt);
            DeleteFileW(saved);
            bot_pool_load(dir);
            int q5 = -1;
            for (int k = 0; k < bot_pool_size(); k++) if (!strcmp(bot_pool_upcoming(k), "Q5")) q5 = k;
            CHECK(q5 >= 0 && !strcmp(bot_pool_upcoming(q5 + 1), "Q6"), "the party of 2 together (%u)", fmt);
            int four = 0, runs = 300;
            for (int k = 0; k < runs; k++) {
                char sv[64]; sprintf_s(sv, "next%u=%d\n", fmt, q5);
                write(saved, sv);
                bot_pool_load(dir);
                bot_pool_seed(777u + 31u * k);
                hb_roster s = seats(8);
                bot_pool_rotate(s, 2);
                int nq = 0, team = -1; bool one = true;
                for (int i = 0; i < 8; i++) if (s.bot[i].name[0] == 'Q') { nq++; if (team < 0) team = s.bot[i].team; else one &= s.bot[i].team == team; }
                CHECK(nq == 2 || nq == 4, "Q bots %d (%u)", nq, fmt);
                CHECK(one && team == 1, "party on one team, the one without people: %d (%u)", team, fmt);
                four += nq == 4;
            }
            CHECK(four > runs * 78 / 100 && four < runs * 92 / 100, "full party %d of %d (want about 85%%, %u)", four, runs, fmt);
            printf("parties (%uv%u): the full party in %d of %d\n", fmt, fmt, four, runs);
        }
        bot_pool_set_format(4);
    }

    // 22c. (Nov 16) Balance teams with a clan too big for any team (5 in a 4v4 with you): the sizes stay even; off, the
    // clan split (4 on the team without you) and the note says so; on, its extra bot swapped for the next pool bot
    {
        hb_roster c{}; c.teams = 2; c.n = 7;
        const char* nm[7] = { "Q1", "Q2", "Q3", "Q4", "Q5", "M1", "M2" };
        for (int i = 0; i < 7; i++) { strcpy_s(c.bot[i].name, nm[i]); c.bot[i].tier = 2; c.bot[i].team = 0; }
        DeleteFileW(saved);
        bot_pool_load(dir);
        hb_matchmaking = 0;
        hb_roster d = c;
        roster_balance(d);
        int qb = 0;
        for (int i = 0; i < 7; i++) qb += d.bot[i].name[0] == 'Q' && d.bot[i].team == 1;
        CHECK(roster_on_team(d, 0) == 3 && roster_on_team(d, 1) == 4, "even with you: %d %d", roster_on_team(d, 0), roster_on_team(d, 1));
        CHECK(qb == 4 && strstr(roster_balance_note(), "[QQ]") && strstr(roster_balance_note(), "split"), "split: %d '%s'", qb, roster_balance_note());
        hb_matchmaking = 1;
        d = c;
        roster_balance(d);
        int nq = 0, qt = -1; bool one = true;
        for (int i = 0; i < 7; i++) if (d.bot[i].name[0] == 'Q') { nq++; if (qt < 0) qt = d.bot[i].team; else one &= d.bot[i].team == qt; }
        CHECK(nq == 4 && one && qt == 1 && strstr(roster_balance_note(), "swapped"), "swapped: %d on %d '%s'", nq, qt, roster_balance_note());
        CHECK(roster_on_team(d, 0) == 3 && roster_on_team(d, 1) == 4, "still even: %d %d", roster_on_team(d, 0), roster_on_team(d, 1));
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
        hb_roster b = seats(2);                       // Old0 red, Old1 blue, Heroic (Nov 23: by rating, a person 1600)
        CHECK(roster_team_points(b, 1) == 2 * SR_PERSON_START + sr_bot("Old1", 2) &&
              roster_team_points(b, 0) == SR_PERSON_START + sr_bot("Old0", 2), "team ratings %d %d", roster_team_points(b, 0), roster_team_points(b, 1));
        DeleteFileW(hum);
    }

    // 24. (Nov 16) the 4v4 / 8v8 files: three clans of 2 bots, each line 10 times, among 200 others. Every clan's
    // parties apart from its own; about 1 in 4 places two clans side by side (they meet); bot_pool.txt unchanged; a clan
    // of one bot is no party; each format keeps its own queue position
    {
        write(prof, "experience=original\neffects=none\nbot=A1,1,AA\nbot=A2,2,AA\nbot=B1,3,BB\nbot=B2,4,BB\n"
                    "bot=C1,5,CC\nbot=C2,6,CC\nbot=Lone,7,LL\n");
        bots_panel_profiles(prof);
        std::string pl;
        for (int k = 0; k < 10; k++) pl += "A1\nA2\nB1\nB2\nC1\nC2\n";
        for (int i = 1; i <= 200; i++) { char l[16]; sprintf_s(l, "M%d\n", i); pl += l; if (i == 100) pl += "Lone\n"; }
        write(pool, pl.c_str());
        DeleteFileW(saved);
        bot_pool_load(dir);
        int met = 0, places = 0;
        for (int run = 0; run < 20; run++) {
            CHECK(bot_pool_reshuffle() == 3, "three clans");
            int n = bot_pool_size();
            CHECK(n == 261, "every line kept: %d", n);
            // each run of clan lines is a place: one clan's party, or two clans' side by side; between places at least
            // 3 other lines (201 lines, about 24 places: about 8 apart, never under half that, rounded down)
            char prev = 0; int last_end = -1, gap_min = 999, solo_n = 0;
            std::string clans_in;
            for (int k = 0; k <= n; k++) {
                const char* nm = k < n ? bot_pool_upcoming(k) : "";
                char c = (nm[0] == 'A' || nm[0] == 'B' || nm[0] == 'C') ? nm[0] : 0;
                if (c && !prev) { clans_in.clear(); if (last_end >= 0 && k - last_end < gap_min) gap_min = k - last_end; }
                if (c && clans_in.find(c) == std::string::npos) clans_in += c;
                if (!c && prev) { places++; met += clans_in.size() > 1; last_end = k; }
                if (!c && k < n) {                       // the other lines in their own order, Lone (a clan of one) among them
                    char w[16];
                    if (solo_n == 100) strcpy_s(w, "Lone"); else sprintf_s(w, "M%d", solo_n < 100 ? solo_n + 1 : solo_n);
                    CHECK(!strcmp(nm, w), "other lines' order: %s want %s", nm, w);
                    solo_n++;
                }
                prev = c;
            }
            CHECK(gap_min >= 3, "places %d apart", gap_min);
        }
        CHECK(met > places * 14 / 100 && met < places * 36 / 100, "clans meet in %d of %d places (want about 25%%)", met, places);
        printf("spread: clans meet in %d of %d places\n", met, places);
        FILE* f = nullptr; _wfopen_s(&f, pool, L"rb"); char head[16] = ""; fread(head, 1, 9, f); fclose(f);
        CHECK(!strncmp(head, "A1\nA2\nB1\n", 9), "bot_pool.txt unchanged: [%s]", head);
        // each format its own place
        hb_roster s = seats(4);
        bot_pool_rotate(s, 2);
        char next4[16]; strcpy_s(next4, bot_pool_upcoming(0));
        bot_pool_set_format(8);
        wchar_t f8[MAX_PATH]; swprintf_s(f8, L"%sbot_pool_8v8.txt", dir);
        CHECK(GetFileAttributesW(f8) != INVALID_FILE_ATTRIBUTES && bot_pool_size() == 261, "the 8v8 file read");
        bot_pool_set_format(4);
        CHECK(!strcmp(bot_pool_upcoming(0), next4), "4v4 place kept: %s want %s", bot_pool_upcoming(0), next4);
    }

    // 25. (Nov 16, Project Noble) bot_pool_matchmake: two teams of 4 (or 8) with the person on Red: 3 / 4 bots (7 / 8);
    // the invited party pinned to Red every time; a clan whole on one team (a clan of 3 with a party of 2 on Red: Blue);
    // no name twice; keep 100: every last-lobby bot stays (teams dealt again), keep 0: a new lobby but the party
    {
        write(prof, "experience=original\neffects=none\nbot=Q1,1,QQ\nbot=Q2,2,QQ\nbot=Q3,3,QQ\n");
        bots_panel_profiles(prof);
        std::string pl = "Q1\nQ2\nQ3\n";
        for (int i = 1; i <= 40; i++) { char l[16]; sprintf_s(l, "M%d\n", i); pl += l; }
        write(pool, pl.c_str());
        DeleteFileW(saved);
        wchar_t hum[MAX_PATH];
        swprintf_s(hum, L"%sbot_pool_humans.txt", dir);
        DeleteFileW(hum);
        const char party[2][16] = { "M5", "M6" };
        for (int size : { 4, 8 }) {
            bot_pool_set_format((uint32_t)size);
            int bad_size = 0, bad_party = 0, bad_clan = 0, dup = 0, clan_seen = 0;
            for (int run = 0; run < 150; run++) {
                bot_pool_seed(4242u + 17u * run);
                hb_roster r = seats(0);
                uint8_t pin[HB_ROSTER_MAX];
                bot_pool_matchmake(r, size, party, 2, 0, 0, 2, pin);
                if (r.n != size * 2 - 1 || roster_on_team(r, 0) != size - 1 || roster_on_team(r, 1) != size) bad_size++;
                int pr = 0, qn = 0, qt = -1; bool one = true;
                for (int i = 0; i < r.n; i++) {
                    if (pin[i]) { pr++; if (r.bot[i].team != 0) bad_party++; }
                    if (r.bot[i].name[0] == 'Q') { qn++; if (qt < 0) qt = r.bot[i].team; else one &= r.bot[i].team == qt; }
                    for (int k = i + 1; k < r.n; k++) dup += !_stricmp(r.bot[i].name, r.bot[k].name);
                }
                if (pr != 2) bad_party++;
                if (qn >= 2) { clan_seen++; if (!one || (size == 4 && qt != 1)) bad_clan++; }
            }
            CHECK(!bad_size, "%dv%d sizes wrong in %d runs", size, size, bad_size);
            CHECK(!bad_party, "%dv%d party off Red or missing in %d", size, size, bad_party);
            CHECK(!bad_clan, "%dv%d clan split or on Red in %d of %d", size, size, bad_clan, clan_seen);
            CHECK(!dup, "%dv%d a name twice %d", size, size, dup);
            printf("proving grounds %dv%d: 150 lobbies, the clan in %d\n", size, size, clan_seen);
        }
        bot_pool_set_format(4);
        bot_pool_seed(99);
        hb_roster r = seats(0);
        uint8_t pin[HB_ROSTER_MAX];
        bot_pool_matchmake(r, 4, party, 2, 0, 0, 2, pin);
        hb_roster kept = r;
        bot_pool_matchmake(kept, 4, party, 2, 0, 100, 2, pin);
        int same = 0;
        for (int i = 0; i < r.n; i++) for (int k = 0; k < kept.n; k++) same += !_stricmp(r.bot[i].name, kept.bot[k].name);
        CHECK(same == r.n && kept.n == 7, "keep 100: %d of %d stayed", same, r.n);
        hb_roster fresh = r;
        bot_pool_matchmake(fresh, 4, party, 2, 0, 0, 2, pin);
        same = 0;
        for (int i = 0; i < r.n; i++) for (int k = 0; k < fresh.n; k++) same += !_stricmp(r.bot[i].name, fresh.bot[k].name);
        CHECK(same < r.n, "keep 0: a new lobby (%d of %d the same, the party among them)", same, r.n);
        // pinned seats keep their team through the point deal, whatever their points
        hb_roster p = seats(7);
        uint8_t pins[HB_ROSTER_MAX] = {};
        p.bot[0].team = 0; p.bot[0].tier = HB_TIER_DEMON; pins[0] = 1;
        p.bot[2].team = 0; p.bot[2].tier = HB_TIER_DEMON; pins[2] = 1;
        int humans[HB_TEAMS_MAX] = { 1 };
        uint32_t rng = 5;
        for (int k = 0; k < 20; k++) { roster_point_balance(p, humans, rng, pins); CHECK(p.bot[0].team == 0 && p.bot[2].team == 0, "pinned moved"); }

        // 26. (Nov 17) friends who joined: each takes a bot's seat on the team MCC has them on (4v4, the player on Red: a
        // friend on Blue, 3 + 3 bots; on Red, 2 + 4); one not on a team yet goes where there are fewer people (Blue) and
        // is written back; 8v8 with a friend is 14 bots, the game's 16; keep 100 with a friend in: one bot goes, the
        // rest stay; out again: one comes back
        bot_pool_set_format(4);
        struct { int team, red, blue, resolved; } cases[] = { { 1, 3, 3, 1 }, { 0, 2, 4, 0 }, { -1, 3, 3, 1 } };
        for (auto& c : cases) {
            bot_pool_seed(7);
            hb_roster f = seats(0);
            uint8_t fp[HB_ROSTER_MAX];
            int people[1] = { c.team };
            bot_pool_matchmake(f, 4, party, 0, 0, 0, 2, fp, people, 1);
            CHECK(f.n == 6 && roster_on_team(f, 0) == c.red && roster_on_team(f, 1) == c.blue && people[0] == c.resolved,
                  "friend on %d: %d bots, %d red, %d blue, counted on %d", c.team, f.n, roster_on_team(f, 0),
                  roster_on_team(f, 1), people[0]);
            CHECK(bot_pool_humans(0) + bot_pool_humans(1) == 2, "friend: %d + %d people counted", bot_pool_humans(0),
                  bot_pool_humans(1));
        }
        // 26b. (Nov 23) a matchmade lobby counts the player at their own rating and a friend at theirs, on their teams
        for (int me : { 1500, 2100 }) {
            bot_pool_seed(7);
            hb_roster f = seats(0);
            uint8_t fp[HB_ROSTER_MAX];
            int people[1] = { 0 }, friends[1] = { 1750 };
            bot_pool_set_people_ratings(me, friends, 1);
            bot_pool_matchmake(f, 4, party, 0, 0, 0, 2, fp, people, 1);
            int bots0 = 0;
            for (int i = 0; i < f.n; i++) if (f.bot[i].team == 0) bots0 += sr_bot(f.bot[i].name, f.bot[i].tier);
            CHECK(roster_team_points(f, 0) == bots0 + me + 1750, "your rating %d: red %d, its bots %d",
                  me, roster_team_points(f, 0), bots0);
        }
        bot_pool_set_people_ratings(SR_PERSON_START, nullptr, 0);
        bot_pool_set_format(8);
        {
            bot_pool_seed(8);
            hb_roster f = seats(0);
            uint8_t fp[HB_ROSTER_MAX];
            int people[1] = { 1 };
            bot_pool_matchmake(f, 8, party, 2, 0, 0, 2, fp, people, 1);
            CHECK(f.n == 14 && roster_on_team(f, 0) == 7 && roster_on_team(f, 1) == 7, "8v8 friend: %d bots", f.n);
        }
        bot_pool_set_format(4);
        {
            bot_pool_seed(9);
            hb_roster a = seats(0);
            uint8_t fp[HB_ROSTER_MAX];
            bot_pool_matchmake(a, 4, party, 0, 0, 0, 2, fp);
            hb_roster b = a;
            int people[1] = { 1 };
            bot_pool_matchmake(b, 4, party, 0, 0, 100, 2, fp, people, 1);
            int same = 0;
            for (int i = 0; i < b.n; i++) for (int k = 0; k < a.n; k++) same += !_stricmp(b.bot[i].name, a.bot[k].name);
            CHECK(b.n == 6 && same == 6, "friend in, keep 100: %d bots, %d stayed", b.n, same);
            hb_roster c2 = b;
            bot_pool_matchmake(c2, 4, party, 0, 0, 100, 2, fp);
            same = 0;
            for (int i = 0; i < c2.n; i++) for (int k = 0; k < b.n; k++) same += !_stricmp(c2.bot[i].name, b.bot[k].name);
            CHECK(c2.n == 7 && same == 6, "friend out, keep 100: %d bots, %d stayed", c2.n, same);
        }
        printf("proving grounds: friends take bots' seats on their teams\n");
    }

    // 27. (Nov 23) the owner's skill ratings (skill_rating.h): bots start in their difficulty's range, a person at 1600;
    // a 4v4's wins, losses, the 150 gap, the kill bonus, quitting, a draw, the ranges and the floor, free for all, and
    // the file read back
    {
        wchar_t rf[MAX_PATH];
        swprintf_s(rf, L"%spg_ratings.txt", dir);
        DeleteFileW(rf);
        CHECK(!sr_open(dir), "no ratings file yet");
        for (int t = 0; t < HB_TIERS; t++) {
            sr_range g = sr_tier_range(t);
            CHECK(g.lo <= g.base && g.base <= g.hi, "tier %d: %d in %d-%d", t, g.base, g.lo, g.hi);
            for (int k = 0; k < 40; k++) {
                char nm[16];
                sprintf_s(nm, "R%d", k);
                int s = sr_bot(nm, t);
                CHECK(s >= g.lo && s <= g.hi && s == sr_bot(nm, t), "tier %d start %d", t, s);
            }
        }
        const int bases[HB_TIERS] = { 400, 600, 800, 1300, 1300, 1650, 1300, 950, 1600, 1700 };
        for (int t = 0; t < HB_TIERS; t++) CHECK(sr_tier_range(t).base == bases[t], "tier %d base %d", t, sr_tier_range(t).base);
        CHECK(sr_tier_range(HB_TIER_NOBLE).lo == 1600 && sr_tier_range(HB_TIER_NOBLE).hi == 1800 &&
              sr_tier_range(HB_TIER_DEMON).lo == 1550 && sr_tier_range(HB_TIER_DEMON).hi == 1800, "Noble and Demon ranges");
        CHECK(sr_person("Me") == 1600, "a person starts at 1600");

        // a close 4v4 the player's team wins: you and 3 Legendary bots vs 4 Legendary bots
        auto lobby = [](int you_kills) {
            std::vector<sr_player> pl;
            sr_player me; me.name = "Me"; me.team = 0; me.place = 1; me.kills = you_kills; pl.push_back(me);
            for (int i = 0; i < 7; i++) {
                sr_player b; b.name = "L" + std::to_string(i); b.bot = true; b.tier = 3; b.team = i < 3 ? 0 : 1;
                b.place = i < 3 ? 1 : 2; b.kills = 10; pl.push_back(b);
            }
            return pl;
        };
        std::vector<sr_player> pl = lobby(10);
        CHECK(sr_rate("m1", true, "Team Slayer", pl), "m1 rated");
        CHECK(pl[0].after - pl[0].before >= 35 && pl[0].after - pl[0].before <= 40, "close win: %+d", pl[0].after - pl[0].before);
        for (int i = 1; i < 8; i++) {
            sr_range g = sr_tier_range(3);
            int want = pl[i].team == 0 ? pl[i].before + 19 : pl[i].before - 19;
            want = want < g.lo ? g.lo : want > g.hi ? g.hi : want;
            CHECK(pl[i].after == want, "bot %d: %d -> %d", i, pl[i].before, pl[i].after);
        }
        CHECK(!sr_rate("m1", true, "Team Slayer", pl), "a match counts once");
        CHECK(sr_person("Me") == pl[0].after && sr_shown("me") == pl[0].after && !strcmp(sr_shown_match(), "m1"), "saved");

        // the kill bonus: in a win, up to +3 over the lobby's average (10 here)
        pl = lobby(40);
        int was = sr_person("Me");
        sr_rate("m2", true, "Team Slayer", pl);
        int got = pl[0].after - was;
        CHECK(got >= 38 && got <= 43, "a win with 40 kills: %+d", got);

        // the 150 gap: you (Me) and 3 Easy bots vs 4 Noble bots. The loss is -10 (they were 150+ higher); the bots on
        // your team lose 9, the Nobles win 9
        pl.clear();
        { sr_player me; me.name = "Me"; me.team = 0; me.place = 2; pl.push_back(me); }
        for (int i = 0; i < 7; i++) {
            sr_player b; b.name = "G" + std::to_string(i); b.bot = true; b.tier = i < 3 ? 0 : HB_TIER_NOBLE;
            b.team = i < 3 ? 0 : 1; b.place = i < 3 ? 2 : 1; pl.push_back(b);
        }
        sr_rate("m3", true, "Team Slayer", pl);
        CHECK(pl[0].after - pl[0].before == -10, "a loss to a much stronger team: %+d", pl[0].after - pl[0].before);
        for (int i = 1; i < 8; i++) {
            sr_range g = sr_tier_range(pl[i].tier);
            int want = pl[i].before + (i < 4 ? -9 : 9);
            want = want < g.lo ? g.lo : want > g.hi ? g.hi : want;
            CHECK(pl[i].after == want, "gap bot %d: %d -> %d (want %d)", i, pl[i].before, pl[i].after, want);
        }
        // the other way round: your team far stronger wins smaller (30-35), loses -15
        for (auto& p : pl) { p.place = p.team == 0 ? 1 : 2; p.tier = p.bot ? (p.team == 0 ? HB_TIER_NOBLE : 0) : -1; }
        sr_rate("m4", true, "Team Slayer", pl);
        CHECK(pl[0].after - pl[0].before >= 30 && pl[0].after - pl[0].before <= 35, "a win over a much weaker team: %+d", pl[0].after - pl[0].before);
        for (auto& p : pl) p.place = p.team == 0 ? 2 : 1;
        sr_rate("m5", true, "Team Slayer", pl);
        CHECK(pl[0].after - pl[0].before == -15 || pl[0].after == SR_PERSON_FLOOR, "a loss to a much weaker team: %+d", pl[0].after - pl[0].before);

        // a draw: nothing, but a person who quit +15 and a bot that quit a loss
        pl = lobby(10);
        for (auto& p : pl) p.place = 1;
        pl[0].completed = false;
        pl[5].completed = false;
        sr_rate("m6", true, "Team Slayer", pl);
        CHECK(pl[0].after - pl[0].before == 15, "you quit a draw: %+d", pl[0].after - pl[0].before);
        CHECK(pl[1].after == pl[1].before && pl[7].after == pl[7].before, "a draw changes nothing");
        CHECK(pl[5].after <= pl[5].before, "a bot that quit lost: %d -> %d", pl[5].before, pl[5].after);

        // the floor: 1500 (40 losses: the gap soon passes 150, so most moves are 9)
        for (int k = 0; k < 40; k++) {
            pl = lobby(0);
            for (auto& p : pl) p.place = p.team == 0 ? 2 : 1;
            char id[16]; sprintf_s(id, "f%d", k);
            sr_rate(id, true, "Team Slayer", pl);
        }
        CHECK(sr_person("Me") == SR_PERSON_FLOOR, "never under 1500: %d", sr_person("Me"));
        // the ranges: the losing Legendaries (your team) end at 1150, the winners at 1450, no further
        CHECK(sr_bot("L0", 3) == 1150 && sr_bot("L3", 3) == 1450, "ranges: %d %d", sr_bot("L0", 3), sr_bot("L3", 3));

        // Firefight: not rated
        pl = lobby(10);
        CHECK(!sr_rate("ff", true, "Firefight Arcade", pl), "Firefight not rated");

        // free for all, its own rating: 1st +40, 2nd +30, 3rd +20, the rest -15; the team ratings untouched
        int team_me = sr_person("Me");
        pl.clear();
        for (int i = 0; i < 6; i++) {
            sr_player p; p.name = i ? "F" + std::to_string(i) : "Me"; p.bot = i > 0; p.tier = HB_TIER_NOBLE; p.team = i;
            p.place = i + 1; pl.push_back(p);
        }
        sr_rate("ffa1", false, "Slayer", pl);
        CHECK(pl[0].before == 1600 && pl[0].after == 1640, "FFA 1st: %d -> %d", pl[0].before, pl[0].after);
        const int ffa_d[6] = { 40, 30, 20, -15, -15, -15 };
        for (int i = 1; i < 6; i++) {
            sr_range g = sr_tier_range(HB_TIER_NOBLE);
            int want = pl[i].before + ffa_d[i];
            want = want < g.lo ? g.lo : want > g.hi ? g.hi : want;
            CHECK(pl[i].after == want, "FFA place %d: %d -> %d", i + 1, pl[i].before, pl[i].after);
        }
        CHECK(sr_person("Me") == team_me && sr_person("Me", true) == 1640, "FFA kept apart: %d %d", sr_person("Me"), sr_person("Me", true));

        // read back from the file; a new difficulty starts in its new range
        int l0 = sr_bot("L0", 3);
        sr_open(L"C:\\");                                  // (another folder, then this one again: read from disk)
        sr_open(dir);
        CHECK(sr_bot("L0", 3) == l0 && sr_person("Me", true) == 1640 && !strcmp(sr_counted(), "ffa1"), "read back");
        CHECK(sr_bot("L0", 0) >= 300 && sr_bot("L0", 0) <= 500, "L0 as Easy: %d", sr_bot("L0", 0));
        sr_reset_person("Me");
        CHECK(sr_person("Me") == 1600 && sr_person("Me", true) == 1600, "reset");

        // (Nov 23) set by hand on the Psych Profile: 1500 to 2500, team and free for all apart
        sr_set_person("Me", 2140, false);
        sr_set_person("Me", 9000, true);
        CHECK(sr_person("Me") == 2140 && sr_person("Me", true) == SR_SET_MAX, "set by hand: %d %d", sr_person("Me"), sr_person("Me", true));
        sr_set_person("Me", 100, false);
        CHECK(sr_person("Me") == SR_PERSON_FLOOR, "set by hand, floor: %d", sr_person("Me"));
        sr_set_person("Me", 1600, false);
        // (Nov 23) the player's own gains: a close win 55-60, much weaker 50-55; a loss -22, to much stronger -17; a
        // friend keeps 35-40 / -15; the gains read back from the file
        sr_set_gains("Me", 60, 22);
        int wt, ls;
        sr_gains_of("Me", &wt, &ls);
        CHECK(wt == 60 && ls == 22, "gains %d %d", wt, ls);
        sr_gains_of("Pal", &wt, &ls);
        CHECK(wt == SR_WIN_TOP && ls == SR_LOSS, "a friend's gains %d %d", wt, ls);
        sr_set_gains("Pal", 5, 500);
        sr_gains_of("Pal", &wt, &ls);
        CHECK(wt == 15 && ls == 50, "gains kept 15-100 / 5-50: %d %d", wt, ls);
        auto duel = [](const char* id, bool me_wins) {
            std::vector<sr_player> pl;
            for (int i = 0; i < 2; i++) {
                sr_player p; p.name = i ? "Friend" : "Me"; p.team = i; p.place = (i == 0) == me_wins ? 1 : 2; pl.push_back(p);
            }
            sr_rate(id, true, "Slayer", pl);
            return pl;
        };
        std::vector<sr_player> d = duel("g1", true);
        CHECK(d[0].after - d[0].before >= 55 && d[0].after - d[0].before <= 60, "your close win with 60: %+d", d[0].after - d[0].before);
        CHECK(d[1].after - d[1].before == -15, "the friend's loss: %+d", d[1].after - d[1].before);
        d = duel("g2", false);
        CHECK(d[0].after - d[0].before == -22 && d[1].after - d[1].before >= 35 && d[1].after - d[1].before <= 40,
              "your loss with 22: %+d, the friend's win %+d", d[0].after - d[0].before, d[1].after - d[1].before);
        sr_set_person("Me", 1800, false);                  // (Me 1800, Friend about 1620: much stronger, 150+ apart)
        sr_set_person("Friend", 1600, false);
        d = duel("g3", true);
        CHECK(d[0].after - d[0].before >= 50 && d[0].after - d[0].before <= 55, "your win over a much weaker one: %+d", d[0].after - d[0].before);
        d = duel("g4", false);
        CHECK(d[0].after - d[0].before == -22, "your loss to a much weaker one: %+d", d[0].after - d[0].before);
        sr_set_person("Me", 1500, false);
        sr_set_person("Friend", 1900, false);
        d = duel("g5", false);
        CHECK(d[0].after - d[0].before == 0 && d[0].before == 1500, "-17 at the floor stays 1500: %d", d[0].after);
        sr_set_person("Me", 1600, false);
        d = duel("g6", false);
        CHECK(d[0].after - d[0].before == -17, "your loss to a much stronger one with 22: %+d", d[0].after - d[0].before);
        sr_open(L"C:\\");
        sr_open(dir);
        sr_gains_of("Me", &wt, &ls);
        CHECK(wt == 60 && ls == 22, "gains read back: %d %d", wt, ls);

        // the balancer counts ratings: a 4v4 with you (1600) dealt within SR_TIE of the most even split
        bot_pool_set_people_ratings(1600, nullptr, 0);
        int humans[HB_TEAMS_MAX] = { 1 };
        hb_roster b{}; b.teams = 2; b.n = 7;
        const int t4[7] = { HB_TIER_DEMON, 3, HB_TIER_BLIND, HB_TIER_TACTICIAN, 2, 1, 0 };
        for (int i = 0; i < 7; i++) { b.bot[i].tier = (uint8_t)t4[i]; b.bot[i].team = (uint8_t)(i < 3 ? 0 : 1); sprintf_s(b.bot[i].name, "F%d", i); }
        uint32_t rng = 5;
        roster_point_balance(b, humans, rng);
        CHECK(roster_on_team(b, 0) == 3, "4v4 sizes kept");
        CHECK(abs(roster_team_points(b, 0) - roster_team_points(b, 1)) <= 200, "4v4 by rating: %d vs %d",
              roster_team_points(b, 0), roster_team_points(b, 1));
        printf("ratings: red %d, blue %d; your rating 1600 counted on red\n", roster_team_points(b, 0), roster_team_points(b, 1));
        DeleteFileW(rf);
        sr_open(dir);
    }

    printf(fails ? "%d FAILED\n" : "all pool checks passed\n", fails);
    return fails ? 1 : 0;
}
