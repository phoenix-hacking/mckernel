# Independent source review: paired perf selector

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Disposition: **source-only; paired selection and ABI/provider proof remain open**.
No execution, compilation, native work or canonical modification was performed
for this review. Source review does not grant any physical operation or acceptance.

## Bound inputs

* `perf-paired-selector-private-1/PERF-PAIRED-SELECTOR.PRIVATE.patch`: SHA-256
  `7aaa310aaa15d12b0ce3a4c49a48f40e3a0e23a2d14c134b264935fbed93f345`.
* `perf-paired-selector-private-1/PROFILE.SOURCE-ONLY.json`: SHA-256
  `5b826ce234767f7f9964b2096e503bdb4af437592b82f7ab0e9b03b64683f1a3`.
* `perf-paired-selector-private-1/REAL-HEADER-ABI-WITNESS.c.inc`: SHA-256
  `212fbf03425ea1e883f01cd4132b3821cca224a015890cabeaf3fda95e80d8c0`.
* `nonheld-signal-perf-group-compositor-1/NONHELD-SIGNAL-PERF-GROUP.PRIVATE.patch`:
  SHA-256 `595d137bcaba9b4ce85361623edd5a12c174dc3baa53670bda5352ce80dd1d1a`.
* Bound baseline `M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/syscall.c`:
  SHA-256 `3388adb79adff66eb85ae65a443af2c18e7b2057dd76d0ec99b531d62a36cab3`;
  sibling `kernel/CMakeLists.txt` SHA-256
  `30e3a04bf48777d4891f7390804e574ca221e4234e9a8d7879bb068910a13fbd`.
* Prior producer `current-frontier-successor-1/PROFILE.SOURCE-ONLY.json`:
  SHA-256 `8ab49c299dfc9218ddcf8df3cf71474d51e87167abe4cd166841ea47c3a32e2d`.
  It is an input description, not authority for this invocation.

## Selector and actual flags

The C delta preserves the baseline C function when its experimental macro is
absent, and substitutes an extern declaration when present. The non-held Rust
patch gates its exported entry on `f03_perf_entry_candidate`, `enable_perf`, and
x86_64 and separately compile-errors when listed Rust provider cfgs are absent.
The C delta separately rejects its selector without ENABLE_PERF, x86_64, the
policy helper, sync-child, leaf and allocation C macros. The prior producer argv
has Rust `enable_perf`, sync-child, leaf and allocation cfgs and has their
corresponding selected C macros. Neither prior argv contains the new entry
selector. These observations establish source intent, not flags actually emitted
for a new candidate.

No cross-language guard enforces both new selectors. C-on/Rust-off can leave no
entry provider; C-off/Rust-on can select two providers. Actual behavior depends
on the final source, all consumers, dead-section handling and link configuration;
do not call either case a proven deterministic link result without running the
proper oracle. Require an exact producer profile binding both selected additions,
the actual emitted C/Rust argv and fresh paired on/off/mismatch link checks.

C `ENABLE_PERF` is not an argument in the retained C command. `cls.h` and
`process.h` include `<config.h>`, top-level CMake generates `config.h` from
`config.h.in` (`#cmakedefine ENABLE_PERF 1`), and the retained argv searches
multiple include roots including `/work/output/build`. Bind the actual generated
header at the resolved include path, its hash, complete ordered include closure,
SDK21, compiler and flags; verify the macro from the exact preprocessed command.
CMake's default or the Rust cfg is not evidence of that generated header's value.

## 31 scalars and 13 callbacks

The witness array has 31 C expressions in the same textual field order as the
Rust binding: four attr size/offsets followed by 27 constants, object sizes and offsets,
ending with the five mckfd callback offsets. Rust uses explicit constants, `size_of`/`offset_of`,
including `Mckfd.padding` for C `sig_no`. The C and Rust sides each assert some
independent layout facts, including 352-byte binding size; no source assertion
compares the actual 31 emitted C words with the 31 words in the Rust-defined
`f03_perf_entry_binding_v1`. The C extern declaration neither emits nor verifies
the Rust value. Bind both objects and compare all 31 unsigned 64-bit values in
order using their actual target endianness, offsets and section/relocation data;
a matching count or total struct size is insufficient. Confirm the C bitfield
frequency behavior separately; it is accessed through a callback and is not a
scalar offset in this array.

C types its 13 fields using `__typeof__` of selected C expressions, but does not
emit a callback table or compare the Rust function-pointer types and targets.
The Rust binding selects, in order: `syscall_copy_from_user_bridge`,
`f03_perf_attr_frequency_v1`, `f03_perf_event_allocate_v1`, the local
`perf_entry_counter_alloc_or_release`, `perf_event_open_do_syscall_bridge`,
`perf_event_alloc_kmalloc_bridge`, `f03_perf_read_v1`, `f03_perf_ioctl_v1`,
`f03_perf_mmap_v1`, `f03_perf_close_v1`, `f03_perf_fcntl_v1`,
`syscall_mckfd_lock_bridge`, `syscall_mckfd_unlock_bridge`. Review all thirteen
function signatures and calling conventions against the exact preprocessed C
provider declarations, pointer/return widths and Rust aliases, then verify the
actual Rust binding's relocation/target for each slot. Typed C mckfd/context
pointers and Rust erased pointer declarations require ABI and semantic review;
the witness struct layout alone does not perform it. Its sys_perf_event_open
static assertion checks the declared C function type, not Rust's linked definition.

The separate C witness is a whole syscall.c translation unit compiled with the
same paired source/config and additional `MCKERNEL_F03_PERF_ENTRY_ABI_WITNESS`.
The `used` static 31-word array is a source/ABI witness, not an image component.
Keep its output in a distinct path and **exclude it from the final image and
all ordinary link inputs**: linking it alongside the selected syscall object
would duplicate syscall.c's nonstatic definitions and may alter sections/metadata.
Inspect its actual object and symbol/section retention rather than assuming
`used` implies final image retention. Never compile a second TU by concatenating
the `.c.inc` to a patch that already appends the same definitions.

## Provider and ownership checks

The Rust counter wrapper calls `f03_perf_counter_allocate_v1` and frees the
fresh event on a negative result. In the inspected Rust x86 provider, the latter
scans the thread map and ignores the event; the analogous C provider also scans
without publishing it. This supports the stated assumption for those exact
sources only, not for a substituted or additional provider. Verify actual selected
`f03_perf_counter_allocate_v1`, `ihk_mc_perfctr_alloc`, tracked-free provider and
local wrapper identity, symbol uniqueness and all dependencies in the final
link. Prove the event is still private on the counter and group-error paths,
that the free is exactly once, and that concurrency/other failure cleanup matches
the selected real group and publication code; these are not established by a
31-scalar witness or link check. The non-held patch explicitly leaves later
Linux-fd and mckfd allocation failure paths as-is; it does not qualify them.

Next step under a fresh reviewed operation/resource release is the exact paired
producer and separate witness object with complete input/header binding, followed
by scalar comparison, callback/type/relocation and unique-provider checks, and
matching original metadata/link and functional/native qualification. No C body
retirement or M14 acceptance follows from this review.
