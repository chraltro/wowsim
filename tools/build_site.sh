#!/bin/sh
# Build the whole site into dist/: a landing page, the Shaman Sim (dist/shaman/), the
# Forever Group Sim (dist/forever/), Forever Craft Profits (dist/crafts/) and the knowledge bank (dist/kb/). The engine itself is built separately by
# tools/build_engine.sh into engine-wasm/engine.wasm.gz (needs Rust); everything here needs only Python.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 "$ROOT/tools/build.py"
python3 "$ROOT/tools/build_mc.py"
python3 "$ROOT/tools/build_crafts.py"
python3 "$ROOT/tools/build_kb.py"
cp "$ROOT/src/site/index.html" "$ROOT/dist/index.html"
cp "$ROOT/NOTICE.md" "$ROOT/dist/NOTICE.txt"   # the MIT notices travel with the compiled engine
touch "$ROOT/dist/.nojekyll"
ls -la "$ROOT/dist" "$ROOT/dist/shaman" "$ROOT/dist/forever" "$ROOT/dist/crafts" "$ROOT/dist/kb"
