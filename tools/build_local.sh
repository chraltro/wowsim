#!/bin/sh
# Build every page for your own use into local/site/ (ignored by git, never published): the start page, the Shaman Sim,
# the Group Sim and Craft Profits, with tabs between them. Open local/site/index.html, or serve the folder
# (python3 -m http.server -d local/site) so the Group Sim can load its engine.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
python3 "$ROOT/tools/build.py"
python3 "$ROOT/tools/build_mc.py"
python3 "$ROOT/tools/build_crafts.py"
mkdir -p "$ROOT/local/site/crafts"
python3 - "$ROOT" <<'PY'
import sys; root = sys.argv[1]; sys.path.insert(0, root + '/tools')
from shell import shell
open(root + '/local/site/index.html', 'w').write(shell(open(root + '/src/site/index.html').read(), 'start', local=True))
PY
python3 - "$ROOT" <<'PY'
# the published crafts page has only its own tab; the local copy gets all four
import sys, re; root = sys.argv[1]
h = open(root + '/dist/crafts/index.html').read()
sys.path.insert(0, root + '/tools'); import shell as S
tabs = re.search(r'<nav class="xl-tabs".*?</nav>', h, re.S).group(0)
full = re.search(r'<nav class="xl-tabs".*?</nav>', S.shell('/*__SHEET_CSS__*/<!--__SHEET_TOP__--><!--__SHEET_TABS__-->', 'crafts', local=True), re.S).group(0)
open(root + '/local/site/crafts/index.html', 'w').write(h.replace(tabs, full))
PY
cp "$ROOT/NOTICE.md" "$ROOT/local/site/NOTICE.txt"
echo "built into $ROOT/local/site"
