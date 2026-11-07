"""Callout zones and the team voice channel.

Zones: named map areas (polygon + height band + priority) loaded from maps/<map>/callouts.json.
A position belongs to the highest-priority zone that contains it; outside every zone it gets
the nearest zone's name (players still say the closest name they know).

Voice channel: how a sighting becomes a callout a teammate has actually heard.
  recognize (in the bot) -> decide to speak -> speech onset -> say it (syllables / rate)
  -> teammates understand it.
One channel per team: one speaker at a time, urgent calls jump the queue, duplicates merge,
stale calls are dropped instead of read out late. Timing numbers: docs/research/07.
"""
import json
import math
import re
from dataclasses import dataclass, field

from .core import Vec, dist


# ---------------------------------------------------------------- zones
@dataclass
class Zone:
    name: str                 # what is said ("Red tele")
    poly: list                # [(x, y), ...] world units
    side: str = "mid"         # red | blue | mid
    zmin: float = -1e9
    zmax: float = 1e9
    priority: int = 0
    full: str = ""
    aka: list = field(default_factory=list)
    area: bool = False        # a large area: names the gaps next to it
    center: Vec = None

    def edge_distance(s, p):
        """0 inside the outline (height ignored), else distance to the nearest edge."""
        if s.contains(p, check_z=False):
            return 0.0
        best, n = 1e9, len(s.poly)
        for k in range(n):
            (x1, y1), (x2, y2) = s.poly[k], s.poly[(k + 1) % n]
            dx, dy = x2 - x1, y2 - y1
            L2 = dx * dx + dy * dy or 1e-9
            u = max(0.0, min(1.0, ((p.x - x1) * dx + (p.y - y1) * dy) / L2))
            best = min(best, math.hypot(x1 + u * dx - p.x, y1 + u * dy - p.y))
        return best

    def contains(s, p, check_z=True):
        if check_z and not (s.zmin <= p.z <= s.zmax):
            return False
        inside, n = False, len(s.poly)
        for k in range(n):
            (x1, y1), (x2, y2) = s.poly[k], s.poly[(k + 1) % n]
            if (y1 > p.y) != (y2 > p.y) and p.x < (x2 - x1) * (p.y - y1) / (y2 - y1) + x1:
                inside = not inside
        return inside


def syllables(text):
    """Rough English syllable count (vowel groups), good enough for timing short callouts."""
    words = re.findall(r"[a-zA-Z]+|\d+", text)
    total = 0
    for w in words:
        if w.isupper() and len(w) <= 4:
            total += len(w) + w.count("W") * 2     # spelled out: "OS" is "oh-ess"
            continue
        w = w.lower()
        if w.isdigit():
            total += {"1": 1, "2": 1, "3": 1, "4": 1}.get(w, 2)
            continue
        n = len(re.findall(r"[aeiouy]+", w))
        if w.endswith("e") and n > 1 and not w.endswith(("le", "ee")):
            n -= 1
        total += max(1, n)
    return total


def key_part(text, zone):
    """The words a listener needs before acting: everything up to the end of the zone name
    (or the whole call if the zone is not in it)."""
    i = text.find(zone)
    return text[:i + len(zone)] if i >= 0 else text


def read_json(path, tries=20):
    """json.load that waits out a file being rewritten (an editor or tool saving it)."""
    import time
    for k in range(tries):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError):
            if k == tries - 1:
                raise
            time.sleep(0.5)


class ZoneMap:
    def __init__(s, zones):
        s.zones = sorted(zones, key=lambda z: -z.priority)
        s.areas = [z for z in s.zones if z.area]
        for z in s.zones:
            xs, ys = [p[0] for p in z.poly], [p[1] for p in z.poly]
            z.center = Vec(sum(xs) / len(xs), sum(ys) / len(ys), 0)

    @classmethod
    def load(cls, path):
        d = read_json(path)
        return cls([Zone(name=n, poly=[tuple(p) for p in z["poly"]], side=z.get("side", "mid"),
                         zmin=z.get("zmin", -1e9), zmax=z.get("zmax", 1e9), priority=z.get("priority", 0),
                         full=z.get("full", ""), aka=z.get("aka", []), area=z.get("area", False))
                    for n, z in d["zones"].items() if len(z["poly"]) >= 3])   # generated zones can come out empty

    def zone(s, p):
        for z in s.zones:
            if z.contains(p):
                return z
        # in a gap between outlines: the nearest outline names it (big areas win ties),
        # preferring zones whose height band fits
        def score(z):
            return z.edge_distance(p) + (0.0 if z.zmin <= p.z <= z.zmax else 50.0) - 0.01 * z.priority
        return min(s.areas or s.zones, key=score)

    def name(s, p):
        return s.zone(p).name

    def area_name(s, p):
        """Coarse area only ("Mid", "Dark side", "Red side"): what a player in a gunfight blurts."""
        inside = [z for z in s.areas if z.contains(p, check_z=False)]
        if inside:
            return max(inside, key=lambda z: z.priority).name
        return min(s.areas, key=lambda z: z.edge_distance(p)).name if s.areas else s.name(p)


# ---------------------------------------------------------------- timing
# docs/research/07-callout-timing.md section 0 (per tier: novice / average / strong / top).
# Times are seconds after the speaker recognised the thing (lognormal medians).
TIMING = {
    #  p_call: calls a fresh sighting at all when not fighting
    #  decide: pick the message (median, sigma); onset: word retrieval to first sound
    #  urgent_start: pre-loaded urgent word ("Carrier!"), speech start after recognition
    #  rate: syllables/s; hear: listener, after the key words end (listener's own tier)
    #  busy_skip: speaker in a duel drops the call; dead: (chance to call on death, start delay)
    #  self_gap: least time between one speaker's own calls
    "novice":  dict(p_call=0.40, decide=(0.45, 0.40), onset=0.75, urgent_start=0.55, rate=4.5, hear=0.30,
                    busy_skip=0.50, dead=(0.25, 1.0), self_gap=1.0),
    "average": dict(p_call=0.65, decide=(0.25, 0.35), onset=0.55, urgent_start=0.40, rate=5.0, hear=0.25,
                    busy_skip=0.30, dead=(0.50, 0.7), self_gap=1.0),
    "strong":  dict(p_call=0.85, decide=(0.15, 0.30), onset=0.43, urgent_start=0.32, rate=5.5, hear=0.20,
                    busy_skip=0.15, dead=(0.75, 0.5), self_gap=0.5),
    "top":     dict(p_call=0.95, decide=(0.10, 0.25), onset=0.38, urgent_start=0.28, rate=6.0, hear=0.15,
                    busy_skip=0.05, dead=(0.90, 0.4), self_gap=0.5),
}
TIMING["demon"] = dict(p_call=0.95, decide=(0.10, 0.25), onset=0.38, urgent_start=0.28, rate=6.0,
                       hear=0.15, busy_skip=0.05, dead=(0.90, 0.4), self_gap=0.5)
ONSET_SIGMA = 0.20
START_FLOOR = 0.22      # no speech starts sooner than this after recognition
BUSY_EXTRA = 0.40       # speaker in a fight starts later (lognormal, clamped 0.2 to 1.0)
LISTENER_BUSY = 0.15    # a listener in a fight understands later
TURN_GAP = 0.25         # gap before the next speaker (lognormal, floor 0.20; urgent cut-ins skip it)
URGENT_RATE, RATE_CAP = 1.15, 7.5
DOUBLE_KEY = 0.3        # urgent calls double the key word sometimes ("Carrier, carrier!")
STALE = {"seen": 2.0, "cracked": 1.5, "one_shot": 1.5, "died": 2.0}   # not started by then: drop
STALE_URGENT = 1.5
MERGE_WINDOW = 4.0      # same zone and kind said this recently: covered, unless the count rose
URGENT_REPEAT = 1.5     # urgent news about the same zone is repeated at most this often
ANNOUNCER = 0.6         # game announcer / HUD message to understood (UNVERIFIED, research 07)
PRIORITY = {"flag_taken": 0, "flag_dropped": 0, "flag_carrier": 0, "died_at_flag": 0,
            "scored": 0, "enemy_scored": 0, "flag_returned": 0, "backup": 0,
            "seen": 1, "cracked": 1, "one_shot": 1, "died": 1, "pickup": 1}
URGENT = {k for k, p in PRIORITY.items() if p == 0}


@dataclass
class Call:
    kind: str
    zone: str
    pos: Vec
    t_event: float            # when the speaker recognised it (or it happened)
    speaker: int
    tier: str
    busy: bool
    count: int = 1
    enemies: set = field(default_factory=set)
    text: str = ""
    update: bool = False      # a short update of a call just made ("Three now")
    killer_weak: bool = False # dead speaker saw the killer's shields go
    t_start: float = 0.0      # speech starts
    t_key: float = 0.0        # the key words (place, "carrier") have been said
    t_end: float = 0.0        # speech ends (channel free again)
    t_heard: float = 0.0      # the first teammate has understood it
    avail: dict = field(default_factory=dict)   # listener id -> when that listener understands

    @property
    def priority(s):
        return PRIORITY.get(s.kind, 2)

    @property
    def urgent(s):
        return s.priority == 0


class VoiceChannel:
    """One shared voice channel for a team (docs/research/07 section 0.2): one speaker at a
    time with a short gap between speakers, urgent calls first and able to cut in, duplicates
    merged, a repeat inside 4 s skipped unless the count rose, calls that could not start in
    time dropped rather than read out late. Returns calls once their key words are out; the
    director then works out when each teammate understands them."""

    def __init__(s, rng, legacy=False, text_of=str):
        s.rng = rng
        s.text_of = text_of
        s.legacy = legacy     # the first version: flat 0.5 to 2.5 s delay, no channel (for comparison)
        s.queue = []          # waiting to be said
        s.speaking = None     # call being said now
        s.in_flight = []      # being said, key words not out yet
        s.recent = {}         # (zone, kind) -> (time said, count)
        s.last_end = -1e9     # when the channel last went quiet
        s.gap = 0.25
        s.speaker_end = {}    # speaker -> when his last call ended
        s.talk = []           # (start, end) of recent speech, for the talk-time figure
        s.dropped = s.merged = s.silent = 0

    def _ln(s, median, sigma=0.25):
        return median * math.exp(s.rng.gauss(0, sigma))

    def post(s, now, call):
        """Returns what happened: queued | merged (joined a queued call) | covered (the team
        heard this zone moments ago) | dropped (too busy, or dead and quiet) | silent (did
        not bother to call it) | announced."""
        if s.legacy:
            for q in s.queue:
                if q.zone == call.zone and q.kind == call.kind:
                    q.enemies |= call.enemies
                    q.count = len(q.enemies - {None}) or q.count
                    return "merged"
            call.t_start = call.t_key = call.t_end = call.t_heard = now + s.rng.uniform(0.5, 2.5)
            s.queue.append(call)
            return "queued"
        if call.speaker == -1:
            return s.announce(now, call)
        t = TIMING[call.tier]
        dead = call.kind in ("died", "died_at_flag")
        if dead and s.rng.random() > t["dead"][0]:
            s.dropped += 1
            return "dropped"
        # merge with a queued call about the same zone and kind
        for q in s.queue:
            if q.zone == call.zone and q.kind == call.kind:
                q.enemies |= call.enemies
                if q.kind == "seen":
                    q.count = len(q.enemies - {None})
                s.merged += 1
                return "merged"
        # same zone and kind said moments ago: covered, unless more of them showed up
        said_t, said_n = s.recent.get((call.zone, call.kind), (-1e9, 0))
        window = URGENT_REPEAT if call.urgent else MERGE_WINDOW
        speaking_same = s.speaking and s.speaking.zone == call.zone and s.speaking.kind == call.kind
        if now - said_t < window or speaking_same:
            if call.kind == "seen" and call.count > said_n and not speaking_same:
                call.update = True            # "Three now"
            else:
                s.merged += 1
                return "covered"
        if call.busy and not call.urgent and s.rng.random() < t["busy_skip"]:
            s.dropped += 1                    # too busy fighting to talk
            return "dropped"
        if call.kind == "seen" and not call.busy and not call.update and s.rng.random() > t["p_call"]:
            s.silent += 1                     # saw it, never said anything (common in novices)
            return "silent"
        if dead:
            start = s._ln(t["dead"][1], 0.3)
        elif call.urgent:
            start = s._ln(t["urgent_start"], 0.20)
        else:
            dm, dsig = t["decide"]
            start = s._ln(dm, dsig) + s._ln(t["onset"], ONSET_SIGMA)
            if call.busy:
                start += min(1.0, max(0.2, s._ln(BUSY_EXTRA, 0.3)))
        call.t_start = call.t_event + max(START_FLOOR, start)
        s.queue.append(call)
        return "queued"

    def update(s, now):
        """Advance the channel; returns calls whose key words have just been said."""
        out = []
        if s.legacy:
            for c in [c for c in s.queue if now >= c.t_heard]:
                s.queue.remove(c)
                c.text = s.text_of(c)
                out.append(c)
            return out
        for c in [c for c in s.in_flight if now >= c.t_key]:
            s.in_flight.remove(c)
            out.append(c)
        if s.speaking and now >= s.speaking.t_end:
            s.last_end, s.gap = s.speaking.t_end, max(0.20, s._ln(TURN_GAP, 0.3))
            s.speaker_end[s.speaking.speaker] = s.speaking.t_end
            s.speaking = None
        # drop what can no longer be said in time: stale news is worse than none
        for c in list(s.queue):
            limit = STALE_URGENT if c.urgent else STALE.get(c.kind, 2.0)
            if now - c.t_event > limit:
                s.queue.remove(c)
                s.dropped += 1
        due = [c for c in s.queue if c.t_start <= now and
               now >= s.speaker_end.get(c.speaker, -1e9) + TIMING[c.tier]["self_gap"]]
        if not due:
            return out
        due.sort(key=lambda c: (c.priority, c.t_event))
        c = due[0]
        if s.speaking:
            if not (c.urgent and s.speaking.priority > 0):
                return out
            # "Carrier, carrier!": urgent news cuts in. A sighting cut before its key words
            # were out goes back in the queue; one already understood just stops.
            cut = s.speaking
            s.speaking = None
            if cut in s.in_flight:
                s.in_flight.remove(cut)
                cut.t_start = now + 0.3
                s.queue.append(cut)
        elif now < s.last_end + s.gap and not c.urgent:
            return out                        # let the last speaker finish breathing
        s.queue.remove(c)
        s._say(now, c)
        return out

    def _say(s, now, c):
        c.text = s.text_of(c)
        if c.kind == "flag_carrier" and s.rng.random() < DOUBLE_KEY:
            c.text = "Carrier, c" + c.text[1:]          # "Carrier, carrier Red port!"
        t = TIMING[c.tier]
        rate = min(RATE_CAP, s._ln(t["rate"], 0.1) * (URGENT_RATE if c.urgent else 1.0))
        c.t_start = now
        c.t_end = now + syllables(c.text) / rate
        c.t_key = now + syllables(key_part(c.text, c.zone)) / rate
        s.recent[(c.zone, c.kind)] = (now, c.count)
        s.talk = [(a, b) for a, b in s.talk if b > now - 20] + [(now, c.t_end)]
        s.speaking = c
        s.in_flight.append(c)

    def announce(s, now, c):
        """Game announcer and HUD (flag taken / dropped): everyone gets it, no voice needed."""
        c.text = s.text_of(c)
        c.t_start = c.t_end = now
        c.t_key = now + s._ln(ANNOUNCER, 0.15)
        s.in_flight.append(c)
        return "announced"

    def talk_share(s, now):
        """Share of the last 20 s someone was talking (research cap: 60%)."""
        return sum(min(b, now) - max(a, now - 20) for a, b in s.talk if b > now - 20) / 20.0
