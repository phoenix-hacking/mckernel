#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Generate compile-only native sigreturn layout witnesses against actual C/Rust types.
No compilation, test, kernel execution, or canonical/shared mutation.
"""
from pathlib import Path
import hashlib, json
here = Path(__file__).resolve().parent
rows = []
def add(key,c,r): rows.append({'key': key,'c': c,'rust': r})
for f in ('flags','link','sigstack','regs','fpregs','reserve','sigmask','info'):
    add('frame.'+f, f'__builtin_offsetof(struct sigsp, {f})', f'offset_of!(Frame, {f})')
for f in ('ss_sp','ss_flags','ss_size'):
    add('stack.'+f, f'__builtin_offsetof(stack_t, {f})', f'offset_of!(SigStack, {f})')
add('stack.size','sizeof(stack_t)','size_of::<SigStack>()')
add('stack.align','__alignof__(stack_t)','align_of::<SigStack>()')
add('thread.vm','__builtin_offsetof(struct thread, vm)','offset_of!(Thread, vm)')
add('process_vm.region','__builtin_offsetof(struct process_vm, region)','offset_of!(ProcessVm, region)')
for f in ('user_start','user_end'):
    add('vm_regions.'+f, f'__builtin_offsetof(struct vm_regions, {f})',f'offset_of!(VmRegions, {f})')
add('context.gpr','__builtin_offsetof(struct x86_user_context, gpr)','offset_of!(X86UserContext, gpr)')
for f in ('r8','r9','r10','r11','r12','r13','r14','r15','rdi','rsi','rbp','rbx','rdx','rax','rcx','rsp','rip','rflags','orig_rax'):
    add('context.gpr.'+f, f'__builtin_offsetof(struct x86_user_context, gpr.{f})',f'offset_of!(X86UserContext, gpr) + offset_of!(X86BasicRegs, {f})')
add('frame.regs.rsp','__builtin_offsetof(struct sigsp, regs[15])','offset_of!(Frame, regs) + 15 * size_of::<CULong>()')
add('frame.regs.rip','__builtin_offsetof(struct sigsp, regs[16])','offset_of!(Frame, regs) + 16 * size_of::<CULong>()')
add('frame.regs.rflags','__builtin_offsetof(struct sigsp, regs[17])','offset_of!(Frame, regs) + 17 * size_of::<CULong>()')
add('thread.sigmask', '__builtin_offsetof(struct thread, sigmask)', 'offset_of!(Thread, sigmask)')
add('sigset.size', 'sizeof(sigset_t)', 'size_of::<SigSet>()')
add('sigset.align', '__alignof__(sigset_t)', 'align_of::<SigSet>()')
add('sigset.first.offset', '__builtin_offsetof(sigset_t, __val[0])', 'offset_of!(SigSet, val)')
add('thread.sigmask.first.offset', '__builtin_offsetof(struct thread, sigmask.__val[0])', 'offset_of!(Thread, sigmask) + offset_of!(SigSet, val)')
add('sigset.first.width', 'sizeof(((sigset_t *)0)->__val[0])', 'inferred_size(&SIGSET_EXAMPLE.val[0])')
prior = here.parent / 'M14-ARCH5-SIGRETURN-ABI-WITNESS-20261030-1/GEOMETRY.json'
assert rows[:40] == json.loads(prior.read_text()) and len(rows) == 46
keys = here/'GEOMETRY.json'
keys.write_text(json.dumps(rows,indent=2)+'\n')
c = ['/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */',
     '/* Compile-only data in actual native arch TU after struct sigsp. Not production. */',
     '#ifdef MCKERNEL_SIGRETURN_ABI_WITNESS_ONLY',
     '#ifndef MCKERNEL_NATIVE_SIGNAL_STACK', '#error "native signal frame required"', '#endif',
     'const unsigned long sigreturn_extra_c_geometry[] __attribute__((used,section(".sigreturn_extra_c"))) = {']
c += [f'    {row["c"]}, /* {i}: {row["key"]} */' for i,row in enumerate(rows)]
c += ['};', f'_Static_assert(sizeof(sigreturn_extra_c_geometry) / sizeof(unsigned long) == {len(rows)}, "geometry length");', '#endif /* MCKERNEL_SIGRETURN_ABI_WITNESS_ONLY */', '']
(here/'sigreturn-extra-abi.inc').write_text('\n'.join(c))
r = ['//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
     '//! Compile-only actual native Rust types; not a production artifact.',
     '#![cfg(sigreturn_abi_witness_only)]',
     'use core::mem::{align_of, offset_of, size_of};',
     'use crate::abi::{CULong, SigStack, SigSet, Thread, ProcessVm, VmRegions, X86UserContext, X86BasicRegs};',
     'use crate::native_signal::Frame;',
     'const SIGSET_EXAMPLE: SigSet = SigSet { val: [0] };',
     'const fn inferred_size<T>(_: &T) -> usize { size_of::<T>() }',
     '#[used]', '#[no_mangle]', '#[link_section = ".sigreturn_extra_rust"]',
     f'pub static sigreturn_extra_rust_geometry: [u64; {len(rows)}] = [']
r += [f'    ({row["rust"]}) as u64, // {i}: {row["key"]}' for i,row in enumerate(rows)]
r += ['];','']
(here/'sigreturn_extra_abi.rs').write_text('\n'.join(r))
for p in (prior,keys,here/'sigreturn-extra-abi.inc',here/'sigreturn_extra_abi.rs',here/'make_witness.py'):
    print(hashlib.sha256(p.read_bytes()).hexdigest(), p)
print(f'Source generation only: {len(rows)} paired entries; no compile or test')
