"""Scaling difficulty: a difficulty of its own, set by the person's K/D (and after 5 games).

One number, the SKILL RATING (1.0 = 100% = a skilled human player's baseline, logs/scaling.json, starting at 100%).
Behaviour is Legendary's (tier "top": weapon seeking, power positions, map knowledge, routes, tactics, teamwork, motion
tracker). The rating sets (PARAMS):
  hands: times and errors (reaction, aim error and the hand's tremor, aim speed, flick, tracking, decisions, flick
  overshoot, trigger looseness, ram error) = the baseline's / rating (300%: a third); shares missed (headshots, leading
  shots) the same; turn speed = the baseline's x rating up to TURN_MAX (2000 deg/s, twice Legendary's: a 180 in
  about 0.14 s, still a smooth swing, never a snap).
  Reaction, tracking and decisions go no quicker than one tick of the brain's 30 Hz loop.
  game sense (memory of where men are, callout hearing, shots at a line before moving on) = Legendary's up to LEGEND
  (150%, where the hands are about Legendary's), past it Legendary's x or / (rating / LEGEND).

No floor; the top is MAX (1800%), the bots' best: there reaction, tracking and decisions are one tick, a callout is
heard within a tick, one shot at a blocked line is enough, the aim error is under 0.5 mrad (a head is 8 mrad wide at
30 u), memory past two minutes. Beyond it nothing a fight feels changes, and the rating only compounded: at a steady
2.6 K/D it went 1721% -> 2350% -> 3033% -> 3910% -> 5016% in four games with the bots no stronger. Held at MAX, one
game under 1.0 brings it straight down. (A 660% cap with game sense held at Legendary's midday, made the bots
weaker: the player went from 2x to 2.5x his teammates' kills. Turn speed held at Legendary's 1000 deg/s left the
bots behind the uncapped ones that had kept up with him; it now goes on to TURN_MAX.)

After each game on Scaling the rating is set again from the person's last N Scaling games (N his choice, 1-20,
botcore.ini scale_games=):
    each game's estimate = the rating that game (MAX at most) x his K/D that game
    new rating = those estimates' geometric mean, the newest weighted most (1, 2, ... n), MAX at most
A K/D of 1.0 keeps it, 3.5 against 100% bots puts it at 350%, 0.5 halves it. A game counts once: completed, 2+
minutes, 3+ of his kills + deaths. Locked (native/bin/scaling.ini lock=1, the BOTS panel's Advanced tab) the rating
stays where he set it; games still count for when he unlocks it. A custom profile there weights each hand setting
against the rating (reaction 150%: half as quick again as the rating gives).
"""
import glob
import json
import math
import os
import re

from .profiles import CRAFT, HANDS, LOOSE, PERSONALITIES, TIERS, TURN as TURNS, Profile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.join(ROOT, "logs")
INI = os.path.join(ROOT, "native", "bin", "scaling.ini")   # the BOTS panel's Advanced tab: lock, custom profiles
STATE = "scaling.json"
GAMES = 5            # the person's last Scaling games averaged, until he picks (botcore.ini scale_games=)
MAX_GAMES = 20       # the most he can pick
VIEW = "scaling_view.txt"   # the BOTS panel's hover box over Scaling: the numbers for each N (write_view)
MIN_FIGHTS = 3       # his kills + deaths for a game to count
BOT_ID = "0xB07B07B0"   # botcore's own players' Xbox IDs start with this
TINY = 1e-6          # (numbers only: no value may reach exactly zero)
TICK = 1.0 / 30      # the live loop's tick (tools/live_bots.py HZ): reaction, tracking, decisions go no quicker
FLOORS = dict(reaction=TICK, track=TICK, decide=TICK)
TURN = TURNS["average"]            # turn speed at 100%
TURN_MAX = 2 * TURNS["top"]        # the quickest Scaling turns (2000 deg/s): reached at 460%
LEGEND = 1.5         # the rating where the hands are about Legendary's: game sense grows past Legendary's above it
MAX = 18.0           # the bots' best (1800%): shots before moving on reach 1 there, the last setting to hit its floor

# the hand settings that scale: (key in a custom profile, label, the bot's settings it sets, at 100%)
PARAMS = (("reaction", "Reaction time", dict(reaction=HANDS["reaction"])),
          ("aim", "Aim accuracy", dict(aim_err=HANDS["aim_err"], tremor_k=1.0)),   # (tremor_k: x bot.TREMOR)
          ("aim_speed", "Aim speed", dict(lag=HANDS["lag"])),
          ("flick", "Flick speed", dict(flick=HANDS["flick"])),
          ("tracking", "Tracking", dict(track=HANDS["track"])),
          ("decide", "Decision speed", dict(decide=HANDS["decide"])),
          ("overshoot", "Flick control", dict(overshoot=HANDS["overshoot"])),
          ("turn", "Turn speed", dict(turn=TURN)),
          ("head", "Headshots", dict(head_aim=0.5)),
          ("lead", "Leading shots", dict(lead=HANDS["lead"])),
          ("trigger", "Trigger discipline", dict(loose_follow=LOOSE["average"]["follow"],
                                                 loose_early=LOOSE["average"]["early"])),
          ("ram", "Ramming accuracy", dict(ram_err=20.0)),
          # game sense: Legendary's (TIERS top memory, callouts.TIMING top hear, Bot.DRY_SHOTS top), past it above LEGEND
          ("memory", "Memory", dict(memory=TIERS["top"]["memory"])),
          ("hear", "Callout hearing", dict(hear=0.15)),
          ("dry", "Shots before moving on", dict(dry_shots=12.0)))
MISSES = ("head_aim", "lead")      # chances: the share missed shrinks with the rating
SENSE = ("memory", "hear", "dry_shots")
EXTRA = ("head_aim", "loose_follow", "loose_early", "ram_err", "tremor_k", "hear", "dry_shots")   # (Profile.extra:
                                                                  # what the brain otherwise reads from its tier tables)


def level(rating, weight=1.0):
    """The rating a setting plays at, with a custom profile's weight (no floor, MAX at most)."""
    return min(MAX, max(TINY, rating * weight))


def values(rating, weights=None):
    """Every scaled setting at this rating (1.0 = 100%), with a custom profile's weights {key: 1.0 = as rated}."""
    out = {}
    for key, _, base in PARAMS:
        r = level(rating, (weights or {}).get(key, 1.0))
        g = max(1.0, r / LEGEND)                       # game sense: Legendary's, then past it
        for k, v in base.items():
            out[k] = (min(TURN_MAX, v * r) if k == "turn" else
                      max(0.0, 1.0 - (1.0 - v) / r) if k in MISSES else
                      v * g if k == "memory" else max(1.0, v / g) if k == "dry_shots" else v / g if k == "hear" else
                      max(FLOORS.get(k, 0.0), v / r))
    return out


def settings(path=INI):
    """The Advanced tab's Scaling settings: {lock, rating (used while locked), name, weights} (native/bin/scaling.ini:
    lock=0|1, rating=<percent>, use=<n>, then one profile=<name>|<key>=<percent>|... line each, use 1 the first;
    use=0 or none: every weight 100%)."""
    out = dict(lock=False, rating=None, name="", weights={})
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return out
    use, profiles = 0, []
    for line in lines:
        key, _, val = line.partition("=")
        try:
            if key == "lock":
                out["lock"] = val.strip() == "1"
            elif key == "rating":
                out["rating"] = max(TINY, float(val) / 100.0)
            elif key == "use":
                use = int(val)
            elif key == "profile":
                name, *pairs = val.split("|")
                w = {}
                for p in pairs:
                    k, _, pct = p.partition("=")
                    w[k] = max(TINY, float(pct) / 100.0)
                profiles.append((name, w))
        except ValueError:
            continue
    if 1 <= use <= len(profiles):
        out["name"], out["weights"] = profiles[use - 1]
    return out


def load(logs=LOGS):
    try:
        d = json.load(open(os.path.join(logs, STATE), encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return dict(skill=float(d.get("skill", 1.0)), applied=d.get("applied", []), games=d.get("games", []),
                excluded=d.get("excluded", []))      # (games taken out by hand, and why: kept for the record)


def save(state, logs=LOGS):
    tmp = os.path.join(logs, f"{STATE}.{os.getpid()}.tmp")   # (its own: the panel's refresh and a match start may overlap)
    json.dump(state, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, os.path.join(logs, STATE))


def read_report(path):
    """[players] from MCC's carnage report: each {name, xuid, team, kills, deaths, seconds, completed}."""
    text = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for tag in re.findall(r"<Player [^>]*>", text):
        a = dict(re.findall(r'(\w+)="([^"]*)"', tag))
        out.append(dict(name=a.get("mGamertagText", ""), xuid=a.get("mXboxUserId", ""), team=int(a.get("mTeamId", -1)),
                        kills=int(a.get("mKills", 0)), deaths=int(a.get("mDeaths", 0)),
                        seconds=int(a.get("mSecondsPlayed", 0)), completed=a.get("mCompletedGame") == "1"))
    return out


def person_kd(report):
    """(kills, deaths) of the one person in a game, or None when the game does not count."""
    people = [p for p in read_report(report) if not p["xuid"].upper().startswith(BOT_ID.upper())]
    if len(people) != 1:
        return None
    me = people[0]
    if not me["completed"] or me["seconds"] < 120 or me["kills"] + me["deaths"] < MIN_FIGHTS:
        return None
    return me["kills"], me["deaths"]


def skill_played(trace):
    """The rating the bots had in that match (live_bots writes {"scaling": rating} first), None if not on Scaling."""
    try:
        with open(trace, encoding="utf-8", errors="replace") as f:
            for _ in range(200):
                line = f.readline()
                if not line:
                    break
                if line.startswith('{"t": ') and '"scaling"' in line:
                    v = json.loads(line).get("scaling")
                    return float(v) if isinstance(v, (int, float)) else None
    except (OSError, ValueError):
        pass
    return None


def games_window(ini):
    """N, the games averaged: botcore.ini's scale_games= (the panel's choice), else GAMES."""
    try:
        for line in open(ini, encoding="utf-8", errors="replace"):
            if line.startswith("scale_games="):
                return max(1, min(MAX_GAMES, int(line.split("=", 1)[1])))
    except (OSError, ValueError):
        pass
    return GAMES


def next_skill(games, n=GAMES):
    """The geometric mean of what the bots played at (MAX at most) x his K/D over the last n games, newest weighted
    most, MAX at most; 100% with none."""
    last = games[-n:]
    if not last:
        return 1.0
    w = range(1, len(last) + 1)
    logs = [math.log(level(g["skill"]) * max(g["kills"], 0.5) / max(1, g["deaths"])) for g in last]
    return min(MAX, math.exp(sum(k * x for k, x in zip(w, logs)) / sum(w)))


def update(logs=LOGS, n=GAMES, cfg=None):
    """Count every Scaling game finished since the last update and set the rating from the last n; returns the state,
    "play" the rating the bots play at: that one, or the locked one (cfg = settings(): the lock never touches the
    games' rating, it comes back on unlocking)."""
    st = load(logs)
    for rep in sorted(glob.glob(os.path.join(logs, "trace_*.carnage.xml")), key=os.path.getmtime):
        name = os.path.basename(rep)
        if name in st["applied"]:
            continue
        played = skill_played(rep[:-len(".carnage.xml")] + ".jsonl")
        if played is None:
            continue
        st["applied"].append(name)
        kd = person_kd(rep)
        if kd is not None:
            st["games"].append(dict(report=name, kills=kd[0], deaths=kd[1], skill=played))
    st["applied"], st["games"] = st["applied"][-50:], st["games"][-50:]
    cfg = cfg or dict(lock=False, rating=None, name="", weights={})
    st["skill"] = next_skill(st["games"], n)
    save(st, logs)
    st["play"] = (cfg["rating"] or st["skill"]) if cfg["lock"] else st["skill"]
    write_view(st, logs, cfg)
    return st


def pct(x):
    return f"{100 * x:.0f}%"


def view_lines(games, n, cfg, held=None):
    """The hover box for n games averaged: his K/D over them, the rating, and each setting's percentage of its
    baseline (game sense: of Legendary's) with its value (held: the locked rating)."""
    last = games[-n:]
    rating = held if held is not None else next_skill(games, n)
    kills, deaths = sum(g["kills"] for g in last), sum(g["deaths"] for g in last)
    out = [f"used|{len(last)}", f"kd|{kills / max(1, deaths):.2f}" if last else "kd|-", f"skill|{pct(rating)}{' (max)' if rating >= MAX else ''}"]
    v = values(rating, cfg["weights"])
    for key, label, base in PARAMS:
        k = next(iter(base))
        r = level(rating, cfg["weights"].get(key, 1.0))
        if k == "turn":
            r = v[k] / TURN
        elif k in SENSE:
            r = max(1.0, r / LEGEND)
        elif k in FLOORS:
            r = base[k] / v[k]
        shown = (f"{math.degrees(v[k]):.0f} deg/s" if k == "turn" else f"{1000 * v[k]:.2f} mrad" if k == "aim_err" else
                 f"{100 * v[k]:.0f}%" if k in MISSES or k == "overshoot" else f"{v[k]:.1f} deg" if k == "ram_err" else
                 f"{v[k]:.2f}x" if k == "flick" else f"{v[k]:.0f} s" if k == "memory" else
                 f"{v[k]:.1f} shots" if k == "dry_shots" else f"{1000 * v[k]:.0f} ms")
        out.append(f"row|{label}|{pct(r)}|{shown}")
    return out


def write_view(st, logs=LOGS, cfg=None):
    """logs/scaling_view.txt for the BOTS panel: "games|<Scaling games recorded>", "lock|0|1", "profile|<name>", then
    for each n 1..MAX_GAMES a "[n]" block of view_lines."""
    cfg = cfg or dict(lock=False, rating=None, name="", weights={})
    held = st.get("play", st["skill"]) if cfg["lock"] else None
    lines = [f"games|{len(st['games'])}", f"lock|{int(cfg['lock'])}", f"profile|{cfg['name']}"]
    for n in range(1, MAX_GAMES + 1):
        lines += [f"[{n}]"] + view_lines(st["games"], n, cfg, held)
    tmp = os.path.join(logs, f"{VIEW}.{os.getpid()}.tmp")
    open(tmp, "w", encoding="utf-8", newline="").write(chr(10).join(lines) + chr(10))   # (LF only: the panel reads it)
    os.replace(tmp, os.path.join(logs, VIEW))


def profile(rating, personality, rng, weights=None):
    """A bot at this rating: Legendary's behaviour, the rated settings from values() (each value jittered +-10%, as
    make_profile does); the brain's tier-table settings ride in profile.extra."""
    vals = {k: v * rng.uniform(0.9, 1.1) for k, v in {**TIERS["top"], **CRAFT["top"], **values(rating, weights),
                                                      **PERSONALITIES[personality]}.items()}
    extra = {k: vals.pop(k) for k in EXTRA}
    return Profile(tier="top", personality=personality, **vals, extra=extra)


def summary(rating, weights=None):
    v = values(rating, weights)
    return (f"skill rating {pct(rating)}: reaction {1000 * v['reaction']:.0f} ms, aim error {1000 * v['aim_err']:.2f} "
            f"mrad, turn {math.degrees(v['turn']):.0f} deg/s, headshots {pct(v['head_aim'])}, memory {v['memory']:.0f} s")
