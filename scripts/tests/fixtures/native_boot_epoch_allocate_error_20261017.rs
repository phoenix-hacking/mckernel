// Actual production allocate body; Arc::new's allocator error stays distinct
// from kernel Error. Allocation injection substitutes only the Arc boundary.
use std::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, AtomicUsize, Ordering};
#[derive(Debug, PartialEq, Eq)] struct Error(i32);
#[derive(Debug)] struct AllocError;
impl From<AllocError> for Error { fn from(_:AllocError)->Self { Error(-12) } }
type Result<T> = std::result::Result<T,Error>;
const EIO:Error=Error(-5);
const GFP_KERNEL:u32=0;
const SHUTDOWN_OPEN:u32=0;
static NEXT_BOOT_EPOCH:AtomicU64=AtomicU64::new(1);
static FAIL_ALLOC:AtomicBool=AtomicBool::new(false);
static ALLOCATIONS:AtomicUsize=AtomicUsize::new(0);
#[derive(Debug)] struct Arc<T>(Box<T>);
impl<T> Arc<T> {
    fn new(value:T,_flags:u32)->std::result::Result<Self,AllocError> {
        ALLOCATIONS.fetch_add(1,Ordering::Relaxed);
        if FAIL_ALLOC.load(Ordering::Relaxed) { Err(AllocError) } else { Ok(Self(Box::new(value))) }
    }
}
#[derive(Debug)] struct BootEpoch { id:u64, shutdown:AtomicU32 }
impl BootEpoch { // PRODUCTION_ALLOCATE
}
fn reset() {
    NEXT_BOOT_EPOCH.store(1,Ordering::Relaxed);
    FAIL_ALLOC.store(false,Ordering::Relaxed);
    ALLOCATIONS.store(0,Ordering::Relaxed);
}
#[test] fn successful_allocation_keeps_epoch_and_open_state() {
    reset();let epoch=BootEpoch::allocate().unwrap();
    assert_eq!(epoch.0.id,1);assert_eq!(epoch.0.shutdown.load(Ordering::Acquire),SHUTDOWN_OPEN);
    assert_eq!(NEXT_BOOT_EPOCH.load(Ordering::Acquire),2);assert_eq!(ALLOCATIONS.load(Ordering::Relaxed),1);
}
#[test] fn allocator_error_converts_to_enomem_and_consumed_epoch_is_not_reused() {
    reset();FAIL_ALLOC.store(true,Ordering::Relaxed);
    assert_eq!(BootEpoch::allocate().unwrap_err(),Error(-12));
    assert_eq!(NEXT_BOOT_EPOCH.load(Ordering::Acquire),2);assert_eq!(ALLOCATIONS.load(Ordering::Relaxed),1);
    FAIL_ALLOC.store(false,Ordering::Relaxed);
    assert_eq!(BootEpoch::allocate().unwrap().0.id,2);
}
#[test] fn exhausted_epoch_returns_eio_before_allocator() {
    reset();NEXT_BOOT_EPOCH.store(u64::MAX,Ordering::Relaxed);
    assert_eq!(BootEpoch::allocate().unwrap_err(),EIO);
    assert_eq!(ALLOCATIONS.load(Ordering::Relaxed),0);
    assert_eq!(NEXT_BOOT_EPOCH.load(Ordering::Acquire),u64::MAX);
}
