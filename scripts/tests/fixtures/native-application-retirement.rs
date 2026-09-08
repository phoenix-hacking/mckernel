// SPDX-License-Identifier: GPL-2.0
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_rpc.rs"]
mod rpc;
#[allow(dead_code)]
#[path = "../../../kernel/rust/abi.rs"]
mod abi;
#[allow(dead_code)]
mod lock_helpers {
    include!("native-retirement-lock-type.rs");
}
#[allow(dead_code)]
mod guest {
    include!("native-application-guest-reference.rs");
    include!("native-retirement-guest-reference.rs");
    unsafe extern "C" fn host_cleanup_process_bridge(_: i32) -> i32 {
        crate::PEER.with(|p| p.borrow_mut().effects.push("cleanup"));
        0
    }
    unsafe extern "C" fn host_terminate_host_bridge(_: i32, _: *mut c_void) {
        crate::PEER.with(|p| p.borrow_mut().effects.push("terminate"));
    }
    unsafe extern "C" fn host_cleanup_process_log_bridge(_: i32, _: u64) {}
    unsafe extern "C" fn host_ikc_packet_send_raw_bridge(c: *mut c_void, p: *mut IkcScdPacket) {
        crate::send(c, p);
    }
    pub unsafe fn dispatch(p: *mut IkcScdPacket) -> i32 {
        host_cleanup_process_request_bridge(core::ptr::null_mut(), p)
    }
}
use core::{ffi::c_void, ptr};
use std::cell::RefCell;
struct Peer {
    cpu: *mut abi::CpuLocalVar,
    process: *mut abi::Process,
    present: bool,
    locked: bool,
    lookups: usize,
    unlocks: usize,
    effects: Vec<&'static str>,
    replies: Vec<[u8; 128]>,
}
thread_local! {
    static PEER: RefCell<Peer> = const { RefCell::new(Peer {
        cpu: ptr::null_mut(), process: ptr::null_mut(), present: false, locked: false,
        lookups: 0, unlocks: 0, effects: Vec::new(), replies: Vec::new(),
    }) };
}
#[no_mangle]
unsafe extern "C" fn get_this_cpu_local_var() -> *mut abi::CpuLocalVar {
    PEER.with(|p| p.borrow().cpu)
}
#[no_mangle]
unsafe extern "C" fn find_process(
    pid: i32,
    lock: *mut lock_helpers::McsRwlockNodeIrqsave,
) -> *mut abi::Process {
    assert_eq!(pid, 723);
    assert_eq!(lock as usize % 64, 0);
    PEER.with(|p| {
        let mut p = p.borrow_mut();
        assert!(!p.locked);
        p.lookups += 1;
        p.locked = p.present;
        if p.present {
            p.process
        } else {
            ptr::null_mut()
        }
    })
}
#[no_mangle]
unsafe extern "C" fn process_unlock(
    process: *mut abi::Process,
    _: *mut lock_helpers::McsRwlockNodeIrqsave,
) {
    PEER.with(|p| {
        let mut p = p.borrow_mut();
        assert!(p.locked);
        assert_eq!(process, p.process);
        p.locked = false;
        p.unlocks += 1;
    })
}
unsafe extern "C" fn send(_: *mut c_void, packet: *mut abi::IkcScdPacket) {
    let mut bytes = [0; 128];
    ptr::copy_nonoverlapping(packet.cast::<u8>(), bytes.as_mut_ptr(), 128);
    PEER.with(|p| {
        let mut p = p.borrow_mut();
        assert!(!p.locked);
        p.effects.push("send");
        p.replies.push(bytes);
    })
}
struct Environment {
    cpu: Box<abi::CpuLocalVar>,
    resources: Box<abi::ResourceSet>,
    _process: Box<abi::Process>,
}
impl Environment {
    fn new(present: bool) -> Self {
        let mut cpu: Box<abi::CpuLocalVar> = Box::new(unsafe { core::mem::zeroed() });
        let mut resources: Box<abi::ResourceSet> = Box::new(unsafe { core::mem::zeroed() });
        let mut process: Box<abi::Process> = Box::new(unsafe { core::mem::zeroed() });
        resources.process_hash = ptr::NonNull::<abi::ProcessHash>::dangling().as_ptr();
        cpu.resource_set = &mut *resources;
        PEER.with(|p| {
            *p.borrow_mut() = Peer {
                cpu: &mut *cpu,
                process: &mut *process,
                present,
                locked: false,
                lookups: 0,
                unlocks: 0,
                effects: Vec::new(),
                replies: Vec::new(),
            }
        });
        Self {
            cpu,
            resources,
            _process: process,
        }
    }
}
fn vector(name: &str, token: u64) -> [u8; 128] {
    let row = include_str!("native-retirement-c.txt")
        .lines()
        .find_map(|row| {
            let (tag, hex) = row.split_once(' ')?;
            (tag == name).then_some(hex)
        })
        .unwrap();
    assert_eq!(row.len(), 256);
    let mut bytes = [0; 128];
    for (index, pair) in row.as_bytes().chunks_exact(2).enumerate() {
        bytes[index] = u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap();
    }
    bytes[16..24].copy_from_slice(&token.to_le_bytes());
    bytes
}
fn dispatch(bytes: &[u8; 128]) -> i32 {
    let mut packet: abi::IkcScdPacket = unsafe { core::mem::zeroed() };
    unsafe {
        ptr::copy_nonoverlapping(bytes.as_ptr(), (&raw mut packet).cast(), 128);
        guest::dispatch(&mut packet)
    }
}
fn query() -> rpc::Exchange {
    let mut q = rpc::Exchange::retirement(3, 2, 723).unwrap();
    q.begin().unwrap();
    q
}
#[test]
fn schedule_matches_c_fields_and_publication_has_no_ack_dependency() {
    for thread in [0, 1, 0x7fff_ffff_f000] {
        assert!(rpc::Exchange::schedule(3, 2, 723, thread).is_err());
    }
    let mut q = rpc::Exchange::schedule(3, 2, 723, 0xffff_8800_1234_5000).unwrap();
    q.begin().unwrap();
    let expected = vector("SCHEDULE", q.token().wire());
    for _ in 0..1024 {
        assert_eq!(q.outgoing(), Some(expected));
        assert_eq!(q.result(), None);
    }
    q.published().unwrap();
    assert_eq!(q.result(), Some(0));
    assert_eq!(q.outgoing(), None);
    assert_eq!(q.published(), Err(-16));
}
#[test]
fn absent_query_runs_actual_lookup_and_reply_after_unlock() {
    let _environment = Environment::new(false);
    let mut q = query();
    assert_eq!(q.outgoing(), Some(vector("QUERY", q.token().wire())));
    assert_eq!(dispatch(&q.outgoing().unwrap()), 0);
    q.published().unwrap();
    PEER.with(|p| {
        let p = p.borrow();
        assert_eq!(p.lookups, 1);
        assert_eq!(p.unlocks, 0);
        assert_eq!(p.effects, ["send"]);
        assert_eq!(p.replies, [vector("ABSENT", q.token().wire())]);
        q.accept(&p.replies[0]).unwrap();
    });
    assert_eq!(q.result(), Some(0));
}
#[test]
fn present_query_is_retryable_and_never_terminates_or_borrows_a_thread() {
    let _environment = Environment::new(true);
    let mut q = query();
    assert_eq!(dispatch(&q.outgoing().unwrap()), 0);
    q.published().unwrap();
    PEER.with(|p| {
        let p = p.borrow();
        assert_eq!((p.lookups, p.unlocks), (1, 1));
        assert_eq!(p.effects, ["send"]);
        assert_eq!(p.replies, [vector("PRESENT", q.token().wire())]);
        q.accept(&p.replies[0]).unwrap();
    });
    assert_eq!(q.result(), Some(-11));
    let mut next = query();
    assert_ne!(q.token(), next.token());
    next.published().unwrap();
    assert_eq!(next.accept(&vector("ABSENT", q.token().wire())), Err(-2));
    assert_eq!(next.result(), None);
}
#[test]
fn missing_runtime_is_an_error_not_absence() {
    for missing in 0..3 {
        let mut environment = Environment::new(false);
        match missing {
            0 => PEER.with(|p| p.borrow_mut().cpu = ptr::null_mut()),
            1 => environment.cpu.resource_set = ptr::null_mut(),
            _ => environment.resources.process_hash = ptr::null_mut(),
        }
        let mut q = query();
        assert_eq!(dispatch(&q.outgoing().unwrap()), 0);
        q.published().unwrap();
        PEER.with(|p| {
            let p = p.borrow();
            assert_eq!(p.lookups, 0);
            assert_eq!(p.effects, ["send"]);
            q.accept(&p.replies[0]).unwrap();
        });
        assert_eq!(q.result(), Some(-22));
    }
}
#[test]
fn malformed_marked_queries_have_no_effect() {
    let _environment = Environment::new(false);
    for offset in [8, 32, 40] {
        let mut bytes = query().outgoing().unwrap();
        if offset == 32 {
            bytes[32..36].fill(0);
        } else {
            bytes[offset] ^= 1;
        }
        assert_eq!(dispatch(&bytes), -22);
    }
    PEER.with(|p| {
        let p = p.borrow();
        assert_eq!(p.lookups, 0);
        assert!(p.effects.is_empty());
    });
}
#[test]
fn stale_foreign_and_legacy_responses_cannot_retire_a_query() {
    let mut q = query();
    let answer = vector("ABSENT", q.token().wire());
    assert_eq!(q.accept(&answer), Err(-16));
    q.published().unwrap();
    for offset in [8, 16, 24, 28, 32, 40, 120, 127] {
        let mut wrong = answer;
        wrong[offset] ^= 1;
        assert_eq!(q.accept(&wrong), Err(-2));
        assert_eq!(q.result(), None);
    }
    assert_eq!(q.accept(&vector("LEGACY", q.token().wire())), Err(-2));
    q.accept(&answer).unwrap();
    assert_eq!(q.accept(&answer), Err(-16));
}
#[test]
fn unmarked_cleanup_keeps_the_original_ack_before_terminate_order() {
    let _environment = Environment::new(false);
    let mut q = rpc::Exchange::new(3, 2, 723).unwrap();
    q.begin().unwrap();
    assert_eq!(dispatch(&q.outgoing().unwrap()), 0);
    q.published().unwrap();
    PEER.with(|p| {
        let p = p.borrow();
        assert_eq!(p.lookups, 0);
        assert_eq!(p.effects, ["cleanup", "send", "terminate"]);
        assert_eq!(p.replies, [vector("LEGACY", q.token().wire())]);
        q.accept(&p.replies[0]).unwrap();
    });
    assert_eq!(q.result(), Some(0));
}
