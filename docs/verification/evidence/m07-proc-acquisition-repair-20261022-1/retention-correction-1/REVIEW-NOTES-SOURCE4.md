Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is the one coherent bounded retention-integration correction to blocked
source3. Source3 and its packet remain unchanged. Final source4 is the additive
`coupled/bound-terminal-proc-v2-source-4/` directory. No root, container, guest,
Git or shared-source mutation was performed. The original proc.v2 producer,
eight-sweep/five-second acquisition, two complete sweeps, cumulative ownership
and publisher decisions, boot/root/caller checks and strict oracles are unchanged.

The process-report count limit is now sixteen. The actual normal fresh
Transaction.run path requires nine census acquisitions: one preflight, one
post-lock, one before container removal, one after removal, two for each of the
two ownership records, and one final check. The former count-eight limit could
therefore refuse after both releases. The original 16MiB aggregate bound and
4MiB reservation plus 1024-byte margin remain enforced before each acquisition.
Raising the count limit does not disable an aggregate refusal or permit an
oversized report. A normal maximum-count Linux profile (4096 PIDs, ten-digit
PID/parent fields, maximum u64 starttime, two complete sweeps and no publishers)
was supplied to the actual producer and then through all nine real consumer
checks. Its largest canonical report is 1,142,952 bytes; nine retained reports
are 10,286,578 bytes. Eight reports plus the 4MiB reserve remain below 16MiB.
Nine arbitrary maximum 4MiB reports cannot fit 16MiB and are not claimed to fit.
Extra churn/failed sweeps can still cause a strict aggregate refusal; after
mutation that correctly enters quarantine with the already retained evidence.

The full reports are now included in both the durable quarantine marker and
its existing QUARANTINED_ROOT_LOCK_HELD capture status before the nonreturning
hold. A quarantine-write failure still attempts the status capture and reaches
the original hold. No exception path was added around or after that hold, and
original root-lock/signal restoration rules remain unchanged. Recovery's body
check permits exactly these two process_reports dictionary additions, verifies
their values are the actual PROCESS_REPORTS variable, then compares all remaining
AST structure to the accepted original. Generated source pins are coupled.

The retained serialized collection stays below 16MiB. Default JSON spacing adds
at most one space per comma or colon, bounded by half the compact JSON size;
thus the report portion remains below 24MiB even at the aggregate bound. The
preflight's fixed envelope/limited trace and completed-child diagnostics retain
headroom under its 32MiB capture cap; cleanup/postjoin use the existing 128MiB
critical capture. Formal application stdout/stderr assertions are unchanged.

Verification uses the reviewed CPU7, 1GiB AS, 20 CPU-second and 30 wall-second
ordinary profile. Four new full-transaction tests execute actual main, recover,
Transaction.run, preflight, census, process_absent, embedded producer and report
validator with root/filesystem/container mutations supplied as in-memory
boundaries. They verify nine acquisitions reach PASS_EXECUTED with all nine
journal events and normal close/unmask; the maximum normal census geometry fits;
a structured refusal at the ninth check persists all nine reports and never
completes; and quarantine persistence failure still holds the root lock and
signal mask. The actual nonreturning quarantine_wait function blocks on explicit
test-time boundaries in daemon test threads. Assertions observe the hold and
verify close/unmask were not called. Those threads disappear only when the
bounded unprivileged test process exits; no real ownership lock is involved.

All fifteen proc/consumer regression tests pass, including finite count and
aggregate cap refusal before another acquisition. Actual generated observer
main, summary and finite postjoin integration passes its positive case and
retained-publisher refusal case. The generated body checker passes its original
49 targeted refusals. No physical/native/application acceptance follows.

Two test-fixture failures are preserved rather than hidden. The in-memory
append boundary initially omitted the original append method's mutation of its
passed row list; one correction restored that behavior and the full normal
journal passes. The first maximum-count fixture included the known forbidden
owner PID999 and correctly refused; one correction excluded it, followed by the
more conservative maximum-width PID geometry. These were fixture defects; the
corrected source4 engine did not fail either transaction test family.

Minimal next steps remain a focused independent review of this exact source4
freeze, dispatcher publication/fetched-blob binding, and separately reviewed
fresh observer/readback and root execution releases. The source-only nonce is
`m07-sigill-pass-image-observation-proc-acquisition-4`; pending operations grant
no execution. Do not reuse source3/v1 releases or relabel old observer evidence.
Old raw archives require an explicit independently bound reuse decision; none
is supplied here. Reserve576 remains pending; Scratch21 and mutex27:4 remain.
