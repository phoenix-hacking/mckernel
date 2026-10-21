# NUMA interval Rust application — source preparation only

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

`numa_interval_app.rs` is one standalone Rust std application, following the
existing `scripts/application-tests/practical_rust_std_app.rs` standalone style
and `practical_process_exec_wait.rs` explicit Linux x86_64 LP64 boundary. The
scoped search in `scripts/application-tests/cases` found no mbind/get_mempolicy
case to reuse. No library, framework, kernel provider or compute C is added.
Nothing was compiled or executed. No acceptance claim is made.

## Source route and witness

The assigned current `kernel/rust/syscall_policy.rs` input identity is
`75b89149aa031076ae547248e0aab64eda5a7b75162952a954489e86067f0b2d`.
Relevant actual bodies are `mbind_body_result`, `get_mempolicy_body_result`,
`get_mempolicy_validate`, and `syscall_vm_range_policy_search_body_result`.
The 160-source preparation's `guest-compiler-commands.json` supplies selected
`MCKERNEL_RUST_SYSCALL_POLICY_HELPERS` and Rust kernel compile inputs; these
are not user-application compilation commands or a linked-image proof.

Linux x86_64 syscall numbers are mmap9, munmap11, mbind237, get_mempolicy239
(NUMA numbers confirmed against `/usr/include/x86_64-linux-gnu/asm/unistd_64.h`).
`arch/x86_64/kernel/include/arch-memory.h` defines PAGE_SHIFT12. Rust uses
`asm!("syscall")` directly, so failures remain raw negative errno values;
libc errno conversion cannot disguise them. rcx/r11 are declared clobbered;
no nomem option permits compiler reordering across pointed-to kernel accesses.

The app maps and fills three 4096-byte pages. It first obtains the actual
exposed allowed-node witness with get_mempolicy(NULL,mask,256,NULL,
MPOL_F_MEMS_ALLOWED=4); this is the current Rust body's VM `numa_mask` path.
It selects the lowest set bit within that returned 256-bit mask. Empty masks
and syscall errors fail. It never assumes node0 exists, a node count, a cpuset,
or a Linux host topology. The returned mask is the source contract's exposed
witness; this does not independently certify topology/physical placement.

The app reads process policy with flags0, then selects MPOL_BIND2 unless the
process mode is already2, when it selects MPOL_PREFERRED1. Both are explicitly
supported by the actual mbind body. The selected mode always differs from the
observed process fallback. mbind sets exactly the middle-page interval with
the witnessed single-node mask, maxnode256 and flags0 (no strict/move privilege
or migration request). On a fresh process this exercises policy search,
allocation/insertion, and interval policy/mask population. A getter that silently
misses the interval and returns the unchanged process default fails the mode check.

Three get_mempolicy calls use MPOL_F_ADDR2 with addresses start, start+2048,
and end-1. Each requires the selected mode and all32 mask bytes, with sentinels
around the4-byte mode and32-byte mask. On a matching selected image the actual
caller acquires the VM range read lock, looks up the valid mapped VM range,
calls the Rust tree traversal through its bridge, snapshots mode/mask while
locked, unlocks, and copies the snapshot. This is a real successful snapshot
consumer. It does not by itself distinguish the old concurrent lifetime defect,
force red-black-tree left/right branches, or prove concurrent node retirement;
the existing actual-body fixture and independent review retain those jobs.

Every mapped byte must still equal `(index*37+11)%251` after mbind and all
getters; all12288 bytes are checked with volatile reads. Exactly one munmap
is attempted after successful mmap, including a failed policy operation.
Its return must be0 before any success line is emitted. No post-unmap access
is performed. Existing kernel/runtime logs and teardown checks remain mandatory.

## Exact application oracle

PASS requires all of the following, conjunctively:

* Exact stdout bytes (one LF, no other bytes):
  `numa allowed=1 interval=1 queries=3 mode=1 mask=1 guards=1 bytes=12288 preserved=1 unmapped=1\n`
* Empty stderr and normal process exit37; raw waitpid status9472 (`37<<8`),
  with no signal/core flag. The output's `mode=1` means equality verified,
  rather than actual policy number1; actual selected policy is1 or2 as above.
* All direct policy syscalls and munmap return exactly0. The mode output is
 4bytes and mask32bytes; every requested mask bit matches the selected witness
  and both adjacent sentinels remain unchanged.
* Matching current source/default linked-image identity, unchanged kernel log
  failure scanner, actual McKernel launch routing and positive normal teardown.
  These remain separately owned prerequisites, absent from this source packet.

Any ordinary detected failure exits1, prints a `FAIL stage=...` diagnostic
on stderr and emits no PASS line. Raw syscall errors include the exact negative
return. Failed policy operations include `unmap_raw=...`, preserving cleanup
failure as well. ENOSYS=-38, EPERM=-1, EACCES=-13, EINVAL=-22 and any unsupported
condition are failures, never skip/PASS. An unexpected panic/abort/signal,
timeout, nonempty stderr, partial stdout or output error also fails. stdout
write/flush failure may leave partial bytes, which the exact oracle rejects.
There are no retry, feature downgrade, synthetic witness or error-as-success paths.

## Minimal command proposal — not executed

Reuse the existing ordinary Rust std application compilation recorded in
`docs/verification/evidence/practical-rust-std-app-preparation-20261017-2.json`
`commands[0]`, with its exact pinned compiler and static application flags.
Propose the equivalent unprivileged CPU6/one-compiler/1GiB-class profile and
a fresh `compile-reference-1/` output directory below this packet. The dispatcher
must admit the profile/output and aggregate overlap before any execution.
`guest-compiler-commands.json`'s kernel no_std flags are not application flags.
Proposed payload command (inside that ordinary profile, with output directory
created by its owning coordinator):

```sh
/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc --edition=2021 -D warnings -C opt-level=1 -C codegen-units=1 -C target-feature=+crt-static -C relocation-model=static -C link-arg=-no-pie -C link-arg=-Wl,-z,noexecstack /home/holden/mckernel-work/host-preparation/numa-native-app-consumer-20261021-1/numa_interval_app.rs -o /home/holden/mckernel-work/host-preparation/numa-native-app-consumer-20261021-1/compile-reference-1/numa_interval_app
```

This uses the existing pinned std compiler with no toolchain download/update.
Capture compiler identity,
exact argv, full stdout/stderr and status. No Cargo dependencies/network needed.
Only one compiler process is needed, with the retained100second compile timeout.
Preserve the current aggregate CPU/RAM budget, no network and no swap. The
CPU6/1GiB-class proposal does not expand the heavy4CPU/12GiB/512task profile;
no new profile, lease or root release is asserted here.

Next, within the existing ordinary Linux application-reference execution profile,
run the built binary once using its owning bounded supervisor, capture stdout,
stderr, raw wait status and timeout state, and compare against the exact oracle
above. A direct payload command is `./numa_interval_app`; it exits37 on success.
Do not wrap it with an exit0-only checker or `|| true`. The supervisor should
allow at most10seconds and positively retire its owned process on timeout.
The existing Docker seccomp/profile or host NUMA configuration may reject either
NUMA syscall: preserve raw errors, report the reference blocked/failed and do
not weaken isolation or count a positive reference. No such result exists yet.

Native execution needs its separately reviewed root/module/guest release and
a newly built, source-bound current NUMA image with unique linked definitions.
The older4-overlay threadnative image is not a NUMA input or NUMA proof.
Retain this same unchanged application/oracle for a later matching guest run.
This packet does not perform that run, grant execution release, retire C, or
claim compilation, Linux reference, current-image/default linkage or native PASS.

Failure-family history: this new application has zero compile/reference/native
attempts and zero corrections. Permit at most one failed candidate plus one
bounded correction in a family before focused escalation; preserve failures.
Service-policy failures remain authoritative and must never be retried/reset.

Stop condition reached: one source application and exact oracle/command proposal.
Only this private directory was written; no tests/build/root/leases/Git/ledger,
shared-source edit, cleanup, resize, network, credentials or child agents used.
