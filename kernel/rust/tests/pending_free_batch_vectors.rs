// Appended verbatim to extracted production source. Pointer IDs are fixture-local.
use std::cell::{Cell, RefCell};
use std::sync::atomic::{AtomicUsize, Ordering};
#[derive(Clone, Copy, Debug)]
struct Callback(CULong, CInt, CInt);
struct Ledger { entries: [Callback; 32], used: usize, limit: usize }
thread_local! {
    static LEDGER: RefCell<Ledger> = const { RefCell::new(Ledger { entries: [Callback(0,0,0);32], used: 0, limit: 32 }) };
    static CALLBACK_ERROR: Cell<usize> = const { Cell::new(0) };
}
static TLS_ERROR: AtomicUsize = AtomicUsize::new(0);
unsafe extern "C" fn free_page(p: CULong, n: CInt, u: CInt) {
    let access = LEDGER.try_with(|c| {
        let error = match c.try_borrow_mut() {
            Ok(mut l) => { if l.used >= l.limit { 2 } else { let i=l.used; l.entries[i]=Callback(p,n,u); l.used+=1; 0 } },
            Err(_) => 1,
        };
        if error != 0 && CALLBACK_ERROR.try_with(|e|e.set(error)).is_err() { TLS_ERROR.fetch_add(1,Ordering::SeqCst); }
    });
    if access.is_err() { TLS_ERROR.fetch_add(1,Ordering::SeqCst); }
}
fn reset() { LEDGER.with(|c| { let mut l=c.borrow_mut(); l.used=0; l.limit=32; }); CALLBACK_ERROR.with(|c|c.set(0)); assert_eq!(TLS_ERROR.load(Ordering::SeqCst),0); }
fn callbacks() -> String { LEDGER.with(|c| { let l=c.borrow(); let v:Vec<String>=l.entries[..l.used].iter().map(|x|format!("[{},{},{}]",x.0,x.1,x.2)).collect(); format!("[{}]",v.join(",")) }) }
fn callback_controls() { reset(); LEDGER.with(|c| { let _held=c.borrow_mut(); unsafe { free_page(1,1,1); } }); assert_eq!(CALLBACK_ERROR.with(Cell::get),1); reset(); LEDGER.with(|c|c.borrow_mut().limit=0); unsafe { free_page(1,1,1); } assert_eq!(CALLBACK_ERROR.with(Cell::get),2); reset(); println!("CONTROL|callback-borrow-and-capacity-observed"); }
fn head() -> AbiListHead { AbiListHead {next:null_mut(),prev:null_mut()} }
fn page(i:usize) -> MemPage { MemPage {list:head(),hash:head(),mode:PM_NONE,phys:100+i as u64,count:IhkAtomic{counter:70+i as i32},mapped:IhkAtomic64{counter64:80+i as i64},offset:0,pgshift:12+i as i32} }
struct World { s:AbiListHead,t:AbiListHead,p:[MemPage;4],b:Pin<Box<PendingFreeBatch>> }
impl World {
    fn new()->Box<Self>{Box::new(Self{s:head(),t:head(),p:std::array::from_fn(page),b:Box::pin(PendingFreeBatch::new())})}
    unsafe fn id(&self,x:*mut AbiListHead)->usize {
        if x.is_null(){return 0} if x==(&raw const self.s).cast_mut(){return 1} if x==(&raw const self.t).cast_mut(){return 2}
        if x==(&raw const self.b.as_ref().get_ref().head).cast_mut(){return 3}
        for (i,p) in self.p.iter().enumerate(){if x==(&raw const p.list).cast_mut(){return 10+i} if x==(&raw const p.hash).cast_mut(){return 20+i}}
        if x as usize==LIST_POISON1{return 90} if x as usize==LIST_POISON2{return 91} panic!("unknown pointer")
    }
    unsafe fn links(&self,h:&AbiListHead)->String{format!("{{\"next\":{},\"prev\":{}}}",self.id(h.next),self.id(h.prev))}
    unsafe fn snapshot(&self)->String {
        let pages:Vec<String>=self.p.iter().map(|p|format!("{{\"list\":{},\"hash\":{},\"mode\":{},\"phys\":{},\"count\":{},\"mapped\":{},\"offset\":{},\"pgshift\":{}}}",self.links(&p.list),self.links(&p.hash),p.mode,p.phys,p.count.counter,p.mapped.counter64,p.offset,p.pgshift)).collect();
        let b=self.b.as_ref().get_ref();let state=match b.state{PendingFreeBatchState::Vacant=>0,PendingFreeBatchState::Retained=>1,PendingFreeBatchState::Drained=>2};
        format!("{{\"source\":{},\"other\":{},\"batch\":{{\"head\":{},\"state\":{},\"source\":{}}},\"pages\":[{}]}}",self.links(&self.s),self.links(&self.t),self.links(&b.head),state,self.id(b.source),pages.join(","))
    }
    unsafe fn retained_destination(&self)->String {
        let b=self.b.as_ref().get_ref();assert!(b.state==PendingFreeBatchState::Retained);
        let pages:Vec<String>=self.p[..2].iter().map(|p|format!("{}:{}:{}:{}:{}:{}:{}:{}",self.links(&p.list),self.links(&p.hash),p.mode,p.phys,p.count.counter,p.mapped.counter64,p.offset,p.pgshift)).collect();
        format!("{}:{}:{}",self.links(&b.head),self.id(b.source),pages.join(","))
    }
    unsafe fn setup(&mut self,n:usize,other:bool){assert_eq!(mem_begin_free_pages_pending_result(&raw mut self.s),0);for i in 0..n {assert_eq!(mem_free_pages_pending_enqueue_result(&raw mut self.p[i],&raw mut self.s,i as i32+1,None),1)} if other {assert_eq!(mem_begin_free_pages_pending_result(&raw mut self.t),0);assert_eq!(mem_free_pages_pending_enqueue_result(&raw mut self.p[3],&raw mut self.t,4,None),1)} for p in &mut self.p {init_list_head(&raw mut p.hash)} }
    unsafe fn emit(&self,name:&str,op:&str,rc:i32,before:String){let after=self.snapshot();let cb=callbacks();println!("JSON|{{\"case\":\"{}\",\"op\":\"{}\",\"rc\":{},\"before\":{},\"after\":{},\"callbacks\":{}}}",name,op,rc,before,after,cb);assert_eq!(CALLBACK_ERROR.with(Cell::get),0);assert_eq!(TLS_ERROR.load(Ordering::SeqCst),0);if rc<0 {assert!(before==after && cb=="[]","PARTIAL_RELEASE_DETECTED case={}",name)} }
    unsafe fn detach(&mut self,name:&str,src:usize){reset();let before=self.snapshot();let s=match src{0=>null_mut(),3=>&raw mut self.b.as_mut().get_unchecked_mut().head,_=>&raw mut self.s};let rc=detach_pending_free_batch(s,self.b.as_mut());self.emit(name,"detach",rc,before)}
    unsafe fn drain(&mut self,name:&str,wrong:bool,callback:bool){reset();let before=self.snapshot();let s=if wrong{&raw mut self.t}else{&raw mut self.s};let rc=drain_pending_free_batch(s,self.b.as_mut(),if callback{Some(free_page)}else{None});self.emit(name,"drain",rc,before)}
}
fn main(){unsafe{
    assert_eq!(core::mem::offset_of!(MemPage,list),0);assert_eq!(core::mem::size_of::<MemPage>(),80);
    callback_controls();
    for (name,n) in [("empty",0),("one",1),("three-order",3)] {let mut w=World::new();w.setup(n,false);w.detach(name,1);w.drain(name,false,true);}
    let mut w=World::new();w.setup(2,false);w.detach("later-invalid-setup",1);w.p[1].mode=PM_NONE;w.drain("later-invalid",false,true);w.p[1].mode=PM_PENDING_FREE;w.drain("later-invalid-repair",false,true);
    let mut w=World::new();w.setup(1,false);w.detach("missing-callback-setup",1);w.drain("missing-callback",false,false);w.drain("missing-callback-recovery",false,true);
    let mut w=World::new();w.setup(1,true);w.detach("wrong-source-setup",1);w.drain("wrong-source",true,true);w.drain("wrong-source-recovery",false,true);
    let mut w=World::new();w.setup(1,false);w.detach("repeated-setup",1);w.detach("repeated-detach",1);w.drain("repeated-recovery",false,true);w.drain("repeated-drain",false,true);
    let mut w=World::new();w.setup(0,false);w.detach("null-source",0);
    let mut w=World::new();w.detach("inactive-empty",1);
    let mut w=World::new();w.setup(1,false);w.detach("alias-destination",3);
    let mut w=World::new();w.setup(1,false);w.b.as_mut().get_unchecked_mut().head.next=&raw mut w.s;w.detach("mixed-destination-links",1);
    let mut w=World::new();w.setup(1,false);w.b.as_mut().get_unchecked_mut().state=PendingFreeBatchState::Retained;w.detach("mixed-destination-state",1);
    let mut w=World::new();w.setup(2,true);w.detach("two-head-isolation",1);let retained=w.retained_destination();
    reset();let before=w.snapshot();let rc=mem_begin_free_pages_pending_result(&raw mut w.s);w.emit("source-reuse","begin",rc,before);
    assert_eq!(w.retained_destination(),retained);assert_eq!(callbacks(),"[]");
    reset();let before=w.snapshot();let rc=mem_free_pages_pending_enqueue_result(&raw mut w.p[2],&raw mut w.s,7,None);w.emit("source-reuse","enqueue",rc,before);
    assert_eq!(w.retained_destination(),retained);assert_eq!(callbacks(),"[]");
    reset();let before=w.snapshot();let rc=mem_finish_free_pages_pending_result(&raw mut w.s,Some(free_page));w.emit("source-reuse","finish",rc,before);
    assert_eq!(w.retained_destination(),retained);assert_eq!(callbacks(),"[[102,7,1]]");
    w.drain("two-head-isolation",false,true);assert_eq!(callbacks(),"[[100,1,1],[101,2,1]]");
    reset();let before=w.snapshot();let rc=mem_finish_free_pages_pending_result(&raw mut w.t,Some(free_page));w.emit("other-head-finish","finish",rc,before);
}}
