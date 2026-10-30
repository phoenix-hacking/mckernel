// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code)]
type Result<T=()> = core::result::Result<T,i32>;
const EINVAL:i32=-22;
#[derive(Clone, Copy, PartialEq, Eq)] struct Token(u64);
impl Token { fn wire(self)->u64{self.0} }
#[derive(Clone, Copy, PartialEq, Eq)] struct Worker { id:u64 }
impl Worker { fn wire(self)->u64{self.id} fn tid(self)->i32{99} }
struct WorkerState { worker:Worker, delivery:Option<Token> }
#[derive(Clone)] struct Request { number:u64,args:[u64;6],cpu:i32 }
type SyscallRequest=Request;
impl Request { fn number(&self)->u64{self.number} fn arguments(&self)->[u64;6]{self.args} fn cpu(&self)->i32{self.cpu} fn tid_buffer(&self)->Result<(u64,u64)>{Err(-22)} }
struct Delivery { serial:Token, request:Request, worker:Worker, delivered:bool }
impl Delivery {
 fn serial(&self)->Token{self.serial} fn request(&self)->&Request{&self.request}
 fn check_return(&self,w:Worker,cpu:i64)->Result{if !self.delivered||self.worker!=w {Err(-16)} else if cpu!=self.request.cpu as i64 {Err(-22)} else {Ok(())}}
 fn begin_return(&mut self,w:Worker,cpu:i64)->Result{self.check_return(w,cpu)?;self.delivered=false;Ok(())}
 fn cancel(&mut self)->Result{self.delivered=false;Ok(())}
}
struct Exec;
impl Exec { fn pending(&self)->bool{false} fn complete(&self,_:&Request)->Result<bool>{Ok(true)} }
struct Completion<M>{_memory:M, value:i64}
struct Response<M>{memory:M}
impl<M> Response<M> { fn memory_mut(&mut self)->&mut M{&mut self.memory} fn prepare_retained(self,_:i32,value:i64)->core::result::Result<Completion<M>,(Self,i32)>{Ok(Completion{_memory:self.memory,value})} }
struct Call<M>{delivery:Delivery,response:Option<Response<M>>,completion:Option<Completion<M>>,kernel:bool,fork_parked:bool,service:bool,cancelled:bool,transferred:bool,exec:Option<Exec>,credential_written:bool}
struct Mailbox<M>{workers:Vec<Option<WorkerState>>,calls:Vec<Option<Call<M>>>,closed:bool,quarantined:bool}
#[derive(Default)] struct FakeMemory{claimed:bool,destination:u64,data:Vec<u8>,fail:bool}
impl FakeMemory {
 fn prepare_payload(&mut self,p:u64,n:usize,d:bool)->Result{if self.claimed||n!=32||!d{return Err(-16)};self.claimed=true;self.destination=p;Ok(())}
 fn pager_copy(&mut self,off:usize,b:&mut[u8],d:bool)->Result{if self.fail{return Err(-5)};if !self.claimed||off!=0||!d{return Err(-22)};self.data=b.to_vec();Ok(())}
}
include!("actual-methods.rs");
fn setup(phys:u64)->Mailbox<FakeMemory>{let w=Worker{id:7};Mailbox{workers:vec![Some(WorkerState{worker:w,delivery:Some(Token(11))})],calls:vec![Some(Call{delivery:Delivery{serial:Token(11),request:Request{number:122,args:[phys,1,0,0,0,0],cpu:2},worker:w,delivered:true},response:Some(Response{memory:FakeMemory::default()}),completion:None,kernel:false,fork_parked:false,service:false,cancelled:false,transferred:false,exec:None,credential_written:false})],closed:false,quarantined:false}}
fn call(m:&mut Mailbox<FakeMemory>,w:u64,s:u64,p:u64,b:&mut[u8])->Result {m.write_credentials(w,s,p,b,|r,mem,phys,bytes|mem.copy_credentials(r,phys,bytes))}
#[test] fn actual_body_success_and_ret(){let mut m=setup(0x1000);let mut bytes=[0x5a;32];assert_eq!(call(&mut m,7,11,0x1000,&mut bytes),Ok(()));let c=m.calls[0].as_ref().unwrap();assert!(c.credential_written);let mem=&c.response.as_ref().unwrap().memory;assert!(mem.claimed);assert_eq!(mem.data,bytes);assert_eq!(call(&mut m,7,11,0x1000,&mut bytes),Err(-16));assert_eq!(m.return_value(7,11,2,0,|_|Ok(())),Ok(()));assert_eq!(m.calls[0].as_ref().unwrap().completion.as_ref().unwrap().value,0);}
#[test] fn wrong_identity_and_request_never_write(){let mut bytes=[1;32];for (w,s,p) in [(8,11,0x1000),(7,12,0x1000),(7,11,0x1004)] {let mut m=setup(0x1000);assert!(call(&mut m,w,s,p,&mut bytes).is_err());let c=m.calls[0].as_ref().unwrap();assert!(!c.credential_written);assert!(!c.response.as_ref().unwrap().memory.claimed);}for (number,arg1) in [(121,1),(122,0),(122,2)]{let mut m=setup(0x1000);let r=&mut m.calls[0].as_mut().unwrap().delivery.request;r.number=number;r.args[1]=arg1;assert_eq!(call(&mut m,7,11,0x1000,&mut bytes),Err(-22));}}
#[test] fn geometry_and_phase(){let mut bytes=[1;32];for p in [0,1,0x1fe4,u64::MAX-3] {let mut m=setup(p);assert_eq!(call(&mut m,7,11,p,&mut bytes),Err(-22));}let mut m=setup(0x1fe0);assert_eq!(call(&mut m,7,11,0x1fe0,&mut bytes),Ok(()));let mut m=setup(0x1000);assert_eq!(call(&mut m,7,11,0x1000,&mut bytes[..31]),Err(-22));m.calls[0].as_mut().unwrap().delivery.delivered=false;assert_eq!(call(&mut m,7,11,0x1000,&mut bytes),Err(-16));}
#[test] fn negative_and_zero_return_and_cancel_require_completed_bytes(){for value in [-512,0,7] {let mut m=setup(0x1000);assert_eq!(m.return_value(7,11,2,value,|_|Ok(())),Err(-16));assert!(m.calls[0].as_ref().unwrap().response.is_some());}let mut m=setup(0x1000);let c=m.calls[0].as_mut().unwrap();assert_eq!(Mailbox::<FakeMemory>::cancel_call(c),Err(-16));assert!(c.cancelled&&c.response.is_some()&&c.completion.is_none());}
#[test] fn failed_copy_retains_uncompleted_claim(){let mut m=setup(0x1000);m.calls[0].as_mut().unwrap().response.as_mut().unwrap().memory.fail=true;let mut b=[9;32];assert_eq!(call(&mut m,7,11,0x1000,&mut b),Err(-5));let c=m.calls[0].as_ref().unwrap();assert!(!c.credential_written&&c.response.as_ref().unwrap().memory.claimed);assert_eq!(m.return_value(7,11,2,0,|_|Ok(())),Err(-16));}
#[test] fn ordinary_cancel_remains_unchanged(){let mut m=setup(0x1000);m.calls[0].as_mut().unwrap().delivery.request.number=123;let c=m.calls[0].as_mut().unwrap();assert_eq!(Mailbox::<FakeMemory>::cancel_call(c),Ok(()));assert_eq!(c.completion.as_ref().unwrap().value,-512);}
