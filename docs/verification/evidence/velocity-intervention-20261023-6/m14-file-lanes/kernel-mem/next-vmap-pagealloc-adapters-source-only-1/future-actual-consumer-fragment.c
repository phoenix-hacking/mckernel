/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only future boundary fixture; no main/driver/second queue.
 * Link actual original C wrappers and the proposed Rust wrappers. Production
 * public allocator algorithm remains the existing Rust page_alloc module.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
struct vmap_call{unsigned calls,kind;unsigned long start,size,unit,address;void *desc;int npages,p2align;};
static struct vmap_call call;static void *init_return;static unsigned long alloc_return;
void *ihk_pagealloc_init(unsigned long s,unsigned long n,unsigned long u){call.calls++;call.kind=1;call.start=s;call.size=n;call.unit=u;return init_return;}
unsigned long ihk_pagealloc_alloc(void *d,int n,int a){call.calls++;call.kind=2;call.desc=d;call.npages=n;call.p2align=a;return alloc_return;}
void ihk_pagealloc_free(void *d,unsigned long a,int n){call.calls++;call.kind=3;call.desc=d;call.address=a;call.npages=n;}
typedef void *(*init_cb)(unsigned long,unsigned long,unsigned long);
typedef unsigned long(*alloc_cb)(void*,int,int);
typedef void(*free_cb)(void*,unsigned long,int);
static int init_actual_pair(init_cb a,init_cb b,unsigned long s,unsigned long n,unsigned long u,void *result){struct vmap_call first;init_return=result;memset(&call,0,sizeof call);void *x=a(s,n,u);first=call;memset(&call,0,sizeof call);void *y=b(s,n,u);return x!=result||x!=y||first.calls!=1||call.calls!=1||memcmp(&first,&call,sizeof call);}
static int alloc_actual_pair(alloc_cb a,alloc_cb b,void *d,int n,int p,unsigned long result){struct vmap_call first;alloc_return=result;memset(&call,0,sizeof call);unsigned long x=a(d,n,p);first=call;memset(&call,0,sizeof call);unsigned long y=b(d,n,p);return x!=result||x!=y||first.calls!=1||call.calls!=1||memcmp(&first,&call,sizeof call);}
static int free_actual_pair(free_cb a,free_cb b,void *d,unsigned long address,int n){struct vmap_call first;memset(&call,0,sizeof call);a(d,address,n);first=call;memset(&call,0,sizeof call);b(d,address,n);return first.calls!=1||call.calls!=1||memcmp(&first,&call,sizeof call);}
/* Future vectors preserve zero/ULONG_MAX address/size/unit, NULL/live opaque
 * descriptors, INT_MIN/-1/0/1/INT_MAX npages and p2align, exact zero/nonzero
 * provider returns and exactly one call. Invalid inputs are forwarded unchanged
 * to the existing provider; no clamp/new NULL/error policy or invented free ACK.
 * Real fullcrate+wholememTU/allocatedcall/partial must separately prove direct
 * public Rust provider binding, not claim allocator internals from this mock.
 */
