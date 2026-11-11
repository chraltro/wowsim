---
description: What to do next with the character, from the newest export (gear, quests, professions, bags)
---

Run the character check and tell Christian what to do next.

1. Run `node tools/check.js $ARGUMENTS` from the repo root. With no argument it takes the newest export from his pastes folder. If it says there is no quest data, run `python tools/fetch_quests.py` once and run the check again. If Node is missing, say so and stop.
2. Read the whole report. It is also saved as `local/reports/latest.md`.
3. Answer in this order, short, and commit to a pick in each:
   - Gear: what to put on right now, which quest reward to take, and the one or two auction buys worth the gold. Give price and the gain.
   - Quests: where to go next. Start with the zone he is in, then class quests, then the dungeon of his level with the quests to collect first.
   - Professions: recipes to learn at the trainer, the next skill points and what to buy for them, and a warning when a profession is at its cap.
   - Bags: what to post, what to vendor.
4. Check the report's notes. A collapsed quest header, a bank never opened, an old export or an addon older than 1.4 changes how far the answer can be trusted, so say it.

Rules:
- The numbers come from the Shaman Sim engine and Craft Profits. Do not replace them with your own estimate. If a number looks wrong, say so and look at `src/check/advise.js`.
- Auction prices are the export's own scan when he ran `/claudeah`, otherwise AHledger's latest scan of the house, which can be hours old and may list an item that has sold.
- Read `docs/kb/` before adding advice the report does not contain, and `local/notes.md` if it exists for his own plans.
- Nothing from `local/` or his pastes goes into a commit.
