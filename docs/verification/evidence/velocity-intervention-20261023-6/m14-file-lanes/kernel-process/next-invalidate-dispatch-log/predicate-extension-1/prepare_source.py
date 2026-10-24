"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Next finite invalidate PTE predicate source slice; no compiler or ready queue.
"""
from pathlib import Path
import difflib,hashlib,json
P=Path(__file__).resolve().parent;B=P.parent/'pte-extension-1';ROOT=Path('/home/holden/mckernel')
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
 assert pin(cp)['sha256']=='95efb7dff9bc9a3f923e69c4ee10695965bed516be99408cbc775ffc785c5c3a'
 assert pin(rp)['sha256']=='47fbe4882db455cc403d130113c48e21ea7cd95158eb71e63b4fb6a865200d4d'
 c=cp.read_text();r=rp.read_text()
 old='crate::mem_helpers::rusage_memory_stat_sub((*args).memobj, pgsize, pgsize as CInt);'
 new='crate::mem_helpers::rusage_memory_stat_sub((*args).memobj, pgsize as CULong, pgsize as CInt);'
 assert r.count(old)==1;r=r.replace(old,new,1)
 # Coherent source successor carries the same sole root-authorized LP64 cast;
 # original uncompiled634 batch remains immutable.
 baseline=r
 names=['process_pte_is_null_bridge','process_pte_is_fileoff_bridge']
 decls=['int process_pte_is_null_bridge(void *);','int process_pte_is_fileoff_bridge(void *, size_t);']
 for name,decl in zip(names,decls):
  original=function(c,'int '+name+'(')
  put(P/'fixture'/(name+'.ACTUAL-C.inc'),original+'\n')
  c=c.replace(original,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'+decl+'\n#else\n'+original+'\n#endif',1)
 for decl in ['    fn process_pte_is_null_bridge(ptep: *mut c_void) -> CInt;\n','    fn process_pte_is_fileoff_bridge(ptep: *mut c_void, pgsize: SizeT) -> CInt;\n']:
  assert r.count(decl)==1;r=r.replace(decl,'',1)
 bodies='''#[no_mangle]
pub unsafe extern "C" fn process_pte_is_null_bridge(ptep: *mut c_void) -> CInt {
    crate::pte_helpers::pte_is_null(ptep.cast::<CULong>())
}

#[no_mangle]
pub unsafe extern "C" fn process_pte_is_fileoff_bridge(
    ptep: *mut c_void,
    pgsize: SizeT,
) -> CInt {
    crate::pte_helpers::pte_is_fileoff(ptep.cast::<CULong>(), pgsize)
}
'''
 r+='\n// Existing read-only PTE predicates for the unchanged invalidate owner.\n'+bodies
 for rel,pre,post in [('kernel/process.c',cp.read_text(),c),('kernel/rust/process_helpers.rs',rp.read_text(),r)]:
  put(P/'candidate'/rel,post)
  put(P/'patch'/(Path(rel).name+'.PREDICATES-AND-AUTHORIZED-CAST.diff'),''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 for name in ['process_invalidate_one_page_body_result','invalidate_one_page']:
  expected=function(rp.read_text(),'pub unsafe extern "C" fn '+name+'(')
  assert function(r,'pub unsafe extern "C" fn '+name+'(')==expected
  put(P/'fixture'/('unchanged_'+name+'.ACTUAL-RUST.inc'),expected+'\n')
 put(P/'fixture/callbacks.ACTUAL-RUST.inc',bodies)
 ac=(ROOT/'arch/x86_64/kernel/memory.c').read_text()
 for name in ['pte_is_null','pte_is_fileoff']:
  put(P/'fixture'/(name+'.ACTUAL-ARCH-C.inc'),function(ac,'int '+name+'(')+'\n')
 pr=(ROOT/'kernel/rust/pte_helpers.rs').read_text()
 provider=pr[:pr.index('extern "C" {')]+function(pr,'unsafe fn pte_load(')+'\n'
 for name in ['pte_is_null','pte_is_fileoff']:
  provider+='#[no_mangle]\n'+function(pr,'pub unsafe extern "C" fn '+name+'(')+'\n'
 put(P/'fixture/pte_predicates.ACTUAL-RUST.inc',provider)
 put(P/'fixture/abi.ACTUAL.rs',(B/'fixture/abi.ACTUAL.rs').read_text())
 put(P/'fixture/actual_provider.rs','''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] pub mod abi;
mod pte_helpers { include!("pte_predicates.ACTUAL-RUST.inc"); }
use core::ffi::c_void;use abi::{CInt,CULong,SizeT};
include!("callbacks.ACTUAL-RUST.inc");
''')
 put(P/'fixture/actual_header_ABI.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <arch-memory.h>
extern int process_pte_is_null_bridge(void *);
extern int process_pte_is_fileoff_bridge(void *,size_t);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_is_null_bridge),int (*)(void *)),"original signed predicate callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_is_fileoff_bridge),int (*)(void *,size_t)),"original file-offset predicate callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_is_null),int (*)(pte_t *)),"actual C PTE predicate signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_is_fileoff),int (*)(pte_t *,size_t)),"actual C file-offset predicate signature");
_Static_assert(sizeof(pte_t)==8&&sizeof(size_t)==8&&sizeof(int)==4,"supported word and result widths");
''')
 remaining=json.loads((B/'sourcehandoff/SOURCE-EXTENDED-BATCH.json').read_text())['remaining_exact_owner_C_callbacks']
 remaining=[name for name in remaining if name not in names]
 ready=P.parent.parent/'production-batch-preparation-1/bounded-source-correction-1/EXECUTABLE-READY.BOUNDED-SOURCE-CORRECTION.NOT-GRANTED.json'
 receipt=dict(scope=SCOPE,status='SIX_CALLBACK_INVALIDATE_BATCH_SOURCE_ONLY_NO_SECOND_EXECUTABLE_QUEUE',
  previous634_source=pin(B/'sourcehandoff/SOURCE-EXTENDED-BATCH.json'),
  original340_and294_cases_retained_unrun=True,
  source_cast_alignment='Carries only the root-authorized lossless pgsize as CULong RSS cast, matching queued bounded fullcrate source5bf085bf. Original uncompiled candidates remain immutable.',
  queued_production_ready=pin(ready),
  postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},
  original_C_fallback_exact=True,actual_predicate_Rust=pin(P/'fixture/callbacks.ACTUAL-RUST.inc'),
  fixture=pin(P/'actual_predicate_parity.SOURCE-ONLY.c'),
  provider_pins={rel:pin(ROOT/rel) for rel in ['kernel/rust/pte_helpers.rs','arch/x86_64/kernel/memory.c','arch/x86_64/kernel/include/arch-memory.h']},
  owner_invariant='Unchanged Rust invalidate owner tests null first and short-circuits before fileoff; a true predicate exits0 before phys lookup, Page/PTE mutation, TLB, unmap or memobj dispatch. New adapters reuse existing volatile read-only predicates; exactly CInt0/1, same PTE borrowed alignment and page-size dispatch, no new lock/ref/retention or write.',
  new_planned_comparisons=56,cumulative_planned_comparisons=690,
  remaining_exact_owner_C_callbacks=remaining,
  next_observation='56 actual original C/provider vs actual Rust/provider read-only predicate cases with exact independent0/1 oracle and guard/PTE immutability; real header ABI and unchanged actual owner/caller source retained. Full selected consumer/link requires later root grant.',
  compiler_jobs=0,tests_executed=0,CPU_reservations=0,new_executable_queues=0,native_default_credit=False)
 put(P/'sourcehandoff/SOURCE-EXTENDED-BATCH.json',json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-EXTENDED-BATCH.json'),postimages=receipt['postimages'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
