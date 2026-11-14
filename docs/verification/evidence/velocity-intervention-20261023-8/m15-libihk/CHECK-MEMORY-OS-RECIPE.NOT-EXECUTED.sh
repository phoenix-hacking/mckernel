#!/bin/bash
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Execute only after root grants the existing ordinary fixture profile.
# Host-only controlled libc/ioctl/directory/allocator consumers; no real IHK device use.
set -eu
cd /home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-8/m15-libihk
: "${CC:?explicit granted compiler}" "${RUSTC:?explicit granted Rust compiler}"
"$RUSTC" --edition=2021 --crate-name ihklib_memory_fixture --crate-type lib -C panic=abort -C codegen-units=1 -C relocation-model=pic -C opt-level=2 --emit=obj=ihklib_memory.fixture.o libihk_memory_chain.rs
"$CC" -std=gnu11 -O2 -Wall -Wextra -Wno-unused-parameter -I/home/holden/mckernel/ihk/linux/include reference_cpu.c reference_memory_os.c test_memory_os_equivalence.c ihklib_memory.fixture.o -Wl,--wrap=calloc -Wl,--wrap=free -o test_memory_os_equivalence
./test_memory_os_equivalence
