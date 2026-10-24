// Fixture binding to genuine Rust allocator bodies. No alternative allocator.
// Single-CPU, MEMDEBUG=NULL valid arena only. Physical page growth and remote
// frees HOLD; alloc_pages endpoint is a controlled exhausted-page result.
use core::ffi::c_void;
unsafe extern "C" {
 fn fixture_cpu()->*mut abi::CpuLocalVar;
 fn fixture_arena()->*mut c_void;
 fn fixture_fail_alloc()->CInt;
 fn cpu_disable_interrupt_save()->CULong;
 fn cpu_restore_interrupt(flags:CULong);
 fn fixture_provider_error();
}
#[no_mangle] static mut memdebug:*mut i8=core::ptr::null_mut();
#[no_mangle] static mut kmalloc_track_hash:[AbiListHead;256]=unsafe{core::mem::zeroed()};
#[no_mangle] static mut kmalloc_addr_hash:[AbiListHead;256]=unsafe{core::mem::zeroed()};
#[no_mangle] static mut kmalloc_track_hash_locks:[abi::IhkSpinlock;256]=unsafe{core::mem::zeroed()};
#[no_mangle] static mut kmalloc_addr_hash_locks:[abi::IhkSpinlock;256]=unsafe{core::mem::zeroed()};
#[no_mangle] static mut kmalloc_runcount:CInt=0;
unsafe extern "C" fn pages_exhausted(_:CInt,_:CULong,_:CInt)->*mut c_void {null_mut()}
unsafe extern "C" fn remote_cpu(_:CInt)->*mut c_void {fixture_provider_error();null_mut()}
unsafe extern "C" fn corrupt(_: *mut c_void){fixture_provider_error();}
#[no_mangle] pub unsafe extern "C" fn get_this_cpu_local_var()->*mut abi::CpuLocalVar{fixture_cpu()}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_base_alloc_bridge(n:CInt,f:CULong)->*mut c_void{
 if fixture_fail_alloc()!=0 {return null_mut();}
 mem_helpers::___kmalloc_body_result(n,f,&raw mut (*fixture_cpu()).free_list,Some(cpu_disable_interrupt_save),Some(cpu_restore_interrupt),Some(pages_exhausted))
}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_base_free_bridge(p:*mut c_void){
 let rc=mem_helpers::___kfree_body_result(p,&raw mut (*fixture_cpu()).free_list,offset_of!(abi::CpuLocalVar,remote_free_list_lock) as CULong,offset_of!(abi::CpuLocalVar,remote_free_list) as CULong,Some(cpu_disable_interrupt_save),Some(cpu_restore_interrupt),Some(remote_cpu),Some(mem_kmalloc_track_lock_bridge),Some(mem_kmalloc_track_unlock_bridge),Some(corrupt));if rc!=0{fixture_provider_error();}
}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_lock_bridge(l:CULong)->CULong{spinlock_helpers::__ihk_mc_spinlock_lock(l as *mut spinlock_helpers::IhkSpinlock)}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_unlock_bridge(l:CULong,f:CULong){spinlock_helpers::__ihk_mc_spinlock_unlock(l as *mut spinlock_helpers::IhkSpinlock,f)}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_spin_init_bridge(l:CULong){spinlock_helpers::ihk_mc_spinlock_init(l as *mut spinlock_helpers::IhkSpinlock)}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_log_bridge(_:CInt,_:*mut c_void,_:*mut i8,_:CInt,_:CInt){fixture_provider_error();}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_invalid_free_bridge(_:*mut c_void,_:*mut i8,_:CInt){fixture_provider_error();}
#[no_mangle] pub unsafe extern "C" fn fixture_reset_genuine_arena(){
 let h=&raw mut (*fixture_cpu()).free_list;(*h).next=h;(*h).prev=h;
 let c=fixture_arena().cast::<abi::KmallocHeader>();mem_helpers::___kmalloc_init_chunk_result(c,(65536-size_of::<abi::KmallocHeader>()) as CInt);mem_helpers::___kmalloc_insert_chunk_result(h,c);
}
