"""The bot simulation's model and match engine (custom, Nov 17; the owner: "a bot simulation system where they play
games ... so that the website tracker gives bots a chance to keep up"; docs/BOT_SIMULATION_PLAN.md is the agreed plan).
tools/bot_sim.py decides who plays and stores the results; this file says how well each bot plays (fit) and plays one
match fight by fight (play).

What it knows, and where from (the plan's ladder: Reach's rules, then the bot's own real matches, then its tier's, then
the map and gametype's; otherwise nothing):
  - skill: the bot's difficulty (TIER_SKILL), nothing else (the owner, Nov 19). fit still works out a Bradley-Terry
    skill from the real matches (Model.skill), but no simulated match uses it.
  - pace, assists, suicides, betrayals, headshots, weapon mix, the medals the rules cannot work out: each bot's real
    numbers, shrunk toward its tier's and everyone's ((own + C * typical) / (count + C)).
  - each map's weapons and vehicles, with their respawn times: the game's own files (maps/<map>/objects.json from the
    scenario; a Forge or Anniversary layout's .mvar, brain/mvar.py). Where kills land: the real kill spots on that map
    when there are enough, else the map's own respawn points and weapon spots.
  - score and time limits: the real matches of that gametype when they show them, else Reach's usual ones.
  - medals: multi-kills (4 s), sprees, Killjoy, Revenge, Avenger, First Strike, Extermination, Perfection, weapon
    sprees, Wheelman, Splatter, Hijack by Reach's rules on the fight-by-fight record; the rest at the rates real
    matches show them.

Randomness is this file's own (Rng, splitmix64), so a seed plays the same match on any Python.
"""
import json
import math
import os
import sys

ENGINE = 1                                   # (stored with each match: a later engine keeps the old one's matches)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ---------------------------------------------------------------- randomness of our own
M64 = (1 << 64) - 1


class Rng:
    """splitmix64: the same numbers from a seed on any Python (random.Random's own methods may change)."""

    def __init__(self, seed):
        self.s = int(seed) & M64

    def u64(self):
        self.s = (self.s + 0x9E3779B97F4A7C15) & M64
        z = self.s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        return z ^ (z >> 31)

    def random(self):
        return (self.u64() >> 11) / 9007199254740992.0

    def below(self, n):
        return int(self.random() * n) if n > 0 else 0

    def chance(self, p):
        return self.random() < p

    def pick(self, seq):
        return seq[self.below(len(seq))]

    def weighted(self, weights):
        total = sum(weights)
        if total <= 0:
            return self.below(len(weights))
        r, acc = self.random() * total, 0.0
        for i, w in enumerate(weights):
            acc += w
            if r < acc:
                return i
        return len(weights) - 1

    def expo(self, rate):
        return -math.log(1.0 - self.random()) / rate if rate > 0 else float("inf")

    def gauss(self, mu=0.0, sd=1.0):
        u1, u2 = max(self.random(), 1e-12), self.random()
        return mu + sd * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    def poisson(self, lam):
        if lam <= 0:
            return 0
        if lam > 30:
            return max(0, int(round(self.gauss(lam, math.sqrt(lam)))))
        limit, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= self.random()
            if p <= limit:
                return k
            k += 1

    def shuffle(self, seq):
        for i in range(len(seq) - 1, 0, -1):
            j = self.below(i + 1)
            seq[i], seq[j] = seq[j], seq[i]
        return seq


def hash_of(s, salt):
    """native/proving_grounds.cpp hash_of: FNV-1a of the lower-cased name, mixed (the bots' tastes, the same values)."""
    h = (2166136261 ^ salt) & 0xFFFFFFFF
    for c in s.encode("utf-8"):
        if 65 <= c <= 90:
            c += 32
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return h


def hfloat(name, salt):
    return (hash_of(name, salt) & 0xFFFF) / 65535.0


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, x))))


# ---------------------------------------------------------------- tiers, styles
# bots_panel.cpp TIER_KEY (bot_pool_saved.ini's difficulty names) and its Mixed deal (roster_mixed_tier)
TIERS = ["novice", "average", "strong", "top", "scaling", "demon", "blind", "tactician", "mythic", "noble"]
TIER_NAME = {"novice": "Easy", "average": "Normal", "strong": "Heroic", "top": "Legendary", "scaling": "Scaling",
             "demon": "Demon", "blind": "Blind", "tactician": "Tactician", "mythic": "Mythic", "noble": "Noble"}
MIXED = ["average", "novice", "strong", "top", "demon", "blind"]
TOP_TIERS = {"top", "blind", "mythic", "demon", "noble"}          # (the owner: "Legendary and above")
# each tier's skill (logit units: a 1.0 edge wins 73% of even fights), in the difficulty picker's order: a simulated
# bot plays at its tier's, whatever its real matches. Noble (the testing difficulty, Demon's base in game): Demon's
# (Nov 23, the owner: "Yes like demon")
TIER_SKILL = {"novice": -1.2, "average": -0.6, "strong": 0.0, "tactician": 0.3, "top": 0.6, "scaling": 0.6,
              "blind": 0.5, "mythic": 0.85, "demon": 1.1, "noble": 1.1}
SWEAT = {"novice": -0.7, "average": -0.35, "strong": 0.0, "top": 0.45, "scaling": 0.2, "demon": 0.85, "blind": 0.45,
         "tactician": 0.3, "mythic": 0.65, "noble": 0.85}           # (proving_grounds.cpp sweat_of BY_TIER)
# a Noble wins this share of even fights against a Demon, each Noble its own fixed roll in it from its name (Nov 23, the
# owner: "In the simulations make the nobles 5-10% better than demons"; asked, he chose fights won, each its own roll)
NOBLE_EDGE = (0.55, 0.60)
# (Nov 23, the owner, after "After 46 games not a single bot has a 2 or more kd" and his and a friend's real Infinite
# games, 2 to 16 K/D: "Yes, flip flop + B") the tiers' strength gaps in fights twice TIER_SKILL's (a Demon beats a
# Legendary 73% of fights, not 62%), and fights found HUNT times more often between mismatched players
# (exp(HUNT * gap): the strong hunt the weak, as in a real Big Team Battle). Measured on his pool before it went in:
# Demons 1.40 -> about 3.5, Nobles 1.77 -> about 5.5. Fitted models carry them; each match stores its own (slice).
# Then (the owner: "cloudybarracude going 91/4 in a 100 kill game isnt realistic. 4 of the top 5 games all have over
# 100 kills"): one Demon in a lobby of weaker bots was in nearly every fight (hunting up to 27 times), 90-121 kills.
# HUNT_MAX caps a pair's hunting at 3 times, and the gaps went to 3 times TIER_SKILL's (he chose "Balanced"): measured
# on his pool (hunt_tune, 10 rounds): the top player of a 4v4 about 40 kills (57 in a big game, 67 at most; his real
# 4v4 matches: 35, 46), 27% of the match's kills (real 23%); Demons 3.0 K/D, Nobles 3.5, best bots 5-5.7.
SKILL_SCALE = 3.0
HUNT = 1.5
HUNT_MAX = 3.0


def skill_of(name, tier, scale=1.0):
    """A simulated bot's strength: its tier's TIER_SKILL times scale (SKILL_SCALE for new matches); a Noble's, Demon's
    plus its own NOBLE_EDGE roll (as log-odds: a fight is won with sigmoid of the strengths' difference, so a Noble wins
    55-60% against a Demon whatever the scale)."""
    s = TIER_SKILL.get(tier, 0.0) * scale
    if tier == "noble":
        p = NOBLE_EDGE[0] + (NOBLE_EDGE[1] - NOBLE_EDGE[0]) * hfloat(name, 67)
        s += math.log(p / (1.0 - p))
    return s


STYLES = ["rusher", "camper", "flanker", "objector", "spammer", "grudger", "sniper", "wheelman", "any"]

# ---------------------------------------------------------------- weapons, vehicles (tools/service_record_site/weapons.json)
MAGNUM, AR, DMR, SHOTGUN, SNIPER, ROCKETS, LASER, FRAG, GL = 4, 5, 6, 7, 8, 9, 10, 11, 12
PLASMA_PISTOL, NEEDLER, PLASMA_RIFLE, REPEATER, NEEDLE_RIFLE, SPIKER, PLASMA_LAUNCHER = 13, 14, 15, 16, 17, 18, 19
HAMMER, SWORD, PLASMA_NADE, CONCUSSION, MELEE, FOCUS, FUEL_ROD = 20, 21, 22, 23, 43, 63, 64
MG_TURRET, PLASMA_TURRET = 54, 55
FLAG_DT, BOMB_DT, BALL_DT, SUICIDE_DT, FALL_DT = 46, 47, 49, 3, 41
PRECISION = {MAGNUM, DMR, SNIPER, NEEDLE_RIFLE, FOCUS}
GRENADES = {FRAG, PLASMA_NADE}
ITEM_DT = {
    "magnum": MAGNUM, "assault_rifle": AR, "dmr": DMR, "shotgun": SHOTGUN, "sniper": SNIPER, "sniper_rifle": SNIPER,
    "rockets": ROCKETS, "rocket_launcher": ROCKETS, "spartan_laser": LASER, "frag_grenade": FRAG,
    "grenade_launcher": GL, "plasma_pistol": PLASMA_PISTOL, "needler": NEEDLER, "plasma_rifle": PLASMA_RIFLE,
    "plasma_repeater": REPEATER, "needle_rifle": NEEDLE_RIFLE, "spiker": SPIKER, "plasma_launcher": PLASMA_LAUNCHER,
    "gravity_hammer": HAMMER, "sword": SWORD, "energy_sword": SWORD, "plasma_grenade": PLASMA_NADE,
    "concussion_rifle": CONCUSSION, "focus_rifle": FOCUS, "fuelrod": FUEL_ROD, "fuel_rod_gun": FUEL_ROD,
    "fuel_rod_cannon": FUEL_ROD, "machinegun": MG_TURRET, "machinegun_turret": MG_TURRET,
    "plasma_turret_mounted": PLASMA_TURRET, "plasma_turret": PLASMA_TURRET,
}
# a power weapon held: (kills its ammo lasts, at most; its share of the holder's kills; its edge in a fight; the play
# style that goes for it). Reach's ammo per pickup in kills, roughly: sniper 4 + 8 rounds, rockets 2 + 2, ...
POWER = {SNIPER: (5, 0.85, 0.6, "sniper"), ROCKETS: (4, 0.9, 1.1, "rusher"), LASER: (5, 0.9, 1.0, "sniper"),
         SHOTGUN: (6, 0.85, 0.8, "rusher"), SWORD: (8, 0.9, 1.0, "rusher"), HAMMER: (8, 0.9, 1.0, "rusher"),
         GL: (5, 0.8, 0.6, "spammer"), FOCUS: (5, 0.8, 0.4, "sniper"), FUEL_ROD: (5, 0.85, 0.8, "rusher"),
         PLASMA_LAUNCHER: (4, 0.85, 0.8, "rusher"), CONCUSSION: (5, 0.75, 0.4, "spammer"),
         MG_TURRET: (8, 0.85, 0.6, "camper"), PLASMA_TURRET: (8, 0.85, 0.6, "camper")}
# vehicles: driver's damage type, gunner's (None: no gun seat), share of the driver's kills that are splatters, its
# edge in a fight, how much more it fights, an aircraft (Skyjack), the driver's other weapon and its share
VEHICLES = {
    "warthog": (33, 34, 1.0, 0.6, 1.4, False, None, 0.0), "warthog_gauss": (33, 35, 1.0, 0.7, 1.4, False, None, 0.0),
    "warthog_rocket": (33, 36, 1.0, 0.7, 1.4, False, None, 0.0), "mongoose": (32, None, 1.0, 0.0, 0.8, False, None, 0.0),
    "ghost": (24, None, 0.3, 0.5, 1.5, False, None, 0.0), "revenant": (25, 26, 0.15, 0.7, 1.4, False, None, 0.0),
    "wraith": (27, 28, 0.1, 1.0, 1.5, False, None, 0.0), "scorpion": (37, 38, 0.05, 1.2, 1.6, False, None, 0.0),
    "banshee": (29, None, 0.0, 0.9, 1.7, True, 30, 0.35), "falcon": (39, 40, 0.0, 0.8, 1.5, True, None, 0.0),
}
SPLATTER_DT = {33, 32, 24, 25, 27, 37}
ANTI_VEHICLE = {ROCKETS, LASER, PLASMA_LAUNCHER, GL, FUEL_ROD, PLASMA_PISTOL, CONCUSSION, PLASMA_NADE}

# ---------------------------------------------------------------- medals (MCC's numbers: art/medals.json)
MULTI = [None, None, 62, 224, 162, 140, 142, 134, 141, 139, 137]      # Double .. Killionaire (4 s apart)
SPREES = [(5, 136), (10, 135), (15, 189), (20, 173), (25, 231), (30, 127), (35, 123), (40, 229)]
WEAPON_SPREE = {SNIPER: 210, SHOTGUN: 199, SWORD: 220, HAMMER: 251, LASER: 257}
M_ASSIST, M_HEADSHOT, M_MELEE, M_SNIPER, M_LASER, M_SPLATTER, M_SPLATTER_SPREE = 8, 111, 156, 266, 149, 212, 213
M_KILLJOY, M_REVENGE, M_AVENGER, M_FIRST, M_EXTERMINATION, M_PERFECTION = 138, 184, 9, 74, 69, 167
M_WHEELMAN, M_WHEELMAN_SPREE, M_ASSIST_SPREE, M_HIJACK, M_SKYJACK = 239, 260, 254, 114, 205
M_BEATDOWN, M_ASSASSINATION, M_STICK, M_SUPERCOMBINE = 29, 7, 105, 217
M_FLAG_CAP, M_FLAG_CARRIER_KILL, M_FLAG_KILL, M_BOMB_PLANT, M_BOMB_CARRIER_KILL, M_BOMB_KILL = 77, 78, 83, 38, 33, 37
M_BALL_CARRIER_KILL, M_BALL_KILL, M_KING_KILL, M_TERRITORY = 10, 16, 145, 48
# medals on a kill at the rate real matches show them (per kill; the weapon ones per kill with that weapon)
STYLE_MEDALS = [54, 180, 171, 270, 110, 130, 271, 267]   # Close Call, Reload This, Protector, Second Wind, Headcase,
                                                          # Kill From The Grave, Firebird, Kill Jetpack
WEAPON_MEDALS = [(M_MELEE, MELEE), (M_BEATDOWN, MELEE), (M_ASSASSINATION, MELEE), (M_SNIPER, SNIPER),
                 (M_LASER, LASER), (M_STICK, PLASMA_NADE), (M_SUPERCOMBINE, NEEDLER)]
MODE_MEDALS = {"ctf": [M_FLAG_CARRIER_KILL, M_FLAG_KILL], "assault": [M_BOMB_CARRIER_KILL, M_BOMB_KILL],
               "koth": [M_KING_KILL]}

# ---------------------------------------------------------------- gametypes
# Reach's usual limits when no real match of the gametype shows them: (score, seconds)
FAMILY_RULES = {"slayer": (50, 720), "ctf": (3, 720), "assault": (3, 720), "koth": (150, 720),
                "oddball": (200, 600), "territories": (150, 720), "stockpile": (10, 600), "headhunter": (50, 720)}
# score limits that hold whatever the real matches showed, (family, team size) -> score (Nov 23, the owner: "the site
# simulates BTB (8v8) slayer games to a score of 50 but its too 100"; the real BTB Slayer games had all run to time, so
# the model had kept the 50 above)
SCORE_RULES = {("slayer", 8): 100}
FAMILY_TOKENS = {"ctf": ("ctf - flag", "mp_flag_base", "ctf_flag_return"), "assault": ("as_bomb", "as_goal"),
                 "koth": ("koth_hill", "mp_hill_beacon"), "oddball": ("oddball_ball",), "territories": ("terr_object",),
                 "stockpile": ("stp_flag", "stp_goal"), "headhunter": ("hh_drop_point",)}
OBJ_RATE = {"ctf": 3.0 / 720, "assault": 3.0 / 720, "stockpile": 10.0 / 600}   # a team's scoring rate, even teams
# Multi Flag as the owner's own games play it (Nov 23, the owner: "use the capture the flag game I played on asylum
# earlier to match other sim games to ... Multi flags end with too little kills"; asked about captures: "About one
# capture per team every 25 minutes ... if the difficulties on either team are similar. If the games have more skill
# diversity on teams you can make it 3-0 or 2-1 or 3-1"). Stored with each match (model_slice), so earlier ones replay.
# kills a player a minute, (gametype, team size): his Asylum game, Nov 22: 168 kills, 4v4, 12.2 minutes
KPM_RULES = {("tu multi flag ctf", 4): 1.73}
# a team's capture rate (per second) between even teams, and how steeply the stronger team's grows with the teams'
# strength gap (exp(k * gap), the gap of the whole teams this match): his three full-length real Multi Flag games had 3
# captures in about 74 team-minutes. Tuned on his model (mf_calib, Nov 23): even 4v4 about 1 capture a game (0-0, 1-0,
# 1-1, 2-0), 11.8 min, 160 kills; Demon against Heroic mostly 3-0 in 7.6 min; 8v8 about 0.5, 12 min, 200 kills
# The third number (Nov 23, with SKILL_SCALE and HUNT): a team scores at most 16 times the even rate; with the steeper
# gaps a weaker team was often all dead at once and lost 3-0 in about a minute. With them the even rate is one in 26
# min (was 40): even 4v4 about 1 capture a game, 11.8 min, 158 kills; Demon against Heroic mostly 3-0 in 6.6 min.
OBJ_RULES = {"tu multi flag ctf": (1.0 / 1560, 2.2, 16.0)}
ROUND_SECS, ROUNDS = 180.0, 4                              # One Flag, One Bomb: 4 rounds of 3 minutes, sides swap
KOTH_HELD = 0.45                                           # (real Crazy King: about 45% of seconds score for someone)
RESPAWN = 5.0
MATCH_SD = 0.45
DRIVER_SHARE = 0.35                                        # (a two-seat vehicle's driver fights this much of its rate)
AVENGER_S = 3.0                                            # (an enemy who killed a teammate this recently)                                            # (bot_sim.py --check: real K/D inside the simulated 90% band)


def family(type_name):
    """tools/service_record.py family (the same rules)."""
    import service_record as sr
    return sr.family(type_name)


def rounds_of(gametype):
    """One Flag and One Bomb are played in rounds, a side attacking each."""
    t = (gametype or "").upper()
    return ROUNDS if ("ONE FLAG" in t or "ONE BOMB" in t) else 1


def starting_weapons(gametype):
    """What everyone spawns with (Reach's TU loadouts: the DMR gametypes the DMR and Magnum; the others DMR or AR)."""
    base = {DMR, MAGNUM, FRAG, MELEE}
    return base if "DMR" in (gametype or "").upper() else base | {AR}


# ---------------------------------------------------------------- maps
def _floats(p):
    if isinstance(p, str):
        p = p.split()
    try:
        return [float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0]
    except (TypeError, ValueError, IndexError):
        return None


class MapInfo:
    """One map (or Forge / Anniversary layout) as its own files have it."""

    def __init__(self, key):
        self.key = key          # "<map>" or "<map>@<Forge layout id>": the model's and the heatmap's key
        self.weapons = []       # [(damage type, respawn s)]
        self.vehicles = []      # [(kind, team or None, respawn s)]
        self.points = []        # [[x, y, z]]: respawn points and weapon spots
        self.tokens = set()     # objective flags and labels
        self.real_pairs = []    # [(victim spot, killer spot)] of real kills
        self.loaded = False

    def supports(self, fam):
        if fam == "slayer" or not self.loaded or fam not in FAMILY_TOKENS:
            return True
        return any(t in self.tokens for t in FAMILY_TOKENS[fam])


def _games_ok(games, fam):
    if not games:
        return True
    g = [x.lower() for x in games]
    return "all games" in g or fam in g


def load_map(map_id, key=None, mvar_file=None, fam="slayer", root=ROOT, mvar_files=None):
    """MapInfo from maps/<map>/objects.json (the scenario: weapons, vehicles, respawn points, objective flags) and, for a
    layout, its .mvar (MCC's own file, read by brain/mvar.py), whose objects then stand for the map's."""
    info = MapInfo(key or map_id)
    try:
        with open(os.path.join(root, "maps", map_id, "objects.json"), encoding="utf-8") as f:
            o = json.load(f)
        info.loaded = True
    except (OSError, ValueError):
        o = {}
    for e in o.get("netgame_flags") or []:
        info.tokens.add(str(e.get("type", "")).lower())
    for e in o.get("placed") or []:
        info.tokens.add(str(e.get("name", "")).lower())
    objs = None
    if mvar_file:
        objs, labels = _mvar_objects(mvar_file, mvar_files)
    if objs is None:
        for e in o.get("equipment") or []:
            dt = ITEM_DT.get(e.get("item"))
            if dt and _games_ok(e.get("games"), fam):
                info.weapons.append((dt, float(e.get("spawn_time") or 0)))
                p = _floats(e.get("pos"))
                if p:
                    info.points.append(p)
        for e in o.get("vehicles") or []:
            item = e.get("item")
            if not _games_ok(e.get("games"), fam):
                continue
            if item in VEHICLES:
                team = e.get("team")
                info.vehicles.append((item, team if team in (0, 1) else None, float(e.get("spawn_time") or 0)))
            elif ITEM_DT.get(item) in POWER:
                info.weapons.append((ITEM_DT[item], float(e.get("spawn_time") or 0)))
        for e in o.get("spawns") or []:
            p = _floats(e.get("pos"))
            if p and _games_ok(e.get("games"), fam):
                info.points.append(p)
        return info
    info.loaded = True
    info.tokens |= {str(x).lower() for x in labels}
    for ob in objs:
        name, pos = str(ob.get("name") or ""), _floats(ob.get("pos"))
        info.tokens.add(name.lower())
        if ob.get("label"):
            info.tokens.add(str(ob["label"]).lower())
        team = ob.get("team")
        if name in ("respawn_point", "initial_spawn_point"):
            if pos:
                info.points.append(pos)
        elif name in VEHICLES:
            info.vehicles.append((name, team if team in (0, 1) else None, float(ob.get("respawn_time") or 0)))
        elif ITEM_DT.get(name):
            info.weapons.append((ITEM_DT[name], float(ob.get("respawn_time") or 0)))
            if pos:
                info.points.append(pos)
    return info


_MVAR = {}


def _mvar_objects(base, files=None):
    """(objects, labels) of MCC's map variant file named base (haloreach\\map_variants), or (None, [])."""
    if base in _MVAR:
        return _MVAR[base]
    out = (None, [])
    try:
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from brain import mvar
        files = files if files is not None else mvar.library(kind="map")
        hit = next((p for p in files if os.path.basename(str(p)).lower() == base.lower()), None)
        if hit:
            d = mvar.read(str(hit))
            out = (d.get("objects") or [], d.get("labels") or [])
    except Exception:                                    # (no MCC on this PC, or an unreadable file: the scenario's)
        out = (None, [])
    _MVAR[base] = out
    return out


# ---------------------------------------------------------------- the model, from real matches only
def shrink(own, count, typical, c):
    return (own + c * typical) / (count + c) if count + c > 0 else typical


class Model:
    """How each bot plays, from the real matches (never a simulated one)."""

    def __init__(self):
        self.skill = {}          # name -> logit skill
        self.agg = {}            # name -> fight rate, 1 the usual
        self.assist = {}         # name -> chance of an assist on a teammate's kill
        self.suicide = {}        # name -> per minute
        self.betray = {}         # name -> per minute
        self.headshot = {}       # name -> share of precision kills that are headshots
        self.weapons = {}        # name -> {damage type: real kills}
        self.tier_weapons = {}   # tier -> {damage type: kills}
        self.all_weapons = {}
        self.kpm = 0.9           # kills a player a minute
        self.kpm_by = {}         # family -> kills a player a minute
        self.kpm_size = {}       # (family, team size) -> kills a player a minute (4v4 and 8v8 differ)
        self.kpm_game = {}       # (gametype lowercased, team size) -> kills a player a minute (fit: KPM_RULES)
        self.obj_rules = {}      # gametype lowercased -> (even teams' rate a second, steepness) (fit: OBJ_RULES)
        self.score_rules = {}    # (family, team size) -> score limit (fit: SCORE_RULES)
        self.skill_scale = 1.0   # the tiers' strength gaps in fights (fit: SKILL_SCALE)
        self.hunt = 0.0          # mismatched fights' extra rate, exp(hunt * gap) (fit: HUNT)
        self.hunt_max = None     # and at most this many times (fit: HUNT_MAX; None: no cap)
        self.style_rate = {}     # medal -> per kill
        self.weapon_medal = {}   # medal -> per kill with its weapon
        self.mode_rate = {}      # (family, medal) -> per kill in that family
        self.hijack = 0.0        # hijacks per kill on maps with vehicles
        self.assist_medal = 1.0  # Assist medals per assist
        self.limits = {}         # gametype -> (score, seconds)
        self.maps = {}           # map key -> {"pairs": [...], "weapons": {dt: n}}
        self.real_minutes = {}   # name -> real minutes played
        self.tiers = {}          # name -> tier (bots)
        self.defaults = {"agg": {}, "assist": 0.15, "suicide": 0.02, "betray": 0.002, "headshot": 0.45}

    def inputs_of(self, name, tier):
        """What the match uses of one bot (stored with each simulated match, so it can be played again)."""
        d = self.defaults
        # (Nov 19, the owner: "Simulated strength should be based on their difficulty": a bot's tier alone, never
        # its fitted self.skill, which a few bad real games pulled a Demon below Heroic with)
        return {"s": round(skill_of(name, tier, self.skill_scale), 4),
                "a": round(self.agg.get(name, (d.get("agg") or {}).get(tier, 1.0)), 4),
                "q": round(self.assist.get(name, d.get("assist", 0.15)), 4),
                "su": round(self.suicide.get(name, d.get("suicide", 0.02)), 5),
                "bt": round(self.betray.get(name, d.get("betray", 0.002)), 5),
                "hs": round(self.headshot.get(name, d.get("headshot", 0.45)), 4)}


def fit(real, tiers):
    """Model from real matches: real = [(detail, kill rows or None, layout id or None)], detail as
    service_record.read_report keeps it; tiers {bot: tier key}. People in those matches are fitted too (as opponents)."""
    import service_record as sr
    import kill_record
    m = Model()
    m.tiers = dict(tiers)
    st = {}

    def rec(name):
        return st.setdefault(name, {"min": 0.0, "k": 0, "d": 0, "a": 0, "su": 0, "bt": 0, "tk": 0, "hs": 0, "prec": 0,
                                    "w": {}, "bot": True})
    pairs, field = [], []                                # real fights (winner, loser); K/D where no kill record
    fam_kills, fam_min = {}, {}
    medal_tot, kills_tot, vehicle_kills, hijacks = {}, 0, 0, 0
    weapon_kills_rec, weapon_medals_rec, assists_tot = {}, {}, 0
    gt_seen, mode_count, fs_kills, fs_min = {}, {}, {}, {}
    for detail, rows, layout in real:
        players = detail.get("players") or []
        if len(players) < 2:
            continue
        fam = sr.family(detail.get("type", ""))
        secs = max((p.get("seconds", 0) for p in players), default=0)
        teams = {}
        for p in players:
            teams.setdefault(p["team"], []).append(p)
        size = max(len(tp) for tp in teams.values())
        if len(teams) == 2:                              # (limits from two-team matches, by team size: 4v4, 8v8)
            gt_seen.setdefault((detail.get("type", ""), size), []).append(
                (secs, {t: sum(x.get("score", 0) for x in tp) for t, tp in teams.items()}))
            fs_kills[(fam, size)] = fs_kills.get((fam, size), 0) + sum(p["kills"] for p in players)
            fs_min[(fam, size)] = fs_min.get((fam, size), 0.0) + sum(p.get("seconds", 0) for p in players) / 60.0
        has_veh = False
        tally = sr.kill_tally(detail, rows) if rows else {}
        if rows:
            names = sr.kill_names(detail, rows)
            mk = (detail.get("map") or "") + (f"@{layout}" if layout else "")
            mp = m.maps.setdefault(mk, {"pairs": [], "weapons": {}})
            for k in rows:
                f = kill_record.read(k, detail.get("teams", True))
                if not f or f[0] != "kill":
                    continue
                _, killer, weapon = f
                if isinstance(weapon, int) and 24 <= weapon <= 40:
                    has_veh = True
                if weapon is not None:
                    mp["weapons"][weapon] = mp["weapons"].get(weapon, 0) + 1
                if k.get("vp") and len(mp["pairs"]) < 4000:
                    mp["pairs"].append((list(k["vp"][:3]), list((k.get("kp") or k["vp"])[:3])))
                a, b = names.get(killer), names.get(k["v"])
                if a and b:
                    pairs.append((a, b))
        for p in players:
            r = rec(p["name"])
            r["bot"] = r["bot"] and bool(p.get("bot"))
            mins = p.get("seconds", 0) / 60.0
            medals = p.get("medals") or {}
            r["min"] += mins
            r["k"] += p["kills"]
            r["d"] += p["deaths"]
            r["a"] += p["assists"]
            assists_tot += p["assists"]
            r["su"] += p.get("suicides", 0)
            r["bt"] += p.get("betrayals", 0)
            r["tk"] += max(0, sum(x["kills"] for x in teams.get(p["team"], [])) - p["kills"])
            fam_kills[fam] = fam_kills.get(fam, 0) + p["kills"]
            fam_min[fam] = fam_min.get(fam, 0.0) + mins
            kills_tot += p["kills"]
            for i, n in medals.items():
                i = int(i)
                medal_tot[i] = medal_tot.get(i, 0) + n
                if i in (M_HIJACK, M_SKYJACK):
                    hijacks += n
                if i in MODE_MEDALS.get(fam, ()):
                    mode_count[(fam, i)] = mode_count.get((fam, i), 0) + n
            mine = tally.get(p["name"]) if tally else None
            if mine:
                for key, (kn, _) in mine["weapons"].items():
                    try:
                        dt = int(key)
                    except ValueError:
                        continue
                    r["w"][dt] = r["w"].get(dt, 0) + kn
                    weapon_kills_rec[dt] = weapon_kills_rec.get(dt, 0) + kn
                    if dt in PRECISION:
                        r["prec"] += kn
                r["hs"] += int(medals.get(str(M_HEADSHOT), 0))
                for med, _ in WEAPON_MEDALS:
                    weapon_medals_rec[med] = weapon_medals_rec.get(med, 0) + int(medals.get(str(med), 0))
            elif not rows:
                opp = [x["name"] for t, tp in teams.items() if t != p["team"] for x in tp]
                if opp:
                    field.append((p["name"], p["kills"], p["deaths"], opp))
        if has_veh:
            vehicle_kills += sum(p["kills"] for p in players)
    # skill: Bradley-Terry around each one's start (maximum a posteriori, Newton sweeps)
    mu0 = {n: (TIER_SKILL.get(tiers.get(n, "strong"), 0.0) if r["bot"] else 0.6) for n, r in st.items()}
    tau = {n: (0.5 if r["bot"] else 1.0) for n, r in st.items()}
    s = dict(mu0)
    wins, losses, field_by = {}, {}, {}
    for a, b in pairs:
        wins.setdefault(a, []).append(b)
        losses.setdefault(b, []).append(a)
    for name, k, d, opp in field:
        field_by.setdefault(name, []).append((k, d, opp))
    for _ in range(25):
        for n in st:
            g = -(s[n] - mu0[n]) / tau[n] ** 2
            h = -1.0 / tau[n] ** 2
            for o in wins.get(n, ()):
                q = sigmoid(s[n] - s[o])
                g += 1 - q
                h -= q * (1 - q)
            for o in losses.get(n, ()):
                q = sigmoid(s[n] - s[o])
                g -= q
                h -= q * (1 - q)
            for k, d, opp in field_by.get(n, ()):
                q = sigmoid(s[n] - sum(s.get(o, 0.0) for o in opp) / len(opp))
                g += k * (1 - q) - d * q
                h -= (k + d) * q * (1 - q)
            s[n] -= g / h
    m.skill = {n: round(v, 4) for n, v in s.items()}
    # the usual rates, and each bot's shrunk toward its tier's
    tot_min = sum(r["min"] for r in st.values())
    if tot_min > 1:
        m.kpm = sum(r["k"] for r in st.values()) / tot_min
    m.kpm_by = {f: fam_kills[f] / fam_min[f] for f in fam_kills if fam_min.get(f, 0) >= 60}
    m.kpm_size = {k: fs_kills[k] / fs_min[k] for k in fs_kills if fs_min.get(k, 0) >= 120}
    e_all = sum(r["k"] + r["d"] for r in st.values()) / tot_min if tot_min > 1 else 2 * m.kpm
    q_all = sum(r["a"] for r in st.values()) / max(1, sum(r["tk"] for r in st.values())) if st else 0.15
    su_all = sum(r["su"] for r in st.values()) / tot_min if tot_min > 1 else 0.02
    bt_all = sum(r["bt"] for r in st.values()) / tot_min if tot_min > 1 else 0.002
    prec_all = sum(r["prec"] for r in st.values())
    hs_all = sum(r["hs"] for r in st.values()) / prec_all if prec_all else 0.45
    tier_agg = {}
    for n, r in st.items():
        if r["bot"] and r["min"] > 0:
            t = tiers.get(n, "strong")
            tier_agg.setdefault(t, [0.0, 0.0])
            tier_agg[t][0] += r["k"] + r["d"]
            tier_agg[t][1] += r["min"]
            tw = m.tier_weapons.setdefault(t, {})
            for dt, kn in r["w"].items():
                tw[dt] = tw.get(dt, 0) + kn
        for dt, kn in r["w"].items():
            m.all_weapons[dt] = m.all_weapons.get(dt, 0) + kn
    tier_a = {t: (v[0] / v[1]) / e_all for t, v in tier_agg.items() if v[1] > 0 and e_all > 0}
    for n, r in st.items():
        ta = tier_a.get(tiers.get(n, "strong"), 1.0)
        # fights a minute against the usual, with 20 minutes of its tier's: (K + D + 20 e ta) / ((min + 20) e)
        m.agg[n] = round(shrink(r["k"] + r["d"], r["min"] * e_all, ta, 20 * e_all), 4) if e_all > 0 else 1.0
        m.assist[n] = round(shrink(r["a"], r["tk"], q_all, 30), 4)
        m.suicide[n] = round(shrink(r["su"], r["min"], su_all, 30), 5)
        m.betray[n] = round(shrink(r["bt"], r["min"], bt_all, 60), 5)
        m.headshot[n] = round(shrink(r["hs"], r["prec"], hs_all, 20), 4)
        if r["w"]:
            m.weapons[n] = dict(r["w"])
        m.real_minutes[n] = round(r["min"], 2)
    m.defaults = {"agg": tier_a, "assist": q_all, "suicide": su_all, "betray": bt_all, "headshot": hs_all}
    m.style_rate = {i: medal_tot.get(i, 0) / kills_tot for i in STYLE_MEDALS} if kills_tot else {}
    for med, dt in WEAPON_MEDALS:
        wk = weapon_kills_rec.get(dt, 0)
        m.weapon_medal[med] = min(1.0, weapon_medals_rec.get(med, 0) / wk) if wk else \
            (1.0 if med in (M_MELEE, M_SNIPER, M_LASER) else 0.0)
    m.mode_rate = {key: n / max(1, fam_kills.get(key[0], 0)) for key, n in mode_count.items()}
    m.hijack = hijacks / vehicle_kills if vehicle_kills else 0.0
    m.assist_medal = min(1.0, medal_tot.get(M_ASSIST, 0) / assists_tot) if assists_tot else 1.0
    m.limits = {key: limits_from(key[0], seen) for key, seen in gt_seen.items()}
    m.kpm_game, m.obj_rules, m.score_rules = dict(KPM_RULES), dict(OBJ_RULES), dict(SCORE_RULES)
    m.skill_scale, m.hunt, m.hunt_max = SKILL_SCALE, HUNT, HUNT_MAX
    return m


def kpm_of(model, fam, size, gametype=None):
    """Kills a player a minute: the gametype's own at that team size (KPM_RULES), else real matches of that family at
    that team size, else of the family, else all."""
    return (getattr(model, "kpm_game", {}).get(((gametype or "").lower(), size))
            or getattr(model, "kpm_size", {}).get((fam, size)) or model.kpm_by.get(fam) or model.kpm)


def obj_rule_of(model, gametype, fam):
    """(a team's scoring rate a second between even teams, steepness k: the stronger team's rate grows exp(k * gap)):
    the gametype's own (OBJ_RULES), else its family's OBJ_RATE and 1; None when the family scores no objective."""
    rule = getattr(model, "obj_rules", {}).get((gametype or "").lower())
    if rule:
        return tuple(rule)
    return (OBJ_RATE[fam], 1.0) if fam in OBJ_RATE else None


def limits_of(model, gametype, size):
    """(score limit, seconds) of a gametype at a team size: its real matches at that size, else at any size, else
    Reach's usual ones for its family; the score SCORE_RULES' when it has one. Names match without case (the real
    matches say "TU BTB Team Slayer", the playlist "TU BTB TEAM SLAYER")."""
    low = (gametype or "").lower()
    hit = model.limits.get((gametype, size)) or next(
        (v for (g, s), v in model.limits.items() if g.lower() == low and s == size), None)
    if hit is None:
        any_size = [v for (g, _), v in model.limits.items() if g.lower() == low]
        hit = any_size[0] if len(any_size) == 1 else None
    score, secs = tuple(hit) if hit else FAMILY_RULES.get(family(gametype), FAMILY_RULES["slayer"])
    # (the fitted model's SCORE_RULES; a stored match's slice keeps the limits it was played to)
    return getattr(model, "score_rules", {}).get((family(gametype), size), score), secs


def limits_from(gametype, seen):
    """(score limit, seconds) a gametype is played to, from its real matches [(seconds, {team: score})]: the score
    most of the matches that ended early stopped at, and the time the others ran to."""
    fam = family(gametype) if gametype else "slayer"
    d_score, d_secs = FAMILY_RULES.get(fam, FAMILY_RULES["slayer"])
    seen = [x for x in seen if x[0] >= 120 and x[1] and max(x[1].values()) > 0]   # (quit early, or no score: nothing)
    if not seen:
        return d_score, d_secs
    t_obs = int(round(max(s for s, _ in seen) / 60.0)) * 60
    early = [max(sc.values()) for s, sc in seen if s < t_obs - 15]
    if early:
        counts = {}
        for x in early:
            counts[x] = counts.get(x, 0) + 1
        score = max(counts, key=lambda x: (counts[x], -x))
    else:
        score = d_score
    timed = any(s >= t_obs - 15 and max(sc.values()) < score for s, sc in seen)
    secs = t_obs if timed and t_obs >= 300 else max(t_obs, d_secs)
    return score, secs


# ---------------------------------------------------------------- one match, fight by fight
class P:
    __slots__ = ("i", "name", "team", "clan", "s", "a", "q", "su", "bt", "hs", "style", "back", "run", "multi", "last",
                 "last_killer", "k", "d", "as_", "sui", "btr", "score", "alive_s", "alive_since", "best_run", "medals",
                 "kw", "kg", "km", "ko", "vs", "power", "ammo", "veh", "seat", "wrun", "wdt", "arun", "wheel", "splat",
                 "mix", "mix_keys", "mix_w", "objw")


def weapon_mix(model, name, tier, allowed, map_ref):
    """{damage type: weight} of a bot's ordinary kills: its own real weapon kills, plus 40 kills' worth of the map's mix
    (or its tier's, or everyone's), only weapons this map and gametype have (1% each at least: a weapon the map has)."""
    own = model.weapons.get(name, {})
    ref = map_ref if map_ref and sum(map_ref.get(w, 0) for w in allowed) >= 150 else \
        (model.tier_weapons.get(tier) or model.all_weapons)
    ref_tot = sum(ref.get(w, 0) for w in allowed) or 1
    return {w: own.get(w, 0) + 40 * max(ref.get(w, 0) / ref_tot, 0.01) for w in sorted(allowed)}


def match_inputs(spec, model, info):
    """{name: what the match uses of each player}, rounded as stored: a stored match plays again from these."""
    gametype = spec["gametype"]
    allowed = starting_weapons(gametype) | {dt for dt, _ in info.weapons if dt not in POWER}
    map_ref = (model.maps.get(info.key) or {}).get("weapons") or (model.maps.get(info.key.split("@")[0]) or {}).get("weapons")
    out = {}
    for x in spec["players"]:
        tier = x.get("tier", "strong")
        inp = model.inputs_of(x["name"], tier)
        inp["mix"] = [[w, round(n, 3)] for w, n in weapon_mix(model, x["name"], tier, allowed, map_ref).items()]
        out[x["name"]] = inp
    return out


def model_slice(model, gametype, size):
    """The model's numbers a match of this gametype uses besides its players' (stored with it)."""
    fam = family(gametype)
    rule = getattr(model, "obj_rules", {}).get(gametype.lower())
    return {"kpm": round(kpm_of(model, fam, size, gametype), 5), "size": size,
            "limits": list(limits_of(model, gametype, size)),
            **({"obj": list(rule)} if rule else {}),           # (Nov 23: a gametype's own capture rule)
            **({"scale": model.skill_scale, "hunt": model.hunt}   # (Nov 23: steeper gaps, hunting)
               if getattr(model, "skill_scale", 1.0) != 1.0 or getattr(model, "hunt", 0.0) else {}),
            **({"hunt_max": model.hunt_max} if getattr(model, "hunt_max", None) else {}),
            "style_rate": {str(k): round(v, 6) for k, v in model.style_rate.items()},
            "weapon_medal": {str(k): round(v, 6) for k, v in model.weapon_medal.items()},
            "mode_rate": [[f, mid, round(v, 6)] for (f, mid), v in model.mode_rate.items() if f == fam],
            "hijack": round(model.hijack, 6), "assist_medal": round(model.assist_medal, 6)}


def model_from_slice(sl, gametype):
    m = Model()
    fam = family(gametype)
    m.kpm, m.kpm_by = sl["kpm"], {fam: sl["kpm"]}
    m.limits = {(gametype, sl.get("size", 0)): tuple(sl["limits"])}
    m.obj_rules = {gametype.lower(): tuple(sl["obj"])} if sl.get("obj") else {}
    m.skill_scale, m.hunt = float(sl.get("scale", 1.0)), float(sl.get("hunt", 0.0))   # (older matches: 1 and 0)
    m.hunt_max = float(sl["hunt_max"]) if sl.get("hunt_max") else None              # (older: no cap)
    m.style_rate = {int(k): v for k, v in sl["style_rate"].items()}
    m.weapon_medal = {int(k): v for k, v in sl["weapon_medal"].items()}
    m.mode_rate = {(f, int(mid)): v for f, mid, v in sl["mode_rate"]}
    m.hijack, m.assist_medal = sl["hijack"], sl["assist_medal"]
    return m


def play(spec, model, info, seed, inputs=None):
    """One match. spec: {"players": [{"name", "team", "clan", "style", "tier"}], "gametype", "size"}; info: MapInfo;
    inputs {name: Model.inputs_of} (a stored match played again uses its own). Returns (report rows, kill rows,
    {"seconds", "scores", "winner"})."""
    rng = Rng(seed)
    gametype = spec["gametype"]
    fam = family(gametype)
    size = max(1, int(spec["size"]))
    score_limit, secs = limits_of(model, gametype, size)
    scale = getattr(model, "skill_scale", 1.0) or 1.0              # (Nov 23: the fights' steeper gaps, hunting)
    hunt = getattr(model, "hunt", 0.0)
    n_rounds = rounds_of(gametype)
    if n_rounds > 1:
        score_limit, secs = None, ROUND_SECS * n_rounds
    allowed = starting_weapons(gametype) | {dt for dt, _ in info.weapons if dt not in POWER}
    map_ref = (model.maps.get(info.key) or {}).get("weapons") or (model.maps.get(info.key.split("@")[0]) or {}).get("weapons")
    inputs = inputs or {}
    ps = []
    for i, x in enumerate(spec["players"]):
        tier = x.get("tier", "strong")
        inp = inputs.get(x["name"]) or model.inputs_of(x["name"], tier)
        p = P()
        p.i, p.name, p.team, p.clan, p.style = i, x["name"], x["team"], x.get("clan", ""), x.get("style", "any")
        p.s, p.a, p.q, p.hs = inp["s"], inp["a"], inp["q"], inp["hs"]
        p.s += rng.gauss(0.0, MATCH_SD)                  # (a match's own good or bad game: K/D spreads as real ones do)
        p.su, p.bt = inp["su"] / 60.0, inp["bt"] / 60.0
        p.back, p.run, p.multi, p.last, p.last_killer = 0.0, 0, 0, -99.0, None
        p.k = p.d = p.as_ = p.sui = p.btr = p.score = 0
        p.alive_s, p.alive_since, p.best_run = 0.0, 0.0, 0
        p.medals, p.vs = {}, {}
        p.kw = p.kg = p.km = p.ko = 0
        p.power, p.ammo, p.veh, p.seat = None, 0, None, None
        p.wrun, p.wdt, p.arun, p.wheel, p.splat = 0, None, 0, 0, 0
        p.mix = {int(w): float(n) for w, n in inp["mix"]} if inp.get("mix") else \
            weapon_mix(model, p.name, tier, allowed, map_ref)
        p.mix_keys = list(p.mix)
        p.mix_w = [p.mix[w] for w in p.mix_keys]
        p.objw = p.a * (2.0 if p.style == "objector" else 1.0)
        ps.append(p)
    teams = sorted({p.team for p in ps})
    by_team = {tm: [p for p in ps if p.team == tm] for tm in teams}
    team_score = {tm: 0 for tm in teams}
    rows = []
    state = {"t": 0.0, "first": False, "round": 1, "round_end": ROUND_SECS if n_rounds > 1 else secs,
             "attack": teams[0] if teams else 0, "next_tick": 1.0, "done": False}
    recent = []                                          # (time, killer, victim's team): Avenger
    # the fight rate a pair: the lobby's kills a minute come out as real matches have them. Each player is alive
    # 1 / (1 + kpm * respawn / 60) of the time (a death every 60 / kpm s, then the respawn), so with both teams' fight
    # rates a: kills a second = lam0 * (size * mean a * alive)^2 = 2 * size * kpm / 60
    kpm = kpm_of(model, fam, size, gametype)
    a_mean = sum(p.a for p in ps) / len(ps) if ps else 1.0
    alive_share = 1.0 / (1.0 + kpm * RESPAWN / 60.0)
    lam0 = 2.0 * (kpm / 60.0) / (size * max(0.2, a_mean) ** 2 * alive_share ** 2)
    power = [{"dt": dt, "respawn": rs if rs > 0 else 120.0, "at": 0.0 if rs <= 60 else 20.0, "held": None}
             for dt, rs in info.weapons if dt in POWER]
    vehicles = [{"kind": kind, "team": team, "respawn": rs if rs > 0 else 60.0, "at": 0.0, "driver": None,
                 "gunner": None, "up": True} for kind, team, rs in info.vehicles]
    ball = {"holder": None, "free_at": 15.0}
    terr = [None] * 5

    def now():
        return state["t"]

    def medal(p, mid, n=1):
        p.medals[mid] = p.medals.get(mid, 0) + n

    def jit(c, sd):
        return round(c + rng.gauss(0, sd), 2)

    def spot(dt):
        if len(info.real_pairs) >= 120:
            v, k = rng.pick(info.real_pairs)
            return [jit(v[0], 0.4), jit(v[1], 0.4), round(v[2], 2)], [jit(k[0], 0.4), jit(k[1], 0.4), round(k[2], 2)]
        pts = info.points
        if not pts:
            return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
        v0 = rng.pick(pts)
        v = [jit(v0[0], 1.5), jit(v0[1], 1.5), round(v0[2], 2)]
        want = {SNIPER: 40, DMR: 25, NEEDLE_RIFLE: 25, MAGNUM: 18, FOCUS: 30, MELEE: 1.5, SWORD: 2.5, HAMMER: 2.5,
                SHOTGUN: 4, ROCKETS: 15, LASER: 35}.get(dt, 12)
        best, bd = v0, 1e9
        for _ in range(6):
            c = rng.pick(pts)
            gap = abs(math.hypot(c[0] - v[0], c[1] - v[1]) - want)
            if gap < bd:
                best, bd = c, gap
        return v, [round(best[0], 2), round(best[1], 2), round(best[2], 2)]

    def alive(p):
        return p.back <= now()

    def bonus(p):
        b = 0.0
        if p.veh is not None:
            vs = VEHICLES[p.veh["kind"]]
            b += vs[3] * (0.6 if p.seat == "driver" and vs[1] else 1.0)
        elif p.power is not None:
            b += POWER[p.power["dt"]][2]
        if fam == "oddball" and ball["holder"] is p:
            b -= 0.8
        return b

    def rate_mult(p):
        if p.veh is not None:
            vs = VEHICLES[p.veh["kind"]]
            if p.seat == "driver" and (vs[1] or p.veh["kind"] == "mongoose"):
                return vs[4] * DRIVER_SHARE                  # (the gunner does the shooting; the driver splatters)
            return vs[4]
        return 1.15 if p.power is not None else 1.0

    def vehicle_gone(v):
        for seat in ("driver", "gunner"):
            if v[seat] is not None:
                v[seat].veh, v[seat].seat = None, None
            v[seat] = None
        v["up"] = False
        v["at"] = now() + v["respawn"]

    def free_power(w):
        w["held"] = None
        w["at"] = now() + w["respawn"]

    def weapon_of(p):
        """(damage type, from a vehicle seat?) of p's kill now."""
        if p.veh is not None:
            vs = VEHICLES[p.veh["kind"]]
            if p.seat == "gunner" and vs[1]:
                return vs[1], True
            if vs[6] and rng.chance(vs[7]):
                return vs[6], True
            return vs[0], True
        if fam == "oddball" and ball["holder"] is p:
            return BALL_DT, False
        if p.power is not None and rng.chance(POWER[p.power["dt"]][1]):
            dt = p.power["dt"]
            p.ammo -= 1
            if p.ammo <= 0:
                free_power(p.power)
                p.power = None
            return dt, False
        return p.mix_keys[rng.weighted(p.mix_w)], False

    def kill_medals(k, v, dt, from_vehicle, assists):
        t = now()
        if not state["first"]:
            state["first"] = True
            medal(k, M_FIRST)
        k.multi = k.multi + 1 if t - k.last <= 4.0 else 1
        k.last = t
        if k.multi >= 2:
            medal(k, MULTI[min(k.multi, 10)])
        k.run += 1
        k.best_run = max(k.best_run, k.run)
        for need, mid in SPREES:
            if k.run == need:
                medal(k, mid)
        if dt in WEAPON_SPREE:
            k.wrun = k.wrun + 1 if k.wdt == dt else 1
            k.wdt = dt
            if k.wrun == 5:
                medal(k, WEAPON_SPREE[dt])
        if v.run >= 5:
            medal(k, M_KILLJOY)
        if k.last_killer is not None:                    # (its first kill since it died: its killer, Revenge)
            if v is k.last_killer:
                medal(k, M_REVENGE)
            k.last_killer = None
        if any(tt >= t - AVENGER_S and kk is v and team == k.team for tt, kk, team in recent):
            medal(k, M_AVENGER)
        if dt in PRECISION and rng.chance(k.hs):
            medal(k, M_HEADSHOT)
        for med, wdt in WEAPON_MEDALS:
            if wdt == dt and rng.chance(model.weapon_medal.get(med, 0.0)):
                medal(k, med)
        if from_vehicle and dt in SPLATTER_DT and k.seat == "driver" and rng.chance(VEHICLES[k.veh["kind"]][2]):
            medal(k, M_SPLATTER)
            k.splat += 1
            if k.splat == 5:
                medal(k, M_SPLATTER_SPREE)
        for mid, r in model.style_rate.items():
            if r and rng.chance(r):
                medal(k, mid)
        for mid in MODE_MEDALS.get(fam, ()):
            r = model.mode_rate.get((fam, mid), 0.0)
            if r and rng.chance(r):
                medal(k, mid)
        if fam == "oddball" and ball["holder"] is v:
            medal(k, M_BALL_CARRIER_KILL)
        if dt == BALL_DT:
            medal(k, M_BALL_KILL)
        foes = by_team[v.team]
        if len(foes) >= 4 and all(not alive(p) or p is v for p in foes):
            medal(k, M_EXTERMINATION)
        for a in assists:
            if rng.chance(model.assist_medal):
                medal(a, M_ASSIST)
            a.arun += 1
            if a.arun == 5:
                medal(a, M_ASSIST_SPREE)
            if from_vehicle and a.veh is not None and a.veh is k.veh and a.seat == "driver" and k.seat == "gunner":
                medal(a, M_WHEELMAN)
                a.wheel += 1
                if a.wheel == 5:
                    medal(a, M_WHEELMAN_SPREE)

    def die(v, killer, dt):
        t = now()
        v.d += 1
        v.alive_s += max(0.0, t - v.alive_since)
        v.run = v.wrun = v.arun = v.splat = v.wheel = v.multi = 0
        v.wdt = None
        v.back = t + RESPAWN
        v.alive_since = v.back
        if fam == "oddball" and ball["holder"] is v:
            ball["holder"], ball["free_at"] = None, t + 3.0
        if v.veh is not None:
            veh, seat = v.veh, v.seat
            destroyed = killer is None or killer.veh is not None or dt in ANTI_VEHICLE or rng.chance(0.4)
            if destroyed:
                vehicle_gone(veh)
            else:
                veh[seat] = None
                v.veh, v.seat = None, None
                if seat == "driver" and killer.veh is None and killer.power is None and \
                        rng.chance(min(0.9, model.hijack / 0.25)):
                    veh["driver"], killer.veh, killer.seat = killer, veh, "driver"
                    medal(killer, M_SKYJACK if VEHICLES[veh["kind"]][5] else M_HIJACK)
        if v.power is not None:
            w, ammo = v.power, v.ammo
            v.power, v.ammo = None, 0
            if killer is not None and killer.veh is None and killer.power is None and ammo > 0 and \
                    w["dt"] not in (MG_TURRET, PLASMA_TURRET) and rng.chance(0.35):
                killer.power, killer.ammo, w["held"] = w, ammo, killer
            else:
                free_power(w)

    def row(v, k, dt, assists):
        vp, kp = spot(dt)
        t = now()
        hits = [[k.i, dt, 0, 0.0, 0.0, 2]] + [[a.i, a.mix_keys[rng.weighted(a.mix_w)], 0, 0.0, 0.0, 30]
                                              for a in assists[:3]]
        rows.append({"v": v.i, "k": k.i, "new": True, "o": k.i, "c": dt, "m": 0, "hits": hits, "vt": v.team,
                     "kt": k.team, "vb": 1, "kb": 1, "vp": vp, "kp": kp if k is not v else vp, "gt": int(t * 30),
                     "st": 1, "t": round(t, 2), "sim": 1})

    def credit(k, dt):
        if dt in GRENADES:
            k.kg += 1
        elif dt == MELEE:
            k.km += 1
        elif 24 <= dt <= 40 or dt in (FLAG_DT, BOMB_DT, BALL_DT):
            k.ko += 1
        else:
            k.kw += 1

    def add_score(tm, by, n=1):
        team_score[tm] += n
        if by is not None:
            by.score += n

    def strength(tm, at=None):
        at = now() if at is None else at
        al = [p for p in by_team[tm] if p.back <= at]
        # (objectives on TIER_SKILL's own scale, as they were tuned: the steeper gaps are the fights')
        return ((sum(p.s + bonus(p) for p in al) / size / scale) if al else -3.0), len(al)

    def obj_pick(tm, at=None):
        at = now() if at is None else at
        al = [p for p in by_team[tm] if p.back <= at]
        return al[rng.weighted([p.objw for p in al])] if al else None

    def next_round():
        """A round of One Flag / One Bomb over (a capture, or its time out): the sides swap, everyone respawns."""
        if state["round"] >= n_rounds:
            state["done"] = True
            return
        state["round"] += 1
        state["round_end"] = now() + ROUND_SECS
        state["attack"] = teams[(teams.index(state["attack"]) + 1) % len(teams)]
        for p in ps:
            if p.back > now():
                p.back = p.alive_since = now()

    def over():
        if state["done"] or now() >= secs:
            return True
        return bool(score_limit) and max(team_score.values()) >= score_limit

    def tick(upto):
        """Each whole second up to `upto`: the hill, the ball, territories, power weapon pickups, boarding."""
        while state["next_tick"] <= upto:
            if score_limit and max(team_score.values()) >= score_limit:
                state["t"] = min(state["t"], state["next_tick"] - 1.0)    # (the limit reached: the match ends there)
                return
            tt = state["next_tick"]
            state["next_tick"] += 1.0
            if fam == "koth" and rng.chance(KOTH_HELD):
                sa = {tm: strength(tm, tt) for tm in teams}
                live = [tm for tm in teams if sa[tm][1] > 0]
                if live:
                    owner = live[rng.weighted([math.exp(1.2 * sa[tm][0]) * sa[tm][1] for tm in live])]
                    by = obj_pick(owner, tt)
                    if by is not None:                       # (the second goes to the one standing in the hill)
                        add_score(owner, by)
            elif fam == "oddball":
                h = ball["holder"]
                if h is not None:
                    add_score(h.team, h)
                elif tt >= ball["free_at"]:
                    al = [p for p in ps if p.back <= tt and p.veh is None]
                    if al:
                        ball["holder"] = al[rng.weighted([p.objw for p in al])]
            elif fam == "territories":
                for j in range(5):
                    o = terr[j]
                    for tm in teams:
                        if tm == o:
                            continue
                        sa = strength(tm, tt)[0]
                        sb = strength(o, tt)[0] if o is not None else -1.0
                        rate = (1 / 15.0 if o is None else 1 / 45.0) * math.exp(sa - sb)
                        if rng.chance(min(0.5, rate)):
                            terr[j] = tm
                            by = obj_pick(tm, tt)
                            if by is not None:
                                medal(by, M_TERRITORY)
                            break
                if int(tt) % 10 == 0:                        # (a point a held territory every 10 s, to a holder)
                    for o in terr:
                        if o is not None:
                            by = obj_pick(o, tt)
                            if by is not None:
                                add_score(o, by)
            for w in power:
                if w["held"] is None and tt >= w["at"] and rng.chance(0.1):
                    al = [p for p in ps if p.back <= tt and p.veh is None and p.power is None]
                    if al:
                        want = POWER[w["dt"]][3]
                        g = al[rng.weighted([p.a * (3.0 if p.style == want else 1.0) for p in al])]
                        g.power, g.ammo, w["held"] = w, POWER[w["dt"]][0], g
            for v in vehicles:
                if not v["up"]:
                    if tt < v["at"]:
                        continue
                    v["up"] = True
                vs = VEHICLES[v["kind"]]
                for seat, rate in (("driver", 1 / 12.0), ("gunner", 1 / 15.0)):
                    if seat == "gunner" and (not vs[1] or v["driver"] is None):
                        continue
                    if v[seat] is not None or not rng.chance(rate):
                        continue
                    side = v["driver"].team if seat == "gunner" else v["team"]
                    cands = [p for p in ps if p.back <= tt and p.veh is None and p.power is None
                             and (side is None or side not in teams or p.team == side)
                             and not (fam == "oddball" and ball["holder"] is p)]
                    if cands:
                        g = cands[rng.weighted([p.a * (4.0 if p.style == "wheelman" else 1.0) for p in cands])]
                        v[seat], g.veh, g.seat = g, v, seat

    obj_rule = obj_rule_of(model, gametype, fam)
    # (the steep part on the whole teams' strength this match, all players, dead or not: on the moment's, a team with
    # men down swung it so hard that even teams swept 3-0)
    roster = {tm: sum(p.s for p in by_team[tm]) / max(1, len(by_team[tm])) / scale for tm in teams}

    # (hunting moves fights toward mismatched pairs without adding any: the lobby's kills a minute stay kpm's)
    hunt_max = getattr(model, "hunt_max", None)

    def hunt_of(x, y):                                   # (a pair's hunting factor, at most hunt_max)
        f = math.exp(hunt * abs(x.s - y.s))
        return min(f, hunt_max) if hunt_max else f
    hunt_norm = 1.0
    if hunt:
        cross = [hunt_of(x, y) for x in ps for y in ps if x.team != y.team]
        hunt_norm = sum(cross) / len(cross) if cross else 1.0

    def objective_rates():
        out = {}
        if obj_rule is None:
            return out
        base, steep = obj_rule[0], obj_rule[1]
        cap = math.log(obj_rule[2]) if len(obj_rule) > 2 else None    # (most times the even rate a team scores)
        for tm in teams:
            if n_rounds > 1 and tm != state["attack"]:
                continue
            sa, na = strength(tm)
            sb = max((strength(o)[0] for o in teams if o != tm), default=0.0)
            gap = roster[tm] - max((roster[o] for o in teams if o != tm), default=roster[tm])
            x = sa - sb + (steep - 1.0) * gap
            if cap is not None:
                x = min(x, cap)
            if na:
                out[tm] = base * (2.0 if n_rounds > 1 else 1.0) * math.exp(x) * na / size
        return out

    while not over():
        t = now()
        alive_by = {tm: [p for p in by_team[tm] if p.back <= t] for tm in teams}
        pairs, weights = [], []
        for ai, ta in enumerate(teams):
            for tb in teams[ai + 1:]:
                for x in alive_by[ta]:
                    mx = x.a * rate_mult(x)
                    for y in alive_by[tb]:
                        pairs.append((x, y))
                        w = mx * y.a * rate_mult(y)
                        weights.append(w * hunt_of(x, y) if hunt else w)   # (the strong hunt)
        fight_rate = lam0 * sum(weights) / hunt_norm
        su_rate = sum(p.su + p.bt for p in ps if p.back <= t)
        obj = objective_rates()
        total = fight_rate + su_rate + sum(obj.values())
        wait = rng.expo(total) if total > 0 else float("inf")
        stop = secs
        if n_rounds > 1:
            stop = min(stop, state["round_end"])
        # (a respawn changes the rates: the wait drawn now holds only until then)
        stop = min(stop, min((p.back for p in ps if p.back > t), default=secs))
        if total <= 0:
            stop = min(stop, t + 1.0)
        if t + wait >= stop:
            state["t"] = stop
            tick(stop)
            if n_rounds > 1 and stop >= state["round_end"] - 1e-9 and stop < secs:
                next_round()
            continue
        state["t"] = t = t + wait
        tick(t)
        if over():
            break
        r = rng.random() * total
        if r < fight_rate:
            x, y = pairs[rng.weighted(weights)]
            if not rng.chance(sigmoid(x.s + bonus(x) - y.s - bonus(y))):
                x, y = y, x
            k, v = x, y
            dt, from_vehicle = weapon_of(k)
            assists = [m_ for m_ in by_team[k.team] if m_ is not k and m_.back <= t and rng.chance(m_.q)]
            if from_vehicle and k.seat == "gunner" and k.veh["driver"] is not None and k.veh["driver"] not in assists:
                assists.append(k.veh["driver"])              # (the driver of a gunner's kill: Wheelman, an assist)
            k.k += 1
            k.vs[v.name] = k.vs.get(v.name, 0) + 1
            credit(k, dt)
            if fam in ("slayer", "headhunter"):
                add_score(k.team, k)
            kill_medals(k, v, dt, from_vehicle, assists)
            for a in assists:
                a.as_ += 1
            row(v, k, dt, assists)
            v.last_killer = k
            recent.append((t, k, v.team))
            if len(recent) > 40:
                del recent[:20]
            die(v, k, dt)
        elif r < fight_rate + su_rate:
            cands = [p for p in ps if p.back <= t]
            p = cands[rng.weighted([c.su + c.bt for c in cands])]
            mates = [m_ for m_ in by_team[p.team] if m_ is not p and m_.back <= t]
            if mates and rng.chance(p.bt / max(1e-12, p.su + p.bt)):
                v = rng.pick(mates)
                p.btr += 1
                dt = p.mix_keys[rng.weighted(p.mix_w)]
                row(v, p, dt, [])
                if fam in ("slayer", "headhunter"):
                    add_score(p.team, p, -1)
                die(v, None, dt)
            else:
                p.sui += 1
                dt = rng.pick([FRAG, FALL_DT, SUICIDE_DT])
                row(p, p, dt, [])
                if fam in ("slayer", "headhunter"):
                    add_score(p.team, p, -1)
                die(p, None, dt)
        else:
            rr, acc = r - fight_rate - su_rate, 0.0
            for tm, rate in obj.items():
                acc += rate
                if rr < acc:
                    by = obj_pick(tm)
                    add_score(tm, by)
                    if by is not None and fam in ("ctf", "assault"):
                        medal(by, M_FLAG_CAP if fam == "ctf" else M_BOMB_PLANT)
                    if n_rounds > 1:
                        next_round()
                    break
    end = min(now(), secs)
    order = sorted(teams, key=lambda tm: -team_score[tm])
    draw = len(teams) > 1 and len({team_score[tm] for tm in teams}) == 1
    place = {tm: (0 if draw or team_score[tm] == team_score[order[0]] else rank) for rank, tm in enumerate(order)}
    out = []
    for p in ps:
        if p.back <= end:
            p.alive_s += max(0.0, end - p.alive_since)
        if fam == "slayer" and not draw and place[p.team] == 0 and p.k >= 15 and p.d == 0:
            medal(p, M_PERFECTION)
        killed_by = {q.name: q.vs[p.name] for q in ps if q.vs.get(p.name)}
        most = max(sorted(p.vs.items()), key=lambda kv: kv[1]) if p.vs else None
        by = max(sorted(killed_by.items()), key=lambda kv: kv[1]) if killed_by else None
        score = p.score if fam not in ("slayer", "headhunter") else p.k - p.sui - p.btr
        out.append({"name": p.name, "bot": True, "idx": p.i, "clan": p.clan, "team": p.team, "standing": place[p.team],
                    "score": score, "kills": p.k, "deaths": p.d, "assists": p.as_, "betrayals": p.btr,
                    "suicides": p.sui, "spree": p.best_run, "alive": int(round(min(p.alive_s, end))),
                    "seconds": int(round(end)), "completed": 1, "kw": p.kw, "kg": p.kg, "km": p.km, "ko": p.ko,
                    "medal_total": sum(p.medals.values()),
                    "medals": {str(i): n for i, n in sorted(p.medals.items())},
                    "killed_most": list(most) if most else None, "killed_by": list(by) if by else None})
    return out, rows, {"seconds": int(round(end)), "scores": {str(tm): team_score[tm] for tm in teams},
                       "winner": None if draw else order[0]}
