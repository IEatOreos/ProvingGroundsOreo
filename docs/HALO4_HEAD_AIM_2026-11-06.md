# Halo 4 animated head aiming

Custom source version: 0.2.2-custom.2, on installed upstream 0.2.2-s181.

## Evidence

Two read-only live captures on Bloodline (ca_blood_crash) and Adrift (wraparound) established the Halo 4 Spartan model's animated target_head marker and a paired unit view point. Calibration included stationary, strafing and crouched poses. The second capture included a fixed Legendary DMR bot, movement, elevation changes and deaths. These are observations of pose/aim, not measurements of each bullet's collision or a controlled post-fix accuracy result.

Local evidence is excluded from Git: logs/h4_head_probe_2026-11-06 and logs/h4_bot_aim_probe_2026-11-06. Replay covered 1,154 calibration poses and 1,626 raw human/bot poses. Every one of these 2,780 poses passed the new decoder's guards.

The exported Halo 4 Spartan rig has 120 nodes and target_head on node 54, with local marker (-6.9422384e-8, 0.02300628, -0.006868857). The captured node-array descriptor is at unit +0x1BC; its observed offset is 0x145C, and each transform is 52 bytes. The reader follows the validated descriptor rather than assuming a fixed node-array address.

Standing target_head was roughly 0.247 units above the position returned by the Halo 4 reader. Strafing shifted it horizontally and vertically; crouched samples were near that reported position. Thus the position is not interchangeable with the feet-based generic aim reference.

Unit +0xD50 provides a cached view point that follows the model base at +0x64. It was approximately 0.60 above the base when standing and 0.42 when crouched, with movement/elevation variation in the bot capture. This is empirically validated view geometry. It is not independently verified as the physical muzzle/projectile spawn for every Halo 4 weapon. Post-fix bullet accuracy still requires gameplay validation.

## Implementation and scope

- LiveH4F.h4_spartan_pose runs only for halo4.dll and the supported 120-node layout. The caller only requests pose data on foot. It rejects incomplete reads, invalid transforms/scales, nonfinite coordinates and points inconsistent with the unit/model base.
- The live snapshot carries head_pos plus view_pos. A valid pair is required at both shooter and target before using the new Halo 4 ray. Unsupported/partial models retain the legacy pair; Reach's existing head correction retains its own origin.
- Aim.step accepts an explicit world-space target_point and origin. It does not add the generic head height a second time. Existing difficulty error and timing remain except where the pre-existing precise sniper policy bypasses them.
- Final DMR/sniper corrections and percentage-sniper outcomes use the same paired origin/target. The existing movement rotation and shot-roll persistence remain.
- Perception and firing check world-space head rays through the existing terrain material and barrier handling. A visible head behind bullet-proof geometry does not automatically permit a shot.
- No global eye() change, chassis position rewrite, Reach/H2A rig change, native/DLL change, cadence increase, stat bonus, timing change or accuracy-threshold change is included.

## Validation

All 50 regression tests pass; all 85 current Python source files compile in memory. New tests cover standing/crouched decoding, wrong DLL/rig/offsets, malformed reads, NaN and invalid transforms, paired final aim, movement direction, precise and ordinary tracking, sniper hit outcomes, Reach/partial-pair fallback, head visibility and obstruction, perception and the actual Halo 4 players() wiring. The prior placed.py unclosed-file warning remains.

MCC was closed before implementation, so no post-fix live kill-rate improvement is claimed. Restart the Proving Grounds launcher/bot process and test standing, strafing and crouching in a fresh Halo 4 match. In particular, verify both accuracy and cover handling before treating the change as gameplay-confirmed.
