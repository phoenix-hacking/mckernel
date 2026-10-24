"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only split physical-page adapter; existing lower phys_to_page C debt retained.
"""
from pathlib import Path
import difflib,hashlib,json,re
B=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel');S=B/'next-split-rss-source-only-1/candidate';P=B/'next-split-phys-page-source-only-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as o:o.write(s)
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs';c=cp.read_text();r=rp.read_text()
assert ref(cp)['sha256']=='579238399aff33d488e483fb11a4fa5c94cfdc96188ddd46c33720c2e3aa135d'
assert ref(rp)['sha256']=='cd91b8d289ebac4c9573501a3004368b479ffd5fa5cae1bf26c32f29f4ce4134'
old='''static void *x86_split_phys_to_page_bridge(unsigned long phys)
{
	return phys_to_page(phys);
}'''
assert c.count(old)==1 and 'fn x86_split_phys_to_page_bridge(' not in r
assert r.count('    fn phys_to_page(phys: CULong) -> *mut Page;')==1
nc=c.replace(old,'#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC\nvoid *x86_split_phys_to_page_bridge(unsigned long phys);\n#else\n'+old+'\n#endif',1)
nc=re.sub(r'(?m)(#endif\n)#line [0-9]+',lambda m:m.group(1)+'#line '+str(nc[:m.end()].count('\n')+2),nc)
body='''// Preserve the exact existing physical-page lookup endpoint and pointer bits.
// Its lower C geometry/lookup wrapper remains debt; no new page/null policy.
#[no_mangle]
pub unsafe extern "C" fn x86_split_phys_to_page_bridge(phys: CULong) -> *mut c_void {
    unsafe { phys_to_page(phys).cast::<c_void>() }
}
'''
nr=r+'\n'+body;patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
 put(P/'candidate'/rel,after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-SPLIT-PHYS-PAGE.patch',patch);put(P/'EXACT-ORIGINAL-C-PROVIDER.inc',old+'\n');put(P/'EXACT-RUST-PROVIDER.inc',body)
put(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_phys_to_page_bridge),x86_split_phys_to_page_fn_t),"actual split physical-page callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_page),struct page*(*)(uintptr_t)),"actual existing page lookup endpoint ABI");
_Static_assert(sizeof(uintptr_t)==sizeof(unsigned long),"unchanged physical address geometry");
/* PUBLIC C body absent, original C callback position unchanged. Future actual
 * Rust unique T and selected C allocated relocation required, not assumed.
 */
''')
put(P/'FUTURE-PHYS-POINTER-CONSUMER.NOT-QUEUED.c',r'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only exact-original-C/Rust raw adapter fragment. Controlled lower
 * endpoint, never actual physical memory, hash locking or page lifetime proof.
 */
#include <assert.h>
#include <stdint.h>
struct page;
static unsigned calls;static unsigned long seen;static struct page *answer;
struct page *phys_to_page(uintptr_t phys){++calls;seen=phys;return answer;}
#include "EXACT-ORIGINAL-C-PROVIDER.inc"
extern void *rust_phys(unsigned long) __asm__("x86_split_phys_to_page_bridge");
static void future_phys_case(unsigned long phys,struct page *result){
 answer=result;calls=0;void*a=x86_split_phys_to_page_bridge(phys);assert(calls==1 && seen==phys && a==(void*)answer);
 calls=0;void*b=rust_phys(phys);assert(calls==1 && seen==phys && b==a);
}
/* Actual saved Rust adapter uses its existing foreign phys_to_page declaration.
 * Alias original C static symbol only; full-width physical values and NULL/real
 * aligned observer-owned page/sentinel results test transport without dereference.
 * No invented Page alignment/range validation or NULL rejection. No new queue.
 * A deeper lookup test must reuse real Rust phys_to_page_lookup_body_result
 * with actual C geometry/lock providers; lower C phys_to_page remains debt.
 */
''')
data=dict(scope=__doc__,status='COMPLETE_SPLIT_PHYSICAL_PAGE_ADAPTER_SOURCE_ONLY',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-SPLIT-PHYS-PAGE.patch'),original_C=ref(P/'EXACT-ORIGINAL-C-PROVIDER.inc'),actual_endpoint_header=ref(ROOT/'kernel/include/page.h'),semantics='Exactly one synchronous call through existing phys_to_page foreign ABI, unchanged unsigned-long physical input and raw Page pointer/NULL output. Pointer cast only; no dereference, range test, new null policy or retained reference.',honest_lower_provider_debt='phys_to_page itself remains existing kernel/mem.c C geometry/lookup orchestration backed by actual Rust page_helpers lookup bodies. There is NO page_helpers::phys_to_page export; this port does not invent one or claim complete lower C retirement.',ownership='Original lower lookup endpoint retains hash locking/lifetime/ownership; new adapter introduces no allocation/free/account/ref/lock, and split orchestration still owns call position.',fallback_C_byte_identical=True,new_C_function_getter=False,fragments=[ref(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c'),ref(P/'FUTURE-PHYS-POINTER-CONSUMER.NOT-QUEUED.c')],sole_executable_fixture='set-page-split-provider-fixture-preparation-1/observer-header-inclusion-correction-1/23cea341 source-only; original01 Rust passed, failed02 bounded correction waiting root grant',new_queue_CPU_reservation=None,actual_fixture_production_default_native=None,remaining_major='Split log debug descriptors/format and panic callback remain C; reuse existing Rust logger/panic after exact selector metadata witness. Lower physical lookup/page accounting ownership and full default-linked/native path remain open.',engineering_percentage=None)
put(P/'SOURCE-SPLIT-PHYS-PAGE-AND-INVARIANTS.NOT-EXECUTED.json',json.dumps(data,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-SPLIT-PHYS-PAGE-AND-INVARIANTS.NOT-EXECUTED.json'),postimages=data['postimages'],patch=data['patch'])))
