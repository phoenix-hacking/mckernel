from pathlib import Path
import difflib
here=Path(__file__).resolve().parent
base=here.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel'
reuse=here.parent/'M14-LARGE-TERMINATE-REUSE-1'
host=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-terminate-host-whole-entry-source-1')
oldterm=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/next-terminate-whole-orchestration-source-1')
out=here/'postimage'/'kernel'
basec=(base/'syscall.c').read_text(); c=basec
mc='''void terminate_mcexec(int rc, int sig)
{
\tstruct thread *mythread = get_this_cpu_local_var()->current;
\tstruct process *proc = mythread->proc;
\tstruct syscall_request request IHK_DMA_ALIGN;

\tterminate_mcexec_body_result(proc, &request, rc, sig,
\t\t\tihk_mc_get_processor_id(), __NR_exit_group,
\t\t\t__builtin_offsetof(struct process, group_exit_status),
\t\t\t__builtin_offsetof(struct process, nohost),
\t\t\tterminate_mcexec_cmpxchg_bridge,
\t\t\tterminate_mcexec_do_syscall_bridge);
}
'''
cases=[('MCKERNEL_RUST_F03_TERMINATE_MCEXEC_WHOLE','extern void terminate_mcexec(int rc, int sig);',mc,5183,5190,'#if !defined(__x86_64__) || !defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) || !defined(MCKERNEL_RUST_ATOMIC_HELPERS) || !defined(MCKERNEL_RUST_F03_TERMINATE_CMPXCHG)\n#error "terminate_mcexec candidate needs x86 and existing policy/atomic providers"\n#endif\n'),
 ('MCKERNEL_RUST_F03_TERMINATE_WHOLE','extern void terminate(int rc, int sig);',(oldterm/'terminate.ACTUAL-ORIGINAL-FULL-C.inc').read_text(),5242,5249,'#if !defined(__x86_64__) || !defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) || !defined(MCKERNEL_RUST_F03_TERMINATE_PROFILE_119) || defined(ENABLE_TOFU) || defined(DCFA_KMOD)\n#error "terminate whole candidate requires supported non-Tofu/non-DCFA x86 policy profile"\n#endif\n'),
 ('MCKERNEL_RUST_F03_TERMINATE_HOST_WHOLE','extern void terminate_host(int pid, struct thread *thread);',(host/'terminate_host.ORIGINAL-C.inc').read_text(),5620,5627,'#if !defined(__x86_64__) || !defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) || !defined(MCKERNEL_RUST_ATOMIC_HELPERS) || !defined(MCKERNEL_RUST_F03_TERMINATE_REFCOUNT)\n#error "terminate_host candidate requires x86 policy and refcount providers"\n#endif\n')]
dispatch='#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n'
for selector,proto,orig,on,off,require in cases:
 assert c.count(orig)==1
 n=orig.count('\n')
 # #line on the TRUE arm precedes #else, skipped #line and #endif;
 # the FALSE arm precedes only #endif. Keep exact C fallback and suffix origin.
 wrapped=('#ifdef '+selector+'\n'+require+proto+'\n#else\n'+dispatch+
          '#line '+str(on-3)+'\n#else\n#line '+str(off-1)+'\n#endif\n'+orig+'#endif\n'+dispatch+
          '#line '+str(on+n-3)+'\n#else\n#line '+str(off+n-1)+'\n#endif\n')
 c=c.replace(orig,wrapped)
(out/'syscall.c').write_text(c)
# Convert the two already nested fragments into child module files, so their
# existing `super` references still resolve to syscall_policy.
def unwrap(s,prefix):
 assert s.count(prefix)==1 and s.endswith('}\n')
 return s.replace(prefix,'',1)[:-2]
term=unwrap((reuse/'terminate/terminate.CURRENT119-RUST-METADATA.PRIVATE.rs.inc').read_text(),'#[cfg(f03_terminate_whole_candidate)]\nmod f03_terminate_whole_v1 {\n')
mcfrag=unwrap((reuse/'terminate_mcexec/terminate_mcexec.PRIVATE.rs.inc').read_text(),'#[cfg(all(f03_terminate_mcexec_whole_candidate, target_arch = "x86_64"))]\nmod f03_terminate_mcexec_whole {\n')
hostfrag=(host/'terminate_host.RUST-FRAGMENT.rs.inc').read_text()
# Existing direct entry imports its original common parent types and providers.
hostfrag='use super::*;\n\n'+hostfrag
for filename,text in [('syscall_terminate_whole.rs',term),('syscall_terminate_mcexec_whole.rs',mcfrag),('syscall_terminate_host_whole.rs',hostfrag)]:
 checks={'syscall_terminate_whole.rs':'const _: unsafe extern "C" fn(CInt, CInt) = f03_terminate_whole_v1;\n', 'syscall_terminate_mcexec_whole.rs':'const _: unsafe extern "C" fn(CInt, CInt) = f03_terminate_mcexec_v1;\n', 'syscall_terminate_host_whole.rs':'const _: unsafe extern "C" fn(CInt, *mut Thread) = terminate_host;\n'}
 (out/'rust'/filename).write_text(text+'\n'+checks[filename])
p=(base/'rust/syscall_policy.rs').read_text()
for cfg,filename in [('f03_terminate_whole_candidate','syscall_terminate_whole.rs'),('f03_terminate_mcexec_whole_candidate','syscall_terminate_mcexec_whole.rs'),('f03_terminate_host_whole_candidate','syscall_terminate_host_whole.rs')]:
 profile=', f03_terminate_origin_profile_119' if cfg=='f03_terminate_whole_candidate' else ''
 p+='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all('+cfg+profile+', target_arch = "x86_64"))]\n#[path = "'+filename+'"]\nmod '+filename[:-3]+';\n'
(out/'rust/syscall_policy.rs').write_text(p)
cm=(base/'CMakeLists.txt').read_text();anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"\n';assert cm.count(anchor)==1
addition=''.join('\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/'+f+'"\n' for f in ['syscall_terminate_whole.rs','syscall_terminate_mcexec_whole.rs','syscall_terminate_host_whole.rs'])
(out/'CMakeLists.txt').write_text(cm.replace(anchor,anchor+addition))
patch=[]
for name in ['syscall.c','CMakeLists.txt','rust/syscall_policy.rs','rust/syscall_terminate_whole.rs','rust/syscall_terminate_mcexec_whole.rs','rust/syscall_terminate_host_whole.rs']:
 a,b=base/name,out/name
 patch+=difflib.unified_diff(a.read_text().splitlines(keepends=True) if a.exists() else [],b.read_text().splitlines(keepends=True),fromfile='a/kernel/'+name if a.exists() else '/dev/null',tofile='b/kernel/'+name)
(here/'TERMINATION-FAMILY.PRIVATE-NOT-APPLIED.patch').write_text(''.join(patch))
