// Executable sequential MODEL, not execution of the production kernel paths.
// Exact production bodies are bound by the Python driver. Identity, locks,
// mapping transactions and IRQ draining are abstracted as successful here;
// this checks shutdown ordering and selected failure boundaries only.
const EBUSY: i32 = -16;
const EIO: i32 = -5;
const POST: i64 = 1_i64 << 62;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Outcome { Complete, PreEffect(i32), PostEffect(i32) }

impl Outcome {
    fn wire(self) -> i64 {
        match self {
            Self::Complete => 0,
            Self::PreEffect(e) => i64::from(e),
            Self::PostEffect(e) => POST | i64::from(e as u32),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Event {
    AdmissionClose, AdmissionBusy, AdmissionReopen, IrqCheck, IrqClose,
    TerminalStop, CpuJournal, Reset(usize), Online(usize), ObserveOnline(usize),
    Reconcile, BootOwnersBusy, CpuCommit, MemoryCommit, Quarantine,
}

#[derive(Clone, Copy, Default)]
struct Cpu {
    reset_attempted: bool,
    online_attempted: bool,
    online_status: i32,
    online: bool,
    observed_online: bool,
}

#[derive(Clone, Copy)]
enum OnlineFailure { Offline, Applied, Observation }

#[derive(Default)]
struct Shutdown {
    admission_closed: bool,
    admission_owners: [bool; 5], // service, application, file, procfs, sysfs callback owners
    continuing_boot_owner: bool,
    sysfs_boot_owner: bool,
    shutdown_terminal: bool,
    irq_drained: bool,
    journal_recorded: bool,
    cpus: [Cpu; 2],
    fail_online: Option<(usize, OnlineFailure)>,
    quarantined: bool,
    resources_released: bool,
    trace: Vec<Event>,
}

impl Shutdown {
    // The claim reports whether Drop may undo this attempt's own close.
    fn close_admission(&mut self) -> Result<bool, i32> {
        let newly_closed = !self.admission_closed;
        if newly_closed {
            self.admission_closed = true;
            self.trace.push(Event::AdmissionClose);
        }
        if self.admission_owners.iter().any(|owner| *owner) {
            self.trace.push(Event::AdmissionBusy);
            if newly_closed {
                self.admission_closed = false;
                self.trace.push(Event::AdmissionReopen);
            }
            return Err(EBUSY);
        }
        Ok(newly_closed)
    }

    fn close_irq_senders(&mut self) -> Result<(), Outcome> {
        assert!(self.admission_closed);
        self.trace.push(Event::IrqCheck);
        // Production checks terminal BEFORE accepting an already-drained IRQ.
        if self.shutdown_terminal {
            self.trace.push(Event::TerminalStop);
            return Err(Outcome::PostEffect(EBUSY));
        }
        if !self.irq_drained {
            self.trace.push(Event::IrqClose);
            self.irq_drained = true;
        }
        Ok(())
    }

    fn physical_stop(&mut self) -> Result<(), i32> {
        assert!(self.irq_drained && !self.shutdown_terminal);
        if !self.journal_recorded {
            self.trace.push(Event::CpuJournal);
            self.journal_recorded = true;
        }
        // Re-observe exact identities, including online effects despite error.
        for (index, cpu) in self.cpus.iter_mut().enumerate() {
            if cpu.online_attempted && cpu.observed_online {
                cpu.online = true;
                self.trace.push(Event::ObserveOnline(index));
            } else if cpu.online || (cpu.online_attempted && cpu.online_status == 0) {
                return Err(EIO); // Never blindly repeat successful device_online.
            }
        }
        // All INITs precede the first online operation, as in production.
        for (index, cpu) in self.cpus.iter_mut().enumerate() {
            if !cpu.reset_attempted {
                self.trace.push(Event::Reset(index));
                cpu.reset_attempted = true;
            }
        }
        for (index, cpu) in self.cpus.iter_mut().enumerate() {
            if cpu.online { continue; }
            assert!(cpu.reset_attempted);
            self.trace.push(Event::Online(index));
            cpu.online_attempted = true;
            if let Some((target, failure)) = self.fail_online {
                if target == index {
                    self.fail_online = None;
                    cpu.online_status = match failure { OnlineFailure::Observation => 0, _ => EIO };
                    cpu.observed_online = !matches!(failure, OnlineFailure::Offline);
                    return Err(EIO);
                }
            }
            cpu.online_status = 0;
            cpu.observed_online = true;
            cpu.online = true;
        }
        Ok(())
    }

    fn reconcile(&mut self) -> Result<(), i32> {
        self.trace.push(Event::Reconcile);
        // Semantic prerequisite, independently checked by the mutation oracle.
        assert!(self.journal_recorded && self.irq_drained);
        assert!(self.cpus.iter().all(|cpu| cpu.reset_attempted && cpu.online));
        if self.continuing_boot_owner || self.sysfs_boot_owner {
            self.shutdown_terminal = true;
            self.trace.push(Event::BootOwnersBusy);
            return Err(EBUSY);
        }
        self.trace.push(Event::CpuCommit);
        self.trace.push(Event::MemoryCommit);
        self.resources_released = true;
        self.journal_recorded = false;
        Ok(())
    }

    fn provider_v6(&mut self) -> Outcome {
        if let Err(outcome) = self.close_irq_senders() { return outcome; }
        if let Err(error) = self.physical_stop() { return Outcome::PostEffect(error); }
        match self.reconcile() {
            Ok(()) => Outcome::Complete,
            Err(error) => Outcome::PostEffect(error),
        }
    }

    fn shutdown_v6(&mut self) -> Outcome {
        let newly_closed = match self.close_admission() {
            Ok(claim) => claim,
            Err(error) => return Outcome::PreEffect(error),
        };
        let outcome = self.provider_v6();
        match outcome {
            Outcome::Complete => { self.quarantined = false; },
            Outcome::PreEffect(_) if newly_closed => {
                self.admission_closed = false;
                self.trace.push(Event::AdmissionReopen);
            }
            Outcome::PreEffect(_) => {},
            Outcome::PostEffect(_) => {
                self.quarantined = true;
                self.trace.push(Event::Quarantine);
            }
        }
        outcome
    }

    fn count(&self, event: Event) -> usize {
        self.trace.iter().filter(|actual| **actual == event).count()
    }
}

#[test]
fn owner_free_boot_reconciles_only_after_all_physical_effects() {
    let mut s = Shutdown::default();
    assert_eq!(s.shutdown_v6(), Outcome::Complete);
    assert_eq!(s.trace, vec![Event::AdmissionClose, Event::IrqCheck, Event::IrqClose,
        Event::CpuJournal, Event::Reset(0), Event::Reset(1), Event::Online(0),
        Event::Online(1), Event::Reconcile, Event::CpuCommit, Event::MemoryCommit]);
    assert!(s.admission_closed && s.resources_released);
    assert!(!s.quarantined);
}

#[test]
fn every_admission_owner_refuses_pre_effect_then_allows_retry_after_release() {
    for slot in 0..5 {
        for initially_closed in [false, true] {
            let mut s = Shutdown { admission_closed: initially_closed, ..Shutdown::default() };
            s.admission_owners[slot] = true;
            let result = s.shutdown_v6();
            assert_eq!(result, Outcome::PreEffect(EBUSY));
            assert_eq!(result.wire(), -16);
            assert_eq!(s.admission_closed, initially_closed);
            assert_eq!(s.trace, if initially_closed { vec![Event::AdmissionBusy] }
                else { vec![Event::AdmissionClose, Event::AdmissionBusy, Event::AdmissionReopen] });
            assert!(!s.irq_drained && !s.journal_recorded && !s.quarantined);
            s.admission_owners[slot] = false;
            assert_eq!(s.shutdown_v6(), Outcome::Complete);
            assert_eq!(s.count(Event::Reset(0)), 1);
            assert_eq!(s.count(Event::Reset(1)), 1);
            assert_eq!(s.count(Event::Reconcile), 1);
        }
    }
}

#[test]
fn boot_owners_are_terminal_after_reset_and_retry_stops_before_cpu_or_reconcile() {
    for (continuing, sysfs) in [(true, false), (false, true), (true, true)] {
        let mut s = Shutdown { continuing_boot_owner: continuing, sysfs_boot_owner: sysfs,
            ..Shutdown::default() };
        let result = s.shutdown_v6();
        assert_eq!(result, Outcome::PostEffect(EBUSY));
        assert_eq!(result.wire(), POST | i64::from(EBUSY as u32));
        assert_eq!(s.trace, vec![Event::AdmissionClose, Event::IrqCheck, Event::IrqClose,
            Event::CpuJournal, Event::Reset(0), Event::Reset(1), Event::Online(0),
            Event::Online(1), Event::Reconcile, Event::BootOwnersBusy, Event::Quarantine]);
        assert!(s.admission_closed && s.shutdown_terminal && s.quarantined);
        assert!(!s.resources_released);
        // Even disappearance of owners cannot clear the terminal latch.
        s.continuing_boot_owner = false;
        s.sysfs_boot_owner = false;
        let start = s.trace.len();
        assert_eq!(s.shutdown_v6(), Outcome::PostEffect(EBUSY));
        assert_eq!(&s.trace[start..], &[Event::IrqCheck, Event::TerminalStop, Event::Quarantine]);
        assert_eq!(s.count(Event::Reconcile), 1);
        assert!(!s.resources_released);
    }
}

#[test]
fn partial_cpu_online_retry_uses_journal_and_never_repeats_init() {
    for failure in [OnlineFailure::Offline, OnlineFailure::Applied, OnlineFailure::Observation] {
        let mut s = Shutdown { fail_online: Some((1, failure)), ..Shutdown::default() };
        assert_eq!(s.shutdown_v6(), Outcome::PostEffect(EIO));
        assert!(s.admission_closed && s.quarantined && s.journal_recorded);
        assert!(!s.shutdown_terminal && !s.resources_released);
        assert_eq!(s.count(Event::Reconcile), 0);
        assert_eq!(s.shutdown_v6(), Outcome::Complete);
        assert_eq!(s.count(Event::IrqClose), 1);
        for cpu in 0..2 { assert_eq!(s.count(Event::Reset(cpu)), 1); }
        assert_eq!(s.count(Event::Online(0)), 1);
        assert_eq!(s.count(Event::Online(1)), if matches!(failure, OnlineFailure::Offline) { 2 } else { 1 });
        assert_eq!(s.count(Event::Reconcile), 1);
        assert!(s.resources_released);
        assert!(!s.quarantined);
    }
}

#[test]
fn successful_online_with_unproved_state_does_not_repeat_online_or_reconcile() {
    let mut s = Shutdown { fail_online: Some((1, OnlineFailure::Observation)), ..Shutdown::default() };
    assert_eq!(s.shutdown_v6(), Outcome::PostEffect(EIO));
    s.cpus[1].observed_online = false; // Subsequent target observation still fails.
    assert_eq!(s.shutdown_v6(), Outcome::PostEffect(EIO));
    assert_eq!(s.count(Event::Online(1)), 1);
    assert_eq!(s.count(Event::Reconcile), 0);
    assert!(!s.resources_released);
}
