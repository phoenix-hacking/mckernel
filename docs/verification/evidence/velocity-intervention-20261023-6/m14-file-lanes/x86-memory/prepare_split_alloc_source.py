"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only split page-table allocator; no second executable queue.
"""
from pathlib import Path
import difflib,hashlib,json,re
B=Path(__file__).resolve().parent;S=B/'next-set-page-orchestration-source-only-1/candidate';P=B/'next-split-alloc-source-only-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as o:o.write(s)
assert not P.exists()
cp=S/'arch/x86_64/kernel/memory.c';rp=S/'kernel/rust/x86_memory_helpers.rs'
assert ref(cp)['sha256']=='797768b1adcacccfce7ce89f507c768592a757e7c28040f46e6b430db0c8ac2e'
assert ref(rp)['sha256']=='f5f555b2c12f2444d5a7e71a7d1747acd31388488bea18f3ea02a812804081de'
c=cp.read_text();r=rp.read_text()
old='''static void *x86_split_alloc_new_pt_bridge(int nr_pages, int ap_flag)
{
	if (nr_pages != 1)
		return NULL;
	return __alloc_new_pt((ihk_mc_ap_flag)ap_flag);
}'''
assert c.count(old)==1 and 'fn x86_split_alloc_new_pt_bridge(' not in r
nc=c.replace(old,'#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC\nvoid *x86_split_alloc_new_pt_bridge(int nr_pages, int ap_flag);\n#else\n'+old+'\n#endif',1)
nc=re.sub(r'(?m)(#endif\n)#line [0-9]+',lambda m:m.group(1)+'#line '+str(nc[:m.end()].count('\n')+2),nc)
body='''// The original split callback allocates exactly one zeroed table. Preserve
// rejected counts without touching the allocator and every signed flag bit.
#[no_mangle]
pub unsafe extern "C" fn x86_split_alloc_new_pt_bridge(
    nr_pages: CInt, ap_flag: CInt,
) -> *mut c_void {
    if nr_pages != 1 {
        return core::ptr::null_mut();
    }
    unsafe { x86_pt_alloc_zeroed_result(ap_flag, Some(x86_pt_alloc_pages_bridge)) }
}
'''
nr=r+'\n'+body;patch=''
for rel,before,after in [('arch/x86_64/kernel/memory.c',c,nc),('kernel/rust/x86_memory_helpers.rs',r,nr)]:
 put(P/'candidate'/rel,after);patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
put(P/'EXACT-SPLIT-ALLOC-SOURCE.patch',patch);put(P/'EXACT-ORIGINAL-C-PROVIDER.inc',old+'\n');put(P/'EXACT-RUST-PROVIDER.inc',body)
a=c.index('static struct page_table *__alloc_new_pt(');b=c.index('\n}\n',a)+2
put(P/'EXACT-ORIGINAL-C-HELPER.inc',c[a:b]+'\n')
a=r.index('#[no_mangle]\npub unsafe extern "C" fn x86_pt_alloc_zeroed_result(');b=r.index('\n}\n',a)+2
put(P/'EXACT-EXISTING-RUST-ZEROING-HELPER.inc',r[a:b]+'\n')
put(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c',f'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "{P/'candidate/arch/x86_64/kernel/memory.c'}"
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_split_alloc_new_pt_bridge),x86_pt_alloc_pages_fn_t),"split allocator actual callback ABI");
_Static_assert(sizeof(ihk_mc_ap_flag)==8 && sizeof(int)==4,"actual flag narrowing closure");
/* Original int->ihk_mc_ap_flag(unsigned long)->x86_pt_alloc_zeroed_result(int)
 * preserves the original int bits; new Rust passes that same int unchanged.
 * Real PUBLIC C whole TU must retain split_large_page's allocated callback
 * relocation and exclude only this original callback body, with Rust unique T.
 */
''')
put(P/'FUTURE-ALLOCATOR-ZEROING-CONSUMER.NOT-QUEUED.c',r'''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source fragment only; exact original helpers and actual Rust zeroing reused.
 */
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
struct page_table { unsigned long entries[512]; };
typedef unsigned long ihk_mc_ap_flag;
static struct page_table memory[2];
static unsigned calls;static int seen_count,seen_flags,mode;
void *x86_pt_alloc_pages_bridge(int n,int f) {
 ++calls;seen_count=n;seen_flags=f;
 return mode<0?NULL:&memory[mode];
}
extern void *x86_pt_alloc_zeroed_result(int,void *(*)(int,int));
#include "EXACT-ORIGINAL-C-HELPER.inc"
#include "EXACT-ORIGINAL-C-PROVIDER.inc"
extern void *rust_split_alloc(int,int) __asm__("x86_split_alloc_new_pt_bridge");
static void future_split_alloc_case(int count,int flags,int result_mode) {
 mode=result_mode;calls=0;seen_count=seen_flags=0;
 memset(memory,0xa5,sizeof(memory));
 void *a=x86_split_alloc_new_pt_bridge(count,flags);
 unsigned want_calls=calls;int want_n=seen_count,want_f=seen_flags;
 unsigned char expected[sizeof(memory)];memcpy(expected,memory,sizeof(memory));
 calls=0;seen_count=seen_flags=0;memset(memory,0xa5,sizeof(memory));
 void *b=rust_split_alloc(count,flags);
 assert(a==b && calls==want_calls && seen_count==want_n && seen_flags==want_f);
 assert(!memcmp(expected,memory,sizeof(memory)));
 assert(calls==(count==1?1U:0U));
 if(count==1) {
  assert(seen_count==1 && seen_flags==flags);
  if(mode>=0) for(unsigned i=0;i<512;i++)assert(memory[mode].entries[i]==0);
 } else assert(a==NULL);
}
/* Counts INT_MIN,-2,-1,0,1,2,3,512,INT_MAX; original signed flags and NULL/two
 * actual aligned static buffers. Extract exact saved Rust wrapper+zeroing helper
 * into the future Rust fixture, retain PT_ENTRIES=512/write_bytes actual source.
 * Original static symbol must use an assembler alias original_C_split_alloc;
 * Rust symbol uses its existing public name. No body rewriting beyond alias.
 * This proves only gated callback/zeroing behavior, not real allocation failure
 * policy, page ownership publication, TLB effects or native split execution.
 */
''')
data=dict(scope=__doc__,status='COMPLETE_SPLIT_ALLOCATOR_SOURCE_ONLY',preimages=[ref(cp),ref(rp)],postimages=[ref(P/'candidate/arch/x86_64/kernel/memory.c'),ref(P/'candidate/kernel/rust/x86_memory_helpers.rs')],patch=ref(P/'EXACT-SPLIT-ALLOC-SOURCE.patch'),original_C=[ref(P/'EXACT-ORIGINAL-C-PROVIDER.inc'),ref(P/'EXACT-ORIGINAL-C-HELPER.inc')],existing_Rust=ref(P/'EXACT-EXISTING-RUST-ZEROING-HELPER.inc'),consumer='Existing C split_large_page passes this exact x86_pt_alloc_pages_fn_t callback into existing Rust x86_split_large_page_body_result.',semantics='nr_pages!=1 returns NULL without callbacks. nr_pages==1 reuses existing Rust x86_pt_alloc_zeroed_result with exact already-tested allocator callback; original signed int flag bits preserved through original C unsigned-long/int roundtrip. Existing helper allocates one page, zeros exactly512 CULong entries only for nonNULL and returns raw pointer/NULL.',ownership='No new allocation/free, accounting, panic or policy; same one-page allocation and clearing before synchronous return. No mutable reference across callbacks or retained pointer; caller still owns subsequent page-table publication/failure cleanup.',fallback_C_byte_identical=True,new_C_function_getter=False,selection='PUBLIC declaration with unique new Rust provider, exact original static C definition retained only fallback. Real ABI/TU/reloc/partial proof remains future; no invented C U before actual compile.',fragments=[ref(P/'FUTURE-REAL-HEADER-ABI-FRAGMENT.NOT-QUEUED.c'),ref(P/'FUTURE-ALLOCATOR-ZEROING-CONSUMER.NOT-QUEUED.c')],prior_source_only_orchestration='cb4f7036 plus dd7783fe fixture qualification; unexecuted and not included in queued production four-provider suffix',sole_executable_queue='passed-four-provider-union2-production-suffix-preparation-1/c03ce4ee',new_queue_CPU_reservation=None,actual_fixture_production_default_native=None,engineering_percentage=None)
put(P/'SOURCE-SPLIT-ALLOCATOR-AND-INVARIANTS.NOT-EXECUTED.json',json.dumps(data,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(handoff=ref(P/'SOURCE-SPLIT-ALLOCATOR-AND-INVARIANTS.NOT-EXECUTED.json'),postimages=data['postimages'],patch=data['patch'])))
