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
| SkillLineAbility, Classic Era | Classic Era client build 1.15.9.70576 via wago.tools | how far Forever moved each recipe's skill colors |
| `data/skills.lua` | [MissingTradeSkillsList](https://github.com/Thumbkin/MissingTradeSkillsList_Classic) addon | the skill at which a Classic trainer teaches a recipe, and the trainer's fee |
| Profession tables | MetaBot | trainer or recipe item; its estimated learn skill for recipes new in Forever |
| Item pages | MetaBot (Classic vendor lists) | whether a vendor sells an item, and to which faction |
| Item endpoint | AHledger `/v1/items/{id}` | sell price for items the client tables lack |
| Sales estimates | the last field of each AHledger price table | units sold a day per unit listed, the median over a region's houses that report sales |
| Crate guide | Method | every Waylaid Crate and the fills it accepts (`guides.json`) |
| Favor guide | wow.gg | Merchant's Favor per crate, Craftsman's Writ items, recipes sold for favor (`guides.json`) |

## Learn skill

The client does not say at what skill a trainer teaches a recipe. Forever moved most Classic recipes down the skill
range by a fixed amount each: yellow and grey moved together in 412 of 413 recipes both games share. So the learn
skill is Classic's, moved by the same amount. For the 669 recipes taught by a recipe item, where Forever's requirement
is in the client, that rule gives the right number 644 times. Recipes new in Forever fall back to MetaBot's estimate
and are flagged in the data (`R[12]`). Trainer fees are Classic's (`R[13]`, copper).

An older copy of some recipes is still in the tables under the same name, making an item no house has ever listed.
Those are dropped when a namesake's item is on three or more houses.

AHledger's API is free to use with credit; the page says "Prices from AHledger" and links to ahledger.com.
