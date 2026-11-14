"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual anonymous allocation retry decision port, source/fixture fragments only.
No second executable queue, compiler, canonical mutation or Page implementation.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
P=Path(__file__).resolve().parent;L=P.parent
B=L/'next-page-fault-prepare/preexec-lock-binding-correction-1'
PROD=L/'production-batch-preparation-1/bounded-source-correction-1'
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
 assert pin(cp)['sha256']=='60065b0b2a9d542d74cd980d98951f36ec9917bd4160700056059c4eaaf710ac'
 assert pin(rp)['sha256']=='035a629fd72d0ac95f4c9f518e583401a69fb790259c4b357b8bb15977062ead'
 c=cp.read_text();r=rp.read_text()
 full=function(c,'int page_fault_process_memory_range(')
 start=full.index('\t\t\tsize_t npages;\n\nretry:')
 end=full.index('\t\t\tdkprintf("%s: clearing 0x%lx:%lu\\n"',start)
 original=full[start:end]
 assert original.count('_ihk_mc_alloc_aligned_pages_node(')==1 and original.count('goto out;')==2
 assert '__FUNCTION__' not in original and '__func__' not in original
 absolute=c.index(full)+start
 line=c[:absolute+original.index('__LINE__')].count('\n')+1
 start_line=c[:absolute].count('\n')+1
 cdecl='''#ifdef MCKERNEL_RUST_PROCESS_HELPERS
/* Existing allocator retains these borrowed static tracking identities. */
const char *const process_page_fault_anon_alloc_file = __FILE__;
const int process_page_fault_anon_alloc_line = ALLOC_LINE;
int process_page_fault_anon_allocate_body_result(struct process_vm *, struct vm_range *,
        uintptr_t, uint64_t, pte_t **, void **, size_t *, int *, void **, int *);
#endif

'''.replace('ALLOC_LINE',str(line))
 selection='''#ifdef MCKERNEL_RUST_PROCESS_HELPERS
            /* A successful pointer passes to the existing zero/map tail.
             * Error1 passes to the existing out: unlock, with no page. */
            if (process_page_fault_anon_allocate_body_result(vm, range,
                    fault_addr, reason, &ptep, &pgaddr, &pgsize, &p2align,
                    &virt, &error))
                goto out;
#else
'''+original+'#endif\n'
 assert c.count(original)==1;c=c.replace(original,selection,1)
 c=c.replace('int page_fault_process_memory_range(',cdecl+'int page_fault_process_memory_range(',1)
 body='''#[no_mangle]
pub unsafe extern "C" fn process_page_fault_anon_allocate_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    ptep_out: *mut *mut CULong,
    pgaddr_out: *mut *mut c_void,
    pgsize_out: *mut SizeT,
    p2align_out: *mut CInt,
    virt_out: *mut *mut c_void,
    error_out: *mut CInt,
) -> CInt {
    // Existing caller owns the page-table lock throughout. No allocation has
    // succeeded on entry; success transfers its virtual pointer to that caller.
    loop {
        let npages = (*pgsize_out / PAGE_SIZE as SizeT) as CInt;
        *virt_out = crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
            npages, *p2align_out,
            IHK_MC_AP_NOWAIT | if (*range).flag & VR_AP_USER != 0 { 0x001000 } else { 0 },
            -1, 1, fault_addr,
            process_page_fault_anon_alloc_file as *mut i8,
            process_page_fault_anon_alloc_line,
        );
        if !(*virt_out).is_null() {
            return 0;
        }
        // Reload pgshift after the allocator, exactly as in the original.
        if (*range).pgshift == 0 && *pgsize_out != PAGE_SIZE as SizeT {
            *error_out = crate::x86_memory_helpers::arch_get_smaller_page_size(
                null_mut(), *pgsize_out, pgsize_out, p2align_out,
            );
            if *error_out != 0 {
                let _ = kprintf(
                    b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(anon) failed. %d\\n\\0".as_ptr().cast(),
                    vm, (*range).start, (*range).end, (*range).flag,
                    fault_addr, reason, *error_out,
                );
                return 1;
            }
            // Unlike the prepare slice, the original clears ptep only AFTER
            // a successful shrink; on shrink failure it preserves old ptep.
            *ptep_out = null_mut();
            *pgaddr_out = (fault_addr & !((*pgsize_out as CULong).wrapping_sub(1))) as *mut c_void;
            continue;
        }
        *error_out = -ENOMEM;
        let _ = kprintf(
            b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):cannot allocate new page. %d\\n\\0".as_ptr().cast(),
            vm, (*range).start, (*range).end, (*range).flag,
            fault_addr, reason, *error_out,
        );
        return 1;
    }
}
'''
 extern='''unsafe extern "C" {
    static process_page_fault_anon_alloc_file: *const i8;
    static process_page_fault_anon_alloc_line: CInt;
}
'''
 assert 'process_page_fault_anon_allocate_body_result(' not in r
 assert r.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 assert 'const IHK_MC_AP_NOWAIT: CULong = 0x0000_02;' in r and 'const VR_AP_USER: CULong = 0x4;' in r
 r+='\n// Anonymous-page retry handoff: no lock/ref/free ownership changes.\n'+extern+'\n'+body
 for rel,pre,post in [('kernel/process.c',cp.read_text(),c),('kernel/rust/process_helpers.rs',rp.read_text(),r)]:
  put(P/'candidate'/rel,post)
  put(P/'patch'/(Path(rel).name+'.ANON-ALLOCATION-DECISION.diff'),''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 mem=PROD/'source/kernel/rust/mem_helpers.rs'
 actual_allocator=function(mem.read_text(),'pub unsafe extern "C" fn _ihk_mc_alloc_aligned_pages_node(')
 put(P/'fixture/allocator.EXISTING-RUST-REFERENCE.inc',actual_allocator+'\n')
 put(P/'fixture/original_anon_allocate.ACTUAL-C-BLOCK.inc',original)
 put(P/'fixture/anon_allocate.ACTUAL-RUST.inc',body)
 put(P/'fixture/C-selection.inc',selection)
 put(P/'fixture/C-tracking-data.inc',cdecl)
 # Small coherent reference fragment preserves both real allocator types and
 # lexical tracking context. It is not a new product C helper or a ready job.
 logical='held-original-page-fault-process.c'
 cfixture='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE-ONLY actual C reference fragment. Future host allocator effect provider
 * returns controlled pointers; this does not execute allocator/backend policy. */
#include <process.h>
#include <ihk/debug.h>
const char *const process_page_fault_anon_alloc_file = "'''+logical+'''";
const int process_page_fault_anon_alloc_line = '''+str(line)+''';
int fixture_original_anon_allocate(struct process_vm *vm, struct vm_range *range,
        uintptr_t fault_addr,uint64_t reason,pte_t **po,void **bo,size_t *so,
        int *ao,void **vo,int *eo)
{
    pte_t *ptep=*po;void *pgaddr=*bo;size_t pgsize=*so;int p2align=*ao;
    void *virt=*vo;int error=*eo;
#line '''+str(start_line)+' "'+logical+'"\n'+original+'''
#line 1 "anon-allocation-fixture-fragment"
    *po=ptep;*bo=pgaddr;*so=pgsize;*ao=p2align;*vo=virt;*eo=error;return 0;
out:
    *po=ptep;*bo=pgaddr;*so=pgsize;*ao=p2align;*vo=virt;*eo=error;return 1;
}
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_alloc_aligned_pages_node),
 void *(*)(int,int,ihk_mc_ap_flag,int,int,uintptr_t,char *,int)),
 "existing actual allocator/tracking ABI, including signed pagecount narrowing");
_Static_assert(IHK_MC_AP_NOWAIT==2&&IHK_MC_AP_USER==0x1000&&IHK_MC_PG_USER==1,
 "same existing allocation flags and user accounting");
_Static_assert(sizeof(size_t)==8&&sizeof(uintptr_t)==8&&sizeof(int)==4,
 "actual LP64 retry arithmetic and CInt conversion");
'''
 put(P/'fixture/original_reference.SOURCE-ONLY.c.inc',cfixture)
 shutil.copy2(PROD/'source/kernel/rust/abi.rs',P/'fixture/abi.ACTUAL.rs')
 put(P/'fixture/hosted_decision.SOURCE-ONLY.rs','''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// No executable queue. The model below tests decision/ownership handoff only;
// exact production allocator source remains in allocator.EXISTING-RUST-REFERENCE.inc.
#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;use core::ptr::null_mut;
use abi::{CInt,CULong,SizeT,ProcessVm,VmRange};
const PAGE_SIZE:CULong=4096;const IHK_MC_AP_NOWAIT:CULong=2;
const VR_AP_USER:CULong=4;const ENOMEM:CInt=12;
extern "C" {
 static process_page_fault_anon_alloc_file:*const i8;
 static process_page_fault_anon_alloc_line:CInt;
 fn kprintf(format:*const i8,...)->CInt;
}
mod mem_helpers {
 use core::ffi::c_void;use crate::abi::{CInt,CULong};
 extern "C" { fn fixture_alloc_effect(n:CInt,a:CInt,f:CULong,node:CInt,user:CInt,addr:CULong,file:*mut i8,line:CInt)->*mut c_void; }
 pub unsafe fn _ihk_mc_alloc_aligned_pages_node(n:CInt,a:CInt,f:CULong,node:CInt,user:CInt,addr:CULong,file:*mut i8,line:CInt)->*mut c_void {
  fixture_alloc_effect(n,a,f,node,user,addr,file,line)
 }
}
mod x86_memory_helpers {
 use core::ffi::c_void;use crate::abi::{CInt,SizeT};
 extern "C" { pub fn arch_get_smaller_page_size(args:*mut c_void,size:SizeT,out:*mut SizeT,align:*mut CInt)->CInt; }
}
include!("anon_allocate.ACTUAL-RUST.inc");
''')
 # Verify existing prepare and all accepted callback ports remain byte exact.
 assert function(r,'pub unsafe extern "C" fn process_page_fault_prepare_body_result(')==function(rp.read_text(),'pub unsafe extern "C" fn process_page_fault_prepare_body_result(')
 assert function(c,'int page_fault_process_memory_range(').count(original)==1
 queued=L/'next-page-fault-prepare/bounded-reference-context-correction-1/sourcehandoff/EXECUTABLE-READY.PAGE-FAULT-PREPARE96-CONTINUATION.NOT-GRANTED.json'
 receipt=dict(scope=SCOPE,status='SUBSTANTIVE_ACTUAL_ANONYMOUS_ALLOCATION_RETRY_SOURCE_ONLY_NO_SECOND_QUEUE',
  predecessor={rel:pin(B/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},
  postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},
  original_C_block=pin(P/'fixture/original_anon_allocate.ACTUAL-C-BLOCK.inc'),
  actual_Rust=pin(P/'fixture/anon_allocate.ACTUAL-RUST.inc'),existing_allocator=pin(P/'fixture/allocator.EXISTING-RUST-REFERENCE.inc'),
  original_C_fallback_exact=True,tracking_source_line=line,
  precise_ownership='Entry is inside phys==NOPHYS with existing page_table_lock already held and no newly acquired Page. Each failed allocation returns NULL and owns no page. Successful pointer returnsCONTINUE0 to the original C clearing/profile/memset/virt_to_phys/page_map tail, transferring no additional reference and performing no helper-side free. Final NULL/shrink error returnsGOTO_OUT1 with no allocation and existing lock still held for original out: unlock. Memobj/page accounting and later COW/map/stray cleanup are unchanged.',
  precise_order='Compute page count with original size_t division/CInt narrowing, reload range flags before each allocation, reload range.pgshift after failure. On successful smaller-page result clear ptep and align pgaddr before retry; on smaller-page error preserve old ptep and old pgaddr while retaining provider-updated size/alignment and exact error log. Exhausted4K/fixedshift failure logs-ENOMEM. Ignore logger return, retain static file/line pointer lifetime.',
  original_provider_ABI='Existing _ihk_mc_alloc_aligned_pages_node(CInt,CInt,CULong,CInt,CInt,CULong,*mut i8,CInt)->*mut c_void; existing tracked allocator/body/backends reused, not duplicated.',
  fixture_fragments=[pin(P/'fixture/original_reference.SOURCE-ONLY.c.inc'),pin(P/'fixture/hosted_decision.SOURCE-ONLY.rs')],
  next_meaningful_check='Actual original block/Rust controlled allocator-return tape with first-attempt success,2M/1G retry-to-success, fixedshift/basepage failure, smaller-page failure retaining ptep, range.pgshift/flags mutation after allocator, signed pagecount narrowing and original static file/line identity. Check no frees/refcount changes and lock retained on both outcomes; allocator model is not production backend acceptance.',
  queued_prepare96_continuation=pin(queued),
  remaining_C_debt=['Memobj get-page/zeroobj selection before anonymous allocation','Anonymous clearing/profile/translation/page_map after allocation','COW allocation/copy/accounting, PTE install and final unlock/stray-page cleanup','Existing allocator backend/tracking/lock callbacks and default/native proof'],
  difficulty='This retry slice has explicit NULL/error/success ownership handoff. The remaining COW/copy/accounting cleanup is more difficult because Page references and old/new physical mappings coexist. No estimate or complete-file claim.',
  failure_history='de43 first prepare96 runtime/reference-context failure and sole bounded9ca continuation preserved; original product035 unchanged by its fixture fix. Earlier245/eb65 and795/404 evidence retained.',
  compiler_jobs=0,tests_executed=0,CPU_reservations=0,new_executable_queues=0,canonical_mutations=0,default_native_credit=False)
 put(P/'sourcehandoff/SOURCE-NEXT-BODY.json',json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-NEXT-BODY.json'),postimages=receipt['postimages'],tracking_line=line,compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
