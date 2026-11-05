"""The bots' own looks. native/bin/bot_profiles.ini holds this install's 15 bots (bot=<name>,<seed>), made on first use.
A bot's look in a game comes from its seed alone, so it is the same every match; a name that is not one of the 15 (a
bot renamed in the BOTS panel) gets a seed from its name.

maps/_looks/<game>.json says which bytes of that game's player configuration hold what (decoded per game,
tools/look_probe.py): {"fields": [{"name", "at": config offset, "count": n | "values": [...], "when": {field:
value}}], "how": "..."}. A game with no file keeps the copy of the player's look (botcore's old behaviour)."""
import json
import os
import random
import zlib

from . import armory
from .names import make_names

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES = os.path.join(ROOT, "native", "bin", "bot_profiles.ini")
LOOKS = os.path.join(ROOT, "maps", "_looks")
COUNT = 15


# clan tags (4 characters at most, as MCC shows them): Halo and Xbox 360 era. native/bots_panel.cpp CLAN_TAGS is the
# same list in the same order (tools/test_looks.py checks)
CLAN_TAGS = [
    "ODST", "TBK", "EVO", "NV", "GG", "HAVK", "SPRT", "R3D", "UNSC", "OGs", "FFA", "PRO", "MLG", "ELTE", "GRNT",
    "SKL", "X7", "VX", "117", "BRT", "ONI", "NOBL", "SIX", "MJLR", "CORT", "ARBY", "JKAL", "HNTR", "FLOD", "SNTL",
    "BNSH", "WRTH", "HOG", "GHST", "PELI", "SCRB", "SPNK", "MNGS", "HORN", "ELPH", "MNTR", "343", "BNGE", "HCS", "RROD",
    "XBL", "LIVE", "GOLD", "360", "LAN", "SPLT", "BNET", "GS", "ACHV", "PWND", "N00B", "LAG", "TBAG", "NADE", "STKY",
    "SNPR", "SWAT", "CTF", "KOTH", "ODDB", "JUGG", "INFX", "VIP", "BTB", "REKT", "FRAG", "SWRD", "BR55", "DMR", "MA5",
    "M6D", "NDLR", "CARB", "EMP", "OVR", "CAMO", "BUBL", "LZR", "RKT", "SPKR", "PPST", "FUEL", "GRAV", "HLJM", "S3",
    "SPII", "POA", "INF", "NMPD", "BUCK", "DTCH", "RMEO", "ROOK", "MCKY", "SGT", "JHNS", "KAT", "EMIL", "JUN", "JRGE",
    "CRTR", "KEYS", "RTAS", "SANG", "KIG", "YANM", "COVN", "BRUT", "GRNY", "PROP", "FORR", "HALO", "ARK", "REQ", "BGLC",
    "LCKT", "GRDN", "PIT", "NRWS", "VLHL", "SNWB", "HMRG", "ZBAR", "IVRY", "MDTR", "LSTN", "HGND", "CNST", "SWMP", "OBRN",
    "WARL", "AFTR", "SWRM", "TOP", "ACE", "KOS", "DOA", "AIM", "HDSH", "NSCP", "QSCP", "WAVE", "DUAL", "BXR", "DBLK",
    "TRPL", "OVKL", "KLTX", "KLPC", "RAMP", "LEGD", "HERO", "RECN", "EOD", "CQB", "EVA", "SCUT", "MKV", "MKVI", "HYBS",
    "KTNA", "RGUE", "SCTY", "JFO", "GUNG", "PLSM", "SHDE", "WRTN", "PWN", "SKLZ", "LGND", "MYTH", "IRON", "KILL", "BOOM",
    "PEW", "LOL", "OMG", "LEET", "1337", "H4X", "UBER", "EPIC", "FAIL", "BRB", "AFK", "OP", "DLC", "RVB", "CHF",
    "ARB", "SPRK", "GLTY", "MJ", "BLUE", "RED", "ASLT", "TERR", "HDHT", "GRFB", "RICO", "DOMN", "SPAR", "FIRE", "ICE",
    "VOID", "APEX", "ZERO", "NOVA", "OMEN", "WOLF", "VPR", "HAWK", "RAVN", "GRIM", "REAP", "SHDW", "STLH", "RAID", "WAR",
    "SOS", "TEAM", "CLAN", "SQD", "ARMY", "NAVY", "MRNE", "HELO", "PLT", "RKTS", "SNPZ", "NDLZ", "BRS", "DMRS", "ARS",
    "SMG", "SPEC", "SPTN", "IV", "III", "II", "REB", "OUT", "XB1", "XBX", "PAD", "SKRT", "TKO", "KO", "HAX",
    "MOD", "GLHF", "GGWP", "EZ", "NOPE", "YOLO", "SWAG", "BRUH", "MLG4", "PROZ", "OGZ", "KNG", "QUEN", "ROYL", "DYN",
    "VNGD", "AXIS", "ALFA", "BRVO", "CHRL", "ECHO", "FXTR", "GOLF", "HTL", "INDA", "JLT", "KILO", "LIMA", "MIKE", "OSCR",
    "PAPA", "QBC", "ROMO", "SRRA", "TNGO", "UNI", "VCTR", "WSKY", "XRAY", "YNKE", "ZULU", "ODS", "SPRC", "CRTX", "FRGE",
    "THTR", "FILM", "SHOT", "CLIP", "MNTG", "TBG", "NADZ", "PLZ", "SRSL", "COOP", "LGDY", "SKUL", "IWHB", "GRUN", "TILT",
    "MYTC", "CTCH", "FAMN", "TOUG", "BLND", "BLCK", "COWB", "BLPF",
]


assert len(set(CLAN_TAGS)) == len(CLAN_TAGS) and all(1 < len(t) <= 4 for t in CLAN_TAGS)


def make_clan(rng):
    """A clan tag as native/bots_panel.cpp made_clan draws one: a whole tag 2 times in 3, else 2-4 random characters."""
    if rng.random() < 2 / 3:
        return rng.choice(CLAN_TAGS)
    return "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(rng.randint(2, 4)))


# how many bots wear an armor effect, by the re-roll's choice. The shares are my picks, not measured from real
# lobbies
EFFECT_CHANCE = {"none": 0.0, "rare": 0.10, "common": 0.33, "frequent": 0.66}


def read_profiles(path=PROFILES):
    """(bots [(name, seed, clan)], settings {"experience": "original" | "modern", "effects": EFFECT_CHANCE key,
    "species": "spartans" | "mixed" | "elites", "elites": percent or None}) from bot_profiles.ini: lines experience=,
    effects=, species=, elites= (the Settings tab's re-roll, native/bots_panel.cpp) and bot=<name>,<seed>[,<clan>];
    a file from before the re-roll has no settings: Original, no effects, each game's own Spartan / Elite mix. The
    first re-roll build wrote effects=0 / 1: none / common."""
    bots, settings = [], {"experience": "original", "effects": "none", "species": "mixed", "elites": None}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line.startswith("experience="):
                settings["experience"] = "modern" if line[11:].lower() == "modern" else "original"
            elif line.startswith("effects="):
                v = line[8:].lower()
                settings["effects"] = v if v in EFFECT_CHANCE else ("none" if v in ("", "0") else "common")
            elif line.startswith("species="):
                v = line[8:].lower()
                settings["species"] = v if v in ("spartans", "mixed", "elites") else "mixed"
            elif line.startswith("elites=") and line[7:].isdigit():
                settings["elites"] = min(100, int(line[7:]))
            elif line.startswith("bot="):
                parts = line[4:].split(",")
                if len(parts) >= 2 and parts[0] and parts[1].isdigit():
                    bots.append((parts[0], int(parts[1]), parts[2] if len(parts) > 2 else ""))
    return bots, settings


def overrides_of(name, path=PROFILES):
    """{"<game>.<field>": int}: what the player set by hand in the Settings tab's bot editor (native/bots_panel.cpp),
    the 4th field of the bot's line: bot=<name>,<seed>,<clan>,h3.model=1;h3.primary=4;reach.seed=2. "<game>.seed"
    gives a game a new random look (a salt on the roll); "<game>.species" is the preferred species (0 Spartan, 1
    Elite) where the game has the choice."""
    if not os.path.exists(path):
        return {}
    for line in open(path, encoding="utf-8"):
        parts = line.strip()[4:].split(",", 3) if line.startswith("bot=") else []
        if len(parts) == 4 and parts[0].lower() == name.lower():
            out = {}
            for kv in parts[3].split(";"):
                k, _, v = kv.partition("=")
                if k and v.lstrip("-").isdigit():
                    out[k.strip()] = int(v)
            return out
    return {}


def profiles(path=PROFILES, n=COUNT):
    """[(name, seed)]: this install's bots, drawn once (the first call makes the file, as the re-roll writes it)."""
    bots, _ = read_profiles(path)
    if bots:
        return [(b[0], b[1]) for b in bots]
    rng = random.Random()
    clans = [make_clan(rng) for _ in range(rng.randint(2, 3))]   # two or three, each shared by a few of the 15
    out = [(name, rng.randrange(1, 2 ** 31), rng.choice(clans) if rng.random() < 0.55 else "") for name in make_names(n, rng)]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)     # (a fresh copy has no native/bin until the build)
    with open(path, "w", encoding="utf-8") as f:
        f.write("; this install's bots (brain/looks.py, the Settings tab's re-roll): name, look seed, clan tag\n")
        f.write("experience=original\neffects=none\n")
        f.writelines(f"bot={name},{seed},{clan}\n" for name, seed, clan in out)
    return [(name, seed) for name, seed, _ in out]


def seed_of(name, path=PROFILES):
    for n, seed in profiles(path):
        if n.lower() == name.lower():
            return seed
    return zlib.crc32(name.lower().encode("utf-8")) or 1


def clan_of(name, path=PROFILES):
    """The bot's clan tag ("" in none or not one of the 15): MCC shows it for the bot (native/report.cpp)."""
    return next((c for n, _, c in read_profiles(path)[0] if n.lower() == name.lower()), "")


def emblem_of(name, path=PROFILES):
    """The bot's MCC emblem ids (brain/emblems.py, its profile view's picture): MCC shows it for the bot in every game's
    scoreboard and the post-game report (native/report.cpp). None without the catalog (MCC's default then)."""
    from . import emblems
    try:
        return emblems.ids(emblems.roll(seed_of(name, path)))
    except (OSError, ValueError):
        return None


def choices(spec):
    """The values a field spec allows: a list, or {"range": [lo, hi]} (both ends in)."""
    if isinstance(spec, dict):
        lo, hi = spec["range"]
        return list(range(lo, hi + 1))
    return list(spec)


def pick_field(f, rng, modern, wears):
    """One field's value (maps/_looks/<game>.json): "values" (+ "weights"), "range": [lo, hi], or "original" /
    "modern" (Original Experience: what the game shipped with; Modern: everything MCC adds). "effect": the values
    that are armor effects: a bot that wears one gets one of them, any other bot never does."""
    if "values" in f:
        vals, weights = list(f["values"]), f.get("weights")
    elif "range" in f:
        vals, weights = choices({"range": f["range"]}), None
    else:
        vals, weights = choices(f["modern"] if modern and "modern" in f else f["original"]), None
    every = f.get("effect", [])
    fx = [v for v in every if v in vals]  # (an effect the experience does not hold is never worn)
    if fx and wears:
        return rng.choice(fx)
    keep = [k for k, v in enumerate(vals) if v not in every]
    vals, weights = [vals[k] for k in keep], [weights[k] for k in keep] if weights else None
    return rng.choices(vals, weights)[0] if weights else rng.choice(vals)


def elite_share(settings):
    """The share of bots rolled Elite where a game has the choice: 0 Spartans only, 1 Elites only, the slider's share
    when mixed, None: each game's own (Halo 2 3 in 10, Halo 3, H2A and Reach 1 in 5)."""
    s = settings.get("species", "mixed")
    if s in ("spartans", "elites"):
        return 1.0 if s == "elites" else 0.0
    return settings["elites"] / 100.0 if settings.get("elites") is not None else None


def with_share(f, layout, share):
    """The species field rolled at that share (still one draw, so the fields after it keep theirs)."""
    if share is None or f["name"] != layout.get("species_field") or "values" not in f:
        return f
    return dict(f, values=[0, 1], weights=[1.0 - share, share])


def allowed(f, modern):
    """The values a field may hold in an experience: Original never holds a value only Modern lists."""
    if "count" in f:
        return set(range(f["count"]))
    if "values" in f:
        return set(f["values"])
    if "range" in f:
        return set(choices({"range": f["range"]}))
    return set(choices(f["modern"] if modern and "modern" in f else f["original"]))


def hand_ok(f, v, modern, picked):
    """Whether a value set by hand in the bot editor is worn: only where the experience allows it, so an Original bot
    never wears a Modern item set by hand under Modern, nor mixes a set the game shipped whole (H2A)."""
    s = f.get("original_same_as")
    return v in allowed(f, modern) and (modern or s not in picked or v == picked[s] + f.get("same_shift", 0))


def look(name, game, path=PROFILES, looks_dir=LOOKS, hand=True):
    """(offset, {byte from offset: value}) for botctl.add_bot (one 64-byte window of the configuration), ("roll",
    seed, slot mask, none mask) where the game picks the armor from its own Armory (Reach: maps/_looks/reach.json
    "roll"; "effects": the armor effect slots, each set to the game's none unless the bot is one of the share
    EFFECT_CHANCE[effects] that wears one), or None where the game's layout is not decoded yet (the bot keeps the
    copy of the player's look). hand=False: the roll alone (a "New look" kept, values set by hand left out)."""
    spec = os.path.join(looks_dir, game + ".json")
    if not os.path.exists(spec):
        return None
    layout = json.load(open(spec, encoding="utf-8"))
    _, settings = read_profiles(path)
    over = {k[len(game) + 1:]: v for k, v in overrides_of(name, path).items() if k.startswith(game + ".")}
    salt = over.pop("seed", 0)
    over = over if hand else {}
    rng = random.Random(f"{seed_of(name, path)}:{game}" + (f":{salt}" if salt else ""))
    if "species" in over and "species_field" in layout:   # the editor's species choice names the game's own field
        over.setdefault(layout["species_field"], over["species"])
    if "roll" in layout:                  # the same seed every match: the same armor
        seed, mask = rng.randrange(1, 2 ** 32), int(layout["roll"])
        fx = sum(1 << s for s in layout.get("effects", []))
        wears = rng.random() < EFFECT_CHANCE[settings["effects"]]
        if "effect_byte" in layout:       # Halo 4 / H2A: the effect is a value of its own, not a catalog slot
            eb = layout["effect_byte"]    # {"none": 0, "values": [...], "modern_only": bool}
            allowed = wears and (settings["experience"] == "modern" or not eb.get("modern_only"))
            effect = rng.choice(eb["values"]) if allowed else eb["none"]
            return "roll", seed, mask, 0, effect, roll_fields(layout, rng, settings["experience"] == "modern", wears, over, elite_share(settings))
        mask = (mask | fx) if wears else (mask & ~fx)
        return "roll", seed, mask, 0 if wears else fx, None, roll_fields(layout, rng, settings["experience"] == "modern", wears, over, elite_share(settings))
    out = roll_fields(layout, rng, settings["experience"] == "modern", rng.random() < EFFECT_CHANCE[settings["effects"]], over,
                      elite_share(settings))
    if not out:
        return None
    off = min(out)                        # botctl sends one window of 64 bytes from an offset
    if max(out) - off >= 64:
        raise ValueError(f"maps/_looks/{game}.json spans {max(out) - off + 1} bytes: one look holds 64")
    return off, {k - off: v for k, v in out.items()}


def roll_fields(layout, rng, modern, wears, over, share=None):
    """{configuration offset: value} for a layout's fields (maps/_looks/<game>.json), hand-set values kept."""
    picked, out = {}, {}
    for f in layout.get("fields", []):
        if any(picked.get(k) != v for k, v in f.get("when", {}).items()):
            continue
        if "mcc" in f:                    # Reach / Halo 4, Modern only: an MCC item the game's own Armory does not
            if modern and f["mcc"] and rng.random() < len(f["mcc"]) / (len(f["mcc"]) + f["catalog"]):   # hold, by
                out[f["at"]] = rng.choice(f["mcc"])                                         # its table index over
            if f["name"] in over and hand_ok(f, over[f["name"]], modern, picked):          # the roll; a piece set
                for at in [f["at"]] + f.get("also_at", []):                                 # by hand the same way
                    out[at] = over[f["name"]]                                                # (Reach's effect: 2 bytes)
            continue
        v = rng.randrange(f["count"]) if "count" in f else pick_field(with_share(f, layout, share), rng, modern, wears)
        if not modern and f.get("original_same_as") in picked:   # an original set worn whole (H2A's 2014 launch;
            v = picked[f["original_same_as"]] + f.get("same_shift", 0)   # its Elite's arms / legs number one lower)
        if f["name"] in over and hand_ok(f, over[f["name"]], modern, picked):   # set by hand in the bot editor:
            v = over[f["name"]]                                                  # kept where the experience allows
        picked[f["name"]] = v
        out[f["at"]] = v
    return out


def resolved(name, game, species=None, path=PROFILES, looks_dir=LOOKS, ignore_species=False, hand=True):
    """{field name: value} the bot wears in a game whose layout is decoded (the same roll as look(): hand-set values
    win), or None (no layout, or the game rolls from its own Armory: Reach, Halo 4). species: 0 / 1 shows the bot as
    that species instead of its own (the profile view's species button): the species field is forced and the rest
    rolled as they would be for it. hand=False: the roll alone (the view marks what was set by hand against it)."""
    spec = os.path.join(looks_dir, game + ".json")
    if not os.path.exists(spec):
        return None
    layout = json.load(open(spec, encoding="utf-8"))
    if "roll" in layout or "fields" not in layout:
        return None
    _, settings = read_profiles(path)
    over = {k[len(game) + 1:]: v for k, v in overrides_of(name, path).items() if k.startswith(game + ".")}
    salt = over.pop("seed", 0)
    rng = random.Random(f"{seed_of(name, path)}:{game}" + (f":{salt}" if salt else ""))
    sf = layout.get("species_field")
    if ignore_species:                    # as rolled: a hand-set species left out (the view's "its roll")
        over.pop("species", None)
        over.pop(sf, None)
    if "species" in over and sf:
        over.setdefault(sf, over["species"])
    if species is not None and sf:
        over[sf] = species
    modern, share = settings["experience"] == "modern", elite_share(settings)
    wears = rng.random() < EFFECT_CHANCE[settings["effects"]]
    picked = {}
    for f in layout["fields"]:
        if any(picked.get(k) != v for k, v in f.get("when", {}).items()):
            continue
        v = rng.randrange(f["count"]) if "count" in f else pick_field(with_share(f, layout, share), rng, modern, wears)
        if not modern and f.get("original_same_as") in picked:
            v = picked[f["original_same_as"]] + f.get("same_shift", 0)
        if f["name"] in over and (hand or f["name"] == sf) and hand_ok(f, over[f["name"]], modern, picked):
            v = over[f["name"]]
        picked[f["name"]] = v
    return picked


def reach_species(name, path=PROFILES, rolled=False):
    """The bot's preferred species in Halo: Reach (0 Spartan, 1 Elite): set by hand in the profile view, else rolled
    once from its seed, Elite 1 in 5 like Halo 3's model field. Reach custom games use it where players choose
    (Invasion and Elite game types decide for themselves). ponytail: not worn in game yet: Reach's species byte in
    the player configuration is not decoded (botcore copies the player's)"""
    over = None if rolled else overrides_of(name, path).get("reach.species")
    if over is not None:
        return over
    share = elite_share(read_profiles(path)[1])        # (the re-roll's Spartan / Elite share, else 1 in 5)
    return int(random.Random(f"{seed_of(name, path)}:reach:species").random() < (0.2 if share is None else share))


def armory_view(name, game, path=PROFILES, looks_dir=LOOKS):
    """The profile view's lines for a game whose armor botcore rolls from the game's own Armory (export_view): Reach's
    preferred species, then the other one (Invasion); Halo 4's Spartan. Each with its colours, visor tint, body (Reach:
    0 male, 1 female; the roll, the view lays a hand-set one over it) and pieces, the model's region:permutation list it
    wears: botcore's roll worked out offline (brain/armory.py), the body as worn (a hand-set one too, so the view shows
    it). No pieces where the roll's are not known (Halo 4's variants botcore has not logged yet: the view keeps the
    logo)."""
    reach = game == "reach"
    sp, rolled = (reach_species(name, path), reach_species(name, path, True)) if reach else (0, 0)
    head = [f"species={s};rolled_species={rolled}" for s in (sp, 1 - sp)] if reach else [""]
    t = armory.table(os.path.join(looks_dir, game + "_armory.json"))
    lk, roll = look(name, game, path, looks_dir), look(name, game, path, looks_dir, hand=False)
    if t is None or not lk or lk[0] != "roll":
        return head[:1] if reach else []
    layout = json.load(open(os.path.join(looks_dir, game + ".json"), encoding="utf-8"))
    at = {f["at"]: f["name"] for f in layout["fields"]}
    vals = {at[k]: v for k, v in roll[5].items() if k in at and at[k] != "visor"}
    app = armory.appearance(armory.roll(*lk[1:4], t["catalog"]), t)
    for f in layout["fields"]:            # each armor slot's rolled piece (the editor names its roll), MCC's over it
        if "catalog" in f and f["name"] not in ("visor", "gender") and f["name"] not in vals and app is not None:
            if f["at"] - 0x20 in app:
                vals[f["name"]] = app[f["at"] - 0x20]
    if "effect_byte" in layout and len(roll) > 4 and roll[4] is not None:   # Halo 4: its own effect byte's roll
        vals["armor_effect"] = roll[4]
    over = {k - 0x20: v for k, v in lk[5].items() if k >= 0x20}   # the bytes laid over the roll (an MCC item by its
    if app is not None:                                            # table index, the body, the colours, Halo 4's visor)
        app.update(over)
    worn = {at[k]: v for k, v in lk[5].items() if k in at}
    body = lambda s: "elite" if s else "female" if worn.get("gender") == 1 else "male"
    common = "".join(f";{k}={v}" for k, v in vals.items()) + f";visor={(app or over).get(0x2B, 0)}"
    return [(h + common).lstrip(";") + (";pieces=" + ",".join(f"{r}:{p}" for r, p in armory.pieces(app, body(s), t))
                                        if app is not None else "")
            for h, s in zip(head, (sp, 1 - sp))]


def table_pieces(name, game, species=None, path=PROFILES, looks_dir=LOOKS):
    """";pieces=region:permutation,..." a decoded look wears by its game's customization table (Halo 3, H2A: their bytes
    are the table's values, maps/_looks/<game>_armory.json), the hand-set values in (the view shows what the bot wears;
    species as resolved()), or "" for a game without a table."""
    t = armory.table(os.path.join(looks_dir, game + "_armory.json"))
    if t is None:
        return ""
    layout = json.load(open(os.path.join(looks_dir, game + ".json"), encoding="utf-8"))
    at = {f["name"]: f["at"] for f in layout["fields"]}
    worn = resolved(name, game, species, path, looks_dir)
    app = {at[k] - 0x20: v for k, v in worn.items() if k in at}   # (a later field over an earlier one's byte)
    body = "elite" if worn.get(layout.get("species_field")) else "male"
    return ";pieces=" + ",".join(f"{r}:{p}" for r, p in armory.pieces(app, body, t))


VIEW = os.path.join(ROOT, "native", "bin", "bot_looks.ini")
VIEW_GAMES = ("ce", "h2", "h3", "h2a")


def export_view(path=PROFILES, out=VIEW, looks_dir=LOOKS):
    """What the Settings tab's profile view shows (native/bots_panel.cpp reads it): each bot's look as rolled, per
    game, and in the games with a species choice the look as the other species too (its preferred one first). Lines:
    <name>|<game>|<view>|field=value... with view "own" (its preferred species) or "other"; Halo 3, Reach, H2A and
    Halo 4 end with pieces=region:permutation... (the 3D model's pieces it wears: table_pieces, armory_view).
    Written by botcore (tools/looks_export.py) when the profiles change, so the panel never shows "Random" for what
    the roll decided."""
    lines = ["; native/bin/bot_looks.ini: each bot's look as rolled (brain/looks.py export_view), for the profile view"]
    for name, _ in profiles(path):
        for game in VIEW_GAMES:
            # the roll alone, as the bot's preferred species (hand-set or rolled); the view lays hand-set values over it
            own = resolved(name, game, None, path, looks_dir, hand=False)
            if own is None:
                continue
            sf = json.load(open(os.path.join(looks_dir, game + ".json"), encoding="utf-8")).get("species_field")
            if sf and sf in own:                 # the species it rolled, before any hand-set one (the view's "its roll")
                rolled = resolved(name, game, None, path, looks_dir, ignore_species=True)[sf]
                own["rolled_species"] = int(rolled != 0)
            lines.append(f"{name}|{game}|own|" + ";".join(f"{k}={v}" for k, v in own.items())
                         + table_pieces(name, game, None, path, looks_dir))
            if sf and sf in own:
                other = resolved(name, game, 1 - int(own[sf] != 0), path, looks_dir, hand=False)
                lines.append(f"{name}|{game}|other|" + ";".join(f"{k}={v}" for k, v in other.items())
                             + table_pieces(name, game, 1 - int(own[sf] != 0), path, looks_dir))
        for game in ("reach", "h4"):          # (the games botcore rolls from their own Armory)
            views = zip(("own", "other"), armory_view(name, game, path, looks_dir))
            lines += [f"{name}|{game}|{view}|{kv}" for view, kv in views]
    try:                                      # each bot's own emblem picture (brain/emblems.py), for the same view
        from . import emblems
        emblems.export([(name, seed_of(name, path)) for name, _ in profiles(path)])
    except (OSError, ImportError, ValueError):
        pass                                  # (no emblem art extracted yet: the view shows none)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, out)                      # whole or not at all: the panel may read it any frame
    return len(lines) - 1


ORIGINAL = os.path.join(LOOKS, "original_content.json")


def original_items(game, slot, mode="strict", path=ORIGINAL):
    """The items of `slot` in `game` a bot may wear in `mode`, from maps/_looks/original_content.json (the player's
    list of each game's original customization, docs/research/13): "strict" = default + unlock, "exclusives" = adds
    promo / DLC and staff items, "mcc" = None (no filter: everything the game offers in MCC). A Reach helmet's
    attachment variants are items of their own, "Helmet / Variant". An item the mode leaves out falls back to the
    slot's default item (the first one)."""
    data = json.load(open(path, encoding="utf-8"))
    tags = data["modes"][mode]
    if tags is None:
        return None
    slots = data["games"][game]["slots"]
    s = slots[slot]
    s = slots.get(s.get("same_as"), s)
    out = []
    for it in s.get("items", []):
        if it.get("tag") in tags:
            out.append(it["name"])
            out += [f"{it['name']} / {v['name']}" for v in it.get("variants", []) if v.get("tag") in tags]
    return out


if __name__ == "__main__":
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "bot_profiles.ini")
    a = profiles(p)
    assert len(a) == COUNT and profiles(p) == a, "profiles not kept"
    bots, st = read_profiles(p)
    assert st == {"experience": "original", "effects": "none"} and all(clan_of(n, p) == c for n, _, c in bots)
    assert any(c for *_, c in bots) and all(2 <= len(c) <= 4 for *_, c in bots if c), "clan tags"
    os.makedirs(os.path.join(d, "looks"))
    json.dump({"fields": [{"name": "species", "at": 76, "values": [0, 1]},
                          {"name": "helmet", "at": 88, "count": 20, "when": {"species": 0}}]},
              open(os.path.join(d, "looks", "reach.json"), "w"))
    l1 = look(a[0][0], "reach", p, os.path.join(d, "looks"))
    assert l1 == look(a[0][0], "reach", p, os.path.join(d, "looks")), "a look changed between matches"
    assert look(a[0][0], "ce", p, os.path.join(d, "looks")) is None
    assert l1[0] == 76 and set(l1[1]) <= {0, 12}, f"window offset: {l1}"
    print("looks OK", a[:3], l1)
