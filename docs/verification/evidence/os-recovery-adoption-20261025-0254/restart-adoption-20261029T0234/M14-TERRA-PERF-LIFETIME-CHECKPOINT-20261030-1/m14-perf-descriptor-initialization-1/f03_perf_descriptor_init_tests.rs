//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Actual perf entry + publication bodies with mock allocation/offload/lock boundaries.
//! The selected source must be built in an independently admitted test profile.
use super::*;
use core::mem::{offset_of, size_of, MaybeUninit};
use core::sync::atomic::{AtomicBool, AtomicPtr, AtomicUsize, Ordering};

#[repr(C)]
struct FixtureProc { lock: CLong, head: *mut c_void }
#[repr(C)]
struct FixtureThread { pmc: CULong }
#[repr(C)]
struct FixtureEvent {
    pid: CInt, counter: CInt, leader: *mut c_void,
    siblings: AbiListHead, entry: AbiListHead, nr: CInt, status: CULong,
}
static DESCRIPTOR: AtomicPtr<Mckfd> = AtomicPtr::new(core::ptr::null_mut());
static EVENT: AtomicPtr<FixtureEvent> = AtomicPtr::new(core::ptr::null_mut());
static ALLOCS: AtomicUsize = AtomicUsize::new(0);
static LOCK_SAW_INITIALIZED: AtomicBool = AtomicBool::new(false);
static UNLOCK_SAW_PUBLISHED: AtomicBool = AtomicBool::new(false);

unsafe extern "C" fn event_alloc(out: *mut *mut c_void, _: *mut c_void) -> CInt {
    ALLOCS.fetch_add(1, Ordering::SeqCst);
    unsafe { *out = EVENT.load(Ordering::SeqCst).cast() };
    0
}
unsafe extern "C" fn counter(_: *mut c_void, _: *mut c_void) -> CInt { 3 }
unsafe extern "C" fn syscall(_: *mut SyscallRequest, _: CInt) -> CLong { 44 }
unsafe extern "C" fn alloc(size: SizeT, _: CULong) -> *mut c_void {
    if size != size_of::<Mckfd>() { return core::ptr::null_mut(); }
    DESCRIPTOR.load(Ordering::SeqCst).cast()
}
unsafe extern "C" fn long_callback(_: *mut c_void, _: *mut c_void) -> CLong { 1 }
unsafe extern "C" fn int_callback(_: *mut c_void, _: *mut c_void) -> CInt { 2 }
unsafe extern "C" fn lock(p: *mut c_void) -> CLong {
    let descriptor = DESCRIPTOR.load(Ordering::SeqCst);
    let proc = p.cast::<FixtureProc>(); // lock is the first field
    let initialized = unsafe {
        (*descriptor).opt.is_null() && (*descriptor).dup_cb.is_null()
            && (*descriptor).fd == 44 && (*descriptor).padding == -1
            && (*proc).head == 1usize as *mut c_void
    };
    LOCK_SAW_INITIALIZED.store(initialized, Ordering::SeqCst);
    19
}
unsafe extern "C" fn unlock(p: *mut c_void, irq: CLong) {
    let proc = p.cast::<FixtureProc>();
    let descriptor = DESCRIPTOR.load(Ordering::SeqCst);
    let published = unsafe { irq == 19 && (*proc).head == descriptor.cast()
        && (*descriptor).next.cast::<c_void>() == 1usize as *mut c_void };
    UNLOCK_SAW_PUBLISHED.store(published, Ordering::SeqCst);
}

#[test]
fn poisoned_descriptor_initialized_before_publication() {
    let mut desc = MaybeUninit::<Mckfd>::uninit();
    let descp = desc.as_mut_ptr();
    unsafe { core::ptr::write_bytes(descp.cast::<u8>(), 0xa5, size_of::<Mckfd>()) };
    let mut event: FixtureEvent = unsafe { MaybeUninit::zeroed().assume_init() };
    let mut thread = FixtureThread { pmc: 0 };
    let mut proc = FixtureProc { lock: 0, head: 1usize as *mut c_void };
    let mut request: SyscallRequest = unsafe { MaybeUninit::zeroed().assume_init() };
    let mut attr = 0u64;
    DESCRIPTOR.store(descp, Ordering::SeqCst);
    EVENT.store(&mut event, Ordering::SeqCst);
    ALLOCS.store(0, Ordering::SeqCst);
    LOCK_SAW_INITIALIZED.store(false, Ordering::SeqCst);
    UNLOCK_SAW_PUBLISHED.store(false, Ordering::SeqCst);

    // This calls the actual private entry body, not a copy of its initialization
    // or publication logic. Only the boundary callbacks and fixture layouts are mocked.
    let invoke = |size| unsafe {
        perf_entry_body_with_group_cleanup(
            &mut request, (&mut thread as *mut FixtureThread).cast(),
            (&mut proc as *mut FixtureProc).cast(), (&mut attr as *mut u64).cast(),
            7, -1, 298, 0, size, 2,
            offset_of!(FixtureEvent, pid), offset_of!(FixtureEvent, counter),
            offset_of!(FixtureProc, head), offset_of!(Mckfd, next),
            offset_of!(Mckfd, fd), offset_of!(Mckfd, data),
            offset_of!(FixtureEvent, leader), offset_of!(FixtureEvent, siblings),
            offset_of!(FixtureEvent, entry), offset_of!(FixtureEvent, nr),
            offset_of!(FixtureEvent, status), offset_of!(FixtureThread, pmc),
            offset_of!(FixtureProc, lock), offset_of!(Mckfd, padding),
            offset_of!(Mckfd, read_cb), offset_of!(Mckfd, ioctl_cb),
            offset_of!(Mckfd, mmap_cb), offset_of!(Mckfd, close_cb),
            offset_of!(Mckfd, fcntl_cb), Some(event_alloc), Some(counter),
            Some(syscall), Some(alloc), Some(long_callback), Some(int_callback),
            Some(long_callback), Some(int_callback), Some(int_callback),
            Some(lock), Some(unlock),
        )
    };
    // Size mismatch cannot allocate an event or issue a host request.
    let mut invoke = invoke;
    assert_eq!(invoke(size_of::<Mckfd>() - 1), -(EINVAL as CLong));
    assert_eq!(ALLOCS.load(Ordering::SeqCst), 0);
    assert_eq!(invoke(size_of::<Mckfd>()), 44);
    assert_eq!(ALLOCS.load(Ordering::SeqCst), 1);
    assert!(LOCK_SAW_INITIALIZED.load(Ordering::SeqCst));
    assert!(UNLOCK_SAW_PUBLISHED.load(Ordering::SeqCst));
    let actual = unsafe { desc.assume_init_ref() };
    assert!(actual.opt.is_null() && actual.dup_cb.is_null());
    assert_eq!(actual.data as usize, (&mut event as *mut FixtureEvent) as usize);
    assert_eq!(actual.read_cb as usize, long_callback as usize);
    assert_eq!(actual.ioctl_cb as usize, int_callback as usize);
    assert_eq!(actual.mmap_cb as usize, long_callback as usize);
    assert_eq!(actual.close_cb as usize, int_callback as usize);
    assert_eq!(actual.fcntl_cb as usize, int_callback as usize);
    assert_eq!(thread.pmc, 1 << 3);
    assert_eq!(event.pid, 7);
    assert_eq!(event.counter, 3);
    assert_eq!(event.leader, (&mut event as *mut FixtureEvent).cast());
    assert_eq!(event.status, 1 << 3);
}
