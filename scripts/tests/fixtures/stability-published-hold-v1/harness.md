# Held native-interface and staging harness source

These additive tests have not been imported, staged, compiled or run by their
author. Root owns independent review, retained preparation, pinned compilation
and bounded test execution. The frozen native overlay and its earlier source
review are unchanged; this is a separate test-source artifact.

`prepare_stability_published_hold_harness.py --output FRESH --mode 2` (and a
separate fresh mode 3 output) copies the exact reviewed phase module, four native
appendices and send-gate block. Only the phase template's one mode marker is
substituted. The harness includes those exact source files as Rust modules or
include blocks. Tag/Claim/Delivery and Selection/Phase declarations are extracted
from the exact retained original observer source, with fragment offsets/hashes.
No native helper body is copied into an independent implementation or rewritten.

The standard-library test crate supplies concrete clock, log, mutex/guard, owner
record, application slot, Started/Context and UserSlice stubs. Kernel aliases
resolve to those stubs. It includes the actual Mailbox and Remote helper bodies,
actual Runtime accepted/command methods, actual private ioctl method, and actual
send gate. A test-owned context is allocated for the synchronous calls and
released only after they finish. There is no guest pointer dereference: physical
addresses are literal scalars and UserSlice uses one declared in-process byte
array through a fixed test token. These are controlled interface tests, not real
kernel owner/lifetime, user access, scheduling or ABI acceptance.

Stub locks increment a counter while held. Actual native logging and actual
ioctl user-copy callbacks assert that no production guard is held; copyout also
probes the real Permit after native code should have dropped it. The supplied
completion/clock transitions are labelled stubs: the new helper must only copy
the supplied original timer. They do not claim to test the unchanged production
Completion::prepare or expiry scan. Each of 24 declared cases runs in a fresh
process for each mode; no reset hook is added to native state.

Root compiles `harness.rs` with pinned `rustc --edition=2021`, retaining command,
compiler identity, source, stdout/stderr and binary. Invoke `./harness CASE` for
each name in `native-expectations.json`, with an eight-second per-case deadline
and 256-KiB limits on each stream. The exact expected raw process exit is zero
and the final marker names that mode/case with acceptance=false. Treat panic,
unknown case, extra argument, truncation, timeout, failed cleanup or an unexpected
ioctl value as a failure. Preserve every original attempt before fixing source.
No success marker substitutes for complete raw supervision evidence.

The ioctl vectors print complete literal request/reply bytes and raw results.
The bounded decode loops identify each deterministic byte mutation against
their retained literal baseline. Positive controls surround stale owner/local
health mutations. Full owner observation and fault logs are explicitly named
HARNESS_STUB records; they must never enter a real guest acceptance parser.

`test_stability_published_hold_stage.py` contains 18 focused unittest cases.
Root must supply `STABILITY_PUBLISHED_HOLD_COMPOSED_SOURCE` pointing to the actual
flat, original mode-2 tree after the old owner/phase/send/RET composition and
before new held staging. It refuses a missing source instead of skipping. It
retains that complete source plus the exact reviewed helper/templates before
importing the retained helper. Each scenario has fresh source/output directories,
literal changes, invocation metadata and actual returns/exceptions. The mode-3
positive changes only the two exact original send appendix mode literals.

These stage tests exercise preserved byte identities, five changed native files,
inverse restoration, wrong modes, exact source drift, source caps, failed-input
retention, special files and output ownership. The aggregate-cap case retains
72 MiB of space bytes as nine 8-MiB triggering files; that is controlled failure
evidence, while the helper's accepted logical budget stays 64 MiB. Root must
budget this capture and preserve it. No staging test compiles native Rust or
proves production source authorization by a PREPARED label.
The synthetic symlink/FIFO cases retain exact type/path/target/mode identities
and actual results before unlinking only those owned special objects. This
prevents later artifact walkers following a symlink or blocking on a FIFO;
their original source bytes and explicit cleanup records remain retained.

The separate held native module must still pass the full pinned production
compile and actual stack-chain audit before guest use. Host/controller/physical
proof and all mode-specific runtime outcomes remain independent gates.
