"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Generate actual production bodies against explicit Linux/std/transport adapters.
"""
from pathlib import Path
import json,hashlib,sys
sys.path.insert(0,str(Path.cwd()))
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item as item
O=Path(__file__).resolve().parent
prep=json.loads(Path('docs/verification/evidence/current68-native235-v3-host-control-sdk-preparation-20261022-1.json').read_text())
rows=[]
def walk(x):
 if isinstance(x,dict):
  if 'origin' in x and 'path' in x: rows.append(x)
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(prep)
mods=['current_fork_host.rs','application_rpc.rs','application_syscall.rs','smp_application_syscall.rs','exec_transfer_checked.rs','exec_delivery.rs','application_image.rs']
M=O/'modules';M.mkdir(exist_ok=True);pins=[]
for name in mods:
 row=next(r for r in rows if r['path']==name)
 p=Path(row['origin']);data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256'],name
 (M/name).write_bytes(data);pins.append(row)
(O/'TESTED-SDK-MODULE-PINS.json').write_text(json.dumps(pins,indent=2)+'\n')
base=Path('docs/verification/evidence/phase5-paired-registration-lifetime-20261020-1/fixture-1/actual-pair.rs').read_text()
base=base[:base.index('\n}\nuse process::')].replace('#![allow(dead_code,non_snake_case)]','')
base=base.replace('struct Entry{process:Arc<Process>}','struct Entry{process:Arc<Process>,files:usize}')
base=base.replace('struct Process{slot:u32,generation:u64,pid:ProcessId,registration:Mutex<Option<Arc<Registration>>>}', 'struct Process{slot:u32,generation:u64,pid:ProcessId,registration:Mutex<Option<Arc<Registration>>>,executable:Mutex<Option<()>>}')
base=base.replace('AtomicBool,AtomicI32,Ordering','AtomicBool,AtomicI32,AtomicU64,Ordering').replace('fn same(&self,other:&Self)->bool{self.token==other.token}','fn same(&self,other:&Self)->bool{self.token==other.token}fn thread_alive(&self)->bool{self.pid!=260}')
base=base.replace('struct HostWorker{handle:u64}','struct HostWorker{handle:u64,identity:ProcessId,delivery:AtomicU64}')
base=base.replace('mapping:Mutex<Option<Arc<Mirror>>>','workers:Mutex<Vec<Arc<HostWorker>>>,mapping:Mutex<Option<Arc<Mirror>>>').replace('mapping:Mutex::new(Some(Arc::new(Mirror)))','workers:Mutex::new(Vec::new()),mapping:Mutex::new(Some(Arc::new(Mirror)))')
base=base.replace('armed:AtomicBool,workers:', 'armed:AtomicBool,cleanup_requested:AtomicBool,workers:').replace('armed:AtomicBool::new(true),workers:', 'armed:AtomicBool::new(true),cleanup_requested:AtomicBool::new(false),workers:')
base=base.replace('#[path="/home/holden/mckernel-work/host-preparation/phase5-parent-exit-rust-lifetime-correction-20261020-1/fixture-1/current_fork_host.rs"]', '#[path="'+str(M/'current_fork_host.rs')+'"]')
base=base.replace('const ENOENT:Error', 'const EIO:Error=Error(-5);const ENOENT:Error')
base=base.replace('pub struct ForkControlCallV1{','pub const CLEANUP:u32=4;pub const WORKER_CLOSE:u32=5;\n pub struct ForkControlCallV1{')
fixture=Path('scripts/tests/fixtures/native-application-syscall.rs').read_text()
prelude=fixture[fixture.index('extern crate self as kernel;'):fixture.index('#[allow(dead_code)]\n#[path = "../../../kernel/rust/abi.rs"]')]
ram=fixture[fixture.index('#[repr(C, align(8))]'):fixture.index('\n#[test]',fixture.index('#[repr(C, align(8))]'))]
ram+=fixture[fixture.index('struct TestRam {'):fixture.index('fn queued_request(')]
head='#![allow(dead_code,non_snake_case,non_camel_case_types,non_upper_case_globals,private_interfaces,dropping_copy_types)]\n'+prelude+'\nuse std::sync::Arc; use core::sync::atomic::{AtomicU64,Ordering};\n'
for name in mods[1:]:head+=f'#[path="{M/name}"] mod {name[:-3]};\n'
head+='use application_syscall as syscall;use smp_application_syscall as mailbox;\n'+ram
head+='''
thread_local! { static WORKER:std::cell::Cell<u64>=const{std::cell::Cell::new(0)}; static BACKEND:std::cell::RefCell<Option<(mailbox::Mailbox<TestMemory>,Arc<TestRam>)>>=const{std::cell::RefCell::new(None)}; static CLEANUPS:std::cell::Cell<usize>=const{std::cell::Cell::new(0)}; static CLOSES:std::cell::Cell<usize>=const{std::cell::Cell::new(0)}; }
fn setup_backend(){
 let mut p=[0u8;128]; p[8..12].copy_from_slice(&4i32.to_le_bytes());p[32..36].copy_from_slice(&260i32.to_le_bytes());p[48..52].copy_from_slice(&260i32.to_le_bytes());p[56..64].copy_from_slice(&1u64.to_le_bytes());p[64..72].copy_from_slice(&231u64.to_le_bytes());p[120..128].copy_from_slice(&0x800000u64.to_le_bytes());
 let request=syscall::Request::decode(&p,4).unwrap();let mut q=mailbox::Mailbox::new().unwrap();let w=q.open_worker(260).unwrap();WORKER.with(|n|n.set(w));let ram=TestRam::new(request.response(),2);q.admit(request,|_|ram.claim()).unwrap();let(s,_)=q.reserve(w).unwrap().unwrap();q.copied(w,s,true).unwrap();BACKEND.with(|b|*b.borrow_mut()=Some((q,ram)));CLEANUPS.with(|n|n.set(0));CLOSES.with(|n|n.set(0));
}
'''
extra='''
impl Registration{fn invoke(&self,command:u32,bytes:&mut[u8])->Result {assert_eq!(command,application_abi::WORKER_CLOSE);crate::BACKEND.with(|b|b.borrow_mut().as_mut().unwrap().0.close_worker(u64::from_le_bytes(bytes[..8].try_into().unwrap())).map_err(Error))}}

macro_rules! pr_info { ($($args:tt)*)=>{{let _=format_args!($($args)*);}} }
unsafe fn ihk_os_application_invoke_v1(_: *mut c_void,command:u32,_:*mut u8,_:usize)->i64 {assert_eq!(command,application_abi::CLEANUP);crate::CLEANUPS.with(|n|n.set(n.get()+1));crate::BACKEND.with(|b|b.borrow_mut().as_mut().unwrap().0.close().unwrap());-110}
unsafe fn ihk_os_application_close_v1(_: *mut c_void){crate::CLOSES.with(|n|n.set(n.get()+1));}
'''
tests='''
#[test]fn actual_reaper_close_retains_worker_until_actual_publication(){
 crate::setup_backend();let r=Registration::new(257,100);let handle=crate::WORKER.with(|n|n.get());r.workers.lock().push(Arc::new(HostWorker{handle,identity:ProcessId{pid:260,token:200},delivery:AtomicU64::new(97)}),GFP_KERNEL).unwrap();r.reap_workers().unwrap();assert_eq!(r.workers.lock().len(),1);
 crate::BACKEND.with(|b|{let mut b=b.borrow_mut();let(q,ram)=b.as_mut().unwrap();assert!(!q.drained());assert_eq!(ram.status(),0);assert_eq!(q.publish(0,|_|Err(-11)),Err(-11));assert!(ram.claimed.load(Ordering::Acquire));assert_eq!(q.publish(0,|_|Ok(())),Ok(true));assert_eq!(ram.status(),1);assert!(q.drained());});r.reap_workers().unwrap();assert_eq!(r.workers.lock().len(),0);
}

fn fixture_pair()->(Arc<Registration>,Arc<Registration>,Arc<Process>){
 let p=Registration::new(257,100);let c=Registration::new(260,200);let proof=application_abi::ForkPreparedV3{geometry:application_abi::ForkGeometryV3{root:4096,start:8192,length:4096},child_pid:260,reserved:0,child_mm:300,response:0x800000,nonce:9};c.reserve_fork_pair(&p,&proof).unwrap();
 let process=Arc::new(Process{slot:1,generation:7,pid:c._pid.clone(),registration:Mutex::new(Some(c.clone())),executable:Mutex::new(Some(()))});table().lock().push(Entry{process:process.clone(),files:1});(p,c,process)
}
#[test]fn last_binding_close_reaches_retained_child_and_real_publication(){
 crate::setup_backend();let(p,c,process)=fixture_pair();let weak=Arc::downgrade(&c);drop(c);drop(Binding(process.clone()));assert!(table().lock().is_empty());assert!(process.registration.lock().is_none());assert!(weak.upgrade().is_some());assert_eq!(p.control_children.lock().len(),1);assert!(weak.upgrade().unwrap().armed.load(Ordering::Acquire));crate::CLOSES.with(|n|assert_eq!(n.get(),0));
 crate::CLEANUPS.with(|n|assert_eq!(n.get(),@EXPECTED@));
 crate::BACKEND.with(|b|{let mut b=b.borrow_mut();let(q,ram)=b.as_mut().unwrap();assert!(!q.drained());assert_eq!(ram.status(),0);assert!(ram.claimed.load(Ordering::Acquire));assert_eq!(ram.releases.load(Ordering::Acquire),0);@PUBLICATION@});
 process.detach_owners();crate::CLEANUPS.with(|n|assert_eq!(n.get(),@EXPECTED@));assert!(weak.upgrade().is_some());assert_eq!(p.control_children.lock().len(),1);
 // Explicit test teardown after checks; this is not a production release path.
 let child=weak.upgrade().unwrap();drop(p.control_children.lock().swap_remove(0));child.fork_parent.lock().take();drop(child);drop(p);drop(process);
}
#[test]fn duplicate_cleanup_is_once_and_unarmed_is_untouched(){crate::setup_backend();let p=Registration::new(257,100);@DUPLICATE@let q=Registration::new(260,200);q.armed.store(false,Ordering::Release);drop(q);crate::CLEANUPS.with(|n|assert_eq!(n.get(),@DUP_EXPECTED@));drop(p);crate::CLEANUPS.with(|n|assert_eq!(n.get(),1));}
'''
for mode in ['preimage','candidate']:
 s=(O/(mode+'-mcctrl_process.rs')).read_text();out=head+'\n'+base+'\n'+extra+'\n'
 if mode=='candidate':out+='impl Registration{'+item(s,'fn request_cleanup(&self)')+'}\n'
 out+='impl Registration{'+item(s,'fn reap_workers(&self)')+'}\n'
 out+=item(s,'impl Drop for Registration {')+'\nimpl Process{'+item(s,'fn detach_owners(&self)')+'}\nstruct Binding(Arc<Process>);\n'+item(s,'impl Drop for Binding {')+'\n'
 t=tests.replace('@EXPECTED@','1' if mode=='candidate' else '0').replace('@DUP_EXPECTED@','1' if mode=='candidate' else '0').replace('@DUPLICATE@','p.request_cleanup();p.request_cleanup();' if mode=='candidate' else '')
 t=t.replace('@PUBLICATION@','assert_eq!(q.publish(0,|_|Err(-11)),Err(-11));assert_eq!(ram.status(),0);assert!(!q.drained());assert!(ram.claimed.load(Ordering::Acquire));assert_eq!(q.publish(0,|_|Ok(())),Ok(true));assert!(q.drained());assert_eq!(ram.status(),1);assert_eq!(ram.releases.load(Ordering::Acquire),1);' if mode=='candidate' else 'assert_eq!(q.publish(0,|_|panic!("no completion queued")),Ok(false));')
 out+=t+'\n}\nuse process::{application_abi,mcctrl_vm};\n';(O/(mode+'-actual.rs')).write_text(out)
