Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Independent decision: PASS both exact private BODY4 candidates at source/ABI/
ownership and settled HOST qualification scope. F03 source24927595/HOST7a4eeb99
and rebased118 F06 source322410ee/HOST3bb70cfe/results5d54bffa are accepted at
that scope. Original116 F06 proposal remains stale for integration; its sealed
inputs and history are preserved. Actual canonical118 adoption c161d7b6 and all
nine postimages still match. Accepted default artifact remains CURRENT116.

F03 util_show_syscall_profile preserves the one-time uti_desc capture before the
first log, offloaded header then ascending512 slots, other-thread header then
ascending512 slots, zero suppression and signed64-bit counts. Rust passes index
as CInt/i32 to %d and count as CLong/i64 to %ld; existing parent kprintf has its
real variadic declaration and the genuine kmsg.h driver consumes int/long with
va_arg. Return0 ignores every logger result, including signed extrema. The raw
pointer implementation creates no whole-descriptor reference, writes no byte,
and adds no lock, allocation, validation or null behavior. The existing foreign
descriptor lifetime/synchronization and TODO usercopy debt remain unchanged.

The existing project SyscallStruct/UtiDesc Rust field declarations are reused.
The real UTI header and Rust table compare26 ABI words: struct sizes/alignments,
all field offsets, stack/slot counts and scalar widths. The fixture contains the
same production module/function, adding only an exported ABI table. Its original
C oracle body is verbatim canonical C, renamed only at inclusion. The independent
expected event stream and complete primary/decoy byte comparisons check both
implementations separately. Logger callbacks replace the global descriptor after
the first header, alter future slots at headers and mid-table, and alter an
already visited slot. Those effects distinguish captured pointer, live ordered
reads and no replay/snapshot behavior. Six patterns, three mutation modes and
four logger returns yield72 original-C/Rust pairs, including zero tables, full
tables, final slots, signed minima/maxima and values above32-bit width.

F06 arch_ptrace_xstate_copy_from_bridge preserves its raw live Thread read and
the caller's existing ptrace/write exclusion. Null fp_regs returns-ENOMEM without
calling usercopy. Otherwise the unchanged Rust copy_from_user receives borrowed
FP storage as destination and the original user address/count as source/count.
Its signed CInt result widens to CLong with sign extension. The candidate does
not acquire ownership, form a Thread/user-memory reference, change locks, allocate,
map, normalize an argument, roll back a partial write or execute FP instructions.
Null/invalid target Thread remains outside the original C defined domain.

The real-header ABI compile checks copy_from_user's signed-int32 result, bridge
LP64 argument/result types, ENOMEM12, actual Thread5568/align64/fp_regs4784 and
xsave1088/align64. The entire unchanged Rust candidate module compiles against
the complete ABI snapshot; the C oracle includes the verbatim original bridge
under symbol-only redirects. The1944 pairs cover two FP-presence states, nine
counts, nine signed results, three source-address forms and four partial prefixes.
They compare complete destination/source/Thread bytes, provider call/argument/
result trace and a separately constructed expected trace/result/canary image.
Null/high source addresses and huge counts are mocked forwarding cases; they
do not execute actual usercopy, validate arbitrary memory or qualify ptrace.

All107 checked byte references match. The three F03 and four rebased118 F06
commands match their new Root grants, exact plans, pinned tools and preimages.
Their retained raw command/start/preflight/result/stdout/stderr evidence confirms
seven exit0 positive direct wait4 joins and closed parent stream pairs. F03 uses
CPU6 and F06 CPU7; both enforce jobs1/AS2GiB/CPU60s/wall90s. Fresh preentry source/
control/account checks are evidenced by the bound runners and captured facts;
this reviewer invoked no live check. F06 records zero group-scan errors. F03's
group scanner skips inaccessible proc entries, so its recorded empty group is
not independently promoted to global physical/native clearance; direct-child
joins and parent stream closure are explicit. No new workload cleanup or native
custody claim follows. Read-only nm confirms F03's Rust export/ABI table and the
F06 original-C oracle and real-header witness symbols.

Independent CPU0/AS2GiB source/evidence checks also apply each exact patch in
memory; all context matches, and all three F06 proposed postimage hashes match
PREIMAGES. No implementation, compiler, fixture, runner or guard executed during
review. The first review-checker comparison found one fixture-only blank line
before its ABI-table separator. Original checker bytes/failure remain retained;
one correction ignores only that separator newline and passes exact function
comparison. This is no failed OS candidate, compiler retry or weakened behavior
oracle. The original F03 manifest-path failure and original F06 stale116 history
remain retained and unchanged.

Root may compose these exact bodies with independently accepted BODY3 do_munmap
and xstate-copy-to using adopted118 as the sole source baseline. Shared append
sites in syscall_policy.rs, lib.rs and CMake need one coherent additive merge;
never overwrite118 with older whole files or apply stale116 selection patches.
Preserve existing118 selectors, restore-FP/vDSO modules and ABI. Maintain unique
Rust exports and exact selected C extern/fallback boundaries for both copy
directions and util profiling. Rebind the real combined F06 origin/profile and
source dependency closure, including both new F06 leaves, without relabeling the
old profile or replaying the seven settled HOST commands. Generic C logical
line preservation also needs the final composed source comparison.

Required integration evidence remains genuine fullcrate compilation, full
selected/fallback C translation units, actual default linked artifact/provider
ownership and preservation of inherited registry/ABI/behavior, followed by the
applicable matching-current profiling/ptrace write-regset/error/partial-copy/
lifetime checks. Neither private HOST fixture proves those production providers
or completes F03/F06 files. New default/native/C-retirement/file deltas are zero.
All credential/service/signal exclusions, original failures, current cutoffs
UTC1793253600/MONO1035704.5689393478/BOOT1051042.6959879305, run
7f4af94a83b14cc08f97401f5891d965/ceiling57774.852125/floor22812.3311,
retained BFD custody, scratch21 and permanent27:4 remain unchanged.
