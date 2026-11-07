# ProvingGroundsOreo — code review and integration handoff

Prepared November 6, 2026 for the main AI/developer reviewing the owner's custom Project Proving Grounds code. This document describes the combined work of the owner, this coding assistant, and the owner's coding collaborator. It covers the published customization history, final behavior, integration points, validation, and open proposals.

## 1. Repository and review baseline

| Item | Value |
|---|---|
| Private repository | [IEatOreos/ProvingGroundsOreo](https://github.com/IEatOreos/ProvingGroundsOreo) |
| Published branch | `main` |
| Verified published source | [`9a4cf17ed61102c2d373a279d02d33ba03c0f4d8`](https://github.com/IEatOreos/ProvingGroundsOreo/commit/9a4cf17ed61102c2d373a279d02d33ba03c0f4d8) |
| Custom source version | `0.2.2-custom.4` in `CUSTOM_VERSION` |
| Installed author version | `0.2.2-s181` in `VERSION` |
| Owner's live installation / Git working tree | `E:\Proving Grounds\Project Proving Grounds` |
| Upstream project | [AyoItzKye/project-proving-grounds](https://github.com/AyoItzKye/project-proving-grounds) |
| License and attribution | Preserve `LICENSE.md`, PolyForm Noncommercial 1.0.0, `NOTICE.md`, and original credits |

The owner approved publishing both the bot changes and the collaborator's LiDAR feature. Both are in the published history. The latest approved publication is a source push. Installed runtimes, native binaries, an installer, a version tag, and a GitHub Release were outside that publication.

The first commit, `c9a9b1f`, captured an already-customized installation. Several earlier aim/grenade/visibility changes are present there without individual implementation commits. Treat those as retained baseline behavior. The later installed-source import `6433bb3` records what the new installer left on this machine. It is an installed-state snapshot rather than a verified pristine checkout of the author's source history.

Git author metadata uses the owner's account for much of the work. It cannot reliably identify which human or AI wrote every line. Preserve the commit identities and use the behavior/file descriptions below to review the combined contribution.

### Quick category index

| Category | Main work |
|---|---|
| Halo Reach — aiming | Animated Spartan head marker for DMR/sniper, stance fallback, accurate head/chest visibility |
| Halo Reach — ammunition | Live magazine/reserve counts, between-fight magazine memory, known-empty detection |
| Halo Reach — loadouts | Shotgun preferred over AR beside DMR, Focus Rifle range/rank changes |
| Halo Reach — abilities | Armor Lock activation for a visible sword/Gravity Hammer enemy within 6 units |
| Halo Reach — maps | Breakpoint tower-to-bridge sight/shot correction |
| Halo 4 — aiming | Animated head plus matched shooter view point, shared ray for tracking/visibility/firing |
| Shared difficulty/brain | Independent Demon, restored Legendary attributes with precision exceptions, sniper shot percentages, awareness changes |
| Shared director/vehicles | Power/gunner priority, expanded high-tier power fetch, Demon power-job precedence |
| Shared LiDAR/tools | Record and display driven/flown vehicle paths in mapping mode |
| General integration | Merge custom behavior into installed 0.2.2-s181, regression tests, source/version/release workflow |

## 2. Architecture and meaning of “brain commands”

The Python brain is shared across the games, with game-specific readers, weapon tables, maps, and branches. The owner considered fully independent brains for each Halo and chose to keep the current shared architecture.

| Layer | Entry points / files | Responsibility |
|---|---|---|
| Live game reading | `brain/live.py` | Read players, pose, weapons, ammo, vehicles, and match state using the appropriate game layout |
| Shared state | `brain/core.py` | `PlayerState`, `Snapshot`, `Action`, world-space positions, optional `head_pos` / `view_pos` |
| Live execution | `tools/live_bots.py` | Approximately 30 Hz snapshot/decision/input loop, state forwarding, recording, learning |
| Per-bot brain | `brain/bot.py` | `Bot.think`, `Bot.plan`, perception, aiming, firing, pickups, reload/rearm, driving |
| Difficulty | `brain/profiles.py`, `brain/scaling.py` | Fixed profiles, separate Scaling construction, precision guards and call weights |
| Team brain | `brain/director.py` | Roles, power fetches, crew/gunner calls, carrier transport, vehicle jobs |
| Equipment | `brain/equipment.py` | `Kit` decisions and ability input/energy/hold/release handling |
| Map and geometry | `brain/maps.py`, `brain/terrain.py` | Navigation, material-aware visibility and shot rays, map-scoped corrections |
| Weapon behavior | `brain/bot.py`, `brain/loadouts.py` | Range/rank/loadout valuation, firing cadence, projectile/charge logic, spawn palettes |
| Vehicle behavior | `brain/vehicles.py`, `Bot.drive` | Chassis/seat/gun classification, tactics, mount heights, pathing, recovery |
| Native interface | `native/`, `tools/botctl.py`, `tools/play.py` | BOTS menu, roster/difficulty mapping, shared-memory inputs, process launch |
| Mapping and review | `tools/lidar.py`, `tools/lidar_view.html`, Observer and trace/export tools | Mapping, driven-path feeds, recorded reasoning and inspection |

The main commands in this context are internal orders and actions. `Order` carries `role`, `point`, `target`, and optional `via`. Ordinary roles include runner, escort, defender, hunter, mid, and free. Vehicle coordination also uses drive, ride, board, ferry, and driver_wait. `Action` submits movement, aim, fire, reload, weapon switch, interaction, grenade, melee, and ability inputs through the existing native interface.

A 0 ms profile reaction removes an intentional recognition delay. A 10 ms decision deadline is serviced on available loop updates. Neither setting raises the live loop above its approximately 30 Hz target.

## 3. Halo Reach changes

### 3.1 DMR/sniper animated head targeting

- **Problem.** A bot could point precisely at a fixed height while the animated head moved above, below, or sideways from that estimate during strafing/crouching. Precision at the wrong world point still produced misses.
- **Reader.** `LiveReach.spartan_head_position()` in `brain/live.py` transforms the Spartan's live `target_head` marker. The validated multiplayer layout is 82 transforms of 52 bytes, descriptor at unit `+0x178`, observed array offset `0xF1C`, and head node 38. Scale, finite coordinates, transform axes, and plausible displacement are checked.
- **State flow.** `PlayerState.head_pos` reaches the bot through `tools/live_bots.py`.
- **Aiming/firing.** Eligible fixed Legendary and Demon DMR/sniper firing actions receive final yaw/pitch correction after the ordinary turn cap. Movement inputs rotate with the correction so the requested world movement direction is preserved. Unsupported poses use the existing stance-height fallback.
- **Visibility.** Head/chest selection and material-aware shot rays remain coupled to the intended body part. Final DMR head-directed fire has an alignment relaxation. Sniper cadence and firing gates still apply.
- **Current scope.** Legendary and Demon retain this work after the difficulty separation. Lower fixed tiers use precise head aim on their percentage-sniper path.
- **Evidence.** Reach DMR improvement was owner-confirmed. Later owner reports described very strong Legendary sniper performance. There is no controlled post-change accuracy benchmark for every weapon, pose, and difficulty.
- **History.** Present in initial snapshot `c9a9b1f`, retained through `ca7eeb0`, protected during `6a31238`.
- **Review files.** `brain/live.py`, `brain/core.py`, `brain/bot.py` functions `head_solution`, `live_head_ray`, `Aim.step`, `Bot.think`, `Bot.fight`, and `Bot.line_clear`; `brain/terrain.py`; `tools/live_bots.py`.

### 3.2 Live magazine/reserve ammunition and reloading

- **Problem.** Reach ammo had been unavailable to the brain, weakening existing reload, empty-weapon switching, and rearm decisions. Magazine maxima were also missed when observations occurred mainly outside combat.
- **Reader change.** `LiveReach.rounds(handle)` reads signed 16-bit reserve at weapon `+0x2C6` and loaded magazine at `+0x2CA`, returning `(reserve + magazine, magazine)`. Zero is a valid known-empty result, including on the first read. Unknown/invalid reads return `(-1, -1)`.
- **Recognized round-fed weapons.** DMR, sniper, assault rifle, magnum, shotgun, needle rifle, Needler, rockets, Fuel Rod, Concussion Rifle, and Grenade Launcher. The updated upstream generic/tag-learning fallback remains for unnamed weapons.
- **Game isolation.** Reach's offsets are guarded against use by inherited Halo 4/H2A readers. Their existing layouts/fallbacks remain separate.
- **Reload support.** `Bot.think` remembers observed magazine maxima every tick, including combat. Existing `reload_between_fights` can request a reload with no visible enemy, loaded rounds at or below 40% of the observed maximum, reserve available, and its reload timer ready.
- **Empty switching.** Known ammo now supplies the existing weapon-selection and rearm logic. The switch message displayed by the player's HUD helped confirm depletion during testing. The implementation reads weapon memory rather than detecting HUD text or icons.
- **Verified live sequences.** DMR 15 loaded / 30 reserve → 12/30 after three shots → 15/27 after reload. Sniper 4/4 → 3/4 → 4/3 → 0/0 at depletion.
- **Limit.** Battery/energy weapons still report unknown depletion. Overheating and permanent battery depletion are separate states. A plasma-pistol screenshot showing 0 energy did not establish an implemented energy reader. Individual round-fed weapons and actual bot reload/switch outcomes still need broader gameplay checks.
- **History/tests.** `3f96e8e`, reconciled with the author's overlapping reader in `ca7eeb0`; `tools/test_reach_ammo.py`, `tools/test_upstream_migration.py`.

### 3.3 Sniper retention and Reach loadout valuation

- **Loaded-sniper retention, shared across games.** `Bot.rearm_point` returns no low-ammo replacement target while the held `sniper` has any known total ammunition remaining. A reserve round awaiting reload counts. This targets the report of a bot abandoning a useful sniper for an AR. Empty rearming and deliberate loadout upgrades are separate decisions. Commit `a731340`.
- **AR/shotgun choice.** Reach AR Short-band proficiency is 0.8 and shotgun is 1.0. Reach's ordinary upgrade gain cutoff is 0.05, allowing the approximately 0.06 gain from DMR+AR to DMR+shotgun. A qualifying nearby shotgun replaces the AR while retaining the DMR. Commit `153d101`.
- **Focus Rifle choice.** Its range tuple is `(0.1, 1.0, 1.0, 1.0)` for Short/Medium/Long/Extreme. Reach's effective rank overrides are Focus 3.6 and DMR 3.5. Commits `05bea4f`, `dab9d6e`.
- **Final pair scores.** DMR+AR 0.91, DMR+Focus 0.92, Focus+AR 0.98, DMR+shotgun 0.97, Focus+shotgun 1.04. Thus an eligible Focus pickup from DMR+AR normally replaces the DMR and keeps the AR. It does not produce the assumed DMR+Focus pair.
- **Why rank alone is insufficient.** `loadout_value` weights the best range coverage in each band and adds a bonus from the highest rank above 3.5. Rank 4+ weapons contribute half coverage to reflect their limited ammunition. `drop_slot` favors known-empty slots, then the replacement that leaves the highest-valued pair. `upgrade_point` also enforces gain, distance, height, and swap cooldown restrictions.
- **Power classification is separate.** Dedicated fetches use map items with value at least 0.8. Raising Focus rank does not automatically classify it as a dedicated power-fetch item.
- **Review/tests.** `brain/bot.py` tables `BANDS`, `BANDS_GAME`, `RANK_GAME`, `UPGRADE_GAIN_GAME`; functions `loadout_value`, `upgrade_point`, `drop_slot`, `choose_weapon`, `rearm_point`; `tools/test_reach_loadout.py`, `tools/test_reach_ammo.py`.

Final effective Reach ranks used by the discussed hierarchy are below. They express AI valuation rather than weapon damage.

| Rank | Weapons |
|---:|---|
| 5.0 | Rockets |
| 4.6 | Spartan Laser |
| 4.5 | Sword |
| 4.0 | Sniper, Fuel Rod, Gravity Hammer |
| 3.8 | Plasma Launcher |
| 3.6 | Focus Rifle |
| 3.5 | DMR |
| 3.0 | Shotgun, Needle Rifle, Grenade Launcher |
| 2.8 | Concussion Rifle |
| 2.6 | Magnum |
| 2.3 | Plasma Repeater |
| 2.2 | Assault Rifle, Plasma Rifle |
| 2.0 | Needler |
| 1.0 | Plasma Pistol |

The Focus tuple lives in the shared name-based `BANDS` table. Its practical normal weapon scope is Reach. The AR, DMR/Focus ranks, and upgrade-cutoff overrides are explicitly keyed by game.

### 3.4 Armor Lock proximity trigger

- Replace both low-shield/recent-hit Armor Lock activation branches with a visible enemy holding a sword or Gravity Hammer within **6 world units, inclusive**.
- The new trigger is independent of the bot's shield percentage, recent damage, and enemy facing. It is in the existing Normal-and-up equipment decision path and covers Demon through its tactics profile.
- Existing grenade, explosive-aim, vehicle, lunge, objective-hold, energy/input, cooldown, and hold/release rules continue to participate. Easy's ability restriction and the Infection-survivor restriction still apply.
- **History/files.** `5620698`; `brain/equipment.py`, `Kit` use decisions; `tools/test_armor_lock.py`.
- **Validation.** Regression scenarios cover full-shield activation, range boundary, visibility, removed low-shield-only behavior, and retained restrictions. Post-change gameplay confirmation is pending.

### 3.5 Breakpoint tower/bridge sight correction

- **Scope.** Only `maps/reach_dlc_invasion`, the Breakpoint map key.
- **Problem.** A thin overhead export surface, with no real ground in the gap beneath it, caused clear tower-to-bridge lines to be treated as blocked terrain.
- **Implementation.** `maps/reach_dlc_invasion/sight_open.json` configures `Terrain.set_open_under`, loaded by `brain/maps.py`. Sight, shot, and crosshair rays treat the specified air beneath the overhead strip correctly. Walking/fall/aircraft floor data use their existing handling.
- **Evidence.** Replay of relevant facing/nearby enemy positions improved open lines from 13/138 to 46/138. Remaining ledge-lip and low-wall obstructions remained physically blocked in the model.
- **History/tests.** Collaborator commit `1aa3339`, preserved through migration; `tools/test_breakpoint_sight.py` verifies the correction is necessary and map-scoped. Live recheck remains pending.

## 4. Halo 4 changes

### Animated head and matched view geometry

- **Problem.** The Halo 4 position reported by the reader did not share Reach's feet-based height convention. Reusing a generic head offset could miss the animated head, particularly while strafing or crouching.
- **Calibration.** Two read-only capture sessions on Bloodline/Adrift covered stationary, crouched, strafing, elevated, bot, and human poses. All 2,780 saved poses passed the new decoder's checks.
- **Reader.** `LiveH4F.h4_spartan_pose()` supports the captured `halo4.dll` Spartan 120-node layout. The descriptor is at unit `+0x1BC`, observed array offset `0x145C`, transform size 52 bytes, head node 54. The local target-head marker is approximately `(-6.94e-8, 0.02300628, -0.006868857)`.
- **Shooter endpoint.** Unit `+0xD50` supplies the cached view point associated with the model base at `+0x64`. Snapshot state now carries `view_pos` alongside `head_pos`.
- **Matched pair.** `live_head_ray` requires valid on-foot shooter/target geometry before using the new pair. `head_solution` supplies a consistent fallback if the supported pair is incomplete. `Aim.step` accepts `origin` and a world-space `target_point`, avoiding a second generic head-height addition.
- **Consumers.** Ordinary protected head tracking, final Legendary/Demon DMR/sniper correction, lower-tier intended sniper hit/miss shots, perception, and firing visibility use the consistent endpoints. Material/cover checks remain part of the decision.
- **Geometry limit.** The measured cached view point is validated as aim/view geometry. Physical projectile spawn/muzzle equivalence for every weapon has not been established.
- **History/files.** `524af62`; `brain/live.py`, `brain/core.py`, `brain/bot.py`, `tools/live_bots.py`, `docs/HALO4_HEAD_AIM_2026-11-06.md`.
- **Tests/status.** `tools/test_h4_head_aim.py` covers decoder guards, stance, tracking, final shots, movement rotation, fallback, occlusion, perception, and reader wiring. Recorded-pose replay passed. Post-fix live bullet-hit improvement remains unconfirmed.

## 5. Other Halo games and campaign/Firefight scope

| Game/context | Current custom scope |
|---|---|
| Halo CE, Halo 2, Halo 3 | Shared fixed-difficulty changes, eligible `sniper` percentage policy, loaded-sniper rearm exemption, director priorities, and shared tooling can apply where their readers/modes expose the required state. Separate game-specific pose calibration was outside this work. |
| Halo 3 ODST | Shared supported brain/tool behavior applies. Campaign/Firefight escort entry points explicitly recognize Demon. Validate the actual mode/reader before assuming multiplayer features apply. |
| Halo 2 Anniversary | Existing reader remains separate. The Halo 4 pose decoder is guarded to `halo4.dll`; H2A is `groundhog.dll`. Reach ammo offsets must not leak through class inheritance. |
| Reach Firefight/campaign escorts | Demon is accepted explicitly. `tools/escort_bots.py` retains its existing high-tier escort parameter row, `(0.15, 0.012)`, for Demon. It is a distinct execution path from the normal multiplayer profile. |
| All supported games | The shared loop, native inputs, engine weapon mechanics, and game/mode capability checks still bound the custom decisions. Live testing has concentrated on Reach and Halo 4. |

The shared sniper policy matches the internal name `sniper`. It does not automatically cover Beam Rifle, Binary Rifle, Focus Rifle, vehicle guns, or every weapon called a sniper in conversation.

## 6. Shared difficulty, awareness, and combat changes

### 6.1 Independent Demon and restored Legendary

The collaborator first added Demon as a label over the tuned Legendary brain in `23e1149`. Later `6a31238` made Demon an independent real tier and restored Legendary's base attributes, with protected precision exceptions. `f022024` then set Legendary's ordinary flick overshoot to zero again.

| Display name | Internal profile | Key guard |
|---|---|---|
| Easy | `novice`, extra None | Fixed Easy |
| Normal | `average`, extra None | Fixed Normal |
| Heroic | `strong`, extra None | Fixed Heroic |
| Legendary | `top`, extra None | `fixed_high`, excluding Demon |
| Demon | `demon`, extra None | `fixed_demon`, also `fixed_high` |
| Scaling | `top`, populated `extra` | Separate `brain/scaling.py` builder |

Keep `profiles.fixed_high`, `fixed_demon`, and `precision_profile` semantics when porting. A broad `tier == "top"` customization can accidentally change Scaling.

| Attribute | Legendary base now | Demon now |
|---|---:|---:|
| Reaction | 154 ms base | 0 ms override |
| Decision interval | 100 ms base | 10 ms override |
| Tracking sample interval | 80 ms base | 1 ms override |
| Aim lag | 45 ms base | 1 ms override |
| Aim error | 0.006 rad base | 0 override |
| Flick overshoot chance | 0 | 0 |
| Leading parameter | 0.8 base | 0 override |
| Flick timing factor | 0.7 base | 0.05 override |
| Turn speed | 1000 degrees/s | 1000 degrees/s |
| Memory | 10 s base | 10 s base |
| Teamwork | 0.95 base | 0.95 base |

Ordinary fixed-profile numbers generally receive ±10% seeded variation. Legendary decisions also multiply by 0.8–1.3 per decision. Demon precision/reaction/decision overrides are applied after variation, with no per-decision interval jitter. Turn speed is not profile-jittered. Higher/lower values are timing or weighting parameters, not measured engine hit rates.

Legendary head-directed and vehicle/turret aim explicitly use an independent precision profile, retaining 0 aim error, 1 ms lag/tracking, zero overshoot/leading parameter, 0.05 flick factor, and 1000 degrees/s turn setting. `Aim` switches its active profile and clears stale aim samples when entering that context. The firing-alignment check uses that active profile too. Legendary's target recognition and decision delay still use its restored base profile.

Demon precision and protected Legendary contexts suppress the ordinary randomized lead variation, tremor, and own-motion prediction. The configured zero leading parameter warrants reviewing moving projectile/vehicle behavior before claiming physical accuracy. This tuning primarily grew out of the owner's DMR/sniper tests.

Tier-dependent tables now include explicit Demon entries for reaction, turn, sharpness, craft, pressure, headshot behavior, ram error, dry-fire safeguards, and callout timing. Demon has its own profile rows rather than mutable aliases to Legendary. Mixed retains its standard composition. Seven personality presets still cover rusher, camper, flanker, objective-focused objector, grenade-focused spammer, grudger, and sniper.

### 6.2 Vision and radar

- **Legendary.** 120-degree horizontal detection cone, central half-angle 50 degrees, outer half-angle 60 degrees. Recognition at the edge uses a 1.5 multiplier.
- **Demon.** 140-degree cone, 70 degrees either side. Its central and peripheral limits coincide and its edge multiplier is 1.0. Combined with zero configured reaction, there is no extra edge timer.
- **Other ordinary profiles/Scaling.** Existing cone and peripheral rules apply. The shared sight limit remains 80 units, with existing very-close recognition exceptions, line of sight, camouflage/blindness, and memory handling.
- **Demon radar.** Always notice an eligible motion-tracker contact. Eligibility still needs enabled tracker, distance below 25 units, horizontal speed above 0.6, uncrouched enemy, and no active jamming. The resulting belief is radar information rather than visual confirmation.
- **Other radar.** Ordinary notice uses `profile.radar * 0.15` per eligible update, with normal profile variation. The base radar weight of 1.0 is not a 100% contact-notice probability. Demon uses an explicit deterministic branch rather than inflating this weight.
- **History/tests.** Baseline vision retained, Demon expansion/radar override in `f022024`; `tools/test_demon_awareness.py`, `tools/test_difficulty_separation.py`.

### 6.3 Sniper intended hit/miss percentages

| Fixed difficulty | Intended sniper hit roll |
|---|---:|
| Easy | 10% |
| Normal | 25% |
| Heroic | 50% |
| Legendary / Demon | Their existing precision path, outside the percentage policy |
| Scaling | Its separate adaptive aiming rules |

- **Scope.** On-foot shooter with internal weapon name `sniper` against an on-foot target. The policy retains perception/reaction, decision, movement, cadence, and safety gates.
- **One accuracy mechanism.** Eligible shots use precise head aim and bypass competing random aim error and loose early/follow-through firing. Intended misses aim beside and above the target while still firing.
- **Acknowledgement.** The roll survives rejected trigger requests and post-grenade retries. Magazine change clears the retained outcome. Unknown magazines use a cadence-bounded fallback.
- **Action conflicts.** Melee, grenade, and weapon-switch conflicts suppress the firing request. Intended misses are excluded from blocked-sightline learning so the bot does not learn a false wall.
- **Limit.** These are intended shot outcomes, not guaranteed engine collision, headshot, or kill percentages.
- **History/tests.** `0c99e08`, migration retention, Halo 4 endpoint integration; `tools/test_sniper_accuracy.py`, including 10,000-consumed-round distributions per affected tier.

### 6.4 Grenades, retry firing, and body-part rays

- High fixed tiers keep tactical grenade uses but suppress ordinary fight-opening and random visible-enemy pressure throws. `LEGENDARY_GRENADES` remains enabled and `fixed_high` extends the shared policy to Demon.
- `POST_GRENADE_RETRY = 2.0` is a retry window. `Bot.retry_after_grenade` retries while the weapon recovers, alternates release/press for semiautomatics, and uses magazine consumption when available to acknowledge actual resumed gunfire.
- Retry requests alone do not count as confirmed shots for learning blocked lines. Unknown-magazine recovery remains bounded but less directly observable.
- `Terrain.point_los` and `target_parts` allow actual origin/head/chest rays using the author's sight versus bullet material distinctions. Seeing through glass/fences does not by itself establish a bullet-clear shot.
- Much of this work was already present in `c9a9b1f` and reconciled with the new installer in `ca7eeb0`. Long post-grenade recovery reports still need controlled gameplay measurement.

## 7. Shared team director and vehicle changes

### 7.1 Power-weapon calls

- Map item `kind == "weapon"` and value at least 0.8 determines dedicated power-fetch classification. Loose weapons and known respawn timers are considered separately.
- Fixed Legendary and Demon can receive calls within **80 units**. Other eligible tiers and Scaling retain **40 units**. Height difference must remain below **6 units**.
- Loose high-tier fetch lifetime is at least 25 seconds or `distance / 2.3 + 10` seconds, whichever is longer. This is a travel allowance, not a delay before leaving. Timed-spawn deadlines retain their own handling.
- New calls rank **Demon → Legendary → Heroic/Scaling → Normal**. Equal weights use distance. Easy retains its existing lack of team-plan eligibility.
- Carrier, vehicle occupancy, urgent objective, already fetching, already carrying a classified power weapon, timer knowledge, and Invasion detour restrictions continue to filter eligibility. A committed valid fetch does not get stolen merely because a higher tier appears later.
- **History.** `2b41b03` adds the original Legendary range/allowance. `6a31238` includes independent Demon. `f022024` adds ordering. `bfbb62d` ties Scaling to Heroic and reserves fetches before new vehicle calls.
- **Entry/test.** `Director.power_runs`; `tools/test_legendary_power_fetch.py`.

### 7.2 Power vehicles, gunners, and precedence

| Call type | Final priority |
|---|---|
| Power weapon | Demon → Legendary → Heroic/Scaling → Normal |
| Power-vehicle driver | Demon → Legendary → Heroic/Scaling → Normal |
| Gunner | Demon → Legendary/Heroic/Scaling → Normal |

- A power vehicle uses the existing `not vehicles.taxi_ok(kind)` classification, such as Banshee, tanks, Chopper, Gauss Hog, or Rocket Hog. Standard chaingun Hog/Falcon transport and Ghost light-harasser classification are distinct.
- Vehicle role and nearest vehicle selection are retained. For the selected power vehicle, choose the highest-priority eligible driver. Ordinary free crew reach is **45 units**. Nearby eligible objective-job bots can compete within their original **15-unit** limit.
- Candidate distance/availability filters run before priority ranking. An unreachable distant Demon cannot block a nearby eligible lower-tier bot.
- Role passes reserve weapon fetches before vehicle orders. Vehicle crews are selected before honked/direct/aboard gunner calls. A Demon fetching a weapon is excluded from new driver jobs. A Demon with a fetch or driver order is excluded from new gunner and gunner-pickup calls. Drivers of every tier are protected from subsequent seat calls during that pass.
- An eligible Demon without a reserved power job can still receive the first gunner call. Same-weight gunner candidates are selected by distance.
- Priority applies through direct gunner calls, nearby driver/rider calls, honked gunner calls, and driver travel to pick up a gunner. Existing crew commitments and rider-eligibility rules participate as before.
- Typical limits are direct gunner **25 units**, honk **20**, ordinary aboard call **12**, and ground-driver gunner pickup **60**. Ordinary passenger/ferry selection retains its separate rules. Aircraft have their existing extended call rules.
- **Files/functions.** `profiles.resource_priority`, `gunner_priority`; `Director.assign_roles`, `vehicle_orders`, `crew_orders`, `rider_calls`, `honk_orders`, `gunner_pickup`, `gunner_available`.
- **History/tests.** `f022024`, `bfbb62d`; `tools/test_resource_calls.py` covers tied weights, range fallback, fetch/seat contention, vehicle/honk contention, driver protection, and retained ordinary transport selection.

### 7.3 Warthog behavior retained from the existing/upstream mod

These scenarios describe the code the reviewer must integrate with. Our latest work changes call weights and job precedence, rather than supplying a complete new driving controller.

- Take a standard Hog as assigned transport or for a long on-foot trip, including mode-specific race/Invasion use.
- Wait briefly for crew, drive to an eligible gunner, taxi riders, fetch a carrier, park a CTF getaway ride, hunt an enemy carrier, escort ours, or patrol.
- A crewed standard Hog circles targets at **3.5–14 units**, usually full throttle, steering side-on and periodically reversing circle direction. Rocket Hog uses **15–30** and Gauss **15–35**.
- An uncrewed standard Hog can attempt eligible splatters within **18 units**, otherwise continue its trip. Light-vehicle rams and dangerous-weapon/Armor-Lock exclusions remain.
- Evade nearby boarders, EMP threats, active Armor Lock, aimed anti-vehicle weapons, and tank barrels using reaction/juke gates. Reach does not use the Halo 2/3 shield-down driver retreat branch.
- Ground navigation uses vehicle traversable ground and human-road preference during travel. Combat circling and several emergency maneuvers issue steering directly.
- A taxi can dismount at its destination or at the end of usable vehicle ground. A working patrol/hunt/escort vehicle usually continues to another position. A wedged ground vehicle tries two angled reverses before exit, with failed-exit retry handling.
- `vehicles.gunner_gun` supplies turret ballistics rather than the rider's handheld gun. `gun_height` supplies a turret mount height, including **0.92** for the standard Hog chaingun. Fixed Legendary/Demon turret aiming receives the protected precision context.
- **Open issue.** A firing-height offset is already present, but a calibrated dynamic muzzle transform has not been verified. The driver also considers `gunner OR riders >= 2` when deciding it is crewed, which can misclassify a passenger-only Hog. Review this when diagnosing circling or missed shots.
- **Review files.** `brain/bot.py` functions `drive`, `crew_target`, `vehicle_pick`, `ram_ok`, `evade`, `crew_coming`; `brain/vehicles.py`; `brain/director.py` functions `vehicle_jobs`, `ferry_orders`.

## 8. Collaborator LiDAR vehicle recording and viewer support

Published collaborator commit **`a57893f`** adds vehicle-drive recording to LiDAR mode and exposes it in the 3D viewer. Normal matches already had the underlying RideWatch integration.

- `tools/lidar.py` mapping-mode loop now updates `RideWatch` for vehicles driven/flown by people and bots. Drive and flight data merge into `maps/<map>/rides.json` during the mapping save cycle, approximately once a minute and at match end. Errors are logged without terminating mapping.
- Ground samples retain person versus bot counts. Navigation accepts a cell driven by a person once or by bots twice. Human driving cells are also preferred roads. Flight samples retain height statistics used for aircraft travel/low-flight handling.
- `RideWatch` exposes a bounded live feed, up to **300,000 samples**, with kind codes for person drive, bot-only drive, and flight. `since()` supports incremental consumption and handles trimmed older samples.
- `Hub.live` and the `/live` endpoint accept `rsince` and return `rseq`, allowing the viewer to retrieve just new drive samples. `rides_view` loads stored paths using the same drive thresholds as navigation and mean flight heights.
- `tools/lidar_view.html` adds the **Vehicle drives** layer, **V** shortcut, drive counts, legend, and distinct person/bot/flight rendering. Driven areas can frame the view even before walking scans exist there.
- Existing `brain/maps.py:rides_layers` and `Terrain._build_vnav` consume the recorded data. Human-road edge cost is **0.4 times** the ordinary length. This favors those roads, while painted drive cells define allowed vehicle ground. The current feature does not serialize a required sequence of vehicle waypoints.
- **Validation from the collaborator.** Eight new tests, LiDAR self-check, stored Park view showing 459 person-drive cells, V-toggle browser check, and simulated live Warthog streaming. Actual recording in a live LiDAR match remains pending.
- **Files.** `tools/lidar.py`, `tools/lidar_view.html`, `tools/test_lidar_drives.py`; related existing consumers in `brain/maps.py`, `brain/terrain.py`, `tools/paint.py`.
- **Deferred by the collaborator.** Paint-page eraser and explicit vehicle-size tags for recorded drives.

## 9. Native Demon menu, reporting, and compatibility

- Demon is native roster tier **5**. Scaling remains roster tier **4**.
- The shared “for everyone” difficulty enumeration is Easy 0, Normal 1, Heroic 2, Legendary 3, Mixed 4, Scaling 5, Demon **6**. The two enumerations serve different structures.
- `botcore` launches the Python tier string `demon`. `tools/botctl.py` accepts it in roster settings. Native BOTS controls, footer/quick setup, selected-bot inspector, lobby tile, crimson styling, and five-chevron Demon presentation were updated.
- Trace metadata, Observer, player stats, match export, and guide display Demon explicitly. Campaign/Firefight escort code recognizes the tier too.
- Preserve old saved difficulty/roster mappings. An older binary interpreting a newer Demon setting may misinterpret or fall back, so source and native menu versions must be considered together.
- **History.** `23e1149` implements native/menu/reporting support. `56ad573` records the collaborator's successful local `native\build.bat demon` and owner-confirmed Demon selection in game. `6a31238` completes the independent Python brain tier.
- **Build status.** The local Demon DLL built successfully with Visual Studio Build Tools 2022. A subsequent panel-art step lacked Pillow on PATH Python. The menu itself was confirmed working by the owner. The local DLL remains excluded from source publication.
- **Files.** `native/botcore.cpp`, `native/bots_panel.cpp`, `native/bots_panel.h`, `native/overlay.cpp`, `native/shared.h`, `tools/botctl.py`, `tools/play.py`, `tools/escort_bots.py`, `brain/tracefmt.py`, `tools/observer.py`, `tools/observer.html`, `tools/player_stats.py`, `tools/match_export.py`, `tools/guide.html`.

## 10. Upstream installer migration and general improvements

The owner installed the author's new release, then we merged reviewed customization blocks into that installed source. `6433bb3` records the installed import and `ca7eeb0` records the custom integration. Preserve both histories when transplanting these changes.

- Retain the author's launcher/updater, Firefight lifecycle changes, map/variant identification, pickup handling, navigation/vehicle improvements, hazard-aware planning, and final melee-facing/teammate validation from 0.2.2-s181.
- Reconcile the overlapping Reach ammo reader while retaining the author's tag/magazine naming caches and fallback handling.
- Combine hazard-aware navigation and melee validation with custom magazine observation, post-grenade recovery, intended sniper rolls, and final animated-head correction in `Bot.think`.
- Preserve newer walked-cell/navigation behavior alongside precise body-part rays and the Breakpoint correction.
- Keep species-specific loadout palettes separate, including Spartan versus Elite palettes in Invasion.
- Native binaries delivered by the installer and the updater remain part of the installed runtime. A later upstream installer can replace customized source again, so future updates need a reviewed merge.
- These retained author features are integration dependencies, not separately authored custom features from our team.

Recovery material on the owner's machine includes the pre-installer full folder backup at `F:\Proving Grounds Backups\Project Proving Grounds_2026-11-06_163131` and the installed-source snapshot at `logs/migration_0.2.2-s181_2026-11-06/installed`. The full backup's 12,676 files were SHA-256 verified before installation. These local materials are separate from the source repository.

## 11. Validation and evidence ledger

At the approved combined source candidate, all **95 tests passed with the local fixtures**. An isolated committed-source snapshot passed **92**, with **3 fixture-dependent skips**. All **91 brain/tools Python source files** and the LiDAR viewer's JavaScript passed syntax checks. Git whitespace checks passed. This handoff uses those release results rather than claiming new gameplay validation.

| Test file | Main regression protection |
|---|---|
| `tools/test_reach_ammo.py` | Recorded ammo sequences, known-empty/unknown/invalid reads, game isolation, reload/empty switching, loaded-sniper retention |
| `tools/test_reach_loadout.py` | Shotgun/Focus pair scores and replacement choices, difficulty/rank isolation, pickup restrictions |
| `tools/test_breakpoint_sight.py` | Breakpoint correction required and scoped |
| `tools/test_sniper_accuracy.py` | Intended percentages, retained rolls, action conflicts, tracking/final aim, movement, false-wall avoidance |
| `tools/test_upstream_migration.py` | Hazard planning, melee safety, ammo caches, retained head decoding, species palettes |
| `tools/test_h4_head_aim.py` | H4 pose/view validation, world-space paired aim, obstruction, fallback, live-reader wiring |
| `tools/test_armor_lock.py` | Sword/hammer activation and retained restrictions |
| `tools/test_demon_difficulty.py` | Demon profile/native/roster/report compatibility |
| `tools/test_difficulty_separation.py` | Independent tiers, stock Legendary except current overshoot, protected precision, scheduling, Scaling isolation |
| `tools/test_demon_awareness.py` | Cone boundaries, zero configured edge delay, deterministic radar eligibility restrictions |
| `tools/test_legendary_power_fetch.py` | Range/time allowances, ordering, eligibility, cancellation, timed spawn behavior |
| `tools/test_resource_calls.py` | Resource/gunner rank ties, precedence, range fallback, driver protection and transport behavior |
| `tools/test_lidar_drives.py` | Vehicle drive/flight feeds, stored thresholds, trimming, endpoint, invalid input, viewer wiring |

Three fixture-dependent skips concern local evidence unavailable in a source-only snapshot. Raw captures, fixture exports, recordings, machine settings, and learned maps are excluded from publication. Inspect actual skip output in your environment before interpreting a changed total.

Local evidence directories include `logs/ammo_probe`, `logs/h4_head_probe_2026-11-06`, `logs/h4_bot_aim_probe_2026-11-06`, and the migration snapshots. Existing evidence documents describe their findings. Old “Unreleased”, version, or “not uploaded” paragraphs in chronological notes reflect when they were written. Use current source and the published head above to determine final settings/status.

## 12. Open issues and discussion-only proposals

| Item | Current state / next review target |
|---|---|
| Battery/energy depletion | Still unknown to the custom reader. Determine actual energy state independently from overheat, then use it for switch/rearm decisions. |
| Reach Warthog missed shots | Existing gun-ballistics/mount-height and protected precision code is present. A complete gameplay-confirmed fix has not been established. |
| Live dot versus physical shot | Hypothesis is an origin/angle mismatch similar to the earlier head-height issue. Verify exactly what the debug dot visualizes, then compare dot, intended target, turret transform, and actual impacts while parked, moving, turning, and tilted. There is no published new turret calibration commit. |
| Passenger-only Hog treated as crewed | Review `gunner OR riders >= 2` in `Bot.drive` against actual seat flags. Identified in code review, still an open behavior issue. |
| Strict owner-created vehicle routes | Discussed, not implemented. Owner wants to retain driver scenarios while using recorded/created routes. The suggested design uses roads for travel and allows pickup approaches, combat maneuvers, emergencies, and recovery to deviate, with explicit strict waypoint routes as an optional authored mode. |
| Per-game independent brains | Discussed and deferred by the owner. Current code remains shared with per-game reader/table/geometry branches. |
| Broader power/sniper retention | The implemented sniper exemption is specifically low-ammo rearming. It is not an absolute ban on every deliberate replacement decision. |
| Projectile leading | Existing weapon-specific projectile/charge/beam logic was investigated. A blanket new leading implementation was outside the completed changes. Review zero-leading precision contexts when evaluating projectile weapons. |
| H4 post-fix accuracy | Pose replay and regressions passed. Run fresh stationary/strafe/crouch bullet-impact tests. |
| Post-grenade pauses | Retry delivery is implemented. Actual engine weapon recovery and rejected-input timing still need measurement. |
| Live tests of final priority/awareness | Validate fresh-match behavior after restarting the bot process, including competing call types and protected objectives. |
| LiDAR follow-ups | Real mapping-match drive recording, eraser, and vehicle-size-specific authored drive tags remain follow-ups. |

## 13. Setup, operation, and integration workflow

### Access and source checkout

The repository is private. The owner grants the reviewer's own GitHub account or coding integration access. Use ordinary authorized Git authentication. A source clone needs the mod's installed runtime, native build outputs, and required map assets before it can function as a complete installation.

```powershell
git clone https://github.com/IEatOreos/ProvingGroundsOreo.git
Set-Location ProvingGroundsOreo
git fetch origin
git log --oneline -8
git switch -c review/custom-bot-integration
```

On the owner's current machine, Git was found at the following path despite being absent from PATH in some sessions.

```powershell
$taskGit = 'C:\Users\marsh\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe'
& $taskGit status --short --branch
& $taskGit remote -v
& $taskGit log -5 --oneline
```

Use the existing working tree on that installation. Inspect local edits and coordinate with the owner before switching files under an active match. Prefer a separate checkout for integration review.

### Brain and mapping entry points

The normal owner-facing entry point is the installed launcher/BOTS panel. For developers, the current parser supports the following examples. Team counts include human players. A compatible running match and native installation are required.

```powershell
.\python\python.exe -I tools\play.py --game reach --red 4 --blue 4 --tier demon
.\python\python.exe -I tools\play.py --game h4 --red 4 --blue 4 --tier top
.\python\python.exe -I tools\lidar.py --view reach_dlc_invasion --open
```

`play.py --roster <ini>` uses the BOTS panel roster. `--tier` can be a comma-separated list. `--lidar N` is the existing mapping-mode launcher option. Confirm active processes before starting another brain loop. Python changes take effect after restarting the bot process/launcher. Native menu changes require the matching build.

### Regression entry point on the owner's embedded Python

This example keeps temporary files in ignored workspace logs and exits nonzero on a failed suite. The LiDAR endpoint test needs localhost socket access. Source-only checkouts can skip fixture-dependent tests.

```powershell
@'
import sys
import tempfile
import unittest
from pathlib import Path

root = Path.cwd()
sys.path[:0] = [str(root), str(root / 'tools')]
temp_root = root / 'logs' / 'test_tmp'
temp_root.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(temp_root.resolve())
suite = unittest.defaultTestLoader.discover(str(root / 'tools'), pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
'@ | .\python\python.exe -B -
```

### Integration safeguards required by the owner

1. Read `AGENTS.md`, `CUSTOMIZATIONS.md`, `CUSTOM_CHANGELOG.md`, and `docs/CUSTOM_RELEASE_WORKFLOW.md` before editing.
2. Preserve upstream attribution and the collaborator's commit identities and intended behavior. Fetch/review local and remote histories before each push. Integrate incoming work with a normal merge and review overlapping behavior.
3. Port reviewed feature blocks into the target author's current source. Avoid applying the old initial snapshot wholesale over a newer mod.
4. Preserve game guards, unsupported-layout fallbacks, Scaling separation, and Legendary/Demon head/turret precision while reviewing each subsystem.
5. Inspect staged/unstaged/untracked work and outgoing commits. Stage exact intended files. `user/`, local fixtures, and learned wall files currently exist untracked and must not be swept into a source upload.
6. Run the affected tests and describe remaining gameplay checks. Record the exact edits and validation in `CUSTOM_CHANGELOG.md` and make a local commit per this repository's workflow.
7. The owner approves every future GitHub push, tag, release, or uploaded artifact. Prior approval of `0.2.2-custom.4` covered that publication only. A new teammate feature discovered during preparation needs scope review.
8. Recheck concurrent local/remote changes immediately before publication and push the reviewed commit explicitly. Preserve personal data and the existing installed runtime.

## 14. Complete published custom history through the review baseline

All entries below are reachable from the verified published head. Earlier intermediate tuning can be superseded by the later commits described above.

| Commit | Purpose / interpretation |
|---|---|
| `c9a9b1f` | Snapshot the already-customized installed 0.2.1 source and establish release workflow. Earlier custom aim/grenade/vision behavior is retained here. |
| `3f96e8e` | Reach live total/magazine ammo and combat magazine observation. |
| `a731340` | Preserve held snipers with ammunition against low-ammo rearming. |
| `428553a` | Initial developer handoff and publication clarification. |
| `1aa3339` | Collaborator's Breakpoint overhead sight/shot correction. |
| `2b41b03` | Legendary power-weapon call radius and travel allowance. |
| `153d101` | Reach AR/shotgun loadout preference and upgrade cutoff. |
| `05bea4f` | Requested Focus Rifle range tuple. |
| `7cac9f7` | Preserve collaborator commits during future pushes. |
| `dab9d6e` | Reach Focus 3.6 / DMR 3.5 ranks and custom source update 2. |
| `f929768` | Historical zero Legendary reaction, now retained by Demon while Legendary has restored base reaction. |
| `12145d5` | Historical 10 ms Legendary decisions, now retained by Demon while Legendary has restored decision timing. |
| `0c99e08` | Lower fixed-tier intended sniper hit/miss rolls with precise aim and acknowledgement. |
| `4d4d847` | Prepare 0.2.1 custom source update 3. |
| `6433bb3` | Import source left by installed upstream 0.2.2-s181. |
| `ca7eeb0` | Merge reviewed customizations into the new installed source. |
| `524af62` | Halo 4 animated head and matched view origin. |
| `23e1149` | Initial Demon native menu/reporting/profile-label implementation. Later brain separation supersedes the label-only alias. |
| `5620698` | Six-unit sword/hammer Armor Lock activation. |
| `ba198f3` | Prepare 0.2.2-custom.3 source publication. |
| `56ad573` | Record successful local Demon native build and owner in-game confirmation. |
| `dde7dcc` | Require reviewing local and remote teammate work before publication. |
| `6a31238` | Independent Demon brain tier, restored Legendary base stats, protected head/turret precision. |
| `f022024` | Legendary zero overshoot, Demon vision/radar, resource priorities. |
| `bfbb62d` | Final owner-clarified Scaling/gunner weights and Demon power-job precedence. |
| `a57893f` | Collaborator's vehicle-drive recording and LiDAR 3D-view feature. |
| `9a4cf17` | Prepare and publish approved combined 0.2.2-custom.4 source update. |

Use `git show <commit>` for an exact patch and `git log --follow -- <path>` for a file's history. Compare against the target mod's actual base before choosing cherry-picks, because the installed-source import and integration commits overlap prior custom functionality.

## 15. Companion references

- [Current customization inventory](../CUSTOMIZATIONS.md)
- [Chronological implementation and validation notes](../CUSTOM_CHANGELOG.md)
- [Upstream migration provenance](UPSTREAM_MIGRATION_2026-11-06.md)
- [Halo 4 pose/aim evidence and scope](HALO4_HEAD_AIM_2026-11-06.md)
- [Historical initial developer handoff](../DEVELOPER_HANDOFF_2026-11-05.md)
- [Owner's release/collaboration workflow](CUSTOM_RELEASE_WORKFLOW.md)
- [Upstream architecture and tool guide bundled with this source](CODE_GUIDE.md)
- [Published commit history](https://github.com/IEatOreos/ProvingGroundsOreo/commits/main)

This handoff is a local documentation deliverable prepared after the published review baseline. Its own commit and publication status should be checked separately from `9a4cf17`.
