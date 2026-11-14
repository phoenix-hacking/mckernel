// Added only after exact actual production function bodies in the projection.
// HOST lower endpoints are explicit; none grants a perf lifetime/reference.
use crate::platform_bindings as platform;
pub unsafe extern "C" fn do_syscall(request:*mut SyscallRequest,cpu:CInt)->CLong{unsafe{crate::host_effects::host_reply(request,cpu)}}
pub unsafe extern "C" fn syscall_copy_from_user_bridge(destination:*mut u8,source:CULong,size:SizeT)->CLong{
 crate::host_effects::assert_effects_unlocked("copy_from_user");
 assert!(!destination.is_null()&&source!=0);unsafe{core::ptr::copy_nonoverlapping(source as *const u8,destination,size)};0
}
pub unsafe extern "C" fn syscall_copy_to_user_bridge(destination:CULong,source:*const u8,size:SizeT)->CLong{
 crate::host_effects::assert_effects_unlocked("copy_to_user");
 assert!(destination!=0&&!source.is_null());unsafe{core::ptr::copy_nonoverlapping(source,destination as *mut u8,size)};0
}
