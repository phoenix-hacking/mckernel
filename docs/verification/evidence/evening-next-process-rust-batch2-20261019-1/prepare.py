from pathlib import Path
import hashlib,json,difflib
O=Path(__file__).parent;S=Path('/home/holden/mckernel')
files=['kernel/process.c','kernel/rust/process_helpers.rs','kernel/rust/abi.rs','kernel/include/process_helpers.h','kernel/include/process.h','kernel/include/memobj.h']
bindings={}
for f in files:
 b=(S/f).read_bytes();p=O/'original'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);bindings[f]=hashlib.sha256(b).hexdigest()
(O/'source-bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
c=(O/'original/kernel/process.c').read_text();rs=(O/'original/kernel/rust/process_helpers.rs').read_text()
# Two fixed, named body ranges; no general declaration producer.
a=c.index('void *process_current_resource_set_bridge(void)\n{');z=c.index('\n}\n',a)+3
current=c[a:z]
a=c.index('void process_release_final_cleanup_bridge(void *resource_set_arg)\n{');z=c.index('\n}\n',a)+3
final=c[a:z]
cc=c
for name,body in [('process_current_resource_set_bridge',current),('process_release_final_cleanup_bridge',final)]:
 (O/(name+'.c')).write_text(body)
 proto=body[:body.index('\n{')]+';\n'
 cc=cc.replace(body,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'+proto+'#else\n'+body+'#endif\n',1)
for declaration in ['    fn process_current_resource_set_bridge() -> *mut c_void;\n','    fn process_release_final_cleanup_bridge(resource_set: *mut c_void);\n']:
 assert rs.count(declaration)==1;rs=rs.replace(declaration,'',1)
body='''
extern "C" {
    fn hugefileobj_cleanup();
    #[cfg(enable_tofu)]
    fn tof_utofu_finalize();
}

const _: () = {
    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);
    assert!(offset_of!(ResourceSet, pid1) == 320);
    assert!(offset_of!(Process, children_list) == 288);
    assert!(offset_of!(Process, children_lock) == 320);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
};

/// Read the current CPU's existing resource-set binding. The CPU-local pointer
/// returned by the existing ABI remains valid for this synchronous read. The
/// caller retains CPU affinity and owns the resource-set lifetime; this callback
/// neither obtains a reference nor interprets a possibly null resource-set value.
#[no_mangle]
pub unsafe extern "C" fn process_current_resource_set_bridge() -> *mut c_void {
    unsafe { (*get_this_cpu_local_var()).resource_set.cast() }
}

/// Perform existing last-child cleanup under pid1's children reader lock.
/// The resource set, pid1 process, initialized child-list head and lock storage
/// remain live, and pid1 stays stable throughout synchronous callbacks. The
/// cleanup callees retain their existing concurrency/ownership contracts. The
/// list-empty test is exactly head.next == head; no list mutation/free is added.
#[no_mangle]
pub unsafe extern "C" fn process_release_final_cleanup_bridge(resource_set_arg: *mut c_void) {
    let rset = resource_set_arg.cast::<ResourceSet>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        process_mcs_reader_lock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
        let head = core::ptr::addr_of_mut!((*(*rset).pid1).children_list);
        if (*head).next == head {
            #[cfg(enable_tofu)]
            tof_utofu_finalize();
            hugefileobj_cleanup();
        }
        process_mcs_reader_unlock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
    }
}
'''
(O/'new-bodies.rs').write_text(body)
for f,new in [('kernel/process.c',cc),('kernel/rust/process_helpers.rs',rs+body)]:
 p=O/'candidate'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(new)
 old=(O/'original'/f).read_text()
 with (O/'candidate.patch').open('a') as out:out.writelines(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+f,tofile='b/'+f))
# The actual default consumer is retained intact, including its unchanged ABI.
a=rs.index('#[no_mangle]\npub unsafe extern "C" fn release_process(proc: *mut Process)');z=rs.index('\n}\n',a)+3
(O/'frozen-rust-consumer.rs').write_text(rs[a:z])
a=c.index('void\nrelease_process(struct process *proc)');z=c.index('\n}\n',a)+3
(O/'frozen-c-consumer.c').write_text(c[a:z])
(O/'FROZEN-ORACLE.md').write_text('''Frozen before compiler/test execution. Current-resource callback invokes existing get_this_cpu_local_var exactly once and returns exactly that live CPU-local resource_set pointer (including a null resource_set value) without mutation or reference operation. Final cleanup always reader-locks pid1.children_lock, then tests exact head.next == head. If true: normal selection calls hugefileobj_cleanup exactly once; TOFU selection calls tof_utofu_finalize exactly once before hugefileobj_cleanup. Both cleanup calls occur after lock and before reader unlock. Nonempty/self-next-mismatch/null-next heads call neither cleanup. Unlock uses same live pid1 lock and aligned node as lock; no field/list/lock byte is modified by the adapter itself. Frozen C body may reload rset.pid1 after callbacks; production precondition keeps pid1 stable. Test-only observers may change head.next after lock to prove test placement, and after cleanup to prove no repeated cleanup/test. Every C and Rust run independently satisfies expected events/state, then their normalized traces must agree. Two compile selections (TOFU off/on); two independent CPU-local records and resource-set bindings; shape cases empty, child, null-next, mismatched-prev empty, and a multi-child circular list; one-time observer mutations confined to head.next with all nodes live. No actual lock/hardware or guest execution. Full real GCC14/C ABI/full crates/image/native proof stays pending.\n''')
print('PREPARED two live final-process resource/cleanup callbacks; private candidate and frozen oracle')
