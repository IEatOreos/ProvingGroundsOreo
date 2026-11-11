// pool_test.cpp (custom, Nov 10): Bot Matchmaking's pool checks. Links the real bots_panel.cpp and drives the pool
// functions on a scratch folder. Build and run: native\build_pool_test.bat (needs Visual Studio's C++ tools, as build.bat).
// pool_test.exe <dir> make: makes <dir>'s bot_pool.txt as botcore does at MCC start (when it is missing).
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
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
    CHECK(r.bot[0].team == 0 && r.bot[1].team == 1 && r.bot[2].team == 0, "teams kept");
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

    printf(fails ? "%d FAILED\n" : "all pool checks passed\n", fails);
    return fails ? 1 : 0;
}
