#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Two default-off x86 signal forwarders under the exact approved wire contract.
"""
import difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent.parent;B=A/'M14-CONVERSION-FIRST-COMPOSITION-1';ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
contract=A/'M14-REMAINING23-DEFINED-CALLER-CONTRACT-1/ROOT-CONTRACTS.APPROVED.json';assert ref(contract)['sha256']=='534c4df211bcf940f19191607d8d3d26d426e2f82d3bfaa7f392c41fe06df19e'
review=json.loads(contract.read_text())['independent_review'];assert ref(Path(review['path']))==review and review['sha256']=='776d9ce095932811212c2e80bb46af195bc067a3d3d7821ada79593885c0f9d0'
assert ref(B/'SOURCE-READY.json')['sha256']=='caef14198a096315e21380de49982772d8070a6489ec91d4d2f0c4d2dde3473e'
paths=['kernel/syscall.c','kernel/CMakeLists.txt','kernel/rust/syscall_policy.rs'];before={x:(B/'postimage'/x).read_text() for x in paths};after=dict(before)
c=before['kernel/syscall.c'];tokens=lambda s:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]',s)
for symbol in ('syscall_forward_rt_sigprocmask_bridge','syscall_forward_sigaction_update_bridge'):
 start=c.index('long\n'+symbol+'(');end=c.index('\n}',start)+2;old=c[start:end]
 sig='unsigned long sigmask' if 'sigprocmask' in symbol else 'int sig, const void *actp'
 fallback=' '.join(line.strip() for line in old.splitlines())
 assert tokens(old)==tokens(fallback)
 new='#if defined(MCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL)\nextern long '+symbol+'('+sig+');\n#else\n'+fallback+'\n#endif'
 assert old.count('\n')>=new.count('\n');new+='\n'*(old.count('\n')-new.count('\n'))
 assert old.count('\n')==new.count('\n');c=c[:start]+new+c[end:]
after['kernel/syscall.c']=c
cm=before['kernel/CMakeLists.txt'];anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_signal_forward_defined_candidate.rs"\n')
anchor='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\t\tif (MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL)\n\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_signal_forward_defined_candidate")\n\t\t\t\tendif()\n')
anchor='\n\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\tif (MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL)\n\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL)\n\t\t\tendif()\n')
after['kernel/CMakeLists.txt']=cm
after['kernel/rust/syscall_policy.rs']+='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_signal_forward_defined_candidate, target_arch = "x86_64"))]\n#[path = "f03_signal_forward_defined_candidate.rs"]\nmod f03_signal_forward_defined_candidate;\n'
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Signal-forwarding six-slot wire contract; selector is default OFF.
use core::{ffi::c_void, mem::MaybeUninit, ptr::{addr_of, addr_of_mut}};
use crate::abi::{CInt, CLong, CULong, KSigAction, X86UserContext};

/// Forward the existing custom signal-mask payload with approved unused zeroes.
///
/// # Safety
/// Original current-thread, endpoint and synchronous transport contracts apply.
/// Only the six argument fields are initialized; no whole-context reference is
/// valid, and the context remains live until generic forwarding completes.
#[no_mangle]
pub unsafe extern "C" fn syscall_forward_rt_sigprocmask_bridge(sigmask: CULong) -> CLong {
    let mut storage = MaybeUninit::<X86UserContext>::uninit();
    let ctx = storage.as_mut_ptr();
    // SAFETY: Each pointer addresses the naturally aligned live raw field. The
    // first volatile write exactly retains original setter0; remaining fields
    // implement the explicitly approved transmitted zero slots.
    unsafe {
        addr_of_mut!((*ctx).gpr.rdi).write_volatile(sigmask);
        addr_of_mut!((*ctx).gpr.rsi).write(0);
        addr_of_mut!((*ctx).gpr.rdx).write(0);
        addr_of_mut!((*ctx).gpr.r10).write(0);
        addr_of_mut!((*ctx).gpr.r8).write(0);
        addr_of_mut!((*ctx).gpr.r9).write(0);
        super::syscall_generic_forwarding(14, ctx)
    }
}

/// Forward original ordered action fields with approved unused zeroes.
///
/// # Safety
/// The action points to the original live aligned initialized action for the
/// original handler/flags reads; caller retains validation, update ordering and
/// endpoint/lifetime contracts. No whole-context reference or zero is formed.
#[no_mangle]
pub unsafe extern "C" fn syscall_forward_sigaction_update_bridge(sig: CInt, action: *const c_void) -> CLong {
    let mut storage = MaybeUninit::<X86UserContext>::uninit();
    let ctx = storage.as_mut_ptr();
    let action = action.cast::<KSigAction>();
    // SAFETY: Match original volatile setter order, including reading handler
    // after arg0 and flags after arg1. Signed sig converts modulo 2^64, as C.
    unsafe {
        addr_of_mut!((*ctx).gpr.rdi).write_volatile(sig as CULong);
        let handler = addr_of!((*action).sa.sa_handler).read() as CULong;
        addr_of_mut!((*ctx).gpr.rsi).write_volatile(handler);
        let flags = addr_of!((*action).sa.sa_flags).read();
        addr_of_mut!((*ctx).gpr.rdx).write_volatile(flags);
        addr_of_mut!((*ctx).gpr.r10).write(0);
        addr_of_mut!((*ctx).gpr.r8).write(0);
        addr_of_mut!((*ctx).gpr.r9).write(0);
        super::syscall_generic_forwarding(13, ctx)
    }
}
const _: unsafe extern "C" fn(CULong) -> CLong = syscall_forward_rt_sigprocmask_bridge;
const _: unsafe extern "C" fn(CInt, *const c_void) -> CLong = syscall_forward_sigaction_update_bridge;
'''
after['kernel/rust/f03_signal_forward_defined_candidate.rs']=leaf
# Verify actual setter implementation performs exactly these volatile register
# stores; writing through raw pointers avoids references to uninitialized fields.
x86=(ROOT/'kernel/rust/x86_cpu_helpers.rs').read_text()
for idx,reg in enumerate(('rdi','rsi','rdx','r10','r8','r9')):assert f'{idx} => write_volatile(&mut (*uctx).gpr.{reg}, value)' in x86
for num in ('__NR_rt_sigaction = 13,','__NR_rt_sigprocmask = 14,'):assert num in (ROOT/'kernel/include/syscall.h').read_text()
assert 'assume_init' not in leaf and 'zeroed' not in leaf and leaf.count('MaybeUninit::<X86UserContext>::uninit()')==2
mask=leaf[leaf.index('fn syscall_forward_rt_sigprocmask_bridge'):leaf.index('/// Forward original ordered action')]
action=leaf[leaf.index('fn syscall_forward_sigaction_update_bridge'):leaf.index('const _:')]
for part in (mask,action):
 for reg in ('rdi','rsi','rdx','r10','r8','r9'):assert part.count('gpr.'+reg)==1
order=['gpr.rdi).write_volatile(sig as CULong)','sa.sa_handler','gpr.rsi).write_volatile(handler)','sa.sa_flags','gpr.rdx).write_volatile(flags)','gpr.r10).write(0)','gpr.r8).write(0)','gpr.r9).write(0)','syscall_generic_forwarding(13, ctx)']
pos=[action.index(v) for v in order];assert pos==sorted(pos)
assert 'gpr.rdi).write_volatile(sigmask)' in mask and all('gpr.'+r+').write(0)' in mask for r in ('rsi','rdx','r10','r8','r9'))
assert len(c.splitlines())==len(before['kernel/syscall.c'].splitlines())
directives=lambda s:[(i,l) for i,l in enumerate(s.splitlines(),1) if re.match(r'^\s*#\s*(?:line\b|\d)',l)]
assert directives(c)==directives(before['kernel/syscall.c'])
sites=lambda s,m:[(i,x.start()+1,l)for i,l in enumerate(s.splitlines(),1)for x in re.finditer(r'\b'+m+r'!\s*\(',l)]
for m in ('line','file','column'):assert sites(before['kernel/rust/syscall_policy.rs'],m)==sites(after['kernel/rust/syscall_policy.rs'],m)
assert len(sites(before['kernel/rust/syscall_policy.rs'],'line'))==53
patch='';rows=[]
for name,text in after.items():
 post=D/'postimage'/name;post.parent.mkdir(parents=True,exist_ok=True);post.write_text(text)
 if name in before:
  pre=D/'preimage'/name;pre.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before[name])
 patch+=''.join(difflib.unified_diff(before.get(name,'').splitlines(True),text.splitlines(True),fromfile='a/'+name if name in before else '/dev/null',tofile='b/'+name))
 rows.append({'path':name,'preimage':ref(D/'preimage'/name) if name in before else None,'postimage':ref(post)})
f=D/'SIGNAL-DEFINED-CALLERS.ON-FIRST20.PRIVATE-NOT-APPLIED.patch';f.write_text(patch)
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_APPROVED_SIGNAL_FORWARD_CALLERS_DEFAULT_OFF_SOURCE_ONLY','contract':ref(contract),'review':review,'patch':ref(f),'files':rows,'checks':['six raw fields only; original meaningful setter volatile writes and action reads in original order','mask arg0/zeros1-5; action sig/handler/flags/zeros3-5 exact','existing Rust setter maps match raw volatile field stores','original fallback tokens, C #line and 53 policy macro origins preserved','x86 non-UBSAN paired experimental selector default OFF'],'actual_selected_consumer_semantic_closure':'source review 776d9ce0 scope only; final linked profile still open','abi_codegen_lifetime':False,'actual_compile_link_native':False,'default_selection_authorized':False,'runtime_authority':None}
(D/'SIGNAL-SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
