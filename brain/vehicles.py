"""Every MCC game's vehicles for the brain.

Names are the maps' own (maps/<map>/objects.json "vehicles": CE paths, the other games' placement names; Halo 3 calls
the Elephant "behemoth", ODST's Olifaunt is "olifaunt"). Each kind:
  move    ground | air | hover (a Ghost, Wraith: ground rules) | none (turrets: a seat only)
  seats   in the order a player gets in when he presses the action key at that side of it: driver first (front,
          left), then the gun, then passengers; a turret's only seat is its gun
  gun     the seat that shoots: "driver" (Ghost, Banshee, Scorpion's main gun, Mongoose: none), "gunner"
          (Warthog, Elephant), None
  speed   world units a second at full throttle (rough: the brain plans trips with it)
  crew    seats worth filling before driving off (a Warthog waits for its gunner)
  value   how much a driver wants it (Scorpion, Wraith high; Mongoose low: fast, unarmed)
"""
import math

from .core import Vec, dist

VEHICLES = {
    "warthog":   dict(move="ground", seats=("driver", "gunner", "passenger"), gun="gunner", speed=11.0, crew=2, value=0.7),
    "rwarthog":  dict(move="ground", seats=("driver", "gunner", "passenger"), gun="gunner", speed=11.0, crew=2, value=0.75),
    "gauss":     dict(move="ground", seats=("driver", "gunner", "passenger"), gun="gunner", speed=11.0, crew=2, value=0.8),
    "mongoose":  dict(move="ground", seats=("driver", "passenger"), gun=None, speed=13.0, crew=1, value=0.35),
    "gungoose":  dict(move="ground", seats=("driver", "passenger"), gun="driver", speed=13.0, crew=1, value=0.5),
    "ghost":     dict(move="hover", seats=("driver",), gun="driver", speed=10.0, crew=1, value=0.6),
    "chopper":   dict(move="ground", seats=("driver",), gun="driver", speed=10.0, crew=1, value=0.6),
    "revenant":  dict(move="hover", seats=("driver", "passenger"), gun="driver", speed=9.0, crew=1, value=0.65),
    "spectre":   dict(move="hover", seats=("driver", "gunner", "passenger"), gun="gunner", speed=9.0, crew=2, value=0.65),
    "mantis":    dict(move="ground", seats=("driver",), gun="driver", speed=5.0, crew=1, value=0.85),
    "scorpion":  dict(move="ground", seats=("driver", "gunner"), gun="driver", speed=5.0, crew=1, value=0.95),
    "wraith":    dict(move="hover", seats=("driver", "gunner"), gun="driver", speed=5.0, crew=1, value=0.9),
    "banshee":   dict(move="air", seats=("driver",), gun="driver", speed=12.0, crew=1, value=0.8),
    "hornet":    dict(move="air", seats=("driver", "passenger", "passenger"), gun="driver", speed=11.0, crew=1, value=0.8),
    # vtol: climbs on its vertical input, not its pitch (Reach action +0x3C, decoded live: tools/falcon_probe.py)
    "falcon":    dict(move="air", seats=("driver", "gunner", "gunner"), gun="gunner", speed=11.0, crew=2, value=0.75,
                      vtol=True),
    # Halo 3's Brute Prowler (Forge only): driver, turret gunner, two riders with their own guns (guide 17)
    "prowler":   dict(move="hover", seats=("driver", "gunner", "passenger", "passenger"), gun="gunner", speed=9.0,
                      crew=2, value=0.6),
    # Reach's MCC Forge fighters (Forge World, Tempest): one pilot, its own guns
    "sabre":     dict(move="air", seats=("driver",), gun="driver", speed=20.0, crew=1, value=0.9),
    "seraph":    dict(move="air", seats=("driver",), gun="driver", speed=20.0, crew=1, value=0.9),
    # Reach's Transport Hog: the Warthog body with a troop bed riding on it in place of a gun (TURRETS)
    "thog":      dict(move="ground", seats=("driver", "passenger", "passenger", "passenger"), gun=None, speed=11.0,
                      crew=1, value=0.5),
    "elephant":  dict(move="ground", seats=("driver", "gunner", "gunner", "passenger", "passenger"), gun="gunner",
                      speed=3.0, crew=2, value=0.5),
    "olifaunt":  dict(move="ground", seats=("driver", "passenger"), gun=None, speed=4.0, crew=1, value=0.2),
    "turret":    dict(move="none", seats=("gunner",), gun="gunner", speed=0.0, crew=1, value=0.6),
}
# what a gunner's seat shoots, as the hand gun with the same flight (brain/bot.py PROJECTILE_SPEED, SPLASH): its lead and
# where it aims come from this, not from the gun the gunner holds (a rocket in his hands led a chaingun 30 times too far)
GUNNER_GUN = {"warthog": "assault_rifle", "gauss": "sniper", "rwarthog": "rockets", "falcon": "assault_rifle",
              "elephant": "assault_rifle", "spectre": "plasma_rifle", "scorpion": "assault_rifle",
              "wraith": "plasma_rifle", "turret": "assault_rifle", "prowler": "plasma_rifle"}
# Reach builds its variants from one body and the gun riding on it, a vehicle of its own (maps/_shapes/reach_seats.json):
# the turret's name -> (the variant's kind, what that gun shoots as above). The Falcon's guns hang on its sides (which
# side a gunner sits on: Bot.drive keeps that side to the target); the chin gun, the Forge nose-gun variant's only, is
# the pilot's (in Reach multiplayer the Falcon has none: docs/research/17-vehicle-tactics-guide.md, REACH-PUR-03)
TURRETS = (("warthog_gauss", "gauss", "sniper"), ("warthog_rocket", "rwarthog", "rockets"),
           ("warthog_troop", "thog", None), ("warthog_chaingun", "warthog", "assault_rifle"),
           ("falcon_side_grenade", "falcon", "grenade_launcher"), ("falcon_side_gun", "falcon", "assault_rifle"),
           ("scorpion_anti_infantry", "scorpion", "assault_rifle"), ("wraith_anti_infantry", "wraith", "plasma_rifle"))
# How each kind is fought by its driver (docs/research/16-vehicle-roles.md): role "strafe" (gun runs side on, never
# parked), "artillery" (holds its range, keeps moving, backs off boarders), "circle" (round the fight so its gunner
# works: Bot.drive), "air" (attack runs low, travels high), "transport"; rng: the driver's fighting range (u); gun:
# what the driver's own gun throws, for the aim's lead (brain/bot.py PROJECTILE_SPEED: a mortar's slow shot, a tank
# shell); splatter: it runs down a man on foot who has nothing that kills vehicles
STRATEGY = {
    # (the player's driving match 221404, 234 s with a bot gunner: the nearest enemy 3.6-13.9 u for 80% of the fight,
    # median 7.8 u, side on 58%, 5.8 u/s; at 12-25 u the bots turned away from every man under 12 u)
    "warthog":  dict(role="circle", rng=(3.5, 14.0), splatter=True),
    # (no runs: "not a ram vehicle ... ramming infantry wastes its main weapon", guide 17 CE / Reach rocket hog)
    "rwarthog": dict(role="circle", rng=(15.0, 30.0)),
    "gauss":    dict(role="circle", rng=(15.0, 35.0), splatter=True),
    "mongoose": dict(role="transport", rng=(0.0, 0.0), splatter=True),
    "gungoose": dict(role="strafe", rng=(8.0, 20.0), splatter=True),
    "ghost":    dict(role="strafe", rng=(8.0, 22.0), gun="plasma_rifle", splatter=True),
    # (its guns fire where it points: "charge", straight at him with the boost close in; a skilled player's,
    # Bot.ram_boost)
    "chopper":  dict(role="charge", rng=(6.0, 18.0), splatter=True),
    "revenant": dict(role="artillery", rng=(10.0, 30.0), gun="fuelrod", splatter=True),
    "spectre":  dict(role="circle", rng=(12.0, 25.0), splatter=True),
    "mantis":   dict(role="strafe", rng=(8.0, 30.0)),
    "scorpion": dict(role="artillery", rng=(15.0, 45.0), gun="tank_shell"),
    "wraith":   dict(role="artillery", rng=(15.0, 40.0), gun="mortar"),
    "banshee":  dict(role="air", rng=(10.0, 40.0), gun="plasma_rifle"),
    "hornet":   dict(role="air", rng=(10.0, 40.0)),
    # (its side guns' reach, about a chaingun's: guide 17 §4.1, 40 m = 13 u; was 15-30 u)
    "falcon":   dict(role="circle", rng=(8.0, 18.0)),
    "elephant": dict(role="circle", rng=(15.0, 40.0)),
    "olifaunt": dict(role="transport", rng=(0.0, 0.0)),
    "thog":     dict(role="transport", rng=(0.0, 0.0)),     # ("do not ram ... a flipped Transport Hog loses its passengers")
    "prowler":  dict(role="circle", rng=(10.0, 25.0), splatter=True),   # ("splatters infantry at speed like a Warthog")
    "sabre":    dict(role="air", rng=(15.0, 50.0), gun="assault_rifle"),   # (auto cannons: a bullet's flight)
    # ponytail: the Seraph's fuel rods fly at a speed no tag gave us yet: led as hitscan
    "seraph":   dict(role="air", rng=(15.0, 50.0)),
}
# Ramming (guide 17 §4.3, Halo 2 on: H3's collision damage, H2's head-on Warthog kills a Ghost): the light vehicles each
# kind runs into head on; nobody rams a Scorpion, Wraith, Elephant or Mantis. RAM_THETA: degrees off its nose a target
# may be for a vehicle with its own gun to commit to a run (narrower = worse steering); others 15
RAM_VEHICLES = {"warthog": {"ghost", "mongoose", "prowler", "gungoose"}, "gauss": {"ghost", "mongoose", "prowler", "gungoose"},
                "chopper": {"ghost", "mongoose", "prowler", "gungoose", "warthog", "gauss", "rwarthog", "thog", "chopper",
                            "hornet"}}
RAM_THETA = {"warthog": 20.0, "gauss": 20.0, "ghost": 12.0, "chopper": 8.0, "mongoose": 15.0}
BOARD_D = 6.0        # a man this close to a tank or a Wraith can board it (research: boarders, EMP): back off
# What each kind is for when a team picks its vehicles (guide 17 §4.7: one anti-air, one anti-vehicle, one transport,
# then harassers; the Falcon, Chopper and Mongoose fill either of two). The kinds §4.7 leaves out, by their profiles:
# the Revenant and Mantis assault guns, the Spectre and Elephant carriers, the Gungoose a harasser
ROLES = {"banshee": ("anti_air",), "hornet": ("anti_air",), "falcon": ("anti_air", "transport"),
         "rwarthog": ("anti_air",), "gauss": ("anti_vehicle",), "scorpion": ("anti_vehicle",),
         "wraith": ("anti_vehicle",), "chopper": ("anti_vehicle", "harasser"), "mantis": ("anti_vehicle",),
         "revenant": ("anti_vehicle",), "warthog": ("transport",), "thog": ("transport",),
         "mongoose": ("transport",), "spectre": ("transport",), "elephant": ("transport",),
         "prowler": ("transport",), "ghost": ("harasser",), "gungoose": ("harasser",), "sabre": ("anti_air",),
         "seraph": ("anti_air",)}
ROLE_ORDER = ("anti_air", "anti_vehicle", "transport", "harasser")
# objective modes bias the order (§4.7): carrying games want the transport first, hill games the anti-vehicle gun
ROLE_FIRST = {"ctf": "transport", "assault": "transport", "king": "anti_vehicle", "territories": "anti_vehicle"}


# Target scoring (guide 17 §4.2): seconds for each vehicle gun to kill each target (Reach's tags: §2's TTK matrix, its
# Spartan table for a man on foot). The other games' tags are not extracted (§1, §5): Reach's ratios stand in ("treat
# the ratios as reliable"). cannon: the Scorpion's shell and the Wraith's mortar
_COLS = ("mongoose", "ghost", "banshee", "revenant", "warthog", "falcon", "scorpion", "wraith", "infantry")
TTK = {g: dict(zip(_COLS, row)) for g, row in {
    "chaingun":        (3.6, 3.2, 3.9, 4.8, 5.9, 5.9, 10.7, 10.7, 1.5),
    "coax":            (3.9, 3.4, 4.2, 5.1, 6.4, 6.4, 11.5, 11.5, 1.5),
    "ghost":           (6.7, 6.0, 11.1, 13.3, 16.7, 16.7, 40.0, 40.0, 2.7),
    "banshee":         (3.4, 3.0, 5.5, 6.7, 8.4, 8.4, 20.0, 20.0, 1.4),
    "wraith_ai":       (3.8, 3.5, 6.4, 7.7, 9.6, 9.6, 23.1, 23.1, 1.5),
    "gauss":           (1.6, 1.6, 1.6, 2.4, 2.4, 2.4, 4.0, 4.0, 0.8),
    "rocket_hog":      (2.0, 2.0, 2.0, 2.0, 4.0, 4.0, 6.0, 6.0, 2.0),
    "revenant_mortar": (6.0, 6.0, 7.5, 9.0, 10.5, 10.5, 16.5, 16.5, 3.0),
    "cannon":          (3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 6.0, 6.0, 3.0)}.items()}
# a kind the matrix has no column for -> the column it is fought as (the Chopper "tougher than a Ghost, well below a
# tank"; a turret's gunner sits in the open); None: it cannot be destroyed (its crew is the target: infantry)
TARGET_COL = {"gungoose": "mongoose", "chopper": "revenant", "spectre": "revenant", "prowler": "revenant",
              "hornet": "falcon", "gauss": "warthog", "rwarthog": "warthog", "thog": "warthog", "mantis": "scorpion",
              "sabre": "banshee", "seraph": "banshee", "turret": "infantry", "elephant": None, "olifaunt": None}
# the gun each kind's shooting seat fires (a pair: the driver's, the gunner's)
SEAT_GUN = {"warthog": "chaingun", "gauss": "gauss", "rwarthog": "rocket_hog", "falcon": "chaingun",
            "elephant": "chaingun", "turret": "chaingun", "spectre": "wraith_ai", "prowler": "wraith_ai",
            "scorpion": ("cannon", "coax"), "wraith": ("cannon", "wraith_ai"), "ghost": "ghost", "banshee": "banshee",
            "chopper": "coax", "revenant": "revenant_mortar", "hornet": "chaingun", "gungoose": "chaingun",
            "mantis": "chaingun", "sabre": "chaingun", "seraph": "cannon"}
# §4.2 base_threat (the kinds it leaves out by their nearest listed one); a man on foot 0.3, with a vehicle killer 0.9
BASE_THREAT = {"banshee": 1.0, "sabre": 1.0, "seraph": 1.0, "hornet": 0.9, "falcon": 0.9, "scorpion": 1.0,
               "wraith": 1.0, "mantis": 1.0, "gauss": 0.9, "chopper": 0.8, "warthog": 0.7, "rwarthog": 0.7,
               "thog": 0.5, "elephant": 0.5, "revenant": 0.6, "spectre": 0.6, "prowler": 0.6, "ghost": 0.5,
               "gungoose": 0.4, "mongoose": 0.3}
TANKS = {"scorpion", "wraith", "mantis"}
# boosted into a man close ahead (Bot.ram_boost), the Wraith's boosters are "mainly for splattering opponents"
BOOSTS = {"ghost", "chopper", "revenant", "wraith"}
# Boosting to get somewhere (Bot.travel_boost, the Revenant's "for getting from a to b quicker", the Banshee; the
# Wraith's "not too efficiently": none), held and let go as he did: his right-button holds on Forge World
# (logs/tmp/key_holds.py), the median hold and the median gap after it, s. The Seraph as the Sabre; the Sabre's
# whole tank lasted 15-16 s, three drains (2575-2637 s)
TRAVEL_BOOST = {"ghost": (1.7, 3.6), "revenant": (3.2, 5.0), "banshee": (2.4, 3.9), "sabre": (2.45, 5.4),
                "seraph": (2.45, 5.4)}
# How far the player keeps an aircraft from anything it could hit (tools/vehicle_clearance.py over recorded Forge World
# flights, maps/_vehicles/clearance_reach_forge.json; 10th percentiles while moving): near, the nearest solid thing
# round it (u; his Falcon note at 727.5 s, came after passes 4.0 u off); ttc, the seconds of flight ahead he keeps open
# (what is clear along where it goes over its speed; the Sabre never had anything inside his 60 u probe: 60 u at its
# median 20.6 u/s); over, its height over the floor under it (u); travel, his median height (Bot.drive flies at it
# where no flying is learned on the map). Bot.air_guard looks ttc ahead and keeps near and over. INFERRED: the Hornet
# as the Falcon (both hover on their lift), any other aircraft as the Banshee
CLEARANCE = {"banshee": dict(near=8.4, ttc=2.5, over=6.8, travel=14.8),
             "falcon": dict(near=4.6, ttc=1.8, over=4.7, travel=7.9),
             "hornet": dict(near=4.6, ttc=1.8, over=4.7, travel=7.9),
             "sabre": dict(near=25.0, ttc=3.0, over=18.5, travel=37.8),
             "seraph": dict(near=25.0, ttc=3.0, over=18.5, travel=37.8)}
# Where a player flew a map's aircraft, recorded for the bots to copy (a Forge run Nov 6 19:32, Island v704f87f3,
# logs/tmp/owner_flight.py, docs/research/flags_2026-11-06_evening.md section 4): the spire's axis (x, y); the
# highest flown ("ceiling", z); by height band (z from, z to, u) the nearest to the axis flown
# (the closest, 5.2-7 u under the top platform, 10 u level with the top and over it; at 17.5 u out the
# deck over the aircraft held it under z -31: the terrain's own probes keep that);
# "run_floor": the attack runs' lowest pull-out over the floor (4-9 u); the phase's bomb targets (z of the floor),
# Invasion phase 2's objective rooms at the spire's floor 2 lift entrances (the bomb runs aimed into those rooms).
# Air_guard: the ceiling; as far off the spire as it was flown at its height, the decks over it are no floor to climb
# to;
# runs pull out at run_floor. Replayed closed loop (tools/air_replay.py, live Spire 20261106-185412's Banshees):
# bot 14 runs 6 -> 8, cannon ticks 10 -> 147, in range 14% -> 42%; bot 7 in range 45% -> 61% (fire 119 -> 98); floor
# touches 1-2 as before. Its own clearances here (tools/vehicle_clearance.py, logs/tmp/clearance_spire_owner.json: a
# Banshee 4.6 u off anything, 1.64 s open ahead, 5.85 u over the floor) replayed worse (bot 14: 1 run, 0 shots): not used
AIR_ENVELOPE = {"reach_35_island": dict(axis=(-178.24, -405.33), ceiling=-17.2, run_floor=4.0,
                                        bands=((-80.0, -40.0, 5.5), (-40.0, -24.0, 7.0), (-24.0, -10.0, 9.4)),
                                        bombs={2: ((-171.92, -403.20, -58.76), (-178.12, -398.81, -58.76))})}


def envelope(map_name):
    """AIR_ENVELOPE for a map (its base map's for a variant: "reach_35_island/variants/..."), or None."""
    return AIR_ENVELOPE.get((map_name or "").split("/")[0].split("@")[0])


def envelope_min_r(env, z):
    """The nearest to the axis flown at height z (env bands), 0 outside them."""
    return next((r for z0, z1, r in env["bands"] if z0 <= z < z1), 0.0)


# How each takes off (his, logs/tmp/takeoffs.py): "up", straight up first, to the height given (u), then off (the
# Falcon "take off in falcon is upward, and then I take off, this is to avoid hitting any walls": 1.7-5.6 u up,
# moving off 4.5-11 s after getting in); "forward", it launches by itself, the nose up by the pitch given (rad) its
# first TAKE_OFF_S s and its heading the open air (the Banshee "automatically goes forward, so I have to pull up
# instantly": moving in 0.6 s, his nose 25-36 deg up; the Sabre and Seraph in 0.1 s, 1-13 deg up, "you must be
# absolutely clear before take off")
TAKE_OFF = {"falcon": ("up", 2.5), "hornet": ("up", 2.5), "banshee": ("forward", 0.5), "sabre": ("forward", 0.15),
            "seraph": ("forward", 0.15)}
TAKE_OFF_S = 2.0


def clearance(kind):
    """The aircraft's CLEARANCE (any other flyer: the Banshee's)."""
    return CLEARANCE.get(kind, CLEARANCE["banshee"])
# an enemy's ground vehicle a man on foot boards (Halo 2 on: Bot.board_check): hijacks, and the tanks' hulls
BOARDABLE = {"warthog", "gauss", "rwarthog", "thog", "mongoose", "gungoose", "ghost", "chopper", "revenant", "spectre",
             "prowler", "scorpion", "wraith"}
# A tank driver's view (a skilled player's shots Avalanche, logs/tmp/owner_rides.py, his pitch over the line from the
# vehicle to the man): (camera height over the vehicle, arc degrees per u of range, the arc's cap). The Scorpion's view
# is its camera's, about 2 u over the hull: his shots looked 9.6 / 5.7 / 4.6 / 3.4 deg under that line at 5 / 15 / 25 /
# 35 u (374 shots), as from 2 u up at the feet; the Wraith's mortar is lobbed over that, about 0.33 deg a u (+4.6 / +8.7
# / +15 deg at 15 / 25 / 55 u, 41 shots), up to 15 The Revenant (the player Forge World, Reach; logs/tmp/lob.py over his
# 103 shots): +9.0 deg over that line at 10-20 u (75 shots, quartiles +8.3 / +10.1), so 0.6 a u up to 9; his 9 shots
# past 20 u are too few to say more. (His Reach Wraith shots there, +6.1 deg at 10-20 u, 80 shots, agree with the
# Avalanche lob)
DRIVER_VIEW = {"scorpion": (2.0, 0.0, 0.0), "wraith": (2.0, 0.33, 15.0), "revenant": (2.0, 0.6, 9.0)}


def driver_view(kind, flat):
    """(camera height, lob in radians) a driver of this kind aims with at a man flat u away; (0, 0) for the rest."""
    cam, per_u, cap = DRIVER_VIEW.get(kind, (0.0, 0.0, 0.0))
    return cam, math.radians(min(cap, per_u * flat))


def seat_gun(kind, seat):
    """The TTK row of the gun this seat of this kind fires (None: the seat has none)."""
    g = SEAT_GUN.get(kind)
    if isinstance(g, tuple):
        return g[0] if seat == "driver" else g[1]
    s = VEHICLES.get(kind)
    return g if s is not None and (s["gun"] == seat or kind == "turret") else None


def target_score(game, shooter, gun, seat, target, killer=False, objective=1.0, off=None, up=0.0, moving=0.0,
                 d=10.0, in_ram=False):
    """guide 17 §4.2: base_threat x objective_weight x killability (1 / seconds to kill) x angle_factor, with each
    shooter's own preferences. shooter: our kind; gun: our seat's TTK row; target: his vehicle's kind (None: on foot);
    killer: he carries a vehicle killer; objective: 2.0 a carrier, 1.5 in the hill, 1.3 by our objective, else 1.0;
    off: radians off the nose of a gun that points where the vehicle does (None: a turret that turns); up: radians
    above us; moving: his speed (u/s); d: distance (u); in_ram: inside our run at him (Bot.ram_ok). 0: hold fire."""
    col = "infantry" if target is None or game == "ce" else TARGET_COL.get(target, target)   # (CE: vehicles never
    if col is None:                                                                         # die, their crews do)
        col = "infantry"
    base = (0.9 if killer else 0.3) if target is None else BASE_THREAT.get(target, 0.5)
    ttk = TTK.get(gun or "chaingun", TTK["chaingun"])
    score = base * objective / ttk.get(col, ttk["infantry"])
    if off is not None and off > 1.5708:
        score *= 0.5                               # a turn of more than 90 degrees first
    if (shooter in TANKS and seat == "driver" and up > 0.87) or (shooter == "chopper" and off is not None and off > 2.1):
        score *= 0.2                               # the tank's overhead cone (50 deg up), the Chopper's rear
    air = target is not None and VEHICLES.get(target, {}).get("move") == "air"
    if shooter in ("banshee", "sabre", "seraph") and air:
        score *= 2.0
    if shooter == "gauss":
        score *= 0.5 if target is None else 1.5
    if shooter in ("ghost", "chopper") and in_ram:
        score *= 1.5
    if shooter == "wraith" and seat == "driver":
        score *= 1.5 if moving < 0.5 else 0.4 if target is None else 1.0
    if shooter == "rwarthog" and target is None and game in ("reach", "h4"):
        score = 0.0                                # anti-air: "hold fire on ground targets" (Reach / Halo 4 M12R)
    if shooter in ("scorpion", "wraith") and seat == "gunner" and game in ("h3", "odst") and d < 3.3:
        score *= 10.0                              # the tank gunner's standing order: the hull and 10 m first (§4.5)
    return score


def roles_of(name):
    k = kind_of(name)
    return ROLES.get(k, ()) if k else ()


def strategy(name):
    k = kind_of(name)
    return STRATEGY.get(k, dict(role="strafe", rng=(8.0, 25.0))) if k else dict(role="strafe", rng=(8.0, 25.0))


# the maps' names -> a kind above (substring, first match; order matters: "rwartho" before "warthog")
ALIASES = (("rwartho", "rwarthog"), ("warthog_gauss", "gauss"), ("gauss", "gauss"), ("warth", "warthog"),
           ("thog", "thog"), ("prowler", "prowler"), ("sabre", "sabre"), ("seraph", "seraph"),
           ("gungoose", "gungoose"), ("mongoose", "mongoose"), ("ghost", "ghost"), ("brute_chopper", "chopper"),
           ("chopper", "chopper"), ("revenant", "revenant"), ("spectre", "spectre"), ("mantis", "mantis"),
           ("scorpio", "scorpion"), ("wraith", "wraith"), ("banshee", "banshee"), ("hornet", "hornet"),
           ("falcon", "falcon"), ("behemoth", "elephant"), ("elephant", "elephant"), ("olifaunt", "olifaunt"),
           ("turret", "turret"), ("machinegun", "turret"), ("c g", "turret"), ("shade", "turret"), ("missile_pod", None),
           ("forklift", None), ("camera", None), ("defender", None))


# Halo: Reach's seat indexes for the enter-seat interaction (tools/vehicle_seats.py -> maps/_shapes/reach_seats.json, from
# the editing kit's tags): driver 0; passengers by index; turret=True: the gun is its own vehicle riding on this one
# (Warthog chaingun / gauss / rocket, Scorpion anti-infantry gun, Wraith anti-infantry gun, Falcon side guns), seat 0
REACH_SEATS = {"warthog": dict(passenger=(1,), turret=True), "rwarthog": dict(passenger=(1,), turret=True),
               "gauss": dict(passenger=(1,), turret=True), "mongoose": dict(passenger=(1,)),
               "revenant": dict(passenger=(1,)), "scorpion": dict(passenger=(1, 2, 3, 4), turret=True),
               "wraith": dict(turret=True), "falcon": dict(passenger=(1, 2, 3, 4, 5), turret=True),
               # ponytail: the seat by the driver only; the troop bed's three ride on the bed, a vehicle of its own
               "thog": dict(passenger=(1,))}
# ... and its boarding seats (reach_seats.json: the seats flagged "boarding seat"), where a boarder of an enemy's vehicle
# asks to go: live (Breakpoint 20261103-181702, bot 1) Use with the driver's seat asked 3 s beside an enemy Wraith never
# took. The gun riding on a Warthog / Falcon has its own (seat 1 of the gun)
REACH_BOARD = {"warthog": (2, 3), "rwarthog": (2, 3), "gauss": (2, 3), "mongoose": (2, 3), "scorpion": (5, 6, 7),
               "ghost": (1, 2, 3), "wraith": (1, 2, 3), "revenant": (2, 3), "banshee": (1, 2), "falcon": (6, 7)}


# (custom, Nov 8) Halo 4: the seat number a bot asks for at an enemy's vehicle to board it: botcore puts it on one of the
# vehicle's boarding / hijack spots (native/shared.h HB_SEAT_BOARD, h4f.cpp f_board), not in a seat
H4_BOARD_SEAT = 14


def reach_seat(kind, want, tries=0):
    """(seat index, turret) a bot asks for to get into a Reach vehicle as want ("driver", "gunner", "passenger"), or
    None when it has no such seat. tries: the next passenger seat each time (the first may be taken)."""
    k = kind_of(kind) or kind
    if k == "turret":
        return (0, False)                   # a standalone gun: its only seat
    s = REACH_SEATS.get(k, {})
    if want == "board":                     # an enemy's vehicle: its boarding seats in turn, else its driver's
        b = REACH_BOARD.get(k)
        return (b[tries % len(b)], False) if b else (0, False)
    if want == "driver":
        return (0, False)
    if want == "gunner":
        return (0, True) if s.get("turret") else None
    p = s.get("passenger", ())
    return (p[tries % len(p)], False) if p else None


def kind_of(name):
    """The VEHICLES kind for a map's vehicle name (None: not something a bot uses: cameras, forklifts)."""
    n = (name or "").lower().rsplit("\\", 1)[-1]
    for sub, kind in ALIASES:
        if sub in n:
            return kind
    return None


def spec(name):
    k = kind_of(name)
    return VEHICLES.get(k) if k else None


# Sandtrap's Elephant (its model, objects\levels\multi\shrine\behemoth: tools/model2obj on shrine.map), in its own
# frame (f forward, l left, z up over its origin, world units): each team's flag hangs at its "flag_spawn" marker
# (1.45, -0.47, 1.36), 0.76 u over the bay floor (z 0.5-0.6, f -3.8 to 2.2, within 0.9 of the middle line), and is
# captured at "flag_return" on that floor; the bay's one way in is the rear ramp (40 degrees, l -1.0 to 0.0)
ELEPHANT = dict(flag_return=(0.24, -0.27, 0.55), bay=(-3.8, 2.4, 0.9), ramp=((-4.7, -0.5), (-2.4, -0.5)),
                hull=(-4.25, 4.2, 2.3))


def frame_of(v):
    """A vehicle's (snapshot dict) flat frame: to_local(p) -> (f, l, z over it), to_world(f, l) -> Vec at its height;
    None without a facing."""
    f = v.get("fwd")
    n = math.hypot(f[0], f[1]) if f else 0.0
    if not n:
        return None
    c, s_ = f[0] / n, f[1] / n
    ox, oy, oz = v["pos"][0], v["pos"][1], v["pos"][2]

    def to_local(p):
        dx, dy = p.x - ox, p.y - oy
        return dx * c + dy * s_, -dx * s_ + dy * c, p.z - oz

    def to_world(fw, lf, up=0.0):
        return Vec(ox + fw * c - lf * s_, oy + fw * s_ + lf * c, oz + up)
    return to_local, to_world


def upright(v):
    """Standing: its up vector's z over 0.5 (under 60 degrees of tilt), or not known (taken as standing). One on its side
    or roof takes a bot in and puts it out a second later, again and again (Halo 4 Exile: 25 of 25 seat spells of 1.5 s
    or less were in vehicles not upright at the time; an upturned Warthog boarded 20 times)"""
    up = v.get("up")
    return up is None or up[2] > 0.5


DUD_S, DUD_FOR = 10.0, 120.0     # s a bot may stand within DUD_NEAR of a vehicle without getting in; then nobody tries it
DUD_NEAR = 6.0                   # (that long: dud). The Pit, live: two Warthogs the map shows behind its fences,
                                 # 15-18% of both teams' bot time on the way to them, 13,921 rows 2-4 u off, never in


def usable(v, now=0.0, duds=None):
    """A vehicle a bot may go for: standing (upright), not a wreck (the snapshot's "dead": brain/live.py
    Live.vehicle_dead), and not one bots stood by lately without getting in (duds: handle -> until, Bot.dud_check)."""
    return upright(v) and not v.get("dead") and (duds or {}).get(v["handle"], 0.0) <= now


def variant(name, turrets=()):
    """A vehicle's name as the brain reads it: the variant the gun riding on it makes (TURRETS: a Reach Warthog carrying
    a gauss gun is a "gauss"), else its own."""
    for t in turrets:
        k = next((kind for sub, kind, gun in TURRETS if sub in t), None)
        if k is not None and k != kind_of(name):
            return k
    return name


# where a Reach gun's shot leaves, over the place the game reads for the man in it (his vehicle's own height: Spire, a
# Warthog gunner read at the Warthog's origin, a Falcon's at the Falcon's): the gun's mount on the vehicle plus its
# pivot or muzzle (their models, tools/model2obj on 35_island.map). Aimed from the eye's 0.62 the chaingun shot 0.3 u
# over its aim point: 4.8 s at 6 u into a man who lost nothing
GUN_HEIGHT = {"warthog_chaingun": 0.92, "falcon_side_gun": 0.38}
# ... and along the vehicle's forward axis (u, + ahead): Reach's Warthog carries its chaingun on its "turret" marker,
# 0.536 u behind its origin, on its centre line (logs/tmp/reach_guns/warthog.obj.markers.json, model2obj on
# 35_island.map). Aimed from the origin, a man 10 u off to its side was missed by 3 deg, 6 at 5 u: to the right of one
# on its left (a Spire flag Nov 6, the turret aim to the right, flagged Oct 30 too)
GUN_FORWARD = {"warthog_chaingun": -0.536}
GUN_FORWARD_KIND = {"warthog": -0.536}   # (Halo 3's unnamed turret, as GUN_HEIGHT_KIND: INFERRED, not measured)


def gun_forward(turret, kind=None):
    """GUN_FORWARD for the gun a gunner sits in (its name), else by the vehicle's kind where the game does not name the
    gun (GUN_FORWARD_KIND), 0 where not measured."""
    f = next((f for sub, f in GUN_FORWARD.items() if sub in (turret or "")), None)
    return f if f is not None else (GUN_FORWARD_KIND.get(kind, 0.0) if turret in (None, "", "unknown") else 0.0)
# ... by the vehicle's kind where the game does not name the gun: Halo 3's turret reads "unknown" in every gunner row,
# so its Warthog gunner aimed from the eye's 0.62 and shot over the man. INFERRED: Halo 3's Warthog carries its gun as
# Reach's does (not measured on its model)
GUN_HEIGHT_KIND = {"warthog": 0.92}

SCORPION_TURN = math.radians(90.0)  # Reach Boneyard: upper sustained driver view speed in the owner's recording.
# (Halo 4's Scorpion drivers use it too, every fixed tier: Bot.drive. Not measured in Halo 4)
SCORPION_SETTLE = 0.10              # s of aligned aim before requesting a shot; barrel orientation is not read.


def warthog_gun_origin(v, mount):
    """Reach chaingun attachment position in the Warthog frame, with the calibrated shot height."""
    if mount is None or len(mount) != 3 or not all(math.isfinite(c) for c in mount):
        return None
    if math.hypot(*mount[:2]) > 2.5 or abs(mount[2]) > 2.0:
        return None                    # reject a world position or a bad attachment read
    frame = frame_of(v)
    if frame is None:
        return None
    return frame[1](mount[0], mount[1], GUN_HEIGHT["warthog_chaingun"])


def h4_warthog_gun_origin(v):
    """Halo 4's turret marker plus the chaingun's aiming pivot, measured on Harvest's models."""
    forward, up = v.get("fwd"), v.get("up")
    if (not forward or not up or not all(math.isfinite(c) for c in (*forward, *up))
            or not all(0.9 < math.hypot(*axis) < 1.1 for axis in (forward, up))
            or abs(sum(f * u for f, u in zip(forward, up))) >= 0.1):
        return None
    return Vec(*v["pos"]) - Vec(*forward).norm() * 0.616 + Vec(*up).norm() * 0.924


def gun_height(turret, kind=None):
    """GUN_HEIGHT for the gun a gunner sits in (its name, the snapshot's turret), else by the vehicle's kind
    (GUN_HEIGHT_KIND), None where not measured."""
    h = next((h for sub, h in GUN_HEIGHT.items() if sub in (turret or "")), None)
    return h if h is not None or turret not in (None, "", "unknown") else GUN_HEIGHT_KIND.get(kind)


def gunner_gun(v, turret=""):
    """What a gunner's seat on vehicle v shoots, as a hand gun (GUNNER_GUN): by the gun it sits in where that is a
    vehicle of its own (TURRETS: a Falcon's grenade launcher), else by the vehicle's kind."""
    gun = next((g for sub, kind, g in TURRETS if sub in turret), None) if turret else None
    return gun or GUNNER_GUN.get(kind_of(v["kind"]) or v["kind"])


def driver_armed(v):
    """The driver's seat shoots: its kind's gun is the driver's (a Ghost, a Banshee), or a chin gun rides on it (the
    Forge nose-gun Falcon). A Warthog's driver, a Mongoose's, and a Reach multiplayer Falcon's pilot have none: the
    pilot fired 1179 of 1402 ticks at 0.2 degrees off and 14.5 u and hurt nobody (Spire, live)."""
    s = spec(v["kind"])
    return bool(s) and (s["gun"] == "driver" or any("chin_gun" in t for t in v.get("turrets", ())))


def gun_sides(v):
    """The sides of v whose hung guns are manned ("left", "right": a Falcon's), from the snapshot's manned turrets."""
    return {side for t in v.get("manned", ()) for side in ("left", "right") if t.endswith(side)}


def needs_gunner(v, snap):
    """A vehicle (snapshot dict) one of ours drives with its gun seat empty: {handle, kind, pos, riders}."""
    s = spec(v["kind"])
    if not (s and s["gun"] == "gunner" and v.get("riders", 0) >= 1):
        return False
    return not v["gunner"] if "gunner" in v else v.get("riders", 0) == 1   # (Reach reads who is in the gun)


# (custom, the owner's ask Nov 7) the ground transports a Demon never drives, in any game: every Warthog (chaingun, rocket,
# gauss, troop) and the Mongooses. It rides their guns and seats; Normal and Heroic are the team's drivers
# (profiles.driver_priority, director.crew_orders). His Gore Valley CTF (20261107-223617): two Demons drove about a minute
# each, a Warthog driver has no gun, and 28% of his hits on Demons came while they were in vehicles
DEMON_NO_DRIVE = {"warthog", "rwarthog", "gauss", "thog", "mongoose", "gungoose"}


# (custom, Nov 7) a light vehicle's body as boxes in its own frame (forward, left, up from its origin; u), for whether a
# round at a rider's head goes through the vehicle first (hull_blocks). INFERRED around the owner's seat capture
# (logs/h4_seat_capture_20261107-233231, Halo 4): heads (fwd, left, up) Warthog driver (0.01, 0.13, 0.24), passenger
# (0.06, -0.19, 0.43), gunner (-0.55, 0.0, 0.49-0.68), Ghost (-0.25, 0.01, 0.17), Mongoose (0.03, 0.0, 0.31); the
# driver's pelvis 0.03 up and feet 0.3 ahead at -0.03. The level data has no vehicles in it; not the tag's collision
# model: a round the hull really takes is caught by Bot.dry_part (a rider gone dry is held off)
HULLS = {
    "warthog": (((-0.9, 0.9), (-0.42, 0.42), (-0.45, 0.06)),      # chassis, the cab's sides to the riders' waists
                ((0.3, 0.9), (-0.42, 0.42), (0.06, 0.14))),        # the hood ahead of the cab
    "mongoose": (((-0.6, 0.55), (-0.25, 0.25), (-0.35, 0.05)),),
    "ghost": (((-0.6, 0.7), (-0.5, 0.5), (-0.4, 0.0)),             # the hull
              ((-0.12, 0.6), (-0.3, 0.3), (0.0, 0.2))),            # its nose and canopy ahead of the driver
}
HULL_KIND = {"warthog": "warthog", "rwarthog": "warthog", "gauss": "warthog", "thog": "warthog",
             "mongoose": "mongoose", "gungoose": "mongoose", "ghost": "ghost"}


# Halo 4: a seated man's own view point (+0xD50, the seat capture's medians) in the vehicle's frame, where his shots are
# aimed from: a driver's is the vehicle's camera point at its origin, the Warthog passenger's his first-person eye. The
# gunner's is the chaingun's pivot (h4_warthog_gun_origin)
H4_SEAT_VIEW = {("warthog", "driver"): (0.017, -0.015, 0.007), ("warthog", "passenger"): (0.128, -0.247, 0.428),
                ("mongoose", "driver"): (0.055, 0.002, -0.012), ("ghost", "driver"): (-0.003, -0.001, 0.003)}


def frame_point(v, p):
    """The world point of p (forward, left, up) in vehicle v's frame, or None without a sane orientation read."""
    f, u = v.get("fwd"), v.get("up")
    if not f or not u:
        return None
    left = (u[1] * f[2] - u[2] * f[1], u[2] * f[0] - u[0] * f[2], u[0] * f[1] - u[1] * f[0])
    n = math.sqrt(sum(c * c for c in left))
    if not 0.5 < n < 1.5:
        return None
    left = tuple(c / n for c in left)
    o = v["pos"]
    o = (o.x, o.y, o.z) if hasattr(o, "x") else o
    return Vec(*(o[i] + p[0] * f[i] + p[1] * left[i] + p[2] * u[i] for i in range(3)))


# (custom, Nov 8) Halo 4: the Banshee driver's aim line runs from his camera's anchor, the model's "banshee_d_camera"
# marker, (-0.104, 0, 0.595) in the vehicle's frame (forward, left, up), through its bone's bind pose (tools/model2obj
# --skin on ca_blood_crash.map, storm_banshee; the conventions checked on the Warthog's turret marker,
# h4_warthog_gun_origin). It had no seat view at all: the generic chest, his place + 0.35, over a Spartan's head.
# The Ghost's own "ghost_d_camera" (-0.019, 0, 0.496) was tried and taken back the same day: aimed from it, live Blood
# Crash 20261108-152614, Ghost drivers made 0.6 kills a minute at the controls (1.3-2.2 in the four matches before) and
# a man 10-20 u off took damage after 5% of their fire rows (25% before): the captured seat view (H4_SEAT_VIEW, at the
# origin) stays the Ghost's
H4_DRIVER_AIM = {"banshee": (-0.104, 0.0, 0.595)}


def h4_driver_aim(v):
    """Halo 4: where a Ghost's or Banshee's driver aims from (H4_DRIVER_AIM), or None (another kind, no orientation)."""
    p = H4_DRIVER_AIM.get(kind_of(v.get("kind")) or "")
    return frame_point(v, p) if p is not None else None


def h4_seat_view(v, seat):
    """Halo 4: where a man in this seat of v aims from (H4_SEAT_VIEW), or None (a seat not captured, the gunner's)."""
    p = H4_SEAT_VIEW.get((HULL_KIND.get(kind_of(v.get("kind")), ""), seat))
    return frame_point(v, p) if p is not None else None


def hull_blocks(v, a, b, spare=0.06):
    """Whether the segment a -> b (a shot from our view to a rider's head) passes through vehicle v's body (HULLS), its
    last spare u (the head itself) left out. False for a vehicle with no hull here or no orientation read."""
    boxes = HULLS.get(HULL_KIND.get(kind_of(v.get("kind")), ""))
    f, u = v.get("fwd"), v.get("up")
    if not boxes or not f or not u:
        return False
    left = (u[1] * f[2] - u[2] * f[1], u[2] * f[0] - u[0] * f[2], u[0] * f[1] - u[1] * f[0])
    n = math.sqrt(sum(c * c for c in left))
    if not 0.5 < n < 1.5:
        return False
    axes = (f, tuple(c / n for c in left), u)
    o = v["pos"]
    a, b = [(p.x, p.y, p.z) if hasattr(p, "x") else tuple(p) for p in (a, b)]
    pa = [sum((a[i] - o[i]) * ax[i] for i in range(3)) for ax in axes]
    pb = [sum((b[i] - o[i]) * ax[i] for i in range(3)) for ax in axes]
    seg = math.sqrt(sum((pb[i] - pa[i]) ** 2 for i in range(3)))
    if seg < 1e-6:
        return False
    t_end = max(0.0, 1.0 - spare / seg)
    for box in boxes:
        lo, hi = 0.0, t_end
        for k in range(3):
            d = pb[k] - pa[k]
            if abs(d) < 1e-9:
                if not box[k][0] <= pa[k] <= box[k][1]:
                    break
                continue
            t0, t1 = (box[k][0] - pa[k]) / d, (box[k][1] - pa[k]) / d
            lo, hi = max(lo, min(t0, t1)), min(hi, max(t0, t1))
            if lo > hi:
                break
        else:
            return True
    return False


def demon_no_drive(name):
    """A vehicle a Demon does not drive (DEMON_NO_DRIVE)."""
    return kind_of(name) in DEMON_NO_DRIVE


def taxi_ok(name):
    """A vehicle a bot may ride somewhere and leave there: a transport (Falcon, Warthog, Mongoose ...) or a light harasser
    (Ghost). A power vehicle (Banshee, Hornet, tank, Chopper, gun Warthogs) is taken for a job, never as a taxi."""
    r = ROLES.get(kind_of(name), ())
    return not r or "transport" in r or r == ("harasser",)


def ride_score(v, me, goal, trip):
    """How much this bot wants to take vehicle v for a trip to goal: its value, closer is better, a long trip pays. Never
    a power vehicle (taxi_ok)."""
    s = spec(v["kind"])
    if not s or s["move"] == "none" or v.get("occupied") or v.get("dead") or not taxi_ok(v["kind"]):
        return 0.0
    d = dist(me.pos, Vec(*v["pos"]))       # (the snapshot's vehicle positions are tuples)
    return s["value"] * max(0.0, 1.0 - d / 25.0) * min(1.0, trip / 40.0)
