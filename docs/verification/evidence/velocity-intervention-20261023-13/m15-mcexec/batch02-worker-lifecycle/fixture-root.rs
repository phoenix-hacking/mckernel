// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Existing Rust orchestration and ABI below extracted verbatim from reference.
#![no_std]
use core::ffi::{c_int,c_void};
const ENOMEM: c_int=12;
unsafe extern "C" {
 #[link_name="thread_data"] static mut MCEXEC_THREAD_DATA:*mut McexecThreadData;
 #[link_name="n_threads"] static mut MCEXEC_N_THREADS:c_int;
 fn malloc(size:usize)->*mut u8;
 fn mcexec_main_loop_thread_func_body(arg:*mut c_void)->*mut c_void;
    fn mcexec_create_worker_thread_alloc_bridge() -> *mut McexecThreadData;
    fn mcexec_create_worker_thread_alloc_error_bridge();
    fn mcexec_create_worker_thread_next_cpu_bridge() -> c_int;
    fn mcexec_create_worker_thread_lock_bridge() -> *mut c_void;
    fn mcexec_create_worker_thread_publish_bridge(
        tp: *mut McexecThreadData,
        tp_out: *mut *mut McexecThreadData,
    );
    fn mcexec_create_worker_thread_pthread_create_bridge(tp: *mut McexecThreadData) -> c_int;
    fn mcexec_main_loop_thread_barrier_wait_bridge(barrier: *mut c_void) -> c_int;
    fn mcexec_init_worker_threads_lock_init_bridge();
    fn mcexec_init_worker_threads_barrier_init_bridge(count: c_int);
    fn mcexec_init_worker_threads_reset_cpuid_bridge();
    fn mcexec_init_worker_threads_create_bridge() -> c_int;
    fn mcexec_init_worker_threads_wait_bridge();
    fn mcexec_init_worker_threads_error_bridge(ret: c_int);
    fn mcexec_join_all_threads_head_bridge() -> *mut McexecThreadData;
    fn mcexec_join_all_threads_join_bridge(tp: *mut McexecThreadData);
    fn mcexec_kill_thread_head_bridge() -> *mut McexecThreadData;
    fn mcexec_kill_thread_pthread_kill_bridge(tp: *mut McexecThreadData, sig: c_int) -> c_int;
    fn mcexec_util_thread_barrier_init_bridge();
    fn mcexec_util_thread_create_worker_bridge(tp_out: *mut *mut McexecThreadData) -> c_int;
    fn mcexec_util_thread_worker_error_bridge(rc: c_int);
    fn mcexec_util_thread_barrier_wait_bridge();
}
#[repr(C)]
pub struct McexecThreadData {
    next: *mut McexecThreadData,
    thread_id: usize,
    cpu: i32,
    ret: i32,
    tid: i32,
    terminate: i32,
    remote_tid: i32,
    remote_cpu: i32,
    joined: i32,
    detached: i32,
    lock: *mut u8,
    init_ready: *mut u8,
}


#[no_mangle]
pub unsafe extern "C" fn mcexec_create_worker_thread_body(
    tp_out: *mut *mut McexecThreadData,
    init_ready: *mut c_void,
) -> c_int {
    let tp = unsafe { mcexec_create_worker_thread_alloc_bridge() };
    if tp.is_null() {
        unsafe { mcexec_create_worker_thread_alloc_error_bridge() };
        return ENOMEM;
    }

    unsafe {
        core::ptr::write_bytes(tp, 0, 1);
        (*tp).cpu = mcexec_create_worker_thread_next_cpu_bridge();
        (*tp).lock = mcexec_create_worker_thread_lock_bridge() as *mut u8;
        (*tp).init_ready = init_ready as *mut u8;
        (*tp).terminate = 0;
        mcexec_create_worker_thread_publish_bridge(tp, tp_out);
        mcexec_create_worker_thread_pthread_create_bridge(tp)
    }
}

#[no_mangle]
pub unsafe extern "C" fn init_worker_threads(_fd: c_int) -> c_int {
    let thread_count = unsafe { MCEXEC_N_THREADS };

    unsafe {
        mcexec_init_worker_threads_lock_init_bridge();
        mcexec_init_worker_threads_barrier_init_bridge(thread_count + 2);
        mcexec_init_worker_threads_reset_cpuid_bridge();
    }

    let mut i: c_int = 0;
    while i <= thread_count {
        let ret = unsafe { mcexec_init_worker_threads_create_bridge() };
        if ret != 0 {
            unsafe { mcexec_init_worker_threads_error_bridge(ret) };
            return -ret;
        }
        i += 1;
    }

    unsafe { mcexec_init_worker_threads_wait_bridge() };
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_join_all_threads_body() {
    loop {
        let mut live_thread = 0;
        let mut tp = unsafe { mcexec_join_all_threads_head_bridge() };

        while !tp.is_null() {
            if unsafe { (*tp).joined != 0 || (*tp).detached != 0 } {
                tp = unsafe { (*tp).next };
                continue;
            }

            live_thread = 1;
            unsafe {
                mcexec_join_all_threads_join_bridge(tp);
                (*tp).joined = 1;
                tp = (*tp).next;
            }
        }

        if live_thread == 0 {
            break;
        }
    }
}
#[cfg(mcexec_worker_candidate)]
#[path="mcexec_worker_lifecycle.rs"]
mod mcexec_worker_lifecycle;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! { loop {} }
