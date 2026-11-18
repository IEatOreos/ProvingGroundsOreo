// pg_preview.cpp (custom, Nov 16): Proving Grounds' screens drawn offscreen to PNGs, for checking them without MCC.
// Links the real proving_grounds.cpp and bots_panel.cpp; MCC's side (pg_lobby.cpp) is stood in for by the Halo: Reach
// lists MCC gave in the owner's lobby test (Nov 16). The pool is a copy (the owner's own files are only read).
// usage: native\bin\pg_preview.exe <out folder>   (build: native\build_pg_preview.bat)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <d3d11.h>
#include <wincodec.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include "third_party/imgui/imgui.h"
#include "third_party/imgui/imgui_impl_dx11.h"
#include "bots_panel.h"
#include "proving_grounds.h"
#include "model_view.h"

void pg_preview_stage(int which, float t, pg_env& e);
void pg_preview_odds(const hb_roster& r);

void logf(const char* fmt, ...) {
    va_list a; va_start(a, fmt); vprintf(fmt, a); va_end(a); printf("\n");
}
const char* mcc_player_name() { return "TheNobleOreo"; }
// (Nov 17) a stand-in for the person's look as MCC's lookup gives it (report.cpp): an emblem's five and a nameplate
bool mcc_player_look(int32_t emblem[5], int* nameplate) {
    const int32_t e[5] = { 149, 602, 17, 27, 29 };
    memcpy(emblem, e, sizeof e);
    *nameplate = nameplates_count() > 40 ? nameplate_id_at(40) : -1;
    return true;
}
// (Nov 17) MCC's session as session_watch.cpp reads it: the player on Red; with PG_FRIEND set, a friend who joined,
// MCC's team PG_FRIEND (0, 1, or -1 not yet on one) and a look of his own
int mcc_player_team() { return 0; }
int mcc_session_people(uint64_t* ids, char (*names)[32], int* teams, int cap) {
    char v[8];
    if (cap < 1 || !GetEnvironmentVariableA("PG_FRIEND", v, sizeof v)) return 0;
    if (ids) ids[0] = 0x0009000000000002ull;
    if (names) strcpy_s(names[0], 32, "A Friend");
    if (teams) teams[0] = atoi(v);
    return 1;
}
bool mcc_person_look(uint64_t id, int32_t emblem[5], int* nameplate) {
    if (id != 0x0009000000000002ull) return false;
    const int32_t e[5] = { 80, 525, 19, 26, 12 };
    memcpy(emblem, e, sizeof e);
    *nameplate = nameplates_count() > 90 ? nameplate_id_at(90) : -1;
    return true;
}

// ---- MCC's side, stood in for (the owner's lobby test, Nov 16: native\bin\lobby_library.txt)
struct fake { int id, kind, cat, teams; const char* name; const char* key; };
static const fake MAPS[] = {
    {5082, 1, -1, -1, "$HReach_MPMap_R-1_Title", "HReachMP_Boardwalk"}, {5083, 1, -1, -1, "$HReach_MPMap_R-2_Title", "HReachMP_Boneyard"},
    {5084, 1, -1, -1, "$HReach_MPMap_R-3_Title", "HReachMP_Countdown"}, {5085, 1, -1, -1, "$HReach_MPMap_R-4_Title", "HReachMP_Powerhouse"},
    {5086, 1, -1, -1, "$HReach_MPMap_R-5_Title", "HReachMP_Reflection"}, {5087, 1, -1, -1, "$HReach_MPMap_R-6_Title", "HReachMP_Spire"},
    {5088, 1, -1, -1, "$HReach_MPMap_R-7_Title", "HReachMP_SwordBase"}, {5089, 1, -1, -1, "$HReach_MPMap_R-8_Title", "HReachMP_Zealot"},
    {5090, 1, -1, -1, "$HReach_MPMap_R-9_Title", "HReachMP_Anchor9"}, {5091, 1, -1, -1, "$HReach_MPMap_R-10_Title", "HReachMP_Breakpoint"},
    {5092, 1, -1, -1, "$HReach_MPMap_R-11_Title", "HReachMP_Tempest"}, {5093, 1, -1, -1, "$HReach_MPMap_R-12_Title", "HReachMP_Condemned"},
    {5094, 1, -1, -1, "$HReach_MPMap_R-13_Title", "HReachMP_Highlands"}, {5099, 1, -1, -1, "$HReach_MPMap_R-18_Title", "HReachMP_HighNoon"},
    {5097, 1, -1, -1, "$HReach_MPMap_R-16_Title", "HReachMP_Ridgeline"}, {5100, 1, -1, -1, "$HReach_MPMap_R-19_Title", "HReachMP_Breakneck"},
    {5106, 2, -1, -1, "$HReach_MPMap_R-21_Title", "HReachMP_ForgeWorld"}, {5107, 2, -1, -1, "$HReach_MPMap_R-22_Title", "HReachMP_ForgeWorld"},
    {5108, 2, -1, -1, "$HReach_MPMap_R-23_Title", "HReachMP_ForgeWorld"}, {5109, 2, -1, -1, "$HReach_MPMap_R-24_Title", "HReachMP_ForgeWorld"},
    {5110, 2, -1, -1, "$HReach_MPMap_R-25_Title", "HReachMP_ForgeWorld"}, {5102, 2, -1, -1, "Beaver Creek Anniversary", "HReachMP_BattleCanyon"},
    {5103, 2, -1, -1, "Damnation Anniversary", "HReachMP_Penance"}, {5104, 2, -1, -1, "Hang 'Em High Anniv", "HReachMP_HighNoon"},
    {5105, 2, -1, -1, "Headlong Anniversary", "HReachMP_Breakneck"}, {5111, 2, -1, -1, "Prisoner Anniversary", "HReachMP_Solitary"},
    {5112, 2, -1, -1, "Timberland Anniversary", "HReachMP_Ridgeline"} };
static const fake GTS[] = {
    // (team flags as the owner's MCC read them, lobby_library.txt Nov 16: SWAT, King, Crazy King, Oddball free for all)
    {5160, 2, 1, 1, "TU TEAM SLAYER DMR", "CG_Slayer"}, {5182, 2, 1, 0, "SLAYER", "CG_Slayer"}, {5187, 2, 1, 0, "SWAT", "CG_Slayer"},
    {5146, 2, 0, 1, "CAPTURE THE FLAG", "CG_CaptureTheFlag"}, {5147, 2, 0, 1, "ONE FLAG CTF", "CG_CaptureTheFlag"},
    {5148, 2, 0, 1, "MULTI FLAG CTF", "CG_CaptureTheFlag"}, {5176, 2, 3, 0, "KING OF THE HILL", "CG_KingOfTheHill"},
    {5177, 2, 3, 0, "CRAZY KING", "CG_KingOfTheHill"}, {5178, 2, 2, 0, "ODDBALL", "CG_OddBall"},
    {5150, 2, 22, 0, "HEADHUNTER", "CG_HeadHunter"}, {5145, 2, 16, 1, "ONE BOMB ASSAULT", "CG_Assault"},
    {5144, 2, 16, 1, "NEUTRAL BOMB ASSAULT", "CG_Assault"}, {5186, 2, 21, 1, "STOCKPILE", "CG_Stockpile"},
    {5190, 2, 15, 1, "TERRITORIES", "CG_Territories"}, {5188, 2, 15, 1, "3-PLOT TERRITORIES", "CG_Territories"},
    {5156, 2, 0, 1, "TU MULTI FLAG CTF", "CG_CaptureTheFlag"},
    // (Nov 16) the owner's own, as MCC should list them (kind 3), two with MCC's built-in names
    {6001, 3, 1, 1, "TU TEAM SLAYER DMR", "CG_Slayer"}, {6002, 3, 0, 1, "TU MULTI FLAG CTF", "CG_CaptureTheFlag"},
    {6003, 3, 0, 1, "TU MULTI FLAG CTF (4-10)", "CG_CaptureTheFlag"}, {6004, 3, 0, 1, "TU ONE FLAG CTF (4-10)", "CG_CaptureTheFlag"},
    {6005, 3, 16, 1, "TU NEUTRAL BOMB ASSAULT (4-10)", "CG_Assault"}, {6006, 3, 3, 1, "TU TEAM CRAZY KING (4-10)", "CG_KingOfTheHill"},
    {6007, 3, 2, 1, "TU TEAM ODDBALL", "CG_OddBall"}, {6008, 3, 3, 0, "TU FFA CRAZY KING", "CG_KingOfTheHill"},
    {6009, 3, 15, 1, "CTU 5-PLOT TERRITORIES", "CG_Territories"} };
static void put(pg_entry& p, const fake& f) {
    memset(&p, 0, sizeof p);
    p.id = f.id; p.kind = f.kind; p.category = f.cat; p.teams = f.teams;
    strcpy_s(p.name, f.name); strcpy_s(p.key, f.key);
}
bool pg_lobby_live() { return true; }
int pg_lobby_maps(pg_entry* out, int cap) { int n = 0; for (const fake& f : MAPS) if (n < cap) put(out[n++], f); return n; }
int pg_lobby_gametypes(pg_entry* out, int cap) { int n = 0; for (const fake& f : GTS) if (n < cap) put(out[n++], f); return n; }
uint32_t pg_lobby_seq() { return 1; }
static int g_ticket;
int pg_lobby_check(const int*, const int*, int) { return ++g_ticket; }
bool pg_lobby_checked(int ticket, uint8_t* ok, int n) { for (int i = 0; i < n; i++) ok[i] = 1; return ticket == g_ticket; }
void pg_lobby_launch(int, int) {}
int pg_lobby_launch_state(char* why, int cap) { if (why) why[0] = 0; return 1; }
// (Nov 18) the link to a joined friend's copy (pg_link.cpp): a loopback here, so pg_11 draws the host's state as a
// friend's copy follows it
static unsigned char g_loop[PGS_MAX];
static uint32_t g_loop_n;
void pg_link_set_state(const void* d, uint32_t n) { if (n <= PGS_MAX) { memcpy(g_loop, d, n); g_loop_n = n; } }
uint32_t pg_link_state(void* out, uint32_t cap, uint64_t* age_ms) {
    *age_ms = g_loop_n ? 0 : ~0ull;
    if (!g_loop_n || g_loop_n > cap) return 0;
    memcpy(out, g_loop, g_loop_n);
    return g_loop_n;
}
void pg_link_send_vote(uint32_t, int, const char*) {}
bool pg_link_vote(char*, int, uint32_t*, int*) { return false; }

// ---- offscreen drawing
static ID3D11Device* g_dev;
static ID3D11DeviceContext* g_ctx;
static unsigned long long make_texture(int w, int h, const unsigned char* rgba) {
    D3D11_TEXTURE2D_DESC d{};
    d.Width = w; d.Height = h; d.MipLevels = 1; d.ArraySize = 1; d.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    d.SampleDesc.Count = 1; d.Usage = D3D11_USAGE_DEFAULT; d.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA sd{ rgba, (UINT)w * 4, 0 };
    ID3D11Texture2D* t = nullptr;
    ID3D11ShaderResourceView* v = nullptr;
    if (FAILED(g_dev->CreateTexture2D(&d, &sd, &t))) return 0;
    g_dev->CreateShaderResourceView(t, nullptr, &v);
    t->Release();
    return (unsigned long long)(intptr_t)v;
}

// (Nov 17) the player card's Spartan: bots_panel.cpp's own figure, on this device (model_view.cpp)
static unsigned long long pv_render(const wchar_t* path, const mv_pick* picks, int n, const mv_colors& c, float yaw,
                                    int w, int h) {
    return mv_render(g_dev, g_ctx, path, picks, n, c, yaw, w, h);
}
static bool pv_has(const wchar_t* path, const char* region, const char* perm) { return mv_has(g_dev, path, region, perm); }
static unsigned long long pv_figure(const char* name, bool bot, float yaw, int w, int h) {
    bool known = false;                                      // (a bot without a profile: none, so the preview never
    for (int i = 0; i < profiles_count(); i++) known |= !_stricmp(profile_name(i), name);   // adds one to the owner's file)
    if (bot && !known) return 0;
    bots_panel_env be{};
    be.make_texture = make_texture; be.render_model = pv_render; be.model_has = pv_has;
    be.model_zoom = mv_set_zoom; be.model_head = mv_head; be.model_headroom = mv_set_headroom; be.title = 5;
    return bot ? bot_figure(be, name, yaw, w, h) : person_figure(be, yaw, w, h);
}

static bool save_png(const wchar_t* path, const unsigned char* rgba, int w, int h, int pitch) {
    IWICImagingFactory* f = nullptr;
    if (FAILED(CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&f)))) return false;
    IWICStream* s = nullptr; IWICBitmapEncoder* enc = nullptr; IWICBitmapFrameEncode* fr = nullptr;
    bool ok = SUCCEEDED(f->CreateStream(&s)) && SUCCEEDED(s->InitializeFromFilename(path, GENERIC_WRITE)) &&
              SUCCEEDED(f->CreateEncoder(GUID_ContainerFormatPng, nullptr, &enc)) && SUCCEEDED(enc->Initialize(s, WICBitmapEncoderNoCache)) &&
              SUCCEEDED(enc->CreateNewFrame(&fr, nullptr)) && SUCCEEDED(fr->Initialize(nullptr)) && SUCCEEDED(fr->SetSize(w, h));
    WICPixelFormatGUID fmt = GUID_WICPixelFormat32bppBGRA;   // (the PNG encoder's; the caller's pixels are BGRA)
    ok = ok && SUCCEEDED(fr->SetPixelFormat(&fmt)) && IsEqualGUID(fmt, GUID_WICPixelFormat32bppBGRA) &&
         SUCCEEDED(fr->WritePixels(h, pitch, pitch * h, (BYTE*)rgba)) && SUCCEEDED(fr->Commit()) && SUCCEEDED(enc->Commit());
    if (fr) fr->Release(); if (enc) enc->Release(); if (s) s->Release(); f->Release();
    return ok;
}

static void copy_file(const wchar_t* from_dir, const wchar_t* to_dir, const wchar_t* name) {
    wchar_t a[MAX_PATH], b[MAX_PATH];
    swprintf_s(a, L"%s%s", from_dir, name); swprintf_s(b, L"%s%s", to_dir, name);
    CopyFileW(a, b, FALSE);
}

void pg_preview_lists();

int main(int argc, char** argv) {
    if (argc < 2) { printf("usage: pg_preview <out folder> | pg_preview lists (PG_INI=<scratch ini>)\n"); return 2; }
    if (!strcmp(argv[1], "lists")) { pg_preview_lists(); return 0; }
    CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    wchar_t out[MAX_PATH], bin[MAX_PATH], tmp[MAX_PATH];
    swprintf_s(out, L"%S", argv[1]);
    GetModuleFileNameW(nullptr, bin, MAX_PATH);
    *(wcsrchr(bin, L'\\') + 1) = 0;                          // native\bin\ (this exe's folder)
    swprintf_s(tmp, L"%spg_preview_pool\\", bin);
    CreateDirectoryW(tmp, nullptr);
    for (const wchar_t* f : { L"bot_pool.txt", L"bot_pool_saved.ini" }) copy_file(bin, tmp, f);
    wchar_t prof[MAX_PATH];
    swprintf_s(prof, L"%sbot_profiles.ini", bin);
    bots_panel_profiles(prof);
    bot_pool_load(tmp);
    {   // (Nov 17) MCC's nameplates for the bots' rows, as pool_test finds MCC (MCC_ROOT, else the owner's Steam library)
        wchar_t mcc[300];
        DWORD n = GetEnvironmentVariableW(L"MCC_ROOT", mcc, 300);
        if (!n) wcscpy_s(mcc, L"F:\\SteamLibrary\\steamapps\\common\\Halo The Master Chief Collection\\");
        else if (mcc[n - 1] != L'\\') wcscat_s(mcc, L"\\");
        nameplates_load(mcc);
    }

    D3D_FEATURE_LEVEL fl;
    if (FAILED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &g_dev, &fl, &g_ctx)) &&
        FAILED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, nullptr, 0, D3D11_SDK_VERSION, &g_dev, &fl, &g_ctx))) {
        printf("no D3D11 device\n"); return 1;
    }
    const int W = 1920, H = 1080;
    D3D11_TEXTURE2D_DESC td{};
    td.Width = W; td.Height = H; td.MipLevels = 1; td.ArraySize = 1; td.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    td.SampleDesc.Count = 1; td.Usage = D3D11_USAGE_DEFAULT; td.BindFlags = D3D11_BIND_RENDER_TARGET;
    ID3D11Texture2D* rt = nullptr; ID3D11RenderTargetView* rtv = nullptr; ID3D11Texture2D* st = nullptr;
    g_dev->CreateTexture2D(&td, nullptr, &rt);
    g_dev->CreateRenderTargetView(rt, nullptr, &rtv);
    td.Usage = D3D11_USAGE_STAGING; td.BindFlags = 0; td.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    g_dev->CreateTexture2D(&td, nullptr, &st);

    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.IniFilename = nullptr;
    io.DisplaySize = ImVec2((float)W, (float)H);
    ImFontConfig fc; fc.OversampleH = 2;
    ImFont* fs = io.Fonts->AddFontFromFileTTF("C:\\Windows\\Fonts\\bahnschrift.ttf", 22.0f, &fc);
    ImFont* fl2 = io.Fonts->AddFontFromFileTTF("C:\\Windows\\Fonts\\bahnschrift.ttf", 40.0f, &fc);
    if (!fs) fs = fl2 = io.Fonts->AddFontDefault();
    ImGui_ImplDX11_Init(g_dev, g_ctx);
    io.MousePos = ImVec2(-1000, -1000);

    // a backdrop standing in for MCC's menu behind (the Service Record's own header picture when this PC has it)
    wchar_t bdp[MAX_PATH];
    swprintf_s(bdp, L"%sservice_record\\art\\backdrops\\header.jpg", bin);
    int bw = 0, bh = 0;
    unsigned char* bpx = hb_image_rgba(bdp, &bw, &bh);
    unsigned long long backdrop = bpx ? make_texture(bw, bh, bpx) : 0;
    free(bpx);

    hb_roster roster{};
    roster.teams = 2;
    uint32_t bots_on = 1, lidar = 0;
    const char* names[] = { "menu", "invite", "search", "vote", "result", "error", "roster_details", "roster_card",
                            "roster_you", "credits", "challenges", "friend_vote" };
    const float at[] = { 2.0f, 0.5f, 3.2f, 6.0f, 1.5f, 0.5f, 2.0f, 6.0f, 6.0f, 4.4f, 1.0f, 6.0f };
    for (int s = 0; s < 12; s++) {
        pg_env e{};
        e.roster = &roster; e.difficulty = 2; e.scale = 1; e.W = (float)W; e.H = (float)H;
        e.f_label = fl2; e.f_small = fs; e.make_texture = make_texture; e.play_sound = nullptr; e.sounds = 0;
        e.lobby_visible = true; e.bots_enabled = &bots_on; e.lidar_mode = &lidar;
        e.figure = pv_figure;                                  // (Nov 17: the player card's Spartan, as in game)
        bool staged = false;
        for (int frame = 0; frame < 4; frame++) {
            io.DeltaTime = 1.0f / 60;
            ImGui_ImplDX11_NewFrame();
            ImGui::NewFrame();
            if (!staged) { pg_preview_stage(s, at[s], e); staged = true; if (s == 3) pg_preview_odds(roster); }
            if (backdrop) ImGui::GetBackgroundDrawList()->AddImage((ImTextureID)backdrop, ImVec2(0, 0), ImVec2((float)W, (float)H));
            pg_frame(e);
            ImGui::Render();
            float clear[4] = { 0.05f, 0.08f, 0.1f, 1 };
            g_ctx->OMSetRenderTargets(1, &rtv, nullptr);
            g_ctx->ClearRenderTargetView(rtv, clear);
            ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
        }
        g_ctx->CopyResource(st, rt);
        D3D11_MAPPED_SUBRESOURCE m;
        if (SUCCEEDED(g_ctx->Map(st, 0, D3D11_MAP_READ, 0, &m))) {
            unsigned char* p = (unsigned char*)m.pData;
            for (int y = 0; y < H; y++)
                for (int x = 0; x < W; x++) {                   // (opaque, BGRA)
                    unsigned char* q = p + y * m.RowPitch + x * 4;
                    unsigned char r = q[0]; q[0] = q[2]; q[2] = r; q[3] = 255;
                }
            wchar_t path[MAX_PATH];
            swprintf_s(path, L"%s\\pg_%d_%S.png", out, s + 1, names[s]);
            printf("%s %S\n", save_png(path, p, W, H, (int)m.RowPitch) ? "wrote" : "FAILED", path);
            g_ctx->Unmap(st, 0);
        }
    }
    ImGui_ImplDX11_Shutdown();
    ImGui::DestroyContext();
    return 0;
}
