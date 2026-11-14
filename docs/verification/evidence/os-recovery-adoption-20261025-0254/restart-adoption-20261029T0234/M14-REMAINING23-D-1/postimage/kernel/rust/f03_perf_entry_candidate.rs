//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Default-off entry binding to the existing Rust perf body and C metadata.
use core::{ffi::c_void, mem::{size_of, MaybeUninit}};
use crate::abi::{CInt, CLong, CULong, SyscallRequest, X86UserContext};
use crate::f03_perf_attr_callbacks::PerfEventAttr;
use crate::x86_cpu_helpers::{ihk_mc_syscall_arg0, ihk_mc_syscall_arg1, ihk_mc_syscall_arg2, ihk_mc_syscall_arg3, ihk_mc_syscall_arg4};
use super::{PerfAttrFreqFn,PerfCounterAllocFn,PerfOpenAllocEventFn,PerfOpenSyscallFn,SyscallCopyFromUserFn,SyscallMckfdIntFn,SyscallMckfdLockFn,SyscallMckfdLongFn,SyscallMckfdUnlockFn,SyscallPolicyAllocFn};
#[repr(C)]
struct PerfEntryBinding {
    attr_size: CULong,
    attr_type: CULong,
    attr_read_format: CULong,
    attr_sample_period: CULong,
    raw_type: CULong,
    hardware_type: CULong,
    cache_type: CULong,
    unsupported_format: CULong,
    sign_bit: CULong,
    syscall_number: CULong,
    mckfd_size: CULong,
    allocation_flags: CULong,
    event_pid: CULong,
    event_counter_id: CULong,
    proc_mckfd: CULong,
    mckfd_next: CULong,
    mckfd_fd: CULong,
    mckfd_data: CULong,
    event_group_leader: CULong,
    event_sibling_list: CULong,
    event_group_entry: CULong,
    event_nr_siblings: CULong,
    event_pmc_status: CULong,
    thread_pmc_alloc_map: CULong,
    proc_mckfd_lock: CULong,
    mckfd_sig_no: CULong,
    mckfd_read_cb: CULong,
    mckfd_ioctl_cb: CULong,
    mckfd_mmap_cb: CULong,
    mckfd_close_cb: CULong,
    mckfd_fcntl_cb: CULong,
    copy_from: Option<SyscallCopyFromUserFn>,
    attr_freq: Option<PerfAttrFreqFn>,
    event_alloc: Option<PerfOpenAllocEventFn>,
    counter_alloc: Option<PerfCounterAllocFn>,
    syscall: Option<PerfOpenSyscallFn>,
    allocate: Option<SyscallPolicyAllocFn>,
    read: Option<SyscallMckfdLongFn>,
    ioctl: Option<SyscallMckfdIntFn>,
    mmap: Option<SyscallMckfdLongFn>,
    close: Option<SyscallMckfdIntFn>,
    fcntl: Option<SyscallMckfdIntFn>,
    lock: Option<SyscallMckfdLockFn>,
    unlock: Option<SyscallMckfdUnlockFn>,
}
unsafe extern "C" { static f03_perf_entry_binding_v1: PerfEntryBinding; }
const _: () = { assert!(size_of::<CULong>() == 8 && size_of::<usize>() == 8); };
/// Reuse the original perf entry provider, field and callback bindings.
///
/// # Safety
/// The caller supplies the original live syscall context and current thread,
/// process, perf, VM and endpoint lifetimes. Existing perf and request helper
/// contracts, publication/cleanup and all unreleased holds remain unchanged.
#[no_mangle]
pub unsafe extern "C" fn sys_perf_event_open(_number: CInt, ctx: *mut X86UserContext) -> CLong {
    // No whole reference to either uninitialized stack object is formed.
    let mut request = MaybeUninit::<SyscallRequest>::uninit();
    let mut attr = MaybeUninit::<PerfEventAttr>::uninit();
    // SAFETY: Identical current CPU/thread/process and context prerequisites as C.
    let thread = unsafe { (*super::get_this_cpu_local_var()).current };
    let proc = unsafe { (*thread).proc };
    let arg0 = unsafe { ihk_mc_syscall_arg0(ctx) };
    let pid = unsafe { ihk_mc_syscall_arg1(ctx) } as CInt;
    let cpu = unsafe { ihk_mc_syscall_arg2(ctx) } as CInt;
    let group_fd = unsafe { ihk_mc_syscall_arg3(ctx) } as CInt;
    let flags = unsafe { ihk_mc_syscall_arg4(ctx) };
    let linux_cpu = unsafe { super::ihk_mc_get_processor_id() };
    // SAFETY: Read-only C binding captures the original values and exact provider
    // addresses. The existing body retains all initialisation and ownership rules.
    let b = unsafe { &f03_perf_entry_binding_v1 };
    unsafe { super::perf_event_open_entry_body_result(
        request.as_mut_ptr(), thread.cast::<c_void>(), proc.cast::<c_void>(),
        attr.as_mut_ptr().cast::<c_void>(), arg0,
        b.attr_size as usize, b.attr_type as usize, b.attr_read_format as usize,
        b.attr_sample_period as usize, pid, cpu, group_fd, flags, linux_cpu,
        b.raw_type, b.hardware_type, b.cache_type, b.unsupported_format,
        b.sign_bit, b.syscall_number as CInt, b.mckfd_size as usize, b.allocation_flags,
        b.event_pid as usize,
        b.event_counter_id as usize,
        b.proc_mckfd as usize,
        b.mckfd_next as usize,
        b.mckfd_fd as usize,
        b.mckfd_data as usize,
        b.event_group_leader as usize,
        b.event_sibling_list as usize,
        b.event_group_entry as usize,
        b.event_nr_siblings as usize,
        b.event_pmc_status as usize,
        b.thread_pmc_alloc_map as usize,
        b.proc_mckfd_lock as usize,
        b.mckfd_sig_no as usize,
        b.mckfd_read_cb as usize,
        b.mckfd_ioctl_cb as usize,
        b.mckfd_mmap_cb as usize,
        b.mckfd_close_cb as usize,
        b.mckfd_fcntl_cb as usize,
        b.copy_from,
        b.attr_freq,
        b.event_alloc,
        b.counter_alloc,
        b.syscall,
        b.allocate,
        b.read,
        b.ioctl,
        b.mmap,
        b.close,
        b.fcntl,
        b.lock,
        b.unlock,
    ) }
}
const _: unsafe extern "C" fn(CInt, *mut X86UserContext) -> CLong = sys_perf_event_open;
