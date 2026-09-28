//! Adapter whose semantic tests call extracted production shutdown methods.
mod smp_topology {
    pub struct Cpu {
        pub linux_id: u32,
        pub apic_id: u32,
    }
}
mod smp_memory {
    use super::fixture::{OsToken, Result, MEMORY_RELEASES, RETIRE_CALLS};
    use std::sync::atomic::Ordering;
    pub fn retire_os_boot(_owner: OsToken) -> Result {
        RETIRE_CALLS.fetch_add(1, Ordering::Relaxed);
        Ok(())
    }
    pub fn release_os_resources(_owner: OsToken, commit: impl FnOnce()) -> Result {
        MEMORY_RELEASES.fetch_add(1, Ordering::Relaxed);
        commit();
        Ok(())
    }
}
mod fixture {
    use std::pin::Pin;
    use std::ptr;
    use std::sync::atomic::{AtomicBool, AtomicI32, AtomicPtr, AtomicU32, Ordering};
    use std::sync::Arc;

    const SMP_MAX_CPUS: usize = 4;
    const EIO: i32 = -5;
    const ENODEV: i32 = -19;
    const EINVAL: i32 = -22;
    type Error = i32;
    pub(super) type Result<T = ()> = std::result::Result<T, Error>;
    trait ErrorNumber {
        fn to_errno(self) -> i32;
    }
    impl ErrorNumber for i32 {
        fn to_errno(self) -> i32 {
            self
        }
    }

    mod bindings {
        use super::{AtomicBool, AtomicI32, Ordering, SMP_MAX_CPUS};
        #[allow(non_camel_case_types)]
        pub struct device;
        pub unsafe fn put_device(_device: *mut device) {
            super::DEVICE_DROPS.fetch_add(1, Ordering::Relaxed);
        }
        static ONLINE: [AtomicBool; SMP_MAX_CPUS] =
            [const { AtomicBool::new(false) }; SMP_MAX_CPUS];
        static STATUS: [AtomicI32; SMP_MAX_CPUS] = [const { AtomicI32::new(0) }; SMP_MAX_CPUS];
        static BREAK_AFTER_ONLINE: [AtomicBool; SMP_MAX_CPUS] =
            [const { AtomicBool::new(false) }; SMP_MAX_CPUS];
        pub fn reset() {
            for cpu in 0..SMP_MAX_CPUS {
                ONLINE[cpu].store(false, Ordering::Relaxed);
                STATUS[cpu].store(0, Ordering::Relaxed);
                BREAK_AFTER_ONLINE[cpu].store(false, Ordering::Relaxed);
            }
        }
        pub fn online(cpu: usize) -> bool {
            ONLINE[cpu].load(Ordering::Acquire)
        }
        pub fn set_online(cpu: usize, value: bool) {
            ONLINE[cpu].store(value, Ordering::Release);
        }
        pub fn set_status(cpu: usize, value: i32) {
            STATUS[cpu].store(value, Ordering::Release);
        }
        pub fn break_identity_after_online(cpu: usize) {
            BREAK_AFTER_ONLINE[cpu].store(true, Ordering::Release);
        }
        pub unsafe fn get_cpu_device(cpu: u32) -> *mut device {
            (cpu as usize + 0x1000) as *mut device
        }
        pub unsafe fn device_online(cpu_device: *mut device) -> i32 {
            let cpu = cpu_device as usize - 0x1000;
            let status = STATUS[cpu].load(Ordering::Acquire);
            if status == 0 {
                ONLINE[cpu].store(true, Ordering::Release);
            }
            status
        }
        pub fn identity_broken(cpu: usize) -> bool {
            BREAK_AFTER_ONLINE[cpu].load(Ordering::Acquire) && online(cpu)
        }
    }
    mod kernel {
        pub mod error {
            pub fn to_result(status: i32) -> Result<(), i32> {
                if status == 0 {
                    Ok(())
                } else {
                    Err(status)
                }
            }
        }
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    pub(super) struct OsToken {
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
    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    struct HostCpuSnapshot {
        hardware_id: u32,
        numa_node: u32,
        online: bool,
    }
    #[allow(dead_code)]
    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum CpuState {
        Online,
        Absent,
        Available,
        Assigned,
        Quarantined,
    }
    #[derive(Clone, Copy)]
    struct Slot {
        state: CpuState,
        owner: Option<OsToken>,
        hardware_id: u32,
        numa_node: u32,
    }
    impl Slot {
        fn state(&self) -> CpuState {
            self.state
        }
        fn owner(&self) -> Option<OsToken> {
            self.owner
        }
        fn hardware_id(&self) -> u32 {
            self.hardware_id
        }
        fn numa_node(&self) -> u32 {
            self.numa_node
        }
    }
    struct CpuTable<const N: usize> {
        slots: [Slot; N],
    }
    impl CpuTable<SMP_MAX_CPUS> {
        fn slot(&self, cpu: usize) -> Result<&Slot> {
            self.slots.get(cpu).ok_or(EIO)
        }
        fn assigned_cpus(
            &self,
            owner: OsToken,
            requests: &mut [usize; SMP_MAX_CPUS],
        ) -> Result<usize> {
            let mut count = 0;
            for cpu in 1..SMP_MAX_CPUS {
                if self.slots[cpu].state == CpuState::Assigned
                    && self.slots[cpu].owner == Some(owner)
                {
                    requests[count] = cpu;
                    count += 1;
                }
            }
            Ok(count)
        }
        fn prepare_assign<'a>(
            &'a mut self,
            owner: OsToken,
            cpus: &'a [usize],
            _journal: &mut [CpuChange],
        ) -> Result<Transaction<'a>> {
            Ok(Transaction {
                table: self,
                owner: Some(owner),
                cpus,
            })
        }
        fn prepare_release<'a>(
            &'a mut self,
            _owner: OsToken,
            cpus: &'a [usize],
            _journal: &mut [CpuChange],
        ) -> Result<Transaction<'a>> {
            Ok(Transaction {
                table: self,
                owner: None,
                cpus,
            })
        }
    }
    struct Transaction<'a> {
        table: &'a mut CpuTable<SMP_MAX_CPUS>,
        owner: Option<OsToken>,
        cpus: &'a [usize],
    }
    impl Transaction<'_> {
        fn begin_external_effects(&mut self) -> Result {
            BEGIN_CALLS.fetch_add(1, Ordering::Relaxed);
            Ok(())
        }
        fn commit(self) -> Result {
            COMMITS.fetch_add(1, Ordering::Relaxed);
            for &cpu in self.cpus {
                self.table.slots[cpu].owner = self.owner;
            }
            Ok(())
        }
        fn compensated_rollback(self) -> Result {
            ROLLBACKS.fetch_add(1, Ordering::Relaxed);
            Ok(())
        }
    }
    #[derive(Clone, Copy)]
    struct CpuChange;
    struct ResourceModulePin;
    impl Drop for ResourceModulePin {
        fn drop(&mut self) {
            PIN_DROPS.fetch_add(1, Ordering::Relaxed);
        }
    }
    struct CpuRequest {
        array: usize,
        count: usize,
    }
    struct UserSlice;
    impl UserSlice {
        fn new(_array: usize, _length: usize) -> Self {
            Self
        }
        fn reader(self) -> Self {
            self
        }
        fn read<T>(&mut self) -> Result<T> {
            Err(EINVAL)
        }
    }
    struct DeviceHotplugGuard;
    impl DeviceHotplugGuard {
        fn lock() -> Self {
            Self
        }
    }
    struct LinuxCpuBatch<'a> {
        devices: &'a [Option<CpuDevice>; SMP_MAX_CPUS],
        _hotplug: &'a DeviceHotplugGuard,
    }
    impl LinuxCpuBatch<'_> {
        fn observe(&mut self, cpu: usize) -> Result<HostCpuSnapshot> {
            self.devices[cpu].as_ref().ok_or(ENODEV)?;
            observed_cpu(cpu, &CpuReadGuard::lock(), self._hotplug)
        }
    }

    // std::sync::Mutex has the same T: Send bounds as the pinned kernel Lock:
    // both Send and Sync require Send, not Sync, of the protected payload.
    struct Mutex<T>(std::sync::Mutex<T>);
    impl<T> Mutex<T> {
        fn lock(&self) -> std::sync::MutexGuard<'_, T> {
            self.0.lock().unwrap()
        }
    }
    type ContextMutex = Mutex<&'static mut CpuContext>;
    static PUBLISHED: AtomicPtr<ContextMutex> = AtomicPtr::new(ptr::null_mut());
    // Representative module envelope retaining the actual extracted controller.
    // Other fields carry independent Send+Sync owners and do not hide CPU bounds.
    #[allow(dead_code)]
    struct ModuleEnvelope {
        cpu_controller: Option<CpuController>,
        other_owners: Arc<()>,
    }

    struct CpuReadGuard;
    impl CpuReadGuard {
        fn lock() -> Self {
            Self
        }
    }

    static RESET_CALLS: AtomicU32 = AtomicU32::new(0);
    pub(super) static RETIRE_CALLS: AtomicU32 = AtomicU32::new(0);
    pub(super) static MEMORY_RELEASES: AtomicU32 = AtomicU32::new(0);
    static BEGIN_CALLS: AtomicU32 = AtomicU32::new(0);
    static COMMITS: AtomicU32 = AtomicU32::new(0);
    static ROLLBACKS: AtomicU32 = AtomicU32::new(0);
    static DEVICE_DROPS: AtomicU32 = AtomicU32::new(0);
    static PIN_DROPS: AtomicU32 = AtomicU32::new(0);
    static OBSERVATIONS: [AtomicU32; SMP_MAX_CPUS] = [const { AtomicU32::new(0) }; SMP_MAX_CPUS];
    static FAIL_ON_OBSERVATION: [AtomicU32; SMP_MAX_CPUS] =
        [const { AtomicU32::new(0) }; SMP_MAX_CPUS];
    fn reset_mock() {
        bindings::reset();
        RESET_CALLS.store(0, Ordering::Relaxed);
        for counter in [
            &RETIRE_CALLS,
            &MEMORY_RELEASES,
            &BEGIN_CALLS,
            &COMMITS,
            &ROLLBACKS,
            &DEVICE_DROPS,
            &PIN_DROPS,
        ] {
            counter.store(0, Ordering::Relaxed);
        }
        for cpu in 0..SMP_MAX_CPUS {
            OBSERVATIONS[cpu].store(0, Ordering::Relaxed);
            FAIL_ON_OBSERVATION[cpu].store(0, Ordering::Relaxed);
        }
    }
    fn fail_on_observation(cpu: usize, observation: u32) {
        FAIL_ON_OBSERVATION[cpu].store(observation, Ordering::Release);
    }
    fn observed_cpu(
        cpu: usize,
        _read: &CpuReadGuard,
        _hotplug: &DeviceHotplugGuard,
    ) -> Result<HostCpuSnapshot> {
        let observation = OBSERVATIONS[cpu].fetch_add(1, Ordering::AcqRel) + 1;
        let bad = observation == FAIL_ON_OBSERVATION[cpu].load(Ordering::Acquire)
            || bindings::identity_broken(cpu);
        Ok(HostCpuSnapshot {
            hardware_id: if bad { 0xffff } else { 0x20 + cpu as u32 },
            numa_node: 1,
            online: bindings::online(cpu),
        })
    }
    unsafe fn native_reset_secondary_cpu_via_init(_apic_id: u32) {
        RESET_CALLS.fetch_add(1, Ordering::Release);
    }
    struct TransitionTask;
    impl TransitionTask {
        fn new(_cpu: usize) -> Self {
            Self
        }
    }

    // PRODUCTION_SHUTDOWN_CPU_TYPES

    impl CpuContext {
        fn new(cpus: &[usize]) -> Self {
            let owner = token();
            let vacant = Slot {
                state: CpuState::Absent,
                owner: None,
                hardware_id: 0,
                numa_node: 0,
            };
            let mut context = Self {
                table: CpuTable {
                    slots: [vacant; SMP_MAX_CPUS],
                },
                shutdown_journal: [ShutdownCpuJournal::empty(); SMP_MAX_CPUS],
                journal: [CpuChange; SMP_MAX_CPUS],
                requests: [0; SMP_MAX_CPUS],
                requested: [false; SMP_MAX_CPUS],
                devices: [const { None }; SMP_MAX_CPUS],
                pin: Some(ResourceModulePin),
                poisoned: false,
            };
            for &cpu in cpus {
                context.table.slots[cpu] = Slot {
                    state: CpuState::Assigned,
                    owner: Some(owner),
                    hardware_id: 0x20 + cpu as u32,
                    numa_node: 1,
                };
                context.devices[cpu] = Some(CpuDevice(
                    (cpu + 0x1000) as *mut bindings::device,
                    Arc::new(super::smp_topology::Cpu {
                        linux_id: cpu as u32,
                        apic_id: 0x20 + cpu as u32,
                    }),
                ));
            }
            context
        }
        // PRODUCTION_SHUTDOWN_CPU_CONTROL
    }

    fn token() -> OsToken {
        OsToken {
            slot: 7,
            generation: 91,
        }
    }
    fn run(cpus: &[usize]) -> (CpuContext, Result) {
        let mut context = CpuContext::new(cpus);
        let result = context.shutdown_reset_and_reonline(token(), &DeviceHotplugGuard);
        (context, result)
    }

    #[test]
    fn success_runs_extracted_body_and_preserves_progress() {
        reset_mock();
        let (context, result) = run(&[1, 2]);
        assert_eq!(result, Ok(()));
        assert_eq!(RESET_CALLS.load(Ordering::Acquire), 2);
        for record in &context.shutdown_journal[..2] {
            assert!(
                record.recorded
                    && record.reset_attempted
                    && record.online_attempted
                    && record.online
            );
            assert_eq!(record.online_status, 0);
            assert!(!record.retained && record.first_failure == 0 && record.matches_owner(token()));
        }
    }
    #[test]
    fn extracted_pre_reset_validation_retains_all_without_reset() {
        reset_mock();
        fail_on_observation(2, 2);
        let (context, result) = run(&[1, 2]);
        assert_eq!(result, Err(EIO));
        assert_eq!(RESET_CALLS.load(Ordering::Acquire), 0);
        for record in &context.shutdown_journal[..2] {
            assert!(
                record.recorded
                    && record.retained
                    && !record.reset_attempted
                    && !record.online_attempted
            );
            assert_eq!(
                record.first_failure_stage,
                ShutdownCpuFailureStage::PreResetValidation
            );
        }
    }
    #[test]
    fn extracted_online_error_keeps_raw_status_and_retains_progress() {
        for (status, expected) in [(-19, -19), (1, EIO)] {
            reset_mock();
            bindings::set_status(2, status);
            let (context, result) = run(&[1, 2]);
            assert_eq!(result, Err(expected));
            assert_eq!(RESET_CALLS.load(Ordering::Acquire), 2);
            assert!(context.shutdown_journal[0].online && context.shutdown_journal[0].retained);
            let failed = context.shutdown_journal[1];
            assert!(
                failed.reset_attempted
                    && failed.online_attempted
                    && !failed.online
                    && failed.retained
            );
            assert_eq!(failed.online_status, status);
            assert_eq!(failed.first_failure, expected);
            assert_eq!(
                failed.first_failure_stage,
                ShutdownCpuFailureStage::DeviceOnline
            );
        }
    }
    #[test]
    fn extracted_post_online_identity_uncertainty_retains_all() {
        reset_mock();
        bindings::break_identity_after_online(2);
        let (context, result) = run(&[1, 2]);
        assert_eq!(result, Err(EIO));
        assert!(context.shutdown_journal[0].online && !context.shutdown_journal[1].online);
        assert!(context.shutdown_journal[0].retained && context.shutdown_journal[1].retained);
        assert_eq!(
            context.shutdown_journal[1].first_failure_stage,
            ShutdownCpuFailureStage::PostOnlineValidation
        );
    }
    #[test]
    fn extracted_preflight_failure_never_creates_a_partial_journal() {
        reset_mock();
        bindings::set_online(2, true);
        let (context, result) = run(&[1, 2]);
        assert_eq!(result, Err(EIO));
        assert_eq!(RESET_CALLS.load(Ordering::Acquire), 0);
        assert!(context
            .shutdown_journal
            .iter()
            .all(|record| !record.recorded && !record.retained));
    }
    #[test]
    fn extracted_entry_rejects_second_call_without_clearing_journal() {
        reset_mock();
        let (mut context, result) = run(&[1]);
        assert_eq!(result, Ok(()));
        assert_eq!(
            context.shutdown_reset_and_reonline(token(), &DeviceHotplugGuard),
            Err(EIO)
        );
        assert!(
            context.poisoned
                && context.shutdown_journal[0].recorded
                && context.shutdown_journal[0].online
        );
    }

    #[test]
    fn production_field_bounds_propagate_to_mutex_controller_and_module() {
        fn send<T: Send>() {}
        fn send_sync<T: Send + Sync>() {}
        send::<CpuContext>();
        send_sync::<ShutdownCpuJournal>();
        send_sync::<ContextMutex>();
        send_sync::<CpuController>();
        send_sync::<ModuleEnvelope>();
    }

    // Publish a real mutex for the extracted free function. The pointer is removed
    // before either owner drops, and all fixture tests run on one test thread.
    fn destroy(context: &mut CpuContext, owner: OsToken) -> Result {
        let mut mutex = Mutex(std::sync::Mutex::new(context));
        PUBLISHED.store(
            (&mut mutex as *mut Mutex<&mut CpuContext>).cast(),
            Ordering::Release,
        );
        let result = release_os_resources(owner);
        PUBLISHED.store(ptr::null_mut(), Ordering::Release);
        result
    }

    fn assert_no_release_effects() {
        for counter in [
            &RETIRE_CALLS,
            &MEMORY_RELEASES,
            &BEGIN_CALLS,
            &COMMITS,
            &ROLLBACKS,
            &DEVICE_DROPS,
            &PIN_DROPS,
        ] {
            assert_eq!(counter.load(Ordering::Relaxed), 0);
        }
    }

    #[test]
    fn exact_ordinary_callers_reject_successful_and_failed_journals_before_effects() {
        for failed in [false, true] {
            for operation in 0..5 {
                reset_mock();
                if failed {
                    bindings::set_status(1, -19);
                }
                let (mut context, result) = run(&[1]);
                assert_eq!(result, if failed { Err(-19) } else { Ok(()) });
                let records = context.shutdown_journal;
                let owners: Vec<_> = context.table.slots.iter().map(|slot| slot.owner).collect();
                let empty = CpuRequest { array: 0, count: 0 };
                let other = OsToken {
                    slot: 99,
                    generation: 1,
                };
                let observed = match operation {
                    0 => context.verify_owned(&DeviceHotplugGuard),
                    1 => context.change_os(token(), &empty, true).map(|_| ()),
                    2 => context.change_os(token(), &empty, false).map(|_| ()),
                    3 => destroy(&mut context, token()),
                    // Zero assigned CPU count for this owner must not bypass the fence.
                    4 => destroy(&mut context, other),
                    _ => unreachable!(),
                };
                assert_eq!(observed, Err(EIO));
                assert!(context.poisoned);
                assert_eq!(context.shutdown_journal, records);
                assert_eq!(
                    context
                        .table
                        .slots
                        .iter()
                        .map(|slot| slot.owner)
                        .collect::<Vec<_>>(),
                    owners
                );
                assert!(context.pin.is_some() && context.devices[1].is_some());
                assert_no_release_effects();
            }
        }
    }

    #[test]
    fn exact_ordinary_callers_without_journal_reach_instrumented_effects() {
        reset_mock();
        let mut context = CpuContext::new(&[1]);
        let empty = CpuRequest { array: 0, count: 0 };
        assert_eq!(context.verify_owned(&DeviceHotplugGuard), Ok(()));
        assert_eq!(context.change_os(token(), &empty, true), Ok(0));
        assert_eq!(context.change_os(token(), &empty, false), Ok(0));
        assert_eq!(RETIRE_CALLS.load(Ordering::Relaxed), 2);
        assert_eq!(destroy(&mut context, token()), Ok(()));
        assert_eq!(MEMORY_RELEASES.load(Ordering::Relaxed), 1);
        assert_eq!(COMMITS.load(Ordering::Relaxed), 1);
        assert_eq!(BEGIN_CALLS.load(Ordering::Relaxed), 1);
        assert_eq!(context.table.slots[1].owner, None);
        assert_eq!(destroy(&mut context, token()), Ok(()));
        assert_eq!(MEMORY_RELEASES.load(Ordering::Relaxed), 2);
        assert_eq!(COMMITS.load(Ordering::Relaxed), 1);
        drop(context);
        assert_eq!(DEVICE_DROPS.load(Ordering::Relaxed), 1);
        assert_eq!(PIN_DROPS.load(Ordering::Relaxed), 1);
    }
}
