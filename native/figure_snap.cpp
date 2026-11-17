// figure_snap.cpp (custom, Nov 16): each bot's Reach figure as a still picture for the Service Record site
// (tools/service_record.py), drawn by the mod's own 3D bot view (model_view.cpp) the way the bots panel draws it
// (bots_panel.cpp ed_model): the game's own model and textures (native/bin/models/reach_<spartan|elite>.mdl,
// tools/make_models.py), the pieces its Armory roll put on the bot (bot_looks.ini "pieces"), its primary and secondary
// colours and visor tint. MCC need not run: the program makes its own Direct3D 11 device (the graphics card, else
// Windows' software one). The whole figure, turned a little like the customization screen shows it, on a see-through
// background; one PNG a bot, its angles side by side, and figures.tsv (name, file, species, angles, an angle's width and height)
// in the out folder. Read only: bot_looks.ini and the models.
//
// usage: figure_snap.exe <bot_looks.ini> <models folder> <out folder> [width height yaw frames]
#include <windows.h>
#include <d3d11.h>
#include <wincodec.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>
#include "model_view.h"

// Reach's 30 colours, MCC's own values (Data/UI/playercustomization.xml): the same table as bots_panel.cpp REACH_COL
// (tools/test_figure_snap.py checks the two agree), 0 Steel ... 29 Pale
static const unsigned char REACH_RGB[30][3] = {
    {77, 77, 77}, {129, 129, 129}, {204, 204, 204}, {75, 63, 38}, {126, 89, 64}, {176, 141, 121},
    {103, 106, 89}, {108, 119, 74}, {148, 173, 97}, {45, 94, 49}, {71, 141, 87}, {110, 172, 121},
    {36, 108, 105}, {55, 141, 140}, {100, 186, 183}, {47, 71, 99}, {81, 99, 137}, {113, 145, 186},
    {69, 68, 110}, {101, 96, 152}, {115, 113, 160}, {92, 31, 30}, {144, 6, 6}, {197, 115, 117},
    {116, 36, 27}, {209, 114, 70}, {198, 148, 118}, {114, 63, 28}, {171, 119, 8}, {214, 200, 128} };
// the visor tint by the value Reach's Armory writes (bots_panel.cpp REACH_VISOR): Default, Silver, Blue, Gold, Black
static const float REACH_VISOR[5][3] = { {0.80f, 0.56f, 0.16f}, {0.62f, 0.66f, 0.70f}, {0.18f, 0.40f, 0.86f},
                                         {0.92f, 0.74f, 0.18f}, {0.07f, 0.07f, 0.08f} };

struct look { std::string name; bool elite = false; int primary = 0, secondary = 0, visor = -1; std::string pieces; };

static int kv_int(const std::string& kv, const char* key, int def) {
    std::string k = std::string(";") + key + "=";
    std::string s = ";" + kv;
    size_t at = s.find(k);
    return at == std::string::npos ? def : atoi(s.c_str() + at + k.size());
}
static std::string kv_text(const std::string& kv, const char* key) {
    std::string k = std::string(";") + key + "=";
    std::string s = ";" + kv;
    size_t at = s.find(k);
    if (at == std::string::npos) return "";
    size_t from = at + k.size(), to = s.find(';', from);
    return s.substr(from, to == std::string::npos ? std::string::npos : to - from);
}

// every bot's own Reach look (name|reach|own|key=value;...), the last line of a name winning as in the panel
static std::vector<look> read_looks(const wchar_t* path) {
    std::vector<look> out;
    FILE* f = nullptr;
    if (_wfopen_s(&f, path, L"rb") != 0 || !f) return out;
    char line[4096];
    while (fgets(line, sizeof line, f)) {
        std::string s(line);
        while (!s.empty() && (s.back() == '\n' || s.back() == '\r')) s.pop_back();
        size_t a = s.find('|'), b = a == std::string::npos ? a : s.find('|', a + 1), c = b == std::string::npos ? b : s.find('|', b + 1);
        if (c == std::string::npos || s.compare(a + 1, b - a - 1, "reach") || s.compare(b + 1, c - b - 1, "own")) continue;
        look L;
        L.name = s.substr(0, a);
        std::string kv = s.substr(c + 1);
        L.elite = kv_int(kv, "species", 0) == 1;
        L.primary = kv_int(kv, "primary", 0);
        L.secondary = kv_int(kv, "secondary", 0);
        L.visor = kv_int(kv, "visor", -1);
        L.pieces = kv_text(kv, "pieces");
        bool seen = false;
        for (auto& o : out) if (o.name == L.name) { o = L; seen = true; }
        if (!seen) out.push_back(L);
    }
    fclose(f);
    return out;
}

// a file name for a bot: its letters and digits, then a hash of the whole name (two names never share a file)
static std::string file_for(const std::string& name) {
    std::string base;
    for (unsigned char ch : name) base += (isalnum(ch) ? (char)tolower(ch) : '_');
    if (base.size() > 24) base.resize(24);
    unsigned h = 2166136261u;
    for (unsigned char ch : name) { h ^= ch; h *= 16777619u; }
    char buf[16];
    sprintf_s(buf, "_%08x.png", h);
    return base + buf;
}

static void rgb(int i, float out[3]) {
    const unsigned char* c = REACH_RGB[i >= 0 && i < 30 ? i : 0];
    for (int k = 0; k < 3; k++) out[k] = c[k] / 255.0f;
}

// the drawn texture's pixels, BGRA with straight alpha (the 4x resolve leaves the edges premultiplied over
// see-through black; BGRA is what every PNG encoder takes)
static bool read_back(ID3D11Device* dev, ID3D11DeviceContext* ctx, ID3D11ShaderResourceView* srv, std::vector<unsigned char>& px,
                      UINT& w, UINT& h) {
    ID3D11Resource* res = nullptr;
    srv->GetResource(&res);
    ID3D11Texture2D* tex = nullptr;
    res->QueryInterface(__uuidof(ID3D11Texture2D), (void**)&tex);
    res->Release();
    D3D11_TEXTURE2D_DESC d;
    tex->GetDesc(&d);
    d.MipLevels = 1; d.Usage = D3D11_USAGE_STAGING; d.BindFlags = 0; d.CPUAccessFlags = D3D11_CPU_ACCESS_READ; d.MiscFlags = 0;
    d.SampleDesc.Count = 1; d.SampleDesc.Quality = 0;
    ID3D11Texture2D* st = nullptr;
    if (FAILED(dev->CreateTexture2D(&d, nullptr, &st))) { tex->Release(); return false; }
    ctx->CopySubresourceRegion(st, 0, 0, 0, 0, tex, 0, nullptr);
    tex->Release();
    D3D11_MAPPED_SUBRESOURCE m;
    if (FAILED(ctx->Map(st, 0, D3D11_MAP_READ, 0, &m))) { st->Release(); return false; }
    w = d.Width; h = d.Height;
    px.assign((size_t)w * h * 4, 0);
    for (UINT y = 0; y < h; y++) {
        const unsigned char* row = (const unsigned char*)m.pData + (size_t)y * m.RowPitch;
        unsigned char* o = &px[(size_t)y * w * 4];
        for (UINT x = 0; x < w; x++) {
            unsigned a = row[x * 4 + 3];
            for (int k = 0; k < 3; k++) {
                unsigned v = a ? (row[x * 4 + k] * 255u + a / 2) / a : 0;
                o[x * 4 + 2 - k] = (unsigned char)(v > 255 ? 255 : v);
            }
            o[x * 4 + 3] = (unsigned char)a;
        }
    }
    ctx->Unmap(st, 0);
    st->Release();
    return true;
}

static bool write_png(const std::vector<unsigned char>& px, UINT w, UINT h, const std::wstring& path) {
    IWICImagingFactory* wic = nullptr;
    if (FAILED(CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&wic)))) return false;
    std::wstring tmp = path + L".tmp";
    IWICStream* stream = nullptr; IWICBitmapEncoder* enc = nullptr; IWICBitmapFrameEncode* frame = nullptr;
    bool ok = SUCCEEDED(wic->CreateStream(&stream)) && SUCCEEDED(stream->InitializeFromFilename(tmp.c_str(), GENERIC_WRITE)) &&
              SUCCEEDED(wic->CreateEncoder(GUID_ContainerFormatPng, nullptr, &enc)) &&
              SUCCEEDED(enc->Initialize(stream, WICBitmapEncoderNoCache)) && SUCCEEDED(enc->CreateNewFrame(&frame, nullptr)) &&
              SUCCEEDED(frame->Initialize(nullptr)) && SUCCEEDED(frame->SetSize(w, h));
    WICPixelFormatGUID fmt = GUID_WICPixelFormat32bppBGRA;
    ok = ok && SUCCEEDED(frame->SetPixelFormat(&fmt)) && IsEqualGUID(fmt, GUID_WICPixelFormat32bppBGRA) &&
         SUCCEEDED(frame->WritePixels(h, w * 4, (UINT)px.size(), (BYTE*)px.data())) &&
         SUCCEEDED(frame->Commit()) && SUCCEEDED(enc->Commit());
    if (frame) frame->Release();
    if (enc) enc->Release();
    if (stream) stream->Release();
    wic->Release();
    if (ok) ok = MoveFileExW(tmp.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING) != 0;
    else DeleteFileW(tmp.c_str());
    return ok;
}

// The turntable as one strip, the angles side by side: every angle cut by the same box (so the figure neither jumps
// nor shrinks as it turns), its sides even about the frame's middle, where the model's middle is drawn (so the body
// stays centred and a held sword or a wide stance just reaches further out), 6 pixels round all that was drawn.
// Returns the width of one angle, 0 if nothing was drawn.
static UINT strip(const std::vector<std::vector<unsigned char>>& frames, UINT w, UINT h, std::vector<unsigned char>& out, UINT& ch) {
    int half = -1, y0 = (int)h, y1 = -1, mid = (int)w / 2;
    for (const auto& px : frames)
        for (int y = 0; y < (int)h; y++)
            for (int x = 0; x < (int)w; x++)
                if (px[((size_t)y * w + x) * 4 + 3]) {
                    int d = x < mid ? mid - x : x - mid + 1;
                    if (d > half) half = d;
                    if (y < y0) y0 = y;
                    if (y > y1) y1 = y;
                }
    if (half < 0) return 0;
    half = half + 6 < mid ? half + 6 : mid;
    y0 = y0 > 6 ? y0 - 6 : 0; y1 = y1 + 6 < (int)h ? y1 + 6 : (int)h - 1;
    UINT cw = (UINT)(2 * half);
    ch = (UINT)(y1 - y0 + 1);
    size_t n = frames.size();
    out.assign((size_t)cw * n * ch * 4, 0);
    for (size_t f = 0; f < n; f++)
        for (UINT y = 0; y < ch; y++)
            memcpy(&out[(((size_t)y * cw * n) + f * cw) * 4], &frames[f][(((size_t)(y0 + y)) * w + (mid - half)) * 4], (size_t)cw * 4);
    return cw;
}

static std::wstring wide(const std::string& s) {
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, nullptr, 0);
    std::wstring w(n ? n - 1 : 0, L'\0');
    if (n) MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, &w[0], n);
    return w;
}

int wmain(int argc, wchar_t** argv) {
    if (argc < 4) { fwprintf(stderr, L"usage: figure_snap.exe <bot_looks.ini> <models folder> <out folder> [width height yaw frames]\n"); return 2; }
    int W = argc > 5 ? _wtoi(argv[4]) : 480, H = argc > 5 ? _wtoi(argv[5]) : 640;
    float yaw = argc > 6 ? (float)_wtof(argv[6]) : 0.35f;
    int N = argc > 7 ? _wtoi(argv[7]) : 1;                   // angles round the turntable, the first at yaw
    if (N < 1) N = 1;
    if (N > 72) N = 72;
    std::vector<look> looks = read_looks(argv[1]);
    std::wstring models = argv[2], out = argv[3];
    CreateDirectoryW(out.c_str(), nullptr);
    if (FAILED(CoInitializeEx(nullptr, COINIT_MULTITHREADED))) return 1;
    ID3D11Device* dev = nullptr;
    ID3D11DeviceContext* ctx = nullptr;
    D3D_FEATURE_LEVEL want = D3D_FEATURE_LEVEL_11_0, got;
    if (FAILED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, &want, 1, D3D11_SDK_VERSION, &dev, &got, &ctx)) &&
        FAILED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, &want, 1, D3D11_SDK_VERSION, &dev, &got, &ctx))) {
        fwprintf(stderr, L"figure_snap: no Direct3D 11 device\n");
        return 1;
    }
    mv_set_zoom(0.0f);                                       // the whole figure, head to boots
    mv_set_headroom(0.0f);
    std::wstring index = out + L"\\figures.tsv.tmp";
    FILE* tsv = nullptr;
    if (_wfopen_s(&tsv, index.c_str(), L"wb") != 0 || !tsv) return 1;
    int made = 0, skipped = 0;
    for (const look& L : looks) {
        std::wstring model = models + (L.elite ? L"\\reach_elite.mdl" : L"\\reach_spartan.mdl");
        std::vector<std::string> regions, perms;
        std::string list = L.pieces;
        size_t at = 0;
        while (at <= list.size()) {                          // region:permutation,... as the panel reads it
            size_t end = list.find(',', at);
            std::string t = list.substr(at, end == std::string::npos ? std::string::npos : end - at);
            size_t colon = t.find(':');
            if (colon != std::string::npos) {
                std::string r = t.substr(0, colon), p = t.substr(colon + 1);
                if (mv_has(dev, model.c_str(), r.c_str(), p.c_str())) { regions.push_back(r); perms.push_back(p); }
                else if (mv_has(dev, model.c_str(), r.c_str(), "base")) { regions.push_back(r); perms.push_back("base"); }
            }
            if (end == std::string::npos) break;
            at = end + 1;
        }
        if (getenv("FIGURE_SNAP_DEBUG"))
            fprintf(stderr, "%s: %s, %zu of the listed pieces in the model (%s)\n", L.name.c_str(), L.elite ? "elite" : "spartan",
                    regions.size(), L.pieces.substr(0, 80).c_str());
        if (regions.empty()) { skipped++; continue; }        // no pieces logged yet: no picture, not a guess
        std::vector<mv_pick> picks;
        for (size_t k = 0; k < regions.size(); k++) picks.push_back({ regions[k].c_str(), perms[k].c_str() });
        mv_colors c{};
        float pri[3], sec[3];
        rgb(L.primary, pri);
        rgb(L.secondary, sec);
        float under[3] = { 0.07f + 0.10f * sec[0], 0.07f + 0.10f * sec[1], 0.08f + 0.10f * sec[2] };
        float visor[3] = { 0.80f, 0.56f, 0.16f }, skin[3] = { 0.24f, 0.21f, 0.19f };
        if (L.visor >= 0 && L.visor < 5) memcpy(visor, REACH_VISOR[L.visor], 12);
        memcpy(c.armor, pri, 12); memcpy(c.undersuit, under, 12); memcpy(c.visor, visor, 12);
        memcpy(c.lights, sec, 12); memcpy(c.skin, skin, 12); memcpy(c.secondary, sec, 12);
        std::vector<std::vector<unsigned char>> frames;
        UINT fw = 0, fh = 0;
        for (int k = 0; k < N; k++) {
            float turn = yaw + 6.2831853f * k / N;
            unsigned long long srv = mv_render(dev, ctx, model.c_str(), picks.data(), (int)picks.size(), c, turn, W, H);
            std::vector<unsigned char> px;
            if (!srv || !read_back(dev, ctx, (ID3D11ShaderResourceView*)(intptr_t)srv, px, fw, fh)) { frames.clear(); break; }
            frames.push_back(std::move(px));
        }
        std::vector<unsigned char> sheet;
        UINT ch = 0, cw = frames.empty() ? 0 : strip(frames, fw, fh, sheet, ch);
        std::string file = file_for(L.name);
        if (getenv("FIGURE_SNAP_DEBUG")) fprintf(stderr, "  drawn: %zu of %d angles, %u x %u each\n", frames.size(), N, cw, ch);
        if (cw && write_png(sheet, cw * N, ch, out + L"\\" + wide(file))) {
            fprintf(tsv, "%s\t%s\t%s\t%d\t%u\t%u\n", L.name.c_str(), file.c_str(), L.elite ? "elite" : "spartan", N, cw, ch);
            made++;
        } else skipped++;
    }
    fclose(tsv);
    MoveFileExW(index.c_str(), (out + L"\\figures.tsv").c_str(), MOVEFILE_REPLACE_EXISTING);
    printf("figure_snap: %d figures, %d without pieces or not drawn\n", made, skipped);
    ctx->Release();
    dev->Release();
    CoUninitialize();
    return 0;
}
