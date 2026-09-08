// SPDX-License-Identifier: GPL-2.0
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_image.rs"]
mod image;
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
#[allow(dead_code)]
mod procfs {
    include!("native-application-procfs-reference.rs");
}

use core::{
    ffi::c_void,
    mem::{align_of, offset_of, size_of},
};
use std::cell::RefCell;

fn flatten(strings: &[&[u8]]) -> Vec<u8> {
    let mut bytes = vec![0; 8 * (strings.len() + 2)];
    image::put_word(&mut bytes, 0, strings.len() as u64).unwrap();
    for (index, string) in strings.iter().enumerate() {
        let offset = bytes.len();
        image::put_word(&mut bytes, 8 * (index + 1), offset as u64).unwrap();
        bytes.extend_from_slice(string);
        bytes.push(0);
    }
    bytes
}
fn valid() -> Vec<u8> {
    let args = flatten(&[b"/bin/true", b"hello"]);
    let envs = flatten(&[b"PATH=/bin"]);
    let mut bytes = vec![0; image::HEADER + image::SECTION];
    image::put_word(&mut bytes, 0, image::MAGIC).unwrap();
    bytes[8..12].copy_from_slice(&1i32.to_le_bytes());
    bytes[16..20].copy_from_slice(&771i32.to_le_bytes());
    for (offset, value) in [
        (image::USER_END, image::USER_LIMIT - image::LAUNCHER_GAP),
        (image::ARGS_LEN, args.len() as u64),
        (image::ENVS_LEN, envs.len() as u64),
        (image::HEADER, 0x400000),
        (image::HEADER + 8, 4096),
        (image::HEADER + 24, 32),
    ] {
        image::put_word(&mut bytes, offset, value).unwrap();
    }
    bytes[image::CPU_SET] = 1;
    bytes[image::HEADER + 40] = 5;
    bytes.extend(args);
    bytes.extend(envs);
    bytes
}

#[test]
fn existing_c_and_guest_rust_match_every_native_image_field() {
    let c: Vec<u64> = include_str!("native-application-image-layout.txt")
        .split_whitespace()
        .map(|n| n.parse().unwrap())
        .collect();
    let native = [
        image::HEADER as u64,
        8,
        image::SECTION as u64,
        8,
        image::HEADER as u64,
        image::MAGIC,
        image::NUM_SECTIONS as u64,
        image::CPU as u64,
        image::PID as u64,
        image::CREDENTIALS as u64,
        image::ENTRY as u64,
        image::USER_START as u64,
        image::USER_END as u64,
        image::THREAD as u64,
        image::PAGE_TABLE as u64,
        image::ARGS as u64,
        image::ARGS_LEN as u64,
        image::ENVS as u64,
        image::ENVS_LEN as u64,
        image::INTERP_ALIGN as u64,
        image::CPU_SET as u64,
        image::PROFILE as u64,
    ];
    let rust = [
        size_of::<abi::ProgramLoadDesc>() as u64,
        align_of::<abi::ProgramLoadDesc>() as u64,
        size_of::<abi::ProgramImageSection>() as u64,
        align_of::<abi::ProgramImageSection>() as u64,
        size_of::<abi::ProgramLoadDesc>() as u64,
        image::MAGIC,
        offset_of!(abi::ProgramLoadDesc, num_sections) as u64,
        offset_of!(abi::ProgramLoadDesc, cpu) as u64,
        offset_of!(abi::ProgramLoadDesc, pid) as u64,
        offset_of!(abi::ProgramLoadDesc, cred) as u64,
        offset_of!(abi::ProgramLoadDesc, entry) as u64,
        offset_of!(abi::ProgramLoadDesc, user_start) as u64,
        offset_of!(abi::ProgramLoadDesc, user_end) as u64,
        offset_of!(abi::ProgramLoadDesc, rprocess) as u64,
        offset_of!(abi::ProgramLoadDesc, rpgtable) as u64,
        offset_of!(abi::ProgramLoadDesc, args) as u64,
        offset_of!(abi::ProgramLoadDesc, args_len) as u64,
        offset_of!(abi::ProgramLoadDesc, envs) as u64,
        offset_of!(abi::ProgramLoadDesc, envs_len) as u64,
        offset_of!(abi::ProgramLoadDesc, interp_align) as u64,
        offset_of!(abi::ProgramLoadDesc, cpu_set) as u64,
        offset_of!(abi::ProgramLoadDesc, profile) as u64,
    ];
    assert_eq!(native.as_slice(), c);
    assert_eq!(rust.as_slice(), c);
    assert_eq!(
        image::DESCRIPTOR_CAPACITY,
        size_of::<abi::ProgramLoadDesc>() + 16 * size_of::<abi::ProgramImageSection>()
    );
}

#[test]
fn flat_vectors_validate_counts_offsets_null_slots_and_string_termination() {
    for strings in [
        vec![],
        vec![b"".as_slice()],
        vec![b"one".as_slice(), b"two".as_slice()],
    ] {
        assert_eq!(image::flattened(&flatten(&strings)), Ok(()));
    }
    let base = flatten(&[b"one", b"two"]);
    for (offset, value) in [
        (0, u64::MAX),
        (0, i32::MAX as u64),
        (8, 0),
        (8, base.len() as u64),
        (24, 1),
    ] {
        let mut bad = base.clone();
        image::put_word(&mut bad, offset, value).unwrap();
        assert!(image::flattened(&bad).is_err());
    }
    let mut bad = flatten(&[b"one"]);
    *bad.last_mut().unwrap() = 1;
    assert!(image::flattened(&bad).is_err());
    assert_eq!(image::flattened(&[0; 15]), Err(-7));
    assert_eq!(
        image::flattened(&vec![0; image::MAX_FLAT_BYTES + 1]),
        Err(-7)
    );
}

#[test]
fn image_input_rejects_geometry_and_cpu_errors_before_publication() {
    let base = valid();
    let layout = image::Input::parse(&base, 1).unwrap();
    assert_eq!((layout.descriptor, layout.cpu, layout.pid), (832, 0, 771));
    assert_eq!(base.len(), layout.descriptor + layout.args + layout.envs);
    for (offset, value) in [
        (0, 0),
        (image::ARGS_LEN, u64::MAX),
        (image::ENVS_LEN, 0),
        (image::USER_END, image::USER_LIMIT + 4096),
        (image::USER_START, 1),
        (image::HEADER, u64::MAX - 100),
        (image::HEADER + 8, 0),
        (image::HEADER + 24, 4097),
        (image::HEADER + 32, u64::MAX),
    ] {
        let mut bad = base.clone();
        image::put_word(&mut bad, offset, value).unwrap();
        assert!(image::Input::parse(&bad, 1).is_err(), "offset {offset}");
    }
    for (offset, value) in [
        (8, 0),
        (8, 17),
        (12, -1),
        (12, 1),
        (16, 0),
        (image::HEADER + 40, 8),
    ] {
        let mut bad = base.clone();
        bad[offset..offset + 4].copy_from_slice(&i32::to_le_bytes(value));
        assert!(image::Input::parse(&bad, 1).is_err());
    }
    let mut bad = base.clone();
    bad[image::CPU_SET] = 2;
    assert!(image::Input::parse(&bad, 1).is_err());
    let mut bad = base;
    bad[image::HEADER + 44] = 1;
    assert!(image::Input::parse(&bad, 1).is_err());
}

#[test]
fn reservation_gap_cannot_wrap_over_the_linux_executable() {
    assert_eq!(image::reservation_end(None), Ok(image::USER_LIMIT));
    assert_eq!(
        image::reservation_end(Some(0x6000_0000_0000)),
        Ok(0x6000_0000_0000 - image::LAUNCHER_GAP)
    );
    for value in [
        0,
        0x400000,
        image::LAUNCHER_GAP,
        image::USER_LIMIT + 2 * image::LAUNCHER_GAP,
    ] {
        assert_eq!(image::reservation_end(Some(value)), Err(-12));
    }
}

#[test]
fn four_level_page_walk_preserves_permissions_and_checks_every_table_read() {
    let address = 0x400123;
    let records = [
        (0x1000, 0x2007),
        (0x2000, 0x3007),
        (0x3010, 0x4007),
        (0x4000, 0x800087),
    ];
    let page = image::translate(0x1000, address, |at| {
        records
            .iter()
            .find(|(p, _)| *p == at)
            .map(|(_, v)| *v)
            .ok_or(-14)
    })
    .unwrap();
    assert_eq!(
        page,
        image::Page {
            physical: 0x800123,
            writable: true,
            executable: true
        }
    );
    let page = image::translate(0x1000, address, |at| {
        records
            .iter()
            .find(|(p, _)| *p == at)
            .map(|(_, v)| {
                if at == 0x2000 {
                    (v & !2) | (1 << 63)
                } else {
                    *v
                }
            })
            .ok_or(-14)
    })
    .unwrap();
    assert!(!page.writable && !page.executable);
    for failed in [0x1000, 0x2000, 0x3010, 0x4000] {
        assert_eq!(
            image::translate(0x1000, address, |at| if at == failed {
                Err(-14)
            } else {
                records
                    .iter()
                    .find(|(p, _)| *p == at)
                    .map(|(_, v)| *v)
                    .ok_or(-14)
            }),
            Err(-14)
        );
    }
}

#[test]
fn huge_page_walk_distinguishes_pat_and_rejects_reserved_geometry() {
    for (address, shift) in [(0x401234u64, 21), (0x123456u64, 30)] {
        let mut level = 39;
        let page = image::translate(0x1000, address, |_| {
            let pte = if level == shift {
                0x4000_1000 | 0x87
            } else {
                0x2007
            };
            level -= 9;
            Ok(pte)
        })
        .unwrap();
        assert_eq!(page.physical, 0x4000_0000 | (address & ((1 << shift) - 1)));
    }
    assert_eq!(image::translate(0x1000, 0, |_| Ok(0x2087)), Err(-71));
    assert_eq!(image::translate(0x1000, 0, |_| Ok(0x2003)), Err(-14));
    assert_eq!(
        image::translate(0x1000, image::USER_LIMIT, |_| panic!()),
        Err(-22)
    );
}

#[derive(Default)]
struct Peer {
    argument: u64,
    pid: i32,
    thread: u64,
    error: i32,
    events: Vec<&'static str>,
    reply: Vec<u8>,
}
thread_local! { static PEER: RefCell<Peer> = RefCell::new(Peer::default()); }
unsafe extern "C" fn prepare(argument: u64) -> i32 {
    PEER.with(|peer| {
        let mut peer = peer.borrow_mut();
        assert_eq!(argument, peer.argument);
        peer.events.push("prepare");
        peer.error
    })
}
unsafe extern "C" fn cleanup(pid: i32) -> i32 {
    PEER.with(|peer| {
        let mut peer = peer.borrow_mut();
        assert_eq!(pid, peer.pid);
        peer.events.push("cleanup");
        peer.error
    })
}
unsafe extern "C" fn terminate(pid: i32, thread: *mut c_void) {
    PEER.with(|peer| {
        let mut peer = peer.borrow_mut();
        assert_eq!(pid, peer.pid);
        assert_eq!(thread as u64, peer.thread);
        peer.events.push("terminate");
    })
}
unsafe extern "C" fn send(_: *mut c_void, packet: *mut abi::IkcScdPacket) {
    PEER.with(|peer| {
        let mut peer = peer.borrow_mut();
        peer.events.push("ack");
        peer.reply = core::slice::from_raw_parts(packet.cast::<u8>(), 128).to_vec();
    })
}
fn reply(exchange: &mut rpc::Exchange, is_prepare: bool, error: i32) -> Vec<u8> {
    exchange.begin().unwrap();
    let bytes = exchange.outgoing().unwrap();
    PEER.with(|peer| {
        *peer.borrow_mut() = Peer {
            argument: image::word(&bytes, 40).unwrap(),
            pid: image::integer(&bytes, 32).unwrap(),
            thread: image::word(&bytes, 40).unwrap(),
            error,
            ..Peer::default()
        }
    });
    let mut request: abi::IkcScdPacket = unsafe { core::mem::zeroed() };
    unsafe {
        core::ptr::copy_nonoverlapping(bytes.as_ptr(), (&raw mut request).cast(), 128);
        if is_prepare {
            assert_eq!(
                guest::host_prepare_process_request_result(
                    core::ptr::null_mut(),
                    &mut request,
                    Some(prepare),
                    Some(send)
                ),
                0
            );
        } else {
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
    }
    exchange.published().unwrap();
    PEER.with(|peer| {
        let peer = peer.borrow();
        assert_eq!(
            peer.events,
            if is_prepare {
                vec!["prepare", "ack"]
            } else {
                vec!["cleanup", "ack", "terminate"]
            }
        );
        peer.reply.clone()
    })
}

#[test]
fn actual_guest_prepare_and_prepared_cleanup_use_distinct_exact_tokens() {
    for error in [0, -12, -22] {
        let mut prepare = rpc::Exchange::prepare(0, 3, 991, 0x12000).unwrap();
        let token = prepare.token();
        let response = reply(&mut prepare, true, error);
        let mut stale = response.clone();
        stale[40] ^= 1;
        assert_eq!(prepare.accept(&stale), Err(-2));
        prepare.abandon();
        assert!(!prepare.retired());
        prepare.accept(&response).unwrap();
        assert!(prepare.retired());
        assert_eq!(prepare.result(), Some(error));
        let mut cleanup = rpc::Exchange::new(0, 0, 991).unwrap();
        assert_ne!(token, cleanup.token());
        cleanup.cleanup_target(3, 0xffff_8000_1234_5000).unwrap();
        let response = reply(&mut cleanup, false, 0);
        assert_eq!(cleanup.cleanup_target(0, 0), Err(-16));
        cleanup.accept(&response).unwrap();
        assert_eq!(cleanup.result(), Some(0));
    }
    for bad in [0, 1, 4095] {
        assert!(rpc::Exchange::prepare(0, 0, 1, bad).is_err());
    }
    let mut cleanup = rpc::Exchange::new(0, 0, 1).unwrap();
    assert_eq!(cleanup.cleanup_target(-1, 0), Err(-22));
    assert_eq!(cleanup.cleanup_target(0, 0x400000), Err(-22));
}

unsafe extern "C" fn deletion_physical(done: *mut c_void) -> u64 {
    assert!(!done.is_null());
    0xdead_beef
}
unsafe extern "C" fn deletion_send(_: *mut c_void, packet: *mut abi::IkcScdPacket) -> i32 {
    PEER.with(|peer| {
        let mut peer = peer.borrow_mut();
        peer.events.push("delete");
        peer.reply = core::slice::from_raw_parts(packet.cast::<u8>(), 128).to_vec();
    });
    0
}
fn deletion(os: i32, cpu: i32, pid: i32, tid: i32) -> Vec<u8> {
    let mut packet: abi::IkcScdPacket = unsafe { core::mem::zeroed() };
    let mut done = 0;
    unsafe {
        assert_eq!(
            procfs::procfs_thread_ctl_result(
                core::ptr::null_mut(),
                &mut packet,
                &mut done,
                rpc::TID_DELETE,
                os,
                cpu,
                pid,
                tid,
                Some(deletion_physical),
                Some(deletion_send),
                None,
            ),
            0
        );
    }
    // The unchanged guest DELETE neither waits nor requires a completion write.
    assert_eq!(done, 0);
    let bytes = PEER.with(|peer| peer.borrow().reply.clone());
    assert_eq!(image::word(&bytes, 120).unwrap(), 0xdead_beef);
    bytes
}

#[test]
fn prepared_cleanup_retains_owner_until_matching_unscheduled_deletion() {
    let mut cleanup = rpc::Exchange::new(0, 0, 991).unwrap();
    cleanup.cleanup_target(3, 0xffff_8000_1234_5000).unwrap();
    let response = reply(&mut cleanup, false, 0);
    let event = deletion(0, 3, 991, 0);
    assert_eq!(cleanup.accept_unscheduled_delete(&event), Err(-16));
    cleanup.abandon();
    cleanup.accept(&response).unwrap();
    assert_eq!(cleanup.result(), Some(0));
    assert!(!cleanup.release_ready() && !cleanup.retired());
    assert_eq!(cleanup.accept_unscheduled_delete(&event[..127]), Err(-22));
    for offset in [8, 24, 28, 32, 40] {
        let mut wrong = event.clone();
        wrong[offset] ^= 1;
        assert_eq!(cleanup.accept_unscheduled_delete(&wrong), Err(-2));
        assert!(!cleanup.release_ready() && !cleanup.retired());
    }
    let original = event.clone();
    cleanup.accept_unscheduled_delete(&event).unwrap();
    assert_eq!(event, original);
    assert!(cleanup.release_ready() && cleanup.retired());
    assert_eq!(cleanup.accept_unscheduled_delete(&event), Err(-16));
}

#[test]
fn unprepared_cleanup_releases_after_ack_without_a_deletion_event() {
    let mut cleanup = rpc::Exchange::new(0, 3, 991).unwrap();
    let response = reply(&mut cleanup, false, 0);
    cleanup.accept(&response).unwrap();
    assert!(cleanup.release_ready());
    let event = deletion(0, 3, 991, 0);
    assert_eq!(cleanup.accept_unscheduled_delete(&event), Err(-2));
    cleanup.abandon();
    assert!(cleanup.retired());
}
