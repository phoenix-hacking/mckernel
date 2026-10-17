// Deterministic Linux adapters for actual shutdown epoch/CPU proof bodies.
// Hardware CPU reset, real Linux callback drain and physical release are not tested.
#![allow(dead_code)]
use std::sync::atomic::{AtomicI32, AtomicU32, Ordering};
static CPU_LOCKS: AtomicU32 = AtomicU32::new(0);
static MEMORY_LOCKS: AtomicU32 = AtomicU32::new(0);
static HOTPLUG_LOCKS: AtomicU32 = AtomicU32::new(0);
static STOP_CALLS: AtomicU32 = AtomicU32::new(0);
static IRQ_STATUS: AtomicI32 = AtomicI32::new(0);
struct CountedGuard<'a, T> { guard: std::sync::MutexGuard<'a,T>, counter: &'static AtomicU32 }
impl<T> std::ops::Deref for CountedGuard<'_,T> { type Target=T; fn deref(&self)->&T { &self.guard } }
impl<T> std::ops::DerefMut for CountedGuard<'_,T> { fn deref_mut(&mut self)->&mut T { &mut self.guard } }
impl<T> Drop for CountedGuard<'_,T> { fn drop(&mut self) { self.counter.fetch_sub(1,Ordering::AcqRel); } }
mod smp_resource { pub(super) use super::smp_cpu::OsToken; }
mod sysfs_remote {
    // PRODUCTION_PEER_PROOF
}
mod smp_memory {
    use std::{marker::PhantomData, ptr, sync::atomic::{AtomicPtr, AtomicU32, AtomicU64, Ordering}};
    use super::smp_cpu::{OsToken,Result};
    const EIO:i32=-5; const EBUSY:i32=-16; const EINVAL:i32=-22; const ENODEV:i32=-19;
    const GFP_KERNEL:()=();
    struct Arc<T>(std::sync::Arc<T>);
    impl<T> Arc<T> { fn new(value:T,_flags:())->Result<Self> {Ok(Self(std::sync::Arc::new(value)))} fn ptr_eq(a:&Self,b:&Self)->bool {std::sync::Arc::ptr_eq(&a.0,&b.0)} }
    impl<T> Clone for Arc<T> {fn clone(&self)->Self {Self(self.0.clone())}}
    impl<T> std::ops::Deref for Arc<T> {type Target=T;fn deref(&self)->&T {&self.0}}
    mod service {
        use super::Result;
        use std::sync::Arc;
        const EBUSY:i32=-16;
        struct RemoteAdapter;
        impl RemoteAdapter {
            fn shutdown_after_peer_stop(&self, proof:&super::super::sysfs_remote::PeerStopped<'_>)->Result<bool> {
                assert!(proof.matches_boot(&super::current_claim_for_test()));
                super::super::STOP_CALLS.fetch_add(1,super::Ordering::AcqRel);Ok(true)
            }
            fn shutdown_drained(&self, proof:&super::super::sysfs_remote::PeerStopped<'_>)->Result<bool> {
                Ok(proof.matches_boot(&super::current_claim_for_test()))
            }
        }
        struct Runtime {remote:RemoteAdapter}
        struct Thread;
        impl Thread {
            fn stop_join(&self) {
                assert_eq!(super::super::CPU_LOCKS.load(super::Ordering::Acquire),0);
                assert_eq!(super::super::MEMORY_LOCKS.load(super::Ordering::Acquire),0);
                assert_eq!(super::super::HOTPLUG_LOCKS.load(super::Ordering::Acquire),0);
            }
        }
        // PRODUCTION_STARTED_STRUCT
        impl Started { // PRODUCTION_STARTED_STOP
        }
        pub(super) fn fixture_started()->Started {
            Started {runtime:Arc::new(Runtime {remote:RemoteAdapter}),metadata:Arc::new(Thread),packets:Arc::new(Thread),zeroing:Arc::new(Thread)}
        }
    }
    // PRODUCTION_EPOCH
    struct MockIrq { drained: bool }
    impl MockIrq { fn shutdown_drained(&self,_owner:OsToken)->bool {self.drained} }
    struct PreparedBoot { continuing:Option<service::Started>, irq:MockIrq }
    struct BootStorage { epoch:Arc<BootEpoch>, started:bool, shutdown_terminal:bool, prepared:PreparedBoot }
    struct LoadedImage { owner:OsToken, boot:Option<BootStorage> }
    impl LoadedImage {fn started(&self)->bool {self.boot.as_ref().is_some_and(|boot|boot.started)}}
    struct MemoryContext { images:[Option<LoadedImage>;64] }
    impl MemoryContext {
        // PRODUCTION_MEMORY_METHODS
    }
    struct ContextMutex(std::sync::Mutex<MemoryContext>);
    impl ContextMutex {fn lock(&self)->super::CountedGuard<'_,MemoryContext> {
        let guard=self.0.lock().unwrap(); super::MEMORY_LOCKS.fetch_add(1,Ordering::AcqRel);
        super::CountedGuard {guard,counter:&super::MEMORY_LOCKS}
    }}
    static PUBLISHED:AtomicPtr<ContextMutex>=AtomicPtr::new(ptr::null_mut());
    // PRODUCTION_MEMORY_CLAIM_WRAPPER
    pub(super) enum ShutdownIrqFailure {PreEffect(i32),PostEffect(i32)}
    pub(super) fn shutdown_close_irq_senders(owner:OsToken)->std::result::Result<(),ShutdownIrqFailure> {
        let status=super::IRQ_STATUS.load(Ordering::Acquire);
        if status!=0 {return Err(ShutdownIrqFailure::PostEffect(status));}
        let mut context=unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock();
        let image=context.images[owner.slot() as usize].as_mut().unwrap();
        image.boot.as_mut().unwrap().prepared.irq.drained=true;Ok(())
    }
    pub(super) fn setup(owner:OsToken) {
        let mut images=[const{None};64];
        images[owner.slot() as usize]=Some(LoadedImage {owner,boot:Some(BootStorage {epoch:BootEpoch::allocate().unwrap(),started:true,shutdown_terminal:false,prepared:PreparedBoot {continuing:Some(service::fixture_started()),irq:MockIrq {drained:false}}})});
        PUBLISHED.store(Box::into_raw(Box::new(ContextMutex(std::sync::Mutex::new(MemoryContext {images})))),Ordering::Release);
    }
    pub(super) fn ordinary_boot(owner:OsToken)->Result {unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().require_unstarted(owner)}
    pub(super) fn admission_open(owner:OsToken)->bool {unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].as_ref().unwrap().boot.as_ref().unwrap().epoch.admission_open()}
    pub(super) fn replace_epoch(owner:OsToken) {unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].as_mut().unwrap().boot.as_mut().unwrap().epoch=BootEpoch::allocate().unwrap();}
    pub(super) fn invalidate(owner:OsToken) {unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].as_ref().unwrap().boot.as_ref().unwrap().epoch.shutdown.store(SHUTDOWN_RETAINED,Ordering::Release);}
    // Alias a live claim only in the fixture to check matching without taking
    // ownership of the transaction or changing its state on Drop.
    fn current_claim_for_test()->std::mem::ManuallyDrop<ShutdownBoot> {
        let context=unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock();
        let image=context.images.iter().flatten().next().unwrap();let boot=image.boot.as_ref().unwrap();
        std::mem::ManuallyDrop::new(ShutdownBoot {owner:image.owner,epoch:boot.epoch.clone(),started:service::fixture_started(),_task:PhantomData})
    }
    pub(super) fn retire_os_boot(_owner:OsToken)->Result {Ok(())}
    pub(super) fn release_os_resources(_owner:OsToken,commit:impl FnOnce())->Result {commit();Ok(())}
    pub(super) fn finish_shutdown(_owner:OsToken,commit:impl FnOnce())->Result {commit();Ok(())}
}
// PRODUCTION_CPU_FIXTURE
