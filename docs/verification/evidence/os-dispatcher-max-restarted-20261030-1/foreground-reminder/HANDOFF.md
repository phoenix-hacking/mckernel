# Foreground15minute reminder successor source (unselected)

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Permissions remain danger-full-access, approval never. Only this new directory was written. `foreground_reminder.py` and `test_reminder.py` are exact unchanged copies of FOREGROUND-15MIN-PRIORITY-SOLMAX-20261030-3. Its queue/runtime/hold predicates remain byte-identical. No preparation, launch, RPC, queue, signal, lease probe, cancellation or cleanup was performed.

`prepare_reminder.py` defaults to source-only. Explicit preparation is reserved for Root after DISPATCHER-MAX-PREFERRED-20261030-1 has actual healthy ACTUAL-CONTROLS-ARMED.json and ACTUAL-CAPACITY-FALLBACK-ARMED.json. Missing receipts refuse before interface import/probes. It requires Root's actual CODEX_THREAD_ID to equal the original foreground origin01a18ac2-f20f-7992-828e-cd269dff983f. It does not substitute the worker thread ID or change the user's literal origin.

Preparation uses that controller's existing check_packet/live_binding, actor birth, no_holds, instruction, heartbeat and read-only lease interfaces. It verifies current Root/receipt equality, same watcher/guardian/monitor births, live worker/server ancestry, fresh current-invocation heartbeat, guardian packet/health, monitor cursor/publication, capacity publication/source packet and five occupied controller leases. It verifies the old reminder's sealed source packet, positively stopped status, actual launch/status birth equality, original birth absence and own lease freedom. Old HOLD/STOP records prevent preparation; none are removed or cleared.

Config preserves the exact literal15minute/specific instructions and historical function queue, carries cumulative deliveries17 when still current, original origin, exact old next_due_monotonic and the minimum old/new/guardian caps. Existing runtime emits one immediate replacement notice; if the carried due is future it honors that due afterwards, otherwise it schedules once900seconds later. There is no backlog or delivery replay. Historical files remain in place and fresh preparation snapshots/hashes preserve their reference. A changed old/controller receipt during observation refuses.

The emitted CONFIG.json binds exact current campaign thread, new actual guardian/path/packet and current canonical launcher hash. PREPARATION-OBSERVATIONS.json records the actual readbacks and baseline hash. SOURCE-PACKET.json pins all top-level source, preparation and review-inventory files and is immediately source-verified without queue/run. It supplies no native, budget, retry or controller authority and does not start a reminder.

Offline validation: `python3 -B -m unittest -v test_prepare_reminder` passes7 tests. They cover missing actual receipt refusal before probes, source-only default, byte-identical originals, valid synthetic receipt/healthy/cadence DATA binding, independent hold/birth/lock/ancestry/quota/heartbeat/cap refusals and the unchanged source-only verifier against an in-memory packet. No test invokes a real lease/RPC/queue/runtime. The unchanged test_reminder.py is copied but its temporary queue-integration run() was deliberately not executed under this task's no-queue scope.

Root interface after campaign restart:

1. Confirm Root environment CODEX_THREAD_ID is01a18ac2-f20f-7992-828e-cd269dff983f and the new campaign's actual receipts are healthy. From this directory run `python3 -B prepare_reminder.py --prepare`. It performs observations and immutable source preparation only.
2. Independently review the emitted SOURCE-PACKET hash, CONFIG, PREPARATION-OBSERVATIONS and predecessor snapshots. Source verification is `python3 -B foreground_reminder.py --source-sha256 <SOURCE-PACKET sha256>`; it does not queue.
3. Root owns any explicit activation after review: `taskset -c 0 python3 -B foreground_reminder.py --source-sha256 <same reviewed digest> --run`. Existing runtime requires ordinary UID1000/CPU0 and refuses retained reminder status. Keep process supervision and actual birth/lease/readback evidence under Root ownership. No activation is performed by this task/helper.

Stop and preserve evidence on a new mismatch or hold; never reset status/cadence or retry an uncertain queue. This helper changes no campaign, account, ownership, allowance, physical admission or foreground-control authority.
