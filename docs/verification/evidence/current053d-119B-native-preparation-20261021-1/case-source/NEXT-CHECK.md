# Separate NUMA nonempty overlap case — source proposal ready

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source-only private preparation. No compiler, test, application, guest, root,
staging, census, workload, lock, cleanup or launcher operation was performed.
No new native evidence or acceptance/retirement credit. The main six-app campaign
and accepted strict116B NUMA case are unchanged. This proposal reuses accepted
kernel image SHA256 `053d59b533665eef9d56fe1b348e699d97159e954fbc1fbff973bbe46113f485`;
it does not request a kernel rebuild.

`numa_nonempty_overlap_app.rs` derives only its syscall ABI, guarded getter and
mmap/unmap/output lifecycle from the accepted source at
`/home/holden/mckernel-work/host-preparation/numa-native-app-consumer-20261021-1/numa_interval_app.rs`.
`numa_nonempty_overlap_app.patch` makes that derivation reviewable as a NEW case;
it is not a request to patch the accepted source. `integration-proposal.json`
uses the existing native diagnostic runner and exact payload contract, with
unbound binary/assets/release fields deliberately null/false. No new framework.

Independent oracle: let P=4096, base be a fresh seven-page mapping, S be the
lowest actually returned allowed-mask set bit (all other 255 bits zero), F the
process policy and N0/N1/N2/N3 the before snapshots at offsets 0,P-1,6P,7P-1.
A is BIND2 unless F.mode=2, when A=PREFERRED1. B is PREFERRED1 if neither F.mode
nor A.mode is1, otherwise INTERLEAVE3. Therefore A, B and process fallback modes
are pairwise distinct. Each interval has mask S; INTERLEAVE uses that same
single observed node without any placement claim. No assumed node0, node count,
physical placement or host/guest topology. A getter silently falling back to F
cannot satisfy either interval oracle. Empty allowed masks or a neighbor already
matching A fail as inadequate witnesses; errors never skip or pass.

The exact expected page policies after each successful bind are independently:

| Operation, offsets from base | Page0 | Page1 | Page2 | Page3 | Page4 | Page5 | Page6 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bind [P,6P) A | N0/N1 | A | A | A | A | A | N2/N3 |
| bind [3P,4P) B | N0/N1 | A | A | B | A | A | N2/N3 |
| bind [2P,5P) B | N0/N1 | A | B | B | B | A | N2/N3 |

Each row queries first and last byte of EVERY page with MPOL_F_ADDR2, preserving
both immediate interval bounds plus both exterior pages. All four exterior
snapshots compare against their own original address, not a shared default.
All nondefault masks compare all32 bytes; DEFAULT masks are absent, following
the supported McKernel getter semantics. Every getter checks both mode and mask
sentinels. Process policy is queried before and after and must be identical.
There are48 policy queries: process2 + exterior-before4 + three rows*14. The
allowed-mask call is an additional getter. Every byte in the28672-byte mapping
must retain `(offset*37+11)%251` after EACH row (three full passes). A successful
mapping has exactly one munmap attempt on success or ordinary policy failure;
success requires return0. No post-unmap access/query is claimed.

Expected application result is exact `expected.stdout`, empty stderr, normal
exit37 (raw normal wait status9472 where the runner actually records wait status).
The one LF-terminated stdout line is:

```text
numa overlap=1 binds=3 queries=48 split=1 reinsert=1 neighbors=4 process=1 guards=1 bytes=28672 preserved=3 unmapped=1
```

Any raw syscall error, changed policy/mask/byte/guard, output error, unexpected
stream bytes, timeout, signal or teardown/kernel-log failure rejects the case.
No migration flags, privilege escalation, retries or unsupported-error PASS.

Source invariant review: the accepted source overlay
`numa-insert-clear-image-successor-preparation-20261021-1/source-overlays/kernel/rust/syscall_policy.rs`
has `syscall_vm_policy_clear_range_body_result` at23265. Its strict-interior
branch truncates the leading A, allocates/copies the trailing A and reinserts
it. Thus bind2 reaches nonempty clear and right-tail reinsertion. Bind3 crosses
both A nodes, trims them, deletes the fully covered former B through the
rb_first/next loop, then mbind inserts the new B. Resulting half-open ranges are
nonempty/disjoint, meeting the helper contract. No algorithm incompatibility
was identified from these bounded source reads. These are expected paths,
not observed native execution or coverage measurements. Noninterleave cursor
and allocation-failure behaviors are outside this success-case oracle.

Next prerequisite (proposal only): independently review this source/oracle,
then admit ONE ordinary compile/reference slot after the current main campaign
needs, using the already qualified pinned Rust1.92 std compiler and static
application flags from the original NUMA app. Proposed source is this directory's
`numa_nonempty_overlap_app.rs`; new output is this directory's future
`compile-reference-1/numa_nonempty_overlap_app`. Exact compiler argv:

```sh
/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc --edition=2021 -D warnings -C opt-level=1 -C codegen-units=1 -C target-feature=+crt-static -C relocation-model=static -C link-arg=-no-pie -C link-arg=-Wl,-z,noexecstack /home/holden/mckernel-work/host-preparation/numa-nonempty-overlap-native-case-preparation-20261021-1/numa_nonempty_overlap_app.rs -o /home/holden/mckernel-work/host-preparation/numa-nonempty-overlap-native-case-preparation-20261021-1/compile-reference-1/numa_nonempty_overlap_app
```

Reuse qualified ordinary CPU6/one-process/1GiB compile profile,100s wall timeout,
no network,16MiB total output reservation,64KiB each compiler/reference stream;
preserve16/12GiB host/scratch floors and aggregate/single-heavy restrictions.
No profile is granted by this note. Preserve exact compiler identity/argv,
streams, status and source/binary binding. Then one bounded Linux reference
(max10s under existing qualified supervisor), exact oracle comparison and
positive process closure. A Linux PASS is not native evidence. Preserve failures
and stop; do not weaken modes, masks or bounds to obtain PASS.

After those prerequisites, use a distinct case ID/assets/manifest/captures via
the existing stage/runner, accepted image053d, current accepted launcher/modules,
and separately reviewed runtime admission/release. Bind the new binary and
oracle into that new case only. Existing strict116B case continues to mean
first-node insertion/empty-tree clear only. No launch or source integration is
performed by this proposal. Stop condition: reviewable source/oracle and bounded
compile/reference prerequisite ready; no action is needed to delay six-app work.
