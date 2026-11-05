// model_view.cpp: see model_view.h. One cached model per file, one render target per view size. Version 1 models
// (geometry only) are lit as clean figures in the bot's colours; version 2 models (tools/model_pack2.py: posed, holding
// their weapon, with the game's own textures) draw the game's diffuse, colour-change, normal, detail-normal and
// self-illumination maps.
#include <windows.h>
#include <d3d11.h>
#include <d3dcompiler.h>
#include <wincodec.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "model_view.h"
#pragma comment(lib, "windowscodecs.lib")
#pragma comment(lib, "ole32.lib")

namespace {
const int NTEX = 5;                       // diffuse, color_change, normal, self_illum, detail normal
struct material { char file[NTEX][48]; float tiling; ID3D11ShaderResourceView* srv[NTEX]; bool loaded; };
struct group { char region[24]; char perm[32]; int index, kind; unsigned first, count; int mat; float lo[3], hi[3]; };
struct model {
    wchar_t path[260] = L"";
    wchar_t texdir[260] = L"";
    ID3D11Buffer* vb = nullptr;
    ID3D11Buffer* ib = nullptr;
    group* groups = nullptr;
    int ngroups = 0;
    material* mats = nullptr;
    int nmats = 0;
    float lo[3], hi[3];
    bool failed = false;
};
model g_model[4];
int g_next = 0;
ID3D11VertexShader* g_vs;
ID3D11PixelShader* g_ps;
ID3D11InputLayout* g_layout;
ID3D11Buffer* g_cb;
ID3D11RasterizerState* g_rs;
ID3D11DepthStencilState* g_ds;
ID3D11BlendState* g_bs;
ID3D11SamplerState* g_smp;
ID3D11Texture2D* g_rt;
ID3D11Texture2D* g_rt_ms;
ID3D11ShaderResourceView* g_srv;
ID3D11RenderTargetView* g_rtv;
ID3D11Texture2D* g_depth;
ID3D11DepthStencilView* g_dsv;
int g_samples = 1;
int g_w, g_h;
ID3D11Device* g_dev_seen;
bool g_shader_failed;

// textures by file, shared by every model and material (a few hundred at most)
struct tex_slot { char name[48]; ID3D11ShaderResourceView* srv; bool failed; };
tex_slot g_tex[768];
int g_ntex = 0;

// params: x kind, y a weapon (1: metal), z textured (1), w has a detail normal; extra: x the model's height, y / z cos / sin of the
// turn, w its lowest z; axis: x / y the model's middle, z its half width, w the detail tiling; color2: the secondary
// colour; texon: which of the five maps are bound (1 / 0)
struct cbuf { float mvp[16]; float color[4]; float params[4]; float extra[4]; float axis[4]; float color2[4]; float texon[4]; };

// Studio light in the turned model's frame (the viewer on +x, screen right +y, up +z): a warm key from the upper left,
// a cool fill from the right, a back light for the outline, sky / ground ambient. Per material: armor semi-gloss with
// bright worn edges and dark creases (the surface's curvature from the screen-space change of its normal: hard plates,
// not clay), under-suit matte, the visor a mirror of the studio. Textured (version 2): the game's diffuse tinted by its
// colour-change map (red: primary, green: secondary), its normal and detail-normal maps through a cotangent frame from
// the screen-space derivatives (no tangents stored), specular from the diffuse alpha, the lights glowing in the detail
// colour.
const char* HLSL = R"(
cbuffer C : register(b0) { float4x4 mvp; float4 color; float4 params; float4 extra; float4 axis; float4 color2; float4 texon; };
Texture2D tdif : register(t0); Texture2D tcc : register(t1); Texture2D tnrm : register(t2); Texture2D till : register(t3);
Texture2D tdet : register(t4);
SamplerState smp : register(s0);
struct VI { float3 p : POSITION; float3 n : NORMAL; float2 uv : TEXCOORD0; };
struct VO { float4 p : SV_POSITION; float3 n : NORMAL; float3 w : TEXCOORD0; float2 uv : TEXCOORD1; };
VO vs(VI i) { VO o; o.p = mul(mvp, float4(i.p, 1)); o.n = i.n; o.w = i.p; o.uv = i.uv; return o; }
float3 turn(float3 v) { return float3(v.x * extra.y + v.y * extra.z, -v.x * extra.z + v.y * extra.y, v.z); }
float hash(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float vnoise(float3 x) {                                        // value noise: the paint's fine unevenness
    float3 i = floor(x), f = frac(x); f = f * f * (3 - 2 * f);
    return lerp(lerp(lerp(hash(i), hash(i + float3(1, 0, 0)), f.x), lerp(hash(i + float3(0, 1, 0)), hash(i + float3(1, 1, 0)), f.x), f.y),
                lerp(lerp(hash(i + float3(0, 0, 1)), hash(i + float3(1, 0, 1)), f.x), lerp(hash(i + float3(0, 1, 1)), hash(i + float3(1, 1, 1)), f.x), f.y), f.z);
}
float3 perturb(float3 N, float3 P, float2 uv, float3 t) {      // tangent-space normal -> world, by the cotangent frame
    float3 dp1 = ddx(P), dp2 = ddy(P);
    float2 du1 = ddx(uv), du2 = ddy(uv);
    float3 dp2p = cross(dp2, N), dp1p = cross(N, dp1);
    float3 T = dp2p * du1.x + dp1p * du2.x, B = dp2p * du1.y + dp1p * du2.y;
    float im = rsqrt(max(max(dot(T, T), dot(B, B)), 1e-20));
    return normalize(T * im * t.x + B * im * t.y + N * t.z);
}
float4 ps(VO i) : SV_TARGET {
    float3 n0 = normalize(i.n);
    float3 c = color.rgb;
    float smask = 1, glow = 0;
    float3 emit = 0;
    if (params.z > 0) {                                           // the game's own surface
        float4 dif = texon.x > 0 ? tdif.Sample(smp, i.uv) : float4(0.6, 0.6, 0.6, 0.5);
        float4 cc = texon.y > 0 ? tcc.Sample(smp, i.uv) : 0;
        float3 tint = lerp(1, color.rgb * 1.9, cc.r) * lerp(1, color2.rgb * 1.9, cc.g);
        c = dif.rgb * tint;
        smask = dif.a;
        if (texon.z > 0) {
            float3 t = tnrm.Sample(smp, i.uv).xyz * 2 - 1;
            if (params.w > 0) { float3 d = tdet.Sample(smp, i.uv * axis.w).xyz * 2 - 1; t = float3(t.xy + d.xy * 0.6, t.z); }
            n0 = perturb(n0, i.w, i.uv, normalize(t));
        }
        if (texon.w > 0) emit = till.Sample(smp, i.uv).rgb * color2.a;
    }
    float3 n = normalize(turn(n0)), p = turn(i.w);
    if (params.x == 3 && params.z == 0) return float4(color.rgb * 1.5, 1);   // lights glow
    if (params.x == 6) return float4(color.rgb, 1);                          // an energy sword's blade
    float3 V = float3(1, 0, 0);
    float3 key = normalize(float3(0.65, -0.5, 0.6)), fill = normalize(float3(0.35, 0.85, -0.05));
    float3 back = normalize(float3(-0.75, 0.25, 0.6));
    float up = n.z * 0.5 + 0.5;
    float3 amb = lerp(float3(0.10, 0.10, 0.12), float3(0.30, 0.36, 0.48), up);
    float ao = lerp(0.72, 1.0, saturate((p.z - extra.w) / max(extra.x, 1e-4) * 2.5));   // dimmer at the feet
    // inner faces (inside of the legs and arms, under the arms: turned toward the body's middle) are in its shadow
    float2 out2 = i.w.xy - axis.xy;
    float r = length(out2);
    float inward = saturate(-dot(normalize(i.n.xy + 1e-5), out2 / max(r, 1e-5)));
    ao *= 1 - 0.45 * inward * (1 - saturate(r / max(axis.z, 1e-4)));
    // curvature: + on a convex edge, - in a crease, per unit of the model's height
    float3 nn = normalize(turn(normalize(i.n)));
    float3 dnx = ddx(nn), dny = ddy(nn), dpx = ddx(p), dpy = ddy(p);
    float curv = (dot(dnx, dpx) / max(dot(dpx, dpx), 1e-10) + dot(dny, dpy) / max(dot(dpy, dpy), 1e-10)) * extra.x;
    float k = params.x == 0 ? 1.0 : params.x == 4 ? 0.6 : 0.4;
    if (params.z > 0) k *= 0.5;                                  // (the normal maps carry most of the form)
    float edge = saturate(curv * 0.004) * k, crease = saturate(-curv * 0.006) * k;
    float power = params.x == 2 ? 90 : params.x == 0 ? 36 : params.x == 4 ? 20 : 14;
    float sk = params.x == 2 ? 1.2 : params.x == 0 ? 0.30 : params.x == 4 ? 0.18 : 0.10;
    if (params.z > 0 && params.x != 2) { sk = 0.12 + 0.55 * smask; power = 28 + 60 * smask; }
    float d = saturate(dot(n, key)), f = saturate(dot(n, fill)), b = saturate(dot(n, back));
    float fres = pow(1 - saturate(dot(n, V)), 4);
    if (params.x == 1 && params.z == 0) { c = max(c, float3(0.07, 0.07, 0.075)); sk = 0.16; power = 18; }   // the suit
    if (params.x == 0 && params.z == 0) {                         // armor paint: fine unevenness, a little scuffed
        float g = vnoise(i.w * 140 / max(extra.x, 1e-4)) * 0.6 + vnoise(i.w * 37 / max(extra.x, 1e-4)) * 0.4;
        c *= 0.94 + 0.10 * g;
        sk *= 0.8 + 0.4 * g;
    }
    float spec = pow(saturate(dot(n, normalize(key + V))), power) * sk;
    float3 lit = c * (amb * ao + float3(1.0, 0.96, 0.9) * 0.85 * d + float3(0.55, 0.68, 0.9) * 0.25 * f)
               + float3(0.75, 0.85, 1.0) * 0.35 * b * (0.4 + 0.6 * fres) + spec * float3(1.0, 0.97, 0.92);
    if (params.y > 0) {                                           // a gun's metal: the studio in its finish
        float3 rr = reflect(-V, n);
        float3 env = lerp(float3(0.03, 0.03, 0.04), float3(0.62, 0.68, 0.78), saturate(rr.z * 0.7 + 0.4));
        lit += env * (0.25 + 0.75 * c) * (0.15 + 0.35 * smask) + c * 0.35 * fres;
    }
    if (params.x == 2) {                                          // visor: the studio in its glass, tinted
        float3 rr = reflect(-V, n);
        float3 env = lerp(float3(0.05, 0.05, 0.06), float3(0.9, 0.92, 1.0), saturate(rr.z * 0.8 + 0.45));
        // (Halo 4's visor shader: the front colour facing us, the rim colour toward the edges, srf_char_visor.fx;
        // the other games give both the same)
        float3 vc = lerp(color2.rgb, color.rgb, pow(saturate(dot(n, V)), 3.0));
        lit = vc * 0.25 + vc * env * 0.75 + spec;
    }
    lit *= 1 - 0.55 * crease;
    lit += c * 0.6 * edge + edge * 0.12;
    lit += emit;
    return float4(saturate(lit), 1);
}
)";

template <class T> void rel(T*& p) { if (p) { p->Release(); p = nullptr; } }

void free_model(model& m) {
    rel(m.vb); rel(m.ib); free(m.groups); free(m.mats);
    m = model();
}

void reset_device_objects() {
    for (model& m : g_model) free_model(m);
    for (int k = 0; k < g_ntex; k++) rel(g_tex[k].srv);
    g_ntex = 0;
    rel(g_vs); rel(g_ps); rel(g_layout); rel(g_cb); rel(g_rs); rel(g_ds); rel(g_bs); rel(g_smp);
    rel(g_srv); rel(g_rtv); rel(g_rt); rel(g_rt_ms); rel(g_dsv); rel(g_depth);
    g_w = g_h = 0;
    g_shader_failed = false;
}

bool make_shaders(ID3D11Device* dev) {
    if (g_vs) return true;
    if (g_shader_failed) return false;
    ID3DBlob *v = nullptr, *p = nullptr, *err = nullptr;
    if (FAILED(D3DCompile(HLSL, strlen(HLSL), "model_view", nullptr, nullptr, "vs", "vs_4_0", 0, 0, &v, &err)) ||
        FAILED(D3DCompile(HLSL, strlen(HLSL), "model_view", nullptr, nullptr, "ps", "ps_4_0", 0, 0, &p, &err))) {
        if (err) { OutputDebugStringA((const char*)err->GetBufferPointer()); err->Release(); }
        if (v) v->Release();
        g_shader_failed = true;
        return false;
    }
    dev->CreateVertexShader(v->GetBufferPointer(), v->GetBufferSize(), nullptr, &g_vs);
    dev->CreatePixelShader(p->GetBufferPointer(), p->GetBufferSize(), nullptr, &g_ps);
    D3D11_INPUT_ELEMENT_DESC el[3] = {
        {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 12, D3D11_INPUT_PER_VERTEX_DATA, 0},
        {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 24, D3D11_INPUT_PER_VERTEX_DATA, 0} };
    dev->CreateInputLayout(el, 3, v->GetBufferPointer(), v->GetBufferSize(), &g_layout);
    v->Release(); p->Release();
    D3D11_BUFFER_DESC bd{};
    bd.ByteWidth = sizeof(cbuf); bd.Usage = D3D11_USAGE_DYNAMIC; bd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    bd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
    dev->CreateBuffer(&bd, nullptr, &g_cb);
    D3D11_RASTERIZER_DESC rd{};
    rd.FillMode = D3D11_FILL_SOLID; rd.CullMode = D3D11_CULL_NONE; rd.DepthClipEnable = TRUE;   // (both windings: the
    dev->CreateRasterizerState(&rd, &g_rs);                                                        // export's mixed)
    D3D11_DEPTH_STENCIL_DESC dd{};
    dd.DepthEnable = TRUE; dd.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ALL; dd.DepthFunc = D3D11_COMPARISON_LESS;
    dev->CreateDepthStencilState(&dd, &g_ds);
    D3D11_BLEND_DESC b{};
    b.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    dev->CreateBlendState(&b, &g_bs);
    D3D11_SAMPLER_DESC sd{};
    sd.Filter = D3D11_FILTER_ANISOTROPIC; sd.MaxAnisotropy = 8;
    sd.AddressU = sd.AddressV = sd.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
    sd.MaxLOD = D3D11_FLOAT32_MAX;
    dev->CreateSamplerState(&sd, &g_smp);
    return g_vs && g_ps && g_layout && g_cb && g_smp;
}

// a PNG / JPEG from the model's texture folder (tools/model_pack2.py), with its mip chain; nullptr if missing
ID3D11ShaderResourceView* texture(ID3D11Device* dev, ID3D11DeviceContext* ctx, const wchar_t* dir, const char* name) {
    if (!name[0]) return nullptr;
    for (int k = 0; k < g_ntex; k++)
        if (!strcmp(g_tex[k].name, name)) return g_tex[k].srv;
    if (g_ntex >= (int)(sizeof g_tex / sizeof g_tex[0])) return nullptr;
    tex_slot& slot = g_tex[g_ntex++];
    strncpy_s(slot.name, name, _TRUNCATE);
    slot.srv = nullptr;
    HRESULT co = CoInitializeEx(nullptr, COINIT_MULTITHREADED);   // (RPC_E_CHANGED_MODE: already set up: fine)
    IWICImagingFactory* wic = nullptr;
    IWICBitmapDecoder* dec = nullptr;
    IWICBitmapFrameDecode* frame = nullptr;
    IWICFormatConverter* conv = nullptr;
    wchar_t path[400];
    swprintf_s(path, L"%s%S", dir, name);
    UINT w = 0, h = 0;
    unsigned char* px = nullptr;
    if (SUCCEEDED(CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&wic))) &&
        SUCCEEDED(wic->CreateDecoderFromFilename(path, nullptr, GENERIC_READ, WICDecodeMetadataCacheOnDemand, &dec)) &&
        SUCCEEDED(dec->GetFrame(0, &frame)) && SUCCEEDED(wic->CreateFormatConverter(&conv)) &&
        SUCCEEDED(conv->Initialize(frame, GUID_WICPixelFormat32bppRGBA, WICBitmapDitherTypeNone, nullptr, 0, WICBitmapPaletteTypeCustom)) &&
        SUCCEEDED(conv->GetSize(&w, &h)) && w && h) {
        px = (unsigned char*)malloc((size_t)w * h * 4);
        if (px && FAILED(conv->CopyPixels(nullptr, w * 4, w * h * 4, px))) { free(px); px = nullptr; }
    }
    if (conv) conv->Release();
    if (frame) frame->Release();
    if (dec) dec->Release();
    if (wic) wic->Release();
    if (co == S_OK || co == S_FALSE) CoUninitialize();
    if (!px) { slot.failed = true; return nullptr; }
    D3D11_TEXTURE2D_DESC td{};
    td.Width = w; td.Height = h; td.MipLevels = 0; td.ArraySize = 1; td.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    td.SampleDesc.Count = 1; td.Usage = D3D11_USAGE_DEFAULT;
    td.BindFlags = D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_RENDER_TARGET; td.MiscFlags = D3D11_RESOURCE_MISC_GENERATE_MIPS;
    ID3D11Texture2D* t = nullptr;
    if (SUCCEEDED(dev->CreateTexture2D(&td, nullptr, &t))) {
        ctx->UpdateSubresource(t, 0, nullptr, px, w * 4, 0);
        if (SUCCEEDED(dev->CreateShaderResourceView(t, nullptr, &slot.srv))) ctx->GenerateMips(slot.srv);
        t->Release();
    }
    free(px);
    return slot.srv;
}

model* load(ID3D11Device* dev, const wchar_t* path) {
    for (model& m : g_model) if (!_wcsicmp(m.path, path)) return m.failed ? nullptr : &m;
    model& m = g_model[g_next];
    g_next = (g_next + 1) % 4;
    free_model(m);
    wcsncpy_s(m.path, path, _TRUNCATE);
    wcsncpy_s(m.texdir, path, _TRUNCATE);                       // <model folder>\tex\ (tools/model_pack2.py)
    wchar_t* slash = wcsrchr(m.texdir, L'\\');
    if (slash) wcscpy_s(slash + 1, 260 - (slash + 1 - m.texdir), L"tex\\");
    m.failed = true;
    FILE* f = nullptr;
    if (_wfopen_s(&f, path, L"rb") != 0 || !f) return nullptr;
    char magic[4]; unsigned ver = 0, head[4] = {}; float b[6];
    if (fread(magic, 1, 4, f) != 4 || memcmp(magic, "HBMD", 4) || fread(&ver, 4, 1, f) != 1 || (ver != 1 && ver != 2) ||
        fread(head, 4, ver == 2 ? 4 : 3, f) != (ver == 2 ? 4u : 3u) || fread(b, 4, 6, f) != 6) { fclose(f); return nullptr; }
    unsigned ng = head[0], nv = head[1], ni = head[2], nm = ver == 2 ? head[3] : 0;
    m.groups = (group*)calloc(ng, sizeof(group));
    m.mats = nm ? (material*)calloc(nm, sizeof(material)) : nullptr;
    float* verts = (float*)malloc((size_t)nv * 32);
    unsigned* idx = (unsigned*)malloc((size_t)ni * 4);
    bool ok = m.groups && verts && idx && (!nm || m.mats);
    for (unsigned k = 0; ok && k < nm; k++) {
        material& mt = m.mats[k];
        char name[48]; float tail[2];
        ok = fread(name, 1, 48, f) == 48 && fread(mt.file, 48, NTEX, f) == (size_t)NTEX && fread(tail, 4, 2, f) == 2;
        for (int s = 0; s < NTEX; s++) mt.file[s][47] = 0;
        mt.tiling = tail[0] > 0 ? tail[0] : 1.0f;
    }
    for (unsigned k = 0; ok && k < ng; k++) {
        group& g = m.groups[k];
        int tail[2]; unsigned span[2]; int mat = -1;
        ok = fread(g.region, 1, 24, f) == 24 && fread(g.perm, 1, 32, f) == 32 && fread(tail, 4, 2, f) == 2 && fread(span, 4, 2, f) == 2
             && (ver == 1 || fread(&mat, 4, 1, f) == 1);
        g.region[23] = g.perm[31] = 0;
        g.index = tail[0]; g.kind = tail[1]; g.first = span[0]; g.count = span[1];
        g.mat = mat >= 0 && (unsigned)mat < nm ? mat : -1;
    }
    if (ok && ver == 2) ok = fread(verts, 32, nv, f) == nv;
    else if (ok) {                                               // version 1: position and normal, no texture coordinates
        for (unsigned k = 0; ok && k < nv; k++) {
            ok = fread(verts + k * 8, 4, 6, f) == 6;
            verts[k * 8 + 6] = verts[k * 8 + 7] = 0;
        }
    }
    ok = ok && fread(idx, 4, ni, f) == ni;
    fclose(f);
    for (unsigned k = 0; ok && k < ng; k++) {                   // each piece's own extent (the camera frames the worn ones)
        group& g = m.groups[k];
        for (int a = 0; a < 3; a++) { g.lo[a] = 1e9f; g.hi[a] = -1e9f; }
        for (unsigned t = g.first; t < g.first + g.count && t < ni; t++) {
            unsigned v = idx[t];
            if (v >= nv) continue;
            for (int a = 0; a < 3; a++) { g.lo[a] = fminf(g.lo[a], verts[v * 8 + a]); g.hi[a] = fmaxf(g.hi[a], verts[v * 8 + a]); }
        }
    }
    if (ok) {
        D3D11_BUFFER_DESC bd{};
        bd.Usage = D3D11_USAGE_IMMUTABLE;
        bd.ByteWidth = nv * 32; bd.BindFlags = D3D11_BIND_VERTEX_BUFFER;
        D3D11_SUBRESOURCE_DATA sd{ verts, 0, 0 };
        ok = SUCCEEDED(dev->CreateBuffer(&bd, &sd, &m.vb));
        bd.ByteWidth = ni * 4; bd.BindFlags = D3D11_BIND_INDEX_BUFFER;
        sd.pSysMem = idx;
        ok = ok && SUCCEEDED(dev->CreateBuffer(&bd, &sd, &m.ib));
    }
    free(verts); free(idx);
    if (!ok) { free_model(m); return nullptr; }
    wcsncpy_s(m.path, path, _TRUNCATE);
    m.ngroups = (int)ng;
    m.nmats = (int)nm;
    memcpy(m.lo, b, 12); memcpy(m.hi, b + 3, 12);
    m.failed = false;
    return &m;
}

// drawn 4x multisampled (smooth outlines: single-sampled, its edges were stair steps), resolved into g_rt for the panel
bool make_target(ID3D11Device* dev, int w, int h) {
    if (g_rt && g_w == w && g_h == h) return true;
    rel(g_srv); rel(g_rtv); rel(g_rt); rel(g_rt_ms); rel(g_dsv); rel(g_depth);
    UINT q = 0;
    g_samples = SUCCEEDED(dev->CheckMultisampleQualityLevels(DXGI_FORMAT_R8G8B8A8_UNORM, 4, &q)) && q ? 4 : 1;
    D3D11_TEXTURE2D_DESC td{};
    td.Width = w; td.Height = h; td.MipLevels = 1; td.ArraySize = 1; td.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    td.SampleDesc.Count = 1; td.Usage = D3D11_USAGE_DEFAULT; td.BindFlags = D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;
    if (FAILED(dev->CreateTexture2D(&td, nullptr, &g_rt))) return false;
    dev->CreateShaderResourceView(g_rt, nullptr, &g_srv);
    if (g_samples > 1) {
        td.SampleDesc.Count = g_samples; td.BindFlags = D3D11_BIND_RENDER_TARGET;
        if (FAILED(dev->CreateTexture2D(&td, nullptr, &g_rt_ms))) return false;
        dev->CreateRenderTargetView(g_rt_ms, nullptr, &g_rtv);
    } else {
        dev->CreateRenderTargetView(g_rt, nullptr, &g_rtv);
    }
    td.Format = DXGI_FORMAT_D24_UNORM_S8_UINT; td.BindFlags = D3D11_BIND_DEPTH_STENCIL;
    if (FAILED(dev->CreateTexture2D(&td, nullptr, &g_depth))) return false;
    dev->CreateDepthStencilView(g_depth, nullptr, &g_dsv);
    g_w = w; g_h = h;
    return g_rtv && g_srv && g_dsv;
}

// 4x4 row-vector matrices (p * M), uploaded as they are
void mat_mul(const float* a, const float* b, float* o) {        // o = a * b (row-major)
    float t[16];
    for (int r = 0; r < 4; r++)
        for (int c = 0; c < 4; c++) t[r * 4 + c] = a[r * 4] * b[c] + a[r * 4 + 1] * b[4 + c] + a[r * 4 + 2] * b[8 + c] + a[r * 4 + 3] * b[12 + c];
    memcpy(o, t, sizeof t);
}

// the game's graphics state, as imgui_impl_dx11 keeps it around its own draw (and the pixel shader's textures and
// sampler, which the textured models bind)
struct backup {
    UINT nsc, nvp;
    D3D11_RECT sc[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE];
    D3D11_VIEWPORT vp[D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE];
    ID3D11RasterizerState* rs; ID3D11BlendState* bs; FLOAT bf[4]; UINT sm; ID3D11DepthStencilState* ds; UINT sr;
    ID3D11RenderTargetView* rtv[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]; ID3D11DepthStencilView* dsv;
    ID3D11PixelShader* ps; ID3D11VertexShader* vs; ID3D11GeometryShader* gs; ID3D11HullShader* hs; ID3D11DomainShader* dms;
    ID3D11Buffer* vscb; ID3D11Buffer* pscb;
    D3D11_PRIMITIVE_TOPOLOGY topo; ID3D11Buffer* ib; DXGI_FORMAT ibf; UINT ibo; ID3D11Buffer* vb; UINT vbs, vbo;
    ID3D11InputLayout* il;
    ID3D11ShaderResourceView* srv[NTEX]; ID3D11SamplerState* smp;
};
void save(ID3D11DeviceContext* c, backup& b) {
    memset(&b, 0, sizeof b);
    b.nsc = b.nvp = D3D11_VIEWPORT_AND_SCISSORRECT_OBJECT_COUNT_PER_PIPELINE;
    c->RSGetScissorRects(&b.nsc, b.sc); c->RSGetViewports(&b.nvp, b.vp); c->RSGetState(&b.rs);
    c->OMGetBlendState(&b.bs, b.bf, &b.sm); c->OMGetDepthStencilState(&b.ds, &b.sr);
    c->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT, b.rtv, &b.dsv);
    c->PSGetShader(&b.ps, nullptr, nullptr); c->VSGetShader(&b.vs, nullptr, nullptr); c->GSGetShader(&b.gs, nullptr, nullptr);
    c->HSGetShader(&b.hs, nullptr, nullptr); c->DSGetShader(&b.dms, nullptr, nullptr);
    c->VSGetConstantBuffers(0, 1, &b.vscb); c->PSGetConstantBuffers(0, 1, &b.pscb);
    c->IAGetPrimitiveTopology(&b.topo); c->IAGetIndexBuffer(&b.ib, &b.ibf, &b.ibo);
    c->IAGetVertexBuffers(0, 1, &b.vb, &b.vbs, &b.vbo); c->IAGetInputLayout(&b.il);
    c->PSGetShaderResources(0, NTEX, b.srv); c->PSGetSamplers(0, 1, &b.smp);
}
void restore(ID3D11DeviceContext* c, backup& b) {
    c->RSSetScissorRects(b.nsc, b.sc); c->RSSetViewports(b.nvp, b.vp); c->RSSetState(b.rs);
    c->OMSetBlendState(b.bs, b.bf, b.sm); c->OMSetDepthStencilState(b.ds, b.sr);
    c->OMSetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT, b.rtv, b.dsv);
    c->PSSetShader(b.ps, nullptr, 0); c->VSSetShader(b.vs, nullptr, 0); c->GSSetShader(b.gs, nullptr, 0);
    c->HSSetShader(b.hs, nullptr, 0); c->DSSetShader(b.dms, nullptr, 0);
    c->VSSetConstantBuffers(0, 1, &b.vscb); c->PSSetConstantBuffers(0, 1, &b.pscb);
    c->IASetPrimitiveTopology(b.topo); c->IASetIndexBuffer(b.ib, b.ibf, b.ibo);
    c->IASetVertexBuffers(0, 1, &b.vb, &b.vbs, &b.vbo); c->IASetInputLayout(b.il);
    c->PSSetShaderResources(0, NTEX, b.srv); c->PSSetSamplers(0, 1, &b.smp);
    IUnknown* all[] = { b.rs, b.bs, b.ds, b.dsv, b.ps, b.vs, b.gs, b.hs, b.dms, b.vscb, b.pscb, b.ib, b.vb, b.il, b.smp };
    for (IUnknown* u : all) if (u) u->Release();
    for (ID3D11RenderTargetView* r : b.rtv) if (r) r->Release();
    for (ID3D11ShaderResourceView* s : b.srv) if (s) s->Release();
}

// the group drawn for a region: its permutation by name, or "#n" by its index in the model's list; the held weapon
// (region "weapon", tools/model_pack2.py) always
bool picked(const model& m, const group& g, const mv_pick* picks, int n) {
    if (!_stricmp(g.region, "weapon")) return true;
    for (int k = 0; k < n; k++) {
        if (_stricmp(picks[k].region, g.region)) continue;
        if (picks[k].perm[0] == '#') return atoi(picks[k].perm + 1) == g.index;
        return !_stricmp(picks[k].perm, g.perm);
    }
    (void)m;
    return false;
}
}  // namespace

bool mv_has(void* device, const wchar_t* path, const char* region, const char* perm) {
    ID3D11Device* dev = (ID3D11Device*)device;
    if (!dev) return false;
    if (dev != g_dev_seen) { reset_device_objects(); g_dev_seen = dev; }
    model* m = load(dev, path);
    if (!m) return false;
    for (int k = 0; k < m->ngroups; k++)
        if (!_stricmp(m->groups[k].region, region) && (perm[0] == '#' ? m->groups[k].index == atoi(perm + 1) : !_stricmp(m->groups[k].perm, perm)))
            return true;
    return false;
}

static float g_zoom = 1.0f;          // mv_set_zoom: 0 the whole figure, 1 the upper torso
static const float TORSO_CUT = 0.52f;   // at zoom 1 the lower 52% of the figure's height (legs, hips) is out of frame
void mv_set_zoom(float zoom) { g_zoom = zoom < 0 ? 0 : zoom > 1 ? 1 : zoom; }
static float g_head[3];                 // mv_head: the last draw's head, in its pixels
void mv_head(float out[3]) { memcpy(out, g_head, sizeof g_head); }
static float g_headroom = 0.0f;         // mv_set_headroom: room above the head, a share of the framed height
void mv_set_headroom(float share) { g_headroom = share < 0 ? 0 : share > 0.6f ? 0.6f : share; }

unsigned long long mv_render(void* device, void* context, const wchar_t* path, const mv_pick* picks, int npicks,
                             const mv_colors& colors, float yaw, int w, int h) {
    ID3D11Device* dev = (ID3D11Device*)device;
    ID3D11DeviceContext* ctx = (ID3D11DeviceContext*)context;
    if (!dev || !ctx || w < 8 || h < 8) return 0;
    if (dev != g_dev_seen) { reset_device_objects(); g_dev_seen = dev; }   // a new device (MCC reset): start over
    model* m = load(dev, path);
    if (!m || !make_shaders(dev) || !make_target(dev, w, h)) return 0;
    backup b;
    save(ctx, b);
    float clear[4] = { 0, 0, 0, 0 };                           // transparent: the panel's backdrop shows through
    ctx->ClearRenderTargetView(g_rtv, clear);
    ctx->ClearDepthStencilView(g_dsv, D3D11_CLEAR_DEPTH, 1.0f, 0);
    ctx->OMSetRenderTargets(1, &g_rtv, g_dsv);
    D3D11_VIEWPORT vp{ 0, 0, (float)w, (float)h, 0, 1 };
    ctx->RSSetViewports(1, &vp);
    ctx->RSSetState(g_rs);
    ctx->OMSetDepthStencilState(g_ds, 0);
    float bf[4] = { 0, 0, 0, 0 };
    ctx->OMSetBlendState(g_bs, bf, 0xFFFFFFFF);
    UINT stride = 32, off = 0;
    ctx->IASetVertexBuffers(0, 1, &m->vb, &stride, &off);
    ctx->IASetIndexBuffer(m->ib, DXGI_FORMAT_R32_UINT, 0);
    ctx->IASetInputLayout(g_layout);
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    ctx->VSSetShader(g_vs, nullptr, 0);
    ctx->PSSetShader(g_ps, nullptr, 0);
    ctx->GSSetShader(nullptr, nullptr, 0); ctx->HSSetShader(nullptr, nullptr, 0); ctx->DSSetShader(nullptr, nullptr, 0);
    ctx->VSSetConstantBuffers(0, 1, &g_cb);
    ctx->PSSetConstantBuffers(0, 1, &g_cb);
    ctx->PSSetSamplers(0, 1, &g_smp);
    // the worn pieces' extent, the gun left out (version 2 holds every armor piece: the file's own extent took the
    // tallest helmet of all and the gun, so each game's figure came out a different size); the camera: their middle,
    // the figure's height FILL of the view, turned by yaw about the up axis
    const float FILL = 0.84f;
    float lo[3] = { 1e9f, 1e9f, 1e9f }, hi[3] = { -1e9f, -1e9f, -1e9f };
    for (int k = 0; k < m->ngroups; k++) {
        const group& g = m->groups[k];
        if (g.kind == 5 || !g.count || !_stricmp(g.region, "weapon") || g.lo[0] > g.hi[0] || !picked(*m, g, picks, npicks)) continue;
        for (int a = 0; a < 3; a++) { lo[a] = fminf(lo[a], g.lo[a]); hi[a] = fmaxf(hi[a], g.hi[a]); }
    }
    if (lo[0] > hi[0]) { memcpy(lo, m->lo, 12); memcpy(hi, m->hi, 12); }
    // the zoom (mv_set_zoom): the frame's top kept at the head, its bottom raised from the feet to the waist
    float tall = hi[2] - lo[2], span = tall * (1.0f - TORSO_CUT * g_zoom);
    float cx = (lo[0] + hi[0]) * 0.5f, cy = (lo[1] + hi[1]) * 0.5f, cz = hi[2] - span * 0.5f;
    if (g_headroom > 0) { cz += span * g_headroom * 0.5f; span *= 1.0f + g_headroom; }   // (the frame grown upward)
    float fov = 0.52f, dist = span * 0.5f / tanf(fov * 0.5f) / FILL;
    // ... and wide enough for its arms (an Elite's, out from its sides, were cut at the card's edges up close)
    float wide = 0.5f * fmaxf(hi[0] - lo[0], hi[1] - lo[1]), wdist = wide / (tanf(fov * 0.5f) * ((float)w / h)) / 0.94f;
    if (wdist > dist) dist = wdist;
    float c = cosf(yaw), s = sinf(yaw);
    float T[16] = { 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -cx, -cy, -cz, 1 };
    float R[16] = { c, -s, 0, 0, s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1 };
    // view axes (row vectors): screen right = world +y (its left hand on our right: it faces us), up = z, depth = -x
    float V[16] = { 0, 0, -1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, dist, 1 };
    float aspect = (float)w / h, fy = 1.0f / tanf(fov * 0.5f), fx = fy / aspect, zn = dist * 0.3f, zf = dist * 3.0f;
    float P[16] = { fx, 0, 0, 0, 0, fy, 0, 0, 0, 0, zf / (zf - zn), 1, 0, 0, -zn * zf / (zf - zn), 0 };
    float M[16];
    mat_mul(T, R, M); mat_mul(M, V, M); mat_mul(M, P, M);
    // the head on screen (mv_head): the worn head / helmet pieces' extent (Reach's helmet flair too), else the top
    // twelfth of the figure; its centre and half height projected through the same camera
    float hl[3] = { 1e9f, 1e9f, 1e9f }, hh[3] = { -1e9f, -1e9f, -1e9f };
    for (int k = 0; k < m->ngroups; k++) {
        const group& g = m->groups[k];
        char rg[24]; strcpy_s(rg, g.region); _strlwr_s(rg);
        if (!g.count || g.lo[0] > g.hi[0] || !picked(*m, g, picks, npicks) || (!strstr(rg, "head") && !strstr(rg, "helmet")))
            continue;
        for (int a = 0; a < 3; a++) { hl[a] = fminf(hl[a], g.lo[a]); hh[a] = fmaxf(hh[a], g.hi[a]); }
    }
    if (hl[0] > hh[0]) { hl[0] = lo[0]; hl[1] = lo[1]; hh[0] = hi[0]; hh[1] = hi[1]; hh[2] = hi[2]; hl[2] = hi[2] - tall / 12; }
    auto project = [&](float x, float y, float z, float* px_) {
        float v[4] = { x, y, z, 1 }, o[4];
        for (int c2 = 0; c2 < 4; c2++) o[c2] = v[0] * M[c2] + v[1] * M[4 + c2] + v[2] * M[8 + c2] + v[3] * M[12 + c2];
        px_[0] = (o[0] / o[3] * 0.5f + 0.5f) * w; px_[1] = (0.5f - o[1] / o[3] * 0.5f) * h;
    };
    float hx = (hl[0] + hh[0]) * 0.5f, hy = (hl[1] + hh[1]) * 0.5f, top[2], bot[2], mid[2];
    project(hx, hy, hh[2], top); project(hx, hy, hl[2], bot); project(hx, hy, (hl[2] + hh[2]) * 0.5f, mid);
    g_head[0] = mid[0]; g_head[1] = mid[1]; g_head[2] = fabsf(bot[1] - top[1]) * 0.5f;
    for (int k = 0; k < m->ngroups; k++) {
        const group& g = m->groups[k];
        if (g.kind == 5 || !g.count || !picked(*m, g, picks, npicks)) continue;
        bool weapon = !_stricmp(g.region, "weapon");
        const float* col = g.kind == 1 ? colors.undersuit : g.kind == 2 ? colors.visor : g.kind == 3 ? colors.lights
                         : g.kind == 4 ? colors.skin : colors.armor;
        ID3D11ShaderResourceView* srv[NTEX] = {};
        bool textured = false;
        float tiling = 1;
        if (g.mat >= 0) {
            material& mt = m->mats[g.mat];
            for (int t = 0; t < NTEX; t++) srv[t] = texture(dev, ctx, m->texdir, mt.file[t]);
            textured = srv[0] != nullptr;
            tiling = mt.tiling;
        }
        ctx->PSSetShaderResources(0, NTEX, srv);
        D3D11_MAPPED_SUBRESOURCE ms;
        if (FAILED(ctx->Map(g_cb, 0, D3D11_MAP_WRITE_DISCARD, 0, &ms))) continue;
        cbuf& cb = *(cbuf*)ms.pData;
        memcpy(cb.mvp, M, sizeof M);            // row-vector matrix as is: HLSL reads it column-major (imgui_impl_dx11)
        // a textured piece: its colour-change map picks where the primary and secondary go (a weapon keeps its own);
        // the visor always its own colour
        static const float blade[3] = { 0.62f, 0.86f, 1.0f };         // (Halo's energy sword: blue-white)
        const float* pri = g.kind == 6 ? blade : weapon ? nullptr : g.kind == 2 || !textured ? col : colors.armor;
        float white[3] = { 0.53f, 0.53f, 0.53f };
        if (!pri) pri = white;
        cb.color[0] = pri[0]; cb.color[1] = pri[1]; cb.color[2] = pri[2]; cb.color[3] = 1;
        const float* sec = weapon ? white : g.kind == 2 ? (colors.rim_on ? colors.visor_rim : colors.visor)
                                                         : colors.secondary;
        cb.color2[0] = sec[0]; cb.color2[1] = sec[1]; cb.color2[2] = sec[2];
        cb.color2[3] = 1.4f;                                       // the self-illumination's strength
        cb.params[0] = (float)g.kind; cb.params[1] = weapon ? 1.0f : 0.0f;
        cb.params[2] = textured && g.kind != 2 ? 1.0f : 0.0f;
        cb.params[3] = srv[4] ? 1.0f : 0.0f;
        for (int t = 0; t < 4; t++) cb.texon[t] = srv[t] ? 1.0f : 0.0f;
        cb.extra[0] = tall; cb.extra[1] = c; cb.extra[2] = s; cb.extra[3] = lo[2];
        cb.axis[0] = cx; cb.axis[1] = cy; cb.axis[2] = 0.5f * (hi[1] - lo[1]); cb.axis[3] = tiling;
        ctx->Unmap(g_cb, 0);
        ctx->DrawIndexed(g.count, g.first, 0);
    }
    if (g_samples > 1) ctx->ResolveSubresource(g_rt, 0, g_rt_ms, 0, DXGI_FORMAT_R8G8B8A8_UNORM);
    restore(ctx, b);
    return (unsigned long long)(intptr_t)g_srv;
}
