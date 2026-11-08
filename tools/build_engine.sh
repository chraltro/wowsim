#!/bin/sh
# Build MythicSim's Forever engine (vendor/mythicsim-forever-engine, MIT) for the browser.
# Needs rustup; the toolchain and wasm target are pinned in engine-wasm/rust-toolchain.toml.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
git -C "$ROOT" submodule update --init vendor/mythicsim-forever-engine
# Our fixes to the engine, kept as patches over the pinned revision
for p in "$ROOT"/engine-wasm/patches/*.patch; do
  if git -C "$ROOT/vendor/mythicsim-forever-engine" apply --reverse --check "$p" 2>/dev/null; then echo "already applied: $(basename "$p")";
  else git -C "$ROOT/vendor/mythicsim-forever-engine" apply "$p" && echo "applied: $(basename "$p")"; fi
done
cd "$ROOT/engine-wasm"
cargo build --release --target wasm32-unknown-unknown
gzip -9 -c target/wasm32-unknown-unknown/release/wowsim_engine.wasm > "$ROOT/engine-wasm/engine.wasm.gz"
ls -la "$ROOT/engine-wasm/engine.wasm.gz"
