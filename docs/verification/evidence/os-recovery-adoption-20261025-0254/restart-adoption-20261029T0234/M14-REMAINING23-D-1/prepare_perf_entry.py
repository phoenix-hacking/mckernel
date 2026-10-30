#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private, default-off source binding to the existing perf entry body.
"""
import difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-CONVERSION-FIRST-COMPOSITION-1';ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
assert ref(B/'SOURCE-READY.json')['sha256']=='caef14198a096315e21380de49982772d8070a6489ec91d4d2f0c4d2dde3473e'
paths=['kernel/syscall.c','kernel/CMakeLists.txt','kernel/rust/syscall_policy.rs'];before={p:(B/'postimage'/p).read_text() for p in paths};after=dict(before)
# Values are the exact ordered inputs in the original C entry, not guesses of
# target C structure layout or constants. Both C and Rust declarations are
# generated from this common source-only table and still require real ABI proof.
values=[('attr_size','sizeof(struct perf_event_attr)'),('attr_type','__builtin_offsetof(struct perf_event_attr, type)'),('attr_read_format','__builtin_offsetof(struct perf_event_attr, read_format)'),('attr_sample_period','__builtin_offsetof(struct perf_event_attr, sample_period)'),('raw_type','PERF_TYPE_RAW'),('hardware_type','PERF_TYPE_HARDWARE'),('cache_type','PERF_TYPE_HW_CACHE'),('unsupported_format','PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING | PERF_FORMAT_ID'),('sign_bit','1UL << 63'),('syscall_number','__NR_perf_event_open'),('mckfd_size','sizeof(struct mckfd)'),('allocation_flags','IHK_MC_AP_NOWAIT'),('event_pid','__builtin_offsetof(struct mc_perf_event, pid)'),('event_counter_id','__builtin_offsetof(struct mc_perf_event, counter_id)'),('proc_mckfd','__builtin_offsetof(struct process, mckfd)'),('mckfd_next','__builtin_offsetof(struct mckfd, next)'),('mckfd_fd','__builtin_offsetof(struct mckfd, fd)'),('mckfd_data','__builtin_offsetof(struct mckfd, data)'),('event_group_leader','__builtin_offsetof(struct mc_perf_event, group_leader)'),('event_sibling_list','__builtin_offsetof(struct mc_perf_event, sibling_list)'),('event_group_entry','__builtin_offsetof(struct mc_perf_event, group_entry)'),('event_nr_siblings','__builtin_offsetof(struct mc_perf_event, nr_siblings)'),('event_pmc_status','__builtin_offsetof(struct mc_perf_event, pmc_status)'),('thread_pmc_alloc_map','__builtin_offsetof(struct thread, pmc_alloc_map)'),('proc_mckfd_lock','__builtin_offsetof(struct process, mckfd_lock)'),('mckfd_sig_no','__builtin_offsetof(struct mckfd, sig_no)'),('mckfd_read_cb','__builtin_offsetof(struct mckfd, read_cb)'),('mckfd_ioctl_cb','__builtin_offsetof(struct mckfd, ioctl_cb)'),('mckfd_mmap_cb','__builtin_offsetof(struct mckfd, mmap_cb)'),('mckfd_close_cb','__builtin_offsetof(struct mckfd, close_cb)'),('mckfd_fcntl_cb','__builtin_offsetof(struct mckfd, fcntl_cb)')]
funcs=[('copy_from','syscall_copy_from_user_bridge','SyscallCopyFromUserFn'),('attr_freq','perf_event_open_attr_freq_bridge','PerfAttrFreqFn'),('event_alloc','perf_event_open_alloc_event_bridge','PerfOpenAllocEventFn'),('counter_alloc','perf_event_open_counter_alloc_bridge','PerfCounterAllocFn'),('syscall','perf_event_open_do_syscall_bridge','PerfOpenSyscallFn'),('allocate','perf_event_alloc_kmalloc_bridge','SyscallPolicyAllocFn'),('read','perf_read','SyscallMckfdLongFn'),('ioctl','perf_ioctl','SyscallMckfdIntFn'),('mmap','perf_mmap','SyscallMckfdLongFn'),('close','perf_close','SyscallMckfdIntFn'),('fcntl','perf_fcntl','SyscallMckfdIntFn'),('lock','syscall_mckfd_lock_bridge','SyscallMckfdLockFn'),('unlock','syscall_mckfd_unlock_bridge','SyscallMckfdUnlockFn')]
assert len(values)==31 and len(funcs)==13
c=after['kernel/syscall.c'];start=c.index('long sys_perf_event_open(int n, ihk_mc_user_context_t *ctx)\n{');end=c.index('\n#endif /* ENABLE_PERF */',start);old=c[start:end]
# Each original scalar and callback is found in exact call order.
call=old[old.index('return perf_event_open_entry_body_result('):]
pos=0
for name,expr in values:
 # first four inputs precede pid/cpu/group/flags/linux_cpu in the call; remaining
 # constants/offsets occur in the same table order thereafter.
 match=re.sub(r'\s+','',expr)
 flat=re.sub(r'\s+','',call)
 idx=flat.find(match,pos);assert idx>=0,(name,expr);pos=idx+len(match)
for name,symbol,ty in funcs:
 idx=flat.find(symbol,pos);assert idx>=0,(name,symbol);pos=idx+len(symbol)
# Keep original fallback tokens and line count, including function body positions.
fallback=old.replace('long sys_perf_event_open(int n, ihk_mc_user_context_t *ctx)\n{','long sys_perf_event_open(int n, ihk_mc_user_context_t *ctx) {',1)
fallback=fallback.replace('struct syscall_request request IHK_DMA_ALIGN;\n\tstruct thread *thread = get_this_cpu_local_var()->current;\n\tstruct process *proc = thread->proc;', 'struct syscall_request request IHK_DMA_ALIGN; struct thread *thread = get_this_cpu_local_var()->current; struct process *proc = thread->proc;',1)
fallback=fallback.replace('int pid = ihk_mc_syscall_arg1(ctx);\n\tint cpu = ihk_mc_syscall_arg2(ctx);', 'int pid = ihk_mc_syscall_arg1(ctx); int cpu = ihk_mc_syscall_arg2(ctx);', 1)
new='#if defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)\nextern long sys_perf_event_open(int n, ihk_mc_user_context_t *ctx);\n#else\n'+fallback+'\n#endif'
assert old.count('\n')==new.count('\n')
tok=lambda s:re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]',s)
assert tok(old)==tok(fallback)
c=c[:start]+new+c[end:]
metadata='\n\n/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n#if defined(ENABLE_PERF) && defined(MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)\nstruct f03_perf_entry_binding_v1_type {\n'
metadata+=''.join('\tunsigned long '+name+';\n' for name,_ in values)
metadata+=''.join('\t__typeof__(&'+symbol+') '+name+';\n' for name,symbol,_ in funcs)
metadata+='};\nconst struct f03_perf_entry_binding_v1_type f03_perf_entry_binding_v1 = {\n'
metadata+=''.join('\t.'+name+' = '+expr+',\n' for name,expr in values)
metadata+=''.join('\t.'+name+' = '+symbol+',\n' for name,symbol,_ in funcs)
metadata+='};\n#endif\n'
after['kernel/syscall.c']=c+metadata
cm=after['kernel/CMakeLists.txt'];anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_perf_entry_candidate.rs"\n')
anchor='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\t\tif (ENABLE_PERF AND MCKERNEL_F03_PERF_ENTRY_EXPERIMENTAL)\n\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_entry_candidate")\n\t\t\t\tendif()\n')
anchor='\n\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\tif (ENABLE_PERF AND MCKERNEL_F03_PERF_ENTRY_EXPERIMENTAL)\n\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)\n\t\t\tendif()\n')
after['kernel/CMakeLists.txt']=cm
after['kernel/rust/syscall_policy.rs']+='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_perf_entry_candidate, enable_perf, target_arch = "x86_64"))]\n#[path = "f03_perf_entry_candidate.rs"]\nmod f03_perf_entry_candidate;\n'
imports=','.join(sorted({ty for _,_,ty in funcs}))
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Default-off entry binding to the existing Rust perf body and C metadata.
use core::{ffi::c_void, mem::{size_of, MaybeUninit}};
use crate::abi::{CInt, CLong, CULong, SyscallRequest, X86UserContext};
use crate::f03_perf_attr_callbacks::PerfEventAttr;
use crate::x86_cpu_helpers::{ihk_mc_syscall_arg0, ihk_mc_syscall_arg1, ihk_mc_syscall_arg2, ihk_mc_syscall_arg3, ihk_mc_syscall_arg4};
use super::{'''+imports+'''};
#[repr(C)]
struct PerfEntryBinding {
'''
leaf+=''.join('    '+name+': CULong,\n' for name,_ in values)
leaf+=''.join('    '+name+': Option<'+ty+'>,\n' for name,_,ty in funcs)
leaf+='''}
unsafe extern "C" { static f03_perf_entry_binding_v1: PerfEntryBinding; }
const _: () = { assert!(size_of::<CULong>() == 8 && size_of::<usize>() == 8); };
/// Reuse the original perf entry provider, field and callback bindings.
///
/// # Safety
/// The caller supplies the original live syscall context and current thread,
/// process, perf, VM and endpoint lifetimes. Existing perf and request helper
/// contracts, publication/cleanup and all unreleased holds remain unchanged.
#[no_mangle]
pub unsafe extern "C" fn sys_perf_event_open(_number: CInt, ctx: *mut X86UserContext) -> CLong {
    // No whole reference to either uninitialized stack object is formed.
    let mut request = MaybeUninit::<SyscallRequest>::uninit();
    let mut attr = MaybeUninit::<PerfEventAttr>::uninit();
    // SAFETY: Identical current CPU/thread/process and context prerequisites as C.
    let thread = unsafe { (*super::get_this_cpu_local_var()).current };
    let proc = unsafe { (*thread).proc };
    let arg0 = unsafe { ihk_mc_syscall_arg0(ctx) };
    let pid = unsafe { ihk_mc_syscall_arg1(ctx) } as CInt;
    let cpu = unsafe { ihk_mc_syscall_arg2(ctx) } as CInt;
    let group_fd = unsafe { ihk_mc_syscall_arg3(ctx) } as CInt;
    let flags = unsafe { ihk_mc_syscall_arg4(ctx) };
    let linux_cpu = unsafe { super::ihk_mc_get_processor_id() };
    // SAFETY: Read-only C binding captures the original values and exact provider
    // addresses. The existing body retains all initialisation and ownership rules.
    let b = unsafe { &f03_perf_entry_binding_v1 };
    unsafe { super::perf_event_open_entry_body_result(
        request.as_mut_ptr(), thread.cast::<c_void>(), proc.cast::<c_void>(),
        attr.as_mut_ptr().cast::<c_void>(), arg0,
        b.attr_size as usize, b.attr_type as usize, b.attr_read_format as usize,
        b.attr_sample_period as usize, pid, cpu, group_fd, flags, linux_cpu,
        b.raw_type, b.hardware_type, b.cache_type, b.unsupported_format,
        b.sign_bit, b.syscall_number as CInt, b.mckfd_size as usize, b.allocation_flags,
'''
leaf+=''.join('        b.'+name+' as usize,\n' for name,_ in values[12:])
leaf+=''.join('        b.'+name+',\n' for name,_,_ in funcs)
leaf+='''    ) }
}
const _: unsafe extern "C" fn(CInt, *mut X86UserContext) -> CLong = sys_perf_event_open;
'''
after['kernel/rust/f03_perf_entry_candidate.rs']=leaf
# Source-level preimage conservation: no held domain changed in C prefix/suffix;
# all prior line/file/column sites remain in place.
assert len(c.splitlines())==len(before['kernel/syscall.c'].splitlines())
directives=lambda s:[(i,l) for i,l in enumerate(s.splitlines(),1) if re.match(r'^\s*#\s*(?:line\b|\d)',l)]
assert directives(c)==directives(before['kernel/syscall.c'])
sites=lambda s,m:[(i,x.start()+1,l) for i,l in enumerate(s.splitlines(),1) for x in re.finditer(r'\b'+m+r'!\s*\(',l)]
for m in ('line','file','column'):assert sites(before['kernel/rust/syscall_policy.rs'],m)==sites(after['kernel/rust/syscall_policy.rs'],m)
assert len(sites(before['kernel/rust/syscall_policy.rs'],'line'))==53
assert leaf.count('super::perf_event_open_entry_body_result(')==1 and 'zeroed' not in leaf and 'assume_init' not in leaf
patch='';rows=[]
for path,text in after.items():
 post=D/'postimage'/path;post.parent.mkdir(parents=True,exist_ok=True);post.write_text(text)
 if path in before:
  pre=D/'preimage'/path;pre.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before[path])
 patch+=''.join(difflib.unified_diff(before.get(path,'').splitlines(True),text.splitlines(True),fromfile='a/'+path if path in before else '/dev/null',tofile='b/'+path))
 rows.append({'path':path,'preimage':ref(D/'preimage'/path) if path in before else None,'postimage':ref(post)})
p=D/'PERF-ENTRY.ON-FIRST20.PRIVATE-NOT-APPLIED.patch';p.write_text(patch)
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_EXPERIMENTAL_PERF_ENTRY_SOURCE_BINDING_ONLY','composition':ref(B/'SOURCE-READY.json'),'patch':ref(p),'files':rows,'argument_binding_values':values,'callback_binding_names':funcs,'checks':['31 original C expressions and 13 callback names found in original call order','unchanged fallback tokens and physical/#line origins; new C data appended after old source','unchanged existing Rust body and preimage; 53 line/file/column macro sites unchanged','request/attr are uninitialized typed storage without whole references or extra zeroing','experimental paired ENABLE_PERF selectors disabled by default'],'actual_abi_compile_link_native':False,'default_selection_authorized':False,'held_request_endpoint_release':False,'runtime_authority':None}
(D/'PERF-SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
