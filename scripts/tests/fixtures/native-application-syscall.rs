// SPDX-License-Identifier: GPL-2.0
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_rpc.rs"]
mod application_rpc;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_syscall.rs"]
mod syscall;
use syscall as application_syscall;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/smp_application_syscall.rs"]
mod mailbox;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_pager.rs"]
mod pager;

// Only allocation is substituted. Tests compile the complete native mailbox
// source, with its real protocol, owner transitions and bounded slot handling.
extern crate self as kernel;
pub mod prelude {
    pub const GFP_KERNEL: u32 = 0;
    pub struct AllocError;
    pub struct Vec<T>(std::vec::Vec<T>);
    pub trait VecExt<T>: Sized {
        fn with_capacity(n: usize, flags: u32) -> Result<Self, AllocError>;
        fn push(&mut self, value: T, flags: u32) -> Result<(), AllocError>;
    }
    impl<T> VecExt<T> for Vec<T> {
        fn with_capacity(n: usize, _flags: u32) -> Result<Self, AllocError> {
            let mut value = std::vec::Vec::new();
            value.try_reserve(n).map_err(|_| AllocError)?;
            Ok(Self(value))
        }
        fn push(&mut self, value: T, _flags: u32) -> Result<(), AllocError> {
            self.0.try_reserve(1).map_err(|_| AllocError)?;
            self.0.push(value);
            Ok(())
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
}
#[allow(dead_code)]
#[path = "../../../kernel/rust/abi.rs"]
mod abi;
#[allow(dead_code)]
mod guest {
    include!("native-application-syscall-rust-producer.rs");
}
#[allow(dead_code)]
mod host {
    include!("native-application-syscall-rust-wake.rs");
}

use core::{
    ffi::c_void,
    mem::{align_of, offset_of, size_of},
    sync::atomic::{AtomicU64, Ordering},
};
use std::{
    cell::RefCell,
    collections::BTreeSet,
    sync::{Arc, Barrier},
};
use syscall::{Delivery, Request, Response, Worker};

const VALUES: [i64; 6] = [0, -1, -4095, i64::MAX, i64::MIN, 23];

fn hex(text: &str) -> Vec<u8> {
    assert_eq!(text.len() % 2, 0);
    text.as_bytes()
        .chunks_exact(2)
        .map(|pair| u8::from_str_radix(core::str::from_utf8(pair).unwrap(), 16).unwrap())
        .collect()
}

fn c_requests() -> Vec<Vec<u8>> {
    include_str!("native-application-syscall-c.txt")
        .lines()
        .filter(|line| line.starts_with("request "))
        .map(|line| hex(line.split_whitespace().nth(2).unwrap()))
        .collect()
}

fn request() -> Request {
    Request::decode(&c_requests()[0], 4).unwrap()
}

#[repr(C, align(8))]
struct Buffer([u8; 64]);

impl Buffer {
    fn new(state: u64) -> Self {
        let mut buffer = Self([0xa5; 64]);
        buffer.0[8..16].fill(0);
        buffer.0[16..24].copy_from_slice(&state.to_le_bytes());
        buffer
    }
}

#[test]
fn existing_c_user_and_guest_rust_layouts_match_all_used_fields() {
    let line = include_str!("native-application-syscall-c.txt")
        .lines()
        .next()
        .unwrap();
    let c: Vec<usize> = line
        .split_whitespace()
        .skip(1)
        .map(|word| word.parse().unwrap())
        .collect();
    assert_eq!(
        c,
        vec![
            72, 8, 0, 4, 8, 16, 24, 40, 8, 0, 4, 8, 16, 24, 32, 48, 88, 8, 0, 8, 80, 40, 8, 0, 8,
            16, 24, 32, 128, 48, 120
        ]
    );
    assert_eq!(
        [
            size_of::<abi::SyscallRequest>(),
            align_of::<abi::SyscallRequest>(),
            offset_of!(abi::SyscallRequest, rtid),
            offset_of!(abi::SyscallRequest, ttid),
            offset_of!(abi::SyscallRequest, valid),
            offset_of!(abi::SyscallRequest, number),
            offset_of!(abi::SyscallRequest, args)
        ],
        c[..7]
    );
    assert_eq!(size_of::<abi::SyscallResponse>(), c[15]);
    assert_eq!(
        [
            offset_of!(abi::SyscallResponse, ttid),
            offset_of!(abi::SyscallResponse, stid),
            offset_of!(abi::SyscallResponse, status),
            offset_of!(abi::SyscallResponse, req_thread_status),
            offset_of!(abi::SyscallResponse, ret),
            offset_of!(abi::SyscallResponse, fault_address)
        ],
        c[9..15]
    );
    assert_eq!(syscall::REQUEST_BYTES, c[0]);
    assert_eq!(syscall::RESPONSE_BYTES, c[7]);
    assert_eq!(syscall::WAIT_BYTES, c[16]);
    assert_eq!(syscall::RETURN_BYTES, c[21]);
    assert_eq!(size_of::<abi::IkcScdPacket>(), c[28]);
}

#[test]
fn exact_original_c_and_rust_producers_agree_including_targeted_worker() {
    let numbers = [1u64, 39, 231, 203, 0, 0xffff_ffff];
    let original = c_requests();
    assert_eq!(original.len(), numbers.len());
    for (n, number) in numbers.into_iter().enumerate() {
        let mut source = abi::SyscallRequest {
            rtid: 0,
            ttid: 0,
            valid: 0xa5,
            number,
            args: [0, 1, 0x400123, u64::MAX, 1 << 63, 17],
        };
        let mut response: abi::SyscallResponse = unsafe { core::mem::zeroed() };
        let mut packet: abi::IkcScdPacket = unsafe { core::mem::zeroed() };
        unsafe {
            assert_eq!(
                guest::syscall_offload_prepare_result(
                    &mut source,
                    &mut response,
                    700 + n as i32,
                    number as i32,
                    0,
                    203,
                    0
                ),
                (number == 203) as i32
            );
            assert_eq!(
                guest::syscall_send_prepare_result(&mut source, &mut response),
                0
            );
            let traditional =
                core::ptr::addr_of_mut!(packet.body).cast::<abi::IkcScdPacketTraditional>();
            assert_eq!(
                guest::syscall_request_copy_result(&mut (*traditional).req, &source),
                0
            );
            assert_eq!(
                guest::syscall_request_publish_result(&mut (*traditional).req),
                0
            );
            assert_eq!(
                guest::syscall_packet_traditional_prepare_result(
                    &mut packet,
                    4,
                    (n % 4) as i32,
                    600 + n as i32,
                    0x180000 + 128 * n as u64
                ),
                0
            );
            let bytes = core::slice::from_raw_parts(core::ptr::from_ref(&packet).cast::<u8>(), 128);
            assert_eq!(bytes, original[n]);
            let decoded = Request::decode(bytes, 4).unwrap();
            assert_eq!(decoded.number(), number);
            assert_eq!(decoded.pid(), 600 + n as i32);
            assert_eq!(decoded.target(), if number == 203 { 703 } else { 0 });
            assert_eq!(decoded.response(), 0x180000 + 128 * n as u64);
            let output = decoded.wait_output();
            assert_eq!(
                u64::from_le_bytes(output[..8].try_into().unwrap()),
                (n % 4) as u64
            );
            assert_eq!(&output[8..16], &bytes[48..56]);
            assert_eq!(&output[16..24], &[0; 8]);
            assert_eq!(&output[24..], &bytes[64..120]);
        }
    }
}

#[test]
fn malformed_requests_never_authorize_a_response_mapping() {
    let original = c_requests().remove(0);
    for length in 0..128 {
        assert!(Request::decode(&original[..length], 4).is_err());
    }
    let mut oversized = original.clone();
    oversized.push(0);
    assert!(Request::decode(&oversized, 4).is_err());
    for (offset, values) in [
        (8, [0, 3, 0x14]),
        (24, [-1, 4, i32::MAX]),
        (32, [0, -1, i32::MIN]),
        (48, [0, -1, i32::MIN]),
        (52, [-1, -2, i32::MIN]),
    ] {
        for value in values {
            let mut bad = original.clone();
            bad[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
            assert!(Request::decode(&bad, 4).is_err());
        }
    }
    for (offset, values) in [
        (56, [0u64, 2, u64::MAX]),
        (120, [0, 0x180001, u64::MAX - 7]),
    ] {
        for value in values {
            let mut bad = original.clone();
            bad[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
            assert!(Request::decode(&bad, 4).is_err());
        }
    }
    assert!(Request::decode(&original, 0).is_err());
    // The actual producer does not publish osnum; its checked transport owns
    // the OS identity. No user/wire osnum is allowed to replace that owner.
    let mut other = original.clone();
    other[28..32].copy_from_slice(&37i32.to_le_bytes());
    assert_eq!(Request::decode(&other, 4), Request::decode(&original, 4));
}

#[test]
fn failed_user_copy_requeues_and_tid_reuse_cannot_steal_delivery() {
    let mut delivery = Delivery::new(request()).unwrap();
    let first = Worker::new(900).unwrap();
    let reused = Worker::new(900).unwrap();
    let other = Worker::new(901).unwrap();
    assert_ne!(first, reused);
    assert!(Worker::new(0).is_err());
    for _ in 0..64 {
        let output = delivery.reserve(first).unwrap();
        assert_eq!(output, request().wait_output());
        assert_eq!(delivery.reserve(other), Err(-16));
        assert_eq!(delivery.copied(reused, true), Err(-16));
        assert_eq!(delivery.begin_return(first, 0), Err(-16));
        delivery.copied(first, false).unwrap();
    }
    delivery.reserve(first).unwrap();
    delivery.copied(first, true).unwrap();
    assert_eq!(delivery.copied(first, false), Err(-16));
    assert_eq!(delivery.begin_return(reused, 0), Err(-16));
    assert_eq!(delivery.begin_return(other, 0), Err(-16));
    assert_eq!(delivery.begin_return(first, 1), Err(-22));
    delivery.begin_return(first, 0).unwrap();
    assert_eq!(delivery.begin_return(first, 0), Err(-16));
    assert_eq!(delivery.completed(reused), Err(-16));
    delivery.completed(first).unwrap();
    assert_eq!(delivery.completed(first), Err(-16));
    assert_eq!(delivery.reserve(first), Err(-16));
}

#[test]
fn targeted_request_waits_for_the_original_target_number() {
    let mut delivery = Delivery::new(Request::decode(&c_requests()[3], 4).unwrap()).unwrap();
    assert!(!delivery.eligible(Worker::new(900).unwrap()));
    let target = Worker::new(703).unwrap();
    assert!(delivery.eligible(target));
    delivery.reserve(target).unwrap();
    delivery.copied(target, false).unwrap();
    assert!(delivery.eligible(target));
}

#[test]
fn completion_matches_original_c_for_spinning_and_descheduled_requesters() {
    let request = request();
    for line in include_str!("native-application-syscall-c.txt")
        .lines()
        .filter(|line| line.starts_with("response "))
    {
        let words: Vec<_> = line.split_whitespace().collect();
        let state = words[1].parse::<u64>().unwrap();
        let case = words[2].parse::<usize>().unwrap();
        let mut buffer = Buffer::new(state);
        let address = buffer.0.as_mut_ptr();
        let mut completion = unsafe { Response::new(&request, address) }
            .unwrap()
            .prepare(900, VALUES[case])
            .unwrap();
        let mut sent = 0;
        completion
            .publish(|packet| {
                sent += 1;
                assert_eq!(
                    i32::from_le_bytes(packet[8..12].try_into().unwrap()),
                    words[4].parse().unwrap()
                );
                assert_eq!(
                    i32::from_le_bytes(packet[24..28].try_into().unwrap()),
                    words[5].parse().unwrap()
                );
                assert_eq!(
                    unsafe { AtomicU64::from_ptr(address.add(8).cast()) }.load(Ordering::Acquire),
                    words[6].parse().unwrap()
                );
                Ok(())
            })
            .unwrap();
        assert_eq!(sent, words[3].parse::<i32>().unwrap());
        assert_eq!(buffer.0.as_slice(), hex(words[7]));
    }
}

thread_local! { static WAKE_TRACE: RefCell<Vec<(i32,i32)>>=const {RefCell::new(Vec::new())}; }
unsafe extern "C" fn find(pid: i32, tid: i32) -> *mut c_void {
    WAKE_TRACE.with(|trace| trace.borrow_mut().push((pid, tid)));
    core::ptr::dangling_mut::<u8>().cast()
}
unsafe extern "C" fn wake(thread: *mut c_void) {
    assert_eq!(thread, core::ptr::dangling_mut::<u8>().cast());
    WAKE_TRACE.with(|trace| trace.borrow_mut().push((1, 0)));
}
unsafe extern "C" fn unlock(thread: *mut c_void) {
    assert_eq!(thread, core::ptr::dangling_mut::<u8>().cast());
    WAKE_TRACE.with(|trace| trace.borrow_mut().push((2, 0)));
}

#[test]
fn wake_packet_is_consumed_by_the_exact_existing_guest_body() {
    WAKE_TRACE.with(|trace| trace.borrow_mut().clear());
    let request = request();
    let mut buffer = Buffer::new(2);
    let mut completion = unsafe { Response::new(&request, buffer.0.as_mut_ptr()) }
        .unwrap()
        .prepare(900, 23)
        .unwrap();
    completion
        .publish(|bytes| {
            let mut packet: abi::IkcScdPacket = unsafe { core::mem::zeroed() };
            unsafe {
                core::ptr::copy_nonoverlapping(
                    bytes.as_ptr(),
                    core::ptr::addr_of_mut!(packet).cast(),
                    128,
                );
            }
            assert_eq!(
                unsafe {
                    host::host_wake_syscall_thread_request_result(
                        &mut packet,
                        Some(find),
                        Some(wake),
                        Some(unlock),
                        None,
                    )
                },
                0
            );
            Ok(())
        })
        .unwrap();
    WAKE_TRACE.with(|trace| assert_eq!(*trace.borrow(), vec![(0, 700), (1, 0), (2, 0)]));
}

#[test]
fn full_queue_retains_result_and_response_until_actual_wake_publication() {
    let request = request();
    let mut buffer = Buffer::new(2);
    let pointer = buffer.0.as_mut_ptr();
    let mut completion = unsafe { Response::new(&request, pointer) }
        .unwrap()
        .prepare(900, -4095)
        .unwrap();
    let before = buffer.0;
    let mut previous = None;
    for attempt in 0..1024 {
        let error = if attempt % 2 == 0 { -16 } else { -11 };
        assert_eq!(
            completion.publish(|packet| {
                if let Some(prior) = previous {
                    assert_eq!(*packet, prior);
                }
                previous = Some(*packet);
                Err(error)
            }),
            Err(error)
        );
        assert_eq!(buffer.0, before);
        assert_eq!(
            unsafe { AtomicU64::from_ptr(pointer.add(8).cast()) }.load(Ordering::Acquire),
            0
        );
    }
    completion
        .publish(|packet| {
            assert_eq!(Some(*packet), previous);
            Ok(())
        })
        .unwrap();
    assert_eq!(
        unsafe { AtomicU64::from_ptr(pointer.add(8).cast()) }.load(Ordering::Acquire),
        1
    );
    buffer.0.fill(0x5a); // Simulate peer reuse after final publication.
    assert_eq!(
        completion.publish(|_| panic!("duplicate wake after completion")),
        Err(-16)
    );
    assert_eq!(buffer.0, [0x5a; 64]);
}

#[test]
fn invalid_response_states_are_rejected_without_overwriting_peer_bytes() {
    let request = request();
    for (status, state) in [
        (0u64, 1u64),
        (0, 3),
        (0, u64::MAX),
        (1, 0),
        (2, 2),
        (3, 0),
        (u64::MAX, 2),
    ] {
        let mut buffer = Buffer::new(state);
        buffer.0[8..16].copy_from_slice(&status.to_le_bytes());
        let before = buffer.0;
        let result = unsafe { Response::new(&request, buffer.0.as_mut_ptr()) }
            .unwrap()
            .prepare(900, 23);
        assert!(matches!(result, Err(-71)));
        assert_eq!(buffer.0, before);
    }
    let mut buffer = Buffer::new(0);
    let before = buffer.0;
    assert!(matches!(
        unsafe { Response::new(&request, buffer.0.as_mut_ptr()) }
            .unwrap()
            .prepare(-1, 23),
        Err(-22)
    ));
    assert_eq!(buffer.0, before);
    assert!(unsafe { Response::new(&request, core::ptr::null_mut()) }.is_err());
    assert!(unsafe { Response::new(&request, buffer.0.as_mut_ptr().add(1)) }.is_err());
}

struct TestRam {
    bytes: core::cell::UnsafeCell<Buffer>,
    physical: u64,
    claimed: core::sync::atomic::AtomicBool,
    releases: core::sync::atomic::AtomicUsize,
}
// SAFETY: The exclusive TestMemory claim serializes host writes. Concurrent
// peer operations use only aligned atomics; full snapshots follow joined work.
unsafe impl Sync for TestRam {}
impl TestRam {
    fn new(physical: u64, state: u64) -> Arc<Self> {
        Arc::new(Self {
            bytes: core::cell::UnsafeCell::new(Buffer::new(state)),
            physical,
            claimed: core::sync::atomic::AtomicBool::new(false),
            releases: core::sync::atomic::AtomicUsize::new(0),
        })
    }
    fn claim(self: &Arc<Self>) -> Result<TestMemory, i32> {
        self.claimed
            .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
            .map_err(|_| -16)?;
        Ok(TestMemory {
            ram: self.clone(),
            released: false,
        })
    }
    fn snapshot(&self) -> [u8; 64] {
        unsafe { (*self.bytes.get()).0 }
    }
    fn status(&self) -> u64 {
        unsafe { AtomicU64::from_ptr(self.bytes.get().cast::<u8>().add(8).cast()) }
            .load(Ordering::Acquire)
    }
}
struct TestMemory {
    ram: Arc<TestRam>,
    released: bool,
}
// SAFETY: Construction checks the exclusive claim. Arc owns the aligned RAM;
// unfinished destruction deliberately retains it as a quarantined test owner.
unsafe impl syscall::ResponseMemory for TestMemory {
    fn physical(&self) -> u64 {
        self.ram.physical
    }
    fn address(&mut self) -> *mut u8 {
        self.ram.bytes.get().cast()
    }
    unsafe fn release(mut self) {
        assert!(self.ram.claimed.swap(false, Ordering::AcqRel));
        self.ram.releases.fetch_add(1, Ordering::AcqRel);
        self.released = true;
    }
}
impl Drop for TestMemory {
    fn drop(&mut self) {
        if !self.released {
            // The synthetic peer supplied no retirement proof. Keep its RAM,
            // matching the native started owner's quarantine contract.
            std::mem::forget(self.ram.clone());
        }
    }
}
fn queued_request(index: usize, target: i32) -> Request {
    let mut packet = c_requests()[0].clone();
    packet[48..52].copy_from_slice(&(700 + index as i32).to_le_bytes());
    packet[52..56].copy_from_slice(&target.to_le_bytes());
    packet[120..128].copy_from_slice(&(0x800000 + 128 * index as u64).to_le_bytes());
    Request::decode(&packet, 4).unwrap()
}
fn admit(queue: &mut mailbox::Mailbox<TestMemory>, request: Request, state: u64) -> Arc<TestRam> {
    let memory = TestRam::new(request.response(), state);
    assert_eq!(queue.admit(request, |_| memory.claim()), Ok(true));
    memory
}

#[test]
fn kernel_cancellation_matches_original_c_with_servicing_tid_zero() {
    let request = request();
    let rows: Vec<_> = include_str!("native-application-syscall-c.txt")
        .lines()
        .filter(|line| line.starts_with("cancellation "))
        .collect();
    assert_eq!(rows.len(), 2);
    for line in rows {
        let words: Vec<_> = line.split_whitespace().collect();
        let mut buffer = Buffer::new(words[1].parse().unwrap());
        let mut completion = unsafe { Response::new(&request, buffer.0.as_mut_ptr()) }
            .unwrap()
            .prepare(0, -512)
            .unwrap();
        let mut sends = 0;
        completion
            .publish(|packet| {
                sends += 1;
                assert_eq!(
                    i32::from_le_bytes(packet[8..12].try_into().unwrap()),
                    words[3].parse().unwrap()
                );
                assert_eq!(
                    i32::from_le_bytes(packet[24..28].try_into().unwrap()),
                    words[4].parse().unwrap()
                );
                assert_eq!(
                    u64::from_le_bytes(buffer.0[8..16].try_into().unwrap()),
                    words[5].parse().unwrap()
                );
                Ok(())
            })
            .unwrap();
        assert_eq!(sends, words[2].parse::<usize>().unwrap());
        assert_eq!(buffer.0.as_slice(), hex(words[6]));
    }
}

#[test]
fn owned_completion_survives_request_scope_and_moves_between_threads() {
    let ram = TestRam::new(queued_request(0, 0).response(), 2);
    let completion = {
        let request = queued_request(0, 0);
        Response::from_memory(&request, ram.claim().unwrap())
            .unwrap()
            .prepare(900, 37)
            .unwrap()
    };
    let mut completion = std::thread::spawn(move || {
        let mut completion = completion;
        completion.publish(|_| Ok(())).unwrap();
        completion
    })
    .join()
    .unwrap();
    assert_eq!(ram.status(), 1);
    assert_eq!(ram.releases.load(Ordering::Acquire), 1);
    assert!(!ram.claimed.load(Ordering::Acquire));
    unsafe {
        (*ram.bytes.get()).0.fill(0x5a);
    }
    assert_eq!(completion.publish(|_| panic!("late wake")), Err(-16));
    assert_eq!(ram.snapshot(), [0x5a; 64]);
}

#[test]
fn actual_mailbox_capacity_retries_without_claiming_or_losing_a_request() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let mut memory = Vec::new();
    for index in 0..mailbox::CAPACITY {
        memory.push(admit(&mut queue, queued_request(index, 0), 2));
    }
    let extra = queued_request(64, 0);
    assert_eq!(
        queue.admit(extra, |_| panic!("full admission took a claim")),
        Err(-11)
    );
    assert_eq!(
        queue.admit(queued_request(0, 0), |_| panic!("duplicate responder")),
        Ok(false)
    );
    queue.close().unwrap();
    assert!(!queue.drained());
    for _ in 0..mailbox::CAPACITY {
        assert_eq!(queue.publish(0, |_| Ok(())), Ok(true));
    }
    assert!(queue.drained());
    assert_eq!(queue.publish(0, |_| panic!("extra completion")), Ok(false));
    for ram in memory {
        assert_eq!(ram.status(), 1);
        assert_eq!(ram.releases.load(Ordering::Acquire), 1);
        let bytes = ram.snapshot();
        assert_eq!(i32::from_le_bytes(bytes[4..8].try_into().unwrap()), 0);
        assert_eq!(i64::from_le_bytes(bytes[24..32].try_into().unwrap()), -512);
    }
}

#[test]
fn actual_mailbox_preserves_target_priority_copy_rollback_and_worker_identity() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let worker = queue.open_worker(900).unwrap();
    let other = queue.open_worker(901).unwrap();
    let general = admit(&mut queue, queued_request(0, 0), 0);
    let targeted = admit(&mut queue, queued_request(1, 900), 0);
    let (serial, output) = queue.reserve(worker).unwrap().unwrap();
    assert_eq!(output, queued_request(1, 900).wait_output());
    assert_eq!(queue.copied(other, serial, true), Err(-16));
    queue.copied(worker, serial, false).unwrap();
    let (again, output) = queue.reserve(worker).unwrap().unwrap();
    assert_eq!(again, serial);
    assert_eq!(output, queued_request(1, 900).wait_output());
    queue.copied(worker, serial, true).unwrap();
    assert_eq!(
        queue.return_value(worker, serial, 1, 23, |_| panic!("wrong CPU copy")),
        Err(-22)
    );
    assert_eq!(
        queue.return_value(other, serial, 0, 23, |_| panic!("wrong owner copy")),
        Err(-16)
    );
    assert_eq!(
        queue.return_value(worker, serial, 0, 23, |_| Err(-14)),
        Err(-14)
    );
    assert_eq!(targeted.status(), 0);
    queue
        .return_value(worker, serial, 0, 23, |_| Ok(()))
        .unwrap();
    assert_eq!(
        queue.return_value(worker, serial, 0, 23, |_| panic!("duplicate return copy")),
        Err(-16)
    );
    queue
        .publish(0, |_| panic!("spinning requester was sent a wake"))
        .unwrap();
    assert_eq!(queue.returned(worker, serial), Ok(true));
    queue.close_worker(worker).unwrap();
    let reused = queue.open_worker(900).unwrap();
    assert_ne!(reused, worker);
    assert_eq!(queue.reserve(worker), Err(-2));
    let (serial, output) = queue.reserve(reused).unwrap().unwrap();
    assert_eq!(output, queued_request(0, 0).wait_output());
    queue.copied(reused, serial, true).unwrap();
    queue
        .return_value(reused, serial, 0, -1, |_| Ok(()))
        .unwrap();
    queue.publish(0, |_| panic!("spinning wake")).unwrap();
    assert!(queue.drained());
    assert_eq!(general.status(), 1);
}

#[test]
fn actual_mailbox_full_wake_queue_retains_worker_until_publication() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let worker = queue.open_worker(900).unwrap();
    let first = admit(&mut queue, queued_request(0, 0), 2);
    let second = admit(&mut queue, queued_request(1, 0), 2);
    let (serial, _) = queue.reserve(worker).unwrap().unwrap();
    queue.copied(worker, serial, true).unwrap();
    queue
        .return_value(worker, serial, 0, 37, |_| Ok(()))
        .unwrap();
    for _ in 0..1024 {
        assert_eq!(queue.publish(0, |_| Err(-11)), Err(-11));
        assert_eq!(queue.reserve(worker), Ok(None));
        assert_eq!(queue.returned(worker, serial), Ok(false));
        assert_eq!(first.status(), 0);
        assert!(first.claimed.load(Ordering::Acquire));
    }
    assert_eq!(queue.publish(0, |_| Ok(())), Ok(true));
    assert_eq!(queue.returned(worker, serial), Ok(true));
    assert!(queue.reserve(worker).unwrap().is_some());
    queue.close().unwrap();
    queue.publish(0, |_| Ok(())).unwrap();
    assert!(queue.drained());
    assert_eq!(second.status(), 1);
}

#[test]
fn actual_mailbox_worker_death_and_close_cancel_copying_without_tid_reuse() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let worker = queue.open_worker(900).unwrap();
    let ram = admit(&mut queue, queued_request(0, 0), 2);
    let (serial, _) = queue.reserve(worker).unwrap().unwrap();
    assert_eq!(queue.close_worker(worker), Err(-16));
    assert_eq!(queue.open_worker(900), Err(-16));
    assert_eq!(queue.copied(worker, serial, true), Err(-16));
    assert_eq!(queue.publish(0, |_| Err(-11)), Err(-11));
    assert_eq!(ram.status(), 0);
    queue.publish(0, |_| Ok(())).unwrap();
    queue.close_worker(worker).unwrap();
    assert_ne!(queue.open_worker(900).unwrap(), worker);
    assert_eq!(
        i64::from_le_bytes(ram.snapshot()[24..32].try_into().unwrap()),
        -512
    );
    assert!(queue.drained());
}

#[test]
fn actual_mailbox_slot_reuse_preserves_pending_fifo_order() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let worker = queue.open_worker(900).unwrap();
    let _first = admit(&mut queue, queued_request(0, 0), 0);
    let _second = admit(&mut queue, queued_request(1, 0), 0);
    let (serial, _) = queue.reserve(worker).unwrap().unwrap();
    queue.copied(worker, serial, true).unwrap();
    queue
        .return_value(worker, serial, 0, 1, |_| Ok(()))
        .unwrap();
    queue.publish(0, |_| Ok(())).unwrap();
    let _third = admit(&mut queue, queued_request(2, 0), 0);
    let (serial, output) = queue.reserve(worker).unwrap().unwrap();
    assert_eq!(
        output,
        queued_request(1, 0).wait_output(),
        "a reused slot overtook an older request"
    );
    queue.copied(worker, serial, true).unwrap();
    queue
        .return_value(worker, serial, 0, 2, |_| Ok(()))
        .unwrap();
    queue.publish(0, |_| Ok(())).unwrap();
    assert_eq!(
        queue.reserve(worker).unwrap().unwrap().1,
        queued_request(2, 0).wait_output()
    );
    queue.close().unwrap();
    queue.publish(0, |_| Ok(())).unwrap();
    assert!(queue.drained());
}

#[test]
fn actual_mailbox_full_wake_queue_does_not_starve_another_cpu() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let first_worker = queue.open_worker(900).unwrap();
    let second_worker = queue.open_worker(901).unwrap();
    let first = admit(&mut queue, queued_request(0, 0), 2);
    let mut packet = c_requests()[0].clone();
    packet[24..28].copy_from_slice(&1i32.to_le_bytes());
    packet[48..52].copy_from_slice(&701i32.to_le_bytes());
    packet[120..128].copy_from_slice(&0x800080u64.to_le_bytes());
    let second = admit(&mut queue, Request::decode(&packet, 4).unwrap(), 2);
    for (worker, cpu) in [(first_worker, 0), (second_worker, 1)] {
        let (serial, _) = queue.reserve(worker).unwrap().unwrap();
        queue.copied(worker, serial, true).unwrap();
        queue
            .return_value(worker, serial, cpu, 37, |_| Ok(()))
            .unwrap();
    }
    assert_eq!(queue.queued_cpu(), Some(0));
    assert_eq!(queue.publish(0, |_| Err(-11)), Err(-11));
    assert_eq!(
        queue.queued_cpu(),
        Some(1),
        "full CPU zero ring starved CPU one"
    );
    queue.publish(1, |_| Ok(())).unwrap();
    assert_eq!(second.status(), 1);
    assert_eq!(first.status(), 0);
    assert_eq!(queue.queued_cpu(), Some(0));
    queue.publish(0, |_| Ok(())).unwrap();
    assert!(queue.drained());
}

#[test]
fn actual_mailbox_quarantines_invalid_response_instead_of_releasing_it() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let worker = queue.open_worker(900).unwrap();
    let ram = admit(&mut queue, queued_request(0, 0), 0);
    let (serial, _) = queue.reserve(worker).unwrap().unwrap();
    queue.copied(worker, serial, true).unwrap();
    unsafe { AtomicU64::from_ptr(ram.bytes.get().cast::<u8>().add(16).cast()) }
        .store(1, Ordering::Release);
    let before = ram.snapshot();
    assert_eq!(
        queue.return_value(worker, serial, 0, 37, |_| Ok(())),
        Err(-71)
    );
    assert!(queue.quarantined());
    assert!(!queue.drained());
    drop(queue);
    assert!(ram.claimed.load(Ordering::Acquire));
    assert_eq!(ram.releases.load(Ordering::Acquire), 0);
    assert_eq!(ram.snapshot(), before);
}

#[test]
fn return_copy_is_bound_to_the_existing_futex_clock_destination_and_extent() {
    let mut packet = c_requests()[0].clone();
    packet[64..72].copy_from_slice(&202u64.to_le_bytes());
    packet[72..80].copy_from_slice(&0x900008u64.to_le_bytes());
    let request = Request::decode(&packet, 4).unwrap();
    assert_eq!(request.authorize_return_copy(0x900008, 16), Ok(()));
    for (address, length) in [(0, 16), (0x900000, 16), (0x900008, 8), (0x900008, 17)] {
        assert_eq!(request.authorize_return_copy(address, length), Err(-22));
    }
    packet[64..72].copy_from_slice(&228u64.to_le_bytes());
    assert_eq!(
        Request::decode(&packet, 4)
            .unwrap()
            .authorize_return_copy(0x900008, 16),
        Err(-22)
    );
}

#[test]
fn real_atomic_deschedule_race_preserves_result_visibility() {
    for round in 0..256 {
        let memory = Arc::new([const { AtomicU64::new(0xa5a5_a5a5_a5a5_a5a5) }; 8]);
        memory[1].store(0, Ordering::Relaxed);
        memory[2].store(0, Ordering::Relaxed);
        let barrier = Arc::new(Barrier::new(2));
        let peer = memory.clone();
        let ready = barrier.clone();
        let guest = std::thread::spawn(move || {
            ready.wait();
            let scheduled = peer[2]
                .compare_exchange(0, 2, Ordering::AcqRel, Ordering::Acquire)
                .is_ok();
            while peer[1].load(Ordering::Acquire) == 0 {
                std::thread::yield_now();
            }
            assert_eq!(peer[3].load(Ordering::Relaxed) as i64, round - 128);
            assert_eq!(peer[0].load(Ordering::Relaxed) >> 32, 900);
            assert_eq!(peer[4].load(Ordering::Relaxed), 0xa5a5_a5a5_a5a5_a5a5);
            assert_eq!(peer[5].load(Ordering::Relaxed), 0xa5a5_a5a5_a5a5_a5a5);
            scheduled
        });
        barrier.wait();
        let request = request();
        let pointer = memory.as_ptr().cast::<u8>().cast_mut();
        let mut completion = unsafe { Response::new(&request, pointer) }
            .unwrap()
            .prepare(900, round - 128)
            .unwrap();
        let mut wakes = 0;
        completion
            .publish(|_| {
                wakes += 1;
                Ok(())
            })
            .unwrap();
        assert_eq!(wakes, guest.join().unwrap() as usize);
    }
}

#[test]
fn concurrent_delivery_and_existing_rpc_tokens_never_overlap() {
    let threads: Vec<_> = (0..8)
        .map(|_| {
            std::thread::spawn(|| {
                let mut tokens = Vec::new();
                for _ in 0..256 {
                    let delivery = Delivery::new(request()).unwrap();
                    tokens.push(delivery.serial().wire());
                    tokens.push(
                        application_rpc::Exchange::new(0, 0, 600)
                            .unwrap()
                            .token()
                            .wire(),
                    );
                }
                tokens
            })
        })
        .collect();
    let tokens: Vec<_> = threads
        .into_iter()
        .flat_map(|thread| thread.join().unwrap())
        .collect();
    assert_eq!(tokens.len(), 4096);
    let distinct: BTreeSet<_> = tokens.iter().copied().collect();
    assert_eq!(distinct.len(), tokens.len());
    assert!(!distinct.contains(&0));
}

fn pager_request(arguments: [u64; 6]) -> Request {
    let mut packet = c_requests()[0].clone();
    packet[64..72].copy_from_slice(&9u64.to_le_bytes());
    for (index, value) in arguments.iter().enumerate() {
        let offset = 72 + index * 8;
        packet[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
    }
    Request::decode(&packet, 4).unwrap()
}

#[test]
fn pager_result_matches_selected_guest_abi_and_keeps_public_ret_narrow() {
    use abi::PagerCreateResult;
    assert_eq!(size_of::<PagerCreateResult>(), pager::CREATE_BYTES);
    assert_eq!(offset_of!(PagerCreateResult, maxprot), 8);
    assert_eq!(offset_of!(PagerCreateResult, flags), 12);
    assert_eq!(offset_of!(PagerCreateResult, size), 16);
    assert_eq!(offset_of!(PagerCreateResult, pgshift), 24);
    assert_eq!(offset_of!(PagerCreateResult, path), 28);
    let mut output = vec![0x5a; pager::CREATE_BYTES + 16];
    pager::create_result(
        &mut output[..pager::CREATE_BYTES],
        7123,
        5,
        8,
        0x3456789,
        b"/lib64/libc.so.6\0",
    )
    .unwrap();
    let value = unsafe { core::ptr::read_unaligned(output.as_ptr().cast::<PagerCreateResult>()) };
    assert_eq!(value.handle, 7123);
    assert_eq!(value.maxprot, 5);
    assert_eq!(value.flags, 8);
    assert_eq!(value.size, 0x3456789);
    assert_eq!(value.pgshift, 0);
    let path = b"/lib64/libc.so.6\0";
    assert_eq!(&output[28..28 + path.len()], path);
    assert!(output[28 + path.len()..pager::CREATE_BYTES]
        .iter()
        .all(|&b| b == 0));
    assert!(output[pager::CREATE_BYTES..].iter().all(|&b| b == 0x5a));
    assert!(pager::create_result(
        &mut output[..pager::CREATE_BYTES],
        1,
        5,
        0,
        0,
        b"missing-nul"
    )
    .is_err());
    let request = pager_request([1, 6, 0x900000, 0, 0, 0]);
    assert_eq!(
        pager::Operation::decode(&request).unwrap().payload(),
        Some((0x900000, 4128, true))
    );
    assert!(request.authorize_return_copy(0x900000, 16).is_err());
    assert!(request.authorize_return_copy(0x900000, 4128).is_err());
}

#[test]
fn pager_request_geometry_rejects_wrapping_ranges_and_preserves_direction() {
    for (code, write) in [(3, false), (4, true)] {
        let request = pager_request([code, 2, 4096, 8192, 0x900000, 0]);
        assert_eq!(
            pager::Operation::decode(&request).unwrap(),
            pager::Operation::Io {
                write,
                handle: 2,
                offset: 4096,
                bytes: 8192,
                physical: 0x900000,
            }
        );
        assert_eq!(
            pager::Operation::decode(&request).unwrap().payload(),
            Some((0x900000, 8192, !write))
        );
    }
    for args in [
        [1, 6, 0, 0, 0, 0],
        [1, 6, u64::MAX - 4095, 0, 0, 0],
        [3, 2, u64::MAX, 1, 0x900000, 0],
        [3, 2, i64::MAX as u64, 1, 0x900000, 0],
        [4, 2, 0, 8, u64::MAX - 3, 0],
        [4, 2, 0, u64::MAX, 0x900000, 0],
    ] {
        assert_eq!(pager::Operation::decode(&pager_request(args)), Err(-22));
    }
    assert_eq!(
        pager::Operation::decode(&pager_request([5, 0, 0, 0, 0, 0])),
        Err(-38)
    );
    assert_eq!(
        pager::Operation::decode(&pager_request([3, 2, 0, 0, 0, 0]))
            .unwrap()
            .payload(),
        None
    );
    assert!(pager::Operation::is_release(&pager_request([
        2, 2, 7, 0, 0, 0
    ])));
}

#[test]
fn kernel_io_defers_owner_cancellation_until_memory_access_finishes() {
    for close_process in [false, true] {
        let mut queue = mailbox::Mailbox::new().unwrap();
        let worker = queue.open_worker(900).unwrap();
        let request = queued_request(0, 0);
        let ram = admit(&mut queue, request.clone(), 2);
        let (serial, _) = queue.reserve(worker).unwrap().unwrap();
        assert_eq!(queue.begin_kernel(worker, serial).unwrap(), request);
        assert!(queue.begin_kernel(worker, serial).is_err());
        assert!(queue
            .return_value(worker, serial, 0, 91, |_| panic!("public RET during I/O"))
            .is_err());
        queue
            .with_kernel_memory(worker, serial, |_, _| Ok(()))
            .unwrap();
        if close_process {
            queue.close().unwrap();
        } else {
            assert_eq!(queue.close_worker(worker), Err(-16));
        }
        assert_eq!(
            queue.publish(0, |_| panic!("early I/O completion")),
            Ok(false)
        );
        assert_eq!(ram.status(), 0);
        assert!(ram.claimed.load(Ordering::Acquire));
        assert!(queue
            .with_kernel_memory::<()>(worker, serial, |_, _| panic!("copy after cancel"))
            .is_err());
        queue
            .finish_kernel(worker, serial, |_, _| {
                panic!("CREATE committed after cancel")
            })
            .unwrap();
        assert_eq!(queue.publish(0, |_| Err(-11)), Err(-11));
        assert_eq!(ram.status(), 0);
        assert!(queue.open_worker(900).is_err());
        assert_eq!(queue.publish(0, |_| Ok(())), Ok(true));
        assert!(queue.drained());
        assert_eq!(ram.status(), 1);
        assert_eq!(
            i64::from_le_bytes(ram.snapshot()[24..32].try_into().unwrap()),
            -512
        );
        queue.close_worker(worker).unwrap();
    }
}

#[test]
fn kernel_io_keeps_exact_worker_serial_and_error_through_completion() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let worker = queue.open_worker(900).unwrap();
    let wrong = queue.open_worker(901).unwrap();
    let ram = admit(&mut queue, queued_request(0, 0), 2);
    let (serial, _) = queue.reserve(worker).unwrap().unwrap();
    assert!(queue.begin_kernel(wrong, serial).is_err());
    assert!(queue.begin_kernel(worker, serial + 1).is_err());
    queue.begin_kernel(worker, serial).unwrap();
    assert!(queue
        .finish_kernel(wrong, serial, |_, _| panic!("wrong worker"))
        .is_err());
    assert!(queue
        .with_kernel_memory::<()>(worker, serial + 1, |_, _| panic!("stale memory"))
        .is_err());
    queue
        .finish_kernel(worker, serial, |_, _| Err(-14))
        .unwrap();
    for _ in 0..1024 {
        assert_eq!(queue.publish(0, |_| Err(-11)), Err(-11));
        assert_eq!(queue.reserve(worker), Ok(None));
        assert_eq!(ram.status(), 0);
    }
    queue.publish(0, |_| Ok(())).unwrap();
    assert_eq!(queue.returned(worker, serial), Ok(true));
    assert_eq!(
        i64::from_le_bytes(ram.snapshot()[24..32].try_into().unwrap()),
        -14
    );
    assert_eq!(
        i32::from_le_bytes(ram.snapshot()[4..8].try_into().unwrap()),
        0
    );
    assert!(queue
        .finish_kernel(worker, serial, |_, _| panic!("duplicate effect"))
        .is_err());
}

#[test]
fn continuing_service_requires_no_worker_and_survives_close_and_duplicate_ingress() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    queue.close().unwrap();
    let request = queued_request(0, 9123);
    let ram = TestRam::new(request.response(), 2);
    let mut effects = 0;
    assert_eq!(
        queue.admit_serviced(
            request.clone(),
            |_| ram.claim(),
            |_| {
                effects += 1;
                23
            }
        ),
        Ok(true)
    );
    assert_eq!(
        queue.admit_serviced(
            request,
            |_| panic!("duplicate claim"),
            |_| panic!("duplicate RELEASE")
        ),
        Ok(false)
    );
    assert_eq!(effects, 1);
    queue.close().unwrap();
    for _ in 0..1024 {
        assert_eq!(queue.publish(0, |_| Err(-11)), Err(-11));
        assert_eq!(ram.status(), 0);
        assert!(ram.claimed.load(Ordering::Acquire));
    }
    queue.publish(0, |_| Ok(())).unwrap();
    assert_eq!(ram.status(), 1);
    assert_eq!(
        i64::from_le_bytes(ram.snapshot()[24..32].try_into().unwrap()),
        23
    );
    assert_eq!(ram.releases.load(Ordering::Acquire), 1);
    assert!(queue.drained());
}
