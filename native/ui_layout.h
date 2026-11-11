// native/ui_layout.h: where MCC draws its menus at any window size, and where botcore's own UI goes beside them.
// Pure arithmetic (no ImGui, no D3D): overlay.cpp, bots_panel.cpp, panel_preview.cpp and native/tests/test_ui_layout.cpp
// all use it. Every size is in 1920x1080 units, measured from MCC screenshots (logs/tmp/ui_res, Nov 5) at 1920x1080,
// 1440x900 (16:10), 1920x540 (32:9) and 3440x1440 (21:9):
//   - the menu content (lobby tiles, pause tiles, screen titles) is a 1920x1080 page FITTED into the window and centred
//     both ways: scaled by height on wider screens (21:9, 32:9: pillarboxed), by width on narrower ones (16:10, 4:3:
//     letterboxed). 1440x900: START at x 732-908, y 164-282 = 976-1211, 158-316 at 0.75 plus 45 px.
//   - the header and footer (nameplate, the Back button row, the lobby's corner icons) sit in a frame no wider than
//     16:9, centred, the full window height, scaled by height from its corners. 1440x900: Back at y 821-853 = 95 px
//     from the bottom at 1080 times 0.833; its right edge 109 px in from the frame's right at 1080.
#pragma once

struct ui_rect { float x0, y0, x1, y1; };
struct ui_page { float x0, y0, w, h, s; };          // a 1920x1080-unit area on screen: origin, size in px, px per unit

inline float ui_min(float a, float b) { return a < b ? a : b; }
inline float ui_max(float a, float b) { return a > b ? a : b; }

// MCC's menu content: the 1920x1080 page fitted and centred. Its s is also the scale of our own windows (panel, report).
inline ui_page mcc_content(float W, float H) {
    float s = ui_min(W / 1920.0f, H / 1080.0f);
    return { (W - 1920.0f * s) * 0.5f, (H - 1080.0f * s) * 0.5f, 1920.0f * s, 1080.0f * s, s };
}
// MCC's header / footer frame: at most 16:9 wide, full height, scaled by height
inline ui_page mcc_frame(float W, float H) {
    float w = ui_min(W, H * 16.0f / 9.0f);
    return { (W - w) * 0.5f, 0.0f, w, H, H / 1080.0f };
}
inline ui_rect ui_at(const ui_page& p, float x0, float y0, float x1, float y1) {
    return { p.x0 + x0 * p.s, p.y0 + y0 * p.s, p.x0 + x1 * p.s, p.y0 + y1 * p.s };
}

// MCC's custom game lobby: the top row's tiles (map, game type, OPTIONS, START), the same in every title
inline ui_rect mcc_lobby_options(float W, float H) { return ui_at(mcc_content(W, H), 736, 158, 971, 316); }
inline ui_rect mcc_lobby_start(float W, float H) { return ui_at(mcc_content(W, H), 976, 158, 1211, 316); }
inline ui_rect mcc_lobby_tiles(float W, float H) { return ui_at(mcc_content(W, H), 96, 158, 1211, 330); }  // + bars
// the lobby probe (overlay.cpp probe_lobby): OPTIONS' and START's left frame lines, most of the tile height
inline float mcc_probe_x(float W, float H, int k, bool ff = false) {
    ui_page p = mcc_content(W, H); return p.x0 + (ff ? (k ? 1136 : 655) : (k ? 976 : 736)) * p.s;
}
inline ui_rect mcc_probe_rows(float W, float H) { return ui_at(mcc_content(W, H), 0, 164, 0, 308); }
// the Firefight lobby's title past where the post-game report's ends: "...CUSTOM FIREFIGHT" reaches it, "POSTGAME
// CARNAGE" (to ~686) does not (live Nov 6, 1920x1080 window: 482 of 5040 pixels letter-white in the lobby, 0 after)
inline ui_rect mcc_ff_title_probe(float W, float H) { return ui_at(mcc_content(W, H), 720, 72, 900, 100); }
// the BOTS tile: the next slot right of START, MCC's own gap (5) and START's size
inline ui_rect bots_tile_rect(float W, float H, bool ff = false) {
    return ff ? ui_at(mcc_content(W, H), 1376, 158, 1611, 316) : ui_at(mcc_content(W, H), 1216, 158, 1451, 316);
}
// Firefight's custom lobby (Reach, ODST: mission, game type, OPTIONS, difficulty, START): the same tiles one slot
// further right (the difficulty tile; measured live Nov 6 on the 3440x1440 buffer, Reach Custom Firefight frame lines:
// mission 95-410, game type 416-651, OPTIONS 655-891, difficulty 896-1131, START 1136-1370, y 158-314)
inline ui_rect mcc_ff_lobby_start(float W, float H) { return ui_at(mcc_content(W, H), 1136, 158, 1371, 316); }
inline ui_rect mcc_ff_lobby_tiles(float W, float H) { return ui_at(mcc_content(W, H), 95, 158, 1371, 330); }

// MCC's pause menu: the tile row (LEAVE, END GAME, SETTINGS, ...; room for six, 232 apart) and the Back button
inline ui_rect mcc_pause_tiles(float W, float H) { return ui_at(mcc_content(W, H), 96, 160, 1484, 363); }
inline ui_rect mcc_footer_back(float W, float H) {
    ui_page f = mcc_frame(W, H);
    return { f.x0 + 108 * f.s, H - 96 * f.s, f.x0 + 192 * f.s, H - 57 * f.s };
}
// the "Report bot bug" button in the pause menu: in MCC's footer row (Back's height and line), right-aligned on the
// frame's right margin (the nameplate's edge); at least 28 px high and as wide as its words need
inline ui_rect bug_button_rect(float W, float H, float text_w_px = 0) {
    ui_page f = mcc_frame(W, H);
    float h = ui_max(39 * f.s, 28.0f), w = ui_max(290 * f.s, text_w_px);
    float x1 = f.x0 + f.w - 109 * f.s, y1 = H - 57 * f.s;
    return { x1 - w, y1 - h, x1, y1 };
}

// (custom, Nov 11) MCC's lobby "MY GAME SESSION" list, top right, in the header frame (anchored to its right edge, scaled
// by height). Measured from the owner's lobby screenshot (Halo 4 custom game, ~2000x1115, Nov 11): the header bar
// 468-9 units in from the frame's right, y 29-66; the host's row (always the player, first) y 75-120 (its focus line
// under it to 127): his team's colour bar 362-350 in, the name box 344-11 in (its emblem 335-305, its clan tag from 289
// at +8, its name at +22); and an 8-player session's rows about 50 apart (checked by drawing these rects on the
// screenshot). Row k: 0 the player's (MCC's own), 1.. the bots the mod draws under it
inline ui_rect mcc_session_header(float W, float H) {
    ui_page f = mcc_frame(W, H);
    float r = f.x0 + f.w;
    return { r - 468 * f.s, 29 * f.s, r - 9 * f.s, 66 * f.s };
}
inline ui_rect mcc_session_row(float W, float H, int k) {      // the name box (x) and the row's height (y)
    ui_page f = mcc_frame(W, H);
    float r = f.x0 + f.w, y = (75 + 50 * k) * f.s;
    return { r - 344 * f.s, y, r - 11 * f.s, y + 45 * f.s };
}
inline float mcc_session_bar_x(float W, float H) {             // the team colour bar's left edge (12 units wide)
    ui_page f = mcc_frame(W, H);
    return f.x0 + f.w - 362 * f.s;
}

inline bool ui_inside(const ui_rect& r, float W, float H) { return r.x0 >= 0 && r.y0 >= 0 && r.x1 <= W && r.y1 <= H; }
inline bool ui_overlap(const ui_rect& a, const ui_rect& b) {
    return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1;
}
