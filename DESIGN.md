# Design

The site looks like the group's shared spreadsheet, because that is where a WoW group plans: loot lists, rosters and leveling routes live in a guild sheet. Picked by Christian on 2026-11-11 from three directions (the others were a 2005 database site and the in-game chat frame).

## Principles

- Gridlines carry the structure. Sections are blocks of cells with a grey header row, not cards. No shadows except on menus and dialogs, which float in a spreadsheet too.
- The game's own colours are the only strong colour: class colours as cell fills for characters, item quality colours for item names. Everything else is the sheet's greys, its link blue and its green for the active tab.
- Numbers sit right-aligned in tabular figures, like cells. Text sits left.
- The pages are the sheet's tabs. The bar at the bottom is the site's navigation on every page, and the one bold element. Inside a page, views are toolbar toggles.
- Each page opens with the name box and formula bar: the page name and one sentence of what it does.
- A remark on a result is a cell note: a bordered cell with the sheet's black corner triangle, not a tinted callout.

## Tokens

Sheet greys, link blue and green are Google Sheets' default interface colours as remembered, not measured from the product. Class and quality colours are the game's (`RAID_CLASS_COLORS` as the Group Sim already used them, item quality colours from the client).

| Token | Value | Role |
| --- | --- | --- |
| `--ground` | `#ffffff` | cells and page |
| `--head` | `#f8f9fa` | header rows, row and column headers, bars |
| `--fill` | `#f1f3f4` | row hover, quiet fills |
| `--grid` | `#e2e3e3` | gridlines |
| `--rule` | `#c4c7c5` | frozen-row divider, control borders |
| `--text` | `#202124` | text |
| `--muted` | `#5f6368` | secondary text, headers |
| `--link` | `#1155cc` | links |
| `--select` | `#1a73e8` | focus and selection outline |
| `--select-fill` | `#e8f0fe` | active toggle, selected row |
| `--tab` | `#188038` | active sheet tab, primary buttons |
| `--good` / `--good-fill` | `#137333` / `#e6f4ea` | gains, profit |
| `--bad` / `--bad-fill` | `#c5221f` / `#fce8e6` | losses, deaths |
| `--warn` / `--warn-fill` | `#b06000` / `#fef7e0` | vanilla fallbacks, warnings |
| Series | `#4285f4 #ea4335 #fbbc04 #34a853 #ff6d01 #46bdc6` | chart lines and builds, the sheet's default chart order |
| Quality on white | uncommon `#1a8a00`, rare `#0062c4`, epic `#8f2bd6` | the game's hues, darkened to 4.5:1 on white |

Dark: the same roles on `#1e1f20` with `#28292a` header rows, `#3c4043` gridlines, `#e8eaed` text, `#8ab4f8` links and selection, `#81c995` for the active tab and gains, and the game's own quality colours, which were made for a dark screen. Character fills keep dark text in both themes. The theme follows the system; the button in the title bar cycles auto, light and dark and remembers the choice in the browser.

Type: Arial (the sheet's default), Liberation Sans where Arial is missing. No web fonts. Scale: 11px row and column headers, 13px cells and body, 15px block headers, 18px document title. Prose line height 1.5, cells 1.35 at 21px rows. Prose measure 72ch.

Spacing unit 4px. Cell padding 3px 6px. Radius: cells and blocks 0, controls 4px, menus and dialogs 8px.

Motion: one moment, the selection outline. Focus draws the sheet's blue 2px box in 100ms. Rows take the hover fill in 120ms. Nothing slides or fades in. Reduced motion turns both off.

## Mode sheet

What a default model makes for this brief, measured on 2026-11-11 with three fresh plans. Off-limits unless asked for:

- Warm dark ink or parchment grounds with a copper, ember or oxblood accent and verdigris green.
- Fraunces or Alegreya SC headings, IBM Plex Mono for numbers.
- A 2x2 grid of tool cards, each with the question it answers and one live number. A roster strip of class-coloured tags. Buttons "Open the group sim" and "Read the notes". A "KB updated" stamp in the masthead. Ledger cards, item-tooltip cards.
- The site's previous look: teal near-black with gold, Cinzel capitals, 18px rounded cards, pill tabs with blur, tracked capital labels, middot meta strings, stat tiles with a coloured left border.
