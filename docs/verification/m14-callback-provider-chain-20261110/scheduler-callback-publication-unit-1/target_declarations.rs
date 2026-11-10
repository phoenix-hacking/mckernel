// Genuine existing targets at original Rust paths: declarations only.
mod local_apic_io {
    use crate::abi::CInt;
    unsafe extern "C" {
        pub(crate) fn x2apic_write(reg: CInt, value: u32);
        pub(crate) fn x2apic_read(reg: CInt) -> u32;
        pub(crate) fn apic_write(reg: CInt, value: u32);
        pub(crate) fn apic_read(reg: CInt) -> u32;
    }
}

mod icr_callbacks {
    unsafe extern "C" {
        pub(crate) fn x2apic_icr_write(low: u32, apicid: u32);
        pub(crate) fn apic_icr_write(high: u32, low: u32);
        pub(crate) fn apic_wait_icr_idle();
    }
}

mod ipi_entries {
    unsafe extern "C" {
        pub(crate) fn x2apic_x86_issue_ipi(apicid: u32, low: u32);
        pub(crate) fn apic_x86_issue_ipi(apicid: u32, low: u32);
    }
}
