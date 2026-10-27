Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

UNRUN controls for the producer and compile-time origin assertion:

1. Exact adopted profile + candidate C source generates the original literal
   `/src/arch/x86_64/kernel/syscall.c`, with trailing NUL only in Rust storage.
2. Mutate source operand, add -fmacro-prefix-map, add -ffile-prefix-map, change
   cwd/compiler, add response file, alter -c placement, or inject -D__FILE__:
   producer rejects changed profile hash before writing outputs.
3. Exact profile with a filename-bearing #line directive or source #define /
   #undef __FILE__ rejects before output generation. Existing number-only #line
   directives remain supported. Unusual preprocessing dialects are unqualified.
4. Unset Rust origin environment: rustc must fail at env!, with no fallback.
5. Original-C/Rust typed fixture832 allocation +8 free: exact filename bytes,
   logical385/391, size_t64 narrowing to int32, flags64, pointer/result64, NULL,
   callback count. Mocks never dereference opaque pointer words.
6. GCC compile static guard in selected C scope: positive #line source-origin
   compiles, wrong #line filename fails _Static_assert. This validates actual
   GCC constant-expression support; no compile success is claimed yet.
7. Paired selector combinations00/01/10/11 must preserve all129 existing
   tracking expressions. Existing Root HOST19 regression remains authoritative;
   rerun changed-candidate selector checks only after its ordinary grant.
8. Actual selected production C object must have neither defined nor undefined
   f06_rt_sigreturn_source_file. Linked Rust object owns filename bytes and both
   forwarding bodies; new C runtime data/function delta is zero for the guard.

The profile SHA lock deliberately rejects all other adopted profiles. A new
compile profile must receive a fresh exact origin binding and independent review;
this proposal does not claim general support for prefix-map flag semantics.
