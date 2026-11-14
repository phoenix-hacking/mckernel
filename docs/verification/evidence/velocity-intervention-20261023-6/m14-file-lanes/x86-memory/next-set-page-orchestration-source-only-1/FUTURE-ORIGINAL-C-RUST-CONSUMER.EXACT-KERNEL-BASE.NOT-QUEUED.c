/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source fragment only. Controlled lock/body endpoints, not real IRQ/page proof.
 */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <string.h>
struct page_table { unsigned long unused; };
typedef struct { unsigned int head_tail; } ihk_spinlock_t;
enum ihk_mc_pt_attribute { ATTR_ZERO=0,ATTR_FORCE_64=ULONG_MAX };
static ihk_spinlock_t init_pt_lock;
static struct page_table table_a,table_b,*init_pt;
static unsigned long ATTR_MASK,expected_flags;
static int held,kernel_case,body_result;
static unsigned events[4],event_count;
static void *captured[6];static unsigned long args[4];
static int x86_pt_kernel_lock_needed_result(unsigned long v) { return v>=0xffff000000000000UL; }
unsigned long fixture_lock(void *p) {
 assert(p==&init_pt_lock && !held && kernel_case);held=1;
 events[event_count++]=1;init_pt=&table_b;return expected_flags;
}
void fixture_unlock(void *p,unsigned long flags) {
 assert(p==&init_pt_lock && held && flags==expected_flags);
 events[event_count++]=3;held=0;
}
#define ihk_mc_spinlock_lock(p) fixture_lock(p)
#define ihk_mc_spinlock_unlock(p,f) fixture_unlock(p,f)
void *x86_init_page_table_lock_bridge(void) { assert(kernel_case);return &init_pt_lock; }
void *x86_page_table_init_pt_bridge(void) { assert(held==kernel_case);return init_pt; }
unsigned long x86_attr_mask_bridge(void) { assert(held==kernel_case);return ATTR_MASK; }
void *x86_pt_alloc_pages_bridge(int n,int f) { (void)n;(void)f;assert(0);return 0; }
unsigned long x86_pt_virt_to_phys_bridge(void *p) { (void)p;assert(0);return 0; }
void *x86_pt_phys_to_virt_bridge(unsigned long p) { (void)p;assert(0);return 0; }
void x86_pt_set_page_log_bridge(unsigned long p) { (void)p;assert(0); }
int x86_pt_set_page_body_result(void *pt,void *ip,unsigned long v,unsigned long p,
 unsigned long a,unsigned long mask,void *(*alloc)(int,int),
 unsigned long(*vp)(void*),void *(*pv)(unsigned long),void(*log)(unsigned long)) {
 assert(held==kernel_case);events[event_count++]=2;
 assert(alloc==x86_pt_alloc_pages_bridge && vp==x86_pt_virt_to_phys_bridge);
 assert(pv==x86_pt_phys_to_virt_bridge && log==x86_pt_set_page_log_bridge);
 captured[0]=pt;captured[1]=ip;args[0]=v;args[1]=p;args[2]=a;args[3]=mask;
 return body_result;
}
#include "EXACT-ORIGINAL-C-BODY.inc"
extern int x86_pt_set_page_bridge(void*,unsigned long,unsigned long,unsigned long);
static void reset(unsigned long virt) {
 held=0;event_count=0;init_pt=&table_a;kernel_case=x86_pt_kernel_lock_needed_result(virt);
 memset(events,0,sizeof(events));memset(captured,0,sizeof(captured));memset(args,0,sizeof(args));
}
static void future_case(void *pt,unsigned long v,unsigned long p,unsigned long attr,int ret) {
 body_result=ret;reset(v);int a=__set_pt_page(pt,(void*)v,p,(enum ihk_mc_pt_attribute)attr);
 assert(!held && a==ret && event_count==(kernel_case?3U:1U));
 assert(captured[1]==(kernel_case?(void*)&table_b:(void*)&table_a));
 unsigned want_events[4],n=event_count;void *want_ptrs[6];unsigned long want_args[4];
 memcpy(want_events,events,sizeof(events));memcpy(want_ptrs,captured,sizeof(captured));memcpy(want_args,args,sizeof(args));
 reset(v);int b=x86_pt_set_page_bridge(pt,v,p,attr);
 assert(!held && b==a && n==event_count && !memcmp(want_events,events,sizeof(events)));
 assert(!memcmp(want_ptrs,captured,sizeof(captured)) && !memcmp(want_args,args,sizeof(args)));
}
/* Future bounded harness calls future_case across pt=NULL/table_a/table_b,
 * virt=0,KERNEL_BASE-1,KERNEL_BASE,ULONG_MAX; full-width physical/attr/mask/flags
 * and returns0/-ENOMEM/-EBUSY/INT_MIN/INT_MAX. Add no real IRQ execution.
 * Rust fixture extracts EXACT-RUST-BODY.inc unchanged and supplies crate::abi
 * IhkSpinlock plus spinlock_helpers shims calling fixture_lock/unlock. Other
 * endpoints use these actual C symbols, including complete callback identities.
 * This controlled endpoint test qualifies only orchestration, never table
 * mutation/real allocator/lock contention/interrupt execution/native ownership.
 */
