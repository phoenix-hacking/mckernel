Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private packet selects three still-live F03 C wrappers: extra_set,
init_raw and atomic64_read. It does not touch the foreground ptrace-writer
callbacks or the separate event set_period/update packet. Canonical files and
sealed CURRENT111 build inputs remain untouched.

Two new Rust wrappers call existing x86_perfctr::ihk_mc_perfctr_set_extra and
ihk_mc_perfctr_init_raw exactly once. The extra event address is forwarded by a
raw cast. Init preserves signed counter/mode/int results and the original x86 C
unsigned-long64 to unsigned-int32 conversion with hw_config as u32. The genuine
header declares a different uint64-code variant under POSTK_DEBUG_TEMP_FIX_29,
which top-level CMake introduces for smp-arm64. The supported x86 selected branch
has a compile-time provider-type/width assertion: it cannot silently accept that
other ABI. The original C fallback retains its original header-dependent call.
There are no new runtime checks, masks, hardware instructions or PMU algorithms.

The atomic callback reuses the already-exported syscall_atomic64_read_bridge.
Its exact unchanged Rust body already calls atomic_helpers::ihk_atomic64_read;
the existing provider performs its SeqCst load on its original live/aligned
atomic64 input. A paired C macro maps the perf callback to that existing bridge.
No duplicate Rust atomic wrapper or new atomic algorithm is implemented. Pointer
validity/null/alignment, observation ordering and caller ownership stay with the
original provider contract. This packet adds no reference or dereference.

Private C/Rust patches select exactly these three C bodies, append only two new
Rust bodies, and preserve every193 existing __FILE__/__LINE__ expression identity.
Selected branches use MCKERNEL_RUST_SYSCALL_POLICY_HELPERS together with
MCKERNEL_RUST_F03_PERF_PROVIDER_NEXT3_BRIDGES. The separate Root-owned CMake
proposal pairs f03_perf_provider_next3_bridges_selected_candidate under the
existing runtime/Linux6.12/x86_64/noUBSAN/ENABLE_PERF gates. No new C runtime
algorithm, C metadata owner, shared ABI declaration or provider body is added.
Root must reconcile these bounded hunks with its latest canonical sources.

The literal unrun seven-command HOST recipe builds one focused Rust object,
one selected witness, three original fallback profiles, one link and one mock
parity run. It includes the existing atomic Rust bridge byte-exact from the
captured policy source and mocks all three underlying providers. No actual PMU,
event dereference or atomic load executes in that fixture. Proposed872 pairs
are48 extra-pointer pairs,768 signed-counter/u64-to-u32-code/mode pairs and56
full signed-long atomic-pointer pairs. Each old/new call must produce one exact
independent trace,1744 total; ABI16 and all three selected addresses must match.
NULL/unaligned/high-bit pointers are only opaque mock arguments. No complete
event-layout, real atomic ordering or hardware behavior is qualified by mocks.

Pure source composition, selector, retained-body and narrowing-boundary checks
passed. The output directory has not been created. No compiler, workload, guard,
admission, Docker, Root, guest or cleanup operation ran. Root needs fresh exact
ordinary authority before executing the recipe, then genuine whole Rust/C/link
and matching native provider proof before retirement. Source prediction is three
selected C removals, two new Rust exports and one existing Rust bridge selection;
it is not measured artifact or native credit. M14/whole-file predicates stay OPEN.

Same fixed cutoff2026-10-28T05:36:09Z, creditrun7f4af94a83b14cc08f97401f5891d965/
57774.852125 ceiling/cumulative spent>=22812.3311 and real holds remain. All
one-heavy/mutex/scratch21/resource rules stay unchanged; this packet grants none.
