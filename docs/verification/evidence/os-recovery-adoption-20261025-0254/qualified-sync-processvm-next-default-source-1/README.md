Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private coherent successor reuses actual HOST-qualified sync_child_event
(F03 a640 source/9a14 actual, 3072 graph pairs plus genuine ABI) and the F06
process-VM public entry (a252 actual, ABI22/40 controlled pairs/4 flag cases).
Its baseline is accepted F42/NEXT10, independent receipt b9edb7a5. No new
algorithm, logger, offset body or thirteen-adapter implementation was written.
Only two public Rust exports become selected; expected C function removal
counts describe selection, not fifteen newly implemented algorithms.

Five canonical postimages are in candidate/; their exact preimages and hashes
are in COHERENT-SOURCE-PLAN.NOT-GRANTED.json:

| Path | Current SHA prefix | Private SHA prefix |
| --- | --- | --- |
| kernel/syscall.c | 8b8037ce | aeeb1d71 |
| kernel/rust/syscall_policy.rs | 5bc789e1 | 02ddaecf |
| arch/x86_64/kernel/syscall.c | d3cd4d9a | 060ae704 |
| kernel/CMakeLists.txt | edbd78df | cd41d90e |
| kernel/rust/f06_process_vm_entry.rs | absent | 0e9d9d23 |

The policy merge appends the exact qualified F03 layout/entry and the unchanged
F06 module declaration. Existing bodies and all prior NEXT10 changes remain.
The F03 C file is byte-identical to its current-context qualified candidate.
The F06 C successor equals the existing qualified composition API applied to
the current source; both fallback regions reverse byte-for-byte. The leaf is
the unchanged 5428-byte qualified consumer, with two distinct stack lock nodes,
thirteen callbacks and the sole canonical logger/offset storage reused.

The paired Rust cfgs are f03_sync_child_event_candidate and
f06_process_vm_entry_candidate. Their C selectors are
MCKERNEL_RUST_F03_SYNC_CHILD_EVENT and MCKERNEL_RUST_F06_PROCESS_VM_ENTRY.
They are added inside the existing supported CMake branch. Existing
enable_profile/enable_perf and Linux6.12/x86_64/non-UBSAN/non-DCFA lock context
are preserved. Genuine NOCACHE remains undefined. No new configuration scope
is qualified.

The profile reuses the unchanged reviewed four-command API: whole Rust object,
changed kernel/syscall.c, changed arch/x86_64/kernel/syscall.c, and identical
eleven-input raw ld/link.d. The same eight C prefix inputs remain read-only,
including F02 process b8168c1f; no prefix compiler command is replayed. The
closed Rust snapshot has106 regular files: only policy changes among the prior
105 and the one real module is added. Reuse the single reviewed read-only
/src/kernel/rust directory mount; binding the missing new leaf beneath the
immutable source parent is invalid. Original source6153/SDK21/toolchain/config,
UID1000, CPU2-5/12GiB/noswap/pids512/noNet and all guards remain unchanged.

ACCEPTANCE-INPUTS.SOURCE-ONLY.json and validator-templates/ are prepared before
any future clock or compiler. They bind the actual F42 C76/45 object references,
every baseline function name and the exact expected remaining75/31 sets. The
F06 fourteen names are confirmed allocated FUNCs in the actual current object;
the historical fourteen-symbol observer is not used as the current baseline.
No compiler-elision waiver exists. Thirty-three Rust exports carry forward,
sync_child_event and do_process_vm_read_writev make35, and the exact expected
Rust import delta removes those two names with no additions. C debug64 remains.
The scoped clone/panic/logger/full11ld/F02 data/alias gates are reused once.

Three new Rust immutable metadata objects must exactly match the authenticated
actual HOST sync object and final-image bytes: offsets64B/align8, attr ABI32B/
align8 and inherit pattern104B/align1. They must have unique Rust ownership and
allocated/read-only/non-executable sections. Existing PT_LOAD RWE semantics
and the ld warning stay explicit; this makes no runtime page-protection claim.
The corrected retained-process report reference and authenticated C-baseline/
exact-remaining-set predicates are retained. The postjoin reader is the accepted
exact data-binding wrapper; only its result label changes for this cohort.

Warnings start from actual141 Rust,7 kernel-C unused,0 arch-C and unchanged ld
RWX. The prior exact typed-pointer declaration disposition is bound to b9ed;
new deltas are captured and unknown warnings block artifact acceptance. No
warning suppression, casts, recompile or blanket declaration waiver is supplied.

Root next commands, after its current workload and normal independent release:

```sh
E=/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254
Q="$E/qualified-sync-processvm-next-default-source-1"
taskset -c 0 prlimit --as=2147483648 --cpu=30 --core=0 -- timeout 60s python3 -B "$Q/check_static_cohort.py"
```

That command is preadoption-only. After focused independent source/ABI review,
Root checks all four preimages together, checks the new leaf remains absent,
authenticates all five candidate hashes, and adopts only these postimages.
After adoption compare canonical bytes against plan.postimages; do not rerun
the old preimage check. Publish these source bytes and the frozen static profile,
reuse/export/acceptance/validator/reader refs before a fresh admission clock.
Use the five existing tools byte-for-byte from
ROOT-NEXT10-DEFAULT-BUILD-ADMISSION-1: run_build_only.py, build_only_worker.py,
hold_and_run_build_only.py, publish_approved_ready.py, capture_and_bind_resource.py.
The source-only profile is data for those existing APIs; no guard change is needed.

Root chooses a fresh disjoint actual admission/output root, request hash,
current clearance, nonce, resource capture, holder/bootstrap, independent review,
publication and actual grant. Every such value remains NULL here. Preserve the
same holder/direct-wait/canonical-lock/source/export/freshness guards. The old
consumed F42 grant/current-free receipt is provenance and supplies no new release.

After actual four-command completion, with N set by Root to its actual absolute
admission path, run the one prepared read-only gate:

```sh
taskset -c 0 prlimit --as=2147483648 --cpu=60 --core=0 -- timeout 90s python3 -B "$Q/qualify_produced_cohort.py" --admission "$N"
```

Copy check_postbuild_current.py byte-for-byte into N before publication. After
positive actual holder-tool join, save that tool terminal result as
N/ROOT-ACTUAL-HOLDER-TOOL-RESULT.json, then run:

```sh
taskset -c 0 prlimit --as=2147483648 --cpu=60 --core=0 -- timeout 90s python3 -I -B "$N/check_postbuild_current.py"
```

The reader binds actual CID, nonce, actor PID/births and admission path from the
authenticated new metadata; original queries/probes/joins/mounts/floors remain.
No actual observer, compiler, Docker, canonical/Git, clock, nonce or grant ran
in this preparation. Source/API checks and eight reused pure regression tests
pass. Future compiler and blocked-duration timestamps remain unknown.

Real MM/usercopy/fault/concurrency, unresolved direct VMlock192/ABI6 receipt,
final-reference/current-stack, event initialization/list/PMU ownership and
matching native holds remain. HOST evidence and this source preparation do not
close them, accept this default image or retire either whole C file.
