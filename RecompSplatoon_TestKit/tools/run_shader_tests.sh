#!/usr/bin/env bash
# tools/run_shader_tests.sh — Build & run the R700 → GLSL test harness.
#
# Usage:
#     tools/run_shader_tests.sh                              # unit tests only
#     tools/run_shader_tests.sh <fixtures_dir>               # + real shader fixtures
#
# Requires:
#     - g++ or clang++ with C++20
#     - RebrewU checked out at /app/vendor/rebrewu (see docs/AUDIT.md)
#     - Optional: glslangValidator on PATH for strict GLSL syntax check
set -eu

RBREW_DIR="${RBREW_DIR:-/app/vendor/rebrewu}"
GX2_DIR="${RBREW_DIR}/port/os/gx2"
TEST_SRC="/app/tests/test_r700_to_glsl.cpp"
OUT_BIN="/app/build/test_r700_to_glsl"

if [ ! -d "$RBREW_DIR" ]; then
    echo "error: $RBREW_DIR not found — see docs/AUDIT.md §1" >&2
    exit 2
fi

mkdir -p /app/build
g++ -std=c++20 -Wall -Wno-unused-parameter -Wno-comment \
    -I"$GX2_DIR" \
    "$TEST_SRC" \
    "$GX2_DIR/r700_to_glsl.cpp" \
    -o "$OUT_BIN"

if [ $# -ge 1 ]; then
    RECOMP_FIXTURES_DIR="$1" "$OUT_BIN"
else
    "$OUT_BIN"
fi
