# Compact dispatcher handoff

Reconciled 2026-09-28 during the active aggressive launcher invocation. The
whole-OS goal remains active and incomplete. A checkpoint, stable-core row or
diagnostic application is never whole-OS completion.

## Authority and identity

- Branch: `codex/local-native-staging-repair`.
- Last verified remote checkpoint before the current evidence delta:
  `a252a47a32b5db5f724b011b2ec8e0a9f71e46a4`.
- Adopted policy SHA-256: GOAL `76c4f5d1...c0bcc3`, START
  `1698d342...6216c`, CONVERGENCE `f6938bd2...3e86a`, HANDOFF predecessor
  `265cd999...a415`.
- Launcher PID/PGID/SID 3125264/starttime 80228730; recovered worker
  3170135/starttime 80670556; app-server 3170137/starttime 80670562.
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

Next executable source step: implement and semantically test the distinct
native shutdown reset/re-online journal using the new reset export, without
wiring v5 or freeing resources. Independently implement and test the
generation-scoped IRQ-work sender/drain registry. Continue the existing
lifecycle-checker correction from its exact unstaged WIP; its current 60-test
run still fails before the intended negative assertions, so it is not an
accepted oracle. Then freeze STOP/ACK only after both ownership boundaries pass
independent review. Do not run the shutdown fixture earlier.

Keep original failures in CURRENT.md/evidence. At the next coherent checkpoint
update touched stable-core rows, run `scripts/update_progress_tracker.py`, commit,
push and verify fetched blobs. One heavy build/guest maximum; aggregate seven
jobs/24 GiB, pinned container at CPUs 2-5/12 GiB/no swap/512 tasks/no network.
