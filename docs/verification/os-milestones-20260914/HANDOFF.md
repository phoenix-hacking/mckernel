# Compact dispatcher handoff

## Latest continuation: checkpoint 153

Checkpoint 153 supersedes the retirement release state. Fetched v1 release
`342de408...18f5` passed mechanical, complete live content, Docker and immutable
capability review but was BLOCKed before execution: its post-canonical-scan
SC_AVPHYS value was 3.23 GiB although Linux MemAvailable remained 19.83 GiB.
Read-only reproduction confirmed the canonical pack-cache ordering defect. V1
remains immutable and unexecuted; no tombstone or quarantine exists.

Additive v2 DRAFT `84015a3f...43e3b` and tests `de7a3448...7ac1` use a strict
Linux MemAvailable parser with the unchanged 4-GiB floor. After preserving the
aligned-format failure and correcting an independent review BLOCK on the shared
lease, v2 retains exact build exclusion `native-exact-build-lease-704f6654-1.json`
and uses fresh v2 quarantine/evidence names. Python 3.8/3.9 each pass 110 tests;
independent rereview PASSes source only. The release sentinel remains.

Next push/fetch the v2 template, mechanically finalize its two-path release,
then obtain a fresh execution review and full live preflight before any one-shot
retirement. Only accepted retirement unlocks a fresh build candidate. Counts
remain unchanged and the OS is incomplete.

Checkpoint 151 supersedes the storage-bridge status. Retention preparation now
PASSes independent evidence review: inventory `4067c653...61b8e1`, capsule
`b6c85e40...ecec1`, success record `be700dd5...eed4d`, 10,609 live entries,
924 capsule members, 49 links and 9,024 canonical objects. All workers retired;
candidate/backup remain 26/36767 and 26/47413; claims/leases are absent.

The first bound retirement DRAFT was independently BLOCKed on stale Docker IDs
and unenforced failure artifacts. Corrected DRAFT `51d7c6d0...ee215`, additive
helper `46311908...c517` and their tests pass 121 cases under Python 3.8/3.9;
independent rereview PASSes source only. The exact four 704f terminal candidate
users and preserved build-failure artifacts are now enforced. The release
sentinel remains, so no retirement is authorized.

Next fetched-verify this template checkpoint, mechanically create the two-path
retirement release, obtain separate execution review and complete all fresh
privileged preflight gates. Only after accepted retirement may tmpfs capacity be
used for a wholly fresh commit-derived build candidate. Counts remain unchanged.
The launcher shutdown leaves every child terminal and no heavy operation active;
preserve wrapper/worker/server identities 3399308/83682487,
3399313/83682494 and 3399317/83682500. The release sentinel remains authoritative,
the OS is incomplete, and a later launcher invocation may continue from this
temporary pause.

Checkpoint 150 adds the required storage bridge. Fresh candidate preparation
needs retirement of consumed `704f6654-1`, but retirement cannot precede an
exact inventory/restoration capsule. Non-destructive preparation DRAFT
`3c684c86...e8b86` and tests `a5496af2...c59c4` pass independent design review
and 46 combined tests on Python 3.8/3.9; it remains unreleased. Future retirement
DRAFT `3fd47e37...1bb37` passes 79 tests but remains blocked by explicit
inventory/capsule/success/release sentinels.

Next fetch-verify the DRAFT template commit, generate an acyclic release changing
only the retention-preparation packet sentinel plus its new release JSON, then
obtain separate mechanical/execution review and complete preflight. The first
run is ordinary-user, read-only over candidate/backup, and writes only fresh
inventory/archive/scratch evidence. Independently accept those outputs before
any privileged retirement release. No build, runtime or counter advances.

The `704f6654-1` heavy request is consumed and must never be rerun. Its phase-0
queue-fixture failure is now exactly reproduced: `/tmp` is `noexec`, while an
evidence-style bind mount compiles and executes the unchanged seven-test fixture.
Checker `84634d62...a46c` and tests `83032bf2...41c8` implement and independently
PASS one bounded correction using the offline driver's existing executable
`RUNNER_TEMP=/evidence/build`; production Rust and the oracle are unchanged.
Corrected light container `d778b8fa...bc44` exits 0 under exact Rust 1.92.
Evidence is `stability-native-queue-fixture-exec-location-success-20260929-1.json`
and archive SHA256 `9002fe60...3d6c`. No build, guest or formal counter advances.

Next checkpoint and verify these exact bytes, then derive a wholly fresh
candidate and request from that fetched commit using new names for candidate,
backup, manifest, request, output, evidence and lease. The old preparation
packet is a template only; its execution/review authorities are consumed.
Require fresh preparation review/evidence review and then a separate one-shot
heavy-build release. Preserve candidate/backup 26/36767 and 26/47413, failed
container `68881c05...927a6`, all three light probe containers, and launcher
identities 3399308/83682487, 3399313/83682494 and 3399317/83682500.

The active policy hashes loaded for this continuation are GOAL `76c4f5d1...c0bcc3`,
START `1698d342...6216c`, CONVERGENCE `f6938bd2...3e86a`, and the live pre-update
HANDOFF `2b3031ad...43a`; the latter contains later checkpoints than the
launcher's stored predecessor hash. The whole-OS objective remains incomplete.

Reconciled 2026-09-28 during the active aggressive launcher invocation. The
whole-OS goal remains active and incomplete. A checkpoint, stable-core row or
diagnostic application is never whole-OS completion.

## Authority and identity

- Branch: `codex/local-native-staging-repair`.
- Last verified remote checkpoint before this shutdown save:
  `ecbd002de15330a5c78244f1144322781021da09`.
- Adopted policy SHA-256: GOAL `76c4f5d1...c0bcc3`, START
  `1698d342...6216c`, CONVERGENCE `f6938bd2...3e86a`, HANDOFF predecessor
  `265cd999...a415`.
- Launcher wrapper PID/PGID/SID 3399308/starttime 83682487; worker
  3399313/starttime 83682494; app-server 3399317/starttime 83682500.
- No QEMU, mcexec, diagnostic owner or heavy build/guest lease is live. The
  failed build owner PID 3488858/starttime 84850867 has exited and its lease is
  absent. Preserve its exited container and evidence. Recheck exact identities
  and capacity before heavy work.
- Preserve unrelated dirty launcher/policy files, deleted/untracked pycache and
  dirty nested `ihk`; stage only campaign-owned paths.

Official counters remain 0/273 accepted applications, 2/4 narrow fault modes,
6/130 production gates, 350/10,000 points and 0/7 language gates. Four real
diagnostic guest applications (memory/files/threads/signals) have run; zero
current-candidate builds exist. Required hardware/exposure remains unavailable
locally and does not prevent independent implementation work.

## Current source closure and active M05 lifecycle family

The exact current native Rust host source closure is independently PASS for
source/Layer-B only. The corrected integrated command passes 196 tests and the
exact-build/workflow subset passes 48 tests. It binds current smp_memory and
os_runtime escape surfaces, SMP v4, the mcctrl service boundary, literal escape
ordering and the complete `LoadedImage` owner lifecycle. Preserve the original
failures and exact inventory in
`stability-native-current-source-closure-success-20260928-1.json`; the corrected
independent decision is
`stability-native-current-source-closure-independent-review-20260928-1.json`.
Four build-output blockers remain. No configured build or runtime result follows
from this source decision.

The allocation-free registry shutdown transaction is source-reviewed and passes
15 exact Rust tests. The additive v5 host shutdown/admission boundary now also
passes exact Rust 1.92 production-body fixture execution: 62 tests, source SHA
`5b79ca8c...7144`, fixture `3c380a76...579b0`, driver
`ad592a7d...57d5`. Independent review returns PASS for this bounded scope.

Verified host behavior: shutdown closes admission before its registry/provider
transaction; live ApplicationConnection and FileService owners return EBUSY
without invoking shutdown; their provider Close runs before admission/lease
release; pre-effect errors roll back; successful shutdown retains the closed
gate; successful boot reopens after Ready. Forced connection allocation failure
calls Close exactly once, and Close reenters production `topology_query` with
result 73, proving the operation mutex is no longer held.

Evidence:

- `stability-native-shutdown-registry-source-success-20260928-1.json`
- `stability-native-shutdown-admission-source-success-20260928-1.json`
- `stability-native-shutdown-observer-source-success-20260928-1.json`
- `stability-native-shutdown-stop-ack-design-review-20260928-1.json`
- `stability-native-shutdown-x86-reclaim-design-review-20260928-1.json`
- `stability-native-shutdown-x86-reset-export-source-success-20260928-1.json`
- `stability-native-shutdown-irq-drain-design-review-20260928-1.json`

This is source/Layer-B evidence only. The v5 callback is not wired to SMP and no
production module, root command, container or shutdown guest has run. V5 nonzero
results must remain pre-effect; partial teardown cannot be rolled back.

## Exact stop/ACK blocker and next implementation

The guest master queue is CPU0-only and cannot prove every assigned CPU stopped.
Per-CPU regular 128-byte channels are the only existing delivery route, but an
ACK cannot yet authorize release:

1. A stopped CPU still executes guest code/stack/page tables; implement an
   independently retained parking transition and subsequent CPU reclamation.
2. STOP must defer until packet release and interrupted-context rundown; it
   cannot park inside the current packet handler.
3. Guest-allocated Linux IRQ-work can remain queued or executing after ACK,
   including publication followed by failed IPI. Add exact per-generation work
   inventory, started `BootIrqRoute` unpublish and callback drain.
4. Establish immutable boot-session identity and STOP capability before service
   admission. Only then reserve/freeze a versioned wire encoding.

Required order is Running → AdmissionClosed → Draining → StopPublished per CPU
→ SenderQuiesced per CPU → HostCallbacksDrained → CPUReclaimed → Released.
Timeout or malformed/stale/missing ACK retains every CPU, RAM, mapping, queue,
module pin and ledger owner. Never substitute `nmi_mode`, `arch_cpu_stop`, CPU0
master activity, guest poweroff or QEMU exit.

Independent x86 review accepts one narrower CPU-reclamation design for an
explicitly supported native AP profile: retain every owner, issue the existing
Linux INIT assert/deassert sequence to each validated offline assigned AP, then
require successful synchronous Linux `device_online` and revalidate its exact
device/APIC identity plus `cpu_online`. INIT is only a reset attempt; Linux
re-online is the reclamation proof. No SIPI belongs in the reset helper, and any
failed or uncertain reset/online retains all owners in a per-CPU journal. This
does not solve the separate IRQ-work/callback drain.

The minimal Linux `send_init_sequence(apicid)` export now applies to the exact
retained pinned source and passes its one-test body-preservation contract after
one retained malformed-hunk failure and one bounded correction. It remains
source-only and unbuilt. Exact pinned Linux source also confirms that
`irq_work_sync` is GPL-exported. The reviewed drain boundary uses a private
generation/state/sender-count registry: stop new sender leases, wait for every
publisher, synchronize every retained per-CPU work node, then unpublish the
route and permit generation reuse. Never remove nodes from `raised_list`.

The distinct reset/re-online journal and the replacement preemption-protected
Linux wrapper now exist as source-only WIP. The journal passes six exact Rust
1.92 fixture tests after the first independent review's findings were repaired;
the wrapper passes its pinned-source test after three retained candidate
failures. An exact-build supplement for patches 0006 through 0010-v2 passes its
two-test suite after one retained final-writer verification failure. None has a
configured build, module link/load, privileged execution or final independent
review. See the two `stability-native-shutdown-reset-*-wip-20260928-1.json`
records.

The canonical remote workflow dispatch is independently BLOCKED as an execution
release. It pins the Rocky digest, `-j2` and 330-minute timeout, but does not
enforce/read back CPUs 2-5, 12 GiB/no swap, 512 tasks or no-network; its package
and source acquisition require network; and success automatically starts two
downstream jobs. It also lacks an exact exclusive owner, disk-floor admission
and retirement receipt. No workflow was dispatched.

Next executable step: implement and test a two-boundary owner. Authenticated
preparation must produce immutable tool/image and source-asset identities; the
single offline build container must enforce/read back the frozen limits, hold an
exclusive heavy lease, preserve partial evidence and retire before release. Seek
fresh independent review before execution. After a successful configured build,
bind its exact kernel/modules to the smallest real McKernel startup application.
Separately continue failed-IRQ_WORK_VECTOR retry/offline quarantine, callback
drain, STOP/v5 integration and CPU reclamation. Do not freeze STOP/ACK or run the
shutdown fixture before CPU reclamation and callback drain pass review.

The two-boundary source implementation now passes 32 focused tests after expert
escalation. It reuses the workflow's exact source/stage/configure/compile and
post-provenance validator bodies; preparation is source-free, and runtime is one
offline cap-drop-all container with effective-profile readback and terminal
lease discipline. Evidence is
`stability-native-exact-build-boundary-source-success-20260928-1.json`. This is
not an execution release. Next create and bind the clean checkout/full manifest,
then seek independent review for the separate networked image-preparation phase.

The first preparation review BLOCKED buffered `docker exec` failure evidence.
The bounded correction streams every command to retained files and handles
TERM/INT through bounded retirement/receipt; SIGKILL tests preserve already
emitted bytes. All 43 focused tests pass with a retained raw log, and independent
rereview released only the exact d094 source-free preparation.

That exact preparation now PASSes. Image
`sha256:0f8ad280e47d76b23554de4aec411752e1f779f9b2fc7fece6b0b3375dc9775d`
is locally retained; its receipt SHA is `18225919...8172`. All 59 bound files
and 18 command statuses verify, the container is absent, and the lease is gone.
The candidate is clean after three hardlinks were broken/restored and its full
8,899-file manifest reverified. Evidence is
`stability-native-exact-image-preparation-success-20260928-1.json` plus archive
`evidence/stability-native-exact-image-preparation-d0947e0c-20260928-1.tar.gz`.
No configured build has run.

The immediate build blocker is privilege separation: uid 1000 cannot access the
Docker socket, but the owner must not run as root. Independent review BLOCKs a
prefix-only sudo patch because elevated Docker client retirement would be
unproven. The expert correction now elevates only the immutable Docker client,
uses catchable TERM before forced retirement, classifies negative sudo-wrapper
completion on every path, retains the lease on sticky client uncertainty,
filters SUDO_ASKPASS without logging it and pins the Unix socket. The original
three-test/seven-failure reproducer is retained and 39 corrected tests pass.
Final independent rereview PASSed the source boundary and conditionally released
one exact offline build after its bytes and request passed preflight. That single
attempt failed in the offline driver's identity phase before compilation: the
bind-mounted candidate is a linked worktree whose `.git` points to unmounted
host metadata. It ran zero build commands, produced no artifacts, and exited 1.
The original evidence is committed in
`stability-native-exact-build-identity-failure-20260928-1.json` and
`evidence/stability-native-exact-build-identity-failure-d0947e0c-20260928-1.tar.gz`.
Retain exited container `mckernel-exact-272a777b73aa4a5185f607bfa8fad490`
(ID `110dfe01...799b0`) and do not retry the released request.

Expert escalation and independent review now PASS the bounded source correction.
The helper retains current identity/index, the exact historical root commit,
seven necessary trees, four locked ABI blobs and complete pinned IHK history;
52 tests pass with original stores hidden. Review caught and withdrew a
cross-filesystem scratch backup before execution. After checkpointing the exact
helper/test bytes, execute the released conversion once using the same-device
backup `/home/holden/mckernel-exact-metadata-backup-d0947e0c-1` and evidence
`/home/holden/mckernel-exact-metadata-evidence-d0947e0c-1`. Verify every Git
consumer, full manifest, owner admission and clean identities before seeking a
fresh attempt-2 one-shot release. No successful current-candidate build or
acceptance counter follows from source review or conversion.

Keep original failures in CURRENT.md/evidence. At the next coherent checkpoint
update touched stable-core rows, run `scripts/update_progress_tracker.py`, commit,
push and verify fetched blobs. One heavy build/guest maximum; aggregate seven
jobs/24 GiB, pinned container at CPUs 2-5/12 GiB/no swap/512 tasks/no network.

Shutdown checkpoint 65 supersedes the preceding next step. The standalone Git
metadata conversion PASSed and is preserved, but independent review BLOCKed the
d094 build on three deterministic stale source-contract families. Lifecycle and
mapping corrections now pass independent source review and exact Rust 1.92
diagnostics (78 scoped tests, one intentional skip); the corrected container is
retired and no build/guest ran. The d094 candidate is quarantined because six
later edits propagated through shared hardlinks. See
`stability-native-exact-metadata-conversion-success-20260928-1.json`,
`stability-native-lifecycle-mapping-contract-checkpoint-20260928-1.json` and
CURRENT checkpoint 65.

On the next authorized continuation, create a fresh non-hardlinked candidate
from the fetched checkpoint, bind a new full manifest, install standalone Git
metadata under fresh backup/evidence roots and run the complete offline source
phase in the pinned image. Obtain independent one-shot execution review before
any heavy build. Preserve launcher wrapper PID 3399308/starttime 83682487,
worker PID 3399313/starttime 83682494 and app-server PID 3399317/starttime
83682500 as the shutdown identities. Formal counters and diagnostic-app/build
counts remain unchanged; this is a temporary launcher pause, not OS completion.

Checkpoint 66 resumes the campaign and supersedes the host-filesystem candidate
step. A full non-hardlinked host clone breached the 16-GiB floor and was stopped
and removed; reflinks are unsupported. The repository now has an independently
PASSed canonical manifest producer/consumer and corrected owner resource
admission. Eighty consolidated source tests pass, including retained symlink,
assume-unchanged, mode, forged-manifest, CR/CRLF path, publication-race,
allocation-walk and 24-GiB aggregate negatives. See
`stability-native-exact-manifest-owner-source-success-20260928-1.json`.

Next, after fetched verification, seek a command-level release for a fresh
non-hardlinked candidate in `/dev/shm`, standalone metadata conversion, exact
manifest generation and complete offline source phase. Recheck candidate plus
12-GiB container against the aggregate 24-GiB limit, MemAvailable >=16 GiB and
the unchanged host/scratch floors. No build/guest is released yet. Preserve the
old d094 roots/container and all failed provenance/resource candidates. Counts
remain 0/273, 2/4, 6/130, 350/10,000, 0/7, four diagnostic apps and zero
successful current-candidate builds.

Shutdown checkpoint 67 supersedes that next action until a later launcher
continuation. The exact owner now admits all declared preparation-owned memory
roots and sums their tmpfs allocations with the pinned 12-GiB container before
lease/Docker; 48 focused tests pass. Independent review of owner SHA-256
`32e0c28d...e0d5f` and test SHA-256 `d4db50d2...8c3a9` is still required.
The command packet also still needs durable scratch evidence/logs and an
explicit staging/emergency headroom bound. See
`stability-native-exact-owner-allocation-roots-wip-20260928-1.json` and CURRENT
checkpoint 67. No preparation/build/guest ran; preserve the exited failed
container and launcher PIDs/starttimes. Counts remain unchanged, and this is a
temporary launcher pause rather than OS completion.

Checkpoint 68 resumes and closes the owner-allocation source block. Exact owner
`9cb8565e...65ea2` and tests `6bdf439f...0797f` pass independent review after
raw-byte mount parsing, root/mount identity binding, memory-backed filesystem
accounting and aggregate-wide revalidation. See
`stability-native-exact-owner-allocation-final-source-success-20260928-1.json`.

After fetched verification, prepare one fresh commit-derived candidate and
same-device backup on `/dev/shm`; keep evidence/logs/manifest on durable scratch
and maintain at least 4 GiB staging/emergency headroom. Require exact clean
main/IHK identity, distinct tmpfs inodes, conversion PASS, installed-only Git
consumers, canonical manifest plus separate verification, and
`BuildOwner.validate()` with candidate and backup roots. This releases no
Docker build or guest; those still require separate review.

Checkpoint 69 prepared exact candidate `80b8c492...b7d0a` successfully on
`/dev/shm`. Standalone metadata, installed-only Git consumers, the canonical
manifest and independent `verify_inputs` all PASS. Validate-only accounting is
21,951,848,448/25,769,803,776 bytes with 7,530,528,768 bytes still free on
tmpfs; no lease or Docker ran. See
`stability-native-exact-candidate-preparation-success-20260928-1.json`.

Preserve candidate `/dev/shm/mckernel-exact-candidate-80b8c492-1`, backup,
durable metadata evidence/manifest/request/log and the old d094 roots/container.
Command provenance review corrected the prior routing: the offline driver's five
phases already include the heavy kernel/module compile and artifact validation;
there is no separately released Docker source phase. Next obtain an independent
one-shot heavy-build release for the exact request/image receipt.

Shutdown checkpoint 70 supersedes that next action until a later launcher
continuation. The released request ran exactly once and failed in source-only
phase 0 before compilation because the stage manifest did not name exactly the
build authorities and locked supplemental inputs. Preserve exact record
`stability-native-exact-build-phase0-failure-20260928-1.json`, archive
`evidence/stability-native-exact-build-phase0-failure-80b8c492-20260928-1.tar.gz`,
candidate `/dev/shm/mckernel-exact-candidate-80b8c492-1`, its metadata backup,
and both terminal failed containers. The latest container is
`c6917efd...f9f0772` / `mckernel-exact-917e1468d2664989aa026baf667b2b7b`,
exit 1, PID 0, non-OOM. Its owner and Docker wait processes retired, its lease
is absent, and its output root is empty.

Next: reproduce the exact stage-manifest expected/observed set locally without
Docker; make only one bounded correction for this failure family; run focused
regressions and independent review. Then checkpoint and prepare wholly fresh
candidate/manifest/request/output/evidence/lease names before seeking another
one-shot release. Never rerun the unchanged 80b request. Launcher wrapper PID
3399308/starttime 83682487 and worker PID 3399313/starttime 83682494 are the
active shutdown identities. No child agent or heavy operation remains. This is
a temporary pause, not OS completion; formal counters and the four diagnostic
apps/zero successful current-candidate builds are unchanged.

Checkpoint 71 closes only the exact 18-versus-21 audit mismatch. Exact source
hashes `bddd9a10...be9dc` and `1a2726e9...d537e` pass 22 tests, the direct audit
and independent review; see
`stability-native-build-surface-audit-correction-20260928-1.json`.

Before any fresh candidate, fix the separately proven recursive source closure:
the three crate roots require 31 unconditional inputs not copied by the current
manifest/stager (29 Rust and two included assembly files). Add a hash-bound
closure oracle, then update the exact manifest/staging inventory with focused
negative tests and independent review. Never rerun the old 80b request. Preserve
its candidate/evidence and both terminal containers. Counts remain unchanged.

Checkpoint 72 closes the tmpfs candidate permission-admission defect. The 80b
checkout's `0600/0700` modes are now rejected by the generator, offline verifier
and unconditional pre-lease owner check; 98 tests and independent real-Git
probes PASS under umask `0077`. See
`stability-native-exact-candidate-mode-admission-20260928-1.json`. Preserve the
old candidate unchanged. Future preparation must use umask `0022` or exact
index-mode normalization and then pass both admission layers. Continue the
separate 57-file staging closure and unsafe-ledger repair before a fresh build.

Shutdown checkpoint 73 preserves the completed bounded parser correction as
WIP. The 57-file recursive stage closure passes the four exact reviewer
regressions and direct source checks, but the post-correction full 114-test run
and independent rereview are still required. The unsafe-ledger parser's seven
focused tests pass, but real missing safety documentation begins at
`host-kernel/native-rust/os_runtime.rs:648` and the durable ledger has not been
reconciled. See
`stability-native-recursive-stage-and-unsafe-ledger-shutdown-wip-20260928-1.json`.

Next run the full recursive suite and independent rereview, then close that
family only if both pass. Follow with one expert-reviewed safety-documentation
and full-ledger reconciliation pass, including affected manifest/stager hashes.
Do not prepare a candidate until phase 0 is source-clean; never reuse the failed
80b request. No heavy operation remains active. Preserve launcher wrapper PID
3399308/starttime 83682487 and worker PID 3399313/starttime 83682494 as the
shutdown identities. Counts remain unchanged and the OS goal is not complete.

Checkpoint 74 adds the missing small retention capsule for failed candidate 80b:
installed main/IHK Git metadata, both backups, two unique bytecode files and the
exact manifest/request/receipt/observers. The 4,363,203-byte archive and its
924-entry inventory pass member-by-member verification; see
`stability-native-exact-failed-candidate-retention-capsule-20260928-1.json`.
The candidate and backup remain untouched. After fetched verification, obtain
independent deletion rereview; retain both terminal containers. This changes no
runtime or acceptance count.

Checkpoint 75 supersedes that cleanup hold. After a corrected privileged
device/inode and filesystem-root observer passed independent rereview, only the
two exact failed-80b tmpfs roots were removed. Both are absent and
9,066,999,808 bytes were recovered; tmpfs now has 16,597,475,328 bytes free.
The fetched capsule/inventory and both terminal containers remain preserved.
See `stability-native-exact-failed-candidate-cleanup-20260928-1.json`. Do not
prepare a fresh candidate until the active recursive-stage and unsafe-ledger
source closure is independently accepted and fetched.

Shutdown checkpoint 76 preserves the joined source lanes as WIP. The unsafe/FFI
ledger now binds 55 inputs and 637 sites, preserves 156 historical mappings and
adds 481 pending IDs; its 22 focused tests and direct inventory/check pass.
Twenty-two Rust files have comment-only safety documentation. See
`stability-native-source-closure-shutdown-wip-20260928-1.json` for exact hashes,
checks and limitations.

The final integrated staging gate still fails closed on one stale v5 exact
escape-prefix expectation in `native_rust_host_audit.py`; do not treat the
earlier 114-test pass as final because it predates the manifest reseal. Next make
one bounded expectation correction without weakening the audit, rerun the full
recursive and ledger suites plus direct staging/inventory checks, and obtain
independent review. Only then checkpoint and prepare a fresh correctly-moded
candidate. No heavy operation is active. Preserve launcher wrapper PID
3399308/starttime 83682487 and worker PID 3399313/starttime 83682494. The OS
goal remains incomplete and the launcher pause is temporary.

Checkpoint 77 closes the phase-0 recursive staging/unsafe-ledger source family
on exact reviewed bytes. The fail-fast matrix passes 196 tests and all 16 direct
checks; the ledger binds 55 inputs/637 sites and all 22 Rust documentation edits
are non-comment-token-equivalent to base `1129961b...61f`. See
`stability-native-rust-source-closure-checkpoint-20260928-1.json` and archive
`evidence/stability-native-rust-source-closure-20260928-1.tar.gz`.

This grants source preparation only: Rocky retains four readiness blockers,
RS-011 remains NOT_READY and no build/runtime credit moves. After fetched
verification, obtain an independent command-level release for one fresh
SHA-derived candidate, explicitly using `umask 0022`, exact Git mode admission,
fresh candidate/backup/evidence/manifest/request/output/lease paths, and the
existing resource floors. Never reuse failed-80b names. Candidate preparation
does not release Docker execution; any heavy build still needs separate review.

Shutdown checkpoint 78 preserves, but does not release, the replacement
preparation-only one-shot packet for commit `68cf089a`. It passes shell syntax
only and has not been independently reviewed or executed. The rejected generic
wrapper remains archived as historical BLOCK evidence; its source files remain
removed. See
`stability-native-exact-candidate-preparation-shutdown-wip-20260928-1.json`.

On continuation, review the exact one-shot packet first, correct at most one
concrete defect, and obtain explicit release for any privileged Docker
observation. Then capture process/lease/container/resource preflight. Only a
review PASS plus clean preflight permits preparation; build execution remains a
separate later release. Preserve launcher wrapper 3399308/83682487, worker
3399313/83682494 and app server 3399317/83682500 as the shutdown identities.
The OS is incomplete; acceptance counters did not move.

Checkpoint 79 accepts preparation only for exact candidate `68cf089a-1` and
pinned IHK `3114d9e7`. The independently reviewed packet
`15f40733...7461` returns inner/outer RC 0, stable source closures, clean Git,
metadata/ABI/manifest/owner validation PASS, empty build/evidence roots, absent
lease and complete postflight. See
`stability-native-exact-candidate-preparation-checkpoint-20260929-1.json` and
archive `evidence/stability-native-exact-candidate-preparation-68cf089a-20260929-1.tar.gz`.

Do not build or mutate this candidate. Heavy-build review is BLOCKed because
`BuildOwner.run` can remove a provisionally successful container before late
allocation, interruption, inventory and durable-receipt checks convert it to
FAIL. Next retain the terminal container through final reconciliation, add
cleanup-time TERM and late-allocation-revalidation regressions, independently
review, commit and prepare a new SHA-bound candidate. Preparation earns no
build, guest or formal acceptance credit; counts remain unchanged.

Checkpoint 80 repairs the heavy-owner evidence blocker at source level. Exact
owner `a8c4c9fc...9155` never removes a terminal container; its tri-state receipt
distinguishes no attempt, unresolved retention, verified owned terminal retention
and a historical snapshot invalidated by client uncertainty. Exact tests
`c96d25c0...0857` pass 65 focused and 118 integrated compatible cases with
independent source review PASS. See
`stability-native-exact-owner-terminal-retention-source-success-20260929-1.json`.

No build is released yet. Preserve candidate `68cf089a-1` unchanged. Its 9.07-GiB
tmpfs allocation must be independently observed and cleaned before a replacement
commit-derived candidate can preserve the 4-GiB reserve. Then rebind the new
owner/test hashes, prepare a new candidate/request and obtain fresh heavy-build
review. The Python-3.9 workflow import failure is retained; do not weaken it.

Checkpoint 81 pushes the pre-cleanup retention capsule for prepared candidate
`68cf089a-1`: 920 installed-Git/backup/manifest/request members, SHA-256
`eed1879b...80c6`. See
`stability-native-exact-prepared-candidate-retention-20260929-1.json`. Both
tmpfs roots remain live. Delete only after fetched verification, root-complete
zero-reference observation, clean lease/container preflight and independent
review of the exact two-root deletion packet. No other path is in cleanup scope.

Checkpoint 83 supersedes the initial cleanup design. Exact observer
`4a15271d...8e05` and inventory-pinned/release-unset deleter
`3803cf64...1eb0` now PASS independent source review after three rejected
designs. The 10,549-row observational inventory is `743c0564...82c0`; committed
archive `evidence/stability-native-exact-complete-inventory-68cf089a-20260929-1.tar.gz`
is `6be734da...b044`. Both live roots remain untouched.

Next build one exact packet that creates a fresh v2 preflight from source-clean,
boot/time, root-identity and root Docker no-bind observations, mechanically pins
the independently reviewed release record, and invokes the root helper once.
Obtain Astra execution review before any sudo or mutation. Any failure retains
the cleanup lease, journal, captures and quarantines without retry. Success only
reclaims tmpfs for a new commit-derived candidate; it moves no acceptance count.

Shutdown checkpoint 84 preserves the first execution-packet draft without
release or execution. Packet `39fbd9c2...be46` and basis `d50f9840...b844`
parse, but deliberately stop before mutation and still contain unset pins plus
the fixed-input-loop, capacity, Git-admission and circular-hash defects listed
in `CURRENT.md`. All child lanes are complete; the three launcher process
identities and both original tmpfs roots remain live and unchanged. Next repair
and independently review the draft, then mechanically pin and review the exact
final helper/packet before any one-shot root run. Do not treat this checkpoint
as cleanup authority, retry authority, build acceptance or OS completion.

Checkpoint 85 supersedes that defective draft: helper `0324772c...9c80`, packet
`c9303cfb...562c` and acyclic DRAFT basis `a6983f74...f593a` PASS independent
source-template review and ten pure regressions. They remain non-executable by
construction. Commit/push/fetch these exact templates, set only the reviewed
source/status/helper/release pins, then seek independent final execution review
before any sudo or mutation. The original roots and all retained evidence stay
protected; success would reclaim space only and changes no acceptance count.

Checkpoint 86 has final independent one-shot release after remote verification:
helper `5500e77e...c753`, packet `d3d4c064...5729`, basis
`704c8409...7323`, tests `aebc02ec...d9f7`. Commit/push/fetch these exact bytes,
then invoke the packet once as non-root from the repository root. Preserve every
failure artifact and never retry or run the helper directly. This authorizes
cleanup only, not a build, guest, application or acceptance promotion.

Checkpoint 87 records the single attempt as FAIL before deletion. Both roots
are now sealed root:root 0700 under the exact quarantine names; originals are
absent and the root lease/journal remain. Five observer rounds produced the
same false blockers: 815 stable-task `map_files` absences and 48 namespaces with
no host-canonical `/dev/shm`, with zero permission denials. Preserve all paths
and hashes in `stability-native-exact-cleanup-failure-20260929-1.json`. Do not
rerun or roll back. Fix/test the observer locally, then obtain independent
review of a new exact quarantine-resume packet bound to the retained failure.

Shutdown checkpoint 88 stops before recovery. All child lanes are joined; the
launcher PIDs 3399308/3399313/3399317 remain live. Preserve both root:root 0700
quarantines, the old lease `69ced239...47e3`, journal `6bf12958...ebe`, and the
raw failure archive. Corrected observer `e6f46761...e4d` has independent source
review PASS, but recovery helper `ad0db6b...f3b`, packet `c59ed2d4...1473` and
basis `fec0e99d...9a6` remain DRAFT/non-executable. Their local regression run
has three fixture failures while self-test, compilation, syntax, JSON and diff
checks pass. Next fix only those pure regressions, obtain independent source
review, checkpoint the templates, mechanically finalize them, and seek a
separate execution release. Never rerun or roll back the failed cleanup.

Checkpoint 89 repairs and independently source-reviews the recovery template.
Helper `d55fedef...188e`, packet `0298aea1...728`, DRAFT basis
`f26ee96c...6bd` and ten-test suite `84f8982d...318` PASS; the release sentinels
still make execution impossible. Commit/push/fetch these exact bytes, then make
only the four authorized final substitutions and seek a separate exact
mechanical-diff/execution review. Both quarantines and old lease remain protected;
no cleanup, build, guest, app or acceptance result follows from this source PASS.

Checkpoint 90 conditionally releases one exact non-root recovery packet after a
final commit/push/fetched-blob match and fresh live preflight. Final helper
`dcb72838...9735`, packet `ab2283d6...abac`, basis `bef067a4...7983` and tests
`aef2cce5...cb08` pass independent mechanical/execution review. Invoke only the
packet once; direct helper execution, retry, rollback and output reuse are
prohibited. Any failure retains the claim/evidence and may leave partial deletion.

Checkpoint 91 records that single attempt as FAIL before deletion. Both
quarantines and the old lease are unchanged; originals are absent; the new claim
and journal are permanent. Five rounds found zero references/denials, but root
PID 2545 thread churn prevented two consecutive identical global task sets.
Preserve failure record/archive `0a3e13ec...78b5`; never retry or roll back either
packet. This is the family's second execution failure, so expert strategy change
must implement a bounded final-live-identity closure scan and a new recovery
identity bound to both failures before independent review and any further run.

Checkpoint 92 independently accepts v2 observer `71fc9f54...3bfa` and 16-test
suite `09206112...5a19` as a source dependency only. It performs bounded closure
over exact identities in returned censuses, safely reconciles exits, persists
reference hits and revalidates exact tree membership. It explicitly does not
claim atomic census; a new DRAFT packet must enforce the sealed-0700/no privileged
or adversarial mutation assumption and bind both retained failures/claims. No
live execution or deletion is authorized, and neither old packet may be retried.

Shutdown checkpoint 93 records a clean scheduling stop at pushed HEAD
`4add99009253bf8341cfacdec9dc077a3a52bf7e`. The recovery-v2 expert was
interrupted before producing any workspace file; all other child lanes were
already complete. No privileged or runtime operation followed the stop request.
Preserve launcher wrapper/worker/app-server identities 3399308/3399313/3399317
with starttimes 83682487/83682494/83682500, both sealed quarantines, the old
lease, both failures and both permanent recovery claims/journals. On the next
authorized continuation, create a new DRAFT recovery-v2 identity bound to all
of that retained state and observer v2, then obtain independent source review;
do not retry either old packet or begin a build. The OS remains incomplete.

Checkpoint 94 supersedes the missing recovery-v2 draft. After an initial BLOCK,
a failed bounded correction and the required larger strategy change, exact
non-executable template helper `fb229489...f8d8c`, packet `5bafd304...6d1d7`,
basis `f2a19915...11ff` and 26-test suite `5d25dc07...6b195` independently PASS
source review. They bind both failures/claims/journals, the old lease, sealed
roots, inventory and observer v2 with an acyclic finalization chain. No live
operation is authorized. Commit/push/fetch the template, mechanically finalize
only reviewed pins/status, then obtain a separate exact execution review and a
second fetched checkpoint before any new one-shot packet. Preserve the explicit
non-atomic operational exclusion through observation and deletion; never retry
either old packet or start a build while the lease remains.

Checkpoint 95 conditionally releases one exact recovery-v2 cleanup attempt only
after final commit/push/fetched verification. Final basis `4c50f12c...f8b5a`,
helper `5ac3601b...2f641`, packet `cc20d877...27d46` and unchanged tests
`5d25dc07...6b195` pass the independent mechanical/execution review. Execution
record `7dc1b2b1...adc0d` binds the one-shot/no-retry/no-rollback contract and
the operational exclusion through observation and deletion. Invoke only the
non-root packet after its fresh gates pass; preserve every output/failure and
never run the helper directly. Cleanup success changes no acceptance counter.

Checkpoint 96 records that one recovery-v2 attempt as FAIL before claim,
journal, Docker, observer or deletion. Sanitized root Git rejected repository
ownership on the `-C` discovery path; failure record `fbdffcf7...3e3b` and raw
archive `93fde8f0...e424` preserve all outputs. Both roots, the old lease and the
prior claim/journal are unchanged; new claim/journal are absent. Never retry or
reuse `-2`. One bounded fresh `-3` correction may replace root Git discovery
with explicit git-dir/work-tree access and otherwise preserve the reviewed state
machine, then requires independent review and a new fetched release. No build or
acceptance work may cross the retained lease.

Checkpoint 97 independently PASSes the fresh recovery-3 DRAFT correction:
helper `b68ff713...72d7e`, packet `d4353972...e1547`, basis
`e887a35c...68ebe`, tests `aec12790...8ad07`. All Git queries use explicit
git-dir/work-tree; every `-3` output is fresh, and consumed `-2` evidence is
immutable input. No execution is authorized. Commit/push/fetch this template,
mechanically finalize the acyclic pins, then require a separate exact execution
review and fetched checkpoint before one attempt. Preserve the old lease/roots
and never retry or alter `-2`.

Shutdown checkpoint 98 preserves the pushed/fetched DRAFT at
`7aa1c02763d517fa2267f2d3ce67e097ddfc7734` without finalizing or executing it.
All child lanes are joined; launcher wrapper/worker/app-server identities remain
3399308/3399313/3399317 with starttimes 83682487/83682494/83682500. Preserve
both sealed quarantine inodes 14117 and 24701, the old lease inode 31447, all
prior failure evidence and the absence of recovery-3 claim/journal outputs. On
the next authorized continuation, reconcile those identities, mechanically
finalize only the reviewed recovery-3 pins/status, rerun all pure checks, obtain
independent exact execution review, and push/fetch a separate release before at
most one non-root attempt. No runtime or acceptance counter changed; the OS is
incomplete and this launcher pause is temporary.

Checkpoint 99 conditionally releases one exact recovery-3 cleanup attempt only
after final commit/push/fetched verification. Final basis
`46a9e891...47270`, helper `74460f72...9842f`, packet
`bf26d3b3...7e56` and unchanged tests `aec12790...8ad07` pass the independent
mechanical/execution review. Execution record `1a683afc...2154a` binds the
one-shot/no-retry/no-rollback contract and operational exclusion through
observation and deletion. Invoke only the non-root packet after its fresh gates
pass; preserve every output/failure and never run the helper directly. Cleanup
success changes no acceptance counter.

Checkpoint 100 closes the stale quarantine/lease blocker. The single recovery-3
attempt PASSed after two clean v7 observer rounds: zero references, denials or
tree failures across 1,636 task scans. Its 10,555-record journal proves 10,547
descriptor-bound deletions, two root removals, old-lease removal and terminal
success. Both quarantines, both originals and the old lease are absent; the new
claim/journal remain preserved. Success record `b9870848...c92ae` and
23-member archive `8a08748c...7388f` bind every live output; all 22 regular
members match. This grants no runtime or acceptance credit.

After fetched verification, prepare a wholly fresh commit-derived candidate and
all fresh backup/manifest/request/output/evidence/lease identities under the
reviewed preparation and aggregate resource constraints. Revalidate source
closure, modes, standalone metadata, at least 4-GiB tmpfs reserve and the pinned
12-GiB container accounting. Preparation does not release Docker build; seek a
fresh independent one-shot heavy-build review for the exact request. Preserve
all recovery outputs and historical failures.

Checkpoint 101 conditionally releases fresh candidate preparation only. Exact
packet `34249db...5a33`, five-test contract `3815ef4d...e0b9` and release record
`3342e097...dfaa` bind fetched source `675891545c881b8d625256ade56fe66ac69fe794`,
pinned IHK `3114d9e7`, corrected owner `a8c4c9fc...9155` and nine fresh
`67589154-1` targets. Independent review permits one non-root packet after
pushed/fetched verification and clean fresh preflight, plus exactly one
read-only privileged Docker `ps` capture. No build, lease, Docker mutation or
guest is released. The live nested IHK `21a0d1e` is a clean local-only whitebox
test change and is excluded by the pinned bare-store checkout. Preserve every
failure; preparation remains non-runtime/non-acceptance evidence.

Shutdown checkpoint 102 records one successful preparation-only invocation.
Candidate `/dev/shm/mckernel-exact-candidate-67589154-1` remains clean at
device/inode 26/25166; its standalone metadata backup remains at 26/35798. Exact
manifest `c5204af6...6ef9` and build request `a2c37952...aa7c` validate, while
the output/evidence roots remain empty and the build lease remains absent.
Record `05972423...dae8` and 75-member archive `53003c8e...a084` preserve the
run; every regular archive member matches its live original. No Docker client,
build, guest or acceptance operation ran, and current-candidate build count is
still zero.

All child lanes are joined for launcher shutdown. Preserve launcher identities
3399308/3399313/3399317 with starttimes 83682487/83682494/83682500 and preserve
the exact candidate, backup, request, manifest, empty roots, receipts and logs.
At the next authorized continuation, reconcile those identities and fresh
resource/process/Docker/lease state, then obtain independent one-shot heavy-
build execution review for request `a2c37952...aa7c`. Commit/push/fetch that
release before any owner invocation; this shutdown checkpoint authorizes no
build, retry, module, guest or acceptance work. The OS remains incomplete and
the launcher pause is temporary.

Checkpoint 103 conditionally releases one exact offline native build. Release
`d657a75e...8869` binds request `a2c37952...aa7c`, candidate
`67589154...fe794`, IHK `3114d9e7`, manifest `c5204af6...6ef9`, corrected
terminal-retaining owner `a8c4c9fc...9155`, driver `1e522a60...962b` and the
immutable source-free image. The separately observed Python 3.8 test-fixture
error is corrected at `b187b587...9ae5`; both host Python versions pass 65/65,
and production bytes/candidate remain unchanged.

Commit/push/fetch the exact release, then perform fresh complete unprivileged
and released absolute-sudo read-only Docker preflight. Only if all input,
identity, empty-target, lease, process, ownership, mount, capacity and aggregate
budget gates pass may the ordinary-user owner command run once. Retain all
terminal containers and evidence; do not retry or clean automatically. No
existing build, guest, runtime, application or acceptance credit is granted.
Success requires independent artifact/evidence review before a separately
released `startup.argv-empty` current-candidate diagnostic.

Checkpoint 104 records the consumed build attempt as FAIL before compilation.
Phase 0 stopped on `ihk-native-queue-check`: the checker demands one file-wide
`snapshot`, but production validly has a forwarding `SharedProducer` method and
the target `SharedQueue` implementation; `try_enqueue` has the same shape.
Record `2402d856...03e6` and 193-member archive `a6e2fff0...b46d` preserve both
preflights, the complete one-shot run and every live regular member. Terminal
container `decd7cf9...c6b9` remains retained, exited 1/non-OOM; owner/clients
retired, lease is absent and output is empty. Never retry, clean or reuse it.

Apply one bounded checker-only correction scoped to exact
`impl SharedQueue<'mapping>`, preserving semantic body checks and adding allowed
forwarder plus duplicate-target rejection. After independent source review,
commit/push/fetch and prepare an entirely fresh candidate/request/namespace;
the consumed release grants nothing further. Build count, apps and counters are
unchanged.

Checkpoint 105 closes the queue-checker prerequisite through the required expert
strategy. Checker `c9b4d012...aa96`, tests `fca20469...6e11` and contract
`b64022b8...f9fd` preserve production source `3163d9cc...e9c5`, ABI and fixture,
scope method extraction to exact `SharedQueue`, and bind the real three internal/
seven total tests. Both host Python suites pass 31/31. The separately reviewed
2-CPU/2-GiB Rocky fixture run PASSes all seven named tests with exact rustc 1.92;
container `8943e497...9bc10` is retained exited 0/non-OOM and binary is
`ceb5db9f...f43d`.

Success record `849d4bee...d036`, release `8affa38e...0062` and 61-member raw
archive `bb26afcc...90d6` have independent evidence PASS; all 59 regular archive
members match. This is source/fixture evidence only, not a kernel build, runtime,
guest, app or gate credit. Commit/push/fetch it, then prepare a wholly fresh
candidate/request/output/evidence/lease namespace and obtain a separate heavy-
build release. Never reuse `67589154-1`; retain both failed-heavy and passing-
fixture containers.

Shutdown checkpoint 106 (2026-09-29): all child lanes are joined and no new
execution was started. Preserve launcher identities 3399308/83682487,
3399313/83682494 and 3399317/83682500 and retained terminal containers
`decd7cf9...c6b9` (exit 1) and `8943e497...bc10` (exit 0). Fresh preparation
packet `7502c748...b3a0a` plus test `ba67804f...d8c` pass their five pure tests
but are unexecuted and unreleased. Cleanup review blocks deleting the consumed
candidate and backup until a complete restoration capsule and reviewed ordinary-
retirement packet support the exact unchanged terminal-container exception and
fresh live-reference closure. See
`stability-shutdown-checkpoint-20260929-106.json` and CURRENT checkpoint 106 for
the precise next tasks. Formal counters and successful current-candidate builds
remain unchanged; the launcher pause is temporary and the OS is incomplete.

Checkpoint 107 closes the source-only restoration/retirement prerequisite after
preserving rejected attempt hashes and their concrete safety defects. Final
planner/archive/retirement hashes are `ac3bb035...d0b26`,
`6a28184e...ac06e`, `744beace...21b5d`; final test hashes are
`ae6f129a...43c9a`, `fa9d727d...8355e`, `3605a65b...2fce`. Python 3.8 and
3.9 each pass 40/40. Independent integrated review PASSes those exact bytes for
source and temporary fixtures only, including actual-v7-shaped integration,
strict restoration authority, deterministic byte-snapshot archive verification,
original+quarantine Docker rejection and post-journal substitution safety.

No live capsule, cleanup, build or guest ran; builds/apps/counters remain zero.
After push/fetch verification, prepare and independently review one fresh
one-shot packet for live `67589154-1` manifest+archive generation only. Verify
the actual 49 links, full member coverage and stable postflight identities.
Do not rename/delete either root or treat that preparation as cleanup release.
See `stability-native-exact-retention-source-checkpoint-20260929-1.json`.

Shutdown checkpoint 108 interrupts the first correction of the live-retention
preparation packet before review or execution. Packet `ab1471e8...4742` is
source-only WIP; its unchanged test `63abe211...27defa` currently has three
passes and one stale-token failure. No inventory, capsule/archive, cleanup,
build or guest operation ran, and the sole active child is joined. Preserve the
three launcher identities, both retained terminal containers and both consumed
roots exactly as recorded in
`stability-shutdown-checkpoint-20260929-108.json`.

At the next authorized continuation, reconcile live state, complete and test
the packet correction, obtain independent source review, and checkpoint/fetch-
verify the exact bytes before creating a separate acyclic one-shot preparation
release. Preparation grants no retirement authority. Independent capsule review
and a separate privileged retirement release remain mandatory before any root
rename or deletion. The OS remains incomplete; successful current-candidate
builds and formal counters remain unchanged.

Checkpoint 109 closes the source/test-design prerequisite for live retention
preparation after preserving four rejected/interrupted candidate hashes and
their findings. Exact reviewed placeholder packet `c57ed38d...8f1c` and test
`57152321...dfa8` pass 14 behavioral tests on Python 3.8 and 3.9 plus
pycompile/diff checks. Independent review PASSes only this source boundary:
acyclic template/release admission, exact fetched blobs and release delta,
bounded standalone Git control metadata, fresh scratch/claim lifecycle,
signal-safe group cleanup, one-read snapshots, exact archive ancestor closure
and second-planner postflight equality.

Commit/push/fetch this placeholder template first. Then construct an
independently reviewed release JSON binding that prior commit and exact inputs;
the following release commit may change exactly the packet release literal and
add that JSON. Do not execute before fetched admission and one-shot release.
No capsule, cleanup, build or guest ran; counters remain unchanged. See
`stability-native-exact-retention-preparation-template-review-20260929-1.json`.

Checkpoint 110 preserves released attempt 1 as an observer FAIL: PID 3780193
vanished between `/proc` enumeration and identity read, before claim, planner,
archive or root traversal. Inventory/archive remain absent and the empty attempt-
1 scratch directory is retained. See
`stability-native-exact-retention-preparation-failure-20260929-1.json`.

Corrected placeholder packet `abe54826...b21b` and test `40dd25d3...8e93`
receive independent source/test PASS after 18 tests on each Python. Candidate
and backup stay at attempt 1; only release/output/evidence paths use attempt 2.
Commit/push/fetch this template, then independently review and mechanically
finalize a fresh attempt-2 release. Never retry attempt 1 or remove its empty
scratch evidence. No runtime, cleanup, build, guest or formal credit changed.

Checkpoint 111: released preparation attempt 2 PASSes. Inventory
`ce0c47f5...e1d10` covers 10,595 entries/49 links; capsule
`94fe0c36...712c8` has 923 exact members; raw evidence
`e91de69b...845df` preserves all worker records. Three workers and owner exit 0
and retire; claims/leases are absent. Independent review verifies all live
entries, exact USTAR bytes and 9,011 reconstructible canonical blobs.

The capsule requires preserved main `67589154...fe794` in the root object store
and IHK `3114d9e7...72a1f` in `.git/modules/ihk`; it is not standalone. Artifact
commit `3c36091c...cf4bb` is pushed/fetched and its four evidence blobs match.
Next obtain a separate privileged retirement release
binding both stores, exact roots, fresh quarantine, two closure rounds and full
Docker/process/mount evidence. No retirement, space recovery, build, guest or
acceptance credit exists. See
`stability-native-exact-retention-preparation-success-20260929-2.json`.

Shutdown checkpoint 112: no new work was dispatched after the stop request;
all child lanes and retention workers are joined. Preserve launcher identities
3399308/83682487, 3399313/83682494 and 3399317/83682500, both retained terminal
containers, both consumed roots, and attempt-1/attempt-2 evidence roots. The
next invocation must reconcile those live identities and the already verified
fetched checkpoint before designing the separate privileged retirement release. Only
after independently reviewed retirement and measured capacity recovery may
fresh preparation `704f6654-1` proceed toward a new heavy build. The OS is
incomplete and the launcher pause is temporary.

Checkpoint 113: expert-corrected retirement helper/observer boundary independently
PASSes source review. Exact hashes are helper `2ba70074...8964e`, helper test
`e7630fa2...20981`, current observer `3562b1d3...53666` and observer test
`b5f48e7b...922e4`; Python 3.8/3.9 tests and observer self-tests pass. It now
durably journals and revalidates the root:root/0700 transition and carries
uid/gid/type/mode through full-tree v7 revalidation. See
`stability-native-exact-retirement-owner-observer-source-success-20260929-1.json`.

This is source-only. The integration packet's initial, bounded-correction and
first expert candidates remain rejected; latest `22f19e81...80eb` has five
retained blockers covering schema compatibility, bounded Git I/O, procfs
completeness, child retirement and held operational exclusion. A single larger
coherent correction is active. Obtain independent source/execution review and a
fetched release before any sudo, rename or deletion. Counts remain unchanged.

Shutdown checkpoint 114: new dispatch stopped; the final expert correction is
joined and no child remains active. Packet `59b3bedf...dc483` and test
`8c57021a...d5c8` pass 15/15 on Python 3.8 and 3.9 plus pycompile/diff checks,
but remain unreviewed source WIP. No live packet, privilege, Docker mutation,
rename, deletion, build or guest operation ran. Preserve the three launcher
identities, candidate/backup and both preparation-evidence roots, and the two
terminal containers recorded in
`stability-shutdown-checkpoint-20260929-114.json`.

Next: reconcile live identities; independently source-review the exact packet
against all five prior blockers; only on PASS checkpoint/fetch the immutable
template, mechanically bind an acyclic release, and obtain separate execution
review. Do not run sudo retirement before that release. Retirement and measured
space recovery precede review of preparation `704f6654-1` and any heavy build.
The OS remains incomplete and the pause is temporary.

Checkpoint 126 supersedes checkpoint 114's retirement-template state. After
preserving independent BLOCKs 118 through 124, exact DRAFT packet
`f1cb3db7...c363`, packet test `41ad8074...c4b6`, helper
`2218e7fe...010` and helper test `c350fc3e...95c1` receive independent
source-template PASS. Python 3.8 and 3.9 each pass 106 related tests
sequentially. The boundary retains child identity and streams before decoration,
uses an unreaped pidfd leader anchor, rejects SID reuse, accumulates retirement
errors and preserves helper/packet composite failures in terminal JSON.

This is not an execution release. Commit/push/fetch the exact template and its
two review records first. Then mechanically add an acyclic release JSON and
replace only the packet's release sentinel, followed by separate independent
execution review and fresh live support gates. A permanent child-pidfd failure
is an explicit fail-closed survivor state, not cleanup success. No candidate,
build, guest, application or acceptance counter changed; successful current-
candidate builds remain zero and applications remain 0/273.

Shutdown checkpoint 128: immutable source-template commit
`325e7c2e00995726c094649168a8e854dd5689a2` is pushed and fetch-verified.
All child lanes are closed. Release-schema audit 127 completed, but the packet
still contains its DRAFT sentinel and no release JSON exists. No root traversal,
retirement, privilege, Docker mutation, build or guest ran. Preserve the exact
live identities and capacities in
`stability-shutdown-checkpoint-20260929-128.json`.

Next: reconcile live state, mechanically bind the release to `325e7c2e` with
fresh complete root/Docker observations, verify the exact packet-plus-release
delta, push/fetch it, and obtain independent mechanical/execution review before
any one-shot sudo retirement. The OS remains incomplete; this pause is
temporary.

Checkpoint 132 supersedes checkpoint 128's exact template hashes. The first
generated release `26bf80ff...e8a8d` failed precommit because Docker Mounts
ordering changes across equivalent inspect calls; no runtime mutation occurred
and the raw candidate is retained. The bounded packet/helper correction now
independently PASSes exact hashes `7e3581fb...0daf` and
`704a3f5f...f54b`, with tests `1e878802...e4f1` and
`c2a65c45...3d68`. Both sides canonicalize only full-object Mounts ordering;
all other Docker and retirement safety fields remain exact.

Commit/push/fetch this DRAFT template and the two new records. Then regenerate
the acyclic release against that fetched commit, change only packet plus release
paths, and obtain separate mechanical/execution review before sudo retirement.
No build, guest, application or acceptance counter changed.

Checkpoint 134 supersedes checkpoint 132's template hashes. Release candidate
2 `5a28247b...bb34` passed root/archive/Docker validation but exposed a second
complete sentinel token embedded inside `final_bytes`; the exact-one guard
correctly blocked it. The raw candidate and failure are preserved. Corrected
DRAFT packet `aaf4ac87...de87` and test `7a563aac...d346` independently PASS:
the source now has one token, finalization changes only its declaration, and
missing/duplicate tokens reject.

Commit/push/fetch this exact template before regenerating the release. Then
obtain independent exact mechanical/execution review before any privileged
retirement. No runtime or acceptance counter changed.

Checkpoint 138 supersedes checkpoint 134's release state. Release
`aa763d01...9d02` is preserved as an unprivileged admission FAIL: its 512-MiB
reader could not map the 7.89-GiB pack. A 12-GiB bounded correction exposed the
wrong authority for 49 symlink digests, 7.9-GiB RSS and an EOF-wait cleanup
defect. Expert redesign and one independent review correction now PASS exact
DRAFT packet `6f2be938...ebc2` and test `e26918a6...5cf1`.

Both runtimes pass 116 tests and complete all 9,011 canonical objects/
9,050,119,070 bytes at about 260 MiB peak RSS with four recorded reader
identities, rc 0, retired state and empty final censuses. The current worktree
removes the invalid release JSON and restores DRAFT. Commit/push/fetch it as the
new template, then regenerate the exact two-path release and obtain separate
execution review before sudo. No retirement/build/guest/application credit.

Checkpoint 143 supersedes checkpoint 138's retirement state. Corrected fetched
release `431df62c...2f35c` passed all 9,011-object admission, independent
execution review and its single `sudo -A` invocation. Independent runtime review
PASSes complete removal of the 10,509-member candidate and 86-member metadata
backup with clean observer/Docker evidence and no surviving packet processes.
Archive `stability-native-exact-retirement-runtime-67589154-20260929-1.tar.gz`
is `840c1e95...c0d`; preserve immutable tombstone `ac3d1895...f34` unchanged.

Next independently review preparation `704f6654-1` packet `7502c748...3a0a`,
then run it once only if released and its nine target names remain absent. Review
that result before one serialized heavy build and the smallest real memory app
diagnostic. No formal acceptance counter changed; builds remain zero and
applications remain 0/273.

Checkpoint 145 supersedes checkpoint 143's preparation state. Exact packet
`7502c748...3a0a` ran once and independently PASSes preparation evidence.
Candidate `704f6654...63561` / IHK `3114d9e7...72a1f` is dev/inode 26/36767,
backup 26/47413; manifest `b8d89bf8...e3b1`, request `891c24c0...a2f`, receipt
`05055889...e6e8` and archive `e9ae5ac4...f306` are retained. Owner validation
requires 21,970,231,296 bytes under the 24-GiB aggregate limit; destinations are
empty and the new lease is absent.

Next obtain fresh independent one-shot heavy-build review for the exact request
and owner command, then run only on PASS. Review the retained terminal container
and build artifacts before the smallest real memory application diagnostic.
Builds remain zero and applications remain 0/273.

Checkpoint 147 supersedes checkpoint 145's build state. Independently released
build `704f6654-1` ran once and failed after 19.99 seconds in phase 0: exact
rustc returned success, but the queue checker rejected its `/tmp` fixture as
not executable/absent. Earlier checks and the prior parser repair passed; no
compile phase or artifact output began. Retained terminal container
`68881c05...927a6` is exited 1, PID 0, non-OOM. Owner/clients retired and the
lease is absent. Preserve failure archive `e09ca937...8417`, candidate, backup,
container and all evidence.

Do not rerun this request. Make one bounded checker/output-location correction,
prove exact Rust compile plus seven-test execution in the reviewed light
profile, independently review it, then prepare a wholly fresh commit-derived
candidate before any later heavy build. Builds remain zero and applications
remain 0/273.

Shutdown checkpoint 154 supersedes checkpoint 147's live retirement state.
The v2 retirement packet ran once, quarantined candidate 26/36767 and metadata
26/47413, then failed closed before deletion because its sealed historical
observer rejected the new quarantine names. Preserve evidence root 26/47525,
immutable consumed-build tombstone 1831/31474, failure archive
`ba74523d...8806`, and failure record `1e63a02e...d7e0`. Never retry or roll
back the consumed packet.

The exact-path observer adaptation `6feda9c9...10a42` is narrowly reviewed.
Continuation DRAFT `fe7a22fa...d40a` is not executable and independent review
BLOCKS it on seven families: release authentication/invocation, callback FD and
process retirement, real observer schema binding, full Docker census handling,
fail-closed process exclusion, hash-at-unlink descriptor/name revalidation, and
durable terminal evidence/cleanup. On continuation, reconcile record
`stability-shutdown-checkpoint-20260929-154.json`, then make one expert bounded
correction and obtain fresh independent review. No release or privileged run is
authorized. Builds remain zero, applications remain 0/273, and the OS remains
incomplete.

Checkpoint 155 supersedes checkpoint 154's blocked source design, not its live
retained state. After two rejected correction cycles, an Astra redesign now
independently PASSes exact DRAFT packet `0f3c4400...418b`, wrapper
`7b41bb6f...e4ef`, basis `241feb5c...ac1f` and tests `1f409919...3ae4`.
Twenty-six tests pass on Python 3.8 and 3.9. The acyclic fetched-commit model,
real observer schema/owned retirement, complete Docker/runtime gates,
descriptor-safe deletion, combined cleanup evidence and bounded signal-storm
closure are source-reviewed.

No execution release or runtime acceptance exists. Preserve quarantine roots
26/36767 and 26/47413, historical evidence 26/47525 and immutable tombstone
1831/31474. Next push/fetch the DRAFT template, then mechanically change only
packet, wrapper and basis while adding the external release as the fourth path.
Obtain independent mechanical/execution review and repeat complete live
preflight before any one-shot sudo continuation. Never retry or roll back the
consumed v2 packet. Builds and real guest applications remain zero; application
acceptance remains 0/273.

Checkpoint 156 adds a mandatory credential-safe Docker binding before release
generation. Exact packet `a1539505...3edf` and tests `f9c38fbb...70e9`
independently PASS 28 cases on Python 3.8/3.9. The external release must retain
only 17 ID-to-hash bindings plus four safe terminal mount exceptions; complete
inspect records are hashed in memory and never serialized. Evidence may contain
only ID, digest, selected terminal state, restart policy and protected mounts.

Push/fetch this DRAFT correction, then mechanically change packet, wrapper and
basis and add one external release as the exact fourth path. Review both the
mechanical derivation and safe runtime authority before any sudo execution.
Quarantines and permanent tombstone remain unchanged; no runtime acceptance or
formal counter moved.

Shutdown checkpoint 157 (2026-09-29) supersedes the live cursor only: all child
lanes are terminal, the three launcher identities remain live, and the consumed
packet remains absent. The quarantine/evidence roots and immutable tombstone are
unchanged. Source checkpoint `f89cc5b8640fbae4119f851571c9254d38579f55`
is fetched and upstream; no execution release exists. Next reconcile identities
and roots, inspect the exact release schemas, mechanically create the exact
four-path finalization from that fetched template, commit it separately, obtain
independent mechanical/execution review, and repeat complete live preflight.
Do not execute, retry, rename, delete or roll back retirement state while
recovering this checkpoint. The OS remains incomplete and 0/273 applications
are accepted.

Checkpoint 158 supersedes the finalization cursor with one required source
correction. A live harmless probe showed the exact wrapper's sudo parent carries
the forbidden packet basename. The first bare-PID correction was independently
BLOCKed by reproduced post-validation PID reuse and status/argv defects. Expert
DRAFT packet `ae2f6d07...a1e9` plus tests `fadd0322...18b6` now retain and
revalidate sudo parent/child and launcher identities, exact executable/NUL argv
and parsed credentials. All 35 tests pass on Python 3.8/3.9 and independent
review PASSes source only. Wrapper/basis remain unchanged and inert; no release
or runtime action exists.

Next commit/push/fetch this correction, then use that fetched commit as the new
template ancestor for the exact packet/wrapper/basis plus external-release
four-path finalization. Review mechanics and live authority independently and
repeat every preflight before one one-shot sudo continuation. Retained roots,
tombstone and formal/application counters remain unchanged.

Checkpoint 159 supersedes release `fc529820...ae607`: independent review passed
it, but the coordinator's external read-only preflight found an exact harness
defect before wrapper invocation or claim. The pinned tar directory header omits
the trailing slash required by `validate_raw_history`. Packet
`682a3791...dcc8` and tests `a8df1959...76c2` correct only that TarInfo name;
the pinned SHA, exact eleven-member/type/duplicate checks and all live/tombstone
byte comparisons remain. Actual retained history passes, 37 tests pass on
Python 3.8/3.9 and independent review PASSes source only.

Packet/wrapper/basis are back in DRAFT. Commit/push/fetch this correction, use
that commit as the new template ancestor, regenerate exactly four release paths,
obtain fresh execution review, and repeat the full external preflight. Never run
the superseded `fc529820` release. No retirement state or acceptance counter
changed.

Checkpoint 161 adds independently source-PASSed observer v3
`14789e10...7139` with process-level map-files coverage and a real
descriptor-closed mmap regression. Historical v2 remains exact and its consumed
proof remains BLOCKed. The separate post-deletion audit has two rejected source
candidates and is now in expert redesign for typed exit/error reconciliation,
baseline-bound descendant mount aliases, stable namespace proof and exact mmap
detection. Do not run the rejected audit or authorize a build. Next review the
expert audit, then obtain a fresh root read-only release and execute it against
the sealed 10,611 deleted identities.

Checkpoint 160 records one-shot physical cleanup success but BLOCKed reference
proof. Release `ef8dffa1...9986` deleted 10,523 candidate and 86 metadata members,
both roots are absent, journal terminal failure is null, observer retired, and
Docker before/after match. Exact archive `16cafe64...af2` plus record
`stability-native-exact-quarantine-continuation-runtime-blocked-704f6654-20260929-1.json`
preserve the result.

Do not accept or rerun it: both observer rounds scanned zero mapping links because
they used nonexistent task-level `map_files` and accepted 1,636 directory
absences. An mmap-only reference could have been missed. Next implement an
additive process-level-map-files observer with an mmap-only regression, obtain
independent review, then perform a current-state audit against all deleted
device/inode identities from the retained inventory. Only that current-state
audit may unlock a wholly fresh clean candidate; it cannot retroactively make
the consumed retirement proof complete. Builds/apps/formal counters remain zero.

Shutdown checkpoint 162 supersedes only the live cursor. Exact expert audit
helper `997c8b80...2406` and tests `cbe06f64...9ab8` independently PASS source;
22 tests pass under Python 3.8/3.9 and the sealed baseline remains exactly
10,611 identities with digest `3ee0942c...a1e8`. No root audit or runtime action
ran. All children are terminal. Preserve launcher wrapper 3399308/83682487,
worker 3399313/83682494, app-server 3399317/83682500, historical evidence
26/47525 and immutable tombstone 1831/31474.

On the next authorized continuation, verify the fetched checkpoint and these
identities, prepare a fresh exact root read-only execution release, obtain
independent execution review, and only then run three audit rounds. Do not rerun
the consumed build or quarantine packets. A successful current-state audit
cannot retroactively repair the consumed retirement proof. The OS remains
incomplete and application acceptance remains 0/273.

Checkpoint 163 supersedes the root-audit release cursor. Fetched attempt-1
proposal `cd3aa38f...2e74` was independently BLOCKed before sudo because stable
kernel threads lack required process resources; never execute it. After the
ordinary bounded correction and first expert candidate were separately BLOCKed
on negative flags, skipped mount aliases, LP64 overflow and oversized VMAs, the
expert correction now independently PASSes source at helper `47e741e7...6d88`
and tests `0e217fbb...9e3`. Python 3.8/3.9 each pass 44 tests and 59 independent
complete-census probes pass.

Commit/push/fetch the corrected source, then create a fresh attempt-2 exact basis
and root read-only proposal and obtain fresh execution review. No privileged
audit has run. A future current-state PASS is sampled evidence only and cannot
repair the consumed retirement proof; builds/apps/formal counters remain zero.

Checkpoint 164 supersedes attempt-2 execution state. Released attempt 2 ran once
and FAILed closed: durable result `f5c1e35e...ee8`, archive `e0e206b3...e171`,
three rounds each with 33,881 map entries and zero retained references, but 267
mountinfo parse failures cleared the census. Never retry it. Canonical nsfs roots
caused most failures; ordinary chroot PID 868/398 exposed the deeper rule that a
filtered view cannot prove namespace-wide alias absence.

Expert helper `641c39a3...d7ab2` plus tests `af9ab213...6904` now independently
PASS source with 56 tests on Python 3.8/3.9. Every observed mount namespace needs
a revalidated root-`/`, parsed nonempty representative; chroot/empty views defer
only within that exact namespace. Commit/push/fetch this correction, then derive
fresh attempt 3 and seek independent execution review. No audit PASS, fresh
candidate build or application acceptance exists.

Checkpoint 166 supersedes the audit execution cursor. Released attempt 3 ran
exactly once after complete preflight and independently `PASS_RUNTIME_REVIEW`.
Root result `ed82eba0...7903` records three identical clean rounds: 271
processes, 816 stable task identities, 33,882 map-file entries, and zero
references, failures, denials or reconciled exits. The target reconstructs to
10,611 identities with digest `3ee0942c...a1e8`. Receipt `1401bb83...fb6`
preserves exit 0, 8.673624604 seconds and empty streams; archive
`842f5d3f...b8be` preserves release, basis, receipt and raw root result.

This sampled current-state PASS unlocks wholly fresh candidate preparation only.
It cannot retroactively accept the consumed retirement and grants no build,
guest, application or gate credit. Next commit/push/fetch this exact evidence,
then generate a new-nonce preparation packet from the fetched main commit and
IHK `3114d9e7101ad52030eb3effa849a5c108972a1f`; never use the dirty nested IHK
or any `67589154-1`/`704f6654-1` path. Obtain independent preparation review
before one preparation run. Builds and real guest applications remain zero.

Checkpoint 167 supersedes preparation routing. Fresh packet `7e3c4897...a0010`
ran once after independent release and produced candidate `f5d8d914-1` at
26/47678 plus metadata backup 26/58429. Main is exact fetched
`f5d8d914f816d4a677990719854f7b4d312a430b`; IHK is `3114d9e7...72a1f`.
Manifest `b37c4f7c...a6d8`, request `9f1b1653...5fd8`, metadata receipt
`6d076fd8...3a7a` and log `b09c18b3...6599` pass independent preparation
review. All 9,129 tracked inputs pass, output/evidence are empty, the lease is
absent, all processes retired, and archive `69976447...a5ae` matches 96 live
members. Aggregate planned memory is 22,026,375,168 under 24 GiB.

Preparation grants no build execution. Next checkpoint/push/fetch this evidence,
then independently release the exact owner command for request `9f1b1653...5fd8`
under the pinned 4-CPU/12-GiB/no-network profile. The candidate includes the
reviewed queue executable-root correction that addresses the consumed 704f
phase-0 failure. Builds and real guest applications remain zero.

Checkpoint 169 supersedes build routing. Both heavy releases for prepared
candidate `f5d8d914-1` were BLOCKed before execution; never use them. Central
phase temp-root repair at fetched `57133e95...8eb1` passed source review. The
first isolated light run exposed two fixture defects, preserved in archive
`f6c0c49a...2d0b1`; bounded corrections are now in fetched `66ced088...fe17`.

Fresh isolated container `3c169e5c...5366` with pinned Rust 1.92 exited 0 under
the same 2-CPU/2-GiB/no-network/read-only/noexec-`/tmp` profile. Four focused
tests, 19 driver tests, the queue fixture, 84/85 consolidated Python tests and
page allocator/page owner/mapping checks pass; the sole skip is the unchanged
external Rocky-source audit. Final marker and empty temp root pass. Archive
`1c3ec354...81f6` and record
`stability-native-offline-exec-temp-root-light-success-66ced088-20260929-2.json`
retain the result. Additive correction `80b31e0a...dcfa` fixes three copied
member hashes in the immutable prior failure record; rereview PASSes.

This is light infrastructure evidence only. Preserve obsolete candidate
26/47678 and backup 26/58429 until a fresh reviewed retention capsule and
separate one-shot retirement release complete. Never direct-delete, patch the
candidate, or reuse blocked/historical packets. After verified retirement,
prepare a wholly fresh candidate from the fetched corrected commit and seek a
new heavy-build release. Builds and real guest applications remain zero.

Checkpoint 170 establishes the retention-preparation template ancestor only.
Packet `91bacf83...f60ab` and immutable tests `2be61b93...aa53` independently
PASS source after expert correction of the release-transition fixture; the same
20 tests pass against placeholder and already-populated forms. Exact roots are
candidate 26/47678 and backup 26/58429; all outputs use fresh `9e5ab03d-1`
names. `RELEASE_HASH_REQUIRED` still forbids execution.

Next push/fetch this exact template commit, then create one release JSON binding
that prior commit and change only it plus the packet literal in a second commit.
Obtain independent execution review and full live preflight before one ordinary-
user retention-preparation run. No retention, retirement or build is accepted.

Checkpoint 171 accepts retention preparation only. Released commit
`610b7bb4...d32f` ran once as ordinary user and exited 0 in 51.644925029 seconds.
Inventory `841dedac...34f89` is byte-identical to postflight; restoration archive
`624da324...a6a4` passes all 924 production-verifier members. All packet/child
processes retired, streams are empty, claims/leases are absent, and candidate
26/47678 plus backup 26/58429 remain clean and unchanged. Raw archive
`7bd51f30...83cf` preserves 23 members; independent review returns
`PASS_RETENTION_PREPARATION`.

Next checkpoint/fetch-verify these bytes, then create a fresh two-root retirement
packet bound to the exact inventory/archive/root identities. Require independent
source and execution review plus fresh canonical reconstruction, process, mount
and reference checks. No restore, retirement, deletion or build is yet accepted.

Shutdown checkpoint 172 supersedes the retirement-draft cursor. The initial
source review BLOCKed six semantic families. The sole worker stopped after one
bounded correction attempt; no packet executed and all children are terminal.
The six preserved files hash to packet `f25b695c...726ed`, packet test
`3370660d...dfa2`, helper `7aa052bc...e18`, helper test `ed7bd0e0...1441`,
observer `34a4e4bc...54a3` and observer test `66b08586...3707`. The attempted
112-test run has one failure and six errors; there is no valid compile result.

Remaining defects are a `docker_callback` indentation/`NameError`, missing
deleted-audit sources in helper fixtures, stale inventory schema/count fixtures,
and a failing signal-cleanup assertion. Per convergence policy, use an expert
correction for this same failure family next; then independently rereview every
initial finding plus post-delete audit and release-transition behavior. Do not
commit a retirement template or construct a release until source review PASSes.
Candidate 26/47678 and backup 26/58429 remain intact. Launcher identities are
3399308/83682487, 3399313/83682494 and 3399317/83682500. No retirement, build or
guest ran; counters remain 6/130, 350/10000 and 0/273 applications.

Checkpoint 173 supersedes the failed draft cursor. Expert escalation repaired
the whole six-file retirement boundary and independent Astra review returns
`PASS_SOURCE`. Exact reviewed hashes are packet `efef4b6e...4ee7`, packet test
`3399b957...7959`, helper `f589ba43...378a`, helper test `5774766d...515e`,
observer `e8800a59...5374d`, and observer test `b4eaac82...1321`. Python 3.9
passes 183 tests independently; Python 3.8 author runs pass 127+56. The current
retained identity contract is 10,716 = 10,629+87, not historical 10,611.

Candidate 26/47678 and backup 26/58429 remain intact; no retirement/build lease
or guest exists. Current launcher identities are 4041681/92434707,
4041684/92434713 and 4041686/92434719. `RELEASE_HASH_REQUIRED` remains. Next
push/fetch-verify this immutable template, then mechanically add one release JSON
and replace only that literal. Obtain independent execution review and repeat
fresh root/process/lease/capacity/Docker checks before one invocation. Source
PASS grants no retirement, build, application or OS acceptance.

Shutdown checkpoint 174 leaves the source template fetched at `5b8f6482...2f65`
and the packet hard-blocked by `RELEASE_HASH_REQUIRED`. Bounded generation made
an unreviewed 2,415,286-byte draft release JSON SHA `f7b48994...06efa`; 127
populated-form tests passed before the literal was restored. It binds roots
26/47678 and 26/58429, the three exact terminal containers, current boot and
launcher identities 4041681/92434707, 4041684/92434713 and 4041686/92434719.
No runtime action occurred and all children are terminal.

Because this checkpoint changes ancestry, next verify its fetched commit and
live state, rebind the draft's template/finalization commit plus any changed
launcher facts, recompute its hash, and make an exact two-path finalization:
release JSON and packet literal only. Push/fetch it, then obtain independent
Astra execution review before one possible `sudo -A` invocation. Do not execute
the checkpoint-174 draft. Counters remain 6/130, 350/10000 and 0/273 apps.
