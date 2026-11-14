// SPDX-License-Identifier: GPL-2.0
//! Exact native transfer method with controlled current identity/MM/user-copy.
use std::{
    cell::{Cell, RefCell},
    collections::BTreeMap,
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
};
type Result<T = ()> = std::result::Result<T, i32>;
const EINVAL: i32 = -22;
fn errno(value: i32) -> i32 {
    value
}
#[allow(dead_code)]
#[path = "application-image.rs"]
mod image;
#[allow(dead_code)]
#[path = "application-abi.rs"]
mod application_abi;
thread_local! {
    static MEMORY: RefCell<BTreeMap<usize, Vec<u8>>> = const { RefCell::new(BTreeMap::new()) };
    static READS: Cell<usize> = const { Cell::new(0) };
    static READ_FAULT: Cell<usize> = const { Cell::new(usize::MAX) };
    static ALLOC_FAULT: Cell<bool> = const { Cell::new(false) };
}
struct Mutex<T>(RefCell<T>);
impl<T> Mutex<T> {
    fn lock(&self) -> std::cell::RefMut<'_, T> {
        self.0.borrow_mut()
    }
}
struct UserSlice {
    address: usize,
    length: usize,
}
impl UserSlice {
    fn new(address: usize, length: usize) -> Self {
        Self { address, length }
    }
    fn reader(self) -> Self {
        self
    }
    fn writer(self) -> Self {
        self
    }
    fn read_slice(self, output: &mut [u8]) -> Result {
        assert_eq!(self.length, output.len());
        let nth = READS.with(|n| {
            let v = n.get();
            n.set(v + 1);
            v
        });
        let fail = READ_FAULT.with(|n| n.get() == nth);
        MEMORY.with(|memory| {
            let memory = memory.borrow();
            let input = memory.get(&self.address).ok_or(-14)?;
            if input.len() < output.len() {
                return Err(-14);
            }
            let n = if fail { output.len() / 2 } else { output.len() };
            output[..n].copy_from_slice(&input[..n]);
            if fail {
                Err(-14)
            } else {
                Ok(())
            }
        })
    }
    fn write_slice(self, input: &[u8]) -> Result {
        assert_eq!(self.length, input.len());
        MEMORY.with(|memory| {
            let mut memory = memory.borrow_mut();
            let output = memory.get_mut(&self.address).ok_or(-14)?;
            if output.len() < input.len() {
                return Err(-14);
            }
            output[..input.len()].copy_from_slice(input);
            Ok(())
        })
    }
}
#[derive(Clone, Copy)]
struct ProcessId(u64);
impl ProcessId {
    fn thread() -> Result<Self> {
        Ok(Self(300))
    }
    fn same(&self, other: &Self) -> bool {
        self.0 == other.0
    }
}
struct Mirror(Cell<Option<i32>>);
impl Mirror {
    fn current(&self) -> Result {
        self.0.get().map_or(Ok(()), Err)
    }
}
struct HostWorker {
    identity: ProcessId,
    mirror: Arc<Mirror>,
    handle: u64,
    delivery: AtomicU64,
}
struct Registration {
    mapping: Mutex<Option<Arc<Mirror>>>,
    workers: Mutex<Vec<Arc<HostWorker>>>,
    calls: RefCell<Vec<(u32, Vec<u8>)>>,
    backend_error: Cell<Option<i32>>,
}
impl Registration {
    fn new(running: bool) -> Self {
        let mirror = Arc::new(Mirror(Cell::new(None)));
        Self {
            mapping: Mutex(RefCell::new(Some(mirror.clone()))),
            workers: Mutex(RefCell::new(vec![
                Arc::new(HostWorker {
                    identity: ProcessId(301),
                    mirror: mirror.clone(),
                    handle: 999,
                    delivery: AtomicU64::new(888),
                }),
                Arc::new(HostWorker {
                    identity: ProcessId(300),
                    mirror,
                    handle: 42,
                    delivery: AtomicU64::new(if running { 77 } else { 0 }),
                }),
            ])),
            calls: RefCell::new(Vec::new()),
            backend_error: Cell::new(None),
        }
    }
    fn invoke(&self, command: u32, bytes: &mut [u8]) -> Result {
        self.calls.borrow_mut().push((command, bytes.to_vec()));
        if let Some(error) = self.backend_error.get() {
            return Err(error);
        }
        if command == application_abi::TRANSFER && image::word(bytes, 8)? == 1 {
            bytes[16..].fill(0x37);
        }
        Ok(())
    }
}
fn zero_bytes(length: usize) -> Result<Vec<u8>> {
    if ALLOC_FAULT.with(Cell::get) {
        Err(-12)
    } else {
        Ok(vec![0; length])
    }
}
mod actual {
    use super::*;
    include!("transfer-method.rs");
    impl Registration {
        pub(super) fn test_transfer(&self, address: usize, compat: bool) -> Result<isize> {
            self.transfer_image(address, compat)
        }
    }
}
fn setup(compat: bool, physical: u64, size: u64, direction: u8) -> Vec<u8> {
    READS.with(|n| n.set(0));
    READ_FAULT.with(|n| n.set(usize::MAX));
    ALLOC_FAULT.with(|n| n.set(false));
    let mut descriptor = vec![0xa5; if compat { 16 } else { 32 }];
    if compat {
        descriptor[..4].copy_from_slice(&(physical as u32).to_le_bytes());
        descriptor[4..8].copy_from_slice(&0x2000u32.to_le_bytes());
        descriptor[8..12].copy_from_slice(&(size as u32).to_le_bytes());
        descriptor[12] = direction;
    } else {
        image::put_word(&mut descriptor, 0, physical).unwrap();
        image::put_word(&mut descriptor, 8, 0x2000).unwrap();
        image::put_word(&mut descriptor, 16, size).unwrap();
        descriptor[24] = direction;
    }
    MEMORY.with(|m| {
        *m.borrow_mut() = BTreeMap::from([
            (0x1000, descriptor.clone()),
            (0x2000, (0..528).map(|i| (i * 17) as u8).collect()),
        ])
    });
    descriptor
}
#[test]
fn transfer_selects_exact_current_worker_and_preserves_original_descriptor() {
    for compat in [false, true] {
        for running in [false, true] {
            let original = setup(compat, 0x1234000, 512, 0);
            let registration = Registration::new(running);
            registration.test_transfer(0x1000, compat).unwrap();
            let calls = registration.calls.borrow();
            assert_eq!(calls.len(), 1);
            let (command, bytes) = &calls[0];
            let prefix = if running { 32 } else { 16 };
            assert_eq!(
                *command,
                if running {
                    application_abi::TID_TRANSFER
                } else {
                    application_abi::TRANSFER
                }
            );
            assert_eq!(bytes.len(), prefix + 512);
            if running {
                assert_eq!(image::word(bytes, 0), Ok(42));
                assert_eq!(image::word(bytes, 8), Ok(77));
            }
            assert_eq!(image::word(bytes, prefix - 16), Ok(0x1234000));
            assert_eq!(image::word(bytes, prefix - 8), Ok(0));
            MEMORY.with(|m| {
                assert_eq!(&bytes[prefix..], &m.borrow()[&0x2000][..512]);
                assert_eq!(m.borrow()[&0x1000], original);
            });
            assert_eq!(
                registration.workers.lock()[1]
                    .delivery
                    .load(Ordering::Acquire),
                if running { 77 } else { 0 }
            );
        }
    }
}
#[test]
fn transfer_copy_and_mm_failures_never_reach_backend_or_fall_back() {
    for compat in [false, true] {
        for failure in 0..5 {
            setup(compat, 0x1234000, 512, 0);
            let registration = Registration::new(true);
            match failure {
                0 | 1 => READ_FAULT.with(|n| n.set(failure)),
                2 => ALLOC_FAULT.with(|n| n.set(true)),
                3 => registration
                    .mapping
                    .lock()
                    .as_ref()
                    .unwrap()
                    .0
                    .set(Some(-18)),
                4 => *registration.mapping.lock() = None,
                _ => unreachable!(),
            }
            assert!(registration.test_transfer(0x1000, compat).is_err());
            assert!(registration.calls.borrow().is_empty());
        }
        for error in [-2, -14, -16, -22, -32] {
            let original = setup(compat, 0x1234000, 512, 0);
            let registration = Registration::new(true);
            registration.backend_error.set(Some(error));
            assert_eq!(registration.test_transfer(0x1000, compat), Err(error));
            assert_eq!(registration.calls.borrow().len(), 1);
            assert_eq!(
                registration.calls.borrow()[0].0,
                application_abi::TID_TRANSFER
            );
            MEMORY.with(|m| assert_eq!(m.borrow()[&0x1000], original));
        }
    }
}
#[test]
fn transfer_preserves_prepared_copyout_and_rejects_invalid_geometry() {
    for compat in [false, true] {
        setup(compat, 0x1234000, 512, 1);
        Registration::new(false)
            .test_transfer(0x1000, compat)
            .unwrap();
        MEMORY.with(|m| {
            assert_eq!(&m.borrow()[&0x2000][..512], &[0x37; 512]);
            assert_eq!(
                &m.borrow()[&0x2000][512..],
                &(512..528).map(|i| (i * 17) as u8).collect::<Vec<_>>()
            );
        });
        for (size, direction) in [(0, 0), (image::MAX_FLAT_BYTES as u64 + 1, 0), (512, 2)] {
            setup(compat, 0x1234000, size, direction);
            let registration = Registration::new(true);
            assert_eq!(registration.test_transfer(0x1000, compat), Err(-22));
            assert!(registration.calls.borrow().is_empty());
        }
    }
    setup(false, u64::MAX - 3, 512, 0);
    let registration = Registration::new(true);
    assert_eq!(registration.test_transfer(0x1000, false), Err(-75));
    assert!(registration.calls.borrow().is_empty());
}
