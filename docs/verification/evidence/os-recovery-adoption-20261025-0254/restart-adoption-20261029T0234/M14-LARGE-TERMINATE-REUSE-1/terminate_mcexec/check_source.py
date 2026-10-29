from pathlib import Path
import hashlib,json,re
here=Path(__file__).resolve().parent;root=here.parent.parent
cfile=root/'M14-PRIVATE-NINE-LEAF-BATCH-1/postimage/kernel/syscall.c';pfile=root/'M14-PRIVATE-NINE-LEAF-BATCH-1/postimage/kernel/rust/syscall_policy.rs'
c=cfile.read_text();p=pfile.read_text();frag=(here/'terminate_mcexec.PRIVATE.rs.inc').read_text()
original='''void terminate_mcexec(int rc, int sig)
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
assert c.count(original)==1
assert 'pub unsafe extern "C" fn terminate_mcexec_body_result(' in p
assert 'type TerminateMcexecCmpxchgFn = unsafe extern "C" fn(*mut CULong, CULong, CULong) -> CULong;' in p
assert 'type TerminateMcexecSyscallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;' in p
assert 'fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;' in p
assert '#define terminate_mcexec_cmpxchg_bridge atomic_cmpxchg_ulong' in c
assert '__NR_exit_group = 231,' in Path('/home/holden/mckernel/kernel/include/syscall.h').read_text()
assert '#define IHK_DMA_ALIGN\n' in Path('/home/holden/mckernel/ihk/cokernel/smp/x86_64/include/ihk/memconst.h').read_text()
atom=Path('/home/holden/mckernel/kernel/rust/atomic_helpers.rs').read_text()
assert re.search(r'pub unsafe extern "C" fn atomic_cmpxchg_ulong\(\s*addr: \*mut CULong,\s*oldval: CULong,\s*newval: CULong,\s*\) -> CULong',atom)
assert 'MaybeUninit::<SyscallRequest>::uninit()' in frag and 'request.as_mut_ptr()' in frag
assert 'const EXIT_GROUP_NR: CInt = 231;' in frag
assert 'offset_of!(Process, group_exit_status), offset_of!(Process, nohost)' in frag
assert 'Some(crate::atomic_helpers::atomic_cmpxchg_ulong)' in frag and 'Some(super::do_syscall)' in frag
assert 'process.cast(), request.as_mut_ptr(), rc, sig,' in frag and frag.count('super::terminate_mcexec_body_result(')==1
assert '#[cfg(all(f03_terminate_mcexec_whole_candidate, target_arch = "x86_64"))]' in frag
assert 'f03_terminate_mcexec_whole_candidate' not in p and 'MCKERNEL_RUST_F03_TERMINATE_MCEXEC_WHOLE' not in c
body=p[p.index('pub unsafe extern "C" fn terminate_mcexec_body_result('):p.index('pub extern "C" fn sync_child_event_needed_result(')]
for i in range(6):assert f'(*request).args[{i}]' in body
assert '(*request).number' in body and 'write_volatile(nohost_ptr, 1)' in body
assert body.index('write_volatile(nohost_ptr, 1)')<body.index('syscall(request, cpu)')
def info(path):
 b=path.read_bytes();return {'path':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'UNSELECTED_SOURCE_ONLY_OWNERSHIP_AND_PROFILE_REVIEW_OPEN','checks':['exact existing C wrapper','existing Rust body and provider callback source ABIs','x86 IHK_DMA_ALIGN empty and __NR_exit_group 231','raw MaybeUninit storage and same current/proc, arguments, CPU, offsets, and providers','source inspection shows body initializes all six args and number before provider','C implementation remains unselected and untouched'], 'source':info(cfile),'provider':info(pfile),'fragment':info(here/'terminate_mcexec.PRIVATE.rs.inc'),'limits':'No new C selector or production integration. Provider must establish all remaining request fields before any read/copy, preserve synchronous lifetime, exact qualified provider/flags, and be independently reviewed; no actual preprocessor/compiler/link/native/389 proof.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
