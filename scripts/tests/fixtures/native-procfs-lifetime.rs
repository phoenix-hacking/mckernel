// SPDX-License-Identifier: GPL-2.0
//! Complete selected guest procfs implementation with controlled effects.
#[allow(dead_code)]
#[path = "../../../kernel/rust/abi.rs"]
mod abi;
#[allow(dead_code)]
#[path = "../../../kernel/rust/object_helpers.rs"]
mod object_helpers;
#[allow(dead_code)]
#[path = "../../../kernel/rust/page_helpers.rs"]
mod page_helpers;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_rpc.rs"]
mod application_rpc;
mod lock_helpers {
    include!("native-procfs-lock-type.rs");
}
mod procfs {
    include!("native-procfs-production.rs");
    #[cfg(test)]
    mod tests {
        use super::*;
        use crate::hooks::*;

        #[test]
        fn completion_follows_all_mapping_and_reference_retirement() {
            let mut case = Case::new(b"mcos0/41/maps\0");
            with(|s| {
                s.maps = [true; 4];
                s.refs = [1; 3];
                s.poison_after_reply = true;
            });
            unsafe {
                goto_cleanup(
                    &mut *case.packet,
                    0,
                    case.data.as_mut_ptr().cast(),
                    1,
                    DATA_MAPPED,
                    &mut *case.request,
                    REQUEST_MAPPED,
                    null_mut(),
                    &mut *case.process,
                    &mut *case.thread,
                    &mut *case.vm,
                );
            }
            with(|s| {
                assert_eq!(s.replies.len(), 1);
                assert_eq!(
                    s.replies[0].maps, [false; 4],
                    "reply before host mapping retirement"
                );
                assert_eq!(
                    s.replies[0].refs, [0; 3],
                    "reply before referenced process/thread/VM release"
                );
                assert_eq!(
                    s.data_unmap_bytes, 4096,
                    "response reuse changed a later guest request read"
                );
                assert_eq!(s.events.last(), Some(&"reply"));
            });
        }

        #[test]
        fn deferred_maps_pagemap_status_do_not_reply_or_release_the_queued_packet() {
            for path in [
                b"mcos0/41/maps\0".as_slice(),
                b"mcos0/41/pagemap\0",
                b"mcos0/41/status\0",
            ] {
                let mut case = Case::new(path);
                with(|s| s.lock_fails = true);
                let result = unsafe { process_procfs_request(&mut *case.packet) };
                with(|s| {
                    assert!(
                        s.replies.is_empty(),
                        "deferred operation acknowledged while packet remains queued"
                    );
                    assert_eq!(
                        result, 0,
                        "successful backlog submission must preserve C return"
                    );
                    assert_eq!(s.maps, [false; 4]);
                    assert_eq!(s.refs, [0; 3]);
                    assert_eq!(s.queue.len(), 1);
                    assert_eq!(s.allocations.len(), 1);
                });
                let (callback, argument) = with(|s| s.queue.remove(0));
                let result = unsafe { callback(argument as *mut c_void) };
                with(|s| {
                    assert!(s.replies.is_empty());
                    // Both existing C/Rust procfs_lock_retry_result return -EAGAIN.
                    assert_eq!(
                        result, -11,
                        "backlog callback must preserve the C retry result"
                    );
                    assert!(s.allocations.contains_key(&argument));
                    assert_eq!(s.maps, [false; 4]);
                    assert_eq!(s.refs, [0; 3]);
                });
            }
        }

        #[test]
        fn terminal_backlog_error_is_not_a_retry_after_packet_free() {
            let mut case = Case::new(b"mcos0/41/maps\0");
            with(|s| s.lock_fails = true);
            unsafe {
                process_procfs_request(&mut *case.packet);
            }
            let (callback, argument) = with(|s| {
                s.replies.clear();
                s.fail_pages = true;
                s.queue.remove(0)
            });
            case.request.pbuf = u64::MAX;
            let result = unsafe { callback(argument as *mut c_void) };
            with(|s| {
                assert!(!s.allocations.contains_key(&argument));
                assert_eq!(s.replies.len(), 1);
                assert_eq!(s.replies[0].error, -5);
                assert_eq!(
                    result, 0,
                    "freed terminal-error packet must never be retried"
                );
                assert_eq!(s.maps, [false; 4]);
                assert_eq!(s.refs, [0; 3]);
            });
        }

        #[test]
        fn backlog_success_finishes_and_frees_once() {
            let mut case = Case::new(b"mcos0/41/maps\0");
            with(|s| s.lock_fails = true);
            unsafe {
                process_procfs_request(&mut *case.packet);
            }
            let (callback, argument) = with(|s| {
                s.replies.clear();
                s.lock_fails = false;
                s.queue.remove(0)
            });
            let result = unsafe { callback(argument as *mut c_void) };
            with(|s| {
                assert_eq!(result, 0);
                assert!(!s.allocations.contains_key(&argument));
                assert_eq!(s.replies.len(), 1);
                assert_eq!(s.replies[0].error, 0);
                assert_eq!(s.replies[0].maps, [false; 4]);
                assert_eq!(s.replies[0].refs, [0; 3]);
                assert_eq!(s.maps, [false; 4]);
                assert_eq!(s.refs, [0; 3]);
            });
        }

        #[test]
        fn missing_task_never_releases_an_unacquired_process_reference() {
            let mut case = Case::new(b"mcos0/41/task/99/stat\0");
            unsafe {
                process_procfs_request(&mut *case.packet);
            }
            with(|s| {
                assert_eq!(
                    s.refs, [0; 3],
                    "lookup lock is not an acquired process reference"
                );
                assert_eq!(s.replies.len(), 1);
                assert_eq!(case.request.ret, -5);
            });
        }

        #[test]
        fn empty_buffer_release_retires_request_before_reply() {
            let mut case = Case::new(b"mcos0/41/maps\0");
            case.packet.msg = 0x15;
            case.request.pbuf = u64::MAX;
            unsafe {
                process_procfs_request(&mut *case.packet);
            }
            with(|s| {
                assert_eq!(s.replies.len(), 1);
                assert_eq!(s.replies[0].error, 0);
                assert_eq!(s.replies[0].maps, [false; 4]);
                assert_eq!(s.replies[0].refs, [0; 3]);
                assert_eq!(case.request.ret, 0);
                assert_eq!(s.events.last(), Some(&"reply"));
            });
        }
    }
}

#[cfg(test)]
mod wire_tests {
    use crate::{abi::*, application_rpc::Exchange, hooks::*};
    use core::mem::{offset_of, size_of};

    fn request(i: usize) -> [u8; 128] {
        let mut p = [0; 128];
        p[8..12].copy_from_slice(&0x12i32.to_le_bytes());
        p[16..24].copy_from_slice(&(0x1234 + i as u64).to_le_bytes());
        p[24..28].copy_from_slice(&((i % 4) as i32).to_le_bytes());
        p[28..32].copy_from_slice(&7i32.to_le_bytes());
        p[32..36].copy_from_slice(&(if i % 2 == 1 { 41i32 } else { 0 }).to_le_bytes());
        p[40..48].copy_from_slice(&(0x1000 * (i + 1) as u64).to_le_bytes());
        p[120..128].fill(0xff);
        p
    }

    fn answer(bytes: [u8; 128], error: i32) -> [u8; 128] {
        let mut packet = core::mem::MaybeUninit::<IkcScdPacket>::uninit();
        with(|s| *s = State::default());
        unsafe {
            core::ptr::copy_nonoverlapping(bytes.as_ptr(), packet.as_mut_ptr().cast(), 128);
            send_procfs_answer(packet.as_mut_ptr(), error);
        }
        with(|s| {
            assert_eq!(s.replies.len(), 1);
            s.replies[0].packet
        })
    }

    #[test]
    fn actual_answer_matches_original_c_with_only_native_retirement_extension() {
        assert_eq!(size_of::<IkcScdPacket>(), 128);
        assert_eq!(
            offset_of!(IkcScdPacket, body) + offset_of!(IkcScdPacketTraditional, resp_pa),
            120
        );
        assert_eq!(size_of::<ProcfsRead>(), 808);
        let errors = [0, -1, -5, -4095, i32::MIN, i32::MAX];
        let lines: Vec<_> = include_str!("native-procfs-answer-c.txt").lines().collect();
        assert_eq!(lines.len(), errors.len());
        for (i, error) in errors.into_iter().enumerate() {
            let hex = lines[i].split_whitespace().nth(2).unwrap();
            let original: Vec<u8> = hex
                .as_bytes()
                .chunks_exact(2)
                .map(|p| u8::from_str_radix(core::str::from_utf8(p).unwrap(), 16).unwrap())
                .collect();
            assert_eq!(original.len(), 128);
            assert_eq!(&original[120..], &[0; 8]);
            let actual = answer(request(i), error);
            assert_eq!(&actual[..120], &original[..120]);
            if cfg!(native_linux_irq_work_v6_12) {
                assert_eq!(&actual[120..], b"MCPR0001");
            } else {
                assert_eq!(actual.as_slice(), original.as_slice());
            }
        }
    }

    #[test]
    fn native_exchange_requires_matching_terminal_contract_and_retains_abandoned_work() {
        assert!(Exchange::new(0, 0, 0).is_err());
        for (os, cpu, pid, physical) in [
            (-1, 0, 0, 0x1000),
            (0, -1, 0, 0x1000),
            (0, 0, -1, 0x1000),
            (0, 0, 0, 0),
            (0, 0, 0, 0x1001),
        ] {
            assert!(Exchange::procfs(os, cpu, pid, physical, false).is_err());
        }
        for release in [false, true] {
            for pid in [0, 41] {
                for error in [0, -5, -5000] {
                    let mut exchange = Exchange::procfs(7, 2, pid, 0x1000, release).unwrap();
                    assert!(exchange.outgoing().is_none());
                    exchange.begin().unwrap();
                    let request = exchange.outgoing().unwrap();
                    assert_eq!(
                        i32::from_le_bytes(request[8..12].try_into().unwrap()),
                        if release { 0x15 } else { 0x12 }
                    );
                    for _ in 0..1024 {
                        assert_eq!(exchange.outgoing(), Some(request));
                        assert!(!exchange.release_ready());
                    }
                    let reply = answer(request, error);
                    assert!(
                        exchange.accept(&reply).is_err(),
                        "unpublished request completed"
                    );
                    exchange.published().unwrap();
                    exchange.abandon();
                    assert!(!exchange.retired());
                    if !cfg!(native_linux_irq_work_v6_12) {
                        assert_eq!(
                            exchange.accept(&reply),
                            Err(-2),
                            "legacy reply authorized host-page retirement"
                        );
                        assert!(!exchange.retired());
                        continue;
                    }
                    for offset in [8, 16, 24, 32, 40, 120] {
                        let mut stale = reply;
                        stale[offset] ^= 1;
                        assert_eq!(exchange.accept(&stale), Err(-2));
                        assert!(!exchange.retired());
                    }
                    let mut unmarked = reply;
                    unmarked[120..].fill(0);
                    assert_eq!(exchange.accept(&unmarked), Err(-2));
                    let mut another = Exchange::procfs(7, 2, pid, 0x1000, release).unwrap();
                    another.begin().unwrap();
                    another.published().unwrap();
                    assert_eq!(
                        another.accept(&reply),
                        Err(-2),
                        "stale response matched a reused address"
                    );
                    exchange.accept(&reply).unwrap();
                    assert_eq!(
                        exchange.result(),
                        Some(if error < -4095 { -71 } else { error })
                    );
                    assert!(exchange.retired());
                    assert_eq!(
                        exchange.accept(&reply),
                        Err(-16),
                        "duplicate terminal response accepted"
                    );
                }
            }
        }
    }

    #[test]
    fn missing_producer_callbacks_do_not_publish() {
        let mut packet: IkcScdPacket = unsafe { core::mem::zeroed() };
        with(|s| *s = State::default());
        unsafe {
            assert_eq!(
                crate::object_helpers::procfs_answer_result(
                    core::ptr::null_mut(),
                    &mut packet,
                    0,
                    None
                ),
                -22
            );
            assert_eq!(
                crate::object_helpers::procfs_answer_result(
                    core::ptr::null_mut(),
                    core::ptr::null_mut(),
                    0,
                    Some(capture_answer)
                ),
                -22
            );
        }
        with(|s| assert!(s.replies.is_empty()));
    }
}

pub mod hooks {
    use crate::{abi::*, lock_helpers::McsRwlockNodeIrqsave};
    use core::ffi::{c_char, c_void};
    use std::{
        alloc::{alloc_zeroed, dealloc, Layout},
        cell::RefCell,
        collections::BTreeMap,
    };
    pub const REQUEST_PHYSICAL: u64 = 0x1000;
    pub const REQUEST_MAPPED: u64 = 0x3000;
    pub const DATA_PHYSICAL: u64 = 0x2000;
    pub const DATA_MAPPED: u64 = 0x4000;
    pub type Backlog = unsafe extern "C" fn(*mut c_void) -> CInt;
    #[derive(Debug)]
    pub struct Reply {
        pub error: i32,
        pub maps: [bool; 4],
        pub refs: [i32; 3],
        pub packet: [u8; 128],
    }
    #[derive(Default)]
    pub struct State {
        pub request: usize,
        pub data: usize,
        pub process: usize,
        pub maps: [bool; 4],
        pub refs: [i32; 3],
        pub replies: Vec<Reply>,
        pub events: Vec<&'static str>,
        pub queue: Vec<(Backlog, usize)>,
        pub allocations: BTreeMap<usize, usize>,
        pub lock_fails: bool,
        pub fail_pages: bool,
        pub poison_after_reply: bool,
        pub data_unmap_bytes: u64,
    }
    impl Drop for State {
        fn drop(&mut self) {
            for (&p, &n) in &self.allocations {
                unsafe { dealloc(p as *mut u8, Layout::from_size_align(n, 8).unwrap()) };
            }
        }
    }
    thread_local! { static STATE:RefCell<State>=RefCell::new(State::default()); }
    pub fn with<T>(f: impl FnOnce(&mut State) -> T) -> T {
        STATE.with(|s| f(&mut s.borrow_mut()))
    }
    pub struct Case {
        pub request: Box<ProcfsRead>,
        pub packet: Box<IkcScdPacket>,
        pub process: Box<Process>,
        pub thread: Box<Thread>,
        pub vm: Box<ProcessVm>,
        pub data: Vec<u8>,
        _space: Box<AddressSpace>,
    }
    fn zeroed<T>() -> Box<T> {
        Box::new(unsafe { core::mem::zeroed() })
    }
    impl Case {
        pub fn new(name: &[u8]) -> Self {
            with(|s| *s = State::default());
            let mut request: Box<ProcfsRead> = zeroed();
            let mut packet: Box<IkcScdPacket> = zeroed();
            let mut process: Box<Process> = zeroed();
            let mut thread: Box<Thread> = zeroed();
            let mut vm: Box<ProcessVm> = zeroed();
            let mut space: Box<AddressSpace> = zeroed();
            let mut data = vec![0u8; 4096];
            request.pbuf = DATA_PHYSICAL;
            request.count = 4096;
            request.ret = -5;
            for (dst, src) in request.fname.iter_mut().zip(name) {
                *dst = *src as i8;
            }
            packet.msg = 0x12;
            unsafe {
                (*(&raw mut packet.body).cast::<IkcScdPacketTraditional>()).arg = REQUEST_PHYSICAL;
            }
            process.pid = 41;
            process.vm = &mut *vm;
            thread.tid = 41;
            thread.proc = &mut *process;
            vm.address_space = &mut *space;
            let head = &raw mut process.threads_list;
            let node = &raw mut thread.siblings_list;
            unsafe {
                (*head).next = node;
                (*head).prev = node;
                (*node).next = head;
                (*node).prev = head;
            }
            with(|s| {
                s.request = (&mut *request) as *mut _ as usize;
                s.data = data.as_mut_ptr() as usize;
                s.process = (&mut *process) as *mut _ as usize;
            });
            Self {
                request,
                packet,
                process,
                thread,
                vm,
                data,
                _space: space,
            }
        }
    }
    fn allocate(n: usize) -> *mut c_void {
        let p = unsafe { alloc_zeroed(Layout::from_size_align(n, 8).unwrap()) };
        assert!(!p.is_null());
        with(|s| {
            s.allocations.insert(p as usize, n);
        });
        p.cast()
    }
    fn free(p: *mut c_void) {
        let n = with(|s| s.allocations.remove(&(p as usize))).expect("free without an allocation");
        unsafe { dealloc(p.cast(), Layout::from_size_align(n, 8).unwrap()) };
    }
    #[no_mangle]
    pub static num_processors: CInt = 1;
    #[no_mangle]
    pub unsafe extern "C" fn ihk_mc_get_osnum() -> CInt {
        0
    }
    #[no_mangle]
    pub unsafe extern "C" fn ihk_mc_map_memory(
        _os: *mut c_void,
        physical: CULong,
        _bytes: CULong,
    ) -> CULong {
        with(|s| match physical {
            REQUEST_PHYSICAL => {
                s.maps[0] = true;
                REQUEST_MAPPED
            }
            DATA_PHYSICAL => {
                s.maps[2] = true;
                DATA_MAPPED
            }
            _ => panic!("unexpected map {physical:x}"),
        })
    }
    #[no_mangle]
    pub unsafe extern "C" fn ihk_mc_map_virtual(
        physical: CULong,
        _pages: CULong,
        _attr: CULong,
    ) -> *mut CULong {
        with(|s| match physical {
            REQUEST_MAPPED => {
                s.maps[1] = true;
                s.request
            }
            DATA_MAPPED => {
                s.maps[3] = true;
                s.data
            }
            _ => panic!("unexpected virtual map"),
        }) as *mut CULong
    }
    #[no_mangle]
    pub unsafe extern "C" fn ihk_mc_unmap_memory(
        _os: *mut c_void,
        physical: CULong,
        bytes: CULong,
    ) {
        with(|s| match physical {
            REQUEST_MAPPED => {
                s.maps[0] = false;
                s.events.push("request physical unmap");
            }
            DATA_MAPPED => {
                s.maps[2] = false;
                s.data_unmap_bytes = bytes;
                s.events.push("data physical unmap");
            }
            _ => panic!("unexpected physical unmap"),
        })
    }
    #[no_mangle]
    pub unsafe extern "C" fn ihk_mc_unmap_virtual(p: *mut CULong, _pages: CULong) {
        with(|s| {
            if p as usize == s.request {
                s.maps[1] = false;
                s.events.push("request virtual unmap");
            } else if p as usize == s.data {
                s.maps[3] = false;
                s.events.push("data virtual unmap");
            } else {
                panic!("unexpected virtual unmap");
            }
        })
    }
    #[no_mangle]
    pub unsafe extern "C" fn send_procfs_answer(p: *mut IkcScdPacket, error: CInt) {
        assert_eq!(
            crate::object_helpers::procfs_answer_result(
                core::ptr::null_mut(),
                p,
                error,
                Some(capture_answer)
            ),
            0
        );
    }
    pub unsafe extern "C" fn capture_answer(_channel: *mut c_void, p: *mut IkcScdPacket) {
        let mut packet = [0; 128];
        core::ptr::copy_nonoverlapping(p.cast::<u8>(), packet.as_mut_ptr(), 128);
        with(|s| {
            s.replies.push(Reply {
                error: (*p).err,
                maps: s.maps,
                refs: s.refs,
                packet,
            });
            s.events.push("reply");
            if s.poison_after_reply {
                (*(s.request as *mut ProcfsRead)).count = 0x12345678;
            }
        })
    }
    #[no_mangle]
    pub unsafe extern "C" fn find_process(
        pid: CInt,
        _lock: *mut McsRwlockNodeIrqsave,
    ) -> *mut Process {
        with(|s| {
            if pid == 41 {
                s.process as *mut Process
            } else {
                core::ptr::null_mut()
            }
        })
    }
    #[no_mangle]
    pub unsafe extern "C" fn process_unlock(_p: *mut Process, _lock: *mut McsRwlockNodeIrqsave) {}
    #[no_mangle]
    pub unsafe extern "C" fn hold_process(_p: *mut Process) {
        with(|s| s.refs[0] += 1)
    }
    #[no_mangle]
    pub unsafe extern "C" fn hold_thread(_p: *mut Thread) -> CInt {
        with(|s| s.refs[1] += 1);
        1
    }
    #[no_mangle]
    pub unsafe extern "C" fn hold_process_vm(_p: *mut ProcessVm) {
        with(|s| s.refs[2] += 1)
    }
    #[no_mangle]
    pub unsafe extern "C" fn release_process(_p: *mut Process) {
        with(|s| {
            s.refs[0] -= 1;
            s.events.push("process release");
        })
    }
    #[no_mangle]
    pub unsafe extern "C" fn release_thread(_p: *mut Thread) {
        with(|s| {
            s.refs[1] -= 1;
            s.events.push("thread release");
        })
    }
    #[no_mangle]
    pub unsafe extern "C" fn release_process_vm(_p: *mut ProcessVm) {
        with(|s| {
            s.refs[2] -= 1;
            s.events.push("vm release");
        })
    }
    #[no_mangle]
    pub unsafe extern "C" fn ihk_rwspinlock_read_trylock_noirq(_lock: *mut c_void) -> CInt {
        with(|s| (!s.lock_fails) as CInt)
    }
    #[no_mangle]
    pub unsafe extern "C" fn ihk_rwspinlock_read_unlock_noirq(_lock: *mut c_void) {}
    #[no_mangle]
    pub unsafe extern "C" fn __mcs_rwlock_reader_lock(
        _lock: *mut c_void,
        _node: *mut McsRwlockNodeIrqsave,
    ) {
    }
    #[no_mangle]
    pub unsafe extern "C" fn __mcs_rwlock_reader_unlock(
        _lock: *mut c_void,
        _node: *mut McsRwlockNodeIrqsave,
    ) {
    }
    #[no_mangle]
    pub unsafe extern "C" fn lookup_process_memory_range(
        _vm: *mut ProcessVm,
        _start: CULong,
        _end: CULong,
    ) -> *mut VmRange {
        core::ptr::null_mut()
    }
    #[no_mangle]
    pub unsafe extern "C" fn next_process_memory_range(
        _vm: *mut ProcessVm,
        _range: *mut VmRange,
    ) -> *mut VmRange {
        core::ptr::null_mut()
    }
    #[no_mangle]
    pub unsafe extern "C" fn _kmalloc(
        size: CInt,
        _flags: CInt,
        _file: *mut c_char,
        _line: CInt,
    ) -> *mut c_void {
        allocate(size as usize)
    }
    #[no_mangle]
    pub unsafe extern "C" fn _kfree(p: *mut c_void, _file: *mut c_char, _line: CInt) {
        free(p)
    }
    #[no_mangle]
    pub unsafe extern "C" fn _ihk_mc_alloc_aligned_pages_node(
        npages: CInt,
        _align: CInt,
        _flag: CULong,
        _node: CInt,
        _user: CInt,
        _virt: CULong,
        _file: *mut c_char,
        _line: CInt,
    ) -> *mut c_void {
        if with(|s| s.fail_pages) {
            core::ptr::null_mut()
        } else {
            allocate(npages as usize * 4096)
        }
    }
    #[no_mangle]
    pub unsafe extern "C" fn _ihk_mc_free_pages(
        p: *mut c_void,
        _npages: CInt,
        _user: CInt,
        _file: *mut c_char,
        _line: CInt,
    ) {
        free(p)
    }
    #[no_mangle]
    pub unsafe extern "C" fn add_backlog(callback: Option<Backlog>, arg: *mut c_void) -> CInt {
        with(|s| s.queue.push((callback.unwrap(), arg as usize)));
        0
    }
    #[no_mangle]
    pub unsafe extern "C" fn virt_to_phys(p: *mut c_void) -> CULong {
        p as CULong
    }
    #[no_mangle]
    pub unsafe extern "C" fn phys_to_virt(p: CULong) -> *mut c_void {
        p as *mut c_void
    }
    include!("native-procfs-unused-effects.rs");
}
