// menu_route.cpp (custom, Nov 23): MCC walked to Halo: Reach's custom game lobby from wherever its menus are, behind
// Project Noble's screens.
//
// (Nov 23, later: the B and Up shorter, and skipped when MCC has not moved: to_top below)
// The owner, after his friend's mod: Project Noble opens from any menu with LB + RB (LT + RT at first), and "number 3 it right": when it
// needs Reach's custom game lobby (Start Matchmaking, Custom Game) and MCC is on another menu, it takes MCC there itself.
// His answers about MCC's main menu (Nov 23): B does nothing on it, and Up stops at its top item. So the route is:
//  - B, 8 times 0.9 s apart: back out of whatever menu MCC is on, to its main menu (B does nothing more there);
//  - Up on the left stick, 10 times 0.5 s apart: the main menu's top item (Up stops there);
//  - then the launcher's own recorded route after its title screen (E:\Proving Grounds\Project Noble, ppg_launch.ini
//    [route] steps, live OK Nov 19): Down, A, Down, Down, A until a game_variants folder opens, A, A until
//    MultiplayerCustomGame.gfx opens; with its timings (a 120 ms press, 1.5 s between presses, 6 s for a checkpoint,
//    0.7 s after one) never shortened (the owner, Nov 19: the mod may not load when Custom Games opens too fast);
//  - the lobby must be Halo: Reach's (overlay.cpp mcc_lobby_title 5).
// (Nov 23, the owner's recording, the launcher's boot.log: from MCC's main menu Down, Down, A, Down, A opened
// Theatre.gfx, Halo: Reach's Theater with its films) MR_THEATER: the same way out and up, then Down, Down, A, Down, A
// until Theatre.gfx opens, then MCC's Theatre screen running (theater.cpp), 1.5 s between presses as the launcher's.
// The presses go into MCC's own pad reads (overlay.cpp h_xinput_get: the pad MCC read first while the route ran), the
// player's own presses held back meanwhile; the checkpoints are the files MCC opens (overlay.cpp h_createfile).
#include <windows.h>
#include <stdio.h>
#include <wchar.h>
#include <string.h>
#include <xinput.h>
#include "proving_grounds.h"

void logf(const char* fmt, ...);
int mcc_lobby_title();

static volatile LONG g_state;                    // 0 idle, 1 running, 2 the lobby open, -1 stopped
static volatile LONG g_buttons, g_ly, g_seq;     // what MCC's pad reads see while the route presses
static HANDLE g_cp_ev;
static wchar_t g_cp[64];                         // the file the step waits for (lower case), or empty
static char g_why[160];

static void press(WORD buttons, SHORT ly) {
    InterlockedExchange(&g_buttons, buttons);
    InterlockedExchange(&g_ly, ly);
    InterlockedIncrement(&g_seq);
    Sleep(120);                                  // (the launcher's press_ms)
    InterlockedExchange(&g_buttons, 0);
    InterlockedExchange(&g_ly, 0);
    InterlockedIncrement(&g_seq);
}

static bool press_until(WORD buttons, SHORT ly, const wchar_t* cp) {
    wcscpy_s(g_cp, cp);
    ResetEvent(g_cp_ev);
    press(buttons, ly);
    bool ok = WaitForSingleObject(g_cp_ev, 6000) == WAIT_OBJECT_0;   // (the launcher's checkpoint_ms)
    g_cp[0] = 0;
    return ok;
}

static void stop(const char* why) {
    strcpy_s(g_why, why);
    logf("menu route: stopped: %s", why);
    InterlockedExchange(&g_state, -1);
}

static volatile LONG g_to;                       // MR_LOBBY or MR_THEATER
static volatile LONG g_at_top;                   // MCC known to be on its main menu's top item: no B and Up first

// (Nov 23, the owner: the walk to the Theater "takes quite a while": its B and Up came to 13 s of its 20) out to MCC's
// main menu and up to its top item: B 7 times 0.6 s apart (it does nothing on the main menu), Up 8 times 0.35 s apart
// (it stops at the top); none of it when the launcher opened Project Noble there and MCC has not moved since
static void to_top() {
    if (g_at_top) { logf("menu route: MCC is still on its main menu's top item (the launcher's): no B or Up"); return; }
    for (int i = 0; i < 7; i++) { press(XINPUT_GAMEPAD_B, 0); Sleep(600); }       // (out to the main menu)
    for (int i = 0; i < 8; i++) { press(0, 32767); Sleep(350); }                   // (its top item)
    Sleep(700);
}

static DWORD WINAPI route_thread(void*) {
    bool theater = g_to == MR_THEATER;
    logf("menu route: from MCC's menus to Halo: Reach's %s", theater ? "Theater" : "custom game lobby");
    to_top();
    if (theater) {                               // (the owner's recording, Nov 23: his own pace about 0.7 s a move)
        press(0, -32767); Sleep(800);                                              // Down
        press(0, -32767); Sleep(800);                                              // Down
        press(XINPUT_GAMEPAD_A, 0); Sleep(1500);                                   // A (its next menu comes in)
        press(0, -32767); Sleep(800);                                              // Down
        if (!press_until(XINPUT_GAMEPAD_A, 0, L"theatre.gfx")) { stop("MCC's Theater did not open"); return 0; }
        for (int i = 0; i < 60 && !pg_theater_live(); i++) Sleep(100);            // (its screen running)
        if (!pg_theater_live()) { stop("MCC's Theater screen was not seen"); return 0; }
        logf("menu route: Halo: Reach's Theater is open");
        g_why[0] = 0;
        InterlockedExchange(&g_state, 2);
        return 0;
    }
    press(0, -32767); Sleep(1500);                                                 // Down
    press(XINPUT_GAMEPAD_A, 0); Sleep(1500);                                       // A
    press(0, -32767); Sleep(1500);                                                 // Down
    press(0, -32767); Sleep(1500);                                                 // Down
    if (!press_until(XINPUT_GAMEPAD_A, 0, L"\\game_variants\\")) { stop("Custom Games did not open"); return 0; }
    Sleep(700);
    press(XINPUT_GAMEPAD_A, 0); Sleep(1500);                                       // A
    if (!press_until(XINPUT_GAMEPAD_A, 0, L"multiplayercustomgame.gfx")) { stop("the custom game lobby did not open"); return 0; }
    for (int i = 0; i < 60 && mcc_lobby_title() != 5; i++) Sleep(100);            // (its game named by its files)
    if (mcc_lobby_title() != 5) { stop("the lobby that opened is not Halo: Reach's"); return 0; }
    logf("menu route: Halo: Reach's custom game lobby is open");
    g_why[0] = 0;
    InterlockedExchange(&g_state, 2);
    return 0;
}

void menu_route_start(int to, bool at_top) {
    if (InterlockedExchange(&g_state, 1) == 1) return;   // (one at a time: already running)
    InterlockedExchange(&g_to, to);
    InterlockedExchange(&g_at_top, at_top ? 1 : 0);
    if (!g_cp_ev) g_cp_ev = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    g_why[0] = 0;
    HANDLE h = CreateThread(nullptr, 0, route_thread, nullptr, 0, nullptr);
    if (h) CloseHandle(h);
    else stop("the route could not start");
}

int menu_route_state() { return g_state; }
int menu_route_to() { return g_to; }
const char* menu_route_why() { return g_why; }

// (overlay.cpp h_createfile) a file MCC opens: the step's checkpoint when its path holds it
void menu_route_file(const wchar_t* path) {
    if (g_state != 1 || !g_cp[0] || !path) return;
    wchar_t l[512];
    size_t i = 0;
    for (; path[i] && i < 511; i++) l[i] = path[i] == L'/' ? L'\\' : (wchar_t)towlower(path[i]);
    l[i] = 0;
    if (wcsstr(l, g_cp)) SetEvent(g_cp_ev);
}

// (overlay.cpp h_xinput_get) while the route runs: what MCC's read of the pad sees (true), the player's own held back
bool menu_route_pad(XINPUT_STATE* st) {
    if (g_state != 1 || !st) return false;
    memset(&st->Gamepad, 0, sizeof st->Gamepad);
    st->Gamepad.wButtons = (WORD)g_buttons;
    st->Gamepad.sThumbLY = (SHORT)g_ly;
    st->dwPacketNumber = 0x60000000u + (DWORD)g_seq;   // (a state of its own each change)
    return true;
}
