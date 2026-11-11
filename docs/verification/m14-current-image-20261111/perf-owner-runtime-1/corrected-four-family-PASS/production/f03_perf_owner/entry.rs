// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PRIVATE UNSELECTED Rust entry, paired only with the new ordinary C guard.
// The original complete validation helper and all genuine provider identities
// are retained; the new real owner module replaces its open transaction only.
use core::ffi::c_void;
use core::mem::{size_of,align_of,offset_of,MaybeUninit};
use crate::abi::{CInt,CLong,CULong,Mckfd,Process,Thread,SyscallRequest,X86UserContext};
use crate::f03_perf_attr_callbacks::PerfEventAttr;
use super::super::f03_sync_child_layout_v2::FullMcPerfEvent as Event;
unsafe extern "C"{static f03_perf_owner_entry_constants_v1:[CULong;12];}
unsafe extern "C" fn frequency(attribute:*const c_void)->CInt{unsafe{(*attribute.cast::<PerfEventAttr>()).frequency()}}
unsafe extern "C" fn read(fd:*mut c_void,ctx:*mut c_void)->CLong{unsafe{super::callbacks::read(fd.cast(),ctx.cast())}}
unsafe extern "C" fn ioctl(fd:*mut c_void,ctx:*mut c_void)->CInt{unsafe{super::callbacks::ioctl(fd.cast(),ctx.cast())}}
unsafe extern "C" fn mmap(fd:*mut c_void,ctx:*mut c_void)->CLong{unsafe{super::super::f03_perf_mmap_entry_v1::f03_perf_mmap_v1(fd.cast(),ctx.cast())}}
unsafe extern "C" fn close(fd:*mut c_void,_ctx:*mut c_void)->CInt{match unsafe{super::descriptors::close_callback_mark(fd.cast())}{Ok(())=>0,Err(error)=>error}}
unsafe extern "C" fn fcntl(fd:*mut c_void,ctx:*mut c_void)->CInt{unsafe{super::callbacks::fcntl(fd.cast(),ctx.cast())}}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_do_syscall_bridge(request:*mut SyscallRequest,cpu:CInt)->CLong{unsafe{super::super::do_syscall(request,cpu)}}
#[no_mangle]
pub unsafe extern "C" fn sys_perf_event_open(_number:CInt,ctx:*mut X86UserContext)->CLong{
    let constants=unsafe{f03_perf_owner_entry_constants_v1};
    if constants[0]!=size_of::<PerfEventAttr>() as CULong||constants[1]!=size_of::<Mckfd>() as CULong
        ||constants[2]!=size_of::<Event>() as CULong||constants[3]!=align_of::<Event>() as CULong
        ||constants[11]!=10{return -22;}
    let cpu=unsafe{crate::cls::get_this_cpu_local_var()};let thread=unsafe{(*cpu).current};let process=unsafe{(*thread).proc};
    let user_attribute=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg0(ctx)};
    let pid=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx)} as CInt;
    let requested_cpu=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx)} as CInt;
    let group=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg3(ctx)} as CInt;
    let flags=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg4(ctx)};
    let mut request=MaybeUninit::<SyscallRequest>::zeroed();let mut attribute=MaybeUninit::<PerfEventAttr>::uninit();
    unsafe{super::super::perf_event_open_entry_body_result(
        request.as_mut_ptr(),thread.cast(),process.cast(),attribute.as_mut_ptr().cast(),user_attribute,
        size_of::<PerfEventAttr>(),offset_of!(PerfEventAttr,type_),offset_of!(PerfEventAttr,read_format),offset_of!(PerfEventAttr,sampling),
        pid,requested_cpu,group,flags,crate::x86_local::ihk_mc_get_processor_id(),
        constants[4],constants[5],constants[6],constants[7],constants[8],constants[9] as CInt,
        size_of::<Mckfd>(),constants[10],offset_of!(Event,pid),offset_of!(Event,counter_id),offset_of!(Process,mckfd),
        offset_of!(Mckfd,next),offset_of!(Mckfd,fd),offset_of!(Mckfd,data),offset_of!(Event,group_leader),
        offset_of!(Event,sibling_list),offset_of!(Event,group_entry),offset_of!(Event,nr_siblings),offset_of!(Event,pmc_status),
        offset_of!(Thread,pmc_alloc_map),offset_of!(Process,mckfd_lock),offset_of!(Mckfd,padding),
        offset_of!(Mckfd,read_cb),offset_of!(Mckfd,ioctl_cb),offset_of!(Mckfd,mmap_cb),offset_of!(Mckfd,close_cb),offset_of!(Mckfd,fcntl_cb),
        Some(super::super::syscall_copy_from_user_bridge),Some(frequency),
        Some(super::super::f03_perf_alloc_entry_v1::f03_perf_event_allocate_v1),
        Some(super::super::f03_perf_counter_allocate_v1::f03_perf_counter_allocate_v1),
        Some(perf_event_open_do_syscall_bridge),Some(super::super::perf_event_alloc_kmalloc_bridge),
        Some(read),Some(ioctl),Some(mmap),Some(close),Some(fcntl),
        Some(super::super::syscall_mckfd_lock_bridge),Some(super::super::syscall_mckfd_unlock_bridge))}
}
const _:unsafe extern "C" fn(CInt,*mut X86UserContext)->CLong=sys_perf_event_open;
const _:unsafe extern "C" fn(*mut SyscallRequest,CInt)->CLong=perf_event_open_do_syscall_bridge;
const _:()={assert!(size_of::<Mckfd>()==80&&size_of::<SyscallRequest>()==72&&align_of::<SyscallRequest>()==8);};

// HOST fixture obtains the actual five entry callbacks without replacing bodies.
pub(super) fn host_callbacks()->(super::super::SyscallMckfdLongFn,super::super::SyscallMckfdIntFn,super::super::SyscallMckfdLongFn,super::super::SyscallMckfdIntFn,super::super::SyscallMckfdIntFn){(read,ioctl,mmap,close,fcntl)}
