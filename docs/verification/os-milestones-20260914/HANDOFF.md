# Compact dispatcher handoff

Reconciled 2026-09-28 during the active aggressive launcher invocation. The
whole-OS goal remains active and incomplete. A checkpoint, stable-core row or
diagnostic application is never whole-OS completion.

## Authority and identity

- Branch: `codex/local-native-staging-repair`.
- Last verified remote checkpoint before the current evidence delta:
  `5af634ce1e71248d7bbe144a49d689443993f449`.
- Adopted policy SHA-256: GOAL `76c4f5d1...c0bcc3`, START
  `1698d342...6216c`, CONVERGENCE `f6938bd2...3e86a`, HANDOFF predecessor
  `265cd999...a415`.
- Launcher wrapper PID/PGID/SID 3399308/starttime 83682487; worker
  3399313/starttime 83682494; app-server 3399317/starttime 83682500.
- No QEMU, mcexec, diagnostic owner or heavy build/guest lease was live at the
  last reconciliation. Recheck exact identities and capacity before heavy work.
- Preserve unrelated dirty launcher/policy files, deleted/untracked pycache and
  dirty nested `ihk`; stage only campaign-owned paths.

Official counters remain 0/273 accepted applications, 2/4 narrow fault modes,
6/130 production gates, 350/10,000 points and 0/7 language gates. Four real
diagnostic guest applications (memory/files/threads/signals) have run; zero
current-candidate builds exist. Required hardware/exposure remains unavailable
locally and does not prevent independent implementation work.

## Active M05 lifecycle family

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

Next executable source step: finish the lifecycle checker's exact import-order
expectation and refresh its `smp_cpu.rs` contract hash, then require the full
60-test suite. Independently rereview the repaired journal and build supplement,
run the workflow assertion with a compatible Python interpreter, and then run a
reviewed configured build. Separately implement the native-revision-gated IRQ
slot descriptor, sender gate and exact failed-IRQ_WORK_VECTOR retry fixture from
`stability-native-shutdown-irq-slot-design-review-20260928-1.json`. Freeze
STOP/ACK only after CPU reclamation and callback drain both pass independent
review. Do not run the shutdown fixture earlier.

Keep original failures in CURRENT.md/evidence. At the next coherent checkpoint
update touched stable-core rows, run `scripts/update_progress_tracker.py`, commit,
push and verify fetched blobs. One heavy build/guest maximum; aggregate seven
jobs/24 GiB, pinned container at CPUs 2-5/12 GiB/no swap/512 tasks/no network.
