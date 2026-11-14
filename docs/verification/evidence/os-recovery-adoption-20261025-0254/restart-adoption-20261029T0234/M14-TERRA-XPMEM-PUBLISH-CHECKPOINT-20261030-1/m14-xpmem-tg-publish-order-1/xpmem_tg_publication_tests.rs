//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Actual xpmem_open_tg_body_result with mocked providers; requires an admitted test profile.
use super::*;
use core::sync::atomic::{AtomicBool, AtomicPtr, AtomicUsize, Ordering};

const TG_BYTES: usize = size_of::<XpmemThreadGroupPrefix>()
    + size_of::<XpmemHashlist>() * XPMEM_AP_HASHTABLE_SIZE as usize;
const PART_BYTES: usize = size_of::<XpmemPartitionPrefix>()
    + size_of::<XpmemHashlist>() * XPMEM_TG_HASHTABLE_SIZE as usize;
#[repr(C, align(64))] struct TgStorage([u8; TG_BYTES]);
#[repr(C, align(64))] struct PartStorage([u8; PART_BYTES]);

// These cells serve one sequential test. No production provider is replaced.
static ALLOCATED: AtomicPtr<c_void> = AtomicPtr::new(core::ptr::null_mut());
static EXISTING: AtomicPtr<c_void> = AtomicPtr::new(core::ptr::null_mut());
static EXPECTED_THREAD: AtomicPtr<c_void> = AtomicPtr::new(core::ptr::null_mut());
static EXPECTED_VM: AtomicPtr<c_void> = AtomicPtr::new(core::ptr::null_mut());
static LOOKUP_MODE: AtomicUsize = AtomicUsize::new(0); // 0 missing, 1 existing, 2 ERR_PTR
static ALLOC_COUNT: AtomicUsize = AtomicUsize::new(0);
static DEREF_COUNT: AtomicUsize = AtomicUsize::new(0);
static INIT_COUNT: AtomicUsize = AtomicUsize::new(0);
static INSERT_COUNT: AtomicUsize = AtomicUsize::new(0);
static LOCK_COUNT: AtomicUsize = AtomicUsize::new(0);
static UNLOCK_COUNT: AtomicUsize = AtomicUsize::new(0);
static HELD: AtomicBool = AtomicBool::new(false);
static INSERT_SAW_READY: AtomicBool = AtomicBool::new(false);

unsafe extern "C" fn lookup(_: CInt) -> *mut c_void {
    match LOOKUP_MODE.load(Ordering::SeqCst) {
        1 => EXISTING.load(Ordering::SeqCst),
        2 => err_ptr(-EINVAL),
        _ => core::ptr::null_mut(),
    }
}
unsafe extern "C" fn deref(_: *mut c_void) { DEREF_COUNT.fetch_add(1, Ordering::SeqCst); }
unsafe extern "C" fn alloc(size: SizeT) -> *mut c_void {
    ALLOC_COUNT.fetch_add(1, Ordering::SeqCst);
    if size != TG_BYTES { return core::ptr::null_mut(); }
    ALLOCATED.load(Ordering::SeqCst)
}
unsafe extern "C" fn object_init(_: *mut c_void) {}
unsafe extern "C" fn atomic_set(_: *mut c_void, _: CInt) {}
unsafe extern "C" fn not_destroyable(_: *mut c_void) { INIT_COUNT.fetch_add(1, Ordering::SeqCst); }
unsafe extern "C" fn lock(_: *mut c_void, _: *mut c_void) {
    LOCK_COUNT.fetch_add(1, Ordering::SeqCst);
    HELD.store(true, Ordering::SeqCst);
}
unsafe extern "C" fn unlock(_: *mut c_void, _: *mut c_void) {
    UNLOCK_COUNT.fetch_add(1, Ordering::SeqCst);
    HELD.store(false, Ordering::SeqCst);
}
unsafe extern "C" fn insert(entry: *mut c_void, _: *mut c_void) {
    INSERT_COUNT.fetch_add(1, Ordering::SeqCst);
    // entry is the actual TG list field passed by the real production body.
    let tg = unsafe { entry.cast::<u8>().sub(offset_of!(XpmemThreadGroupPrefix, tg_hashlist)) };
    let actual = tg.cast::<XpmemThreadGroupPrefix>();
    let ready = unsafe {
        tg.cast::<c_void>() == ALLOCATED.load(Ordering::SeqCst)
            && (*actual).group_leader.cast::<c_void>() == EXPECTED_THREAD.load(Ordering::SeqCst)
            && (*actual).vm.cast::<c_void>() == EXPECTED_VM.load(Ordering::SeqCst)
            && (*actual).tgid == 17 && (*actual).uid == 23 && (*actual).gid == 29
            && INIT_COUNT.load(Ordering::SeqCst) == 1
            && HELD.load(Ordering::SeqCst)
    };
    INSERT_SAW_READY.store(ready, Ordering::SeqCst);
}
fn reset() {
    ALLOC_COUNT.store(0, Ordering::SeqCst);
    DEREF_COUNT.store(0, Ordering::SeqCst);
    INIT_COUNT.store(0, Ordering::SeqCst);
    INSERT_COUNT.store(0, Ordering::SeqCst);
    LOCK_COUNT.store(0, Ordering::SeqCst);
    UNLOCK_COUNT.store(0, Ordering::SeqCst);
    HELD.store(false, Ordering::SeqCst);
    INSERT_SAW_READY.store(false, Ordering::SeqCst);
}

#[test]
fn new_tg_is_complete_before_insertion_and_existing_paths_remain() {
    let mut tg = TgStorage([0xa5; TG_BYTES]);
    let mut part = PartStorage([0; PART_BYTES]);
    let mut process = MaybeUninit::<Process>::uninit();
    let process_ptr = process.as_mut_ptr();
    // Only these real Process fields are read by this body; no Process reference
    // or initialized value is formed from the remaining uninitialized storage.
    unsafe {
        core::ptr::addr_of_mut!((*process_ptr).pid).write(17);
        core::ptr::addr_of_mut!((*process_ptr).ruid).write(23);
        core::ptr::addr_of_mut!((*process_ptr).rgid).write(29);
    }
    let mut thread_byte = 0u8;
    let mut vm_byte = 0u8;
    let mut existing_byte = 0u8;
    let mut lock_byte = 0u8;
    let threadp = (&mut thread_byte as *mut u8).cast::<c_void>();
    let vmp = (&mut vm_byte as *mut u8).cast::<c_void>();
    let mut partp = part.0.as_mut_ptr().cast::<c_void>();
    ALLOCATED.store(tg.0.as_mut_ptr().cast(), Ordering::SeqCst);
    EXPECTED_THREAD.store(threadp, Ordering::SeqCst);
    EXPECTED_VM.store(vmp, Ordering::SeqCst);
    EXISTING.store((&mut existing_byte as *mut u8).cast(), Ordering::SeqCst);

    let mut invoke = |add: Option<XpmemListAddTailFn>| unsafe {
        xpmem_open_tg_body_result(
            &mut partp, threadp, process_ptr.cast(), vmp, &XPMEM_OPEN_TG_OFFSETS,
            (&mut lock_byte as *mut u8).cast(), Some(lookup), Some(deref), Some(alloc),
            Some(object_init), Some(object_init), Some(object_init), Some(atomic_set),
            Some(not_destroyable), Some(lock), Some(unlock), add,
        )
    };

    // A missing lookup builds a new TG; the actual insertion callback checks the
    // exact publication moment, not merely the function's final memory contents.
    reset(); LOOKUP_MODE.store(0, Ordering::SeqCst);
    assert_eq!(invoke(Some(insert)), 0);
    assert_eq!(ALLOC_COUNT.load(Ordering::SeqCst), 1);
    assert_eq!(INSERT_COUNT.load(Ordering::SeqCst), 1);
    assert_eq!(LOCK_COUNT.load(Ordering::SeqCst), 1);
    assert_eq!(UNLOCK_COUNT.load(Ordering::SeqCst), 1);
    assert!(INSERT_SAW_READY.load(Ordering::SeqCst));
    assert!(!HELD.load(Ordering::SeqCst));

    // Existing TG retains the original lookup/deref path without allocation.
    reset(); LOOKUP_MODE.store(1, Ordering::SeqCst);
    assert_eq!(invoke(Some(insert)), 0);
    assert_eq!(DEREF_COUNT.load(Ordering::SeqCst), 1);
    assert_eq!(ALLOC_COUNT.load(Ordering::SeqCst), 0);
    assert_eq!(INSERT_COUNT.load(Ordering::SeqCst), 0);

    // The retained body treats an error pointer as a miss; preserve that path.
    reset(); LOOKUP_MODE.store(2, Ordering::SeqCst);
    assert_eq!(invoke(Some(insert)), 0);
    assert_eq!(INSERT_COUNT.load(Ordering::SeqCst), 1);
    assert!(INSERT_SAW_READY.load(Ordering::SeqCst));

    // Allocation failure and a missing required provider cannot publish.
    reset(); LOOKUP_MODE.store(0, Ordering::SeqCst);
    ALLOCATED.store(core::ptr::null_mut(), Ordering::SeqCst);
    assert_eq!(invoke(Some(insert)), -ENOMEM);
    assert_eq!(INSERT_COUNT.load(Ordering::SeqCst), 0);
    assert_eq!(LOCK_COUNT.load(Ordering::SeqCst), 0);
    reset();
    assert_eq!(invoke(None), -EINVAL);
    assert_eq!(ALLOC_COUNT.load(Ordering::SeqCst), 0);
    assert_eq!(INSERT_COUNT.load(Ordering::SeqCst), 0);
}
