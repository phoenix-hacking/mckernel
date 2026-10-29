#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private context callback pair against the retained ten-callback source batch.
"""
import difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent; A=D.parent; B=A/'M14-PRIVATE-TEN-LEAF-BATCH-1'; ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def toks(s):return re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]',s)
assert ref(B/'SOURCE-READY.json')['sha256']=='958afc6c3caf6960ef74bd095c9d7def8063ffe99d50ec4387432b4e083b3276'
assert ref(B/'TEN-LEAF-BATCH.PRIVATE-NOT-APPLIED.patch')['sha256']=='a36e5af75024ae2fa610004a488230c8e6146f247440b00e441a4743da753948'
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Context callbacks delegate to the existing Rust generic forwarder.
use core::ffi::c_void;
use crate::abi::{CInt, CLong};

type ForwardContext = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;

/// Forward the syscall number and original borrowed user context.
///
/// # Safety
/// The context is the live x86 user context required by the existing forwarder;
/// the caller retains it for the full synchronous call and follows its existing
/// request and endpoint contracts. The pointer is neither retained nor inspected here.
#[no_mangle]
pub unsafe extern "C" fn syscall_forward_context_bridge(number: CInt, context: *mut c_void) -> CLong {
    // SAFETY: Preserve the original context address and callee preconditions.
    unsafe { super::syscall_generic_forwarding(number, context.cast()) }
}

/// Public policy callback for the same existing forwarding operation.
///
/// # Safety
/// Same borrowed context, lifetime and forwarding preconditions as the private
/// callback; no request, endpoint, error or null policy is added by this wrapper.
#[no_mangle]
pub unsafe extern "C" fn syscall_policy_forward_context_bridge(number: CInt, context: *mut c_void) -> CLong {
    // SAFETY: Preserve the original context address and callee preconditions.
    unsafe { super::syscall_generic_forwarding(number, context.cast()) }
}

const _: ForwardContext = syscall_forward_context_bridge;
const _: ForwardContext = syscall_policy_forward_context_bridge;
'''
m=json.loads((B/'SOURCE-CHECKS.json').read_text());rows=m['files'];assert len(rows)==13
before={r['proposed_path']:(B/'postimage'/r['proposed_path']).read_text() for r in rows}
for r in rows: assert ref(B/'postimage'/r['proposed_path'])==r['postimage']
after=dict(before)
c=after['kernel/syscall.c']
old='''static long syscall_forward_context_bridge(int syscall_nr, void *ctx);
void syscall_tsc_to_ts_bridge(unsigned long tsc, void *ts);
unsigned long syscall_timespec_to_jiffy_bridge(const void *ts);
void syscall_ts_add_bridge(void *dst, const void *src);
void *syscall_find_process_bridge(int pid, void *lock_arg);
void syscall_process_unlock_bridge(void *proc, void *lock_arg);'''
new='''#if defined(MCKERNEL_RUST_F03_CONTEXT_FORWARD_PAIR)
extern long syscall_forward_context_bridge(int syscall_nr, void *ctx);
#else
static long syscall_forward_context_bridge(int syscall_nr, void *ctx);
#endif
void syscall_tsc_to_ts_bridge(unsigned long tsc, void *ts); unsigned long syscall_timespec_to_jiffy_bridge(const void *ts); void syscall_ts_add_bridge(void *dst, const void *src); void *syscall_find_process_bridge(int pid, void *lock_arg); void syscall_process_unlock_bridge(void *proc, void *lock_arg);'''
assert c.count(old)==1 and old.count('\n')==new.count('\n')
assert toks(old)==toks('static long syscall_forward_context_bridge(int syscall_nr, void *ctx);\n'+new.split('#endif\n')[1])
c=c.replace(old,new)
old='''static long
syscall_forward_context_bridge(int syscall_nr, void *ctx)
{
\treturn syscall_generic_forwarding(syscall_nr,
\t\t\t(ihk_mc_user_context_t *)ctx);
}

#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long
syscall_policy_forward_context_bridge(int syscall_nr, void *ctx)
{
\treturn syscall_forward_context_bridge(syscall_nr, ctx);
}
#endif'''
new='''#if !defined(MCKERNEL_RUST_F03_CONTEXT_FORWARD_PAIR)
static long syscall_forward_context_bridge(int syscall_nr, void *ctx) { return syscall_generic_forwarding(syscall_nr, (ihk_mc_user_context_t *)ctx); }
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long syscall_policy_forward_context_bridge(int syscall_nr, void *ctx) { return syscall_forward_context_bridge(syscall_nr, ctx); }
#endif
#endif







'''.rstrip('\n')
# Blank lines preserve all following physical origins.
new += '\n' * (old.count('\n') - new.count('\n'))
assert old.count('\n')==new.count('\n') and c.count(old)==1
fallback=new.split('\n',1)[1].split('\n#endif\n#endif',1)[0]
assert toks(old.replace('#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS','').replace('#endif',''))==toks(fallback.replace('#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',''))
c=c.replace(old,new);after['kernel/syscall.c']=c
cm=after['kernel/CMakeLists.txt']
anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_context_forward_pair.rs"\n')
anchor='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_context_forward_pair_candidate")\n')
anchor='COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ;';assert cm.count(anchor)==1
cm=cm.replace(anchor,'COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_CONTEXT_FORWARD_PAIR;MCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ;')
after['kernel/CMakeLists.txt']=cm
after['kernel/rust/syscall_policy.rs']+='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_context_forward_pair_candidate, target_arch = "x86_64"))]\n#[path = "f03_context_forward_pair.rs"]\nmod f03_context_forward_pair;\n'
after['kernel/rust/f03_context_forward_pair.rs']=leaf
policy=before['kernel/rust/syscall_policy.rs']; arch=(ROOT/'kernel/rust/arch_syscall_forward_context_bridge.rs').read_text()
assert 'fn syscall_generic_forwarding(n: CInt, ctx: *mut X86UserContext) -> CLong' in policy
assert 'unsafe { super::syscall_generic_forwarding(number, context.cast()) }' in arch
assert leaf.count('unsafe { super::syscall_generic_forwarding(number, context.cast()) }')==2
assert 'fn syscall_policy_forward_context_bridge(syscall_nr: CInt, ctx: *mut c_void) -> CLong;' in policy
assert 'if ' not in leaf and 'no_mangle' in leaf
assert len(before['kernel/syscall.c'].splitlines())==len(c.splitlines())
directives=lambda s:[(i,l) for i,l in enumerate(s.splitlines(),1) if re.match(r'^\s*#\s*(?:line\b|\d)',l)]
assert directives(before['kernel/syscall.c'])==directives(c)
sites=lambda s,macro:[(i,x.start()+1,l)for i,l in enumerate(s.splitlines(),1)for x in re.finditer(r'\b'+macro+r'!\s*\(',l)]
for macro in ('line','file','column'):assert sites(policy,macro)==sites(after['kernel/rust/syscall_policy.rs'],macro)
assert len(sites(policy,'line'))==53
for r in rows:
 if r['reused_leaf_exact']:assert before[r['proposed_path']]==after[r['proposed_path']]
# Reuse the ten-batch original389 source counter: the two C edits contain no
# metadata, the policy prefix and all nine leaves are exact, and the new leaf
# introduces no descriptors or source-location macros.
assert m['checks'][-1]=='source projection of all 389 registry identities matches original counter'
assert not any(t in leaf for t in ('Ddebug','line!','file!','column!'))
allrows=[];delta='';whole=''
for name,text in after.items():
 post=D/'postimage'/name;post.parent.mkdir(parents=True,exist_ok=True);post.write_text(text)
 original=B/'preimage'/name
 if name in before:
  pre=D/'preimage'/name;pre.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before[name])
  delta+=''.join(difflib.unified_diff(before[name].splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
 else:
  delta+=''.join(difflib.unified_diff([],text.splitlines(True),fromfile='/dev/null',tofile='b/'+name))
 base=original.read_text() if original.exists() else ''
 whole+=''.join(difflib.unified_diff(base.splitlines(True),text.splitlines(True),fromfile='a/'+name if original.exists() else '/dev/null',tofile='b/'+name))
 allrows.append({'path':name,'ten_postimage':ref(B/'postimage'/name) if name in before else None,'postimage':ref(post)})
(D/'CONTEXT-PAIR-ON-TEN.PRIVATE-NOT-APPLIED.patch').write_text(delta)
(D/'TEN-PLUS-CONTEXT-PAIR.PRIVATE-NOT-APPLIED.patch').write_text(whole)
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_PRIVATE_CONTEXT_PAIR_ON_TEN_SOURCE_ONLY','symbols':['syscall_forward_context_bridge','syscall_policy_forward_context_bridge'],'ten_ready':ref(B/'SOURCE-READY.json'),'ten_source_checks':ref(B/'SOURCE-CHECKS.json'),'arch_provider':ref(ROOT/'kernel/rust/arch_syscall_forward_context_bridge.rs'),'delta_patch':ref(D/'CONTEXT-PAIR-ON-TEN.PRIVATE-NOT-APPLIED.patch'),'whole_patch':ref(D/'TEN-PLUS-CONTEXT-PAIR.PRIVATE-NOT-APPLIED.patch'),'files':allrows,'checks':['separate public and private ABI callbacks forward unchanged scalar, context and return to existing generic Rust provider','no new guard, request or endpoint logic; original fallback tokens and C origins preserved','source selector pairs C/Rust x86 Linux6.12 non-UBSAN','prior nine leaf bytes and 53 policy macro sites unchanged','inherited 389 identity projection unchanged: only metadata-free C callback regions, appended metadata-free module'], 'actual_compile_link_native':False,'runtime_authority':None,'independent_review':None}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
