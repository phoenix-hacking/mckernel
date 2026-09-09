// SPDX-License-Identifier: GPL-2.0
//! Actual guest zeroing bodies and list operations, exact C oracle, guarded RAM.
#![allow(dead_code)] // Extracted allocator dependencies vary with the guest cfg.

#[allow(dead_code)]
#[path = "abi.rs"]
mod abi;
#[allow(dead_code)]
#[path = "zero_pages.rs"]
mod zero_pages;
#[allow(dead_code)]
#[path = "application_rpc.rs"]
mod application_rpc;
#[allow(dead_code)]
#[path = "application_syscall.rs"]
mod application_syscall;
#[path = "llist.rs"]
mod llist;

mod guest {
    #[cfg(native_linux_irq_work_v6_12)]
    use super::llist;
    use super::{abi, application_syscall, zero_pages};
    use abi::{CInt, CULong, IkcScdPacket, IkcScdPacketTraditional};
    use core::{
        ffi::c_void,
        mem::{align_of, offset_of, size_of},
        ptr::{null_mut, read_volatile, write_volatile},
        sync::atomic::{compiler_fence, AtomicI32, AtomicPtr, Ordering},
    };
    use std::alloc::{alloc, dealloc, Layout};
    #[cfg(native_linux_irq_work_v6_12)]
    use std::{cell::RefCell, collections::BTreeSet, sync::atomic::AtomicBool};

    #[cfg(native_linux_irq_work_v6_12)]
    thread_local! {
        static ZERO_HOOK: RefCell<Option<Box<dyn FnOnce()>>> = const { RefCell::new(None) };
    }
    unsafe fn phys_to_virt(address: CULong) -> *mut c_void {
        #[cfg(native_linux_irq_work_v6_12)]
        {
            let hook = ZERO_HOOK.with(|slot| slot.borrow_mut().take());
            if let Some(hook) = hook {
                hook();
            }
        }
        address as *mut c_void
    }

    include!("native-application-zeroing-bodies.rs");

    struct Arena {
        storage: *mut u8,
        layout: Layout,
        pages: usize,
    }
    impl Arena {
        fn new(pages: usize, id: usize) -> Self {
            let layout = Layout::from_size_align((pages + 2) * 4096, 4096).unwrap();
            let storage = unsafe { alloc(layout) };
            assert!(!storage.is_null());
            unsafe {
                storage.write_bytes(0xa5, layout.size());
            }
            let result = Self {
                storage,
                layout,
                pages,
            };
            unsafe {
                result.chunk().write(core::mem::zeroed());
                (*result.chunk()).addr = result.chunk() as u64;
                (*result.chunk()).size = (pages * 4096) as u64;
                (*result.chunk()).node.__rb_parent_color = id as u64;
            }
            result
        }
        fn chunk(&self) -> *mut FreeChunk {
            unsafe { self.storage.add(4096).cast() }
        }
        unsafe fn enqueue(&self, node: *mut IhkMcNumaNode) {
            atomic_counter(&raw mut (*node).nr_to_zero_pages)
                .fetch_add(self.pages as i32, Ordering::SeqCst);
            llist_add(chunk_list(self.chunk()), &raw mut (*node).to_zero_list);
        }
        fn check(&self, id: usize, metadata: bool) -> bool {
            unsafe {
                let bytes = core::slice::from_raw_parts(self.storage, self.layout.size());
                assert!(bytes[..4096].iter().all(|v| *v == 0xa5));
                assert!(bytes[(self.pages + 1) * 4096..].iter().all(|v| *v == 0xa5));
                let body = &bytes[4096 + size_of::<FreeChunk>()..(self.pages + 1) * 4096];
                let value = body[0];
                assert!(value == 0 || value == 0xa5);
                assert!(body.iter().all(|v| *v == value));
                if metadata {
                    let chunk = &*self.chunk();
                    assert_eq!(chunk.addr, self.chunk() as u64);
                    assert_eq!(chunk.size, (self.pages * 4096) as u64);
                    assert_eq!(chunk.node.__rb_parent_color, id as u64);
                    assert!(chunk.node.rb_left.is_null() && chunk.node.rb_right.is_null());
                }
                value == 0
            }
        }
    }
    impl Drop for Arena {
        fn drop(&mut self) {
            unsafe {
                dealloc(self.storage, self.layout);
            }
        }
    }
    unsafe fn chain(head: *mut LListHead) -> u64 {
        let mut node = (*head).first;
        let mut value = 0;
        while !node.is_null() {
            value = value * 10 + (*list_to_chunk(node)).node.__rb_parent_color;
            node = (*node).next;
        }
        value
    }
    fn empty_node() -> Box<IhkMcNumaNode> {
        Box::new(unsafe { core::mem::zeroed() })
    }

    #[test]
    fn exact_c_layout_and_first_fit_zeroing_match_both_selections() {
        let output = include_str!("c-reference.log");
        let layout: Vec<usize> = output
            .lines()
            .next()
            .unwrap()
            .split_whitespace()
            .skip(1)
            .map(|s| s.parse().unwrap())
            .collect();
        assert_eq!(
            layout,
            [
                size_of::<FreeChunk>(),
                offset_of!(FreeChunk, list),
                size_of::<IhkMcNumaNode>(),
                align_of::<IhkMcNumaNode>(),
                offset_of!(IhkMcNumaNode, zeroing_workers),
                offset_of!(IhkMcNumaNode, nr_to_zero_pages),
                offset_of!(IhkMcNumaNode, zeroed_list),
                offset_of!(IhkMcNumaNode, to_zero_list)
            ]
        );
        assert_eq!(layout, [48, 40, 256, 64, 40, 44, 48, 56]);
        let patterns: &[&[usize]] = &[&[], &[1], &[1, 3, 2, 4], &[2, 1, 1], &[4, 2, 1]];
        let rows: Vec<_> = output
            .lines()
            .filter(|line| line.starts_with("ZERO "))
            .collect();
        assert_eq!(rows.len(), 30);
        for row in rows {
            let values: Vec<i64> = row
                .split_whitespace()
                .skip(1)
                .map(|s| s.parse().unwrap())
                .collect();
            let pattern = patterns[values[0] as usize];
            let chunks: Vec<_> = pattern
                .iter()
                .enumerate()
                .map(|(i, pages)| Arena::new(*pages, i + 1))
                .collect();
            let mut node = empty_node();
            for chunk in chunks.iter().rev() {
                unsafe {
                    chunk.enqueue(&mut *node);
                }
            }
            let count = unsafe { __ihk_numa_zero_free_pages_node(&mut *node, values[1] as i32) };
            let cleared = chunks.iter().enumerate().fold(0, |mask, (i, chunk)| {
                mask | ((chunk.check(i + 1, true) as i64) << i)
            });
            let actual = unsafe {
                [
                    count as i64,
                    node.nr_to_zero_pages.counter as i64,
                    chain(&raw mut node.to_zero_list) as i64,
                    chain(&raw mut node.zeroed_list) as i64,
                    cleared,
                ]
            };
            assert_eq!(&values[2..], actual, "{row}");
        }
        assert_eq!(unsafe { __ihk_numa_zero_free_pages_node(null_mut(), 0) }, 0);
    }

    fn producer(index: usize) -> [u8; 128] {
        let mut packet: IkcScdPacket = unsafe { core::mem::zeroed() };
        unsafe {
            __ihk_numa_zero_request_packet_fill(
                &mut packet,
                0xfffffffffe910040 + index as u64 * 256,
                index as i32,
                307 + index as i32,
                if index == 5 { 0x12345678 } else { 279 },
            );
        }
        unsafe { core::mem::transmute(packet) }
    }

    #[test]
    fn exact_old_and_native_producers_keep_ordinary_decoder_strict() {
        let rows: Vec<_> = include_str!("c-reference.log")
            .lines()
            .filter_map(|line| line.strip_prefix("PACKET "))
            .collect();
        assert_eq!(rows.len(), 6);
        for (index, row) in rows.iter().enumerate() {
            let mut expected: Vec<u8> = row
                .as_bytes()
                .chunks_exact(2)
                .map(|b| u8::from_str_radix(core::str::from_utf8(b).unwrap(), 16).unwrap())
                .collect();
            let actual = producer(index);
            if cfg!(native_linux_irq_work_v6_12) && index != 5 {
                expected[80..88].copy_from_slice(&zero_pages::BATCH_MARKER.to_le_bytes());
            }
            assert_eq!(actual.as_slice(), expected);
            assert!(application_syscall::Request::decode(&actual, 8).is_err());
            assert_eq!(zero_pages::Request::candidate(&actual), index != 5);
            assert_eq!(
                zero_pages::Request::decode(&actual, 8).is_ok(),
                cfg!(native_linux_irq_work_v6_12) && index != 5
            );
        }
    }

    #[test]
    fn wire_geometry_rejects_wrong_contract_owner_fields_and_wrapping_ranges() {
        let mut packet = producer(0);
        packet[80..88].copy_from_slice(&zero_pages::BATCH_MARKER.to_le_bytes());
        let request = zero_pages::Request::decode(&packet, 1).unwrap();
        assert_eq!(
            (request.cpu, request.pid, request.node),
            (0, 307, 0xfffffffffe910040)
        );
        let base = 0xfffffffffe800000;
        assert_eq!(
            request.node_physical(base, 0x2000000, 8 << 20),
            Ok(0x2110040)
        );
        assert!(request.node_physical(base, u64::MAX - 63, 8 << 20).is_err());
        for node in [
            base - 64,
            base + (8 << 20) - 192,
            base + (8 << 20),
            u64::MAX - 63,
        ] {
            assert!(zero_pages::Request { node, ..request }
                .node_physical(base, 0x2000000, 8 << 20)
                .is_err());
        }
        for (offset, bytes) in [
            (8, 4),
            (24, 4),
            (28, 4),
            (32, 4),
            (48, 4),
            (52, 4),
            (56, 8),
            (64, 8),
            (72, 8),
            (80, 8),
            (88, 8),
            (96, 8),
            (104, 8),
            (112, 8),
            (120, 8),
        ] {
            let mut bad = packet;
            bad[offset..offset + bytes].fill(0xff);
            assert!(
                zero_pages::Request::decode(&bad, 1).is_err(),
                "offset {offset}"
            );
        }
        for length in [0, 1, 127] {
            assert!(zero_pages::Request::decode(&packet[..length], 1).is_err());
        }
        assert!(zero_pages::Request::decode(&packet, 0).is_err());
        let direct = 0xffff888000000000;
        let physical = 0x234000;
        let link = direct + physical + 40;
        let chunk = zero_pages::Chunk::decode(link, direct, physical, 8192).unwrap();
        assert_eq!(
            (chunk.physical, chunk.bytes, chunk.pages),
            (physical, 8192, 2)
        );
        for bad in [0, direct - 1, direct + 39, direct + 40, link - 1, link + 1] {
            assert!(zero_pages::Chunk::header_physical(bad, direct).is_err());
        }
        for size in [0, 1, 4095, 4097, (i32::MAX as u64 + 1) * 4096, u64::MAX] {
            assert!(zero_pages::Chunk::decode(link, direct, physical, size).is_err());
        }
        assert!(zero_pages::Chunk::decode(link, direct, physical + 4096, 4096).is_err());
        assert!(zero_pages::Chunk::decode(u64::MAX - 4095 + 40, 0, u64::MAX - 4095, 4096).is_err());
        assert_eq!(
            (zero_pages::CONTROL_OFFSET, zero_pages::CONTROL_BYTES),
            (40, 24)
        );
    }

    #[cfg(native_linux_irq_work_v6_12)]
    #[test]
    fn native_reentrant_consumer_and_concurrent_arrival_preserve_owned_batch() {
        let mut node = empty_node();
        let chunks: Vec<_> = [1, 3, 2, 4]
            .iter()
            .enumerate()
            .map(|(i, p)| Arena::new(*p, i + 1))
            .collect();
        for chunk in chunks[..3].iter().rev() {
            unsafe {
                chunk.enqueue(&mut *node);
            }
        }
        let node_address = (&raw mut *node) as usize;
        let late = chunks[3].chunk() as usize;
        ZERO_HOOK.with(|slot| {
            *slot.borrow_mut() = Some(Box::new(move || unsafe {
                let node = node_address as *mut IhkMcNumaNode;
                atomic_counter(&raw mut (*node).nr_to_zero_pages).fetch_add(4, Ordering::SeqCst);
                llist_add(
                    chunk_list(late as *mut FreeChunk),
                    &raw mut (*node).to_zero_list,
                );
                assert_eq!(__ihk_numa_zero_free_pages_node(node, 0), 4);
            }))
        });
        assert_eq!(unsafe { __ihk_numa_zero_free_pages_node(&mut *node, 2) }, 3);
        assert_eq!(node.nr_to_zero_pages.counter, 3);
        assert_eq!(unsafe { chain(&raw mut node.to_zero_list) }, 13);
        assert_eq!(unsafe { chain(&raw mut node.zeroed_list) }, 24);
        for (i, chunk) in chunks.iter().enumerate() {
            assert_eq!(chunk.check(i + 1, true), i == 1 || i == 3);
        }

        let mut node = empty_node();
        let first = Arena::new(1, 1);
        let late = Arena::new(1, 2);
        unsafe {
            first.enqueue(&mut *node);
        }
        let node_address = (&raw mut *node) as usize;
        let late_address = late.chunk() as usize;
        ZERO_HOOK.with(|slot| {
            *slot.borrow_mut() = Some(Box::new(move || unsafe {
                let node = node_address as *mut IhkMcNumaNode;
                atomic_counter(&raw mut (*node).nr_to_zero_pages).fetch_add(1, Ordering::SeqCst);
                llist_add(
                    chunk_list(late_address as *mut FreeChunk),
                    &raw mut (*node).to_zero_list,
                );
            }))
        });
        assert_eq!(unsafe { __ihk_numa_zero_free_pages_node(&mut *node, 0) }, 1);
        assert_eq!(node.nr_to_zero_pages.counter, 1);
        assert_eq!(unsafe { chain(&raw mut node.to_zero_list) }, 2);
        assert!(first.check(1, true));
        assert!(!late.check(2, true));
        assert_eq!(
            unsafe { __ihk_numa_zero_free_pages_node(&mut *node, -1) },
            1
        );
    }

    #[cfg(native_linux_irq_work_v6_12)]
    #[test]
    fn three_native_consumers_and_immediate_allocator_reuse_never_share_a_chunk() {
        const COUNT: usize = 2048;
        let chunks: Vec<_> = (0..COUNT).map(|i| Arena::new(1, i + 1)).collect();
        let mut node = empty_node();
        let address = (&raw mut *node) as usize;
        let done = AtomicBool::new(false);
        std::thread::scope(|scope| {
            let mut workers = Vec::new();
            for _ in 0..3 {
                let done = &done;
                workers.push(scope.spawn(move || {
                    let node = address as *mut IhkMcNumaNode;
                    let mut pages = 0;
                    loop {
                        pages += unsafe { __ihk_numa_zero_free_pages_node(node, 0) };
                        if done.load(Ordering::Acquire)
                            && unsafe { llist_head_first(&raw mut (*node).to_zero_list) }
                                .load(Ordering::Acquire)
                                .is_null()
                        {
                            break;
                        }
                        std::thread::yield_now();
                    }
                    pages
                }));
            }
            let allocator = scope.spawn(move || {
                let node = address as *mut IhkMcNumaNode;
                let mut seen = BTreeSet::new();
                while seen.len() != COUNT {
                    let mut cursor = unsafe {
                        llist::llist_del_all((&raw mut (*node).zeroed_list).cast())
                            .cast::<LListNode>()
                    };
                    while !cursor.is_null() {
                        unsafe {
                            let link = cursor;
                            cursor = (*link).next;
                            let chunk = list_to_chunk(link);
                            let id = (*chunk).node.__rb_parent_color;
                            assert!(id > 0 && id <= COUNT as u64 && seen.insert(id));
                            assert!(core::slice::from_raw_parts(
                                chunk.cast::<u8>().add(48),
                                4096 - 48
                            )
                            .iter()
                            .all(|v| *v == 0));
                            // Actual ownership transfer permits immediate metadata reuse.
                            (*chunk).size = u64::MAX;
                            (*chunk).addr = 0;
                            (*link).next = usize::MAX as *mut LListNode;
                        }
                    }
                    std::thread::yield_now();
                }
            });
            for chunk in &chunks {
                unsafe {
                    chunk.enqueue(&mut *node);
                }
                std::thread::yield_now();
            }
            done.store(true, Ordering::Release);
            let pages: i32 = workers.into_iter().map(|w| w.join().unwrap()).sum();
            assert_eq!(pages, COUNT as i32);
            allocator.join().unwrap();
        });
        assert_eq!(node.nr_to_zero_pages.counter, 0);
        assert!(node.to_zero_list.first.is_null() && node.zeroed_list.first.is_null());
        for (i, chunk) in chunks.iter().enumerate() {
            assert!(chunk.check(i + 1, false));
        }
    }
}
