Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

arch_ptrace_alloc_bridge is a genuine selected 27-byte allocated F06 function; exact old private Rust adapter/Safety bytes are reused.

ABI: size_t64 narrows to allocator int32, ihk_mc_ap_flag64, static char* filename/int32 line, void* return64.

Ownership: Existing tracked allocator owns allocation/OOM behavior. No new bound policy; retain same size narrowing/flags/base pointer and Rust static callsite provenance. Caller owns real allocation exactly as before.

The private C/policy candidates and paired selectors retain the original C fallback and change no shared ABI. No logger or VDSO state storage instance is copied. Root current affa9b6d/f4ed7080 postimages are preserved; the older private preimages and original metadata remain under PRE-CENTRAL-PROMOTION-1. Only the common private C/Rust prefix and corresponding binding/diffs were rebased; adapter/prologue/fixture bodies stayed exact.

Future HOST scope: C kmalloc_tracked mock records narrowed size/full flags and checks distinct exact C/Rust filename+line constants before returning opaque bits; no allocation/free/OOM logging. The exact three-command832-case recipe uses the complete genuine syscall-TU prologue and already-passed target/compiler context. Root must provide the specific ordinary CPU slot/grant, accepted04b5/adf admission, current aggregate and fixed-cutoff checks; no new supervisor or runtime authority is supplied.

Source checks pass exact reuse, inverse full-file selectors, one selected symbol, real typed ABI/ownership and frozen next argv. No compiler, actual context/allocation/mapping, real IRQ/IPC/final-ref/current-stack operation or native/default acceptance occurred. Those real provider/lifecycle holds stay open for the matching production integration and proof.

Tracked allocator fixture checks exact source-specific C and Rust filename/line constants separately; it does not waive metadata or equate Rust source provenance with old C coordinates.
