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

- `docs/knowledge-bank.md`: notes on the game itself (dungeons by level, XP rules, class notes, systems, gold making, raids, open questions, sources). Exported from a Claude doc on 2026-11-10. Read it before answering a Forever question. When you learn something new and checked, add it there with its date and source.
- `README.md`: what the three tools do and the full file layout.
- `data/`: items, class stats per level, talents, leveling routes, Shaman spell data, craft and price data.
- `src/`: Shaman Sim (`engine.js`, `logparse.js`), `src/mc/` Group Sim, `src/crafts/` Craft Profits.
- `opt/`: Shaman talent optimizer. `test/`: Node and Playwright checks.
- `addon/ClaudeExport/`: the in-game export addon.

## Character exports

The ClaudeExport addon writes everything about the character as text: stats, equipped gear with full tooltips, bags, bank, quest log with reward choices, talents, skills, reputation, spellbook, buffs, group.

- In game, `/claude` opens a window with the text selected. Christian may paste it straight into the chat.
- The same text is saved to SavedVariables, which the game writes to disk on `/reload` or logout. The file is `ClaudeExport.lua` under the WoW install, in `WTF/Account/<account>/<realm>/<character>/SavedVariables/`. Find it by name. The text is in `ClaudeExportDB.export`, stamped by `ClaudeExportDB.exportTime`. Check the stamp before trusting it.
- The bank part is a snapshot from the last time the bank was open. Quests, reputations and skills under a collapsed header are missing and marked as such.
- A section that reads `(section failed: ...)` means an API call does not exist on the Forever client. Fix it in `addon/ClaudeExport/ClaudeExport.lua`. The addon has not been verified against the live client; it tries both the Classic and the modern API for each section.
- To install or update the addon, copy `addon/ClaudeExport/` into `Interface/AddOns/` in the Forever client folder.

Typical questions: what to vendor, what to post on the auction house, which quest reward to pick, upgrades already in the bags, what to keep for Enhancement, where to quest next.

## Combat logs

`/combatlog` in game writes `Logs/WoWCombatLog*.txt` in the client folder. `src/logparse.js` parses them. Christian wants dungeon logs read and his healing critiqued.

## Working here

- Build with `./tools/build_site.sh`. Deploy with `./tools/deploy_pages.sh`. The live site is https://chraltro.github.io/wowsim/.
- This repo is public. Keep account names, emails and API keys out of it.
- Write plainly. Commit to an answer. No invented numbers.
