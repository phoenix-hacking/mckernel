"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Retire exact post-copy COW RSS/unmap/publication body; preserve caller lock/out.
Source fragments only while the sole frozen extend/COW executable queue waits.
"""
from pathlib import Path
import hashlib,json,difflib
P=Path(__file__).resolve().parent;L=P.parent;B=L/'union2-extend-region-source-1';R=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(rel,s):
 p=P/rel;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
def fun(s,m):
 a=s.index(m);b=s.index('{',a);e=b+1;d=1
 while d:d+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
def main():
 cp=B/'candidate/kernel/process.SOURCE-CONTEXT-CORRECTED.c';rp=B/'candidate/kernel/rust/process_helpers.rs'
 assert pin(cp)['sha256']=='42ee6f390724da418d0cc0ac6573200615c1ed2a52cf0f7a10602d6eb9729ef1'
 assert pin(rp)['sha256']=='2e74d8131170630a1930d8f972e2918b8519e929635c5754fafd935009865da1'
 c=cp.read_text();r=rp.read_text();pf=fun(c,'int page_fault_process_memory_range(')
 a=pf.index('\t\t\t/* Count COW-source pointed-to by only fileobj')
 e=pf.index('\n\t\t}\n\t}\n\telse if',a)
 original=pf[a:e]
 assert original.endswith('\t\t\tpage = phys_to_page(phys);')
 assert original.count('page_unmap(page)')==1 and original.count('phys = virt_to_phys(virt)')==1
 offset=c.index(pf)+a
 def line(token):return c[:offset+original.index(token)].count('\n')+1
 addline=line('dkprintf("%lx+,%s: COW-source')
 subline=line('dkprintf("%lx-,%s: cow,calling memory_stat_rss_sub()')
 body='''#[no_mangle]
pub unsafe extern "C" fn process_page_fault_cow_commit_body_result(
    range: *mut VmRange,
    phys_out: *mut CULong,
    pgsize: SizeT,
    virt: *mut c_void,
    page_out: *mut *mut crate::page_helpers::Page,
    rss_add_debug: *mut crate::debug::Ddebug,
    rss_sub_debug: *mut crate::debug::Ddebug,
) {
    // The original caller still holds page_table_lock and owns the fresh copy.
    // The old Page reference is consumed only by the same existing unmap call.
    let old_phys = *phys_out;
    if crate::mem_helpers::rusage_memory_stat_add(
        range, old_phys, pgsize as CULong, pgsize as CInt,
    ) != 0 {
        if core::ptr::read_volatile(core::ptr::addr_of!((*rss_add_debug).line_flags)) >> 24 != 0 {
            let _ = kprintf(
                b"%lx+,%s: COW-source pointed-to by only fileobj, calling memory_stat_rss_add(),pgsize=%ld\\n\\0".as_ptr().cast(),
                old_phys, b"page_fault_process_memory_range\\0".as_ptr().cast::<i8>(), pgsize,
            );
        }
    }
    if !(*page_out).is_null() {
        if crate::page_helpers::page_unmap(*page_out) != 0 {
            if core::ptr::read_volatile(core::ptr::addr_of!((*rss_sub_debug).line_flags)) >> 24 != 0 {
                let _ = kprintf(
                    b"%lx-,%s: cow,calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\\n\\0".as_ptr().cast(),
                    old_phys, b"page_fault_process_memory_range\\0".as_ptr().cast::<i8>(), pgsize, pgsize,
                );
            }
            // Read memobj after unmap and its diagnostic, as in original C.
            crate::mem_helpers::rusage_memory_stat_sub(
                (*range).memobj.cast::<Memobj>(), pgsize as CULong, pgsize as CInt,
            );
        }
    }
    // Publish the same new physical result before the Page provider call.
    // Leave the old Page pointer visible until that call returns; no guessed
    // reference release, new-page unmap, free, lock change or success ACK.
    *phys_out = crate::x86_memory_helpers::virt_to_phys(virt);
    *page_out = phys_to_page(*phys_out);
}
'''
 declaration='#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'
 for name,ln in [('rss_add',addline),('rss_sub',subline)]:
  declaration+='''static struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_page_fault_cow_'''+name+'''_debug = {
    .file = __FILE__, .func = "page_fault_process_memory_range",
    .line = '''+str(ln)+''', .flags = DDEBUG_DEFAULT,
};
'''
 declaration+='''void process_page_fault_cow_commit_body_result(struct vm_range *,uintptr_t *,
        size_t,void *,struct page **,struct ddebug *,struct ddebug *);
#endif

'''
 selection='''#ifdef MCKERNEL_RUST_PROCESS_HELPERS
            process_page_fault_cow_commit_body_result(range, &phys, pgsize,
                virt, &page, &process_page_fault_cow_rss_add_debug,
                &process_page_fault_cow_rss_sub_debug);
#else
'''+original+'\n#endif'
 assert c.count(original)==1;postc=c.replace(original,selection,1)
 postc=postc.replace('int page_fault_process_memory_range(',declaration+'int page_fault_process_memory_range(',1)
 assert 'process_page_fault_cow_commit_body_result(' not in r
 assert r.count('    fn phys_to_page(phys: CULong) -> *mut crate::page_helpers::Page;')==1
 postr=r+'\n// COW post-copy RSS/unmap/result handoff under the original caller lock.\n'+body
 for rel,pre,post in [('kernel/process.c',c,postc),('kernel/rust/process_helpers.rs',r,postr)]:
  put('candidate/'+rel,post)
  put('patch/'+Path(rel).name+'.COW-COMMIT.diff',''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 put('fixture/original_cow_commit.ACTUAL-C.inc',original+'\n')
 put('fixture/cow_commit.ACTUAL-RUST.inc',body)
 reference='''/* '''+SCOPE+'''
 * SOURCE-ONLY precise reference handback. No allocation/copy/install executes.
 * Future fixture binds original debug selectors and same current Page providers. */
#include <process.h>
#include <rusage_private.h>
#include <memory.h>
#include <ihk/debug.h>
#define __FUNCTION__ "page_fault_process_memory_range"
static void fixture_original_cow_commit(struct vm_range *range,uintptr_t *phys_out,
        size_t pgsize,void *virt,struct page **page_out)
{
    uintptr_t phys=*phys_out;struct page *page=*page_out;
'''+original+'''
    *phys_out=phys;*page_out=page;
}
#undef __FUNCTION__
extern void process_page_fault_cow_commit_body_result(struct vm_range *,uintptr_t *,
        size_t,void *,struct page **,struct ddebug *,struct ddebug *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&rusage_memory_stat_add),
 int (*)(struct vm_range *,uintptr_t,unsigned long,int)),"actual RSS add types");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rusage_memory_stat_sub),
 void (*)(struct memobj *,unsigned long,int)),"actual RSS sub CULong then CInt");
_Static_assert(__builtin_types_compatible_p(__typeof__(&page_unmap),
 int (*)(struct page *)),"same old Page consume/unmap provider");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_page),
 struct page *(*)(uintptr_t)),"remaining actual C lookup provider boundary");
_Static_assert(__builtin_types_compatible_p(__typeof__(&virt_to_phys),
 unsigned long (*)(void *)),"existing actual Rust physical translation export");
_Static_assert(sizeof(size_t)==8&&sizeof(uintptr_t)==8&&sizeof(unsigned long)==8&&sizeof(int)==4,
 "actual supported scalar widths; no new provider signature inference");
'''
 put('fixture/original_reference.SOURCE-ONLY.c.inc',reference)
 mem=(R/'kernel/rust/mem_helpers.rs').read_text();pages=(R/'kernel/rust/page_helpers.rs').read_text()
 providers=''
 for src,markers in [(mem,['pub unsafe extern "C" fn rusage_memory_stat_add(','pub unsafe extern "C" fn rusage_memory_stat_sub(']),(pages,['pub unsafe extern "C" fn page_unmap('])]:
  for marker in markers:providers+='#[no_mangle]\n'+fun(src,marker)+'\n'
 put('fixture/existing_providers.ACTUAL-RUST.REFERENCE-ONLY.inc',providers)
 # Preserve exact still-unported adjacent calls rather than assuming C's
 # unspecified argument evaluation order, or accessing private Page.count.
 copy_start=pf.index('\t\t\tdkprintf("%s: cow,copying')
 copy_end=pf.index('\n\t\t\t/* Count COW-source',copy_start)
 put('fixture/copy_log_and_memcpy.EVALUATION-ORDER-HOLD.ACTUAL-C.inc',pf[copy_start:copy_end]+'\n')
 count_start=pf.index('\t\tdkprintf("%s: non-NULL pte,page=')
 count_end=pf.index('\n\t}',count_start)
 put('fixture/post_install_Page_count.TYPED-PROVIDER-HOLD.ACTUAL-C.inc',pf[count_start:count_end]+'\n')
 fixture=dict(scope=SCOPE,status='SOURCE_FRAGMENTS_ONLY_NO_SECOND_QUEUE',
  strict_cases=['NULL/nonNULL original Page; RSS add and page_unmap signed zero/positive/negative returns; assert exact call order and no unmap for NULL','pgsize4096,2MiB,INT_MAX+1,high-bit64; exact CULong accounting size and CInt narrowing with no error normalization','independent two diagnostic flags0,1,2,255, exact formats/varargs/function name and ignored signed logger result','RSS provider/log/unmap may mutate range.memobj; exact post-unmap/post-log value read by RSS-sub','translation returns zero/high-bit physical and phys_to_page returns NULL/different Page; old outputs retained until prescribed publication; snapshot no extra free/ref/unlock','leave owning new allocation/install and original error/out labels with caller; no synthetic native success or kernel ACK'],
  actual_provider_reuse='Existing Rust rusage_memory_stat_add/sub under original enable_rusage configuration; existing Rust Page-unmap public entry with same C geometry/lock/log callbacks; existing Rust virt_to_phys; existing typed process phys_to_page extern retained as explicit C debt.',
  abi='Real original C declarations and current Rust signatures captured. Hosted models, if used, must be named as controlled effects; no actual lock/ref/backend/native credit.',
  copy_log_hold='Original kprintf argument list contains both phys_to_virt(phys) and virt_to_phys(virt). C does not sequence those argument evaluations. Require exact selected GCC9 generated caller/controlled-call witness before choosing a Rust evaluation sequence; no inferred order/ACK.',
  PTE_count_provider_hold='Original success debug consumes page ? ihk_atomic_read(&page->count) : 0. Current page_helpers::Page.count is private; existing public predicates only return booleans, F01 offset getter does not supply this read. Keep C diagnostic until exact typed borrowed atomic-count provider is supplied/reviewed, without duplicating Page fields or offset guessing.',
  expected_execution=None,compiler_jobs=0,CPU_reservations=0,new_executable_queues=0,default_native_credit=False)
 put('fixture/FIXTURE-PROPOSAL.json',json.dumps(fixture,indent=2)+'\n')
 queue=L/'extend-cow-fixture-preparation-1/preexec-fixture-context-1/sourcehandoff/EXECUTABLE-READY.EXTEND-COW4480.NOT-GRANTED.json'
 receipt=dict(scope=SCOPE,status='COW_POST_COPY_RSS_UNMAP_PUBLICATION_SOURCE_ONLY',
  base=dict(C=pin(cp),Rust=pin(rp)),
  postimages={x:pin(P/'candidate'/x) for x in ['kernel/process.c','kernel/rust/process_helpers.rs']},
  original=pin(P/'fixture/original_cow_commit.ACTUAL-C.inc'),new_Rust=pin(P/'fixture/cow_commit.ACTUAL-RUST.inc'),
  fixture=pin(P/'fixture/FIXTURE-PROPOSAL.json'),actual_provider_references=pin(P/'fixture/existing_providers.ACTUAL-RUST.REFERENCE-ONLY.inc'),
  lock_lifetime_invariant='Caller retains page_table_lock and owns copied allocation before/after helper; unchanged existing Page-unmap is the sole old-Page consumption. No allocation/free/new ref/zeroobj operation/lock/release is added. Original caller retains PTE installation and stray-page out cleanup.',
  exact_order='RSS-add -> optional add log -> optional old Page-unmap -> optional sub log -> RSS-sub reading current range.memobj -> new virt_to_phys -> publish phys -> existing phys_to_page -> publish new Page. Original whole C fallback retained. size to CULong and page-size to CInt exactly match original implicit ABI conversions.',
  selected_actual_provider_debt=['phys_to_page existing C provider remains; no new getter','Page-unmap C geometry/lock/log bridges remain existing provider debt','COW allocation/copy log/memcpy and PTE install/error/out orchestration remain C'],
  copy_log_order_hold=pin(P/'fixture/copy_log_and_memcpy.EVALUATION-ORDER-HOLD.ACTUAL-C.inc'),
  Page_count_provider_hold=pin(P/'fixture/post_install_Page_count.TYPED-PROVIDER-HOLD.ACTUAL-C.inc'),
  zeroobj_ownership_hold_unchanged=True,anonymous_ownership_not_imported=True,
  source_provider_pins={x:pin(R/x) for x in ['kernel/rust/mem_helpers.rs','kernel/rust/page_helpers.rs','kernel/rust/x86_memory_helpers.rs','kernel/include/rusage_private.h']},
  source_context=dict(C_preimage=pin(cp),rss_add_debug_line=addline,rss_sub_debug_line=subline),
  sole_executable_queue_unchanged=pin(queue),all_prior_failures_retained=True,compiler_jobs=0,actual_tests=0,CPU_reservations=0,new_executable_queues=0,canonical_mutations=0,fullcrate_default_native_credit=False)
 put('sourcehandoff/SOURCE-NEXT-BODY.json',json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,handoff=pin(P/'sourcehandoff/SOURCE-NEXT-BODY.json'),postimages=receipt['postimages'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
