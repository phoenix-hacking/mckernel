from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent

def body(src,start):
 a=src.index(start);op=src.index('{',a);depth=1;i=op+1
 while depth:
  if src[i]=='{':depth+=1
  if src[i]=='}':depth-=1
  i+=1
 return src[a:i]
def publication(src):
 a=src.index('        if published {',src.index('pub(crate) fn publish_syscall'));b=src.index('        let entry = slots',a);return src[a:b]
s=(D/'candidate-v3/smp_application.rs').read_text();old=(D/'candidate/smp_application.rs').read_text();f=(D/'actualbody-start.rs').read_text()
assert f.count(publication(old))==1;f=f.replace(publication(old),publication(s))
f=f.replace('completed:Option<(u64,u64)>}', 'completed:Option<(u64,u64)>,next_completion:Option<(u64,u64)>}')
f=f.replace('struct Response{r:Request}impl Response{fn request(&self)->&Request{&self.r}}','struct Response{r:Request,route:(u64,u64)}impl Response{fn request(&self)->&Request{&self.r}fn route(&self)->(u64,u64){self.route}}')
f=f.replace('first_return_published:bool,response:Response}', 'first_return_published:bool,first_return_committed:bool,response:Response}')
f=f.replace('completed:None}', 'completed:None,next_completion:None}')
f=f.replace('first_return_published:true,response:Response{r:original}', 'first_return_published:true,first_return_committed:true,response:Response{r:original,route:(6,31)}')
# Additional methods only supply fixture effects for the complete extracted publisher.
f+='''
impl Mailbox {
 fn publish(&mut self,_:i32,send:impl FnOnce(&[u8;128])->Result)->Result<bool>{let Some(route)=self.next_completion else{return Ok(false);};send(&[0;128])?;self.completed=Some(route);self.next_completion=None;Ok(true)}
 fn drained(&self)->bool{false}
}
impl Entry{fn request_cleanup(&mut self)->Result{Ok(())}}
mod actual_publication {
use super::*;use std::sync::{Mutex,MutexGuard};
const EBUSY:i32=-16;const EAGAIN:i32=-11;
macro_rules! pr_err {($($t:tt)*)=>{()}}
struct Lock<T>(Mutex<T>);impl<T> Lock<T>{fn lock(&self)->MutexGuard<'_,T>{self.0.lock().unwrap()}}
struct Release;impl Release{fn publish(&mut self,_:i32,_:impl FnOnce(&[u8;128])->Result)->Result<bool>{Ok(false)}}
struct Remote{slots:Lock<Vec<Option<Entry>>>,release_token:Token,releases:Lock<Release>}
impl Remote{
 fn transport_health(&self)->Result{Ok(())}
 fn quarantine_transport(&self,slots:&mut[Option<Entry>],_:i32){for e in slots.iter_mut().flatten(){e.quarantined=true;}}
'''+body(s,'    pub(crate) fn publish_syscall(').replace('pub(crate) fn','fn',1)+'\n'+body(s,'    fn finish_publication(')+'''
}
fn remote()->Remote{let mut v=super::setup();let p=v[0].as_mut().unwrap();p.syscalls.call.as_mut().unwrap().0=7;p.syscalls.next_completion=Some((6,31));let c=v[1].as_mut().unwrap();c.fork_ingress.as_mut().unwrap().first_return_published=false;Remote{slots:Lock(Mutex::new(v)),release_token:999,releases:Lock(Mutex::new(Release))}}
#[test]fn genuine_publication_allows_selector1_before_original_ret_waiter(){let r=remote();{let v=r.slots.lock();assert_eq!(super::Remote.current_host_start_child(&v,10,7,35,0,0,0),Err(EACCES));}let notified=AtomicBool::new(false);assert_eq!(r.publish_syscall(10,0,|_|Ok(()),||{assert!(r.slots.0.try_lock().is_err(),"notify must run while the same slots lock excludes other workers");notified.store(true,Ordering::Release);Ok(())}),Ok(true));assert!(notified.load(Ordering::Acquire));let v=r.slots.lock();assert!(v[1].as_ref().unwrap().fork_ingress.as_ref().unwrap().first_return_published);assert!(!v[1].as_ref().unwrap().scheduled);assert_eq!(super::Remote.current_host_start_child(&v,10,7,35,0,0,0),Ok(Some(1)));/* No original RET waiter code has executed. */}
#[test]fn wrong_serial_uncommitted_and_unpublished_cannot_mint_first_publication(){for variant in 0..3{let r=remote();{let mut v=r.slots.lock();match variant{0=>v[0].as_mut().unwrap().syscalls.next_completion=Some((6,30)),1=>v[1].as_mut().unwrap().fork_ingress.as_mut().unwrap().first_return_committed=false,_=>v[0].as_mut().unwrap().syscalls.next_completion=None};}let _=r.publish_syscall(10,0,|_|Ok(()),||Ok(())).unwrap();let v=r.slots.lock();assert!(!v[1].as_ref().unwrap().fork_ingress.as_ref().unwrap().first_return_published);assert!(!v[1].as_ref().unwrap().scheduled);}}
#[test]fn notification_and_send_failure_retain_child_without_publication_receipt(){for notify_failure in [false,true]{let r=remote();let result=r.publish_syscall(10,0,|_|if notify_failure{Ok(())}else{Err(-5)},||if notify_failure{Err(-5)}else{Ok(())});assert_eq!(result,Err(-5));let v=r.slots.lock();let c=v[1].as_ref().unwrap();assert!(c.quarantined);assert!(!c.scheduled);assert!(!c.fork_ingress.as_ref().unwrap().first_return_published);assert!(c.fork_ingress.is_some());assert!(c.inherited_root.is_some());}}
}
'''
# Protect the waiter ordering as a source-binding property: it only observes.
waiter=body(s,'    pub(crate) fn return_syscall(');assert 'first_return_published=true' not in waiter;assert 'if !slots[child].as_ref().unwrap().fork_ingress.as_ref().unwrap().first_return_published' in waiter
p=D/'actualbody-v3-start.rs';assert not p.exists();p.write_text(f)
source=hashlib.sha256(s.encode()).hexdigest();binding={'status':'SOURCE_BOUND_NOT_EXECUTED','v2_fixture_sha256':hashlib.sha256((D/'actualbody-start.rs').read_bytes()).hexdigest(),'v3_source_sha256':source,'fixture_sha256':hashlib.sha256(f.encode()).hexdigest(),'exact_body_sha256':{anchor:hashlib.sha256(body(s,anchor).encode()).hexdigest() for anchor in ('    pub(crate) fn publish_syscall(','    fn finish_publication(','    fn current_host_start_child(','    pub(crate) fn return_syscall(')},'publication_block_sha256':hashlib.sha256(publication(s).encode()).hexdigest(),'waiter_early_mutation_absent':True,'visibility_only_adjustment':'pub(crate) fn publish_syscall to fn in standalone nested module'}
(D/'ACTUALBODY-SOURCE-BINDING-V3.json').write_text(json.dumps(binding,indent=2)+'\n')
