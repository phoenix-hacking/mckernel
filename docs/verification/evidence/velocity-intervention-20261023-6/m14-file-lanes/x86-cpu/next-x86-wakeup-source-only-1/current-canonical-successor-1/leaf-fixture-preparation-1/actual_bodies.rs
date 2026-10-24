#![no_std]
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong};
type CUInt=u32;
unsafe extern "C" {
 fn arch_delay(us:CInt);
    // Existing providers and actual selected C data, no new runtime C getter.
    #[link_name = "x86_set_warm_reset"]
    fn x86_wakeup_set_warm_reset(ip: CULong, first_page: *mut i8);
    #[link_name = "x86_issue_ipi"]
    static mut X86_WAKEUP_ISSUE_IPI: unsafe extern "C" fn(CUInt, CUInt);
    #[link_name = "x86_wakeup_lapic_write_slot"]
    static X86_WAKEUP_LAPIC_WRITE_SLOT: *const unsafe extern "C" fn(CInt, CUInt);
    #[link_name = "x86_wakeup_lapic_read_slot"]
    static X86_WAKEUP_LAPIC_READ_SLOT: *const unsafe extern "C" fn(CInt) -> CUInt;
    #[link_name = "x86_wakeup_wait_slot"]
    static X86_WAKEUP_WAIT_SLOT: *const unsafe extern "C" fn();
    #[link_name = "x86_wakeup_first_page_slot"]
    static X86_WAKEUP_FIRST_PAGE_SLOT: *const *mut i8;
    #[link_name = "x86_wakeup_boot_status_slot"]
    static X86_WAKEUP_BOOT_STATUS_SLOT: *const CInt;
    #[link_name = "x86_wakeup_constants"]
    static X86_WAKEUP_CONSTANTS: [CUInt; 5];
}
// Complete existing INIT/SIPI orchestration; no new AP startup or error policy.
// Existing C macro values come from the typed immutable data witness. Existing
// callback slots remain owned/configured by APIC initialization. Each indirect
// call reloads its slot, preserving the original expression/callback order.
#[export_name = "__x86_wakeup"]
pub unsafe extern "C" fn x86_wakeup(apicid: CInt, ip: CULong) {
    unsafe {
        let esr = X86_WAKEUP_CONSTANTS[0] as CInt;
        let level = X86_WAKEUP_CONSTANTS[1];
        let assert = X86_WAKEUP_CONSTANTS[2];
        let init = X86_WAKEUP_CONSTANTS[3];
        let startup = X86_WAKEUP_CONSTANTS[4];

        let first_page = core::ptr::read_volatile(X86_WAKEUP_FIRST_PAGE_SLOT);
        x86_wakeup_set_warm_reset(ip, first_page);

        core::ptr::read_volatile(X86_WAKEUP_LAPIC_WRITE_SLOT)(esr, 0);
        let _ = core::ptr::read_volatile(X86_WAKEUP_LAPIC_READ_SLOT)(esr);
        core::ptr::read_volatile(&raw const X86_WAKEUP_ISSUE_IPI)(
            apicid as CUInt, level | assert | init,
        );
        core::ptr::read_volatile(&raw const X86_WAKEUP_ISSUE_IPI)(
            apicid as CUInt, level | init,
        );
        core::ptr::read_volatile(X86_WAKEUP_WAIT_SLOT)();

        for _ in 0..3 {
            let _ = core::ptr::read_volatile(X86_WAKEUP_LAPIC_READ_SLOT)(esr);
            // In C, ip promotes the OR to unsigned long, then the existing
            // callback's unsigned-int parameter truncates it to 32 bits.
            core::ptr::read_volatile(&raw const X86_WAKEUP_ISSUE_IPI)(
                apicid as CUInt, ((startup as CULong) | (ip >> 12)) as CUInt,
            );
            core::ptr::read_volatile(X86_WAKEUP_WAIT_SLOT)();
            arch_delay(200);
            if core::ptr::read_volatile(X86_WAKEUP_BOOT_STATUS_SLOT) != 0 {
                break;
            }
        }
    }
}

include!("FUTURE-RUST-TYPE-ABI.inc");
