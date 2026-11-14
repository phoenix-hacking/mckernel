// SPDX-License-Identifier: GPL-2.0-only
//! Exact Remote::return_syscall with the complete production mailbox.
use super::{admit, mailbox, queued_request, Request, TestMemory, TestRam};
use core::cell::{Cell, RefCell, RefMut};
use std::sync::Arc;

#[derive(Debug, PartialEq, Eq, Copy, Clone)]
struct Error(i32);
impl Error {
    fn to_errno(self) -> i32 {
        self.0
    }
}
type Result = std::result::Result<(), Error>;
type Token = u64;
const EINVAL: Error = Error(-22);
const ENOENT: Error = Error(-2);
fn errno(value: i32) -> Error {
    Error(value)
}
struct Entry {
    syscalls: mailbox::Mailbox<TestMemory>,
    quarantined: bool,
}
impl Entry {
    fn key(&self) -> Token {
        91
    }
}
struct Slots(RefCell<Vec<Option<Entry>>>);
impl Slots {
    fn lock(&self) -> RefMut<'_, Vec<Option<Entry>>> {
        self.0.borrow_mut()
    }
}
struct Changed {
    waits: Cell<usize>,
    delay: usize,
    error: bool,
    worker: u64,
    serial: u64,
}
impl Changed {
    fn wait(&self, slots: &mut RefMut<'_, Vec<Option<Entry>>>) {
        let n = self.waits.get();
        self.waits.set(n + 1);
        let queue = &mut slots[0].as_mut().unwrap().syscalls;
        assert_eq!(queue.returned(self.worker, self.serial), Ok(false));
        assert_eq!(queue.reserve(self.worker), Ok(None));
        assert!(queue.open_worker(900).is_err());
        if n < self.delay {
            assert_eq!(queue.publish(0, |_| Err(-11)), Err(-11));
        } else if self.error {
            slots[0].as_mut().unwrap().quarantined = true;
        } else {
            assert_eq!(queue.publish(0, |_| Ok(())), Ok(true));
        }
    }
}
struct Remote {
    slots: Slots,
    changed: Changed,
}
include!("native-application-committed-return-method.rs");

fn setup(delay: usize, error: bool) -> (Remote, Arc<TestRam>, [u8; 72]) {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let worker = queue.open_worker(900).unwrap();
    let ram = admit(&mut queue, queued_request(0, 0), 2);
    let (serial, _) = queue.reserve(worker).unwrap().unwrap();
    queue.copied(worker, serial, true).unwrap();
    let mut bytes = [0; 72];
    bytes[..8].copy_from_slice(&worker.to_le_bytes());
    bytes[8..16].copy_from_slice(&serial.to_le_bytes());
    bytes[24..32].copy_from_slice(&37i64.to_le_bytes());
    (
        Remote {
            slots: Slots(RefCell::new(vec![Some(Entry {
                syscalls: queue,
                quarantined: false,
            })])),
            changed: Changed {
                waits: Cell::new(0),
                delay,
                error,
                worker,
                serial,
            },
        },
        ram,
        bytes,
    )
}

#[test]
fn accepted_result_waits_for_real_publication_and_preserves_owner_across_retries() {
    for delay in [0, 1, 1024] {
        let (remote, ram, mut bytes) = setup(delay, false);
        assert_eq!(
            remote.return_syscall(91, &mut bytes, |_, _, _| panic!("unexpected copy")),
            Ok(())
        );
        assert_eq!(remote.changed.waits.get(), delay + 1);
        assert_eq!(u64::from_le_bytes(bytes[48..56].try_into().unwrap()), 1);
        let actual = ram.snapshot();
        assert_eq!(i64::from_le_bytes(actual[24..32].try_into().unwrap()), 37);
        assert_eq!(ram.releases.load(super::Ordering::Acquire), 1);
        assert!(!ram.claimed.load(super::Ordering::Acquire));
        assert_eq!(
            remote.return_syscall(91, &mut bytes, |_, _, _| panic!("duplicate copy")),
            Err(Error(-16))
        );
    }
}
#[test]
fn rejected_returns_keep_the_delivery_available_without_waiting() {
    let (remote, ram, mut bytes) = setup(0, false);
    assert_eq!(
        remote.return_syscall(90, &mut bytes, |_, _, _| Ok(())),
        Err(ENOENT)
    );
    bytes[40..48].copy_from_slice(&17u64.to_le_bytes());
    assert_eq!(
        remote.return_syscall(91, &mut bytes, |_, _, _| Ok(())),
        Err(EINVAL)
    );
    bytes[40..48].copy_from_slice(&1u64.to_le_bytes());
    assert_eq!(
        remote.return_syscall(91, &mut bytes, |_, _, _| Err(Error(-14))),
        Err(Error(-14))
    );
    assert_eq!(remote.changed.waits.get(), 0);
    assert_eq!(bytes[48..56], [0; 8]);
    assert_eq!(ram.releases.load(super::Ordering::Acquire), 0);
    bytes[40..48].fill(0);
    assert_eq!(
        remote.return_syscall(91, &mut bytes, |_, _, _| Ok(())),
        Ok(())
    );
}
#[test]
fn external_quarantine_wakes_committed_return_and_retains_response() {
    let (remote, ram, mut bytes) = setup(1, true);
    assert_eq!(
        remote.return_syscall(91, &mut bytes, |_, _, _| Ok(())),
        Err(Error(-71))
    );
    assert_eq!(remote.changed.waits.get(), 2);
    assert_eq!(bytes[48..56], 1u64.to_le_bytes());
    assert_eq!(ram.releases.load(super::Ordering::Acquire), 0);
    assert!(ram.claimed.load(super::Ordering::Acquire));
}
