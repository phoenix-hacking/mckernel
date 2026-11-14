"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source preparation only; compiler/tests/runtime require separate exact root grant.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
ROOT=Path('/home/holden/mckernel');B=Path(__file__).resolve().parents[1]
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def item(text,marker):
 start=text.index(marker);brace=text.index('{',start);end=brace+1;depth=1
 while depth:
  if text[end]=='{':depth+=1
  if text[end]=='}':depth-=1
  end+=1
 return text[start:end]
def main():
 for name,sha in [('kernel/process.c','64af918855ea361bd850d6ad7480d304634c28814e04127fe3dec8c013f21044'),('kernel/rust/process_helpers.rs','3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e'),('kernel/include/process_helpers.h','1e4eceec2c06dcd409d86cbd5e24616684d83e828d62d6ca534e08c4e0a20bcb')]:assert pin(ROOT/name)['sha256']==sha
 c=(ROOT/'kernel/process.c').read_text();rust=(ROOT/'kernel/rust/process_helpers.rs').read_text();debug=(ROOT/'kernel/rust/debug.rs').read_text()
 original=item(c,'PROCESS_SCHED_PUBLIC_BRIDGE void vm_range_insert_log_bridge(')
 original_line=c[:c.index('dkprintf("vm_range_insert:')].count('\n')+1;assert original_line==2086
 selector='''/* Keep the displaced dynamic-debug selector as declarative C ABI data.
 * Rust owns both event branches, field reads and the existing variadic logger.
 * The source-bound original success callsite remains selectable at line 2086.
 */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_vm_range_insert_debug = {
    .file = __FILE__,
    .func = "vm_range_insert_log_bridge",
    .line = 2086,
    .flags = DDEBUG_DEFAULT,
};'''
 postc=c.replace(original,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'+selector+'\n#else\n'+original+'\n#endif',1)
 oldextern='''    fn vm_range_insert_log_bridge(
        event: CInt,
        vm: *mut c_void,
        newrange: *mut VmRange,
        range: *mut VmRange,
    );'''
 assert rust.count(oldextern)==1
 postrust=rust.replace(oldextern,'''    fn kprintf(format: *const i8, ...) -> CInt;
    static mut process_vm_range_insert_debug: crate::debug::Ddebug;''',1)
 body='''/// Preserve the actual process.c log event and variadic ABI. Unknown events
/// do nothing; disabled success logging does not evaluate range fields. The
/// caller retains live ranges through the existing synchronous logger call.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert_log_bridge(
    event: CInt,
    vm: *mut c_void,
    newrange: *mut VmRange,
    range: *mut VmRange,
) {
    if event == PROCESS_VM_RANGE_INSERT_LOG_OVERLAP {
        let _ = kprintf(
            b"vm_range_insert(%p,%lx-%lx %x): overlap %lx-%lx %lx\\n\\0".as_ptr().cast(),
            vm,
            (*newrange).start,
            (*newrange).end,
            (*newrange).flag,
            (*range).start,
            (*range).end,
            (*range).flag,
        );
    } else if event == PROCESS_VM_RANGE_INSERT_LOG_SUCCESS {
        let flags = core::ptr::read_volatile(
            core::ptr::addr_of!(process_vm_range_insert_debug.line_flags),
        ) >> 24;
        if flags != 0 {
            let _ = kprintf(
                b"vm_range_insert: %p,%p: %lx-%lx %x\\n\\0".as_ptr().cast(),
                vm,
                newrange,
                (*newrange).start,
                (*newrange).end,
                (*newrange).flag,
            );
        }
    }
}
'''
 marker='#[no_mangle]\npub unsafe extern "C" fn process_vm_range_insert_log_result('
 assert postrust.count(marker)==1;postrust=postrust.replace(marker,body+'\n'+marker,1)
 for filename,pre,post,key in [('process.c',c,postc,'kernel/process.c'),('process_helpers.rs',rust,postrust,'kernel/rust/process_helpers.rs')]:
  (B/'sourcehandoff'/f'{filename}.PREIMAGE').write_text(pre);(B/'candidate'/filename).write_text(post)
  (B/'patch'/f'{filename}.diff').write_text(''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/'+key,tofile='b/'+key)))
 (B/'fixture/original_log.ACTUAL-C-BODY.inc').write_text(original+'\n')
 (B/'fixture/actual_log.ACTUAL-RUST-BODY.inc').write_text(body)
 (B/'fixture/actual_selector.ACTUAL-C-DATA.inc').write_text(selector+'\n')
 (B/'fixture/abi.ACTUAL.rs').write_bytes((ROOT/'kernel/rust/abi.rs').read_bytes())
 ddebug=item(debug,'pub struct Ddebug {');(B/'fixture/ddebug.ACTUAL.rs.inc').write_text('#[repr(C)]\n'+ddebug+'\n')
 (B/'fixture/actual_provider.rs').write_text('''#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
mod debug {
'''+ '#[repr(C)]\n'+ddebug+'\n}\n'+'''use core::ffi::c_void;
use abi::{CInt,VmRange};
const PROCESS_VM_RANGE_INSERT_LOG_OVERLAP:CInt=1;
const PROCESS_VM_RANGE_INSERT_LOG_SUCCESS:CInt=2;
unsafe extern "C" {
    fn kprintf(format:*const i8,...)->CInt;
    static mut process_vm_range_insert_debug:debug::Ddebug;
}
'''+body.replace('fn vm_range_insert_log_bridge(', 'fn fixture_rust_vm_range_insert_log_bridge(',1)+'''
#[no_mangle]
pub unsafe extern "C" fn fixture_log_layout(out:*mut usize) {
    let values=[core::mem::size_of::<VmRange>(),core::mem::offset_of!(VmRange,start),
        core::mem::offset_of!(VmRange,end),core::mem::offset_of!(VmRange,flag),
        core::mem::size_of::<debug::Ddebug>(),core::mem::align_of::<debug::Ddebug>(),
        core::mem::offset_of!(debug::Ddebug,line_flags),core::mem::size_of::<CInt>()];
    core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
''')
 (B/'fixture/actual_default_and_fallback_consumer.c').write_text('''#include <process.h>
#include <process_helpers.h>
#include <ihk/debug.h>
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
'''+selector+'\nextern void vm_range_insert_log_bridge(int,struct process_vm *,struct vm_range *,struct vm_range *);\n#else\n#define PROCESS_SCHED_PUBLIC_BRIDGE static\n'+original+'\n#endif\nvoid (*const actual_log_consumer)(int,struct process_vm *,struct vm_range *,struct vm_range *)=vm_range_insert_log_bridge;\n')
 record=dict(scope=SCOPE,status='SOURCE_PREPARATION_ONLY_NOT_COMPILED',target='kernel/process.c:vm_range_insert_log_bridge',original_success_debug_line=original_line,selector_identity=dict(file='__FILE__ same actual C TU',func='vm_range_insert_log_bridge',line=2086,fmt='NULL exactly existing macro initialization',flags='DDEBUG_DEFAULT exact current C preprocessing rule'),pure_Rust_body=True,existing_log_provider='Existing production Rust debug::kprintf via existing C variadic symbol kprintf; identical pattern as sched_helpers::process_sched_migrate_log_bridge',existing_selector_ABI='crate::debug::Ddebug repr(C), no guessed offsets or references',variadic_arguments='Original C VmRange.flag is unsigned long even for %x; keep CULong in Rust, preserve actual machine ABI and formatter behavior.',ordering='Unknown event reads no pointers/selector; overlap unconditional reads fields and calls once; success reads dynamic flags first and only evaluates fields/calls when nonzero.',lifetime='Raw borrowed VM/range pointers retained only through synchronous kprintf; no allocation/free/locks/refcount changes. No Rust references to VM/ranges constructed.',fallback_original_unchanged=True,remaining_C_debt=['Declarative process_vm_range_insert_debug selector data','vm_range_insert_dump_bridge plus dump_tree/optional dtree','Other remaining VM range bodies/callbacks; no whole area/file claim'],tests_run=False,compiler_jobs=0,CPU_reservations=0,default_image_native='OPEN',failure_family_history='New diagnostic body source family; prior process-entry observer failure/correction remains retained and is not reset.',source_inputs={name:pin(ROOT/name) for name in ['kernel/process.c','kernel/rust/process_helpers.rs','kernel/include/process_helpers.h','kernel/rust/abi.rs','kernel/rust/debug.rs','lib/include/ihk/debug.h']},postimages={name:pin(B/'candidate'/name) for name in ['process.c','process_helpers.rs']})
 (B/'sourcehandoff/SOURCE-CANDIDATE-AND-ABI.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(B/'sourcehandoff/SOURCE-CANDIDATE-AND-ABI.json'),postimages=record['postimages']),indent=2))
if __name__=='__main__':main()
