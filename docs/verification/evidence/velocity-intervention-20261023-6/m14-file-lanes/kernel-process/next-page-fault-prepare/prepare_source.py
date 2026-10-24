"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Port one actual page-fault preparation slice and consume F01's typed accessor.
Only private process sources/fixtures; no compiler, native action or Page edit.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
P=Path(__file__).resolve().parent;L=P.parent;ROOT=Path('/home/holden/mckernel')
BASE=L/'next-invalidate-dispatch-log/phys-size-extension-1'
PROD=L/'production-batch-preparation-1/bounded-source-correction-1'
F01=L.parent/'kernel-mem/page-offset-typed-provider-source-only-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
def function(s,marker):
 a=s.index(marker);b=s.index('{',a);e=b+1;depth=1
 while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
def main():
 cp=BASE/'candidate/kernel/process.c';rp=BASE/'candidate/kernel/rust/process_helpers.rs'
 assert pin(cp)['sha256']=='b7ba75d2c83228adbf273e2b2bc82a5552014b6c665b96e3be8bb55ea8da6a2b'
 assert pin(rp)['sha256']=='2b70399e3c48332aef387a06e75ec8ba1678843c68190c2a8f80d6e9f2a66c5b'
 c=cp.read_text();r=rp.read_text();canonical=(ROOT/'kernel/process.c').read_text()
 f01=json.loads((F01/'SOURCE-ONLY-TYPED-PROVIDER-HANDOFF.json').read_text())
 assert 'pub unsafe extern "C" fn page_get_offset(page: *const Page) -> OffT' in Path(f01['fragment']['path']).read_text()
 assert pin(Path(f01['fragment']['path']))==f01['fragment']
 # Consume the page owner's function; no duplicated Page layout/getter body.
 getter=function(c,'long process_page_offset_bridge(')
 c=c.replace(getter,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\nlong process_page_offset_bridge(void *);\n#else\n'+getter+'\n#endif',1)
 decl='    fn process_page_offset_bridge(page: *mut c_void) -> OffT;\n'
 assert r.count(decl)==1;r=r.replace(decl,'',1)
 getter_rust='''#[no_mangle]
pub unsafe extern "C" fn process_page_offset_bridge(page: *mut c_void) -> OffT {
    crate::page_helpers::page_get_offset(page.cast::<crate::page_helpers::Page>())
}
'''
 # Extract the real original block from the original full function, not a
 # reconstructed test implementation.
 full=function(c,'int page_fault_process_memory_range(')
 start=full.index('\tihk_mc_spinlock_lock_noirq(&vm->page_table_lock);')
 tail='\n\t/*****/\n\tdkprintf("%s: ptep=%lx,pte_is_null=%d,pte_is_fileoff=%d\\n"'
 end=full.index(tail,start)
 original=full[start:end]
 assert original in canonical and original.count('goto out;')==4
 bounds='dkprintf("%s: pgaddr=%lx,range->start=%lx,range->end=%lx,pgaddr+pgsize=%lx\\n"'
 bounds_line=canonical[:canonical.index(bounds)].count('\n')+1
 metadata='''#ifdef MCKERNEL_RUST_PROCESS_HELPERS
/* Original page-fault bounds diagnostic: static ABI data, Rust computation. */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_page_fault_prepare_bounds_debug = {
    .file = __FILE__, .func = "page_fault_process_memory_range",
    .line = BOUNDS_LINE, .flags = DDEBUG_DEFAULT,
};
int process_page_fault_prepare_body_result(struct process_vm *, struct vm_range *,
        uintptr_t, uint64_t, pte_t **, void **, size_t *, int *, int *);
#endif

'''.replace('BOUNDS_LINE',str(bounds_line))
 selected='''#ifdef MCKERNEL_RUST_PROCESS_HELPERS
    /* Both Rust outcomes retain this same lock for the unchanged out: path.
     * CONTINUE0 supplies original locals; GOTO_OUT1 also supplies error. */
    if (process_page_fault_prepare_body_result(vm, range, fault_addr, reason,
            &ptep, &pgaddr, &pgsize, &p2align, &error))
        goto out;
#else
'''+original+'\n#endif'
 c=c.replace('int page_fault_process_memory_range(',metadata+'int page_fault_process_memory_range(',1)
 assert c.count(original)==1;c=c.replace(original,selected,1)
 # This helper owns no Page/reference/allocation. It always acquires and
 # retains precisely the original lock; the existing C caller unlocks it.
 body='''#[no_mangle]
pub unsafe extern "C" fn process_page_fault_prepare_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    ptep_out: *mut *mut CULong,
    pgaddr_out: *mut *mut c_void,
    pgsize_out: *mut SizeT,
    p2align_out: *mut CInt,
    error_out: *mut CInt,
) -> CInt {
    // Match the original valid borrowed inputs; add no NULL/error policy.
    crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(
        &raw mut (*vm).page_table_lock,
    );
    *ptep_out = ihk_mc_pt_lookup_pte(
        (*(*vm).address_space).page_table,
        fault_addr as *mut c_void,
        (*range).pgshift,
        pgaddr_out, pgsize_out, p2align_out,
    );
    if reason & (1 | PF_PATCH) == 0 && !(*ptep_out).is_null()
        && crate::pte_helpers::pte_is_null(*ptep_out) == 0
        && crate::pte_helpers::pte_is_fileoff(*ptep_out, *pgsize_out) == 0
    {
        if crate::pte_helpers::pte_is_present(*ptep_out) == 0 {
            *error_out = -EFAULT;
            let _ = kprintf(
                b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):PROT_NONE. %d\\n\\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, (*range).flag,
                fault_addr, reason, *error_out,
            );
            return 1;
        }
        *error_out = 0;
        return 1;
    }
    if reason & 1 != 0 && ((*ptep_out).is_null()
        || crate::pte_helpers::pte_is_present(*ptep_out) == 0)
    {
        crate::x86_memory_helpers::flush_tlb_single(fault_addr);
        *error_out = 0;
        return 1;
    }
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_page_fault_prepare_bounds_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"%s: pgaddr=%lx,range->start=%lx,range->end=%lx,pgaddr+pgsize=%lx\\n\\0".as_ptr().cast(),
            b"page_fault_process_memory_range\\0".as_ptr().cast::<i8>(),
            *pgaddr_out, (*range).start, (*range).end,
            (*pgaddr_out as CULong).wrapping_add(*pgsize_out as CULong) as *mut c_void,
        );
    }
    while (*pgaddr_out as CULong) < (*range).start
        || (*range).end < (*pgaddr_out as CULong).wrapping_add(*pgsize_out as CULong)
    {
        *ptep_out = null_mut();
        *error_out = crate::x86_memory_helpers::arch_get_smaller_page_size(
            null_mut(), *pgsize_out, pgsize_out, p2align_out,
        );
        if *error_out != 0 {
            let _ = kprintf(
                b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(pte) failed. %d\\n\\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, (*range).flag,
                fault_addr, reason, *error_out,
            );
            return 1;
        }
        *pgaddr_out = (fault_addr & !((*pgsize_out as CULong).wrapping_sub(1))) as *mut c_void;
    }
    crate::pte_helpers::arch_adjust_allocate_page_size(
        (*(*vm).address_space).page_table, fault_addr, *ptep_out,
        pgaddr_out, pgsize_out,
    );
    0
}
'''
 extern='''unsafe extern "C" {
    static mut process_page_fault_prepare_bounds_debug: crate::debug::Ddebug;
    fn ihk_mc_pt_lookup_pte(
        page_table: *mut c_void, virt: *mut c_void, pgshift: CInt,
        basep: *mut *mut c_void, sizep: *mut SizeT, p2alignp: *mut CInt,
    ) -> *mut CULong;
}
'''
 assert 'fn ihk_mc_pt_lookup_pte(' not in r
 assert r.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 r+='\n// F01 owns the typed Page read; process retains its callback ABI.\n'+getter_rust+'\n'+extern+'\n'+body
 for rel,pre,post in [('kernel/process.c',cp.read_text(),c),('kernel/rust/process_helpers.rs',rp.read_text(),r)]:
  put(P/'candidate'/rel,post)
  put(P/'patch'/(Path(rel).name+'.PAGE-FAULT-PREPARE-AND-TYPED-OFFSET.diff'),''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 put(P/'fixture/original_page_fault_prepare.ACTUAL-C-BLOCK.inc',original+'\n')
 put(P/'fixture/original_page_fault.ACTUAL-C-FULL-REFERENCE.inc',function(cp.read_text(),'int page_fault_process_memory_range(')+'\n')
 put(P/'fixture/page_fault_prepare.ACTUAL-RUST.inc',body)
 put(P/'fixture/page_offset.PROCESS-ADAPTER-ONLY.rs.inc',getter_rust)
 put(P/'fixture/actual_C_selection.inc',selected+'\n')
 put(P/'fixture/actual_C_metadata.inc',metadata)
 # Page provider remains external and unmodified; this packet does not duplicate
 # its private Page implementation or claim its tests.
 put(P/'sourcehandoff/F01-TYPED-PROVIDER-DEPENDENCY.json',json.dumps(dict(scope=SCOPE,source_handoff=pin(F01/'SOURCE-ONLY-TYPED-PROVIDER-HANDOFF.json'),candidate=f01['candidate'],fragment=f01['fragment'],contract=f01['consumer_contract'],status='SOURCE_ONLY_DEPENDENCY_NOT_IN_CANONICAL_OR_THIS_LEAF_FIXTURE'),indent=2)+'\n')
 shutil.copy2(PROD/'source/kernel/rust/abi.rs',P/'fixture/abi.ACTUAL.rs')
 # Exact existing PTE predicates and smaller-page operation, with explicitly
 # controlled hosted lock/lookup/TLB/adjust provider effects for the leaf test.
 pte=(PROD/'source/kernel/rust/pte_helpers.rs').read_text()
 provider=pte[:pte.index('extern "C" {')]+function(pte,'unsafe fn pte_load(')+'\n'
 for name in ['pte_is_null','pte_is_fileoff','pte_is_present']:
  provider+='#[no_mangle]\n'+function(pte,'pub unsafe extern "C" fn '+name+'(')+'\n'
 provider+='#[no_mangle]\n'+function(pte,'pub extern "C" fn arch_adjust_allocate_page_size(').replace('fn arch_adjust_allocate_page_size(','fn fixture_actual_arch_adjust_allocate_page_size(',1)+'\n'
 provider+='''extern "C" { fn fixture_adjust_effect(pt:*mut core::ffi::c_void,addr:CULong,pte:*mut CULong,base:*mut *mut core::ffi::c_void,size:*mut SizeT); }
#[no_mangle]
pub unsafe extern "C" fn arch_adjust_allocate_page_size(pt:*mut core::ffi::c_void,addr:CULong,pte:*mut CULong,base:*mut *mut core::ffi::c_void,size:*mut SizeT) {
    fixture_actual_arch_adjust_allocate_page_size(pt,addr,pte,base,size);
    fixture_adjust_effect(pt,addr,pte,base,size);
}
'''
 put(P/'fixture/pte_provider.ACTUAL-RUST.inc',provider)
 xm=(PROD/'source/kernel/rust/x86_memory_helpers.rs').read_text()
 smaller=function(xm,'pub unsafe extern "C" fn x86_smaller_page_size_result(').replace('fn x86_smaller_page_size_result(','fn fixture_actual_smaller_page_size(',1)
 put(P/'fixture/smaller_provider.ACTUAL-RUST.inc','use crate::abi::CULong;\nconst PTL3_SIZE:CULong=1<<30;const PTL2_SIZE:CULong=1<<21;const PTL1_SIZE:CULong=1<<12;const PTL3_SHIFT:i32=30;const PTL2_SHIFT:i32=21;const PTL1_SHIFT:i32=12;const ENOMEM:i32=12;\n#[no_mangle]\n'+smaller+'\n')
 put(P/'fixture/actual_provider.rs','''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;use core::ptr::null_mut;
use abi::{CInt,CULong,SizeT,ProcessVm,VmRange,IhkSpinlock};
const PF_PATCH:CULong=1<<29;const EFAULT:CInt=14;
#[repr(C)] pub struct Ddebug { file:*const i8,func:*const i8,fmt:*const i8,line_flags:u32 }
extern "C" {
 static mut process_page_fault_prepare_bounds_debug:Ddebug;
 fn ihk_mc_pt_lookup_pte(pt:*mut c_void,virt:*mut c_void,shift:CInt,base:*mut *mut c_void,size:*mut SizeT,align:*mut CInt)->*mut CULong;
 fn kprintf(format:*const i8,...)->CInt;
}
mod spinlock_helpers { use crate::abi::IhkSpinlock;extern "C" { pub fn __ihk_mc_spinlock_lock_noirq(lock:*mut IhkSpinlock); } }
mod pte_helpers { include!("pte_provider.ACTUAL-RUST.inc"); }
mod smaller { include!("smaller_provider.ACTUAL-RUST.inc"); }
mod x86_memory_helpers {
 use core::ffi::c_void;use crate::abi::{CULong,CInt,SizeT};
 extern "C" { pub fn flush_tlb_single(addr:CULong);pub fn arch_get_smaller_page_size(args:*mut c_void,size:SizeT,newsize:*mut SizeT,align:*mut CInt)->CInt; }
}
include!("page_fault_prepare.ACTUAL-RUST.inc");
#[no_mangle] pub unsafe extern "C" fn fixture_layout(out:*mut usize) {
 use core::mem::{size_of,align_of,offset_of};
 let x=[size_of::<ProcessVm>(),align_of::<ProcessVm>(),offset_of!(ProcessVm,address_space),offset_of!(ProcessVm,page_table_lock),
 size_of::<abi::AddressSpace>(),offset_of!(abi::AddressSpace,page_table),size_of::<VmRange>(),offset_of!(VmRange,start),offset_of!(VmRange,end),offset_of!(VmRange,flag),offset_of!(VmRange,pgshift),size_of::<IhkSpinlock>(),size_of::<Ddebug>()];
 core::ptr::copy_nonoverlapping(x.as_ptr(),out,x.len());
}
''')
 put(P/'fixture/actual_header_ABI.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <ihk/debug.h>
extern int process_page_fault_prepare_body_result(struct process_vm *,struct vm_range *,uintptr_t,uint64_t,pte_t **,void **,size_t *,int *,int *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_page_fault_prepare_body_result),int (*)(struct process_vm *,struct vm_range *,uintptr_t,uint64_t,pte_t **,void **,size_t *,int *,int *)),"exact borrowed preparation out-pointer ABI");
_Static_assert(sizeof(uintptr_t)==8&&sizeof(uint64_t)==8&&sizeof(size_t)==8&&sizeof(pte_t)==8&&sizeof(int)==4,"actual supported scalar/output widths");
_Static_assert(PF_PROT==1&&PF_PATCH==(1UL<<29),"original fault reason masks");
_Static_assert(sizeof(struct ddebug)==32,"original static bounds selector ABI");
''')
 receipt=dict(scope=SCOPE,status='SUBSTANTIVE_ACTUAL_PAGE_FAULT_PREPARATION_SLICE_AND_TYPED_OFFSET_SOURCE_ONLY',
  predecessor={rel:pin(BASE/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},
  postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},
  original_block=pin(P/'fixture/original_page_fault_prepare.ACTUAL-C-BLOCK.inc'),actual_Rust=pin(P/'fixture/page_fault_prepare.ACTUAL-RUST.inc'),
  original_C_fallback_exact=True,bounds_debug_original_line=bounds_line,F01_dependency=pin(P/'sourcehandoff/F01-TYPED-PROVIDER-DEPENDENCY.json'),
  owner_invariant='Lock acquisition is moved exactly, not added: all Rust outcomes keep the existing page_table_lock held. CONTINUE0 writes the same PTE/address/size/alignment locals before the unchanged C tail; GOTO_OUT1 also writes the same signed error before the unchanged C out: unlock. No Page/allocation/refcount/notification transfer occurs in preparation. Profile/entry debug and anonymous/COW/install/cleanup tail remain original C.',
  provider_debt=['Existing ihk_mc_pt_lookup_pte C public wrapper and its diagnostic/provider callbacks retained','Existing arch_get_smaller_page_size Rust provider includes existing use_1gb_page callback','Hosted lock/lookup/TLB/adjust hooks prove ordering, not native behavior','F01 Page accessor source is required before a coherent fullcrate includes the separate offset adapter','Original page-fault anonymous/memobj/COW/PTE-install/unlock/stray-page cleanup C tail remains'],
  known_remaining_and_difficulty='Finite lower-risk invalidate wrappers remain; F01 typed offset boundary is now consumed source-only. Page-fault preparation is bounded with explicit lock handback; later allocation/COW/accounting/cleanup orchestration has higher ownership/error uncertainty. Default image/provider activation and native acceptance remain broader separate prerequisites. No numeric estimate.',
  compiler_jobs=0,tests_executed=0,CPU_reservations=0,new_executable_queues=0,native_default_credit=False)
 put(P/'sourcehandoff/SOURCE-NEXT-BODY.json',json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-NEXT-BODY.json'),postimages=receipt['postimages'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
