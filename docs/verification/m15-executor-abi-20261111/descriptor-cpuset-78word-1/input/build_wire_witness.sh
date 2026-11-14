#!/usr/bin/bash
# Exactly the reviewed declaration-only C/Rust object and passive metadata commands.
set -euo pipefail
set -o noclobber
umask 022
/usr/bin/cc -std=c11 -Wall -Wextra -Werror -fno-common -fPIC -I/input -c /input/descriptor_cpuset_abi.c -o /output/C-descriptor-abi.o
/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/bin/rustc --crate-name m15_f02_descriptor_abi --crate-type lib --edition=2021 -C panic=abort -C opt-level=2 -C debuginfo=1 -C force-unwind-tables=no --emit=obj=/output/Rust-descriptor-abi.o /input/descriptor_cpuset_abi.rs
/usr/bin/readelf -W -h -S -s -r /output/C-descriptor-abi.o > /output/C-descriptor-abi.elf.txt
/usr/bin/readelf -W -h -S -s -r /output/Rust-descriptor-abi.o > /output/Rust-descriptor-abi.elf.txt
