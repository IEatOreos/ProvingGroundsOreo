// Third person (the BOTS panel's Experimental tab; upstream 0.3.0, build 20261116-2330): the view over the player's
// shoulder. Upstream shares this file with every game's camera hook; (custom, Nov 24, owner: "Reach only") here only
// Halo: Reach's (reach.cpp hr_follow_hook) calls it. The game's own following camera (the one its vehicles' third
// person seats use) is put on the local player on foot; the hook then calls tp_view with the camera's target point, its
// forward and the body's eye point, and the view is set from the aim alone: TP_BACKS behind, aside more as it goes back
// (the body off the middle), a little up, short of walls where the game gives a ray test. Shoulder and distance changes
// ease in over a quarter second, never a snap; the keys flip the shoulder and step the distance (any keyboard key or
// mouse button, set in the panel; no controller button, the owner, Nov 24).
#include <windows.h>
#include <math.h>
#include <stdint.h>
#include <string.h>

bool bots_panel_third_person();
int bots_panel_shoulder();
void bots_panel_flip_shoulder();
int bots_panel_shoulder_key();
int bots_panel_distance();
void bots_panel_cycle_distance();
int bots_panel_distance_key();

namespace {
// world units behind the body's eye (CE's 3.048 m each: set from close and far shots, Nov 16), up above it
const float TP_BACKS[3] = {0.28f, 0.62f, 1.15f}, TP_UP = -0.02f;   // up: from the focus point (+0.07 sat too high)
const float TP_AIM_AT = 25.0f, TP_AIM_NEAR = 0.8f; // units out the crosshair meets the aim (no wall test), the nearest (4 put
                                                   // walls nearer than 12 m off the crosshair: ODST, Nov 16)
float g_side = 1, g_back = 0.6f, g_far;           // where the view is now (it eases to what is asked)
LARGE_INTEGER g_last;

bool key_hit(int vk, bool& was) {                 // vk went down, with MCC in front
    DWORD pid = 0;
    GetWindowThreadProcessId(GetForegroundWindow(), &pid);
    bool down = vk && pid == GetCurrentProcessId() && (GetAsyncKeyState(vk) & 0x8000);
    bool hit = down && !was;
    was = down;
    return hit;
}
}  // namespace

bool tp_on() { return bots_panel_third_person(); }

// the shoulder and distance keys: called each tick the view is up
void tp_keys() {
    static bool side_was, dist_was;
    if (key_hit(bots_panel_shoulder_key(), side_was)) bots_panel_flip_shoulder();
    if (key_hit(bots_panel_distance_key(), dist_was)) bots_panel_cycle_distance();
}

// the view, written into a following camera's output the way the game's observer reads it: p = at + forward level *
// off[0] + right level * off[1] + up * off[2], the camera = p - forward * dist, dist shortened by the game's own wall
// test. So p is put at the shoulder (the eye, aside, a little up), dist the distance asked, and the forward turned from
// the camera to the point the gun's aim meets (the world where a wall test is given, else TP_AIM_AT out) so the
// crosshair is on the shot (bullets landed off it before). eye: the game's own focus point (drawn each frame: a body's
// tick position shook). units: a game's world units in CE's (1.0). clear(from, by): the share of the way clear of the
// world, or null
void tp_view(const float eye[3], const float at[3], float f[3], float off[3], float* dist, float units,
             float (*clear)(const float from[3], const float by[3])) {
    LARGE_INTEGER now, fq;
    QueryPerformanceCounter(&now);
    QueryPerformanceFrequency(&fq);
    float dt = g_last.QuadPart ? (float)(now.QuadPart - g_last.QuadPart) / (float)fq.QuadPart : 1 / 60.0f;
    g_last = now;
    if (dt <= 0 || dt > 0.25f) dt = 1 / 60.0f;
    float ease = 1 - expf(-dt * 12.0f);
    g_side += ((float)bots_panel_shoulder() - g_side) * ease;
    g_back += (TP_BACKS[bots_panel_distance() % 3] - g_back) * ease;
    float h = sqrtf(f[0] * f[0] + f[1] * f[1]);
    if (h < 1e-3f) return;
    float b = g_back * units, s = g_side * (0.13f + 0.14f * g_back) * units;   // aside (a little more as it goes back)
    float rx = f[1] / h, ry = -f[0] / h;           // right, level
    float p[3] = {at[0] + rx * s, at[1] + ry * s, at[2] + TP_UP * units};   // the shoulder (from the game's pivot)
    float cam[3];
    for (int i = 0; i < 3; i++) cam[i] = p[i] - f[i] * b;
    // where the aim meets the world eases there, never nearer than TP_AIM_NEAR: turning past an edge took the point
    // from a wall to the far ground in one frame and the view stepped with it (stutters when turning)
    float far_ = TP_AIM_AT * units;
    if (clear) {
        float by[3] = {f[0] * far_, f[1] * far_, f[2] * far_};
        far_ = fmaxf(TP_AIM_NEAR * units, far_ * fminf(1.0f, clear(eye, by)));
    }
    g_far = g_far > 0 ? g_far + (far_ - g_far) * (1 - expf(-dt * 6.0f)) : far_;
    far_ = g_far;
    float to[3], n = 0;
    for (int i = 0; i < 3; i++) to[i] = eye[i] + f[i] * far_ - cam[i], n += to[i] * to[i];
    n = sqrtf(n);
    if (n > 1e-3f) {
        float g[3] = {to[0] / n, to[1] / n, to[2] / n};
        float gh = sqrtf(g[0] * g[0] + g[1] * g[1]);
        if (gh > 1e-3f) {
            for (int i = 0; i < 3; i++) f[i] = g[i];
            h = gh;
        }
    }
    float v[3];                                    // p again, from the camera along the forward now
    for (int i = 0; i < 3; i++) v[i] = cam[i] + f[i] * b - at[i];
    float cx = f[0] / h, cy = f[1] / h;
    off[0] = v[0] * cx + v[1] * cy;
    off[1] = v[0] * cy - v[1] * cx;
    off[2] = v[2];
    *dist = b;
}

// the camera's up at right angles to its forward, the world's up kept in their plane (as the games' own following
// cameras make it from their forward). tp_view turns the forward to the aim point; the game's up stayed the old
// forward's and a director that checks the pair put its default view in its place (upstream's Halo 3 find). Reach: up
// is the three floats after forward
void tp_up(const float f[3], float up[3]) {
    float d = f[2], u[3] = {-f[0] * d, -f[1] * d, 1.0f - f[2] * d};
    float n = sqrtf(u[0] * u[0] + u[1] * u[1] + u[2] * u[2]);
    if (n < 1e-4f) return;                        // (straight up or down: the game's own up stays)
    for (int i = 0; i < 3; i++) up[i] = u[i] / n;
}

// (upstream 0.3.0, build 20261117-2300; custom, Nov 24, owner: "smaller reticle: with #53, Reach only, only while third
// person is on") Here only Reach's reach.cpp hr_reticle calls it; the Halo 3 parts of the layout (state_at) stay in his
// shape and Reach passes -1 for them.
// The aiming reticle smaller in third person, for the games whose weapon HUD is a chud definition. The layouts are the
// editing kits' (tool export-tag-to-xml on ui\chud\battle_rifle and ui\chud\assault_rifle) and each was read back on the live game
// before use. The tag starts with its widget collections block; a collection has a scripting class and a block of bitmap
// widgets; a bitmap widget has a placement data block (0x1C an entry: an anchor, +0x14 the scale pair) and, in Halo 3,
// a state data block (0x2C an entry, +0x16 the unit zoom state bits, bit 0 unzoomed). A reticle is a placement anchored
// on the crosshair in a collection of the crosshair class; in Halo 3 the scope's own pieces (shown zoomed only) are
// left alone. The pairs are kept and put back when third person ends, a scope comes up or the body is gone; (custom,
// Nov 24) at a new match they are put back while the tags are where they were (reach.cpp hr_reticle_tick), else the
// list is dropped unwritten; tp_chud_back writes a pair back only while it still reads what we made of it
struct tp_chud_layout {
    int coll;                // a collection's size
    int cls_at, cls_size;    // its scripting class: offset, bytes (2 Halo 3, 1 Reach)
    int bitmaps_at;          // its bitmap widgets block
    int bitmap;              // a bitmap widget's size
    int state_at;            // the widget's state data block as Halo 3 has it, or -1
    int place_at;            // the widget's placement data block
    int anchor_at, anchor_size;   // the anchor in a placement entry
    int cls, anchor;         // the crosshair values of the two enums
};
const float TP_CHUD_RETICLE = 0.7f;
static struct { float* at; float w, h, ox, oy; } g_chud[256];   // the scale pair, its values, the offset pair's (just before it)
static int g_chud_n;

void tp_chud_forget() { g_chud_n = 0; }

void tp_chud_back() {
    for (int i = 0; i < g_chud_n; i++) {
        __try {
            float* s = g_chud[i].at;
            if (s[0] == g_chud[i].w * TP_CHUD_RETICLE && s[1] == g_chud[i].h * TP_CHUD_RETICLE) {
                s[0] = g_chud[i].w;
                s[1] = g_chud[i].h;
                s[-2] = g_chud[i].ox;
                s[-1] = g_chud[i].oy;
            }
        } __except (EXCEPTION_EXECUTE_HANDLER) {}
    }
    g_chud_n = 0;
}

// one chud definition's reticles made smaller: `unpack` turns the tag data's packed addresses into pointers
void tp_chud_shrink(uint8_t* chud, uint8_t* (*unpack)(uint32_t), const tp_chud_layout& L) {
    __try {
        int n = *(int32_t*)chud;
        if (n < 1 || n > 64) return;
        uint8_t* colls = unpack(*(uint32_t*)(chud + 4));
        for (int i = 0; i < n; i++) {
            uint8_t* c = colls + (size_t)i * L.coll;
            int cls = L.cls_size == 1 ? c[L.cls_at] : *(uint16_t*)(c + L.cls_at);
            int nb = *(int32_t*)(c + L.bitmaps_at);
            if (cls != L.cls || nb < 1 || nb > 64) continue;
            uint8_t* bp = unpack(*(uint32_t*)(c + L.bitmaps_at + 4));
            for (int j = 0; j < nb; j++) {
                uint8_t* b = bp + (size_t)j * L.bitmap;
                if (L.state_at >= 0 && *(int32_t*)(b + L.state_at) > 0) {
                    uint16_t zoom = *(uint16_t*)(unpack(*(uint32_t*)(b + L.state_at + 4)) + 0x16);
                    if (zoom && !(zoom & 1)) continue;                 // (a piece of the scope's own picture)
                }
                int np = *(int32_t*)(b + L.place_at);
                if (np < 1 || np > 8) continue;
                uint8_t* pp = unpack(*(uint32_t*)(b + L.place_at + 4));
                for (int m = 0; m < np && g_chud_n < 256; m++) {
                    uint8_t* e = pp + (size_t)m * 0x1C;
                    float* s = (float*)(e + 0x14);
                    int anchor = L.anchor_size == 1 ? e[L.anchor_at] : *(uint16_t*)(e + L.anchor_at);
                    float ax = fabsf(s[0]), ay = fabsf(s[1]);          // (a mirrored piece has a negative scale)
                    if (anchor != L.anchor || !(ax > 0.01f && ax < 20.0f && ay > 0.01f && ay < 20.0f)) continue;
                    bool have = false;
                    for (int k = 0; k < g_chud_n; k++) have |= g_chud[k].at == s;
                    if (have) continue;
                    g_chud[g_chud_n].at = s;
                    g_chud[g_chud_n].w = s[0];
                    g_chud[g_chud_n].h = s[1];
                    g_chud[g_chud_n].ox = s[-2];
                    g_chud[g_chud_n].oy = s[-1];
                    g_chud_n++;
                    s[0] *= TP_CHUD_RETICLE;
                    s[1] *= TP_CHUD_RETICLE;
                    // the piece's pixel offset from the anchor too (entry +0xC): a reticle built of pieces set round the
                    // middle (Reach's needle rifle: four arcs 14 px out) kept its pieces apart and came out loose
                    s[-2] *= TP_CHUD_RETICLE;
                    s[-1] *= TP_CHUD_RETICLE;
                }
            }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {}
}
