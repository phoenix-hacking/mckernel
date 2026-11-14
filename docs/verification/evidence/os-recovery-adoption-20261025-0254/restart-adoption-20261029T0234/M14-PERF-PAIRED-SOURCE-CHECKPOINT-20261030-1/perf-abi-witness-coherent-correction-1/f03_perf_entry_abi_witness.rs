//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Witness-only module; compile only in a separate object excluded from every image link.
use super::*;
#[used]
#[no_mangle]
pub static f03_perf_entry_rust_scalar_witness_v1: [CULong; 31] = [
    (size_of::<PerfEventAttr>()) as CULong, // attr_size
    (offset_of!(PerfEventAttr, type_)) as CULong, // attr_type
    (offset_of!(PerfEventAttr, read_format)) as CULong, // attr_read_format
    (offset_of!(PerfEventAttr, sampling)) as CULong, // attr_sample_period
    (4) as CULong, // raw_type
    (0) as CULong, // hardware_type
    (3) as CULong, // cache_type
    (7) as CULong, // unsupported_format
    (1u64 << 63) as CULong, // sign_bit
    (298) as CULong, // syscall_number
    (size_of::<Mckfd>()) as CULong, // mckfd_size
    (super::super::IHK_MC_AP_NOWAIT) as CULong, // allocation_flags
    (offset_of!(FullMcPerfEvent, pid)) as CULong, // event_pid
    (offset_of!(FullMcPerfEvent, counter_id)) as CULong, // event_counter_id
    (offset_of!(Process, mckfd)) as CULong, // proc_mckfd
    (offset_of!(Mckfd, next)) as CULong, // mckfd_next
    (offset_of!(Mckfd, fd)) as CULong, // mckfd_fd
    (offset_of!(Mckfd, data)) as CULong, // mckfd_data
    (offset_of!(FullMcPerfEvent, group_leader)) as CULong, // event_group_leader
    (offset_of!(FullMcPerfEvent, sibling_list)) as CULong, // event_sibling_list
    (offset_of!(FullMcPerfEvent, group_entry)) as CULong, // event_group_entry
    (offset_of!(FullMcPerfEvent, nr_siblings)) as CULong, // event_nr_siblings
    (offset_of!(FullMcPerfEvent, pmc_status)) as CULong, // event_pmc_status
    (offset_of!(Thread, pmc_alloc_map)) as CULong, // thread_pmc_alloc_map
    (offset_of!(Process, mckfd_lock)) as CULong, // proc_mckfd_lock
    (offset_of!(Mckfd, padding)) as CULong, // mckfd_sig_no
    (offset_of!(Mckfd, read_cb)) as CULong, // mckfd_read_cb
    (offset_of!(Mckfd, ioctl_cb)) as CULong, // mckfd_ioctl_cb
    (offset_of!(Mckfd, mmap_cb)) as CULong, // mckfd_mmap_cb
    (offset_of!(Mckfd, close_cb)) as CULong, // mckfd_close_cb
    (offset_of!(Mckfd, fcntl_cb)) as CULong, // mckfd_fcntl_cb
];
const _: () = { assert!(size_of::<[CULong; 31]>() == 248); };
const _: SyscallCopyFromUserFn = syscall_copy_from_user_bridge; // copy_from
const _: PerfAttrFreqFn = f03_perf_attr_frequency_v1; // attr_freq
const _: PerfOpenAllocEventFn = f03_perf_event_allocate_v1; // event_alloc
const _: PerfCounterAllocFn = perf_entry_counter_alloc_or_release; // counter_alloc
const _: PerfOpenSyscallFn = perf_event_open_do_syscall_bridge; // syscall
const _: SyscallPolicyAllocFn = perf_event_alloc_kmalloc_bridge; // allocate
const _: SyscallMckfdLongFn = f03_perf_read_v1; // read
const _: SyscallMckfdIntFn = f03_perf_ioctl_v1; // ioctl
const _: SyscallMckfdLongFn = f03_perf_mmap_v1; // mmap
const _: SyscallMckfdIntFn = f03_perf_close_v1; // close
const _: SyscallMckfdIntFn = f03_perf_fcntl_v1; // fcntl
const _: SyscallMckfdLockFn = syscall_mckfd_lock_bridge; // lock
const _: SyscallMckfdUnlockFn = syscall_mckfd_unlock_bridge; // unlock
const _: unsafe extern "C" fn(CInt, *mut X86UserContext) -> CLong = sys_perf_event_open;
