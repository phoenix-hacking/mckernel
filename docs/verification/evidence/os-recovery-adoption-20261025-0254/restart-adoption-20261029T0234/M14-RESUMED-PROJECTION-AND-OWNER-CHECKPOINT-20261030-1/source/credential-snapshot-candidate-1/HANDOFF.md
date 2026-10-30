# Private credential snapshot source candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Effective thread permissions confirmed once: danger-full-access, approval never.
Owner writes only this private directory; all other writers and held artifacts
were preserved. No compiler, tests, container, native, privileged, controller,
cleanup or hold retry operation was performed.

The actual119 C preimage and selected align32 syscall_policy.rs are hash-bound
in MANIFEST.json. The existing genuine wrappers' UID indices0..3 and GID
indices4..7 are reused. The older paired credential patch remains NO-GO/held;
its host ABI changes were neither adopted nor replayed.

`CREDENTIAL-SNAPSHOT.PRIVATE.patch` proposes exactly two original C function
selectors and a default-off Rust module. No CMake flag, production default,
source-retirement record or shared compositor file was changed. The canonical
compositor owns any later integration. The new source has not been compiled.

The implementation captures and pins the original process before the offload
adapter, receives an initialized eight-ID reply by value, and uses the real
Rust process update_lock provider for the short four-field commit. It never
reloads thread.proc after offload. No user or external response pointer is
returned to the commit path. Known failed queries and unknown/malformed replies
perform no credential-field writes. This is deferred commit: it never restores
an old snapshot over a later valid credential update, and it never claims to
undo an applied host credential change. UNKNOWN is passed to the real owner
finish interface, whose required behavior is retention, never synthetic ACK.
Failure to finish a known owner cannot become a successful checked result.

This is **not link-ready or selectable**: the genuine process-wide serialized
owner adapter does not exist in this packet. Its unresolved symbols are an
intentional integration dependency, not dummy providers. Before selection:

1. All credential setters, including uid/gid/reuid/regid/resuid/resgid/fsuid/fsgid,
   must participate in one real per-process transaction spanning the original
   host mutation, snapshot query and guest commit. Begin must attach to that
   already-owned operation when invoked from a setter; independently taking a
   nonrecursive lock after host mutation would fail ordering or deadlock. The
   existing wrappers currently forward first and refresh afterward, so those
   caller paths require a reviewed source correction before this can be enabled.
2. The adapter must own actual response/request/mapping storage independently
   of this stack and retain its own process pin. Its returned reply is an ABI
   value copied while the immutable host snapshot owner is live. A real UNKNOWN
   operation cannot retain a pointer into this function's stack or borrow a
   temporary user buffer. Failure-after-effect and uncertain in-flight outcomes
   retain the exact real owner and must be reconciled before releasing its gate.
3. A READY/status0 reply requires all eight original values and real synchronous
   completion/visibility. A zeroed local reply, old host false-zero status, source
   label or mock result does not supply that evidence. No legacy host ABI change
   is proposed here. Failed query after successful host mutation leaves guest
   cached fields stale; deferred commit alone does not reconcile that condition.
4. The original void do_setresuid/do_setresgid ABI cannot return the checked
   refresh status to syscall callers. The unresolved failure hook must have a
   reviewed reconciliation/failure path, or all callers must migrate to a
   checked API with correct original syscall/setfsid return semantics. This
   source does not claim that returning an error undoes the host mutation.
5. Readers needing a coherent four-field snapshot must participate in update_lock;
   short writer locking cannot make current unlocked readers atomic. Original
   field readers and clone/exec initialization must be reconciled by the shared
   ABI/compositor owner; no such shared edit was made here.

`credential-owner-abi.h`, `abi-witness.c` and `abi-witness.rs` supply paired
layout/prototype and actual-process-offset witness source. Static layout alone
does not qualify the by-value C/Rust calling convention; emit and compare both
sides under the selected toolchain before use.

`regression.rs` includes the actual candidate file with synthetic process/lock
providers. Its source covers UID/GID selection, process retarget during offload,
negative/positive/malformed/UNKNOWN results with unchanged fields, and owner
finish failure after commit. No regression was executed. It does not model
native host storage, gate fairness, cancellation or in-flight teardown and cannot
prove the unresolved adapter's contracts.

Two unrelated root70 directories were encountered during the initial bounded
candidate search: UID1000 could not traverse root-owned0700 directories.
`namei -l` established ordinary Unix ownership/mode; no permission change or
elevated read was needed or attempted. Subsequent reads used exact candidate
paths only. Original stop records, held work, scratch21 and native ownership
remain untouched.
