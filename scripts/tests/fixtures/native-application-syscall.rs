// SPDX-License-Identifier: GPL-2.0
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_rpc.rs"]
mod application_rpc;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_syscall.rs"]
mod syscall;
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
            .prepare(0, 23),
        Err(-22)
    ));
    assert_eq!(buffer.0, before);
    assert!(unsafe { Response::new(&request, core::ptr::null_mut()) }.is_err());
    assert!(unsafe { Response::new(&request, buffer.0.as_mut_ptr().add(1)) }.is_err());
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
