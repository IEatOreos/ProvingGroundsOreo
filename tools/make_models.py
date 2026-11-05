"""The Settings tab's 3D bots (native/model_view.cpp): each game's character models from MCC's own map files, exported with
model2obj (the separate map tools, GPL-3.0) with their skeletons and textures, posed holding a weapon and packed with
tools/model_pack2.py into native/bin/models/<game>_<species>.mdl (version 2) and native/bin/models/tex/. Run once per
install (native/build.bat runs it when the models are missing); a few minutes, about 450 MB (every Armory piece of
Reach, H2A and Halo 4 too; Halo 4's alone 180 MB). Textures no model uses any more (an export numbers them anew) are
removed afterwards.

usage: python -I make_models.py [MCC folder] [--only h3_spartan,h3_elite] [--out <models folder>] [--clean-exports]
       (--out: build somewhere else, e.g. while MCC has native/bin/models open; --clean-exports: delete the
       exported meshes in maps/_models/<game> afterwards, as the first-time setup does)
"""
import os
import shutil
import struct
import subprocess
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from brain import paths  # noqa: E402  (where MCC, the mod kits and Visual Studio are)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
ARGS = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] not in ("--only", "--out")]
MCC = ARGS[0] if ARGS else paths.mcc()
ONLY = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(ROOT, "native", "bin", "models")
CE, H2, H3 = r"halo1\maps\bloodgulch.map", r"halo2\h2_maps_win64_dx11\lockout.map", r"halo3\maps\construct.map"
H2A, REACH = r"groundhog\maps\ca_lockout.map", r"haloreach\maps\20_sword_slayer.map"
# out name, species (the pose), game (texture name prefix), map, the model's tag name end, the held weapon's tag name
# end, model_pack2 options (an Elite holds the energy sword, one-handed: the player's picture; Halo 3 has one sword
# model for both views, fp_energy_blade) each model's own hold ("Halo 3 rifle in body a lil bit", Reach's Elite sword
# hand and head, "H2A and H4 completely self explanatory"). Spartans: the rifle across the chest at low ready as in
# the player's picture (logs/tmp/ owner_img_1.jpg), searched with the hinge-true arms (logs/tmp/pose_search3.py: both
# elbows hanging, the left bent, wrists within 40, the gun clear of the torso: logs/tmp/pose_qc.py), then judged in
# renders front, side and back three- quarters with the hands zoomed. Halo 2's is the one the player passed. Elites:
# slouched forward, top-front heavy, the head down, both elbows bent, the hilt across the palm
# (logs/tmp/elite_search.py, the player's logs/tmp/owner_img_2.png)
MODELS = [
    ("ce_spartan", "spartan", "ce", CE, r"cyborg\cyborg", r"weapons\assault rifle\assault rifle",
     ["--hold", "grip=0.13,0.01,0.08;barrel=0.25,0.9,-0.45;pole_r=-0.3,-0.8,-0.5;pole_l=-0.3,0.7,-0.65;stance=1.5;"
      "relax=1.5;knees=40"]),   # (its bind stands nearly straight, knees 7-8 degrees: bent on their own hinge, feet
                                # planted, 40 / 44 degrees reads like Halo 2's and 3's stance on its blocky armor)
    ("h2_spartan", "spartan", "h2", H2, r"masterchief\masterchief", r"rifle\battle_rifle\battle_rifle",
     ["--hold", "grip=0.11,0.01,0.08;barrel=0.35,0.8,-0.45;pole_r=-0.3,-0.8,-0.5;pole_l=-0.5,0.5,-0.7"]),
    ("h2_elite", "elite", "h2", H2, r"elite\elite", r"melee\energy_blade\energy_blade",
     ["--one-hand", "--hold", "grip=0.09,-0.21,-0.05;barrel=0.45,-0.3,-0.84;pole_r=-0.6,-0.6,-0.4;rest=0.1,0.21,-0.05;"
      "upright=-10;chin=8"]),
    ("h3_spartan", "spartan", "h3", H3, r"mp_masterchief\mp_masterchief", r"assault_rifle\assault_rifle",
     ["--hold", "grip=0.11,0.01,0.06;barrel=0.25,0.9,-0.45;pole_r=-0.3,-0.8,-0.5;pole_l=-0.5,0.5,-0.7"]),
    ("h3_elite", "elite", "h3", H3, r"mp_elite\mp_elite", r"fp_energy_blade\fp_energy_blade",
     ["--one-hand", "--hold", "grip=0.09,-0.21,-0.05;barrel=0.45,-0.3,-0.84;pole_r=-0.6,-0.6,-0.4;rest=0.1,0.21,-0.05;"
      "upright=-10;chin=8"]),
    # Halo 2: Anniversary's bots wear its three original sets (spartan_iv Mark VI, spartan_var2 Centurion, spartan_var3
    # Hoplite) and in Modern MCC's added pieces (Orion, Bioroid, Robot, Trooper, Breach, Panzer: its customization
    # table, maps/_looks/h2a.json, h2a_armory.json): pieces no bot wears (Halo 4's left in this model, the Flood's) out
    ("h2a_spartan", "spartan", "h2a", H2A, r"storm_masterchief\storm_masterchief_mp", r"h2a_battle_rifle\h2a_br",
     ["--drop", "infected,chief,spartan_warrior,female",
      "--hold", "grip=0.08,-0.05,0.07;barrel=0.6,0.9,-0.45;pole_r=-0.3,-0.8,-0.5;pole_l=-0.3,0.7,-0.65"]),
    # its Elite in the three original sets (Combat, Outrider, Invader: armor_var1-3) with the energy sword; its model's
    # own lean, 16 degrees, is the slouch
    ("h2a_elite", "elite", "h2a", H2A, r"h2a_elite\h2a_elite", r"h2a_energy_sword\h2a_energy_sword",
     ["--one-hand", "--hold", "grip=0.04,-0.21,-0.05;barrel=0.45,-0.3,-0.84;pole_r=-0.3,-0.8,-0.2;rest=0.1,0.21,-0.05;"
      "upright=0;chin=8"]),
    # Reach: every Armory piece (helmets, the instanced flair on shoulders, chest, wrist, thigh and knees: model2obj's
    # instance owners) for the bots' rolled armor (maps/_looks/reach_armory.json)
    ("reach_spartan", "spartan", "reach", REACH, r"spartans\spartans", r"rifle\assault_rifle\assault_rifle",
     ["--hold", "grip=0.12,-0.01,0.06;barrel=0.3,1.2,-0.45;pole_r=-0.3,-0.8,-0.5;pole_l=-0.3,0.7,-0.65"]),
    ("reach_elite", "elite", "reach", REACH, r"elite\elite", r"melee\energy_sword\energy_sword",
     ["--one-hand", "--hold", "grip=0.04,-0.21,-0.05;barrel=0.45,-0.3,-0.84;pole_r=-0.6,-0.6,-0.4;rest=0.04,0.16,-0.05;"
      "upright=-6;chin=4"]),
    # Halo 4: every piece its Armory can roll, male and female (maps/_looks/h4_armory.json); its own hold
    ("h4_spartan", "spartan", "h4", r"halo4\maps\ca_warhouse.map", r"storm_masterchief\storm_masterchief_mp",
     r"rifle\storm_assault_rifle\storm_assault_rifle",
     ["--hold", "grip=0.09,0.01,0.04;barrel=0.1,0.9,-0.35;pole_r=-0.3,-0.8,-0.5;pole_l=-0.3,0.7,-0.65"]),
]


def prune(out):
    """Removes the textures in <out>/tex that no version 2 model in <out> names (model_view.cpp's layout: a 48-byte
    header ending in the material count, then per material a 48-byte name, five 48-byte file names and two floats)."""
    if not os.path.isdir(os.path.join(out, "tex")):
        return 0
    used = set()
    for f in os.listdir(out):
        if f.endswith(".mdl"):
            with open(os.path.join(out, f), "rb") as fh:
                head = fh.read(48)
                if head[:4] != b"HBMD" or struct.unpack_from("<I", head, 4)[0] != 2:
                    continue
                for _ in range(struct.unpack_from("<I", head, 20)[0]):
                    rec = fh.read(48 + 5 * 48 + 8)
                    used.update(rec[48 * k:48 * k + 48].split(b"\0")[0].decode() for k in range(1, 6))
    gone = [t for t in os.listdir(os.path.join(out, "tex")) if t not in used]
    for t in gone:
        os.remove(os.path.join(out, "tex", t))
    return len(gone)


# models the game hangs on the body by a marker (model_pack2 --gear): Halo 3's MCC backpacks are the mp_masterchief gear
# model's chest_flair on the body's "backpack" marker; Guardian's has all 26 the customization table lists (Construct's
# has 18)
GEAR = {"h3_spartan": (r"halo3\maps\guardian.map", r"mp_masterchief\gear\gear", "chest_flair=backpack")}


def main():
    exe = paths.need(paths.map_tool("model2obj"), "model2obj.exe (the map tools: tools/map_tools)")
    made, skipped = [], []
    for name, species, game, mp, tag, weapon, opts in MODELS:
        if ONLY and name not in ONLY:
            continue
        if not os.path.exists(os.path.join(MCC, mp)) or (name in GEAR and not os.path.exists(os.path.join(MCC, GEAR[name][0]))):
            skipped.append(name)                     # (that game is not installed: Steam installs each on its own)
            print(f"{name}: skipped ({paths.GAME_NAMES.get(game, game)} is not installed)")
            continue
        tmp = os.path.join(ROOT, "maps", "_models", game)
        tex = os.path.join(tmp, "tex")
        os.makedirs(tex, exist_ok=True)
        body, held = os.path.join(tmp, species + ".obj"), os.path.join(tmp, name + "_weapon.obj")
        out = os.path.join(OUT, name + ".mdl")
        r = subprocess.run([exe, os.path.join(MCC, mp), tag, body, "--uv", "--skin", "--tex", tex], capture_output=True,
                           text=True, errors="replace")
        w = subprocess.run([exe, os.path.join(MCC, mp), weapon, held, "--uv", "--tex", tex], capture_output=True,
                           text=True, errors="replace")
        if r.returncode or w.returncode or not os.path.exists(body) or not os.path.exists(held):
            print(f"{name}: not exported ({(r.stdout + r.stderr + w.stdout + w.stderr).strip()[-200:]})")
            continue
        extra = []
        if name in GEAR:
            gmap, gtag, gspec = GEAR[name]
            gobj = os.path.join(tmp, species + "_gear.obj")
            g = subprocess.run([exe, os.path.join(MCC, gmap), gtag, gobj, "--uv", "--skin", "--tex", tex],
                               capture_output=True, text=True, errors="replace")
            if g.returncode or not os.path.exists(gobj):     # (the model without its backpack, not no model)
                print(f"{name}: its gear model was not exported ({(g.stdout + g.stderr).strip()[-200:]})")
            else:
                extra = ["--gear", gobj + "|" + gspec]
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "model_pack2.py"), species, body, held, out,
                        "--prefix", game] + opts + extra, check=True)
        made.append(name)
    shutil.rmtree(os.path.join(ROOT, "maps", "_models", "h3", "tex"), ignore_errors=True) if "--clean" in sys.argv else None
    if "--clean-exports" in sys.argv:              # (the setup: the exports are only working space, ~2.4 GB; the packed
        for game in {m[2] for m in MODELS}:        # models and their textures are in native/bin/models)
            shutil.rmtree(os.path.join(ROOT, "maps", "_models", game), ignore_errors=True)
    print(f"{prune(OUT)} unused textures removed")
    if not ONLY:
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "emblems.py"), "extract", MCC])   # the bots' emblem art
        with open(os.path.join(OUT, "made.txt"), "w", encoding="utf-8") as f:     # (tools/setup.py: this step ran)
            f.write(f"made: {' '.join(made)}\nskipped, game not installed: {' '.join(skipped)}\n")
    print(f"3D bots: {len(made)} made" + (f", {len(skipped)} skipped (games not installed)" if skipped else ""))


if __name__ == "__main__":
    main()
