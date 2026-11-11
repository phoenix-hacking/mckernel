// HOST-only platform effects. No actual owner/gate/group/lease body lives here.
use crate::abi::*;
use core::ffi::c_void;
use core::sync::atomic::{AtomicUsize,Ordering};
pub static SCHEDULE_CALLS:AtomicUsize=AtomicUsize::new(0);
fn refused(name:&str)->! { eprintln!("UNSUPPORTED_HOST_PLATFORM_PATH:{name}"); std::process::abort() }
#[no_mangle]
pub unsafe extern "C" fn schedule(){SCHEDULE_CALLS.fetch_add(1,Ordering::SeqCst);refused("actual kernel scheduler was requested");}
#[no_mangle]
pub unsafe extern "C" fn get_cpu_local_var_result(id:CInt)->*mut CpuLocalVar {assert_eq!(id,0);unsafe{crate::host_effects::cls::get_this_cpu_local_var()}}
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_get_processor_id()->CInt{0}
#[no_mangle]
pub unsafe extern "C" fn sched_wakeup_thread(_thread:*mut c_void,_states:CInt)->CInt{refused("unexpected real waitq wake target");}
#[no_mangle]
pub unsafe extern "C" fn sched_wakeup_thread_locked(_thread:*mut c_void,_states:CInt)->CInt{refused("unexpected real locked waitq wake target");}
// Exact retained C metadata bytes from the already-qualified 6aae C object.
#[no_mangle] pub static f03_mckfd_alloc_origin_file_v1:[u8;22]=*b"/src/kernel/syscall.c\0";
#[no_mangle] pub static f03_mckfd_free_origin_file_v1:[u8;22]=*b"/src/kernel/syscall.c\0";
#[no_mangle] pub static f03_mckfd_alloc_origin_line_v1:CInt=20206;
#[no_mangle] pub static f03_mckfd_free_origin_line_v1:CInt=20218;

// Refusal callbacks close unchanged release-body type/link closure. Each target
// case keeps a genuine base owner. Reaching its final destruction is a test
// failure, never a fake successful destructor or rewritten refcount decision.
pub unsafe extern "C" fn refused_current_resource()->*mut c_void{refused("final Process resource lookup")}
pub unsafe extern "C" fn refused_pair(_a:*mut c_void,_b:*mut c_void){refused("final Process pair action")}
pub unsafe extern "C" fn refused_action(_a:*mut c_void){refused("unexpected final destruction action")}
pub unsafe extern "C" fn refused_detach(_a:*mut c_void,_pid:CInt){refused("unexpected address-space detach")}
pub unsafe extern "C" fn refused_lock(_a:CULong)->CULong{refused("unexpected final Process lock")}
pub unsafe extern "C" fn refused_unlock(_a:CULong,_f:CULong){refused("unexpected final Process unlock")}
// Only used by the unchanged F02/RB final-destruction closure. Those paths are
// outside these retained-base-owner cases; they may never get fake physical
// validation or a successful virtual-to-physical mapping in HOST.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_chk_page_address(_address:CULong)->CInt{refused("unexpected kernel physical-page validation")}
#[no_mangle]
pub unsafe extern "C" fn virt_to_phys(_address:*mut c_void)->CULong{refused("unexpected kernel virtual-to-physical translation")}
