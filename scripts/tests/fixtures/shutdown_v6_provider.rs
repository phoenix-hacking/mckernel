#![allow(dead_code)]
use std::sync::atomic::{AtomicI32, AtomicU32, Ordering};
type Error = i32;
type Result<T = ()> = std::result::Result<T, Error>;
const EINVAL: Error = -22;
const EIO: Error = -5;
const EBUSY: Error = -16;
// PRODUCTION_EFFECT_TAG
trait Errno { fn to_errno(self) -> i32; }
impl Errno for Error { fn to_errno(self) -> i32 { self } }
mod kernel { pub type Error = i32; }
mod smp_resource {
    #[derive(Clone, Copy, PartialEq, Eq, Debug)]
    pub struct OsToken { pub slot: u32, pub generation: u64 }
    impl OsToken {
        pub fn slot(self) -> u32 { self.slot }
        pub unsafe fn from_ihk_lease_v2(slot: u32, generation: u64) -> Result<Self, ()> {
            if slot > 1 || generation == 0 { Err(()) } else { Ok(Self { slot, generation }) }
        }
    }
}
use smp_resource::OsToken;
static RESET_STATUS: AtomicI32 = AtomicI32::new(0);
static CPU_COMMIT: AtomicU32 = AtomicU32::new(0);
static BOOT_DROP: AtomicU32 = AtomicU32::new(0);
static MEMORY_COMMIT: AtomicU32 = AtomicU32::new(0);
static MAP_STATUS: AtomicI32 = AtomicI32::new(0);
static MEMORY: std::sync::Mutex<Option<smp_memory::MemoryContext>> = std::sync::Mutex::new(None);
mod smp_cpu {
    use super::*;
    pub enum ShutdownResetFailure { PreEffect(Error), PostEffect(Error) }
    pub fn shutdown_reset_and_reonline_outcome(_: OsToken) -> std::result::Result<(), ShutdownResetFailure> {
        match RESET_STATUS.load(Ordering::Relaxed) {
            0 => Ok(()), -19 => Err(ShutdownResetFailure::PreEffect(-19)),
            error => Err(ShutdownResetFailure::PostEffect(error)),
        }
    }
    pub fn reconcile_shutdown(owner: OsToken) -> Result {
        MEMORY.lock().unwrap().as_mut().unwrap().finish_shutdown(owner, || {
            CPU_COMMIT.fetch_add(1, Ordering::Relaxed);
        })
    }
}
mod smp_memory {
    use super::*;
    // PRODUCTION_IRQ_FAILURE
    pub struct Irq { pub owner: OsToken, pub effect: bool, pub drained: bool, pub released: bool }
    impl Irq {
        fn shutdown_has_effect(&self, owner: OsToken) -> bool { self.owner == owner && self.effect }
        fn shutdown_drained(&self, owner: OsToken) -> bool { self.owner == owner && self.drained }
        fn release_drained(&mut self, owner: OsToken) -> Result {
            if !self.shutdown_drained(owner) { return Err(EIO); }
            self.released = true;
            Ok(())
        }
    }
    pub struct Prepared {
        pub irq: Irq, pub continuing: Option<()>, pub sysfs: Option<()>,
        pub pre_error: bool, pub post_error: bool,
    }
    impl Prepared {
        fn close_irq_senders(&mut self, _: &Map) -> Result {
            if self.pre_error { return Err(EINVAL); }
            self.irq.effect = true;
            if self.post_error { return Err(EIO); }
            self.irq.drained = true;
            Ok(())
        }
    }
    pub struct Boot { pub started: bool, pub shutdown_terminal: bool, pub prepared: Prepared }
    impl Drop for Boot {
        fn drop(&mut self) {
            assert!(!self.started && self.prepared.irq.released);
            BOOT_DROP.fetch_add(1, Ordering::Relaxed);
        }
    }
    pub struct Image { pub owner: OsToken, pub boot: Option<Boot> }
    impl Image { fn started(&self) -> bool { self.boot.as_ref().is_some_and(|b| b.started) } }
    pub struct Map;
    pub struct MemoryWorkspace;
    impl MemoryWorkspace { fn new(_: &mut ()) -> Result<Self> { Ok(Self) } }
    struct Transaction;
    impl Map {
        fn prepare_release_all(&mut self, _: OsToken, _: &mut MemoryWorkspace) -> Result<Transaction> {
            if MAP_STATUS.load(Ordering::Relaxed) != 0 { Err(EIO) } else { Ok(Transaction) }
        }
    }
    impl Transaction {
        fn begin_external_effects(&mut self) -> Result { Ok(()) }
        fn compensated_rollback(self) -> Result { Ok(()) }
        fn commit(self) -> Result { MEMORY_COMMIT.fetch_add(1, Ordering::Relaxed); Ok(()) }
    }
    pub struct MemoryContext {
        pub images: [Option<Image>; 2], pub arguments: [Option<()>; 2],
        pub map: Map, pub staging: (), pub verify_error: bool,
    }
    impl MemoryContext {
        fn verify(&self) -> Result { if self.verify_error { Err(EIO) } else { Ok(()) } }
        // PRODUCTION_MEMORY_METHODS
    }
    pub fn shutdown_close_irq_senders(owner: OsToken) -> std::result::Result<(), ShutdownIrqFailure> {
        MEMORY.lock().unwrap().as_mut().unwrap().close_irq_senders_for_shutdown(owner)
    }
}
// PRODUCTION_CALLBACK
fn owner() -> OsToken { OsToken { slot: 0, generation: 9 } }
mod retention_drop {
    use std::mem::ManuallyDrop;
    use std::sync::atomic::{AtomicU32, Ordering};
    static DROPS: AtomicU32 = AtomicU32::new(0);
    struct PreparedBoot;
    impl Drop for PreparedBoot { fn drop(&mut self) { DROPS.fetch_add(1, Ordering::Relaxed); } }
    // PRODUCTION_BOOT_STORAGE
    #[test] fn started_storage_cannot_drop_its_allocations() {
        DROPS.store(0, Ordering::Relaxed);
        drop(BootStorage { prepared: ManuallyDrop::new(PreparedBoot), started: true, shutdown_terminal: true });
        assert_eq!(DROPS.load(Ordering::Relaxed), 0);
    }
    #[test] fn reconciled_storage_drops_its_allocations_exactly_once() {
        DROPS.store(0, Ordering::Relaxed);
        drop(BootStorage { prepared: ManuallyDrop::new(PreparedBoot), started: false, shutdown_terminal: false });
        assert_eq!(DROPS.load(Ordering::Relaxed), 1);
    }
}
fn setup() {
    // Quarantined test owners must not run destructors: production likewise
    // retains their started allocation. This is test-only disposal.
    if let Some(old) = MEMORY.lock().unwrap().take() { std::mem::forget(old); }
    for counter in [&CPU_COMMIT, &BOOT_DROP, &MEMORY_COMMIT] { counter.store(0, Ordering::Relaxed); }
    RESET_STATUS.store(0, Ordering::Relaxed); MAP_STATUS.store(0, Ordering::Relaxed);
    *MEMORY.lock().unwrap() = Some(smp_memory::MemoryContext {
        images: [Some(smp_memory::Image { owner: owner(), boot: Some(smp_memory::Boot {
            started: true, shutdown_terminal: false, prepared: smp_memory::Prepared {
                irq: smp_memory::Irq { owner: owner(), effect: false, drained: false, released: false },
                continuing: None, sysfs: None, pre_error: false, post_error: false,
            },
        }) }), None], arguments: [Some(()), None], map: smp_memory::Map,
        staging: (), verify_error: false,
    });
}
fn invoke() -> i64 { unsafe { ihk_smp_shutdown_v6(0, 9) } }
fn post(error: i32) -> i64 { (1_i64 << 62) | (error as u32 as i64) }
fn edit(f: impl FnOnce(&mut smp_memory::MemoryContext)) { f(MEMORY.lock().unwrap().as_mut().unwrap()); }
fn boot(c: &mut smp_memory::MemoryContext) -> &mut smp_memory::Boot { c.images[0].as_mut().unwrap().boot.as_mut().unwrap() }
fn retained() {
    assert_eq!(CPU_COMMIT.load(Ordering::Relaxed), 0);
    assert_eq!(BOOT_DROP.load(Ordering::Relaxed), 0);
    assert_eq!(MEMORY_COMMIT.load(Ordering::Relaxed), 0);
    edit(|c| assert!(boot(c).started));
}
#[test] fn success_requires_both_logical_commits_and_boot_retirement() {
    setup(); assert_eq!(invoke(), 0);
    for counter in [&CPU_COMMIT, &BOOT_DROP, &MEMORY_COMMIT] { assert_eq!(counter.load(Ordering::Relaxed), 1); }
    edit(|c| assert!(c.images[0].is_none() && c.arguments[0].is_none()));
}
#[test] fn pre_begin_failure_is_rollback_safe_and_retryable() {
    setup(); edit(|c| boot(c).prepared.pre_error = true);
    assert_eq!(invoke(), EINVAL as i64); retained();
    edit(|c| boot(c).prepared.pre_error = false); assert_eq!(invoke(), 0);
}
#[test] fn post_begin_failure_is_tagged_and_never_early_success() {
    setup(); edit(|c| boot(c).prepared.post_error = true);
    assert_eq!(invoke(), post(EIO)); retained();
    edit(|c| c.verify_error = true); assert_eq!(invoke(), post(EIO)); retained();
}
#[test] fn cpu_failure_after_drain_is_always_post_effect() {
    for status in [-19, -5] {
        setup(); RESET_STATUS.store(status, Ordering::Relaxed);
        assert_eq!(invoke(), post(status)); retained();
        RESET_STATUS.store(0, Ordering::Relaxed); assert_eq!(invoke(), 0);
    }
}
#[test] fn logical_failure_retries_without_reopening_irq() {
    setup(); MAP_STATUS.store(-5, Ordering::Relaxed);
    assert_eq!(invoke(), post(EIO)); retained();
    edit(|c| boot(c).prepared.pre_error = true);
    MAP_STATUS.store(0, Ordering::Relaxed); assert_eq!(invoke(), 0);
}
#[test] fn continuing_service_and_sysfs_are_terminal_retained_owners() {
    for sysfs in [false, true] {
        setup(); edit(|c| if sysfs { boot(c).prepared.sysfs = Some(()) } else { boot(c).prepared.continuing = Some(()) });
        assert_eq!(invoke(), post(EBUSY)); retained();
        edit(|c| assert!(boot(c).shutdown_terminal));
        assert_eq!(invoke(), post(EBUSY)); retained();
    }
}
#[test] fn wrong_generation_cannot_close_or_reconcile_foreign_owner() {
    setup(); assert_eq!(unsafe { ihk_smp_shutdown_v6(0, 10) }, EBUSY as i64); retained();
    edit(|c| { boot(c).prepared.irq.effect = true; boot(c).prepared.irq.drained = true; });
    assert_eq!(smp_cpu::reconcile_shutdown(OsToken { generation: 10, ..owner() }), Err(EIO)); retained();
    edit(|c| c.images[0].as_mut().unwrap().owner.generation = 10);
    assert_eq!(smp_cpu::reconcile_shutdown(owner()), Err(EIO)); retained();
}
