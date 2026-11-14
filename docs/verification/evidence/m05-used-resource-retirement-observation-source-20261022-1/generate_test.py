from pathlib import Path
import sys,json,hashlib
Q=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel');sys.path.insert(0,str(ROOT))
from scripts.tests import test_native_shutdown_integration_source_20261017_1 as integ
from scripts.tests import test_native_shutdown_epoch_source_20261017_1 as epoch
from scripts.tests import test_shutdown_cpu_reclaim as cpu
from scripts.tests import test_sysfs_remote_shutdown_20261017 as remote
class Sources:
 def __truediv__(self,name):
  private=Q/'postimages'/name
  return private if private.is_file() else ROOT/'host-kernel/native-rust'/name
for module in [integ,epoch,remote]:
 if hasattr(module,'NATIVE'):module.NATIVE=Sources()
cpu.SOURCE=Q/'postimages/smp_cpu.rs'
text=integ.generated()
# Add the actual observation method that the existing consumer fixture did not
# previously need, leaving both changed coupled commit bodies byte-for-byte.
balanced=cpu.balanced_item
method=balanced((Q/'postimages/smp_cpu.rs').read_text(),'fn observe_shutdown_cpus(')
at=text.index('// COMPILE_FAIL_CONTROL');text=text[:at]+'impl CpuContext {\n'+method+'\n}\n'+text[at:]
# Memory/CPU tables below are explicit deterministic adapters. Production
# claim, validation, service retirement, release and log formatting execute.
method=balanced((Q/'postimages/smp_memory.rs').read_text(),'fn observe_shutdown_memory(')
text=text.replace('impl MemoryContext {','impl MemoryContext {\n'+method,1)
adapter=r'''
    struct ObservedExtent {start:u64,length:u64,owner:Option<OsToken>}
    impl ObservedExtent {
      fn start(&self)->u64{self.start}fn length(&self)->u64{self.length}
      fn numa_node(&self)->u32{0}fn owner(&self)->Option<OsToken>{self.owner}
    }
    impl Map {
      fn len(&self)->usize{if crate::OBSERVE_MANY.load(Ordering::Acquire){65}else{3}}
      fn extent(&self,index:usize)->Option<ObservedExtent>{
        if index>=self.len(){return None;}
        Some(ObservedExtent{start:4096+(index as u64)*8192,length:8192,
          owner:if index==0{self.owner}else if index==1{Some(super::smp_cpu::fixture_owner(7,92))}else{None}})
      }
    }
    pub(super) fn integration_epoch(owner:OsToken)->u64{unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].as_ref().unwrap().boot.as_ref().unwrap().epoch.id}
'''
text=text.replace('    struct MemoryWorkspace;',adapter+'\n    struct MemoryWorkspace;',1)
old='macro_rules! pr_info {($($t:tt)*)=>{{let _=format_args!($($t)*);}}}'
new='''static OBSERVATION_LOGS:std::sync::Mutex<Vec<String>>=std::sync::Mutex::new(Vec::new());
static OBSERVE_MANY:std::sync::atomic::AtomicBool=std::sync::atomic::AtomicBool::new(false);
macro_rules! pr_info {($($t:tt)*)=>{{crate::OBSERVATION_LOGS.lock().unwrap().push(format!($($t)*));}}}'''
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace('fn reset_integration_state(){','fn reset_integration_state(){OBSERVATION_LOGS.lock().unwrap().clear();OBSERVE_MANY.store(false,Ordering::Release);',1)
tests=r'''
    #[test]
    fn actual_resource_observations_preserve_commit_and_failure_boundaries(){
      let output=std::env::var("M05_OBSERVATION_OUTPUT").unwrap();
      for (case,failure) in [("good",0),("irq_retained",1),("map_retained",2),("epoch_retained",3),("bounded_unknown",4)] {
        setup_epoch(&[1,2]);
        let epoch=super::smp_memory::integration_epoch(token());
        match failure {1=>{super::IRQ_RELEASE_STATUS.store(-5,Ordering::Release);},
          2=>{super::MAP_STATUS.store(-5,Ordering::Release);},
          3=>{super::INJECT_STALE.store(true,Ordering::Release);},
          4=>{super::OBSERVE_MANY.store(true,Ordering::Release);},_=>{}}
        let result=invoke_provider();
        let logs=super::OBSERVATION_LOGS.lock().unwrap().join("");
        std::fs::write(format!("{}/{}.log",output,case),&logs).unwrap();
        std::fs::write(format!("{}/{}.json",output,case),format!("{{\"os\":7,\"generation\":91,\"epoch\":{},\"result\":{}}}\n",epoch,result)).unwrap();
        if failure==0||failure==4 {assert_eq!(result,0);assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);}
        else {assert_ne!(result,0);assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);assert!(!logs.contains("phase=committed"));}
      }
    }
'''
at=text.index('// COMPILE_FAIL_CONTROL');text=text[:at]+tests+'\n'+text[at:]
# Current production additions require matching storage in the old fixture's
# explicit adapters. No production method or ownership oracle is changed.
text=text.replace('struct Entry {cleanup:', 'struct Entry {parent_slot_pins:u32,fork_ingress:Option<()>,inherited_root:Option<()>,cleanup:',1)
text=text.replace('zeroing:Vec<Tagged>}', 'zeroing:Vec<Tagged>,exec_payloads:Vec<Option<Tagged>>}',1)
text=text.replace('zeroing:vec![]}', 'zeroing:vec![],exec_payloads:vec![]}',1)
(Q/'actual-resource-body.rs').write_text(text)
# Hash only the selected source/fixture consumers needed by this fixture.
selected=[Q/'postimages/smp_cpu.rs',Q/'postimages/smp_memory.rs']
selected += [Path(m.__file__) for m in [integ,epoch,cpu,remote]]
(Q/'ACTUAL-BODY-SOURCE-PINS.json').write_text(json.dumps({str(p):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in selected},indent=2)+'\n')
print(json.dumps({'generated':str(Q/'actual-resource-body.rs'),'bytes':len(text.encode()),'actual_cpu_method_embedded':method is not None}))
