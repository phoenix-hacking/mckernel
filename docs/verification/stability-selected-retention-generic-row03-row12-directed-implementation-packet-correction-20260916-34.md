# M01-B packet29 correction34 — API, handoff, and source-integrity repair

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This additive correction replaces
neither packet29 nor correction31 and releases no implementation, compilation,
execution, runtime, guest, native, production-gate, application, or whole-OS
acceptance. It authorizes one fresh implementation attempt only after a new
independent `PASS_PACKET` review.

## Pins and preserved failures

Authenticate fetched checkpoint `353dbeb56a5ca7590516d6d9662fe36b73cde68d`,
packet29 `7fa429e0d3e4a960d514296b7cd9fcae71a3e82285efd7513420b9837043e753`,
correction31 `d8bb9c2fd55b8507136cd992d314d5f87ab677fe107e374192678c4f713575a9`,
PASS review32 `e24f4229de75a6d24ceac1b3dcf6f5e2c42718d0d0ea9b6a23a7fbd30507f2b1`,
failed archive33 `02a538557b4b080df4468d6871e5263ac685fcc337f358c16ccee15e0dc823fa`,
source-stage failure33 `5e55b71461d1102f8aec048c6e36cbcdc9bf0119cf4aed6ee922f93ee2b420c8`,
and review33 `a026d76626e14bf43f6cb1d46cdd995a38a9b8af45ecd20f4276559c56422d1e`.
Root29 and its archive remain immutable. Correction31's early-failure rule is
unchanged: before handoff, only `<root>/phase-i-failure.txt` may be created,
with its six exact LF-terminated fields, then preserve and stop.

## Fresh root and revised success accounting

The implementation owner must choose a newly absent root whose name is not
root29 or any prior attempt, and record its exact path in the handoff. Packet29
Phase I paths remain the only implementation paths. Add one explicitly
allowlisted root artifact: `<root>/phase-i-handoff.json`. A successful root is
therefore 327 Phase-I regular files (163 per mode plus this artifact), and
completed Phase II is exactly 347 regular files. Phase II binds 346 finalized
files; the handoff manifest itself is externally bound and is not self-hashed.
No Phase II file may exist during Phase I.

`phase-i-handoff.json` exact schema is:

```json
{"schema_version":1,"record_kind":"m01b_phase_i_handoff","status":"PASS_PHASE_I","modes":[{"mode":"mode2","record_sha256":"<64hex>","adapter_sha256":"<64hex>","runner_sha256":"<64hex>","members":[{"name":"<basename>","size":<int>,"sha256":"<64hex>"}]},{"mode":"mode3","record_sha256":"<64hex>","adapter_sha256":"<64hex>","runner_sha256":"<64hex>","members":[{"name":"<basename>","size":<int>,"sha256":"<64hex>"}]}]}
```

Each `members` array has exactly 51 entries, sorted by `name`; mode order is
mode2 then mode3. Serialize UTF-8 with `json.dumps(..., sort_keys=True,
separators=(',', ':')) + '\n'`, no extra keys, and bind the raw bytes and SHA
in dispatcher evidence. The artifact is a handoff record, not an execution
result or acceptance oracle.

## Required source implementation delta

Use the authenticated staged `application_syscall.rs`,
`smp_application_syscall.rs`, `stability_observer.rs`, and `stability_phase.rs`
for each mode. The exact APIs are:

- `application_syscall.rs:35`: `Request::decode(packet: &[u8], cpus: usize) -> Result<Self, i32>`; call it as `application_syscall::Request::decode(&bytes, 1)`.
- `application_syscall.rs:316-327`: `unsafe trait ResponseMemory`; implement `verification_owner(&self) -> Option<Claim>` returning the exact `Some(Claim)`, plus `physical`, `address`, and consuming `unsafe release`.
- `smp_application_syscall.rs:44,61,124-129,212,262`: `Mailbox::new() -> Result<Self>`, `open_worker(&mut self, i32) -> Result<u64>`, `admit(&mut self, Request, claim) -> Result<bool>`, `reserve(&mut self, u64) -> Result<Option<(u64,[u8;80])>>`, and `copied(&mut self, u64, u64, bool) -> Result`. All are mutable mailbox calls; never call them on a worker or invented handle.
- `smp_application_syscall.rs:465-472`: `return_value(&mut self, handle, serial, cpu: i64, value: i64, copy) -> Result`.
- `smp_application_syscall.rs:579-583`: mailbox `publish(&mut self, cpu: i32, send) -> Result<bool>`.
- `smp_application_syscall.rs:708-712,747-760`: `verification_read16(&self, Option<i32>, u64) -> Result<Option<Selection>>`; pass the returned real `Selection` to `stability_observer::select` (observer `:223-244`), never fabricate one.
- `smp_application_syscall.rs:836-839`: phase query takes that `Selection`.
- `stability_phase.rs:98-125,148-207`: use real `accepted_selected`, `before_selected_send`, `begin_emitting`, `commit_held`, `claim_release`, and `commit_release`; test-only setters must drive these transitions, not substitute strings.

`runner.rs` must be a standalone std crate loading the five exact modules
(`application_rpc`, `application_syscall`, `smp_application_syscall`,
`stability_observer`, `stability_phase`) and supply minimal fallible `Vec`,
`kernel::pr_info!`, and positive monotonic-clock compatibility. Inline the
`#[cfg(test)]` mailbox scenarios in staged `smp_application_syscall.rs` without
recursive runner inclusion. Scenarios must construct the exact 128-byte request,
run `Mailbox::new -> open_worker -> admit -> reserve -> copied ->
verification_read16 -> observer::select -> return_value ->
verification_phase_completion -> publish`, and assert real results, Selection/
Claim/address identity, baseline, event order, snapshots before drains, and
row03 quarantine/deallocation and row12 deferred/deallocation outcomes.

`Completion::publish` is at `application_syscall.rs:462-481`; its real status
store is `:478`, and consuming release is `:479`. Insert a module-local
`#[cfg(test)]` metadata hook between those exact operations. The hook records
the actual stored status only. `release` records ownership/release/deferred
events only; it must not fabricate `StatusStore`. All Box transfers occur
under `Mutex`, drain batches move out under lock and drop after unlock, and no
post-publication backing read is allowed.

## Stops and review boundary

Reject fake calls, incompatible receivers, invented Request/Selection/Claim,
missing `Some(Claim)`, omitted compatibility, recursive includes, absent
snapshots/drains/assertions, wrong hook placement, changed non-test bytes,
manifest serialization/count mismatch, unexpected paths, bytecode, or any
failed inverse/hash. On the first failure write only the correction31
`phase-i-failure.txt`, preserve the partial fresh root, and stop without repair,
retry, Phase II, compilation, or execution. Independent review must authenticate
the raw handoff bytes before Phase II is considered.
