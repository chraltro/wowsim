# Data pipeline (reference)

These are the one-off scripts that built the JSON files in `data/`. They are kept as a record of where each number came from. They will not run as they are:

- They use hard-coded paths under `/home/claude/` (`data/`, `cache/`, `ext/`, `work/`, `data/repos/`).
- They expect local clones of wowsims/forever and mythicsim-forever-engine.
- They expect wago.tools DB2 CSV exports, cmangos SQL dumps and caches of fetched pages. None of these are in this repo.

To rebuild the page from the data already here, use the scripts in `tools/` instead.

## Items: `data/items_forever_all.json`

The levels 40 to 60 set was built first. `all/` extends it to every level with the same code path.

1. `targets.py` and `all/targets_all.py`: pick the Shaman-usable item IDs from the wowsims Forever item database.
2. `list_items.py`, `crawl_items.py`, `tt.py`, `all/list_items_low.py`, `all/crawl_items_low.py`: Warcraft DB Forever item lists, item pages and tooltips.
3. `wh_fetch.py` and `all/wh_fetch_all.py`: Wowhead Forever tooltips for drop chances, effect text and requirements.
4. `spell_fetch.py` and `all/spell_fetch_all.py`: Warcraft DB recipe skill levels for crafted items.
5. `questie_parse.py`: quest levels, zones and factions from QuestieDB-Forever.
6. `build_dataset.py` and `all/build_all.py`: merge all of the above into one item file.
7. `supplement.py`: add Forever items that Warcraft DB lists and the wowsims database leaves out.
8. `parse_tbc.py`, `apply_loot.py` and `all/apply_loot_all.py`: dungeon loot tables and drop chances from wowtbc.gg.
9. `all/finalize_all.py`: final cleanup. `all/report_all.py`: coverage report.
10. `presets.py`: resolve guide gear lists into `data/presets/shaman_presets_resolved.json`.
11. `slot_samples.py`: per-slot samples used while checking the data.

## Spell ranks and per-level stats: `data/shaman_ranks.json`, `data/shaman_levels.json`

In `levels/`:

- `parse_spells.py`: parse the wowsims Forever spell records into one JSON.
- `gen_ranks.py`: every Shaman spell rank with base points, points per level, scaling levels, coefficients, cast times and costs.
- `gen_levels.py`: base stats, crit scaling and mob health, damage and armor for each level. It uses the Forever client tables PlayerExpectedStat and ExpectedStat, with cmangos and vmangos filling gaps.
- `show.py` and `sqlvals.py`: helpers.

Every value in `shaman_levels.json` names its source and status.

## Research helpers

These did not produce data files. They were used to read guide pages and forum threads.

- `fetchall.py` and `disc.py`: fetch and print Blizzard forum threads.
- `go_extract.py`, `rsc_decode.py`, `ts_extract.py`, `totext.py`: pull text and data out of guide pages.
- `parse_method.py`: parse method.gg dungeon loot pages, used to cross-check drop sources.
- `decode.py`, `decode_digits.py`, `dump.py`: talent code decoding and file inspection.
