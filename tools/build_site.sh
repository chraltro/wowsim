#!/bin/sh
# Build the public site into dist/: only Forever Craft Profits (dist/crafts/), plus a root page that sends you there.
# The Shaman Sim, the Group Sim and the start page carry the group's names, so they are built for your own use only:
# ./tools/build_local.sh puts them in local/site/ (ignored by git). The knowledge bank is not published either.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
rm -rf "$ROOT/dist"
mkdir -p "$ROOT/dist"
python3 "$ROOT/tools/build_crafts.py"
cat > "$ROOT/dist/index.html" <<'HTML'
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Craft Profits</title>
<meta http-equiv="refresh" content="0; url=crafts/"><link rel="canonical" href="crafts/"></head>
<body style="font:13px Arial,sans-serif;margin:16px"><a href="crafts/">Craft Profits</a></body></html>
HTML
touch "$ROOT/dist/.nojekyll"
ls -la "$ROOT/dist" "$ROOT/dist/crafts"
