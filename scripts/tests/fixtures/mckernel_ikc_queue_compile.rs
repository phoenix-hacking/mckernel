// SPDX-License-Identifier: GPL-2.0
#![allow(dead_code)]

// Actual complete guest queue/list bodies and native host queue body. Only
// logging/address translation are stubs; unused channel services are discarded
// by the executable linker. The C reference uses the same sequential driver.
#[path = "../../../kernel/rust/abi.rs"]
mod guest_abi;
#[path = "../../../host-kernel/native-rust/abi/x86_64.rs"]
mod host_abi;
mod abi {
    pub use super::guest_abi::{CInt, CULong, IhkSpinlock};
    pub use super::host_abi::*;
}
#[path = "../../../kernel/rust/list_helpers.rs"]
mod list_helpers;
#[cfg(not(legacy_c_reference))]
#[path = "../../../kernel/rust/ikc_queue.rs"]
mod guest;
#[path = "../../../host-kernel/native-rust/ikc_queue.rs"]
mod host;

#[cfg(legacy_c_reference)]
mod guest {
    pub use super::host_abi::IhkIkcQueueHead;
    use core::ffi::c_void;
    pub type IhkIkcChannelDesc = c_void;
    pub type IkcPacketHandler =
        Option<unsafe extern "C" fn(*mut IhkIkcChannelDesc, *mut c_void, *mut c_void) -> i32>;
    unsafe extern "C" {
        pub fn ihk_ikc_init_queue(
            q: *mut IhkIkcQueueHead,
            id: i32,
            kind: i32,
            bytes: i32,
            packet: i32,
        ) -> i32;
        pub fn ihk_ikc_queue_is_empty(q: *mut IhkIkcQueueHead) -> i32;
        pub fn ihk_ikc_queue_is_full(q: *mut IhkIkcQueueHead) -> i32;
        pub fn ihk_ikc_write_queue(q: *mut IhkIkcQueueHead, packet: *mut c_void, flag: i32) -> i32;
        pub fn ihk_ikc_read_queue(q: *mut IhkIkcQueueHead, packet: *mut c_void, flag: i32) -> i32;
        pub fn ihk_ikc_read_queue_handler(
            q: *mut IhkIkcQueueHead,
            channel: *mut IhkIkcChannelDesc,
            handler: IkcPacketHandler,
            argument: *mut c_void,
            flag: i32,
        ) -> i32;
    }
}

use core::ffi::c_void;
use core::ptr::null_mut;
use host::{QueueError, SharedProducer, SharedQueue};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::time::{Duration, Instant};

core::arch::global_asm!(
    ".text",
    ".globl kprintf",
    ".type kprintf,@function",
    "kprintf:",
    "xor eax,eax",
    "ret",
    ".size kprintf,.-kprintf"
);
#[no_mangle]
extern "C" fn virt_to_phys(pointer: *mut c_void) -> u64 {
    pointer as u64
}

#[repr(C, align(64))]
struct Storage([u8; 576]);

fn packet(key: u64) -> [u64; 8] {
    core::array::from_fn(|index| key.rotate_left(index as u32 * 7) ^ index as u64)
}

fn bytes(value: &[u64; 8]) -> &[u8] {
    // SAFETY: Fully initialized word array, read-only byte view of its extent.
    unsafe { core::slice::from_raw_parts(value.as_ptr().cast(), 64) }
}

unsafe extern "C" fn copy_handler(
    _channel: *mut guest::IhkIkcChannelDesc,
    slot: *mut c_void,
    argument: *mut c_void,
) -> i32 {
    core::ptr::copy_nonoverlapping(slot.cast::<u64>(), argument.cast::<u64>(), 8);
    -999 // The public queue API preserves the original ignored callback result.
}

fn sequential() {
    let mut digest = 0xcbf29ce484222325u64;
    for count in [2, 3, 4, 8] {
        let mut storage = Storage([0; 576]);
        let q = storage.0.as_mut_ptr().cast::<guest::IhkIkcQueueHead>();
        unsafe {
            assert_eq!(guest::ihk_ikc_init_queue(q, 9, 3, 64 + count * 64, 64), 0);
            for round in 0..1024 {
                assert_eq!(guest::ihk_ikc_queue_is_empty(q), 1);
                for index in 0..count - 1 {
                    let mut sent = packet((round * 8 + index + 1) as u64);
                    assert_eq!(
                        guest::ihk_ikc_write_queue(q, sent.as_mut_ptr().cast(), 0),
                        0
                    );
                }
                assert_eq!(guest::ihk_ikc_queue_is_full(q), 1);
                assert_eq!(
                    guest::ihk_ikc_write_queue(q, packet(0).as_mut_ptr().cast(), 0),
                    -16
                );
                for index in 0..count - 1 {
                    let mut copied = [0u64; 8];
                    let result = if index % 2 == 0 {
                        guest::ihk_ikc_read_queue(q, copied.as_mut_ptr().cast(), 0)
                    } else {
                        guest::ihk_ikc_read_queue_handler(
                            q,
                            null_mut(),
                            Some(copy_handler),
                            copied.as_mut_ptr().cast(),
                            0,
                        )
                    };
                    assert_eq!(result, 0);
                    assert_eq!(copied, packet((round * 8 + index + 1) as u64));
                    for byte in bytes(&copied) {
                        digest = (digest ^ *byte as u64).wrapping_mul(0x100000001b3);
                    }
                }
                assert_eq!(
                    guest::ihk_ikc_read_queue(q, [0u64; 8].as_mut_ptr().cast(), 0),
                    -1
                );
            }
        }
    }
    println!("IKC_QUEUE sequential packets=13312 digest={digest:016x}");
}

#[cfg(native_linux_irq_work_v6_12)]
fn concurrent() {
    const EACH: usize = 4096;
    const TOTAL: usize = 4 * EACH;
    let mut storage = Storage([0; 576]);
    drop(SharedQueue::initialize(&mut storage.0, 0, 0, 64).unwrap());
    let address = storage.0.as_mut_ptr() as usize;
    // SAFETY: Stable aligned storage with no Rust aliases. The actual native
    // guest readers serialize and release only after their copy has completed.
    let sender = unsafe { SharedProducer::attach(address as *mut _, 576) }.unwrap();
    let completed = AtomicUsize::new(0);
    let seen: Vec<_> = (0..TOTAL).map(|_| AtomicBool::new(false)).collect();
    std::thread::scope(|scope| {
        for producer in 0..4 {
            let sender = &sender;
            scope.spawn(move || {
                for index in 0..EACH {
                    let value = packet((producer * EACH + index + 1) as u64);
                    loop {
                        match sender.try_enqueue(bytes(&value)) {
                            Ok(()) => break,
                            Err(QueueError::Full) => std::thread::yield_now(),
                            error => panic!("producer {error:?}"),
                        }
                    }
                }
            });
        }
        for _ in 0..4 {
            let completed = &completed;
            let seen = &seen;
            scope.spawn(move || {
                while completed.load(Ordering::Acquire) != TOTAL {
                    let mut copied = [0u64; 8];
                    let result = unsafe {
                        guest::ihk_ikc_read_queue(address as *mut _, copied.as_mut_ptr().cast(), 0)
                    };
                    match result {
                        0 => {
                            let key = copied[0] as usize;
                            assert!((1..=TOTAL).contains(&key));
                            assert_eq!(copied, packet(key as u64));
                            assert!(
                                !seen[key - 1].swap(true, Ordering::Relaxed),
                                "duplicate {key}"
                            );
                            completed.fetch_add(1, Ordering::Release);
                        }
                        -1 | -16 => std::thread::yield_now(),
                        error => panic!("consumer {error}"),
                    }
                }
            });
        }
    });
    assert!(seen.iter().all(|value| value.load(Ordering::Relaxed)));
    let state = sender.snapshot().unwrap();
    assert_eq!(
        (state.read, state.published, state.reserved),
        (TOTAL as u64, TOTAL as u64, TOTAL as u64)
    );
    println!("IKC_QUEUE concurrent producers=4 readers=4 packets={TOTAL} slots=8");
}

#[cfg(native_linux_irq_work_v6_12)]
struct Paused {
    address: usize,
    entered: AtomicBool,
    release: AtomicBool,
}

#[cfg(native_linux_irq_work_v6_12)]
unsafe extern "C" fn paused_handler(
    _channel: *mut guest::IhkIkcChannelDesc,
    slot: *mut c_void,
    argument: *mut c_void,
) -> i32 {
    let paused = &*argument.cast::<Paused>();
    assert_eq!(
        guest::ihk_ikc_read_queue(paused.address as *mut _, [0u64; 8].as_mut_ptr().cast(), 0),
        -16
    );
    paused.entered.store(true, Ordering::Release);
    while !paused.release.load(Ordering::Acquire) {
        std::thread::yield_now();
    }
    let mut copy = [0u64; 8];
    core::ptr::copy_nonoverlapping(slot.cast::<u64>(), copy.as_mut_ptr(), 8);
    assert_eq!(copy, packet(1));
    -999
}

#[cfg(native_linux_irq_work_v6_12)]
fn paused() {
    let mut storage = Storage([0; 576]);
    drop(SharedQueue::initialize(&mut storage.0[..192], 0, 0, 64).unwrap());
    let address = storage.0.as_mut_ptr() as usize;
    let sender = unsafe { SharedProducer::attach(address as *mut _, 192) }.unwrap();
    sender.try_enqueue(bytes(&packet(1))).unwrap();
    let paused = Paused {
        address,
        entered: AtomicBool::new(false),
        release: AtomicBool::new(false),
    };
    std::thread::scope(|scope| {
        let paused = &paused;
        scope.spawn(move || {
            assert_eq!(
                unsafe {
                    guest::ihk_ikc_read_queue_handler(
                        address as *mut _,
                        null_mut(),
                        Some(paused_handler),
                        (paused as *const Paused).cast_mut().cast(),
                        0,
                    )
                },
                0
            );
        });
        let deadline = Instant::now() + Duration::from_secs(5);
        while !paused.entered.load(Ordering::Acquire) {
            assert!(Instant::now() < deadline);
            std::thread::yield_now();
        }
        for _ in 0..1024 {
            assert_eq!(sender.snapshot().unwrap().read, 0);
            assert_eq!(sender.try_enqueue(bytes(&packet(2))), Err(QueueError::Full));
        }
        paused.release.store(true, Ordering::Release);
    });
    for key in 2..=257 {
        sender.try_enqueue(bytes(&packet(key))).unwrap();
        let mut copied = [0u64; 8];
        assert_eq!(
            unsafe { guest::ihk_ikc_read_queue(address as *mut _, copied.as_mut_ptr().cast(), 0) },
            0
        );
        assert_eq!(copied, packet(key));
    }
    assert_eq!(sender.snapshot().unwrap().read, 257);
    println!("IKC_QUEUE paused-handler blocked=1024 reentrant=busy reused=256");
}

#[cfg(native_linux_irq_work_v6_12)]
fn invalid() {
    let mut storage = Storage([0; 576]);
    drop(SharedQueue::initialize(&mut storage.0, 0, 0, 64).unwrap());
    let head = storage.0.as_mut_ptr().cast::<host_abi::IhkIkcQueueHead>();
    let q = head.cast::<guest::IhkIkcQueueHead>();
    let mut copied = [0u64; 8];
    unsafe {
        (*head).max_read_offset = 8;
        assert_eq!(
            guest::ihk_ikc_read_queue(q, copied.as_mut_ptr().cast(), 0),
            -117
        );
        assert_eq!((*head).reserved, 0);
        (*head).max_read_offset = 1;
        assert_eq!(guest::ihk_ikc_read_queue(q, q.cast(), 0), -22);
        assert_eq!((*head).read_offset, 0);
        assert_eq!((*head).reserved, 0);
        (*head).packet_count = 1;
        assert_eq!(
            guest::ihk_ikc_read_queue(q, copied.as_mut_ptr().cast(), 0),
            -22
        );
        (*head).packet_count = 8;
        (*head).queue_size -= 1;
        assert_eq!(
            guest::ihk_ikc_read_queue(q, copied.as_mut_ptr().cast(), 0),
            -22
        );
        assert_eq!((*head).reserved, 0);
    }
    println!("IKC_QUEUE invalid geometry=checked overlap=rejected claim=released");
}

fn main() {
    match std::env::args().nth(1).as_deref() {
        None => sequential(),
        #[cfg(native_linux_irq_work_v6_12)]
        Some("concurrent") => concurrent(),
        #[cfg(native_linux_irq_work_v6_12)]
        Some("paused") => paused(),
        #[cfg(native_linux_irq_work_v6_12)]
        Some("invalid") => invalid(),
        other => panic!("unknown mode {other:?}"),
    }
}
