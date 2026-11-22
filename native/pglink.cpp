// pglink.cpp (custom, Nov 18): the link test. Can the host's mod and a joined PC friend's mod pass data to each other
// while both are in MCC? (The owner wants Project Noble's search, vote and level-up on a PC friend's screen, following
// the host: "we need this to work in order to expand it even further".) It is a DLL of its own (pglink.dll, loaded by
// pglink_load.exe next to it), so a friend on an older install can run it without a new botcore. It changes nothing
// in MCC's games and logs to pglink.log next to itself. Two links are tested:
//  1. MCC's PlayFab Party network (PartyWin.dll 1.4.13), which MCC uses for voice and text chat. Static read and an
//     offline test of the DLL, Nov 18:
//     - MCC's network allows 0 message endpoints a device (the PartyCreateNewNetwork call at MCC rva 0x25F58F), so
//       endpoint messages are out;
//     - every property call (device, network, endpoint, chat control) answers "API not implemented" in this version;
//     - text chat works: PartyChatControlSendText to chosen chat controls, up to 1023 characters, with data buffers
//       accepted. MCC grants text permissions itself (its chooser at rva 0x261D98 adds 0xC and 0x10).
//     So this sends text messages from this PC's chat control. Only the friend's copy speaks first (a file
//     pglink_friend.txt next to the DLL): it gives each other chat control one "hello" (3 at most, a minute apart).
//     A copy without that file (the host's) never messages first; it only answers a chat control whose pglink spoke
//     to it. (Live, Nov 18: the friend's MCC dropped out 5-10 s after each hello from the host, and no pglink text
//     ever came back, so a hello reaching an MCC without the test may crash it.) Only a chat control that sent a
//     pglink message of its own gets the rest: a post every 3 s (an id, a sequence number, and the last number read
//     from the other side, so a round trip shows in one log). After the answer, a 1023-character text and texts with
//     1000, 4000, 16000 and 60000 data bytes test the sizes. On this PC, every pglink message is taken out of the
//     state changes before MCC sees them (PartyStartProcessingStateChanges and PartyFinishProcessingStateChanges
//     hooked; MCC finishes a copy without them, this finishes the original). Each chat control's entity id, device and
//     the permissions MCC gave it are logged too, for finding which player is which later.
//  2. Halo: Reach's session (haloreach.dll), read only. Is it up in MCC's lobby (state, peers, members)? Do its
//     parameters for Reach's own matchmaking vote and its countdown change on this machine? The session parameters
//     are made by FUN_1803E2xxx: an object a parameter, its type at +8 and its name at +0x10 (the strings
//     "countdown-timer", "matchmaking-voting-results", ...). Each one's bytes after its 0x18-byte header are hashed
//     4 times a second and logged when they change (every 2 s at most).
// For a lobby of PC players who all run it: another player's MCC would get the friend's hellos as chat text.
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdarg.h>
#include <share.h>
#include "third_party/minhook/include/MinHook.h"

static FILE* g_log;
static CRITICAL_SECTION g_log_cs;
static uint32_t g_id;                            // this machine's id in its messages (random a load)
static bool g_first;                             // this copy says hello first (pglink_friend.txt next to the DLL)

static void plog(const char* fmt, ...) {
    if (!g_log) return;
    SYSTEMTIME st;
    GetLocalTime(&st);
    EnterCriticalSection(&g_log_cs);
    fprintf(g_log, "%02d:%02d:%02d.%03d ", st.wHour, st.wMinute, st.wSecond, st.wMilliseconds);
    va_list a;
    va_start(a, fmt);
    vfprintf(g_log, fmt, a);
    va_end(a);
    fputc('\n', g_log);
    fflush(g_log);
    LeaveCriticalSection(&g_log_cs);
}

static uint64_t now_ms() { return GetTickCount64(); }

// bytes readable from p (0: not a readable address)
static size_t readable(const void* p) {
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

// ------------------------------------------------------------------ MCC
static uint8_t* g_exe;
static int menu_state() {                        // as overlay.cpp mcc_menu_state: 0 menus, 1 in a game, -1 unknown
    __try { return g_exe ? g_exe[0x4000B8C + 0x11] : -1; }
    __except (EXCEPTION_EXECUTE_HANDLER) { return -1; }
}
static volatile char g_role = '-';               // from Reach's session: 'h' this machine hosts, 'g' joined, '-' none

// ------------------------------------------------------------------ 1. PlayFab Party (the C API, PartyWin.dll 1.4)
typedef uint32_t perr;
typedef const void* ph;                          // any Party handle
struct pbuf { const void* buffer; uint32_t bytes; };
struct pchange { uint32_t type; };
typedef perr (*p_start)(ph handle, uint32_t* count, const pchange* const** changes);
typedef perr (*p_finish)(ph handle, uint32_t count, const pchange* const* changes);
typedef perr (*p_networks)(ph handle, uint32_t* count, const ph** networks);
typedef perr (*p_net_devices)(ph net, uint32_t* count, const ph** devices);
typedef perr (*p_net_config)(ph net, uint32_t* config);
typedef perr (*p_chats)(ph handle, uint32_t* count, const ph** chats);
typedef perr (*p_chat_local)(ph chat, uint32_t* is_local);
typedef perr (*p_chat_entity)(ph chat, const char** entity);
typedef perr (*p_chat_device)(ph chat, ph* device);
typedef perr (*p_chat_perm)(ph local, ph target, uint32_t* perm);
typedef perr (*p_chat_send)(ph chat, uint32_t ntargets, const ph* targets, const char* text, uint32_t nbufs,
                            const pbuf* bufs);
typedef perr (*p_errmsg)(perr e, const char** msg);

static HMODULE g_party;                          // the PartyWin.dll hooked
static void *g_start_at, *g_finish_at;           // its two functions hooked (for a reload: unhooked first)
static p_start o_start;
static p_finish o_finish;
static p_networks f_networks;
static p_net_devices f_net_devices;
static p_net_config f_net_config;
static p_chats f_chats;
static p_chat_local f_chat_local;
static p_chat_entity f_chat_entity;
static p_chat_device f_chat_device;
static p_chat_perm f_chat_perm;
static p_chat_send f_chat_send;
static p_errmsg f_errmsg;
static volatile bool g_party_off;                // a fault: the Party side stops (MCC's calls still go through)

// the state changes MCC took (PartyStateChangeType, in PartyWin.dll's own name table order, with one gap: offline, a
// new chat control came as 34 then 32, ChatControlCreated and CreateChatControlCompleted, one past the table's own
// places, so one value before 32 has no name there; placed at 31, a guess. Numbers are logged with the names)
static const char* const g_change_names[] = {
    "RegionsChanged", "DestroyLocalUserCompleted", "CreateNewNetworkCompleted", "ConnectToNetworkCompleted",
    "AuthenticateLocalUserCompleted", "NetworkConfigurationMadeAvailable", "NetworkDescriptorChanged",
    "LocalUserRemoved", "RemoveLocalUserCompleted", "LocalUserKicked", "CreateEndpointCompleted",
    "DestroyEndpointCompleted", "EndpointCreated", "EndpointDestroyed", "RemoteDeviceCreated", "RemoteDeviceDestroyed",
    "RemoteDeviceJoinedNetwork", "RemoteDeviceLeftNetwork", "DevicePropertiesChanged", "LeaveNetworkCompleted",
    "NetworkDestroyed", "EndpointMessageReceived", "DataBuffersReturned", "EndpointPropertiesChanged",
    "NetworkJoinabilityChanged", "SetAccessControlListCompleted", "SynchronizeMessagesBetweenEndpointsCompleted",
    "NetworkPropertiesChanged", "KickDeviceCompleted", "KickUserCompleted", "SetJoinabilityCompleted", "(no name)",
    "CreateChatControlCompleted", "DestroyChatControlCompleted", "ChatControlCreated", "ChatControlDestroyed",
    "SetChatAudioEncoderBitrateCompleted", "ChatTextReceived", "VoiceChatTranscriptionReceived",
    "SetChatAudioInputCompleted", "SetChatAudioOutputCompleted", "LocalChatAudioInputChanged",
    "LocalChatAudioOutputChanged", "SetTextToSpeechProfileCompleted", "SynthesizeTextToSpeechCompleted",
    "SetTranscriptionRequestedCompleted", "ChatControlPropertiesChanged", "ChatControlJoinedNetwork",
    "ChatControlLeftNetwork", "ConnectChatControlCompleted", "DisconnectChatControlCompleted",
    "PopulateAvailableTextToSpeechProfilesCompleted", "CreateInvitationCompleted", "RevokeInvitationCompleted",
    "InvitationCreated", "InvitationDestroyed", "SetLanguageCompleted", "SetTranscriptionOptionsCompleted"};
static const int N_CHANGE_NAMES = sizeof g_change_names / sizeof g_change_names[0];
static uint32_t g_changes[96], g_changes_logged[96];
static uint64_t g_changes_at;
static const char* change_name(uint32_t t) { return t < (uint32_t)N_CHANGE_NAMES ? g_change_names[t] : "?"; }

static const char* errmsg(perr e) {
    const char* m = nullptr;
    __try { if (f_errmsg) f_errmsg(e, &m); } __except (EXCEPTION_EXECUTE_HANDLER) { m = nullptr; }
    return m ? m : "";
}

// every chat control this PC has seen
struct chat_seen {
    ph chat;
    uint64_t at;                                 // last seen
    bool local;
    bool answered;                               // a pglink message came from it: it runs the test too
    int hellos;
    uint64_t hello_at, answered_at;
    uint32_t perm;                               // the permissions this PC's chat control has toward it
    int big_stage;                               // the size tests sent to it (0 none, 1 the long text, 2.. data)
    uint64_t big_at;
};
static chat_seen g_chats[32];
static int chat_index(ph chat) {
    for (int i = 0; i < 32; i++) if (g_chats[i].chat == chat) return i;
    return -1;
}
static int chat_slot(ph chat) {
    int i = chat_index(chat);
    if (i >= 0) return i;
    for (i = 0; i < 32; i++)
        if (!g_chats[i].chat || now_ms() - g_chats[i].at > 120000) break;
    if (i == 32) i = 0;
    memset(&g_chats[i], 0, sizeof g_chats[i]);
    g_chats[i].chat = chat;
    g_chats[i].perm = 0xFFFFFFFF;
    return i;
}

static uint32_t g_seq, g_echo;                   // the last sequence posted; the last one read from the other side
static uint64_t g_sent_at[64];                   // when each of the last 64 sequence numbers went out
static uint32_t g_rtt_logged;
static uint64_t g_post_at, g_poll_at;
static perr g_send_err = 0xFFFFFFFF;
static uint32_t g_nets_logged = 0xFFFFFFFF, g_devcount_logged[4] = {0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF};
static uint32_t g_chats_logged = 0xFFFFFFFF;
static ph g_cfg_net[4];
static perr g_net_err;
static int g_text_type = -1, g_text_slot = -1;   // where the texts were found (learned from the first one)
static bool g_layout_logged;

static perr send_text(ph local, int n, const ph* to, const char* text, uint32_t nbufs, const pbuf* bufs,
                      const char* what) {
    perr e = f_chat_send(local, (uint32_t)n, to, text, nbufs, bufs);
    if (e != g_send_err || nbufs || strlen(text) > 200)
        plog(e ? "party: sending %s failed: error %u %s" : "party: sending %s works (error %u%s)", what, e, errmsg(e));
    g_send_err = e;
    return e;
}

static void send_round(ph local) {
    uint64_t t = now_ms();
    ph to[32];
    int n = 0;
    char text[1100];
    for (auto& c : g_chats) {
        if (!c.chat || c.local || t - c.at > 5000) continue;
        if (c.answered) { to[n++] = c.chat; continue; }
        if (g_first && c.hellos < 3 && (!c.hellos || t - c.hello_at > 60000)) {
            sprintf_s(text, "pglink 1 id=%08x role=%c seq=0 echo=%u hello", g_id, g_role, g_echo);
            c.hellos++;
            c.hello_at = t;
            perr e = send_text(local, 1, &c.chat, text, 0, nullptr, "a hello");
            plog("party: hello %d of 3 to chat control %d: error %u", c.hellos, chat_index(c.chat), e);
        }
    }
    if (n && t - g_post_at >= 3000) {
        g_post_at = t;
        uint32_t seq = g_seq + 1;
        sprintf_s(text, "pglink 1 id=%08x role=%c seq=%u echo=%u t=%llu", g_id, g_role, seq, g_echo,
                  (unsigned long long)t);
        if (!send_text(local, n, to, text, 0, nullptr, "a post")) {
            g_seq = seq;
            g_sent_at[seq % 64] = t;
            if (seq <= 3 || seq % 20 == 0) plog("party: posted seq %u to %d chat control(s)", seq, n);
        }
    }
    // the size tests, to the first chat control that answered, 10 s apart
    for (auto& c : g_chats) {
        if (!c.chat || c.local || !c.answered || c.big_stage >= 6) continue;
        if (t - (c.big_stage ? c.big_at : c.answered_at) < 10000) break;
        c.big_stage++;
        c.big_at = t;
        static char data[60001];
        if (c.big_stage == 1) {
            int k = sprintf_s(text, "pglink 1 id=%08x role=%c seq=0 echo=0 long ", g_id, g_role);
            for (; k < 1023; k++) text[k] = (char)('a' + k % 26);
            text[1023] = 0;
            send_text(local, 1, &c.chat, text, 0, nullptr, "a 1023-character text");
        } else {
            uint32_t sz = c.big_stage == 2 ? 1000 : c.big_stage == 3 ? 4000 : c.big_stage == 4 ? 16000 : 60000;
            memcpy(data, "PGDATA", 6);
            for (uint32_t i = 6; i < sz; i++) data[i] = (char)('A' + i % 26);
            sprintf_s(text, "pglink 1 id=%08x role=%c seq=0 echo=0 data n=%u", g_id, g_role, sz);
            pbuf b = {data, sz};
            char what[48];
            sprintf_s(what, "a text with %u data bytes", sz);
            send_text(local, 1, &c.chat, text, 1, &b, what);
        }
        break;
    }
}

static void poll(ph handle) {
    uint32_t nn = 0;
    const ph* nets = nullptr;
    perr e = f_networks(handle, &nn, &nets);
    if (e) {
        if (e != g_net_err) plog("party: no networks (error %u %s)", e, errmsg(e));
        g_net_err = e;
        return;
    }
    g_net_err = 0;
    if (nn != g_nets_logged) {
        plog("party: %u network(s) (MCC menu state %d)", nn, menu_state());
        g_nets_logged = nn;
    }
    for (uint32_t i = 0; i < nn && i < 4 && nets; i++) {
        ph net = nets[i];
        if (net != g_cfg_net[i]) {
            uint32_t cfg[16] = {};
            if (!f_net_config(net, cfg)) {
                plog("party: network %u configuration: %u users, %u devices, %u users a device, %u devices a user, %u "
                     "endpoints a device, [5] %u", i, cfg[0], cfg[1], cfg[2], cfg[3], cfg[4], cfg[5]);
                g_cfg_net[i] = net;
            }
        }
        uint32_t nd = 0;
        const ph* devs = nullptr;
        if (!f_net_devices(net, &nd, &devs) && nd != g_devcount_logged[i]) {
            plog("party: network %u has %u device(s) (MCC menu state %d, Reach session: %s)", i, nd, menu_state(),
                 g_role == 'h' ? "this PC hosts" : g_role == 'g' ? "joined" : "none");
            g_devcount_logged[i] = nd;
        }
    }
    uint32_t nc = 0;
    const ph* chats = nullptr;
    if (f_chats(handle, &nc, &chats) || !chats) return;
    if (nc != g_chats_logged) {
        plog("party: %u chat control(s)", nc);
        g_chats_logged = nc;
    }
    ph local = nullptr;
    for (uint32_t i = 0; i < nc && i < 32; i++) {
        uint32_t loc = 0;
        f_chat_local(chats[i], &loc);
        if ((loc & 0xFF) && !local) local = chats[i];
    }
    for (uint32_t i = 0; i < nc && i < 32; i++) {
        bool fresh = chat_index(chats[i]) < 0;
        chat_seen& c = g_chats[chat_slot(chats[i])];
        c.at = now_ms();
        uint32_t loc = 0;
        f_chat_local(chats[i], &loc);
        c.local = (loc & 0xFF) != 0;
        if (fresh) {
            const char* ent = nullptr;
            ph dev = nullptr;
            f_chat_entity(chats[i], &ent);
            f_chat_device(chats[i], &dev);
            plog("party: chat control %d (%s): entity %s, device %p", chat_index(chats[i]),
                 c.local ? "this PC" : "remote", ent && readable(ent) >= 2 ? ent : "?", dev);
        }
        if (!c.local && local) {
            uint32_t perm = 0;
            if (!f_chat_perm(local, chats[i], &perm) && perm != c.perm) {
                plog("party: this PC's chat permissions toward chat control %d: 0x%X", chat_index(chats[i]), perm);
                c.perm = perm;
            }
        }
    }
    if (local) send_round(local);
}

// a pglink text in this state change? (then it is read here and kept from MCC)
static void got_text(const pchange* c, const uint64_t* q, int slot, const char* text, size_t len) {
    uint64_t t = now_ms();
    int from = -1;
    for (int k = 1; k <= 6; k++) {
        int i = chat_index((ph)q[k]);
        if (i >= 0 && !g_chats[i].local) { from = i; break; }
    }
    if (!g_layout_logged) {
        g_layout_logged = true;
        char line[512] = "";
        for (int k = 0; k < 12; k++) {
            char one[24];
            sprintf_s(one, " [%d]%llx", k, (unsigned long long)q[k]);
            strcat_s(line, one);
        }
        plog("party: the first pglink text came in a state change of type %u (%s), text at slot %d, sender slot "
             "found: %s. Its words:%s", c->type, change_name(c->type), slot, from >= 0 ? "yes" : "no", line);
    }
    if (from >= 0 && !g_chats[from].answered) {
        g_chats[from].answered = true;
        g_chats[from].answered_at = t;
        plog("party: HANDSHAKE: chat control %d runs the test too", from);
    }
    unsigned id = 0, seq = 0, echo = 0;
    char role = '?';
    if (sscanf_s(text, "pglink 1 id=%x role=%c seq=%u echo=%u", &id, &role, 1, &seq, &echo) < 4) {
        plog("party: a pglink text from chat control %d did not read: '%.80s'", from, text);
        return;
    }
    const char* what = role == 'h' ? "host" : role == 'g' ? "joined" : "no Reach session";
    if (strstr(text, " hello")) plog("party: hello from chat control %d: id %08x (%s)", from, id, what);
    else if (strstr(text, " long ")) plog("party: a %zu-character text came from chat control %d", len, from);
    else if (const char* d = strstr(text, " data n=")) {
        unsigned n = 0;
        sscanf_s(d, " data n=%u", &n);
        int at = -1;
        for (int k = 1; k + 1 < 12; k++)
            if ((uint32_t)q[k] == n && readable((const void*)q[k + 1]) >= 6 && !memcmp((const void*)q[k + 1], "PGDATA", 6)) {
                at = k;
                break;
            }
        if (at >= 0) plog("party: a text with %u data bytes came, the data intact at slot %d", n, at);
        else plog("party: a text announcing %u data bytes came, the data not found in the state change", n);
    } else if (seq) {
        g_echo = seq;
        if (seq <= 3 || seq % 20 == 0)
            plog("party: post from chat control %d: id %08x (%s) seq %u, echo %u", from, id, what, seq, echo);
        if (echo && echo != g_rtt_logged && echo <= g_seq && g_seq - echo < 64 && g_sent_at[echo % 64]) {
            g_rtt_logged = echo;
            if (echo <= 3 || echo % 10 == 0)
                plog("party: ROUND TRIP: chat control %d read our seq %u and sent it back: %llu ms (posts every 3 s, "
                     "sent once a second at most)", from, echo, (unsigned long long)(t - g_sent_at[echo % 64]));
        }
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
        if (r < 9 || memcmp(s, "pglink 1 ", 9)) continue;
        size_t len = strnlen(s, r < 2048 ? r : 2048);
        g_text_type = (int)c->type;
        g_text_slot = k;
        got_text(c, q, k, s, len);
        return true;
    }
    return false;
}

// MCC's view of the state changes, without ours: a copy MCC finishes; this finishes the original
static const pchange* g_copy[4][512];
static struct { const pchange* const* orig; uint32_t n; } g_pend[4];
static const pchange* const g_none[1] = {nullptr};
static int g_hidden;

static void after_start(ph handle, uint32_t* count, const pchange* const** changes) {
    uint64_t t = now_ms();
    if (!g_changes_at) g_changes_at = t;
    uint32_t n = *count;
    const pchange* const* arr = *changes;
    bool ours[512];
    int k = 0;
    for (uint32_t i = 0; i < n && i < 512; i++) {
        uint32_t ty = arr[i] ? arr[i]->type : 0xFFFFFFFF;
        ours[i] = is_ours(arr[i]);
        k += ours[i];
        if (ours[i]) continue;
        if (ty < 96) g_changes[ty]++;
        if (ty == 14 || ty == 15 || ty == 16 || ty == 17 || ty == 2 || ty == 3 || ty == 19 || ty == 20 || ty == 34 ||
            ty == 35)
            plog("party: MCC took %s (%u)", change_name(ty), ty);
    }
    if (k && n <= 512) {
        int slot = -1;
        for (int s = 0; s < 4; s++) if (!g_pend[s].orig) { slot = s; break; }
        if (slot < 0) plog("party: no room to hide %d pglink text(s): MCC sees them", k);
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
        if (++g_hidden <= 3) plog("party: %d pglink text(s) kept from MCC", k);
    }
    if (t - g_changes_at > 30000 && memcmp(g_changes, g_changes_logged, sizeof g_changes)) {
        char line[1024] = "";
        for (int j = 0; j < 96; j++)
            if (g_changes[j] != g_changes_logged[j]) {
                char one[96];
                sprintf_s(one, " %s(%u)+%u", change_name(j), j, g_changes[j] - g_changes_logged[j]);
                if (strlen(line) + strlen(one) + 1 < sizeof line) strcat_s(line, one);
            }
        plog("party: MCC's state changes in the last %llus:%s", (unsigned long long)((t - g_changes_at) / 1000), line);
        memcpy(g_changes_logged, g_changes, sizeof g_changes);
        g_changes_at = t;
    }
    if (t - g_poll_at >= 1000) {
        g_poll_at = t;
        poll(handle);
    }
}

static perr h_start(ph handle, uint32_t* count, const pchange* const** changes) {
    perr e = o_start(handle, count, changes);
    if (!g_party_off && !e && count && changes && *changes) {
        __try { after_start(handle, count, changes); }
        __except (EXCEPTION_EXECUTE_HANDLER) {
            g_party_off = true;
            plog("party: a fault in the test (code %08lx): the Party side stops", GetExceptionCode());
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

static void party_watch() {
    HMODULE m = GetModuleHandleW(L"PartyWin.dll");
    if (!m) m = GetModuleHandleW(L"PartyWin7.dll");
    if (m == g_party) return;
    if (g_party) {
        plog("party: PartyWin.dll unloaded or moved");
        g_party = nullptr;
    }
    if (g_start_at) {                            // (MinHook's records of the old copy: its code may be gone)
        __try { MH_RemoveHook(g_start_at); MH_RemoveHook(g_finish_at); }
        __except (EXCEPTION_EXECUTE_HANDLER) {}
        g_start_at = g_finish_at = nullptr;
    }
    if (!m) return;
    void* start = (void*)GetProcAddress(m, "PartyStartProcessingStateChanges");
    void* finish = (void*)GetProcAddress(m, "PartyFinishProcessingStateChanges");
    f_networks = (p_networks)GetProcAddress(m, "PartyGetNetworks");
    f_net_devices = (p_net_devices)GetProcAddress(m, "PartyNetworkGetDevices");
    f_net_config = (p_net_config)GetProcAddress(m, "PartyNetworkGetNetworkConfiguration");
    f_chats = (p_chats)GetProcAddress(m, "PartyGetChatControls");
    f_chat_local = (p_chat_local)GetProcAddress(m, "PartyChatControlIsLocal");
    f_chat_entity = (p_chat_entity)GetProcAddress(m, "PartyChatControlGetEntityId");
    f_chat_device = (p_chat_device)GetProcAddress(m, "PartyChatControlGetDevice");
    f_chat_perm = (p_chat_perm)GetProcAddress(m, "PartyChatControlGetPermissions");
    f_chat_send = (p_chat_send)GetProcAddress(m, "PartyChatControlSendText");
    f_errmsg = (p_errmsg)GetProcAddress(m, "PartyGetErrorMessage");
    g_party = m;
    if (!start || !finish || !f_networks || !f_net_devices || !f_net_config || !f_chats || !f_chat_local ||
        !f_chat_entity || !f_chat_device || !f_chat_perm || !f_chat_send) {
        plog("party: PartyWin.dll at %p is missing a function this test needs: not hooked", m);
        return;
    }
    // (Finish first: once Start is on, MCC may finish a copy at once)
    if (MH_CreateHook(finish, (void*)&h_finish, (void**)&o_finish) != MH_OK) {
        plog("party: hooking PartyFinishProcessingStateChanges failed");
        return;
    }
    g_finish_at = finish;
    if (MH_CreateHook(start, (void*)&h_start, (void**)&o_start) != MH_OK) {
        MH_RemoveHook(finish);
        g_finish_at = nullptr;
        plog("party: hooking PartyStartProcessingStateChanges failed");
        return;
    }
    g_start_at = start;
    if (MH_EnableHook(finish) != MH_OK || MH_EnableHook(start) != MH_OK) {
        MH_RemoveHook(start);
        MH_RemoveHook(finish);
        g_start_at = g_finish_at = nullptr;
        plog("party: turning the Party hooks on failed");
        return;
    }
    wchar_t path[MAX_PATH] = L"";
    GetModuleFileNameW(m, path, MAX_PATH);
    plog("party: watching MCC's Party (%ls at %p)", path, m);
}

// ------------------------------------------------------------------ 2. Halo: Reach's session (read only)
static const uintptr_t HR_SESSION = 0x4E0E910;   // reach.cpp's: the session is *(*(this) + 0x18)
static const uint32_t S_END = 0x60EF0;           // the session object's size is past +0x60EF8 (its state)
static uint8_t* g_hr;
static uint8_t* g_s;
struct pwatch {
    const char* name;
    uint32_t len;                                // bytes after the 0x18-byte header
    uint32_t off;                                // the object's offset in the session (0 not found)
    uint64_t hash;
    uint32_t changes;                            // since the last line
    uint64_t logged_at;
    uint8_t prev[64];
};
static pwatch g_pw[] = {
    {"life-cycle", 0x90}, {"game-start-status", 0x98}, {"countdown-timer", 0x98}, {"matchmaking-progress", 0x100},
    {"matchmaking-voting-results", 0xA8}, {"matchmaking-voting-rounds", 0x1440},
    {"matchmaking-voting-descriptions", 0x1000}};
static int g_s_state = -99, g_s_host = -99, g_s_local = -99;
static uint32_t g_s_peers, g_s_players;
static int g_menu_logged = -99;

static uint64_t fnv(const uint8_t* p, uint32_t n) {
    uint64_t h = 1469598103934665603ull;
    for (uint32_t i = 0; i < n; i++) h = (h ^ p[i]) * 1099511628211ull;
    return h;
}

// a name string in haloreach.dll's read-only data
static const uint8_t* find_string(uint8_t* mod, const char* s) {
    IMAGE_NT_HEADERS* nt = (IMAGE_NT_HEADERS*)(mod + ((IMAGE_DOS_HEADER*)mod)->e_lfanew);
    IMAGE_SECTION_HEADER* sec = IMAGE_FIRST_SECTION(nt);
    size_t n = strlen(s) + 1;
    for (int i = 0; i < nt->FileHeader.NumberOfSections; i++, sec++) {
        if ((sec->Characteristics & IMAGE_SCN_MEM_EXECUTE) || !(sec->Characteristics & IMAGE_SCN_MEM_READ)) continue;
        const uint8_t* a = mod + sec->VirtualAddress;
        size_t len = sec->Misc.VirtualSize;
        for (size_t k = 1; k + n <= len; k++)
            if (a[k] == (uint8_t)s[0] && !a[k - 1] && !memcmp(a + k, s, n)) return a + k;
    }
    return nullptr;
}

static int g_params_found = -1;                  // (the last find's count: it is tried again every 10 s till all are)
static uint64_t g_params_at;
static void find_params(uint8_t* s) {
    int found = 0;
    g_params_at = now_ms();
    for (auto& w : g_pw) {
        w.off = 0;
        w.hash = 0;
        const uint8_t* str = find_string(g_hr, w.name);
        if (!str) continue;
        for (uint32_t o = 0x10; o + 8 <= S_END; o += 8)
            if (*(const uint8_t* const*)(s + o) == str) {
                uint32_t obj = o - 0x10;
                uint32_t type = *(uint32_t*)(s + obj + 8);
                if (type < 0x80 && obj + 0x18 + w.len <= S_END) { w.off = obj; found++; }
                break;
            }
    }
    if (found == g_params_found) return;
    g_params_found = found;
    char line[512] = "";
    for (auto& w : g_pw) {
        char one[80];
        sprintf_s(one, " %s(not found)", w.name);
        if (w.off) sprintf_s(one, " %s@+0x%X(type 0x%X)", w.name, w.off, *(uint32_t*)(s + w.off + 8));
        if (strlen(line) + strlen(one) + 1 < sizeof line) strcat_s(line, one);
    }
    plog("reach: session parameters found %d of %d:%s", found, (int)(sizeof g_pw / sizeof g_pw[0]), line);
}

static void reach_probe_inner() {
    int menu = menu_state();
    if (menu != g_menu_logged) {
        plog("mcc: menu state %d (%s)", menu, menu == 0 ? "menus" : menu == 1 ? "in a game" : "?");
        g_menu_logged = menu;
    }
    uint8_t* hr = (uint8_t*)GetModuleHandleW(L"haloreach.dll");
    if (hr != g_hr) {
        plog(hr ? "reach: haloreach.dll loaded at %p" : "reach: haloreach.dll unloaded", hr);
        g_hr = hr;
        g_s = nullptr;
        g_s_state = g_s_host = g_s_local = -99;
        g_role = '-';
    }
    if (!hr) return;
    uint8_t* so = *(uint8_t**)(hr + HR_SESSION);
    uint8_t* s = so ? *(uint8_t**)(so + 0x18) : nullptr;
    if (s != g_s) {
        plog(s ? "reach: session object at %p" : "reach: no session object", s);
        g_s = s;
        g_s_state = g_s_host = g_s_local = -99;
        g_role = '-';
        g_params_found = -1;
        if (s) find_params(s);
    }
    if (!s) return;
    if (g_params_found < (int)(sizeof g_pw / sizeof g_pw[0]) && now_ms() - g_params_at > 10000) find_params(s);
    int state = *(int32_t*)(s + 0x60EF8), host = *(int32_t*)(s + 0x40), local = *(int32_t*)(s + 0x4464);
    uint32_t peers = *(uint32_t*)(s + 0x5C), players = *(uint32_t*)(s + 0x173C);
    if (state != g_s_state || host != g_s_host || local != g_s_local || peers != g_s_peers || players != g_s_players) {
        int np = 0, nm = 0;
        for (int i = 0; i < 17; i++) np += (peers >> i) & 1;
        for (int i = 0; i < 16; i++) nm += (players >> i) & 1;
        plog("reach: session state %d, host peer %d, this peer %d (%s), %d peer(s) mask %05X, %d member(s) mask %04X, "
             "MCC menu state %d", state, host, local, host == local && host >= 0 ? "this PC hosts" : "joined", np, peers,
             nm, players, menu);
        g_s_state = state; g_s_host = host; g_s_local = local; g_s_peers = peers; g_s_players = players;
    }
    g_role = host >= 0 && host == local ? 'h' : local >= 0 ? 'g' : '-';
    uint64_t t = now_ms();
    for (auto& w : g_pw) {
        if (!w.off) continue;
        const uint8_t* d = s + w.off + 0x18;
        uint64_t h = fnv(d, w.len);
        if (h == w.hash) continue;
        bool first = !w.hash;
        w.hash = h;
        w.changes++;
        if (!first && t - w.logged_at < 2000) continue;
        int diff = 0;
        for (int i = 0; i < 64 && (uint32_t)i < w.len; i++) diff += d[i] != w.prev[i];
        char hex[3 * 48 + 1] = "";
        for (int i = 0; i < 48 && (uint32_t)i < w.len; i++) sprintf_s(hex + 3 * i, 4, "%02X ", d[i]);
        plog("reach: %s %s (%u change(s); %d of its first 64 bytes differ): %s", w.name, first ? "now" : "changed",
             w.changes, first ? 0 : diff, hex);
        memcpy(w.prev, d, w.len < 64 ? w.len : 64);
        w.changes = 0;
        w.logged_at = t;
    }
}

static volatile bool g_reach_off;
static void reach_probe() {
    if (g_reach_off) return;
    __try { reach_probe_inner(); }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        g_reach_off = true;
        plog("reach: a fault reading the session (code %08lx): the Reach side stops", GetExceptionCode());
    }
}

// ------------------------------------------------------------------ start
static DWORD WINAPI worker(void* self) {
    wchar_t path[MAX_PATH];
    GetModuleFileNameW((HMODULE)self, path, MAX_PATH);
    wchar_t marker[MAX_PATH];
    wcscpy_s(marker, path);
    if (wchar_t* slash = wcsrchr(marker, L'\\')) {
        slash[1] = 0;
        wcscat_s(marker, L"pglink_friend.txt");
        g_first = GetFileAttributesW(marker) != INVALID_FILE_ATTRIBUTES;
    }
    wchar_t* dot = wcsrchr(path, L'.');
    if (dot) wcscpy_s(dot, 5, L".log");
    InitializeCriticalSection(&g_log_cs);
    g_log = _wfsopen(path, L"w", _SH_DENYNO);
    g_exe = (uint8_t*)GetModuleHandleW(L"MCC-Win64-Shipping.exe");
    g_id = (GetTickCount() * 2654435761u) ^ GetCurrentProcessId();
    plog("pglink test 3 (Nov 18): id %08x, process %lu, MCC %s", g_id, GetCurrentProcessId(),
         g_exe ? "found" : "NOT found");
    plog(g_first ? "role: friend's copy (pglink_friend.txt found): says hello first"
                 : "role: host's copy (no pglink_friend.txt): never messages first, only answers another pglink");
    MH_STATUS mh = MH_Initialize();
    if (mh != MH_OK && mh != MH_ERROR_ALREADY_INITIALIZED) plog("MinHook failed to start (%d)", (int)mh);
    for (;;) {
        __try { party_watch(); }
        __except (EXCEPTION_EXECUTE_HANDLER) { plog("party: a fault looking for PartyWin.dll"); }
        reach_probe();
        Sleep(250);
    }
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(h);
        HANDLE t = CreateThread(nullptr, 0, worker, h, 0, nullptr);
        if (t) CloseHandle(t);
    }
    return TRUE;
}
