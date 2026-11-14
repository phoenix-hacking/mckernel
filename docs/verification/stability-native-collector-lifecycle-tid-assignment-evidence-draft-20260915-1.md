# Native collector lifecycle TID-assignment evidence draft 1

Date: 2026-09-15
Task: `M02-C-lifecycle-tid-assignment-evidence`
Disposition: `EVIDENCE_DRAFT_ONLY`

This source-bound audit separates native implementation behavior from missing
model policy. It authorizes no implementation, compilation, model execution,
guest execution or acceptance. Bind all conclusions to these exact inputs:

| Input | SHA256 |
| --- | --- |
| `kernel/rust/host_helpers.rs` | `79ec492e531d9793206cd9ebc84482ab695fcfdc284675492d81ee5a072eeaac` |
| `kernel/host_helpers.c` | `ab82fcb8ca66f37620f960ce3a63b128d0ddb6561d6b458e7751852e22c521ef` |
| `kernel/host.c` | `3a1ed8ab20ef12a48cb5f9b578f33c83d465c637cf0ecf66a6c597a4cef066b3` |
| `kernel/include/host_helpers.h` | `24eb8e76a71e81e70d01ab20a96334f7deb8a07bd9839bac5a45c0e01cee30a4` |
| `kernel/syscall.c` | `ac80bb17e41979652e3dd90f8a94d205c28853cd6171975fcf4349f3d301ab58` |
| `kernel/rust/process_helpers.rs` | `b3a28ea8b0cd2594305644c224ae718eac384c0709305da315a6b8fd1285d00b` |
| `kernel/process_helpers.c` | `c444c9c911b3dd231e6c8d8ae544c82f5d69893506f99bcff4be4ae3216a34f5` |
| `kernel/process.c` | `6480b1ab121acf17610495682cd9e58cba774427de9695b1ce8dd65a9bc07cb2` |
| `kernel/include/process.h` | `907391bd99a38b48be54ff6700f1ca12143e5a9bfabf4826b6f09ab2b842bc6c` |

Retained literal-review authorities are:

- abort review SHA256 `3c49e61a21f52a117f0a190211d3de80ab9f962a2c2cc9835a9b4e84f5994370`;
- multithread review SHA256 `d9103e9a27a5869274459cb865ca5b7a918a82b328a7d4707f785d8149f96d70`;
- semantic-negative review SHA256 `f7a5d5b1693f9ede901b4058416595bc06e0f01c7a8cf523df546f4a0fe42046`.

The retained START protocol archive SHA256 is
`c40afc2710b40455519ba8116ea89195b5be9fa74fcc9d04db3d022837acb62d`.
It contains prepared-cleanup ownership and wire-matching results, not a
TID-assignment phase/reassignment matrix.

## Enforced native paths

The Rust native scheduling bridge at `host_helpers.rs:5869` reaches
`host_schedule_process_request_result` near line 2840. That helper checks required
callbacks, nonnull thread/process objects and CPU availability. Near line 2912 it
assigns PID as TID, changes running statuses, chains objects and queues the thread.
The assignment adapter near line 1129 checks callback presence only; its raw
bridge near line 5576 writes `Thread.tid` directly.

The matching C helper begins near `kernel/host_helpers.c:1546`, assigns near line
1608, and is called near `kernel/host.c:1397`. The callback typedef and helper
prototype are near `kernel/include/host_helpers.h:136` and line 441; the Rust
callback type is near line 408. `kernel/include/process.h` stores the numeric TID
as signed `int` near its lines 449 and 628.

`do_fork` near `kernel/syscall.c:7434` holds the process-threads writer lock while
obtaining the TID table and reserving an empty slot with pointer compare-exchange.
Near line 7473 it resets the cloned thread's TID to zero; near 7481 it copies the
reserved slot TID. Exhaustion rolls back with `-ENOMEM`. Non-`CLONE_VM` assigns
the host PID near line 7520. Thread chaining near 7607 precedes fallible host-clone
completion near 7651 and `runq_add_thread` near 7670; rollback near 7684–7708
releases acquired resources through `release_thread`.

Destruction near `kernel/rust/process_helpers.rs:10857` serializes thread-list and
TID changes. `process_destroy_thread_tid_action_result` near 9270 distinguishes
main, nonmain and UTI replacement. `process_release_tid_body_result` near 10623
finds the owning slot, and `process_tid_release_slot_result` near 8434 clears it.
Numeric slot reuse is therefore distinct from retained seven-component model
identity.

## Predicate evidence and limits

| Input condition | Enforced behavior | Missing model policy |
| --- | --- | --- |
| Unassigned | Fresh-fork setup explicitly writes TID zero before reservation. | Scheduling assumes a valid prepared object; it does not require the old TID to be zero. |
| Same assigned TID | Scheduling overwrites without comparing the old value. | No idempotence or error result follows. |
| Different assigned TID | The setter has no old-value comparison. | Caller freshness/ownership is a precondition, not a local guard or permission for reassignment. |
| Active alias | Fork excludes occupied slots under lock and compare-exchange. | It does not prove numeric uniqueness across duplicate table entries; scheduling performs no alias lookup. |
| Retired alias | A released nonmain slot becomes reusable; main and UTI handling differ. | There is no seven-component identity predicate or model result code. |
| Wrong phase | Fork operates on a newly cloned object; scheduling/setters have no lifecycle-phase guard. | Absence of a guard is not permission to call repeatedly on stale pointers. |

## Retained literal scope

`assigned-tid-abort` has an Allocated/E/refs-one thread whose TID changes from
zero to 200 with literal result `OK`. `active-tid-alias` produces `IDENTITY` for
`T_ALLOC`, not for `TID_ASSIGN`. `tid-reuse` has a new `T_ALLOC` reuse numeric TID
201 only after the old full identity is retired and retained separately. Their
review manifests explicitly establish literal-only scope and no model execution.

The following remain unresolved and prohibit freezing the `TID_ASSIGN` family:
lifecycle phase/domain permission; same/different reassignment; exact alias
classification; reference and authority interaction; and `CLOSED` precedence.
Do not extrapolate T_ALLOC literals, native errno values, absent guards or caller
preconditions into those cells. A separately reviewed contract decision is still
required before transition vectors or model implementation can be released.
