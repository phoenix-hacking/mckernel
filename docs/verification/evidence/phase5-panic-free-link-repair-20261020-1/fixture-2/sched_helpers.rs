use crate::abi::*;use core::mem::offset_of;use core::ptr::{read_volatile,write_volatile};
const EINVAL:i32=22;const SCHED_RUNQ_LOG_RUNQ_ADD:CInt=5;type SchedRunqLogFn=unsafe extern "C" fn(i32,usize,usize,i32,i32);

pub struct SchedRunqueueOffsets {
    pub thread_cpu_id_offset: usize,
    pub thread_tid_offset: usize,
    pub thread_status_offset: usize,
    pub thread_spin_sleep_lock_offset: usize,
    pub thread_spin_sleep_offset: usize,
    pub thread_sched_list_offset: usize,
    pub thread_sigpending_offset: usize,
    pub thread_sigcommon_offset: usize,
    pub sigcommon_sigpending_offset: usize,
    pub thread_proc_offset: usize,
    pub thread_mod_clone_offset: usize,
    pub proc_pid_offset: usize,
    pub proc_status_offset: usize,
    pub proc_update_lock_offset: usize,
    pub proc_clone_count_offset: usize,
    pub cpu_runq_lock_offset: usize,
    pub cpu_runq_irqstate_offset: usize,
    pub cpu_current_offset: usize,
    pub cpu_prevpid_offset: usize,
    pub cpu_runq_offset: usize,
    pub cpu_runq_len_offset: usize,
    pub cpu_runq_reserved_offset: usize,
    pub cpu_flags_offset: usize,
    pub cpu_status_offset: usize,
    pub cpu_in_interrupt_offset: usize,
    pub cpu_nr_ctx_switches_offset: usize,
}

fn sched_runqueue_offsets() -> SchedRunqueueOffsets {
    SchedRunqueueOffsets {
        thread_cpu_id_offset: offset_of!(Thread, cpu_id),
        thread_tid_offset: offset_of!(Thread, tid),
        thread_status_offset: offset_of!(Thread, status),
        thread_spin_sleep_lock_offset: offset_of!(Thread, spin_sleep_lock),
        thread_spin_sleep_offset: offset_of!(Thread, spin_sleep),
        thread_sched_list_offset: offset_of!(Thread, sched_list),
        thread_sigpending_offset: offset_of!(Thread, sigpending),
        thread_sigcommon_offset: offset_of!(Thread, sigcommon),
        sigcommon_sigpending_offset: offset_of!(SigCommon, sigpending),
        thread_proc_offset: offset_of!(Thread, proc),
        thread_mod_clone_offset: offset_of!(Thread, mod_clone),
        proc_pid_offset: offset_of!(Process, pid),
        proc_status_offset: offset_of!(Process, status),
        proc_update_lock_offset: offset_of!(Process, update_lock),
        proc_clone_count_offset: offset_of!(Process, clone_count),
        cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
        cpu_runq_irqstate_offset: offset_of!(CpuLocalVar, runq_irqstate),
        cpu_current_offset: offset_of!(CpuLocalVar, current),
        cpu_prevpid_offset: offset_of!(CpuLocalVar, prevpid),
        cpu_runq_offset: offset_of!(CpuLocalVar, runq),
        cpu_runq_len_offset: offset_of!(CpuLocalVar, runq_len),
        cpu_runq_reserved_offset: offset_of!(CpuLocalVar, runq_reserved),
        cpu_flags_offset: offset_of!(CpuLocalVar, flags),
        cpu_status_offset: offset_of!(CpuLocalVar, status),
        cpu_in_interrupt_offset: offset_of!(CpuLocalVar, in_interrupt),
        cpu_nr_ctx_switches_offset: offset_of!(CpuLocalVar, nr_ctx_switches),
    }
}

unsafe fn list_prev_addr(list_addr: usize) -> usize {
    unsafe { read_volatile(list_addr.wrapping_add(core::mem::size_of::<usize>()) as *const usize) }
}

unsafe fn list_add_tail_addr(entry_addr: usize, head_addr: usize) {
    let prev = unsafe { list_prev_addr(head_addr) };

    unsafe {
        write_volatile(entry_addr as *mut usize, head_addr);
        write_volatile(
            entry_addr.wrapping_add(core::mem::size_of::<usize>()) as *mut usize,
            prev,
        );
        write_volatile(prev as *mut usize, entry_addr);
        write_volatile(
            head_addr.wrapping_add(core::mem::size_of::<usize>()) as *mut usize,
            entry_addr,
        );
    }
}

unsafe fn list_add_tail_counted_addr(entry_addr: usize, head_addr: usize, len_addr: usize) -> bool {
    if entry_addr == 0 || head_addr == 0 || len_addr == 0 {
        return false;
    }
    unsafe {
        list_add_tail_addr(entry_addr, head_addr);
        let len = read_volatile(len_addr as *const usize);
        write_volatile(len_addr as *mut usize, len.wrapping_add(1));
    }
    true
}

unsafe fn sched_read_usize(base: usize, offset: SizeT) -> usize {
    unsafe { read_volatile(base.wrapping_add(offset) as *const usize) }
}

pub unsafe extern "C" fn sched_runq_add_thread_locked_result(
    thread_addr: usize,
    cpu_addr: usize,
    cpu_id: CInt,
    need_resched_flag: u32,
    running_status: CInt,
    offsets: *const SchedRunqueueOffsets,
    log_fn: Option<SchedRunqLogFn>,
) -> CInt {
    if thread_addr == 0 || cpu_addr == 0 || offsets.is_null() {
        return -EINVAL;
    }

    let offsets = unsafe { &*offsets };
    unsafe {
        list_add_tail_counted_addr(
            thread_addr.wrapping_add(offsets.thread_sched_list_offset),
            cpu_addr.wrapping_add(offsets.cpu_runq_offset),
            cpu_addr.wrapping_add(offsets.cpu_runq_len_offset),
        );
        let flags_addr = cpu_addr.wrapping_add(offsets.cpu_flags_offset);
        let flags = read_volatile(flags_addr as *const u32);
        write_volatile(flags_addr as *mut u32, flags | need_resched_flag);
        write_volatile(
            thread_addr.wrapping_add(offsets.thread_cpu_id_offset) as *mut CInt,
            cpu_id,
        );
        write_volatile(
            cpu_addr.wrapping_add(offsets.cpu_status_offset) as *mut CInt,
            running_status,
        );
    }

    if let Some(log) = log_fn {
        let tid = unsafe {
            read_volatile(thread_addr.wrapping_add(offsets.thread_tid_offset) as *const CInt)
        };
        unsafe {
            log(SCHED_RUNQ_LOG_RUNQ_ADD, thread_addr, cpu_addr, tid, cpu_id);
        }
    }
    0
}

// Adapter only for platform outer-lock/procfs/IRQ callbacks. The production
// runqueue insertion body and its real ABI offsets above execute unchanged.
pub unsafe fn runq_add_thread_checked(thread:*mut Thread,cpu:i32)->i32{
 if crate::phase5_tests::mode()==3{return -22;}
 let target=crate::phase5_tests::target();let offsets=sched_runqueue_offsets();
 let result=sched_runq_add_thread_locked_result(thread as usize,target as usize,cpu,1,1,&offsets,None);
 if result==0{(*target).runq_reserved-=1;crate::phase5_tests::queued();}result
}

unsafe extern "C" {fn arch_flush_icache_all();fn release_thread(p:*mut core::ffi::c_void);fn rusage_num_threads_dec();fn kprintf(format:*const i8,...)->CInt;}
#[repr(C)]
pub struct SchedExitDebug {
    pub num_threads: *const CULong,
    pub total_memory_usage: *const CULong,
    pub memory_stat_rss: *const CLong,
    pub memory_stat_mapped_file: *const CLong,
    pub page_sizes: CInt,
}
pub unsafe extern "C" fn sched_schedule_exit_cleanup(
    old_cpu: *mut CpuLocalVar,
    last: *mut Thread,
    exited_status: CInt,
    debug: *const SchedExitDebug,
) {
    if last.is_null() || unsafe { read_volatile(&raw const (*last).status) } != exited_status {
        return;
    }
    unsafe {
        write_volatile(&raw mut (*old_cpu).prevpid, 0);
        arch_flush_icache_all();
        // Freeze the existing slot/epoch while last is still live. An
        // untracked Thread must remain untracked if release frees its address.
        let exit_token = crate::fork_control_registry::capture_runtime_exit_before_release(last as usize);
        release_thread(last.cast());
        // Never relook up or dereference last after the ordinary edge release.
        let _ = crate::fork_control_registry::complete_runtime_exit_after_release(exit_token);
        rusage_num_threads_dec();
    }
    // release_thread may free last, including its backing pages. Only the
    // independent accounting inputs are used from this point onward.
    if !debug.is_null() && unsafe { read_volatile((*debug).num_threads) } == 0 {
        unsafe {
            kprintf(
                b"total_memory_usage=%ld\n\0".as_ptr().cast(),
                read_volatile((*debug).total_memory_usage),
            );
            let mut i: CInt = 0;
            while i < (*debug).page_sizes {
                kprintf(
                    b"memory_stat_rss[%d]=%ld\n\0".as_ptr().cast(),
                    i,
                    read_volatile((*debug).memory_stat_rss.add(i as usize)),
                );
                i += 1;
            }
            i = 0;
            while i < (*debug).page_sizes {
                kprintf(
                    b"memory_stat_mapped_file[%d]=%ld\n\0".as_ptr().cast(),
                    i,
                    read_volatile((*debug).memory_stat_mapped_file.add(i as usize)),
                );
                i += 1;
            }
        }
    }
}
