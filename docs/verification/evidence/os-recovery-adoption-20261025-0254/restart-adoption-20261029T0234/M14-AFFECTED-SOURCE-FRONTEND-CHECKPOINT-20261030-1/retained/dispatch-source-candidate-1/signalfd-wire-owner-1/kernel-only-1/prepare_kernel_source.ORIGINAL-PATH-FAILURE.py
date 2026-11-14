"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
M14 compute-only source materialization. No tests/compiler/workload execution.
"""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent
V=D.parents[3]
SRC=V/'m14-combined-frontend-candidate-2/work-1/src'
K=SRC/'kernel/rust/syscall_policy.rs'
ROOT=Path('/home/holden/mckernel')
PIN='aa751edb617692c1da8ed2fe59c897bb2e20e6357f8a3431a16d27443becadeb'
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(data):return hashlib.sha256(data).hexdigest()
base=K.read_bytes()
require(sha(base)==PIN,'exact passed parent changed')
marker=b'#[no_mangle]\npub unsafe extern "C" fn syscall_signalfd_create_bridge('
require(base.count(marker)==1,'function start must be unique')
start=base.index(marker);end=base.index(b'\n}\n',start)+3
old=base[start:end]
require(sha(old)=='51eb544714c24f2e1fffe42aec22fff553b24767db59f11d3f6f5ab924f0a1bd','qualified function preimage changed')
body=b'''    let mut request = MaybeUninit::<SyscallRequest>::zeroed();
    let requestp = request.as_mut_ptr();
    (*requestp).number = syscall_nr as CULong;
    (*requestp).args[0] = 0;
    (*requestp).args[1] = flags as CULong;
'''
replacement=b'''    let mut request = MaybeUninit::<SyscallRequest>::uninit();
    let requestp = request.as_mut_ptr();
    // Preserve the previously defined wire vector field by field. The actual
    // prepare/send providers own rtid, ttid and valid before their first copy.
    unsafe {
        addr_of_mut!((*requestp).number).write(syscall_nr as CULong);
        addr_of_mut!((*requestp).args[0]).write(0);
        addr_of_mut!((*requestp).args[1]).write(flags as CULong);
        addr_of_mut!((*requestp).args[2]).write(0);
        addr_of_mut!((*requestp).args[3]).write(0);
        addr_of_mut!((*requestp).args[4]).write(0);
        addr_of_mut!((*requestp).args[5]).write(0);
    }
'''
require(old.count(body)==1,'constructor body must be unique')
new=old.replace(body,replacement,1)
(D/'KERNEL-FUNCTION.OLD.rs.inc').write_bytes(old)
(D/'KERNEL-FUNCTION.NEW.rs.inc').write_bytes(new)
line=base[:start].count(b'\n')+1
patch=(b'--- a/kernel/rust/syscall_policy.rs\n+++ b/kernel/rust/syscall_policy.rs\n'+f'@@ -{line},{old.count(bytes([10]))} +{line},{new.count(bytes([10]))} @@\n'.encode()+b''.join(b'-'+x for x in old.splitlines(keepends=True))+b''.join(b'+'+x for x in new.splitlines(keepends=True)))
(D/'SIGNALFD-EXPLICIT-WIRE.M14-ONLY.PRIVATE-NOT-APPLIED.patch').write_bytes(patch)
inputs=[K,SRC/'kernel/rust/lib.rs',SRC/'kernel/rust/abi.rs',ROOT/'kernel/syscall.c',ROOT/'executer/include/uprotocol.h']
(D/'INPUTS.json').write_text(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','milestone':'M14_ONLY','inputs':[{'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in inputs],'original_function_preimage_sha256':sha(old),'replacement_function_sha256':sha(new),'source_map_effective_mount_or_custody_proof':False},indent=2)+'\n')
(D/'READINESS-ROWS.json').write_text(json.dumps({'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','milestone':'M14_ONLY','rows':[{'original_C_function':'syscall_signalfd_create_bridge','original_C_path':str(ROOT/'kernel/syscall.c'),'original_C_sha256':sha((ROOT/'kernel/syscall.c').read_bytes()),'current_Rust_source_path':str(K),'current_Rust_source_sha256':PIN,'exact_function_preimage_sha256':sha(old),'replacement_function_sha256':sha(new),'actual_prototype':'unsafe extern C fn(CInt, CInt) -> CLong','correction':'Replace caller whole-zero storage with exact number+six raw wire field writes; preserve existing defined wire vector and helper-owned rtid/ttid/valid','callable_provider':'existing syscall_policy::do_syscall and ihk_mc_get_processor_id; unchanged','provider_gap':'Existing synchronous request/response/current-thread/stack/channel lifetime contract retained; no additional global selection or ACK','status':'READY_FOR_ONE_AFFECTED_ACTUAL_KERNEL_FRONTEND_AFTER_OWNER_BINDING','new_C_retirement_credit':0,'new_guest_apps':0,'new_current_candidate_builds':0,'tests_or_compiler_run':False}],'host_runtime_patch_included':False,'M15_host_draft_deferred':True,'next_check':'Root/compositor one actual kernel Rust frontend with existing passed 172-source cfg/environment/tool tuple and fresh private output, changing only this exact function; no new cfg/selector required.'},indent=2)+'\n')
print(json.dumps({'kernel_patch_sha256':sha(patch),'replacement_function_sha256':sha(new),'bound_parent_sha256':PIN},sort_keys=True))
