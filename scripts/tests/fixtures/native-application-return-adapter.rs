// SPDX-License-Identifier: GPL-2.0
//! Actual extracted Linux ioctl adapters with controlled user-copy/backend effects.
//! Real PID/MM identity, module dispatch and transport require the guest runs.

use std::{
    cell::{Cell, RefCell},
    sync::{
        atomic::{AtomicI32, AtomicU64, Ordering},
        Arc,
    },
};

type Result<T = ()> = std::result::Result<T, i32>;
const EINVAL: i32 = -22;
const EBUSY: i32 = -16;
const EIO: i32 = -5;
fn errno(value: i32) -> i32 {
    value
}
macro_rules! pr_info {
    ($($arg:tt)*) => { let _ = format_args!($($arg)*); };
}
mod application_abi {
    pub const WAIT_SYSCALL: u32 = 1;
    pub const COPIED_SYSCALL: u32 = 2;
    pub const RETURN_SYSCALL: u32 = 3;
}
mod image {
    pub fn word(bytes: &[u8], offset: usize) -> Result<u64, i32> {
        let value = bytes.get(offset..offset + 8).ok_or(-22)?;
        Ok(u64::from_le_bytes(value.try_into().unwrap()))
    }
}

thread_local! {
    static READ_FAULT: Cell<bool> = const { Cell::new(false) };
    static WRITE_FAULT: Cell<bool> = const { Cell::new(false) };
}
struct UserSlice {
    address: usize,
    bytes: usize,
}
impl UserSlice {
    fn new(address: usize, bytes: usize) -> Self {
        Self { address, bytes }
    }
    fn reader(self) -> Self {
        self
    }
    fn writer(self) -> Self {
        self
    }
    fn read_slice(self, output: &mut [u8]) -> Result {
        assert_eq!(self.bytes, output.len());
        if READ_FAULT.with(Cell::get) {
            return Err(-14);
        }
        // Tests supply a live, distinct buffer covering this complete range.
        unsafe {
            std::ptr::copy_nonoverlapping(
                self.address as *const u8,
                output.as_mut_ptr(),
                self.bytes,
            )
        };
        Ok(())
    }
    fn write_slice(self, input: &[u8]) -> Result {
        assert_eq!(self.bytes, input.len());
        let fault = WRITE_FAULT.with(Cell::get);
        let bytes = if fault { self.bytes / 2 } else { self.bytes };
        // Model partial copyout failure, not an all-or-nothing test shortcut.
        unsafe { std::ptr::copy_nonoverlapping(input.as_ptr(), self.address as *mut u8, bytes) };
        if fault {
            Err(-14)
        } else {
            Ok(())
        }
    }
}

struct HostWorker {
    handle: u64,
    delivery: AtomicU64,
    delivery_cpu: AtomicI32,
}
struct Backend {
    serial: u64,
    guest_cpu: i64,
    copied: Vec<bool>,
    returns: Vec<[u8; 72]>,
    accepted: bool,
    error: Option<i32>,
}
struct Registration {
    worker: Arc<HostWorker>,
    backend: RefCell<Backend>,
    slot: u32,
    generation: u64,
    pid: i32,
}
impl Registration {
    fn new(cpu: i64) -> Self {
        Self {
            worker: Arc::new(HostWorker {
                handle: 42,
                delivery: AtomicU64::new(0),
                delivery_cpu: AtomicI32::new(-1),
            }),
            backend: RefCell::new(Backend {
                serial: 73,
                guest_cpu: cpu,
                copied: Vec::new(),
                returns: Vec::new(),
                accepted: true,
                error: None,
            }),
            slot: 0,
            generation: 1,
            pid: 123,
        }
    }
    fn trace(&self) -> bool {
        true
    }
    fn worker(&self, _create: bool) -> Result<Arc<HostWorker>> {
        Ok(self.worker.clone())
    }
    fn invoke(&self, command: u32, bytes: &mut [u8]) -> Result {
        let mut backend = self.backend.borrow_mut();
        assert_eq!(image::word(bytes, 0)?, 42);
        match command {
            application_abi::WAIT_SYSCALL => {
                assert_eq!(bytes.len(), 96);
                bytes[8..16].copy_from_slice(&backend.serial.to_le_bytes());
                bytes[16..24].copy_from_slice(&backend.guest_cpu.to_le_bytes());
                bytes[40..48].copy_from_slice(&1u64.to_le_bytes());
            }
            application_abi::COPIED_SYSCALL => {
                assert_eq!(image::word(bytes, 8)?, backend.serial);
                backend.copied.push(image::word(bytes, 16)? != 0);
            }
            application_abi::RETURN_SYSCALL => {
                assert_eq!(image::word(bytes, 8)?, backend.serial);
                // The real backend retains this strict trusted-CPU assertion.
                assert_eq!(image::word(bytes, 16)? as i64, backend.guest_cpu);
                backend.returns.push(bytes.try_into().unwrap());
                bytes[48..56].copy_from_slice(&(backend.accepted as u64).to_le_bytes());
                if let Some(error) = backend.error {
                    return Err(error);
                }
            }
            _ => panic!("unexpected command"),
        }
        Ok(())
    }
    fn deliver(&self) -> Result<isize> {
        let mut output = [0u8; 80];
        self.adapter_wait(output.as_mut_ptr() as usize)
    }
    fn complete(&self, slot: i64, value: i64, size: u64) -> Result<isize> {
        let descriptor = [slot as u64, value as u64, 0, 0, size];
        self.adapter_return(descriptor.as_ptr() as usize)
    }
}

// The helper extracts these two complete production methods without edits.
mod actual {
    use super::*;
    include!("native-application-return-adapter-methods.rs");
    impl Registration {
        pub(super) fn adapter_wait(&self, argument: usize) -> Result<isize> {
            self.wait_syscall(argument, false)
        }
        pub(super) fn adapter_return(&self, argument: usize) -> Result<isize> {
            self.return_syscall(argument, false)
        }
    }
}

#[test]
fn launcher_slot_does_not_select_the_guest_cpu() {
    for cpu in [0, 3] {
        for slot in [0, 1, 7, -1, i64::MAX] {
            let registration = Registration::new(cpu);
            assert_eq!(registration.deliver(), Ok(0));
            assert_eq!(registration.complete(slot, 25, 0), Ok(0));
            let backend = registration.backend.borrow();
            assert_eq!(backend.copied, [true]);
            assert_eq!(backend.returns.len(), 1);
            assert_eq!(image::word(&backend.returns[0], 24), Ok(25));
            assert_eq!(registration.worker.delivery.load(Ordering::Acquire), 0);
        }
    }
}

#[test]
fn failed_wait_copy_does_not_publish_a_delivery() {
    let registration = Registration::new(3);
    WRITE_FAULT.with(|fault| fault.set(true));
    assert_eq!(registration.deliver(), Err(-14));
    WRITE_FAULT.with(|fault| fault.set(false));
    assert_eq!(registration.backend.borrow().copied, [false]);
    assert_eq!(registration.worker.delivery.load(Ordering::Acquire), 0);
    assert_eq!(registration.worker.delivery_cpu.load(Ordering::Relaxed), -1);
    assert_eq!(registration.complete(1, 25, 0), Err(EINVAL));
    assert!(registration.backend.borrow().returns.is_empty());
}

#[test]
fn invalid_return_copy_preserves_the_delivered_request() {
    let registration = Registration::new(0);
    assert_eq!(registration.deliver(), Ok(0));
    READ_FAULT.with(|fault| fault.set(true));
    assert_eq!(registration.complete(1, 25, 0), Err(-14));
    READ_FAULT.with(|fault| fault.set(false));
    assert_eq!(registration.complete(1, 25, 17), Err(EINVAL));
    assert!(registration.backend.borrow().returns.is_empty());
    assert_eq!(registration.worker.delivery.load(Ordering::Acquire), 73);
    assert_eq!(registration.complete(1, 25, 0), Ok(0));
}

#[test]
fn only_backend_acceptance_consumes_the_host_delivery() {
    for accepted in [false, true] {
        let registration = Registration::new(0);
        assert_eq!(registration.deliver(), Ok(0));
        {
            let mut backend = registration.backend.borrow_mut();
            backend.accepted = accepted;
            backend.error = Some(-4);
        }
        assert_eq!(registration.complete(1, 25, 0), Err(-4));
        assert_eq!(
            registration.worker.delivery.load(Ordering::Acquire),
            if accepted { 0 } else { 73 }
        );
    }
}

#[test]
fn successive_deliveries_replace_cpu_and_serial_together() {
    let registration = Registration::new(0);
    assert_eq!(registration.complete(1, 25, 0), Err(EINVAL));
    assert_eq!(registration.deliver(), Ok(0));
    assert_eq!(registration.deliver(), Err(EBUSY));
    assert_eq!(registration.complete(1, 25, 0), Ok(0));
    assert_eq!(registration.complete(1, 25, 0), Err(EINVAL));
    {
        let mut backend = registration.backend.borrow_mut();
        backend.guest_cpu = 3;
        backend.serial = 74;
    }
    assert_eq!(registration.deliver(), Ok(0));
    assert_eq!(registration.complete(1, -9, 0), Ok(0));
    let backend = registration.backend.borrow();
    assert_eq!(backend.returns.len(), 2);
    assert_eq!(image::word(&backend.returns[1], 8), Ok(74));
    assert_eq!(image::word(&backend.returns[1], 24), Ok((-9i64) as u64));
}
