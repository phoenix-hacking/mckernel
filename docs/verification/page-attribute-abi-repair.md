# Preserve 64-bit page attributes across existing Rust components

The local compatibility rebuild of `496e2fc8` succeeded and retained the
existing Rust image, host helpers, and user-tool consumers. Its compiler
warnings exposed inconsistent external declarations between existing Rust
modules. Inspection of `arch/x86_64/kernel/include/arch-memory.h` confirms that
`enum ihk_mc_pt_attribute` contains `PTATTR_NO_EXECUTE` at bit 63. It is an
eight-byte unsigned value on this target, not a four-byte C `int`.

The first repair retains `mem_helpers.rs::ihk_mc_map_virtual`, its existing
mapping/rollback sequencer, and the XPMEM permission/setting bridges. Their
attribute arguments, callbacks, and return declarations are adapted to the
existing 64-bit ABI. `abi.rs` names that representation, and `abi_checks.c`
asserts the actual header's enum width and NX value during the kernel build.
No memory-management algorithm or existing Rust body is replaced. The existing
C bridge already takes the full-width enum; the stale Rust-side declaration
and helper prototype are corrected. The temporary C bridge remains part of the
separately tracked Rust/assembly retirement work.

The original memory equivalence fixture now carries NX through its existing
successful mapping case, with full-width capture and callback signatures.
The additional C ABI probe links the real built Rust object, calls its public
mapping and XPMEM entry points through the existing C headers, and substitutes
only the hardware-effect callbacks. It checks zero, low bits, bits 31/32/63,
all bits, rollback at every page, unmapping, and rejection of negative counts.
It does not execute privileged instructions, change live page tables, or prove
a guest workload. The retained original object is the negative regression
control; a rebuilt object must pass the same probe.

Remaining declaration disagreements in other components are still under
review. This repair does not claim complete shared-ABI closure, native boot,
or production tracker credit.

Local verification on 2026-09-07 used the offline, unprivileged compatibility
container with four CPUs and a 12-GiB memory limit. The original `496e2fc8`
object fails both page-map and XPMEM attribute probes. The repaired image
build passes, and its Rust object passes both probes. The existing memory/init
and XPMEM equivalence cases also pass, with digests `00338ce95ffd5b5d` and
`6674c6cafec0e555`. Their C reference objects were compiled in the same run.
The full historical equivalence harness is not claimed: it also references
Rust crates absent from the pinned IHK submodule. The bounded runner extracts
the original fixtures and commands without replacing their test logic.

Repeat the two checks inside the isolated compatibility environment, using a
writable private source checkout and new output directories:

```sh
python3 scripts/mckernel_page_attribute_abi.py \
  --build-dir /work/compat-build-pageattrs-20260907 \
  --output-dir /work/page-attribute-probe-new
python3 kernel/rust/tests/run_memory_equivalence.py \
  --repo /work/compat-source-pageattrs-20260907 \
  --output-dir /work/memory-xpmem-equivalence-new
```

The compatibility build also passes its existing no-SIMD, Rust linkage,
syscall composition, and configured source-retirement checks. These checks
do not imply a C-free image: its executable sections contain 614,235 Rust
bytes out of 783,895 total (78.356795%), with C, assembly, and padding still
in the remainder. Compiler warnings in other external declarations remain.
The source is `496e2fc8` plus this recorded ABI repair, not the clean parent
revision. See `page-attribute-abi-repair-20260907.json` for retained inputs,
build reports, and logs.
