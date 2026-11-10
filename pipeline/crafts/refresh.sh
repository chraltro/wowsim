#!/bin/sh
# Refresh data/crafts.json from today's auctions in a few minutes instead of half an hour.
# Re-downloads every Forever house's price table (the built-in scan, the cross-house reference prices and sell speeds),
# fetches pages only for items not seen before, and rebuilds. A table that fails to download keeps its old copy.
# Needs raw/ from an earlier fetch_inputs.sh run: recipes and client tables only change with a game build.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
RAW="$HERE/raw"
UA="wowsim-crafts (personal tool; prices from AHledger)"
[ -d "$RAW/pt" ] || { echo "No raw/ folder here. Run fetch_inputs.sh once first." >&2; exit 1; }
cd "$RAW"
curl -sS -m 20 -A "$UA" -o markets.json.new "https://api.ahledger.com/v1/markets"
python3 -c "import json;d=json.load(open('markets.json.new'));m=d.get('markets',d);assert m;print(chr(10).join(x['id'] for x in m if x['game']=='forever'))" > market_ids.new
mv markets.json.new markets.json
mv market_ids.new market_ids.txt
kept=0
while read -r mid; do
  curl -sS -m 40 -A "$UA" -o "pt/$mid.new" "https://api.ahledger.com/v1/pricetable/$mid" || true
  if head -c 5 "pt/$mid.new" 2>/dev/null | grep -q '^AHL1'; then mv "pt/$mid.new" "pt/$mid.txt"; else rm -f "pt/$mid.new"; kept=$((kept + 1)); echo "kept the old table for $mid" >&2; fi
  sleep 1
done < market_ids.txt
echo "$(wc -l < market_ids.txt) houses, $kept kept as they were"
python3 "$HERE/prepare_lists.py" "$RAW"
xargs -P 4 -L 1 "$HERE/fetch_mb.sh" "$RAW" < mb_list.tsv
xargs -P 2 -L 1 "$HERE/fetch_ahl_item.sh" "$RAW" < ahl_need.txt
python3 "$HERE/build_data.py" "$RAW"
