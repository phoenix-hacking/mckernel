// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Remaining worker callbacks use libc/pthread directly; existing Rust owns sequencing.
use super::{c_int,c_void,McexecThreadData};
use core::ptr::{addr_of_mut,null_mut};
static mut NEXT_CPU: c_int = 0;
unsafe extern "C" {
    static mut lock: c_void;
    static mut init_ready: c_void;
    static mut uti_init_ready: c_void;
    static mut stderr: *mut c_void;
    fn pthread_mutex_init(lock: *mut c_void, attr: *const c_void) -> c_int;
    fn pthread_barrier_init(barrier: *mut c_void, attr: *const c_void, count: u32) -> c_int;
    fn pthread_barrier_wait(barrier: *mut c_void) -> c_int;
    fn pthread_create(thread: *mut usize, attr: *const c_void,
        entry: unsafe extern "C" fn(*mut c_void)->*mut c_void, arg:*mut c_void) -> c_int;
    fn pthread_join(thread: usize, value: *mut *mut c_void) -> c_int;
    fn pthread_kill(thread: usize, sig: c_int) -> c_int;
    fn fprintf(stream: *mut c_void, format: *const u8, ...) -> c_int;
    fn printf(format: *const u8, ...) -> c_int;
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_create_worker_thread_alloc_bridge() -> *mut McexecThreadData {
    super::malloc(core::mem::size_of::<McexecThreadData>()).cast()
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_create_worker_thread_alloc_error_bridge() {
    fprintf(stderr,b"create_worker_thread: error: allocating thread structure\n\0".as_ptr());
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_create_worker_thread_next_cpu_bridge() -> c_int {
    let current = NEXT_CPU;
    // Inputs in supported execution cannot exhaust int; preserve postincrement ordering.
    NEXT_CPU = current.wrapping_add(1);
    current
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_create_worker_thread_lock_bridge() -> *mut c_void { addr_of_mut!(lock) }
#[no_mangle]
pub unsafe extern "C" fn mcexec_create_worker_thread_publish_bridge(tp:*mut McexecThreadData,out:*mut *mut McexecThreadData) {
    (*tp).next = super::MCEXEC_THREAD_DATA;
    super::MCEXEC_THREAD_DATA = tp;
    if !out.is_null() { *out=tp; }
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_create_worker_thread_pthread_create_bridge(tp:*mut McexecThreadData)->c_int {
    pthread_create(addr_of_mut!((*tp).thread_id),core::ptr::null(),super::mcexec_main_loop_thread_func_body,tp.cast())
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_main_loop_thread_barrier_wait_bridge(barrier:*mut c_void)->c_int { pthread_barrier_wait(barrier) }
#[no_mangle]
pub unsafe extern "C" fn mcexec_init_worker_threads_lock_init_bridge() { pthread_mutex_init(addr_of_mut!(lock),core::ptr::null()); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_init_worker_threads_barrier_init_bridge(count:c_int) {
    pthread_barrier_init(addr_of_mut!(init_ready),core::ptr::null(),count as u32);
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_init_worker_threads_reset_cpuid_bridge() { NEXT_CPU=0; }
#[no_mangle]
pub unsafe extern "C" fn mcexec_init_worker_threads_create_bridge()->c_int {
    super::mcexec_create_worker_thread_body(null_mut(),addr_of_mut!(init_ready))
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_init_worker_threads_wait_bridge() { pthread_barrier_wait(addr_of_mut!(init_ready)); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_init_worker_threads_error_bridge(ret:c_int) {
    printf(b"ERROR: creating worker threads (%d), check ulimit?\n\0".as_ptr(),ret);
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_join_all_threads_head_bridge()->*mut McexecThreadData { super::MCEXEC_THREAD_DATA }
#[no_mangle]
pub unsafe extern "C" fn mcexec_join_all_threads_join_bridge(tp:*mut McexecThreadData) { pthread_join((*tp).thread_id,null_mut()); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_kill_thread_head_bridge()->*mut McexecThreadData { super::MCEXEC_THREAD_DATA }
#[no_mangle]
pub unsafe extern "C" fn mcexec_kill_thread_pthread_kill_bridge(tp:*mut McexecThreadData,sig:c_int)->c_int { pthread_kill((*tp).thread_id,sig) }
#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_barrier_init_bridge() { pthread_barrier_init(addr_of_mut!(uti_init_ready),core::ptr::null(),2); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_create_worker_bridge(out:*mut *mut McexecThreadData)->c_int { super::mcexec_create_worker_thread_body(out,addr_of_mut!(uti_init_ready)) }
#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_worker_error_bridge(rc:c_int) { printf(b"util_thread: Error: create_worker_thread failed (%d)\n\0".as_ptr(),rc); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_barrier_wait_bridge() { pthread_barrier_wait(addr_of_mut!(uti_init_ready)); }

#[cfg(mcexec_worker_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_worker_fixture_abi(out:*mut usize) {
 let values=[core::mem::size_of::<McexecThreadData>(),core::mem::align_of::<McexecThreadData>(),
 core::mem::offset_of!(McexecThreadData,thread_id),core::mem::offset_of!(McexecThreadData,cpu),
 core::mem::offset_of!(McexecThreadData,lock),core::mem::offset_of!(McexecThreadData,init_ready)];
 core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
