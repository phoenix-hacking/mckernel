# SC-VM-01 host-clear error build/equivalence packet

Status: **READY FOR INDEPENDENT REVIEW; EXECUTION BLOCKED pending a focused
runner/helper.**  This packet is source/build evidence only.  It grants no
runtime, guest, application, production, or acceptance credit.

## Binding and scope

- Task: `SC-VM-01`; base/current worktree: `fc8832a385b52923ece48071c03384591926e270`.
- The exact five source inputs are read-only and must be copied to the fresh
  output root before any compiler starts:

| path | SHA-256 |
|---|---|
| `kernel/include/syscall.h` | `459e6d0faec3f1b8366a0d329571ef5ea813042706be11f9423b0399bbba6ffa` |
| `kernel/syscall.c` | `1f4836b5deef84b75801e461d4d13f683db2cb74802454f96965e8b7ca011647` |
| `kernel/rust/syscall_policy.rs` | `2edc424e01e3bb3acc7542432dde8fa0f977884558d3525efb0354acbc3c04ea` |
| `kernel/rust/tests/run_equivalence.sh` | `53c85fb9913d084eb11544477bde591f3a96b512f26b5d41708a9035831a492e` |
| `ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c` | `7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77` |

- Pinned image: `sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94`;
  image manifest SHA-256:
  `c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a`.
- Review profile: external pinned wrapper, four CPUs (`2-5`), 12 GiB,
  12 GiB swap limit/no swap, pids 512, network none, repository/image mounts
  read-only, UID `1000:1000`, `/tmp` only writable tmpfs, fresh exclusive
  output root under `/home/holden/mckernel-work`, and the existing development
  lock.  No host output path may be reused.

## Intended bounded checks

The selected C/Rust cases are the `do_munmap_body_result` host-clear branch:
successful clear; clear `-44` with no prior error; prior remove `-12` while
clear returns `-45`; callback count/arguments, logging, and returned first
error.  The ABI/signature controls must bind `clear_host_pte` and its bridge
as `long`, the Rust `DoMunmapClearHostFn` as `-> CLong`, and reject the old
void callback declarations.  `git diff --check` and the existing negative
controls (wrong return type, omitted propagation, and wrong callback prototype)
are required.

The following commands are the exact preflight commands (noninteractive,
read-only) for the dispatcher/owner:

```sh
set -eu
OUT=/home/holden/mckernel-work/sc-vm-01-clear-build-equivalence-20260928-1
test ! -e "$OUT"
mkdir -m 700 "$OUT"
sha256sum kernel/include/syscall.h kernel/syscall.c kernel/rust/syscall_policy.rs \
  kernel/rust/tests/run_equivalence.sh \
  ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c > "$OUT/input-sha256.txt"
git diff --check -- kernel/include/syscall.h kernel/syscall.c \
  kernel/rust/syscall_policy.rs kernel/rust/tests/run_equivalence.sh \
  ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c
grep -F 'long clear_host_pte(uintptr_t addr, size_t len, int holding_memory_range_lock)' kernel/syscall.c
grep -F 'typedef long (*do_munmap_clear_host_fn_t)' kernel/syscall.c
grep -F 'type DoMunmapClearHostFn = unsafe extern "C" fn(CULong, SizeT, CInt) -> CLong;' kernel/rust/syscall_policy.rs
! grep -F 'typedef void (*do_munmap_clear_host_fn_t)' kernel/syscall.c
! grep -F 'type DoMunmapClearHostFn = unsafe extern "C" fn(CULong, SizeT, CInt);' kernel/rust/syscall_policy.rs
```

## Execution blocker (must not be papered over)

`kernel/rust/tests/run_equivalence.sh` has no row/fixture selector.  Its only
entry point runs the full unrelated equivalence and object/undefined-symbol
suite.  No reviewed helper currently exists that extracts and compiles only
the listed host-clear C body and Rust body, compares those rows, and runs the
requested negative controls.  Therefore there is no honest exact command yet
for “compile native C and Rust selected body” or “run only relevant rows”.
Do **not** invoke the full script, invent a temporary extractor, or claim a
build result.  An independently reviewed helper/command must first bind the
five inputs, selected row IDs, C/Rust oracle, ABI negatives, compiler streams,
and artifact hashes.  This is the sole blocker; source review does not waive it.

## Required retained evidence when unblocked

Retain the wrapper identity/invocation, image and manifest hashes, UID/CPU/
memory/network/read-only evidence, copied-input hashes, `/usr/bin/gcc` and
`/usr/bin/rustc` identity and SHA-256, exact compile/link argv (at most four
jobs), stdout/stderr/status per command, C/Rust row output and equality digest,
ABI/signature and negative-control results, object/dependency maps, and every
artifact SHA-256.  Stop on the first unexpected failure and preserve all
streams.  No retry in the same root.

The owner must finish each attempt within 120 seconds per command and remove
the container and temporary output by the reviewed cleanup deadline (10
minutes after terminal status); verify absence by exact ID/name/label.  The
dispatcher owns independent review before execution and any cleanup escalation.

## Review boundary

Independent review must verify the five hashes, image/manifest pins, exact
profile, fresh-root rule, selected-row definition, negative controls, missing
helper blocker, evidence schema, and that this packet cannot be interpreted as
application or production acceptance.  Original source and all prior failure
records remain unchanged.
