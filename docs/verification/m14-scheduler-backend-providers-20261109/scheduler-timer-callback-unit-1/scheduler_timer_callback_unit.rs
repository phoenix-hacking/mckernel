#![no_std]

#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;

// Genuine LAPIC interfaces only; actual backend bodies are not selected.
mod x86_cpu_helpers {
    type CUInt = u32;
    extern "C" {
        pub fn lapic_timer_enable(clocks: CUInt);
        pub fn lapic_timer_disable();
    }
}

// Preserve the actual super:: namespace and its genuine existing providers.
mod process_helpers {
    use crate::abi::CULong;
    extern "C" {
        pub fn process_spin_lock_bridge(lock_addr: CULong) -> CULong;
        pub fn process_spin_unlock_bridge(lock_addr: CULong, irqstate: CULong);
    }

mod remaining_process_timer_adapters {
    use super::*;
    /// Same IRQ-save spin-lock boundary, without an extra lock or IRQ operation.
    /// # Safety
    /// lock_addr is the original live aligned writable ticket lock, in the
    /// original IRQ context with its existing pairing/ownership contract.
    #[no_mangle]
    pub unsafe extern "C" fn process_timer_spin_lock_bridge(lock_addr: CULong) -> CULong {
        unsafe { super::process_spin_lock_bridge(lock_addr) }
    }
    /// Preserve the exact saved IRQ state of the paired original lock.
    /// # Safety
    /// The original caller holds the same lock and provides its saved state.
    #[no_mangle]
    pub unsafe extern "C" fn process_timer_spin_unlock_bridge(lock_addr: CULong, irqstate: CULong) {
        unsafe { super::process_spin_unlock_bridge(lock_addr, irqstate); }
    }
    /// Forward the original unsigned32 clocks to the existing timer code.
    /// # Safety
    /// The existing LAPIC/CPU privilege and MMIO mapping contract applies.
    #[no_mangle]
    pub unsafe extern "C" fn process_timer_lapic_enable_bridge(clocks: u32) {
        unsafe { crate::x86_cpu_helpers::lapic_timer_enable(clocks); }
    }
    /// Invoke the original disable once without changing timer policy.
    /// # Safety
    /// The existing LAPIC/CPU privilege and MMIO mapping contract applies.
    #[no_mangle]
    pub unsafe extern "C" fn process_timer_lapic_disable_bridge() {
        unsafe { crate::x86_cpu_helpers::lapic_timer_disable(); }
    }
}
}
