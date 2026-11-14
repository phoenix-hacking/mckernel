# Ptrace wakeup dynamic-debug synchronization — bounded source design

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source review/design only; no implementation, compile, runtime, release or acceptance.
The proposal only makes the one new wakeup descriptor race-free. It preserves the
registry ABI, not a claim that all other descriptors are race-free. Its tests are
future requirements, not executed results.

## Bound inputs

- Candidate `ptrace-free-log-source-1/postimage/kernel/rust/syscall_ptrace_wakeup_logger.rs`: SHA256 `4ef213da88797997bf7d7743d651fda6bfc0a090656eaf24211f522b1400cf61`.
- Main `kernel/rust/debug.rs`: `fed7537d21f5d5fe0fc3ffdb1fe44783f5f9ac13937b3bdbbcc452cc2fa5eb16`.
- Main `kernel/debug.c`: `5896fabfd22da1c023a9b4b9970fe7cfe1524de7bf353383b2dd04ad2b6c1f92`.
- Main `lib/include/ihk/debug.h`: `7315ef758c56c4888242295ed9340b44f649d772b1315502acc49eb6105048dc`.

These hashes identify reviewed files, not an assertion that they are all the
selected integrated image's inputs. Rebind against its actual materialized sources.

## Access inventory and finding

The candidate defines the sole private `WAKEUP_DEBUG` and reads its `line_flags`
with `read_volatile` at lines 24–47. `ptrace_wakeup_sig_body_result` calls this
logger at `kernel/rust/syscall_policy.rs:16912` before find-thread or its later
update lock. Ptrace request routing is at `syscall_policy.rs:17295–17304` and
`:17343–17362`. Sysfs dispatch invokes the registered store through
`kernel/sysfs.c:622–629,602–605,528–536,50–54`; Rust debug registration is
`kernel/rust/debug.rs:47–50`. The Rust registry reads packed line/flags at
`debug.rs:77–89`, displays at `:261–293`, and matches and updates at `:411–421`.
There is no common exclusion on these paths. C fallback performs corresponding
ordinary bitfield reads/writes at `kernel/debug.c:200–203,300–306`. The packed
word at byte 24 contains line and flags together; reading the line while another
CPU writes flags is also a conflicting access. `kprintf` synchronization begins
after the decision and does not protect this word.

Do not change all registry writes to atomic while leaving the existing readers:
`lib/include/ihk/debug.h:27–37` uses ordinary C bitfield reads; Rust word readers
appear in nine current files containing `.line_flags` (including the registry),
with some volatile and some ordinary; `kernel/rust/page_helpers.rs:698,728` and
`kernel/rust/mem_helpers.rs:8517,8666–8675` perform ordinary byte reads at the
selected ABI offset. Other pointer-based aliases must be checked against the exact
integrated source and object relocations. No exhaustive claim about the historical
389 selected descriptors is made from this repository-wide textual inventory.
The independently observed candidate descriptor is its own static record and the
logger is its named source-level direct consumer; prove no other address escape or
linked consumer in the selected candidate before relying on this distinction.

## Implementable narrow design, subject to independent review

1. Replace just the candidate's private descriptor definition with a dedicated
   `#[repr(C, align(8))]` type containing the same three pointer fields followed
   by `AtomicU32`. Initialize the atomic before publication with the same low
   24-bit line and high 8-bit build-bound flags. Assert size 32, alignment 8,
   and offset 24, and verify actual linked descriptor bytes, section membership,
   count, full C ABI and the actual profile's file/function/line/default. Keep
   all original record identities and the selected full-registry validator. Do
   not reinterpret a C bitfield allocation as an atomic or change the global
   `struct ddebug` layout. Check the *selected pinned toolchain*, not the system
   `rustc`, supports the chosen API. Atomic loads can use `Ordering::Relaxed`;
   flags do not publish any accompanying state.
2. Expose an ABI-stable Rust function which returns this record's address for
   identity comparison, and tightly scoped Rust load/update functions. The
   logger reads only this exact atomic word. Rust sysfs line and flag readers
   check identity *before* accessing `line_flags` and call the atomic load for
   this record; all other records keep their original access path. The update
   callback similarly branches before any ordinary read or write and uses a
   relaxed atomic `fetch_update`/CAS loop setting bits 24–31 while preserving
   bits 0–23. The line and flag formatter may use a single loaded snapshot.
   Keep the original nonzero flag semantics, filtering, return values and command
   grammar. Do not construct a shared or mutable Rust reference to the complete
   candidate as a non-atomic `Ddebug`; raw field-address operations and raw
   reads of its immutable pointer fields must not touch its atomic word.
3. The C debug fallback must make the same identity check *before* evaluating
   `dbg->line` or `dbg->flags`, and call Rust atomic load/update functions for
   this one Rust-owned descriptor. This avoids casts, mixed atomic widths and
   C bitfield type/aliasing assumptions. C call sites for ordinary descriptors
   remain unchanged. This adds C fallback routing logic; under the compute-C
   boundary, it requires an explicit reviewed exception or a proven profile
   that prevents C debug fallback with the selected Rust logger, enforced by a
   build-time error. Merely assuming C fallback is unreachable is insufficient.
4. Bind the C selector, Rust logger cfg and registry dispatch with a common
   compile configuration. A selected logger with missing registry handling must
   fail at build/link time; do not depend on a weak symbol or silently default
   to ordinary access. If the logger is off, the old registry behaves unchanged.
   Check mutually exclusive provider selection and all combinations that the
   supported profiles actually allow. The exposed symbol is an identity/atomic
   bridge, not permission for other users to access that record's word normally.
5. Verify immutability/lifetime and exact ownership: only this static uses the
   special type; linker registry iteration cannot create a non-atomic aggregate
   access; each mutable access to this address, including show and line matching,
   takes the special branch; no external pointer alias, copied snapshot, raw byte
   reader or C logger refers to it. Verify full selected symbols, relocations and
   actual link map; candidate is not promoted on textual inventory alone.

The update CAS need only preserve the original single descriptor value and allow
concurrent toggles to linearize. A logger may decide from the value immediately
before a concurrent toggle, as before; no synchronization with output completion
is promised. No lock is held while formatting, avoiding logging recursion/IRQ
lock-order changes. Existing unrelated descriptor races are explicitly outside
this narrow candidate's proof and remain an open whole-registry issue.

## Required future validation, not performed

- Compile checks with the actual paired C/Rust profiles, including selected and
  fallback combinations, exact Rust ABI, symbols and descriptor bytes; verify no
  missing or duplicate record, and preserve all original full 389-oracle inputs.
- A targeted test through *actual* registry and candidate functions for default,
  matching/nonmatching file/func/line, `+p`, `-p`, `=p`, `=_`, logger output and
  line-bit preservation. Include repeated concurrent toggle/show/log checks for
  the candidate, but do not treat stress success as proof or alter the oracle.
- An independent source and linked-artifact review of every access/alias to this
  exact record and both enabled C/Rust paths. Real execution still requires fresh
  admission and review and must preserve all native owners and existing holds.

Current state: private design only. No shared file modified; no build, Docker,
privileged operation, guest or native check run. Exact cutoff and weekly-only
limits are unchanged.
