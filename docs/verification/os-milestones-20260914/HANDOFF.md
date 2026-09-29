# Compact dispatcher handoff

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
