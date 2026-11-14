// Included after exact production excerpts, never a contract model.
use std::sync::{Arc, Barrier};
fn owner() -> PageOwner { PageOwner { physical: 0x10000, order: 0 } }
fn pair() -> Box<guest::NativeIrqWorkDescriptor> {
    let mut d = Box::new(guest::NativeIrqWorkDescriptor::unpublished(9, 0x10000, 2));
    let bytes = NativeIrqWorkDescriptorView::encode_unpublished(9, 0x10000, 2);
    unsafe { core::ptr::copy_nonoverlapping(bytes.as_ptr(), (&mut *d as *mut guest::NativeIrqWorkDescriptor).cast(), 64); }
    d
}
fn host(d: &guest::NativeIrqWorkDescriptor) -> &NativeIrqWorkDescriptorView {
    unsafe { &*(d as *const guest::NativeIrqWorkDescriptor).cast() }
}
fn valid(d: &guest::NativeIrqWorkDescriptor) -> bool {
    validate_native_irq_work_descriptor(host(d), 9, &owner(), 2, &[(0x20000, 0x21000)])
}
#[test]
fn real_encoding_and_release_publication() {
    let d = pair();
    assert_eq!(d.version, 1); assert_eq!(d.bytes, 64);
    assert!(d.validate_unpublished(2)); assert!(!valid(&d));
    d.publish_release_ready(); assert!(valid(&d));
    assert!(!d.validate_unpublished(2));
}
#[test]
fn exact_geometry_and_generation_rejections() {
    let mut d = pair(); d.publish_release_ready();
    assert!(!validate_native_irq_work_descriptor(host(&d), 8, &owner(), 2, &[]));
    assert!(!validate_native_irq_work_descriptor(host(&d), 9, &owner(), 1, &[]));
    assert!(!validate_native_irq_work_descriptor(host(&d), 9, &owner(), 2, &[(0x10800,0x11000)]));
    d.slots_phys += 64; assert!(!valid(&d)); d.slots_phys -= 64;
    d.slots_count = 65; assert!(!valid(&d)); d.slots_count = 2;
    d.slots_stride = 63; assert!(!valid(&d)); d.slots_stride = 64;
    d.reserved[5] = 1; assert!(!valid(&d)); d.reserved[5] = 0;
    d.slots_phys = u64::MAX - 63; assert!(d.checked_end().is_none());
}
#[test]
fn close_waits_real_lease_across_failed_ipi_and_final_access() {
    let d: Arc<guest::NativeIrqWorkDescriptor> = Arc::from(pair()); d.publish_release_ready();
    let entered = Arc::new(Barrier::new(2)); let release = Arc::new(Barrier::new(2));
    let thread = { let d = d.clone(); let entered = entered.clone(); let release = release.clone();
        std::thread::spawn(move || {
            let mut lease = d.senders.acquire().unwrap();
            assert!(!lease.list_inserted()); assert!(lease.busy_acquired());
            assert!(lease.list_inserted()); assert!(lease.ipi_result(-5));
            entered.wait(); release.wait(); assert!(lease.slot_accessed());
        }) };
    entered.wait();
    assert!(!close_native_irq_work_senders(host(&d), || false));
    assert!(d.senders.acquire().is_none()); assert!(!d.senders.can_drain());
    release.wait(); thread.join().unwrap();
    assert!(close_native_irq_work_senders(host(&d), || panic!("already quiescent")));
    assert!(d.senders.can_drain());
}
#[test]
fn concurrent_admission_close_and_publication_visibility() {
    let d: Arc<guest::NativeIrqWorkDescriptor> = Arc::from(pair());
    let slots = Arc::new(std::sync::atomic::AtomicU32::new(0));
    let thread = { let d=d.clone(); let slots=slots.clone(); std::thread::spawn(move || {
        slots.store(73, Ordering::Relaxed); d.publish_release_ready();
        while let Some(lease) = d.senders.acquire() { std::hint::black_box(&lease); }
    }) };
    while native_irq_work_state_acquire(host(&d)) == 0 { std::thread::yield_now(); }
    assert_eq!(slots.load(Ordering::Relaxed), 73);
    assert!(close_native_irq_work_senders(host(&d), || { std::thread::yield_now(); true }));
    thread.join().unwrap(); assert!(d.senders.acquire().is_none());
}

#[cfg(native_linux_irq_work_v6_12)]
mod producer {
    use super::*;
    use core::ffi::c_void;
    use core::sync::atomic::{AtomicBool, AtomicPtr};
    #[repr(C, align(64))] struct Slots([u8; 128]);
    const RETAINED_PHYSICAL: u64 = 0x10000;
    const LINUX_PAGE_OFFSET: u64 = 0xffff_9000_0000_0000;
    static mut SLOTS: Slots = Slots([0xa5; 128]);
    static mut PARAMS: [u64; 1024] = [0; 1024];
    static QUEUE: AtomicPtr<llist::LListNode> = AtomicPtr::new(core::ptr::null_mut());
    static FAIL_MAP: AtomicBool = AtomicBool::new(true);
    static FAIL_IPI: AtomicBool = AtomicBool::new(false);
    #[no_mangle] static mut boot_param: *mut c_void = core::ptr::null_mut();
    #[no_mangle] static mut num_processors: i32 = 2;
    #[no_mangle] unsafe extern "C" fn cpu_disable_interrupt_save() -> u64 { 0x202 }
    #[no_mangle] unsafe extern "C" fn cpu_restore_interrupt(_:u64) {}
    #[no_mangle] unsafe extern "C" fn cpu_pause() { std::thread::yield_now(); }
    #[no_mangle] unsafe extern "C" fn map_fixed_area(phys:u64, bytes:u64, flags:u64) -> *mut c_void {
        assert_eq!(phys, RETAINED_PHYSICAL);
        assert_eq!(bytes, 128);
        assert_eq!(flags, 0);
        if FAIL_MAP.load(Ordering::Relaxed) { core::ptr::null_mut() } else { (&raw mut SLOTS).cast() }
    }
    unsafe extern "C" fn callback(_: *mut guest::LinuxIrqWork) {}
    #[no_mangle] unsafe extern "C" fn ihk_mc_ikc_arch_issue_host_ipi(_:i32, _:i32) -> i32 {
        let p = QUEUE.load(Ordering::Acquire);
        assert_eq!(p as u64, LINUX_PAGE_OFFSET + RETAINED_PHYSICAL);
        assert_ne!(p as u64, (&raw const SLOTS) as u64);
        assert_eq!((p as u64).checked_sub(LINUX_PAGE_OFFSET), Some(RETAINED_PHYSICAL));
        // Emulate Linux's mapping of the same retained physical page. The
        // high Linux list address must never be dereferenced by guest code.
        let alias = (&raw mut SLOTS).cast::<u8>();
        assert_eq!(guest::per_cpu_irq_work.cast::<u8>(), alias);
        assert_eq!((*alias.add(8).cast::<AtomicU32>()).load(Ordering::Acquire), 2);
        assert_eq!(alias.add(16).cast::<usize>().read(), callback as *const () as usize);
        assert!(alias.add(24).cast::<[u8; 40]>().read().iter().all(|byte| *byte == 0));
        if FAIL_IPI.load(Ordering::Relaxed) { return -5; }
        QUEUE.store(core::ptr::null_mut(), Ordering::Release);
        (*alias.add(8).cast::<AtomicU32>()).store(0, Ordering::Release);
        0
    }
    #[test]
    fn real_producer_mapping_publication_failure_and_close() { unsafe {
        boot_param = (&raw mut PARAMS).cast();
        let p = boot_param.cast::<u8>();
        p.add(24).cast::<i32>().write(8192);
        p.add(136).cast::<u64>().write(LINUX_PAGE_OFFSET);
        p.add(192).cast::<*const AtomicPtr<llist::LListNode>>().write(&QUEUE);
        p.add(4288).cast::<usize>().write(callback as *const () as usize);
        let descriptor = p.add(8192-64).cast::<guest::NativeIrqWorkDescriptor>();
        descriptor.write(guest::NativeIrqWorkDescriptor::unpublished(9, RETAINED_PHYSICAL, 2));
        assert_eq!(guest::ihk_mc_interrupt_host(0,0), -12);
        assert_eq!((*descriptor).state.load(Ordering::Acquire), 0);
        FAIL_MAP.store(false, Ordering::Relaxed);
        assert_eq!(guest::ihk_mc_interrupt_host(0,0), 0);
        assert_eq!((*descriptor).state.load(Ordering::Acquire), 1);
        assert_eq!((*descriptor).slots_phys, RETAINED_PHYSICAL);
        assert!(valid(&*descriptor));
        FAIL_IPI.store(true, Ordering::Relaxed);
        assert_eq!(guest::ihk_mc_interrupt_host(0,0), -5);
        let retained = QUEUE.load(Ordering::Acquire);
        assert_eq!(retained as u64, LINUX_PAGE_OFFSET + RETAINED_PHYSICAL);
        assert!(close_native_irq_work_senders(host(&*descriptor), || false));
        assert_eq!(guest::ihk_mc_interrupt_host(0,0), -16);
        assert_eq!(QUEUE.load(Ordering::Acquire), retained);
        assert_eq!((*(&raw const SLOTS).cast::<u8>().add(8).cast::<AtomicU32>()).load(Ordering::Acquire), 2);
        assert_eq!((*descriptor).slots_phys, RETAINED_PHYSICAL);
    } }
}
