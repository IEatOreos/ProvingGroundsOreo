"""Simulated bot-only matches for the Service Record (custom, Nov 17; the owner: "when I play a match all other bots also
play a game ... so that the website tracker gives bots a chance to keep up"; the plan agreed with him:
docs/BOT_SIMULATION_PLAN.md). The match itself is tools/sim_engine.py's; this file decides who plays, puts lobbies
together, holds the vote, and keeps the results.

Who plays: every bot of Bot Matchmaking's pool (people never), each at its own pace around a third of yours (one round =
one match of yours); whether a bot grinds is one roll at its difficulty's chance (GRINDER_CHANCE); Demon bots play every
round, one game to each of yours (Nov 19, the owner; EVERY_ROUND). Lobbies as
yours: (Nov 19, the owner) one game a round at most (a bot's pace is its chance of a game), and the bots of the
match of yours a round goes alongside sit it out. Arena 4v4 or Big Team Battle 8v8 from proving_grounds.ini's playlists, clans as one group (85% of rounds: all in when
one plays, one playlist, parties up to a team; clans_together),
teams balanced by skill, a map and gametype by the same vote as yours (native/proving_grounds.cpp liking / bot_vote,
None of the Above included). Bots a lobby cannot seat wait for the next round.

Where results go: native/bin/service_record/sim.db (SQLite): each match's seed, engine, the inputs it was played from,
its ledger row and its report and kill rows (compressed), and a mark when a reset covers it; native\\bin\\service_record
\\matchmaking.txt gets its id, so the Service Record counts it like a match of yours. tools/service_record.py and
tools/bot_career.py read the database as they build (site_entries, ledger_entries): a simulated match shows exactly
like a real one, and never teaches the model (sim_engine.fit reads real matches only).

usage: python -I bot_sim.py --after <GameUniqueId>   one round alongside that match of yours (Project Noble, as it ends)
       python -I bot_sim.py --rounds N               N rounds now (the menu row, the site's button)
       python -I bot_sim.py --stats                  who plays how often, and the model's numbers
       python -I bot_sim.py --check                  the model against the real matches (kills a minute, wins)
       python -I bot_sim.py --verify [N]             the last N stored matches played again from their seeds
       add --quiet to print nothing
"""
import datetime
import json
import math
import os
import sqlite3
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import service_record as sr  # noqa: E402
import sim_engine as se  # noqa: E402

DB = "sim.db"
TITLE = {"arena": "ARENA", "btb": "BIG TEAM BATTLE"}
# the playlists as native/proving_grounds.cpp default_playlists has them (proving_grounds.ini then changes them)
DEFAULT_PLAYLISTS = {
    "arena": {"size": 4, "gametypes": [("TU TEAM SLAYER DMR", 5), ("SWAT", 1), ("ONE FLAG CTF", 1), ("MULTI FLAG CTF", 1),
                                       ("CAPTURE THE FLAG", 1), ("KING OF THE HILL", 1), ("CRAZY KING", 1),
                                       ("ODDBALL", 1), ("HEADHUNTER", 1), ("ONE BOMB ASSAULT", 1),
                                       ("NEUTRAL BOMB ASSAULT", 1), ("STOCKPILE", 1), ("3-PLOT TERRITORIES", 1)],
              "maps": ["Sword Base", "Countdown", "Zealot", "Powerhouse", "Reflection", "Boardwalk", "Anchor 9",
                       "Condemned", "Asylum", "The Cage", "Pinnacle", "Beaver Creek", "Damnation", "Hang 'Em High",
                       "Prisoner"]},
    "btb": {"size": 8, "gametypes": [("TU TEAM SLAYER DMR", 5), ("MULTI FLAG CTF", 1), ("CAPTURE THE FLAG", 1),
                                     ("ONE BOMB ASSAULT", 1), ("NEUTRAL BOMB ASSAULT", 1), ("STOCKPILE", 1),
                                     ("TERRITORIES", 1), ("HEADHUNTER", 1)],
            "maps": ["Boneyard", "Spire", "Breakpoint", "Tempest", "Highlands", "Hemorrhage", "Paradiso", "Ridgeline",
                     "Breakneck", "Headlong", "Timberland"]},
}
# MCC's free for all ones as the owner's MCC reads them (lobby_library.txt): never in a team playlist
FREE_FOR_ALL = {"SWAT", "KING OF THE HILL", "CRAZY KING", "ODDBALL", "HEADHUNTER", "SLAYER", "TU FFA CRAZY KING"}
# a map's name in the lobby -> (map id, its MCC map variant file or None, its Forge layout's R number or None)
MAP_FILES = {
    "Sword Base": ("reach_20_sword_slayer", None, None), "Countdown": ("reach_45_launch_station", None, None),
    "Zealot": ("reach_45_aftship", None, None), "Powerhouse": ("reach_30_settlement", None, None),
    "Reflection": ("reach_52_ivory_tower", None, None), "Boardwalk": ("reach_50_panopticon", None, None),
    "Anchor 9": ("reach_dlc_slayer", None, None), "Condemned": ("reach_condemned", None, None),
    "Boneyard": ("reach_70_boneyard", None, None), "Spire": ("reach_35_island", None, None),
    "Breakpoint": ("reach_dlc_invasion", None, None), "Tempest": ("reach_dlc_medium", None, None),
    "Highlands": ("reach_trainingpreserve", None, None), "Ridgeline": ("reach_cex_timberland", None, None),
    "Breakneck": ("reach_cex_headlong", None, None), "Forge World": ("reach_forge_halo", None, None),
    "Asylum": ("reach_forge_halo", "hr_forgeWorld_asylum.mvar", 21),
    "Hemorrhage": ("reach_forge_halo", "hr_forgeWorld_hemorrhage.mvar", 22),
    "Paradiso": ("reach_forge_halo", "hr_forgeWorld_paradiso.mvar", 23),
    "Pinnacle": ("reach_forge_halo", "hr_forgeWorld_pinnacle.mvar", 24),
    "The Cage": ("reach_forge_halo", "hr_forgeWorld_theCage.mvar", 25),
    "Utopie": ("reach_forge_halo", "Utopie.mvar", None),    # (the owner's own Forge map, LocalFiles\...\Map)
    "Beaver Creek": ("reach_cex_beaver_creek", "beaver_creek_cl_031.mvar", None),
    "Damnation": ("reach_cex_damnation", "damnation_cl_031.mvar", None),
    "Hang 'Em High": ("reach_cex_hangemhigh", "hang_em_high_cl_031.mvar", None),
    "Prisoner": ("reach_cex_prisoner", "prisoner_cl_031.mvar", None),
    "Headlong": ("reach_cex_headlong", "headlong_cl_031.mvar", None),
    "Timberland": ("reach_cex_timberland", "timberland_cl_031.mvar", None),
}
# a map's feel for the bots' tastes (proving_grounds.cpp FEEL): size, vehicles, competitive
FEEL = {"Boardwalk": (1, 0, 1), "Boneyard": (2, 2, 0), "Countdown": (1, 0, 2), "Powerhouse": (1, 0, 1),
        "Reflection": (1, 0, 2), "Spire": (2, 2, 1), "Sword Base": (1, 0, 2), "Zealot": (1, 0, 2), "Anchor 9": (1, 0, 1),
        "Breakpoint": (2, 2, 0), "Tempest": (2, 2, 0), "Condemned": (1, 0, 1), "Highlands": (2, 2, 0),
        "Ridgeline": (2, 1, 0), "Breakneck": (2, 2, 0), "Forge World": (2, 2, 0), "Asylum": (1, 0, 2),
        "Hemorrhage": (2, 2, 1), "Paradiso": (2, 2, 0), "Pinnacle": (1, 0, 1), "The Cage": (1, 0, 2),
        "Beaver Creek": (0, 0, 2), "Damnation": (0, 0, 1), "Hang 'Em High": (1, 0, 1), "Headlong": (2, 2, 0),
        "Prisoner": (0, 0, 1), "Timberland": (2, 1, 0)}
# proving_grounds.cpp's gametype families, in its order (the bots' tastes are seeded by this number)
PG_FAMILY = ["slayer", "ctf", "assault", "koth", "oddball", "territories", "stockpile", "headhunter", "juggernaut",
             "infection", "race", "invasion", "insane"]
# proving_grounds.ini sim.<key>= (the plan's numbers)
SETTINGS = {"pace": 1 / 3, "grinder_pace": 1.0, "other_pace": 0.074, "btb_lean": 0.35,
            "spread": 0.6, "after_match": 1}      # (sim.after_match=0: no round alongside your matches; the button still)
# a bot's chance to be a grinder, by its difficulty: one roll a bot, from its name, so it keeps it (Nov 20, the owner:
# "every single bot doing like a percentage roll ... demon ... 75% ... mythic ... 65% ... legendary ... 50% ...
# Tactician will also have a 50% chance. Then heroic, normal will both have a 25% chance. An easy 5%"; Blind and
# Scaling, not named, as Legendary; Noble as Demon, Nov 23). sim.grinder_<tier>= in proving_grounds.ini changes one.
GRINDER_CHANCE = {"demon": 0.75, "noble": 0.75, "mythic": 0.65, "top": 0.50, "tactician": 0.50, "blind": 0.50,
                  "scaling": 0.50, "strong": 0.25, "average": 0.25, "novice": 0.05}
# tiers that play a game every round, one to each match of yours (Nov 19, the owner: "I would like all the demon
# difficulties to play just as much as me. So they play 1 game to my 1 game"; Noble too, Nov 23: "Yes like demon");
# a lobby that cannot seat one queues it
EVERY_ROUND = {"demon", "noble"}
# tiers that play every other round, in two fixed halves that take turns, whatever their grinder roll (Nov 23, the
# owner: "make all Heroics and Tacticians ... flip flop ... play 50% of all games"; "Yes, flip flop + B")
FLIP_FLOP = {"strong", "tactician"}


def flip_half(name):
    """0 or 1: which half of FLIP_FLOP a bot is in (from its name, so it keeps it)."""
    return se.hash_of(name, 71) % 2


# ---------------------------------------------------------------- settings, playlists
def ini_path():
    return os.path.join(sr.BIN, "proving_grounds.ini")


def read_ini(path=None):
    """(playlists {key: {"size", "gametypes" [(name, weight)], "maps" [name]}}, settings) as Project Noble reads
    proving_grounds.ini (its default_playlists, then <playlist>.gametype= / addgametype= / removegametype= and the maps
    the same way), and the sim.<key>= settings."""
    pls = {k: {"size": v["size"], "gametypes": list(v["gametypes"]), "maps": list(v["maps"])}
           for k, v in DEFAULT_PLAYLISTS.items()}
    settings = dict(SETTINGS)
    add = {k: {"gametypes": [], "maps": []} for k in pls}
    drop = {k: {"gametypes": [], "maps": []} for k in pls}
    replaced = {k: set() for k in pls}
    try:
        with open(path or ini_path(), encoding="utf-8-sig", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        lines = []
    for line in lines:
        line = line.strip()
        if not line or line[0] in "#;":
            continue
        if line.lower().startswith("sim.") and "=" in line:
            k, v = line[4:].split("=", 1)
            try:
                settings[k.strip()] = float(v)
            except ValueError:
                pass
            continue
        for key in pls:
            if not line.lower().startswith(key + "."):
                continue
            rest = line[len(key) + 1:]
            low = rest.lower()
            is_add, is_drop = low.startswith("add"), low.startswith("remove")
            what = rest[3:] if is_add else rest[6:] if is_drop else rest
            for kind, field in (("gametype=", "gametypes"), ("map=", "maps")):
                if not what.lower().startswith(kind):
                    continue
                val = what[len(kind):].strip()
                if not val:
                    continue
                item = val
                if field == "gametypes":
                    w = 1
                    if "*" in val:
                        name, ws = val.rsplit("*", 1)
                        try:
                            w = max(1, int(ws.strip()))
                        except ValueError:
                            w = 1
                        val = name.strip()
                    item = (val, w)
                if is_add:
                    add[key][field].append(item)
                elif is_drop:
                    drop[key][field].append(val)
                else:
                    if field not in replaced[key]:
                        pls[key][field] = []
                        replaced[key].add(field)
                    pls[key][field].append(item)
    for key, pl in pls.items():
        gts = [g for g in pl["gametypes"] if all(g[0].lower() != d.lower() for d in drop[key]["gametypes"])]
        for name, w in add[key]["gametypes"]:
            hit = False
            for i, g in enumerate(gts):
                if g[0].lower() == name.lower():
                    gts[i], hit = (g[0], w), True
            if not hit:
                gts.append((name, w))
        pl["gametypes"] = [(n.upper(), w) for n, w in gts if n.upper() not in FREE_FOR_ALL]
        squash = lambda s: "".join(c for c in s.lower() if c.isalnum())
        maps = [m for m in pl["maps"] if all(squash(m) != squash(d) for d in drop[key]["maps"])]
        maps += add[key]["maps"]
        pl["maps"] = [m for m in maps if m in MAP_FILES]
    return pls, settings


def default_difficulty():
    """botcore.ini's difficulty= (the BOTS panel's "for everyone": 0..3 the ranks, 4 Mixed, 5 Scaling, 6 Demon, 7 Blind,
    8 Tactician, 9 Mythic, 10 Noble)."""
    try:
        with open(os.path.join(sr.BIN, "botcore.ini"), encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip().lower().startswith("difficulty="):
                    return int(line.split("=", 1)[1].strip())
    except (OSError, ValueError):
        pass
    return 4


def tier_of(name, saved, difficulty):
    """A bot's tier as its lobbies give it: its saved difficulty (bot_pool_saved.ini), else the "for everyone" one;
    under Mixed, one of Mixed's six for good, from its name. saved is keyed as population keys it (pool_name, no case:
    the BOTS panel's own match, so "ii Toxic Moose " and "Death Adder" find their lines)."""
    key = sr.pool_name(name).lower()
    if key in saved and saved[key][0] in se.TIERS:
        return saved[key][0]
    d = {0: "novice", 1: "average", 2: "strong", 3: "top", 5: "scaling", 6: "demon", 7: "blind", 8: "tactician",
         9: "mythic", 10: "noble"}.get(difficulty)
    return d or se.MIXED[se.hash_of(name, 31) % len(se.MIXED)]


# ---------------------------------------------------------------- the population
class Bot:
    __slots__ = ("name", "tier", "style", "clan", "pace", "grinder", "lean")


def population(paths, settings, model=None):
    """[Bot] of the pool, people left out, each with its pace (games a round, on average), whether it grinds, and its
    lean toward Big Team Battle; all from its name, so they stay the same."""
    names = sr.read_pool_names(paths.bot_pool)
    saved = {sr.pool_name(k).lower(): v for k, v in sr.read_pool(paths.pool).items()}   # (as the panel matches)
    clans = sr.read_profiles(paths.profiles)
    people = people_names(paths)
    diff = default_difficulty()
    sp = settings["spread"]
    bots = []
    for n in names:
        if n in people:
            continue
        b = Bot()
        b.name, b.tier = n, tier_of(n, saved, diff)
        b.style = saved.get(sr.pool_name(n).lower(), ("", "any"))[1] or "any"
        b.style = b.style if b.style in se.STYLES else "any"
        b.clan = clans.get(n, "") or ""
        b.grinder = se.hfloat(n, 41) < grinder_chance(b.tier, settings)
        b.lean = min(0.9, max(0.05, settings["btb_lean"] + (se.hfloat(n, 44) - 0.5) * 0.5))
        b.pace = math.exp(sp * se.Rng(se.hash_of(n, 43)).gauss())    # (its own spread; the median set below)
        bots.append(b)
    # grinders always at their median pace; the others' median whatever brings everyone's average to the pace asked
    # for, but never under other_pace: with many grinders the round grows instead of the grinders shrinking (Nov 20,
    # the owner, "make it bigger"; other_pace is what the others had under the old 30%/10% grinder chances)
    # (EVERY_ROUND and FLIP_FLOP tiers left out of it: they play every round or every other one, and the rest keep the
    # pace they had)
    rest = [b for b in bots if b.tier not in EVERY_ROUND and b.tier not in FLIP_FLOP]
    target = settings["pace"] * len(rest)
    g_sum = sum(b.pace * settings["grinder_pace"] for b in rest if b.grinder)
    c_sum = sum(b.pace for b in rest if not b.grinder)
    c_med = max(settings["other_pace"], (target - g_sum) / c_sum) if c_sum else 0.0
    for b in bots:
        if b.tier in EVERY_ROUND:
            b.pace = 1.0
        elif b.tier in FLIP_FLOP:
            b.pace = 0.5                                     # (every other round: games_this_round)
        else:
            b.pace *= settings["grinder_pace"] if b.grinder else c_med
    return bots


def grinder_chance(tier, settings):
    """A tier's chance to grind: GRINDER_CHANCE, or proving_grounds.ini's sim.grinder_<tier>=."""
    return settings.get("grinder_" + tier, GRINDER_CHANCE.get(tier, 0.25))


def games_this_round(b, rng, round_no=None):
    """0 or 1: whether a bot plays this round (one game a round at most). An EVERY_ROUND tier always; a FLIP_FLOP one
    when its half's turn (round_no, the rounds played so far: odd and even take turns); the others by their pace (a
    Poisson draw, so a pace is the chance 1 - e^-pace). The draw is made for every bot, so the rounds' randomness
    stays as it was."""
    draw = min(1, rng.poisson(b.pace))
    if b.tier in EVERY_ROUND:
        return 1
    if b.tier in FLIP_FLOP and round_no is not None:
        return int(flip_half(b.name) == round_no % 2)
    return draw


def people_names(paths):
    """Names of people (never in a simulated match): the owner's list, the humans' pool file, every name a report has
    as a person."""
    out = set(sr.load_people(paths))
    try:
        with open(os.path.join(sr.BIN, "bot_pool_humans.txt"), encoding="utf-8-sig", errors="replace") as f:
            out |= {l.strip()[:15] for l in f if l.strip() and l.strip()[0] not in "#;"}
    except OSError:
        pass
    ledger = sr.load_json(paths.ledger, {})
    for m in ledger.values():
        for p in m.get("players", []):
            if not p.get("bot") and p.get("name"):
                out.add(p["name"])
    return out


# ---------------------------------------------------------------- the real matches, the model
def real_matches(paths):
    """[(detail, kill rows or None, Forge layout id or None)] of every real Reach match kept (its stats reset or not:
    resets are about records, not about how a bot plays)."""
    store = sr.load_json(os.path.join(paths.store, "matches.json"), {}).get("matches", {})
    kills = sr.load_json(os.path.join(paths.store, "kills.json"), {}).get("kills", {})
    out = []
    for m in store.values():
        if (m.get("game") or "") != "reach" or not (m.get("map") or "").startswith("reach"):
            continue
        entry = kills.get(f"{m.get('map')}_{m.get('start')}")
        rows = sr.kill_rows(entry) if entry is not None else None
        layout = None
        if rows and m.get("map") == "reach_forge_halo":
            spots = [c for k in rows if isinstance(k.get("vp"), list) for c in k["vp"][:2]]
            layout = sr.match_variant(m["map"], m.get("start"), spots, paths)
        out.append((m, rows or None, layout))
    return out


def build_model(paths, bots):
    tiers = {b.name: b.tier for b in bots}
    return se.fit(real_matches(paths), tiers)


def forge_layouts(paths):
    """{R number: layout id} of the Forge layouts seen live (maps/reach_forge_halo/variants: the heatmaps' layouts)."""
    out = {}
    folder = os.path.join(paths.maps, "reach_forge_halo", "variants")
    try:
        for vid in os.listdir(folder):
            v = sr.load_json(os.path.join(folder, vid, "variant.json"), {})
            name = v.get("name") or ""
            if name.startswith("$HReach_MPMap_R-"):
                try:
                    out[int(name.split("R-")[1].split("_")[0])] = vid
                except ValueError:
                    pass
    except OSError:
        pass
    return out


_MAPS = {}


def map_info(name, fam, paths, model, layouts):
    mid, mvar_file, r = MAP_FILES[name]
    layout = layouts.get(r) if r else None
    key = mid + (f"@{layout}" if layout else "")
    ck = (name, fam)
    if ck not in _MAPS:
        info = se.load_map(mid, key=key, mvar_file=mvar_file, fam=fam, root=os.path.dirname(paths.maps))
        _MAPS[ck] = info
    info = _MAPS[ck]
    info.real_pairs = (model.maps.get(key) or {}).get("pairs") or (
        (model.maps.get(mid) or {}).get("pairs") if not mvar_file else []) or []
    return info, mid, layout


# ---------------------------------------------------------------- lobbies and the vote
def liking(b, opt, fav_maps):
    """proving_grounds.cpp liking: the bot's taste in kinds of game, its favourite maps, its style, how sweaty it is."""
    fam_i = PG_FAMILY.index(opt["family"]) if opt["family"] in PG_FAMILY else len(PG_FAMILY) - 1
    s = (se.hfloat(b.name, 100 + fam_i) - 0.45) * 1.1
    if opt["family"] == "slayer":
        s += 0.35
    sweat = se.SWEAT.get(b.tier, 0.0) + (se.hfloat(b.name, 7) - 0.5) * 0.4
    size, vehicles, comp = FEEL.get(opt["map"], (1, 0, 1))
    s += sweat * (comp - 1) * 0.55
    if opt["family"] == "slayer":
        s += sweat * 0.35
    if opt["family"] in ("invasion", "infection"):
        s -= sweat * 0.3
    wheels, big = (se.hfloat(b.name, 11) - 0.4) * 0.8, (se.hfloat(b.name, 12) - 0.5) * 0.7
    if b.style == "wheelman":
        wheels += 0.9
    if b.style == "sniper":
        big += 0.6
    if b.style == "rusher":
        big -= 0.5
    s += wheels * (vehicles - 1) * 0.45 + big * (size - 1) * 0.35
    if fav_maps:
        n = len(fav_maps)
        fav, fav2, hate = se.hash_of(b.name, 21) % n, se.hash_of(b.name, 22) % n, se.hash_of(b.name, 23) % n
        if fav_maps[fav] == opt["map"]:
            s += 1.25
        elif fav_maps[fav2] == opt["map"]:
            s += 0.5
        if fav_maps[hate] == opt["map"] and hate != fav:
            s -= 0.9
    return s


def bot_vote(b, opts, nota, fav_maps, rng):
    """proving_grounds.cpp bot_vote: its odds for each option (None of the Above last), then its roll."""
    p = [math.exp(liking(b, o, fav_maps) / 0.45) for o in opts]
    total = sum(p)
    p = [x / total for x in p]
    pn = 0.0
    if nota:
        pn = min(0.3, 0.04 + 0.6 * max(0.0, 0.45 - max(p)) + (0.03 if se.SWEAT.get(b.tier, 0) < -0.4 else 0))
        p = [x * (1 - pn) for x in p]
    r, acc = rng.random(), 0.0
    for i, x in enumerate(p):
        acc += x
        if r < acc:
            return i
    return len(opts) if nota else len(opts) - 1


def draw_options(pl, rng, fits):
    """Three options as Project Noble draws them: gametypes by the playlist's weights, maps at random, a pair the map
    can hold (fits), a map at most once while there is a choice. A gametype may fill more than one option (Nov 19:
    each option its own roll of the weights)."""
    gts, maps = pl["gametypes"], pl["maps"]
    if not gts or not maps:
        return []
    cands = []
    for _ in range(200):
        if len(cands) >= 24:
            break
        g = gts[rng.weighted([w for _, w in gts])][0]
        m = rng.pick(maps)
        if (m, g) not in cands and fits(m, g):
            cands.append((m, g))
    opts = []
    for pass_ in range(2):
        for m, g in cands:
            if len(opts) >= 3:
                break
            used = any(o["map"] == m if pass_ == 0 else (o["map"] == m and o["gametype"] == g)
                       for o in opts)
            if not used:
                opts.append({"map": m, "gametype": g, "family": sr.family(g)})
    return opts


def vote(lobby, pl, rng, fits):
    opts = draw_options(pl, rng, fits)
    if not opts:
        return None
    for round_ in (1, 2):
        nota = round_ == 1
        counts = [0] * (len(opts) + 1)
        for b in lobby:
            if rng.chance(0.05):                                     # (one in twenty never votes)
                continue
            counts[bot_vote(b, opts, nota, pl["maps"], rng)] += 1
        if nota and counts[-1] * 2 > len(lobby):                     # (a majority on None of the Above: new options)
            opts = draw_options(pl, rng, fits) or opts
            continue
        best = max(counts[:len(opts)])
        tied = [i for i in range(len(opts)) if counts[i] == best]
        return opts[rng.pick(tied)]
    return opts[0]


CLAN_TOGETHER = 0.85                    # (a clan's chance a round to queue as one group)


def clans_together(bots, rng):
    """{clan, lowercased}: the clans (two members or more) that queue as one group this round, each CLAN_TOGETHER.
    Such a clan plays the round when any member would, every member in it (but those in your match), all in one
    playlist and in parties of a team at most (Nov 20, the owner: clanmates had each rolled their own round and
    playlist, so they met in 37 of 984 simulated matches)."""
    count = {}
    for b in bots:
        if b.clan:
            count[b.clan.lower()] = count.get(b.clan.lower(), 0) + 1
    return {c for c in sorted(count) if count[c] > 1 and rng.chance(CLAN_TOGETHER)}


def parties_of(bots, size, rng, together=None):
    """[[Bot]]: a clan queues together (CLAN_TOGETHER of the time, or as together, clans_together's, says), in parties
    of a team at most; everyone else alone."""
    by_clan, out = {}, []
    for b in bots:
        if b.clan:
            by_clan.setdefault(b.clan.lower(), []).append(b)
        else:
            out.append([b])
    for clan, members in by_clan.items():
        grouped = clan in together if together is not None else rng.chance(CLAN_TOGETHER)
        if len(members) > 1 and grouped:
            for i in range(0, len(members), size):
                out.append(members[i:i + size])
        else:
            out += [[b] for b in members]
    return rng.shuffle(out)


def team_split(parties, size, skill):
    """The parties of two or more (indexes into parties) that make team 0, so that both teams can be filled to size
    with the lone bots, the two teams' skill closest; None when they cannot be (3 + 3 + 2 into 4 + 4)."""
    multi = [i for i, p in enumerate(parties) if len(p) > 1]
    total = sum(len(parties[i]) for i in multi)
    best = None
    for mask in range(1 << len(multi)):
        side = [multi[k] for k in range(len(multi)) if mask >> k & 1]
        n0 = sum(len(parties[i]) for i in side)
        if n0 > size or total - n0 > size:
            continue
        s0 = sum(skill(b) for i in side for b in parties[i])
        s1 = sum(skill(b) for i in multi if i not in side for b in parties[i])
        if best is None or abs(s0 - s1) < best[0]:
            best = (abs(s0 - s1), side)
    return None if best is None else best[1]


def lobbies_of(bots, size, rng, skill, first=None, together=None):
    """([[team 0 bots], [team 1 bots]] per lobby, bots left waiting): parties seated first come first (in a lobby whose
    teams can still be made: team_split), teams dealt by skill with each party on one team. first(bot): a party with
    one is never left waiting while a full lobby holds a party of its size without one, or as many lone bots (they
    change places; the Demons' game every round, EVERY_ROUND)."""
    fits = lambda lb: team_split(lb, size, lambda b: 0.0) is not None
    lobbies, open_ = [], []
    for party in parties_of(bots, size, rng, together):
        home = next((lb for lb in open_ if 2 * size - sum(len(p) for p in lb) >= len(party)
                     and (len(party) == 1 or fits(lb + [party]))), None)
        if home is None:
            home = []
            open_.append(home)
            lobbies.append(home)
        home.append(party)
        if sum(len(p) for p in home) == 2 * size:
            open_.remove(home)
    if first:
        filled = [lb for lb in lobbies if sum(len(p) for p in lb) == 2 * size]
        for lb in lobbies:
            if lb in filled:
                continue
            for i, party in enumerate(lb):
                if not any(first(b) for b in party):
                    continue
                for f in filled:
                    j = next((j for j, q in enumerate(f) if len(q) == len(party) and not any(first(b) for b in q)),
                             None)
                    if j is not None:
                        f[j], lb[i] = party, f[j]
                        break
                    # (else as many lone bots without one: a clan party of a Demon, Nov 20)
                    lone = [j for j, q in enumerate(f) if len(q) == 1 and not first(q[0])][:len(party)]
                    rest = [q for j, q in enumerate(f) if j not in lone] + [party]
                    if len(party) > 1 and len(lone) == len(party) and fits(rest):
                        out = [f[j] for j in lone]
                        f[:] = rest
                        lb[i:i + 1] = out
                        break
    full, waiting = [], []
    for lb in lobbies:
        side = team_split(lb, size, skill) if sum(len(p) for p in lb) == 2 * size else None
        if side is None:
            waiting += [b for p in lb for b in p]
            continue
        teams, tot = [[], []], [0.0, 0.0]
        for i, party in enumerate(lb):                               # (the parties of two or more as team_split says)
            if len(party) > 1:
                t = 0 if i in side else 1
                teams[t] += party
                tot[t] += sum(skill(b) for b in party)
        for party in sorted((p for p in lb if len(p) == 1), key=lambda p: -skill(p[0])):
            room = [size - len(teams[0]), size - len(teams[1])]
            t = min((x for x in (0, 1) if room[x] > 0), key=lambda x: tot[x])
            teams[t] += party
            tot[t] += skill(party[0])
        for _ in range(20):                                          # (swaps of two lone bots that even the teams)
            gap, best = tot[0] - tot[1], None
            lone = [{b.name for p in lb if len(p) == 1 for b in p}]
            for x in teams[0]:
                for y in teams[1]:
                    if x.name in lone[0] and y.name in lone[0]:
                        d = skill(x) - skill(y)
                        if abs(gap - 2 * d) < abs(gap) - 1e-9 and (best is None or abs(gap - 2 * d) < best[0]):
                            best = (abs(gap - 2 * d), x, y, d)
            if not best:
                break
            _, x, y, d = best
            teams[0][teams[0].index(x)], teams[1][teams[1].index(y)] = y, x
            tot[0] -= d
            tot[1] += d
        if len(teams[0]) == size and len(teams[1]) == size:
            full.append(teams)
        else:
            waiting += teams[0] + teams[1]
    return full, waiting


# ---------------------------------------------------------------- storage
def db_path(paths):
    return os.path.join(paths.store, DB)


def connect(paths):
    os.makedirs(paths.store, exist_ok=True)
    con = sqlite3.connect(db_path(paths), timeout=30)
    con.execute("CREATE TABLE IF NOT EXISTS matches (gid TEXT PRIMARY KEY, t REAL, playlist TEXT, map TEXT, start TEXT,"
                " seed INTEGER, engine INTEGER, reset TEXT DEFAULT '', round INTEGER, ledger TEXT, data BLOB)")
    con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    return con


def meta_get(con, k, default):
    r = con.execute("SELECT v FROM meta WHERE k = ?", (k,)).fetchone()
    try:
        return json.loads(r[0]) if r else default
    except ValueError:
        return default


def meta_set(con, k, v):
    con.execute("INSERT OR REPLACE INTO meta (k, v) VALUES (?, ?)", (k, json.dumps(v)))


def pack(obj):
    return zlib.compress(json.dumps(obj, separators=(",", ":")).encode("utf-8"), 9)


def unpack(blob):
    return json.loads(zlib.decompress(blob).decode("utf-8"))


def _entries(paths, want_detail):
    if not os.path.exists(db_path(paths)):
        return {}, {}, {}
    try:
        con = sqlite3.connect(db_path(paths), timeout=30)
        cur = con.execute("SELECT gid, reset, ledger" + (", data" if want_detail else "") + " FROM matches")
        ledger, details, kills = {}, {}, {}
        for row in cur:
            gid, reset, led = row[0], row[1], json.loads(row[2])
            if reset == "all":
                led["all_reset"] = True
            elif reset == "bots":
                led["bots_reset"] = True
            ledger[gid] = led
            if want_detail:
                d = unpack(row[3])
                details[gid] = d["detail"]
                kills[f"{d['detail']['map']}_{d['detail']['start']}"] = {"v": 2, "rows": d["rows"]}
        con.close()
        return ledger, details, kills
    except (sqlite3.Error, ValueError, KeyError, zlib.error):
        return {}, {}, {}


def site_entries(paths):
    """(ledger rows {gid: entry}, reports {gid: detail}, kill rows {"<map>_<start>": entry}) of every simulated
    match, for tools/service_record.py's build. Nothing when there is no database."""
    return _entries(paths, True)


def ledger_entries(paths=None):
    """{gid: ledger entry} of every simulated match (tools/bot_career.py's totals)."""
    return _entries(paths or sr.Paths(), False)[0]


def mark_reset(kind, paths=None):
    """bot_career --reset-bots ("bots") / --reset-all ("all"): the simulated matches so far stop counting the same way
    (kept, marked, so they are never counted again)."""
    paths = paths or sr.Paths()
    if not os.path.exists(db_path(paths)):
        return 0
    con = connect(paths)
    with con:
        if kind == "all":
            n = con.execute("UPDATE matches SET reset = 'all' WHERE reset != 'all'").rowcount
        else:
            n = con.execute("UPDATE matches SET reset = 'bots' WHERE reset = ''").rowcount
    con.close()
    return n


def add_to_matchmaking(paths, rows):
    """Each simulated match's id in matchmaking.txt beside the owner's (the Service Record counts only those)."""
    path = paths.matchmaking or os.path.join(paths.store, "matchmaking.txt")
    fresh = not os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if fresh:
            f.write("# The matches Project Noble started (native/proving_grounds.cpp), by MCC's GameUniqueId: the "
                    "Service\n# Record (tools/service_record.py) counts only these. id<TAB>when<TAB>playlist\n")
        for gid, t, playlist in rows:
            f.write(f"{gid}\t{time.strftime('%Y-%m-%d %H:%M', time.localtime(t))}\t{playlist}\n")


def pid_alive(pid):
    """Whether a process with this id runs (Windows: OpenProcess; elsewhere signal 0)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)        # (PROCESS_QUERY_LIMITED_INFORMATION)
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return bool(ok) and code.value == 259                              # (STILL_ACTIVE)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class Lock:
    """One simulation at a time (the end of a match and a button pressed at once)."""

    def __init__(self, paths):
        self.path = os.path.join(paths.store, "sim.lock")

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        for _ in range(300):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return self
            except FileExistsError:
                try:
                    with open(self.path, encoding="utf-8") as f:
                        pid = int(f.read().strip() or 0)
                    if not pid_alive(pid) or time.time() - os.path.getmtime(self.path) > 600:
                        os.remove(self.path)                 # (left by a run that stopped: not running now)
                        continue
                except (OSError, ValueError):
                    pass
                time.sleep(0.2)
        raise TimeoutError("another simulation is running")

    def __exit__(self, *a):
        try:
            os.remove(self.path)
        except OSError:
            pass


# ---------------------------------------------------------------- a round
def gid_from(rng):
    h = "%032x" % ((rng.u64() << 64) | rng.u64())
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def used_starts(paths, con):
    """{(map, start)} already taken (kill rows are filed by map and start)."""
    out = {(m.get("map"), m.get("start")) for m in sr.load_json(os.path.join(paths.store, "matches.json"), {})
           .get("matches", {}).values()}
    out |= set(con.execute("SELECT map, start FROM matches").fetchall())
    return out


def play_round(paths, window, seed, settings=None, playlists=None, quiet=True, sit_out=()):
    """One round: who plays, the lobbies, the votes, the matches, stored. window (from, to): when its matches start
    (epoch seconds). sit_out: the bots of the match of yours this round goes alongside (Nov 19, the owner: they
    played that match; it is their game this round; a queued one keeps its place for the next). Each bot plays one
    game a round at most (Nov 19, the owner: no bot in two matches at once; its pace is its chance to play).
    Returns the matches it stored [(gid, playlist title, map, gametype)]."""
    playlists, ini_settings = (playlists, settings) if playlists else read_ini()
    settings = settings or ini_settings
    bots = population(paths, settings)
    if not bots:
        return []
    model = build_model(paths, bots)
    layouts = forge_layouts(paths)
    by_name = {b.name: b for b in bots}
    rng = se.Rng(seed)
    skill = lambda b: se.skill_of(b.name, b.tier, model.skill_scale)   # (its difficulty only, as the match plays it)
    stored = []
    con = connect(paths)
    try:
        taken = used_starts(paths, con)
        queue = [by_name[n] for n in meta_get(con, "queue", []) if n in by_name]
        sit = {n.lower() for n in sit_out}
        round_no = meta_get(con, "rounds", 0)                        # (FLIP_FLOP's halves take turns by it)
        games = {b.name: games_this_round(b, rng, round_no) for b in bots}   # (one a round at most; Demons every)
        for b in bots:
            if b.name.lower() in sit:                                # (in your match: that is its game this round)
                games[b.name] = 0
        for q in queue:                                              # (last round's waiting bots: their game now)
            if q.name.lower() not in sit:
                games[q.name] = 1
        together = clans_together(bots, rng)                         # (these clans play as one group this round)
        clan_of = lambda b: b.clan.lower() if b.clan and b.clan.lower() in together else ""
        playing = {clan_of(b) for b in bots if clan_of(b) and games[b.name]}
        for b in bots:
            if clan_of(b) in playing and b.name.lower() not in sit:
                games[b.name] = 1
        layers = max(games.values()) if games else 0
        waiting = [q for q in queue if q.name.lower() in sit]        # (queued but in your match: first next round)
        rows_mm, n_lobby = [], 0
        for layer in range(1, layers + 1):
            entrants = [b for b in queue + bots if games.get(b.name, 0) >= layer]
            seen, uniq = set(), []
            for b in entrants:
                if b.name not in seen:
                    seen.add(b.name)
                    uniq.append(b)
            split, clan_pick = {"arena": [], "btb": []}, {}
            for b in uniq:
                c = clan_of(b)
                if c and c not in clan_pick:                         # (one playlist for the clan: its members' lean)
                    leans = [m.lean for m in uniq if clan_of(m) == c]
                    clan_pick[c] = "btb" if rng.chance(sum(leans) / len(leans)) else "arena"
                pick = clan_pick[c] if c else "btb" if rng.chance(b.lean) else "arena"
                split[pick].append(b)
            for key, members in split.items():
                pl = playlists.get(key)
                if not pl or not pl["maps"] or not pl["gametypes"]:
                    waiting += members
                    continue
                size = pl["size"]
                full, left = lobbies_of(members, size, rng, skill, first=lambda b: b.tier in EVERY_ROUND,
                                        together=together)
                waiting += left
                for teams in full:
                    n_lobby += 1
                    lobby = teams[0] + teams[1]
                    fits = lambda m, g: map_info(m, sr.family(g), paths, model, layouts)[0].supports(sr.family(g))
                    opt = vote(lobby, pl, rng, fits)
                    if not opt:
                        continue
                    fam = opt["family"]
                    info, mid, layout = map_info(opt["map"], fam, paths, model, layouts)
                    spec = {"gametype": opt["gametype"], "size": size,
                            "players": [{"name": b.name, "team": t, "clan": b.clan, "style": b.style, "tier": b.tier}
                                        for t in (0, 1) for b in teams[t]]}
                    mseed = rng.u64()
                    sl = se.model_slice(model, opt["gametype"], size)
                    inputs = se.match_inputs(spec, model, info)
                    report, krows, res = se.play(spec, se.model_from_slice(sl, opt["gametype"]), info, mseed, inputs)
                    t0 = window[0] + rng.random() * max(1.0, window[1] - window[0])
                    while True:
                        start = time.strftime("%Y%m%d-%H%M%S", time.localtime(t0))
                        if (mid, start) not in taken:
                            break
                        t0 += 1
                    taken.add((mid, start))
                    end = t0 + res["seconds"]
                    gid = gid_from(rng)
                    fname = f"trace_{mid}_{start}.carnage.xml"
                    detail = {"file": fname, "game": "reach", "map": mid, "start": start, "type": opt["gametype"],
                              "teams": True, "players": report}
                    if layout:
                        detail["layout"] = layout
                    led = {"file": fname, "time": end, "sim": {"seed": mseed, "engine": se.ENGINE,
                                                              "playlist": TITLE[key]},
                           "players": [{"name": r["name"], "bot": True, "team": r["team"], "standing": r["standing"],
                                        "kills": r["kills"], "deaths": r["deaths"], "assists": r["assists"],
                                        "seconds": r["seconds"]} for r in report]}
                    data = {"detail": detail, "rows": krows, "spec": spec, "inputs": inputs, "slice": sl,
                            "map": opt["map"], "result": res}
                    con.execute("INSERT INTO matches (gid, t, playlist, map, start, seed, engine, reset, round, ledger,"
                                " data) VALUES (?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?)",
                                (gid, end, TITLE[key], mid, start, mseed & ((1 << 63) - 1), se.ENGINE,
                                 meta_get(con, "rounds", 0) + 1, json.dumps(led, separators=(",", ":")), pack(data)))
                    rows_mm.append((gid, t0, TITLE[key]))
                    stored.append((gid, TITLE[key], opt["map"], opt["gametype"]))
        left, seen = [], set()
        for b in waiting:                                            # (seated nowhere this round: first in the next)
            if b.name not in seen:
                seen.add(b.name)
                left.append(b.name)
        meta_set(con, "queue", left[:2000])
        meta_set(con, "rounds", meta_get(con, "rounds", 0) + 1)
        meta_set(con, "last", {"when": time.time(), "matches": len(stored), "lobbies": n_lobby})
        con.commit()
        add_to_matchmaking(paths, rows_mm)
    finally:
        con.close()
    return stored


def write_status(paths, n):
    """sim_status.txt: what the last run did (Project Noble's menu row shows it)."""
    path = os.path.join(paths.store, "sim_status.txt")
    try:
        total = sqlite3.connect(db_path(paths)).execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    except sqlite3.Error:
        total = 0
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(f"matches\t{n}\ntotal\t{total}\nwhen\t{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    os.replace(tmp, path)


def window_after(paths, gid):
    """(from, to) epoch seconds the round alongside a match of yours starts in: from its start, through its first half
    (it ended when MCC wrote its report; it lasted as long as its longest player). Now when it is not in the ledger."""
    m = sr.load_json(paths.ledger, {}).get(gid)
    if not m:
        now = time.time()
        return now - 600, now - 300
    end = float(m.get("time", time.time()))
    secs = max((p.get("seconds", 0) for p in m.get("players", [])), default=600) or 600
    start = end - secs
    return start, start + max(60.0, secs * 0.5)


def bots_in(paths, gid):
    """(Nov 19) The bots' names of a match of yours (its ledger row; bot_career adds it before this runs): they sit
    out the round alongside it. [] when it is not in the ledger."""
    m = sr.load_json(paths.ledger, {}).get(gid) or {}
    return [p["name"] for p in m.get("players", []) if p.get("bot") and p.get("name")]


def run(paths, rounds=1, after=None, quiet=False):
    """The command line's work: rounds now, or one round alongside the match `after`. Returns matches stored."""
    total = []
    with Lock(paths):
        con = connect(paths)
        base_seed = meta_get(con, "seed", None)
        if base_seed is None:
            base_seed = int(time.time() * 1000) & ((1 << 62) - 1)
        n_done = meta_get(con, "rounds", 0)
        con.close()
        for i in range(rounds):
            sit_out = ()
            if after:
                window = window_after(paths, after)
                sit_out = bots_in(paths, after)
            else:
                now = time.time()
                back = (rounds - i) * 900 + 720
                window = (now - back, now - back + 120)
            seed = (base_seed * 6364136223846793005 + n_done + i + 1) & ((1 << 64) - 1)
            got = play_round(paths, window, seed, sit_out=sit_out)
            total += got
            if not quiet:
                print(f"round {n_done + i + 1}: {len(got)} matches", flush=True)
        con = connect(paths)
        with con:
            meta_set(con, "seed", base_seed)
        con.close()
        write_status(paths, len(total))
    return total


# ---------------------------------------------------------------- checks
def stats(paths):
    pls, settings = read_ini()
    bots = population(paths, settings)
    model = build_model(paths, bots)
    n = len(bots)
    top = [b for b in bots if b.tier in se.TOP_TIERS]
    grind = [b for b in bots if b.grinder]
    print(f"{n} bots (people left out); {len(top)} Legendary and above")
    by = {}
    for b in bots:
        by.setdefault(b.tier, [0, 0])[0] += b.grinder
        by[b.tier][1] += 1
    print(f"grinders: {len(grind)} ({100 * len(grind) / max(1, n):.0f}%): " + ", ".join(
        f"{t} {g}/{c} ({100 * g / c:.0f}%, chance {100 * grinder_chance(t, settings):.0f}%)"
        for t, (g, c) in sorted(by.items(), key=lambda x: -grinder_chance(x[0], settings))))
    mean = sum(b.pace for b in bots) / max(1, n)
    gp = sorted(b.pace for b in grind)
    cp = sorted(b.pace for b in bots if not b.grinder)
    med = lambda xs: xs[len(xs) // 2] if xs else 0
    print(f"games per match of yours: everyone {mean:.3f} on average; grinders' median {med(gp):.2f}, "
          f"the others' {med(cp):.3f}")
    plays = lambda b: (1.0 if b.tier in EVERY_ROUND else 0.5 if b.tier in FLIP_FLOP
                       else 1.0 - math.exp(-b.pace))     # (one a round at most: its chance)
    print(f"per round about {sum(plays(b) for b in bots):.0f} seats: about {sum(plays(b) * (1 - b.lean) for b in bots) / 8:.0f}"
          f" Arena and {sum(plays(b) * b.lean for b in bots) / 16:.0f} Big Team Battle lobbies")
    print(f"model: kills a player a minute {model.kpm:.3f}; by family { {k: round(v, 3) for k, v in model.kpm_by.items()} }")
    print(f"real minutes: {sum(model.real_minutes.get(b.name, 0) for b in bots):.0f} across "
          f"{sum(1 for b in bots if model.real_minutes.get(b.name))} bots")
    print(f"limits: { {f'{g} {s}v{s}': v for (g, s), v in model.limits.items()} }")
    for key, pl in pls.items():
        print(f"{TITLE[key]}: {len(pl['maps'])} maps, gametypes {pl['gametypes']}")


def check(paths, reps=200):
    """The model against the real matches: each real Reach match's lineup played `reps` times; kills a minute, the
    real K/D inside the simulated 90% band, the Brier score of the win calls."""
    pls, settings = read_ini()
    bots = population(paths, settings)
    tiers = {b.name: b.tier for b in bots}
    model = build_model(paths, bots)
    layouts = forge_layouts(paths)
    names = {v: k for k, v in MAP_FILES.items() if not v[1]}
    real_kpm, sim_kpm, inside, total, brier, nb = 0.0, 0.0, 0, 0, 0.0, 0
    rng = se.Rng(12345)
    for detail, rows, layout in real_matches(paths):
        ps = detail["players"]
        teams = sorted({p["team"] for p in ps})
        if len(teams) != 2 or len(ps) < 4:
            continue
        size = max(sum(1 for p in ps if p["team"] == t) for t in teams)
        spec = {"gametype": detail.get("type", "TU TEAM SLAYER DMR"), "size": size,
                "players": [{"name": p["name"], "team": teams.index(p["team"]), "clan": "", "style": "any",
                             "tier": tiers.get(p["name"], "top")} for p in ps]}
        info = se.load_map(detail["map"], fam=sr.family(spec["gametype"]), root=os.path.dirname(paths.maps))
        info.real_pairs = (model.maps.get(detail["map"]) or {}).get("pairs") or []
        secs = max(p["seconds"] for p in ps)
        real_k = sum(p["kills"] for p in ps)
        if secs < 120:
            continue
        kds = {p["name"]: [] for p in ps}
        wins, k_tot, s_tot = 0, 0, 0
        for _ in range(reps):
            out, _, res = se.play(spec, model, info, rng.u64())
            k_tot += sum(r["kills"] for r in out)
            s_tot += res["seconds"]
            wins += res["winner"] == 0
            for r in out:
                kds[r["name"]].append(r["kills"] / max(1, r["deaths"]))
        real_kpm += real_k / (secs / 60.0) / len(ps)
        sim_kpm += k_tot / (s_tot / 60.0) / len(ps)
        for p in ps:
            xs = sorted(kds[p["name"]])
            lo, hi = xs[int(0.05 * len(xs))], xs[int(0.95 * len(xs)) - 1]
            kd = p["kills"] / max(1, p["deaths"])
            inside += lo <= kd <= hi
            total += 1
        real_win = next((p["standing"] == 0 for p in ps if p["team"] == teams[0]), False) and \
            not all(p["standing"] == 0 for p in ps)
        brier += (wins / reps - (1.0 if real_win else 0.0)) ** 2
        nb += 1
    if not nb:
        print("no real two-team Reach matches to check against")
        return
    print(f"{nb} real matches, each played {reps} times")
    print(f"kills a player a minute: real {real_kpm / nb:.3f}, simulated {sim_kpm / nb:.3f}")
    print(f"real K/D inside the simulated 90% band: {100 * inside / max(1, total):.0f}% of {total} players (90% is right)")
    print(f"Brier score of the win calls: {brier / nb:.3f} (0.25 is a coin flip; lower is better)")


def verify(paths, n=20):
    """The last n stored matches played again from their seed and inputs: the same scoreboard, or a difference."""
    con = connect(paths)
    rows = con.execute("SELECT gid, seed, data FROM matches ORDER BY t DESC LIMIT ?", (n,)).fetchall()
    con.close()
    layouts = forge_layouts(paths)
    same = 0
    for gid, _, blob in rows:
        d = unpack(blob)
        spec, gt = d["spec"], d["spec"]["gametype"]
        info, _, _ = map_info(d["map"], sr.family(gt), paths, se.Model(), layouts)
        info.real_pairs = []
        seed = json.loads(con_ledger(paths, gid))["sim"]["seed"]
        out, _, _ = se.play(spec, se.model_from_slice(d["slice"], gt), info, seed, d["inputs"])
        want = [(r["name"], r["kills"], r["deaths"], r["assists"]) for r in d["detail"]["players"]]
        got = [(r["name"], r["kills"], r["deaths"], r["assists"]) for r in out]
        same += want == got
    print(f"{same} of {len(rows)} played again the same (a difference means the map files or real kill spots changed)")


def con_ledger(paths, gid):
    con = connect(paths)
    r = con.execute("SELECT ledger FROM matches WHERE gid = ?", (gid,)).fetchone()
    con.close()
    return r[0] if r else "{}"


def main(argv):
    paths = sr.Paths()
    quiet = "--quiet" in argv
    if "--stats" in argv:
        stats(paths)
        return 0
    if "--check" in argv:
        check(paths)
        return 0
    if "--verify" in argv:
        i = argv.index("--verify")
        verify(paths, int(argv[i + 1]) if i + 1 < len(argv) and argv[i + 1].isdigit() else 20)
        return 0
    after = argv[argv.index("--after") + 1] if "--after" in argv and argv.index("--after") + 1 < len(argv) else None
    rounds = 1
    if "--rounds" in argv:
        try:
            rounds = max(1, min(50, int(argv[argv.index("--rounds") + 1])))
        except (IndexError, ValueError):
            sys.exit("--rounds needs a number")
    if not after and "--rounds" not in argv:
        print(__doc__)
        return 1
    if after and not read_ini()[1].get("after_match", 1):
        if not quiet:
            print("sim.after_match=0 in proving_grounds.ini: no round alongside matches")
        return 0
    t0 = time.time()
    got = run(paths, rounds=1 if after else rounds, after=after, quiet=quiet)
    if not quiet:
        print(f"{len(got)} simulated matches in {time.time() - t0:.1f} s ({db_path(paths)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
