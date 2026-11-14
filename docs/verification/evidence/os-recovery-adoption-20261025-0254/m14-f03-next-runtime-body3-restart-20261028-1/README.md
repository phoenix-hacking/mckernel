Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private next F03 body: `do_munmap`, an actual 168-byte C function in the accepted
CURRENT116 generic syscall object. This work excludes banked117 `perf_mmap`,
banked118 `clear_host_pte`, every held credential draft, and the service-held
request/endpoint/signal work. Root owns all canonical integration and execution.

The candidate reuses the exact complete current Rust `do_munmap_body_result`.
The new Rust entry owns the original CPU-local/current-thread lookup, borrowed
VM/process extraction, genuine Rust `Process` straight-map field offsets and
immutable actual-header callback binding. It preserves the original pointer,
length, holding-lock flag and signed return type. It adds no null checks,
allocation, range lock, host request construction or C runtime function.

The C binding retains the exact original six providers. The selected begin,
remove-range and finish aliases continue resolving through their existing Rust
selectors. Host clear/set and log callbacks remain explicit selected C debt,
along with their unchanged downstream provider contracts and existing holds.
The existing body preserves begin/remove/host/finish/log order, reads straight
map state after range removal, bypasses host callbacks for contained ranges,
preserves range-removal errors over host-clear errors, truncates host-clear
results to the original C `int`, forwards full-width addresses/lengths and the
unchanged holding-lock flag, and calls finish/log after all ordinary outcomes.

Paired source uses the already enabled SYSCALL_POLICY_HELPERS selector and
retains the verbatim original C entry in the opposite branch. The existing
dispatch-dependent logical line states are restored after the replacement;
shared source, ABI and CMake files are unchanged. Root must recheck current
preimages and compose with banked117/118 before canonical adoption.

The HOST fixture source includes the real Rust ABI and exact current Rust body.
Its separate C oracle includes both the verbatim original C entry and complete
retained C body. Each invocation also checks a separately computed result,
provider arguments/count/order, initially zero ro_freed, straight-map values
changed by the removal callback, and full CPU/thread/VM/process object bytes.
The planned ABI27 check compares genuine C layouts, field offsets, provider
widths, protection bits and immutable binding layout against Rust facts.
The 4860 planned C/Rust pairs cover ordinary/boundary/wrapping/full-width ranges,
straight-map containment and changes during removal, negative/nonzero lock
flags, remove/clear/set errors, positive errors and signed return narrowing.
All range/host callbacks are mocks. There is no actual MM, syscall or hardware
effect in this fixture. No compiler or fixture has run in this lane.

`FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json` contains exact three-command argv
for the Rust object, genuine-header C/oracle link and functional fixture run.
The output root is a placeholder requiring a fresh Root grant, exact tool/header
binding and a disjoint output directory under the existing CPU6/jobs1 HOST
profile. It is source material only and grants no workload. The next true check
is those three commands after Root grants ordinary execution. A successful
HOST result would still require coherent real default object/link proof that
the C `do_munmap` definition is absent, all callers resolve to the new Rust
definition and the six bindings retain their selected owners. Matching native
unmap/range/remap/lifecycle proof and full F03 closure remain open.

Earliest inherited UTC/MONO/BOOT deadline clamps and cumulative credit run are
recorded in SOURCE-READY.json without modification. Old grants, nonces, consumed
prefixes, failures, scratch21, permanent27:4 and all other workers' dirty work
remain preserved. Source checks establish exact extraction and binding only;
they supply no functional test, selected artifact, native or whole-file credit.
