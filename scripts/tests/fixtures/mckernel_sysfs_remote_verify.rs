// SPDX-License-Identifier: GPL-2.0-only
//! Real Linux files/callbacks with an independent, module-owned protocol peer.
//! This fixture proves no IHK generation, McKernel memory map or guest boot.
use core::{
    ptr,
    sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering},
};
use kernel::{
    bindings, fmt,
    prelude::*,
    str::CString,
    sync::{new_mutex, Arc, Mutex},
};
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/abi/sysfs_request.rs"]
mod sysfs_request;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_rpc.rs"]
mod sysfs_rpc;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_objects.rs"]
mod sysfs_objects;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_tree.rs"]
mod sysfs_tree;
#[allow(dead_code)]
#[path = "../../../host-kernel/native-rust/sysfs_remote.rs"]
mod sysfs_remote;

// Substitute only the setup mapping carrier and diagnostic identity. The
// actual adapter/state/tree/object sources above are included unchanged.
// This owner is deliberately not an OsToken or simulated IHK authority.
mod sysfs_setup {
    pub(crate) struct FixtureOwner;
    impl FixtureOwner {
        pub(crate) fn slot(&self) -> u32 {
            0
        }
        pub(crate) fn generation(&self) -> u64 {
            1
        }
    }
    pub(crate) struct SharedData {
        pub(crate) owner: FixtureOwner,
        pub(crate) physical: u64,
        pub(crate) address: u64,
        pub(crate) bytes: usize,
    }
}
use sysfs_objects::{AttributeOps, Directory, File};
use sysfs_remote::{Attribute, Remote};
use sysfs_request::Client;
use sysfs_tree::Tree;
const OPS: u64 = 0xffff_ffff_fe80_1234;

module! {
    type: RemoteVerify,
    name: "mckernel_sysfs_remote_verify",
    author: "McKernel developers",
    description: "Native remote sysfs callback and drain verification",
    license: "GPL",
}

struct Page(usize);
impl Page {
    fn new() -> Result<Self> {
        // SAFETY: Sleepable module init; the unique page is retained until all
        // callbacks and the independent peer are drained and joined.
        let address = unsafe {
            bindings::get_free_pages_noprof(bindings::GFP_KERNEL | bindings::__GFP_ZERO, 0)
        };
        if address == 0 {
            return Err(ENOMEM);
        }
        Ok(Self(address as usize))
    }
}
impl Drop for Page {
    fn drop(&mut self) {
        unsafe { bindings::free_pages(self.0 as u64, 0) };
    }
}

struct Stats {
    gate: AtomicBool,
    phase: AtomicUsize,
    released: AtomicU64,
    requests: AtomicU64,
    retries: AtomicU64,
}
struct Status(Arc<Stats>);
impl AttributeOps for Status {
    fn show(&self, output: &mut [u8]) -> Result<usize> {
        let text = CString::try_from_fmt(fmt!(
            "{} {} {} {}\n",
            self.0.phase.load(Ordering::Acquire),
            self.0.released.load(Ordering::Acquire),
            self.0.requests.load(Ordering::Acquire),
            self.0.retries.load(Ordering::Acquire)
        ))?;
        output[..text.as_bytes().len()].copy_from_slice(text.as_bytes());
        Ok(text.as_bytes().len())
    }
}
struct Gate(Arc<Stats>);
impl AttributeOps for Gate {
    fn store(&self, input: &[u8]) -> Result<usize> {
        let value = match input {
            b"0\n" => false,
            b"1\n" => true,
            _ => return Err(EINVAL),
        };
        self.0.gate.store(value, Ordering::Release);
        Ok(input.len())
    }
}
struct Remove(Arc<Mutex<Tree>>);
impl AttributeOps for Remove {
    fn store(&self, input: &[u8]) -> Result<usize> {
        if input != b"1\n" {
            return Err(EINVAL);
        }
        self.0.lock().unlink(b"/sys/slow", 1)?;
        Ok(input.len())
    }
}

struct Peer {
    remote: Arc<Remote>,
    stats: Arc<Stats>,
    entered: Arc<AtomicBool>,
    address: usize,
    values: [[u8; 64]; 4],
    lengths: [usize; 4],
    retry: bool,
}
impl Peer {
    fn text(&self, value: &[u8]) -> i64 {
        for (i, b) in value.iter().copied().enumerate() {
            unsafe { ptr::write_volatile((self.address as *mut u8).add(i), b) };
        }
        value.len() as i64
    }
    fn handle(&mut self, packet: &[u8; 128]) {
        let msg = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        let bytes = i32::from_le_bytes(packet[12..16].try_into().unwrap());
        let token = u64::from_le_bytes(packet[24..32].try_into().unwrap());
        let ops = u64::from_le_bytes(packet[32..40].try_into().unwrap());
        let instance = u64::from_le_bytes(packet[40..48].try_into().unwrap());
        assert_eq!(ops, OPS);
        assert!((1..=9).contains(&instance));
        assert!(token > 0 && token <= i64::MAX as u64);
        self.stats.requests.fetch_add(1, Ordering::Relaxed);
        let result = if msg == 0x3e {
            assert_eq!(bytes, 0);
            unsafe { bindings::msleep(20) };
            let old = self
                .stats
                .released
                .fetch_or(1 << instance, Ordering::AcqRel);
            assert_eq!(old & (1 << instance), 0);
            0
        } else {
            assert!(msg == 0x3a || msg == 0x3c);
            if msg == 0x3a {
                assert_eq!(bytes, 0);
            } else {
                assert!((0..=4096).contains(&bytes));
            }
            match instance {
                1..=4 => {
                    let index = instance as usize - 1;
                    if msg == 0x3c {
                        assert!(bytes < 64);
                        for i in 0..bytes as usize {
                            self.values[index][i] =
                                unsafe { ptr::read_volatile((self.address as *const u8).add(i)) };
                        }
                        self.lengths[index] = bytes as usize;
                        bytes as i64
                    } else {
                        self.text(&self.values[index][..self.lengths[index]])
                    }
                }
                5 => {
                    if msg == 0x3a {
                        4096
                    } else {
                        bytes as i64 + 1
                    }
                }
                6 => -22,
                7 | 8 => {
                    assert_eq!(msg, 0x3a);
                    self.stats.phase.store(instance as usize, Ordering::Release);
                    while !self.stats.gate.load(Ordering::Acquire) {
                        unsafe { bindings::msleep(1) };
                    }
                    self.text(if instance == 7 { b"slow\n" } else { b"late\n" })
                }
                9 => {
                    if msg == 0x3c {
                        assert_eq!(bytes, 4096);
                        for i in 0..4096 {
                            assert_eq!(
                                unsafe { ptr::read_volatile((self.address as *const u8).add(i)) },
                                b'k'
                            );
                        }
                        4096
                    } else {
                        for i in 0..4095 {
                            unsafe { ptr::write_volatile((self.address as *mut u8).add(i), b'z') };
                        }
                        4095
                    }
                }
                _ => unreachable!(),
            }
        };
        let mut response = [0u8; 128];
        response[8..12].copy_from_slice(&(msg + 1).to_le_bytes());
        response[12..16]
            .copy_from_slice(&(if result < 0 { result as i32 } else { 0 }).to_le_bytes());
        response[24..32].copy_from_slice(&token.to_le_bytes());
        response[32..40].copy_from_slice(&result.to_le_bytes());
        self.remote.reply(&response).unwrap();
        self.stats.phase.store(0, Ordering::Release);
    }
}

// SAFETY: One owned Box is transferred to this callback. The task signals
// entry and remains alive until its unique owner stops and joins it.
unsafe extern "C" fn peer_thread(data: *mut core::ffi::c_void) -> i32 {
    let mut peer = unsafe { Box::from_raw(data.cast::<Peer>()) };
    peer.entered.store(true, Ordering::Release);
    while !unsafe { bindings::kthread_should_stop() } {
        let mut packet = [0u8; 128];
        let result = {
            let Peer {
                retry,
                remote,
                stats,
                ..
            } = &mut *peer;
            remote.publish(|source| {
                if !*retry {
                    *retry = true;
                    stats.retries.fetch_add(1, Ordering::Relaxed);
                    return Err(EBUSY);
                }
                *retry = false;
                packet.copy_from_slice(source);
                Ok(())
            })
        };
        match result {
            Ok(true) => peer.handle(&packet),
            Ok(false) => {}
            Err(error) => assert_eq!(error, EBUSY),
        }
        unsafe { bindings::msleep(1) };
    }
    0
}
struct PeerThread(*mut bindings::task_struct);
// SAFETY: The pointer is private; its only access is the unique stop/join in
// Drop. The entered worker remains live and owns synchronized shared state.
unsafe impl Send for PeerThread {}
unsafe impl Sync for PeerThread {}
impl Drop for PeerThread {
    fn drop(&mut self) {
        assert_eq!(unsafe { bindings::kthread_stop(self.0) }, 0);
    }
}
impl PeerThread {
    fn start(remote: Arc<Remote>, stats: Arc<Stats>, address: usize) -> Result<Self> {
        let entered = Arc::new(AtomicBool::new(false), GFP_KERNEL)?;
        let mut values = [[0; 64]; 4];
        for value in &mut values {
            value[..8].copy_from_slice(b"initial\n");
        }
        let peer = Box::new(
            Peer {
                remote,
                stats,
                entered: entered.clone(),
                address,
                values,
                lengths: [8; 4],
                retry: false,
            },
            GFP_KERNEL,
        )?;
        let data = Box::into_raw(peer);
        let task = unsafe {
            bindings::kthread_create_on_node(
                Some(peer_thread),
                data.cast(),
                -1,
                kernel::c_str!("mck-sysfs-peer").as_char_ptr(),
            )
        };
        if (-4095..0).contains(&(task as isize)) {
            unsafe { drop(Box::from_raw(data)) };
            return Err(kernel::error::to_result(task as isize as i32)
                .err()
                .unwrap_or(EIO));
        }
        assert!(!task.is_null());
        unsafe { bindings::wake_up_process(task) };
        while !entered.load(Ordering::Acquire) {
            unsafe { bindings::msleep(1) };
        }
        Ok(Self(task))
    }
}

struct RemoteVerify {
    tree: Arc<Mutex<Tree>>,
    remove: Option<File<Remove>>,
    status: Option<File<Status>>,
    gate: Option<File<Gate>>,
    peer: Option<PeerThread>,
    _remote: Arc<Remote>,
    stats: Arc<Stats>,
    _page: Page,
    _root: Directory,
}
impl kernel::Module for RemoteVerify {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        let root = Directory::new(None, kernel::c_str!("mckernel_sysfs_remote_verify"))?;
        let page = Page::new()?;
        let data = sysfs_setup::SharedData {
            owner: sysfs_setup::FixtureOwner,
            address: page.0 as u64,
            physical: (page.0 as u64)
                .checked_sub(unsafe { bindings::page_offset_base })
                .ok_or(EIO)?,
            bytes: 4096,
        };
        // SAFETY: This independent peer owns the original Linux page and its
        // module lifetime. Every callback/peer is drained before that page can
        // drop. FixtureOwner is only a diagnostic tag, not IHK authority.
        let remote = unsafe { Remote::new(data)? };
        let stats = Arc::new(
            Stats {
                gate: AtomicBool::new(true),
                phase: AtomicUsize::new(0),
                released: AtomicU64::new(0),
                requests: AtomicU64::new(0),
                retries: AtomicU64::new(0),
            },
            GFP_KERNEL,
        )?;
        let peer = PeerThread::start(remote.clone(), stats.clone(), page.0)?;
        let tree = Tree::new(Directory::new(Some(&root), kernel::c_str!("sys"))?)?;
        let tree = Arc::pin_init(new_mutex!(tree), GFP_KERNEL)?;
        for (index, path) in [
            b"/sys/value1".as_slice(),
            b"/sys/value2",
            b"/sys/value3",
            b"/sys/value4",
            b"/sys/overflow",
            b"/sys/error",
            b"/sys/slow",
            b"/sys/interrupt",
            b"/sys/boundary",
        ]
        .iter()
        .enumerate()
        {
            let attribute = Attribute::new(
                remote.clone(),
                Client {
                    operations: OPS,
                    instance: index as u64 + 1,
                },
            )?;
            tree.lock().create(path, 0o644, attribute.clone())?;
            attribute.arm();
        }
        let failed = Attribute::new(
            remote.clone(),
            Client {
                operations: OPS,
                instance: 10,
            },
        )?;
        assert_eq!(
            tree.lock().create(b"/sys/value1", 0o644, failed.clone()),
            Err(EEXIST)
        );
        drop(failed);
        assert_eq!(stats.released.load(Ordering::Acquire), 0);
        let status = File::new(
            &root,
            kernel::c_str!("status"),
            0o444,
            Status(stats.clone()),
        )?;
        let gate = File::new(&root, kernel::c_str!("gate"), 0o222, Gate(stats.clone()))?;
        let remove = File::new(
            &root,
            kernel::c_str!("remove_slow"),
            0o222,
            Remove(tree.clone()),
        )?;
        pr_info!("MCKERNEL_SYSFS_REMOTE_VERIFY READY files=9 duplicate_preserved=1\n");
        Ok(Self {
            tree,
            remove: Some(remove),
            status: Some(status),
            gate: Some(gate),
            peer: Some(peer),
            _remote: remote,
            stats,
            _page: page,
            _root: root,
        })
    }
}
impl Drop for RemoteVerify {
    fn drop(&mut self) {
        self.stats.gate.store(true, Ordering::Release);
        self.remove.take();
        self.gate.take();
        self.status.take();
        self.tree.lock().clear_contents();
        assert_eq!(self.stats.released.load(Ordering::Acquire), 1022);
        assert_eq!(
            self.stats.requests.load(Ordering::Acquire),
            self.stats.retries.load(Ordering::Acquire)
        );
        pr_info!(
            "MCKERNEL_SYSFS_REMOTE_VERIFY DRAINED releases=9 requests={} retries={}\n",
            self.stats.requests.load(Ordering::Acquire),
            self.stats.retries.load(Ordering::Acquire)
        );
        self.peer.take();
    }
}
