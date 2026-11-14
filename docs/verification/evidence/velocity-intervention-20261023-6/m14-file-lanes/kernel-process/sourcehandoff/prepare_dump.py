"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source prep only for real dump entry+tree operation; no compiler/test/root job.
"""
from pathlib import Path
import difflib,hashlib,json
R=Path('/home/holden/mckernel');B=Path(__file__).resolve().parents[1]
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def item(s,mark):
 start=s.index(mark);brace=s.index('{',start);end=brace+1;depth=1
 while depth:
  if s[end]=='{':depth+=1
  if s[end]=='}':depth-=1
  end+=1
 return s[start:end]
def main():
 c=(R/'kernel/process.c').read_text();rust=(R/'kernel/rust/process_helpers.rs').read_text();rbtree=(R/'kernel/rust/rbtree.rs').read_text()
 assert pin(R/'kernel/process.c')['sha256']=='08c238a08066a6eda5f346bbd6e6f87333bd505d8d598276dc9c52cd43568a45'
 assert pin(R/'kernel/rust/process_helpers.rs')['sha256']=='d04b48c887c834edd6380e3ae06fccdef7dfafaf67196fd28af7f9571993bd6d'
 oldblock=c[c.index('#ifdef DEBUG_PRINT_PROCESS'):c.index('extern struct thread *arch_switch_context')]
 dtree=item(oldblock,'static void dtree(');dump=item(oldblock,'static void dump_tree(')
 disabled='static void dump_tree(struct process_vm *vm) {}';assert disabled in oldblock
 prefix='''#ifdef DEBUG_PRINT_PROCESS
#undef DDEBUG_DEFAULT
#define DDEBUG_DEFAULT DDEBUG_PRINT
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
/* Existing compile-time dump gate, exposed as readonly ABI data only. */
const int process_dump_tree_enabled = 1;
#else
'''
 postblock=prefix+dtree+'\n'+dump+'''\n#endif
#else
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
const int process_dump_tree_enabled = 0;
#else
'''+disabled+'\n#endif\n#endif\n\n'
 original_entry=item(c,'PROCESS_SCHED_PUBLIC_BRIDGE void vm_range_insert_dump_bridge(')
 postc=c.replace(oldblock,postblock,1).replace(original_entry,'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+original_entry+'\n#endif',1)
 extern='    fn vm_range_insert_dump_bridge(vm: *mut c_void);'
 assert rust.count(extern)==1
 assert rust.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 postrust=rust.replace(extern,'    static process_dump_tree_enabled: CInt;',1)
 helper='''// Same synchronous in-order diagnostic traversal as the displaced dtree.
// The existing VM/range exclusion keeps every visited node live. Field reads
// and the right-child load remain after left traversal and the logger call.
unsafe fn process_dump_tree_node(node: *mut RbNode, level: CInt) {
    if node.is_null() {
        return;
    }
    let range = vm_range_from_rb_node(node);
    process_dump_tree_node((*node).rb_left, level.wrapping_add(1));
    let _ = kprintf(
        b"dtree: %0*d, %p: %lx-%lx\\n\\0".as_ptr().cast(),
        level,
        0 as CInt,
        range,
        (*range).start,
        (*range).end,
    );
    process_dump_tree_node((*node).rb_right, level.wrapping_add(1));
}
'''
 entry='''/// Preserve DEBUG_PRINT_PROCESS gating without retaining C dump computation.
/// Disabled dumping never dereferences vm. Enabled dumping logs the header
/// before loading the root, then synchronously visits the borrowed live tree.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert_dump_bridge(vm: *mut c_void) {
    if core::ptr::read_volatile(core::ptr::addr_of!(process_dump_tree_enabled)) == 0 {
        return;
    }
    let _ = kprintf(b"dump_tree %p\\n\\0".as_ptr().cast(), vm);
    let root = (*vm.cast::<ProcessVm>()).vm_range_tree.rb_node.cast::<RbNode>();
    process_dump_tree_node(root, 1);
}
'''
 marker='#[no_mangle]\npub unsafe extern "C" fn process_vm_range_insert_dump_result('
 assert postrust.count(marker)==1;postrust=postrust.replace(marker,helper+'\n'+entry+'\n'+marker,1)
 assert postrust.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 for name,before,after,relative in [('process.c',c,postc,'kernel/process.c'),('process_helpers.rs',rust,postrust,'kernel/rust/process_helpers.rs')]:
  (B/'sourcehandoff'/f'{name}.PREIMAGE').write_text(before)
  target=B/'candidate'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(after)
  (B/'patch'/f'{name}.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
 for name,text in [('original_dtree.ACTUAL-C.inc',dtree),('original_dump_tree.ACTUAL-C.inc',dump),('original_disabled_dump.ACTUAL-C.inc',disabled),('original_entry.ACTUAL-C.inc',original_entry),('actual_dump_helpers.ACTUAL-RUST.inc',helper+'\n'+entry),('actual_selected_and_fallback_block.ACTUAL-C.inc',postblock)]:
  (B/'fixture'/name).write_text(text+'\n')
 (B/'fixture/abi.ACTUAL.rs').write_bytes((R/'kernel/rust/abi.rs').read_bytes())
 node=item(rbtree,'pub struct RbNode {')
 (B/'fixture/rbnode.ACTUAL.rs.inc').write_text('#[repr(C)]\n'+node+'\n')
 conversion=item(rust,'unsafe fn vm_range_from_rb_node(')
 prefix='''#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
mod rbtree {
use crate::abi::CULong;
'''+ '#[repr(C)]\n'+node+'\n}\n'+'''use core::ffi::c_void;
use abi::{CInt,ProcessVm,VmRange};
use rbtree::RbNode;
unsafe extern "C" {
    fn kprintf(format:*const i8,...)->CInt;
    static process_dump_tree_enabled:CInt;
}
'''+conversion+'\n'+helper+'\n'
 (B/'fixture/actual_provider.rs').write_text(prefix+entry.replace('fn vm_range_insert_dump_bridge(','fn fixture_rust_vm_range_insert_dump_bridge(',1)+'''
#[no_mangle]
pub unsafe extern "C" fn fixture_dump_layout(out:*mut usize) {
    let values=[core::mem::size_of::<VmRange>(),core::mem::offset_of!(VmRange,vm_rb_node),
        core::mem::offset_of!(VmRange,start),core::mem::offset_of!(VmRange,end),
        core::mem::offset_of!(ProcessVm,vm_range_tree),core::mem::size_of::<RbNode>(),
        core::mem::offset_of!(RbNode,rb_left),core::mem::offset_of!(RbNode,rb_right),
        core::mem::size_of::<CInt>()];
    core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
''')
 (B/'fixture/production_leaf_provider.rs').write_text(prefix+entry)
 (B/'fixture/actual_default_and_fallback_consumer.c').write_text('''#include <process.h>
#include <process_helpers.h>
#include <ihk/debug.h>
'''+postblock+'''#ifdef MCKERNEL_RUST_PROCESS_HELPERS
extern void vm_range_insert_dump_bridge(struct process_vm *);
#else
#define PROCESS_SCHED_PUBLIC_BRIDGE static
'''+original_entry+'\n#endif\nvoid (*const actual_dump_consumer)(struct process_vm *)=vm_range_insert_dump_bridge;\n')
 receipt=dict(scope=SCOPE,status='SOURCE_IMPLEMENTATION_PREPARED_NO_COMPILER_TEST_OR_CPU_RESERVATION',chosen_actual_body='vm_range_insert_dump_bridge plus tightly coupled dump_tree/dtree computation',source_preimages={p:pin(R/p) for p in ['kernel/process.c','kernel/rust/process_helpers.rs','kernel/include/process_helpers.h','kernel/rust/abi.rs','kernel/rust/rbtree.rs']},postimages={p:pin(B/'candidate'/p) for p in ['kernel/process.c','kernel/rust/process_helpers.rs']},gate='Same #ifdef DEBUG_PRINT_PROCESS C compile rule exposes readonly process_dump_tree_enabled=1/0; original DDEBUG_DEFAULT update preserved. No C function/getter introduced.',default_profile='Gate0 returns without reading vm or tree, exactly original no-op.',enabled_profile='Existing kprintf header then root load; exact in-order recursion/typed width0/range pointers/UL fields and formats. Right edge read after node logging; no pointer retained.',unconditional_kprintf_declaration_reused=True,kprintf_declaration_count=1,prior_E0428_failure='2fb3a229/e9a1 retained; no duplicate declaration added',C_compute_dump_helpers_remaining_in_selected_profile=False,C_fallback_exact_bodies_retained=True,remaining_C_debt=['Readonly compile-gate data process_dump_tree_enabled','Other process.c compute bodies and existing debug selector metadata; no whole file/area credit'],ownership='Same caller-held VM range exclusion and borrowed live tree; no allocation/free/locks/refcount changes. No Rust references to foreign allocations.',compiler_jobs=0,CPU_reservations=0,default_image_native=False)
 (B/'sourcehandoff/SOURCE-CANDIDATE-AND-ABI.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(scope=SCOPE,receipt=pin(B/'sourcehandoff/SOURCE-CANDIDATE-AND-ABI.json'),postimages=receipt['postimages'],compiler_jobs=0),indent=2))
if __name__=='__main__':main()
