// SPDX-License-Identifier: GPL-2.0-only
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/abi/sysfs.rs"]
mod wire;
use std::{cell::UnsafeCell, sync::{Arc, atomic::{AtomicI32, AtomicUsize, Ordering}}, thread};
#[repr(align(4096))]
struct Page(UnsafeCell<[u8; 4096]>);
// SAFETY: The two peers hand off access through busy using release/acquire.
// The host never borrows the peer bytes and never accesses them after reply.
unsafe impl Sync for Page {}
impl Page {
    fn pointer(&self) -> *mut u8 { self.0.get().cast() }
    fn busy(&self) -> &AtomicI32 { unsafe { AtomicI32::from_ptr(self.pointer().add(1052).cast()) } }
}

#[test]
fn layout_matches_the_unchanged_legacy_c_header() {
    use std::mem::{align_of, offset_of, size_of};
    let expected: Vec<usize> = include_str!("native-sysfs-setup-layout.txt")
        .split_whitespace().map(|word| word.parse().unwrap()).collect();
    assert_eq!(expected, [size_of::<wire::SetupRequest>(), align_of::<wire::SetupRequest>(),
        offset_of!(wire::SetupRequest, error), offset_of!(wire::SetupRequest, physical),
        offset_of!(wire::SetupRequest, bytes), offset_of!(wire::SetupRequest, busy)]);
}

#[test]
fn malformed_fields_alignment_and_errno_do_not_publish_success() {
    let page = Page(UnsafeCell::new([0xa5; 4096]));
    let p = page.pointer();
    unsafe { p.add(8).cast::<u64>().write(4096); p.add(16).cast::<i64>().write(4096); }
    page.busy().store(1, Ordering::Release);
    assert_eq!(unsafe { wire::read_setup(p) }, Ok((4096, 4096)));
    for size in [-1, 0, 1, 4095, 4097, i64::MAX] {
        unsafe { p.add(16).cast::<i64>().write(size); }
        assert_eq!(unsafe { wire::read_setup(p) }, Err(-22));
        assert_eq!(page.busy().load(Ordering::Acquire), 1);
    }
    unsafe { p.add(16).cast::<i64>().write(4096); }
    for address in [0, 1, 4095, 4097, u64::MAX] {
        unsafe { p.add(8).cast::<u64>().write(address); }
        assert_eq!(unsafe { wire::read_setup(p) }, Err(-22));
    }
    for error in [1, i32::MAX, -4096, i32::MIN] {
        assert_eq!(unsafe { wire::complete_setup(p, error) }, Err(-22));
        assert_eq!(page.busy().load(Ordering::Acquire), 1);
    }
    assert_eq!(unsafe { wire::read_setup(p.add(1)) }, Err(-22));
    assert_eq!(unsafe { wire::complete_setup(p.add(1), 0) }, Err(-22));
    assert_eq!(unsafe { wire::read_setup(std::ptr::null_mut()) }, Err(-22));
    assert_eq!(unsafe { wire::complete_setup(std::ptr::null_mut(), 0) }, Err(-22));
    for error in [-4095, -22, -12, -5, -1, 0] {
        page.busy().store(1, Ordering::Release);
        unsafe { wire::complete_setup(p, error) }.unwrap();
        assert_eq!(page.busy().load(Ordering::Acquire), 0);
        assert_eq!(unsafe { p.cast::<i32>().read() }, error);
        assert_eq!(unsafe { wire::complete_setup(p, 0) }, Err(-16));
        assert_eq!(unsafe { p.cast::<i32>().read() }, error);
    }
}

#[test]
fn completion_publishes_owners_and_error_before_peer_can_reuse_request() {
    let page = Arc::new(Page(UnsafeCell::new([0xa5; 4096])));
    page.busy().store(0, Ordering::Release);
    let published = Arc::new(AtomicUsize::new(0));
    let peer = page.clone(); let owners = published.clone();
    let host = thread::spawn(move || {
        for iteration in 1..=4096 {
            while peer.busy().load(Ordering::Acquire) != 1 { thread::yield_now(); }
            assert_eq!(unsafe { wire::read_setup(peer.pointer()) }, Ok((iteration as u64 * 4096, 4096)));
            owners.store(iteration, Ordering::Relaxed);
            unsafe { wire::complete_setup(peer.pointer(), if iteration % 2 == 0 { 0 } else { -12 }) }.unwrap();
        }
    });
    for iteration in 1..=4096 {
        let p = page.pointer();
        unsafe { p.cast::<i32>().write(-115); p.add(8).cast::<u64>().write(iteration as u64 * 4096); p.add(16).cast::<i64>().write(4096); }
        page.busy().store(1, Ordering::Release);
        while page.busy().load(Ordering::Acquire) != 0 { thread::yield_now(); }
        assert_eq!(published.load(Ordering::Relaxed), iteration);
        assert_eq!(unsafe { p.cast::<i32>().read() }, if iteration % 2 == 0 { 0 } else { -12 });
        // Reuse immediately; the responder must perform no later request access.
        unsafe { p.cast::<i32>().write(0x55555555); }
    }
    host.join().unwrap();
    let bytes = unsafe { &*page.0.get() };
    assert!(bytes[24..1052].iter().all(|&byte| byte == 0xa5));
    assert!(bytes[1056..].iter().all(|&byte| byte == 0xa5));
}
