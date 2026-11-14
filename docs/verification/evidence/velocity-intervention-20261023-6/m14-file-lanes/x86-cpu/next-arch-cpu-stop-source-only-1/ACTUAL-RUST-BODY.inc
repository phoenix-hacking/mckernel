/// Complete nonreturning stop loop, using the existing architecture halt body.
/// Each wakeup returns to the next halt; no IRQ state, return policy or counter
/// is introduced. The C ABI remains void(void), as in the actual panic caller.
#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn arch_cpu_stop() {
    loop {
        unsafe { cpu_halt(); }
    }
}
