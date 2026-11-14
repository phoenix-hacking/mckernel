# M14-02-04 private idle orchestration: actual implementation ready for review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Rust now owns a PRIVATE candidate for idle initialization, one complete idle-loop
iteration and the production infinite loop. **Canonical integration, pinned
production/default image and native validation remain OPEN.** No retirement or
practical35/35 credit is claimed. This is independent of the frozen235 attempt;
its image10972, sources, SDK/profile and all other workers' files are unchanged.

Exact assignment/invariants preceded implementation in PRIVATE-ABI-BRIEF.md.
M14-02-04 directly includes idle/runqueue/migration transition ordering; this
packet does not broaden its scope to other C areas or change FP/post-switch code.
Owner writes only this new subdirectory and matching HOST subdirectory. No root,
Docker, guest, actual full process TU/fullcrate/image build, launcher or ownership
mutation occurred. Existing idle-scan packet and passed checks remain unchanged.

## Exact code and before/after behavior

Private sources:
/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/idle-orchestration-1/{preimage,postimage}/.
Only kernel/process.c, kernel/rust/sched_helpers.rs and kernel/include/sched_helpers.h
change. SOURCE-MAP.json binds their exact current-canonical preimages and private
postimages. source.patch is the precise canonical-base delta; the separate
COMBINED-CURRENT10972-SOURCE.patch applies the original reviewed scan plus this
new orchestration to the actual old selected10972 source. This distinguishes
the current Git implementation from the still-C frozen image correctly.

| File | Canonical-base SHA256 | Private postimage SHA256 |
| --- | --- | --- |
| kernel/process.c |910771e0908d3fc69fcad13e94a2f0da13a964ce0293911fa2dcd5180b6e9ca7|7203019d2ba8143f9240a03d11bc8c5cfcd495d89183aa7ab643c6159a6bd02d|
| kernel/rust/sched_helpers.rs |8b5c15fe52c59964105561d560bca5c648464872a44ead44b672e180c44acbd1|449df570965855f992a0fe024fca7cd6527b20622b4b8e3b33af04900b02e923|
| kernel/include/sched_helpers.h |15e506c4a6e6bd359e704a29e89bff20ea65a14ea69f24171aeb43024847d474|9712a3df59eb0251f517ce01254e4576119868924b35f7da6fbee294bff966ae|

Before, C idle() captured v/monitor, released the inherited runq lock, changed
RUNNING→IDLE, enabled IRQs and owned its complete scheduling/migration/scan/halt
loop. Its scan alone had a previously source-reviewed Rust branch in current Git.
After, the PROCESS_HELPERS-selected C entry supplies the same initial v/monitor,
C-produced offsetof/type/constants and existing primitive function addresses to
sched_idle_loop_body_result. Rust owns all prior initialization and loop state/
control behavior. The complete old idle() function remains byte-identical under
the fallback branch. All C bytes outside that exact selection are identical;
no cpu.c, schedule(), context-switch, FP or post-switch release fix was edited.
The C ABI descriptors/declarations add no compute-C algorithm or subsystem.

Rust iteration order is exact: current STOPPED → schedule → re-read current and
set RUNNING → disable IRQ → migrate if requested → re-read flags, clear only
NEED_MIGRATE → IDLE/RESERVED locked exact-running scan → unlock → fresh status
decision. Idle path: consolidate → zero-free → monitor IDLE → current
INTERRUPTIBLE → safe-halt → monitor KERNEL → wrapping unsigned counter increment
→ re-read current RUNNING. Other status enables IRQs. Existing Rust scan is reused;
no list mutation or replacement scheduler is added.

## Unsafe/ABI contract requiring the focused decision

Review whether that C/IRQ/runqueue/current-thread order and valid-lifetime
contract are ready for canonical integration. Cpu/monitor addresses retain the
original idle lifetime, current CPU lookup is a pure existing primitive, and the
current CPU/thread is looked up again after schedule/halt boundaries. Initial
unlock uses the existing saved irqstate. The callback table is complete/non-null,
immutable and valid for the COMPLETE idle lifetime; raw descriptor pointers are
held by the infinite loop but are never globally published or ownership-transferred.
No Rust references point to mutable CPU/thread/monitor/list objects. The only
Rust references point to the valid immutable descriptor tables.

Offsets80B, values36B and callbacks80B are repr(C) in Rust and C. C assertions
require LP64, four-byte int statuses/unsigned-int flags, unsigned-long monitor
counter and leading list.next. Actual C headers produce all offsets/constants;
there are no guessed thread/CPU layouts in the implementation or fixtures.
Status/flag/counter accesses use raw volatile loads/stores, not a new atomicity
guarantee. Counter wrap matches C unsigned long. Migration and unlock are allowed
to change flags/status; the next decisions use fresh observations. No null/list
corruption recovery or stronger concurrency guarantee is introduced.

The new Rust sched_idle_current_cpu_bridge calls existing
ihk_mc_get_processor_id→process_sched_cpu_local_bridge. The focused test provider
excludes ONLY this tiny lookup bridge and supplies a controlled current-CPU
callback; production default consumer compilation checks its typed address/import.
Its actual fullcrate resolution and native lookup remain explicitly pending.
All other new Rust types/initialization/iteration/loop bodies are compiled from
the staged source exactly. A primitive callback remains a dependency, not proof
that all of its own C implementation has been retired.

## Actual checks, failures and supported limits

CPU6 one job,2GiB AS,60CPU,90wall+6s grace,32MiB per-file/core0, inherited NPROC;
ordinary host GCC9 and pinned Rust1.92/codegen1/2MiB Rust stack. Exact invocation:

```text
/usr/bin/taskset -c 6 /usr/bin/prlimit --as=2147483648 --cpu=60 --fsize=33554432 --core=0 -- /usr/bin/timeout --kill-after=6s 90s /home/holden/anaconda3/bin/python3 -I -B docs/verification/evidence/compute-idle-rust-cutover-20261023-1/idle-orchestration-1/check_actual_bodies.py
```

Attempt3 exit0: **108 actual original-C/Rust state+callback-order comparisons**
using actual selected process.h/cls.h/monitor/list headers and generated config.
The existing C body's initialization and exact iteration are extracted; only
primitive call identifiers are bound to safe test callbacks. Rust uses its actual
new bodies and existing scan. Nine event scenarios ×4 initial CPU states ×3
queue states compare every CPU/thread/monitor byte and complete callback trace.
No real IRQ, halt, lock, CPU migration or kernel allocator executes.

Covered event scenarios: ordinary empty/stopped-spin-only/running queues;
current-thread change during schedule; current-thread change during halt;
migration preserves newly changed unrelated flags; lock callback queues running
work; unlock changes status; migration changes CPU status; schedule changes CPU
status; monitor unsigned counter wrap. Callback assertions enforce lock/IRQ and
STOPPED/RUNNING/INTERRUPTIBLE/monitor state ordering. Byte snapshots include
production object padding and pointers at the same stable fixture addresses.

Actual Rust object has zero undefined symbols and no FP/SIMD registers or
XSAVE/XRSTOR instructions in its retained disassembly. Host link --no-undefined
passes; executable prints the108-case PASS and exits0. Exact default C producer
with actual headers compiles, checks its static assertions and imports the Rust
loop/current-CPU bridge. Its fallback compiles with neither new Rust import.
These are host consumer/header diagnostics, NOT pinned GCC14/full-TU/default
whole-image or native acceptance. The infinite loop is compiled but not executed;
fixtures exercise the SAME begin and single-iteration bodies it calls.

Failure history retained, no production-source correction or profile change:

1. Fixture compile family: attempt1 monitor variable collided with the existing
   header global; identifier substitution also renamed .schedule. Original
   script/fixture, generated C,1648B stderr and all statuses remain. ONE bounded
   correction renamed the fixture monitor and preserved member identifiers.
2. Separate host-fixture link family: attempt2 compiled C and actual Rust, then
   failed on __inline_memset from kernel string-header reset helpers. ONE bounded
   correction added test-only volatile byte helpers. Rust/C production postimages
   stayed byte-identical. Attempt3 completed successfully. Both families have
   consumed their correction; recurrence requires expert escalation.

Rust's disabled-SSE2 target warning, the unused local monitor reference warning
and the standalone fallback's undeclared-body do_migrate warning are preserved.
The last warning is a small-TU fixture limitation: whole process.c contains that
existing static body. No warning-free/wholecrate claim. The earlier source scan's
80 parity cases and the previous actual-header3-case check are reused, not rerun.
After108 PASS, no further compile/vector/census was run.

## Delivery boundary and remaining C table

| Path | Private candidate behavior | Production/native retirement |
| --- | --- | --- |
| Idle locked exact-running scan |Existing Rust helper reused within Rust iteration|Current10972 remains old C; pinned/native OPEN|
| Idle initialization and state/IRQ/migrate/scan/halt orchestration |New Rust begin/iteration/infinite loop;108 actual-body cases and default host producer PASS|Private only; canonical review, whole TU/fullcrate/default image/native OPEN|
| Thin idle entry / existing primitive implementations |C producer thunk and existing primitive dependencies remain explicit|Not a zero-C result or full M14-02-04 closure|

ACTIVATION-CONTRACT.json combines this exact final three-file image-source
successor and source fingerprint, candidate identity
f99a62a71ce3223a62b51fe5030f17be2d233de061fe101ffdbbc4dfd71ff399.
NEXT-PINNED-PRODUCTION-COMMANDS.json reuses the prior selected GCC14 process.c
and default Rust/image target argv under the pinned image41778f1f..., retaining
PROCESS_HELPERS, ENABLE_RUST_KERNEL=ON, native fork and Linux6.12 ABI selection.
It is preparation data, not an execution release or authority to overwrite the
accepted source/build/image. Foreground owns canonical M14/ledger edits.

Next decision: focused independent unsafe/ABI/order SOURCE review of these exact
private postimages. On SOURCE PASS the dispatcher supplies a precise canonical
three-file integration brief with fresh preimage joins. Later, after the current
235/SDK chain is physically retired, it may release one coherent new pinned
production TU/fullcrate/default image candidate under existing4CPU/12GiB/no-swap/
512task/network-none and ownership/capacity controls. Require default C producer
imports, unique Rust/final definitions including the current-CPU lookup bridge,
zero final undefineds, then matching separately reviewed native idle/wakeup/order
evidence with unchanged application oracles. No source/mock/native credit is
invented here. Full M14 remains separate from practical35/35.

All private before/after sources, commands, generated fixtures, objects, binary,
disassembly, both original failures and passed traces are retained in
retained-private-sources-and-tests.tar.gz (263733B,
SHA256b610f43d31ed490390090a64ad49e9bfa783c1d56a0e445d8404b7d75eaf4c04)
and the HOST directory. RECEIPT.json binds that archive and proof limitations.
No active/current source or image, Scratch21, permanent27:4, existing ownership,
budget/model/launcher settings or unrelated dirty work changed.
