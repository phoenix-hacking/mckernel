#![no_std]
use core::ptr::read_volatile;
type CInt=i32;
unsafe fn list_next(list_addr: usize) -> usize {
    unsafe { read_volatile(list_addr as *const usize) }
}
#[no_mangle]
pub unsafe extern "C" fn sched_idle_runqueue_has_running_result(
    runq_head: usize,
    thread_sched_list_offset: usize,
    thread_status_offset: usize,
    running_status: CInt,
) -> CInt {
    let mut entry = unsafe { list_next(runq_head) };
    while entry != runq_head {
        let thread = entry.wrapping_sub(thread_sched_list_offset);
        let status = unsafe {
            read_volatile(thread.wrapping_add(thread_status_offset) as *const CInt)
        };
        if status == running_status {
            return 1;
        }
        entry = unsafe { list_next(entry) };
    }
    0
}
