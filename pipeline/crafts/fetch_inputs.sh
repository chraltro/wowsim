#!/bin/sh
# Download every input for data/crafts.json into pipeline/crafts/raw/ (not committed), then build it.
# Takes about half an hour, most of it MetaBot item pages. Re-running skips pages already fetched.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
RAW="$HERE/raw"
UA="wowsim-crafts (personal tool; prices from AHledger)"
BUILD=1.60.1.70862
MARKET=forever.rppvp.alliance.eu
mkdir -p "$RAW/pt" "$RAW/mb" "$RAW/mbprof" "$RAW/ahl_items"
cd "$RAW"
# Recipes and reagents for every profession
for p in Alchemy Blacksmithing Cooking Enchanting Engineering "First Aid" Herbalism Leatherworking Mining Skinning Tailoring; do
  f="crafting_$(echo "$p" | tr ' A-Z' '_a-z').json"
  curl -sS -m 60 -A "$UA" -o "$f" "https://api.ahledger.com/v1/crafting/$MARKET?profession=$(echo "$p" | sed 's/ /%20/g')&all=1&limit=1000"
  sleep 2
done
# Price tables for every Forever house: the built-in scan and the cross-house reference prices
curl -sS -m 20 -A "$UA" -o markets.json "https://api.ahledger.com/v1/markets"
python3 -c "import json;d=json.load(open('markets.json'));m=d.get('markets',d);print(chr(10).join(x['id'] for x in m if x['game']=='forever'))" > market_ids.txt
while read -r mid; do curl -sS -m 40 -A "$UA" -o "pt/$mid.txt" "https://api.ahledger.com/v1/pricetable/$mid"; sleep 1; done < market_ids.txt
# Client tables: names, qualities, vendor prices, skill-up levels, recipe items
for t in ItemSparse Item SkillLineAbility ItemEffect ItemXItemEffect; do
  curl -sS -m 180 -o "$t.csv" "https://wago.tools/db2/$t/csv?build=$BUILD"
done
# MetaBot recipe tables: learn skill and whether a recipe comes from a trainer or a recipe item
for p in alchemy blacksmithing cooking enchanting engineering first-aid leatherworking mining herbalism skinning tailoring; do
  curl -sS -m 120 -A "$UA" -o "mbprof/$p.html" "https://metabot.gg/en/wow-forever/professions/$p"; sleep 1
done
# Waylaid Crates (Method) and favor per crate, Craftsman's Writs and favor recipes (wow.gg) -> guides.json
mkdir -p guides
curl -sS -m 60 -A "Mozilla/5.0 ($UA)" -o guides/method_crates.html "https://www.method.gg/wow-forever/how-to-get-waylaid-crates-and-merchants-favor-in-wow-forever"
curl -sS -m 60 -A "Mozilla/5.0 ($UA)" -o guides/wowgg_favor.html "https://wow.gg/guides/merchants-favor"
python3 "$HERE/parse_guides.py" "$RAW"
python3 "$HERE/prepare_lists.py" "$RAW"
xargs -P 4 -L 1 "$HERE/fetch_mb.sh" "$RAW" < mb_list.tsv
xargs -P 2 -L 1 "$HERE/fetch_ahl_item.sh" "$RAW" < ahl_need.txt
python3 "$HERE/build_data.py" "$RAW"
