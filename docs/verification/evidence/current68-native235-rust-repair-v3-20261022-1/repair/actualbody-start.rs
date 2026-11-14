#![allow(dead_code)]
use std::sync::atomic::{AtomicBool,Ordering};
type Token=u64; type Result<T=()>=std::result::Result<T,i32>;
const EACCES:i32=-13;const ENOENT:i32=-2;fn errno(e:i32)->i32{e}
#[derive(Clone)]struct Request{a:[u64;6],pid:i32,cpu:i32,requester:i32,target:i32}
impl Request{fn arguments(&self)->[u64;6]{self.a}fn cpu(&self)->i32{self.cpu}fn pid(&self)->i32{self.pid}fn requester(&self)->i32{self.requester}fn target(&self)->i32{self.target}}
struct Mailbox{call:Option<(u64,u64,Request)>,extra:Option<(u64,u64,Request)>,open:bool,completed:Option<(u64,u64)>}
impl Mailbox{fn delivered_fork_request(&self,h:u64,s:u64)->Result<Option<Request>>{let mut calls=self.call.iter().chain(self.extra.iter());let r=calls.find(|(w,_,_)|*w==h).ok_or(-2)?;if r.1!=s{return Err(-16);}Ok(Some(r.2.clone()))}fn has_open_worker(&self)->bool{self.open}fn unique_delivered_fork(&self,f:impl Fn(&Request)->bool)->Result<Option<(u64,u64,Request)>>{Ok(self.call.as_ref().filter(|(_,_,r)|f(r)).cloned())}fn returned(&self,w:u64,s:u64)->Result<bool>{Ok(self.completed==Some((w,s)))}}
struct Cleanup{pid:i32}impl Cleanup{fn pid(&self)->i32{self.pid}}
struct ChildTask{pid:i32}impl ChildTask{fn tgid(&self)->i32{self.pid}}
struct Response{r:Request}impl Response{fn request(&self)->&Request{&self.r}}
struct Owner{parent:Token,child:Token,child_task:ChildTask,host_start_return:Option<(u64,u64)>,host_revoke:Option<()>,sealed:AtomicBool,first_return_published:bool,response:Response}
struct Image{start:u64,end:u64,root:u64}
struct Entry{key:Token,cleanup:Cleanup,syscalls:Mailbox,fork_ingress:Option<Owner>,inherited_root:Option<Image>,closed:bool,needs_cleanup:bool,quarantined:bool,scheduled:bool}
impl Entry{fn key(&self)->Token{self.key}fn backend_ready(&self)->Result{if self.fork_ingress.as_ref().is_some_and(|o|o.sealed.load(Ordering::Acquire)&&o.host_revoke.is_none()){Ok(())}else{Err(EACCES)}}}
struct Remote;impl Remote{
    fn current_host_start_child(&self,slots:&[Option<Entry>],parent:Token,
        worker:u64,serial:u64,cpu:i64,value:i64,length:u64)->Result<Option<usize>> {
        let pe=slots.iter().flatten().find(|entry|entry.key()==parent).ok_or(ENOENT)?;
        let request=pe.syscalls.delivered_fork_request(worker,serial).map_err(errno)?;
        let Some(request)=request else{return Ok(None);};
        let args=request.arguments();
        if args[0]!=1||args[5]!=0x313030434b46434d{return Ok(None);}
        if value!=0{return Ok(None);}
        let a=request.arguments();
        if cpu!=request.cpu() as i64||length!=0||request.pid()!=pe.cleanup.pid()
            ||request.target()!=0{return Err(EACCES);}
        let mut matched=None;
        for (index,entry) in slots.iter().enumerate() {
            let Some(ce)=entry else{continue;};
            let Some(owner)=ce.fork_ingress.as_ref() else{continue;};
            if owner.parent!=parent||owner.child_task.tgid() as u64!=a[1]{continue;}
            let image=ce.inherited_root.as_ref().ok_or(EACCES)?;
            let original=owner.response.request();
            if matched.is_some()||ce.closed||ce.needs_cleanup||ce.quarantined||ce.scheduled
                ||owner.host_start_return.is_some()||owner.host_revoke.is_some()
                ||!owner.sealed.load(Ordering::Acquire)||!owner.first_return_published
                ||owner.child!=ce.key()||!ce.syscalls.has_open_worker()
                ||image.end-image.start!=a[2]||image.root!=a[3]
                ||original.arguments()[4]!=a[4]||original.arguments()[5]!=a[5]
                ||original.requester()!=request.requester()||original.cpu()!=request.cpu()
                {return Err(EACCES);}
            ce.backend_ready()?;matched=Some(index);
        }
        matched.map(Some).ok_or(EACCES)
    }
fn publish_actualbody(&self,slots:&mut [Option<Entry>],token:Token,published:bool)->Result{
        if published {
            for index in 0..slots.len() {
                let route=slots[index].as_ref().and_then(|entry|entry.fork_ingress.as_ref())
                    .filter(|owner|owner.parent==token).and_then(|owner|owner.host_start_return);
                let Some((worker,serial))=route else{continue;};
                let parent=slots.iter().flatten().find(|entry|entry.key()==token).ok_or(ENOENT)?;
                if parent.syscalls.returned(worker,serial).map_err(errno)? {
                    // Exact successful selector1 RET has been published. This
                    // is child admission, never destruction/final-ACK proof.
                    let child=slots[index].as_mut().unwrap();
                    child.scheduled=true;
                    child.fork_ingress.as_mut().unwrap().host_start_return=None;
                }
            }
        }
Ok(())}}
fn setup()->Vec<Option<Entry>>{
 let marker=0x313030434b46434d;
 let original=Request{a:[0,0x1000,0x2000,0x3000,0x4000,marker],pid:255,cpu:0,requester:255,target:0};
 let start=Request{a:[1,258,0x2000,0x3000,0x4000,marker],..original.clone()};
 let entry=|key,pid,call,owner,image|Some(Entry{key,cleanup:Cleanup{pid},syscalls:Mailbox{call,extra:None,open:true,completed:None},fork_ingress:owner,inherited_root:image,closed:false,needs_cleanup:false,quarantined:false,scheduled:key==10});
 vec![entry(10,255,Some((6,35,start)),None,None),entry(20,258,None,Some(Owner{parent:10,child:20,child_task:ChildTask{pid:258},host_start_return:None,host_revoke:None,sealed:AtomicBool::new(true),first_return_published:true,response:Response{r:original}}),Some(Image{start:0x1000,end:0x3000,root:0x3000}))]
}
fn select(v:&[Option<Entry>])->Result<Option<usize>>{Remote.current_host_start_child(v,10,6,35,0,0,0)}
#[test]fn exact_host_start_selects_owned_child(){assert_eq!(select(&setup()),Ok(Some(1)));}
#[test]fn failed_start_never_schedules(){assert_eq!(Remote.current_host_start_child(&setup(),10,6,35,0,-10,0),Ok(None));}
#[test]fn wrong_worker_is_not_this_return(){assert_eq!(Remote.current_host_start_child(&setup(),10,7,35,0,0,0),Err(-2));}
#[test]fn requires_real_first_publication(){let mut v=setup();v[1].as_mut().unwrap().fork_ingress.as_mut().unwrap().first_return_published=false;assert_eq!(select(&v),Err(EACCES));}
#[test]fn rejects_wrong_carrier_root_and_requester(){for field in 0..3{let mut v=setup();let r=&mut v[0].as_mut().unwrap().syscalls.call.as_mut().unwrap().2;match field{0=>r.a[4]+=8,1=>r.a[3]+=4096,_=>r.requester+=1};assert_eq!(select(&v),Err(EACCES));}}
#[test]fn rejects_closed_quarantined_revoke_and_missing_worker(){for field in 0..4{let mut v=setup();let c=v[1].as_mut().unwrap();match field{0=>c.closed=true,1=>c.quarantined=true,2=>c.fork_ingress.as_mut().unwrap().host_revoke=Some(()),_=>c.syscalls.open=false};assert_eq!(select(&v),Err(EACCES));}}
#[test]fn scheduled_only_after_exact_published_ret(){let mut v=setup();assert_eq!(select(&v),Ok(Some(1)));v[1].as_mut().unwrap().fork_ingress.as_mut().unwrap().host_start_return=Some((6,35));Remote.publish_actualbody(&mut v,10,true).unwrap();assert!(!v[1].as_ref().unwrap().scheduled);v[0].as_mut().unwrap().syscalls.completed=Some((6,34));Remote.publish_actualbody(&mut v,10,true).unwrap();assert!(!v[1].as_ref().unwrap().scheduled);v[0].as_mut().unwrap().syscalls.completed=Some((6,35));Remote.publish_actualbody(&mut v,10,false).unwrap();assert!(!v[1].as_ref().unwrap().scheduled);Remote.publish_actualbody(&mut v,10,true).unwrap();assert!(v[1].as_ref().unwrap().scheduled);assert!(v[1].as_ref().unwrap().fork_ingress.is_some());}
#[test]fn retains_adoption_and_does_not_set_destructor_ack(){let mut v=setup();let c=v[1].as_mut().unwrap();c.fork_ingress.as_mut().unwrap().host_start_return=Some((6,35));v[0].as_mut().unwrap().syscalls.completed=Some((6,35));Remote.publish_actualbody(&mut v,10,true).unwrap();let o=v[1].as_ref().unwrap().fork_ingress.as_ref().unwrap();assert!(o.host_revoke.is_none());assert_eq!(o.child_task.tgid(),258);}

#[test]fn concurrent_selector1_routes_remain_distinct(){let mut v=setup();let mut other=setup().pop().unwrap().unwrap();other.key=30;other.cleanup.pid=259;let o=other.fork_ingress.as_mut().unwrap();o.child=30;o.child_task.pid=259;o.response.r.a[4]=0x5000;let mut r=v[0].as_ref().unwrap().syscalls.call.as_ref().unwrap().2.clone();r.a[1]=259;r.a[4]=0x5000;v[0].as_mut().unwrap().syscalls.extra=Some((7,36,r));v.push(Some(other));assert_eq!(select(&v),Ok(Some(1)));assert_eq!(Remote.current_host_start_child(&v,10,7,36,0,0,0),Ok(Some(2)));}
#[test]fn stale_worker_and_delivery_generation_refused(){let v=setup();assert_eq!(Remote.current_host_start_child(&v,10,6+(1u64<<32),35,0,0,0),Err(-2));assert_eq!(Remote.current_host_start_child(&v,10,6,35+(1u64<<32),0,0,0),Err(-16));}
mod actual_mailbox{
use super::{Request,Result};
#[derive(Clone,Copy,PartialEq)]struct Token(u64);impl Token{fn wire(self)->u64{self.0}}
#[derive(Clone,Copy,PartialEq)]struct Worker(Token);impl Worker{fn wire(self)->u64{self.0.wire()}}
struct State{worker:Worker,delivery:Option<Token>}
struct Delivery{worker:Worker,serial:Token,request:Request}
impl Delivery{fn serial(&self)->Token{self.serial}fn request(&self)->&Request{&self.request}fn check_return(&self,w:Worker,cpu:i64)->Result{if w==self.worker&&cpu==self.request.cpu as i64{Ok(())}else{Err(-13)}}}
impl Request{fn number(&self)->u64{56}}
struct Call{delivery:Delivery}
struct Mailbox{closed:bool,quarantined:bool,workers:Vec<Option<State>>,calls:Vec<Option<Call>>}
impl Mailbox{
    fn delivered_fork_request(&self,handle:u64,serial:u64)->Result<Option<Request>> {
        if self.closed||self.quarantined{return Err(-32);}
        let worker=self.workers.iter().flatten().find(|state|state.worker.wire()==handle).ok_or(-2)?;
        if worker.delivery.map(Token::wire)!=Some(serial){return Err(-16);}
        let call=self.calls.iter().flatten().find(|call|call.delivery.serial().wire()==serial).ok_or(-2)?;
        call.delivery.check_return(worker.worker,call.delivery.request().cpu() as i64)?;
        let request=call.delivery.request();
        Ok(if request.number()==56{Some(request.clone())}else{None})
    }
}
#[test]fn exact_actual_mailbox_route_and_generation(){let r=super::setup()[0].as_ref().unwrap().syscalls.call.as_ref().unwrap().2.clone();let mut r2=r.clone();r2.a[1]=259;let m=Mailbox{closed:false,quarantined:false,workers:vec![Some(State{worker:Worker(Token(6)),delivery:Some(Token(35))}),Some(State{worker:Worker(Token(7)),delivery:Some(Token(36))})],calls:vec![Some(Call{delivery:Delivery{worker:Worker(Token(6)),serial:Token(35),request:r}}),Some(Call{delivery:Delivery{worker:Worker(Token(7)),serial:Token(36),request:r2}})]};assert_eq!(m.delivered_fork_request(6,35).unwrap().unwrap().a[1],258);assert_eq!(m.delivered_fork_request(7,36).unwrap().unwrap().a[1],259);assert!(matches!(m.delivered_fork_request(6,36),Err(-16)));assert!(matches!(m.delivered_fork_request((1u64<<32)+6,35),Err(-2)));assert!(matches!(m.delivered_fork_request(6,(1u64<<32)+35),Err(-16)));}
}
