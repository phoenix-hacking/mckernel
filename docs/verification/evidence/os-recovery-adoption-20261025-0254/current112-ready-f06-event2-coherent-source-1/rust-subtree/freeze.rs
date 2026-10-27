use core::ffi::c_void;

use crate::abi::{CInt, CULong, CpuLocalVar, IhkOsCpuMonitor};

const IHK_OS_MONITOR_KERNEL_FROZEN: CInt = 9;
const IHK_OS_MONITOR_KERNEL_THAW: CInt = 10;
const IHK_OS_MONITOR_ALLOW_THAW_REQUEST: CInt = 1 << 31;

extern "C" {
    static multi_intr_mode: CInt;

    fn ihk_mc_get_processor_id() -> CInt;
    fn get_cpu_local_var(id: CInt) -> *mut CpuLocalVar;
    fn cpu_enable_interrupt_save() -> CULong;
    fn cpu_restore_interrupt(flags: CULong);
    fn cpu_halt();
    fn cpu_pause();
    fn mod_nmi_ctx(ctx: *mut c_void, handler: unsafe extern "C" fn());
    fn __freeze();
}

#[inline(always)]
unsafe fn this_monitor() -> *mut IhkOsCpuMonitor {
    (*get_cpu_local_var(ihk_mc_get_processor_id())).monitor
}

#[no_mangle]
pub unsafe extern "C" fn freeze() {
    let monitor = this_monitor();

    if (*monitor).status_bak & IHK_OS_MONITOR_ALLOW_THAW_REQUEST != 0 {
        return;
    }

    (*monitor).status_bak = (*monitor).status | IHK_OS_MONITOR_ALLOW_THAW_REQUEST;
    (*monitor).status = IHK_OS_MONITOR_KERNEL_FROZEN;
    let flags = cpu_enable_interrupt_save();

    loop {
        while (*monitor).status == IHK_OS_MONITOR_KERNEL_FROZEN {
            cpu_halt();
            cpu_pause();
        }
        if (*monitor).status_bak == IHK_OS_MONITOR_KERNEL_THAW {
            break;
        }
        (*monitor).status = IHK_OS_MONITOR_KERNEL_FROZEN;
    }

    cpu_restore_interrupt(flags);
    (*monitor).status = (*monitor).status_bak;
}

#[no_mangle]
pub unsafe extern "C" fn freeze_thaw(nmi_ctx: *mut c_void) -> CULong {
    let monitor = this_monitor();

    if multi_intr_mode == 1 {
        if (*monitor).status != IHK_OS_MONITOR_KERNEL_FROZEN {
            mod_nmi_ctx(nmi_ctx, __freeze);
            return 1;
        }
    } else if multi_intr_mode == 2
        && ((*monitor).status_bak & IHK_OS_MONITOR_ALLOW_THAW_REQUEST) != 0
    {
        (*monitor).status = (*monitor).status_bak & !IHK_OS_MONITOR_ALLOW_THAW_REQUEST;
        (*monitor).status_bak = IHK_OS_MONITOR_KERNEL_THAW;
    }

    0
}
