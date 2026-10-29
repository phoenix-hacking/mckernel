from pathlib import Path
import difflib
here=Path(__file__).resolve().parent
base=here.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel'
selector='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\n'
dispatch='#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n'
configs=[
 dict(directory='wakeup',name='ptrace_detach_wakeup_bridge',file='syscall_ptrace_detach_wakeup.rs', old='''static void
ptrace_detach_wakeup_bridge(void *thread, int valid_states)
{
\tsched_wakeup_thread((struct thread *)thread, valid_states);
}
''', proto='extern void ptrace_detach_wakeup_bridge(void *thread, int valid_states);', first=(4698,4705), perf=False, leaf='''use core::ffi::{c_int, c_void};

/// Forward the callback to the qualified existing scheduler provider.
///
/// # Safety
/// The thread and its lifetime must meet the original callback and scheduler
/// provider contracts; this callback does not acquire or release ownership.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_wakeup_bridge(thread: *mut c_void, valid_states: c_int) {
    // SAFETY: The caller supplies the same live thread and states as the C
    // callback. The original callback also discards the scheduler result.
    let _ = unsafe { crate::sched_helpers::sched_wakeup_thread(thread.cast(), valid_states) };
}
'''),
 dict(directory='terminate_mcexec',name='terminate_mcexec_do_syscall_bridge',file='syscall_terminate_mcexec_forward.rs',old='''static long
terminate_mcexec_do_syscall_bridge(struct syscall_request *request, int cpu)
{
\treturn do_syscall(request, cpu);
}
''',proto='extern long terminate_mcexec_do_syscall_bridge(struct syscall_request *request, int cpu);',first=(5138,5145),perf=False),
 dict(directory='perf_open',name='perf_event_open_do_syscall_bridge',file='syscall_perf_open_forward.rs',old='''static long
perf_event_open_do_syscall_bridge(struct syscall_request *request, int cpu)
{
\treturn do_syscall(request, cpu);
}
''',proto='extern long perf_event_open_do_syscall_bridge(struct syscall_request *request, int cpu);',first=(21115,),perf=True)]
for x in configs:
 out=here/x['directory']/'postimage'/'kernel';(out/'rust').mkdir(parents=True,exist_ok=True)
 s=(base/'syscall.c').read_text();assert s.count(x['old'])==1
 if x['perf']:
  f=x['first'][0];body=selector+x['proto']+'\n#else\n#line '+str(f)+'\n'+x['old']+'#endif\n#line '+str(f+5)+'\n'
 else:
  on,off=x['first']; body=selector+x['proto']+'\n#else\n'+dispatch+'#line '+str(on-3)+'\n#else\n#line '+str(off-1)+'\n#endif\n'+x['old']+'#endif\n'+dispatch+'#line '+str(on+2)+'\n#else\n#line '+str(off+4)+'\n#endif\n'
 (out/'syscall.c').write_text(s.replace(x['old'],body))
 policy=(base/'rust/syscall_policy.rs').read_text()
 extra=', enable_perf' if x['perf'] else ''
 (out/'rust/syscall_policy.rs').write_text(policy+'\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"'+extra+'))]\n#[path = "'+x['file']+'"]\nmod '+x['file'][:-3]+';\n')
 cm=(base/'CMakeLists.txt').read_text(); anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"\n'; assert cm.count(anchor)==1
 (out/'CMakeLists.txt').write_text(cm.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/'+x['file']+'"\n'))
 if 'leaf' not in x:
  x['leaf']='''use crate::abi::{CInt, CLong, SyscallRequest};

/// Forward the existing request callback without inspecting its raw pointer.
///
/// # Safety
/// The request and cpu must satisfy the original caller and existing do_syscall
/// provider contracts. This function neither creates nor retains the request.
#[no_mangle]
pub unsafe extern "C" fn '''+x['name']+'''(request: *mut SyscallRequest, cpu: CInt) -> CLong {
    // SAFETY: The same pointer and CPU are passed to the original provider;
    // its exact return value is returned to the original caller.
    unsafe { super::do_syscall(request, cpu) }
}
'''
 (out/'rust'/x['file']).write_text('// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n'+x['leaf'])
 patch=[]
 for name in ['syscall.c','CMakeLists.txt','rust/syscall_policy.rs','rust/'+x['file']]:
  a,b=base/name,out/name
  patch+=difflib.unified_diff(a.read_text().splitlines(keepends=True) if a.exists() else [],b.read_text().splitlines(keepends=True),fromfile='a/kernel/'+name if a.exists() else '/dev/null',tofile='b/kernel/'+name)
 (here/x['directory']/'PRIVATE-NOT-APPLIED.patch').write_text(''.join(patch))
