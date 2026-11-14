# One bounded C witness origin correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The first actual paired witness compile failed in the C stage with exit 1; Rust did not run. Retained `c.stderr` SHA `0dc27a70286acfe434e75c0b17f01f6eb2934a660a4bd91ca00e1f3def196ce4` reports `static assertion failed: "F06 signal allocator original __FILE__ binding drift"` at logical line 384. `COMPILERS.RESULT.ACTUAL.json` retains the failed attempt, tool/resource records and group closure. This packet preserves that failure and proposes one source-only correction; no compiler or test was run here.

The selected C source reaches `#include "f06_rt_sigreturn_origin.h"` followed by `_Static_assert(__builtin_strcmp(__FILE__, MCKERNEL_F06_RT_SIGRETURN_ORIGIN) == 0, ...)`. The genuine origin header SHA `aeece54c3b6f01c326fff3eb925b89b88acd3b198b0047393c8c9c0d78f74ded` defines the expected string `/src/arch/x86_64/kernel/syscall.c`. The actual C operand and error identify the long private staged HOST path ending in `/src/arch/x86_64/kernel/syscall.c`. The main C file uses numeric `#line` directives and has no quoted filename line directive. The real selected debug header remains the independently bound SHA `7315ef758c56c4888242295ed9340b44f649d772b1315502acc49eb6105048dc`; neither header nor assertion is altered.

`CORRECTED-PAIR.PROPOSED.json` and the two `CORRECTED-*-ARGV.sh.txt` files retain the prior C/Rust argv and selectors, replacing the old consumed attempt output and depfile paths with fresh proposed paths and adding only this C flag:

```text
-fmacro-prefix-map=/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/arch46-host-witness-preparation-1/src/arch/x86_64/kernel/syscall.c=/src/arch/x86_64/kernel/syscall.c
```

The file-scoped source prefix is deliberately narrower than mapping the whole staging root. It is intended to map C macro filename expansions from this exact operand to the header's original logical filename, without remapping unrelated headers or changing Rust flags. GCC prefix matching can also affect any path beginning with that full filename, so the actual selected dependencies and compiler output still need confirmation. It does not rewrite source, redefine `__FILE__`, change `#line`, weaken the assertion or prove an emitted value. Other `__FILE__` expansions in this same C file will also use the mapped filename; that is an intentional consequence. C debug-prefix mapping and Rust's separate HOST location strings are unchanged.

The original staged C and Rust source bytes, reviewed 46 oracle entries, source/ABI selectors and prefix/clone-position binding remain unchanged. Old origin receipt `b5e9...` still binds only the original full source; the staged witness source SHA `e293...` remains different. No new origin receipt, original 389 registry/debug equivalence, final-link ownership, default or native acceptance is claimed.

The output paths in the vectors are explicit **proposed fresh** paths in this new private packet; they have not been created or used. Root owns final fresh output/environment script binding, finite unprivileged admission, process joins and actual rerun. The operation must preserve raw stderr, return and depfiles, and compare 46 emitted values only after C and Rust succeed. Both resulting witness objects remain forbidden in diagnostic and production links by actual identity. If the corrected attempt fails in this same family, preserve the new failure and escalate rather than repeat unchanged.
