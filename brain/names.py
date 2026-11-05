"""Gamertag-style bot names: made up from parts, in the styles of an MCC lobby (word + number,
xX..Xx, clan-ish, plain words). Up to 15 characters (the game's name field)."""
import random

FIRST = ["Shadow", "Ghost", "Spartan", "Reaper", "Covert", "Silent", "Rogue", "Frost", "Iron", "Static",
         "Crimson", "Lone", "Rapid", "Hollow", "Grim", "Lucky", "Toxic", "Vapor", "Noble", "Echo", "Night",
         "Storm", "Pixel", "Nova", "Cosmic", "Lazy", "Salty", "Turbo", "Quiet", "Feral", "Dark", "Blood",
         "Lethal", "Insane", "Epic", "Mad", "Fatal", "Sick", "Legit", "Mythic", "Heroic", "Rampant", "Atomic",
         "Cyber", "Hyper", "Mega", "Ultra", "Phantom", "Spectre", "Brutal", "Savage", "Swift", "Zero", "Omega",
         "Alpha", "Delta", "Sierra", "Steel", "Chrome", "Venom", "Fury", "Havoc", "Rebel", "Outlaw", "Wicked",
         "Chief", "Major", "Agent", "Covie", "Plasma", "Sticky", "Frag", "Gravity", "Stealth",
         "Sneaky", "Bacon", "Elder", "Scarlet",]
SECOND = ["Wolf", "Sniper", "Hunter", "Falcon", "Viper", "Rider", "Blade", "Fox", "Owl", "Jackal", "Grunt",
          "Elite", "Brute", "Hawk", "Raven", "Tiger", "Panda", "Moose", "Badger", "Lynx", "Pilot", "Medic",
          "Ranger", "Bandit", "Nomad", "Drifter", "Warden", "Sentry", "Rocket", "Pistol", "Ninja", "Slayer",
          "Killa", "Gamer", "Assassin", "Dragon", "Demon", "Wraith", "Scorpion", "Mongoose", "Hornet", "Pelican",
          "Chopper", "Prowler", "Arbiter", "Prophet", "Marine", "Trooper", "Recon", "Scout", "Striker", "Gunner",
          "Sapper", "Warlord", "Legend", "Lord", "King", "Boss", "Beast", "Monkey", "Duck", "Taco", "Noob",
          "Fragger", "Camper", "Goat", "Bear", "Shark", "Cobra", "Skull", "Zealot", "Bomber",
          "Runner", "Carrier", "Sword", "Hammer", "Needler", "Magnum"]
WORDS = ["Plasmatic", "Overshield", "Needlerz", "Warthog", "Banshee", "Gulch", "Sidewinder", "Cortana", "Monitor",
         "Sentinel", "Flood", "Teabag", "Noscope", "Sticky", "Flagrunner", "Arbiter", "Pelican", "Scarab",
         "Mongoose", "Elephant", "Wraith", "Snipes", "Headshot", "Killtacular", "Overkill", "Killtrocity",
         "Killionaire", "Perfection", "Hogrider", "Rocketrider", "Swordlunge", "Doubleshot", "Quickscope",
         "Ragequit", "Partychat", "Gamerscore", "Redring", "Lagswitch", "Superjump", "Bridgecamp", "Lockout",
         "Guardian", "Valhalla", "Sandtrap", "Highground", "Zanzibar", "Ascension", "Headlong", "Chillout",
         "Midship", "Foundry", "Narrows", "Countdown", "Powerhouse", "Boardwalk", "Spartacus", "Grifball",
         "Juggernaut", "Oddball", "Bloodline", "Killjoy", "Pwnage", "Fragtastic", "Bubbleshield", "Spikegrenade"]


def make_names(n, rng=None, taken=()):
    rng = rng or random.Random()
    out, used = [], {t.lower() for t in taken}
    while len(out) < n:
        style = rng.random()
        if style < 0.35:
            name = rng.choice(FIRST) + rng.choice(SECOND)
        elif style < 0.6:
            name = rng.choice(FIRST + SECOND) + str(rng.choice([rng.randint(1, 99), rng.randint(100, 999), 7, 117, 343]))
        elif style < 0.75:
            name = "xX" + rng.choice(SECOND + WORDS)[:9] + "Xx"
        elif style < 0.9:
            name = rng.choice(WORDS) + rng.choice(["", "", "x", "TV", "HD", "_" + str(rng.randint(1, 9))])
        else:
            name = rng.choice(["The", "Mr", "Lil", "Big", "Sir"]) + rng.choice(SECOND)
        name = name[:15]
        if name.lower() not in used:
            used.add(name.lower())
            out.append(name)
    return out


if __name__ == "__main__":
    names = make_names(30, random.Random(1))
    assert len(set(names)) == 30 and all(len(n) <= 15 for n in names)
    print(names)
