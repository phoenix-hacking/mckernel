// Actual full release bodies above decide the genuine reference lifecycle.
// The finite actors keep a base owner, so final destructor callbacks refuse.
use crate::platform_bindings as platform;
pub unsafe extern "C" fn find_process(pid:CInt,node:*mut crate::lock_helpers::McsRwlockNodeIrqsave)->*mut Process{
 unsafe{crate::host_effects::find_process(pid,node.cast()).cast()}
}
pub unsafe extern "C" fn process_unlock(process:*mut Process,node:*mut crate::lock_helpers::McsRwlockNodeIrqsave){
 unsafe{crate::host_effects::unlock_process(process.cast(),node.cast())}
}
pub unsafe extern "C" fn release_process(process:*mut Process){
 crate::host_effects::assert_effects_unlocked("release_process");
 crate::host_effects::marker("actual_release_process_body");
 let result=unsafe{process_release_process_body_result(process.cast(),offset_of!(Process,refcount) as CULong,
 offset_of!(Process,tids) as CULong,offset_of!(Process,main_thread) as CULong,
 offset_of!(Process,mckfd) as CULong,offset_of!(Process,mckfd_lock) as CULong,offset_of!(Mckfd,next) as CULong,
 None,Some(platform::refused_current_resource),Some(platform::refused_pair),Some(platform::refused_action),None,
 Some(platform::refused_action),Some(platform::refused_lock),Some(platform::refused_unlock),
 Some(platform::refused_action),Some(platform::refused_action),Some(platform::refused_action))};
 assert_eq!(result,0,"finite positive remote edge must not destroy its base owner");
}
pub unsafe extern "C" fn release_process_vm(vm:*mut ProcessVm){
 crate::host_effects::assert_effects_unlocked("release_process_vm");
 crate::host_effects::marker("actual_release_process_vm_body");
 let result=unsafe{process_release_vm_body_result(vm.cast(),offset_of!(ProcessVm,refcount) as CULong,
 offset_of!(ProcessVm,proc) as CULong,offset_of!(Process,mckfd) as CULong,offset_of!(Process,mckfd_lock) as CULong,
 offset_of!(Mckfd,next) as CULong,offset_of!(Mckfd,close_cb) as CULong,offset_of!(ProcessVm,free_cb) as CULong,
 offset_of!(ProcessVm,opt) as CULong,offset_of!(ProcessVm,address_space) as CULong,offset_of!(Process,pid) as CULong,
 offset_of!(Process,vm) as CULong,offset_of!(ProcessVm,vm_range_numa_policy_tree) as CULong,
 offset_of!(VmRangeNumaPolicy,policy_rb_node) as CULong,None,
 Some(platform::refused_lock),Some(platform::refused_unlock),Some(platform::refused_action),Some(platform::refused_action),
 Some(platform::refused_detach),Some(platform::refused_action),Some(platform::refused_action),Some(platform::refused_action))};
 assert_eq!(result,0,"finite parent VM pin must release to its still-live base owner");
}
