// Complete extracted production items execute below. CPU reset/hotplug,
// physical IRQ drain and memory map transactions remain deterministic stubs.
// Sequential only: this does not execute os_request, locks or native hardware.
// PROVIDER_FIXTURE

mod abi {
    // PRODUCTION_ABI
}
mod os_registry {
    // PRODUCTION_REGISTRY
}
mod runtime {
    use super::{EBUSY, Result};
    use std::{ptr, sync::atomic::{AtomicU32, Ordering}};
    const ADMISSION_CLOSED: u32 = 1 << 31;
    const ADMISSION_OVERFLOW: u32 = 1 << 30;
    const ADMISSION_COUNT_MASK: u32 = !(ADMISSION_CLOSED | ADMISSION_OVERFLOW);
    const SHUTDOWN_V6_POST_EFFECT: i64 = 1_i64 << 62;
    const SHUTDOWN_V6_PAYLOAD_MASK: i64 = 0xffff_ffff;
    // PRODUCTION_RUNTIME
    pub(super) fn closed() -> bool { ADMISSION.is_closed() }
    static ADMISSION: Admission = Admission::new();
    pub(super) fn reset() { ADMISSION.word.store(0, Ordering::Relaxed); }
    pub(super) fn busy() {
        let owner = ADMISSION.enter().unwrap();
        assert!(ADMISSION.close_for_shutdown().is_err());
        assert!(!ADMISSION.is_closed());
        drop(owner);
    }
    pub(super) fn transaction(registry: &super::os_registry::OsRegistry,
                             handle: super::os_registry::OsHandle) -> i32 {
        let admission = ADMISSION.close_for_shutdown().unwrap();
        let guard = registry.begin_shutdown(handle).unwrap();
        assert_eq!(guard.status(), super::os_registry::OsStatus::Shutdown);
        let result = super::invoke();
        finish_shutdown(guard, admission, shutdown_v6_outcome(result))
    }
}
static ACTIVE: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
static PHYSICAL: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
static OWNER_GENERATION: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(9);
fn physical_boundary() {
    if !ACTIVE.load(Ordering::Relaxed) { return; }
    assert!(runtime::closed());
    edit(|c| assert!(boot(c).prepared.irq.drained));
    PHYSICAL.store(true, Ordering::Relaxed);
}
fn reconcile_boundary() {
    if ACTIVE.load(Ordering::Relaxed) {
        assert!(PHYSICAL.load(Ordering::Relaxed), "reconcile before physical reset/reonline");
        assert!(runtime::closed());
    }
}
fn transaction_setup() -> (os_registry::OsRegistry, os_registry::OsHandle) {
    setup(); runtime::reset();
    PHYSICAL.store(false, Ordering::Relaxed);
    ACTIVE.store(true, Ordering::Relaxed);
    let registry = os_registry::OsRegistry::new();
    let reservation = registry.reserve().unwrap();
    let handle = reservation.handle();
    reservation.commit().unwrap();
    assert_eq!(handle.minor(), owner().slot as usize);
    OWNER_GENERATION.store(handle.generation(), Ordering::Relaxed);
    edit(|c| {
        let image = c.images[0].as_mut().unwrap();
        image.owner = owner();
        image.boot.as_mut().unwrap().prepared.irq.owner = owner();
    });
    registry.transition(handle, os_registry::OsStatus::Booting).unwrap();
    registry.transition(handle, os_registry::OsStatus::Running).unwrap();
    (registry, handle)
}
#[test] fn actual_order_success() {
    let (registry, handle) = transaction_setup();
    assert_eq!(runtime::transaction(&registry, handle), 0);
    assert!(runtime::closed());
    assert_eq!(registry.snapshot(handle).unwrap().status, os_registry::OsStatus::NotBooted);
    for counter in [&CPU_COMMIT, &MEMORY_COMMIT, &BOOT_DROP] {
        assert_eq!(counter.load(Ordering::Relaxed), 1);
    }
}
#[test] fn actual_order_pre_effect_restores_running_and_admission() {
    let (registry, handle) = transaction_setup();
    edit(|c| boot(c).prepared.pre_error = true);
    assert_eq!(runtime::transaction(&registry, handle), EINVAL);
    assert!(!runtime::closed());
    assert_eq!(registry.snapshot(handle).unwrap().status, os_registry::OsStatus::Running);
    assert!(!PHYSICAL.load(Ordering::Relaxed));
    retained();
}
#[test] fn actual_order_post_effect_retains_registry_and_admission() {
    let (registry, handle) = transaction_setup();
    edit(|c| boot(c).prepared.post_error = true);
    assert_eq!(runtime::transaction(&registry, handle), EIO);
    assert!(runtime::closed());
    assert_eq!(registry.snapshot(handle).unwrap().status, os_registry::OsStatus::Shutdown);
    assert!(!PHYSICAL.load(Ordering::Relaxed));
    retained();
    edit(|c| boot(c).prepared.post_error = false);
    assert_eq!(runtime::transaction(&registry, handle), 0);
    assert_eq!(registry.snapshot(handle).unwrap().status, os_registry::OsStatus::NotBooted);
}
#[test] fn actual_order_live_callback_refuses_close_without_effect() {
    let (_registry, _handle) = transaction_setup();
    runtime::busy();
    assert!(!PHYSICAL.load(Ordering::Relaxed));
    retained();
}
