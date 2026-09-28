//! Executable driver template for the native shutdown CPU journal.
//!
//! `test_shutdown_cpu_reclaim.py` injects the exact retained-device wrapper,
//! journal and ordinary-operation fence from `host-kernel/native-rust/smp_cpu.rs`.
//! This adapter compiles that production control core in a small context rather
//! than copying journal setters. Linux CPU hotplug itself remains out of scope.

use std::ptr;

mod bindings {
    #[allow(non_camel_case_types)]
    pub struct device;
}

#[derive(Clone, Copy)]
struct OsToken {
    slot: u32,
    generation: u64,
}

impl OsToken {
    const fn slot(self) -> u32 {
        self.slot
    }
    const fn generation(self) -> u64 {
        self.generation
    }
}

#[derive(Clone, Copy)]
struct HostCpuSnapshot {
    hardware_id: u32,
    numa_node: u32,
    online: bool,
}

// PRODUCTION_SHUTDOWN_CPU_CONTROL

struct ProductionCpuContextAdapter {
    shutdown_journal: [ShutdownCpuJournal; 4],
    poisoned: bool,
}

impl ProductionCpuContextAdapter {
    fn new() -> Self {
        Self {
            shutdown_journal: [ShutdownCpuJournal::empty(); 4],
            poisoned: false,
        }
    }

    /// Mirrors the production `verify_owned` fence. The production context
    /// additionally observes Linux identity after this exact early barrier.
    fn ordinary_verify_owned(&mut self) -> Result<(), i32> {
        if self.poisoned || shutdown_journal_blocks_ordinary_use(&self.shutdown_journal) {
            self.poisoned = true;
            return Err(-5);
        }
        Ok(())
    }

    /// Mirrors the distinct production reconciliation entry's repeat fence.
    /// It does not clear, release, or roll back a completed journal.
    fn shutdown_reconciliation_entry(&mut self) -> Result<(), i32> {
        if self.poisoned || shutdown_journal_blocks_ordinary_use(&self.shutdown_journal) {
            self.poisoned = true;
            return Err(-5);
        }
        Ok(())
    }
}

fn assert_send_sync<T: Send + Sync>() {}

fn token() -> OsToken {
    OsToken {
        slot: 7,
        generation: 91,
    }
}

fn target(cpu: usize, apic: u32, node: u32) -> HostCpuSnapshot {
    assert!(cpu != 0);
    HostCpuSnapshot {
        hardware_id: apic,
        numa_node: node,
        online: false,
    }
}

fn record_all(journal: &mut [ShutdownCpuJournal], targets: &[(usize, HostCpuSnapshot)]) {
    for (index, (cpu, snapshot)) in targets.iter().enumerate() {
        journal[index].record(
            token(),
            *cpu,
            *snapshot,
            (*cpu + 0x1000) as *mut bindings::device,
        );
    }
}

fn retain_all(
    journal: &mut [ShutdownCpuJournal],
    count: usize,
    stage: ShutdownCpuFailureStage,
    error: i32,
) {
    for entry in &mut journal[..count] {
        if entry.recorded {
            entry.retain(stage, error);
        }
    }
}

fn run(
    targets: &[(usize, HostCpuSnapshot)],
    prevalidate: impl Fn(usize, HostCpuSnapshot) -> Result<(), i32>,
    validate_before_reset: impl Fn(usize, ShutdownCpuJournal) -> bool,
    online_status: impl Fn(usize) -> i32,
    validate_after_online: impl Fn(usize, ShutdownCpuJournal) -> bool,
) -> ([ShutdownCpuJournal; 4], Vec<&'static str>, Result<(), i32>) {
    assert!(!targets.is_empty() && targets.len() <= 4);
    let mut journal = [ShutdownCpuJournal::empty(); 4];
    let mut log = Vec::new();
    for (index, (_, snapshot)) in targets.iter().enumerate() {
        if let Err(error) = prevalidate(index, *snapshot) {
            log.push("prevalidate-failed");
            return (journal, log, Err(error));
        }
    }
    log.push("prevalidated");
    record_all(&mut journal, targets);
    log.push("recorded");
    for index in 0..targets.len() {
        if !validate_before_reset(index, journal[index]) {
            retain_all(
                &mut journal,
                targets.len(),
                ShutdownCpuFailureStage::PreResetValidation,
                -5,
            );
            return (journal, log, Err(-5));
        }
    }
    for entry in &mut journal[..targets.len()] {
        entry.reset_attempted();
        log.push("init");
    }
    for index in 0..targets.len() {
        journal[index].online_attempted();
        log.push("online");
        let status = online_status(index);
        journal[index].online_status(status);
        if status != 0 {
            let failure = if status < 0 { status } else { -5 };
            retain_all(
                &mut journal,
                targets.len(),
                ShutdownCpuFailureStage::DeviceOnline,
                failure,
            );
            return (journal, log, Err(failure));
        }
        if !validate_after_online(index, journal[index]) {
            retain_all(
                &mut journal,
                targets.len(),
                ShutdownCpuFailureStage::PostOnlineValidation,
                -5,
            );
            return (journal, log, Err(-5));
        }
        journal[index].online();
    }
    (journal, log, Ok(()))
}

#[test]
fn success_records_before_effects_and_preserves_order() {
    let targets = [(1, target(1, 33, 1)), (2, target(2, 34, 1))];
    let (journal, log, result) = run(&targets, |_, _| Ok(()), |_, _| true, |_| 0, |_, _| true);
    assert_eq!(result, Ok(()));
    assert_eq!(
        log,
        [
            "prevalidated",
            "recorded",
            "init",
            "init",
            "online",
            "online"
        ]
    );
    for entry in &journal[..2] {
        assert!(entry.recorded && entry.reset_attempted && entry.online_attempted && entry.online);
        assert_eq!(entry.online_status, 0);
        assert!(!entry.retained && entry.first_failure == 0 && entry.matches_owner(token()));
    }
}

#[test]
fn validation_failure_has_no_effect_and_retains_every_target() {
    let targets = [(1, target(1, 33, 1)), (2, target(2, 34, 1))];
    let (journal, log, result) = run(
        &targets,
        |_, _| Ok(()),
        |index, _| index != 1,
        |_| 0,
        |_, _| true,
    );
    assert_eq!(result, Err(-5));
    assert_eq!(log, ["prevalidated", "recorded"]);
    for entry in &journal[..2] {
        assert!(
            entry.recorded && entry.retained && !entry.reset_attempted && !entry.online_attempted
        );
        assert_eq!(
            entry.first_failure_stage,
            ShutdownCpuFailureStage::PreResetValidation
        );
    }
}

#[test]
fn online_failure_or_positive_noop_retains_reset_progress() {
    let targets = [(1, target(1, 33, 1)), (2, target(2, 34, 1))];
    for (status, expected) in [(-19, -19), (1, -5)] {
        let (journal, _, result) = run(
            &targets,
            |_, _| Ok(()),
            |_, _| true,
            |index| if index == 1 { status } else { 0 },
            |_, _| true,
        );
        assert_eq!(result, Err(expected));
        assert!(journal[0].online && journal[0].reset_attempted);
        assert!(journal[1].reset_attempted && journal[1].online_attempted && !journal[1].online);
        assert!(journal[0].retained && journal[1].retained);
        assert_eq!(journal[1].online_status, status);
        assert_eq!(journal[1].first_failure, expected);
        assert_eq!(
            journal[1].first_failure_stage,
            ShutdownCpuFailureStage::DeviceOnline
        );
    }
}

#[test]
fn post_online_identity_uncertainty_retains_all() {
    let targets = [(1, target(1, 33, 1)), (2, target(2, 34, 1))];
    let (journal, _, result) = run(
        &targets,
        |_, _| Ok(()),
        |_, _| true,
        |_| 0,
        |index, _| index != 1,
    );
    assert_eq!(result, Err(-5));
    assert!(journal[0].online && !journal[1].online);
    assert!(journal[0].retained && journal[1].retained);
    assert_eq!(
        journal[1].first_failure_stage,
        ShutdownCpuFailureStage::PostOnlineValidation
    );
}

#[test]
fn prevalidation_failure_never_leaves_a_partial_journal() {
    let targets = [(1, target(1, 33, 1)), (2, target(2, 34, 1))];
    let (journal, log, result) = run(
        &targets,
        |index, _| if index == 1 { Err(-19) } else { Ok(()) },
        |_, _| true,
        |_| 0,
        |_, _| true,
    );
    assert_eq!(result, Err(-19));
    assert_eq!(log, ["prevalidate-failed"]);
    assert!(journal
        .iter()
        .all(|entry| !entry.recorded && !entry.retained));
}

#[test]
fn ordinary_paths_remain_closed_after_online_restoration() {
    assert_send_sync::<RetainedCpuDevice>();
    assert_send_sync::<ShutdownCpuJournal>();
    assert_send_sync::<ProductionCpuContextAdapter>();
    assert!(RetainedCpuDevice::empty().is_null());
    let targets = [(1, target(1, 33, 1))];
    let (journal, _, result) = run(&targets, |_, _| Ok(()), |_, _| true, |_| 0, |_, _| true);
    assert_eq!(result, Ok(()));
    let mut context = ProductionCpuContextAdapter::new();
    context.shutdown_journal[..1].copy_from_slice(&journal[..1]);
    assert!(context.shutdown_journal[0].online);
    assert_eq!(context.ordinary_verify_owned(), Err(-5));
    assert!(context.poisoned);
}

#[test]
fn repeated_shutdown_entry_is_rejected_without_clearing_any_record() {
    let targets = [(1, target(1, 33, 1))];
    let (journal, _, result) = run(&targets, |_, _| Ok(()), |_, _| true, |_| 0, |_, _| true);
    assert_eq!(result, Ok(()));
    let mut context = ProductionCpuContextAdapter::new();
    context.shutdown_journal[..1].copy_from_slice(&journal[..1]);
    assert_eq!(context.shutdown_reconciliation_entry(), Err(-5));
    assert!(context.shutdown_journal[0].recorded);
    assert!(context.shutdown_journal[0].online);
    assert!(!context.shutdown_journal[0].retained);
}

#[test]
fn owner_and_target_controls_stay_fail_closed() {
    let mut journal = ShutdownCpuJournal::empty();
    journal.record(
        token(),
        1,
        target(1, 33, 1),
        0x1001 as *mut bindings::device,
    );
    assert!(!journal.matches_owner(OsToken {
        slot: 7,
        generation: 92
    }));
    assert!(!journal.matches_owner(OsToken {
        slot: 8,
        generation: 91
    }));
    assert_eq!(journal.cpu, 1);
    assert_ne!(journal.apic_id, 0);
    assert!(!target(1, 33, 1).online);
}

#[test]
fn repeated_failure_retains_first_error_and_never_clears_progress() {
    let mut journal = ShutdownCpuJournal::empty();
    journal.record(
        token(),
        1,
        target(1, 33, 1),
        0x1001 as *mut bindings::device,
    );
    journal.reset_attempted();
    journal.retain(ShutdownCpuFailureStage::DeviceOnline, -5);
    journal.retain(ShutdownCpuFailureStage::PostOnlineValidation, -19);
    assert!(journal.recorded && journal.reset_attempted && journal.retained);
    assert_eq!(journal.first_failure, -5);
    assert_eq!(
        journal.first_failure_stage,
        ShutdownCpuFailureStage::DeviceOnline
    );
}
