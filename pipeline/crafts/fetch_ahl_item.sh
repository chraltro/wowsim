#!/bin/sh
# fetch_ahl_item.sh RAW ID: name, quality and vendor sell price for an item the client tables lack.
RAW="$1"; id="$2"
out="$RAW/ahl_items/$id.json"
[ -s "$out" ] && exit 0
curl -sS -m 30 -A "wowsim-crafts (personal tool; prices from AHledger)" "https://api.ahledger.com/v1/items/$id?game=forever" -o "$out"
sleep 0.6
