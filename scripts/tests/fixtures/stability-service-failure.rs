// SPDX-License-Identifier: GPL-2.0-only
//! Exact candidate Runtime/Remote methods, real mailbox and RPC, Linux mocks.
//! Staged as a child of the retained complete syscall/C-peer fixture.
use super::{
    admit,
    application_rpc::{Exchange, Token},
    mailbox::Mailbox,
    queued_request, Request, TestMemory, TestRam,
};
use core::sync::atomic::{AtomicI32, AtomicUsize, Ordering};
use std::{
    ops::{Deref, DerefMut},
    sync::{Arc, Condvar, Mutex, MutexGuard},
    thread,
    time::{Duration, Instant},
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
const EINVAL: Error = Error(-22);
const ENOENT: Error = Error(-2);
const EAGAIN: Error = Error(-11);
const EBUSY: Error = Error(-16);
const CAPACITY: usize = 64;
fn errno(value: i32) -> Error {
    Error(value)
}

struct Lock<T> {
    inner: Mutex<T>,
    acquiring: AtomicUsize,
}
impl<T> Lock<T> {
    fn new(value: T) -> Self {
        Self {
            inner: Mutex::new(value),
            acquiring: AtomicUsize::new(0),
        }
    }
    fn lock(&self) -> Guard<'_, T> {
        self.acquiring.fetch_add(1, Ordering::AcqRel);
        let guard = self.inner.lock().unwrap();
        self.acquiring.fetch_sub(1, Ordering::AcqRel);
        Guard(Some(guard))
    }
}
struct Guard<'a, T>(Option<MutexGuard<'a, T>>);
impl<T> Deref for Guard<'_, T> {
    type Target = T;
    fn deref(&self) -> &T {
        self.0.as_ref().unwrap()
    }
}
impl<T> DerefMut for Guard<'_, T> {
    fn deref_mut(&mut self) -> &mut T {
        self.0.as_mut().unwrap()
    }
}
struct Changed {
    condition: Condvar,
    waits: AtomicUsize,
    wakes: AtomicUsize,
}
impl Changed {
    fn new() -> Self {
        Self {
            condition: Condvar::new(),
            waits: AtomicUsize::new(0),
            wakes: AtomicUsize::new(0),
        }
    }
    fn notify_all(&self) {
        self.wakes.fetch_add(1, Ordering::AcqRel);
        self.condition.notify_all();
    }
    fn wait<T>(&self, slots: &mut Guard<'_, T>) {
        self.waits.fetch_add(1, Ordering::AcqRel);
        let (guard, timeout) = self
            .condition
            .wait_timeout(slots.0.take().unwrap(), Duration::from_secs(5))
            .unwrap();
        slots.0 = Some(guard);
        assert!(!timeout.timed_out(), "fixture waiter exceeded its bound");
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
struct Procfs(AtomicUsize);
impl Procfs {
    fn close(&self) {
        self.0.fetch_add(1, Ordering::AcqRel);
    }
}
// The reservation's full field layout is represented; real preparation and
// procfs behavior are outside these tests. RPC and mailbox owners are real.
struct Entry {
    cleanup: Exchange,
    owner_slot: i32,
    prepare: Option<()>,
    schedule: Option<Exchange>,
    retirement: Option<Exchange>,
    retirement_after: u64,
    procfs: Option<Arc<Procfs>>,
    syscalls: Mailbox<TestMemory>,
    scheduled: bool,
    needs_cleanup: bool,
    closed: bool,
    quarantined: bool,
}
impl Entry {
    fn key(&self) -> Token {
        self.cleanup.token()
    }
    fn request_cleanup(&mut self) -> Result {
        panic!("unexpected fixture cleanup")
    }
}
const ORDER: [&str; 8] = [
    "procfs.advance",
    "master",
    "regular",
    "remote",
    "applications",
    "syscalls",
    "application.advance",
    "procfs",
];
struct Trace {
    records: Mutex<Vec<(&'static str, i32)>>,
    faults: Vec<(&'static str, i32)>,
}
impl Trace {
    fn step(&self, name: &'static str, health: i32) -> Result {
        self.records.lock().unwrap().push((name, health));
        match self.faults.iter().find(|(key, _)| *key == name) {
            Some((_, error)) => Err(errno(*error)),
            None => Ok(()),
        }
    }
}
struct Remote {
    owner: Owner,
    slots: Lock<Vec<Option<Entry>>>,
    releases: Lock<Mailbox<TestMemory>>,
    release_token: Token,
    transport_error: AtomicI32,
    changed: Changed,
    trace: Arc<Trace>,
}
include!("stability-service-failure-remote-methods.rs");
impl Remote {
    // Only this pump step is substituted; failure/admission/publication and
    // accepted-return methods above are extracted verbatim from the candidate.
    fn advance(&self) -> Result {
        self.trace.step(
            "application.advance",
            self.transport_error.load(Ordering::Acquire),
        )
    }
}
struct PumpProcfs(Arc<Trace>);
impl PumpProcfs {
    fn advance(&self) {
        self.0.step("procfs.advance", 0).unwrap();
    }
}
struct Runtime {
    owner: Owner,
    error: AtomicI32,
    application: Arc<Remote>,
    procfs: PumpProcfs,
    trace: Arc<Trace>,
}
include!("stability-service-failure-runtime-methods.rs");
impl Runtime {
    fn step(&self, name: &'static str) -> Result {
        self.trace.step(name, self.error.load(Ordering::Acquire))
    }
    fn pump_master(&self) -> Result {
        self.step("master")
    }
    fn pump_regular(&self) -> Result {
        self.step("regular")
    }
    fn publish_remote(&self) -> Result {
        self.step("remote")
    }
    fn publish_applications(&self) -> Result {
        self.step("applications")
    }
    fn publish_syscalls(&self) -> Result {
        self.step("syscalls")
    }
    fn publish_procfs(&self) -> Result {
        self.step("procfs")
    }
}
fn runtime(faults: Vec<(&'static str, i32)>) -> Arc<Runtime> {
    let trace = Arc::new(Trace {
        records: Mutex::new(Vec::new()),
        faults,
    });
    let application = Arc::new(Remote {
        owner: Owner,
        slots: Lock::new((0..CAPACITY).map(|_| None).collect()),
        releases: Lock::new(Mailbox::new().unwrap()),
        release_token: Token::allocate().unwrap(),
        transport_error: AtomicI32::new(0),
        changed: Changed::new(),
        trace: trace.clone(),
    });
    Arc::new(Runtime {
        owner: Owner,
        error: AtomicI32::new(0),
        application,
        procfs: PumpProcfs(trace.clone()),
        trace,
    })
}
fn until(mut predicate: impl FnMut() -> bool) {
    let deadline = Instant::now() + Duration::from_secs(3);
    while !predicate() {
        assert!(
            Instant::now() < deadline,
            "fixture synchronization exceeded its bound"
        );
        thread::yield_now();
    }
}
fn delivered(runtime: &Runtime) -> (Token, Arc<TestRam>, [u8; 72]) {
    let token = runtime.application.reserve(700).unwrap();
    let mut slots = runtime.application.slots.lock();
    let entry = slots
        .iter_mut()
        .flatten()
        .find(|entry| entry.key() == token)
        .unwrap();
    entry.procfs = Some(Arc::new(Procfs(AtomicUsize::new(0))));
    let worker = entry.syscalls.open_worker(900).unwrap();
    let ram = admit(&mut entry.syscalls, queued_request(0, 0), 2);
    let (serial, _) = entry.syscalls.reserve(worker).unwrap().unwrap();
    entry.syscalls.copied(worker, serial, true).unwrap();
    let mut bytes = [0; 72];
    bytes[..8].copy_from_slice(&worker.to_le_bytes());
    bytes[8..16].copy_from_slice(&serial.to_le_bytes());
    bytes[24..32].copy_from_slice(&37i64.to_le_bytes());
    (token, ram, bytes)
}

#[test]
fn service_error_is_not_visible_until_admission_mutex_is_owned() {
    let runtime = runtime(vec![]);
    let guard = runtime.application.slots.lock();
    let worker = {
        let runtime = runtime.clone();
        thread::spawn(move || runtime.fail(errno(-5)))
    };
    until(|| runtime.application.slots.acquiring.load(Ordering::Acquire) > 0);
    // A naive Runtime CAS followed by fail_transport fails this assertion.
    assert_eq!(runtime.error.load(Ordering::Acquire), 0);
    drop(guard);
    worker.join().unwrap();
    assert_eq!(runtime.error.load(Ordering::Acquire), -5);
    assert_eq!(runtime.application.reserve(701), Err(errno(-5)));
    assert!(runtime.application.slots.lock().iter().all(Option::is_none));
}

#[test]
fn stale_ready_observation_cannot_reserve_after_failure_and_old_owner_is_retained() {
    let runtime = runtime(vec![]);
    let (token, ram, _) = delivered(&runtime);
    let before = ram.snapshot();
    assert_eq!(runtime.error.load(Ordering::Acquire), 0); // pre-existing ready observation
    runtime.fail(errno(-12));
    assert_eq!(runtime.application.reserve(701), Err(errno(-12)));
    let mut slots = runtime.application.slots.lock();
    let entry = slots
        .iter_mut()
        .flatten()
        .find(|entry| entry.key() == token)
        .unwrap();
    assert!(entry.quarantined && entry.needs_cleanup && entry.syscalls.quarantined());
    assert!(entry.syscalls.open_worker(901).is_err());
    assert_eq!(entry.procfs.as_ref().unwrap().0.load(Ordering::Acquire), 1);
    assert_eq!(ram.snapshot(), before);
    assert!(ram.claimed.load(Ordering::Acquire));
    assert_eq!(ram.releases.load(Ordering::Acquire), 0);
    assert!(runtime.application.releases.lock().quarantined());
}

#[test]
fn independent_domains_keep_their_first_errors_and_repeat_failure_keeps_owners() {
    let runtime = runtime(vec![]);
    let (_, ram, _) = delivered(&runtime);
    let before = ram.snapshot();
    runtime.application.fail_transport(errno(-110));
    runtime.fail(errno(-5));
    runtime.fail(errno(-19));
    assert_eq!(runtime.error.load(Ordering::Acquire), -5);
    assert_eq!(runtime.application.transport_health(), Err(errno(-110)));
    assert_eq!(runtime.application.reserve(701), Err(errno(-110)));
    let slots = runtime.application.slots.lock();
    let entry = slots.iter().flatten().next().unwrap();
    assert_eq!(entry.procfs.as_ref().unwrap().0.load(Ordering::Acquire), 1);
    assert_eq!(ram.snapshot(), before);
    assert_eq!(ram.releases.load(Ordering::Acquire), 0);
    assert!(runtime.application.changed.wakes.load(Ordering::Acquire) >= 3);
}

#[test]
fn actual_committed_return_waiter_wakes_without_guest_publication_or_replay() {
    let runtime = runtime(vec![]);
    let (token, ram, mut bytes) = delivered(&runtime);
    let mut accepted = ram.snapshot();
    // Accepted RET prepares the result and claims the descheduled wake before
    // its queue publication. Only these original ABI fields may change.
    accepted[4..8].copy_from_slice(&900i32.to_le_bytes());
    accepted[16..24].copy_from_slice(&1u64.to_le_bytes());
    accepted[24..32].copy_from_slice(&37i64.to_le_bytes());
    let waiter = {
        let runtime = runtime.clone();
        thread::spawn(move || {
            let result = runtime
                .application
                .return_syscall(token, &mut bytes, |_, _, _| {
                    panic!("unexpected return copy")
                });
            (result, bytes)
        })
    };
    until(|| runtime.application.changed.waits.load(Ordering::Acquire) > 0);
    assert_eq!(ram.snapshot(), accepted);
    assert_eq!(ram.status(), 0);
    runtime.fail(errno(-5));
    let (result, returned) = waiter.join().unwrap();
    assert_eq!(result, Err(errno(-71)));
    assert_eq!(returned[48..56], 1u64.to_le_bytes());
    assert_eq!(
        runtime.application.publish_syscall(
            token,
            0,
            |_| panic!("publication after service failure"),
            || panic!("late notification")
        ),
        Err(errno(-5))
    );
    assert_eq!(ram.snapshot(), accepted);
    assert_eq!(ram.status(), 0);
    assert!(ram.claimed.load(Ordering::Acquire));
    assert_eq!(ram.releases.load(Ordering::Acquire), 0);
}

#[test]
fn both_admission_failure_interleavings_have_one_retained_or_rejected_owner() {
    for _ in 0..32 {
        let runtime = runtime(vec![]);
        let barrier = Arc::new(std::sync::Barrier::new(3));
        let admission = {
            let runtime = runtime.clone();
            let barrier = barrier.clone();
            thread::spawn(move || {
                barrier.wait();
                runtime.application.reserve(701)
            })
        };
        let failure = {
            let runtime = runtime.clone();
            let barrier = barrier.clone();
            thread::spawn(move || {
                barrier.wait();
                runtime.fail(errno(-5));
            })
        };
        barrier.wait();
        let reserved = admission.join().unwrap();
        failure.join().unwrap();
        let slots = runtime.application.slots.lock();
        match reserved {
            Ok(token) => {
                let entry = slots
                    .iter()
                    .flatten()
                    .find(|entry| entry.key() == token)
                    .unwrap();
                assert!(entry.quarantined && entry.needs_cleanup);
                assert_eq!(slots.iter().flatten().count(), 1);
            }
            Err(error) => {
                assert_eq!(error, errno(-5));
                assert!(slots.iter().all(Option::is_none));
            }
        }
    }
}

#[test]
fn each_pump_error_is_handled_before_later_steps_and_all_drain_steps_run() {
    for failed in 1..ORDER.len() {
        let mut faults = vec![(ORDER[failed], -5)];
        if failed + 1 < ORDER.len() {
            faults.push((ORDER[failed + 1], -19));
        }
        let runtime = runtime(faults);
        runtime.pump();
        let records = runtime.trace.records.lock().unwrap();
        assert_eq!(
            records.iter().map(|(name, _)| *name).collect::<Vec<_>>(),
            ORDER
        );
        for (index, (_, error)) in records.iter().enumerate() {
            assert_eq!(
                *error,
                if index > failed { -5 } else { 0 },
                "{failed}: {records:?}"
            );
        }
        assert_eq!(runtime.error.load(Ordering::Acquire), -5);
        assert_eq!(runtime.application.transport_health(), Err(errno(-5)));
    }
}
