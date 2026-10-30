// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Mock providers isolate publication order; they do not model kernel locks or refcounts.
use std::mem::{offset_of, size_of};
use std::sync::atomic::{AtomicBool, AtomicPtr, AtomicUsize, Ordering};

#[repr(C)] struct FixtureProc { pid: CInt, uid: CInt, gid: CInt }
const TG_BYTES: usize = size_of::<XpmemThreadGroupPrefix>()
    + size_of::<XpmemHashlist>() * XPMEM_AP_HASHTABLE_SIZE as usize;
const PART_BYTES: usize = size_of::<XpmemPartitionPrefix>()
    + size_of::<XpmemHashlist>() * XPMEM_TG_HASHTABLE_SIZE as usize;
#[repr(C, align(64))] struct TgStorage([u8; TG_BYTES]);
#[repr(C, align(64))] struct PartStorage([u8; PART_BYTES]);
static ALLOCATED: AtomicPtr<c_void> = AtomicPtr::new(std::ptr::null_mut());
static EXISTING: AtomicPtr<c_void> = AtomicPtr::new(std::ptr::null_mut());
static EXPECTED_THREAD: AtomicPtr<c_void> = AtomicPtr::new(std::ptr::null_mut());
static EXPECTED_VM: AtomicPtr<c_void> = AtomicPtr::new(std::ptr::null_mut());
static MODE: AtomicUsize = AtomicUsize::new(0); // 0 missing, 1 existing, 2 error
static ALLOCS: AtomicUsize = AtomicUsize::new(0);
static DEREFS: AtomicUsize = AtomicUsize::new(0);
static INITIALIZED: AtomicUsize = AtomicUsize::new(0);
static INSERTS: AtomicUsize = AtomicUsize::new(0);
static LOCKS: AtomicUsize = AtomicUsize::new(0);
static UNLOCKS: AtomicUsize = AtomicUsize::new(0);
static LOCKED: AtomicBool = AtomicBool::new(false);
static SAW_EXPECTED: AtomicBool = AtomicBool::new(false);
static SAW_NULL: AtomicBool = AtomicBool::new(false);
static SAW_OTHER: AtomicBool = AtomicBool::new(false);

unsafe extern "C" fn lookup(_: CInt) -> *mut c_void {
    match MODE.load(Ordering::SeqCst) {
        1 => EXISTING.load(Ordering::SeqCst),
        2 => (-EINVAL as isize) as *mut c_void,
        _ => std::ptr::null_mut(),
    }
}
unsafe extern "C" fn deref(_: *mut c_void) { DEREFS.fetch_add(1, Ordering::SeqCst); }
unsafe extern "C" fn alloc(size: SizeT) -> *mut c_void {
    ALLOCS.fetch_add(1, Ordering::SeqCst);
    if size != TG_BYTES { return std::ptr::null_mut(); }
    ALLOCATED.load(Ordering::SeqCst)
}
unsafe extern "C" fn init(_: *mut c_void) {}
unsafe extern "C" fn set(_: *mut c_void, _: CInt) {}
unsafe extern "C" fn not_destroyable(_: *mut c_void) { INITIALIZED.fetch_add(1, Ordering::SeqCst); }
unsafe extern "C" fn lock(_: *mut c_void, _: *mut c_void) {
    LOCKS.fetch_add(1, Ordering::SeqCst); LOCKED.store(true, Ordering::SeqCst);
}
unsafe extern "C" fn unlock(_: *mut c_void, _: *mut c_void) {
    UNLOCKS.fetch_add(1, Ordering::SeqCst); LOCKED.store(false, Ordering::SeqCst);
}
unsafe extern "C" fn insert(entry: *mut c_void, _: *mut c_void) {
    INSERTS.fetch_add(1, Ordering::SeqCst);
    let tg = unsafe { entry.cast::<u8>().sub(offset_of!(XpmemThreadGroupPrefix, tg_hashlist)) };
    let obj = tg.cast::<XpmemThreadGroupPrefix>();
    let leader = unsafe { (*obj).group_leader.cast::<c_void>() };
    SAW_EXPECTED.store(leader == EXPECTED_THREAD.load(Ordering::SeqCst), Ordering::SeqCst);
    SAW_NULL.store(leader.is_null(), Ordering::SeqCst);
    let valid = unsafe {
        tg.cast::<c_void>() == ALLOCATED.load(Ordering::SeqCst)
            && (*obj).vm.cast::<c_void>() == EXPECTED_VM.load(Ordering::SeqCst)
            && (*obj).tgid == 17 && (*obj).uid == 23 && (*obj).gid == 29
            && INITIALIZED.load(Ordering::SeqCst) == 1 && LOCKED.load(Ordering::SeqCst)
    };
    SAW_OTHER.store(valid, Ordering::SeqCst);
}
fn reset() {
    for v in [&ALLOCS, &DEREFS, &INITIALIZED, &INSERTS, &LOCKS, &UNLOCKS] {
        v.store(0, Ordering::SeqCst);
    }
    for v in [&LOCKED, &SAW_EXPECTED, &SAW_NULL, &SAW_OTHER] {
        v.store(false, Ordering::SeqCst);
    }
}
fn offsets() -> XpmemOpenTgOffsets {
    XpmemOpenTgOffsets {
        proc_pid_offset: offset_of!(FixtureProc, pid), proc_ruid_offset: offset_of!(FixtureProc, uid),
        proc_rgid_offset: offset_of!(FixtureProc, gid), tg_size: TG_BYTES,
        tg_lock_offset: offset_of!(XpmemThreadGroupPrefix, lock),
        tg_tgid_offset: offset_of!(XpmemThreadGroupPrefix, tgid),
        tg_uid_offset: offset_of!(XpmemThreadGroupPrefix, uid),
        tg_gid_offset: offset_of!(XpmemThreadGroupPrefix, gid),
        tg_uniq_segid_offset: offset_of!(XpmemThreadGroupPrefix, uniq_segid),
        tg_uniq_apid_offset: offset_of!(XpmemThreadGroupPrefix, uniq_apid),
        tg_seg_list_lock_offset: offset_of!(XpmemThreadGroupPrefix, seg_list_lock),
        tg_seg_list_offset: offset_of!(XpmemThreadGroupPrefix, seg_list),
        tg_n_pinned_offset: offset_of!(XpmemThreadGroupPrefix, n_pinned),
        tg_tg_hashlist_offset: offset_of!(XpmemThreadGroupPrefix, tg_hashlist),
        tg_group_leader_offset: offset_of!(XpmemThreadGroupPrefix, group_leader),
        tg_vm_offset: offset_of!(XpmemThreadGroupPrefix, vm),
        tg_ap_hashtable_offset: size_of::<XpmemThreadGroupPrefix>(),
        part_tg_hashtable_offset: size_of::<XpmemPartitionPrefix>(),
        hashlist_stride: size_of::<XpmemHashlist>(),
        hashlist_lock_offset: offset_of!(XpmemHashlist, lock),
        hashlist_list_offset: offset_of!(XpmemHashlist, list),
    }
}
type Entry = unsafe extern "C" fn(
    *mut *mut c_void, *mut c_void, *mut c_void, *mut c_void, *const XpmemOpenTgOffsets,
    *mut c_void, Option<XpmemTgRefFn>, Option<XpmemObjectVoidFn>, Option<XpmemAllocFn>,
    Option<XpmemObjectVoidFn>, Option<XpmemObjectVoidFn>, Option<XpmemObjectVoidFn>,
    Option<XpmemAtomicSetFn>, Option<XpmemObjectVoidFn>, Option<XpmemRwlockFn>,
    Option<XpmemRwlockFn>, Option<XpmemListAddTailFn>,
) -> CInt;
fn exercise(entry: Entry, expected_at_insert: bool) {
    let mut tg = TgStorage([0xa5; TG_BYTES]);
    let mut part = PartStorage([0; PART_BYTES]);
    let mut proc = FixtureProc { pid: 17, uid: 23, gid: 29 };
    let mut thread = 0u8;
    let mut vm = 0u8;
    let mut existing = 0u8;
    let mut lock_node = 0u8;
    let mut partp = part.0.as_mut_ptr().cast::<c_void>();
    let threadp = (&mut thread as *mut u8).cast::<c_void>();
    let vmp = (&mut vm as *mut u8).cast::<c_void>();
    let tgp = tg.0.as_mut_ptr().cast::<c_void>();
    ALLOCATED.store(tgp, Ordering::SeqCst);
    EXPECTED_THREAD.store(threadp, Ordering::SeqCst);
    EXPECTED_VM.store(vmp, Ordering::SeqCst);
    EXISTING.store((&mut existing as *mut u8).cast(), Ordering::SeqCst);
    let layout = offsets();
    let mut invoke = |add: Option<XpmemListAddTailFn>| unsafe {
        entry(&mut partp, threadp, (&mut proc as *mut FixtureProc).cast(), vmp, &layout,
            (&mut lock_node as *mut u8).cast(), Some(lookup), Some(deref), Some(alloc),
            Some(init), Some(init), Some(init), Some(set), Some(not_destroyable),
            Some(lock), Some(unlock), add)
    };
    reset(); MODE.store(0, Ordering::SeqCst);
    assert_eq!(invoke(Some(insert)), 0);
    assert_eq!(INSERTS.load(Ordering::SeqCst), 1);
    assert_eq!(LOCKS.load(Ordering::SeqCst), 1);
    assert_eq!(UNLOCKS.load(Ordering::SeqCst), 1);
    assert!(SAW_OTHER.load(Ordering::SeqCst));
    assert_eq!(SAW_EXPECTED.load(Ordering::SeqCst), expected_at_insert);
    assert_eq!(SAW_NULL.load(Ordering::SeqCst), !expected_at_insert);
    assert_eq!(unsafe { (*tgp.cast::<XpmemThreadGroupPrefix>()).group_leader.cast::<c_void>() }, threadp);
    reset(); MODE.store(1, Ordering::SeqCst);
    assert_eq!(invoke(Some(insert)), 0);
    assert_eq!(DEREFS.load(Ordering::SeqCst), 1);
    assert_eq!(ALLOCS.load(Ordering::SeqCst), 0);
    assert_eq!(INSERTS.load(Ordering::SeqCst), 0);
    reset(); MODE.store(2, Ordering::SeqCst);
    assert_eq!(invoke(Some(insert)), 0);
    assert_eq!(SAW_EXPECTED.load(Ordering::SeqCst), expected_at_insert);
    assert_eq!(SAW_NULL.load(Ordering::SeqCst), !expected_at_insert);
    reset(); MODE.store(0, Ordering::SeqCst);
    ALLOCATED.store(std::ptr::null_mut(), Ordering::SeqCst);
    assert_eq!(invoke(Some(insert)), -ENOMEM);
    assert_eq!(INSERTS.load(Ordering::SeqCst), 0);
    assert_eq!(LOCKS.load(Ordering::SeqCst), 0);
    reset();
    assert_eq!(invoke(None), -EINVAL);
    assert_eq!(ALLOCS.load(Ordering::SeqCst), 0);
    assert_eq!(INSERTS.load(Ordering::SeqCst), 0);
}
fn main() {
    // Exact production ABI layout assertions; Process fields are a fixture layout.
    assert_eq!(size_of::<XpmemHashlist>(), 128);
    assert_eq!(size_of::<XpmemThreadGroupPrefix>(), 192);
    assert_eq!(offset_of!(XpmemThreadGroupPrefix, group_leader), 168);
    assert_eq!(offset_of!(XpmemThreadGroupPrefix, vm), 176);
    exercise(original::xpmem_open_tg_body_result, false);
    exercise(patched::xpmem_open_tg_body_result, true);
    println!("original insertion observes null; candidate observes current thread; preserved paths pass");
}
