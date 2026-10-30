use core::ffi::c_void;
use core::ptr::read_volatile;

use crate::abi::{CInt, CpuLocalVar};

const IHK_OS_MONITOR_PANIC: CInt = 99;
const IHK_OS_EVENTFD_TYPE_STATUS: CInt = 2;
const PANIC_FMT: &[u8; 4] = b"%s\n\0";

unsafe extern "C" {
    static mut clv: *mut CpuLocalVar;

    fn ihk_mc_get_processor_id() -> CInt;
    fn eventfd(type_: CInt);
    fn cpu_disable_interrupt();
    fn kprintf(format: *const i8, ...) -> CInt;
    fn arch_print_stack();
    fn arch_show_interrupt_context(reg: *const c_void);

    #[cfg(not(enable_fugaku_hacks))]
    fn arch_cpu_stop();
    #[cfg(not(enable_fugaku_hacks))]
    fn cpu_halt();

    #[cfg(enable_fugaku_hacks)]
    fn cpu_halt_panic();
}

#[inline(always)]
unsafe fn publish_panic_status() {
    let base = read_volatile(&raw const clv);

    if !base.is_null() {
        let cpu = ihk_mc_get_processor_id();
        let cpu_local = base.add(cpu as usize);
        (*(*cpu_local).monitor).status = IHK_OS_MONITOR_PANIC;
        eventfd(IHK_OS_EVENTFD_TYPE_STATUS);
    }
}

#[no_mangle]
pub unsafe extern "C" fn panic(msg: *const i8) -> ! {
    publish_panic_status();
    cpu_disable_interrupt();
    kprintf(PANIC_FMT.as_ptr().cast(), msg);
    arch_print_stack();

    #[cfg(not(enable_fugaku_hacks))]
    {
        arch_cpu_stop();
        loop {
            cpu_halt();
        }
    }

    #[cfg(enable_fugaku_hacks)]
    loop {
        cpu_halt_panic();
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_debug_show_interrupt_context(reg: *const c_void) {
    arch_show_interrupt_context(reg);
}
