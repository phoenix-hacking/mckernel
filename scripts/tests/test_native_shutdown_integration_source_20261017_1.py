"""Execute actual v6 provider, CPU/epoch consumer, service retirement and commit.

Only Linux allocation/hardware/thread/namespace boundaries use deterministic
adapters. This is source integration feedback, never native runtime acceptance.
"""
from pathlib import Path
import hashlib,json,os,subprocess,unittest
from scripts.tests import test_shutdown_cpu_reclaim as cpu_fixture
from scripts.tests import test_sysfs_remote_shutdown_20261017 as remote_fixture
balanced_item=cpu_fixture.balanced_item
ROOT=Path(__file__).resolve().parents[2]
NATIVE=ROOT/'host-kernel/native-rust'
FIXTURE=ROOT/'scripts/tests/fixtures/native_shutdown_integration_source_20261017_1.rs'
RUSTC='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'

MEMORY_ADAPTER=r'''
    struct MemoryWorkspace;
    impl MemoryWorkspace{fn new(_staging:&mut [Option<()>;1])->Result<Self>{Ok(Self)}}
    struct Map{owner:Option<OsToken>}
    struct MapTransaction<'a>{map:&'a mut Map}
    impl Map{fn prepare_release_all<'a>(&'a mut self,owner:OsToken,_work:&mut MemoryWorkspace)->Result<MapTransaction<'a>>{
        if super::MAP_STATUS.load(Ordering::Acquire)!=0||self.owner!=Some(owner){return Err(EIO);}Ok(MapTransaction{map:self})
    }}
    impl MapTransaction<'_>{fn begin_external_effects(&mut self)->Result{Ok(())}fn compensated_rollback(self)->Result{Ok(())}fn commit(self)->Result{self.map.owner=None;super::MEMORY_COMMITS.fetch_add(1,Ordering::AcqRel);Ok(())}}
    pub(super) fn integration_image_present(owner:OsToken)->bool{unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].is_some()}
    pub(super) fn integration_assigned(owner:OsToken)->bool{unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().map.owner==Some(owner)}
'''

INTEGRATION_TESTS=r'''
    fn invoke_provider()->i64{unsafe{super::ihk_smp_shutdown_v6(token().slot(),token().generation())}}
    fn assert_retained(cpu:&Mutex<&mut CpuContext>){
        assert!(super::smp_memory::integration_image_present(token()));
        assert!(super::smp_memory::integration_assigned(token()));
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);
        let cpu=cpu.lock();assert_eq!(cpu.table.slots[1].owner,Some(token()));assert!(cpu.devices[1].is_some());
    }
    #[test]fn integrated_quiescent_provider_consumes_same_claim_and_releases_exactly_once(){
        let cpu=setup_epoch(&[1,2]);assert_eq!(invoke_provider(),0);
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);
        assert_eq!(super::JOIN_COUNT.load(Ordering::Acquire),3);assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),2);
        assert!(!super::smp_memory::integration_image_present(token()));assert!(!super::smp_memory::integration_assigned(token()));
        {let cpu=cpu.lock();for c in [1,2]{assert!(cpu.devices[c].is_some());assert_eq!(cpu.table.slots[c].owner,None);assert_eq!(cpu.table.slots[c].state,CpuState::Online);assert!(!cpu.shutdown_journal[c-1].recorded);}}
        assert_eq!(invoke_provider(),-22);assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),2);
    }
    #[test]fn integrated_active_application_and_pager_are_post_claim_busy_without_discard(){
        for kind in [1,6]{let cpu=setup_epoch(&[1]);super::smp_memory::service::configure(kind);
            let result=invoke_provider();assert_ne!(result&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);assert_eq!(result as u32 as i32,-16);assert_eq!(RESET_CALLS.load(Ordering::Acquire),0);
            assert!(super::smp_memory::service::reserve_after_close());
            if kind==1{assert_eq!(super::smp_memory::service::app_retained(),1);}
            assert_eq!(super::JOIN_COUNT.load(Ordering::Acquire),0);assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),0);assert_retained(cpu);
        }
    }
    #[test]fn integrated_active_callback_pending_worker_and_procfs_are_post_effect_busy(){
        for kind in [2,4,5,7]{let cpu=setup_epoch(&[1]);super::smp_memory::service::configure(kind);
            let result=invoke_provider();assert_ne!(result,0);assert_ne!(result&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);
            assert_eq!(RESET_CALLS.load(Ordering::Acquire),1);assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),0);
            assert!(super::smp_memory::service::namespaces_retained());assert_retained(cpu);
        }
    }
    #[test]fn integrated_ledger_busy_and_map_preflight_failure_retain_all_physical_owners(){
        for kind in [3,0]{let cpu=setup_epoch(&[1]);super::smp_memory::service::configure(kind);
            if kind==0{super::MAP_STATUS.store(-5,Ordering::Release);}
            assert_ne!(invoke_provider()&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);assert_retained(cpu);
            assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),2);assert_eq!(super::JOIN_COUNT.load(Ordering::Acquire),3);
        }
    }
    #[test]fn integrated_same_epoch_is_revalidated_after_callback_drain_before_commit(){
        let cpu=setup_epoch(&[1]);super::INJECT_STALE.store(true,Ordering::Release);
        assert_ne!(invoke_provider()&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);assert_retained(cpu);
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);
    }
    #[test]fn integrated_irq_release_failure_preserves_both_logical_maps_and_devices(){
        let cpu=setup_epoch(&[1]);super::IRQ_RELEASE_STATUS.store(-5,Ordering::Release);
        assert_ne!(invoke_provider()&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);assert_retained(cpu);
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);
    }
    #[test]fn integrated_actual_file_tree_drop_blocks_release_until_linux_callback_drain_returns(){
        setup_epoch(&[1]);super::CALLBACK_DRAIN_BLOCK.store(true,Ordering::Release);
        let running=std::thread::spawn(invoke_provider);
        let deadline=std::time::Instant::now()+std::time::Duration::from_secs(2);
        while super::CALLBACK_DRAIN_ENTERED.load(Ordering::Acquire)==0{assert!(std::time::Instant::now()<deadline);std::thread::yield_now();}
        super::no_dependent_locks();assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);assert_eq!(super::CALLBACK_STORAGE_DROPS.load(Ordering::Acquire),0);
        assert!(super::smp_memory::integration_image_present(token()));
        super::CALLBACK_DRAIN_BLOCK.store(false,Ordering::Release);assert_eq!(running.join().unwrap(),0);
        assert_eq!(super::CALLBACK_STORAGE_DROPS.load(Ordering::Acquire),2);assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);
    }
    #[test]fn integrated_worker_join_blocks_final_release_without_dependent_locks(){
        setup_epoch(&[1]);super::JOIN_BLOCK.store(true,Ordering::Release);
        let running=std::thread::spawn(invoke_provider);
        let deadline=std::time::Instant::now()+std::time::Duration::from_secs(2);
        while super::JOIN_ENTERED.load(Ordering::Acquire)==0{assert!(std::time::Instant::now()<deadline);std::thread::yield_now();}
        super::no_dependent_locks();assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);
        assert!(super::smp_memory::integration_image_present(token()));assert_eq!(super::smp_memory::ordinary_boot(token()),Err(EBUSY));
        super::JOIN_BLOCK.store(false,Ordering::Release);assert_eq!(running.join().unwrap(),0);
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);
    }
'''

RUNTIME_TESTS=r'''
    fn runtime_setup()->(super::os_registry::OsRegistry,super::os_registry::OsHandle){
        let registry=super::os_registry::OsRegistry::new();
        for _ in 0..7{registry.reserve().unwrap().commit().unwrap();}
        for _ in 0..90{let reservation=registry.reserve().unwrap();assert_eq!(reservation.handle().minor(),7);drop(reservation);}
        let handle=registry.reserve().unwrap().commit().unwrap();assert_eq!((handle.minor(),handle.generation()),(7,91));
        registry.transition(handle,super::os_registry::OsStatus::Booting).unwrap();
        registry.transition(handle,super::os_registry::OsStatus::Running).unwrap();
        super::runtime_consumer::reset();(registry,handle)
    }
    #[test]fn integrated_runtime_keeps_running_closed_after_every_post_claim_gate_effect(){
        for kind in [1,6,8]{let cpu=setup_epoch(&[1]);let(registry,handle)=runtime_setup();
            if kind==8{super::IRQ_PRE_STATUS.store(-5,Ordering::Release);}else{super::smp_memory::service::configure(kind);}
            let result=super::runtime_consumer::transaction(&registry,handle,false);
            assert_eq!(result,if kind==8{-5}else{-16});
            assert!(super::runtime_consumer::closed(),"IHK admission reopened after native gate closure");
            assert_eq!(registry.snapshot(handle).unwrap().status,super::os_registry::OsStatus::Shutdown,"registry restored Running while native gates remain closed");
            assert!(!super::smp_memory::admission_open(token()));
            if kind!=8{assert!(super::smp_memory::service::reserve_after_close());}
            assert_eq!(RESET_CALLS.load(Ordering::Acquire),0);assert_retained(cpu);
        }
    }
    #[test]fn integrated_runtime_true_no_claim_failure_restores_running_without_closing_native_gates(){
        let cpu=setup_epoch(&[1]);let(registry,handle)=runtime_setup();
        assert_eq!(super::runtime_consumer::transaction(&registry,handle,true),-5);
        assert!(!super::runtime_consumer::closed());
        assert_eq!(registry.snapshot(handle).unwrap().status,super::os_registry::OsStatus::Running);
        assert!(super::smp_memory::admission_open(token()));
        assert!(!super::smp_memory::service::reserve_after_close());
        assert_eq!(RESET_CALLS.load(Ordering::Acquire),0);assert_retained(cpu);
    }
'''

def runtime_consumers():
    runtime=(NATIVE/'os_runtime.rs').read_text()
    registry=(NATIVE/'os_registry.rs').read_text().split('#[cfg(test)]\nmod tests {',1)[0]
    abi=(NATIVE/'abi/x86_64.rs').read_text()
    constants='\n'.join(line for line in abi.splitlines() if line.startswith('pub const IHK_OS_STATUS_'))
    runtime_constants='\n'.join(line for line in runtime.splitlines() if line.startswith(('const ADMISSION_','const SHUTDOWN_V6_')))
    markers=['struct Admission {','impl Admission {','struct ShutdownAdmission {','impl ShutdownAdmission {','impl Drop for ShutdownAdmission {','struct AdmissionOwner {','impl Drop for AdmissionOwner {','enum ShutdownCallbackOutcome {','fn shutdown_v6_outcome(','fn shutdown_errno(','fn finish_shutdown(']
    bodies='\n'.join(balanced_item(runtime,m) for m in markers)
    adapter=r'''
    static ADMISSION:Admission=Admission::new();
    static OPERATION:std::sync::Mutex<()>=std::sync::Mutex::new(());
    pub(super) fn reset(){ADMISSION.word.store(0,Ordering::Release);}
    pub(super) fn closed()->bool{ADMISSION.is_closed()}
    pub(super) fn transaction(registry:&super::os_registry::OsRegistry,handle:super::os_registry::OsHandle,stale:bool)->i32{
        // Real production registry lease remains live across the actual callback
        // and finish consumer. std mutex supplies the operation serialization;
        // an actual Linux ProviderModule pin is outside this source fixture.
        let _lease=registry.acquire(handle).unwrap();
        let _operation=OPERATION.lock().unwrap();
        let admission=ADMISSION.close_for_shutdown().unwrap();
        let guard=registry.begin_shutdown(handle).unwrap();
        assert!(ADMISSION.is_closed());
        let generation=if stale{handle.generation()-1}else{handle.generation()};
        let result=unsafe{super::ihk_smp_shutdown_v6(handle.minor() as u32,generation)};
        finish_shutdown(guard,admission,shutdown_v6_outcome(result))
    }
'''
    return 'mod abi {\n'+constants+'\n}\nmod os_registry {\n'+registry+'\n}\nmod runtime_consumer {\nuse super::smp_cpu::Result;\nuse std::{ptr,sync::atomic::{AtomicU32,Ordering}};\nconst EBUSY:i32=-16;\n'+runtime_constants+'\n'+bodies+'\n'+adapter+'\n}\n'

def generated():
    source=remote_fixture.generated()
    fixture=FIXTURE.read_text()
    app=(NATIVE/'smp_application.rs').read_text();service=(NATIVE/'smp_service.rs').read_text()
    cpu=(NATIVE/'smp_cpu.rs').read_text();memory=(NATIVE/'smp_memory.rs').read_text();provider=(NATIVE/'ihk_smp_x86_64.rs').read_text()
    pager=(NATIVE/'smp_file_pager.rs').read_text();procfs=(NATIVE/'smp_procfs.rs').read_text();ledger=(NATIVE/'sysfs_memory.rs').read_text()
    globals_=fixture[:fixture.index('mod smp_application {')]
    globals_=globals_.replace('// PRODUCTION_PROVIDER',balanced_item(provider,'fn shutdown_v6_post_effect(')+'\n'+balanced_item(provider,'unsafe extern "C" fn ihk_smp_shutdown_v6('))
    globals_+='\nfn reset_integration_state(){CALLBACK_DRAIN_BLOCK.store(false,Ordering::Release);for counter in [&CALLBACK_DRAIN_ENTERED,&CALLBACK_STORAGE_DROPS,&JOIN_COUNT,&JOIN_ENTERED,&NAMESPACE_DROPS,&MEMORY_COMMITS]{counter.store(0,Ordering::Release);}JOIN_BLOCK.store(false,Ordering::Release);IRQ_RELEASE_STATUS.store(0,Ordering::Release);IRQ_PRE_STATUS.store(0,Ordering::Release);MAP_STATUS.store(0,Ordering::Release);INJECT_STALE.store(false,Ordering::Release);}\n'
    source=source.replace('#![allow(dead_code)]','#![allow(dead_code)]\n'+globals_,1)
    appmod=balanced_item(fixture,'mod smp_application {').replace('// PRODUCTION_PAGER_CHECK',balanced_item(pager[pager.index('impl Registry {'):],'pub(crate) fn shutdown_quiescent(')).replace('// PRODUCTION_APP_METHODS','\n'.join(balanced_item(app,marker) for marker in ['pub(crate) fn reserve(', 'fn transport_health(', 'pub(crate) fn shutdown_close_if_quiescent(', 'pub(crate) fn shutdown_quiescent(']))
    source+='\n'+appmod
    callbacks=balanced_item(fixture,'mod callback_boundary {').replace('// PRODUCTION_FILE_DROP',balanced_item((NATIVE/'sysfs_objects.rs').read_text(),'impl<T: AttributeOps> Drop for File<T> {')).replace('// PRODUCTION_TREE_DROP',balanced_item((NATIVE/'sysfs_tree.rs').read_text(),'impl Drop for Tree {'))
    source+='\n'+callbacks
    servicemod=balanced_item(fixture,'mod integration_service_fixture {').replace('mod integration_service_fixture {','pub(super) mod service {',1)
    for marker,body in {
        'MEMORY_CHECK':balanced_item(ledger[ledger.index('impl Memory {'):],'pub(super) fn shutdown_quiescent('),
        'PROCFS_CHECK':balanced_item(procfs,'pub(super) fn close_if_quiescent('),
        'PROCFS_SERVICE_CHECK':balanced_item(procfs[procfs.index('impl Service {'):],'pub(super) fn shutdown_quiescent('),
        'STARTED_STRUCT':'#[derive(Clone)]\n'+balanced_item(service,'pub(in super::super) struct Started {'),
        'STARTED_METHODS':'\n'.join(balanced_item(service,m) for m in ['pub(super) fn stop_workers_after_peer_stop(', 'pub(super) fn close_application_admission(', 'pub(super) fn same_runtime(', 'pub(super) fn retire_after_peer_stop(']),
    }.items():servicemod=servicemod.replace('// PRODUCTION_'+marker,body)
    source=source.replace(balanced_item(source,'mod service {'),servicemod,1)
    source=source.replace('struct Error(i32);','pub(crate) struct Error(pub(crate) i32);',1)
    source+='\nimpl From<sysfs_remote::Error> for i32{fn from(error:sysfs_remote::Error)->Self{error.0}}\n'
    source=source.replace('struct Remote { data:SharedData, state:Mutex<State>, changed:CondVar }','pub(crate) struct Remote { data:SharedData, state:Mutex<State>, changed:CondVar }',1)
    # Narrow state hooks belong exclusively to the deterministic service adapter.
    hook='pub(super) fn fixture_service_remote()->Arc<Remote>{setup(0)}\nimpl Remote {pub(super) fn fixture_callbacks(&self,n:usize){self.state.lock().callbacks=n;}}\n'
    at=source.index('mod sysfs_remote {')+len('mod sysfs_remote {');source=source[:at]+hook+source[at:]
    source=source.replace('struct PreparedBoot { continuing:Option<service::Started>, irq:MockIrq }','struct PreparedBoot {sysfs:Option<()>, continuing:Option<service::Started>, irq:MockIrq }',1)
    source=source.replace('prepared:PreparedBoot {continuing:','prepared:PreparedBoot {sysfs:None,continuing:',1)
    source=source.replace('struct MemoryContext { images:[Option<LoadedImage>;64] }','struct MemoryContext { images:[Option<LoadedImage>;64],arguments:[Option<()>;64],map:Map,staging:[Option<()>;1] }',1)
    source=source.replace('MemoryContext {images}', 'MemoryContext {images,arguments:[None;64],map:Map{owner:Some(owner)},staging:[None]}',1)
    memorymethods=balanced_item(memory,'fn finish_shutdown_claim(')+'\nfn verify(&self)->Result{Ok(())}\n'
    source=source.replace('impl MemoryContext {','impl MemoryContext {\n'+memorymethods,1)
    source=source.replace('        let status=super::IRQ_STATUS.load(Ordering::Acquire);', '        let pre=super::IRQ_PRE_STATUS.load(Ordering::Acquire);if pre!=0{return Err(ShutdownIrqFailure::PreEffect(pre));}\n        let status=super::IRQ_STATUS.load(Ordering::Acquire);',1)
    source=source.replace('impl MockIrq {','impl MockIrq {fn release_drained(&mut self,_owner:OsToken)->Result{let status=super::IRQ_RELEASE_STATUS.load(Ordering::Acquire);if status!=0{return Err(status);}if !self.drained{return Err(EIO);}self.drained=false;Ok(())}',1)
    at=source.index('mod smp_memory {')+len('mod smp_memory {');source=source[:at]+MEMORY_ADAPTER+source[at:]
    source=source.replace('    pub(super) fn retire_os_boot(', balanced_item(memory,'pub(super) fn finish_shutdown_claim(')+'\n    pub(super) fn retire_os_boot(',1)
    source=source.replace('        reset_mock();super::STOP_CALLS', '        super::reset_integration_state();reset_mock();super::STOP_CALLS',1)
    extra='\n'.join(balanced_item(cpu,marker) for marker in ['pub(super) struct ShutdownFailure {','impl ShutdownFailure {','pub(super) fn shutdown_os_boot(','fn reconcile_shutdown_boot('])
    source=source.replace('// COMPILE_FAIL_CONTROL',extra+'\n'+INTEGRATION_TESTS+'\n'+RUNTIME_TESTS+'\n// COMPILE_FAIL_CONTROL',1)
    source+='\n'+runtime_consumers()
    source=source.replace('impl OsToken {','impl OsToken {pub(super) unsafe fn from_ihk_lease_v2(slot:u32,generation:u64)->Result<Self>{if slot>=64||generation==0{return Err(EINVAL);}Ok(Self{slot,generation})}',1)
    return source

class ShutdownIntegrationTests(unittest.TestCase):
    def test_production_consumers_and_negative_oracles(self):
        directory=Path(os.environ['MCKERNEL_SHUTDOWN_INTEGRATION_OUTPUT']);directory.mkdir(exist_ok=False)
        source=generated();self.assertNotIn('// PRODUCTION_',source);(directory/'actual.rs').write_text(source)
        compile_=subprocess.run([RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(directory/'actual.rs'),'-o',str(directory/'actual')],capture_output=True,text=True,timeout=30)
        for stream in ['stdout','stderr']:(directory/f'compile.{stream}').write_text(getattr(compile_,stream))
        (directory/'compile.status').write_text(str(compile_.returncode)+'\n');self.assertEqual(compile_.returncode,0,compile_.stderr)
        result=subprocess.run([str(directory/'actual'),'--test-threads=1'],capture_output=True,text=True,timeout=30)
        for stream in ['stdout','stderr']:(directory/f'run.{stream}').write_text(getattr(result,stream))
        (directory/'run.status').write_text(str(result.returncode)+'\n');self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('20 passed; 0 failed',result.stdout);print(result.stdout)
        for name,control,expected in [
            ('escape-claim',"fn bad(){let mut escaped=None;let _=with_shutdown_workers_stopped(token(),|boot|{escaped=Some(boot);Ok(())});let _=escaped;}",'E0521'),
            ('escape-proof',"fn bad<'a>(boot:&'a super::smp_memory::ShutdownBoot)->super::sysfs_remote::PeerStopped<'a>{let cpus=StoppedCpus{boot};super::sysfs_remote::PeerStopped::after_reset(&cpus)}",'E0515'),
        ]:
            path=directory/f'{name}.rs';path.write_text(source.replace('// COMPILE_FAIL_CONTROL',control))
            result=subprocess.run([RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(path),'-o',str(directory/name)],capture_output=True,text=True,timeout=30)
            (directory/f'{name}.stderr').write_text(result.stderr);(directory/f'{name}.status').write_text(str(result.returncode)+'\n');self.assertNotEqual(result.returncode,0);self.assertIn(expected,result.stderr)
            print(name,expected,'rejected')
        method=balanced_item(source,'pub(super) fn stop_workers_after_peer_stop(')
        bad=method.replace("PeerStopped<'_>","PeerStopped")
        self.assertNotEqual(method,bad)
        path=directory/'elided-service-lifetime.rs';path.write_text(source.replace(method,bad,1))
        result=subprocess.run([RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(path),'-o',str(directory/'elided-service-lifetime')],capture_output=True,text=True,timeout=30)
        (directory/'elided-service-lifetime.stderr').write_text(result.stderr);(directory/'elided-service-lifetime.status').write_text(str(result.returncode)+'\n')
        self.assertNotEqual(result.returncode,0);self.assertIn('elided_lifetimes_in_paths',result.stderr)
        print('actual service missing lifetime rejected under production lints')
        for name,old in [('application-effect','ShutdownFailure::at("application_quiesce", error, true)'),('irq-local-pre-effect','ShutdownFailure::at("irq_close", error, true)')]:
            self.assertIn(old,source)
            mutated=source.replace(old,old.replace(', true)',', false)'),1)
            path=directory/f'{name}-mutant.rs';path.write_text(mutated)
            result=subprocess.run([RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(path),'-o',str(directory/name)],capture_output=True,text=True,timeout=30)
            (directory/f'{name}.compile.stderr').write_text(result.stderr);(directory/f'{name}.compile.status').write_text(str(result.returncode)+'\n');self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([str(directory/name),'--exact','smp_cpu::integrated_runtime_keeps_running_closed_after_every_post_claim_gate_effect','--test-threads=1'],capture_output=True,text=True,timeout=10)
            (directory/f'{name}.run.stdout').write_text(result.stdout);(directory/f'{name}.run.stderr').write_text(result.stderr);(directory/f'{name}.run.status').write_text(str(result.returncode)+'\n')
            self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('FAILED',result.stdout)
            print(name,'old mapping rejected by actual runtime consumer')

if __name__=='__main__':unittest.main()
