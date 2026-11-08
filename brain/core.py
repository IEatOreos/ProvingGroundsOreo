"""Shared types: what the game hands the brain each tick, and what the brain hands back."""
from dataclasses import dataclass, field
import math

TICK = 1 / 30  # Halo CE simulates at 30 ticks per second


@dataclass(frozen=True)
class Vec:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(s, o): return Vec(s.x + o.x, s.y + o.y, s.z + o.z)
    def __sub__(s, o): return Vec(s.x - o.x, s.y - o.y, s.z - o.z)
    def __mul__(s, k): return Vec(s.x * k, s.y * k, s.z * k)
    def length(s): return math.sqrt(s.x * s.x + s.y * s.y + s.z * s.z)
    def flat(s): return math.hypot(s.x, s.y)

    def norm(s):
        n = s.length()
        return Vec(s.x / n, s.y / n, s.z / n) if n > 1e-9 else Vec()


def dist(a, b): return (a - b).length()


def angles_to(src, dst):
    """yaw, pitch (radians) to look from src at dst."""
    d = dst - src
    return math.atan2(d.y, d.x), math.atan2(d.z, max(d.flat(), 1e-6))


def eye(p):
    """Where a player's shots come from: positions are at the feet; CE cyborg camera height is
    0.62 standing, 0.35 crouching."""
    return p.pos + Vec(0, 0, 0.35 if p.crouching else 0.62)


# where to aim on a crouched man over his feet, head and chest (standing: 0.62 and 0.35, Aim.step). Bots shot at a
# crouched man's standing head height and never killed him. The crouched body is 56% of the standing one by CE's
# camera heights (eye: 0.35 / 0.62) and 70% in the sim's hit model (brain/sim.py shoot); the game's own figure is not
# read. 0.38 is in the head in the first and the top of the body in the second; 0.22 in the body in both
CROUCH_HEAD, CROUCH_CHEST = 0.38, 0.22


def wrap(a):
    """angle to -pi..pi"""
    return (a + math.pi) % (2 * math.pi) - math.pi


@dataclass
class PlayerState:
    id: int
    team: int            # 0 red, 1 blue
    name: str
    pos: Vec
    vel: Vec = field(default_factory=Vec)
    yaw: float = 0.0
    pitch: float = 0.0
    alive: bool = True
    shield: float = 1.0  # 0..1, CE shields fully recharge
    health: float = 1.0  # 0..1
    weapon: str = "pistol"
    weapons: list = field(default_factory=list)   # inventory in slot order (live game; the sim leaves it empty)
    ammo: list = field(default_factory=list)      # rounds left (magazine + reserve) per weapons entry, -1 unknown
    mag: list = field(default_factory=list)       # rounds in the magazine per weapons entry, -1 unknown
    vehicle: int = -1          # handle of the vehicle this player rides, -1 = on foot
    gunner_seat: bool = False  # in the gun riding on that vehicle (Reach: its turret is a vehicle of its own)
    turret: str = ""           # ... that gun's name ("falcon_side_gun_left", "warthog_gauss"; brain/vehicles.TURRETS)
    has_flag: bool = False
    camo_until: float = 0.0   # active camouflage running until this time (0 = none)
    crouching: bool = False
    is_bot: bool = True
    equipment: str = ""        # the equipment / armor ability carried (brain/equipment.py kinds), "" none
    ability_on: bool = False   # that ability is running (armor lock held, jetpack on, camo on ...)
    decoy: bool = False        # a hologram (the game's truth: bots tell it only from what it does)
    tracker: bool = True       # enemies show on this player's motion tracker (the match settings: live.tracker())
    head_pos: object = None    # Vec: the animated head (Reach / Halo 4 on foot: live.py's head readers), None not read
    view_pos: object = None    # Vec: Halo 4's view point that head goes with (its place is not the feet), None not read


@dataclass
class FlagState:
    team: int
    home: Vec
    pos: Vec
    state: str = "home"   # home | carried | dropped
    carrier: int = -1


@dataclass
class Snapshot:
    time: float
    players: list
    flags: dict = field(default_factory=dict)  # team -> FlagState (CTF only)
    score: dict = field(default_factory=lambda: {0: 0, 1: 0})   # team -> points (free for all: each player's team)
    mode: str = "slayer"   # slayer | ctf | king | oddball | firefight
    score_limit: int = 0       # the variant's score to win, 0 = not known (brain/match.py)
    time_left: object = None   # seconds left in the match, None = no limit or not known
    vehicles: list = field(default_factory=list)   # [{handle, kind, pos, occupied}] (live game)
    honks: list = field(default_factory=list)      # vehicle handles a teammate honked from (director.honk_orders)
    honk_at: dict = field(default_factory=dict)    # vehicle handle -> the bot the person's horn picked (None: nearest)
    ground_weapons: list = field(default_factory=list)   # [(name, Vec)] lying on the map (live game)
    hill: object = None        # King of the Hill: the active hill's centre (Vec) and its radius
    hill_r: float = 0.0
    ball: object = None        # Oddball: where the ball is (Vec), and who carries it (player id or None)
    ball_carrier: object = None
    deployed: list = field(default_factory=list)   # [{kind, pos, team, t}] domes, fields, mines, flares, sentries
    grenades: list = field(default_factory=list)   # [{pos, team, t}] grenades in flight or lying live (the simulator's,
                                                   # brain/simgear.py; live none: no grenade objects read)
    shieldless: bool = False   # no shields this match (Team SWAT, Snipers ...): every living shield reads 0 (live_bots)    # Reach Invasion (brain/invasion.py): phase 1-3, the team attacking, this phase's territories [Vec], the core
    # (Vec or None until phase 3) and its carrier (player id or None), and where the core is delivered
    inv_phase: int = 0
    inv_attackers: int = -1
    inv_zones: list = field(default_factory=list)
    inv_zone_r: list = field(default_factory=list)   # each zone's size (its boundary), the same order
    inv_core: object = None
    inv_core_carrier: object = None
    inv_armed: bool = False    # Breakpoint's bomb lies armed in its plant zone (brain/invasion.py)
    inv_bomb: bool = False     # phase 3's object is Breakpoint's bomb, not the core (a melee drops the core, not the bomb)
    inv_delivery: object = None
    inv_stand: object = None   # where phase 3's core (Breakpoint's bomb in its run) stands until taken: off it, it is
                               # dropped, the defenders' to return (Bot.return_point)
    inv_phase_t: float = 0.0   # seconds into the phase (brain/invasion.py Watch; the director's push)
    # the other objective modes (brain/modes.py: territories, assault, stockpile, headhunter, infection):
    # zones [(Vec, radius, owner team or -1)], objects to carry [{pos, carrier, kind}], each team's goals {team: [Vec]}
    obj_zones: list = field(default_factory=list)
    obj_items: list = field(default_factory=list)
    obj_goals: dict = field(default_factory=dict)
    infected: int = -1         # Infection: the infected side when the reader knows it (Halo 3: by the zombies' gun)
    vips: tuple = ()           # VIP: each team's VIP (player ids), as the game marks them (Halo 3: brain/modes.py)
    race_next: dict = field(default_factory=dict)   # Race: player id -> his next gate (Vec), brain/modes.py Race

    def player(s, pid):
        return next((p for p in s.players if p.id == pid), None)


@dataclass
class Action:
    """Mirrors Halo CE player_action: throttle, facing, control buttons."""
    forward: float = 0.0   # -1..1
    strafe: float = 0.0    # -1..1 (left positive)
    yaw: float = 0.0
    pitch: float = 0.0
    fire: bool = False
    jump: bool = False
    crouch: bool = False
    grenade: bool = False
    melee: bool = False
    action: bool = False   # pick up / swap weapon
    reload: bool = False
    weapon: int = -1       # inventory slot to switch to, -1 = keep the current one
    equipment: bool = False   # use the equipment / armor ability (held for hold-mode abilities)
    ability: bool = False     # with equipment: a hold-mode ability's held bit (Reach +0x08 bit 8; brain/equipment.py
                              # hold_bit; sent where decoded, maps/_inputs/<game>.json "ability")
    sprint: bool = False      # Halo 4's sprint (Reach's is an armor ability: equipment)
    zoom: int = 0             # scope level wanted: 0 none, 1 first, 2 second (sent where decoded)
    seat: int = -1            # with action: the vehicle seat to enter (Reach: native enters it, brain/vehicles.reach_seat)
    turret: bool = False      # ... in the gun riding on the vehicle (a Warthog's turret)
    vertical: float = 0.0     # a hovering aircraft's vertical input: 1 up, 0.5 hold, -1 down (Reach's Falcon; shared.h
                              # HB_VERT_SHIFT)
    fire2: bool = False       # a vehicle's second input: a Banshee's bomb; in Reach its boost (shared.h HB_BTN_FIRE2;
                              # sent where decoded, maps/_inputs/<game>.json "fire2")
    cycle: bool = False       # a press of the weapon cycle: Reach's Banshee fuel rod is cycled to (shared.h
                              # HB_BTN_CYCLE; sent where decoded, maps/_inputs/<game>.json "cycle")
    lunge_at: int = -1        # the player id a sword / hammer / melee press locks onto: its red reticle's target, which
                              # the game's lunge needs in the action (shared.h HB_TARGET_SHIFT; issue #3)
