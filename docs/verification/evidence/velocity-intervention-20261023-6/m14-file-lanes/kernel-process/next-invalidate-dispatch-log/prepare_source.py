"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source preparation only; no compiler, fixture execution, CPU lease or ready queue.
"""
from pathlib import Path
import difflib, hashlib, json

P=Path(__file__).resolve().parent
LANE=P.parent
BASE=LANE/'production-batch-preparation-1'
ROOT=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
    b=p.read_bytes()
    return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f: f.write(s)
def function(s,marker):
    a=s.index(marker); b=s.index('{',a); e=b+1; depth=1
    while depth:
        depth+=(s[e]=='{')-(s[e]=='}'); e+=1
    return s[a:e]
def main():
    cp=BASE/'candidate/kernel/process.c'
    rp=BASE/'candidate/kernel/rust/process_helpers.rs'
    assert pin(cp)['sha256']=='7ab29dad607ac06e9548065f4395c6e870359558a2777844c1052d67e046ca13'
    assert pin(rp)['sha256']=='908aa07b957d5ff7cc96edfaff4d6324b8e9f12059e5d0d68538c4eba9145cca'
    c=cp.read_text(); r=rp.read_text()
    cm='int process_memobj_invalidate_page_bridge('
    cl='void process_invalidate_one_page_log_bridge('
    orig_dispatch=function(c,cm); orig_log=function(c,cl)
    rust_dispatch='''#[no_mangle]
pub unsafe extern "C" fn process_memobj_invalidate_page_bridge(
    memobj: *mut Memobj,
    phys: CULong,
    pgsize: SizeT,
) -> CInt {
    crate::object_helpers::memobj_invalidate_page(memobj, phys, pgsize)
}'''
    rust_log='''#[no_mangle]
pub unsafe extern "C" fn process_invalidate_one_page_log_bridge(
    arg0: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pte_value: CULong,
    pgaddr: *mut c_void,
    pgshift: CInt,
    error: CInt,
) {
    let _ = kprintf(
        b"invalidate_one_page(%p,%p,%p %#lx,%p,%d):invalidate failed. %d\\n\\0".as_ptr().cast(),
        arg0, page_table, ptep, pte_value, pgaddr, pgshift, error,
    );
}'''
    declarations=[
'''    fn process_memobj_invalidate_page_bridge(
        memobj: *mut Memobj,
        phys: CULong,
        pgsize: SizeT,
    ) -> CInt;
''',
'''    fn process_invalidate_one_page_log_bridge(
        arg0: *mut c_void,
        page_table: *mut c_void,
        ptep: *mut c_void,
        pte_value: CULong,
        pgaddr: *mut c_void,
        pgshift: CInt,
        error: CInt,
    );
''']
    for d in declarations:
        assert r.count(d)==1; r=r.replace(d,'',1)
    assert r.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
    r+='\n\n// Typed invalidate callbacks; original C fallback remains in process.c.\n'+rust_dispatch+'\n\n'+rust_log+'\n'
    for original,declaration in [
        (orig_dispatch,'int process_memobj_invalidate_page_bridge(struct memobj *, uintptr_t, size_t);'),
        (orig_log,'void process_invalidate_one_page_log_bridge(void *, void *, void *, unsigned long, void *, int, int);'),
    ]:
        assert c.count(original)==1
        c=c.replace(original,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'+declaration+'\n#else\n'+original+'\n#endif',1)
    # The selected owner/caller algorithms and every other pending port stay exact.
    for name in ['process_invalidate_one_page_body_result','invalidate_one_page']:
        old=function(rp.read_text(),'pub unsafe extern "C" fn '+name+'(')
        assert function(r,'pub unsafe extern "C" fn '+name+'(')==old
        put(P/'fixture'/('unchanged_'+name+'.ACTUAL-RUST.inc'),old+'\n')
    put(P/'candidate/kernel/process.c',c)
    put(P/'candidate/kernel/rust/process_helpers.rs',r)
    for rel,pre,post in [('kernel/process.c',cp.read_text(),c),('kernel/rust/process_helpers.rs',rp.read_text(),r)]:
        put(P/'patch'/(Path(rel).name+'.NEXT-SLICE.diff'),''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
    put(P/'fixture/original_dispatch.ACTUAL-C.inc',orig_dispatch+'\n')
    put(P/'fixture/original_error_log.ACTUAL-C.inc',orig_log+'\n')
    put(P/'fixture/callbacks.ACTUAL-RUST.inc',rust_dispatch+'\n\n'+rust_log+'\n')
    # Keep the existing typed provider implementation, not a host replacement.
    obj=(ROOT/'kernel/rust/object_helpers.rs').read_text()
    provider='use core::mem::transmute;\nuse crate::abi::{CInt,CULong,SizeT,Memobj};\n'
    provider+='type MemobjPageOpFn = unsafe extern "C" fn(*mut Memobj, CULong, SizeT) -> CInt;\n'
    for marker in ['pub extern "C" fn memobj_op_present_result(', 'pub extern "C" fn memobj_default_page_op_result(', 'pub unsafe extern "C" fn memobj_invalidate_page(']:
        provider+='#[no_mangle]\n'+function(obj,marker)+'\n'
    put(P/'fixture/object_dispatch.ACTUAL-RUST.inc',provider)
    put(P/'fixture/abi.ACTUAL.rs',(ROOT/'kernel/rust/abi.rs').read_text())
    put(P/'fixture/actual_provider.rs','''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path="abi.ACTUAL.rs"] pub mod abi;
mod object_helpers { include!("object_dispatch.ACTUAL-RUST.inc"); }
use core::ffi::c_void;
use abi::{CInt,CULong,SizeT,Memobj};
unsafe extern "C" { fn kprintf(format: *const i8, ...) -> CInt; }
include!("callbacks.ACTUAL-RUST.inc");
#[no_mangle]
pub unsafe extern "C" fn fixture_layout(out: *mut usize) {
    let values=[core::mem::size_of::<Memobj>(),core::mem::align_of::<Memobj>(),
        core::mem::offset_of!(Memobj,ops),core::mem::size_of::<abi::MemobjOps>(),
        core::mem::offset_of!(abi::MemobjOps,invalidate_page)];
    core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
''')
    put(P/'fixture/actual_header_ABI.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <memobj.h>
#include <ihk/debug.h>
extern int process_memobj_invalidate_page_bridge(struct memobj *,uintptr_t,size_t);
extern void process_invalidate_one_page_log_bridge(void *,void *,void *,unsigned long,void *,int,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_memobj_invalidate_page_bridge),memobj_invalidate_page_func_t *),"exact typed dispatch callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_invalidate_one_page_log_bridge),void (*)(void *,void *,void *,unsigned long,void *,int,int)),"exact typed log callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct memobj_ops *)0)->invalidate_page),memobj_invalidate_page_func_t *),"actual memobj invalidate operation signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int (*)(const char *,...)),"unchanged variadic logger ABI");
_Static_assert(sizeof(uintptr_t)==8&&sizeof(size_t)==8&&sizeof(unsigned long)==8&&sizeof(int)==4,"supported LP64 widths and signed CInt result");
''')
    put(P/'fixture/actual_default_and_fallback_consumer.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY.
 * These are the actual callbacks passed by the unchanged Rust invalidate_one_page
 * entry to its existing body-result owner, not a new kernel helper.
 */
#include <process.h>
#include <memobj.h>
extern int process_memobj_invalidate_page_bridge(struct memobj *,uintptr_t,size_t);
extern void process_invalidate_one_page_log_bridge(void *,void *,void *,unsigned long,void *,int,int);
memobj_invalidate_page_func_t *const actual_dispatch_consumer=process_memobj_invalidate_page_bridge;
void (*const actual_error_consumer)(void *,void *,void *,unsigned long,void *,int,int)=process_invalidate_one_page_log_bridge;
''')
    receipt=dict(scope=SCOPE,status='ACTUAL_INVALIDATE_DISPATCH_AND_ERROR_LOG_SOURCE_ONLY_NOT_EXECUTABLE_READY',
        predecessor={str(x.relative_to(BASE/'candidate')):pin(x) for x in [cp,rp]},
        postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},
        original_C={n:pin(P/'fixture'/n) for n in ['original_dispatch.ACTUAL-C.inc','original_error_log.ACTUAL-C.inc']},
        actual_Rust=pin(P/'fixture/callbacks.ACTUAL-RUST.inc'),
        fixture_sources={n:pin(P/n) for n in ['actual_parity.SOURCE-ONLY.c','fixture/actual_provider.rs','fixture/actual_header_ABI.c','fixture/actual_default_and_fallback_consumer.c']},
        planned_comparisons=340,
        fixture_scope='Actual originalC callbacks and new actual Rust callbacks share the exact existing Rust memobj operation dispatcher. 320 present/absent-operation, full-width phys/size, signed-return and operation-mutation cases, plus20 direct logger opaque/null pointer, signed-shift/error and ignored-logger-return cases. Actual owner/caller source retained unchanged, but its full PTE/lock algorithm is not executed by this minimal callback fixture.',
        providers={rel:pin(ROOT/rel) for rel in ['kernel/rust/object_helpers.rs','kernel/rust/abi.rs','kernel/include/memobj.h','lib/include/ihk/debug.h']},
        invariant='Unchanged invalidate_one_page passes these exact callbacks to its unchanged existing Rust owner. Owner resolves phys/page/PTE transitions and page_unmap before dispatch; a nonzero signed dispatch result invokes the logger once with current live PTE before returning that same result. New wrappers acquire no locks, references or ownership and retain no pointers. Existing typed memobj operation is invoked once if present, otherwise returns0. Error logger ignores kprintf return and preserves all pointer/UL/CInt variadic arguments.',
        original_C_fallback_exact=True,kprintf_declaration_count=1,
        remaining_C_debt=['All other invalidate PTE/phys/page offset/contiguity/TLB/panic bridges','process_invalidate_range_log_bridge and remap range logging','phys_to_page C provider and existing lock/backend callbacks','Actual memobj invalidate operation implementations selected at runtime'],
        qualified_scope='No caller algorithm, ABI, kernel lock/refcount, PTE or notification changes. No new compute-C helper. Real originalC/Rust/header fixture sources only; no compilation or comparison acceptance.',
        failure_history_preserved=['Historical duplicate kprintf E0428 2fb/e9a','Accepted sync bounded comma correction 4e2d/795, no replay','Dump original c774 observer failure and retained84ef/e48c acceptance','Unrun production9d/4df plus current observer successor01fbc preserved unchanged'],
        queued_production_ready=pin(BASE/'EXECUTABLE-READY.OBSERVER-SUCCESSOR.NOT-GRANTED.json'),
        compiler_jobs=0,fixture_runs=0,CPU_reservations=0,new_executable_queues=0,fullimage_native_credit=False)
    put(P/'sourcehandoff/SOURCE-NEXT-BODY.json',json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(scope=SCOPE,receipt=pin(P/'sourcehandoff/SOURCE-NEXT-BODY.json'),postimages=receipt['postimages'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__': main()
