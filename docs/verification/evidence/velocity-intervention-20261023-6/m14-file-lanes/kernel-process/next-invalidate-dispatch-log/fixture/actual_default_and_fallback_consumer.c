/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY.
 * These are the actual callbacks passed by the unchanged Rust invalidate_one_page
 * entry to its existing body-result owner, not a new kernel helper.
 */
#include <process.h>
#include <memobj.h>
extern int process_memobj_invalidate_page_bridge(struct memobj *,uintptr_t,size_t);
extern void process_invalidate_one_page_log_bridge(void *,void *,void *,unsigned long,void *,int,int);
memobj_invalidate_page_func_t *const actual_dispatch_consumer=process_memobj_invalidate_page_bridge;
void (*const actual_error_consumer)(void *,void *,void *,unsigned long,void *,int,int)=process_invalidate_one_page_log_bridge;
