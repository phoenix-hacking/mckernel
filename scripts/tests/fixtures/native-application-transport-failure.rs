// SPDX-License-Identifier: GPL-2.0-only
//! Extracted Remote publication/failure/wait methods with the complete mailbox.
use super::{admit, mailbox, queued_request, Request, TestMemory, TestRam};
use core::{
    cell::{Cell, RefCell, RefMut},
    sync::atomic::{AtomicI32, Ordering},
};
use std::{
    rc::{Rc, Weak},
    sync::Arc,
};

macro_rules! pr_err { ($($args:tt)*) => {{ let _ = format_args!($($args)*); }} }

#[derive(Debug, PartialEq, Eq, Copy, Clone)]
struct Error(i32);
impl Error {
    fn to_errno(self) -> i32 {
        self.0
    }
}
type Result<T = ()> = std::result::Result<T, Error>;
type Token = u64;
const EINVAL: Error = Error(-22);
const ENOENT: Error = Error(-2);
const EBUSY: Error = Error(-16);
const EAGAIN: Error = Error(-11);
const PUBLICATION_TIMEOUT_SECONDS: u64 = 5;
fn errno(value: i32) -> Error {
    Error(value)
}

struct Lock<T>(RefCell<T>);
impl<T> Lock<T> {
    fn lock(&self) -> RefMut<'_, T> {
        self.0.borrow_mut()
    }
}
struct Procfs(Cell<usize>);
impl Procfs {
    fn close(&self) {
        self.0.set(self.0.get() + 1);
    }
}
struct Owner;
impl Owner {
    fn slot(&self) -> u32 {
        0
    }
    fn generation(&self) -> u64 {
        1
    }
}
struct Cleanup;
impl Cleanup {
    fn pid(&self) -> i32 {
        700
    }
}
struct Entry {
    token: Token,
    cleanup: Cleanup,
    syscalls: mailbox::Mailbox<TestMemory>,
    quarantined: bool,
    needs_cleanup: bool,
    procfs: Option<Procfs>,
}
impl Entry {
    fn key(&self) -> Token {
        self.token
    }
    fn request_cleanup(&mut self) -> Result {
        panic!("unexpected cleanup after quarantine")
    }
}
#[derive(Clone, Copy)]
enum Action {
    Success,
    Hard(i32),
    Notify(i32),
    Timeout,
}
struct Changed {
    remote: Weak<Remote>,
    waits: Cell<usize>,
    wakes: Cell<usize>,
    delay: usize,
    action: Action,
}
impl Changed {
    fn notify_all(&self) {
        self.wakes.set(self.wakes.get() + 1);
    }
    fn wait(&self, slots: &mut RefMut<'_, Vec<Option<Entry>>>) {
        let step = self.waits.get();
        self.waits.set(step + 1);
        let remote = self.remote.upgrade().unwrap();
        if step < self.delay {
            let result = slots[0]
                .as_mut()
                .unwrap()
                .syscalls
                .publish(0, |_| Err(-11))
                .map_err(errno);
            assert_eq!(
                remote.finish_publication(slots, result, || panic!("notify before publication")),
                Ok(false)
            );
        } else {
            match self.action {
                Action::Timeout => {
                    assert_eq!(remote.expire_publications(slots, 100), Ok(()));
                    assert_eq!(remote.expire_publications(slots, 104), Ok(()));
                    assert_eq!(remote.expire_publications(slots, 105), Err(Error(-110)));
                }
                action => {
                    let result = slots[0]
                        .as_mut()
                        .unwrap()
                        .syscalls
                        .publish(0, |_| match action {
                            Action::Hard(value) => Err(value),
                            _ => Ok(()),
                        })
                        .map_err(errno);
                    let outcome = remote.finish_publication(slots, result, || match action {
                        Action::Notify(value) => Err(Error(value)),
                        _ => Ok(()),
                    });
                    match action {
                        Action::Success => assert_eq!(outcome, Ok(true)),
                        Action::Hard(value) | Action::Notify(value) => {
                            assert_eq!(outcome, Err(Error(value)))
                        }
                        _ => unreachable!(),
                    }
                }
            }
        }
    }
}
struct Remote {
    owner: Owner,
    slots: Lock<Vec<Option<Entry>>>,
    releases: Lock<mailbox::Mailbox<TestMemory>>,
    transport_error: AtomicI32,
    release_token: Token,
    changed: Changed,
}
include!("native-application-transport-failure-methods.rs");

fn setup(delay: usize, action: Action) -> (Rc<Remote>, Arc<TestRam>, [u8; 72]) {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let worker = queue.open_worker(900).unwrap();
    let ram = admit(&mut queue, queued_request(0, 0), 2);
    let (serial, _) = queue.reserve(worker).unwrap().unwrap();
    queue.copied(worker, serial, true).unwrap();
    let mut bytes = [0; 72];
    bytes[..8].copy_from_slice(&worker.to_le_bytes());
    bytes[8..16].copy_from_slice(&serial.to_le_bytes());
    bytes[24..32].copy_from_slice(&37i64.to_le_bytes());
    let remote = Rc::new_cyclic(|weak| Remote {
        owner: Owner,
        slots: Lock(RefCell::new(vec![Some(Entry {
            token: 91,
            cleanup: Cleanup,
            syscalls: queue,
            quarantined: false,
            needs_cleanup: false,
            procfs: Some(Procfs(Cell::new(0))),
        })])),
        releases: Lock(RefCell::new(mailbox::Mailbox::new().unwrap())),
        transport_error: AtomicI32::new(0),
        release_token: 92,
        changed: Changed {
            remote: weak.clone(),
            waits: Cell::new(0),
            wakes: Cell::new(0),
            delay,
            action,
        },
    });
    (remote, ram, bytes)
}

fn accepted(remote: &Remote, bytes: &[u8; 72]) {
    let worker = u64::from_le_bytes(bytes[..8].try_into().unwrap());
    let serial = u64::from_le_bytes(bytes[8..16].try_into().unwrap());
    remote.slots.lock()[0]
        .as_mut()
        .unwrap()
        .syscalls
        .return_value(worker, serial, 0, 37, |_| Ok(()))
        .unwrap();
}

#[test]
fn real_transition_releases_committed_waiter_and_preserves_unpublished_memory() {
    for delay in [0, 1, 1024] {
        for action in [Action::Hard(-5), Action::Timeout] {
            let (remote, ram, mut bytes) = setup(delay, action);
            assert_eq!(
                remote.return_syscall(91, &mut bytes, |_, _, _| panic!("unexpected copy")),
                Err(Error(-71))
            );
            assert_eq!(bytes[48..56], 1u64.to_le_bytes());
            assert_eq!(ram.status(), 0);
            assert_eq!(ram.releases.load(Ordering::Acquire), 0);
            assert!(ram.claimed.load(Ordering::Acquire));
            let before = ram.snapshot();
            assert!(remote
                .publish_syscall(
                    91,
                    0,
                    |_| panic!("republication"),
                    || panic!("notification")
                )
                .is_err());
            remote.fail_transport(Error(-19));
            let mut slots = remote.slots.lock();
            let entry = slots[0].as_mut().unwrap();
            assert!(entry.quarantined && entry.needs_cleanup);
            assert_eq!(entry.procfs.as_ref().unwrap().0.get(), 1);
            assert!(entry.syscalls.open_worker(900).is_err());
            assert_eq!(entry.syscalls.close(), Err(-71));
            assert_eq!(entry.syscalls.queued_cpu(), None);
            assert_eq!(ram.snapshot(), before);
            assert!(remote.changed.wakes.get() >= 1);
        }
    }
}

#[test]
fn notification_failure_is_terminal_even_after_mailbox_completed() {
    for value in [-5, -11, -16, -19] {
        let (remote, ram, mut bytes) = setup(1, Action::Notify(value));
        assert_eq!(
            remote.return_syscall(91, &mut bytes, |_, _, _| panic!("unexpected copy")),
            Err(Error(-71))
        );
        assert_eq!(bytes[48..56], 1u64.to_le_bytes());
        assert_eq!(remote.transport_health(), Err(Error(value)));
        assert_eq!(ram.status(), 1);
        assert_eq!(ram.releases.load(Ordering::Acquire), 1);
        assert!(!ram.claimed.load(Ordering::Acquire));
    }
}

#[test]
fn publication_and_notification_are_distinct_after_response_memory_reuse() {
    let (remote, ram, bytes) = setup(0, Action::Success);
    accepted(&remote, &bytes);
    let sends = Cell::new(0);
    let notifications = Cell::new(0);
    let marker = [0x6d; 64];
    assert_eq!(
        remote.publish_syscall(
            91,
            0,
            |_| {
                sends.set(sends.get() + 1);
                assert_eq!(ram.status(), 0);
                Ok(())
            },
            || {
                notifications.set(notifications.get() + 1);
                assert_eq!(ram.releases.load(Ordering::Acquire), 1);
                assert!(!ram.claimed.load(Ordering::Acquire));
                // The guest may recycle this backing span immediately after status=1.
                unsafe {
                    (*ram.bytes.get()).0 = marker;
                }
                Err(Error(-5))
            }
        ),
        Err(Error(-5))
    );
    assert!(remote
        .publish_syscall(91, 0, |_| panic!("second wake"), || panic!("second notify"))
        .is_err());
    assert_eq!(ram.snapshot(), marker);
    assert_eq!(sends.get(), 1);
    assert_eq!(notifications.get(), 1);
    assert_eq!(ram.releases.load(Ordering::Acquire), 1);
}

#[test]
fn queue_pressure_recovers_without_notification_or_ownership_loss() {
    let (remote, ram, bytes) = setup(0, Action::Success);
    accepted(&remote, &bytes);
    for _ in 0..1024 {
        assert_eq!(
            remote.publish_syscall(91, 0, |_| Err(EAGAIN), || panic!("premature notify")),
            Ok(false)
        );
        assert_eq!(remote.transport_health(), Ok(()));
        assert_eq!(ram.status(), 0);
        assert_eq!(ram.releases.load(Ordering::Acquire), 0);
    }
    assert_eq!(
        remote.publish_syscall(91, 0, |_| Ok(()), || Ok(())),
        Ok(true)
    );
    assert_eq!(ram.status(), 1);
    assert_eq!(ram.releases.load(Ordering::Acquire), 1);
    assert_eq!(
        remote.publish_syscall(
            91,
            0,
            |_| panic!("duplicate wake"),
            || panic!("duplicate notify")
        ),
        Ok(false)
    );
}

#[test]
fn prepublication_target_failure_closes_admission_and_retains_exact_scope() {
    let (remote, ram, bytes) = setup(0, Action::Success);
    let (other, _, _) = setup(0, Action::Success);
    accepted(&remote, &bytes);
    remote.fail_transport(Error(-19));
    assert_eq!(remote.transport_health(), Err(Error(-19)));
    assert_eq!(other.transport_health(), Ok(()));
    assert!(remote.releases.lock().open_worker(901).is_err());
    assert_eq!(ram.status(), 0);
    assert_eq!(ram.releases.load(Ordering::Acquire), 0);
    assert!(remote
        .publish_syscall(91, 0, |_| panic!("send after failed target"), || panic!())
        .is_err());
}

#[test]
fn delivered_and_running_kernel_work_are_not_timed_as_committed_results() {
    let (remote, ram, _) = setup(0, Action::Success);
    let mut slots = remote.slots.lock();
    assert_eq!(remote.expire_publications(&mut slots, 0), Ok(()));
    assert_eq!(remote.expire_publications(&mut slots, u64::MAX), Ok(()));
    assert_eq!(ram.status(), 0);
    drop(slots);
    let mut queue = mailbox::Mailbox::new().unwrap();
    let worker = queue.open_worker(902).unwrap();
    let ram = admit(&mut queue, queued_request(1, 0), 2);
    let (serial, _) = queue.reserve(worker).unwrap().unwrap();
    queue.begin_kernel(worker, serial).unwrap();
    assert!(!queue.publication_expired(0, 5));
    assert!(!queue.publication_expired(u64::MAX, 5));
    queue.quarantine();
    assert_eq!(
        queue.finish_kernel(worker, serial, |_, _| panic!("copy after quarantine")),
        Err(-71)
    );
    assert!(queue
        .with_kernel_memory(worker, serial, |_, _| -> core::result::Result<(), i32> {
            panic!("access after quarantine")
        })
        .is_err());
    assert_eq!(queue.close_worker(worker), Err(-71));
    assert_eq!(
        queue.publish(0, |_| panic!("publication after quarantine")),
        Err(-71)
    );
    assert_eq!(ram.status(), 0);
    assert_eq!(ram.releases.load(Ordering::Acquire), 0);
}

#[test]
fn each_completion_has_an_independent_monotonic_deadline() {
    let mut queue = mailbox::Mailbox::new().unwrap();
    let first = queue.open_worker(900).unwrap();
    let second = queue.open_worker(901).unwrap();
    admit(&mut queue, queued_request(0, 900), 2);
    admit(&mut queue, queued_request(1, 901), 2);
    let (a, _) = queue.reserve(first).unwrap().unwrap();
    let (b, _) = queue.reserve(second).unwrap().unwrap();
    queue.copied(first, a, true).unwrap();
    queue.copied(second, b, true).unwrap();
    queue.return_value(first, a, 0, 37, |_| Ok(())).unwrap();
    assert!(!queue.publication_expired(100, 5));
    queue.return_value(second, b, 0, 38, |_| Ok(())).unwrap();
    assert!(!queue.publication_expired(104, 5));
    assert!(!queue.publication_expired(99, 5));
    assert!(queue.publication_expired(105, 5));
    queue.publish(0, |_| Ok(())).unwrap();
    assert!(!queue.publication_expired(108, 5));
    assert!(queue.publication_expired(109, 5));
}
