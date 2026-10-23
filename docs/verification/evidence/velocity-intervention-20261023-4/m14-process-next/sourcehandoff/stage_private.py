#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source preparation only: no compiler, test executable, runtime or root operation.
"""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

ROOT = Path('/home/holden/mckernel')
OUT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / 'docs/verification/evidence/velocity-intervention-20261023-4/m14-process-next'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def item(source, marker):
    start = source.index(marker)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        if source[end] == '{': depth += 1
        if source[end] == '}': depth -= 1
        end += 1
    return source[start:end]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    cbytes = (ROOT/'kernel/process.c').read_bytes()
    rbytes = (ROOT/'kernel/rust/process_helpers.rs').read_bytes()
    sched = (ROOT/'kernel/rust/sched_helpers.rs').read_bytes()
    assert digest(cbytes) == 'e2f2562b32ec462d9ee78c74dee4222485a69c4a3e2a81a332663fcef7e2b52d'
    assert digest(sched) == 'd16200db3054d88a83752fda1383d6c101d24de4b787bd78cd42edb46ab251fc'
    c, rust = cbytes.decode(), rbytes.decode()
    original = item(c, 'static int vm_range_insert(struct process_vm *vm, struct vm_range *newrange)')
    declaration = 'static int vm_range_insert(struct process_vm *vm,\n\t\tstruct vm_range *newrange);'
    assert c.count(declaration) == 1
    postc = c.replace(declaration,
        '#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'
        'int vm_range_insert(struct process_vm *vm, struct vm_range *newrange);\n'
        '#else\n'+declaration+'\n#endif', 1)
    for name in ('vm_range_insert_log_bridge', 'vm_range_insert_dump_bridge'):
        assert postc.count('static void '+name+'(') == 1
        postc = postc.replace('static void '+name+'(', 'PROCESS_SCHED_PUBLIC_BRIDGE void '+name+'(', 1)
    postc = postc.replace(original, '#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+original+'\n#endif', 1)
    externs = '''    fn vm_range_insert_log_bridge(
        event: CInt,
        vm: *mut c_void,
        newrange: *mut VmRange,
        range: *mut VmRange,
    );
    fn vm_range_insert_dump_bridge(vm: *mut c_void);
'''
    assert 'fn vm_range_insert(' not in rust
    postrust = rust.replace('unsafe extern "C" {\n', 'unsafe extern "C" {\n'+externs, 1)
    entry = '''/// Own the selected process.c insertion entry in Rust. The caller holds the
/// existing VM range exclusion and supplies a live ProcessVm, exactly as for
/// the former C wrapper; the helper retains all tree mutation and error order.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert(
    vm: *mut ProcessVm,
    newrange: *mut VmRange,
) -> CInt {
    process_vm_range_insert_result(
        (&raw mut (*vm).vm_range_tree).cast::<RbRoot>(),
        newrange,
        vm.cast(),
        Some(vm_range_insert_log_bridge),
        Some(vm_range_insert_dump_bridge),
    )
}
'''
    marker = '#[no_mangle]\npub extern "C" fn process_extend_up_result('
    assert postrust.count(marker) == 1
    postrust = postrust.replace(marker, entry+'\n'+marker, 1)
    for name, before, after, logical in (
        ('process.c', c, postc, 'kernel/process.c'),
        ('process_helpers.rs', rust, postrust, 'kernel/rust/process_helpers.rs'),
    ):
        (OUT/'sourcehandoff'/f'{name}.PREIMAGE').write_text(before)
        (OUT/'candidate'/name).write_text(after)
        (OUT/'patch'/f'{name}.diff').write_text(''.join(difflib.unified_diff(
            before.splitlines(True), after.splitlines(True),
            fromfile='a/'+logical, tofile='b/'+logical)))
    (OUT/'fixture/original_vm_range_insert.ACTUAL-C-BODY.inc').write_text(original+'\n')
    (OUT/'fixture/vm_range_insert.ACTUAL-RUST-ENTRY.inc').write_text(entry)
    (OUT/'fixture/abi.ACTUAL.rs').write_bytes((ROOT/'kernel/rust/abi.rs').read_bytes())
    (OUT/'fixture/rbtree.ACTUAL.rs').write_bytes((ROOT/'kernel/rust/rbtree.rs').read_bytes())
    snippets = []
    for function in ('unsafe fn vm_range_rb_node(', 'unsafe fn vm_range_from_rb_node(',
                     'pub unsafe extern "C" fn process_vm_range_insert_log_result(',
                     'pub unsafe extern "C" fn process_vm_range_insert_dump_result(',
                     'pub unsafe extern "C" fn process_vm_range_insert_result('):
        snippets.append(('#[no_mangle]\n' if function.startswith('pub ') else '')+item(postrust, function))
    prefix = '''#![no_std]
#![allow(dead_code)]
#[path="abi.ACTUAL.rs"] mod abi;
#[path="rbtree.ACTUAL.rs"] mod rbtree;
use core::ffi::c_void;
use core::ptr::null_mut;
use abi::{CInt,ProcessVm,VmRange};
use rbtree::{RbNode,RbRoot,rb_link_node,rb_insert_color};
const EINVAL:CInt=22;
const EFAULT:CInt=14;
const PROCESS_VM_RANGE_INSERT_LOG_OVERLAP:CInt=1;
const PROCESS_VM_RANGE_INSERT_LOG_SUCCESS:CInt=2;
type ProcessVmRangeInsertLogFn=unsafe extern "C" fn(CInt,*mut c_void,*mut VmRange,*mut VmRange);
type ProcessVmRangeInsertDumpFn=unsafe extern "C" fn(*mut c_void);
unsafe extern "C" {
'''
    (OUT/'fixture/actual_provider.rs').write_text(prefix+externs+'}\n'+'\n'.join(snippets)+'\n'+entry+'''
#[no_mangle]
pub unsafe extern "C" fn fixture_rust_layout(out:*mut usize) {
    let values=[core::mem::size_of::<ProcessVm>(),core::mem::size_of::<VmRange>(),
        core::mem::offset_of!(ProcessVm,vm_range_tree),core::mem::offset_of!(VmRange,vm_rb_node),
        core::mem::offset_of!(VmRange,start),core::mem::offset_of!(VmRange,end),
        core::mem::size_of::<CInt>()];
    core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
''')
    # Actual caller bodies remain byte exact in the consumer. Source selection
    # is made with the same MCKERNEL_RUST_PROCESS_HELPERS default selector.
    consumer = '''#include <process.h>
#include <process_helpers.h>
'''+('#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'
        'int vm_range_insert(struct process_vm *vm, struct vm_range *newrange);\n'
        '#else\n'+original+'\n#endif\n')
    consumer = consumer.replace('#else\n'+original,
        '#else\nstatic void vm_range_insert_log_bridge(int,struct process_vm *,struct vm_range *,struct vm_range *);\n'
        'static void vm_range_insert_dump_bridge(struct process_vm *);\n'+original)
    consumer += '\n'+item(c, 'int process_split_range_insert_bridge(struct process_vm *vm,\n\t\tstruct vm_range *range)\n{')+'\n'
    consumer += item(c, 'int process_add_range_insert_bridge(struct process_vm *vm,\n\t\t\t\t    struct vm_range *range)\n{')+'\n'
    consumer += '''#ifndef MCKERNEL_RUST_PROCESS_HELPERS
static void vm_range_insert_log_bridge(int e,struct process_vm *v,struct vm_range *n,struct vm_range *r) {(void)e;(void)v;(void)n;(void)r;}
static void vm_range_insert_dump_bridge(struct process_vm *v) {(void)v;}
#endif
'''
    (OUT/'fixture/actual_default_and_fallback_consumers.c').write_text(consumer)
    receipt = dict(scope=SCOPE,status='SOURCE_PREPARATION_ONLY_EXECUTION_NOT_GRANTED',
        target='kernel/process.c:vm_range_insert',worklist='M14-02-02',
        exact_c_fallback_preserved=True,new_compute_c=False,
        selected_c_computation='none in vm_range_insert entry after selection; two existing Rust-entry callbacks remain C',
        remaining_c_callbacks=['vm_range_insert_log_bridge','vm_range_insert_dump_bridge; dump_tree and optional dtree subtree'],
        unchanged_real_default_callers=['process_split_range_insert_bridge','process_add_range_insert_bridge'],
        lifetime='Live nonnull ProcessVm and preexisting caller-held VM exclusion; newrange handling unchanged in existing helper. No ownership transfer or reference drop.',
        order='Existing helper logs overlap then returns -EFAULT, or logs success then dumps the PRE-INSERT tree then rb_link_node/rb_insert_color; wrapper does not add a lock or callback.',
        tests_run=False,source_review_pass=False,full_crate_pass=False,
        actual_default_TU_pass=False,default_image_link_pass=False,native_pass=False,
        failure_family_history=[],files={})
    for path in (OUT/'sourcehandoff/process.c.PREIMAGE',OUT/'sourcehandoff/process_helpers.rs.PREIMAGE',
                 OUT/'candidate/process.c',OUT/'candidate/process_helpers.rs',
                 OUT/'fixture/abi.ACTUAL.rs',OUT/'fixture/rbtree.ACTUAL.rs'):
        receipt['files'][str(path.relative_to(OUT))]=digest(path.read_bytes())
    (OUT/'sourcehandoff/SOURCE-CANDIDATE-AND-ABI.json').write_text(json.dumps(receipt,indent=2)+'\n')
    for directory in ('candidate','fixture','patch','sourcehandoff'):
        shutil.copytree(OUT/directory,MIRROR/directory,dirs_exist_ok=True)
    print(json.dumps(receipt,indent=2))


if __name__ == '__main__': main()
