"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Port bounded memobj acquisition; keep ambiguous owning zeroobj error path in C.
Private fragments only, no second queue/compiler/canonical or Page edits.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
P=Path(__file__).resolve().parent;L=P.parent;B=L/'union2-passed-prepare-production-1'
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
 assert pin(cp)['sha256']=='5439bd122571cc5080617b281a7956bb6c5170121a0242ac7f7f7448179d1db2'
 assert pin(rp)['sha256']=='9bb64e6d4982d6f026b8d35f98a123b6cef86a886b8f7ac99c17c423128a6b96'
 c=cp.read_text();r=rp.read_text()
 full=function(c,'int page_fault_process_memory_range(')
 start=full.index('\t\tphys = NOPHYS;\n')
 end=full.index('\t\tif (phys == NOPHYS) {',start)
 original=full[start:end]
 error_if=function(original,'\t\t\tif (error) {')
 opening=error_if.index('{');error_contents=error_if[opening+1:-1]
 assert 'zeroobj_create(&obj)' in error_contents and 'goto out;' in error_contents
 assert original.count('memobj_get_page(')==2  # real call and existing accounting comment
 assert not any(name in original for name in ['__FUNCTION__','__func__','__FILE__','__LINE__'])
 declaration='''#ifdef MCKERNEL_RUST_PROCESS_HELPERS
int process_page_fault_memobj_get_body_result(struct vm_range *, void *, uintptr_t,
        pte_t *, size_t, int, uintptr_t *, unsigned long *, int *);
#endif

'''
 selection='''#ifdef MCKERNEL_RUST_PROCESS_HELPERS
        /* Rust returns the existing signed-error predicate, not a new release
         * policy. Preserve the owning zeroobj error branch here verbatim. */
        if (process_page_fault_memobj_get_body_result(range, pgaddr,
                fault_addr, ptep, pgsize, p2align, &phys, &memobj_flag, &error)) {'''+error_contents+'''
        }
#else
'''+original+'#endif\n'
 assert c.count(original)==1;c=c.replace(original,selection,1)
 c=c.replace('int page_fault_process_memory_range(',declaration+'int page_fault_process_memory_range(',1)
 body='''#[no_mangle]
pub unsafe extern "C" fn process_page_fault_memobj_get_body_result(
    range: *mut VmRange,
    pgaddr: *mut c_void,
    fault_addr: CULong,
    ptep: *mut CULong,
    pgsize: SizeT,
    p2align: CInt,
    phys_out: *mut CULong,
    memobj_flag_out: *mut CULong,
    error_out: *mut CInt,
) -> CInt {
    *phys_out = NOPHYS;
    if (*range).memobj.is_null() {
        // The original no-memobj path does not overwrite flags or error.
        return 0;
    }
    let off = if ptep.is_null()
        || crate::pte_helpers::pte_is_fileoff(ptep, pgsize) == 0
    {
        ((*range).objoff as CULong)
            .wrapping_add((pgaddr as CULong).wrapping_sub((*range).start)) as OffT
    } else {
        crate::pte_helpers::pte_get_off(ptep, pgsize)
    };
    *error_out = crate::object_helpers::memobj_get_page(
        (*range).memobj.cast::<Memobj>(), off, p2align,
        phys_out, memobj_flag_out, fault_addr,
    );
    // The unchanged C caller owns zeroobj/panic/comparison handling. This
    // predicate preserves every positive/negative provider error unchanged.
    (*error_out != 0) as CInt
}
'''
 assert 'process_page_fault_memobj_get_body_result(' not in r
 assert 'const NOPHYS: CULong = !0;' in r
 r+='\n// Memobj result publication; zeroobj owning-reference policy remains C.\n'+body
 for rel,pre,post in [('kernel/process.c',cp.read_text(),c),('kernel/rust/process_helpers.rs',rp.read_text(),r)]:
  put(P/'candidate'/rel,post)
  put(P/'patch'/(Path(rel).name+'.MEMOBJ-ACQUISITION.diff'),''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 put(P/'fixture/original_memobj_branch.ACTUAL-C.inc',original)
 put(P/'fixture/retained_zeroobj_error.ACTUAL-C.inc',error_if+'\n')
 put(P/'fixture/memobj_get.ACTUAL-RUST.inc',body)
 # Mechanical reference wrapper stops at the precise new handback boundary.
 # The original whole branch above remains the authoritative raw C reference.
 prefix=original[:original.index('\t\t\tif (error) {')]
 reference='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE-ONLY reference fragment. Actual original pre-error statements extracted
 * verbatim; wrapper exposes the exact new handback, not a zeroobj model. */
#include <process.h>
#include <memobj.h>
int fixture_original_memobj_get(struct vm_range *range,void *pgaddr,uintptr_t fault_addr,
        pte_t *ptep,size_t pgsize,int p2align,uintptr_t *po,unsigned long *fo,int *eo)
{
    uintptr_t phys=*po;unsigned long memobj_flag=*fo;int error=*eo;
'''+prefix+'''
            *po=phys;*fo=memobj_flag;*eo=error;return error!=0;
        }
    *po=phys;*fo=memobj_flag;return 0;
}
extern int process_page_fault_memobj_get_body_result(struct vm_range *,void *,uintptr_t,pte_t *,size_t,int,uintptr_t *,unsigned long *,int *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&memobj_get_page),
 int (*)(struct memobj *,off_t,int,uintptr_t *,unsigned long *,uintptr_t)),
 "exact actual memobj provider output/offset signature");
_Static_assert(sizeof(uintptr_t)==8&&sizeof(off_t)==8&&sizeof(unsigned long)==8&&sizeof(int)==4,
 "actual supported wrapped-offset/output ABI");
_Static_assert(NOPHYS==(uintptr_t)-1,"same actual no-physical sentinel");
'''
 put(P/'fixture/original_lookup_reference.SOURCE-ONLY.c.inc',reference)
 obj=(ROOT/'kernel/rust/object_helpers.rs').read_text()
 provider='use core::mem::transmute;\nuse crate::abi::{CInt,CULong,OffT,Memobj};\nconst ENXIO:CInt=6;\n'
 alias='type MemobjGetPageFn =\n    unsafe extern "C" fn(*mut Memobj, OffT, CInt, *mut CULong, *mut CULong, CULong) -> CInt;'
 assert alias in obj;provider+=alias+'\n'
 for marker in ['pub extern "C" fn memobj_op_present_result(','pub extern "C" fn memobj_missing_page_op_result(','pub unsafe extern "C" fn memobj_get_page(']:
  provider+='#[no_mangle]\n'+function(obj,marker)+'\n'
 put(P/'fixture/object_provider.ACTUAL-RUST.inc',provider)
 pte=(ROOT/'kernel/rust/pte_helpers.rs').read_text()
 pte_provider=pte[:pte.index('extern "C" {')]+function(pte,'unsafe fn pte_load(')+'\n'
 for name in ['pte_is_fileoff','pte_get_off']:
  pte_provider+='#[no_mangle]\n'+function(pte,'pub unsafe extern "C" fn '+name+'(')+'\n'
 put(P/'fixture/pte_provider.ACTUAL-RUST.inc',pte_provider)
 shutil.copy2(ROOT/'kernel/rust/abi.rs',P/'fixture/abi.ACTUAL.rs')
 put(P/'fixture/actual_provider.SOURCE-ONLY.rs','''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual providers; no zeroobj implementation/reference policy is duplicated.
#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;use abi::{CInt,CULong,OffT,SizeT,VmRange,Memobj};
const NOPHYS:CULong=!0;
mod object_helpers { include!("object_provider.ACTUAL-RUST.inc"); }
mod pte_helpers { include!("pte_provider.ACTUAL-RUST.inc"); }
include!("memobj_get.ACTUAL-RUST.inc");
''')
 zero=ROOT/'kernel/rust/zeroobj.rs'
 zero_body=function(zero.read_text(),'pub unsafe extern "C" fn zeroobj_create(')
 assert 'memobj_ref(obj);' in zero_body and 'memobj_unref' not in error_contents
 put(P/'fixture/zeroobj_create.OWNERSHIP-REFERENCE-ONLY.inc',zero_body+'\n')
 ready=B/'ROOT-READY.CURRENT-UNION2-PREPARE-AND-F01-CONSUMER.json'
 receipt=dict(scope=SCOPE,status='MEMOBJ_ACQUISITION_SOURCE_ONLY_WITH_EXPLICIT_ZEROOBJ_OWNERSHIP_HOLD',
  predecessor_ready=pin(ready),postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},
  original_C_branch=pin(P/'fixture/original_memobj_branch.ACTUAL-C.inc'),new_Rust=pin(P/'fixture/memobj_get.ACTUAL-RUST.inc'),
  exact_original_C_fallback=True,retained_error_branch=pin(P/'fixture/retained_zeroobj_error.ACTUAL-C.inc'),
  no_added_lock_refcount_Page_or_cleanup='Caller retains its existing VM lock and original memobj/Page ownership. New helper only publishes NOPHYS/physical result, provider flags and signed provider error. No extra Page lookup/ref/unmap/free or owning zeroobj pointer is introduced.',
  original_order='NOPHYS first; absent memobj leaves flags/error unchanged. Null/nonfileoff PTE uses exact unsigned-wrapped range offset, fileoff uses actual Rust PTE offset provider. Call actual typed memobj_get_page once, preserve all output mutations and signed result, return only nonzero-error predicate to original C branch.',
  explicit_ownership_hold='Existing zeroobj_create calls memobj_ref on success. Original C temporary comparison branch has no paired unref. Intent/lifetime is not established here; it remains byte-preserved C, and no owning zeroobj ref crosses this new Rust boundary. Root/owner must disposition that retained reference before porting the error branch; no invented ACK/unref.',
  provider_sources={rel:pin(ROOT/rel) for rel in ['kernel/rust/object_helpers.rs','kernel/rust/pte_helpers.rs','kernel/rust/zeroobj.rs','kernel/include/memobj.h']},
  fixture_fragments=[pin(P/'fixture/original_lookup_reference.SOURCE-ONLY.c.inc'),pin(P/'fixture/actual_provider.SOURCE-ONLY.rs')],
  next_check='Actual C reference/Rust phases with absent/present/missing operation, signed offset/high-bit wrap/fileoff offsets, provider0/positive/negative extremes, physical+flag output changes even on error, and pointer/operation mutation. Assert no zeroobj call/ref/unmap/free in this boundary; exact C provider signature and real layouts. Source fragments only; no new executable queue.',
  anonymous_allocation_port_included=False,production_ready_unchanged=pin(ready),
  remaining='Owning zeroobj comparison branch held; anonymous allocation/clear/map and COW/copy/accounting/install/cleanup still separate source/private C debt. Default/native acceptance open.',
  compiler_jobs=0,tests_executed=0,CPU_reservations=0,new_executable_queues=0,canonical_mutations=0,default_native_credit=False)
 put(P/'sourcehandoff/SOURCE-NEXT-BODY.json',json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-NEXT-BODY.json'),postimages=receipt['postimages'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
