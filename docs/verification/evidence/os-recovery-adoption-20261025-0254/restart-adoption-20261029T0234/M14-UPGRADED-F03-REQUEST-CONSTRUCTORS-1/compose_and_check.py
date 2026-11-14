#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only experimental declared-arity request constructor candidate.
"""
import difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-PRIVATE-TEN-LEAF-BATCH-1';ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def tok(s):return re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]',s)
contract=A/'M14-F03-REQUEST-CONSTRUCTOR-CONTRACT-1/ROOT-CONTRACT.REFINED-APPROVED.json'
assert ref(contract)['sha256']=='ca85a6c4de8c6e09f03039ffd7fc8d3c9aa3803ea94dcea21e0d52de11905ed0'
ct=json.loads(contract.read_text());assert ct['source_implementation_authorized'] and not ct['default_selection_authorized']
assert ref(B/'SOURCE-READY.json')['sha256']=='958afc6c3caf6960ef74bd095c9d7def8063ffe99d50ec4387432b4e083b3276'
files=['kernel/syscall.c','kernel/CMakeLists.txt','kernel/rust/syscall_policy.rs']
before={x:(B/'postimage'/x).read_text() for x in files};after=dict(before)
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Experimental declared-arity wire constructors; default selection stays disabled.
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::addr_of_mut;
use crate::abi::{CInt, CLong, CULong, SyscallRequest};

// Object alignment is separate from the 72-byte, 8-aligned C request type.
#[repr(C, align(64))]
struct DmaRequest(MaybeUninit<SyscallRequest>);
const _: () = {
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(offset_of!(SyscallRequest, number) == 16 && offset_of!(SyscallRequest, args) == 24);
    assert!(align_of::<DmaRequest>() == 64);
};

/// Construct only the approved wire fields; IDs and valid belong to the callee.
///
/// # Safety
/// The existing synchronous do_syscall contract, request/response lifetime,
/// endpoint and caller-specific number/argument preconditions must all hold.
/// The current CPU and helper must be usable in the calling context.
unsafe fn forward(number: CInt, args: [CULong; 6]) -> CLong {
    let mut storage = DmaRequest(MaybeUninit::uninit());
    let request = storage.0.as_mut_ptr();
    // SAFETY: Aligned live storage. Raw field pointers never form a reference to
    // the incomplete request. Only approved number and six wire slots are set;
    // the existing helper owns sender IDs and valid before their first read.
    unsafe {
        addr_of_mut!((*request).number).write(number as CULong);
        let slots = addr_of_mut!((*request).args).cast::<CULong>();
        slots.add(0).write(args[0]);
        slots.add(1).write(args[1]);
        slots.add(2).write(args[2]);
        slots.add(3).write(args[3]);
        slots.add(4).write(args[4]);
        slots.add(5).write(args[5]);
        super::do_syscall(request, super::ihk_mc_get_processor_id())
    }
}

/// # Safety
/// Caller meets the approved two-argument wire and existing do_syscall contracts.
#[no_mangle]
pub unsafe extern "C" fn syscall_do_syscall2_bridge(number: CInt, arg0: CULong, arg1: CULong) -> CLong {
    unsafe { forward(number, [arg0, arg1, 0, 0, 0, 0]) }
}
/// # Safety
/// Same contract as the two-argument callback; its wire values are unchanged.
#[no_mangle]
pub unsafe extern "C" fn syscall_policy_do_syscall2_bridge(number: CInt, arg0: CULong, arg1: CULong) -> CLong {
    unsafe { forward(number, [arg0, arg1, 0, 0, 0, 0]) }
}
/// # Safety
/// Caller meets the approved three-argument wire and existing do_syscall contracts.
#[no_mangle]
pub unsafe extern "C" fn syscall_do_syscall3_bridge(number: CInt, arg0: CULong, arg1: CULong, arg2: CULong) -> CLong {
    unsafe { forward(number, [arg0, arg1, arg2, 0, 0, 0]) }
}
/// # Safety
/// Same contract as the three-argument callback; its wire values are unchanged.
#[no_mangle]
pub unsafe extern "C" fn syscall_policy_do_syscall3_bridge(number: CInt, arg0: CULong, arg1: CULong, arg2: CULong) -> CLong {
    unsafe { forward(number, [arg0, arg1, arg2, 0, 0, 0]) }
}
/// # Safety
/// Caller meets the original wait4 process and do_syscall lifetime contracts.
#[no_mangle]
pub unsafe extern "C" fn wait_host_wait4_bridge(pid: CInt, options: CInt) -> CInt {
    const SYS_WAIT4: CInt = 61;
    unsafe { forward(SYS_WAIT4, [pid as CULong, 0, options as CULong, 0, 0, 0]) as CInt }
}

type Two = unsafe extern "C" fn(CInt, CULong, CULong) -> CLong;
type Three = unsafe extern "C" fn(CInt, CULong, CULong, CULong) -> CLong;
const _: Two = syscall_do_syscall2_bridge;
const _: Two = syscall_policy_do_syscall2_bridge;
const _: Three = syscall_do_syscall3_bridge;
const _: Three = syscall_policy_do_syscall3_bridge;
const _: unsafe extern "C" fn(CInt, CInt) -> CInt = wait_host_wait4_bridge;
'''
c=after['kernel/syscall.c']
old='''static long syscall_do_syscall2_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1);
static long syscall_do_syscall3_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1, unsigned long arg2);
long syscall_policy_do_syscall3_bridge(int syscall_nr, unsigned long arg0,
		unsigned long arg1, unsigned long arg2);'''
new='''#if defined(MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)
extern long syscall_do_syscall2_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1); extern long syscall_do_syscall3_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1, unsigned long arg2);
#else
static long syscall_do_syscall2_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1); static long syscall_do_syscall3_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1, unsigned long arg2);
#endif
long syscall_policy_do_syscall3_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1, unsigned long arg2);'''
assert c.count(old)==1 and old.count('\n')==new.count('\n')
assert tok(old)==tok(new.split('#else\n')[1].replace('#endif\n',''))
c=c.replace(old,new)
old='''static int
wait_host_wait4_bridge(int pid, int options)
{
\tstruct syscall_request request IHK_DMA_ALIGN;

\trequest.number = __NR_wait4;
\trequest.args[0] = pid;
\trequest.args[1] = 0;
\trequest.args[2] = options;
\treturn do_syscall(&request, ihk_mc_get_processor_id());
}'''
flat='static int wait_host_wait4_bridge(int pid, int options) { struct syscall_request request IHK_DMA_ALIGN; request.number = __NR_wait4; request.args[0] = pid; request.args[1] = 0; request.args[2] = options; return do_syscall(&request, ihk_mc_get_processor_id()); }'
assert tok(old)==tok(flat)
new='#if defined(MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)\nextern int wait_host_wait4_bridge(int pid, int options);\n#else\n'+flat+'\n#endif'
new+='\n'*(old.count('\n')-new.count('\n'));assert old.count('\n')==new.count('\n') and c.count(old)==1
c=c.replace(old,new)
start=c.index('static long\nsyscall_do_syscall2_bridge(', c.index('wait_host_wait4_bridge'))
end=c.index('\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',start)
old=c[start:end]
new='''#ifndef MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS
static long syscall_do_syscall2_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1) { struct syscall_request request IHK_DMA_ALIGN; request.number = syscall_nr; request.args[0] = arg0; request.args[1] = arg1; return do_syscall(&request, ihk_mc_get_processor_id()); }
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long syscall_policy_do_syscall2_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1) { return syscall_do_syscall2_bridge(syscall_nr, arg0, arg1); }
#endif
static long syscall_do_syscall3_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1, unsigned long arg2) { struct syscall_request request IHK_DMA_ALIGN; request.number = syscall_nr; request.args[0] = arg0; request.args[1] = arg1; request.args[2] = arg2; return do_syscall(&request, ihk_mc_get_processor_id()); }
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
long syscall_policy_do_syscall3_bridge(int syscall_nr, unsigned long arg0, unsigned long arg1, unsigned long arg2) { return syscall_do_syscall3_bridge(syscall_nr, arg0, arg1, arg2); }
#endif
#endif'''
clean=lambda s:re.sub(r'^\s*#(?:ifn?def|endif)[^\n]*','',s,flags=re.M)
assert tok(clean(old))==tok(clean(new))
new+='\n'*(old.count('\n')-new.count('\n'));assert old.count('\n')==new.count('\n')
c=c[:start]+new+c[end:];after['kernel/syscall.c']=c
cm=after['kernel/CMakeLists.txt'];anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_request_constructors.rs"\n')
anchor='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)\n\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_request_constructors_candidate")\n\t\t\t\tendif()\n')
anchor='\n\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)\n\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)\n\t\t\tendif()\n')
after['kernel/CMakeLists.txt']=cm
after['kernel/rust/syscall_policy.rs']+='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_request_constructors_candidate, target_arch = "x86_64"))]\n#[path = "f03_request_constructors.rs"]\nmod f03_request_constructors;\n'
after['kernel/rust/f03_request_constructors.rs']=leaf
assert '__NR_wait4 = 61,' in (ROOT/'kernel/include/syscall.h').read_text()
abi=(ROOT/'kernel/rust/abi.rs').read_text(); assert 'pub struct SyscallRequest {' in abi
for clause in ('assert_eq_usize(size_of::<SyscallRequest>(), 72)', 'assert_eq_usize(align_of::<SyscallRequest>(), 8)', 'assert_eq_usize(offset_of!(SyscallRequest, number), 16)', 'assert_eq_usize(offset_of!(SyscallRequest, args), 24)'): assert clause in abi
assert 'fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;' in before['kernel/rust/syscall_policy.rs']
assert leaf.count('slots.add(')==6 and 'MaybeUninit::uninit()' in leaf and 'zeroed' not in leaf and 'assume_init' not in leaf
assert 'forward(number, [arg0, arg1, 0, 0, 0, 0])' in leaf and 'forward(number, [arg0, arg1, arg2, 0, 0, 0])' in leaf
assert 'forward(SYS_WAIT4, [pid as CULong, 0, options as CULong, 0, 0, 0]) as CInt' in leaf
assert len(before['kernel/syscall.c'].splitlines())==len(c.splitlines())
directives=lambda s:[(i,l)for i,l in enumerate(s.splitlines(),1)if re.match(r'^\s*#\s*(?:line\b|\d)',l)]
assert directives(before['kernel/syscall.c'])==directives(c)
sites=lambda s,macro:[(i,x.start()+1,l) for i,l in enumerate(s.splitlines(),1) for x in re.finditer(r'\b'+macro+r'!\s*\(',l)]
for macro in ('line','file','column'):assert sites(before['kernel/rust/syscall_policy.rs'],macro)==sites(after['kernel/rust/syscall_policy.rs'],macro)
assert len(sites(before['kernel/rust/syscall_policy.rs'],'line'))==53
patch='';rows=[]
for path,text in after.items():
 post=D/'postimage'/path;post.parent.mkdir(parents=True,exist_ok=True);post.write_text(text)
 if path in before:
  pre=D/'preimage'/path;pre.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before[path])
 patch+=''.join(difflib.unified_diff(before.get(path,'').splitlines(True),text.splitlines(True),fromfile='a/'+path if path in before else '/dev/null',tofile='b/'+path))
 rows.append({'path':path,'preimage':ref(D/'preimage'/path) if path in before else None,'postimage':ref(post)})
p=D/'REQUEST-CONSTRUCTORS.ON-TEN.PRIVATE-NOT-APPLIED.patch';p.write_text(patch)
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_PRIVATE_EXPERIMENTAL_CONSTRUCTORS_SOURCE_ONLY','contract':ref(contract),'ten_ready':ref(B/'SOURCE-READY.json'),'abi':ref(ROOT/'kernel/rust/abi.rs'),'wait_nr_header':ref(ROOT/'kernel/include/syscall.h'),'patch':ref(p),'files':rows,'checks':['number plus six explicit raw field writes without complete Request reference or general zeroing','2/3/wait4 wire slots and signed C int conversions follow approved contract','align64 stack storage separate from 72B align8 request; existing do_syscall typed ABI','default selection disabled: explicit experimental CMake gate in qualified branch','OFF C tokens, C #line origins and 53 Rust line/file/column sites retained'], 'actual_callgraph_closure':False,'actual_29_word_abi':False,'default_selection_authorized':False,'actual_compile_link_native':False,'runtime_authority':None,'independent_review':None}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
