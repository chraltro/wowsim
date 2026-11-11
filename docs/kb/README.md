# WoW Forever knowledge bank

What we know about World of Warcraft: Forever as a five-man Alliance group on RP-PvP, checked against Blizzard posts and guide sites. Beta-era and unconfirmed facts are marked where they stand. Vanilla and Classic knowledge is not valid here unless a page says so.

Last checked against Blizzard's notes: 2026-11-11 (hotfixes through Nov 10).

| Page | What is in it |
| --- | --- |
| [The group](group.md) | Who plays what, and the rules the group agreed |
| [Leveling path and dungeons](leveling.md) | Zones by level, every dungeon, dungeon XP, where dungeon quests start |
| [Shaman](shaman.md) | Restoration and Enhancement |
| [Protection Paladin alt](paladin.md) | The planned tank alt |
| [What each class brings](classes.md) | Warrior, Druid, Warlock, Mage, Hunter |
| [Systems](systems.md) | Mounts, rested XP, camping, professions, Legacy, transmog, RP-PvP rules, what differs from vanilla |
| [Gold making](gold.md) | Our auction house, flips, crafting, the cost of leveling a profession |
| [Raids and roadmap](raids.md) | The launch raids and what comes after |
| [Unconfirmed or conflicting](open-questions.md) | What no source settles yet |
| [Sources](sources.md) | Where the facts come from |
| [Changes](changelog.md) | What changed in the game and in these pages, newest first |

These pages are published at https://chraltro.github.io/wowsim/kb/ on every push.

## Keeping it current

- `watch.json` lists the pages Blizzard posts changes on. A scheduled job (`.github/workflows/watch.yml`) reads them every morning and opens an issue in the repo when one has changed.
- In Claude Code, `/update-knowledge` reads the changed sources and proposes edits to these pages, to `data/hotfixes.json` (item changes) and to the sims' numbers when a hotfix touches them.
- Every fact added gets its date and its source. A number nobody has confirmed for Forever is labelled as vanilla, beta or unconfirmed, never stated plain.
- When a page changes, add a line to `changelog.md`.

This started as a Claude doc on 2026-11-07 and moved here on 2026-11-10. The repo is the copy to trust.
