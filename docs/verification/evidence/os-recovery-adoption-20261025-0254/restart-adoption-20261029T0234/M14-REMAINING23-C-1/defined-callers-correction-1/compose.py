from pathlib import Path
import difflib
here=Path(__file__).resolve().parent;base=here.parent/'postimage'/'kernel';out=here/'postimage'/'kernel'
c=(base/'syscall.c').read_text()
old='''static void
ptrace_wakeup_log_bridge(int event, int value, int result)
{
\tif (event == PTRACE_CONTROL_LOG_WAKEUP_ENTER) {
\t\tdkprintf("ptrace_wakeup_sig,pid=%d,data=%08x\\n",
\t\t\t\tvalue, result);
\t}
}
'''
assert c.count(old)==1
new='''#if defined(MCKERNEL_RUST_F03_PTRACE_WAKEUP_LOG_DEFINED) && defined(MCKERNEL_RUST_F03_PTRACE_WAKEUP_LOG_PROFILE_119) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(__x86_64__)
extern void ptrace_wakeup_log_bridge(int event, int value, int result);
#else
#line 24425
'''+old+'''#endif
#line 24433
'''
(out/'syscall.c').write_text(c.replace(old,new))
policy=(base/'rust/syscall_policy.rs').read_text()
policy+='''\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_ptrace_wakeup_log_defined_u32_candidate, f03_ptrace_wakeup_log_origin_profile_119, target_arch = "x86_64"))]\n#[path = "syscall_ptrace_wakeup_log.rs"]\nmod syscall_ptrace_wakeup_log;\n'''
(out/'rust/syscall_policy.rs').write_text(policy)
logger=(here.parent/'contract-proposals/ptrace_wakeup_log.UNSELECTED.rs.inc').read_text()
prefix='''#[cfg(all(f03_ptrace_wakeup_log_defined_u32_candidate,
          f03_ptrace_wakeup_log_origin_profile_119, target_arch = "x86_64"))]
mod ptrace_wakeup_log_defined_u32 {
'''
assert logger.count(prefix)==1 and logger.endswith('}\n')
logger=logger.replace(prefix,'',1)[:-2]
logger=logger.replace('// PROPOSED contract: event 4 logs the result\'s low 32 bits as unsigned hex.\n// This fragment is not selected or integrated pending Root\'s explicit decision.','// Approved defined contract: event 4 logs the result\'s low 32 bits as unsigned hex.')
logger+='\nconst _: unsafe extern "C" fn(CInt, CInt, CInt) = ptrace_wakeup_log_bridge;\n'
(out/'rust/syscall_ptrace_wakeup_log.rs').write_text(logger)
for f in ['syscall_terminate_whole.rs','syscall_terminate_mcexec_whole.rs','syscall_terminate_host_whole.rs','syscall_ptrace_detach_kfree.rs','syscall_ptrace_detach_kill.rs','syscall_interrupt_arity3.rs']:
 (out/'rust'/f).write_bytes((base/'rust'/f).read_bytes())
cm=(base/'CMakeLists.txt').read_text()
anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_interrupt_arity3.rs"\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_wakeup_log.rs"\n')
anchor='\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")\n';assert cm.count(anchor)==1
cfg='''\t\t# Defined named-callers contract, only under the retained /src x86 profile.
\t\tif (MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12" AND NOT ENABLE_UBSAN AND
\t\t    CMAKE_CURRENT_SOURCE_DIR STREQUAL "/src/kernel")
\t\t\tlist(APPEND RUST_KERNEL_CFG
\t\t\t\t"--cfg" "f03_interrupt_arity3_defined_candidate"
\t\t\t\t"--cfg" "f03_interrupt_origin_profile_119"
\t\t\t\t"--cfg" "f03_interrupt_origin_dispatch"
\t\t\t\t"--cfg" "f03_ptrace_wakeup_log_defined_u32_candidate"
\t\t\t\t"--cfg" "f03_ptrace_wakeup_log_origin_profile_119")
\t\tendif()
'''
cm=cm.replace(anchor,anchor+cfg)
anchor='''\t\t"MCKERNEL_RUST_SHMID_HELPERS;MCKERNEL_RUST_SHM_PERM_HELPERS;MCKERNEL_RUST_RLIMIT_HELPERS;MCKERNEL_RUST_SCHED_PRIO_HELPERS;MCKERNEL_RUST_SCHED_POLICY_HELPERS;MCKERNEL_RUST_SYSCALL_POLICY_HELPERS;MCKERNEL_RUST_SYSCALL_OFFLOAD;MCKERNEL_RUST_SIGNAL_HELPERS;MCKERNEL_RUST_F03_IO_DIAGNOSTICS;MCKERNEL_RUST_F03_MINCORE;MCKERNEL_RUST_F03_MOVE_PAGES;MCKERNEL_RUST_F03_SCHED_BRIDGES;MCKERNEL_RUST_F03_SIGNAL_PROCESS_BRIDGES;MCKERNEL_RUST_F03_DISPATCH_CONTEXT;MCKERNEL_RUST_F03_LEAF_CALLBACKS")
''';assert cm.count(anchor)==1
cp='''\tif (MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12" AND NOT ENABLE_UBSAN AND
\t    CMAKE_CURRENT_SOURCE_DIR STREQUAL "/src/kernel")
\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY
\t\t\tCOMPILE_DEFINITIONS "MCKERNEL_RUST_F03_INTERRUPT_ARITY3_DEFINED;MCKERNEL_RUST_F03_INTERRUPT_ORIGIN_PROFILE_119;MCKERNEL_RUST_F03_PTRACE_WAKEUP_LOG_DEFINED;MCKERNEL_RUST_F03_PTRACE_WAKEUP_LOG_PROFILE_119")
\tendif()
'''
cm=cm.replace(anchor,anchor+cp)
(out/'CMakeLists.txt').write_text(cm)
patch=[]
for name in ['syscall.c','CMakeLists.txt','rust/syscall_policy.rs','rust/syscall_ptrace_wakeup_log.rs']:
 a,b=base/name,out/name
 patch+=difflib.unified_diff(a.read_text().splitlines(keepends=True) if a.exists() else [],b.read_text().splitlines(keepends=True),fromfile='a/kernel/'+name if a.exists() else '/dev/null',tofile='b/kernel/'+name)
(here/'DEFINED-CALLERS.PRIVATE-NOT-APPLIED.patch').write_text(''.join(patch))
