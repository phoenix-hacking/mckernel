#![allow(dead_code)]
use std::ptr;
use std::sync::atomic::{AtomicPtr,AtomicU32,AtomicU64,Ordering};
use std::sync::{Mutex,OnceLock};
use std::mem::offset_of;
mod kernel {
    pub mod error {
        #[derive(Clone, Copy, Debug, Eq, PartialEq)]
        pub struct Error(i32);
        pub type Result<T = ()> = core::result::Result<T, Error>;
        impl Error {
            pub const fn from_errno(errno: i32) -> Self { Self(errno) }
            pub const fn to_errno(self) -> i32 { self.0 }
        }
        pub fn to_result(ret: i32) -> Result {
            if ret < 0 { Err(Error::from_errno(ret)) } else { Ok(()) }
        }
    }
}
use kernel::error::{Error, Result};
const EBUSY:Error=Error::from_errno(-16); const EINVAL:Error=Error::from_errno(-22);
const ENODEV:Error=Error::from_errno(-19); const EIO:Error=Error::from_errno(-5); const ESTALE:i32=116;
const BOOT_IRQ_LIVE:u32=1; const BOOT_IRQ_CLOSING:u32=2; const BOOT_IRQ_DRAINED:u32=3; const BOOT_IRQ_QUARANTINED:u32=4; const SMP_MAX_CPUS:usize=64;
static BOOT_IRQ_PHASE:[AtomicU32;SMP_MAX_CPUS]=[const{AtomicU32::new(0)};SMP_MAX_CPUS];
static BOOT_IRQ_GENERATIONS:[AtomicU64;SMP_MAX_CPUS]=[const{AtomicU64::new(0)};SMP_MAX_CPUS];
static BOOT_IRQ_EVENTS:[AtomicU64;SMP_MAX_CPUS]=[const{AtomicU64::new(0)};SMP_MAX_CPUS];
static BOOT_IRQ_INFLIGHT:[AtomicU32;SMP_MAX_CPUS]=[const{AtomicU32::new(0)};SMP_MAX_CPUS];
static FORCE_GENERATION_CAS_FAILURE:AtomicU32=AtomicU32::new(0);
struct TestAtomicPtr<T>{inner:AtomicPtr<T>}
impl<T> TestAtomicPtr<T>{
    const fn new(value:*mut T)->Self{Self{inner:AtomicPtr::new(value)}}
    fn load(&self,order:Ordering)->*mut T{self.inner.load(order)}
    fn store(&self,value:*mut T,order:Ordering){self.inner.store(value,order)}
    fn compare_exchange(&self,current:*mut T,new:*mut T,success:Ordering,failure:Ordering)->std::result::Result<*mut T,*mut T>{
        let result=self.inner.compare_exchange(current,new,success,failure);
        if !current.is_null() && new.is_null() && result.is_ok(){trace(Event::MasterRemoved);}
        if FORCE_GENERATION_CAS_FAILURE.load(Ordering::Acquire)!=0 && !current.is_null() && new.is_null() && result.is_ok(){BOOT_IRQ_GENERATIONS[6].store(15,Ordering::Release);}
        result
    }
}
static BOOT_MASTER:[TestAtomicPtr<smp_ikc::BootMaster>;SMP_MAX_CPUS]=[const{TestAtomicPtr::new(ptr::null_mut())};SMP_MAX_CPUS];
struct TargetUsers(AtomicU32);
impl TargetUsers {
    fn load(&self,o:Ordering)->u32{self.0.load(o)}
    fn store(&self,v:u32,o:Ordering){self.0.store(v,o)}
    fn fetch_add(&self,v:u32,o:Ordering)->u32{self.0.fetch_add(v,o)}
    fn fetch_sub(&self,v:u32,o:Ordering)->u32{let old=self.0.fetch_sub(v,o);trace(Event::TargetDecrement);old}
}
static BOOT_IRQ_TARGET_USERS:TargetUsers=TargetUsers(AtomicU32::new(0));
static EVENTS:OnceLock<Mutex<Vec<&'static str>>>=OnceLock::new();
fn events()->&'static Mutex<Vec<&'static str>>{EVENTS.get_or_init(||Mutex::new(Vec::new()))}
fn reset(){reset_observer();FORCE_GENERATION_CAS_FAILURE.store(0,Ordering::Release);for x in &BOOT_IRQ_PHASE{x.store(0,Ordering::Release)} for x in &BOOT_IRQ_GENERATIONS{x.store(0,Ordering::Release)} for x in &BOOT_MASTER{x.store(ptr::null_mut(),Ordering::Release)} BOOT_IRQ_TARGET_USERS.store(0,Ordering::Release);events().lock().unwrap().clear()}
// Source-bound extraction of the pinned Linux Rust error contract: errno
// remains negative from to_result through Error::to_errno.
fn boot_irq_stale()->Error{kernel::error::to_result(-ESTALE).unwrap_err()}
mod bindings{pub const EOVERFLOW:u32=75;pub unsafe fn msleep(_:u32){super::sleep_hook();}}
mod smp_ikc{use super::*;pub fn validate_apic()->Result{Ok(())} #[derive(Debug)] pub struct BootMaster{owner:super::OsToken} impl BootMaster{pub fn new(owner:super::OsToken)->Self{Self{owner}} pub fn owner(&self)->super::OsToken{self.owner} pub fn interrupt(&self){super::events().lock().unwrap().push("interrupt");super::interrupt_hook();}}}
#[derive(Clone,Copy,Debug,Eq,PartialEq)] struct OsToken{slot:u32,generation:u64}
impl OsToken{fn slot(self)->u32{self.slot} fn generation(self)->u64{self.generation}}
struct HostCpu{online:bool} struct BootTopology<'a>{cpus:&'a[HostCpu]} impl BootTopology<'_>{fn host_cpu(&self,n:usize)->Result<&HostCpu>{self.cpus.get(n).ok_or(ENODEV)}}
// PRODUCTION_SHUTDOWN_IRQ_ROUTE
#[test]fn unused_drop_recreate_and_exactly_once_decrement(){reset();let t=OsToken{slot:2,generation:7};let q=BootTopology{cpus:&[HostCpu{online:true}]};let r=BootIrqRoute::new(t,&q).unwrap();drop(r);assert_eq!(*TRACE.lock().unwrap(),vec![Event::TargetDecrement]);assert_eq!(BOOT_IRQ_TARGET_USERS.load(Ordering::Acquire),0);assert!(BootIrqRoute::new(OsToken{slot:2,generation:8},&q).is_ok());}
#[test]fn callback_executes_live_and_is_quiet_after_close(){reset();let t=OsToken{slot:1,generation:8};let q=BootTopology{cpus:&[HostCpu{online:true}]};let mut r=BootIrqRoute::new(t,&q).unwrap();let m=Box::leak(Box::new(smp_ikc::BootMaster::new(t)));unsafe{r.publish_master(m).unwrap();boot_irq_callback::<1>(ptr::null_mut());}assert_eq!(BOOT_IRQ_EVENTS[1].load(Ordering::Acquire),1);assert_eq!(BOOT_IRQ_INFLIGHT[1].load(Ordering::Acquire),0);r.begin_close().unwrap();unsafe{boot_irq_callback::<1>(ptr::null_mut());}assert_eq!(BOOT_IRQ_EVENTS[1].load(Ordering::Acquire),1);assert_eq!(*events().lock().unwrap(),vec!["interrupt"]);}
#[test]fn successful_close_order_and_once_only_target_decrement(){reset();let t=OsToken{slot:3,generation:9};let q=BootTopology{cpus:&[HostCpu{online:true}]};let mut r=BootIrqRoute::new(t,&q).unwrap();let m=Box::leak(Box::new(smp_ikc::BootMaster::new(t)));unsafe{r.publish_master(m).unwrap();}r.begin_close().unwrap();r.finish_close().unwrap();assert_eq!(BOOT_IRQ_PHASE[3].load(Ordering::Acquire),BOOT_IRQ_DRAINED);assert_eq!(BOOT_IRQ_TARGET_USERS.load(Ordering::Acquire),0);assert!(r.finish_close().is_err());assert_eq!(*TRACE.lock().unwrap(),vec![Event::MasterRemoved,Event::TargetDecrement]);}
#[test]fn persistent_busy_sender_timeout_and_no_reuse(){reset();let t=OsToken{slot:4,generation:10};let q=BootTopology{cpus:&[HostCpu{online:true}]};let mut r=BootIrqRoute::new(t,&q).unwrap();BOOT_IRQ_INFLIGHT[4].store(1,Ordering::Release);r.begin_close().unwrap();assert_eq!(r.finish_close(),Err(EBUSY));assert_eq!(BOOT_IRQ_PHASE[4].load(Ordering::Acquire),BOOT_IRQ_QUARANTINED);assert!(BootIrqRoute::new(OsToken{slot:4,generation:11},&q).is_err());}
#[test]fn stale_generation_quarantine_reports_estale(){reset();let t=OsToken{slot:5,generation:12};let q=BootTopology{cpus:&[HostCpu{online:true}]};let mut r=BootIrqRoute::new(t,&q).unwrap();r.begin_close().unwrap();BOOT_IRQ_GENERATIONS[5].store(13,Ordering::Release);assert_eq!(r.finish_close(),Err(boot_irq_stale()));assert_eq!(BOOT_IRQ_PHASE[5].load(Ordering::Acquire),BOOT_IRQ_QUARANTINED);}
#[test]fn master_pointer_cas_mismatch_preserves_foreign_master(){reset();let t=OsToken{slot:6,generation:14};let q=BootTopology{cpus:&[HostCpu{online:true}]};let mut r=BootIrqRoute::new(t,&q).unwrap();let m=Box::leak(Box::new(smp_ikc::BootMaster::new(t)));let foreign=Box::leak(Box::new(smp_ikc::BootMaster::new(t)));unsafe{r.publish_master(m).unwrap();}r.begin_close().unwrap();BOOT_MASTER[6].store(foreign as *mut _,Ordering::Release);assert_eq!(r.finish_close(),Err(boot_irq_stale()));assert_eq!(BOOT_MASTER[6].load(Ordering::Acquire),foreign as *mut _);assert_eq!(BOOT_IRQ_PHASE[6].load(Ordering::Acquire),BOOT_IRQ_QUARANTINED);}
#[test]fn generation_cas_restore_failure_preserves_master_and_quarantines(){
    // The fixture's pointer wrapper injects a generation change immediately
    // after the production shared-master CAS succeeds, so this executes the
    // real failed generation CAS and its restoration branch deterministically.
    reset(); let t=OsToken{slot:6,generation:14}; let q=BootTopology{cpus:&[HostCpu{online:true}]};
    let mut r=BootIrqRoute::new(t,&q).unwrap(); let m=Box::leak(Box::new(smp_ikc::BootMaster::new(t)));
    unsafe{r.publish_master(m).unwrap();} r.begin_close().unwrap(); FORCE_GENERATION_CAS_FAILURE.store(1,Ordering::Release);
    assert_eq!(r.finish_close(),Err(boot_irq_stale())); assert_eq!(BOOT_MASTER[6].load(Ordering::Acquire),m as *mut _);
    assert_eq!(BOOT_IRQ_GENERATIONS[6].load(Ordering::Acquire),15); assert_eq!(BOOT_IRQ_PHASE[6].load(Ordering::Acquire),BOOT_IRQ_QUARANTINED);
}
#[test]fn closing_and_quarantine_reuse_rejected(){reset();let t=OsToken{slot:7,generation:15};let q=BootTopology{cpus:&[HostCpu{online:true}]};let mut r=BootIrqRoute::new(t,&q).unwrap();r.begin_close().unwrap();assert!(BootIrqRoute::new(OsToken{slot:7,generation:16},&q).is_err());r.quarantine();assert!(BootIrqRoute::new(OsToken{slot:7,generation:17},&q).is_err());}

// The memory helpers and BOTH PreparedBoot methods below are extracted verbatim.
// Only unrelated allocation/topology containers and Linux calls are mocked.
// Each event originates at a consumed boundary, never in the test's expected
// ordering. Atomics delegate to std atomics with the production orderings.
#[derive(Clone,Debug,Eq,PartialEq)]
enum Event {
    Sync{index:usize,senders:u32,busy:u32,master:bool,users:u32},
    MasterRemoved, TargetDecrement,
}
static TRACE:Mutex<Vec<Event>>=Mutex::new(Vec::new());
fn trace(e:Event){TRACE.lock().unwrap().push(e);}
type Hook=std::sync::Arc<dyn Fn()+Send+Sync>;
static SLEEP_HOOK:Mutex<Option<Hook>>=Mutex::new(None);
static INTERRUPT_HOOK:Mutex<Option<Hook>>=Mutex::new(None);
static SYNC_HOOK:Mutex<Option<Hook>>=Mutex::new(None);
static SYNC_DESCRIPTOR:AtomicU64=AtomicU64::new(0);
static SYNC_BASE:AtomicU64=AtomicU64::new(0);
static PAGE_DROPS:AtomicU32=AtomicU32::new(0);
static SLEEPS:AtomicU32=AtomicU32::new(0);
fn invoke(h:&Mutex<Option<Hook>>){let hook=h.lock().unwrap().clone();if let Some(hook)=hook{hook()}}
fn sleep_hook(){SLEEPS.fetch_add(1,Ordering::Relaxed);invoke(&SLEEP_HOOK);std::thread::yield_now();}
fn interrupt_hook(){invoke(&INTERRUPT_HOOK);}
fn reset_observer(){TRACE.lock().unwrap().clear();*SLEEP_HOOK.lock().unwrap()=None;*INTERRUPT_HOOK.lock().unwrap()=None;*SYNC_HOOK.lock().unwrap()=None;PAGE_DROPS.store(0,Ordering::Relaxed);SLEEPS.store(0,Ordering::Relaxed);}
mod linux_mock {
    use super::*;
    // This replaces only Linux's external function, not the production caller.
    // It observes the exact node pointer and shared flags handed to Linux.
    #[no_mangle]
    unsafe extern "C" fn irq_work_sync(work:*mut core::ffi::c_void){
        let d=unsafe{&*(SYNC_DESCRIPTOR.load(Ordering::Acquire) as *const NativeIrqWorkDescriptorView)};
        let slot=unsafe{&*(work as *const NativeIrqWorkSlot)};
        trace(Event::Sync{index:(work as u64-SYNC_BASE.load(Ordering::Acquire)) as usize/64,
            senders:d.senders.load(Ordering::Acquire),busy:slot.flags.load(Ordering::Acquire)&2,
            master:!BOOT_MASTER[8].load(Ordering::Acquire).is_null(),
            users:BOOT_IRQ_TARGET_USERS.load(Ordering::Acquire)});
        invoke(&SYNC_HOOK);
    }
}

struct PageOwner{physical:u64,bytes:u64}
impl PageOwner{fn end(&self)->u64{self.physical+self.bytes}}
#[repr(C,align(64))]
struct AlignedPage([u8;4096]);
struct BootPages{storage:Box<AlignedPage>,pages:PageOwner,address:u64,bytes:usize}
impl BootPages{
    fn new(physical:u64,bytes:usize)->Self{let storage=Box::new(AlignedPage([0;4096]));let address=storage.0.as_ptr() as u64;Self{storage,pages:PageOwner{physical,bytes:4096},address,bytes}}
    fn physical(&self)->u64{self.pages.physical}
    fn read64(&self,offset:usize)->Result<u64>{let b=self.storage.0.get(offset..offset+8).ok_or(EIO)?;Ok(u64::from_ne_bytes(b.try_into().unwrap()))}
}
impl Drop for BootPages{fn drop(&mut self){PAGE_DROPS.fetch_add(1,Ordering::Relaxed);}}
struct LowRegion(u64);impl LowRegion{fn physical(&self)->u64{self.0}}
struct Extent{base:u64,bytes:u64}impl Extent{fn start(&self)->u64{self.base}fn end(&self)->Result<u64>{self.base.checked_add(self.bytes).ok_or(EIO)}}
struct MemoryMap<const N:usize>{extents:Vec<Extent>}
impl<const N:usize> MemoryMap<N>{fn len(&self)->usize{self.extents.len()}fn extent(&self,i:usize)->Option<&Extent>{self.extents.get(i)}}
const MAX_EXTENTS:usize=4096;
mod abi{#[repr(C)]pub struct IhkSmpBootParam{pub message_buffer:u64,pub message_buffer_size:u64}}
struct OwnedControlChannel{pages:BootPages}
// The subset contains every field read by the complete extracted impl.
struct PreparedBoot{params:BootPages,irq_slots:BootPages,irq_generation:u64,_dump:BootPages,
    trampoline:LowRegion,irq:BootIrqRoute,cpus:Vec<()>,channels:Vec<OwnedControlChannel>,
    master:Box<smp_ikc::BootMaster>}
// PRODUCTION_MEMORY_IRQ
// PRODUCTION_PREPARED_CLOSE

fn empty_memory()->MemoryMap<MAX_EXTENTS>{MemoryMap{extents:Vec::new()}}
fn prepared()->PreparedBoot{
    reset();let owner=OsToken{slot:8,generation:123};
    let irq=BootIrqRoute::new(owner,&BootTopology{cpus:&[HostCpu{online:true}]}).unwrap();
    let master=Box::new(smp_ikc::BootMaster::new(owner));unsafe{irq.publish_master(&master).unwrap();}
    let mut p=PreparedBoot{params:BootPages::new(0x10000,128),irq_slots:BootPages::new(0x20000,128),irq_generation:123,
        _dump:BootPages::new(0x30000,4096),trampoline:LowRegion(0x40000),irq,cpus:vec![(),()],channels:Vec::new(),master};
    p.params.storage.0[0..8].copy_from_slice(&0x50000_u64.to_ne_bytes());
    p.params.storage.0[8..16].copy_from_slice(&4096_u64.to_ne_bytes());
    unsafe{ptr::write((p.params.address+64) as *mut NativeIrqWorkDescriptorView,NativeIrqWorkDescriptorView{
        magic:NATIVE_IRQ_WORK_MAGIC,version:1,bytes:64,generation:123,slots_phys:p.irq_slots.physical(),slots_count:2,slots_stride:64,
        state:AtomicU32::new(1),senders:AtomicU32::new(0),reserved:[0;6]});
        for n in 0..2{ptr::write((p.irq_slots.address+n*64) as *mut NativeIrqWorkSlot,NativeIrqWorkSlot{_llist:[0;8],flags:AtomicU32::new(0),opaque:[0;20]});}}
    SYNC_DESCRIPTOR.store(p.params.address+64,Ordering::Release);SYNC_BASE.store(p.irq_slots.address,Ordering::Release);p
}
fn descriptor(p:&PreparedBoot)->&NativeIrqWorkDescriptorView{unsafe{&*((p.params.address+64) as *const NativeIrqWorkDescriptorView)}}
fn slot(p:&PreparedBoot,n:u64)->&NativeIrqWorkSlot{unsafe{&*((p.irq_slots.address+n*64) as *const NativeIrqWorkSlot)}}
fn sync_event(index:usize)->Event{Event::Sync{index,senders:1<<31,busy:0,master:true,users:1}}
fn retained(p:&PreparedBoot,senders:u32){
    assert_eq!(descriptor(p).senders.load(Ordering::Acquire),senders);
    assert_eq!(PAGE_DROPS.load(Ordering::Acquire),0);
    assert_eq!(BOOT_MASTER[8].load(Ordering::Acquire),(&*p.master as *const smp_ikc::BootMaster).cast_mut());
    assert_eq!(BOOT_IRQ_TARGET_USERS.load(Ordering::Acquire),1);
    assert_eq!(BOOT_IRQ_GENERATIONS[8].load(Ordering::Acquire),123);
    assert_eq!(BOOT_IRQ_PHASE[8].load(Ordering::Acquire),BOOT_IRQ_QUARANTINED);
}

#[test]fn memory_abi_and_errno_are_exact(){
    assert_eq!(std::mem::size_of::<NativeIrqWorkSlot>(),32);assert_eq!(offset_of!(NativeIrqWorkSlot,flags),8);
    assert_eq!(NATIVE_IRQ_WORK_BUSY,2);assert_eq!(native_irq_error(110).to_errno(),-110);
    assert_eq!(std::mem::size_of::<NativeIrqWorkDescriptorView>(),64);
}
#[test]fn prepared_success_syncs_each_node_before_master_and_target_retire(){
    let mut p=prepared();let addresses=(p.params.address,p.irq_slots.address,p._dump.address);
    assert_eq!(p.close_irq_senders(&empty_memory()),Ok(()));
    assert_eq!(*TRACE.lock().unwrap(),vec![sync_event(0),sync_event(1),Event::MasterRemoved,Event::TargetDecrement]);
    assert_eq!(BOOT_IRQ_TARGET_USERS.load(Ordering::Acquire),0);assert_eq!(BOOT_IRQ_GENERATIONS[8].load(Ordering::Acquire),0);
    assert_eq!(PAGE_DROPS.load(Ordering::Acquire),0);assert_eq!(addresses,(p.params.address,p.irq_slots.address,p._dump.address));
    let before=TRACE.lock().unwrap().clone();assert_eq!(p.close_irq_senders(&empty_memory()),Err(EBUSY));
    assert_eq!(*TRACE.lock().unwrap(),before);drop(p);assert_eq!(PAGE_DROPS.load(Ordering::Acquire),3);
    assert_eq!(*TRACE.lock().unwrap(),before);
}
#[test]fn outstanding_sender_retires_only_after_gate_closure_before_sync(){
    let mut p=prepared();descriptor(&p).senders.store(1,Ordering::Release);
    let address=p.params.address+64;
    *SLEEP_HOOK.lock().unwrap()=Some(std::sync::Arc::new(move||{
        let d=unsafe{&*(address as *const NativeIrqWorkDescriptorView)};
        assert_eq!(d.senders.load(Ordering::Acquire),(1<<31)|1);assert!(TRACE.lock().unwrap().is_empty());
        assert_eq!(BOOT_IRQ_PHASE[8].load(Ordering::Acquire),BOOT_IRQ_CLOSING);
        d.senders.fetch_sub(1,Ordering::Release);
    }));
    assert_eq!(p.close_irq_senders(&empty_memory()),Ok(()));assert_eq!(SLEEPS.load(Ordering::Acquire),1);
    assert_eq!(*TRACE.lock().unwrap(),vec![sync_event(0),sync_event(1),Event::MasterRemoved,Event::TargetDecrement]);
}
#[test]fn sender_timeout_keeps_closed_gate_and_every_owner(){
    let mut p=prepared();descriptor(&p).senders.store(1,Ordering::Release);
    assert_eq!(p.close_irq_senders(&empty_memory()),Err(native_irq_error(110)));retained(&p,(1<<31)|1);
    assert_eq!(SLEEPS.load(Ordering::Acquire),1000);assert!(TRACE.lock().unwrap().is_empty());
    assert_eq!(p.close_irq_senders(&empty_memory()),Err(EBUSY));retained(&p,(1<<31)|1);
}
#[test]fn first_busy_node_timeout_retains_gate_master_target_and_pages(){
    let mut p=prepared();slot(&p,0).flags.store(2,Ordering::Release);
    assert_eq!(p.close_irq_senders(&empty_memory()),Err(native_irq_error(110)));retained(&p,1<<31);
    assert_eq!(SLEEPS.load(Ordering::Acquire),1000);assert!(TRACE.lock().unwrap().is_empty());
}
#[test]fn second_busy_node_timeout_preserves_partial_sync_and_all_owners(){
    let mut p=prepared();slot(&p,1).flags.store(2,Ordering::Release);
    assert_eq!(p.close_irq_senders(&empty_memory()),Err(native_irq_error(110)));retained(&p,1<<31);
    assert_eq!(*TRACE.lock().unwrap(),vec![sync_event(0)]);
}
#[test]fn busy_node_retirement_precedes_its_linux_sync(){
    let mut p=prepared();slot(&p,1).flags.store(2,Ordering::Release);let address=p.irq_slots.address+64;
    *SLEEP_HOOK.lock().unwrap()=Some(std::sync::Arc::new(move||{
        assert_eq!(*TRACE.lock().unwrap(),vec![sync_event(0)]);
        unsafe{&*(address as *const NativeIrqWorkSlot)}.flags.store(0,Ordering::Release);
    }));
    assert_eq!(p.close_irq_senders(&empty_memory()),Ok(()));
    assert_eq!(*TRACE.lock().unwrap(),vec![sync_event(0),sync_event(1),Event::MasterRemoved,Event::TargetDecrement]);
}
#[test]fn live_callback_concurrently_finishes_while_close_waits_for_busy_node(){
    let mut p=prepared();slot(&p,0).flags.store(2,Ordering::Release);
    let entered=std::sync::Arc::new(std::sync::Barrier::new(2));let release=std::sync::Arc::new(std::sync::Barrier::new(2));
    let (a,b)=(entered.clone(),release.clone());
    *INTERRUPT_HOOK.lock().unwrap()=Some(std::sync::Arc::new(move||{a.wait();b.wait();}));
    let address=p.irq_slots.address;let done=std::sync::Arc::new(std::sync::Barrier::new(2));let child_done=done.clone();
    let child=std::thread::spawn(move||{unsafe{boot_irq_callback::<8>(ptr::null_mut());}
        unsafe{&*(address as *const NativeIrqWorkSlot)}.flags.store(0,Ordering::Release);child_done.wait();});
    entered.wait();assert_eq!(BOOT_IRQ_INFLIGHT[8].load(Ordering::Acquire),1);
    let once=AtomicU32::new(0);
    *SLEEP_HOOK.lock().unwrap()=Some(std::sync::Arc::new(move||{if once.fetch_add(1,Ordering::Relaxed)==0{
        assert_eq!(BOOT_IRQ_PHASE[8].load(Ordering::Acquire),BOOT_IRQ_CLOSING);
        assert!(!BOOT_MASTER[8].load(Ordering::Acquire).is_null());assert!(TRACE.lock().unwrap().is_empty());release.wait();done.wait();
    }}));
    assert_eq!(p.close_irq_senders(&empty_memory()),Ok(()));child.join().unwrap();
    assert_eq!(BOOT_IRQ_INFLIGHT[8].load(Ordering::Acquire),0);assert_eq!(BOOT_IRQ_EVENTS[8].load(Ordering::Acquire),1);
    assert_eq!(*TRACE.lock().unwrap(),vec![sync_event(0),sync_event(1),Event::MasterRemoved,Event::TargetDecrement]);
}
#[test]fn concurrent_callback_after_close_admission_stays_quiet_during_sync(){
    let mut p=prepared();*SYNC_HOOK.lock().unwrap()=Some(std::sync::Arc::new(||{
        std::thread::spawn(||unsafe{boot_irq_callback::<8>(ptr::null_mut());}).join().unwrap();
        assert_eq!(BOOT_IRQ_INFLIGHT[8].load(Ordering::Acquire),0);
        assert_eq!(BOOT_IRQ_EVENTS[8].load(Ordering::Acquire),0);
    }));
    assert_eq!(p.close_irq_senders(&empty_memory()),Ok(()));assert!(events().lock().unwrap().is_empty());
}
#[test]fn invalid_retained_geometry_rejects_before_closing_anything(){
    let mut p=prepared();let memory=MemoryMap{extents:vec![Extent{base:0x20000,bytes:4096}]};
    assert_eq!(p.close_irq_senders(&memory),Err(EIO));assert_eq!(descriptor(&p).senders.load(Ordering::Acquire),0);
    assert_eq!(BOOT_IRQ_PHASE[8].load(Ordering::Acquire),BOOT_IRQ_LIVE);assert!(TRACE.lock().unwrap().is_empty());
    assert_eq!(PAGE_DROPS.load(Ordering::Acquire),0);assert_eq!(BOOT_IRQ_TARGET_USERS.load(Ordering::Acquire),1);
}
#[test]fn typed_wait_rejection_preserves_closed_sender_gate(){
    let p=prepared();descriptor(&p).senders.store(2,Ordering::Release);
    assert_eq!(close_native_irq_work_senders_typed(descriptor(&p),p.irq_slots.address,||false),Err(native_irq_error(110)));
    assert_eq!(descriptor(&p).senders.load(Ordering::Acquire),(1<<31)|2);assert!(TRACE.lock().unwrap().is_empty());
}
