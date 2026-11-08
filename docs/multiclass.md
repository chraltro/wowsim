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
| Engine in the browser | `engine-wasm/` wraps `vendor/mythicsim-forever-engine` (pinned b3c5eb6) with `ws_alloc`, `ws_sim`, `ws_out_ptr`, `ws_out_len`. Built by `tools/build_engine.sh` into `dist/engine.wasm.gz` (5.6 MB) | Done. Matches the native build exactly. Each run needs a fresh instance: a second run in the same instance traps |
| Request builder | `src/mc/request.js`: class, race, spec, level, talents from the route, gear, a character sheet from our class data, level-dependent class options, and a target from the client mob tables | Done for damage specs and healers. Tanks need `raid.tanks` and a swinging target |
| Typical gear for a level | `src/mc/gear.js` `typicalGear()` | Done. Rough stat weights per style, easy sources only |
| Check of every spec | `test/mc_levels.js` | 162 runs at levels 10 to 60. Open failures are listed below |
| Questing model for all classes | uses engine damage per second over the kill time, plus our damage-taken, resting and walking loop from the Shaman model | Next |
| Page | class and race per character, group view | After that |

## Engine fixes we carry

These are patches in `engine-wasm/patches/`, applied by `tools/build_engine.sh`.

1. **Hunter pets scale with level** (`0001`). The engine sized every tamed pet from the level 60 creature damage row, whatever the hunter's level, so a level 10 Cat did about 57 damage per second. Its own code comments fit the level 11, 17 and 30 pet sheets to those levels' rows, so the patch uses the client row for the pet's level.

## Known engine gaps

- **Warlock demons** use level 60 stats at every level (`src/classes/warlock/prepare/pets.rs`, "level 60 pet stats"). The Imp's Firebolt is fixed at rank 7. Not patched yet.
- **Protection Warrior from 40** is refused: Shield Slam reads block value and needs a tanked target. Tank sims need `raid.tanks` and a swinging target.
- **Restoration Shaman from 30 to 50** is refused during preparation: Mana Tide's MP5 is "not added and taken away exactly". Level 60 works. Our own Shaman engine covers Resto Shaman healing.
- **Below level 10** the engine refuses every class. The Shaman keeps our own engine for levels 1 to 9. Other classes show nothing below 10 for now.
- **Ammo below 25**: the engine has no Rough/Sharp Arrow or Light/Heavy Shot option, so hunters below 25 sim with no ammo. That leaves out 1.5 damage per second, or 3.5 from level 10.
- **Healer Priest** shows a pet from level 10 (about 18 damage per second), probably Shadowfiend summoned before it is learned. Not checked yet.
- **Assassination Rogue** is low at every level (93 damage per second at 60, against 346 for Combat) because typical gear does not pick daggers for Mutilate. The gear picker needs weapon types per spec.
- **Feral Druid** drops from 112 at 40 to 74 at 50. Not checked yet: the route or the gear.
- **Arcane Mage at 10** does no damage. The preset probably casts nothing the character knows at 10.
- **Player damage per second already counts the pet.** `summarize()` reports `dps` (with the pet), `petDps` and `ownDps`.
- **Racial stat percentages** (Gnome Intellect, Human Spirit) are not added to our character sheet. The engine calibrates health and mana to the sheet, so the effect is small.

## Order of work

1. Questing model on engine numbers for every class: kill time from engine damage per second against a normal mob of your level, the damage you take (your pet tanks for Hunter and Warlock), resting with food and water.
2. Demon scaling patch, tank setup, upgrade ranking on engine numbers. Upgrades need many sims, so rank first with stat weights from two or three sims per character, then re-sim the top items.
3. The page: characters for the group, class, race, level, spec route, gear (typical gear for the level as a start), questing, dungeon, upgrades, logs.
