#!/bin/bash
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# No real access/open/ioctl/close: fixture provides controlled symbols only.
# Requires explicit ordinary compiler profile grant; never run implicitly.
set -eu
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-libihk
: "${CC:?explicit granted C compiler}" "${RUSTC:?explicit granted Rust compiler}"
IHK_INCLUDE=/home/holden/mckernel/ihk/linux/include
"$RUSTC" --edition=2021 --crate-name ihklib_cpu_fixture --crate-type lib --cfg ihklib_cpu_fixture -C panic=abort -C codegen-units=1 -C relocation-model=pic -C opt-level=2 --emit=obj=ihklib_cpu.fixture.o ihklib_cpu.rs
"$CC" -std=gnu11 -O2 -Wall -Wextra -Wno-unused-parameter -I"$IHK_INCLUDE" reference_cpu.c test_cpu_equivalence.c ihklib_cpu.fixture.o -o test_cpu_equivalence
./test_cpu_equivalence
"$RUSTC" --edition=2021 --crate-name ihklib_cpu --crate-type lib -C panic=abort -C codegen-units=1 -C relocation-model=pic -C opt-level=2 --emit=obj=ihklib_cpu.o ihklib_cpu.rs
# Expected refusal, captured separately by approved driver: same rustc with --cfg ihklib_with_krm.
# Production integration next removes exactly the five exported C definitions,
# retains C static device_readable for unported APIs, and links this PIC Rust object.
# CMake WITH_KRM=ON must refuse before selecting it. No installed C removal yet.
