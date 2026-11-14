Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Ready private F03 slice: `clear_host_pte`, an actual CURRENT115 selected129-byte
global C function outside CURRENT116's seven and CURRENT117's perf_mmap entry.
This candidate reuses the exact existing complete Rust
`clear_host_pte_body_result`. The new Rust export owns the remaining current
thread/VM lookup, genuine CPU-ID lookup, header-bound providers and real Rust
ProcessVm field offset. No mapping or lock operation is reimplemented.

The existing body publishes the CPU ID only when holding_memory_range_lock is
nonzero; calls the original forwarding provider with munmap/address/length/0;
restores -1 before any logging; logs every nonzero result once; returns the exact
signed result. No additional null handling, error conversion, cleanup, lock,
allocation, credential call, context construction or host side effect is added.
Callers retain the original live CPU/thread/VM and range-lock contracts.

`clear-host-pte-binding.C.inc` is immutable actual-header data containing the
syscall number and original typed callback pointers. The original C log bridge
and three-argument forwarding bridge remain explicit C debt; existing request
initialization/endpoint holds remain unchanged. No new C runtime function is
introduced. Paired selection uses the already enabled SYSCALL_POLICY_HELPERS;
the opposite branch retains the exact original C function. Existing dispatch
selector-dependent logical-line states are restored before subsequent source,
preserving tracked allocation/debug origins. Shared CMake/ABI/canonical files
remain unchanged. Root must reconcile current preimages before selective use.

The HOST fixture includes exact current Rust ABI definitions and complete body,
plus the proposed entry. Its actual-header C driver compares18 ABI words for the
real CPU/thread/VM and binding layouts and provider widths. It runs the unchanged
original C wrapper and new Rust export through mocked CPU/forward/log effects.
The planned2304 pairs cover8 full-width address/length patterns,4 signed lock
flags,4 CPU IDs,6 signed results and3 initial lock-marker states. Every invocation
independently checks lookup counts/order, exact forwarding arguments, the marker
while the forward call is active, restoration before log, exact result, full VM
bytes, unchanged full thread/CPU bytes and exact log count/error. No real MM,
syscall, CPU-local hardware, Docker, root or guest operation is performed.

No compiler/behavior test has run in this lane. The exact three-command HOST plan
is source only and needs fresh Root ordinary source/tool/header binding and grant.
No old grant/window/nonce is revived. Existing unprivileged HOST limits are
CPU6/jobs1/AS2GiB/CPU60s/wall90s. Deadline2026-10-29T06:00Z and cumulative credit
run7f4af94a83b14cc08f97401f5891d965/57774.852125 remain unchanged.

Actual C-body removal condition: a newly selected generic syscall object must
contain no C-defined `clear_host_pte`; all existing callers must resolve to the
new Rust global; its data binding must resolve to the unchanged real forwarding
and log providers; the linked default image must carry this same ownership.
Matching native host-PTE/unmap/lifecycle checks remain required. This packet
predicts one C-function removal and claims no actual build/object/native delta,
no supported-file closure and no completion of the retained C providers.

The earlier `setresuid-entry.Rust.inc` and `driver.c` are HELD and excluded from
all ready patches/fixtures/plans. SETRESUID-HOLD.json records that getcred cannot
establish initialized response bytes after its ignored offload result. No
initialized-only credential fixture supplies full error qualification and no
Rust credential port is ready for integration. Those source drafts remain
preserved; no credential operation or compiler ran.

Other workers' changes, prior failures/evidence, scratch21, failed96 and
permanent27:4 are preserved. Root owns integration, compiler/runtime authority,
shared files, Git and control processes.
