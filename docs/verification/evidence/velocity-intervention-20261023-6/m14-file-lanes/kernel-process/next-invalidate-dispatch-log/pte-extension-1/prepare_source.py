"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Add two actual invalidate PTE callback ports; source only, no executable queue.
"""
from pathlib import Path
import difflib,hashlib,json
P=Path(__file__).resolve().parent
B=P.parent
ROOT=Path('/home/holden/mckernel')
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
 assert pin(cp)['sha256']=='9bf642a4387765a0e7a84a8a9ae7f6d9e69f4507e0c3e8a9adc0d05e52a8b6d6'
 assert pin(rp)['sha256']=='25c029da79f228fa12be1eda716788d25f6c68225bef6fe1eb3601a8c51db675'
 c=cp.read_text();r=rp.read_text()
 names=['process_pte_make_fileoff_bridge','process_pte_xchg_bridge']
 originals=[function(c,'void '+name+'(') for name in names]
 declarations=['void process_pte_make_fileoff_bridge(long, size_t, void *);','void process_pte_xchg_bridge(void *, void *);']
 for body,decl in zip(originals,declarations):
  assert c.count(body)==1;c=c.replace(body,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'+decl+'\n#else\n'+body+'\n#endif',1)
 for decl in ['    fn process_pte_make_fileoff_bridge(off: OffT, pgsize: SizeT, ptep: *mut c_void);\n','    fn process_pte_xchg_bridge(ptep: *mut c_void, valp: *mut c_void);\n']:
  assert r.count(decl)==1;r=r.replace(decl,'',1)
 bodies='''#[no_mangle]
pub unsafe extern "C" fn process_pte_make_fileoff_bridge(
    off: OffT,
    pgsize: SizeT,
    ptep: *mut c_void,
) {
    crate::pte_helpers::pte_make_fileoff(off, 0, pgsize, ptep.cast::<CULong>());
}

#[no_mangle]
pub unsafe extern "C" fn process_pte_xchg_bridge(
    ptep: *mut c_void,
    valp: *mut c_void,
) {
    crate::pte_helpers::pte_xchg(ptep.cast::<CULong>(), valp.cast::<CULong>());
}
'''
 r+='\n// Existing typed PTE providers; no change to owner exclusion or callback order.\n'+bodies
 for rel,old,new in [('kernel/process.c',cp.read_text(),c),('kernel/rust/process_helpers.rs',rp.read_text(),r)]:
  put(P/'candidate'/rel,new)
  put(P/'patch'/(Path(rel).name+'.TWO-MORE-CALLBACKS.diff'),''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 for name,original in zip(names,originals):put(P/'fixture'/(name+'.ACTUAL-C.inc'),original+'\n')
 put(P/'fixture/callbacks.ACTUAL-RUST.inc',bodies)
 # Original owner and caller source stay exact including callback selection/order.
 for name in ['process_invalidate_one_page_body_result','invalidate_one_page']:
  old=function(rp.read_text(),'pub unsafe extern "C" fn '+name+'(')
  assert function(r,'pub unsafe extern "C" fn '+name+'(')==old
  put(P/'fixture'/('unchanged_'+name+'.ACTUAL-RUST.inc'),old+'\n')
 # Original C providers are real extracted bodies, not a duplicate test algorithm.
 ac=(ROOT/'arch/x86_64/kernel/memory.c').read_text()
 for name in ['pte_make_fileoff','pte_xchg']:
  put(P/'fixture'/(name+'.ACTUAL-ARCH-C.inc'),function(ac,'void '+name+'(')+'\n')
 pr=(ROOT/'kernel/rust/pte_helpers.rs').read_text()
 prefix=pr[:pr.index('extern "C" {')]
 store=function(pr,'unsafe fn pte_store(')
 actual_provider=prefix+store+'\n'
 for name in ['pte_make_fileoff','pte_xchg']:
  actual_provider+='#[no_mangle]\n'+function(pr,'pub unsafe extern "C" fn '+name+'(')+'\n'
 put(P/'fixture/pte_providers.ACTUAL-RUST.inc',actual_provider)
 put(P/'fixture/abi.ACTUAL.rs',(B/'fixture/abi.ACTUAL.rs').read_text())
 put(P/'fixture/actual_provider.rs','''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] pub mod abi;
mod pte_helpers { include!("pte_providers.ACTUAL-RUST.inc"); }
use core::ffi::c_void;
use abi::{CULong,OffT,SizeT};
include!("callbacks.ACTUAL-RUST.inc");
''')
 put(P/'fixture/actual_header_ABI.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <arch-memory.h>
extern void process_pte_make_fileoff_bridge(long,size_t,void *);
extern void process_pte_xchg_bridge(void *,void *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_make_fileoff_bridge),void (*)(off_t,size_t,void *)),"original signed LP64 offset callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_pte_xchg_bridge),void (*)(void *,void *)),"original two-borrowed-pointer exchange ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_make_fileoff),void (*)(off_t,enum ihk_mc_pt_attribute,size_t,pte_t *)),"real architecture encoder signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&pte_xchg),void (*)(pte_t *,pte_t *)),"real architecture atomic exchange signature");
_Static_assert(sizeof(off_t)==8&&sizeof(long)==8&&sizeof(pte_t)==8&&sizeof(size_t)==8,"supported LP64 signedness/widths");
_Static_assert(__alignof__(pte_t)==__alignof__(unsigned long),"existing atomic PTE alignment");
''')
 put(P/'fixture/actual_consumer.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * The unchanged Rust invalidate_one_page entry passes these function pointers
 * directly to its existing owner. This witness exposes their exact C ABI. */
#include <process.h>
extern void process_pte_make_fileoff_bridge(long,size_t,void *);
extern void process_pte_xchg_bridge(void *,void *);
void (*const actual_encode_consumer)(long,size_t,void *)=process_pte_make_fileoff_bridge;
void (*const actual_exchange_consumer)(void *,void *)=process_pte_xchg_bridge;
''')
 old=json.loads((B/'sourcehandoff/SOURCE-DEPENDENCY-QUALIFICATION.json').read_text())
 remaining=[n for n in old['unchanged_actual_owner_C_callbacks'] if n not in names]
 receipt=dict(scope=SCOPE,status='FOUR_CALLBACK_INVALIDATE_BATCH_SOURCE_ONLY_NOT_EXECUTABLE_READY',
  previous_source_receipt=pin(B/'sourcehandoff/SOURCE-NEXT-BODY.json'),
  previous340_fixture=pin(B/'actual_parity.SOURCE-ONLY.c'),
  previous340_history='Retained unchanged and unrun; planned340 callback comparisons remain source preparation only.',
  new_actual_C_bodies=[pin(P/'fixture'/(name+'.ACTUAL-C.inc')) for name in names],
  new_actual_Rust=pin(P/'fixture/callbacks.ACTUAL-RUST.inc'),
  postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},
  provider_pins={rel:pin(ROOT/rel) for rel in ['kernel/rust/pte_helpers.rs','arch/x86_64/kernel/memory.c','arch/x86_64/kernel/include/arch-memory.h','kernel/rust/abi.rs']},
  fixture_sources={rel:pin(P/rel) for rel in ['actual_pte_parity.SOURCE-ONLY.c','fixture/actual_provider.rs','fixture/actual_header_ABI.c','fixture/actual_consumer.c']},
  original_C_fallback_exact=True,
  owner_invariant='Existing actual Rust invalidate owner calls encoder only when a borrowed Page offset differs from linear offset, then atomically exchanges the live PTE with stack-local apte before the existing TLB callback. New typed adapters preserve off_t bits, ptattr0, size_t and aligned borrowed PTE pointers, including ptep==valp behavior. Existing Rust provider uses SeqCst atomic swap, exactly one volatile valp load and old-value store. No new lock/refcount/lifetime or native TLB effect.',
  unproven_scope='No compiler/test or new ready queue. Sequential actualC/actualRust parity validates callback/provider source when granted; it does not newly qualify concurrent PTE use, native TLB, the complete invalidate owner, production/default link or the kernel image.',
  new_planned_comparisons=294,total_planned_callback_comparisons=634,
  remaining_exact_owner_C_callbacks=remaining,
  selected_consumer='Unchanged actual invalidate_one_page function and process_invalidate_one_page_body_result full function extraction retained in fixture/.',
  existing_queued_ready=pin(B.parent/'production-batch-preparation-1/EXECUTABLE-READY.OBSERVER-SUCCESSOR.NOT-GRANTED.json'),
  compiler_jobs=0,CPU_reservations=0,new_executable_queues=0,fullimage_native_credit=False)
 put(P/'sourcehandoff/SOURCE-EXTENDED-BATCH.json',json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-EXTENDED-BATCH.json'),postimages=receipt['postimages'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
