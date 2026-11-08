#!/bin/sh
# Build MythicSim's Forever engine (vendor/mythicsim-forever-engine, MIT) for the browser.
# Needs rustup; the toolchain and wasm target are pinned in engine-wasm/rust-toolchain.toml.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
git -C "$ROOT" submodule update --init vendor/mythicsim-forever-engine
cd "$ROOT/engine-wasm"
cargo build --release --target wasm32-unknown-unknown
mkdir -p "$ROOT/dist"
gzip -9 -c target/wasm32-unknown-unknown/release/wowsim_engine.wasm > "$ROOT/dist/engine.wasm.gz"
ls -la "$ROOT/dist/engine.wasm.gz"
