#!/usr/bin/bash
# Genuine matched Rust1.95 core dependency; not a kernel/image/PMU execution.
set -euo pipefail
set -o noclobber
umask 022
/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/bin/rustc --crate-name core --crate-type rlib --edition=2024 -C panic=abort -C opt-level=2 -C debuginfo=2 -C code-model=large -C relocation-model=static -C no-redzone=yes -C force-frame-pointers=yes -C overflow-checks=off -C force-unwind-tables=no -C no-vectorize-loops -C no-vectorize-slp -C target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma -C metadata=mckernel_kernel_195 --cfg no_fp_fmt_parse --sysroot=/dev/null -Z dep-info-omit-d-target -Z binary-dep-depinfo --emit=obj=/core-output/core.o,metadata=/core-output/libcore.rmeta,dep-info=/core-output/core.raw.d /home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/lib/rustlib/src/rust/library/core/src/lib.rs
/usr/bin/readelf -W -h -S /core-output/core.o > /core-output/core-elf.stdout
/usr/bin/readelf -W -s -r /core-output/core.o > /core-output/core-symbols-relocations.stdout
/usr/bin/objdump -drw /core-output/core.o > /core-output/core-disassembly.stdout
