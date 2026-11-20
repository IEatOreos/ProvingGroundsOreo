// proving_grounds_reach.inc (custom, Nov 19): Halo: Reach's own menus around Proving Grounds, phase 1. Included once by
// proving_grounds.cpp, after menu_screen: it draws with that file's helpers (P, text, item, prompt, painted_background,
// the roster) and keeps its own settings in native\bin\reach_menus.ini.
//
// The owner sent seven frames of Reach's menus: "Starting here. This is the main menu. And the matchmaking menus all
// phase 1". Proving Grounds' S_MENU now shows Reach's pages (g_rpage):
//  - RP_TITLE: the title screen, on the first open of a session (the launcher's route lands here): the title spaced
//    wide over the painting, START SOLO CAMPAIGN (not in Proving Grounds yet) and MAIN MENU;
//  - RP_MAIN: MAIN MENU: CAMPAIGN, MATCHMAKING, FIREFIGHT, CUSTOM GAME, FORGE, THEATER, a line on each, MY PARTY at
//    the right. MATCHMAKING opens RP_MM; CUSTOM GAME leaves for MCC's own Halo: Reach custom game lobby (it is under
//    these screens); the rest are not in Proving Grounds yet (they say so);
//  - RP_MM: MATCHMAKING: the playlist's banner, PLAYLIST, SEARCH RESTRICTIONS, PSYCH PROFILE, START MATCHMAKING (the
//    search, the vote, the game: Proving Grounds as before), MY PARTY;
//  - RP_PLAYLIST: Reach's categories and playlists in two columns, the picked one's picture, words and numbers, the
//    player's band. Proving Grounds plays THE ARENA (4v4) and BIG TEAM BATTLE (8v8); the rest of Reach's list is shown,
//    marked as not here yet;
//  - RP_RESTRICT / RP_PSYCH: SEARCH RESTRICTIONS (three ticks) and PSYCH PROFILE (four choices), saved; the search does
//    not use them yet (each page says so);
//  - RP_OPTIONS: Proving Grounds' own menu as before (invite, challenges, commendations, simulate matches, game size),
//    opened with the Menu prompt (the pad's Start, M on the keys) from the title, the main menu or matchmaking.
// Our own drawing and words throughout: no Bungie or 343 art, logos or icons. The paintings behind the title, the main
// menu and matchmaking are this PC's own (native\bin\pg_backgrounds: title, main_menu, matchmaking_lobby, else the
// menu and matchmaking ones already there); the sub-pages draw their own dark steel-blue ground.

// ------------------------------------------------------------------ settings (native\bin\reach_menus.ini)
static int g_rm_restrict[3];                     // good connection, language, skill (0 / 1)
// g_rm_psych[4] (proving_grounds.cpp): chattiness, motivation, teamwork, tone (0 no preference, 1, 2)
static bool g_rm_loaded;
static int g_rm_col, g_rm_cat = 1;               // the playlist page: the column with the focus, the category picked

static void rm_ini(wchar_t* out) { swprintf_s(out, MAX_PATH, L"%s\\reach_menus.ini", g_bin); }
static const wchar_t* RM_RKEY[3] = { L"good_connection", L"language", L"skill" };
static const wchar_t* RM_PKEY[4] = { L"chattiness", L"motivation", L"teamwork", L"tone" };
static void rm_load() {
    if (g_rm_loaded) return;
    g_rm_loaded = true;
    wchar_t p[MAX_PATH];
    rm_ini(p);
    for (int i = 0; i < 3; i++) g_rm_restrict[i] = GetPrivateProfileIntW(L"search_restrictions", RM_RKEY[i], 0, p) ? 1 : 0;
    for (int i = 0; i < 4; i++) {
        int v = GetPrivateProfileIntW(L"psych_profile", RM_PKEY[i], 0, p);
        g_rm_psych[i] = v < 0 || v > 2 ? 0 : v;
    }
}
static void rm_save() {
    wchar_t p[MAX_PATH], v[8];
    rm_ini(p);
    for (int i = 0; i < 3; i++) { swprintf_s(v, L"%d", g_rm_restrict[i]); WritePrivateProfileStringW(L"search_restrictions", RM_RKEY[i], v, p); }
    for (int i = 0; i < 4; i++) { swprintf_s(v, L"%d", g_rm_psych[i]); WritePrivateProfileStringW(L"psych_profile", RM_PKEY[i], v, p); }
}

// ------------------------------------------------------------------ the playlists, as Reach lists them
// pl: Proving Grounds' playlist (g_pl index) when it plays it, -1 when not yet. Our own words for each.
struct rm_pl { int cat; const char* name; int pl; const char* blurb; };
static const char* RM_CAT[5] = { "STANDARD", "EVOLVED", "ANNIVERSARY", "COMMUNITY", "COOPERATIVE" };
static const char* RM_CAT_BLURB[5] = {
    "The core of matchmaking: Slayer and objective games for squads of every skill.",
    "Bigger teams, more teams, smaller teams and the competitive Arena.",
    "Halo: Combat Evolved's battlefields, remade for Reach.",
    "Playlists built from the community's own maps and games.",
    "Firefight and the campaign, with your squad." };
static const rm_pl RM_PL[] = {
    { 0, "TEAM SLAYER", -1, "Two teams, one goal: more kills than the other side." },
    { 0, "TEAM SWAT", -1, "Team Slayer with precision weapons, no shields and no motion tracker." },
    { 0, "TEAM SNIPERS", -1, "Team Slayer with sniper rifles from the start." },
    { 0, "LIVING DEAD", -1, "Infection: the survivors hold out as the dead spread." },
    { 0, "INVASION", -1, "Spartans against Elites, six on six, phase by phase." },
    { 1, "SUPER SLAYER", -1, "Slayer with every power-up and every big weapon in play." },
    { 1, "TEAM OBJECTIVE", -1, "Flags, bombs, territories and hills: objective games only." },
    { 1, "RUMBLE PIT", -1, "Every player for themselves." },
    { 1, "DOUBLE TEAM", -1, "Two on two." },
    { 1, "BIG TEAM BATTLE", 1, nullptr },
    { 1, "MULTI TEAM", -1, "Four teams of three, Slayer and objective games." },
    { 1, "THE ARENA", 0, nullptr } };
static const int RM_NPL = (int)(sizeof RM_PL / sizeof RM_PL[0]);

static int rm_lists(int cat, int* out) {         // the playlists of a category, as RM_PL indexes
    int n = 0;
    for (int i = 0; i < RM_NPL; i++) if (RM_PL[i].cat == cat) out[n++] = i;
    return n;
}
static int rm_current() {                        // the RM_PL entry Proving Grounds is set to
    for (int i = 0; i < RM_NPL; i++) if (RM_PL[i].pl == (g_size >= 8 ? 1 : 0)) return i;
    return 0;
}

// ------------------------------------------------------------------ drawing
// text spaced wide, centred on x (align 1) or from x (0)
static float rm_spaced_w(float size, const char* s, float sp) {
    float w = 0;
    for (const char* c = s; *c; c++) {
        char one[2] = { *c, 0 };
        w += g_fl->CalcTextSizeA(U(size), 1e9f, 0, one).x / g_pg.s + (c[1] ? sp : 0);
    }
    return w;
}
static void rm_spaced(float size, float x, float y, ImU32 c, const char* s, float sp, int align) {
    if (align == 1) x -= rm_spaced_w(size, s, sp) * 0.5f;
    for (const char* ch = s; *ch; ch++) {
        char one[2] = { *ch, 0 };
        g_dl->AddText(g_fl, U(size), P(x + 2, y + 3), A(IM_COL32(0, 0, 0, (c >> 24) / 2)), one);
        g_dl->AddText(g_fl, U(size), P(x, y), A(c), one);
        x += g_fl->CalcTextSizeA(U(size), 1e9f, 0, one).x / g_pg.s + sp;
    }
}
// Reach's breadcrumb: the page it came from, upright along the left, reading downward (x: the letters' right edge)
static void rm_vtext(float size, float x, float y, ImU32 c, const char* s) {
    int i0 = g_dl->VtxBuffer.Size;
    ImVec2 p = P(x, y);
    g_dl->AddText(g_fl, U(size), p, A(c), s);
    for (int i = i0; i < g_dl->VtxBuffer.Size; i++) {   // (each vertex turned a quarter clockwise about p)
        ImVec2& v = g_dl->VtxBuffer[i].pos;
        float dx = v.x - p.x, dy = v.y - p.y;
        v = ImVec2(p.x - dy, p.y + dx);
    }
}
// words wrapped to a width
static void rm_wrap(ImFont* f, float size, float x, float y, float w, ImU32 c, const char* s) {
    g_dl->AddText(f, U(size), P(x + 1, y + 1), A(IM_COL32(0, 0, 0, 140)), s, nullptr, U(w));
    g_dl->AddText(f, U(size), P(x, y), A(c), s, nullptr, U(w));
}
// our own marks for the headers (no game art): a winged chevron (the main menu, matchmaking), four diamonds (the
// sub-pages)
static void rm_wings(float cx, float cy, float s, ImU32 c) {
    ImVec2 v[3] = { P(cx - 0.42f * s, cy - 0.30f * s), P(cx, cy + 0.12f * s), P(cx + 0.42f * s, cy - 0.30f * s) };
    g_dl->AddPolyline(v, 3, A(c), 0, U(0.13f * s));
    ImVec2 w[3] = { P(cx - 0.30f * s, cy + 0.10f * s), P(cx, cy + 0.38f * s), P(cx + 0.30f * s, cy + 0.10f * s) };
    g_dl->AddPolyline(w, 3, A(c), 0, U(0.09f * s));
    for (int k = -1; k <= 1; k += 2) {               // the wings: three feathers each, out and up
        for (int f = 0; f < 3; f++) {
            float x0 = cx + k * (0.18f + 0.05f * f) * s, y0 = cy - (0.34f + 0.06f * f) * s;
            g_dl->AddLine(P(x0, y0), P(x0 + k * (0.30f - 0.06f * f) * s, y0 - (0.18f - 0.04f * f) * s), A(c), U(0.05f * s));
        }
    }
}
static void rm_diamond(float cx, float cy, float r, ImU32 c, float thick) {
    ImVec2 q[4] = { P(cx, cy - r), P(cx + r, cy), P(cx, cy + r), P(cx - r, cy) };
    g_dl->AddPolyline(q, 4, A(c), ImDrawFlags_Closed, U(thick));
}
static void rm_diamonds(float cx, float cy, float s, ImU32 c) {
    float r = s * 0.2f, d = s * 0.22f;
    rm_diamond(cx, cy - d, r, c, 2.2f); rm_diamond(cx + d, cy, r, c, 2.2f);
    rm_diamond(cx, cy + d, r, c, 2.2f); rm_diamond(cx - d, cy, r, c, 2.2f);
    rm_diamond(cx, cy, s * 0.5f, IM_COL32(150, 190, 230, 120), 1.2f);
}

// the sub-pages' ground: a deep steel blue, a soft light across, a faint lattice of diamonds by the title
static void rm_ground(float t) {
    ImVec2 d = ImGui::GetIO().DisplaySize;
    g_dl->AddRectFilledMultiColor(ImVec2(0, 0), d, IM_COL32(20, 38, 50, 255), IM_COL32(14, 30, 42, 255),
                                  IM_COL32(5, 10, 15, 255), IM_COL32(8, 15, 21, 255));
    float sw = 0.5f + 0.5f * sinf(t * 0.07f), mid = d.x * (0.55f + 0.1f * sw);   // (a soft light: up, then down)
    g_dl->AddRectFilledMultiColor(ImVec2(mid - d.x * 0.22f, 0), ImVec2(mid, d.y), IM_COL32(120, 170, 200, 0),
                                  IM_COL32(120, 170, 200, 16), IM_COL32(120, 170, 200, 6), IM_COL32(120, 170, 200, 0));
    g_dl->AddRectFilledMultiColor(ImVec2(mid, 0), ImVec2(mid + d.x * 0.22f, d.y), IM_COL32(120, 170, 200, 16),
                                  IM_COL32(120, 170, 200, 0), IM_COL32(120, 170, 200, 0), IM_COL32(120, 170, 200, 6));
    for (int gy = 0; gy < 9; gy++)                   // (the lattice: brightest by the title, fading out)
        for (int gx = 0; gx < 16; gx++) {
            float x = 120 + gx * 26.0f + (gy & 1) * 13.0f, y = 30 + gy * 13.0f;
            float dist = sqrtf((x - 330) * (x - 330) + (y - 90) * (y - 90));
            int a = (int)(60 - dist * 0.22f);
            if (a > 4) rm_diamond(x, y, 5, IM_COL32(150, 190, 220, a), 1.0f);
        }
    g_dl->AddRectFilledMultiColor(ImVec2(0, d.y * 0.75f), d, IM_COL32(0, 0, 0, 0), IM_COL32(0, 0, 0, 0),
                                  IM_COL32(0, 0, 0, 120), IM_COL32(0, 0, 0, 120));
}

static const pic* rm_picture(const wchar_t* name) {
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\pg_backgrounds\\%s.png", g_bin, name);
    if (const pic* q = picture(p)) return q;
    swprintf_s(p, L"%s\\pg_backgrounds\\%s.jpg", g_bin, name);
    return picture(p);
}

// the frame's ground for Reach's pages (false: not one of them, Proving Grounds' own ground then)
static bool rmenu_background(float t) {
    if (g_rpage == RP_OPTIONS) return false;
    const pic* art = nullptr;
    if (g_rpage == RP_TITLE) { art = rm_picture(L"title"); if (!art) art = bg_picture(BG_MENU); }
    else if (g_rpage == RP_MAIN) { art = rm_picture(L"main_menu"); if (!art) art = bg_picture(BG_MATCH); }
    else if (g_rpage == RP_MM) { art = rm_picture(L"matchmaking_lobby"); if (!art) art = bg_picture(BG_MATCH); }
    if (art) painted_background(t, art);
    else rm_ground(t);
    return true;
}
static bool rmenu_party() { return g_rpage == RP_MAIN || g_rpage == RP_MM || g_rpage == RP_OPTIONS; }

// a list row as Reach's: the label (and a value at its right), Reach's band on the focused one; a row not in Proving
// Grounds yet stays dim
static void rm_row(float x0, float y0, float x1, float y1, bool focus, const char* label, bool on = true,
                   const char* value = nullptr) {
    if (focus) focus_band(x0, y0, x1, y1);
    float h = y1 - y0, fs = h * 0.66f;
    ImU32 c = !on ? IM_COL32(150, 156, 162, focus ? 200 : 120) : focus ? C_TEXT : C_DIM;
    text(g_fl, fs, x0 + 10, y0 + (h - fs * 1.2f) * 0.5f + 1, c, label);
    if (value) text(g_fl, fs * 0.9f, x1 - 10, y0 + (h - fs * 1.08f) * 0.5f + 1, focus ? C_TEXT : C_DIM, value, 2);
}

// MAIN MENU's and MATCHMAKING's header: our mark, the title, the line under it; the page it came from, upright
static void rm_big_header(const char* title, const char* sub, const char* crumb) {
    g_dl->AddRectFilled(P(140, 334), P(236, 414), A(IM_COL32(30, 34, 38, 120)));
    rm_wings(188, 380, 92, IM_COL32(222, 226, 230, 235));
    text(g_fl, 72, 254, 334, C_TEXT, title);
    if (sub) text(g_fl, 26, 256, 440, C_DIM, sub);
    if (crumb) rm_vtext(46, 212, 432, IM_COL32(200, 206, 212, 70), crumb);
}
// the sub-pages': four diamonds, the title; the page it came from upright under the diamonds
static void rm_small_header(const char* title, const char* crumb) {
    rm_diamonds(350, 98, 64, IM_COL32(120, 176, 230, 255));
    text(g_fl, 58, 394, 70, C_TEXT, title);
    char cut[96];                                    // (a long one ends above the player's band: cut to what fits)
    strcpy_s(cut, crumb);
    for (size_t n = strlen(cut); n > 0 && text_w(g_fl, 52, cut) / g_pg.s > 660; ) cut[--n] = 0;
    rm_vtext(52, 372, 148, IM_COL32(200, 206, 212, 64), cut);
}

// the button prompts along the bottom of the main pages; true when Menu was asked for (the pad's Start, M, a click)
static bool rm_prompts(float x, float y, bool select, bool back, bool menu) {
    g_dl->AddLine(P(180, y - 30), P(1740, y - 30), A(IM_COL32(206, 212, 218, 70)), U(1));
    bool menu_click = false;
    if (select) x = prompt(x, y, "A", "Enter", "Select", nullptr);
    if (back) x = prompt(x, y, "B", "Esc", "Back", &g_footer_back);
    if (menu) prompt(x, y, "Start", "M", "Menu", &menu_click);
    return menu && !g_inert &&
           (menu_click || ImGui::IsKeyPressed(ImGuiKey_GamepadStart, false) || ImGui::IsKeyPressed(ImGuiKey_M, false));
}
// (phase 2) the Menu prompt opens Reach's Start menu (RP_MENU); Exit (Start again) or B goes back where it was opened
static int g_rmenu_from = RP_MAIN;
static void rm_open_options() {
    g_rmenu_from = g_rpage;
    g_rpage = RP_MENU;
    g_focus_after = 0;
    sound(PS_SELECT);
}

// MY PARTY at the right, as the menu's (session_panel), its header naming the page's lobby
static void rm_party(pg_env& e, const char* where_caps, const char* where) {
    const hb_roster& r = *e.roster;
    uint64_t ids[PG_PEOPLE];
    char names[PG_PEOPLE][32];
    int teams[PG_PEOPLE], np = mcc_session_people(ids, names, teams, PG_PEOPLE);
    std::vector<ros_row> rows;
    rows.push_back({ RK_ME, me_name(), "", -1, -1, false, 1, 0, 0 });
    for (int k = 0; k < np; k++) rows.push_back({ RK_PERSON, names[k], "", -1, -1, false, 1, ids[k], k ? 0.0f : 5.0f });
    for (int i = 0; i < g_nparty; i++) {
        int tier = 3;
        for (int k = 0; k < r.n; k++) if (!_stricmp(r.bot[k].name, g_party[i])) tier = r.bot[k].tier;
        int tt, st;
        if (bot_pool_saved_of(g_party[i], &tt, &st)) tier = tt;
        rows.push_back({ RK_BOT, g_party[i], profile_clan_of(g_party[i]), -1, tier, true, 1, 0, (np || i) ? 0.0f : 5.0f });
    }
    char cnt[16], now[8], max[8];
    sprintf_s(cnt, "%d/%d", g_nparty + 1 + np, 16);
    sprintf_s(now, "%d", g_nparty + 1 + np);
    sprintf_s(max, "%d", 16);
    ros_head h = { where_caps, cnt, where, cnt, "MY PARTY", "MY PARTY DETAILS",
                   { me_name(), cur_pl().title, now, max, "Proving Grounds" } };
    roster(e, rows, h, 1830, 34, 82, 0, nullptr);
}

// the player's band along the bottom of the sub-pages, as Reach's: emblem, rank insignia, name, rank, credits, next.
// The Armory's pages show the credits left to spend instead (spend >= 0), the rank still the credits earned
static void rm_band(int spend = -1) {
    const float x0 = 318, x1 = 1530, y0 = 842, y1 = 956;
    comm_load();
    g_dl->AddRectFilledMultiColor(P(x0 + 120, y0), P(x1, y1), A(IM_COL32(44, 50, 56, 215)), A(IM_COL32(24, 28, 32, 170)),
                                  A(IM_COL32(24, 28, 32, 170)), A(IM_COL32(44, 50, 56, 215)));
    g_dl->AddLine(P(x0 + 120, y0), P(x1, y0 - 12), A(IM_COL32(214, 220, 226, 110)), U(1.2f));
    int32_t emb[5];
    int np = -1;
    unsigned long long em = g_make && mcc_player_look(emb, &np) ? player_emblem(emb, g_make) : 0;
    if (em) g_dl->AddImage((ImTextureID)em, P(x0 + 4, y0 + 8), P(x0 + 112, y0 + 116), ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
    else crest(x0 + 58, y0 + 62, 46, C_TEXT);
    const char* who = g_comm_who.empty() ? me_name() : g_comm_who.c_str();
    if (const pic* rp = sr_rank_picture(sr_rank_of(who, false))) image_fit(rp, x0 + 144, y0 + 12, x0 + 214, y0 + 66);
    text(g_fl, 44, x0 + 226, y0 + 6, C_TEXT, who);
    g_dl->AddRectFilled(P(x0 + 136, y0 + 72), P(x0 + 560, y0 + 108), A(IM_COL32(255, 255, 255, 24)));
    text(g_fl, 26, x0 + 144, y0 + 75, C_DIM, g_comm_rank.empty() ? "Rank not recorded yet" : g_comm_rank.c_str());
    std::string crs = cr_text(spend >= 0 ? spend : g_comm_cr) + " cR";
    text(g_fl, 40, x1 - 14, y0 + 2, C_TEXT, crs.c_str(), 2);
    if (spend >= 0) text(g_fl, 23, x1 - 14, y0 + 62, C_DIM, ("To spend \xC2\xB7 earned " + cr_text(g_comm_cr) + " cR").c_str(), 2);
    else if (!g_comm_next.empty()) text(g_fl, 23, x1 - 14, y0 + 62, C_DIM, ("Next: " + g_comm_next).c_str(), 2);
}

// ------------------------------------------------------------------ the pages
static const char* g_rm_version_text() {
    static char v[48];
    if (!v[0]) {
        strcpy_s(v, " ");
        wchar_t p[MAX_PATH];
        swprintf_s(p, L"%s\\CUSTOM_VERSION", g_root);
        FILE* f = nullptr;
        if (!_wfopen_s(&f, p, L"rb") && f) {
            char line[40] = {};
            if (fgets(line, sizeof line, f)) { line[strcspn(line, "\r\n")] = 0; strcpy_s(v, line); }
            fclose(f);
        }
    }
    return v;
}

static void rm_title(pg_env& e, float t) {
    (void)e;
    float in = t < 1.2f ? t / 1.2f : 1;              // (the title fades up as Reach's did)
    float keep = g_alpha;
    g_alpha *= in;
    g_dl->AddRectFilledMultiColor(P(0, 572), P(960, 600), A(IM_COL32(230, 236, 240, 0)), A(IM_COL32(230, 236, 240, 60)),
                                  A(IM_COL32(230, 236, 240, 0)), A(IM_COL32(230, 236, 240, 0)));
    g_dl->AddRectFilledMultiColor(P(960, 572), P(1920, 600), A(IM_COL32(230, 236, 240, 60)), A(IM_COL32(230, 236, 240, 0)),
                                  A(IM_COL32(230, 236, 240, 0)), A(IM_COL32(230, 236, 240, 0)));
    rm_spaced(30, 960, 446, IM_COL32(214, 220, 226, 200), "PROJECT", 22, 1);
    rm_spaced(104, 960, 476, IM_COL32(236, 240, 244, 235), "PROVING GROUNDS", 30, 1);
    g_alpha = keep;
    int base = (int)g_items.size();
    bool f0 = item(160, 800, 640, 838), f1 = item(160, 842, 640, 880);
    rm_row(160, 800, 640, 838, f0, "START SOLO CAMPAIGN", false);
    rm_row(160, 842, 640, 880, f1, "MAIN MENU");
    if (f0) text(g_fs, 22, 170, 890, IM_COL32(200, 206, 212, 220), "The campaign is not in Proving Grounds yet.");
    text(g_fl, 22, 1760, 900, IM_COL32(214, 220, 226, 150), "PROJECT PROVING GROUNDS", 2);
    text(g_fs, 18, 1760, 928, IM_COL32(214, 220, 226, 110), g_rm_version_text(), 2);
    if (rm_prompts(176, 966, false, false, true)) rm_open_options();
    if (pressed(base + 0)) sound(PS_ERROR);
    if (pressed(base + 1)) { g_rpage = RP_MAIN; g_focus_after = 1; sound(PS_SELECT); }
}

static const char* RM_MAIN_ITEMS[6] = { "CAMPAIGN", "MATCHMAKING", "FIREFIGHT", "CUSTOM GAME", "FORGE", "THEATER" };
static const char* RM_MAIN_DESC[6] = {
    "The campaign is not in Proving Grounds yet: play it from MCC's own menus.",
    "Take your party into matchmaking: Proving Grounds' playlists, a lobby of bots and the vote.",
    "Firefight is not in Proving Grounds yet: play it from MCC's own menus.",
    "Leave for MCC's own Halo: Reach custom game lobby: your own map, game type and bots (BOTS).",
    "Forge is not in Proving Grounds yet: play it from MCC's own menus.",
    "Theater is not in Proving Grounds yet: watch your films from MCC's own menus." };
static const bool RM_MAIN_ON[6] = { false, true, false, true, false, false };

static void rm_main(pg_env& e, float t) {
    (void)t;
    if (ros_up()) { rm_party(e, "IN MAIN MENU LOBBY", "In Main Menu Lobby"); return; }
    rm_big_header("MAIN MENU", "This party is offline: you and the bots you invite.", nullptr);
    g_dl->AddLine(P(248, 572), P(940, 572), A(IM_COL32(206, 212, 218, 60)), U(1));
    int base = (int)g_items.size(), focus = -1;
    for (int k = 0; k < 6; k++) {
        float y = 578 + 41.0f * k;
        bool f = item(248, y, 940, y + 38);
        if (f) focus = k;
        rm_row(248, y, 940, y + 38, f, RM_MAIN_ITEMS[k], RM_MAIN_ON[k]);
    }
    g_dl->AddLine(P(248, 828), P(940, 828), A(IM_COL32(206, 212, 218, 60)), U(1));
    if (focus >= 0) rm_wrap(g_fl, 26, 256, 842, 600, IM_COL32(222, 226, 230, 255), RM_MAIN_DESC[focus]);
    rm_party(e, "IN MAIN MENU LOBBY", "In Main Menu Lobby");
    if (rm_prompts(256, 966, true, true, true)) rm_open_options();
    for (int k = 0; k < 6; k++) {
        if (!pressed(base + k)) continue;
        if (!RM_MAIN_ON[k]) { sound(PS_ERROR); continue; }
        if (k == 1) { g_rpage = RP_MM; g_focus_after = 4; sound(PS_SELECT); }   // (on START MATCHMAKING)
        if (k == 3) { sound(PS_SELECT); g_stage = S_OFF; logf("proving grounds: closed for MCC's custom game lobby (main menu)"); }
    }
}

static void rm_restrict_summary(char* out, int cap) {
    out[0] = 0;
    const char* N[3] = { "GOOD CONNECTION", "LANGUAGE", "SKILL" };
    for (int i = 0; i < 3; i++)
        if (g_rm_restrict[i]) { if (out[0]) strcat_s(out, cap, ", "); strcat_s(out, cap, N[i]); }
    if (!out[0]) strcpy_s(out, cap, "NONE (FASTEST)");
}

static void rm_mm(pg_env& e, float t) {
    if (ros_up()) { rm_party(e, "IN MATCHMAKING LOBBY", "In Matchmaking Lobby"); return; }
    rm_load();
    // the banner: the playlist's maps in turn, the pool's count and the team size along its foot
    panel(243, 66, 940, 322, IM_COL32(18, 20, 23, 200));
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    library();
    playlist_pool(cur_pl(), gts, maps);
    if (!maps.empty()) {
        const pic* p = map_picture(maps[(int)(t / 6) % maps.size()]->key);
        if (p) image(p, 245, 68, 938, 320, 0.95f);
    }
    g_dl->AddRectFilledMultiColor(P(245, 230), P(938, 320), A(IM_COL32(8, 10, 12, 0)), A(IM_COL32(8, 10, 12, 0)),
                                  A(IM_COL32(8, 10, 12, 220)), A(IM_COL32(8, 10, 12, 220)));
    char a[48], b[48];
    sprintf_s(a, "%d Bots in Your Pool", g_pool_count);
    sprintf_s(b, "%s: %dv%d", cur_pl().title, cur_pl().size, cur_pl().size);
    text(g_fl, 30, 258, 270, C_TEXT, a);
    text(g_fl, 30, 926, 276, C_TEXT, b, 2);
    rm_big_header("MATCHMAKING", "This party is offline: you and the bots you invite.", "MAIN MENU");
    text(g_fl, 27, 256, 566, C_TEXT, "Ready");
    g_dl->AddLine(P(248, 606), P(940, 606), A(IM_COL32(206, 212, 218, 60)), U(1));
    char rs[64];
    rm_restrict_summary(rs, sizeof rs);
    // (Nov 19, the owner: "the commendations tab ... between Psych profile and start mathcmaking")
    comm_load();
    char cms[32];
    sprintf_s(cms, "%.1f%%", g_comm_pct);
    const char* L[5] = { "PLAYLIST", "SEARCH RESTRICTIONS", "PSYCH PROFILE", "COMMENDATIONS", "START MATCHMAKING" };
    const char* V[5] = { RM_PL[rm_current()].name, rs, nullptr, g_comm_have && !g_comm_items.empty() ? cms : nullptr, nullptr };
    const char* D[5] = { "Pick a playlist that suits the way you play.",
                         "Choose what the search puts first.",
                         "Tell the search what kind of players you want around you. Simulated matches and invites are here too.",
                         "Your commendations, tiers and progress, as your Service Record has them.",
                         "Find a game: a lobby of bots from your pool, then the vote." };
    int base = (int)g_items.size(), focus = -1;
    for (int k = 0; k < 5; k++) {
        float y = 612 + 41.0f * k;
        bool f = item(248, y, 940, y + 38);
        if (f) focus = k;
        rm_row(248, y, 940, y + 38, f, L[k], true, V[k]);
    }
    g_dl->AddLine(P(248, 828), P(940, 828), A(IM_COL32(206, 212, 218, 60)), U(1));
    if (focus >= 0) rm_wrap(g_fl, 26, 256, 842, 600, IM_COL32(222, 226, 230, 255), D[focus]);
    rm_party(e, "IN MATCHMAKING LOBBY", "In Matchmaking Lobby");
    if (rm_prompts(256, 966, true, true, true)) rm_open_options();
    if (pressed(base + 0)) {
        g_rpage = RP_PLAYLIST; g_rm_col = 0; g_rm_cat = RM_PL[rm_current()].cat; g_focus_after = g_rm_cat; sound(PS_SELECT);
    }
    if (pressed(base + 1)) { g_rpage = RP_RESTRICT; g_focus_after = 0; sound(PS_SELECT); }
    if (pressed(base + 2)) { g_rpage = RP_PSYCH; g_focus_after = 0; sound(PS_SELECT); }
    if (pressed(base + 3)) { g_comm = true; g_comm_check = 0; g_comm_tab = 0; g_comm_scroll = 0; g_focus = 0; sound(PS_SELECT); }
    if (pressed(base + 4)) { sound(PS_SELECT); start_search(e); }
}

static void rm_playlist(pg_env& e, float t) {
    (void)e;
    rm_small_header("PLAYLIST", "MATCHMAKING");
    int lists[16], cur = rm_current();
    int base = (int)g_items.size();
    int show_cat = g_rm_col == 0 ? -1 : g_rm_cat;    // (the categories' column: the focused one decides what shows)
    // the categories
    for (int c = 0; c < 5; c++) {
        float y = 145 + 41.0f * c;
        bool f = g_rm_col == 0 && item(390, y, 770, y + 38);
        if (f) show_cat = c;
        if (g_rm_col == 1 && c == g_rm_cat) {        // (picked, the focus in the playlists: a quieter band)
            g_dl->AddRectFilled(P(390, y), P(770, y + 38), A(IM_COL32(196, 202, 208, 40)));
            g_dl->AddRectFilled(P(390, y), P(393, y + 38), A(C_LIT));
        }
        ImU32 col = g_rm_col == 1 ? (c == g_rm_cat ? C_TEXT : IM_COL32(176, 182, 188, 90)) : 0;
        if (g_rm_col == 0) rm_row(390, y, 770, y + 38, f, RM_CAT[c]);
        else text(g_fl, 25, 400, y + 5, col, RM_CAT[c]);
        if (f && rm_lists(c, lists)) text(g_fl, 28, 750, y + 3, C_TEXT, ">", 2);
        if (g_rm_col == 1 && ros_clicked(390, y, 770, y + 38)) { g_rm_col = 0; g_focus_after = c; sound(PS_BACK); }
    }
    if (show_cat < 0) show_cat = g_rm_cat;
    // the playlists of the category shown
    int n = rm_lists(show_cat, lists), focus_pl = -1;
    for (int k = 0; k < n; k++) {
        const rm_pl& p = RM_PL[lists[k]];
        float y = 153 + 41.0f * k;
        bool f = g_rm_col == 1 && item(782, y, 1137, y + 38);
        if (f) focus_pl = lists[k];
        if (g_rm_col == 1) rm_row(782, y, 1137, y + 38, f, p.name, p.pl >= 0);
        else text(g_fl, 25, 792, y + 5, p.pl >= 0 ? C_DIM : IM_COL32(150, 156, 162, 110), p.name);
        if (lists[k] == cur) g_dl->AddRectFilled(P(1126, y + 14), P(1136, y + 24), A(C_BLUE));   // (the one set now)
        if (g_rm_col == 0 && ros_clicked(782, y, 1137, y + 38)) { g_rm_col = 1; g_rm_cat = show_cat; g_focus_after = k; sound(PS_SELECT); }
    }
    if (!n) text(g_fl, 24, 792, 158, IM_COL32(176, 182, 188, 160), "Nothing here yet.");
    // the picked one's picture, name and words
    const char* big = focus_pl >= 0 ? RM_PL[focus_pl].name : RM_CAT[show_cat];
    panel(1160, 168, 1513, 308, IM_COL32(18, 20, 23, 200));
    int pi = focus_pl >= 0 && RM_PL[focus_pl].pl >= 0 ? RM_PL[focus_pl].pl : show_cat == 1 ? 1 : 0;
    std::vector<pool_gt> gts;
    std::vector<const pg_entry*> maps;
    library();
    playlist_pool(g_pl[pi], gts, maps);
    if (!maps.empty()) {
        const pic* p = map_picture(maps[((int)(t / 5) + (focus_pl >= 0 ? focus_pl : show_cat)) % maps.size()]->key);
        if (p) image(p, 1162, 170, 1511, 306, focus_pl >= 0 && RM_PL[focus_pl].pl < 0 ? 0.45f : 0.95f);
    }
    g_dl->AddRectFilledMultiColor(P(1162, 240), P(1511, 306), A(IM_COL32(8, 10, 12, 0)), A(IM_COL32(8, 10, 12, 0)),
                                  A(IM_COL32(8, 10, 12, 200)), A(IM_COL32(8, 10, 12, 200)));
    g_dl->PushClipRect(P(1162, 170), P(1511, 306), true);   // (Reach's own: the name cut at the picture's edge)
    text(g_fl, 46, 1170, 252, IM_COL32(236, 240, 244, 150), big);
    g_dl->PopClipRect();
    float y = 322;
    if (focus_pl < 0) {
        rm_wrap(g_fl, 25, 1170, y, 345, IM_COL32(222, 226, 230, 255), RM_CAT_BLURB[show_cat]);
    } else {
        const rm_pl& p = RM_PL[focus_pl];
        if (p.pl < 0) {
            rm_wrap(g_fl, 25, 1170, y, 345, IM_COL32(222, 226, 230, 255), p.blurb);
            text(g_fl, 24, 1170, y + 110, C_GOLD, "Not in Proving Grounds yet.");
        } else {
            const playlist& pl = g_pl[p.pl];
            rm_wrap(g_fl, 25, 1170, y, 345, IM_COL32(222, 226, 230, 255), pl.blurb);
            char l[4][48];
            sprintf_s(l[0], "Team Size: %d", pl.size);
            sprintf_s(l[1], "Max Party Size: %d", pl.size);
            sprintf_s(l[2], "Bots in Your Pool: %d", g_pool_count);
            sprintf_s(l[3], "Voting: %d s", g_vote_s);
            for (int i = 0; i < 4; i++) text(g_fl, 25, 1170, y + 120 + 30.0f * i, C_TEXT, l[i]);
            if (focus_pl == cur) text(g_fl, 24, 1170, y + 250, C_BLUE, "Your playlist now.");
        }
    }
    rm_band();
    float x = prompt(318, 966, "A", "Enter", "Select", nullptr);
    prompt(x, 966, "B", "Esc", "Back", &g_footer_back);
    // the columns: Right or A into the playlists, Left back to the categories (B too: pg_back)
    if (g_rm_col == 0) {
        int c = -1;
        for (int k = 0; k < 5; k++) if (pressed(base + k)) c = k;
        if (c < 0 && g_left_right == 1 && g_focus - base >= 0 && g_focus - base < 5) c = g_focus - base;
        if (c >= 0) {
            g_lr_taken = true;
            if (rm_lists(c, lists)) {
                g_rm_cat = c; g_rm_col = 1;
                int at = 0;
                for (int k = 0; k < rm_lists(c, lists); k++) if (lists[k] == cur) at = k;
                g_focus_after = at;
                sound(PS_SELECT);
            } else sound(PS_ERROR);
        }
    } else {
        if (g_left_right == -1) { g_lr_taken = true; g_rm_col = 0; g_focus_after = g_rm_cat; sound(PS_BACK); }
        for (int k = 0; k < n; k++) {
            if (!pressed(base + k)) continue;
            const rm_pl& p = RM_PL[lists[k]];
            if (p.pl < 0) { sound(PS_ERROR); continue; }
            g_size = g_pl[p.pl].size >= 8 ? 8 : 4;
            while (g_nparty > cur_pl().size - 1) g_nparty--;
            save_settings();
            sound(PS_SELECT);
            g_rpage = RP_MM; g_focus_after = 0;
            logf("proving grounds: playlist %s", p.name);
        }
    }
}

static void rm_restrict(pg_env& e, float t) {
    (void)e; (void)t;
    rm_load();
    rm_small_header("SEARCH RESTRICTIONS", "MATCHMAKING");
    const char* L[3] = { "GOOD CONNECTION", "LANGUAGE", "SKILL" };
    const char* D[3] = { "Choose this if you want the search to put a good connection first. Offline, every bot plays on this PC: the connection is always good.",
                         "Choose this if you want the search to put players who speak your language first. Offline, every bot does.",
                         "Choose this if you want the search to put players near your skill first." };
    int base = (int)g_items.size(), focus = -1;
    for (int k = 0; k < 3; k++) {
        float y = 160 + 41.0f * k;
        bool f = item(393, y, 835, y + 38);
        if (f) focus = k;
        rm_row(393, y, 835, y + 38, f, L[k]);
        g_dl->AddRect(P(803, y + 6), P(830, y + 33), A(IM_COL32(214, 220, 226, 220)), 0, 0, U(1.6f));
        if (g_rm_restrict[k]) {
            ImVec2 tick[3] = { P(808, y + 19), P(815, y + 27), P(826, y + 11) };
            g_dl->AddPolyline(tick, 3, A(C_LIT), 0, U(3));
        }
    }
    rm_wrap(g_fl, 26, 877, 172, 345, IM_COL32(222, 226, 230, 255),
            "Setting a priority narrows the search and may make it slower.");
    ImVec2 tri[3] = { P(1285, 190), P(1345, 286), P(1225, 286) };   // (a caution sign of our own)
    g_dl->AddPolyline(tri, 3, A(IM_COL32(214, 128, 60, 230)), ImDrawFlags_Closed, U(4));
    g_dl->AddLine(P(1285, 220), P(1285, 256), A(IM_COL32(214, 128, 60, 230)), U(6));
    g_dl->AddCircleFilled(P(1285, 270), U(4.5f), A(IM_COL32(214, 128, 60, 230)));
    g_dl->AddLine(P(400, 352), P(1430, 352), A(IM_COL32(206, 212, 218, 70)), U(1));
    if (focus >= 0) {
        rm_wrap(g_fl, 27, 402, 366, 1020, C_TEXT, D[focus]);
        text(g_fl, 22, 402, 440, IM_COL32(176, 182, 188, 200), "Saved for your lobbies. The search does not use it yet.");
    }
    for (int gy = -5; gy <= 5; gy++)                  // (the lattice in the middle, as the page's own art)
        for (int gx = -10; gx <= 10; gx++) {
            if ((gx + gy) & 1) continue;
            float dist = sqrtf((float)(gx * gx + gy * gy * 4));
            int a = (int)(150 - dist * 22);
            if (a > 6) rm_diamond(950 + gx * 34.0f, 630 + gy * 34.0f, 20, IM_COL32(110, 170, 230, a), 2.0f);
        }
    rm_band();
    float x = prompt(318, 966, "A", "Enter", "Select", nullptr);
    prompt(x, 966, "B", "Esc", "Back", &g_footer_back);
    for (int k = 0; k < 3; k++)
        if (pressed(base + k)) { g_rm_restrict[k] ^= 1; rm_save(); sound(PS_SELECT); }
}

// ------------------------------------------------------------------ the world map and the home states' heat
// (Nov 19, the owner: "On the pysch profile page id like the same world map. and then a static heat map of the service
// websites player locations") Reach's panel under the profile: the world (native/world_map.h, Natural Earth, public
// domain) in its lines of latitude, and over it the heat of the Service Record's home states: how many of the site's
// players (bots and people) live in each, as the site's last build wrote them (<repo>\logs\service_record\locations.txt,
// tools/service_record.py write_game_locations). The player's own state is ringed.
#include "world_map.h"

static int g_loc_n[64];                          // players by WM_STATES index
static int g_loc_total, g_loc_me = -1;           // all of them; the player's state (-1: not listed)
static ULONGLONG g_loc_check, g_loc_stamp;
// (Nov 19, the owner: "more of a lowkey vibrance to the orange. Make it more of a colormap instead of a popout circle.
// similar to the og") the heat as Reach's own map had it: fine specks over the land, a dot every 0.8 degrees inside
// the states, each coloured by a muted colormap (ember red, orange, soft amber) of the players around it: every
// state's players spread from its label point (a Gaussian, 2.2 degrees), the most-lived-in place the top of the map.
// Worked out once each time locations.txt changes.
struct heat_pt { int16_t lon10, lat10; ImU32 col; };
static std::vector<heat_pt> g_heat;

static bool in_ring(const int16_t* q, int n, float lon, float lat) {   // (even-odd: a point inside a ring)
    bool in = false;
    for (int i = 0, j = n - 1; i < n; j = i++) {
        float xi = q[2 * i] / 10.0f, yi = q[2 * i + 1] / 10.0f, xj = q[2 * j] / 10.0f, yj = q[2 * j + 1] / 10.0f;
        if ((yi > lat) != (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) in = !in;
    }
    return in;
}
static ImU32 heat_colour(float v) {              // 0..1: clear, ember, orange, soft amber (never a full glare)
    static const float S[5][5] = { { 0.00f, 96, 34, 22, 0 }, { 0.25f, 132, 48, 26, 70 }, { 0.50f, 186, 82, 34, 112 },
                                   { 0.75f, 220, 128, 52, 146 }, { 1.00f, 238, 176, 96, 172 } };
    v = v < 0 ? 0 : v > 1 ? 1 : v;
    int k = v >= 1 ? 3 : (int)(v * 4);
    float t = (v - S[k][0]) / (S[k + 1][0] - S[k][0]);
    auto mix = [&](int c) { return (int)(S[k][c] + (S[k + 1][c] - S[k][c]) * t); };
    return IM_COL32(mix(1), mix(2), mix(3), mix(4));
}
static void heat_build() {
    g_heat.clear();
    if (!g_loc_total) return;
    std::vector<int> start(WM_NSTATES);              // (each state's first point in WM_STATE_PTS)
    const int16_t* q = WM_STATE_PTS;
    int ring = 0;
    for (int i = 0; i < WM_NSTATES; i++) {
        start[i] = (int)(q - WM_STATE_PTS);
        for (int r = 0; r < WM_STATES[i].rings; r++) q += 2 * WM_STATE_RING[ring++];
    }
    const float STEP = 0.8f, SIGMA = 2.2f;
    std::vector<std::pair<heat_pt, float>> pts;
    float top = 0;
    for (float lat = 18.0f; lat <= 72.0f; lat += STEP)
        for (float lon = -180.0f; lon <= -64.0f; lon += STEP) {
            bool land = false;                   // (inside a state: the specks keep to the land)
            for (int i = 0; i < WM_NSTATES && !land; i++) {
                const int16_t* p = WM_STATE_PTS + start[i];
                for (int r = 0, rr = WM_STATES[i].ring0; r < WM_STATES[i].rings && !land; r++, rr++) {
                    land = in_ring(p, WM_STATE_RING[rr], lon, lat);
                    p += 2 * WM_STATE_RING[rr];
                }
            }
            if (!land) continue;
            float v = 0;
            for (int i = 0; i < WM_NSTATES; i++) {
                if (!g_loc_n[i]) continue;
                float dx = (lon - WM_STATES[i].lon10 / 10.0f) * cosf(lat * 0.01745f), dy = lat - WM_STATES[i].lat10 / 10.0f;
                v += g_loc_n[i] * expf(-(dx * dx + dy * dy) / (2 * SIGMA * SIGMA));
            }
            if (v > top) top = v;
            pts.push_back({ { (int16_t)(lon * 10), (int16_t)(lat * 10), 0 }, v });
        }
    for (auto& p : pts) {
        float v = top > 0 ? powf(p.second / top, 0.6f) : 0;   // (a gentle curve: the quieter places still show)
        if (v < 0.04f) continue;
        p.first.col = heat_colour(v);
        g_heat.push_back(p.first);
    }
}

static void loc_load() {
    ULONGLONG now = GetTickCount64();
    if (g_loc_check && now - g_loc_check < 2000) return;
    g_loc_check = now;
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\logs\\service_record\\locations.txt", g_root);
    WIN32_FILE_ATTRIBUTE_DATA fa;
    ULONGLONG stamp = GetFileAttributesExW(p, GetFileExInfoStandard, &fa) ? ft_u64(fa.ftLastWriteTime) : 0;
    if (stamp == g_loc_stamp) return;
    g_loc_stamp = stamp;
    memset(g_loc_n, 0, sizeof g_loc_n);
    g_loc_total = 0;
    g_loc_me = -1;
    FILE* f = nullptr;
    if (!stamp || _wfopen_s(&f, p, L"rb") || !f) return;
    char line[512];
    std::vector<std::string> c;
    auto index_of = [](const std::string& code) {
        for (int i = 0; i < WM_NSTATES; i++) if (code == WM_STATES[i].code) return i;
        return -1;
    };
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#') continue;
        line[strcspn(line, "\r\n")] = 0;
        split_tabs(line, c);
        if (c.size() >= 4 && c[0] == "state") {
            int i = index_of(c[1]), n = atoi(c[3].c_str());
            if (i >= 0 && n > 0) { g_loc_n[i] = n; g_loc_total += n; }
        } else if (c.size() >= 3 && c[0] == "person" && !_stricmp(c[1].c_str(), me_name())) {
            g_loc_me = index_of(c[2]);
        }
    }
    fclose(f);
    heat_build();
}

static void rm_world_heat() {
    const float X0 = 393, Y0 = 495, X1 = 1480, Y1 = 800;
    auto at = [](int lon10, int lat10) {             // (latitude 80 at y 508, -40 at 760, as Reach's lines)
        return P(400 + (lon10 / 10.0f + 180) / 360 * 1060, 508 + (80 - lat10 / 10.0f) * 2.1f);
    };
    g_dl->AddRectFilled(P(X0, Y0), P(X1, Y1), A(IM_COL32(7, 10, 13, 200)));
    g_dl->PushClipRect(P(X0, Y0), P(X1, Y1), true);
    std::vector<ImVec2> pts;
    for (int pass = 0; pass < 2; pass++) {           // (the land, then its coasts over it)
        const int16_t* q = WM_LAND_PTS;
        for (int r = 0; r < WM_LAND_RINGS; r++) {
            int n = WM_LAND_RING[r];
            pts.resize(n);
            for (int k = 0; k < n; k++) pts[k] = at(q[2 * k], q[2 * k + 1]);
            if (pass == 0) g_dl->AddConcavePolyFilled(pts.data(), n, A(IM_COL32(40, 46, 52, 235)));
            else g_dl->AddPolyline(pts.data(), n, A(IM_COL32(96, 108, 120, 140)), ImDrawFlags_Closed, 1.0f);
            q += 2 * n;
        }
    }
    {                                                // (the states' borders, faint, where the heat is)
        const int16_t* q = WM_STATE_PTS;
        int rings = 0;
        for (int i = 0; i < WM_NSTATES; i++) rings += WM_STATES[i].rings;
        for (int r = 0; r < rings; r++) {
            int n = WM_STATE_RING[r];
            pts.resize(n);
            for (int k = 0; k < n; k++) pts[k] = at(q[2 * k], q[2 * k + 1]);
            g_dl->AddPolyline(pts.data(), n, A(IM_COL32(120, 132, 144, 70)), ImDrawFlags_Closed, 1.0f);
            q += 2 * n;
        }
    }
    static const char* lat[7] = { "80", "60", "40", "20", "0", "20", "40" };
    for (int i = 0; i < 7; i++) {
        float y = 508 + i * 42.0f;
        g_dl->AddLine(P(400, y), P(1460, y), A(IM_COL32(150, 170, 190, 34)), U(1));
        text(g_fs, 13, 1474, y - 8, IM_COL32(176, 182, 188, 140), lat[i], 2);
    }
    // the heat: the specks of the colormap (heat_build)
    loc_load();
    int most = 0, most_i = -1;
    for (int i = 0; i < WM_NSTATES; i++) if (g_loc_n[i] > most) { most = g_loc_n[i]; most_i = i; }
    const float half = U(0.85f);
    for (const heat_pt& h : g_heat) {
        ImVec2 c = at(h.lon10, h.lat10);
        g_dl->AddRectFilled(ImVec2(c.x - half, c.y - half), ImVec2(c.x + half, c.y + half), A(h.col));
    }
    if (g_loc_me >= 0) {                             // (the player's own state: a thin, quiet ring)
        ImVec2 c = at(WM_STATES[g_loc_me].lon10, WM_STATES[g_loc_me].lat10);
        g_dl->AddCircle(c, U(7), A(IM_COL32(236, 240, 244, 150)), 24, U(1.2f));
    }
    g_dl->PopClipRect();
    char legend[128];
    if (g_loc_total && most_i >= 0)
        sprintf_s(legend, "SERVICE RECORD HOME STATES: %d PLAYERS, THE MOST IN %s (%d)%s", g_loc_total,
                  WM_STATES[most_i].code, most, g_loc_me >= 0 ? ". YOURS IS RINGED." : "");
    else
        strcpy_s(legend, "SERVICE RECORD HOME STATES: NONE YET (THE SITE WRITES THEM WHEN IT IS BUILT)");
    text(g_fs, 15, 404, Y1 - 24, IM_COL32(200, 206, 212, 190), legend);
}

static const char* RM_PSY[4] = { "CHATTINESS", "MOTIVATION", "TEAMWORK", "TONE" };
static const char* RM_PSY_V[4][3] = { { "NO PREFERENCE (DEFAULT)", "QUIET", "TALKATIVE" },
                                      { "NO PREFERENCE (DEFAULT)", "HAVE FUN", "WIN" },
                                      { "NO PREFERENCE (DEFAULT)", "LONE WOLF", "TEAM PLAYER" },
                                      { "NO PREFERENCE (DEFAULT)", "POLITE", "ROWDY" } };
static const char* RM_PSY_D[4][3] = {
    { "No preference set for how talkative the players are.", "Players who keep their callouts short.", "Players who call out everything they see." },
    { "No preference set for why the players play.", "Players who are here to have fun.", "Players who are here to win." },
    { "No preference set for how the players work together.", "Players who go their own way.", "Players who stick with the team." },
    { "No preference set for how the players behave.", "Players who keep it friendly.", "Players who keep it loud." } };
static const char* rm_psych_text(int k) {        // (MY PARTY DETAILS: in Reach's title case)
    static const char* T[4][3] = { { "No Preference (Default)", "Quiet", "Talkative" },
                                   { "No Preference (Default)", "Have Fun", "Win" },
                                   { "No Preference (Default)", "Lone Wolf", "Team Player" },
                                   { "No Preference (Default)", "Polite", "Rowdy" } };
    int v = k >= 0 && k < 4 ? g_rm_psych[k] : 0;
    return T[k < 0 || k > 3 ? 0 : k][v < 0 || v > 2 ? 0 : v];
}

static void rm_psych(pg_env& e, float t) {
    (void)e; (void)t;
    rm_load();
    rm_small_header("PSYCH PROFILE", "MATCHMAKING");
    int base = (int)g_items.size(), focus = -1;
    // (Nov 19, the owner: "the proving grounds options (Simulate Matches 1 round, 2 round, etc) to be on the pysch
    // screen") the four preferences, then Proving Grounds' own two: the bot simulation's rounds, the invited party
    double now = ImGui::GetTime();
    sim_poll(now);
    char sims[48], inv[32];
    bool sim_arrows = false;
    if (g_sim_proc) strcpy_s(sims, "PLAYING...");
    else if (g_sim_done_at >= 0 && now - g_sim_done_at < 10.0 && g_sim_made >= 0) sprintf_s(sims, "DONE: %d MATCHES", g_sim_made);
    else { sprintf_s(sims, "%d ROUND%s", g_sim_rounds, g_sim_rounds == 1 ? "" : "S"); sim_arrows = true; }
    sprintf_s(inv, "%d / %d", g_nparty, cur_pl().size - 1);
    for (int k = 0; k < 6; k++) {
        float y = 160 + 41.0f * k;
        bool f = item(393, y, 1505, y + 38);
        if (f) focus = k;
        rm_row(393, y, 1505, y + 38, f, k < 4 ? RM_PSY[k] : k == 4 ? "SIMULATE MATCHES" : "INVITE PLAYER");
        const char* v = k < 4 ? RM_PSY_V[k][g_rm_psych[k]] : k == 4 ? sims : inv;
        text(g_fl, 25, 1238, y + 7, f ? C_TEXT : C_DIM, v, 1);
        if (f && (k < 4 || (k == 4 && sim_arrows))) { text(g_fl, 28, 960, y + 3, C_DIM, "<"); text(g_fl, 28, 1494, y + 3, C_DIM, ">", 2); }
    }
    g_dl->AddLine(P(400, 414), P(1500, 414), A(IM_COL32(206, 212, 218, 70)), U(1));
    if (focus >= 0 && focus < 4) {
        char l1[96];
        sprintf_s(l1, "Saved for your lobbies. The search does not use your %s yet.", focus == 0 ? "chattiness" :
                  focus == 1 ? "motivation" : focus == 2 ? "teamwork" : "tone");
        text(g_fl, 27, 402, 422, C_TEXT, l1);
        text(g_fl, 25, 402, 456, C_DIM, RM_PSY_D[focus][g_rm_psych[focus]]);
    } else if (focus == 4) {
        text(g_fl, 27, 402, 422, C_TEXT, "Bots play matches of their own for the Service Record.");
        text(g_fl, 25, 402, 456, C_DIM, "Left / Right: how many rounds (a round is about 25 lobbies). A: play them.");
    } else if (focus == 5) {
        text(g_fl, 27, 402, 422, C_TEXT, "Bots who play on your team every game, whatever the lobby.");
        text(g_fl, 25, 402, 456, C_DIM, "A: pick them from your pool.");
    }
    rm_world_heat();                                 // (Nov 19: the world as Reach's, the Service Record's home states)
    rm_band();
    prompt(318, 966, "B", "Esc", "Back", &g_footer_back);
    if (focus >= 0 && focus < 4) {
        int step = g_left_right ? g_left_right : pressed(base + focus) ? 1 : 0;
        if (step) {
            g_lr_taken = true;
            g_rm_psych[focus] = (g_rm_psych[focus] + step + 3) % 3;
            rm_save();
            sound(PS_MOVE);
        }
    }
    if (focus == 4 && g_left_right && !g_sim_proc) {     // (the rounds, 1 to 20, as Proving Grounds' menu had them)
        g_lr_taken = true;
        int r = g_sim_rounds + g_left_right;
        g_sim_rounds = r < 1 ? 1 : r > 20 ? 20 : r;
        g_sim_done_at = -1;
        sound(PS_MOVE);
    }
    if (pressed(base + 4)) {
        if (g_sim_proc) sound(PS_ERROR);
        else { sim_start(); sound(PS_SELECT); }
    }
    if (pressed(base + 5)) { g_invite = true; g_npool_names = 0; g_invite_scroll = 0; g_focus = 0; sound(PS_SELECT); }
}

// ------------------------------------------------------------------ phase 2: the Start menu, the Service Record
// (Nov 19, the owner's ten frames: MY PARTY DETAILS, MENU, SERVICE RECORD, CAREER, CAMPAIGN, ARENA, MATCHMAKING,
// FIREFIGHT twice, COMMENDATIONS) Reach's player pages. The numbers are the Service Record's (career.txt, written with
// the site by tools/service_record.py write_game_career): it counts only Proving Grounds' matches, so Matchmaking is
// all of them and Arena those of The Arena; the campaign, Firefight and custom games are not recorded, and their pages
// say so rather than show made-up numbers. Top Commendations are the three furthest along (commendations.txt).
static int g_car[3][6];                          // matchmaking, arena, btb: games, wins, kills, deaths, assists, seconds
static bool g_car_have;
static ULONGLONG g_car_check, g_car_stamp;
static int g_diff_mode;                          // the difficulty page: 0 the campaign, 1 Firefight

static void career_load() {
    ULONGLONG now = GetTickCount64();
    if (g_car_check && now - g_car_check < 2000) return;
    g_car_check = now;
    wchar_t p[MAX_PATH];
    swprintf_s(p, L"%s\\logs\\service_record\\career.txt", g_root);
    WIN32_FILE_ATTRIBUTE_DATA fa;
    ULONGLONG stamp = GetFileAttributesExW(p, GetFileExInfoStandard, &fa) ? ft_u64(fa.ftLastWriteTime) : 0;
    if (stamp == g_car_stamp) return;
    g_car_stamp = stamp;
    memset(g_car, 0, sizeof g_car);
    g_car_have = false;
    FILE* f = nullptr;
    if (!stamp || _wfopen_s(&f, p, L"rb") || !f) return;
    char line[512];
    std::vector<std::string> c;
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#') continue;
        line[strcspn(line, "\r\n")] = 0;
        split_tabs(line, c);
        if (c.size() < 9 || c[0] != "career" || _stricmp(c[1].c_str(), me_name())) continue;
        int b = c[2] == "matchmaking" ? 0 : c[2] == "arena" ? 1 : c[2] == "btb" ? 2 : -1;
        if (b < 0) continue;
        for (int k = 0; k < 6; k++) g_car[b][k] = atoi(c[3 + k].c_str());
        g_car_have = true;
    }
    fclose(f);
}

// the left list of a menu page (Reach's: 41 apart from y 145), its rows dim when not here; returns the focused one
static int rm_list(const char* const* names, const bool* on, int n, float x1 = 775) {
    int focus = -1;
    for (int k = 0; k < n; k++) {
        float y = 145 + 41.0f * k;
        bool f = item(390, y, x1, y + 38);
        if (f) focus = k;
        rm_row(390, y, x1, y + 38, f, names[k], on ? on[k] : true);
    }
    return focus;
}
// a row of numbers on the right, as Reach's: the label, the value at the right, a faint line under
static void rm_stat(float y, const char* label, const char* value, bool dim = false) {
    text(g_fl, 26, 808, y + 4, dim ? IM_COL32(176, 182, 188, 150) : IM_COL32(220, 224, 228, 255), label);
    text(g_fl, 26, 1500, y + 4, dim ? IM_COL32(176, 182, 188, 150) : C_TEXT, value, 2);
    g_dl->AddLine(P(795, y + 40), P(1515, y + 40), A(IM_COL32(150, 158, 166, 55)), U(1));
}
static float comm_share(const comm_item& c, const comm_now& s) {   // toward the next tier, 0..1
    if (s.n < 0) return 0;
    if (s.tier >= (int)c.need.size()) return 1;
    int lo = s.tier > 0 ? c.need[s.tier - 1] : 0, hi = c.need[s.tier];
    return hi > lo ? (float)(s.n - lo) / (hi - lo) : 0;
}
// Top Commendations: the three furthest along (the highest tier, then the most toward the next), each its name, its
// banner (the tier's own, else the commendation's), a thin bar toward the next tier
static void rm_top_comms(float y) {
    comm_load();
    std::vector<int> order;
    for (int i = 0; i < (int)g_comm_items.size() && i < (int)g_comm_now.size(); i++)
        if (g_comm_now[i].n > 0) order.push_back(i);
    std::sort(order.begin(), order.end(), [](int a, int b) {
        const comm_now &x = g_comm_now[a], &z = g_comm_now[b];
        if (x.tier != z.tier) return x.tier > z.tier;
        return comm_share(g_comm_items[a], x) > comm_share(g_comm_items[b], z);
    });
    g_dl->AddRect(P(792, y), P(1515, y + 170), A(IM_COL32(150, 158, 166, 70)), 0, 0, U(1));
    text(g_fl, 26, 805, y + 8, C_TEXT, "Top Commendations");
    if (order.empty()) { text(g_fl, 22, 805, y + 60, IM_COL32(176, 182, 188, 170), "None earned yet."); return; }
    for (int k = 0; k < 3 && k < (int)order.size(); k++) {
        const comm_item& c = g_comm_items[order[k]];
        const comm_now& s = g_comm_now[order[k]];
        float x0 = 803 + k * 245.0f, x1 = x0 + 222;
        text(g_fl, 23, x0, y + 46, C_DIM, c.name.c_str());
        const pic* bp = s.tier > 0 && s.tier <= (int)c.tier_art.size() ? site_picture(c.tier_art[s.tier - 1]) : nullptr;
        if (!bp) bp = site_picture(c.banner);
        if (bp) image_fit(bp, x0, y + 80, x1, y + 144);
        else { panel(x0, y + 82, x1, y + 142, IM_COL32(40, 70, 104, 200)); crest(x0 + 111, y + 112, 22, C_DIM); }
        float sh = comm_share(c, s);
        g_dl->AddRectFilled(P(x0, y + 150), P(x1, y + 156), A(IM_COL32(60, 66, 72, 200)));
        g_dl->AddRectFilled(P(x0, y + 150), P(x0 + (x1 - x0) * sh, y + 156), A(TIER_COL[s.tier < 7 ? s.tier : 6]));
    }
}
// the Exit prompt at the band's right (the pad's Start, M): true when asked
static bool rm_exit_prompt() {
    bool click = false;
    prompt(1396, 930, "Start", "M", "Exit", &click);
    return !g_inert && (click || ImGui::IsKeyPressed(ImGuiKey_GamepadStart, false) || ImGui::IsKeyPressed(ImGuiKey_M, false));
}
static void rm_exit() { g_rpage = g_rmenu_from; g_focus_after = 0; sound(PS_BACK); }

static void rm_star(float cx, float cy, float r, ImU32 c) {   // (Reach's challenge star, drawn)
    ImVec2 v[10];
    for (int i = 0; i < 10; i++) {
        float a = -1.5708f + i * 0.6283f, rr = (i & 1) ? r * 0.45f : r;
        v[i] = P(cx + cosf(a) * rr, cy + sinf(a) * rr);
    }
    g_dl->AddConcavePolyFilled(v, 10, A(c));
}

// (Nov 19, later) PROVING GROUNDS' own options left the menu: Simulate Matches and Invite Player are on the Psych
// Profile, Commendations on Matchmaking, the challenges here (rm_challenges), the game size the playlist
static const int RM_NMENU = 8;
static const char* RM_MENU_ITEMS[9] = { "THE ARMORY", "PLAYER", "FILE BROWSER", "CONTROLLER", "AUDIO VIDEO", "CHALLENGES",
                                        "NETWORK STATUS", "SERVICE RECORD SITE", "PROVING GROUNDS" };
static const bool RM_MENU_ON[9] = { true, true, false, false, false, true, false, true, true };
static const char* RM_MENU_DESC[9] = {
    "Buy armor with the credits your Service Record has earned, as in Reach. What you equip here is what you wear in "
    "Proving Grounds' matches.",
    "Your Service Record: your career, your commendations.",
    "Your films, maps and game types are in MCC's own menus.",
    "Set your controls in MCC's own Settings.",
    "Set sound and picture in MCC's own Settings.",
    "Today's and this week's challenges, as your Service Record has them.",
    "Proving Grounds plays on this PC: there is no network to check.",
    "Open your Service Record site in the browser: every match, medal and commendation.",
    "Proving Grounds' own options: invite players, challenges, commendations, simulate matches, game size." };

// the challenges in the Start menu, as Reach's DAILY CHALLENGES: each its icon in a ring, its name, what to do, its
// credits, a thin bar and [n/need]; the dailies, then the weeklies
static void rm_challenges() {
    chal_load();
    if (g_chal_items.empty()) {
        rm_wrap(g_fl, 24, 800, 160, 700, IM_COL32(200, 206, 212, 220),
                "No challenges yet: the Service Record site writes them when it is built.");
        return;
    }
    std::vector<const chal_item*> list;
    for (const char* per : { "daily", "weekly" })
        for (const chal_item& c : g_chal_items) if (c.period == per) list.push_back(&c);
    float y = 148;
    std::string per;
    for (size_t k = 0; k < list.size() && y < 800; k++) {
        const chal_item& c = *list[k];
        if (c.period != per) {                       // (each period's heading)
            per = c.period;
            text(g_fl, 20, 800, y, IM_COL32(176, 182, 188, 200), per == "daily" ? "DAILY" : "WEEKLY");
            y += 26;
        }
        int n = 0;
        for (auto& kv : g_chal_now) if (kv.first == c.key) n = kv.second;
        bool done = n >= c.need;
        g_dl->AddCircle(P(838, y + 34), U(28), A(IM_COL32(214, 220, 226, 150)), 32, U(2));
        chal_icon(c.icon, 838, y + 34, 34);
        std::string name = c.name;
        for (auto& ch : name) ch = (char)toupper((unsigned char)ch);
        text(g_fl, 24, 884, y + 2, C_TEXT, name.c_str());
        text(g_fl, 24, 1505, y + 2, done ? C_GOLD : C_TEXT, (cr_text(c.cr) + " cR").c_str(), 2);
        rm_wrap(g_fs, 19, 884, y + 32, 440, IM_COL32(200, 206, 212, 220), c.what.c_str());
        float bx0 = 884, bx1 = 1420, by = y + 76, sh = c.need > 0 ? (float)(n < c.need ? n : c.need) / c.need : 0;
        g_dl->AddRectFilled(P(bx0, by), P(bx1, by + 5), A(IM_COL32(60, 66, 72, 200)));
        if (sh > 0) g_dl->AddRectFilled(P(bx0, by), P(bx0 + (bx1 - bx0) * sh, by + 5), A(done ? C_GOLD : C_BLUE));
        char prog[32];
        sprintf_s(prog, done ? "DONE" : "[%d/%d]", n < c.need ? n : c.need, c.need);
        text(g_fs, 18, 1505, by - 9, C_DIM, prog, 2);
        g_dl->AddLine(P(795, y + 94), P(1515, y + 94), A(IM_COL32(150, 158, 166, 55)), U(1));
        y += 100;
    }
}

static void rm_menu_act(int k) {                 // an entry of the Start menu pressed
    if (!RM_MENU_ON[k]) { sound(PS_ERROR); return; }
    sound(PS_SELECT);
    if (k == 0) { g_rpage = RP_ARMORY; g_focus_after = 0; }
    if (k == 1) { g_rpage = RP_SR; g_focus_after = 0; }
    if (k == 5) { g_chal = true; g_chal_check = 0; }    // (all of them: the Challenges page)
    if (k == 7) open_site_page(me_name(), "");
    if (k == 8) { g_rpage_from = RP_MENU; g_rpage = RP_OPTIONS; g_focus_after = 0; }
}

static void rm_menu(pg_env& e, float t) {
    rm_small_header("MENU", g_rmenu_from == RP_TITLE ? "TITLE" : g_rmenu_from == RP_MM ? "MATCHMAKING" : "MAIN MENU");
    chal_load();
    int base = (int)g_items.size();
    int focus = rm_list(RM_MENU_ITEMS, RM_MENU_ON, RM_NMENU);
    if (!g_chal_items.empty()) rm_star(580, 145 + 41.0f * 5 + 19, 11, IM_COL32(232, 140, 50, 255));
    int f = focus >= 0 ? focus : 0;
    if (f == 5) {                                    // (the challenges take the page's right side, as Reach's)
        rm_challenges();
        rm_band();
        float x = prompt(318, 966, "A", "Enter", "All challenges", nullptr);
        prompt(x, 966, "B", "Esc", "Back", &g_footer_back);
        if (rm_exit_prompt()) { rm_exit(); return; }
        for (int k = 0; k < RM_NMENU; k++) if (pressed(base + k)) rm_menu_act(k);
        return;
    }
    // the middle column: what the focused one holds, dim as Reach's
    static const char* ARMORY[12] = { "HELMET...", "LEFT SHOULDER...", "RIGHT SHOULDER...", "CHEST...", "WRIST...",
                                      "UTILITY...", "VISOR COLOR...", "KNEE GUARDS...", "ARMOR EFFECT...",
                                      "ELITE ARMOR...", "EMBLEM...", "COLORS..." };
    static const char* PLAYER[2] = { "SERVICE RECORD...", "COMMENDATIONS..." };
    static const char* CHAL[2] = { "DAILY...", "WEEKLY..." };
    static const char* PG[5] = { "INVITE PLAYER...", "CHALLENGES...", "COMMENDATIONS...", "SIMULATE MATCHES...", "GAME SIZE..." };
    const char* const* sub = f == 0 ? ARMORY : f == 1 ? PLAYER : f == 5 ? CHAL : f == 8 ? PG : nullptr;
    int nsub = f == 0 ? 12 : f == 1 ? 2 : f == 5 ? 2 : f == 8 ? 5 : 0;
    for (int k = 0; k < nsub; k++) {
        float y = 153 + 40.0f * k + (f == 0 && k >= 10 ? 38 : 0);
        text(g_fl, 25, 790, y, IM_COL32(176, 182, 188, RM_MENU_ON[f] ? 170 : 110), sub[k]);
    }
    if (f == 0) g_dl->AddLine(P(786, 571), P(1090, 571), A(IM_COL32(150, 158, 166, 70)), U(1));
    // the picture: the player's Spartan for the armory, else our own panel with the entry's name faint across it
    panel(1165, 165, 1515, 580, IM_COL32(20, 24, 28, 200));
    if (f == 0 && e.figure) {
        if (unsigned long long fig = e.figure(me_name(), false, 0.35f + 0.25f * sinf(t * 0.4f), 350, 415))
            g_dl->AddImage((ImTextureID)fig, P(1165, 165), P(1515, 580), ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
    } else {
        rm_diamonds(1340, 330, 150, IM_COL32(120, 176, 230, 120));
    }
    g_dl->PushClipRect(P(1165, 165), P(1515, 580), true);
    text(g_fl, 60, 1180, 492, IM_COL32(236, 240, 244, 70), RM_MENU_ITEMS[f]);
    g_dl->PopClipRect();
    rm_wrap(g_fl, 25, 1172, 600, 345, IM_COL32(222, 226, 230, 255), RM_MENU_DESC[f]);
    rm_band();
    float x = prompt(318, 966, "A", "Enter", "Select", nullptr);
    prompt(x, 966, "B", "Esc", "Back", &g_footer_back);
    if (rm_exit_prompt()) { rm_exit(); return; }
    for (int k = 0; k < RM_NMENU; k++) if (pressed(base + k)) rm_menu_act(k);
}

// the player's card on the Service Record: emblem, name, rank, the rank's insignia large at the right
static void rm_card(float y) {
    comm_load();
    g_dl->AddRectFilledMultiColor(P(797, y), P(1505, y + 130), A(IM_COL32(30, 58, 96, 230)), A(IM_COL32(24, 46, 78, 220)),
                                  A(IM_COL32(18, 34, 58, 220)), A(IM_COL32(26, 50, 84, 230)));
    int32_t emb[5];
    int np = -1;
    unsigned long long em = g_make && mcc_player_look(emb, &np) ? player_emblem(emb, g_make) : 0;
    if (em) g_dl->AddImage((ImTextureID)em, P(803, y + 6), P(937, y + 126), ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
    else crest(870, y + 65, 50, C_TEXT);
    const char* who = g_comm_who.empty() ? me_name() : g_comm_who.c_str();
    text(g_fl, 34, 954, y + 22, C_TEXT, who);
    text(g_fl, 28, 954, y + 72, IM_COL32(200, 210, 222, 255), g_comm_rank.empty() ? "Rank not recorded yet" : g_comm_rank.c_str());
    g_dl->AddRectFilled(P(1376, y + 6), P(1505, y + 126), A(IM_COL32(10, 12, 15, 220)));
    if (const pic* rp = sr_rank_picture(sr_rank_of(who, false))) image_fit(rp, 1386, y + 16, 1495, y + 116);
}

static void rm_sr(pg_env& e, float t) {
    (void)e; (void)t;
    career_load();
    rm_small_header("SERVICE RECORD", "PLAYER \xC2\xB7 MENU");
    static const char* L[3] = { "CAREER...", "COMMENDATIONS...", "LEGACY" };
    static const bool ON[3] = { true, true, false };
    int base = (int)g_items.size();
    int focus = rm_list(L, ON, 3);
    rm_card(160);
    char v[2][16];
    sprintf_s(v[0], "%d", g_car[0][1]);
    sprintf_s(v[1], "%d", g_car[0][2]);
    rm_stat(300, "Matchmaking Games Won", g_car_have ? v[0] : "0");
    rm_stat(341, "Matchmaking MP Kills", g_car_have ? v[1] : "0");
    rm_stat(382, "Highest Campaign Difficulty", "Not recorded", true);
    rm_stat(423, "Connected Campaign Kills", "Not recorded", true);
    rm_top_comms(470);
    if (focus == 2) text(g_fs, 21, 400, 280, IM_COL32(200, 206, 212, 200), "Legacy is not in Proving Grounds yet.");
    rm_band();
    float x = prompt(318, 966, "A", "Enter", "Select", nullptr);
    prompt(x, 966, "B", "Esc", "Back", &g_footer_back);
    if (rm_exit_prompt()) { rm_exit(); return; }
    if (pressed(base + 0)) { g_rpage = RP_CAREER; g_focus_after = 2; sound(PS_SELECT); }
    if (pressed(base + 1)) { g_comm = true; g_comm_check = 0; g_comm_tab = 0; g_comm_scroll = 0; g_focus = 0; sound(PS_SELECT); }
    if (pressed(base + 2)) sound(PS_ERROR);
}

static void rm_career(pg_env& e, float t) {
    (void)e; (void)t;
    career_load();
    rm_small_header("CAREER", "SERVICE RECORD \xC2\xB7 PLAYER \xC2\xB7 MENU");
    static const char* L[5] = { "CAMPAIGN...", "ARENA...", "MATCHMAKING...", "FIREFIGHT...", "CUSTOM GAMES" };
    int base = (int)g_items.size();
    int focus = rm_list(L, nullptr, 5), f = focus >= 0 ? focus : 2;
    char v[6][24];
    auto num = [&](int i, int n) { sprintf_s(v[i], "%d", n); return (const char*)v[i]; };
    if (f == 0 || f == 3) {                          // (not recorded: the rows Reach had, with nothing in them)
        const char* R0[5] = { "Highest Difficulty", "First Completion Date", "Total Enemies Killed",
                              "Total Vehicles Destroyed", "Time Played" };
        const char* R3[7] = { "Covenant Kills", "Vehicles Destroyed", "Highest Set Completed (number)",
                              "Most Kills in a Game", "Waves Completed", "Generators Destroyed", "Enemy Players Killed" };
        const char* const* R = f == 0 ? R0 : R3;
        int n = f == 0 ? 5 : 7;
        for (int k = 0; k < n; k++) rm_stat(160 + 41.0f * k, R[k], "Not recorded", true);
        rm_wrap(g_fl, 24, 808, 175 + 41.0f * n, 700, IM_COL32(200, 206, 212, 220), f == 0
                ? "Proving Grounds does not record the campaign: the Service Record counts only its own matches."
                : "Proving Grounds does not record Firefight: the Service Record counts only its own matches.");
    } else if (f == 1 || f == 2) {
        const int* c = g_car[f == 1 ? 1 : 0];
        rm_stat(160, "Games Won", num(0, c[1]));
        rm_stat(201, "Kills", num(1, c[2]));
        rm_stat(242, "Deaths", num(2, c[3]));
        rm_stat(283, "Assists", num(3, c[4]));
        if (f == 1) {
            sprintf_s(v[4], "%d%%", g_car[0][0] ? (int)(100.0f * g_car[1][0] / g_car[0][0] + 0.5f) : 0);
            rm_stat(324, "% of Matchmaking Games Played in Arena", v[4]);
        } else {
            int s = c[5];
            sprintf_s(v[4], "%dd %02d:%02d:%02d", s / 86400, s / 3600 % 24, s / 60 % 60, s % 60);
            rm_stat(324, "Time Played", v[4]);
            rm_top_comms(380);
        }
    } else {
        rm_wrap(g_fl, 25, 808, 175, 700, IM_COL32(222, 226, 230, 255),
                "Custom games are not on the Service Record: it counts only Proving Grounds' matches, the games its "
                "matchmaking started.");
    }
    rm_band();
    float x = prompt(318, 966, "A", "Enter", "Select", nullptr);
    prompt(x, 966, "B", "Esc", "Back", &g_footer_back);
    if (rm_exit_prompt()) { rm_exit(); return; }
    if (pressed(base + 0) || pressed(base + 3)) {
        g_diff_mode = pressed(base + 3) ? 1 : 0;
        g_rpage = RP_DIFF; g_focus_after = 0; sound(PS_SELECT);
    }
}

static void rm_diff(pg_env& e, float t) {
    (void)e; (void)t;
    rm_small_header(g_diff_mode ? "FIREFIGHT" : "CAMPAIGN", "CAREER \xC2\xB7 SERVICE RECORD \xC2\xB7 PLAYER");
    static const char* L[3] = { "NORMAL", "HEROIC", "LEGENDARY" };
    rm_list(L, nullptr, 3);
    const char* C[5] = { "Missions Completed", "Covenant Kills", "Vehicles Destroyed", "Missions Completed Without Dying/Restarted",
                         "Highest Skull Multiplier" };
    const char* F[7] = { "Covenant Kills", "Vehicles Destroyed", "Highest Set Completed", "Most Consecutive Kills without Dying",
                         "Biggest Kill", "Times Beat Par", "Highest Official Score" };
    const char* const* R = g_diff_mode ? F : C;
    int n = g_diff_mode ? 7 : 5;
    for (int k = 0; k < n; k++) rm_stat(160 + 41.0f * k, R[k], "Not recorded", true);
    rm_wrap(g_fl, 24, 808, 175 + 41.0f * n, 700, IM_COL32(200, 206, 212, 220),
            g_diff_mode ? "Proving Grounds does not record Firefight yet." : "Proving Grounds does not record the campaign yet.");
    rm_band();
    prompt(318, 966, "B", "Esc", "Back", &g_footer_back);
    if (rm_exit_prompt()) rm_exit();
}

// ------------------------------------------------------------------ phase 3: the Armory
// (Nov 19, the owner's 17 frames of Reach's Armory and his design: "I do want all the items in the game to be
// purchasable and unlockable ... everything on MCC is actually already unlocked, but we make it to where you can't
// equip it until you purchase it through our menu ... when we go to equip an item that we have not purchased or
// locked, it just doesn't do anything") ARMORY: the slots, the player's Spartan wearing what is equipped; a slot's
// page lists its items (the helmet its helmets, each opening its variants), each EQUIPPED, PURCHASED or its price,
// locked by rank or by the item it needs first; the focused item tried on the Spartan; a purchase asked about first.
// Reach's own prices and rank gates (the Editing Kit's supply depot tag, tools/reach_prices.py), the credits the
// Service Record's (native/armory.cpp, its ledger); what is equipped is worn in Proving Grounds' Halo: Reach matches
// (reach.cpp). Emblem and colours stay MCC's own, as Reach never sold them.
static const char* ARM_TITLE[ARM_NSLOTS] = { "HELMET", "LEFT SHOULDER", "RIGHT SHOULDER", "CHEST", "WRIST", "UTILITY",
                                             "VISOR COLOR", "KNEE GUARDS", "ARMOR EFFECT", "ELITE ARMOR" };
static int g_arm_slot, g_arm_family = -1;       // the item page's slot; the variants page's helmet family
static int g_arm_buy = -1, g_arm_back_focus;     // the purchase being asked about (-1 none); the focus to go back to
static int g_arm_scroll;                         // the item list's first row shown
static float g_arm_yaw = 0.35f;
static std::string g_arm_note;                   // a line after a purchase, shown a few seconds
static double g_arm_note_t;

static void arm_rows(int slot, int family, std::vector<int>& out) {   // a page's items: a helmet's families (each
    out.clear();                                                         // its base) or one family, else the slot's
    const std::vector<arm_item>& it = armory_items();
    for (int i = 0; i < (int)it.size(); i++) {
        if (it[i].slot != ARM_SLOTS[slot]) continue;
        if (slot == 0 && (family < 0 ? it[i].variant != 0 : it[i].family != family)) continue;
        out.push_back(i);
    }
}
static int arm_family_state(int i) {             // a helmet family's row: EQUIPPED when any of it is worn
    const std::vector<arm_item>& it = armory_items();
    int w = armory_worn("helmet");
    if (w >= 0 && it[w].family == it[i].family) return ARM_EQUIPPED;
    return armory_state(i, me_name());
}
static void arm_lock(float cx, float cy, float s, ImU32 c) {   // (our own padlock, drawn)
    g_dl->AddRectFilled(P(cx - s * 0.42f, cy - s * 0.02f), P(cx + s * 0.42f, cy + s * 0.52f), A(c), U(2));
    g_dl->PathArcTo(P(cx, cy - s * 0.02f), U(s * 0.27f), 3.14159f, 6.28318f, 12);
    g_dl->PathStroke(A(c), 0, U(s * 0.11f));
}
// a row's state at its right: EQUIPPED (gold), PURCHASED, else the price (a lock before it when locked)
static void arm_state_text(float x1, float y, float fs, int st, int cost, bool focus) {
    if (st == ARM_EQUIPPED) { text(g_fl, fs, x1, y, C_GOLD, "EQUIPPED", 2); return; }
    if (st == ARM_OWNED) { text(g_fl, fs, x1, y, focus ? C_TEXT : C_DIM, "PURCHASED", 2); return; }
    std::string s = cost ? cr_text(cost) + " cR" : "FREE";
    bool locked = st == ARM_LOCKED_RANK || st == ARM_LOCKED_NEEDS;
    bool short_of = !locked && cost > armory_balance(me_name());
    ImU32 c = locked ? IM_COL32(150, 156, 162, 190) : short_of ? IM_COL32(226, 120, 96, 255) : focus ? C_TEXT : C_DIM;
    text(g_fl, fs, x1, y, c, s.c_str(), 2);
    if (locked) arm_lock(x1 - text_w(g_fl, fs, s.c_str()) / g_pg.s - 18, y + fs * 0.42f, fs * 0.8f, c);
}
// the Spartan in its frame, turned with the right stick (or Q / E)
static void arm_figure(pg_env& e, float x0, float y0, float x1, float y1) {
    panel(x0, y0, x1, y1, IM_COL32(16, 22, 28, 200));
    float dt = ImGui::GetIO().DeltaTime;
    if (!g_inert) {
        if (ImGui::IsKeyDown(ImGuiKey_GamepadRStickLeft) || ImGui::IsKeyDown(ImGuiKey_Q)) g_arm_yaw -= 2.2f * dt;
        if (ImGui::IsKeyDown(ImGuiKey_GamepadRStickRight) || ImGui::IsKeyDown(ImGuiKey_E)) g_arm_yaw += 2.2f * dt;
    }
    if (!e.figure) return;
    if (unsigned long long fig = e.figure(me_name(), false, g_arm_yaw, (int)(x1 - x0), (int)(y1 - y0)))
        g_dl->AddImage((ImTextureID)fig, P(x0, y0), P(x1, y1), ImVec2(0, 0), ImVec2(1, 1), A(IM_COL32(255, 255, 255, 255)));
    else rm_diamonds((x0 + x1) * 0.5f, (y0 + y1) * 0.5f, 150, IM_COL32(120, 176, 230, 120));
}
static bool arm_ready() {                        // the data is there; else the page says why
    if (armory_load()) return true;
    rm_wrap(g_fl, 25, 808, 175, 700, IM_COL32(222, 226, 230, 255),
            "The Armory opens once the Service Record site has been built: it is built after every Proving Grounds "
            "match (or run tools\\service_record.py).");
    return false;
}

static void rm_armory(pg_env& e, float t) {
    (void)t;
    rm_small_header("ARMORY", "MENU");
    static const char* L[12] = { "HELMET", "LEFT SHOULDER", "RIGHT SHOULDER", "CHEST", "WRIST", "UTILITY", "VISOR COLOR",
                                 "KNEE GUARDS", "ARMOR EFFECT", "ELITE ARMOR", "EMBLEM", "COLORS" };
    static const bool ON[12] = { true, true, true, true, true, true, true, true, true, true, false, false };
    int base = (int)g_items.size();
    int focus = rm_list(L, ON, 12), f = focus >= 0 ? focus : 0;
    bool ready = arm_ready();
    if (ready) {
        armory_try(f == 9 ? armory_worn("elite_armor") : -1);   // (the Elite's armor shown on the Elite)
        arm_figure(e, 1080, 140, 1515, 800);
        if (f < ARM_NSLOTS) {
            int own = 0, all = 0;                    // (every item of the slot, the helmets' variants too)
            for (int i = 0; i < (int)armory_items().size(); i++)
                if (armory_items()[i].slot == ARM_SLOTS[f]) { all++; own += armory_state(i, me_name()) >= ARM_OWNED; }
            int w = armory_worn(ARM_SLOTS[f]);
            text(g_fl, 21, 808, 150, IM_COL32(176, 182, 188, 200), "EQUIPPED");
            rm_wrap(g_fl, 28, 808, 176, 255, C_TEXT, w >= 0 ? armory_items()[w].name.c_str() : "Nothing");
            char own_s[48];
            sprintf_s(own_s, "%d of %d owned", own, all);
            text(g_fl, 22, 808, 268, C_DIM, own_s);
        } else {
            rm_wrap(g_fl, 24, 808, 150, 255, IM_COL32(200, 206, 212, 220),
                    "Reach never sold emblems or colours: set them in MCC's own Customization. The Armory keeps them.");
        }
    }
    rm_band(ready ? armory_balance(me_name()) : -1);
    float x = prompt(318, 966, "A", "Enter", "Select", nullptr);
    prompt(x, 966, "B", "Esc", "Back", &g_footer_back);
    if (rm_exit_prompt()) { armory_try(-1); rm_exit(); return; }
    for (int k = 0; k < 12; k++) {
        if (!pressed(base + k)) continue;
        if (!ready || k >= ARM_NSLOTS) { sound(PS_ERROR); continue; }
        sound(PS_SELECT);
        g_arm_slot = k; g_arm_family = -1; g_arm_scroll = 0;
        g_rpage = RP_ARM_ITEMS;
        std::vector<int> rows;                       // (the focus on what is worn)
        arm_rows(k, -1, rows);
        int w = armory_worn(ARM_SLOTS[k]), at = 0;
        for (int r = 0; r < (int)rows.size(); r++)
            if (rows[r] == w || (k == 0 && w >= 0 && armory_items()[rows[r]].family == armory_items()[w].family)) at = r;
        g_focus_after = at;
    }
}

// the description under the Spartan: the name, where its price comes from, what it needs (met or not), its cost
static void arm_describe(int i, float y) {
    const arm_item& it = armory_items()[i];
    const char* me = me_name();
    g_dl->AddRectFilled(P(815, y), P(1515, y + 222), A(IM_COL32(12, 16, 20, 205)));
    g_dl->AddRect(P(815, y), P(1515, y + 222), A(IM_COL32(150, 158, 166, 80)), 0, 0, U(1));
    bool helmets = g_rpage == RP_ARM_ITEMS && g_arm_slot == 0;
    int st = helmets ? arm_family_state(i) : armory_state(i, me);
    text(g_fl, 30, 830, y + 8, C_TEXT, it.name.c_str());
    arm_state_text(1500, y + 12, 24, st, it.cost, true);
    if (helmets) {                                   // (a helmet: how many of its variants are owned)
        std::vector<int> v;
        arm_rows(0, it.family, v);
        int own = 0;
        for (int j : v) own += armory_state(j, me) >= ARM_OWNED;
        char c[48];
        sprintf_s(c, "%d of %d owned", own, (int)v.size());
        text(g_fs, 19, 1500, y + 48, IM_COL32(176, 182, 188, 220), c, 2);
    }
    bool mcc = it.id.rfind("mcc_", 0) == 0 || it.id == "chest_01" || it.id == "chest_02";   // (never in the 2010 Armory)
    const char* src = mcc ? "Added by MCC: Proving Grounds' own price"
                    : it.ours ? "Not sold for credits in 2010: Proving Grounds' own price"
                    : it.def ? "Every Spartan's from the start" : "Halo: Reach's own price and rank";
    text(g_fs, 19, 830, y + 48, IM_COL32(176, 182, 188, 220), src);
    text(g_fl, 20, 830, y + 80, IM_COL32(176, 182, 188, 220), "PREREQUISITES");
    int step = 0;
    armory_me(me, &step, nullptr, nullptr);
    bool rank_ok = step >= it.gate_step;
    auto met = [&](float yy, bool ok) {
        text(g_fl, 20, 1500, yy, ok ? IM_COL32(150, 214, 120, 255) : IM_COL32(226, 120, 96, 255), ok ? "MET" : "NOT MET", 2);
    };
    text(g_fl, 22, 830, y + 106, C_TEXT, ("Rank: " + it.gate).c_str());
    met(y + 107, rank_ok);
    if (!it.needs.empty()) {
        int have = 0;
        for (int n : it.needs) have += armory_state(n, me) >= ARM_OWNED;
        std::string need = it.needs.size() == 1 ? "Requires: " + armory_items()[it.needs[0]].name
                                                : "Requires: " + std::to_string(it.needs.size()) + " other items (" +
                                                      std::to_string(have) + " owned)";
        text(g_fl, 22, 830, y + 136, C_TEXT, need.c_str());
        met(y + 137, have == (int)it.needs.size());
    }
    g_dl->AddLine(P(827, y + 172), P(1503, y + 172), A(IM_COL32(150, 158, 166, 60)), U(1));
    int bal = armory_balance(me);
    std::string cost = it.autobuy ? "Earned by reaching the rank" : "COST  " + (it.cost ? cr_text(it.cost) + " cR" : std::string("FREE"));
    text(g_fl, 22, 830, y + 182, C_TEXT, cost.c_str());
    text(g_fl, 22, 1500, y + 182, it.cost > bal && st == ARM_FOR_SALE ? IM_COL32(226, 120, 96, 255) : C_DIM,
         ("You have " + cr_text(bal) + " cR").c_str(), 2);
}

// A on an item: the helmet list opens a family; else buy (asked first), equip, or nothing when locked
static void arm_act(int i) {
    const char* me = me_name();
    if (g_rpage == RP_ARM_ITEMS && g_arm_slot == 0) {
        sound(PS_SELECT);
        g_arm_family = armory_items()[i].family;
        g_rpage = RP_ARM_FAMILY;
        std::vector<int> rows;
        arm_rows(0, g_arm_family, rows);
        int w = armory_worn("helmet"), at = 0;
        for (int r = 0; r < (int)rows.size(); r++) if (rows[r] == w) at = r;
        g_focus_after = at;
        return;
    }
    int st = armory_state(i, me);
    if (st == ARM_EQUIPPED) { sound(PS_SELECT); return; }
    if (st == ARM_OWNED) {
        if (armory_equip(i, me)) { sound(PS_SELECT); g_arm_note = "Equipped: " + armory_items()[i].name; g_arm_note_t = ImGui::GetTime(); }
        return;
    }
    if (st == ARM_FOR_SALE && armory_items()[i].cost <= armory_balance(me) && !armory_items()[i].autobuy) {
        sound(PS_SELECT);
        g_arm_buy = i;
        g_arm_back_focus = g_focus;
        g_focus_after = 0;
        return;
    }
    sound(PS_ERROR);                                 // (locked, or too few credits: nothing happens)
}

// the purchase, asked about first: PURCHASE AND EQUIP or CANCEL
static void arm_confirm() {
    const arm_item& it = armory_items()[g_arm_buy];
    g_dl->AddRectFilled(P(0, 0), P(1920, 1080), A(IM_COL32(0, 0, 0, 120)));
    g_dl->AddRectFilledMultiColor(P(600, 330), P(1320, 700), A(IM_COL32(34, 46, 58, 245)), A(IM_COL32(26, 36, 46, 245)),
                                  A(IM_COL32(14, 20, 26, 245)), A(IM_COL32(20, 28, 36, 245)));
    g_dl->AddRect(P(600, 330), P(1320, 700), A(IM_COL32(170, 190, 210, 120)), 0, 0, U(1.2f));
    rm_diamonds(648, 378, 44, IM_COL32(120, 176, 230, 255));
    text(g_fl, 40, 690, 352, C_TEXT, "PURCHASE");
    text(g_fl, 30, 630, 420, C_TEXT, it.name.c_str());
    int bal = armory_balance(me_name());
    text(g_fl, 24, 630, 466, C_DIM, ("Cost: " + cr_text(it.cost) + " cR").c_str());
    text(g_fl, 24, 630, 498, C_DIM, ("Left after: " + cr_text(bal - it.cost) + " cR").c_str());
    int base = (int)g_items.size();
    bool f0 = item(630, 552, 1290, 594), f1 = item(630, 600, 1290, 642);
    rm_row(630, 552, 1290, 594, f0, "PURCHASE AND EQUIP");
    rm_row(630, 600, 1290, 642, f1, "CANCEL");
    float x = prompt(630, 652, "A", "Enter", "Select", nullptr);
    prompt(x, 652, "B", "Esc", "Cancel", &g_footer_back);
    if (pressed(base + 0)) {
        if (armory_buy(g_arm_buy, me_name())) {
            armory_equip(g_arm_buy, me_name());
            sound(PS_SELECT);
            g_arm_note = "Purchased and equipped: " + it.name;
        } else {
            sound(PS_ERROR);
            g_arm_note = "Not purchased: " + it.name;
        }
        g_arm_note_t = ImGui::GetTime();
        g_arm_buy = -1;
        g_focus_after = g_arm_back_focus;
    }
    if (pressed(base + 1)) { sound(PS_BACK); g_arm_buy = -1; g_focus_after = g_arm_back_focus; }
}

static void rm_arm_items(pg_env& e, float t) {
    (void)t;
    bool fam = g_rpage == RP_ARM_FAMILY;
    if (!arm_ready()) { rm_small_header(ARM_TITLE[g_arm_slot], "ARMORY \xC2\xB7 MENU"); rm_band(); return; }
    std::vector<int> rows;
    arm_rows(g_arm_slot, fam ? g_arm_family : -1, rows);
    if (rows.empty()) { g_rpage = RP_ARMORY; return; }
    const std::vector<arm_item>& it = armory_items();
    std::string title = fam ? it[rows[0]].name : ARM_TITLE[g_arm_slot];
    for (auto& ch : title) ch = (char)toupper((unsigned char)ch);
    rm_small_header(title.c_str(), fam ? "HELMET \xC2\xB7 ARMORY \xC2\xB7 MENU" : "ARMORY \xC2\xB7 MENU");
    bool asking = g_arm_buy >= 0;
    bool inert_was = g_inert;
    if (asking) g_inert = true;
    // the list, 15 rows at a time, scrolled to keep the focus in view
    const int V = 15;
    int n = (int)rows.size(), base = (int)g_items.size();
    int f = (asking ? g_arm_back_focus : g_focus) - base;   // (the dialog has the focus while it is up)
    if (f < 0 || f >= n) f = 0;
    if (f < g_arm_scroll) g_arm_scroll = f;
    if (f >= g_arm_scroll + V) g_arm_scroll = f - V + 1;
    if (g_arm_scroll > (n > V ? n - V : 0)) g_arm_scroll = n > V ? n - V : 0;
    int focus = -1;
    for (int k = 0; k < n; k++) {
        bool shown = k >= g_arm_scroll && k < g_arm_scroll + V;
        float y = 145 + 41.0f * (k - g_arm_scroll);
        bool fo = shown ? item(390, y, 775, y + 38) : item(-2000, -2000, -1990, -1990);   // (rows out of view: never
        if (fo) focus = k;                                                                   // under the mouse)
        if (!shown) continue;
        int i = rows[k];
        std::string label = fam && it[i].variant > 0 ? it[i].name.substr(it[i].name.find(" / ") != std::string::npos
                                                                         ? it[i].name.find(" / ") + 3 : 0)
                                                     : it[i].name;
        if (fam && it[i].variant == 0) label += " (BASE)";
        int st = !fam && g_arm_slot == 0 ? arm_family_state(i) : armory_state(i, me_name());
        bool lit = st >= ARM_FOR_SALE;
        rm_row(390, y, 795, y + 38, fo, "", lit || fo);
        arm_state_text(785, y + 8, 21, st, it[i].cost, fo);   // (the state at the row's right, the name cut before it)
        g_dl->PushClipRect(P(390, y), P(st >= ARM_OWNED ? 640.0f : 655.0f, y + 38), true);
        ImU32 lc = !(lit || fo) ? IM_COL32(150, 156, 162, 120) : fo ? C_TEXT : C_DIM;
        text(g_fl, 25, 400, y + 5, lc, label.c_str());
        g_dl->PopClipRect();
    }
    if (g_arm_scroll > 0)                            // (more above, more below: small arrows by the list)
        g_dl->AddTriangleFilled(P(592, 128), P(582, 140), P(602, 140), A(C_DIM));
    if (g_arm_scroll + V < n)
        g_dl->AddTriangleFilled(P(582, 150 + 41.0f * V), P(602, 150 + 41.0f * V), P(592, 162 + 41.0f * V), A(C_DIM));
    int sel = rows[focus >= 0 ? focus : f];
    armory_try(sel);
    arm_figure(e, 815, 140, 1515, 585);
    arm_describe(sel, 600);
    if (!g_arm_note.empty() && ImGui::GetTime() - g_arm_note_t < 4.0)
        text(g_fl, 22, 1515, 968, C_GOLD, g_arm_note.c_str(), 2);
    g_inert = inert_was;
    if (asking) {
        rm_band(armory_balance(me_name()));
        arm_confirm();
        return;
    }
    rm_band(armory_balance(me_name()));
    int st = !fam && g_arm_slot == 0 ? 99 : armory_state(sel, me_name());
    const char* a = st == 99 ? "Select" : st == ARM_OWNED ? "Equip" : st == ARM_FOR_SALE && !it[sel].autobuy ? "Purchase" : nullptr;
    float x = 318;
    if (a) x = prompt(x, 966, "A", "Enter", a, nullptr);
    x = prompt(x, 966, "B", "Esc", "Back", &g_footer_back);
    prompt(x, 966, "RS", "Q E", "Turn", nullptr);
    if (rm_exit_prompt()) { armory_try(-1); rm_exit(); return; }
    for (int k = 0; k < n; k++) if (pressed(base + k)) arm_act(rows[k]);
}

// S_MENU's frame while one of Reach's pages is up (the invite list over it, the page held still under it)
static void reach_menu_screen(pg_env& e, float t) {
    g_inert = g_invite;
    switch (g_rpage) {
    case RP_TITLE: rm_title(e, t); break;
    case RP_MAIN: rm_main(e, t); break;
    case RP_MM: rm_mm(e, t); break;
    case RP_PLAYLIST: rm_playlist(e, t); break;
    case RP_RESTRICT: rm_restrict(e, t); break;
    case RP_PSYCH: rm_psych(e, t); break;
    case RP_MENU: rm_menu(e, t); break;
    case RP_SR: rm_sr(e, t); break;
    case RP_CAREER: rm_career(e, t); break;
    case RP_DIFF: rm_diff(e, t); break;
    case RP_ARMORY: rm_armory(e, t); break;
    case RP_ARM_ITEMS: case RP_ARM_FAMILY: rm_arm_items(e, t); break;
    default: break;
    }
    g_inert = false;
    if (g_invite) invite_list(e);
}

// B / Esc on Reach's pages: one page back (false: the title, Proving Grounds closes)
static bool rmenu_back() {
    switch (g_rpage) {
    case RP_TITLE: return false;
    case RP_MAIN: g_rpage = RP_TITLE; g_focus_after = 1; return true;
    case RP_MM: g_rpage = RP_MAIN; g_focus_after = 1; return true;
    case RP_PLAYLIST:
        if (g_rm_col == 1) { g_rm_col = 0; g_focus_after = g_rm_cat; return true; }
        g_rpage = RP_MM; g_focus_after = 0; return true;
    case RP_RESTRICT: g_rpage = RP_MM; g_focus_after = 1; return true;
    case RP_PSYCH: g_rpage = RP_MM; g_focus_after = 2; return true;
    case RP_OPTIONS: g_rpage = g_rpage_from; g_focus_after = g_rpage == RP_MENU ? 8 : 0; return true;
    case RP_MENU: g_rpage = g_rmenu_from; g_focus_after = 0; return true;
    case RP_SR: g_rpage = RP_MENU; g_focus_after = 1; return true;
    case RP_CAREER: g_rpage = RP_SR; g_focus_after = 0; return true;
    case RP_DIFF: g_rpage = RP_CAREER; g_focus_after = g_diff_mode ? 3 : 0; return true;
    case RP_ARMORY: armory_try(-1); g_rpage = RP_MENU; g_focus_after = 0; return true;
    case RP_ARM_ITEMS:
        if (g_arm_buy >= 0) { g_arm_buy = -1; g_focus_after = g_arm_back_focus; return true; }
        armory_try(-1); g_rpage = RP_ARMORY; g_focus_after = g_arm_slot; return true;
    case RP_ARM_FAMILY: {
        if (g_arm_buy >= 0) { g_arm_buy = -1; g_focus_after = g_arm_back_focus; return true; }
        std::vector<int> rows;                       // (back on the family's own row)
        arm_rows(0, -1, rows);
        g_rpage = RP_ARM_ITEMS; g_focus_after = 0;
        for (int r = 0; r < (int)rows.size(); r++) if (armory_items()[rows[r]].family == g_arm_family) g_focus_after = r;
        return true;
    }
    }
    return false;
}
