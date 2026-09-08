// SPDX-License-Identifier: GPL-2.0-only
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/abi/sysfs_request.rs"]
mod sysfs_request;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_rpc.rs"]
mod sysfs_rpc;
#[allow(dead_code)]
#[path = "../../../kernel/rust/abi.rs"]
mod abi;
#[allow(dead_code)]
mod guest {
    include!("native-sysfs-guest-reference.rs");
}
use std::{
    cell::UnsafeCell,
    sync::{
        atomic::{AtomicI32, AtomicUsize, Ordering},
        Arc,
    },
    thread,
};
use sysfs_request::{Client, Kind, Operation};
use sysfs_rpc::{Call, Exchange};

const KINDS: [Kind; 5] = [
    Kind::Create,
    Kind::Mkdir,
    Kind::Symlink,
    Kind::Lookup,
    Kind::Unlink,
];
const CLIENT: Client = Client {
    operations: 0xffff_ffff_fe80_9000,
    instance: 0xffff_ffff_fe80_a008,
};
#[repr(align(4096))]
struct Page(UnsafeCell<[u8; 4096]>);
// SAFETY: Peers exclusively hand off initialized bytes through busy.
unsafe impl Sync for Page {}
impl Page {
    fn pointer(&self) -> *mut u8 {
        self.0.get().cast()
    }
    fn busy(&self, kind: Kind) -> &AtomicI32 {
        unsafe { AtomicI32::from_ptr(self.pointer().add(kind.layout().busy).cast()) }
    }
    fn prepare(&self, kind: Kind) {
        let p = self.pointer();
        unsafe {
            // The server can poll busy while the peer prepares the next call.
            // Never overwrite that atomic word through a non-atomic fill.
            p.write_bytes(0xa5, kind.layout().busy);
            p.add(kind.layout().busy + 4)
                .write_bytes(0xa5, 4096 - kind.layout().busy - 4);
            match kind {
                Kind::Create => {
                    p.cast::<i32>().write(0o644);
                    p.add(8).cast::<u64>().write(CLIENT.operations);
                    p.add(16).cast::<u64>().write(CLIENT.instance);
                }
                Kind::Symlink => p.add(8).cast::<u64>().write(17),
                Kind::Unlink => p.cast::<u32>().write(1),
                _ => {}
            }
            std::ptr::copy_nonoverlapping(
                b"/sys/test/value\0".as_ptr(),
                p.add(kind.layout().path),
                16,
            );
        }
        self.busy(kind).store(1, Ordering::Release);
    }
}

#[test]
fn five_layouts_and_all_payload_offsets_match_unchanged_c() {
    use std::mem::offset_of;
    let witness: Vec<usize> = include_str!("native-sysfs-request-layout.txt")
        .split_whitespace()
        .map(|v| v.parse().unwrap())
        .collect();
    let mut actual = Vec::new();
    for kind in KINDS {
        let l = kind.layout();
        actual.extend([l.bytes, l.alignment, l.error, l.path, l.busy]);
    }
    actual.extend([
        offset_of!(sysfs_request::Create, mode),
        offset_of!(sysfs_request::Create, client_ops),
        offset_of!(sysfs_request::Create, client_instance),
        offset_of!(sysfs_request::WithHandle, handle),
        offset_of!(sysfs_request::WithHandle, handle),
        offset_of!(sysfs_request::WithHandle, handle),
        offset_of!(sysfs_request::Unlink, flags),
    ]);
    assert_eq!(actual, witness);
    for (kind, message) in KINDS.into_iter().zip([0x30, 0x32, 0x34, 0x36, 0x38]) {
        assert_eq!(Kind::from_message(message), Some(kind));
    }
    for message in [i32::MIN, -1, 0, 0x31, 0x39, 0x3a, 0x40, i32::MAX] {
        assert_eq!(Kind::from_message(message), None);
    }
}

#[test]
fn bounded_owned_snapshots_and_validation_do_not_write_peer_inputs() {
    let page = Page(UnsafeCell::new([0; 4096]));
    for kind in KINDS {
        page.prepare(kind);
        let before = unsafe { *page.0.get() };
        let snapshot = unsafe { sysfs_request::read(kind, page.pointer()) }.unwrap();
        assert_eq!(snapshot.path(), b"/sys/test/value");
        let expected = match kind {
            Kind::Create => Operation::Create {
                mode: 0o644,
                client: CLIENT,
            },
            Kind::Mkdir => Operation::Mkdir,
            Kind::Symlink => Operation::Symlink { target: 17 },
            Kind::Lookup => Operation::Lookup,
            Kind::Unlink => Operation::Unlink { flags: 1 },
        };
        assert_eq!(snapshot.operation, expected);
        assert_eq!(unsafe { *page.0.get() }, before);
        unsafe { page.pointer().add(kind.layout().path).write(b'X') };
        assert_eq!(snapshot.path(), b"/sys/test/value");
        unsafe {
            page.pointer()
                .add(kind.layout().path)
                .write_bytes(b'a', 1024)
        };
        assert_eq!(
            unsafe { sysfs_request::read(kind, page.pointer()) }.err(),
            Some(-36)
        );
        unsafe { page.pointer().add(kind.layout().path + 1023).write(0) };
        assert_eq!(
            unsafe { sysfs_request::read(kind, page.pointer()) }
                .unwrap()
                .path()
                .len(),
            1023
        );
        assert_eq!(
            unsafe { sysfs_request::read(kind, page.pointer().add(1)) }.err(),
            Some(-22)
        );
        assert_eq!(
            unsafe { sysfs_request::read(kind, std::ptr::null_mut()) }.err(),
            Some(-22)
        );
        page.busy(kind).store(0, Ordering::Release);
        assert_eq!(
            unsafe { sysfs_request::read(kind, page.pointer()) }.err(),
            Some(-16)
        );
    }
    for mode in [-1, 0o1000, 0o100644, i32::MAX] {
        page.prepare(Kind::Create);
        unsafe { page.pointer().cast::<i32>().write(mode) };
        assert_eq!(
            unsafe { sysfs_request::read(Kind::Create, page.pointer()) }.err(),
            Some(-22)
        );
    }
    for flags in [2, 3, u32::MAX] {
        page.prepare(Kind::Unlink);
        unsafe { page.pointer().cast::<u32>().write(flags) };
        assert_eq!(
            unsafe { sysfs_request::read(Kind::Unlink, page.pointer()) }.err(),
            Some(-22)
        );
    }
    for handle in [0, 1 << 63, u64::MAX] {
        page.prepare(Kind::Symlink);
        unsafe { page.pointer().add(8).cast::<u64>().write(handle) };
        assert_eq!(
            unsafe { sysfs_request::read(Kind::Symlink, page.pointer()) }.err(),
            Some(-22)
        );
    }
}

#[test]
fn replies_change_only_error_optional_handle_and_final_busy() {
    let page = Page(UnsafeCell::new([0; 4096]));
    for kind in KINDS {
        for error in [-4095i32, -22, -12, 0] {
            page.prepare(kind);
            let handle = if matches!(kind, Kind::Mkdir | Kind::Lookup) && error == 0 {
                Some(42)
            } else {
                None
            };
            let mut expected = unsafe { *page.0.get() };
            let l = kind.layout();
            expected[l.error..l.error + 4].copy_from_slice(&error.to_le_bytes());
            expected[l.busy..l.busy + 4].copy_from_slice(&0i32.to_le_bytes());
            if let Some(handle) = handle {
                expected[8..16].copy_from_slice(&u64::to_le_bytes(handle));
            }
            unsafe { sysfs_request::complete(kind, page.pointer(), error, handle) }.unwrap();
            assert_eq!(unsafe { *page.0.get() }, expected);
            assert_eq!(
                unsafe { sysfs_request::complete(kind, page.pointer(), error, handle) },
                Err(-16)
            );
        }
        page.prepare(kind);
        let original = unsafe { *page.0.get() };
        for (error, handle) in [
            (1, None),
            (-4096, None),
            (-1, Some(1)),
            (0, Some(0)),
            (0, Some(u64::MAX)),
        ] {
            assert_eq!(
                unsafe { sysfs_request::complete(kind, page.pointer(), error, handle) },
                Err(-22)
            );
            assert_eq!(unsafe { *page.0.get() }, original);
        }
        if matches!(kind, Kind::Mkdir | Kind::Lookup) {
            assert_eq!(
                unsafe { sysfs_request::complete(kind, page.pointer(), 0, None) },
                Err(-22)
            );
        }
    }
}

#[test]
fn every_metadata_completion_publishes_before_immediate_peer_reuse() {
    for kind in KINDS {
        let page = Arc::new(Page(UnsafeCell::new([0xa5; 4096])));
        page.busy(kind).store(0, Ordering::Release);
        let publication = Arc::new(AtomicUsize::new(0));
        let peer = page.clone();
        let owner = publication.clone();
        let worker = thread::spawn(move || {
            for round in 1..=512usize {
                while peer.busy(kind).load(Ordering::Acquire) != 1 {
                    thread::yield_now();
                }
                let request = unsafe { sysfs_request::read(kind, peer.pointer()) }.unwrap();
                assert_eq!(request.path(), b"/sys/test/value");
                owner.store(round, Ordering::Relaxed);
                let handle = if matches!(kind, Kind::Mkdir | Kind::Lookup) {
                    Some(round as u64)
                } else {
                    None
                };
                unsafe { sysfs_request::complete(kind, peer.pointer(), 0, handle) }.unwrap();
            }
        });
        for round in 1..=512usize {
            page.prepare(kind);
            while page.busy(kind).load(Ordering::Acquire) != 0 {
                thread::yield_now();
            }
            assert_eq!(publication.load(Ordering::Relaxed), round);
            assert_eq!(
                unsafe { page.pointer().add(kind.layout().error).cast::<i32>().read() },
                0
            );
            if matches!(kind, Kind::Mkdir | Kind::Lookup) {
                assert_eq!(
                    unsafe { page.pointer().add(8).cast::<u64>().read() },
                    round as u64
                );
            }
        }
        worker.join().unwrap();
    }
}

fn response(message: i32, token: u64, value: i64, error: i32) -> [u8; 128] {
    let mut p = [0; 128];
    p[8..12].copy_from_slice(&message.to_le_bytes());
    p[12..16].copy_from_slice(&error.to_le_bytes());
    p[24..32].copy_from_slice(&token.to_le_bytes());
    p[32..40].copy_from_slice(&value.to_le_bytes());
    p
}

#[test]
fn rpc_retries_interruption_and_late_replies_preserve_single_buffer_ownership() {
    let mut state = Exchange::new();
    let token = state.begin(CLIENT, Call::Show { capacity: 4095 }).unwrap();
    let packet = state.outgoing().unwrap();
    assert_eq!(state.outgoing(), Some(packet));
    assert_eq!(state.begin(CLIENT, Call::Release), Err(-16));
    assert_eq!(state.finish(token), Err(-16));
    assert_eq!(state.accept(&response(0x3b, token.wire(), 7, 0)), Err(-16));
    state.published(token).unwrap();
    assert_eq!(state.outgoing(), None);
    assert_eq!(state.fail_unpublished(token, -5), Err(-16));
    assert_eq!(state.finish(token), Err(-16)); // An interrupted waiter cannot free this buffer.
    for p in [
        response(0x3d, token.wire(), 7, 0),
        response(0x3b, token.wire() + 1, 7, 0),
    ] {
        assert_eq!(state.accept(&p), Err(-2));
    }
    assert_eq!(state.completed(token), Ok(false));
    state.accept(&response(0x3b, token.wire(), 7, 0)).unwrap();
    assert_eq!(state.begin(CLIENT, Call::Release), Err(-16));
    assert_eq!(state.finish(token), Ok(Ok(7)));
    let second = state.begin(CLIENT, Call::Store { bytes: 7 }).unwrap();
    assert_ne!(token, second);
    state.published(second).unwrap();
    assert_eq!(state.accept(&response(0x3b, token.wire(), 7, 0)), Err(-2));
    state.accept(&response(0x3d, second.wire(), 7, 0)).unwrap();
    assert_eq!(state.finish(second), Ok(Ok(7)));
    let third = state.begin(CLIENT, Call::Release).unwrap();
    state.fail_unpublished(third, -12).unwrap();
    assert_eq!(state.finish(third), Ok(Err(-12)));
}

#[test]
fn rpc_rejects_malformed_counts_errors_special_ops_and_foreign_services() {
    for (call, message, value, error, expected) in [
        (Call::Show { capacity: 4095 }, 0x3b, 4095, 0, Ok(4095)),
        (Call::Show { capacity: 4095 }, 0x3b, 4096, 0, Err(-75)),
        (Call::Store { bytes: 8 }, 0x3d, 9, 0, Err(-75)),
        (Call::Release, 0x3f, 1, 0, Err(-75)),
        (
            Call::Show { capacity: 4095 },
            0x3b,
            -4095,
            -4095,
            Err(-4095),
        ),
        (Call::Show { capacity: 4095 }, 0x3b, -4096, -4096, Err(-71)),
        (Call::Show { capacity: 4095 }, 0x3b, i64::MIN, 0, Err(-71)),
        (Call::Show { capacity: 4095 }, 0x3b, 2, -5, Err(-71)),
        (Call::Show { capacity: 4095 }, 0x3b, -5, 0, Err(-71)),
    ] {
        let mut state = Exchange::new();
        let token = state.begin(CLIENT, call).unwrap();
        state.published(token).unwrap();
        state
            .accept(&response(message, token.wire(), value, error))
            .unwrap();
        assert_eq!(state.finish(token), Ok(expected));
    }
    let mut state = Exchange::new();
    for operations in [1, 8, 9, 1000] {
        assert_eq!(
            state.begin(
                Client {
                    operations,
                    ..CLIENT
                },
                Call::Release
            ),
            Err(-22)
        );
    }
    for call in [
        Call::Show { capacity: 4097 },
        Call::Store { bytes: usize::MAX },
    ] {
        assert_eq!(state.begin(CLIENT, call), Err(-22));
    }
    let mut other = Exchange::new();
    let a = state.begin(CLIENT, Call::Release).unwrap();
    let b = other.begin(CLIENT, Call::Release).unwrap();
    assert_ne!(a, b);
    state.published(a).unwrap();
    assert_eq!(state.accept(&response(0x3f, b.wire(), 0, 0)), Err(-2));
    assert_eq!(state.accept(&[0; 127]), Err(-22));
    assert_eq!(state.completed(a), Ok(false));
}

#[test]
fn actual_guest_response_bodies_match_native_exchange_packets() {
    use std::{
        ffi::c_void,
        mem::{offset_of, size_of},
        ptr,
    };
    assert_eq!(size_of::<abi::IkcScdPacket>(), 128);
    assert_eq!(offset_of!(abi::IkcScdPacket, msg), 8);
    assert_eq!(offset_of!(abi::IkcScdPacket, err), 12);
    assert_eq!(offset_of!(abi::IkcScdPacket, body), 24);
    #[repr(align(8))]
    struct Packet([u8; 128]);
    thread_local! {static REPLY: std::cell::RefCell<Packet>=const{std::cell::RefCell::new(Packet([0;128]))};}
    unsafe extern "C" fn send(msg: i32, err: i32, a: i64, b: i64) -> i32 {
        REPLY.with(|reply| {
            guest::sysfss_packet_prepare_result(
                reply.borrow_mut().0.as_mut_ptr().cast(),
                msg,
                err,
                a,
                b,
            )
        })
    }
    unsafe extern "C" fn show(
        ops: *mut c_void,
        instance: *mut c_void,
        data: *mut c_void,
        size: usize,
    ) -> i64 {
        assert_eq!(ops as u64, CLIENT.operations);
        assert_eq!(instance as u64, CLIENT.instance);
        assert_eq!(size, 4096);
        ptr::copy_nonoverlapping(b"guest=7\n".as_ptr(), data.cast(), 8);
        8
    }
    unsafe extern "C" fn store(
        ops: *mut c_void,
        instance: *mut c_void,
        data: *mut c_void,
        size: usize,
    ) -> i64 {
        assert_eq!(ops as u64, CLIENT.operations);
        assert_eq!(instance as u64, CLIENT.instance);
        assert_eq!(
            std::slice::from_raw_parts(data.cast::<u8>(), size),
            b"new=9\n"
        );
        size as i64
    }
    for round in 0..4096 {
        let mut state = Exchange::new();
        let call = match round % 3 {
            0 => Call::Show { capacity: 4095 },
            1 => Call::Store { bytes: 6 },
            _ => Call::Release,
        };
        let token = state.begin(CLIENT, call).unwrap();
        let (_, packet) = state.outgoing().unwrap();
        let msg = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        assert_eq!(
            msg,
            match call {
                Call::Show { .. } => 0x3a,
                Call::Store { .. } => 0x3c,
                Call::Release => 0x3e,
            }
        );
        assert_eq!(
            u64::from_le_bytes(packet[32..40].try_into().unwrap()),
            CLIENT.operations
        );
        assert_eq!(
            u64::from_le_bytes(packet[40..48].try_into().unwrap()),
            CLIENT.instance
        );
        state.published(token).unwrap();
        let mut data = [0; 4096];
        let mut ssize = 0;
        let mut err = 0;
        REPLY.with(|p| p.borrow_mut().0 = [0; 128]);
        let result = unsafe {
            match call {
                Call::Show { .. } => guest::sysfss_req_show_body_result(
                    token.wire() as i64,
                    CLIENT.operations as *mut _,
                    CLIENT.instance as *mut _,
                    data.as_mut_ptr().cast(),
                    4096,
                    Some(show),
                    Some(send),
                    &mut ssize,
                    &mut err,
                ),
                Call::Store { bytes } => {
                    data[..bytes].copy_from_slice(b"new=9\n");
                    guest::sysfss_req_store_body_result(
                        token.wire() as i64,
                        CLIENT.operations as *mut _,
                        CLIENT.instance as *mut _,
                        data.as_mut_ptr().cast(),
                        bytes,
                        Some(store),
                        Some(send),
                        &mut ssize,
                        &mut err,
                    )
                }
                Call::Release => guest::sysfss_req_release_body_result(
                    token.wire() as i64,
                    CLIENT.operations as *mut _,
                    CLIENT.instance as *mut _,
                    None,
                    Some(send),
                    &mut err,
                ),
            }
        };
        assert_eq!(result, 0);
        assert_eq!(err, 0);
        let reply = REPLY.with(|p| p.borrow().0);
        state.accept(&reply).unwrap();
        assert_eq!(state.finish(token), Ok(Ok(ssize as usize)));
    }
}
