---
description: Bring docs/kb, data/hotfixes.json and the sims in line with what Blizzard has posted since the last check
---

Bring the knowledge bank up to date. Work from primary sources, and change nothing you have not read.

1. Run `python tools/watch_sources.py --dry` to see which watched sources changed. Also open the newest issue labelled `sources`, if there is one (`gh issue list --label sources`).
2. Fetch every changed source in full: Blizzard's hotfix article, the development notes thread, any new Forever article from the news index. Read the whole thing, not a snippet. If a page will not load, say so and leave its facts out.
3. For each change, find where it lands:
   - A fact about the game: the matching page in `docs/kb/`. Rewrite the old sentence so it is true now, and keep the old number in brackets ("was 150%"). Add the date and a link to the source.
   - An item's stats: an entry in `data/hotfixes.json`, then `python3 tools/build_items.py` (and `python3 tools/build_items_all.py` when the engine submodule is checked out).
   - A Shaman spell or talent number the Shaman Sim uses: `src/data.js` (the value and its line under `sources`), then `node test/lv.js` and say how the results moved.
   - Vendor prices, recipes or skill levels: say that `data/crafts.json` is older than the change. Rebuilding it is `pipeline/crafts/fetch_inputs.sh` and takes about half an hour, so ask first.
   - Something a source settles: take it off `docs/kb/open-questions.md`. Something new that sources disagree on: add it there.
4. Add an entry at the top of `docs/kb/changelog.md` with today's date, and change the "Last checked" line in `docs/kb/README.md`.
5. Add any new source to `docs/kb/sources.md`. If Blizzard will keep posting changes on it, add it to `docs/kb/watch.json` too.
6. Run `python tools/watch_sources.py` (no `--dry`) so the new state is recorded, then `./tools/build_site.sh` and `node test/check.js`.
7. Show the diff of `docs/kb/` and the data files, and summarise what changed in the game in a few lines. Commit and push when Christian says so. Pushing to main publishes the site.

Rules:
- A number nobody has confirmed for Forever is labelled vanilla, beta or unconfirmed. Never state it plain.
- Guide sites lag behind hotfixes. When a guide and Blizzard disagree, Blizzard wins and the guide's date goes in the sentence.
- Close the `sources` issue with a one-line comment when its changes are in.
