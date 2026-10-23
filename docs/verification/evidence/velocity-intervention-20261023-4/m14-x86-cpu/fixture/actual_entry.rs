// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
use core::ptr::read_volatile;
type CInt=i32;
type CULong=u64;
const EINVAL:CInt=22;
type X86RunningOnKvmFn=unsafe extern "C" fn()->CInt;
type X86Cpuid6Fn=unsafe extern "C" fn(*mut CULong,*mut CULong);
type X86ReadMsrRegFn=unsafe extern "C" fn(CInt)->CULong;
type X86WriteMsrRegFn=unsafe extern "C" fn(CInt,CULong);
const MSR_PLATFORM_INFO: CInt = 0xce;
const MSR_NHM_TURBO_RATIO_LIMIT: CInt = 0x1ad;
const MSR_IA32_PERF_CTL: CInt = 0x199;
const MSR_IA32_ENERGY_PERF_BIAS: CInt = 0x1b0;
extern "C" {
    #[link_name = "no_turbo"]
    static mut X86_NO_TURBO: CInt;
    fn x86_running_on_kvm_bridge() -> CInt;
    fn x86_cpuid6_bridge(eaxp: *mut CULong, ecxp: *mut CULong);
    fn x86_read_msr_bridge(reg:CInt)->CULong;
    fn x86_write_msr_bridge(reg:CInt,value:CULong);
}
#[no_mangle]
pub unsafe extern "C" fn x86_init_pstate_turbo_body_result(
    no_turbo: CInt,
    platform_info_msr: CInt,
    turbo_ratio_msr: CInt,
    perf_ctl_msr: CInt,
    energy_perf_bias_msr: CInt,
    running_on_kvm_fn: Option<X86RunningOnKvmFn>,
    cpuid6_fn: Option<X86Cpuid6Fn>,
    read_msr_fn: Option<X86ReadMsrRegFn>,
    write_msr_fn: Option<X86WriteMsrRegFn>,
) -> CInt {
    let (Some(running_on_kvm), Some(cpuid6), Some(read_msr), Some(write_msr)) =
        (running_on_kvm_fn, cpuid6_fn, read_msr_fn, write_msr_fn)
    else {
        return -EINVAL;
    };

    if running_on_kvm() != 0 {
        return 0;
    }

    let mut eax = 0;
    let mut ecx = 0;
    cpuid6(&mut eax, &mut ecx);
    if (ecx & 0x01) == 0 {
        return 0;
    }

    let mut value = read_msr(platform_info_msr) & 0xff00;
    if (eax & (1 << 1)) != 0 {
        if no_turbo == 0 {
            value = (read_msr(turbo_ratio_msr) & 0xff) << 8;
            value &= !(1 << 32);
        } else {
            value |= 1 << 32;
        }
    }

    write_msr(perf_ctl_msr, value);
    if (ecx & (1 << 3)) != 0 {
        write_msr(energy_perf_bias_msr, 0);
    }
    0
}
/// Preserve the selected x86 CPU initialization entry and its ordered MSR callbacks.
/// The boot CPU initializes `no_turbo` before entering this serialized setup path.
#[no_mangle]
pub unsafe extern "C" fn init_pstate_and_turbo() {
    let _ = unsafe {
        x86_init_pstate_turbo_body_result(
            read_volatile(core::ptr::addr_of!(X86_NO_TURBO)),
            MSR_PLATFORM_INFO,
            MSR_NHM_TURBO_RATIO_LIMIT,
            MSR_IA32_PERF_CTL,
            MSR_IA32_ENERGY_PERF_BIAS,
            Some(x86_running_on_kvm_bridge),
            Some(x86_cpuid6_bridge),
            Some(x86_read_msr_bridge),
            Some(x86_write_msr_bridge),
        )
    };
}
