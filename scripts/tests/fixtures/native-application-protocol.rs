// SPDX-License-Identifier: GPL-2.0
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_rpc.rs"]
mod rpc;
#[allow(dead_code)]
#[path = "../../../kernel/rust/abi.rs"]
mod abi;
#[allow(dead_code)]
mod guest {
    include!("native-application-guest-reference.rs");
}

use core::ffi::c_void;
use rpc::Exchange;
use std::cell::RefCell;

struct Peer {
    expected_pid: i32,
    error: i32,
    reply: [u8; 128],
    events: Vec<&'static str>,
}
thread_local! {
    static PEER: RefCell<Peer> = const { RefCell::new(Peer {
        expected_pid: 0, error: 0, reply: [0; 128], events: Vec::new(),
    }) };
}
unsafe extern "C" fn cleanup(pid: i32) -> i32 {
    PEER.with(|state| {
        let mut state = state.borrow_mut();
        assert_eq!(pid, state.expected_pid);
        state.events.push("cleanup");
        state.error
    })
}
unsafe extern "C" fn send(_: *mut c_void, packet: *mut abi::IkcScdPacket) {
    PEER.with(|state| {
        let mut state = state.borrow_mut();
        state.events.push("acknowledge");
        core::ptr::copy_nonoverlapping(packet.cast::<u8>(), state.reply.as_mut_ptr(), 128);
    });
}
unsafe extern "C" fn terminate(pid: i32, thread: *mut c_void) {
    PEER.with(|state| {
        let mut state = state.borrow_mut();
        assert_eq!(pid, state.expected_pid);
        assert!(thread.is_null());
        state.events.push("terminate");
    });
}
fn guest_reply(packet: &[u8; 128], error: i32) -> [u8; 128] {
    let pid = i32::from_le_bytes(packet[32..36].try_into().unwrap());
    PEER.with(|state| {
        *state.borrow_mut() = Peer {
            expected_pid: pid,
            error,
            reply: [0xa5; 128],
            events: Vec::new(),
        }
    });
    let mut request: abi::IkcScdPacket = unsafe { core::mem::zeroed() };
    unsafe {
        core::ptr::copy_nonoverlapping(packet.as_ptr(), (&raw mut request).cast(), 128);
        assert_eq!(
            guest::host_cleanup_process_request_result(
                core::ptr::null_mut(),
                &mut request,
                Some(cleanup),
                Some(terminate),
                None,
                Some(send)
            ),
            0
        );
    }
    PEER.with(|state| {
        let state = state.borrow();
        assert_eq!(state.events, ["cleanup", "acknowledge", "terminate"]);
        state.reply
    })
}

#[test]
fn traditional_wire_matches_source_bound_c_and_actual_guest_rust() {
    let layout: Vec<usize> = include_str!("native-application-layout.txt")
        .split_whitespace()
        .map(|value| value.parse().unwrap())
        .collect();
    assert_eq!(
        layout,
        [128, 8, 0, 8, 12, 16, 24, 28, 32, 40, 48, 120, 9, 10]
    );
    assert_eq!(core::mem::size_of::<abi::IkcScdPacket>(), layout[0]);
    assert_eq!(core::mem::align_of::<abi::IkcScdPacket>(), layout[1]);
    let mut exchange = Exchange::new(7, 3, 713).unwrap();
    exchange.begin().unwrap();
    let packet = exchange.outgoing().unwrap();
    assert_eq!(
        u64::from_le_bytes(packet[16..24].try_into().unwrap()),
        exchange.token().wire()
    );
    assert_eq!(i32::from_le_bytes(packet[24..28].try_into().unwrap()), 3);
    assert_eq!(i32::from_le_bytes(packet[28..32].try_into().unwrap()), 7);
    assert_eq!(i32::from_le_bytes(packet[32..36].try_into().unwrap()), 713);
    let reply = guest_reply(&packet, 0);
    assert_eq!(&reply[16..28], &packet[16..28]);
    assert_eq!(&reply[28..40], &[0; 12]); // The actual guest does not echo PID.
    exchange.published().unwrap();
    exchange.accept(&reply).unwrap();
    assert_eq!(exchange.result(), Some(0));
}

#[test]
fn reservation_validation_and_no_premature_publication() {
    for (os, cpu, pid) in [(-1, 0, 1), (0, -1, 1), (0, 0, 0), (0, 0, -1)] {
        assert!(matches!(Exchange::new(os, cpu, pid), Err(-22)));
    }
    let mut exchange = Exchange::new(0, 0, 11).unwrap();
    assert!(exchange.reserved());
    assert!(exchange.outgoing().is_none());
    assert_eq!(exchange.published(), Err(-16));
    assert_eq!(exchange.result(), None);
    exchange.begin().unwrap();
    assert_eq!(exchange.begin(), Err(-16));
}

#[test]
fn queue_full_retries_preserve_identical_request_and_exactly_once_reply() {
    let mut exchange = Exchange::new(0, 0, 17).unwrap();
    exchange.begin().unwrap();
    let packet = exchange.outgoing().unwrap();
    let reply = guest_reply(&packet, 0);
    for _ in 0..257 {
        assert_eq!(exchange.outgoing(), Some(packet));
        assert_eq!(exchange.accept(&reply), Err(-16));
    }
    exchange.published().unwrap();
    assert!(exchange.outgoing().is_none());
    assert_eq!(exchange.published(), Err(-16));
    exchange.accept(&reply).unwrap();
    assert_eq!(exchange.accept(&reply), Err(-16));
    assert_eq!(exchange.result(), Some(0));
}

#[test]
fn wrong_stale_and_sysfs_layout_replies_do_not_release_the_request() {
    let mut exchange = Exchange::new(0, 2, 23).unwrap();
    exchange.begin().unwrap();
    let reply = guest_reply(&exchange.outgoing().unwrap(), 0);
    exchange.published().unwrap();
    for offset in [8, 16, 24, 40] {
        let mut wrong = reply;
        wrong[offset] ^= 1;
        assert_eq!(exchange.accept(&wrong), Err(-2));
        assert_eq!(exchange.result(), None);
    }
    let mut sysfs = [0; 128];
    sysfs[8..12].copy_from_slice(&10i32.to_le_bytes());
    sysfs[24..32].copy_from_slice(&exchange.token().wire().to_le_bytes());
    assert_eq!(exchange.accept(&sysfs), Err(-2));
    assert_eq!(exchange.accept(&reply[..127]), Err(-22));
    exchange.accept(&reply).unwrap();
    let mut next = Exchange::new(0, 2, 23).unwrap();
    next.begin().unwrap();
    next.published().unwrap();
    assert_eq!(next.accept(&reply), Err(-2));
}

#[test]
fn departing_waiters_leave_both_queued_and_published_owners_until_ack() {
    for already_published in [false, true] {
        let mut exchange = Exchange::new(0, 0, 31).unwrap();
        exchange.begin().unwrap();
        let packet = exchange.outgoing().unwrap();
        if already_published {
            exchange.published().unwrap();
        }
        exchange.abandon();
        assert!(exchange.abandoned());
        assert!(!exchange.retired());
        if !already_published {
            assert_eq!(exchange.outgoing(), Some(packet));
            exchange.published().unwrap();
        }
        assert!(!exchange.retired());
        exchange.accept(&guest_reply(&packet, 0)).unwrap();
        assert!(exchange.retired());
    }
}

#[test]
fn actual_guest_cleanup_errors_and_order_are_preserved() {
    for error in [-4095, -22, 0] {
        let mut exchange = Exchange::new(0, 0, 41).unwrap();
        exchange.begin().unwrap();
        let reply = guest_reply(&exchange.outgoing().unwrap(), error);
        exchange.published().unwrap();
        exchange.accept(&reply).unwrap();
        assert_eq!(exchange.result(), Some(error));
    }
}

#[test]
fn matching_malformed_results_retire_with_protocol_error() {
    for error in [1, i32::MAX, i32::MIN, -4096] {
        let mut exchange = Exchange::new(0, 0, 43).unwrap();
        exchange.begin().unwrap();
        let reply = guest_reply(&exchange.outgoing().unwrap(), error);
        exchange.published().unwrap();
        exchange.abandon();
        exchange.accept(&reply).unwrap();
        assert_eq!(exchange.result(), Some(-71));
        assert!(exchange.retired());
    }
}

#[test]
fn concurrent_token_allocation_never_reuses_an_identity() {
    let workers: Vec<_> = (0..8)
        .map(|_| {
            std::thread::spawn(|| {
                (0..512)
                    .map(|_| Exchange::new(0, 0, 47).unwrap().token().wire())
                    .collect::<Vec<_>>()
            })
        })
        .collect();
    let mut tokens: Vec<_> = workers
        .into_iter()
        .flat_map(|worker| worker.join().unwrap())
        .collect();
    assert_eq!(tokens.len(), 4096);
    tokens.sort_unstable();
    tokens.dedup();
    assert_eq!(tokens.len(), 4096);
    assert!(tokens[0] > 0);
}
