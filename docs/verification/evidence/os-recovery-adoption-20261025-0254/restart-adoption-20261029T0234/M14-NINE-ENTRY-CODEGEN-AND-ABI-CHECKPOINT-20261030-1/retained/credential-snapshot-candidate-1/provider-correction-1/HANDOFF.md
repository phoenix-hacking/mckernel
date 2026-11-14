Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Permissions remain danger-full-access/approval never, confirmed for this thread.
Only this private credential packet was written. No workloads, model tests,
compiler, native, privileged or controller operation was launched. Other writers,
held work and all accepted source/build evidence remain preserved.

This is an incremental source correction from the actual-crate module702d402f
which passed frontend0001 (metadataf182bc70) and diagnostic object4ae. Those
results remain evidence for their exact predecessor, not this changed source.
The same existing f03_credential_snapshot_typecheck include can bind this module;
copy the new file beside syscall_policy.rs and apply the incremental patch only
if composing from the predecessor. No C/default/runtime selector changes.

Implemented independent bodies:

* `consume_snapshot` reuses the existing by-value snapshot and actual locked
  four-field commit. A FAILED snapshot query now retains the original real owner
  as UNKNOWN and returns its exact negative status: the query's known failure
  cannot prove that a preceding host credential mutation had no effect. The
  predecessor could finish/release that owner before stale-cache reconciliation.
* `forward_refresh_ordinary` captures/pins the process, obtains the declared real
  owner before invoking the existing forwarding bridge, and shares the original
  successful snapshot/commit body. Negative results skip snapshot/commit,
  preserve the exact CLong return and retain the owner as UNKNOWN. The scalar
  forwarding ABI cannot prove which negative result is a completed host errno
  versus transport uncertainty. Positive nonzero ordinary-setter results also
  retain the owner; only zero reaches snapshot. This helper is inapplicable to
  setfsuid/setfsgid, which return the previous ID.
* Mangled checked uid/gid setter candidates bind the actual current-thread,
  SYS_SETRESUID/GID constants, X86UserContext and existing forwarding bridge.
  These demonstrate checked error propagation without replacing live syscall
  entries or pretending original void callbacks can return errno.

The real begin/snapshot/finish provider stays blocked. No provider implementation,
token table, pretend mutex, new ACK, host ABI or response-lifetime claim was added.
`PROVIDER-CONTRACT.json` records literal prototypes and exact source gaps.

Exact existing route inspected:

1. Guest getcred and its body use caller stack scratch, page-select an eight-int
   span and issue existing setfsuid/mode1. The body ignores do_syscall's result.
2. Rust/C mcexec credential-read bridges discard the GET_CRED ioctl result;
   act_setfsuid submits zero. That cannot prove a fully initialized response.
3. Existing mcctrl Rust GET_CRED writes eight ints via supplied physical mapping
   and current-credential callbacks, but that helper does not prove the original
   task/MM, mapping and offload response lifetimes or the selected native object.
4. Qualified native Rust Mailbox/Response retain real request/response ownership,
   but no current credential state/transition exists; its generic return_value
   does not require an eight-ID write before publishing a credential response.
   The memory adapter's generic payload claim is not a typed credential outcome.

A real provider requires a reviewed credential-capable original response owner,
live exact-guest error contract, typed write/partial/unknown completion and actual
setter-wide serialization. It must copy all eight values into the by-value reply
while its real immutable snapshot storage is owned, and retain that original
storage/gate/process pin for uncertainty. Snapshot failure after host mutation
requires real reconciliation; returning an errno is not a host rollback. Those
interfaces are absent from the inspected existing route, and this assignment
does not authorize inventing a new transport/ACK or porting host/M15 code.

The next executable check belongs to Root: the affected whole-Rust frontend
under the existing private cfg, reusing unaffected inputs. `MANIFEST.json` binds
the candidate and source evidence. This packet supplies no new test/model and
claims no additional C-function retirement, link, production or native credit.
