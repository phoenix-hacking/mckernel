# Independent actual C/Rust mutation result and integration decision

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: PASS_FINITE_ACTUAL_C_RUST_SCHEDULER_MUTATION_PARITY accepted for the
reviewed sixteen-case host helper boundary. The dispatcher may stage/integrate
the reviewed mutation-only two-file hunk after exact preimage reconciliation.
If joining with the separately accepted retained-reference caller hunk, bind and
review the actual combined source before treating the combination as accepted
or using it for subsequent production validation. This report does not claim
the still-unreviewed combined artifact has passed compilation or execution.

The actual output contains exactly eighteen lines: actual C layout, sixteen
independent successful case comparisons and the exact9success/7EINVAL summary.
Observed layout: struct thread5568bytes/alignment64; sched_param4bytes/alignment4;
priority offset0; thread sched_param4348; thread policy4344. Every expected
NORMAL/BATCH/IDLE/FIFO/RR boundary and permissive internal DEADLINE/unknown case
matches both actual bodies, the independent expected result and complete target/
source/canary bytes. This is host C/Rust helper equivalence under the frozen
fixture types/config, not a whole production ABI or native scheduler observation.

All four command rows exited0: Rust object PID2378287/start34852286; C object
PID2378294/start34852291; host link PID2378297/start34852300; sixteen-case binary
PID2378300/start34852304. Every row has direct join, absent group, closed streams,
empty stderr and no timeout, unexpected member, capture or retirement error.
Outer PID2378286/start34852276 exited0 in0.3501210280228406s with persisted
started/direct-wait/direct-join/whole evidence and matching positive closure;
outer stderr is empty. All ten retained inner/outer raw stream sizes and SHA256
values independently match their records.

The root grant binds the approved corrected proposal/review and CPU6/one job,
UID/GID1000 inherited limits AS1GiB/CPU30s/FSIZE32MiB/NOFILE256/CORE0,28s driver
and35s outer capture. MemAvailable28,372,074,496bytes exceeds2GiB. Host available
42,740,318,208 exceeds17,850,957,824 required; scratch14,146,371,584 exceeds
13,555,990,528. These are the mandatory floors PLUS640MiB root growth reserves,
not merely the runner's weaker post-command16MiB expectation. Dispatcher reports
CPU6 released immediately after positive closure; this review grants no lease.

Exact accepted result references:

- check-1/result.json: `9caec596dc4673fa769a5deb25dc2df497dda8a8dcb165cebeed07357b628610`
- outer-capture-1/grant.json: `1fe0fde4fa8738505f9597c4ac0e759c715e00299372b2bef23443299cb4f761`
- outer-capture-1/whole.json: `955c6c6d794e4485a7349d5111115906aa4e616c214a30e6ef726add9d253632`
- check-1/actual-16-cases/stdout: `2765c69b2ab1c56b597ab8059d9582bcda4f354f7d6008b5dc145f582199b87c`

The first failed fixture source/objects/link diagnostic/closed captures remain
immutable and distinguishable from this sole successful bounded correction.
The correction selected genuine host memset only at fixture initialization;
neither mutation body, validator, production header/type nor oracle changed.
The family has one original failure and one successful bounded correction; no
additional run is needed for this finite acceptance.

The separately accepted seven-case caller result remains identified by review
SHA `23c21b59ceccc827c1187aeb967c49547f9f2f29a56783a42a1267b1c6756a57`.
Neither result supplies numeric host-owner incarnation qualification, scheduler
field locking/publication, real target-exit lifecycle acceptance, guarded complete
C/fallback/Rust-crate/ABI compilation, final unique default consumer, matching
native execution or compute-C retirement. Those gates remain open; current160
and its evidence are not retroactively changed.

Only existing result/capture evidence was read/hashed and this private decision
was written. No fixture replay, compiler, root/guest command, lease, shared-source
integration or Git operation was performed by this reviewer.
