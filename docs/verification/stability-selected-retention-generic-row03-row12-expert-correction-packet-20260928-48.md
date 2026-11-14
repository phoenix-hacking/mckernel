# M01-B expert correction packet 48 — coherent Phase-I source repair

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This is a source-design
correction after the authenticated Phase-I handoff failure 47.  It supersedes
no historical evidence and releases no source attempt, staging command,
compilation, test execution, Phase II, guest/native execution, production
gate, application acceptance, or whole-OS acceptance.  A fresh independent
`PASS_PACKET` review of this complete packet is required before a dispatcher
may create the new root described below.

## Authorities, preserved candidate, and scope

Authenticate packet29 and corrections31/34/36/39/42/45, review46 SHA256
`d48f3eb8b978e84389989d9ab89877cf13ddcb77126f0651e488d6dd7fb50825`, and
the following immutable failed attempt as *design input only*:

| item | SHA-256 |
| --- | --- |
| correction45 | `df3c3132504f7f06543035d41ff0961a9c8eb13b762b0799b9a17ee1efd649ee` |
| attempt45 root | `/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-directed-implementation-packet-20260928-45` |
| `phase-i-handoff.json` | `db97372717f50f7dd8b6eec67755b3b20fa58736da7d442e4393f27bb1eb3b0b` |
| mode2 `adapter.rs` / `runner.rs` / `record.json` | `682c487da179523f73ed54a1f514d94cb92e3a32166ad1e2717b7a37a52fba8a` / `147a18ab05ff9fcc01848147ca4030868180411270ba559517e209f8bde71a2a` / `5f94f9f6c3d119134dd9f8efaefac844230986ff16c6d0d9009dffd3e583e593` |
| mode3 `adapter.rs` / `runner.rs` / `record.json` | `d8cc102185b7dedb2456f7d64c3e83a590a8ddce58a22da7586ffebec42b2690` / `92b79eb6c4a651a1b104ad2e5f80d804a3cea00ac3b7a542e946e65927982dec` / `9552d95798832692ab472017c2fe6562ba22d3ce89b522ddddfa479f24b871fd` |
| mode2 staged application/mailbox/phase | `9121342e2f9ce24be258633c6dd2d4914a096f731b2c05e46d0efa7ffee8c449` / `d0f56c14a4873e1b048666f81b938b462deb6f496f812d78f1ab426e69651b8f` / `66170d07b23daa0b9e84e149afe76255502eff581cb397bd74ce12f3b056a20c` |
| mode3 staged application/mailbox/phase | `9121342e2f9ce24be258633c6dd2d4914a096f731b2c05e46d0efa7ffee8c449` / `578eb890846956460371d9ca0b3fe68defcef83783b23ae5f4de8d1854719865` / `d96fa79eaf6558acb2b6b3bae8bcb6834eff8a760e7281b9f309e19fddec005f` |
| archive45 | `e32fa7d1bacbbab76473612fcbcf28dad0052b90d4b283045d216ada19368b70` |
| failure review47 | `8c4810ac30813dd16781b7d18e31474486a83b5cfe4945de25fa67bb896ceabf` |

The review47 `FAIL_HANDOFF` is authoritative: its five findings are not
partial successes and no attempt45 byte may be edited, reused as an output, or
promoted.  The full 51-member mode-specific authority, source-map, stager,
manifest, failure preservation, independent-mode ownership, handoff schema,
and correction42 post-store-hook requirements remain normative.

One future Phase-I owner may use the currently absent root
`/home/holden/mckernel-work/scratch/m01b-generic-row03-row12-expert-correction-packet-20260928-48`.
It must recheck absence and canonicality immediately before creation.  It must
stage mode2 from correction45's exact 51-member mode2 authority and mode3 from
the independently authenticated 51-member mode3 authority.  This paragraph is
not a release to invoke the stager.

## Exact write boundary and compatibility repair

The inherited Phase-I tree/layout and 327-file accounting apply.  Apart from
the inherited stager-created paths, the candidate owner may change only these
regular files under **each** mode root:

```text
adapter.rs
runner.rs
source/application_syscall.rs
source/smp_application_syscall.rs
source/stability_phase.rs
```

No production source outside those three staged source files, no template,
stager, source authority, evidence record, or sibling mode path is writable.
Each changed module must be independently authored in its own mode and retain
the correction39 regular-file/link-count/no-cross-mode restrictions.  `runner`
and adapter code remain `#![cfg(test)]`; every new source hook is
module-local `#[cfg(test)]` and must erase from the `cfg(not(test))` source
path.  Do not add a test-only mutation of production state other than the
strict pristine arm described below.

`runner.rs` must no longer re-export `std::vec::Vec` as the kernel prelude
`Vec`.  It must instead provide a local generic wrapper (with `Deref` and
`DerefMut` to `std::vec::Vec<T>`, `Default`, and the ordinary iterator/index
behaviour the five loaded modules actually use) whose exact fallible API is:

```rust
pub fn with_capacity(capacity: usize, _flags: ()) -> Result<Self, ()>;
pub fn push(&mut self, value: T, _flags: ()) -> Result<(), ()>;
```

The implementation may reserve/push the std backing and map allocation failure
to `Err(())`; it must not replace any staged two-argument call, erase a
`map_err(|_| -12)?`, make allocation infallible at the caller, or alter the
actual `smp_application_syscall.rs` method bytes merely to suit std.  Its
`prelude` exports that wrapper as `Vec`, `GFP_KERNEL: ()`, and only the
minimal traits/types required by the five exact staged modules.  Static source
audit must find the two real call forms at mailbox construction and slot
initialisation: `Vec::with_capacity(CAPACITY, GFP_KERNEL)` and
`push(..., GFP_KERNEL)`, with their existing error propagation intact.

## Guarded retained-memory fixture and observation model

Replace the attempt45 adapter coherently in each mode.  `AlignedBacking` stays
`#[repr(align(8))]` and owns exactly `[u8; 56]`; `TestResponseMemory` retains
the sole `Option<Box<AlignedBacking>>` and an `Arc<Ledger>`.  Its response
span is exactly bytes `[8,48)` of that allocation: non-null, eight-byte
aligned, 40 bytes long, and its checked end must equal start plus 40.  Its
physical identity remains exactly `0x1000..0x1028`, and `verification_owner()`
returns exactly the inherited Claim (`os=1`, `generation=1`, response index
0, serial `Some(1)`, physical `0x1000`, end `0x1028`, payload `None`).

At construction, before any response is admitted, record immutable fixture
metadata in the ledger: allocation byte length/alignment, span offset/length,
checked start/end, physical start/end, and the Claim.  Assert it once before
admission and again immediately before `return_value`; compare metadata and
Claim values, not backing contents.  `address(&mut self)` may record an
`Address` event/counter and call the existing `stability_observer::address`
with that exact Claim **before** final publication.  It must reject a second
live memory owner/alias and never observe the backing after release.  The
expected exact address delta per successful row is two: `Response::from_memory`
and `Completion::publish`; after the `StatusStore` event, address delta,
post-release address counter, and duplicate-release counter all remain zero.

The retained `Ledger` owns a `Mutex<State>` with fallible-compatible deferred,
quarantine, event, and counter storage.  It records at least construction,
preparation baseline, address, status-store, send, release, deferred insertion,
finished drop, unfinished drop, quarantine insertion, and deallocation.  The
metadata hook remains the one correction42 hook immediately after the actual
Release `AtomicU64` store and immediately before consuming `release`; it
records `StatusStore` only and reads no backing/claim/span/address/published
byte.  `release(self)` takes the sole Box under the mutex, records release and
deferred insertion, then unlocks; its `Drop` records only finished destruction.
Unfinished `Drop` transfers its sole Box to quarantine under the mutex.  Each
drain moves the entire selected queue out under lock, unlocks, drops the batch,
then records exactly one deallocation per dropped Box.  No destructor or drain
may access the backing bytes, span, or guest address.

The `publish` closure records `Send` only if called and preserves the supplied
packet check; neither row fabricates a send.  Snapshot helpers must copy
ledger/phase/observer counters while the object remains live.  They must make
no pointer/backing read after final status publication.  A snapshot includes
owner equality, phase stage/invalid/accepted-sequence/release-commit state,
address/send/release/drop/queue/deallocation counters, and observer release,
after-release, and duplicate-release counters.

## Real mailbox and phase scenarios

The mode-local `admitted()` helper must use only the existing actual chain:
`Mailbox::new -> open_worker(71) -> admit(request, move |_| Ok(memory)) ->
reserve -> copied -> verification_read16(Some(70), 42) -> observer::select`.
It returns the real selection and exact Claim; assert selection and Claim match
all owner fields (including serial/index/physical/end), worker, PID, CPU,
requester and delivery identity.  It must not construct a Request, Selection,
Completion, worker, or phase result by hand beyond packet29's exact request
bytes and the actual `TestResponseMemory` supplied to `admit`.

Replace the broad direct state writer
`verification_test_set_state(stage, commits, invalid)` with a narrowly named
`#[cfg(test)] verification_test_arm_pristine() -> Result<(), i32>`.  It may
perform exactly one compare-exchange from initially zero `STAGE` to `ARMED`,
only after asserting all related phase counters/timer/invalid state are still
pristine; it cannot set accepted, emitting, held, released, commit, timer, or
invalid state.  Each row executes in a separate process in any later execution
packet, so it starts from that pristine state.  No row may write stage, commit,
or invalid scalars directly after `return_value`.

For both rows, call `verification_test_arm_pristine`, then actual
`return_value(worker, serial, 0, 16, |_| Ok(()))`.  Assert the real selected
path produces stage `ACCEPTED_PENDING` (2), invalid 0, accepted sequence 0,
no release commit, live matching owner, and the first
`verification_phase_completion(selection)` outcome `present=true` with the
actual unchanged `publication_since` value.  That is the preparation baseline:
record it only after this accepted-stage-2 assertion, never before
`return_value`.

Row03 then calls the actual mailbox `publish(0, ...)` and requires exactly
`Err(-11)`.  It asserts stage 2, invalid 0, commit count 0, owner still live,
completion still present with the same status, address delta 1 (the
construction-time `from_memory` address only), send/status/release/deferred/
finished-drop/unfinished-drop/quarantine/deallocation deltas all zero, and no
observer release/after-release/duplicate-release.  It must call actual
`close_worker(worker)` (requiring its retained cancellation rejection and
mailbox quarantine), then drop/destroy the mailbox before any quarantine drain.
Only after destruction may it snapshot exactly one `UnfinishedDrop` and one
`QuarantineInsertion`, drain quarantine, and assert exactly one
`Deallocation`, no deferred or finished-drop event, no remaining fixture-held
backing owner, and unchanged invalid/commit/send/address/post-release counters.

Row12, after the common accepted-stage-2 baseline, obtains a real permit and
calls the actual transitions in this order with one bounded future timer:
`begin_emitting(timer)`, `commit_held(2, timer)`, `claim_release()`, and
`commit_release(timer)`.  It asserts each Result, stage sequence 2→4→5→3,
accepted sequence 2, invalid 0, exactly one release commit, and the existing
`before_selected_send()` Released outcome.  It may not use a direct setter or
claim release after publication.  Then actual `publish(0, ...)` must return
`Ok(true)` and the send closure must have zero invocations because this exact
request has wake `None`.  Before draining it asserts exactly one status store,
release, deferred insertion, finished drop and the second address call; zero
send, unfinished-drop, quarantine, deallocation, post-release-address,
observer-after-release, and duplicate-release; the event order is
construction, accepted-stage-2 baseline, address(es), status store, release,
deferred insertion, finished drop.  The second required
`verification_phase_completion(selection)` outcome is absent after publication.
After deferred drain it asserts exactly one deallocation and all other counters
remain unchanged.  It must not read response backing/pointer data after status
publication.

## Source-only acceptance and stops

Before handoff, the owner may run only static file/hash inspection,
byte-reading `ast.parse` for Python helpers, exact source-text/AST structural
checks, inverse-diff restoration checks, no-bytecode audit, and
`git diff --check`.  It must not invoke the stager, compiler, test runner,
interpreter import, binary, guest, container, root/sudo, network, or Phase II.
The static checker must reject absent/extra paths; byte/hash or mode drift;
cross-mode dependency; std-Vec aliasing; altered non-test source behaviour;
direct post-arm scalar stores; any absent actual mailbox/phase call; wrong
baseline ordering; missing owner/invalid/commit/send/address/teardown/
post-drain assertion; drain before mailbox destruction in row03; incorrect
phase-completion presence; missing exact geometry/Claim checks; pointer/backing
read after status store; lock-held drop; non-unique/misplaced status hook; or
failed `cfg(not(test))` erasure/inverse.

On the first mismatch, write only correction31's six-field
`phase-i-failure.txt`, preserve the partial fresh root, archive it through the
dispatcher, and stop.  Do not repair, retry, start Phase II, or claim credit.
A successful static handoff is still only `PASS_PHASE_I`; a new independent
handoff review must approve the actual candidate before any separate compiled
microtest packet can be considered.

## Remaining risks

This packet establishes a source-feasible correction only.  The fallible
compatibility wrapper, the test-only pristine-arm boundary, and the exact
drop/phase observations require independent source review and later isolated
compilation/execution evidence.  It does not prove the loaded kernel modules
compile together, that static process isolation is enforced, or that any
native/guest/application/production contract passes.
