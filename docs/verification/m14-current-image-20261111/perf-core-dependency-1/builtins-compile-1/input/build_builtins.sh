#!/usr/bin/bash
# Genuine matched compiler-builtins with actual new kernel-profile core metadata.
set -euo pipefail
set -o noclobber
umask 022
/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/bin/rustc --crate-name compiler_builtins --crate-type rlib --edition=2024 --sysroot=/dev/null -C metadata=mckernel_kernel_195_builtins -C panic=abort -C opt-level=2 -C debuginfo=2 -C code-model=large -C relocation-model=static -C no-redzone=yes -C force-frame-pointers=yes -C overflow-checks=off -C force-unwind-tables=no -C no-vectorize-loops -C no-vectorize-slp -C target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma -Z dep-info-omit-d-target -Z binary-dep-depinfo --extern core=/core-output/libcore.rmeta -L dependency=/core-output --cfg 'feature="compiler-builtins"' --cfg 'feature="no-asm"' --cfg intrinsics_enabled --cfg optimizations_enabled --cfg 'feature="unstable-intrinsics"' --cfg 'feature="mem-unaligned"' --emit=obj=/core-output/compiler_builtins.o,metadata=/core-output/libcompiler_builtins.rmeta,dep-info=/core-output/compiler_builtins.raw.d /home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/lib/rustlib/src/rust/library/compiler-builtins/compiler-builtins/src/lib.rs
/usr/bin/readelf -W -h -S /core-output/compiler_builtins.o > /core-output/builtins-elf.stdout
/usr/bin/readelf -W -s -r /core-output/compiler_builtins.o > /core-output/builtins-symbols-relocations.stdout
/usr/bin/objdump -drw /core-output/compiler_builtins.o > /core-output/builtins-disassembly.stdout
