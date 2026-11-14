/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Compare these real compiler-derived values to the actual Rust ABI witness. */
#include <process.h>
#include <ihk/debug.h>
const unsigned long fixture_extend_actual_abi[] = {
 sizeof(struct process_vm), __alignof__(struct process_vm),
 __builtin_offsetof(struct process_vm,proc),
 sizeof(struct process), __alignof__(struct process),
 __builtin_offsetof(struct process,mpol_flags),
 __builtin_offsetof(struct process,heap_extension),
 sizeof(((struct process *)0)->mpol_flags),
 sizeof(((struct process *)0)->heap_extension),
 sizeof(struct ddebug), __alignof__(struct ddebug)
};
