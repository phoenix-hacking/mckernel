Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source16 replaces only selected arch_process_vm_rw_lookup_range_bridge in its
private Source15 successor. Its fallback body remains exact and logical source
lines are restored. Canonical syscall_policy, arch syscall and ABI files were
not edited. The already retained f06_process_vm_rw_lookup body is copied without
changes; the new public provider delegates to it. There is no second lookup
algorithm and no new allocation or production data.

The caller supplies an aligned live ProcessVm, holds its memory_range_lock via
the qualified Source15 reader pair, and keeps both VM and returned range live
until all uses finish before unlock. The adapter creates no exclusive VM borrow,
acquires no additional ownership and retains no pointer. Existing accepted lookup
cache mutations are preserved. A reader lock alone is not a new proof of cache
concurrency correctness; this fixture is sequential HOST execution only.

The six-command NOT-GRANTED tuple compiles the new adapter and exact eight-body
accepted lookup closure with actual ABI and RB types, compiles the original C
delegate and independent C oracle, links the qualified Source15 VM-lock-Rust.o
without recompiling it, runs the fixture and observes ELF providers/imports and
unchanged lock object hashes. Source15's full archive hash is also retained as
qualification provenance but the link consumes only its existing object.
A separate ordinary execution/resource grant remains necessary.

The planned 3420 cases cover zero/one/seven ranges, three insertion orders with
actual RB insertion/color owners, five empty/warm cache states, both original C
and Rust delegates, two repetitions and nineteen interval queries (empty,
reversed, exact, boundary, gap, spanning, missing and maximum-end). An independent
ascending linear overlap scan and independent cache/index model predict the
returned range and all cache effects. Each lookup occurs inside the real atomic
read-lock pair; live range reads and two original public log event forwards are
checked while counter=8/depth=1, then unlock must restore counter=7/depth=0.
All VM bytes except predicted cache mutations must match, and every range byte
must remain unchanged. Twelve actual C/Rust ABI values include sizes/alignment
and VM/cache/range/RB offsets.

The logger endpoint observes the unchanged public helper's event ABI. This leaf
does not requalify production formatter bytes/descriptors; those accepted logger
paths remain separate. The C and Rust delegates intentionally reach the same
accepted lookup body, so their comparison alone earns no algorithm credit; the
independent linear/cache model supplies the functional expectation.

Actual performed check: python3 check_source.py, exit0, SOURCE_ONLY; validates
retained input hashes, eight exact helper bodies, unchanged existing delegate,
recipe purposes, matrix arithmetic and lock reuse. First failed source metadata
case-count assertion is retained in source-check-first-case-count-failure-1;
one correction changes10260 to3420. No compile, link, fixture runtime, native,
container or guest command has executed for Source16.

Next executable check: after coordinator grant/review, run exactly the six argv
records in EXACT-LOOKUP-RECIPE.NOT-GRANTED.json with fresh disjoint output-1,
preserve all stdout/stderr/exit statuses and fail immediately on the first
failure. Require the SOURCE16 current-input hash check first. Expected runtime
stdout: PASS process_VM_lookup cases=3420 ABI=12 linear_overlap=1 cache_oracle=1
log_events=1 borrowed_under_real_lock=1 lock_restored=1.

This unlocks central current-crate/whole-C consumer/provider qualification.
Default image selection, linked production artifact, native borrowed lifetimes,
actual cache concurrency, IRQ/preemption and whole-file C retirement remain OPEN.
