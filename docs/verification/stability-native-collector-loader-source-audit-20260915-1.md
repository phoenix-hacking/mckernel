# Native collector loader-map source audit — 2026-09-15

Status: **SOURCE_FINDINGS_ONLY**. This bounded read-only M02-C audit neither
freezes an ABI nor authorizes implementation or native execution.

No authoritative native loader/DSO or transient-map producer exists in the
reviewed sources. `host-kernel/native-rust/application_image.rs` (SHA256
`25b7810c273c9f4b5dbff073f54e67db52c69636e63760c7d5f62e471b7a61b2`)
validates caller-supplied load-section descriptors and interpreter alignment but
emits no executed loader-map record. `host-kernel/native-rust/smp_procfs.rs`
(SHA256
`7aba4319fdc6fa76761ca01128c7a7d920c4be85244737167122c914fc1268d5`)
exposes a synthetic maps node, while its published TIDs are mutable numeric
inventory rather than mapping lifetime/ownership evidence.

The compressed `native-application-pager-wip-20260908.json` record (SHA256
`ba5e63b45cd6232fccd8275784104aabddcbefdd843cc72ea909b0d9a867695b`)
shows libc loading through four CREATEs and 473 page reads before the then-failing
zeroing and delegated-munmap paths. It does not establish complete map publication,
release or retirement.

A future structural contract would need source-bound `LOAD_MAP_BEGIN`,
`LOAD_MAP_ROW` and `LOAD_MAP_END` records keyed by application token, guest-thread
generation and loader execution instance. Each row needs typed object identity
(including path/file hash), start/end, file offset, protections, load/interpreter
role, producer sequence/timestamp/clock, owner/generation and immutable raw-event
offset/hash. Complete scoped snapshots, explicit capture-end, and transient map
create/remove events must make omission, overlap, loss and unattributed rows hard
failures. This proposal is not frozen.

Authoritative executed hooks/encoding, complete transient observation, stable
thread birth identity, stream/no-loss attribution and qualified ownership/clock
guarantees remain blockers. No build, runtime, application acceptance or
production gate credit follows.
