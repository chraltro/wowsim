#!/bin/sh
# Publish dist/ to the gh-pages branch, which GitHub Pages serves at https://chraltro.github.io/wowsim/
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC=$(git -C "$ROOT" rev-parse --short HEAD)
TMP=$(mktemp -d)
cp -R "$ROOT/dist/." "$TMP/"
cd "$TMP"
git init -q -b gh-pages
git add -A
git -c user.name="$(git -C "$ROOT" config user.name)" -c user.email="$(git -C "$ROOT" config user.email)" commit -q -m "Site built from $SRC"
git push -f "$(git -C "$ROOT" remote get-url origin)" gh-pages
rm -rf "$TMP"
