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
static PANIC_BRIDGE: AtomicUsize = AtomicUsize::new(0);
unsafe extern "C" fn panic_bridge() { PANIC_BRIDGE.fetch_add(1, Ordering::SeqCst); }
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
fn reset() { LEDGER.with(|c| { let mut l=c.borrow_mut(); l.used=0; l.limit=32; }); CALLBACK_ERROR.with(|c|c.set(0)); PANIC_BRIDGE.store(0, Ordering::SeqCst); assert_eq!(TLS_ERROR.load(Ordering::SeqCst),0); }
fn callbacks() -> String { LEDGER.with(|c| { let l=c.borrow(); let v:Vec<String>=l.entries[..l.used].iter().map(|x|format!("[{},{},{}]",x.0,x.1,x.2)).collect(); format!("[{}]",v.join(",")) }) }
fn callback_controls() { reset(); LEDGER.with(|c| { let _held=c.borrow_mut(); unsafe { free_page(1,1,1); } }); assert_eq!(CALLBACK_ERROR.with(Cell::get),1); reset(); LEDGER.with(|c|c.borrow_mut().limit=0); unsafe { free_page(1,1,1); } assert_eq!(CALLBACK_ERROR.with(Cell::get),2); reset(); println!("CONTROL|callback-borrow-and-capacity-observed"); }
static mut DISPATCH_PAGE:*mut MemPage=null_mut();
unsafe extern "C" fn fixture_virt_to_phys(_: *mut c_void)->CULong {0xfeed}
unsafe extern "C" fn fixture_phys_to_page(_: CULong)->*mut MemPage {DISPATCH_PAGE}
unsafe extern "C" fn fixture_immediate_free(va:*mut c_void,npages:CInt,is_user:CInt){free_page(va as CULong,npages,is_user)}
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
    unsafe fn emit(&self,name:&str,op:&str,rc:i32,before:String){let after=self.snapshot();let cb=callbacks();let panic=PANIC_BRIDGE.load(Ordering::SeqCst);println!("JSON|{{\"case\":\"{}\",\"op\":\"{}\",\"rc\":{},\"panic\":{},\"before\":{},\"after\":{},\"callbacks\":{}}}",name,op,rc,panic,before,after,cb);assert_eq!(CALLBACK_ERROR.with(Cell::get),0);assert_eq!(TLS_ERROR.load(Ordering::SeqCst),0);if rc<0 {assert!(before==after && cb=="[]","PARTIAL_RELEASE_DETECTED case={}",name)} }
    unsafe fn detach(&mut self,name:&str,src:usize){reset();let before=self.snapshot();let s=match src{0=>null_mut(),3=>&raw mut self.b.as_mut().get_unchecked_mut().head,_=>&raw mut self.s};let rc=detach_pending_free_batch(s,self.b.as_mut());self.emit(name,"detach",rc,before)}
    unsafe fn drain(&mut self,name:&str,wrong:bool,callback:bool){reset();let before=self.snapshot();let s=if wrong{&raw mut self.t}else{&raw mut self.s};let rc=drain_pending_free_batch(s,self.b.as_mut(),if callback{Some(free_page)}else{None});self.emit(name,"drain",rc,before)}
    unsafe fn begin(&mut self,name:&str){reset();let before=self.snapshot();let rc=mem_begin_free_pages_pending_result(&raw mut self.s);self.emit(name,"begin",rc,before)}
    unsafe fn begin_body(&mut self,name:&str){reset();let before=self.snapshot();let rc=mem_begin_free_pages_pending_body_result(&raw mut self.s,Some(mem_begin_free_pages_pending_result),Some(panic_bridge));self.emit(name,"begin-body",rc,before)}
    unsafe fn malformed(&mut self,name:&str,boundary:usize){reset();if boundary==0 {self.setup(0,false);self.s.prev=null_mut()} else {self.setup(2,false);if boundary==1 {self.p[0].list.prev=&raw mut self.t} else {self.p[1].list.next=&raw mut self.t}}let before=self.snapshot();let rc=detach_pending_free_batch(&raw mut self.s,self.b.as_mut());self.emit(name,"detach",rc,before)}
}

/* M03 source-only actual-layout controls.  They exercise the unwired private
 * inventory lease instead of changing the released finish helper.  Layer-B
 * owns compilation/execution; this fixture remains finite and source-bound. */
unsafe fn validated_inventory_controls() {
    let bounds=PendingPhysicalBounds{start:0x1000,end:0x9000};
    for n in [0usize,1,3] {
        let mut w=World::new();w.setup(n,false);
        for i in 0..n {w.p[i].phys=0x1000+(i as u64)*0x2000;}
        let mut descriptors=[null_mut();4];for i in 0..n {descriptors[i]=&raw mut w.p[i];}
        let mut captured=[PendingFreeCallbackArgs{phys:0,npages:0};4];
        let lease=PendingInventoryLease::new(&mut descriptors[..n],&mut captured,bounds);
        let token=validate_pending_inventory(&raw mut w.s,lease).expect("actual-layout inventory");
        token.reanchor_into(w.b.as_mut());
        reset();assert_eq!(drain_validated_pending_inventory(w.b.as_mut(),Some(free_page)),n as i32);
        assert_eq!(callbacks(),match n {0=>"[]",1=>"[[4096,1,1]]",_=>"[[4096,1,1],[12288,2,1],[20480,3,1]]"});
    }

    /* Source reuse stays independent of the retained old head. */
    let mut w=World::new();w.setup(2,false);w.p[0].phys=0x1000;w.p[1].phys=0x3000;
    let mut descriptors=[&raw mut w.p[0],&raw mut w.p[1]];
    let mut captured=[PendingFreeCallbackArgs{phys:0,npages:0};2];
    let lease=PendingInventoryLease::new(&mut descriptors,&mut captured,bounds);
    validate_pending_inventory(&raw mut w.s,lease).unwrap().reanchor_into(w.b.as_mut());
    let retained=w.retained_destination();
    assert_eq!(mem_begin_free_pages_pending_result(&raw mut w.s),0);
    assert_eq!(mem_free_pages_pending_enqueue_result(&raw mut w.p[2],&raw mut w.s,1,None),1);
    assert_eq!(w.retained_destination(),retained);
    reset();assert_eq!(mem_finish_free_pages_pending_result(&raw mut w.s,Some(free_page)),1);assert_eq!(callbacks(),"[[102,1,1]]");
    reset();
    assert_eq!(drain_validated_pending_inventory(w.b.as_mut(),Some(free_page)),2);
    assert_eq!(callbacks(),"[[4096,1,1],[12288,2,1]]");

    /* Missing/extra/duplicate/foreign membership and reciprocal-link faults
     * are admission failures and produce no allocator callback. */
    for case in ["missing","extra","duplicate","foreign","link"] {
        let mut w=World::new();w.setup(2,false);w.p[0].phys=0x1000;w.p[1].phys=0x3000;
        let mut descriptors=[&raw mut w.p[0],&raw mut w.p[1],&raw mut w.p[2]];
        let mut captured=[PendingFreeCallbackArgs{phys:0,npages:0};3];
        match case {
            "missing"=>{descriptors[1]=descriptors[0];descriptors[2]=descriptors[0];},
            "extra"=>{descriptors[2]=&raw mut w.p[2];w.p[2].mode=PM_PENDING_FREE;w.p[2].phys=0x5000;w.p[2].offset=1;},
            "duplicate"=>descriptors[1]=descriptors[0],
            "foreign"=>w.p[1].list.next=&raw mut w.t,
            _=>w.p[1].list.prev=&raw mut w.t,
        }
        let descriptor_len=if case=="missing" {1} else if case=="extra" {3} else {2};
        reset();let before=w.snapshot();let captured_before=captured;let lease=PendingInventoryLease::new(&mut descriptors[..descriptor_len],&mut captured,bounds);
        assert!(validate_pending_inventory(&raw mut w.s,lease).is_err(),"{case}");assert_eq!(w.snapshot(),before,"{case}");assert_eq!(captured,captured_before,"{case}");assert_eq!(callbacks(),"[]");
    }

    for case in ["mode","negative-count","count","alignment","range","end-overflow","overlap"] {
        let mut w=World::new();w.setup(2,false);w.p[0].phys=0x1000;w.p[1].phys=0x3000;
        let mut descriptors=[&raw mut w.p[0],&raw mut w.p[1]];
        let mut captured=[PendingFreeCallbackArgs{phys:0,npages:0};2];
        match case {
            "mode"=>w.p[1].mode=PM_NONE,
            "negative-count"=>w.p[1].offset=-1,
            "count"=>w.p[1].offset=CInt::MAX as OffT+1,
            "alignment"=>w.p[1].phys=0x3001,
            "range"=>w.p[1].phys=0x9000,
            "end-overflow"=>{w.p[1].phys=CULong::MAX&!(PAGE_SIZE-1);},
            _=>w.p[1].phys=0x1000,
        }
        let case_bounds=if case=="end-overflow" {PendingPhysicalBounds{start:0,end:CULong::MAX&!(PAGE_SIZE-1)}} else {bounds};
        reset();let before=w.snapshot();let captured_before=captured;let lease=PendingInventoryLease::new(&mut descriptors,&mut captured,case_bounds);
        assert!(validate_pending_inventory(&raw mut w.s,lease).is_err(),"{case}");assert_eq!(w.snapshot(),before,"{case}");assert_eq!(captured,captured_before,"{case}");assert_eq!(callbacks(),"[]");
    }

    /* Capacity and representability are rejected before descriptor traversal. */
    let mut w=World::new();w.setup(1,false);w.p[0].phys=0x1000;
    let mut descriptors=[&raw mut w.p[0]];let mut short=[PendingFreeCallbackArgs{phys:0,npages:0};0];
    let before=w.snapshot();let lease=PendingInventoryLease::new(&mut descriptors,&mut short,bounds);
    assert!(validate_pending_inventory(&raw mut w.s,lease).is_err());assert_eq!(w.snapshot(),before);assert_eq!(short,[]);
    let mut captured=[PendingFreeCallbackArgs{phys:0,npages:0};1];let lease=PendingInventoryLease::new(&mut descriptors,&mut captured,bounds);
    let mut oversized=lease;oversized.descriptor_len=CInt::MAX as usize+1;oversized.callback_len=CInt::MAX as usize+1;
    let before=w.snapshot();let captured_before=captured;assert!(validate_pending_inventory(&raw mut w.s,oversized).is_err());assert_eq!(w.snapshot(),before);assert_eq!(captured,captured_before);
    /* `validate_pending_inventory_ring` is the bounded cardinality phase.  It
     * rejects an empty source with one inaccessible supplied descriptor before
     * inspecting that descriptor; this direct fixture is safe to execute. */
    let mut inaccessible=[1usize as *mut MemPage];let mut capture_one=[PendingFreeCallbackArgs{phys:0,npages:0};1];let lease=PendingInventoryLease::new(&mut inaccessible,&mut capture_one,bounds);
    let mut empty=head();init_list_head(&raw mut empty);assert_eq!(validate_pending_inventory_ring(&raw mut empty,&lease),Err(-EINVAL));assert_eq!(capture_one,[PendingFreeCallbackArgs{phys:0,npages:0};1]);

    /* A later-invalid retained descriptor is rejected before dispatch; repairing
     * it restores the exact two-argument callback order. */
    let mut w=World::new();w.setup(2,false);w.p[0].phys=0x1000;w.p[1].phys=0x3000;
    let mut descriptors=[&raw mut w.p[0],&raw mut w.p[1]];let mut captured=[PendingFreeCallbackArgs{phys:0,npages:0};2];
    let lease=PendingInventoryLease::new(&mut descriptors,&mut captured,bounds);validate_pending_inventory(&raw mut w.s,lease).unwrap().reanchor_into(w.b.as_mut());
    w.p[1].mode=PM_NONE;reset();let before=w.snapshot();let captured_before=captured;assert_eq!(drain_validated_pending_inventory(w.b.as_mut(),Some(free_page)),-EINVAL);assert_eq!(w.snapshot(),before);assert_eq!(captured,captured_before);assert_eq!(callbacks(),"[]");
    w.p[1].mode=PM_PENDING_FREE;assert_eq!(drain_validated_pending_inventory(w.b.as_mut(),Some(free_page)),2);assert_eq!(callbacks(),"[[4096,1,1],[12288,2,1]]");

    /* Separate retained batches preserve independent heads and callback order. */
    let mut left=World::new();let mut right=World::new();left.setup(1,false);right.setup(1,false);left.p[0].phys=0x1000;right.p[0].phys=0x3000;
    let mut left_d=[&raw mut left.p[0]];let mut right_d=[&raw mut right.p[0]];let mut left_c=[PendingFreeCallbackArgs{phys:0,npages:0};1];let mut right_c=[PendingFreeCallbackArgs{phys:0,npages:0};1];
    validate_pending_inventory(&raw mut left.s,PendingInventoryLease::new(&mut left_d,&mut left_c,bounds)).unwrap().reanchor_into(left.b.as_mut());
    validate_pending_inventory(&raw mut right.s,PendingInventoryLease::new(&mut right_d,&mut right_c,bounds)).unwrap().reanchor_into(right.b.as_mut());
    reset();assert_eq!(drain_validated_pending_inventory(right.b.as_mut(),Some(free_page)),1);assert_eq!(callbacks(),"[[12288,1,1]]");reset();assert_eq!(drain_validated_pending_inventory(left.b.as_mut(),Some(free_page)),1);assert_eq!(callbacks(),"[[4096,1,1]]");

    /* Invalid destination, repeat drain, and callback absence are preflight
     * failures; all three retain the validated batch unchanged. */
    let mut w=World::new();w.setup(1,false);w.p[0].phys=0x1000;
    let mut descriptors=[&raw mut w.p[0]];let mut captured=[PendingFreeCallbackArgs{phys:0,npages:0};1];
    let lease=PendingInventoryLease::new(&mut descriptors,&mut captured,bounds);
    let token=validate_pending_inventory(&raw mut w.s,lease).unwrap();
    w.b.as_mut().get_unchecked_mut().state=PendingFreeBatchState::Retained;
    reset();let invalid_before=w.snapshot();let captured_before=captured;
    let token=token.try_reanchor_into(w.b.as_mut()).expect_err("destination");assert_eq!(w.snapshot(),invalid_before);assert_eq!(captured,captured_before);assert_eq!(callbacks(),"[]");
    w.b.as_mut().get_unchecked_mut().state=PendingFreeBatchState::Vacant;
    token.reanchor_into(w.b.as_mut());
    reset();let before=w.snapshot();assert_eq!(drain_validated_pending_inventory(w.b.as_mut(),None),-EINVAL);assert_eq!(w.snapshot(),before);assert_eq!(callbacks(),"[]");
    w.p[0].mode=PM_NONE;let before=w.snapshot();assert_eq!(drain_validated_pending_inventory(w.b.as_mut(),Some(free_page)),-EINVAL);assert_eq!(w.snapshot(),before);assert_eq!(callbacks(),"[]");
    w.p[0].mode=PM_PENDING_FREE;assert_eq!(drain_validated_pending_inventory(w.b.as_mut(),Some(free_page)),1);reset();let repeated_before=w.snapshot();let captured_before=captured;assert_eq!(drain_validated_pending_inventory(w.b.as_mut(),Some(free_page)),-EINVAL);assert_eq!(w.snapshot(),repeated_before);assert_eq!(captured,captured_before);assert_eq!(callbacks(),"[]");
}
unsafe fn free_dispatch_controls(){
    let mut w=World::new();w.setup(0,false);DISPATCH_PAGE=&raw mut w.p[0];
    let before=w.snapshot();reset();assert_eq!(mem_mckernel_free_pages_body_result(0xfeedusize as *mut c_void,2,1,&raw mut w.s,Some(fixture_virt_to_phys),Some(fixture_phys_to_page),Some(fixture_immediate_free),None),1);assert_eq!(callbacks(),"[]");assert_eq!(w.p[0].mode,PM_PENDING_FREE);assert_ne!(w.snapshot(),before);assert_eq!(w.p[0].offset,2);
    let mut w=World::new();DISPATCH_PAGE=&raw mut w.p[0];let before=w.snapshot();reset();assert_eq!(mem_mckernel_free_pages_body_result(0xfeedusize as *mut c_void,2,1,&raw mut w.s,Some(fixture_virt_to_phys),Some(fixture_phys_to_page),Some(fixture_immediate_free),None),0);assert_eq!(w.snapshot(),before);assert_eq!(callbacks(),"[[65261,2,1]]");
}
fn main(){unsafe{
    assert_eq!(core::mem::offset_of!(MemPage,list),0);assert_eq!(core::mem::size_of::<MemPage>(),80);
    callback_controls();
    free_dispatch_controls();
    validated_inventory_controls();
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
    let mut w=World::new();w.setup(1,false);w.begin("conflicting-begin");
    let mut w=World::new();w.begin("nested-begin-first");w.begin("nested-begin-second");
    let mut w=World::new();w.setup(1,false);w.begin_body("begin-panic-bridge");
    let mut w=World::new();w.malformed("malformed-active-empty",0);
    let mut w=World::new();w.malformed("malformed-boundary-prev",1);
    let mut w=World::new();w.malformed("malformed-boundary-next",2);
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
