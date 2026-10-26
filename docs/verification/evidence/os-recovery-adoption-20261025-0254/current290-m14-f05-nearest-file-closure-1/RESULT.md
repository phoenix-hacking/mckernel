Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

F05 has no remaining selected C body to implement in current290. The original
read-only GCC14 memory.c.o (d3207c7a, 2888 bytes), genuinely reused by BUILD3,
has zero runtime functions, runtime objects, undefined imports, and relocations
against allocated sections. Its only nonempty allocated section is the 48-byte
GNU property note. This is the original input, not the empty host mount placeholder.

The CPU0 read-only reconciliation passed. All 343 actual no_mangle functions in
the selected source6153 memory helper/logger modules exist as function providers
in the fresh6284Rust object and linked e6a82 image. All seven pointer fields in
the final image name the matching Rust owned storage; their owners initialize
to zero, and attr_mask initializes to0x807. The exact accepted eleven-input
BUILD3 link and selected image are reused. No compiler/native operation ran.

Nearest next executable behavior is the already-supported baseline.core.memory
profile, using the unchanged 39488-byte dynamic payload558d1607. Compile only
the existing corrected208204ff collector with -DND_CORE_MEMORY, then bind a new
overlay with the existing builder and unchanged e6a82 image/modules. Exact
collector argv, source identities, prospective manifest fields and fresh native
invocation template are in NEXT-CORE-MEMORY-SOURCE-PLAN.json. This is source
preparation, requiring a real compiler grant and later fresh native admission.
The consumed startup2 nonce is not reused. The collector has explicit core-mode
profiles; no batching or new catalog-case dispatch is assumed.

The memory case performs malloc/free and a 256KiB anonymous mapping, complete
64-page byte readback, first-page RW/RO/RW transitions, a post-restore write,
munmap and ordinary retirement. Its unchanged oracle is stdout exactly
`NATIVE_CORE PASS memory\n`, empty stderr, exit37, plus existing native
lifecycle and teardown checks. Startup2 proves startup only. Even a successful
core memory diagnostic leaves large-page split/merge, allocation-failure
ownership, crossCPU TLB visibility, cross-process usercopy partial faults and
move/remap branches without matching native proof. Existing HOST move/teardown
checks are retained rather than replayed. Whole-file and milestone credit stay
open pending applicable native coverage and independent acceptance.

No new Rust port, default rebuild, kernel/module change, framework or ordinary
payload source change is necessary for this next step. Compiler queue entry,
first-compiler and blocked-duration timestamps for this new proposal are unknown;
no compiler admission has occurred.
