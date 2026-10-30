// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Existing retained helpers, wrapped as a single disabled-by-default source unit.
#[cfg(f03_do_fork_owned_candidate)]
mod f03_fork_private_dependencies_v1 {
    use super::*;
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private syscall_policy entry fragment; complete existing request helper reused.
unsafe extern "C" fn f03_settid_virt_to_phys_v1(ptr:*mut c_void)->CULong {
    crate::x86_memory_helpers::virt_to_phys(ptr)
}
unsafe extern "C" fn f03_settid_request_call_v1(
    request:*mut SyscallRequest,cpu:CInt,
)->CLong {
    do_syscall(request,cpu)
}
unsafe extern "C" fn f03_settid_log_v1(ret:CInt) {
    // Preserve original selected literal and legacy __FUNCTION__ == "settid".
    kprintf(c"settid: WARNING: do_syscall returns %d\n".as_ptr().cast(),ret);
}
/// # Safety
/// The existing synchronous gettid-pool ABI retains tids/physical reply storage.
/// thread is deliberately unused, as in original settid. The exact supported
/// x86 IHK_DMA_ALIGN macro is empty; SyscallRequest retains its actual C layout.
/// The helper zero-writes EVERY request byte before any read/publication, so
/// raw scratch carries no undefined trailing arguments or padding into syscall.
#[no_mangle]
pub unsafe extern "C" fn f03_settid_pool_v1(
    _thread:*mut Thread,nr_tids:CInt,tids:*mut CInt,
)->CInt {
    let mut request=MaybeUninit::<SyscallRequest>::uninit();
    syscall_settid_body_result(
        request.as_mut_ptr(),nr_tids,tids,186,
        f03_settid_virt_to_phys_v1,ihk_mc_get_processor_id,
        f03_settid_request_call_v1,f03_settid_log_v1,
    )
}


// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private syscall_policy fragment; root centrally merges declarative C ABI/data.
unsafe extern "C" {
    #[link_name="allow_oversubscribe"] static mut F03_TID_POOL_OVERSUBSCRIBE:CInt;
}
#[repr(C)]
pub struct F03TidPoolOrigins {
    file:*const i8,temp_alloc:CInt,pool_alloc:CInt,
    temp_free_pool_failed:CInt,temp_free_settid_failed:CInt,temp_free_success:CInt,
    populated_debug:*mut crate::debug::Ddebug,assigned_debug:*mut crate::debug::Ddebug,
}
unsafe fn f03_tid_pool_count_v1()->CInt {
    let cpus=crate::ap::num_processors;
    if F03_TID_POOL_OVERSUBSCRIBE!=0 {
        let doubled=cpus.wrapping_mul(2);
        if doubled>128 {doubled} else {128}
    } else {cpus}
}
/// # Safety
/// Caller holds the original new Thread/Process lifetimes; origin/out pointers
/// are live. Existing pool nr_tids entries are initialized. Successful gettid
/// delivery supplies the entire requested int array, as in the bound C producer
/// reference; current selected producer qualification remains a separate task.
/// Boot CPU-count/oversubscription state stays stable and count arithmetic is in
/// the original C defined domain. Scratch IRQ node is written by the real lock
/// before unlock reads it. Only initialized table fields are read, never padding.
/// Return0 continues;1 preserves destroy_thread edge;2 preserves release_ids edge.
#[no_mangle]
pub unsafe extern "C" fn f03_clone_vm_tid_pool_v1(
    new:*mut Thread,proc:*mut Process,created:*mut CInt,error:*mut CInt,
    origin:*const F03TidPoolOrigins,
)->CInt {
    let origin=&*origin;
    let mut node=MaybeUninit::<crate::lock_helpers::McsRwlockNodeIrqsave>::uninit();
    let lock=addr_of_mut!((*proc).threads_lock).cast::<crate::lock_helpers::McsRwlockLock>();
    crate::lock_helpers::__mcs_rwlock_writer_lock(lock,node.as_mut_ptr());
    if (*proc).nr_tids==0 {
        let n=f03_tid_pool_count_v1();
        let tids=crate::mem_helpers::kmalloc_tracked(
            size_of::<CInt>().wrapping_mul(n as usize) as CInt,2,
            origin.file.cast_mut(),origin.temp_alloc,
        ).cast::<CInt>();
        if tids.is_null() {
            crate::lock_helpers::__mcs_rwlock_writer_unlock(lock,node.as_mut_ptr());
            *error=-ENOMEM;return 1;
        }
        let n=f03_tid_pool_count_v1();
        (*proc).tids=crate::mem_helpers::kmalloc_tracked(
            size_of::<crate::abi::McexecTid>().wrapping_mul(n as usize) as CInt,2,
            origin.file.cast_mut(),origin.pool_alloc,
        );
        if (*proc).tids.is_null() {
            crate::lock_helpers::__mcs_rwlock_writer_unlock(lock,node.as_mut_ptr());
            crate::mem_helpers::kfree_tracked(tids.cast(),origin.file.cast_mut(),origin.temp_free_pool_failed);
            *error=-ENOMEM;return 1;
        }
        *created=1;
        let ret=f03_settid_pool_v1(new,f03_tid_pool_count_v1(),tids);
        *error=ret;
        if ret<0 {
            crate::lock_helpers::__mcs_rwlock_writer_unlock(lock,node.as_mut_ptr());
            crate::mem_helpers::kfree_tracked(tids.cast(),origin.file.cast_mut(),origin.temp_free_settid_failed);
            return 2;
        }
        let mut i:CInt=0;
        while i<f03_tid_pool_count_v1() && *tids.add(i as usize)!=0 {
            let tid=*tids.add(i as usize);
            if read_volatile(addr_of!((*origin.populated_debug).line_flags))>>24!=0 {
                kprintf(c"%s: tids[%d]: %d\n".as_ptr().cast(),c"do_fork".as_ptr(),i,tid);
            }
            let slot=(*proc).tids.cast::<crate::abi::McexecTid>().add(i as usize);
            addr_of_mut!((*slot).tid).write(tid);
            addr_of_mut!((*slot).thread).write(null_mut());
            (*proc).nr_tids=(*proc).nr_tids.wrapping_add(1);
            i+=1;
        }
        crate::mem_helpers::kfree_tracked(tids.cast(),origin.file.cast_mut(),origin.temp_free_success);
    }
    (*new).tid=0;
    'retry: loop {
        let mut i:CInt=0;
        while i<(*proc).nr_tids {
            let slot=(*proc).tids.cast::<crate::abi::McexecTid>().add(i as usize);
            if (*slot).thread.is_null() {
                if !crate::atomic_helpers::atomic_cmpxchg_ptr(
                    addr_of_mut!((*slot).thread).cast(),null_mut(),new.cast(),
                ).is_null() {continue 'retry;}
                (*new).tid=(*slot).tid;
                if read_volatile(addr_of!((*origin.assigned_debug).line_flags))>>24!=0 {
                    kprintf(c"%s: tid %d assigned to %p\n".as_ptr().cast(),c"do_fork".as_ptr(),(*new).tid,new);
                }
                break;
            }
            i+=1;
        }
        break;
    }
    crate::lock_helpers::__mcs_rwlock_writer_unlock(lock,node.as_mut_ptr());
    if (*new).tid==0 {
        kprintf(c"%s: no more TIDs available\n".as_ptr().cast(),c"do_fork".as_ptr());
        let mut i:CInt=0;
        while i<(*proc).nr_tids {
            let slot=(*proc).tids.cast::<crate::abi::McexecTid>().add(i as usize);
            kprintf(c"%s: i=%d,tid=%d,thread=%p\n".as_ptr().cast(),c"do_fork".as_ptr(),i,(*slot).tid,(*slot).thread);
            i+=1;
        }
        *error=-ENOMEM;return 2;
    }
    0
}


// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private syscall_policy fragment; public real memory/copy APIs only, no Page getter.
#[repr(C)]
pub struct F03CloneTidDebug {
    parent:*mut crate::debug::Ddebug,clear:*mut crate::debug::Ddebug,
    child:*mut crate::debug::Ddebug,
}
unsafe fn f03_clone_tid_debug_enabled_v1(debug:*mut crate::debug::Ddebug)->bool {
    read_volatile(addr_of!((*debug).line_flags))>>24!=0
}
/// # Safety
/// Original held/nonrunnable child and VM/PT remain live. Native API retains its
/// explicit-VM copy contract, including page-crossing/unaligned user stores.
/// Legacy success maps a live, aligned, writable int as required by original C.
/// Debug descriptors and error local are live. The real translation provider
/// writes phys on every success path; scratch is read only after that success.
/// Return1 preserves original release_ids edge, return0 continues; error local
/// changes exactly where C assigned it. No copy-content/termination assumption.
#[no_mangle]
pub unsafe extern "C" fn f03_clone_commit_tid_addresses_v1(
    new:*mut Thread,flags:CInt,parent:CULong,child:CULong,native_tid:CInt,
    error:*mut CInt,debug:*const F03CloneTidDebug,
)->CInt {
    if clone_parent_tid_store_needed_result(flags)!=0 {
        if f03_clone_tid_debug_enabled_v1((*debug).parent) {
            kprintf(c"clone_flags & CLONE_PARENT_SETTID: 0x%lX\n".as_ptr().cast(),parent);
        }
        *error=crate::x86_memory_helpers::setint_user(parent as *mut CInt,(*new).tid);
        if native_tid!=0 {*error=0;}
        if *error!=0 {return 1;}
    }
    if clone_child_cleartid_needed_result(flags)!=0 {
        if f03_clone_tid_debug_enabled_v1((*debug).clear) {
            kprintf(c"clone_flags & CLONE_CHILD_CLEARTID: 0x%lX\n".as_ptr().cast(),child);
        }
        (*new).clear_child_tid=child as *mut CInt;
    }
    if clone_child_tid_store_needed_result(flags)!=0 {
        if native_tid!=0 {
            let _=crate::x86_memory_helpers::write_process_vm(
                (*new).vm,child as *mut c_void,addr_of!((*new).tid).cast(),size_of::<CInt>(),
            );
        } else {
            if f03_clone_tid_debug_enabled_v1((*debug).child) {
                kprintf(c"clone_flags & CLONE_CHILD_SETTID: 0x%lX\n".as_ptr().cast(),child);
            }
            let mut phys=MaybeUninit::<CULong>::uninit();
            let ret=crate::x86_memory_helpers::ihk_mc_pt_virt_to_phys(
                (*(*(*new).vm).address_space).page_table,
                child as *const c_void,phys.as_mut_ptr(),
            );
            if ret!=0 {
                kprintf(c"ERROR: looking up physical addr for child process\n".as_ptr().cast());
                *error=-EFAULT;return 1;
            }
            let physical=phys.assume_init();
            let mapped=crate::x86_memory_helpers::phys_to_virt(physical).cast::<CInt>();
            mapped.write((*new).tid);
        }
    }
    0
}


// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

/// Complete local clone reporting and the existing final enqueue/return path.
///
/// # Safety
/// The caller has completed thread/process publication and, for non-CLONE_VM,
/// the unchanged host clone request successfully. `new` remains retained through
/// report, TID snapshot and enqueue. The result is a scalar thereafter. `oldproc`
/// and both report lists are live in the reporting branch; their genuine lock
/// serializes list membership. No host request, ownership release or ACK is added.
#[no_mangle]
pub unsafe extern "C" fn f03_clone_finish_report_enqueue_v1(
    new: *mut Thread,
    oldproc: *mut Process,
    flags: CInt,
    termsig: CInt,
    cpuid: CInt,
    ptrace_event: CInt,
) -> CInt {
    if flags & CLONE_VM != 0 && clone_report_thread_result(flags, termsig) != 0 {
        let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
        // SAFETY: The original live process owns this lock. The real writer
        // provider initializes the saved IRQ slot before unlock consumes it.
        unsafe {
            crate::lock_helpers::__mcs_rwlock_writer_lock(
                addr_of_mut!((*oldproc).threads_lock).cast(),
                node.as_mut_ptr(),
            );
        }
        // SAFETY: Under threads_lock, use the genuine layout and list provider.
        // Its ignored result and partial guard semantics match the C call.
        unsafe {
            let _ = crate::process_helpers::process_thread_report_attach_result(
                new.cast(),
                offset_of!(Thread, termsig) as CULong,
                1,
                termsig,
                offset_of!(Thread, report_proc) as CULong,
                oldproc.cast(),
                addr_of_mut!((*new).report_siblings_list),
                addr_of_mut!((*oldproc).report_threads_list),
            );
            crate::lock_helpers::__mcs_rwlock_writer_unlock(
                addr_of_mut!((*oldproc).threads_lock).cast(),
                node.as_mut_ptr(),
            );
        }
        // SAFETY: The published thread is retained. Preserve hold after unlock,
        // including the existing void-style ignored result at this caller edge.
        unsafe { let _ = crate::process_helpers::hold_thread(new); }
    }

    // Snapshot while the caller still owns the prepared child. Once enqueued,
    // the child may run and release its last reference before this caller resumes.
    // The TID was committed before publication and is the result of this clone.
    let child_tid = unsafe { addr_of!((*new).tid).read() };
    // SAFETY: This is the original live prepared thread and chosen CPU. Call the
    // genuine void public enqueuer, not its checked internal alternative.
    unsafe { crate::sched_helpers::runq_add_thread(new, cpuid) };
    if ptrace_event != 0 {
        // SAFETY: The original caller's execution/IRQ context permits schedule.
        // The scalar snapshot avoids accessing the child after publication.
        unsafe { schedule() };
    }
    child_tid
}


// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private policy fragment; the earlier owned-constructor cancel path is untouched.
/// # Safety
/// This is only the original legacy destroy_thread suffix after the retained
/// owned-constructor bypass. The caller owns the same constructed Thread graph
/// and optional saved command line. Original force-to-one refcount assignments
/// are preserved, not justified for arbitrary shared graphs by this extraction.
/// release_thread consumes the existing edge; no thread/Process dereference is
/// permitted after it returns, and this function grants no final-retirement ACK.
#[no_mangle]
pub unsafe extern "C" fn f03_clone_destroy_legacy_thread_v1(
    new:*mut Thread,proc:*mut Process,clone_flags:CInt,
    file:*const i8,origin_line:CInt,
) {
    if clone_flags & CLONE_VM==0 {
        crate::atomic_helpers::ihk_atomic_set(addr_of_mut!((*(*new).proc).refcount).cast(),1);
        crate::mem_helpers::kfree_tracked((*proc).saved_cmdline,file.cast_mut(),origin_line);
        (*proc).saved_cmdline=null_mut();
    }
    crate::atomic_helpers::ihk_atomic_set(addr_of_mut!((*new).refcount).cast(),1);
    crate::process_helpers::release_thread(new);
}

}
#[cfg(f03_do_fork_owned_candidate)]
use f03_fork_private_dependencies_v1::{F03TidPoolOrigins, F03CloneTidDebug,
    f03_settid_pool_v1, f03_clone_vm_tid_pool_v1, f03_clone_commit_tid_addresses_v1,
    f03_clone_finish_report_enqueue_v1, f03_clone_destroy_legacy_thread_v1};
