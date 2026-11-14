/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Future real-helper consumer fragment; no main/driver/second queue.
 * Use production arrays/geometry and actual Rust helpers/providers. IRQ/preempt
 * endpoints may be controlled, but no fake Page, mapping or reference ACK.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
typedef struct page *(*physical_lookup)(uintptr_t);
extern struct list_head page_hash[];
extern ihk_spinlock_t page_hash_locks[];
extern const int page_init_hash_bucket_count;
extern const unsigned long page_init_hash_head_stride,page_unmap_lock_stride;
/* Source-bound future driver constructs live Page/hash nodes with the real C
 * Page layout and exact phys field, preserving collision-chain insertion order.
 * The caller holds those Pages live until BOTH returned pointers are checked.
 */
static int phys_lookup_actual_pair(physical_lookup original,physical_lookup replacement,
 uintptr_t physical,struct page *expected,unsigned char *before_heads,
 unsigned char *before_locks,unsigned char *saved_heads,unsigned char *saved_locks)
{
 unsigned long heads=(unsigned long)page_init_hash_bucket_count*page_init_hash_head_stride;
 unsigned long locks=(unsigned long)page_init_hash_bucket_count*page_unmap_lock_stride;
 memcpy(before_heads,page_hash,heads);memcpy(before_locks,page_hash_locks,locks);
 struct page *a=original(physical);memcpy(saved_heads,page_hash,heads);memcpy(saved_locks,page_hash_locks,locks);
 memcpy(page_hash,before_heads,heads);memcpy(page_hash_locks,before_locks,locks);
 struct page *b=replacement(physical);
 return a!=expected||a!=b||memcmp(saved_heads,page_hash,heads)||memcmp(saved_locks,page_hash_locks,locks);
}
/* Future vectors: emptyhash; phys0; PAGE_SIZE-1/PAGE_SIZE/PAGE_SIZE+1;
 * ULONG_MAX; exactmatch/miss/collisions in first/middle/lastbucket; multiple
 * equal-page-base but different lowbits (the helper compares exact phys, not
 * masked pagebase). Trace must observe one save/disable/lock and matching
 * unlock/enable/restore before pointer return; count/ref/offset/mode immutable.
 * Existing bad-shift/null-callback/checked-addr-overflow helper errors are reused
 * unchanged, not new wrapper policies. No allocation/free/log/mapping effect.
 */
