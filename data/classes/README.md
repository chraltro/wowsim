# Per-class data for WoW Forever, levels 1-60

Built 2026-11-08 for client build 1.60.1.70862. Every value carries a status: `forever` is Forever client data, or a wowsims-forever value read in the Forever game. `vanilla` is a Classic 1.12 fallback. `estimate` is derived or carried across levels. Mob baselines are not repeated here. They are in `data/shaman_levels.json` (`mobs`).

## Files

| File | What it holds |
| --- | --- |
| `<class>_levels.json` (9) | Class-wide per-level arrays: base health and mana, health per Stamina, mana per Intellect, crit per Agility and per Intellect, dodge per Agility, base crit, dodge, parry and block, the attack power and ranged attack power level terms, weapon and defense skill caps. Each Alliance race has its own attribute arrays and naked totals: max health and mana, crit, dodge, AP, RAP, armor from Agility, Spirit mana regen (vanilla and wowsims formulas) and out-of-combat health regen. `meta` holds the class rules: parry, block and dual wield; the AP formulas; spell power; regen; rage and energy rules with Forever changes; racials; the level 60 checks; gaps. |
| `<class>_ranks.json` (9) | Every spell rank a levelling or dungeon sim needs. The per-rank schema is the one `data/shaman_ranks.json` uses. On top of it, each rank has its cost in the right resource, `learned_from` (vanilla trainer level and cost, quest, book, talent, or the spell that triggers it) and `vanilla` (the 1.12 row with `changes_vs_vanilla`). Families also carry `notes` (Forever deep dives and patch notes) and `wowsims_code_notes` (wowsims's comments at the code that builds the spell). `meta.excluded_ladders` lists every wowsims ladder left out, with the reason. |
| `pets.json` | Hunter pets: base stats for each level 1-60 (Forever model plus vanilla cmangos), the family modifiers from the client Tamed Pet Passive rows (plus vanilla), what the pet inherits from the hunter, focus, and 84 pet ability ladders. Warlock demons (Imp, Voidwalker, Succubus, Felhunter): own health, armor and melee for each level 1-60, the level 60 model, vanilla per-level stats, what a demon inherits from the warlock, and 20 demon ability ladders. |

Generators are in `wowsim/pipeline/classes/`. Run them in this order:

1. `extract_cmangos.py`
2. `../levels/parse_spells.py` (writes `work/classes/spells_all.json`)
3. `gen_class_levels.py`
4. `gen_class_ranks.py`
5. `gen_pets.py`

`families.py` holds the ladder selection rules and the hand notes. Paths are relative to `WOWSIM_ROOT` (default `/home/claude`). No third-party code is built or run; the cloned repos are read as data.

## Sources

- **Forever client tables.** PlayerExpectedStat and ExpectedStat for build 70862, from wago.tools. They give base mana, health per Stamina, both crit slopes and the creature values.
- **wowsims-forever at commit 125e534.** The spell store (`sim/core/spelldata/spells_auto_gen.go`, all 8324 records), the class ladders, the talent trees, the book ranks, base stats and race offsets, class/race capabilities, the rage, energy, focus and mana code, and the pet models.
- **cmangos classic-db, z2815.** `player_classlevelstats`, `player_levelstats`, `spell_template`, `npc_trainer`, `npc_trainer_template`, `quest_template`, `playercreateinfo_spell`, `pet_levelstats`, `pet_familystats`, `creature_template` and `petcreateinfo_spell`.
- **Other emulators and sims.** AzerothCore `player_class_stats` (the tie-break for class rows). vmangos `StatSystem.cpp`, `Unit.cpp` and `Player.cpp` (formulas). wowsims SoD `base_stats.go` (a per-level cross-check at 25, 40, 50 and 60). mythicsim `docs/levels.md` and `src/prepare/levels.rs` (rules).
- **Forever changes.** Blizzard news "Meet the New Skyborne" (24302071) and "Class Deep Dives — Hunter and Druid" (24301515). Warcraft Tavern summaries of the Priest & Warrior, Mage & Shaman and Rogue & Warlock deep dives, of "All Changes to Paladins" and of "Pre-Launch Class Changes" (4 Nov 2026, from the 2 Nov dev notes). kami-labs on the 2 Nov notes. Method.gg and Warcraft Tavern race/class tables. Where a guide and a client row disagree, the row wins and the note says so. The Blizzard forum dev-notes thread itself could not be fetched here.

## Race/class combos (Alliance)

- **Warrior:** Human, Dwarf, Night Elf, Gnome, High Order Skyborne.
- **Paladin:** Human, Dwarf.
- **Hunter:** Human (new in Forever), Dwarf, Night Elf, High Order Skyborne.
- **Rogue:** Human, Dwarf, Night Elf, Gnome, High Order Skyborne.
- **Priest:** Human, Dwarf, Night Elf, Gnome (new in Forever).
- **Shaman:** Dwarf (new in Forever).
- **Mage:** Human, Gnome, High Order Skyborne.
- **Warlock:** Human, Gnome.
- **Druid:** Night Elf, High Order Skyborne.

Every High Order Skyborne combo is new; Skyborne is a new race. Sources: wowsims ClassRaceCapabilities, Blizzard's Skyborne page, Warcraft Tavern and Method.gg.

## Known gaps

- **Base health below 60** is vanilla (cmangos) only. The Forever client has no player base-health table.
  - Priest and Mage are 10 below wowsims SoD at levels 25, 40, 50 and 60, and below wowsims-forever at 60 (Priest 1387 vs 1397, Mage 1360 vs 1370). This is unresolved.
  - Hunter at level 50: cmangos 1032 vs SoD 1047.
- **Base crit, base dodge and dodge per Agility** are hand-kept vanilla tables, or wowsims's level 60 rule carried to every level.
- **Spirit mana regen below 60 and health regen** have no Forever source. The vanilla (vmangos) and wowsims formulas are both given.
- **High Order Skyborne attributes** use one wowsims reading of the race offset at level 1, assumed constant at every level.
- **Talents** are out of scope. Passive talents and talent procs are excluded. Active talent abilities are included.
- **Server-side spell formulas** are only in `wowsims_code_notes`, where wowsims states them. Examples: Life Tap's Spirit term, the poison AP coefficients, Eviscerate's 0.04 AP per combo point.
- **Forever trainer costs** are not in local data. The 2 Nov notes put training 1-60 at 206-207 gold for every class. The vanilla costs here are only for comparison.
- **Pets:**
  - Hunter pet health (one in-game reading) and attack power (readings at levels 11, 17 and 30) are carried across levels.
  - Demon health and armor shares were read at levels 20 and 30. Demon attributes exist only at 60.
  - The Felhunter has no health share.
  - No Felguard or Incubus model.
- **Not in the wowsims data:** Dark Pact, Blessing of Sanctuary. Tiger's Fury was removed in Forever.
