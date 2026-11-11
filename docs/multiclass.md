# Multi-class version: plan and status

Goal: one page for the whole group (Warrior, Druid, Warlock, Mage, Hunter, Paladin, Shaman, and Priest and Rogue after), at every level, with:

- questing speed (kills per hour, rest included);
- the dungeon role (damage, tank, healer survival);
- upgrades ranked by effort, from items each class can wear at its level;
- the combat log critique;
- a group view.

Class combat runs on MythicSim's Forever engine (MIT), compiled to WebAssembly. Everything around it is ours.

## Pieces

| Piece | Where | Status |
| --- | --- | --- |
| Item data, all classes | `data/items_all.json`, compacted by `tools/build_items_all.py` into `src/mc/items.js` | Done. 8,643 items, 8,163 kept after the raid-only filter |
| Class stats, spell ranks, pets | `data/classes/` | Done |
| Talent trees, leveling routes, level 60 builds | `data/talents/`, `data/routes/` | Done. Routes checked for legality in `tools/build_mc_data.py` |
| Class data for the page | `tools/build_mc_data.py` makes `src/mc/classdata.js`: base stats per race and level, trees, routes, rotation presets, spec templates | Done |
| Engine in the browser | `engine-wasm/` wraps `vendor/mythicsim-forever-engine` (pinned b3c5eb6) with `ws_alloc`, `ws_sim`, `ws_out_ptr`, `ws_out_len`. Built by `tools/build_engine.sh` into `engine-wasm/engine.wasm.gz` (5.6 MB), which is committed | Done. Matches the native build exactly. Each run needs a fresh instance: a second run in the same instance traps |
| Request builder | `src/mc/request.js`: class, race, spec, level, talents from the route, gear, a character sheet from our class data, level-dependent class options, and a target from the client mob tables | Done for every spec at levels 1 to 60. Tank specs get `raid.tanks` and a target that swings at them; presets get a low-level filler where their own is not learned yet |
| Typical gear for a level | `src/mc/gear.js` `typicalGear()` | Done. Rough stat weights per style, easy sources only, weapon types per spec where the rotation needs them |
| Check of every spec | `test/mc_levels.js` | 162 runs at levels 10 to 60 and 162 at 1, 2, 5, 8, 9 and 10: no failures. The drops left are explained below |
| Questing model for all classes | `src/mc/quest.js`: engine damage per second over the kill time, plus our damage-taken, resting and walking loop | Done |
| Page | `src/mc/app.html`, `app.js`, `worker.js`; `tools/build_mc.py` builds `dist/forever/` (the engine ships gzipped as `engine.gz.wasm`, since artifact hosting does not serve `.gz`) | Live at https://chraltro.github.io/wowsim/forever/ and https://claude.ai/artifact/8jyCtNWjmQr2Gjfx9iN7pJ |

## Engine fixes we carry

These are patches in `engine-wasm/patches/`, applied by `tools/build_engine.sh` over the pinned engine. Every patch leaves level 60 as it was: the same requests through the engine before and after give bit-identical results at 60 for all 27 specs and all four demons. The engine's own tests pass with the patches: `cargo test --release` of the library (378) and of `classes` (475), `levels_20261108`, `forever_totems_20261104`, `shaman_notes_20261102`, `rogue_rework_20261104`, `forever_feral_measured_20261107` and `druid_live_20261104`, run on 8 November. The full suite was not run.

1. **Hunter pets scale with level** (`0001`). The engine sized every tamed pet from the level 60 creature damage row, whatever the hunter's level, so a level 10 Cat did about 57 damage per second. Its own code comments fit the level 11, 17 and 30 pet sheets to those levels' rows, so the patch uses the client row for the pet's level.
2. **Warlock demons scale with level** (`0002`, `classes/warlock/prepare/pets.rs` and `export.rs`). The engine used level 60 stats, swings and spell ranks at every level. Now:
   - Firebolt and Lash of Pain use the highest rank the level allows (the demon learns them from Grimoires, taken as bought). Every number is client data, build 1.60.1.70862 from wago.tools: base points, points per level, variance and coefficient from `SpellEffect`, spell and max level from `SpellLevels`, mana cost from `SpellPower` (the same rows as wowsims-forever's `spells_auto_gen.go`). Firebolt ranks 1 to 7 come at 1, 8, 18, 28, 38, 48 and 58; Lash of Pain ranks 1 to 6 at 20, 28, 36, 44, 52 and 60 (16 to 50 damage).
   - Strength, Agility, Stamina, Intellect and Spirit are each demon's own vanilla row for the level: cmangos classic-db `pet_levelstats`, entries 416 Imp, 1860 Voidwalker, 1863 Succubus, 417 Felhunter (the `vanilla_cmangos` rows of `data/classes/pets.json`). The engine's level 60 attributes are exactly those rows at 60. Vanilla data, not Forever data.
   - Melee range is the engine's level 60 range times the client creature auto attack dps for the level over its level 60 value (`ExpectedStat` CreatureAutoAttackDps, the row `0001` uses). wowsims-forever reads a demon's weapon as a fixed share of that row for its level, read in game at levels 20 and 30. The share kept is the engine's own level 60 one. Estimate.
   - Base mana is the engine's level 60 value (576 Imp, 1,066 the others) times the vanilla row's mana for the level over its mana at 60. Estimate: the engine's 576 is no vanilla or client value.
3. **Buff and debuff ranks stay in their spell family** (`0003`, `prepare/levels.rs` `known_buff_rank`). A levelling character's buff or debuff was the highest row of the same name it could know, from any family. Item and NPC rows with a class spell's name won: the Dazzling Longsword's proc 13752 is "Faerie Fire" Rank 2 at spell level 45 with no class family, and 13532 is a familyless "Thunder Clap" at 50. From 45 to 53 the Feral Druid's own Faerie Fire debuff became 13752, the rotation never saw its debuff up and cast Faerie Fire every global cooldown instead of Shred. From 50 to 57 the Protection Warrior spammed Thunder Clap the same way. Rows of another family are now left out (client `SpellClassOptions` family).
4. **Feral cat ranks at the known rank** (`0004`, `classes/druid/prepare/feral.rs` `cat_rank`). Rake, Rip and Ferocious Bite were registered at their top rank (9904 at 54, 9896 and 31018 at 60), which a levelling druid has not learned, so the export left them out of the rotation. Below 54 the druid never raked, below 60 it never spent its combo points. They now use the rank the level allows.
5. **Mana Tide Totem at the known rank** (`0005`, `prepare/buffs.rs`, `prepare/stat_auras.rs`, `classes/shaman/prepare/totems.rs`). The exactness check compared the levelling shaman's lower rank (146.7 MP5 at 30) with the level 60 row's 483.3 and refused levels 30 to 59. The shaman's own totem also used the level 60 row. Both now read the rank the aura is built from.
6. **Shaman imbue and fire totem ranks** (`0006`, `classes/shaman/prepare/imbues.rs`, `spells.rs`, `export.rs`). Flametongue Weapon's proc was rank 6 (16344, level 56) at every level: a level 10 shaman's imbue hit for about 85 and made 23 of its 41 damage per second. It now uses the proc rank the level allows (8026, 8028, 8029, 10445, 16343, 16344 at 10, 18, 26, 36, 46, 56). Fire Nova's hit (408428) and Magma Totem's pulse (10581) were fixed at their top ranks too; each now uses the row of the known rank's spell level (408423 to 408428 for Fire Nova ranks 1 to 5, 8187, 10579, 10580, 10581 for Magma Totem ranks 1 to 4). Windfury Weapon, Frostbrand Weapon and Rockbiter Weapon already took the known rank.
7. **Healer Priest's Shadowfiend follows its option below 60** (`0007`, `classes/priest/prepare.rs`). The engine gave every healer the Shadowfiend ("Gear planner only: the healer always has the Shadowfiend"), so a level 10 healer had a pet doing 18 damage per second. Below 60 the healer now reads `useShadowfiend` from its class options like the DPS priest; at 60 it keeps the Shadowfiend.
8. **Levels 1 to 9** (`0008`, `prepare/levels.rs` `MIN_LEVEL`). The engine refused every level below 10 ("below 10 a character has no talents and almost no rotation"). The gate now starts at 1. Ranks resolve by spell level as above 10, and a request below 10 names no talents. The engine test that expected level 5 to be refused now checks level 61.
9. **Overpower and Slice and Dice at the known rank** (`0009`, `classes/warrior/prepare/spells.rs` and `export.rs`, `classes/rogue/prepare/spells.rs`). Both were registered at their top rank (Overpower 11585 at 60, Slice and Dice 6774 at 42), which the export leaves out of the rotation as unlearned. Warriors never overpowered below 60 and rogues never used Slice and Dice below 42.

## Request builder fixes

- **Tanks** (`TANK_SPECS`: Protection Warrior, Protection Paladin, Feral in the tank role). The raid names the player in `raid.tanks` (`proto.UnitReference`, as the engine's tanking test sets it) and the target swings at the player. The average swing is the client's creature auto attack dps for the target's level times the 2.0 second swing (`LEVELS.mobDPS`, `ExpectedStat`), or `LEVELS.eliteDPS` with `elite` or `boss` (the client row times the cmangos elite median ratio, an estimate). The engine rolls `minBaseDamage * (1 + 0.3333 * roll)`, so `minBaseDamage` is the average over 1.16665. `canCrush` is set as in the engine's tank fixtures; its attack table crushes only from 3 levels up. Protection Paladin was simmed untanked before and changes with it (175 to 243 at 60).
- **Healer Priest** sends `useShadowfiend` at 40 and above, the rule the DPS priest already had. The 40 is our rule, not a verified learn level: client 401977 has spell level 1 and its trainer level is not in the client, and wowsims-forever (125e534) has no Shadowfiend at all.
- **Low-level fillers** (`LOW_FILLERS`), appended to the end of a preset's priority list until the preset's own filler is learned; the engine casts each at the highest rank the character knows:
  - Arcane fills with Arcane Blast, rank 1 at level 20 (400574). Below 20 the preset cast nothing (0 at level 10). Now Arcane Missiles, then Frostbolt, then Fireball.
  - Assassination builds only with Mutilate, a 31 point talent (level 56 on the route), and Subtlety with Hemorrhage (34 on the route). Before them: Backstab, then Sinister Strike.
  - Frost below 4 (Frostbolt): Fireball. Shadow before Mind Flay (talent): Smite.
- **Weapon types per spec** (`gear.js` `WEAPON_PREF`). Mutilate needs a dagger in both hands (`classes/rogue/prepare/export_specs.rs`: `has_dagger(Main) && has_dagger(Off)`); Backstab and Ambush need one in the main hand, and Hemorrhage takes its larger share with one. Assassination picks daggers in both hands, Subtlety in the main hand. A hand with no wearable dagger takes the best weapon of any type. Other classes are unchanged.

## Harness before and after

`node test/mc_levels.js all`, damage plus healing per second, 60 second fight, 100 iterations. Only the specs that changed:

| Spec | 10 | 20 | 30 | 40 | 50 | 60 |
| --- | --- | --- | --- | --- | --- | --- |
| Warrior Arms | 17 / 17 | 37 / 42 | 72 / 81 | 112 / 126 | 192 / 212 | 368 / 368 |
| Warrior Fury | 16 / 16 | 35 / 38 | 65 / 70 | 135 / 139 | 210 / 225 | 433 / 433 |
| Warrior Protection | 13 / 13 | 27 / 35 | 48 / 62 | refused / 84 | refused / 100 | refused / 169 |
| Paladin Protection | 16 / 16 | 39 / 39 | 59 / 60 | 95 / 100 | 131 / 142 | 175 / 243 |
| Rogue Assassination | 11 / 20 | 29 / 50 | 42 / 76 | 51 / 110 | 58 / 144 | 93 / 312 |
| Rogue Combat | 20 / 20 | 56 / 58 | 82 / 85 | 125 / 127 | 176 / 176 | 346 / 346 |
| Rogue Subtlety | 11 / 20 | 28 / 50 | 41 / 78 | 128 / 127 | 145 / 145 | 278 / 278 |
| Priest Discipline | 29 / 8 | 88 / 57 | 172 / 122 | 274 / 274 | 380 / 380 | 602 / 602 |
| Priest Holy | 29 / 8 | 89 / 57 | 163 / 111 | 265 / 265 | 385 / 385 | 826 / 826 |
| Priest Shadow | 9 / 12 | 41 / 41 | 92 / 92 | 267 / 267 | 344 / 344 | 639 / 639 |
| Shaman Enhancement | 41 / 21 | 76 / 52 | 132 / 114 | 199 / 186 | 259 / 250 | 347 / 347 |
| Shaman Restoration | 19 / 19 | 72 / 72 | refused / 155 | refused / 264 | refused / 386 | 546 / 546 |
| Mage Arcane | 0 / 11 | 56 / 56 | 122 / 122 | 217 / 217 | 333 / 333 | 574 / 574 |
| Warlock Affliction | 43 / 22 | 103 / 59 | 144 / 105 | 183 / 156 | 211 / 200 | 419 / 419 |
| Warlock Demonology | 44 / 21 | 103 / 57 | 163 / 124 | 242 / 213 | 275 / 263 | 519 / 519 |
| Warlock Destruction | 44 / 22 | 105 / 64 | 159 / 121 | 206 / 178 | 260 / 249 | 543 / 543 |
| Druid Feral | 11 / 11 | 47 / 55 | 79 / 102 | 112 / 172 | 74 / 227 | 455 / 455 |

Before / after. The healer priests at 10 to 30 were their Shadowfiend's damage plus a little healing; now healing only. The warlocks' demons at 10 to 50 went from about 27 to 113 damage per second to 5 to 100.

## Known engine gaps

- **The engine is older than the hotfixes of 10 November 2026.** It is pinned at `b3c5eb6`, so the Group Sim still runs Enhancement with Stormstrike at 150% on 6 seconds and Mental Dexterity at 50/100/150%, Hunter pets at their old health, the old Wrack and the old Hawk. Upstream has all of it (`913f04b` Enhancement, `bb41b12` Hawk and Nature's Swiftness, head `2d58021` on 12 November), 258 files on from our pin. Checked on 11 November: patches 0001, 0007 and 0008 still apply to upstream's head, the other six conflict and have to be redone against it. The Shaman Sim has its own engine and already uses the new numbers, so for a Shaman trust that page.
- **Demon mana and swing shares below 60 are estimates** (see fix 2). The engine's demon mana model has no regeneration from the warlock's Intellect; wowsims-forever reads Imp MP5 as 0.3 a point of the warlock's Intellect at level 30 in game. So the Imp is mana bound at every level: 11 to 19 Firebolts a minute of a possible 25. The engine's level 60 Succubus swing is 0.935 of the creature dps times 2, where wowsims-forever's in-game reading at 20 and 30 is 0.698; keeping level 60 unchanged keeps the engine's share at every level, about a third above that reading at 20 and 30.
- **Shadowfiend's learn level** in Forever is unknown (see the request builder). Healer and Shadow Priest numbers from 40 include it.
- **Feral below 20**: the engine starts the cat spec in Cat Form whatever the level, so a druid below 20 only swings. A Wrath filler cannot be cast in Cat Form.
- **Some healers heal nothing at the lowest levels**: Discipline and Holy Priest below 8 (their preset starts with Power Word: Shield at 6 and Renew at 8, with no Lesser Heal) and Holy Paladin below 10. Restoration Shaman and Druid heal from level 1. Questing healers use the `quest` role and a damage rotation.
- **Rogue poisons** are not in our requests at any level. The engine carries only the top ranks, as Go literals (`classes/rogue/prepare/poisons.rs`), so turning them on below 60 would overstate damage.
- **Other top-rank rows** the engine reads whatever the level, left alone because no preset damage depends on them: Windfury Totem's buff (10610, 10612), Charge (11578), Pummel (6554), Vanish (1856), Stealth (1784), Hemorrhage (16511, one rank).
- **Drops left in the harness**, all from 9 to 10: Paladin Retribution and Protection go from 18 to 16 because Seal and Judgement of Righteousness rank 2 come at 10 and cost more mana (the paladin is out of mana 9 seconds into the fight at 10, never at 9). Protection Warrior goes from 13.2 to 12.9 because the client's creature armor rises from 412 to 518 at 10 (with level 9's armor the level 10 warrior does 13.6).
- **Ammo below 25**: the engine has no Rough/Sharp Arrow or Light/Heavy Shot option, so hunters below 25 sim with no ammo. That leaves out 1.5 damage per second, or 3.5 from level 10.
- **Player damage per second already counts the pet.** `summarize()` reports `dps` (with the pet), `petDps` and `ownDps`.
- **Racial stat percentages** (Gnome Intellect, Human Spirit) are not added to our character sheet. The engine calibrates health and mana to the sheet, so the effect is small.

## Order of work

1. Questing model on engine numbers for every class: kill time from engine damage per second against a normal mob of your level, the damage you take (your pet tanks for Hunter and Warlock), resting with food and water.
2. Upgrade ranking on engine numbers (demon scaling and the tank setup are done). Upgrades need many sims, so rank first with stat weights from two or three sims per character, then re-sim the top items.
3. The page: characters for the group, class, race, level, spec route, gear (typical gear for the level as a start), questing, dungeon, upgrades, logs.
