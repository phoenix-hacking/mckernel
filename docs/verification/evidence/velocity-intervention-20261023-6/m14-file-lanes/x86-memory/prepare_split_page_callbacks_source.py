"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only split page-map/unmap callback ownership handoff; no executable queue.
"""
from pathlib import Path
import difflib,hashlib,json,re
B=Path(__file__).resolve().parent;S=B/'next-split-alloc-source-only-1/candidate';P=B/'next-split-page-callbacks-source-only-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as o:o.write(s)
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs'
assert ref(cp)['sha256']=='332cc62ca7823fe10fd6902e6b06ec6fed9f52d57174302adc38dfb30c73d28f'
assert ref(rp)['sha256']=='61b55c2489c7eef22c11c0d2535135da039542e8a704a908f37aa75a5cba3530'
c=cp.read_text();r=rp.read_text();nc=c
old_map='''static void x86_split_page_map_bridge(void *page)
{
	page_map(page);
}'''
old_unmap='''static int x86_split_page_unmap_bridge(void *page)
{
	return page_unmap(page);
}'''
for old,decl in [(old_map,'void x86_split_page_map_bridge(void *page);'),(old_unmap,'int x86_split_page_unmap_bridge(void *page);')]:
 assert nc.count(old)==1
 nc=nc.replace(old,'#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC\n'+decl+'\n#else\n'+old+'\n#endif',1)
nc=re.sub(r'(?m)(#endif\n)#line [0-9]+',lambda m:m.group(1)+'#line '+str(nc[:m.end()].count('\n')+2),nc)
body='''// Preserve the split callback's exact raw page identity and synchronous
// ownership handoff to the already Rust-owned page-map/unmap implementations.
#[no_mangle]
pub unsafe extern "C" fn x86_split_page_map_bridge(page: *mut c_void) {
    unsafe { crate::page_helpers::page_map(page.cast::<Page>()) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_page_unmap_bridge(page: *mut c_void) -> CInt {
    unsafe { crate::page_helpers::page_unmap(page.cast::<Page>()) }
}
'''
assert 'fn x86_split_page_map_bridge(' not in r and 'fn x86_split_page_unmap_bridge(' not in r
nr=r+'\n'+body;patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
 put(P/'candidate'/rel,after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-SPLIT-PAGE-CALLBACKS.patch',patch);put(P/'EXACT-ORIGINAL-C-PROVIDERS.inc',old_map+'\n'+old_unmap+'\n');put(P/'EXACT-RUST-PROVIDERS.inc',body)
put(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_page_map_bridge),x86_split_page_map_fn_t),"actual split map callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_page_unmap_bridge),x86_split_page_unmap_fn_t),"actual split unmap callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_map),void(*)(struct page*)),"existing real page-map endpoint");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_unmap),int(*)(struct page*)),"existing real page-unmap endpoint");
/* PUBLIC bodies excluded; existing split_large_page pointer consumers remain,
 * unique Rust providers/actual allocated relocs/partial proof must follow.
 */
''')
put(P/'FUTURE-RAW-PAGE-CONSUMER.NOT-QUEUED.c',r'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only controlled endpoint fragment. Does not dereference page sentinels.
 */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
static void *seen;static unsigned calls;static int endpoint_ret;
void page_map(void *page) { ++calls;seen=page; }
int page_unmap(void *page) { ++calls;seen=page;return endpoint_ret; }
#include "EXACT-ORIGINAL-C-PROVIDERS.inc"
extern void rust_map(void*) __asm__("x86_split_page_map_bridge");
extern int rust_unmap(void*) __asm__("x86_split_page_unmap_bridge");
static void future_page_case(void *page,int ret) {
 calls=0;seen=0;x86_split_page_map_bridge(page);assert(calls==1 && seen==page);
 calls=0;seen=0;rust_map(page);assert(calls==1 && seen==page);
 endpoint_ret=ret;calls=0;seen=0;int a=x86_split_page_unmap_bridge(page);
 assert(calls==1 && seen==page && a==ret);
 calls=0;seen=0;int b=rust_unmap(page);assert(calls==1 && seen==page && b==a);
}
/* Future exact extracted Rust bodies use mock crate::page_helpers::page_map and
 * page_unmap shims calling these actual C endpoints. Alias the two original
 * static definitions to original_C_* assembler names only; preserve body bytes.
 * Valid aligned object and controlled sentinel bit patterns (including NULL)
 * establish unchanged transport/no added null policy ONLY. Real production
 * page helpers require their existing lifetime/lock/page ownership contract;
 * sentinel vectors never enter actual page helpers. Test CInt0/1/-1/min/max.
 * No refcount/hashlock/free/real page mapping, native or partial-link credit.
 */
''')
auth=[Path('/home/holden/mckernel/kernel/include/page.h'),Path('/home/holden/mckernel/kernel/rust/page_helpers.rs')]
data=dict(scope=__doc__,status='COMPLETE_SPLIT_PAGE_MAP_UNMAP_CALLBACKS_SOURCE_ONLY',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-SPLIT-PAGE-CALLBACKS.patch'),authorities=[ref(p) for p in auth],original_C=ref(P/'EXACT-ORIGINAL-C-PROVIDERS.inc'),existing_Rust_reuse='crate::page_helpers::page_map and page_unmap are already no_mangle Rust production providers with exact actual page.h ABI. Direct call preserves same target, Page pointer identity and synchronous CInt return.',ownership='No page dereference/reference, new null policy, refcount/free/accounting/lock introduced in adapters. Existing split orchestration still chooses call order and interprets map/unmap results; existing page helpers own atomic count and hash locking/lifetime. Raw pointer cast only and no borrow crosses a callback.',fallback_C_byte_identical=True,new_C_function_getter=False,selection='PUBLIC retains existing callback declarations and excludes only original static bodies. Existing split_large_page callback arguments unchanged; future actual wholeTU/allocated relocs/Rust unique providers and partial remain NULL.',source_only_predecessors='Set-page orchestration cb4f7036 and split allocator03da72d7 remain untested source; original four-provider production queue remains f13 and excludes these changes.',fragments=[ref(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c'),ref(P/'FUTURE-RAW-PAGE-CONSUMER.NOT-QUEUED.c')],sole_executable_queue='passed-four-provider-union2-production-suffix-preparation-1/c03ce4ee',new_queue_CPU_reservation=None,actual_fixture_production_default_native=None,held_remaining_major_bodies='Split physical-page translation, split RSS/log/panic callbacks still live C; existing Rust phys/page/RSS/kprintf/panic can supply them with exact metadata/format witnesses. Split allocator/set-page lock orchestration and page callbacks now source-only, need actual tests. Physical ownership/real allocation and full default-linked/native path remain harder than callback transport.',engineering_percentage=None)
put(P/'SOURCE-SPLIT-PAGE-CALLBACKS-AND-INVARIANTS.NOT-EXECUTED.json',json.dumps(data,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-SPLIT-PAGE-CALLBACKS-AND-INVARIANTS.NOT-EXECUTED.json'),postimages=data['postimages'],patch=data['patch'])))
