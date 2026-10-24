"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only complete set-page lock orchestration, no second executable queue.
"""
from pathlib import Path
import difflib,hashlib,json,re
B=Path(__file__).resolve().parent;S=B/'next-set-page-log-source-only-1/candidate';P=B/'next-set-page-orchestration-source-only-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as o:o.write(s)
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs'
assert ref(cp)['sha256']=='5fafcfb02eef0e41c48b9b037c4233921e255cd467cc126226a77731b8abf4f4'
assert ref(rp)['sha256']=='8453f89bb7f87ab0dfa3f55159e1b15bd592b7457b28523f02401dad001a690a'
c=cp.read_text();r=rp.read_text()
start=c.index('static int __set_pt_page(');end=c.index('\n}\n',start)+2;old=c[start:end]
bridge='''X86_MEMORY_PUBLIC_BRIDGE int x86_pt_set_page_bridge(void *pt, unsigned long virt,
		unsigned long phys, unsigned long attr)
{
	return __set_pt_page(pt, (void *)virt, phys, attr);
}'''
assert c.count(bridge)==1
nc=c.replace(old,'#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC\n'+old+'\n#endif',1)
nc=nc.replace(bridge,'#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC\nint x86_pt_set_page_bridge(void *pt, unsigned long virt,\n\t\tunsigned long phys, unsigned long attr);\n#else\n'+bridge+'\n#endif',1)
nc=re.sub(r'(?m)(#endif\n)#line [0-9]+',lambda m:m.group(1)+'#line '+str(nc[:m.end()].count('\n')+2),nc)
foreign='    fn x86_pt_set_page_bridge(pt: *mut c_void, virt: CULong, phys: CULong, attr: CULong) -> CInt;\n'
assert r.count(foreign)==1
body='''// Complete original __set_pt_page orchestration. Use the existing IRQ-saving
// spinlock implementation and raw lock address; never borrow across callbacks.
#[no_mangle]
pub unsafe extern "C" fn x86_pt_set_page_bridge(
    pt: *mut c_void, virt: CULong, phys: CULong, attr: CULong,
) -> CInt {
    unsafe {
        let in_kernel = x86_pt_kernel_lock_needed_result(virt) != 0;
        let mut lock: *mut crate::abi::IhkSpinlock = core::ptr::null_mut();
        let mut flags: CULong = 0;
        if in_kernel {
            lock = x86_init_page_table_lock_bridge().cast();
            flags = crate::spinlock_helpers::__ihk_mc_spinlock_lock(lock);
        }
        // Read init_pt after acquisition, exactly as the original C body did.
        let ret = x86_pt_set_page_body_result(
            pt, x86_page_table_init_pt_bridge(), virt, phys, attr,
            x86_attr_mask_bridge(), Some(x86_pt_alloc_pages_bridge),
            Some(x86_pt_virt_to_phys_bridge), Some(x86_pt_phys_to_virt_bridge),
            Some(x86_pt_set_page_log_bridge),
        );
        if in_kernel {
            crate::spinlock_helpers::__ihk_mc_spinlock_unlock(lock, flags);
        }
        ret
    }
}
'''
nr=r.replace(foreign,'',1)+'\n'+body
patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
 put(P/'candidate'/rel,after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-SET-PAGE-ORCHESTRATION.patch',patch)
put(P/'EXACT-ORIGINAL-C-BODY.inc',old+'\n')
put(P/'EXACT-RUST-BODY.inc',body)
put(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_pt_set_page_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long)),"existing set-page public callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__ihk_mc_spinlock_lock),unsigned long(*)(ihk_spinlock_t*)),"actual return-flags lock ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&__ihk_mc_spinlock_unlock),void(*)(ihk_spinlock_t*,unsigned long)),"actual unlock flags ABI");
_Static_assert(sizeof(ihk_spinlock_t)==4 && __alignof__(ihk_spinlock_t)==4,"actual ticket-lock layout");
/* PUBLIC PP excludes __set_pt_page and C bridge definitions; fallback retains
 * both original bodies. Real selected Rust T/no self-U; preserve existing Rust
 * caller and actual remaining C allocated callback relocation when compiled.
 */
''')
# A source-only controlled endpoint fixture: exact saved C body and exact Rust
# body are included, not mirrored implementations. No compiler driver is added.
put(P/'FUTURE-ORIGINAL-C-RUST-CONSUMER.NOT-QUEUED.c',r'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
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
static int x86_pt_kernel_lock_needed_result(unsigned long v) { return v>=0xffff800000000000UL; }
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
''')
authorities=[Path('/home/holden/mckernel/arch/x86_64/kernel/include/arch-lock.h'),Path('/home/holden/mckernel/kernel/rust/spinlock_helpers.rs')]
data=dict(scope=__doc__,status='COMPLETE_SET_PAGE_LOCK_ORCHESTRATION_SOURCE_ONLY',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-SET-PAGE-ORCHESTRATION.patch'),actual_lock_authorities=[ref(p) for p in authorities],original_C=ref(P/'EXACT-ORIGINAL-C-BODY.inc'),Rust_body=ref(P/'EXACT-RUST-BODY.inc'),consumer='Existing Rust ihk_mc_pt_set_page/set_pt_large_page and map/setup callers use existing x86_pt_set_page_bridge symbol. C fallback-only __set_pt_page callers remain exact; C callback consumer remains declaration under PUBLIC.',invariant='Kernel address decision unchanged. Acquire same init_pt_lock through exact existing IRQ-saving Rust implementation; read init_pt only after acquisition; identical body helper/callback identities/raw arguments; unlock once with exact saved flags on every returned CInt. User addresses acquire no lock or new lock getter. No policy, ownership, error translation or cleanup added.',alias_lifetime='Only raw lock pointer crosses body callbacks; no Rust reference/mutable borrow retained. Existing table helper owns allocation/traversal; callback pointers never stored beyond synchronous call. Existing static lock/init_pt/mask getter providers reused; no new C functions/getters.',selection='PUBLIC excludes complete original __set_pt_page plus C bridge body, preserves exact declaration and real C fallback. Remove foreign self-import and supply unique Rust T; actual wholeTU/Rust/partial/default/native remain NULL.',retained_untested_predecessors='Reason/helper-error/log source remains untested separately; no fixture acceptance inferred from source merge. Production four-provider suffix remains f13 only.',fragments=[ref(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c'),ref(P/'FUTURE-ORIGINAL-C-RUST-CONSUMER.NOT-QUEUED.c')],new_executable_queue=None,sole_queue='passed-four-provider-union2-production-suffix-preparation-1/c03ce4ee',actual_fixture_production_default_native=None,engineering_percentage=None)
put(P/'SOURCE-SET-PAGE-ORCHESTRATION-AND-INVARIANTS.NOT-EXECUTED.json',json.dumps(data,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-SET-PAGE-ORCHESTRATION-AND-INVARIANTS.NOT-EXECUTED.json'),postimages=data['postimages'],patch=data['patch'])))
