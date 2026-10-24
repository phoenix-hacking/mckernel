"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite physical-address/page-size callback source extension; no executable queue.
"""
from pathlib import Path
import difflib,hashlib,json
P=Path(__file__).resolve().parent;B=P.parent/'predicate-extension-1';ROOT=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
def function(s,marker):
 a=s.index(marker);br=s.index('{',a);e=br+1;depth=1
 while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
def main():
 cp=B/'candidate/kernel/process.c';rp=B/'candidate/kernel/rust/process_helpers.rs'
 assert pin(cp)['sha256']=='29ca6dd7477e976c2d3e92003245a7cb70e19d67aef3864a14911398ee5f0465'
 assert pin(rp)['sha256']=='3db8c4f2785ca1707de345f226d8a8a6be671bd1307b33b51b085d3e99220015'
 c=cp.read_text();r=rp.read_text()
 items=[
  ('process_pte_get_phys_bridge','uintptr_t','uintptr_t process_pte_get_phys_bridge(void *);'),
  ('process_pgsize_to_tbllv_bridge','int','int process_pgsize_to_tbllv_bridge(size_t);'),
  ('process_tbllv_to_contpgsize_bridge','size_t','size_t process_tbllv_to_contpgsize_bridge(int);')]
 for name,result,decl in items:
  original=function(c,result+' '+name+'(')
  put(P/'fixture'/(name+'.ACTUAL-C.inc'),original+'\n')
  c=c.replace(original,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'+decl+'\n#else\n'+original+'\n#endif',1)
 for decl in ['    fn process_pte_get_phys_bridge(ptep: *mut c_void) -> CULong;\n','    fn process_pgsize_to_tbllv_bridge(pgsize: SizeT) -> CInt;\n','    fn process_tbllv_to_contpgsize_bridge(level: CInt) -> SizeT;\n']:
  assert r.count(decl)==1;r=r.replace(decl,'',1)
 bodies='''#[no_mangle]
pub unsafe extern "C" fn process_pte_get_phys_bridge(ptep: *mut c_void) -> CULong {
    crate::pte_helpers::pte_get_phys(ptep.cast::<CULong>())
}

#[no_mangle]
pub unsafe extern "C" fn process_pgsize_to_tbllv_bridge(pgsize: SizeT) -> CInt {
    crate::pte_helpers::pgsize_to_tbllv(pgsize)
}

#[no_mangle]
pub unsafe extern "C" fn process_tbllv_to_contpgsize_bridge(level: CInt) -> SizeT {
    crate::pte_helpers::tbllv_to_contpgsize(level)
}
'''
 r+='\n// Preserve the invalidate owner physical/contiguous-size callback boundaries.\n'+bodies
 for rel,pre,post in [('kernel/process.c',cp.read_text(),c),('kernel/rust/process_helpers.rs',rp.read_text(),r)]:
  put(P/'candidate'/rel,post)
  put(P/'patch'/(Path(rel).name+'.PHYS-SIZE-ADAPTERS.diff'),''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 for name in ['process_invalidate_one_page_body_result','invalidate_one_page']:
  expected=function(rp.read_text(),'pub unsafe extern "C" fn '+name+'(')
  assert function(r,'pub unsafe extern "C" fn '+name+'(')==expected
  put(P/'fixture'/('unchanged_'+name+'.ACTUAL-RUST.inc'),expected+'\n')
 put(P/'fixture/callbacks.ACTUAL-RUST.inc',bodies)
 ac=(ROOT/'arch/x86_64/kernel/memory.c').read_text()
 for name,result in [('pte_get_phys','uintptr_t'),('pgsize_to_tbllv','int'),('tbllv_to_contpgsize','size_t')]:
  put(P/'fixture'/(name+'.ACTUAL-ARCH-C.inc'),function(ac,result+' '+name+'(')+'\n')
 pr=(ROOT/'kernel/rust/pte_helpers.rs').read_text()
 provider=pr[:pr.index('extern "C" {')]+function(pr,'unsafe fn pte_load(')+'\n'
 for name,decl in [('pte_get_phys','pub unsafe extern "C" fn '),('pgsize_to_tbllv','pub extern "C" fn '),('tbllv_to_contpgsize','pub extern "C" fn ')]:
  provider+='#[no_mangle]\n'+function(pr,decl+name+'(')+'\n'
 put(P/'fixture/providers.ACTUAL-RUST.inc',provider)
 put(P/'fixture/abi.ACTUAL.rs',(B/'fixture/abi.ACTUAL.rs').read_text())
 put(P/'fixture/actual_provider.rs','''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] pub mod abi;
mod pte_helpers { include!("providers.ACTUAL-RUST.inc"); }
use core::ffi::c_void;use abi::{CInt,CULong,SizeT};
include!("callbacks.ACTUAL-RUST.inc");
''')
 put(P/'fixture/actual_header_ABI.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <arch-memory.h>
extern uintptr_t process_pte_get_phys_bridge(void *);
extern int process_pgsize_to_tbllv_bridge(size_t);
extern size_t process_tbllv_to_contpgsize_bridge(int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_get_phys_bridge),uintptr_t (*)(void *)),"original unsigned physical-address callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pgsize_to_tbllv_bridge),int (*)(size_t)),"original page-size to signed level callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_tbllv_to_contpgsize_bridge),size_t (*)(int)),"original signed level to contiguous-size callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_get_phys),uintptr_t (*)(pte_t *)),"real architecture physical extractor signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pgsize_to_tbllv),int (*)(size_t)),"real architecture size converter signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&tbllv_to_contpgsize),size_t (*)(int)),"real architecture contiguous-size converter signature");
_Static_assert(sizeof(uintptr_t)==8&&sizeof(pte_t)==8&&sizeof(size_t)==8&&sizeof(int)==4,"supported LP64 unsigned/signed widths");
''')
 old=json.loads((B/'sourcehandoff/SOURCE-EXTENDED-BATCH.json').read_text())
 remaining=[name for name in old['remaining_exact_owner_C_callbacks'] if name not in {item[0] for item in items}]
 q=P.parent.parent/'remap-range-log-fixture-preparation-1/sourcehandoff/EXECUTABLE-READY.REMAP-LOG404.NOT-GRANTED.json'
 receipt=dict(scope=SCOPE,status='NINE_CALLBACK_INVALIDATE_BATCH_SOURCE_ONLY_NO_SECOND_QUEUE',
  predecessor=pin(B/'sourcehandoff/SOURCE-EXTENDED-BATCH.json'),prior690_sources_unchanged_and_unrun=True,
  postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},
  original_C_fallback_exact=True,new_Rust_callbacks=pin(P/'fixture/callbacks.ACTUAL-RUST.inc'),
  fixture_source=pin(P/'actual_phys_size_parity.SOURCE-ONLY.c'),
  owner_invariant='Existing Rust owner null/fileoff short-circuit precedes physical extraction. Physical mask result is read before Page lookup and PTE exchange. Existing contiguous test/head test precede pgsize_to_tbllv then tbllv_to_contpgsize; nonhead contiguous case exits0. x86 conversion returns0 for unsupported sizes/contiguous levels exactly as existing providers. No lock/ref/notification/lifetime/write changes.',
  new_planned_comparisons=26,cumulative_planned_comparisons=716,
  remaining_exact_owner_C_callbacks=remaining,
  page_offset_request=str(P.parent/'PAGE-OFFSET-TYPED-PROVIDER-REQUEST.md'),
  queued_remap404_ready=pin(q),
  effort_ranking_with_uncertainty=[
   'Lower effort: remaining pure PTE/contiguity adapters reuse existing Rust operations.',
   'Medium: typed phys_to_page/page_unmap/TLB/panic adapters need actual provider/caller and controlled-effect qualification.',
   'Medium-to-higher uncertainty: Page offset private-field boundary needs F01-owned typed provider, no guessed field offset.',
   'Highest known implementation uncertainty: retained page_fault_process_memory_range ownership/error/lock orchestration; existing Rust PTE/memobj/allocator helpers help but do not establish a complete port.',
   'Separate broader dependency: coherent default image linking/provider activation and native/runtime acceptance; current fullcrate/partial and hosted leaf evidence do not close it.'],
  next_observation='26 original C/provider vs real Rust/provider physical-mask and size/default-result cases plus real ABI and unchanged exact caller ordering; source only. The sole executable queue remains remap/log404.',
  compiler_jobs=0,tests_executed=0,CPU_reservations=0,new_executable_queues=0,percentage_estimate=None,ETA=None,default_native_credit=False)
 put(P/'sourcehandoff/SOURCE-EXTENDED-BATCH.json',json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-EXTENDED-BATCH.json'),postimages=receipt['postimages'],remaining_owner_C_callbacks=remaining,compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
