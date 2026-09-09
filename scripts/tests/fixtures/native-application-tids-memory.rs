// SPDX-License-Identifier: GPL-2.0
//! Actual native zeroing/ledger/mapping bodies with controlled Linux providers.
#![allow(dead_code)]
extern crate self as kernel;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Error(i32);
pub type Result<T = ()> = std::result::Result<T, Error>;
pub const EINVAL: Error = Error(-22);
pub const EBUSY: Error = Error(-16);
pub const EIO: Error = Error(-5);
pub const ENOMEM: Error = Error(-12);
pub const EAGAIN: Error = Error(-11);
fn errno(code: i32) -> Error {
    Error(code)
}
thread_local! {
    static ALLOC_LEFT: std::cell::Cell<isize> = const { std::cell::Cell::new(-1) };
    static SLEEP_HOOK: std::cell::RefCell<Option<Box<dyn FnOnce()>>> = const { std::cell::RefCell::new(None) };
}
pub mod prelude {
    pub use crate::{Error, Result, EAGAIN, EBUSY, EINVAL, EIO, ENOMEM};
    pub const GFP_KERNEL: u32 = 0;
    pub struct Vec<T>(pub std::vec::Vec<T>);
    impl<T> Vec<T> {
        pub fn new() -> Self {
            Self(std::vec::Vec::new())
        }
        pub fn as_slice(&self) -> &[T] {
            self.0.as_slice()
        }
        pub fn with_capacity(n: usize, _: u32) -> Result<Self> {
            Ok(Self(std::vec::Vec::with_capacity(n)))
        }
        pub fn push(&mut self, value: T, _: u32) -> Result {
            crate::ALLOC_LEFT.with(|left| {
                let count = left.get();
                if count == 0 {
                    return Err(ENOMEM);
                }
                if count > 0 {
                    left.set(count - 1);
                }
                self.0.try_reserve(1).map_err(|_| ENOMEM)?;
                self.0.push(value);
                Ok(())
            })
        }
        pub fn swap_remove(&mut self, index: usize) -> T {
            self.0.swap_remove(index)
        }
        pub fn remove(&mut self, index: usize) -> T {
            self.0.remove(index)
        }
    }
    impl<T> core::ops::Deref for Vec<T> {
        type Target = [T];
        fn deref(&self) -> &[T] {
            &self.0
        }
    }
    impl<T> core::ops::DerefMut for Vec<T> {
        fn deref_mut(&mut self) -> &mut [T] {
            &mut self.0
        }
    }
    impl<'a, T> IntoIterator for &'a Vec<T> {
        type Item = &'a T;
        type IntoIter = core::slice::Iter<'a, T>;
        fn into_iter(self) -> Self::IntoIter {
            self.0.iter()
        }
    }
}
pub mod sync {
    pub struct Mutex<T>(pub std::sync::Mutex<T>);
    impl<T> Mutex<T> {
        pub fn new(value: T) -> Self {
            Self(std::sync::Mutex::new(value))
        }
        pub fn lock(&self) -> std::sync::MutexGuard<'_, T> {
            self.0.lock().unwrap()
        }
    }
}
pub mod bindings {
    pub unsafe fn msleep(_: u32) {
        let hook = crate::SLEEP_HOOK.with(|slot| slot.borrow_mut().take());
        if let Some(hook) = hook {
            hook();
        }
        std::thread::yield_now();
    }
}
#[path = "smp_resource.rs"]
mod smp_resource;
#[path = "smp_image.rs"]
mod smp_image;
#[path = "ihk_mapping.rs"]
mod ihk_mapping;
#[path = "zero_pages.rs"]
mod zero_pages;

#[path = "application_rpc.rs"]
mod application_rpc;
#[path = "application_syscall.rs"]
mod application_syscall;
#[path = "application_pager.rs"]
mod application_pager;

mod memory {
    use super::{errno, smp_resource, EBUSY, EINVAL, EIO};
    use crate::application_syscall::{
        Request as SyscallRequest, Response, ResponseMemory, RESPONSE_BYTES,
    };
    use crate::smp_resource::{MemoryExtent, MemoryMap};
    use core::ptr;
    use core::sync::atomic::{AtomicI32, AtomicU64, Ordering};
    use kernel::{prelude::*, sync::Mutex};
    use std::alloc::{alloc, dealloc, Layout};
    use std::sync::Arc;
    const MAX_EXTENTS: usize = 4;
    const CONTROL_PACKET_BYTES: usize = 128;
    const METADATA_CAPACITY: usize = 64;
    use crate::smp_image::IDENTITY_WINDOW_END;
    use crate::smp_resource::OsToken;
    use crate::zero_pages;
    include!("native-application-zeroing-memory-bodies.rs");
    #[path = "sysfs_zeroing.rs"]
    mod zeroing;

    const BASE: u64 = 0x1000000;
    const BYTES: usize = 16 << 20;
    const CHUNKS: u64 = BASE + (10 << 20);
    struct Arena {
        memory: Memory,
        storage: *mut u8,
        allocation: Layout,
        node: u64,
        request: zero_pages::Request,
    }
    impl Arena {
        fn new() -> Self {
            let allocation = Layout::from_size_align(BYTES + 8192, 4096).unwrap();
            let storage = unsafe { alloc(allocation) };
            assert!(!storage.is_null());
            unsafe {
                storage.write_bytes(0xa5, allocation.size());
            }
            let direct_map = storage as u64 + 4096 - BASE;
            let owner = unsafe { OsToken::from_ihk_lease_v2(2, 3).unwrap() };
            let mut map = MemoryMap::<4>::new();
            let mut slots = [None; 4];
            let mut workspace = smp_resource::MemoryWorkspace::new(&mut slots).unwrap();
            map.insert_free(BASE, BYTES as u64, 0, &mut workspace)
                .unwrap();
            map.assign(owner, BASE, BYTES as u64, &mut workspace)
                .unwrap();
            let layout = crate::smp_image::BootLayout::select(&map, owner).unwrap();
            let mut extents = Vec::new();
            extents.push(map.extent(0).unwrap(), GFP_KERNEL).unwrap();
            let memory = Memory {
                owner,
                direct_map,
                extents,
                layout,
                numa_nodes: 1,
                ledger: Mutex::new(Ledger {
                    fixed: Vec::new(),
                    requests: Vec::new(),
                    responses: Vec::new(),
                    payloads: Vec::new(),
                    snoops: Vec::new(),
                    procfs: Vec::new(),
                    zeroing: Vec::new(),
                    serial: 0,
                }),
            };
            let node = direct_map + layout.kernel().start() + 64;
            unsafe {
                (node as *mut u8).write_bytes(0, 256);
            }
            let request = zero_pages::Request {
                cpu: 0,
                pid: 12345,
                node: crate::smp_image::KERNEL_BASE + 64,
            };
            Self {
                memory,
                storage,
                allocation,
                node,
                request,
            }
        }
        unsafe fn counter(&self, offset: u64) -> &AtomicI32 {
            AtomicI32::from_ptr((self.node + offset) as *mut i32)
        }
        unsafe fn head(&self, offset: u64) -> &AtomicU64 {
            AtomicU64::from_ptr((self.node + offset) as *mut u64)
        }
        fn chunk(&self, physical: u64, pages: usize, next: u64) -> u64 {
            let address = self.memory.direct_map + physical;
            unsafe {
                (address as *mut u8).write_bytes(0xa5, pages * 4096);
                (address as *mut u64).write(physical);
                ((address + 8) as *mut u64).write((pages * 4096) as u64);
                ((address + 40) as *mut u64).write(next);
            }
            address + 40
        }
        fn start(&self, first: u64, pages: i32) {
            unsafe {
                self.counter(40).store(1, Ordering::SeqCst);
                self.counter(44).store(pages, Ordering::SeqCst);
                self.head(48).store(0, Ordering::SeqCst);
                self.head(56).store(first, Ordering::SeqCst);
            }
        }
        fn body(&self, physical: u64, pages: usize, expected: u8) {
            unsafe {
                assert!(core::slice::from_raw_parts(
                    (self.memory.direct_map + physical + 48) as *const u8,
                    pages * 4096 - 48
                )
                .iter()
                .all(|v| *v == expected));
            }
        }
        fn counts(&self) -> (i32, i32, u64, u64) {
            unsafe {
                (
                    self.counter(40).load(Ordering::Acquire),
                    self.counter(44).load(Ordering::Acquire),
                    self.head(48).load(Ordering::Acquire),
                    self.head(56).load(Ordering::Acquire),
                )
            }
        }
        fn guards(&self) {
            unsafe {
                assert!(core::slice::from_raw_parts(self.storage, 4096)
                    .iter()
                    .all(|v| *v == 0xa5));
                assert!(
                    core::slice::from_raw_parts(self.storage.add(4096 + BYTES), 4096)
                        .iter()
                        .all(|v| *v == 0xa5)
                );
            }
        }
    }
    impl Drop for Arena {
        fn drop(&mut self) {
            self.guards();
            unsafe {
                dealloc(self.storage, self.allocation);
            }
        }
    }

    #[test]
    fn zero_service_clears_owned_union_preserves_headers_and_finishes_one_worker() {
        let mut arena = Arena::new();
        let split = CHUNKS + 4096;
        let owner = Some(arena.memory.owner);
        arena.memory.extents = Vec::new();
        for (start, end, node) in [(BASE, split, 0), (split, BASE + BYTES as u64, 1)] {
            arena
                .memory
                .extents
                .push(
                    MemoryExtent::new(start, end - start, node, owner).unwrap(),
                    GFP_KERNEL,
                )
                .unwrap();
        }
        let first = arena.chunk(CHUNKS, 2, 0);
        let original =
            unsafe { core::slice::from_raw_parts((first - 40) as *const u8, 40).to_vec() };
        arena.start(first, 2);
        assert!(arena.memory.address(CHUNKS, 8192).is_err());
        let done = arena.memory.zero(arena.request).unwrap();
        assert_eq!(
            (done.chunks, done.pages, done.pending, done.workers),
            (1, 2, 0, 0)
        );
        assert_eq!(arena.counts(), (0, 0, first, 0));
        assert_eq!(
            unsafe { core::slice::from_raw_parts((first - 40) as *const u8, 40) },
            original
        );
        arena.body(CHUNKS, 2, 0);
        assert!(arena.memory.ledger.lock().zeroing.is_empty());
        assert!(arena.memory.address(CHUNKS, 8192).is_err());
    }

    #[test]
    fn zero_service_rejects_gap_foreign_generation_and_complete_node_overlap() {
        for foreign in [false, true] {
            let mut arena = Arena::new();
            let split = CHUNKS + 4096;
            arena.memory.extents = Vec::new();
            arena
                .memory
                .extents
                .push(
                    MemoryExtent::new(BASE, split - BASE, 0, Some(arena.memory.owner)).unwrap(),
                    GFP_KERNEL,
                )
                .unwrap();
            if foreign {
                let owner = unsafe { OsToken::from_ihk_lease_v2(2, 4).unwrap() };
                arena
                    .memory
                    .extents
                    .push(
                        MemoryExtent::new(split, BASE + BYTES as u64 - split, 0, Some(owner))
                            .unwrap(),
                        GFP_KERNEL,
                    )
                    .unwrap();
            }
            let first = arena.chunk(CHUNKS, 2, 0);
            arena.start(first, 2);
            assert_eq!(arena.memory.zero(arena.request).err(), Some(EINVAL));
            assert_eq!(arena.counts(), (1, 2, 0, 0));
            arena.body(CHUNKS, 2, 0xa5);
        }
        let mut arena = Arena::new();
        arena.node = arena.memory.direct_map + arena.memory.layout.kernel().start() + 0xf40;
        arena.request.node = crate::smp_image::KERNEL_BASE + 0xf40;
        unsafe {
            (arena.node as *mut u8).write_bytes(0, 256);
        }
        let physical = arena.memory.layout.kernel().start() + 4096;
        let first = arena.chunk(physical, 1, 0);
        arena.start(first, 1);
        assert_eq!(arena.memory.zero(arena.request).err(), Some(EBUSY));
        assert_eq!(arena.counts(), (1, 1, 0, 0));
        arena.body(physical, 1, 0xa5);
    }

    #[test]
    fn zero_service_preflights_entire_chain_before_any_zero_or_publication() {
        for malformed in 0..4 {
            let arena = Arena::new();
            let second = arena.chunk(CHUNKS + 8192, 1, 0);
            let first = arena.chunk(CHUNKS, 1, second);
            unsafe {
                match malformed {
                    0 => (second as *mut u64).write(first),
                    1 => ((second - 32) as *mut u64).write(0),
                    2 => ((second - 40) as *mut u64).write(CHUNKS),
                    _ => ((second - 32) as *mut u64).write(4097),
                }
            }
            arena.start(first, 2);
            assert!(arena.memory.zero(arena.request).is_err());
            assert_eq!(arena.counts(), (1, 2, 0, 0));
            arena.body(CHUNKS, 1, 0xa5);
            arena.body(CHUNKS + 8192, 1, 0xa5);
            assert_eq!(arena.memory.application_range(CHUNKS, 4096), Err(EBUSY));
        }
    }

    #[test]
    fn zero_service_excludes_every_existing_service_claim() {
        for kind in 0..7 {
            let arena = Arena::new();
            let first = arena.chunk(CHUNKS, 1, 0);
            arena.start(first, 1);
            {
                let mut ledger = arena.memory.ledger.lock();
                let span = Span::new(CHUNKS, 4096).unwrap();
                let tag = ledger.tag(span).unwrap();
                match kind {
                    0 => ledger.fixed.push(span, GFP_KERNEL),
                    1 => ledger.requests.push(Some(tag), GFP_KERNEL),
                    2 => ledger.responses.push(Some(tag), GFP_KERNEL),
                    3 => ledger.payloads.push(Some(tag), GFP_KERNEL),
                    4 => ledger.snoops.push(tag, GFP_KERNEL),
                    5 => ledger.procfs.push(tag, GFP_KERNEL),
                    _ => ledger.zeroing.push(tag, GFP_KERNEL),
                }
                .unwrap();
            }
            assert_eq!(arena.memory.zero(arena.request).err(), Some(EBUSY));
            assert_eq!(arena.counts(), (1, 1, 0, 0));
            arena.body(CHUNKS, 1, 0xa5);
        }
    }

    #[test]
    fn zero_service_allocation_failure_quarantines_without_partial_clearing() {
        for fail in 0..5 {
            let arena = Arena::new();
            let second = arena.chunk(CHUNKS + 8192, 1, 0);
            let first = arena.chunk(CHUNKS, 1, second);
            arena.start(first, 2);
            crate::ALLOC_LEFT.with(|left| left.set(fail));
            let result = arena.memory.zero(arena.request);
            crate::ALLOC_LEFT.with(|left| left.set(-1));
            assert_eq!(result.err(), Some(ENOMEM));
            assert_eq!(arena.counts(), (1, 2, 0, if fail == 0 { first } else { 0 }));
            arena.body(CHUNKS, 1, 0xa5);
            arena.body(CHUNKS + 8192, 1, 0xa5);
            if fail > 0 {
                assert!(!arena.memory.ledger.lock().zeroing.is_empty());
            }
        }
    }

    #[test]
    fn zero_service_yields_without_ledger_lock_and_leaves_late_arrivals_pending() {
        let arena = Arena::new();
        let first = arena.chunk(CHUNKS, 300, 0);
        arena.start(first, 300);
        let late = arena.chunk(BASE + (9 << 20), 1, 0);
        let memory_address = (&arena.memory as *const Memory) as usize;
        let node = arena.node;
        crate::SLEEP_HOOK.with(|hook| {
            *hook.borrow_mut() = Some(Box::new(move || {
                let memory = unsafe { &*(memory_address as *const Memory) };
                {
                    let ledger = memory.ledger.0.try_lock().unwrap();
                    assert_eq!(ledger.zeroing.len(), 2);
                }
                unsafe {
                    AtomicI32::from_ptr((node + 44) as *mut i32).fetch_add(1, Ordering::SeqCst);
                    AtomicU64::from_ptr((node + 56) as *mut u64).store(late, Ordering::Release);
                }
            }))
        });
        let done = arena.memory.zero(arena.request).unwrap();
        assert_eq!((done.pages, done.pending, done.workers), (300, 1, 0));
        assert_eq!(arena.counts(), (0, 1, first, late));
        arena.body(CHUNKS, 300, 0);
        arena.body(BASE + (9 << 20), 1, 0xa5);
        unsafe {
            arena.counter(40).store(1, Ordering::SeqCst);
        }
        let done = arena.memory.zero(arena.request).unwrap();
        assert_eq!((done.pages, done.pending, done.workers), (1, 0, 0));
        arena.body(BASE + (9 << 20), 1, 0);
    }

    #[test]
    fn zero_service_rejects_missing_worker_invalid_node_and_counter_underflow() {
        for bad in 0..4 {
            let arena = Arena::new();
            let first = arena.chunk(CHUNKS, 1, 0);
            arena.start(first, 1);
            let mut request = arena.request;
            unsafe {
                match bad {
                    0 => {
                        arena.counter(40).store(0, Ordering::SeqCst);
                    }
                    1 => {
                        (arena.node as *mut i32).write(1);
                    }
                    2 => {
                        arena.counter(44).store(0, Ordering::SeqCst);
                    }
                    _ => {
                        request.node = 0;
                    }
                }
            }
            assert_eq!(arena.memory.zero(request).err(), Some(EINVAL));
            arena.body(CHUNKS, 1, 0xa5);
            assert_eq!(arena.counts().2, 0);
        }
        let arena = Arena::new();
        arena.start(0, 0);
        unsafe {
            arena.counter(40).store(2, Ordering::SeqCst);
        }
        for workers in [1, 0] {
            let done = arena.memory.zero(arena.request).unwrap();
            assert_eq!((done.chunks, done.pages, done.workers), (0, 0, workers));
        }
        assert_eq!(arena.memory.zero(arena.request).err(), Some(EINVAL));
    }

    #[test]
    fn zero_service_concurrent_allocator_reuses_published_metadata_immediately() {
        const COUNT: usize = 512;
        let arena = Arena::new();
        let mut first = 0;
        for i in (0..COUNT).rev() {
            first = arena.chunk(CHUNKS + i as u64 * 4096, 1, first);
        }
        arena.start(first, COUNT as i32);
        let node = arena.node;
        let direct = arena.memory.direct_map;
        std::thread::scope(|scope| {
            let allocator = scope.spawn(move || {
                let mut seen = std::collections::BTreeSet::new();
                while seen.len() != COUNT {
                    let mut link = unsafe { AtomicU64::from_ptr((node + 48) as *mut u64) }
                        .swap(0, Ordering::SeqCst);
                    while link != 0 {
                        unsafe {
                            let address = link - 40;
                            let next = (link as *const u64).read();
                            let physical = (address as *const u64).read();
                            assert_eq!(address, direct + physical);
                            let index = (physical - CHUNKS) / 4096;
                            assert!(index < COUNT as u64 && seen.insert(index));
                            assert!(core::slice::from_raw_parts(
                                (address + 48) as *const u8,
                                4096 - 48
                            )
                            .iter()
                            .all(|v| *v == 0));
                            (address as *mut u8).write_bytes(0xef, 48);
                            link = next;
                        }
                    }
                    std::thread::yield_now();
                }
            });
            let done = arena.memory.zero(arena.request).unwrap();
            assert_eq!(
                (done.chunks, done.pages, done.pending, done.workers),
                (COUNT, COUNT as i32, 0, 0)
            );
            allocator.join().unwrap();
        });
        assert_eq!(arena.counts(), (0, 0, 0, 0));
        assert!(arena.memory.ledger.lock().zeroing.is_empty());
        for i in 0..COUNT {
            arena.body(CHUNKS + i as u64 * 4096, 1, 0);
        }
    }

    #[test]
    fn zero_service_bounded_admission_preserves_unaccepted_packet_and_rejects_old_marker() {
        let pending = Mutex::new(Vec::with_capacity(METADATA_CAPACITY, GFP_KERNEL).unwrap());
        let mut packet = [0u8; CONTROL_PACKET_BYTES];
        packet[8..12].copy_from_slice(&4i32.to_le_bytes());
        packet[32..36].copy_from_slice(&12345i32.to_le_bytes());
        packet[56..64].copy_from_slice(&1u64.to_le_bytes());
        packet[64..72].copy_from_slice(&279u64.to_le_bytes());
        packet[72..80].copy_from_slice(&(crate::smp_image::KERNEL_BASE + 64).to_le_bytes());
        assert_eq!(admit_zeroing(&pending, &packet, 1), Err(EINVAL));
        assert!(pending.lock().is_empty());
        packet[80..88].copy_from_slice(&zero_pages::BATCH_MARKER.to_le_bytes());
        let original = packet;
        for _ in 0..METADATA_CAPACITY {
            admit_zeroing(&pending, &packet, 1).unwrap();
        }
        for _ in 0..1024 {
            assert_eq!(admit_zeroing(&pending, &packet, 1), Err(EAGAIN));
            assert_eq!(packet, original);
        }
        assert_eq!(pending.lock().len(), 64);
        pending.lock().remove(0);
        admit_zeroing(&pending, &packet, 1).unwrap();
        assert_eq!(pending.lock().len(), 64);
    }

    fn tid_request(physical: u64, count: u64) -> SyscallRequest {
        let mut packet = [0u8; 128];
        packet[8..12].copy_from_slice(&4i32.to_le_bytes());
        packet[32..36].copy_from_slice(&12345i32.to_le_bytes());
        packet[48..52].copy_from_slice(&12345i32.to_le_bytes());
        packet[56..64].copy_from_slice(&1u64.to_le_bytes());
        packet[64..72].copy_from_slice(&186u64.to_le_bytes());
        packet[104..112].copy_from_slice(&count.to_le_bytes());
        packet[112..120].copy_from_slice(&physical.to_le_bytes());
        packet[120..128].copy_from_slice(&(BASE + 4096).to_le_bytes());
        SyscallRequest::decode(&packet, 1).unwrap()
    }

    // A separate retained view of this guarded arena, with the complete actual
    // ownership fields and ledger. Arena keeps the backing allocation alive
    // until every synthetic response and callback finishes.
    fn tid_memory(arena: &Arena) -> Arc<Memory> {
        let mut extents = Vec::new();
        for extent in arena.memory.extents.iter() {
            extents.push(*extent, GFP_KERNEL).unwrap();
        }
        let mut responses = Vec::new();
        let mut payloads = Vec::new();
        for _ in 0..2 {
            responses.push(None, GFP_KERNEL).unwrap();
            payloads.push(None, GFP_KERNEL).unwrap();
        }
        let memory = Arc::new(Memory {
            owner: arena.memory.owner,
            direct_map: arena.memory.direct_map,
            extents,
            layout: arena.memory.layout,
            numa_nodes: 1,
            ledger: Mutex::new(Ledger {
                fixed: Vec::new(),
                requests: Vec::new(),
                responses,
                payloads,
                snoops: Vec::new(),
                procfs: Vec::new(),
                zeroing: Vec::new(),
                serial: 0,
            }),
        });
        unsafe {
            let response = (memory.direct_map + BASE + 4096) as *mut u8;
            response.write_bytes(0, RESPONSE_BYTES);
            AtomicU64::from_ptr(response.add(16).cast()).store(2, Ordering::Release);
        }
        memory
    }

    #[test]
    fn tid_payload_retained_through_blocked_publication_and_exact_copy_guards() {
        let arena = Arena::new();
        let memory = tid_memory(&arena);
        let request = tid_request(CHUNKS + 64, 128);
        let mut response = memory.syscall(&request).unwrap();
        let mut data: std::vec::Vec<u8> = (0..512).map(|i| (i * 17) as u8).collect();
        response.copy_tids(&request, &mut data).unwrap();
        let address = (memory.direct_map + CHUNKS + 64) as *const u8;
        unsafe {
            assert_eq!(core::slice::from_raw_parts(address, 512), data);
            assert_eq!(core::slice::from_raw_parts(address.sub(16), 16), [0xa5; 16]);
            assert_eq!(
                core::slice::from_raw_parts(address.add(512), 16),
                [0xa5; 16]
            );
        }
        assert_eq!(response.copy_tids(&request, &mut [0x33; 512]), Err(EBUSY));
        assert!(memory
            .ledger
            .lock()
            .conflicts(Span::new(CHUNKS + 64, 512).unwrap(), true));
        let response = Response::from_memory(&request, response).unwrap();
        let mut completion = response.prepare(900, 0).unwrap();
        for _ in 0..1024 {
            assert_eq!(completion.publish(|_| Err(-11)), Err(-11));
            assert!(memory.ledger.lock().responses[0].is_some());
            assert!(memory.ledger.lock().payloads[0].is_some());
        }
        completion.publish(|_| Ok(())).unwrap();
        assert!(memory.ledger.lock().responses[0].is_none());
        assert!(memory.ledger.lock().payloads[0].is_none());
        unsafe {
            assert_eq!(core::slice::from_raw_parts(address, 512), data);
        }
    }

    #[test]
    fn tid_payload_rejects_every_existing_claim_class_before_write() {
        for kind in 0..7 {
            let arena = Arena::new();
            let memory = tid_memory(&arena);
            let request = tid_request(CHUNKS + 64, 128);
            let mut response = memory.syscall(&request).unwrap();
            {
                let mut ledger = memory.ledger.lock();
                let span = Span::new(CHUNKS + 128, 4).unwrap();
                let tag = ledger.tag(span).unwrap();
                match kind {
                    0 => ledger.fixed.push(span, GFP_KERNEL).unwrap(),
                    1 => ledger.requests.push(Some(tag), GFP_KERNEL).unwrap(),
                    2 => ledger.responses[1] = Some(tag),
                    3 => ledger.payloads[1] = Some(tag),
                    4 => ledger.snoops.push(tag, GFP_KERNEL).unwrap(),
                    5 => ledger.procfs.push(tag, GFP_KERNEL).unwrap(),
                    6 => ledger.zeroing.push(tag, GFP_KERNEL).unwrap(),
                    _ => unreachable!(),
                }
            }
            assert_eq!(response.copy_tids(&request, &mut [0x33; 512]), Err(EBUSY));
            assert!(memory.ledger.lock().payloads[0].is_none());
            unsafe {
                assert_eq!(
                    core::slice::from_raw_parts(
                        (memory.direct_map + CHUNKS + 64) as *const u8,
                        512
                    ),
                    [0xa5; 512]
                );
            }
            Response::from_memory(&request, response)
                .unwrap()
                .prepare(900, -14)
                .unwrap()
                .publish(|_| Ok(()))
                .unwrap();
            assert!(memory.ledger.lock().responses[0].is_none());
        }
    }

    #[test]
    fn tid_payload_rejects_extent_and_descriptor_errors_without_claim() {
        for (physical, count, length) in [
            (CHUNKS + 64, 128, 511),
            (CHUNKS + 65, 128, 512),
            (BASE + BYTES as u64 - 256, 128, 512),
            (BASE - 512, 128, 512),
        ] {
            let arena = Arena::new();
            let memory = tid_memory(&arena);
            let request = tid_request(physical, count);
            let mut response = memory.syscall(&request).unwrap();
            assert!(response
                .copy_tids(&request, &mut vec![0x33; length])
                .is_err());
            assert!(memory.ledger.lock().payloads[0].is_none());
            Response::from_memory(&request, response)
                .unwrap()
                .prepare(900, -14)
                .unwrap()
                .publish(|_| Ok(()))
                .unwrap();
        }
    }
}
