# Craft Profits data

`fetch_inputs.sh` downloads everything into `raw/` (not committed) and runs `build_data.py`, which writes
`data/crafts.json`. `tools/build_crafts.py` then builds the page from it.

| Input | Source | Used for |
| --- | --- | --- |
| Recipes, reagents, yields | AHledger `/v1/crafting/{house}?all=1` | every recipe on the page |
| Price tables, every house | AHledger `/v1/pricetable/{house}` | the built-in scan, and reference prices for trimming |
| ItemSparse, Item | Forever client build 1.60.1.70862 via wago.tools | names, quality, vendor buy and sell prices, binding |
| SkillLineAbility | same | when a recipe turns yellow and grey |
| ItemEffect, ItemXItemEffect | same | which recipe item teaches a recipe, and its required skill |
| Profession tables | MetaBot | learn skill for trainer recipes, trainer or recipe item |
| Item pages | MetaBot (Classic vendor lists) | whether a vendor sells an item, and to which faction |
| Item endpoint | AHledger `/v1/items/{id}` | sell price for items the client tables lack |
| Sales estimates | the last field of each AHledger price table | units sold a day per unit listed, the median over a region's houses that report sales |
| Crate guide | Method | every Waylaid Crate and the fills it accepts (`guides.json`) |
| Favor guide | wow.gg | Merchant's Favor per crate, Craftsman's Writ items, recipes sold for favor (`guides.json`) |

AHledger's API is free to use with credit; the page says "Prices from AHledger" and links to ahledger.com.
