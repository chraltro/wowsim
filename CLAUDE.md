# wowsim

Tools and notes for a five-man group playing World of Warcraft: Forever (Blizzard's Classic+, launched Nov 4, 2026). Forever changed most talents, many spells and thousands of items, so vanilla or Classic knowledge is not valid here. Check the data in this repo or a current source before stating a number, and say when something is a vanilla fallback.

## Who plays what

- Christian (the user): Dwarf Restoration Shaman, the group's only healer. Wants to DPS on the side. Enhancement dual spec at 40. Planned alt: Paladin tank.
- Niels: Warrior, tank/DPS.
- Nicklas: Druid, tank/DPS.
- Mikkel: Warlock.
- Cornelius: Mage, also leveling a Hunter.
- Alliance, RP-PvP ruleset, EU. About one session a week. Mains are leveled together.
- The game is about the journey for this group: advice has to work while leveling, not only at 60.

## Where things are

Everything here shares one set of data and one set of engines. The site, the check command and you all read the same files, so a number is fixed in one place.

- `docs/kb/`: what we know about the game, one page per topic (`README.md` is the index; `shaman.md`, `leveling.md`, `gold.md`, `systems.md`, `classes.md`, `paladin.md`, `raids.md`, `open-questions.md`, `sources.md`, `changelog.md`). Read the page that fits before answering a Forever question. When you learn something new and checked, add it there with its date and source, and add a line to `changelog.md`. They are not published on the site; `tools/build_kb.py` builds a readable page into `local/kb/`.
- `data/`: items, class stats per level, talents, leveling routes, Shaman spell data, craft and price data. `data/hotfixes.json` holds item changes Blizzard made after the item files were built; the build lays them over.
- `src/`: Shaman Sim (`engine.js`, `data.js`, `logparse.js`), `src/mc/` Group Sim, `src/crafts/` Craft Profits, `src/check/` the character check (`parse.js` reads an export, `advise.js` works out upgrades, quests and professions).
- `tools/check.js`: the character check from the command line. `/check` runs it.
- `opt/`: Shaman talent optimizer. `test/`: Node and Playwright checks.
- `addon/ClaudeExport/`: the in-game export addon.
- `README.md`: what the tools do and the full file layout.

## Private files

This repo is public and the site is shared with the group. Christian's own things stay on his PC and are never committed:

- `local/` (ignored by git): `local/reports/` check reports, `local/cache/` quest data and fetched prices, `local/notes.md` his own notes and plans for his characters, `local/config.json` settings (`house`, `pastes`).
- His exports: `C:\Gits\wow\pastes` (a `pastes/` folder inside the repo is ignored too).
- `CLAUDE.local.md` (ignored): instructions that are his alone.

Write anything about his character, his gold, his bags or his plans to `local/`, not to `docs/` or `data/`. Before a commit, look at `git status` and make sure nothing from those places is staged. What we learn about the game itself goes in `docs/kb/` and is shared.

## The character check

`node tools/check.js` (or `/check`) takes the newest export and says what to do next:

- Gear: upgrades already in the bags or bank, which quest reward to pick, the best buys on the auction house for the gold he has, what he can craft himself, rewards of quests he can pick up, vendors and good drops. Gear is scored by the Shaman Sim engine at his level with his talents. Purchases are compared with his gear after he puts on what he already owns.
- Quests: every quest he can pick up now and has not done, his zone first, then class quests and the dungeon of his level. This needs `local/cache/quests.json`; build it once with `python tools/fetch_quests.py` (QuestieDB may not be republished, so it is fetched to his machine and not committed).
- Professions: recipes to learn, the cheapest next skill points with a shopping list, what pays, caps. Same pricing code as Craft Profits.
- Bags: keep, post or vendor.

Prices are the export's own auction scan when there is one (`/claudeah` in game with the auction house open), otherwise AHledger's latest scan of the house, fetched and cached for 45 minutes. `--offline` skips the fetch.

For a class other than Shaman the check still reads the export, quests and professions, but gear is ranked by rough stat values and only among items in the export.

## Character exports

The ClaudeExport addon (version 1.4) writes everything about the character as text: stats, equipped gear with full tooltips, bags, bank, quest log with reward choices, the ids of every finished quest, talents, skills, known recipes, reputation, spellbook, buffs, group, and the last auction house scan.

- In game, `/claude` opens a window with the text selected. Christian may paste it straight into the chat.
- `/claudeexport` saves the text and reloads the UI, which makes the game write it to disk. An addon cannot write files anywhere else. `tools/export_watch.py` watches for that and writes each export as `<Character>_<date>_<time>.txt` plus `latest.txt`, by default in `C:\Gits\wow\pastes`. Read `latest.txt` there when he says he exported, and check its date.
- The raw save is `ClaudeExport.lua` under the WoW install, in `WTF/Account/<account>/<realm>/<character>/SavedVariables/`, with the text in `ClaudeExportDB.export` and the time in `ClaudeExportDB.exportTime`.
- `/claudeah` with the auction house open scans every listing (the game allows a full scan every 15 minutes). The next export carries it: gear with prices in the copy window, every price in the file on disk.
- The bank part is a snapshot from the last time the bank was open, and known recipes are from the last time each profession window was open. Quests, reputations and skills under a collapsed header are missing and marked as such.
- A section that reads `(section failed: ...)` means an API call does not exist on the Forever client. Fix it in `addon/ClaudeExport/ClaudeExport.lua`. The addon has not been verified against the live client; it tries both the Classic and the modern API for each section. `python3 test/addon_run.py` runs the addon in a real Lua against a stand-in for the Classic API, which catches syntax errors and broken sections but cannot prove a call exists in the game. The auction scan and the finished-quest list are new in 1.4 and the least tested: if either is missing from an export, that is the first place to look.
- To install or update the addon, copy `addon/ClaudeExport/` into `Interface/AddOns/` in the Forever client folder.

Typical questions: what to vendor, what to post on the auction house, which quest reward to pick, upgrades already in the bags, what to keep for Enhancement, where to quest next. Run the check first and answer from its report.

## Combat logs

`/combatlog` in game writes `Logs/WoWCombatLog*.txt` in the client folder. `src/logparse.js` parses them. Christian wants dungeon logs read and his healing critiqued.

## Working here

- The public site (https://chraltro.github.io/wowsim/) is Craft Profits only. `./tools/build_site.sh` builds it into `dist/`, and a push to main that touches `src/`, `data/` or `tools/` publishes it (`.github/workflows/pages.yml`). The Shaman Sim, the Group Sim and the start page show the group's names, so they are never published: `./tools/build_local.sh` builds all four pages into `local/site/` for Christian's own use. Do not add a page to `PUBLISHED` in `tools/shell.py` without asking him.
- Keeping the knowledge current: `.github/workflows/watch.yml` checks the sources in `docs/kb/watch.json` every morning and opens an issue labelled `sources` when Blizzard has posted something. `/update-knowledge` reads the changes and edits `docs/kb/`, `data/hotfixes.json` and the sim numbers. Guides lag behind hotfixes: when a guide and Blizzard disagree, Blizzard wins.
- Checks: `node test/check.js`, `node test/crafts.js`, `node test/routes.js`, `node test/lv.js`, `python3 test/addon_run.py --check` (needs `pip install lupa`).
- This repo is public. Keep account names, emails and API keys out of it.
- Write plainly. Commit to an answer. No invented numbers.
