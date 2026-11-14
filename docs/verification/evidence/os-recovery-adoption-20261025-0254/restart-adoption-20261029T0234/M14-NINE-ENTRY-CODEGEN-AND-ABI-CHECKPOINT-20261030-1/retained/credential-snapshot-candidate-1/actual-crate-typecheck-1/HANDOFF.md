Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Effective recovered-thread configuration confirmed: danger-full-access, approval
never. This packet writes only within the credential worker's private directory.
No tests, compiler, models, containers, native, root or other workload launched.

Feed `postimage/kernel/rust/f03_credential_snapshot_candidate.rs` beside the
compositor's actual `kernel/rust/syscall_policy.rs`. Apply
`TYPECHECK-WIRING.PRIVATE.patch`, which includes it as a child of syscall_policy
under `--cfg f03_credential_snapshot_typecheck`. No lib.rs, C, default flag or
runtime selector change is required. The cfg leaves both do_setres entries
mangled; the original C symbols remain selected. Preserve other composition
edits when applying the small contextual wiring hunk.

This successor reuses the earlier169-line module. Its concrete ownership
correction passes the initially captured/pinned process directly into the
refresh body, avoiding a second thread.proc lookup before offload. The short
commit uses explicitly typed actual lock_helpers pointers. Compile-time
function-pointer assignments bind actual process hold/release and lock/unlock
prototypes, while const assertions bind both actual lock layouts and C reply
layouts. Imports and types come solely from the actual crate: no synthetic
Process, Thread, lock or owner implementation is supplied.

`ACTUAL-CRATE-CORRECTION.PRIVATE.patch` is incremental from the preserved earlier
module; `MODULE-ADD.PRIVATE.patch` adds the full successor to a composition which
does not yet contain it. Use one, not both. `MANIFEST.json` binds exact source
inputs and outputs. Do not apply the older CREDENTIAL-SNAPSHOT.PRIVATE.patch
for this frontend check: its proposed runtime C selector changes are unnecessary.

Both Rust entry bodies are ready for the actual whole-crate frontend; no
frontend success is claimed before the coordinator's check. Real owner
begin/snapshot/finish/failure symbols intentionally remain unresolved. The
whole-crate metadata/frontend check can typecheck their ABI without a fake
provider; a successful check will not prove an emitted C/Rust call ABI or link.

`per-function-ready-blocked.json` identifies the original setters and helper
callers. Genuine setter-wide serialization must span original host mutation,
snapshot and guest commit; begin cannot merely lock after the host mutation or
reacquire a nonrecursive lock already held by a setter. A host-success/query-
failure outcome needs real reconciliation, and original void callbacks cannot
propagate the checked status. UNKNOWN requires retention of actual independent
storage and process owner; no ACK, native cleanup or host rollback is fabricated.
Those are explicit runtime provider/caller gaps. They do not prevent this
unselected actual-crate source from entering the frontend now.
