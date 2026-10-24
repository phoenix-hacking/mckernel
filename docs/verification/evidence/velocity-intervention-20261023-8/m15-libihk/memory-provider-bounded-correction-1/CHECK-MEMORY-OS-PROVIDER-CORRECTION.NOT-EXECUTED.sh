#!/bin/bash
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One bounded production-provider link correction; no altered Rust/API/fixture body.
set -eu
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-libihk
: "${CC:?explicit granted GCC9}" "${RUSTC:?explicit granted Rust1.92}"
"$RUSTC" --edition=2021 --crate-name ihklib_memory_fixture --crate-type staticlib -C panic=abort -C codegen-units=1 -C relocation-model=pic -C opt-level=2 -o memory-provider-bounded-correction-1/libihklib_memory.fixture.a libihk_memory_chain.rs
"$CC" -std=gnu11 -O2 -Wall -Wextra -Wno-unused-parameter -I/home/holden/mckernel/ihk/linux/include reference_cpu.c reference_memory_os.c test_memory_os_equivalence.c memory-provider-bounded-correction-1/libihklib_memory.fixture.a -Wl,--gc-sections -Wl,--wrap=calloc -Wl,--wrap=free -o memory-provider-bounded-correction-1/test_memory_os_equivalence
./memory-provider-bounded-correction-1/test_memory_os_equivalence
