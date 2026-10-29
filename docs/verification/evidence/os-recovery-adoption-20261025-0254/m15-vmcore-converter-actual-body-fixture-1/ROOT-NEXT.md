Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The actual entire unchanged Rust cmd_ldump2mcdump body now has a focused HOST
callback fixture. Candidate5205663e, original Rust4e036420, ACK contract971cccb,
patcha3c14d0f and canonical sources remain unchanged. The command executes through
the real init-array-registered command-table callback. No state-machine replica,
source marker substitute, SDK build, BFD library or actual crashdump ran.

`QUALIFICATION.ACTUAL.json` binds the actual run and separate ownership failure.
27 candidate cases pass the narrow ACK/layout checks: success;7 metadata-read
FALSE positions; first/middle/last physical-read failures; all7 contents-write
failures; close failure; required physchunks lookup NULL;7 allocation failures.
13 original Rust full-body executions directly match the candidate's callback
reads/writes/diagnostics/cleanup observations for success, physical-read faults,
contents-write faults, close failure and missing physchunks. Original metadata
FALSE behavior could use uninitialized data and was deliberately not executed.

The data source uses exact existing C dump-layout declarations,24B page set,
16B page header, one64bit bitmap0x15 and three disjoint4096B chunks. The Rust body
produces the actual72B physchunks section: count3/kernel_base0x1200000/
phys_start0 and entries0x800000,0x802000,0x804000/4096. BFD callbacks validate actual
bytes, section sizes/flags and Rust-written vma/lma/bitfields in the existing
repr(C) section prefix. All metadata/data formats stay unchanged.

Successful ACK is observed exactly once for `/fixture/exact path.mcdump`, then
flushed. Callback event order is successful close58, payload free59, outer chunks
free60, ACK61. Each metadata FALSE returns before downstream read/write callbacks;
both failed bitmap reads free their own bitmap. Each physical FALSE retains
exact `readmem error(0)\n` and all3 physical observations, with later successful
writes retained; ACK is absent. Every BFD contents/close fault and missing
required physchunks suppresses ACK. The fake printf callback captures and checks
formatted bytes at the actual call boundary; result stdout records the event
counters. This is an in-process protocol fixture, not native output publication.

Ownership is separately **FAIL**, as recorded in OWNERSHIP-FAILURES.ACTUAL.json.
Success retains3x32B physmem names, matching the original body. All write/close
faults retain1,048,744B in5allocations, also matching original behavior. Newly
checked second-pass metadata failures enter the retained outer early return and
leave72B mem_chunks live. The second-pass bitmap itself is freed; its outer leak
is not hidden by that narrow bitmap assertion. Allocation-failure cases also
retain earlier buffers.20candidate cases have live producer allocations at
return. The harness records those allocations before reclaiming test-process
memory. No full lifecycle PASS, readiness for production, M15 file closure or
native acceptance follows. A separate reviewed ownership repair remains needed.

The first success run failed the fixture's unknown-free assertion (actual-6):
LLVM optimized malloc+zeroing into calloc. Full undefined symbols were inspected
once; the single bounded correction covers calloc and constant-fprintf fwrite
aliases together. The successful two Rust objects are reused; only the two C
fixtures were relinked. Original failure source/argv/stdout/stderr/wait4 stay in
FIRST-FAILURE.* and actual-run-1.47direct children total are positively wait4
joined:2Rust compiles,4C links and41body invocations (one failed fixture,40valid).
The corrected42-command run finishes in0.433032s, childCPU0.389132s,
peakRSS32248KiB. Exact per-command argv, source pins, outputs, resources and joins
are retained. Parent/capture envelopes bind CPU0/jobs1,AS2GiB,CPU60,FSIZE64MiB,
CORE0 and90s aggregate wall. No subprocess is left running.

Next: independent focused review of this real body fixture and its scoped ACK
observations, then a private ownership cleanup fix with this matrix retained.
Keep the current source candidate frozen for review; Root owns any canonical
integration. The fixture driver uses exclusive attempt directories and refuses
replay of existing attempt names. Existing runtime controls/custody still apply
to any future SDK/native workload.
