#!/bin/sh
# fetch_mb.sh RAW ID SLUG: the first 165 kB of a MetaBot item page holds the vendor list and the FAQ with the price.
RAW="$1"; id="$2"; slug="$3"
out="$RAW/mb/$id.html"
[ -s "$out" ] && exit 0
curl -sS -m 60 -A "wowsim-crafts (personal tool)" "https://metabot.gg/en/wow-forever/items/$slug" 2>/dev/null | head -c 165000 > "$out"
sleep 0.3
