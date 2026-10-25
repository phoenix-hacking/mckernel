#!/bin/bash
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# PROPOSED only: coordinator must supply actual clearance plus ordinary grant.
# Args: absolute pinned rustc, granted single CPU, fresh disjoint absolute output dir.
set -euo pipefail
rustc_path=$1
fixture_cpu=$2
fixture_output=$3
fixture_source=$(cd -- "$(dirname -- "$0")" && pwd)
repo_source=/home/holden/mckernel
mkdir -- "$fixture_output"
export TMPDIR="$fixture_output"
run_compile() {
    timeout --signal=TERM --kill-after=6s 90s taskset -c "$fixture_cpu" \
        prlimit --as=2147483648 --cpu=60 --fsize=33554432 --nofile=256 \
        --core=0 --stack=2097152 -- "$@"
}
run_compile "$rustc_path" --edition=2021 --crate-type=staticlib --crate-name io_parity \
    --cfg f03_io_diagnostic_callbacks_candidate -C opt-level=1 -C panic=abort \
    "$fixture_source/parity.rs" -o "$fixture_output/libio_parity.a" \
    >"$fixture_output/rustc.stdout" 2>"$fixture_output/rustc.stderr"
run_compile /usr/bin/cc -std=gnu11 -O1 -Wall -Wextra -Werror \
    -I "$repo_source/lib/include" "$fixture_source/parity.c" \
    "$fixture_output/libio_parity.a" -ldl -lpthread -lm -o "$fixture_output/parity" \
    >"$fixture_output/cc.stdout" 2>"$fixture_output/cc.stderr"
timeout --signal=TERM --kill-after=6s 15s taskset -c "$fixture_cpu" \
    prlimit --as=2147483648 --cpu=10 --fsize=33554432 --nofile=256 \
    --core=0 --stack=2097152 -- "$fixture_output/parity" \
    >"$fixture_output/parity.stdout" 2>"$fixture_output/parity.stderr"
