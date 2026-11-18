// pg_link.cpp (custom, Nov 18): the link between the host's Proving Grounds and a joined PC friend's, so the friend sees
// the host's search, vote and loading screens (proving_grounds.cpp follow mode). The owner: "we need this to work in
// order to expand it even further". The channel is MCC's own PlayFab Party text chat (PartyWin.dll 1.4.13), as the link
// test (native/pglink.cpp) found and proved live on Nov 18, host and friend: a handshake within 1 s of the join, about
// 0.5 s a round trip, texts with 60000 data bytes intact, still working in a match (MCC's chat permissions 0x1F in the
// lobby, 0x10 in a game), every test text hidden from MCC on both PCs.
//  - Texts start "pgl2 ". This PC's MCC never sees one: PartyStartProcessingStateChanges and
//    PartyFinishProcessingStateChanges are hooked, MCC gets a copy of the state changes without them, the original is
//    finished here (as pglink.cpp).
//  - NEVER a text to an MCC without this hook. Live, Nov 18: the friend's MCC dropped out 5-10 s after each test hello
//    reached it with no hook to hide it, twice. So this PC speaks first only when botcore.ini says pglink=2 (the friend's
//    copy: "I join a host who runs the mod"), only when it joined someone else's Party network (MCC connected to it, did
//    not make it), and only while the lobby has exactly one other player: the host. pglink=1 (the default) answers a
//    hello and never speaks first; pglink=0 hooks nothing.
//  - Messages: "pgl2 hello" (the friend, 3 at most, 20 s apart), "pgl2 ok" (the host's answer), "pgl2 st n=" with the
//    host's Proving Grounds state as a data buffer (proving_grounds.cpp pgs_state: on a change, at most 5 a second, and
//    every second), "pgl2 vote" (the friend's vote, to the host).
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "third_party/minhook/include/MinHook.h"
#include "proving_grounds.h"

void logf(const char* fmt, ...);
extern uint32_t g_pglink;                        // botcore.cpp: botcore.ini pglink= (0 off, 1 answer, 2 speak first)

static size_t readable(const void* p) {          // bytes readable from p (0: not a readable address)
    uintptr_t a = (uintptr_t)p;
    if (a < 0x10000 || a > 0x7FFFFFFEFFFFull) return 0;
    MEMORY_BASIC_INFORMATION mi;
    if (!VirtualQuery(p, &mi, sizeof mi) || mi.State != MEM_COMMIT || (mi.Protect & (PAGE_NOACCESS | PAGE_GUARD)))
        return 0;
    if (!(mi.Protect & (PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE |
                        PAGE_EXECUTE_WRITECOPY)))
        return 0;
    return (uintptr_t)mi.BaseAddress + mi.RegionSize - a;
}
static uint64_t now_ms() { return GetTickCount64(); }

// ------------------------------------------------------------------ the Party C API (PartyWin.dll 1.4)
typedef uint32_t perr;
typedef const void* ph;
struct pbuf { const void* buffer; uint32_t bytes; };
struct pchange { uint32_t type; };
typedef perr (*p_start)(ph handle, uint32_t* count, const pchange* const** changes);
typedef perr (*p_finish)(ph handle, uint32_t count, const pchange* const* changes);
typedef perr (*p_chats)(ph handle, uint32_t* count, const ph** chats);
typedef perr (*p_chat_local)(ph chat, uint32_t* is_local);
typedef perr (*p_chat_entity)(ph chat, const char** entity);
typedef perr (*p_chat_send)(ph chat, uint32_t ntargets, const ph* targets, const char* text, uint32_t nbufs,
                            const pbuf* bufs);
enum { T_CREATE_NET = 2, T_CONNECT_NET = 3, T_LEAVE_NET = 19, T_NET_DESTROYED = 20 };   // (pglink.cpp's name table)

static HMODULE g_party;
static void *g_start_at, *g_finish_at;
static p_start o_start;
static p_finish o_finish;
static p_chats f_chats;
static p_chat_local f_chat_local;
static p_chat_entity f_chat_entity;
static p_chat_send f_chat_send;
static volatile bool g_off;                      // a fault: the link stops (MCC's calls still go through)
static uint32_t g_id;                            // this PC's id in its messages (random a load)
static CRITICAL_SECTION g_cs;                    // the state and votes, between the overlay's thread and MCC's

// this PC's place in the Party network: made it (the host's side) or joined one (MCC connected to it)
static bool g_made_net, g_joined_net;

// (a chat control's handle may be reused for the next player who joins: each poll checks it is still the same player,
// by its PlayFab entity id, and one not in MCC's list now gets nothing)
struct peer {
    ph chat;
    char entity[48];                             // its player's PlayFab entity id
    uint64_t seen;                               // last seen in MCC's chat controls (this poll's time: there now)
    bool local, answered;                        // a pgl2 message came from it: it runs this too
    int hellos;
    uint64_t hello_at;
};
static peer g_peers[16];
static int peer_index(ph c) { for (int i = 0; i < 16; i++) if (g_peers[i].chat == c) return i; return -1; }
static int peer_slot(ph c) {
    int i = peer_index(c);
    if (i >= 0) return i;
    for (i = 0; i < 16; i++) if (!g_peers[i].chat || now_ms() - g_peers[i].seen > 60000) break;
    if (i == 16) i = 0;
    memset(&g_peers[i], 0, sizeof g_peers[i]);
    g_peers[i].chat = c;
    return i;
}

// out: the host's state to send (pg_link_set_state); in: the newest one received; the friend's vote both ways
static uint8_t g_out[PGS_MAX], g_in[PGS_MAX];
static uint32_t g_out_n, g_in_n;
static bool g_out_dirty;
static uint64_t g_out_sent_at, g_in_at;
static char g_vote_out[160];
static bool g_vote_dirty;
struct vote_in { char name[32]; uint32_t key; int v; };
static vote_in g_votes[8];
static int g_nvotes;

static bool send(ph local, int n, const ph* to, const char* text, uint32_t nbufs, const pbuf* bufs) {
    perr e = f_chat_send(local, (uint32_t)n, to, text, nbufs, bufs);
    static perr last = 0xFFFFFFFF;
    if (e != last) { logf("pg link: sending %s", e ? "failed" : "works"); last = e; }
    return e == 0;
}

static void poll(ph handle) {
    uint32_t nc = 0;
    const ph* chats = nullptr;
    if (f_chats(handle, &nc, &chats) || !chats) return;
    uint64_t t = now_ms();
    ph local = nullptr;
    int remote = 0;
    for (uint32_t i = 0; i < nc && i < 16; i++) {
        uint32_t loc = 0;
        f_chat_local(chats[i], &loc);
        const char* ent = nullptr;
        f_chat_entity(chats[i], &ent);
        char e[48] = "";
        if (ent && readable(ent) >= 2) strncpy_s(e, ent, _TRUNCATE);
        peer& p = g_peers[peer_slot(chats[i])];
        if (strcmp(p.entity, e)) {                       // (new here, or the handle now another player's: unlinked)
            ph c = p.chat;
            memset(&p, 0, sizeof p);
            p.chat = c;
            strcpy_s(p.entity, e);
        }
        p.seen = t;
        p.local = (loc & 0xFF) != 0;
        if (p.local) { if (!local) local = chats[i]; }
        else remote++;
    }
    if (!local) return;
    ph to[16];
    int n = 0;
    for (auto& p : g_peers) {
        if (!p.chat || p.local || p.seen != t || !p.entity[0]) continue;   // (in MCC's list now, its player known)
        if (p.answered) { to[n++] = p.chat; continue; }
        // (the friend's copy only, when it joined, the host the only other player; never to an MCC without the hook)
        if (g_pglink == 2 && g_joined_net && !g_made_net && remote == 1 && p.hellos < 3 &&
            (!p.hellos || t - p.hello_at > 20000)) {
            char text[64];
            sprintf_s(text, "pgl2 hello id=%08x", g_id);
            p.hellos++;
            p.hello_at = t;
            bool ok = send(local, 1, &p.chat, text, 0, nullptr);
            logf("pg link: hello %d of 3 to the host%s", p.hellos, ok ? "" : " (not sent)");
        }
    }
    if (!n) return;
    EnterCriticalSection(&g_cs);
    if (g_out_n && ((g_out_dirty && t - g_out_sent_at >= 200) || t - g_out_sent_at >= 1000)) {
        char text[64];
        sprintf_s(text, "pgl2 st id=%08x n=%u", g_id, g_out_n);
        pbuf b = { g_out, g_out_n };
        send(local, n, to, text, 1, &b);
        g_out_dirty = false;
        g_out_sent_at = t;
    }
    if (g_vote_dirty) {
        send(local, n, to, g_vote_out, 0, nullptr);
        g_vote_dirty = false;
    }
    LeaveCriticalSection(&g_cs);
}

// a pgl2 text in this state change (then it is read here and kept from MCC)
static int g_text_type = -1, g_text_slot = -1, g_data_slot = -1;
static void got(const uint64_t* q, int slot, const char* text) {
    int from = -1;
    for (int k = 1; k <= 6 && from < 0; k++) {
        int i = peer_index((ph)q[k]);
        if (i >= 0 && !g_peers[i].local) from = i;
    }
    if (from >= 0 && !g_peers[from].answered) {
        g_peers[from].answered = true;
        logf("pg link: linked with another PC running Proving Grounds' link");
    }
    unsigned id = 0;
    if (!strncmp(text, "pgl2 hello", 10)) {
        // the host's answer, from the poll's sends (its list now has this PC)
        if (from >= 0) {
            ph local = nullptr;
            for (auto& p : g_peers) if (p.chat && p.local) local = p.chat;
            char ok[64];
            sprintf_s(ok, "pgl2 ok id=%08x", g_id);
            if (local) send(local, 1, &g_peers[from].chat, ok, 0, nullptr);
        }
        return;
    }
    if (!strncmp(text, "pgl2 st ", 8)) {
        unsigned n = 0;
        if (sscanf_s(text, "pgl2 st id=%x n=%u", &id, &n) < 2 || n < 8 || n > PGS_MAX) return;
        const uint8_t* d = nullptr;
        for (int k = 1; k + 1 < 12 && !d; k++) {
            if (g_data_slot >= 0 && k != g_data_slot) continue;
            const uint8_t* b = (const uint8_t*)q[k + 1];
            if ((uint32_t)q[k] == n && readable(b) >= n && !memcmp(b, PGS_MAGIC, 4)) { d = b; g_data_slot = k; }
        }
        if (!d) {
            static int missed;
            if (++missed <= 3) logf("pg link: a state text came without its data");
            return;
        }
        EnterCriticalSection(&g_cs);
        memcpy(g_in, d, n);
        g_in_n = n;
        g_in_at = now_ms();
        LeaveCriticalSection(&g_cs);
        return;
    }
    if (!strncmp(text, "pgl2 vote ", 10)) {
        unsigned key = 0;
        int v = -1, at = 0;
        if (sscanf_s(text, "pgl2 vote id=%x key=%u v=%d name=%n", &id, &key, &v, &at) < 3 || !at) return;
        EnterCriticalSection(&g_cs);
        if (g_nvotes < 8) {
            vote_in& w = g_votes[g_nvotes++];
            strncpy_s(w.name, text + at, _TRUNCATE);
            w.key = key;
            w.v = v;
        }
        LeaveCriticalSection(&g_cs);
    }
}

static bool is_ours(const pchange* c) {
    if (!c || readable(c) < 12 * 8) return false;
    if (g_text_type >= 0 && (int)c->type != g_text_type) return false;
    const uint64_t* q = (const uint64_t*)c;
    for (int k = 1; k < 12; k++) {
        if (g_text_slot >= 0 && k != g_text_slot) continue;
        const char* s = (const char*)q[k];
        size_t r = readable(s);
        if (r < 6 || memcmp(s, "pgl2 ", 5)) continue;
        char text[200];
        size_t len = strnlen(s, r < sizeof text - 1 ? r : sizeof text - 1);
        memcpy(text, s, len);
        text[len] = 0;
        g_text_type = (int)c->type;
        g_text_slot = k;
        got(q, k, text);
        return true;
    }
    return false;
}

// MCC's view of the state changes, without ours: a copy MCC finishes; this finishes the original (as pglink.cpp)
static const pchange* g_copy[4][512];
static struct { const pchange* const* orig; uint32_t n; } g_pend[4];
static const pchange* const g_none[1] = { nullptr };
static uint64_t g_poll_at;

static void after_start(ph handle, uint32_t* count, const pchange* const** changes) {
    uint32_t n = *count;
    const pchange* const* arr = *changes;
    bool ours[512];
    int k = 0;
    for (uint32_t i = 0; i < n && i < 512; i++) {
        uint32_t ty = arr[i] ? arr[i]->type : 0xFFFFFFFF;
        if (ty == T_CREATE_NET) { g_made_net = true; g_joined_net = false; }
        else if (ty == T_CONNECT_NET && !g_made_net) { g_joined_net = true; logf("pg link: this PC joined someone's lobby"); }
        else if (ty == T_NET_DESTROYED || ty == T_LEAVE_NET) {
            g_made_net = g_joined_net = false;
            for (auto& p : g_peers) if (!p.local) p.chat = nullptr;
        }
        ours[i] = is_ours(arr[i]);
        k += ours[i];
    }
    if (k && n <= 512) {
        int slot = -1;
        for (int s = 0; s < 4; s++) if (!g_pend[s].orig) { slot = s; break; }
        if (slot < 0) logf("pg link: no room to hide %d text(s)", k);
        else if ((uint32_t)k == n) {
            o_finish(handle, n, arr);             // (all ours: finished now, MCC gets none)
            *count = 0;
            *changes = g_none;
        } else {
            uint32_t m = 0;
            for (uint32_t i = 0; i < n; i++) if (!ours[i]) g_copy[slot][m++] = arr[i];
            g_pend[slot].orig = arr;
            g_pend[slot].n = n;
            *changes = g_copy[slot];
            *count = m;
        }
    }
    uint64_t t = now_ms();
    if (t - g_poll_at >= 100) { g_poll_at = t; poll(handle); }
}

static perr h_start(ph handle, uint32_t* count, const pchange* const** changes) {
    perr e = o_start(handle, count, changes);
    if (!g_off && !e && count && changes && *changes) {
        __try { after_start(handle, count, changes); }
        __except (EXCEPTION_EXECUTE_HANDLER) {
            g_off = true;
            logf("pg link: a fault (code %08lx): the link stops", GetExceptionCode());
        }
    }
    return e;
}

static perr h_finish(ph handle, uint32_t count, const pchange* const* changes) {
    if (changes == g_none) return 0;             // (all were ours: finished already)
    for (int s = 0; s < 4; s++)
        if (g_pend[s].orig && changes == g_copy[s]) {
            const pchange* const* orig = g_pend[s].orig;
            uint32_t n = g_pend[s].n;
            g_pend[s].orig = nullptr;
            return o_finish(handle, n, orig);
        }
    return o_finish(handle, count, changes);
}

void pg_link_watch() {
    static bool init;
    if (!init) {
        init = true;
        InitializeCriticalSection(&g_cs);
        g_id = (GetTickCount() * 2654435761u) ^ GetCurrentProcessId();
        logf("pg link: %s", g_pglink == 0 ? "off (pglink=0)" : g_pglink == 2
             ? "on; speaks first when this PC joins a host's lobby alone (pglink=2)"
             : "on; answers a friend's link, never speaks first (pglink=1)");
    }
    if (!g_pglink || g_off) return;
    HMODULE m = GetModuleHandleW(L"PartyWin.dll");
    if (!m || m == g_party) return;
    if (g_party) { logf("pg link: PartyWin.dll moved: off"); g_off = true; return; }   // (its old copy's hooks: left)
    void* start = (void*)GetProcAddress(m, "PartyStartProcessingStateChanges");
    void* finish = (void*)GetProcAddress(m, "PartyFinishProcessingStateChanges");
    f_chats = (p_chats)GetProcAddress(m, "PartyGetChatControls");
    f_chat_local = (p_chat_local)GetProcAddress(m, "PartyChatControlIsLocal");
    f_chat_entity = (p_chat_entity)GetProcAddress(m, "PartyChatControlGetEntityId");
    f_chat_send = (p_chat_send)GetProcAddress(m, "PartyChatControlSendText");
    g_party = m;
    if (!start || !finish || !f_chats || !f_chat_local || !f_chat_entity || !f_chat_send) {
        logf("pg link: PartyWin.dll is missing a function: off");
        g_off = true;
        return;
    }
    // (Finish first: once Start is on, MCC may finish a copy at once)
    if (MH_CreateHook(finish, (void*)&h_finish, (void**)&o_finish) != MH_OK ||
        MH_CreateHook(start, (void*)&h_start, (void**)&o_start) != MH_OK ||
        MH_EnableHook(finish) != MH_OK || MH_EnableHook(start) != MH_OK) {
        MH_RemoveHook(start);
        MH_RemoveHook(finish);
        logf("pg link: hooking MCC's Party failed: off");
        g_off = true;
        return;
    }
    g_start_at = start;
    g_finish_at = finish;
    logf("pg link: watching MCC's Party");
}

void pg_link_set_state(const void* data, uint32_t n) {
    if (!g_party || n > PGS_MAX) return;
    EnterCriticalSection(&g_cs);
    if (n != g_out_n || memcmp(g_out, data, n)) {
        memcpy(g_out, data, n);
        g_out_n = n;
        g_out_dirty = true;
    }
    LeaveCriticalSection(&g_cs);
}

uint32_t pg_link_state(void* out, uint32_t cap, uint64_t* age_ms) {
    if (!g_party) return 0;
    EnterCriticalSection(&g_cs);
    uint32_t n = g_in_n <= cap ? g_in_n : 0;
    if (n) memcpy(out, g_in, n);
    *age_ms = g_in_at ? now_ms() - g_in_at : ~0ull;
    LeaveCriticalSection(&g_cs);
    return n;
}

void pg_link_send_vote(uint32_t key, int vote, const char* name) {
    if (!g_party) return;
    EnterCriticalSection(&g_cs);
    sprintf_s(g_vote_out, "pgl2 vote id=%08x key=%u v=%d name=%.31s", g_id, key, vote, name);
    g_vote_dirty = true;
    LeaveCriticalSection(&g_cs);
}

bool pg_link_vote(char* name, int cap, uint32_t* key, int* vote) {
    if (!g_party) return false;
    EnterCriticalSection(&g_cs);
    bool got = g_nvotes > 0;
    if (got) {
        strncpy_s(name, cap, g_votes[0].name, _TRUNCATE);
        *key = g_votes[0].key;
        *vote = g_votes[0].v;
        memmove(g_votes, g_votes + 1, sizeof(vote_in) * (g_nvotes - 1));
        g_nvotes--;
    }
    LeaveCriticalSection(&g_cs);
    return got;
}
