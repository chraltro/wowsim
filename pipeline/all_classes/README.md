# All-classes item build: `data/items_all.json`

Extends the Shaman-only item file (`data/items_forever_all.json`) to every item an Alliance character of any of the nine classes can equip while leveling 1 to 60. Same per-item schema, plus `usableBy`, `equipSlots`, `weaponSubtype` and `rangedType`. The scripts reuse the Shaman pipeline (`../build_dataset.py` is imported, not copied) and its caches. The Shaman scripts are not changed.

Paths hang off `ROOT` in `common.py` (default `/home/claude`, override with `WOWSIM_ROOT`). Inputs are the same as the Shaman build: the wowsims Forever clone (read as data only), `cache/` (Warcraft DB, Wowhead, spell, loot, Questie caches) and the Warcraft DB list files `cache/list/lists.json` and `cache/list/lists_low.json`. Intermediate files go to `cache/allclass/`.

## Run order

1. `class_rules.py`: fetches the Forever client DB2 tables SkillLine, SkillLineAbility, SkillRaceClassInfo, SpellEquippedItems and SpellEffect (build 1.60.1.70862, wago.tools CSV) into `ext/wago_allclass/`, and the Warcraft Tavern weapon trainer guide into `cache/web_allclass/`. It works out each class's armor, weapon, ranged and relic proficiencies, the level gates and the Dual Wield level from the DB2. It then cross-checks them against wowsims `sim/core/character_constants.go` and the Warcraft Tavern table. Writes `cache/allclass/class_rules.json`.
2. `targets_allclass.py`: picks target ids from the wowsims db (`db.json`, `leftover_db.json`) that at least one class can equip. Writes `cache/allclass/target_ids.json`.
3. `crawl_wdb_allclass.py`: Warcraft DB Forever item nodes and tabs for every equippable subtype (adds Plate, swords, polearms, bows, guns, crossbows, thrown, wands, idols, librams). Writes to `cache/items/`.
4. `wh_fetch_allclass.py`: Wowhead Forever tooltips for any target or Warcraft DB-only candidate not yet cached. Writes to `cache/wh/`.
5. `spell_fetch_allclass.py`: Warcraft DB recipe spell nodes for crafted sources. Writes to `cache/spell/`.
6. `build_allclass.py`: runs `build_dataset.build()` on the targets. Adds sword and polearm names, ranged and relic slots and subtypes, ranged weapon damage, and a base and bonus armor cross-check against Wowhead. Writes `cache/allclass/items_stage1.json`.
7. `supplement_allclass.py`: adds items that Warcraft DB lists but the wowsims db leaves out, using stats from the Wowhead tooltip. A Wowhead "Classes:" line becomes `classAllowlist`. Writes `items_stage2.json`.
8. `apply_loot_allclass.py`: applies the wowtbc.gg dungeon loot tables (drop sources, drop chances, dungeon levels). Writes `items_stage3.json`.
9. `finalize_allclass.py`: same cleanup as `../all/finalize_all.py`. Adds the class fields and the coverage counts, then writes `wowsim/data/items_all.json`.
10. `verify_allclass.py`: compares the Shaman subset with `items_forever_all.json`, spot-checks 10 random items per class against fresh Wowhead tooltips, and runs whole-file slot, subclass, level, armor and "Classes:" checks. Writes `cache/allclass/verify_report.json`.

Steps 3 to 5 make network requests. They use 4 workers, short sleeps and retries, and write each response to disk before it is parsed. A rerun only fetches what is missing.
