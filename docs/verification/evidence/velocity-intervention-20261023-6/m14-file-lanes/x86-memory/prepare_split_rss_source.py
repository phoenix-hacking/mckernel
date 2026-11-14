"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only split RSS callback pair; existing Rust owns accounting and cfg gates.
"""
from pathlib import Path
import difflib,hashlib,json,re
B=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel');S=B/'set-page-split-provider-fixture-preparation-1/candidate';P=B/'next-split-rss-source-only-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as o:o.write(s)
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs'
c=cp.read_text();r=rp.read_text();nc=c;olds=[]
for op in ['add','sub']:
 old='static void x86_split_rss_'+op+'_bridge(size_t size, size_t pgsize)\n{\n\tmemory_stat_rss_'+op+'(size, pgsize);\n}'
 assert nc.count(old)==1 and 'fn x86_split_rss_'+op+'_bridge(' not in r
 olds.append(old)
 nc=nc.replace(old,'#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC\nvoid x86_split_rss_'+op+'_bridge(size_t size, size_t pgsize);\n#else\n'+old+'\n#endif',1)
nc=re.sub(r'(?m)(#endif\n)#line [0-9]+',lambda m:m.group(1)+'#line '+str(nc[:m.end()].count('\n')+2),nc)
body='''// Keep the real size_t callback ABI and original unsigned-long/int endpoint
// conversion. Existing Rust accounting retains enable_rusage and atomic policy.
#[no_mangle]
pub unsafe extern "C" fn x86_split_rss_add_bridge(size: SizeT, pgsize: SizeT) {
    unsafe { crate::mem_helpers::memory_stat_rss_add(size as CULong, pgsize as CInt) }
}

#[no_mangle]
pub unsafe extern "C" fn x86_split_rss_sub_bridge(size: SizeT, pgsize: SizeT) {
    unsafe { crate::mem_helpers::memory_stat_rss_sub(size as CULong, pgsize as CInt) }
}
'''
nr=r+'\n'+body;patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
 put(P/'candidate'/rel,after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-SPLIT-RSS-CALLBACKS.patch',patch);put(P/'EXACT-ORIGINAL-C-PROVIDERS.inc','\n'.join(olds)+'\n');put(P/'EXACT-RUST-PROVIDERS.inc',body)
put(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_rss_add_bridge),x86_split_rss_fn_t),"split RSS add actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_rss_sub_bridge),x86_split_rss_fn_t),"split RSS sub actual callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&memory_stat_rss_add),void(*)(unsigned long,int)),"existing RSS add endpoint narrowing");
_Static_assert(__builtin_types_compatible_p(__typeof__(&memory_stat_rss_sub),void(*)(unsigned long,int)),"existing RSS sub endpoint narrowing");
_Static_assert(sizeof(size_t)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"actual conversion geometry");
/* PUBLIC old bodies excluded; same C split_large_page callback positions remain.
 * Future proof: exact Rust providers, actual C allocated pointer relocations,
 * coherent wholeTU and partial. No U or relocation invented from source alone.
 */
''')
put(P/'FUTURE-NARROWING-CONSUMER.NOT-QUEUED.c',r'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only original-C/Rust adapter fragment. This controlled endpoint scope
 * does not prove enabled accounting or atomic updates; actual mem_helpers owns
 * rusage conversion, atomic signed adds/negation and enable_rusage gating.
 */
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
static unsigned calls;static unsigned long seen_size;static int seen_pgsize,seen_op;
void memory_stat_rss_add(unsigned long size,int pgsize){++calls;seen_op=1;seen_size=size;seen_pgsize=pgsize;}
void memory_stat_rss_sub(unsigned long size,int pgsize){++calls;seen_op=-1;seen_size=size;seen_pgsize=pgsize;}
#include "EXACT-ORIGINAL-C-PROVIDERS.inc"
extern void rust_add(size_t,size_t) __asm__("x86_split_rss_add_bridge");
extern void rust_sub(size_t,size_t) __asm__("x86_split_rss_sub_bridge");
static void future_rss_case(size_t size,size_t pgsize,int subtract){
 calls=0;if(subtract)x86_split_rss_sub_bridge(size,pgsize);else x86_split_rss_add_bridge(size,pgsize);
 assert(calls==1);unsigned long s=seen_size;int p=seen_pgsize,op=seen_op;
 calls=0;if(subtract)rust_sub(size,pgsize);else rust_add(size,pgsize);
 assert(calls==1 && seen_size==s && seen_pgsize==p && seen_op==op);
}
/* Full-width sizes and pgsize including0,4096,2MiB,1GiB,INT_MAX,INT_MAX+1,
 * UINT_MAX,1UL<<32,1UL<<63,SIZE_MAX distinguish original size_t->int narrowing.
 * Keep exact original callback body and use assembler aliases only; new Rust
 * wrappers are exact saved bodies with controlled mem_helpers endpoint shims.
 * Later real accounting fixture must reuse actual Rust add/sub + RUSAGE layout,
 * rusage_pgsize_to_pgtype and atomic helper in both cfgs. No current run/queue.
 */
''')
auth=[ROOT/'kernel/include/rusage_private.h',ROOT/'kernel/rust/mem_helpers.rs',ROOT/'arch/x86_64/kernel/include/arch-memory-helpers.h']
data=dict(scope=__doc__,status='COMPLETE_SPLIT_RSS_ADD_SUB_SOURCE_ONLY',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-SPLIT-RSS-CALLBACKS.patch'),original_C=ref(P/'EXACT-ORIGINAL-C-PROVIDERS.inc'),authorities=[ref(p) for p in auth],semantics='Same size_t,size_t callback ABI; original C endpoint unsigned long size/int pgsize conversion preserved explicitly. Existing Rust memory_stat_rss_add/sub owns enable_rusage cfg, page-size slot mapping, atomic signed add and wrapping negative subtraction. Wrapper introduces no accounting or policy.',ownership='No pointer/reference/lock/free or callback retention. Existing split orchestration retains ordering and chooses which add/sub event to invoke; no duplicate accounting or feature gate.',fallback_C_byte_identical=True,new_C_function_getter=False,default_selection='PUBLIC declarations replace only these static definitions; actual existing C callback consumers unchanged. Real typed allocated relocations/Rust T/partial required later, output identities NULL.',fragments=[ref(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c'),ref(P/'FUTURE-NARROWING-CONSUMER.NOT-QUEUED.c')],sole_fixture_queue='set-page-split-provider-fixture-preparation-1/8281badb expected498, unexecuted',passed_four_provider_suffix='c03ce4ee frozen f13, central union3 binding pending',new_queue_CPU_reservation=None,actual_fixture_production_default_native=None,remaining_known_work='Split phys-to-page conversion and dynamic-debug/error/panic callback formats remain C. Reuse page_helpers phys_to_page and Rust kprintf/panic only with exact real metadata/selector witnesses; no guessed mutable debug semantics. Real physical ownership/default image/native proof remains open.',engineering_percentage=None)
put(P/'SOURCE-SPLIT-RSS-AND-INVARIANTS.NOT-EXECUTED.json',json.dumps(data,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-SPLIT-RSS-AND-INVARIANTS.NOT-EXECUTED.json'),postimages=data['postimages'],patch=data['patch'])))
