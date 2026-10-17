"""Consume production epoch/claim/CPU-reset/proof bodies with deterministic adapters.

No native build, hardware reset, Linux callback drain or release acceptance.
"""
from pathlib import Path
import json
import os
import subprocess
import unittest
from scripts.tests import test_shutdown_cpu_reclaim as cpu_regression
balanced_item=cpu_regression.balanced_item

ROOT=Path(__file__).resolve().parents[2]
NATIVE=ROOT/'host-kernel/native-rust'
FIXTURE=ROOT/'scripts/tests/fixtures/native_shutdown_epoch_source_20261017_1.rs'
RUSTC='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'

CPU_TESTS=r'''
    fn install_cpu(cpus:&[usize])->&'static Mutex<&'static mut CpuContext> {
        let context=Box::leak(Box::new(CpuContext::new(cpus)));
        let mutex=Box::leak(Box::new(Mutex(std::sync::Mutex::new(context))));
        PUBLISHED.store(mutex,Ordering::Release);mutex
    }
    fn setup_epoch(cpus:&[usize])->&'static Mutex<&'static mut CpuContext> {
        reset_mock();super::STOP_CALLS.store(0,Ordering::Release);super::IRQ_STATUS.store(0,Ordering::Release);
        super::smp_memory::setup(token());install_cpu(cpus)
    }
    #[test] fn scoped_success_joins_outside_all_dependent_locks_and_keeps_admission_closed() {
        let cpu=setup_epoch(&[1,2]);let mut observed=false;
        assert_eq!(with_shutdown_workers_stopped(token(),|boot| {
            observed=true;assert_eq!(boot.revalidate(),Ok(()));
            assert!(!super::smp_memory::admission_open(token()));
            assert_eq!(super::smp_memory::ordinary_boot(token()),Err(EBUSY));
            assert!(matches!(super::smp_memory::claim_shutdown_boot(token()),Err(EBUSY)));
            Ok(())
        }),Ok(()));
        assert!(observed);assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),1);
        assert_eq!(RESET_CALLS.load(Ordering::Acquire),2);
        assert!(!super::smp_memory::admission_open(token()));
        let cpu=cpu.lock();assert!(cpu.shutdown_journal[..2].iter().all(|r|r.boot_epoch!=0));
        assert!(cpu.devices[1].is_some()&&cpu.devices[2].is_some());
        assert!(cpu.table.slots[1].owner==Some(token()));
    }
    #[test] fn stale_generation_and_same_generation_reboot_cannot_adopt_journal() {
        let cpu=setup_epoch(&[1]);
        let stale=OsToken{slot:token().slot(),generation:token().generation()-1};
        assert!(matches!(super::smp_memory::claim_shutdown_boot(stale),Err(EIO)));
        assert_eq!(with_shutdown_workers_stopped(token(), |_|Ok(())),Ok(()));
        let first=cpu.lock().shutdown_journal[0].boot_epoch;
        super::smp_memory::replace_epoch(token());
        assert_eq!(with_shutdown_workers_stopped(token(), |_|panic!("stale epoch reached callback")),Err(EIO));
        assert_eq!(cpu.lock().shutdown_journal[0].boot_epoch,first);
        assert_eq!(RESET_CALLS.load(Ordering::Acquire),1);assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),1);
    }
    #[test] fn reset_error_partial_online_and_irq_error_never_mint_worker_authority() {
        for status in [-19,1] {
            let cpu=setup_epoch(&[1,2]);bindings::set_status(2,status);
            let result=with_shutdown_workers_stopped(token(), |_|panic!("partial proof reached callback"));
            assert!(result.is_err());assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),0);
            let cpu=cpu.lock();assert!(cpu.shutdown_journal[..2].iter().all(|r|r.boot_epoch!=0&&r.recorded));
            assert!(cpu.devices[1].is_some()&&cpu.devices[2].is_some());
        }
        setup_epoch(&[1]);super::IRQ_STATUS.store(-5,Ordering::Release);
        assert_eq!(with_shutdown_workers_stopped(token(), |_|panic!("IRQ failure reached callback")),Err(EIO));
        assert_eq!(RESET_CALLS.load(Ordering::Acquire),0);assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),0);
    }
    #[test] fn complete_but_unscoped_legacy_journal_cannot_mint_proof() {
        let cpu=setup_epoch(&[1]);
        {let mut cpu=cpu.lock();assert_eq!(cpu.shutdown_reset_and_reonline(token(),&DeviceHotplugGuard::lock()),Ok(()));}
        assert_eq!(with_shutdown_workers_stopped(token(), |_|panic!("legacy journal reached callback")),Err(EIO));
        assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),0);assert_eq!(RESET_CALLS.load(Ordering::Acquire),1);
    }
    #[test] fn active_claim_excludes_concurrent_claim_and_reboot_and_stale_commit() {
        setup_epoch(&[1]);let boot=super::smp_memory::claim_shutdown_boot(token()).unwrap();
        let owner=token();std::thread::spawn(move || {
            assert!(matches!(super::smp_memory::claim_shutdown_boot(owner),Err(EBUSY)));
            assert_eq!(super::smp_memory::ordinary_boot(owner),Err(EBUSY));
            assert!(!super::smp_memory::admission_open(owner));
        }).join().unwrap();
        super::smp_memory::shutdown_close_irq_senders(token()).ok().unwrap();
        assert_eq!(boot.revalidate(),Ok(()));
        super::smp_memory::replace_epoch(token());assert_eq!(boot.revalidate(),Err(EIO));
    }
    #[test] fn ended_transaction_revokes_peer_authority_and_post_join_revalidation() {
        setup_epoch(&[1]);let boot=super::smp_memory::claim_shutdown_boot(token()).unwrap();
        super::smp_memory::shutdown_close_irq_senders(token()).ok().unwrap();
        {let mut guard=unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock();guard.reset_shutdown_boot(&boot,&DeviceHotplugGuard::lock()).unwrap();}
        let cpus=StoppedCpus{boot:&boot};let proof=super::sysfs_remote::PeerStopped::after_reset(&cpus);
        assert!(proof.matches_boot(&boot));super::smp_memory::invalidate(token());
        assert!(!proof.matches_boot(&boot));assert_eq!(boot.stop_workers(&proof),Err(EIO));
        assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),0);
        setup_epoch(&[1]);
        assert_eq!(with_shutdown_workers_stopped(token(), |_| {super::smp_memory::replace_epoch(token());Ok(())}),Err(EIO));
    }
    pub(super) fn fixture_owner(slot:u32,generation:u64)->OsToken {OsToken{slot,generation}}
    pub(super) fn fixture_peer_scope(operation:impl for<'a> FnOnce(&super::sysfs_remote::PeerStopped<'a>)) {
        setup_epoch(&[1]);
        with_shutdown_workers_stopped(token(),|boot| {
            // The actual orchestrator already proved IRQ drain/reset/re-online
            // for this exact live boot before exposing its post-join scope.
            let cpus=StoppedCpus{boot};let proof=super::sysfs_remote::PeerStopped::after_reset(&cpus);
            operation(&proof);Ok(())
        }).unwrap();
    }
    // COMPILE_FAIL_CONTROL
'''

def generated():
    memory=(NATIVE/'smp_memory.rs').read_text()
    cpu=(NATIVE/'smp_cpu.rs').read_text()
    remote=(NATIVE/'sysfs_remote.rs').read_text()
    service=(NATIVE/'smp_service.rs').read_text()
    epoch=memory[memory.index('static NEXT_BOOT_EPOCH:'):memory.index('/// Turning started on is irreversible')]
    methods='\n'.join(balanced_item(memory,m) for m in ('fn require_unstarted(', 'fn claim_shutdown_boot(', 'fn validate_shutdown_boot('))
    peer=balanced_item(remote,"pub(crate) struct PeerStopped<'boot>")+ '\n'+balanced_item(remote,"impl<'boot> PeerStopped<'boot>")
    support,control=cpu_regression.ShutdownCpuReclaimTests().source_shutdown_control()
    support+='\n'+balanced_item(cpu,"pub(super) struct StoppedCpus<'boot>")+'\n'+balanced_item(cpu,"impl StoppedCpus<'_>")+'\n'+balanced_item(cpu,'pub(super) fn with_shutdown_workers_stopped(')
    control+='\n'+balanced_item(cpu,'fn reset_shutdown_boot(')
    template=(ROOT/'scripts/tests/fixtures/shutdown_cpu_reclaim.rs').read_text()
    topology=balanced_item(template,'mod smp_topology {')
    adapter=template[template.index('mod fixture {'):template.index('    #[test]')]
    adapter=adapter.replace('mod fixture {','mod smp_cpu {',1)
    adapter=adapter.replace('    const EINVAL: i32 = -22;','    const EINVAL: i32 = -22;\n    const EBUSY:i32=-16;')
    adapter=adapter.replace('        const fn slot(self) -> u32 {','        pub(super) const fn slot(self) -> u32 {').replace('        const fn generation(self) -> u64 {','        pub(super) const fn generation(self) -> u64 {')
    adapter=adapter.replace("fn lock(&self) -> std::sync::MutexGuard<'_, T> {\n            self.0.lock().unwrap()\n        }", "fn lock(&self) -> super::CountedGuard<'_, T> {\n            let guard=self.0.lock().unwrap();super::CPU_LOCKS.fetch_add(1,Ordering::AcqRel);super::CountedGuard {guard,counter:&super::CPU_LOCKS}\n        }")
    adapter=adapter.replace('struct DeviceHotplugGuard;','struct DeviceHotplugGuard;\n    impl Drop for DeviceHotplugGuard {fn drop(&mut self) {super::HOTPLUG_LOCKS.fetch_sub(1,Ordering::AcqRel);}}')
    adapter=adapter.replace('impl DeviceHotplugGuard {\n        fn lock() -> Self {\n            Self', 'impl DeviceHotplugGuard {\n        fn lock() -> Self {\n            super::HOTPLUG_LOCKS.fetch_add(1,Ordering::AcqRel);Self')
    adapter=adapter.replace('// PRODUCTION_SHUTDOWN_CPU_TYPES',support).replace('// PRODUCTION_SHUTDOWN_CPU_CONTROL',control)
    adapter+=CPU_TESTS+'\n}\n'
    return (FIXTURE.read_text().replace('// PRODUCTION_PEER_PROOF',peer).replace('// PRODUCTION_EPOCH',epoch)
            .replace('// PRODUCTION_MEMORY_METHODS',methods).replace('// PRODUCTION_MEMORY_CLAIM_WRAPPER',balanced_item(memory,'pub(super) fn claim_shutdown_boot('))
            .replace('// PRODUCTION_CPU_FIXTURE',topology+'\n'+adapter)
            .replace('// PRODUCTION_STARTED_STRUCT','#[derive(Clone)]\n'+balanced_item(service,'pub(in super::super) struct Started {'))
            .replace('// PRODUCTION_STARTED_STOP',balanced_item(service,'pub(super) fn stop_workers_after_peer_stop(')))

class ShutdownEpochTests(unittest.TestCase):
    def test_actual_bodies_and_lifetime_rejections(self):
        directory=Path(os.environ['MCKERNEL_SHUTDOWN_EPOCH_OUTPUT']);directory.mkdir(exist_ok=False)
        source=generated();self.assertNotIn('// PRODUCTION_',source)
        (directory/'actual.rs').write_text(source)
        compiled=subprocess.run([RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(directory/'actual.rs'),'-o',str(directory/'actual')],capture_output=True,text=True,timeout=30)
        for stream in ('stdout','stderr'):(directory/f'compile.{stream}').write_text(getattr(compiled,stream))
        (directory/'compile.status').write_text(str(compiled.returncode)+'\n')
        self.assertEqual(compiled.returncode,0,compiled.stderr)
        ran=subprocess.run([str(directory/'actual'),'--test-threads=1'],capture_output=True,text=True,timeout=30)
        for stream in ('stdout','stderr'):(directory/f'run.{stream}').write_text(getattr(ran,stream))
        (directory/'run.status').write_text(str(ran.returncode)+'\n')
        self.assertEqual(ran.returncode,0,ran.stdout+ran.stderr);self.assertIn('6 passed; 0 failed',ran.stdout)
        print(ran.stdout)
        controls={
            'escape-claim':'''fn rejected_escape() {let mut escaped=None;let _=with_shutdown_workers_stopped(token(),|boot| {escaped=Some(boot);Ok(())});let _=escaped;}''',
            'escape-proof':'''fn rejected_proof<'a>(boot:&'a super::smp_memory::ShutdownBoot)->super::sysfs_remote::PeerStopped<'a> {let cpus=StoppedCpus{boot};super::sysfs_remote::PeerStopped::after_reset(&cpus)}''',
        }
        for name,body in controls.items():
            path=directory/f'{name}.rs';path.write_text(source.replace('// COMPILE_FAIL_CONTROL',body))
            result=subprocess.run([RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(path),'-o',str(directory/name)],capture_output=True,text=True,timeout=30)
            (directory/f'{name}.stderr').write_text(result.stderr);(directory/f'{name}.status').write_text(str(result.returncode)+'\n')
            self.assertNotEqual(result.returncode,0,result.stderr)
            self.assertIn('E0521' if name=='escape-claim' else 'E0515',result.stderr)
            print(f'{name}: rejected as required')
        old_signature="proof: &super::super::sysfs_remote::PeerStopped<'_>,"
        self.assertEqual(source.count(old_signature),1)
        path=directory/'elided-service-lifetime.rs';path.write_text(source.replace(old_signature,'proof: &super::super::sysfs_remote::PeerStopped,'))
        result=subprocess.run([RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(path),'-o',str(directory/'elided-service-lifetime')],capture_output=True,text=True,timeout=30)
        (directory/'elided-service-lifetime.stderr').write_text(result.stderr)
        (directory/'elided-service-lifetime.status').write_text(str(result.returncode)+'\n')
        self.assertNotEqual(result.returncode,0,result.stderr)
        self.assertIn('elided_lifetimes_in_paths',result.stderr)
        print('original elided service lifetime: rejected under production lints')

if __name__=='__main__':unittest.main()
