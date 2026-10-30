// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Source-only fixture: stub callbacks record effects, they do not free memory.
use core::ffi::c_void;
use std::sync::atomic::{AtomicBool, AtomicI32, AtomicUsize, Ordering};
static RESULT: AtomicI32 = AtomicI32::new(0);
static EXPECT_THREAD: AtomicUsize = AtomicUsize::new(0);
static EXPECT_EVENT: AtomicUsize = AtomicUsize::new(0);
static CALLS: AtomicUsize = AtomicUsize::new(0);
static FREES: AtomicUsize = AtomicUsize::new(0);
static BAD_POINTERS: AtomicUsize = AtomicUsize::new(0);
static PUBLISHED: AtomicBool = AtomicBool::new(false);
static FREE_AFTER_PUBLICATION: AtomicUsize = AtomicUsize::new(0);

#[no_mangle]
pub extern "C" fn f03_perf_counter_allocate_v1(thread: *mut c_void, event: *mut c_void) -> i32 {
    CALLS.fetch_add(1, Ordering::SeqCst);
    if thread as usize != EXPECT_THREAD.load(Ordering::SeqCst)
        || event as usize != EXPECT_EVENT.load(Ordering::SeqCst) {
        BAD_POINTERS.fetch_add(1, Ordering::SeqCst);
    }
    RESULT.load(Ordering::SeqCst)
}
#[no_mangle]
pub extern "C" fn perf_event_alloc_free_bridge(event: *mut c_void) {
    if event as usize != EXPECT_EVENT.load(Ordering::SeqCst) {
        BAD_POINTERS.fetch_add(1, Ordering::SeqCst);
    }
    if PUBLISHED.load(Ordering::SeqCst) {
        FREE_AFTER_PUBLICATION.fetch_add(1, Ordering::SeqCst);
    }
    FREES.fetch_add(1, Ordering::SeqCst);
}
mod selected {
    use core::ffi::c_void;
    type CInt = i32;
    unsafe extern "C" {
        fn f03_perf_counter_allocate_v1(thread: *mut c_void, event: *mut c_void) -> CInt;
        fn perf_event_alloc_free_bridge(event: *mut c_void);
    }
    include!("candidate-wrapper.rs");
    // This is the same ABI as PerfCounterAllocFn and the C callback field.
    const _: unsafe extern "C" fn(*mut c_void, *mut c_void) -> i32 = perf_entry_counter_alloc_or_release;
    pub unsafe fn call(thread: *mut c_void, event: *mut c_void) -> i32 {
        unsafe { perf_entry_counter_alloc_or_release(thread, event) }
    }
}
#[test]
fn independent_return_release_and_publication_oracle() {
    // One test owns the recorder, avoiding inter-test shared-state races.
    // Independent expected values, including zero as a successful index.
    let cases = [(0, 0_usize), (7, 0), (-22, 1), (-12, 1)];
    for (provider_result, expected_frees) in cases {
        let mut thread = 0x31_u8;
        let mut event = 0x72_u8;
        let thread_ptr = (&mut thread as *mut u8).cast::<c_void>();
        let event_ptr = (&mut event as *mut u8).cast::<c_void>();
        EXPECT_THREAD.store(thread_ptr as usize, Ordering::SeqCst);
        EXPECT_EVENT.store(event_ptr as usize, Ordering::SeqCst);
        RESULT.store(provider_result, Ordering::SeqCst);
        CALLS.store(0, Ordering::SeqCst);
        FREES.store(0, Ordering::SeqCst);
        BAD_POINTERS.store(0, Ordering::SeqCst);
        PUBLISHED.store(false, Ordering::SeqCst);
        FREE_AFTER_PUBLICATION.store(0, Ordering::SeqCst);
        let observed = unsafe { selected::call(thread_ptr, event_ptr) };
        assert_eq!(observed, provider_result, "provider result must pass through");
        assert_eq!(CALLS.load(Ordering::SeqCst), 1, "one provider call");
        assert_eq!(FREES.load(Ordering::SeqCst), expected_frees, "no leak or double release");
        assert_eq!(BAD_POINTERS.load(Ordering::SeqCst), 0, "unchanged identities");
        assert_eq!(FREE_AFTER_PUBLICATION.load(Ordering::SeqCst), 0, "no post-publication release");
        assert!(!PUBLISHED.load(Ordering::SeqCst), "wrapper must not publish");
        assert_eq!((thread, event), (0x31, 0x72), "wrapper must not alter objects");
    }
}
