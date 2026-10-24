/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Future fixture fragment only, no main/commands. Actual original C wrapper
 * (rename only) and replacement Rust export are the compared callbacks.
 * Link real page_helpers::page_hash_tables_init_body_result and actual lockinit.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
/* Production definitions/geometry must be extracted from the actual selected C
 * source; do not invent table count or replace providers with zero-return stubs.
 * The future driver binds PHYS_PAGE_HASH_SIZE and these actual array symbols. */
extern struct list_head page_hash[];
extern ihk_spinlock_t page_hash_locks[];
extern const int page_init_hash_bucket_count;
extern const unsigned long page_init_hash_head_stride;
extern const unsigned long page_unmap_lock_stride;
typedef void(*page_initializer)(void);
static int page_init_real_consumer(page_initializer original,page_initializer replacement,
 unsigned char *saved_heads,unsigned char *saved_locks)
{
 int n=page_init_hash_bucket_count;
 unsigned long hbytes=(unsigned long)n*page_init_hash_head_stride;
 unsigned long lbytes=(unsigned long)n*page_unmap_lock_stride;
 memset(page_hash,0xa5,hbytes);memset(page_hash_locks,0xa5,lbytes);
 original();memcpy(saved_heads,page_hash,hbytes);memcpy(saved_locks,page_hash_locks,lbytes);
 memset(page_hash,0xa5,hbytes);memset(page_hash_locks,0xa5,lbytes);
 replacement();
 if(memcmp(saved_heads,page_hash,hbytes)||memcmp(saved_locks,page_hash_locks,lbytes))return 1;
 for(int i=0;i<n;i++){
  struct list_head *head=(struct list_head*)((unsigned long)page_hash+(unsigned long)i*page_init_hash_head_stride);
  ihk_spinlock_t *lock=(ihk_spinlock_t*)((unsigned long)page_hash_locks+(unsigned long)i*page_unmap_lock_stride);
  if(head->next!=head||head->prev!=head||lock->head_tail)return 2;
 }
 return 0;
}
/* Additional future boundary oracle: capture the single exact helper invocation
 * and typed callback addresses, return {-EINVAL,0,n,INT_MAX} without invoking
 * them, and require both void wrappers to discard the value unchanged. This is
 * separate from the real-helper memory comparison above; never fake init or
 * infer mapping/Page allocation ownership. Existing helper checks negativecount,
 * missingcallback and checked address overflow before each lock->bucket step.
 */
