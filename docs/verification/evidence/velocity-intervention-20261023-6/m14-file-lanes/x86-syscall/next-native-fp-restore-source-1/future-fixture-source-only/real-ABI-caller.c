/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Future HOST consumer source only. Hardware/reset/allocator/user-copy providers
 * must be controlled; retain actual Rust xstate validators and original C body.
 */
#include <types.h>
#include <kmalloc.h>
#include <errno.h>
extern long arch_native_signal_restore_fp_bridge(unsigned long,int);
typedef long (*actual_native_fp_restore_entry)(unsigned long,int);
_Static_assert(sizeof(long)==8 && sizeof(void *)==8 && sizeof(int)==4,"LP64 native FP callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_native_signal_restore_fp_bridge),actual_native_fp_restore_entry),"actual callback prototype");
_Static_assert((65536+63)<=2147483647,"existing int tracked allocator extent");
struct f06_native_fp_case {unsigned long address;int provided,configured,allocation_offset,allocation_fails,copy_result;unsigned long xfeatures;unsigned int mxcsr_mask;long restore_result;};
/* Each source case runs original selected C and complete public Rust entry with
 * the same live bounded buffers. Compare getter/reset/alloc/copy/mask/validate/
 * checked-restore/free traces, exact results and one ORIGINAL-base free.
 */
static const struct f06_native_fp_case f06_native_fp_cases[]={
 {0,576,576,0,0,0,3,0xffbf,0},
 {0,0,0,0,0,0,3,0xffbf,-95},
 {1,-1,576,0,0,0,3,0xffbf,0},
 {1,511,511,0,0,0,3,0xffbf,0},
 {1,65537,65537,0,0,0,3,0xffbf,0},
 {1,576,576,1,1,0,3,0xffbf,0},
 {1,576,576,31,0,-14,3,0xffbf,0},
 {1,576,576,63,0,3,3,0xffbf,0},
 {1,576,576,0,0,0,3,0xffbf,0},
 {1,576,576,1,0,0,1,0xffbf,0},
 {1,576,576,31,0,0,3,0,0},
 {1,576,576,63,0,0,3,0x10000,0},
 {1,576,576,1,0,0,3,0xffbf,-14},
 {1,832,832,31,0,0,3,0xffbf,7},
 {1,65536,65536,63,0,0,3,0xffbf,0},
 {1,832,576,0,0,0,3,0xffbf,0},
};
/* Additional byte variants: invalidMXCSR, unallowedstateBV, compactedBV and
 * reservedheader528..575. All64 original allocation alignments must be used.
 * Tracker file/line identify the C-vs-Rust source and are preserved as separate
 * provenance, never used as allocation-owner equality. No test driver yet.
 */
