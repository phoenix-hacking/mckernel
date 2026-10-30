"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private module extraction/materialization only. No tests/compiler/workload launch.
"""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent
OLD=D.parent
V=OLD.parent
BASE=V/'m14-perf-typecheck-integration-2/work-1/src'
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234')
H2=BASE/'kernel/rust/syscall_policy.rs'
PIN='217091d13694fb04a4b14930256e60dd9decdc5ae771fc101605b609aa35e403'
def require(ok,why):
    if not ok:raise ValueError(why)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,data):
    p=D/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
def one(data,old,new):
    require(data.count(old)==1,'replacement must match exactly once')
    return data.replace(old,new,1)
def extract(data,module):
    marker=b'mod '+module+b' {\n'
    require(data.count(marker)==1,'module start not unique')
    inner=data.split(marker,1)[1]
    require(inner.endswith(b'}\n'),'module end missing')
    inner=inner[:-2]
    # Remove exactly one wrapper indentation level, retaining every body token.
    return b''.join(line[4:] if line.startswith(b'    ') else line for line in inner.splitlines(keepends=True))
require(sha(H2)==PIN,'actual H2 parent changed; compositor must bind a successor')
fragments={
 'do':(E/'M14-LARGE-DO-SYSCALL-REUSE-1/RUST-BODY.REUSED.rs.inc').read_bytes(),
 'util':(E/'M14-LARGE-UTIL-THREAD-REUSE-1/RUST-BODY.REUSED.rs.inc').read_bytes(),
 'constructors':(OLD/'postimage/kernel/rust/f03_request_constructors.rs').read_bytes(),
}
do=extract(fragments['do'],b'f03_do_syscall_supported_v1')
util=extract(fragments['util'],b'f03_util_thread_whole_v1')
# Export suppression is confined to these private modules. Actual ABI is extern C.
do=one(do,b'#[export_name = "do_syscall"]\n',b'')
util=one(util,b'#[export_name = "util_thread"]\n',b'')
require(do.count(b'#[no_mangle]\n')==1,'unexpected do ABI export count')
require(util.count(b'#[no_mangle]\n')==1,'unexpected util ABI export count')
do=do.replace(b'#[no_mangle]\n',b'')
util=util.replace(b'#[no_mangle]\n',b'')
ctor=fragments['constructors']
require(ctor.count(b'#[no_mangle]\n')==5,'unexpected constructor export count')
ctor=ctor.replace(b'#[no_mangle]\n',b'')
# This error is before send/preemption/host access. Undo only our local earlier
# accounting; never publish a completion or fabricate a remote drain.
old=b'''        if use_requester < 0 {
            // Preserve the original early return before monitor/count unwind.
            return use_requester as CLong;
        }
'''
new=b'''        if use_requester < 0 {
            // No send or host access occurred. Roll back this entry's local
            // accounting while preserving the exact preparation error result.
            if syscall_offload_counted_result(number, exit_group) != 0 {
                let count = addr_of_mut!((*thread).in_syscall_offload);
                write_volatile(count, read_volatile(count).wrapping_sub(1));
            }
            write_volatile(addr_of_mut!((*monitor).status), old_monitor_status);
            return use_requester as CLong;
        }
'''
do=one(do,old,new)
private_note=b'// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n// Actual-crate frontend only: no production exports or selector authority.\n'
do=private_note+do+b'''
// Exact actual-crate prototypes, checked by the affected frontend.
const _: unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong = f03_do_syscall_supported_v1;
const _: unsafe extern "C" fn(*mut SyscallRequest, CInt, *mut SyscallResponse) = send_syscall;
const _: unsafe extern "C" fn(*mut SyscallRequest, *mut SyscallResponse, CInt, CInt, CULong, CInt, CULong) -> CInt = syscall_offload_prepare_result;
const _: unsafe extern "C" fn(*mut SyscallRequest, *mut SyscallResponse, CInt, *mut Thread) = syscall_offload_wait_reply;
const _: unsafe extern "C" fn() -> *mut CpuLocalVar = crate::cls::get_this_cpu_local_var;
'''
util=private_note+util+b'''
const _: unsafe extern "C" fn(*mut UtiAttr) -> CInt = f03_util_thread_whole_v1;
const _: unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong = existing_do_syscall;
const _: unsafe extern "C" fn(CInt, CInt) = existing_terminate;
const _: unsafe extern "C" fn(CInt) = existing_do_exit;
const _: unsafe extern "C" fn(*mut c_void) -> CULong = crate::x86_memory_helpers::virt_to_phys;
const _: unsafe extern "C" fn(*mut c_void, *mut i8, CInt) = crate::mem_helpers::kfree_tracked;
'''
# Constructor function-pointer constraints already belong to the reused source.
modules={'m14_private_do_syscall.rs':do,'m14_private_util_thread.rs':util,'m14_private_request_constructors.rs':ctor}
append=b'''
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Seven private frontend bodies; existing public provider/modules remain intact.
#[cfg(all(m14_private_frontend, not(target_arch = "x86_64")))]
compile_error!("private M14 frontend requires its selected x86_64 ABI");
#[cfg(all(m14_private_frontend, not(enable_profile)))]
compile_error!("private do_syscall frontend requires its reviewed profile provider");
#[cfg(all(m14_private_frontend, any(enable_tofu, enable_fugaku_hacks)))]
compile_error!("private do_syscall frontend excludes optional ToFu/Fugaku paths");
'''
for filename,data in modules.items():
    require(b'#[no_mangle]' not in data and b'#[export_name' not in data,'private export suppression failed')
    put(Path('postimage/kernel/rust')/filename,data)
    module=filename[:-3]
    append+=b'#[cfg(m14_private_frontend)]\n#[path = "'+filename.encode()+b'"]\nmod '+module.encode()+b';\n'
base=H2.read_bytes()
put(Path('SYSCALL-POLICY.APPEND.rs.inc'),append)
put(Path('postimage/kernel/rust/syscall_policy.rs'),base+append)
put(Path('postimage/kernel/rust/lib.rs'),(BASE/'kernel/rust/lib.rs').read_bytes())
# Exact append/new-file patch, constructed directly without a diff algorithm.
lines=base.splitlines(keepends=True)
context=b''.join(lines[-3:]);start=len(lines)-2
patch=b'--- a/kernel/rust/syscall_policy.rs\n+++ b/kernel/rust/syscall_policy.rs\n'
patch+=f'@@ -{start},3 +{start},{3+append.count(bytes([10]))} @@\n'.encode()
patch+=b''.join(b' '+line for line in context.splitlines(keepends=True))
patch+=b''.join(b'+'+line for line in append.splitlines(keepends=True))
for filename,data in modules.items():
    patch+=b'--- /dev/null\n+++ b/kernel/rust/'+filename.encode()+b'\n'
    patch+=f'@@ -0,0 +1,{data.count(bytes([10]))} @@\n'.encode()
    patch+=b''.join(b'+'+line for line in data.splitlines(keepends=True))
put(Path('H2-PRIVATE-FRONTEND.NOT-APPLIED.patch'),patch)
# Retain the exact bounded behavioral correction separately for review.
old_lines=old.splitlines(keepends=True);new_lines=new.splitlines(keepends=True)
loc=extract(fragments['do'],b'f03_do_syscall_supported_v1').index(old)
put(Path('PRE-SEND-ROLLBACK.OLD.rs.inc'),old)
put(Path('PRE-SEND-ROLLBACK.NEW.rs.inc'),new)
inputs=[H2,BASE/'kernel/rust/lib.rs',BASE/'kernel/rust/abi.rs',BASE/'kernel/rust/cls.rs',BASE/'kernel/rust/profile.rs',BASE/'kernel/rust/mem_helpers.rs',BASE/'kernel/rust/x86_memory_helpers.rs',BASE/'kernel/rust/x86_cpu_helpers.rs',E/'M14-LARGE-DO-SYSCALL-REUSE-1/RUST-BODY.REUSED.rs.inc',E/'M14-LARGE-UTIL-THREAD-REUSE-1/RUST-BODY.REUSED.rs.inc',OLD/'postimage/kernel/rust/f03_request_constructors.rs',OLD/'projection-correction-1/SOURCE-DELIVERY.json',Path('/home/holden/mckernel/kernel/syscall.c')]
put(Path('INPUTS.json'),(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','inputs':[{'path':str(p),'resolved_path':str(p.resolve()),'sha256':sha(p),'bytes':p.stat().st_size} for p in inputs],'not_source_exclusion_or_effective_mount_evidence':True},indent=2)+'\n').encode())
