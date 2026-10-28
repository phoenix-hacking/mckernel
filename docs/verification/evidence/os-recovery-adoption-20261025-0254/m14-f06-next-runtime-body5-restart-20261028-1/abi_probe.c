/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <ihk/debug.h>
typedef int (*printer_abi)(const char *, ...);
typedef void (*bridge_abi)(int, int);
extern void arch_vdso_setup_log_bridge(int, int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf), printer_abi),
               "actual kernel printer variadic int result ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_vdso_setup_log_bridge), bridge_abi),
               "original public logger void/int32/int32 ABI");
_Static_assert(sizeof(int) == 4 && sizeof(char *) == 8 && sizeof(size_t) == 8,
               "supported int32/LP64 widths");
/* Witness the real ekprintf macro expansion against its genuine declaration. */
static void real_error_macro_witness(int error) { ekprintf("%d\n", error); }
int f06_vdso_setup_log_real_header_abi_witness;
