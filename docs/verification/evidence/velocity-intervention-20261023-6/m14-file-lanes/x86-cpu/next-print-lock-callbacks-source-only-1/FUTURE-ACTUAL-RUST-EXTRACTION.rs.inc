// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Source fragment only. Fixture debug namespace supplies controlled endpoints;
// production uses the already selected unchanged actual Rust debug bodies.
type CULong=u64;
mod debug { unsafe extern "C" { pub fn kprintf_lock()->u64; pub fn kprintf_unlock(flags:u64); } }

/// Enter the same existing Rust print lock and return its complete IRQ flags.
/// This is the complete selected C callback body. The surrounding diagnostic
/// caller still owns the lock span; no guard, state or reference is retained.
#[no_mangle]
pub unsafe extern "C" fn x86_kprintf_lock_bridge() -> CULong {
    unsafe { crate::debug::kprintf_lock() }
}

/// Leave the same existing print lock using exactly the caller-supplied flags.
/// No IRQ bit is normalized and no lifetime/ordering policy is introduced.
#[no_mangle]
pub unsafe extern "C" fn x86_kprintf_unlock_bridge(flags: CULong) {
    unsafe { crate::debug::kprintf_unlock(flags); }
}
