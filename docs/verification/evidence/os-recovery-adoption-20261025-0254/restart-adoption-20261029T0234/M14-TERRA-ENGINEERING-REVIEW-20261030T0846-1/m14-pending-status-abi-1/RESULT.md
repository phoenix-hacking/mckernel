# M14 status ABI and cross-kernel writer dependency

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source inspection only, no candidate execution or native/provider operation.

## Input binding

Selected guest candidate `/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src`:
`kernel/rust/abi.rs` SHA256 `ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e`;
`kernel/rust/sched_helpers.rs` `c4e6153bef33ec018d2efc88c93854a4dc351f78c901ed3cb25f73524d7c0020`;
`kernel/syscall.c` `4af4524be701ecdbaae09fba906c99bd065364c4caefdcf007820f463773eaf4`.
Host source from `/home/holden/mckernel` (source availability only; its selection in the qualified artifact is not established here): `executer/kernel/mcctrl/futex.c` SHA256 `776d246c43d27965b3e3843fb7c8c415ba9220e5e76ff66f22dfa6cf6de56259`; `executer/kernel/mcctrl/rust/mcctrl_helpers.rs` `abc99c0e160d3a8aa1aa182f37f297cf3827f86faaac559117ae4df3197e9d14`; `executer/kernel/mcctrl/control.c` `00d83f9ad7cf6c7bd263a33933aa3f5b89e4e399c2245b86ff90be87d1be3221`.

## Actual representation and accesses

Guest Rust `abi.rs:1543-1549` has a `repr(C)` Thread whose status is `CInt`; `:2357-2364` assert size 5568, alignment 64 and status offset 4184. These facts establish layout, not permission to mix conflicting atomic and non-atomic accesses or pack a generation into status. The original numeric PS_* flags have actual readers on both sides.

The selected guest `sched_helpers.rs:5281-5289` performs an AtomicI32 swap for the futex interruptible transition, whereas `:5312-5326` finishes with a volatile read and write, and `:3248-3275` performs its wakeup status operation under runq lock after releasing process update lock. Stop paths and their update-lock exceptions are bound in the earlier `m14-pending-status-revalidation-1/DESIGN.md`. An atomic load by the setter alone does not protect the subsequent slot commit from a status change and does not detect a stopped-running-stopped transition. An adjacent version cannot track writers that do not participate.

The guest publishes the address of the same status field to the host as `uti_info->status_pa` in `kernel/syscall.c:28949`, and for a futex queue at `sched_helpers.rs:5124`, alongside a runq lock address. The host `control.c:4534-4537` maps the former via `phys_to_virt`; host `futex.c:942-944` maps the latter. The host C fallback `futex.c:1308` exchanges mapped status to PS_INTERRUPTIBLE and `:1344` writes PS_RUNNING on return, without the proposed guest-only pending bucket. Its wakeup at `:1023-1033` reads status and exchanges PS_RUNNING while holding the mapped runq lock. The host Rust alternative `mcctrl_helpers.rs:12445-12468` uses its xchg callback and later `write_volatile` for the wait path, and `:12545-12562` uses runq lock and xchg for wakeup. No host change or M15 conversion is authorized by this analysis.

These are real source paths capable of addressing the exported field; this does not establish that UTI is enabled, the exact host provider selected for the qualified artifact, or that a traced stopped thread can overlap the particular host wait path. Those are separate profile and lifetime questions. Do not infer exclusion from missing proof of overlap.

## Decision and next executable dependency

No ABI-preserving all-reader/writer migration is demonstrated. A guest-only status lock or atomic snapshot cannot bind the host paths above if they are in scope; a status-tag encoding changes the existing shared ABI, and even an atomic status load followed by a slot lock leaves the status change window open. Runq lock is not demonstrated as a universal status lock: guest stop writers and host wait transitions shown above do not take it. No concrete safe pending Rust patch is proposed, and existing staged source and first/second-copy behavior are retained.

The smallest next source-bound prerequisite is to bind the exact qualified host mcctrl artifact's futex provider and UTI enabled profile to these source hashes, then trace whether a live traced thread may own a published `uti_info` or `futex_q` during stop, wait, and teardown, including actual ref/lifetime and ownership. If overlap is impossible, prove the exact transition/barrier excluding it; otherwise the shared protocol must include the real host writer and its lock order. In parallel, enumerate actual selected guest status writers and host-visible status users before proposing a common status epoch/lock. Preserve the established slot-participant and usercopy constraints; finish with independent ownership/ABI review and actual-body regressions. No guest, host module, Docker, privileged, controller or cleanup operation was run.
