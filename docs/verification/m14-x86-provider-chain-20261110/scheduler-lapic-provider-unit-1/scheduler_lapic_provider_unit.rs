#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

mod x86_cpu_helpers {
use crate::abi::CInt;

type CUInt = u32;

const EINVAL: CInt = 22;
const LAPIC_TIMER: CInt = 0x320;
const LAPIC_TIMER_INITIAL: CInt = 0x380;
const LAPIC_TIMER_DIVIDE: CInt = 0x3e0;
const LOCAL_TIMER_VECTOR: CUInt = 0xef;
const APIC_DIVISOR: CUInt = 16;
const APIC_LVT_TIMER_PERIODIC: CUInt = 1 << 17;

type X86LapicWriteFn = unsafe extern "C" fn(CInt, CUInt);

unsafe extern "C" {
    fn x86_lapic_write_bridge(reg: CInt, value: CUInt);
}

#[no_mangle]
pub unsafe extern "C" fn x86_lapic_timer_enable_body_result(
    clocks: CUInt,
    write_fn: Option<X86LapicWriteFn>,
) -> CInt {
    let Some(write) = write_fn else {
        return -EINVAL;
    };

    write(LAPIC_TIMER_INITIAL, clocks / APIC_DIVISOR);
    write(LAPIC_TIMER_DIVIDE, 3);
    write(LAPIC_TIMER, LOCAL_TIMER_VECTOR | APIC_LVT_TIMER_PERIODIC);
    0
}

#[no_mangle]
pub unsafe extern "C" fn lapic_timer_enable(clocks: CUInt) {
    let _ = x86_lapic_timer_enable_body_result(clocks, Some(x86_lapic_write_bridge));
}

#[no_mangle]
pub unsafe extern "C" fn x86_lapic_timer_disable_body_result(
    write_fn: Option<X86LapicWriteFn>,
) -> CInt {
    let Some(write) = write_fn else {
        return -EINVAL;
    };

    write(LAPIC_TIMER_INITIAL, 0);
    0
}

#[no_mangle]
pub unsafe extern "C" fn lapic_timer_disable() {
    let _ = x86_lapic_timer_disable_body_result(Some(x86_lapic_write_bridge));
}

mod remaining_cpu_callbacks {
    use crate::abi::CInt;
    use core::ptr::addr_of;

    unsafe extern "C" {
        static mut lapic_write: Option<unsafe extern "C" fn(CInt, u32)>;
    }

    /// Call the same selected LAPIC write target.
    ///
    /// # Safety
    /// The live boot-selected callback and mapped controller must remain owned
    /// through the call; preserve its original MMIO/MSR and interrupt contract.
    #[no_mangle]
    pub unsafe extern "C" fn x86_lapic_write_bridge(register: CInt, value: u32) {
    unsafe { addr_of!(lapic_write).read().unwrap_unchecked()(register, value); }
    }
}

mod dispatch_and_msr_entries {
    use crate::abi::CInt;

    type WriteRegister = unsafe extern "C" fn(CInt, u32);

    #[no_mangle]
    pub(crate) static mut lapic_write: Option<WriteRegister> = None;

    const _: () = {
        assert!(core::mem::size_of::<Option<WriteRegister>>() == 8);
        assert!(core::mem::align_of::<Option<WriteRegister>>() == 8);
    };
}
}
