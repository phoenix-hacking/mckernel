#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private signal forwarding prefix conditioned on an already initialized context.
No selected original callback or absent-slot semantics are proposed here.
"""
import difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent.parent;B=A/'M14-CONVERSION-FIRST-COMPOSITION-1';ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
assert ref(B/'SOURCE-READY.json')['sha256']=='caef14198a096315e21380de49982772d8070a6489ec91d4d2f0c4d2dde3473e'
pre=(B/'postimage/kernel/rust/syscall_policy.rs').read_text();c=(B/'postimage/kernel/syscall.c').read_text();abi=(ROOT/'kernel/rust/abi.rs').read_text();header=(ROOT/'kernel/include/syscall.h').read_text();x86=(ROOT/'kernel/rust/x86_cpu_helpers.rs').read_text()
assert '__NR_rt_sigaction = 13,' in header and '__NR_rt_sigprocmask = 14,' in header
assert 'pub struct KSigAction' in abi and 'pub sa_handler: *mut c_void' in abi and 'pub sa_flags: CULong' in abi
for i in range(6):assert f'fn ihk_mc_syscall_arg{i}' in x86
assert 'fn syscall_generic_forwarding(n: CInt, ctx: *mut X86UserContext) -> CLong' in pre
assert 'ihk_mc_syscall_set_arg0(&ctx0, sigmask);' in c
assert 'ihk_mc_syscall_set_arg0(&ctx0, sig);' in c and '(unsigned long)act->sa.sa_handler' in c and 'ihk_mc_syscall_set_arg2(&ctx0, act->sa.sa_flags);' in c
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Prefixes for an already initialized context; no original callback is selected.
use core::ptr::addr_of;
use crate::abi::{CInt, CLong, CULong, KSigAction, X86UserContext};
use crate::x86_cpu_helpers::{ihk_mc_syscall_set_arg0, ihk_mc_syscall_set_arg1, ihk_mc_syscall_set_arg2};

/// Apply the existing rt_sigprocmask forwarding prefix to supplied context.
///
/// # Safety
/// `ctx` must be an aligned live fully initialized context, writable and retained
/// through the synchronous generic forwarder. Its untouched argument slots and
/// all downstream endpoint semantics require an independently approved contract.
pub(super) unsafe fn forward_mask_on_initialized_context(ctx: *mut X86UserContext, mask: CULong) -> CLong {
    unsafe { ihk_mc_syscall_set_arg0(ctx, mask) };
    unsafe { super::syscall_generic_forwarding(14, ctx) }
}

/// Apply the existing ordered sigaction prefix to supplied context.
///
/// # Safety
/// `ctx` meets the same initialized-context contract above. `action` must remain
/// valid, aligned and initialized for the original handler and flags reads. The
/// caller retains original update ordering and process/endpoint synchronization.
pub(super) unsafe fn forward_action_on_initialized_context(ctx: *mut X86UserContext, sig: CInt, action: *const KSigAction) -> CLong {
    unsafe { ihk_mc_syscall_set_arg0(ctx, sig as CULong) };
    let handler = unsafe { addr_of!((*action).sa.sa_handler).read() } as CULong;
    unsafe { ihk_mc_syscall_set_arg1(ctx, handler) };
    let flags = unsafe { addr_of!((*action).sa.sa_flags).read() };
    unsafe { ihk_mc_syscall_set_arg2(ctx, flags) };
    unsafe { super::syscall_generic_forwarding(13, ctx) }
}
'''
post=pre+'\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_signal_forward_initialized_contract_candidate, target_arch = "x86_64"))]\n#[path = "f03_signal_forward_initialized_contract_candidate.rs"]\nmod f03_signal_forward_initialized_contract_candidate;\n'
# This is a utility only: no C selector, no original symbol export, no context
# initialization strategy and no default enablement or callable production path.
assert '#[no_mangle]' not in leaf and 'zeroed' not in leaf and 'MaybeUninit' not in leaf
assert leaf.index('set_arg0(ctx, sig as CULong)')<leaf.index('sa.sa_handler').__int__()<leaf.index('set_arg1(ctx, handler)')<leaf.index('sa.sa_flags')<leaf.index('set_arg2(ctx, flags)')<leaf.index('syscall_generic_forwarding(13, ctx)')
for rel,text in [('kernel/rust/syscall_policy.rs',pre)]:
 p=D/'preimage'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
for rel,text in [('kernel/rust/syscall_policy.rs',post),('kernel/rust/f03_signal_forward_initialized_contract_candidate.rs',leaf)]:
 p=D/'postimage'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
patch=''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/kernel/rust/syscall_policy.rs',tofile='b/kernel/rust/syscall_policy.rs'))+''.join(difflib.unified_diff([],leaf.splitlines(True),fromfile='/dev/null',tofile='b/kernel/rust/f03_signal_forward_initialized_contract_candidate.rs'))
f=D/'SIGNAL-DEFINED-PREFIX.PRIVATE-NOT-APPLIED.patch';f.write_text(patch)
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_INITIALIZED_CONTEXT_PREFIX_ONLY_NO_ORIGINAL_CALLBACK_SELECTION','patch':ref(f),'leaf':ref(D/'postimage/kernel/rust/f03_signal_forward_initialized_contract_candidate.rs'),'source_C':ref(B/'postimage/kernel/syscall.c'),'x86_setters_getters':ref(ROOT/'kernel/rust/x86_cpu_helpers.rs'),'number_header':ref(ROOT/'kernel/include/syscall.h'),'checks':['original mask arg0 then forward14; action arg0 then handler arg1 then flags arg2 then forward13','signed CInt to CULong preserves modulo conversion','no original callback export/selector and no uninitialized context reads or zero-initialization policy','new Rust module is gated and no config enables it'],'open_contract':'Original C creates uninitialized context, sets only one or three registers, but existing generic forwarder reads all six argument registers. Root must explicitly specify valid values and whether extra slots may be read/marshalled; no accepted parity or guessed zero semantics. Signal request/endpoint lifetime and action ordering still require independent review.','runtime_authority':None,'actual_compile_link_native':False,'callback_implementation_complete':False}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
