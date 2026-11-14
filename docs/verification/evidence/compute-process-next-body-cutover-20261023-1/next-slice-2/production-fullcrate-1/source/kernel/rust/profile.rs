use core::{
    ffi::{c_char, c_void},
    mem::{offset_of, size_of},
    ptr::{null_mut, read_volatile},
};

use crate::abi::{
    AbiListHead, CInt, CLong, CULong, McsLockNode, Process, ProfileEvent, Thread, X86UserContext,
};

const ENOMEM: CInt = 12;
const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const PROFILE_SYSCALL_MAX: usize = 2000;
const PROFILE_OFFLOAD_MAX: usize = PROFILE_SYSCALL_MAX << 1;
const PROFILE_EVENT_MIN: usize = PROFILE_OFFLOAD_MAX;
const PROFILE_EVENT_MAX: usize = PROFILE_EVENT_MIN + PROFILE_EVENT_NAMES.len();
const PROFILE_MPOL_ALLOC_MISSED: CInt = (PROFILE_EVENT_MIN + 7) as CInt;
const PROF_CLEAR: CInt = 0x01;
const PROF_ON: CInt = 0x02;
const PROF_OFF: CInt = 0x04;
const PROF_PRINT: CInt = 0x08;
const PROF_JOB: CInt = 0x4000_0000;
const PROF_PROC: CInt = 0x8000_0000_u32 as CInt;

const PROFILE_FILE: &[u8] = b"kernel/rust/profile.rs\0";
const EVENT_WARN_FMT: &[u8] = b"%s: WARNING: unknown event type %d\n\0";
const PROFILE_EVENT_ADD_NAME: &[u8] = b"profile_event_add\0";
const THREAD_ALLOC_ERR_FMT: &[u8] = b"%s: ERROR: allocating thread private profile counters\n\0";
const PROC_ALLOC_ERR_FMT: &[u8] = b"%s: ERROR: allocating proc private profile counters\n\0";
const JOB_ALLOC_ERR_FMT: &[u8] = b"%s: ERROR: allocating job profile counters\n\0";
const PROFILE_ALLOC_EVENTS_NAME: &[u8] = b"profile_alloc_events\0";
const PROFILE_ACC_JOB_NAME: &[u8] = b"profile_accumulate_and_print_job_events\0";
const THREAD_HDR_FMT: &[u8] = b"TID: %4d elapsed cycles (excluding idle): %luk\n\0";
const PROC_HDR_FMT: &[u8] = b"PID: %4d elapsed cycles for all threads (excluding idle): %luk\n\0";
const JOB_HDR_FMT: &[u8] = b"JOB: (%2d) elapsed cycles for all threads (excluding idle): %luk\n\0";
const TABLE_HDR_FMT: &[u8] = b"%3s: %5s (%3s,%20s): %6s %7s offl: %6s %7s (%6s)\n\0";
const SYSCALL_ROW_FMT: &[u8] = b"%s: %4d (%3d,%20s): %6u %6luk offl: %6u %6luk (%2d.%2d%%)\n\0";
const EVENT_ROW_FMT: &[u8] = b"%s: %4d (%24s): %6u %6lu\n\0";
const ID_LABEL: &[u8] = b"ID\0";
const NUM_LABEL: &[u8] = b"<num>\0";
const NUM2_LABEL: &[u8] = b"num\0";
const NAME_LABEL: &[u8] = b"(syscall/event) name\0";
const CNT_LABEL: &[u8] = b"cnt\0";
const CYCLES_LABEL: &[u8] = b"cycles\0";
const PERC_LABEL: &[u8] = b"perc\0";
const TID_LABEL: &[u8] = b"TID\0";
const PID_LABEL: &[u8] = b"PID\0";
const JOB_LABEL: &[u8] = b"JOB\0";

const PROFILE_EVENT_NAMES: [&[u8]; 24] = [
    b"remote_tlb_invalidate\0",
    b"page_fault\0",
    b"page_fault_anon_clr_mem\0",
    b"page_fault_file\0",
    b"page_fault_dev_file\0",
    b"page_fault_file_clr_mem\0",
    b"remote_page_fault\0",
    b"mpol_alloc_missed\0",
    b"mmap_anon_contig_phys\0",
    b"|-------mmap_straight\0",
    b"|---mmap_not_straight\0",
    b"mmap_anon_no_contig_phys\0",
    b"mmap_regular_file\0",
    b"mmap_device_file\0",
    b"tofu_stag_alloc \0",
    b"|--new_steering \0",
    b"   |-alloc_mbpt \0",
    b"   |-update_mbpt\0",
    b"tofu_stag_free_stags\0",
    b"tofu_stag_free_stag\0",
    b"   |--------pre\0",
    b"   |----cqflush\0",
    b"   |----dealloc\0",
    b"      |---free_pages\0",
];

#[no_mangle]
pub static mut profile_event_names: [*mut c_char; PROFILE_EVENT_NAMES.len()] = [
    PROFILE_EVENT_NAMES[0].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[1].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[2].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[3].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[4].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[5].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[6].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[7].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[8].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[9].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[10].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[11].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[12].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[13].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[14].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[15].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[16].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[17].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[18].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[19].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[20].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[21].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[22].as_ptr() as *mut c_char,
    PROFILE_EVENT_NAMES[23].as_ptr() as *mut c_char,
];

#[no_mangle]
pub static mut job_profile_lock: McsLockNode = McsLockNode {
    locked: 0,
    next: null_mut(),
    irqsave: 0,
};

#[no_mangle]
pub static mut job_profile_events: *mut ProfileEvent = null_mut();

#[no_mangle]
pub static mut job_nr_processes: CInt = -1;

#[no_mangle]
pub static mut job_nr_processes_left: CInt = -1;

#[no_mangle]
pub static mut job_elapsed_ts: CULong = 0;

extern "C" {
    static syscall_name: [*const c_char; PROFILE_SYSCALL_MAX];

    fn _kmalloc(size: CInt, flags: CInt, file: *mut c_char, line: CInt) -> *mut c_void;
    fn _kfree(ptr: *mut c_void, file: *mut c_char, line: CInt);
    fn ihk_mc_get_processor_id() -> CInt;
    fn get_cpu_local_var(id: CInt) -> *mut crate::abi::CpuLocalVar;
    fn mcs_lock_lock(lock: *mut McsLockNode, node: *mut McsLockNode);
    fn mcs_lock_unlock(lock: *mut McsLockNode, node: *mut McsLockNode);
    fn __mcs_rwlock_reader_lock_noirq(lock: *mut c_void, node: *mut c_void);
    fn __mcs_rwlock_reader_unlock_noirq(lock: *mut c_void, node: *mut c_void);
    fn kprintf(format: *const c_char, ...) -> CInt;
    fn __kprintf(format: *const c_char, ...) -> CInt;
    fn kprintf_lock() -> CULong;
    fn kprintf_unlock(flags: CULong);
}

#[inline(always)]
fn file_ptr() -> *mut c_char {
    PROFILE_FILE.as_ptr() as *mut c_char
}

#[inline(always)]
fn rdtsc() -> CULong {
    let high: u32;
    let low: u32;
    unsafe {
        core::arch::asm!("rdtsc", out("eax") low, out("edx") high, options(nomem, nostack));
    }
    ((high as CULong) << 32) | low as CULong
}

#[inline(always)]
unsafe fn current_thread() -> *mut Thread {
    (*get_cpu_local_var(ihk_mc_get_processor_id())).current
}

#[inline(always)]
unsafe fn profile_events(ptr: *mut c_void) -> *mut ProfileEvent {
    ptr.cast::<ProfileEvent>()
}

#[inline(always)]
unsafe fn zero_events(events: *mut ProfileEvent) {
    core::ptr::write_bytes(
        events.cast::<u8>(),
        0,
        size_of::<ProfileEvent>() * PROFILE_EVENT_MAX,
    );
}

#[inline(always)]
unsafe fn thread_from_siblings(link: *mut AbiListHead) -> *mut Thread {
    link.cast::<u8>()
        .sub(offset_of!(Thread, siblings_list))
        .cast::<Thread>()
}

#[inline(always)]
unsafe fn iter_process_threads(proc: *mut Process, mut f: impl FnMut(*mut Thread)) {
    let head = &raw mut (*proc).threads_list;
    let mut node = read_volatile(&(*head).next);
    while node != head {
        let thread = thread_from_siblings(node);
        node = read_volatile(&(*node).next);
        f(thread);
    }
}

#[no_mangle]
pub extern "C" fn profile_syscall2offload(sc: CInt) -> CInt {
    PROFILE_SYSCALL_MAX as CInt + sc
}

#[no_mangle]
pub unsafe extern "C" fn profile_event_add(type_: CInt, tsc: u64) {
    let thread = current_thread();
    if thread.is_null() || (*thread).profile == 0 {
        return;
    }

    if (*thread).profile_events.is_null() {
        if type_ == PROFILE_MPOL_ALLOC_MISSED {
            return;
        }
        if profile_alloc_events(thread) < 0 {
            return;
        }
    }

    if type_ < 0 || type_ as usize >= PROFILE_EVENT_MAX {
        kprintf(
            EVENT_WARN_FMT.as_ptr().cast(),
            PROFILE_EVENT_ADD_NAME.as_ptr(),
            type_,
        );
        return;
    }

    let event = profile_events((*thread).profile_events).add(type_ as usize);
    (*event).cnt = (*event).cnt.wrapping_add(1);
    (*event).tsc = (*event).tsc.wrapping_add(tsc);
}

unsafe fn print_profile_events(
    events: *mut ProfileEvent,
    full_hdr_fmt: *const c_char,
    hdr_prefix: *const u8,
    id: CInt,
    elapsed_ts: CULong,
) {
    let flags = kprintf_lock();
    __kprintf(full_hdr_fmt, id, elapsed_ts / 1000);
    __kprintf(
        TABLE_HDR_FMT.as_ptr().cast(),
        ID_LABEL.as_ptr(),
        NUM_LABEL.as_ptr(),
        NUM2_LABEL.as_ptr(),
        NAME_LABEL.as_ptr(),
        CNT_LABEL.as_ptr(),
        CYCLES_LABEL.as_ptr(),
        CNT_LABEL.as_ptr(),
        CYCLES_LABEL.as_ptr(),
        PERC_LABEL.as_ptr(),
    );

    let mut i = 0usize;
    while i < PROFILE_SYSCALL_MAX {
        let normal = events.add(i);
        let offload = events.add(i + PROFILE_SYSCALL_MAX);
        if (*normal).cnt != 0 || (*offload).cnt != 0 {
            let pct = if (*normal).tsc != 0 && elapsed_ts != 0 {
                (*normal).tsc.wrapping_mul(100) / elapsed_ts
            } else {
                0
            };
            let pct_frac = if (*normal).tsc != 0 && elapsed_ts != 0 {
                ((*normal).tsc.wrapping_mul(10000) / elapsed_ts) % 100
            } else {
                0
            };
            __kprintf(
                SYSCALL_ROW_FMT.as_ptr().cast(),
                hdr_prefix,
                id,
                i as CInt,
                syscall_name[i],
                (*normal).cnt,
                (*normal).tsc / 1000,
                (*offload).cnt,
                (*offload).tsc / 1000,
                pct as CInt,
                pct_frac as CInt,
            );
        }
        i += 1;
    }

    i = PROFILE_EVENT_MIN;
    while i < PROFILE_EVENT_MAX {
        let event = events.add(i);
        if (*event).cnt != 0 {
            let average = (*event).tsc / ((*event).cnt as CULong).max(1);
            __kprintf(
                EVENT_ROW_FMT.as_ptr().cast(),
                hdr_prefix,
                id,
                profile_event_names[i - PROFILE_EVENT_MIN],
                (*event).cnt,
                average,
            );
        }
        i += 1;
    }

    kprintf_unlock(flags);
}

#[no_mangle]
pub unsafe extern "C" fn profile_print_thread_stats(thread: *mut Thread) {
    if thread.is_null() || (*thread).profile_events.is_null() {
        return;
    }
    if (*thread).profile_start_ts != 0 {
        (*thread).profile_elapsed_ts = (*thread)
            .profile_elapsed_ts
            .wrapping_add(rdtsc().wrapping_sub((*thread).profile_start_ts));
    }
    print_profile_events(
        profile_events((*thread).profile_events),
        THREAD_HDR_FMT.as_ptr().cast(),
        TID_LABEL.as_ptr(),
        (*thread).tid,
        (*thread).profile_elapsed_ts,
    );
}

#[no_mangle]
pub unsafe extern "C" fn profile_print_proc_stats(proc: *mut Process) {
    if proc.is_null() || (*proc).profile_events.is_null() || (*proc).profile_elapsed_ts == 0 {
        return;
    }
    print_profile_events(
        profile_events((*proc).profile_events),
        PROC_HDR_FMT.as_ptr().cast(),
        PID_LABEL.as_ptr(),
        (*proc).pid,
        (*proc).profile_elapsed_ts,
    );
}

#[no_mangle]
pub unsafe extern "C" fn profile_accumulate_and_print_job_events(proc: *mut Process) -> CInt {
    let mut node = McsLockNode {
        locked: 0,
        next: null_mut(),
        irqsave: 0,
    };
    mcs_lock_lock(&raw mut job_profile_lock, &raw mut node);

    if job_nr_processes == -1 {
        job_nr_processes = (*proc).nr_processes;
        job_nr_processes_left = (*proc).nr_processes;
        job_elapsed_ts = 0;
    }
    job_nr_processes_left -= 1;

    if job_profile_events.is_null() {
        job_profile_events = _kmalloc(
            (size_of::<ProfileEvent>() * PROFILE_EVENT_MAX) as CInt,
            IHK_MC_AP_NOWAIT,
            file_ptr(),
            line!() as CInt,
        )
        .cast::<ProfileEvent>();
        if job_profile_events.is_null() {
            kprintf(
                JOB_ALLOC_ERR_FMT.as_ptr().cast(),
                PROFILE_ACC_JOB_NAME.as_ptr(),
            );
            return -ENOMEM;
        }
        zero_events(job_profile_events);
    }

    let proc_events = profile_events((*proc).profile_events);
    let mut i = 0usize;
    while i < PROFILE_EVENT_MAX {
        let src = proc_events.add(i);
        if (*src).tsc != 0 {
            let dst = job_profile_events.add(i);
            (*dst).tsc = (*dst).tsc.wrapping_add((*src).tsc);
            (*dst).cnt = (*dst).cnt.wrapping_add((*src).cnt);
            (*src).tsc = 0;
            (*src).cnt = 0;
        }
        i += 1;
    }

    job_elapsed_ts = job_elapsed_ts.wrapping_add((*proc).profile_elapsed_ts);
    if job_nr_processes_left == 0 {
        print_profile_events(
            job_profile_events,
            JOB_HDR_FMT.as_ptr().cast(),
            JOB_LABEL.as_ptr(),
            job_nr_processes,
            job_elapsed_ts,
        );
        job_nr_processes = -1;
        job_nr_processes_left = -1;
        job_elapsed_ts = 0;
        zero_events(job_profile_events);
    }

    mcs_lock_unlock(&raw mut job_profile_lock, &raw mut node);
    0
}

#[no_mangle]
pub unsafe extern "C" fn profile_accumulate_events(thread: *mut Thread, proc: *mut Process) {
    if thread.is_null()
        || proc.is_null()
        || (*thread).profile_events.is_null()
        || (*proc).profile_events.is_null()
    {
        return;
    }

    let mut node = McsLockNode {
        locked: 0,
        next: null_mut(),
        irqsave: 0,
    };
    mcs_lock_lock(&raw mut (*proc).profile_lock, &raw mut node);

    let thread_events = profile_events((*thread).profile_events);
    let proc_events = profile_events((*proc).profile_events);
    let mut i = 0usize;
    while i < PROFILE_EVENT_MAX {
        let src = thread_events.add(i);
        let dst = proc_events.add(i);
        (*dst).tsc = (*dst).tsc.wrapping_add((*src).tsc);
        (*dst).cnt = (*dst).cnt.wrapping_add((*src).cnt);
        (*src).tsc = 0;
        (*src).cnt = 0;
        i += 1;
    }

    (*proc).profile_elapsed_ts = (*proc)
        .profile_elapsed_ts
        .wrapping_add((*thread).profile_elapsed_ts);
    if (*thread).profile_start_ts != 0 {
        (*proc).profile_elapsed_ts = (*proc)
            .profile_elapsed_ts
            .wrapping_add(rdtsc().wrapping_sub((*thread).profile_start_ts));
    }

    mcs_lock_unlock(&raw mut (*proc).profile_lock, &raw mut node);
}

#[no_mangle]
pub unsafe extern "C" fn profile_alloc_events(thread: *mut Thread) -> CInt {
    let proc = (*thread).proc;

    if (*thread).profile_events.is_null() {
        (*thread).profile_events = _kmalloc(
            (size_of::<ProfileEvent>() * PROFILE_EVENT_MAX) as CInt,
            IHK_MC_AP_NOWAIT,
            file_ptr(),
            line!() as CInt,
        );
        if (*thread).profile_events.is_null() {
            kprintf(
                THREAD_ALLOC_ERR_FMT.as_ptr().cast(),
                PROFILE_ALLOC_EVENTS_NAME.as_ptr(),
            );
            return -ENOMEM;
        }
        zero_events(profile_events((*thread).profile_events));
    }

    let mut node = McsLockNode {
        locked: 0,
        next: null_mut(),
        irqsave: 0,
    };
    mcs_lock_lock(&raw mut (*proc).profile_lock, &raw mut node);
    if (*proc).profile_events.is_null() {
        (*proc).profile_events = _kmalloc(
            (size_of::<ProfileEvent>() * PROFILE_EVENT_MAX) as CInt,
            IHK_MC_AP_NOWAIT,
            file_ptr(),
            line!() as CInt,
        );
        if (*proc).profile_events.is_null() {
            kprintf(
                PROC_ALLOC_ERR_FMT.as_ptr().cast(),
                PROFILE_ALLOC_EVENTS_NAME.as_ptr(),
            );
            mcs_lock_unlock(&raw mut (*proc).profile_lock, &raw mut node);
            return -ENOMEM;
        }
        zero_events(profile_events((*proc).profile_events));
    }
    mcs_lock_unlock(&raw mut (*proc).profile_lock, &raw mut node);

    0
}

#[no_mangle]
pub unsafe extern "C" fn profile_dealloc_thread_events(thread: *mut Thread) {
    if !thread.is_null() {
        _kfree((*thread).profile_events, file_ptr(), line!() as CInt);
    }
}

#[no_mangle]
pub unsafe extern "C" fn profile_dealloc_proc_events(proc: *mut Process) {
    if !proc.is_null() {
        _kfree((*proc).profile_events, file_ptr(), line!() as CInt);
    }
}

unsafe fn profile_clear_process(proc: *mut Process) {
    (*proc).profile_elapsed_ts = 0;
    if !(*proc).profile_events.is_null() {
        zero_events(profile_events((*proc).profile_events));
    }
}

unsafe fn profile_clear_thread(thread: *mut Thread) {
    (*thread).profile_start_ts = 0;
    (*thread).profile_elapsed_ts = 0;
    if !(*thread).profile_events.is_null() {
        zero_events(profile_events((*thread).profile_events));
    }
}

#[no_mangle]
pub unsafe extern "C" fn do_profile(flag: CInt) -> CInt {
    let thread = current_thread();
    if thread.is_null() {
        return 0;
    }
    let proc = (*thread).proc;
    let now_ts = rdtsc();

    if flag & PROF_JOB != 0 {
        if flag & PROF_PRINT != 0 {
            __mcs_rwlock_reader_lock_noirq(
                (&raw mut (*proc).threads_lock).cast::<c_void>(),
                null_mut(),
            );
            iter_process_threads(proc, |thread| {
                profile_accumulate_events(thread, proc);
            });
            __mcs_rwlock_reader_unlock_noirq(
                (&raw mut (*proc).threads_lock).cast::<c_void>(),
                null_mut(),
            );
            return profile_accumulate_and_print_job_events(proc);
        }
    } else if flag & PROF_PROC != 0 {
        __mcs_rwlock_reader_lock_noirq(
            (&raw mut (*proc).threads_lock).cast::<c_void>(),
            null_mut(),
        );
        iter_process_threads(proc, |thread| {
            if flag & PROF_PRINT != 0 {
                profile_accumulate_events(thread, proc);
            }
            if flag & PROF_CLEAR != 0 {
                profile_clear_thread(thread);
            }
            if flag & PROF_ON != 0 {
                (*thread).profile = 1;
                if (*thread).profile_start_ts == 0 {
                    (*thread).profile_start_ts = now_ts;
                }
            } else if flag & PROF_OFF != 0 && (*thread).profile != 0 {
                (*thread).profile = 0;
                if (*thread).profile_start_ts != 0 {
                    (*thread).profile_elapsed_ts = (*thread)
                        .profile_elapsed_ts
                        .wrapping_add(now_ts.wrapping_sub((*thread).profile_start_ts));
                }
                (*thread).profile_start_ts = 0;
            }
        });
        __mcs_rwlock_reader_unlock_noirq(
            (&raw mut (*proc).threads_lock).cast::<c_void>(),
            null_mut(),
        );

        if flag & PROF_PRINT != 0 {
            profile_print_proc_stats(proc);
        }
        if flag & PROF_CLEAR != 0 {
            profile_clear_process(proc);
        }
        if flag & PROF_ON != 0 {
            if (*proc).profile == 0 {
                (*proc).profile = 1;
            }
        } else if flag & PROF_OFF != 0 {
            (*proc).profile = 0;
        }
    } else {
        if flag & PROF_PRINT != 0 {
            profile_print_thread_stats(thread);
        }
        if flag & PROF_CLEAR != 0 {
            profile_clear_thread(thread);
            if (*thread).profile != 0 {
                (*thread).profile_start_ts = 0;
                (*thread).profile_elapsed_ts = 0;
            }
        }
        if flag & PROF_ON != 0 {
            if (*thread).profile == 0 {
                (*thread).profile = 1;
                (*thread).profile_start_ts = now_ts;
            }
        } else if flag & PROF_OFF != 0 && (*thread).profile != 0 {
            (*thread).profile = 0;
            if (*thread).profile_start_ts != 0 {
                (*thread).profile_elapsed_ts = (*thread)
                    .profile_elapsed_ts
                    .wrapping_add(now_ts.wrapping_sub((*thread).profile_start_ts));
            }
            (*thread).profile_start_ts = 0;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn sys_profile(_n: CInt, ctx: *mut X86UserContext) -> CLong {
    do_profile((*ctx).gpr.rdi as CInt) as CLong
}
