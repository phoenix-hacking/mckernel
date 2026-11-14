// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private UNWIRED real per-executing-Thread ownership. R serializes registry,
// real bitmap changes and publication; no allocator/offload/hardware call under R.
use core::cell::UnsafeCell;
use core::mem::{ManuallyDrop, size_of};
use core::ptr::{addr_of, null_mut, write};
use crate::abi::{CInt,CULong,Process,Thread};
use super::descriptors::Locked;
use super::events::EventPin;
use super::groups::GroupRead;
use super::monitors::ProcessKey;
use super::thread_counters::{CounterSlot,CounterLease,Reservation,LeaseUse,EventKey};

const EINVAL:CInt=22;const ENOMEM:CInt=12;
const FILE:&[u8]=concat!(file!(),"\0").as_bytes();
const BITS:usize=CULong::BITS as usize;
#[derive(Clone,Copy,PartialEq,Eq)]
pub(super) enum Purpose {
    // One real origin lease, not one per inherited descriptor or memory ref.
    Origin,
    // An actual target Process's current selected group; replacing an
    // association with the same group transfers this same semantic ownership.
    Monitor {target:ProcessKey,group:EventKey},
    Call {operation:u64,group:EventKey},
}
impl Purpose { fn use_(self)->LeaseUse { match self { Self::Origin=>LeaseUse::Open,Self::Monitor{..}=>LeaseUse::Monitor,Self::Call{..}=>LeaseUse::Operation } } }

struct ThreadRecord {
    next:*mut ThreadRecord,next_free:*mut ThreadRecord,
    raw:*mut Thread,process:Option<ProcessKey>,generation:u64,references:usize,
    slot:CounterSlot,
}
struct Binding {
    next:*mut Binding,next_free:*mut Binding,
    thread:*mut ThreadRecord,event:Option<EventKey>,purpose:Option<Purpose>,
    token:Option<CounterLease>,closing:bool,
}
struct Registry {
    threads:*mut ThreadRecord,bindings:*mut Binding,generation:u64,transaction:u64,
    free_threads:*mut ThreadRecord,free_bindings:*mut Binding,
}
struct Cell(UnsafeCell<Registry>);unsafe impl Sync for Cell{}
static REGISTRY:Cell=Cell(UnsafeCell::new(Registry {threads:null_mut(),bindings:null_mut(),generation:1,transaction:1,free_threads:null_mut(),free_bindings:null_mut()}));
unsafe fn registry(_r:&mut Locked)->&mut Registry {unsafe{&mut *REGISTRY.0.get()}}
unsafe fn find_thread(raw:*mut Thread,r:&mut Locked)->*mut ThreadRecord {
    let mut row=unsafe{registry(r).threads};
    while !row.is_null() {if unsafe{(*row).raw==raw}{return row;}row=unsafe{(*row).next};}null_mut()
}
unsafe fn retain_thread(row:*mut ThreadRecord)->Result<(),CInt> {
    let n=unsafe{(*row).references}.checked_add(1).ok_or(-EINVAL)?;
    if unsafe{(*row).references}==0{return Err(-EINVAL);}unsafe{(*row).references=n;}Ok(())
}
unsafe fn release_thread(row:*mut ThreadRecord,r:&mut Locked) {
    let n=unsafe{(*row).references}.checked_sub(1).expect("perf Thread record released twice");
    unsafe{(*row).references=n;}
    if n!=0{return;}
    assert!(unsafe{(*row).raw.is_null() && (*row).slot.retired_and_unused()});
    let reg=unsafe{registry(r)};
    unsafe{(*row).next_free=reg.free_threads;reg.free_threads=row;}
}

/// Called at the actual newly zeroed Thread construction before publication.
/// No permanent hold_thread reference: the real pre-free hook invalidates raw.
pub(crate) unsafe fn prepare_thread(raw:*mut Thread,flags:CULong)->Result<(),CInt> {
    if raw.is_null(){return Err(-EINVAL);}
    let row=unsafe{crate::mem_helpers::kmalloc_tracked(size_of::<ThreadRecord>() as CInt,flags,FILE.as_ptr().cast_mut().cast(),line!() as CInt)}.cast::<ThreadRecord>();
    if row.is_null(){return Err(-ENOMEM);}
    let outcome={let mut r=unsafe{Locked::take()};
        if !unsafe{find_thread(raw,&mut r)}.is_null(){Err(-EINVAL)}else{
            let reg=unsafe{registry(&mut r)};
            match reg.generation.checked_add(1){None=>Err(-EINVAL),Some(next)=>{
                let generation=reg.generation;reg.generation=next;
                unsafe{write(row,ThreadRecord{next:reg.threads,next_free:null_mut(),raw,process:None,generation,references:1,slot:CounterSlot::new(raw,generation)});}
                reg.threads=row;Ok(())
            }}
        }
    };
    if outcome.is_err(){unsafe{crate::mem_helpers::kfree_tracked(row.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};}
    outcome
}

/// Final construction revalidation, before a genuine scheduler/hash/list can
/// expose this Thread. The caller has prepared ALL required monitor mappings.
pub(super) unsafe fn bind_thread_locked(raw:*mut Thread,process:ProcessKey,r:&mut Locked)->Result<(),CInt> {
    let row=unsafe{find_thread(raw,r)};
    if row.is_null() || process.address==0 || process.generation==0{return Err(-EINVAL);}
    if let Some(previous)=unsafe{(*row).process}{if previous!=process{return Err(-EINVAL);}}
    unsafe{(*row).process=Some(process);}Ok(())
}

/// Actual page-free hook, including failed constructors. No allocation, hardware,
/// callback or access through raw occurs after the slot's terminal invalidation.
pub(crate) unsafe fn retire_thread_before_destroy(raw:*mut Thread) {
    if raw.is_null(){return;}
    let mut r=unsafe{Locked::take()};let row=unsafe{find_thread(raw,&mut r)};
    if row.is_null(){return;} // Genuine unregistered idle/failed-before-setup path.
    let reg=unsafe{registry(&mut r)};let mut link=&mut reg.threads as *mut *mut ThreadRecord;
    while unsafe{*link}!=row {assert!(!unsafe{*link}.is_null());link=unsafe{&mut (**link).next};}
    unsafe{*link=(*row).next;(*row).slot.retire_before_destroy(raw).expect("actual Thread terminal identity");(*row).raw=null_mut();(*row).process=None;}
    // Detach every publication token while the real map was still invalidated
    // under this same R. Outstanding operation tokens can retire data-only later.
    let mut link=unsafe{&mut registry(&mut r).bindings as *mut *mut Binding};
    while !unsafe{*link}.is_null(){let b=unsafe{*link};if unsafe{(*b).thread==row}{
        unsafe{*link=(*b).next;release_binding(b,&mut r);}
    }else{link=unsafe{&mut (*b).next};}}
    unsafe{release_thread(row,&mut r);}
}

unsafe fn release_binding(binding:*mut Binding,r:&mut Locked){
    let row=unsafe{(*binding).thread};
    let token=unsafe{(*binding).token.take()}.expect("managed binding missing linear lease");
    if let Err((_error,_owned))=unsafe{(*row).slot.release(token)}{panic!("perf binding token identity changed");}
    unsafe{release_thread(row,r);let reg=registry(r);(*binding).next_free=reg.free_bindings;reg.free_bindings=binding;}
}
unsafe fn has_binding(thread:*mut ThreadRecord,event:EventKey,purpose:Purpose,r:&mut Locked)->bool {
    let mut b=unsafe{registry(r).bindings};while !b.is_null(){
        if unsafe{(*b).thread==thread && (*b).event==Some(event) && (*b).purpose==Some(purpose) && !(*b).closing}{return true;}b=unsafe{(*b).next};
    }false
}

/// Each node is allocated outside all locks. Commit links that very stable node
/// into the real registry; no postpublication allocator or fabricated token.
enum PreparedToken{Reserved(Reservation),Retained(CounterLease),Join(*mut Prepared)}
struct Prepared {next:*mut Prepared,binding:*mut Binding,token:Option<PreparedToken>}
pub(super) struct Plan {free:*mut Prepared,used:*mut Prepared,transaction:u64}
impl Plan {
    pub(super) unsafe fn allocate(capacity:usize,flags:CULong)->Result<Self,CInt>{
        let transaction={let mut r=unsafe{Locked::take()};let reg=unsafe{registry(&mut r)};
            let next=reg.transaction.checked_add(1).ok_or(-EINVAL)?;let old=reg.transaction;reg.transaction=next;old};
        let mut plan=Self{free:null_mut(),used:null_mut(),transaction};
        for _ in 0..capacity{
            let p=unsafe{crate::mem_helpers::kmalloc_tracked(size_of::<Prepared>() as CInt,flags,FILE.as_ptr().cast_mut().cast(),line!() as CInt)}.cast::<Prepared>();
            if p.is_null(){return Err(-ENOMEM);}
            let b=unsafe{crate::mem_helpers::kmalloc_tracked(size_of::<Binding>() as CInt,flags,FILE.as_ptr().cast_mut().cast(),line!() as CInt)}.cast::<Binding>();
            if b.is_null(){unsafe{crate::mem_helpers::kfree_tracked(p.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};return Err(-ENOMEM);}
            unsafe{write(b,Binding{next:null_mut(),next_free:null_mut(),thread:null_mut(),event:None,purpose:None,token:None,closing:false});write(p,Prepared{next:plan.free,binding:b,token:None});}plan.free=p;
        }Ok(plan)
    }
    pub(super) unsafe fn grow(&mut self,capacity:usize,flags:CULong)->Result<(),CInt>{
        for _ in 0..capacity {
            let p=unsafe{crate::mem_helpers::kmalloc_tracked(size_of::<Prepared>() as CInt,flags,FILE.as_ptr().cast_mut().cast(),line!() as CInt)}.cast::<Prepared>();
            if p.is_null(){return Err(-ENOMEM);}
            let b=unsafe{crate::mem_helpers::kmalloc_tracked(size_of::<Binding>() as CInt,flags,FILE.as_ptr().cast_mut().cast(),line!() as CInt)}.cast::<Binding>();
            if b.is_null(){unsafe{crate::mem_helpers::kfree_tracked(p.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};return Err(-ENOMEM);}
            unsafe{write(b,Binding{next:null_mut(),next_free:null_mut(),thread:null_mut(),event:None,purpose:None,token:None,closing:false});write(p,Prepared{next:self.free,binding:b,token:None});}self.free=p;
        }Ok(())
    }
    /// Number of potential real Thread/event pairs; caller allocates this
    /// capacity outside R, then retries only preparation if concurrent setup
    /// increased the count. No host call or published work is replayed.
    pub(super) unsafe fn thread_count_locked(process:Option<ProcessKey>,r:&mut Locked)->usize{
        let mut row=unsafe{registry(r).threads};let mut n=0usize;
        while !row.is_null(){if process.is_none() || unsafe{(*row).process}==process{n=n.checked_add(1).expect("perf Thread count overflow");}row=unsafe{(*row).next};}n
    }
    unsafe fn add_locked(&mut self,row:*mut ThreadRecord,event:EventKey,purpose:Purpose,counters:CInt,r:&mut Locked)->Result<(),CInt>{
        if unsafe{has_binding(row,event,purpose,r)}{return Ok(());}
        let mut old=self.used;let mut shared=null_mut();
        while !old.is_null(){let b=unsafe{(*old).binding};
            if unsafe{(*b).thread==row && (*b).event==Some(event)}{
                if unsafe{(*b).purpose==Some(purpose)}{return Ok(());}shared=old;
            }old=unsafe{(*old).next};}
        if self.free.is_null(){return Err(-ENOMEM);}
        let token=if !shared.is_null(){PreparedToken::Join(shared)}else{
            match unsafe{(*row).slot.retain(event,purpose.use_())}{Ok(lease)=>PreparedToken::Retained(lease),Err(_)=>{
                PreparedToken::Reserved(unsafe{(*row).slot.reserve(event,self.transaction,counters)?})
            }}
        };
        // Retain cannot fail after moving a slot token without dropping it. Do
        // the refcount capacity check first in this same R window.
        if unsafe{(*row).references}==usize::MAX{
            match token{PreparedToken::Reserved(reservation)=>{let _=unsafe{(*row).slot.rollback(reservation)};},PreparedToken::Retained(lease)=>{let _=unsafe{(*row).slot.release(lease)};},PreparedToken::Join(_)=>{}}
            return Err(-EINVAL);
        }
        unsafe{retain_thread(row).expect("prevalidated Thread ref");}
        let p=self.free;self.free=unsafe{(*p).next};let b=unsafe{(*p).binding};
        unsafe{(*b).thread=row;(*b).event=Some(event);(*b).purpose=Some(purpose);(*p).token=Some(token);(*p).next=self.used;}self.used=p;Ok(())
    }
    pub(super) fn transaction(&self)->u64{self.transaction}
    pub(super) unsafe fn call_one_locked(&mut self,thread:*mut Thread,event:EventKey,group:EventKey,counters:CInt,r:&mut Locked)->Result<(),CInt>{
        let row=unsafe{find_thread(thread,r)};if row.is_null(){return Err(-EINVAL);}
        unsafe{self.add_locked(row,event,Purpose::Call{operation:self.transaction,group},counters,r)}
    }
    pub(super) unsafe fn call_group_locked(&mut self,thread:*mut Thread,group:&mut GroupRead<'_>,group_key:EventKey,counters:CInt,r:&mut Locked)->Result<(),CInt>{
        let row=unsafe{find_thread(thread,r)};if row.is_null(){return Err(-EINVAL);}
        while let Some(event)=unsafe{group.next_locked(r)}{unsafe{self.add_locked(row,event.key(),Purpose::Call{operation:self.transaction,group:group_key},counters,r)?;}}
        Ok(())
    }
    pub(super) unsafe fn origin_locked(&mut self,thread:*mut Thread,event:&EventPin,counters:CInt,r:&mut Locked)->Result<(),CInt>{
        let row=unsafe{find_thread(thread,r)};if row.is_null(){return Err(-EINVAL);}
        unsafe{self.add_locked(row,event.key(),Purpose::Origin,counters,r)}
    }
    pub(super) unsafe fn monitor_locked(&mut self,target:ProcessKey,group:&mut GroupRead<'_>,group_key:EventKey,counters:CInt,r:&mut Locked)->Result<(),CInt>{
        while let Some(event)=unsafe{group.next_locked(r)}{
            let mut row=unsafe{registry(r).threads};while !row.is_null(){let next=unsafe{(*row).next};
                if unsafe{(*row).process}==Some(target){unsafe{self.add_locked(row,event.key(),Purpose::Monitor{target,group:group_key},counters,r)?;}}row=next;
            }
        }Ok(())
    }
    pub(super) unsafe fn new_thread_monitor_locked(&mut self,thread:*mut Thread,target:ProcessKey,group:&mut GroupRead<'_>,group_key:EventKey,counters:CInt,r:&mut Locked)->Result<(),CInt>{
        let row=unsafe{find_thread(thread,r)};if row.is_null(){return Err(-EINVAL);}
        while let Some(event)=unsafe{group.next_locked(r)}{unsafe{self.add_locked(row,event.key(),Purpose::Monitor{target,group:group_key},counters,r)?;}}
        Ok(())
    }
    /// Appending an event reserves its actual mapping for every current monitored
    /// Thread of this group, including a monitor/fork added during host offload.
    pub(super) unsafe fn group_append_locked(&mut self,group:EventKey,event:&EventPin,counters:CInt,r:&mut Locked)->Result<(),CInt>{
        let mut b=unsafe{registry(r).bindings};while !b.is_null(){let next=unsafe{(*b).next};
            if let Some(Purpose::Monitor{target,group:actual})=unsafe{(*b).purpose}{
                if actual==group && !unsafe{(*b).closing} && unsafe{super::process_targets::current_group_locked(target,group,r)}{unsafe{self.add_locked((*b).thread,event.key(),Purpose::Monitor{target,group},counters,r)?;}}
            }b=next;
        }Ok(())
    }
    pub(super) unsafe fn origin_index_locked(&self,r:&mut Locked)->Option<CInt>{
        let mut p=self.used;while !p.is_null(){let b=unsafe{(*p).binding};if unsafe{(*b).purpose}==Some(Purpose::Origin){
            return match unsafe{(*p).token.as_ref()}?{PreparedToken::Reserved(token)=>Some(token.index()),PreparedToken::Retained(token)=>Some(token.index()),PreparedToken::Join(other)=>match unsafe{(**other).token.as_ref()}?{PreparedToken::Reserved(token)=>Some(token.index()),PreparedToken::Retained(token)=>Some(token.index()),_=>None}};
        }p=unsafe{(*p).next};}let _=r;None
    }
    /// Validate in the SAME final R window as commit; no source lock is held
    /// over offload, so a Thread retired during it causes actual rollback.
    pub(super) unsafe fn validate_locked(&self,_r:&mut Locked)->Result<(),CInt>{
        let mut p=self.used;while !p.is_null(){let b=unsafe{(*p).binding};if unsafe{(*(*b).thread).raw.is_null()}{return Err(-EINVAL);}p=unsafe{(*p).next};}Ok(())
    }
    pub(super) unsafe fn commit_locked(&mut self,r:&mut Locked){
        // Reserved rows must commit before Join tokens retain them. Two passes
        // avoid depending on the reversed linked preparation order.
        for joins in [false,true]{let mut p=self.used;while !p.is_null(){let b=unsafe{(*p).binding};
            let is_join=matches!(unsafe{(*p).token.as_ref()},Some(PreparedToken::Join(_)));
            if is_join==joins {if let Some(token)=unsafe{(*p).token.take()}{
                let row=unsafe{(*b).thread};let kind=unsafe{(*b).purpose.unwrap()}.use_();
                let lease=match token{PreparedToken::Reserved(reservation)=>match unsafe{(*row).slot.commit(reservation,kind)}{Ok(lease)=>lease,Err(_)=>panic!("prevalidated perf reservation changed")},PreparedToken::Retained(lease)=>lease,PreparedToken::Join(_)=>unsafe{(*row).slot.retain((*b).event.unwrap(),kind)}.expect("committed shared perf reservation")};
                unsafe{(*b).token=Some(lease);let reg=registry(r);(*b).next=reg.bindings;reg.bindings=b;(*p).binding=null_mut();}
            }}p=unsafe{(*p).next};}}
        // Thread metadata references move to published Binding records.
    }
    unsafe fn abort_locked(&mut self,r:&mut Locked){
        let mut p=self.used;while !p.is_null(){let b=unsafe{(*p).binding};if !b.is_null(){
            if let Some(token)=unsafe{(*p).token.take()}{let row=unsafe{(*b).thread};
                match token{PreparedToken::Reserved(reservation)=>{if unsafe{(*row).slot.rollback(reservation)}.is_err(){panic!("perf reservation rollback identity");}},PreparedToken::Retained(lease)=>{if unsafe{(*row).slot.release(lease)}.is_err(){panic!("perf retained rollback identity");}},PreparedToken::Join(_)=>{}}
                unsafe{release_thread(row,r);}
            }
        }p=unsafe{(*p).next};}
    }
}
impl Drop for Plan{fn drop(&mut self){
    {let mut r=unsafe{Locked::take()};unsafe{self.abort_locked(&mut r);}}
    for mut p in [self.free,self.used]{while !p.is_null(){let next=unsafe{(*p).next};unsafe{
        if !(*p).binding.is_null(){crate::mem_helpers::kfree_tracked((*p).binding.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt);}
        crate::mem_helpers::kfree_tracked(p.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt);
    }p=next;}}
}}

/// No allocation/failure in the IRQ/exit path: all actual mappings were prepared
/// by setup. Width is the real CULong hardware-mask width, not an event quota.
pub(super) struct HardwareLeases {leases:[Option<Operation>;BITS],used:usize}
struct Operation {thread:*mut ThreadRecord,lease:Option<CounterLease>,event:EventKey}
impl HardwareLeases{
    pub(super) unsafe fn capture_one_locked(thread:*mut Thread,event:EventKey,r:&mut Locked)->Result<Self,CInt>{
        let row=unsafe{find_thread(thread,r)};if row.is_null(){return Err(-EINVAL);}
        unsafe{retain_thread(row)?;}
        let lease=match unsafe{(*row).slot.retain(event,LeaseUse::Operation)}{Ok(lease)=>lease,Err(error)=>{unsafe{release_thread(row,r);}return Err(error);}};
        let mut result=Self{leases:[const{None};BITS],used:1};
        result.leases[0]=Some(Operation{thread:row,lease:Some(lease),event});Ok(result)
    }
    pub(super) unsafe fn capture_locked(thread:*mut Thread,group:&mut GroupRead<'_>,r:&mut Locked)->Result<Self,CInt>{
        let row=unsafe{find_thread(thread,r)};if row.is_null(){return Err(-EINVAL);}
        let mut result=Self{leases:[const{None};BITS],used:0};
        while let Some(event)=unsafe{group.next_locked(r)}{
            if result.used==BITS{unsafe{result.release_locked(r);}return Err(-EINVAL);}
            if let Err(error)=unsafe{retain_thread(row)}{unsafe{result.release_locked(r);}return Err(error);}
            let lease=match unsafe{(*row).slot.retain(event.key(),LeaseUse::Operation)}{Ok(lease)=>lease,Err(error)=>{
                unsafe{release_thread(row,r);result.release_locked(r);}return Err(error);
            }};
            result.leases[result.used]=Some(Operation{thread:row,lease:Some(lease),event:event.key()});result.used+=1;
        }Ok(result)
    }
    pub(super) fn index(&self,event:EventKey)->CInt{
        for op in self.leases.iter().take(self.used).flatten(){if op.event==event{return op.lease.as_ref().unwrap().index();}}
        panic!("perf hardware operation missing prebound actual Thread lease")
    }
    pub(super) unsafe fn runtime(&self,event:EventKey)->*mut super::runtime::LocalRuntime{
        for op in self.leases.iter().take(self.used).flatten(){if op.event==event{return unsafe{(*op.thread).slot.runtime(op.lease.as_ref().unwrap())};}}
        panic!("perf runtime missing actual Operation token")
    }
    pub(super) unsafe fn reserve_extra(&self,event:EventKey,preferred:CInt)->Result<(CInt,bool),CInt>{
        let _r=unsafe{Locked::take()};
        for op in self.leases.iter().take(self.used).flatten(){if op.event==event{return unsafe{(*op.thread).slot.reserve_extra(op.lease.as_ref().unwrap(),preferred)};}}
        Err(-EINVAL)
    }
    pub(super) unsafe fn abort_new_extra(&self,event:EventKey,index:CInt){
        let _r=unsafe{Locked::take()};
        for op in self.leases.iter().take(self.used).flatten(){if op.event==event{unsafe{(*op.thread).slot.abort_new_extra(op.lease.as_ref().unwrap(),index)};return;}}
        panic!("perf extra rollback missing actual Operation token")
    }
    pub(super) fn translated_mask(&self,logical:CULong,event:EventKey,creation:CInt)->CULong{
        if creation<0 || creation>=CULong::BITS as CInt || logical&(1u64<<creation)==0{0}else{1u64<<self.index(event)}
    }
    pub(super) unsafe fn release_locked(&mut self,r:&mut Locked){
        for item in self.leases.iter_mut().take(self.used){if let Some(mut op)=item.take(){
            let lease=op.lease.take().unwrap();if unsafe{(*op.thread).slot.release(lease)}.is_err(){panic!("perf operation token identity");}
            unsafe{release_thread(op.thread,r);}
        }}self.used=0;
    }
}
impl Drop for HardwareLeases{fn drop(&mut self){if self.used==0{return;}let mut r=unsafe{Locked::take()};unsafe{self.release_locked(&mut r);}}}

/// Called only by the actual last descriptor-storage retirement. It consumes
/// Origin tokens only; inherited monitors and in-flight operations own distinct
/// tokens. No Event-memory-refcount or measured counter is used as liveness.
pub(super) unsafe fn retire_origin(event:EventKey){unsafe{retire_matching(|b|(*b).event==Some(event)&&(*b).purpose==Some(Purpose::Origin));}}
/// Exact group callback after old epochs drained; nested own subgroup E and
/// containing group L have different keys and cannot release each other's maps.
pub(super) unsafe fn retire_group(group:EventKey,event:EventKey){unsafe{retire_matching(|b|{
    (*b).event==Some(event)&&matches!((*b).purpose,Some(Purpose::Monitor{group:actual,..})if actual==group)
});}}
/// Real event-final fallback consumes only registered linear tokens. Event keys
/// are compared, never dereferenced after actual event storage has been freed.
pub(super) unsafe fn retire_event(event:EventKey){unsafe{retire_matching(|b|(*b).event==Some(event));}}
unsafe fn retire_matching<F:Fn(*mut Binding)->bool>(matches:F){
    let mut r=unsafe{Locked::take()};let mut link=unsafe{&mut registry(&mut r).bindings as *mut *mut Binding};
    while !unsafe{*link}.is_null(){let b=unsafe{*link};if matches(b){unsafe{*link=(*b).next;release_binding(b,&mut r);}}else{link=unsafe{&mut (*b).next};}}
}
/// Refresh from the real current target association. Old operation tokens keep
/// their exact map bits alive after a cleared/replaced association is retired.
pub(super) unsafe fn reconcile_monitors_locked<F:FnMut(ProcessKey,EventKey,&mut Locked)->bool>(mut live:F,r:&mut Locked){
    let mut link=unsafe{&mut registry(r).bindings as *mut *mut Binding};
    while !unsafe{*link}.is_null(){let b=unsafe{*link};let valid=match unsafe{(*b).purpose}{Some(Purpose::Monitor{target,group})=>live(target,group,r),_=>true};
        if !valid{unsafe{*link=(*b).next;release_binding(b,r);}}else{link=unsafe{&mut (*b).next};}
    }
}
pub(super) unsafe fn drain_deferred(){
    let (mut bindings,mut threads)={let mut r=unsafe{Locked::take()};let reg=unsafe{registry(&mut r)};let result=(reg.free_bindings,reg.free_threads);reg.free_bindings=null_mut();reg.free_threads=null_mut();result};
    while !bindings.is_null(){let next=unsafe{(*bindings).next_free};unsafe{crate::mem_helpers::kfree_tracked(bindings.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};bindings=next;}
    while !threads.is_null(){let next=unsafe{(*threads).next_free};unsafe{crate::mem_helpers::kfree_tracked(threads.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};threads=next;}
}

pub(super) unsafe fn retire_call(operation:u64){unsafe{retire_matching(|b|matches!((*b).purpose,Some(Purpose::Call{operation:actual,..})if actual==operation));}}
pub(super) struct CallScope{operation:u64}
impl CallScope{pub(super) fn new(plan:&Plan)->Self{Self{operation:plan.transaction()}}}
impl Drop for CallScope{fn drop(&mut self){unsafe{retire_call(self.operation);}}}
