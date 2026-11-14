//! Deterministic Linux adapters; production CPU, topology and policy bodies.
#![allow(dead_code)]
mod smp_resource {
    // REAL_RESOURCE
}
mod smp_topology {
    use super::smp_cpu::{bindings, Result};
    const WORDS: usize = 8;
    // REAL_TOPOLOGY
    impl CpuMask {
        pub(crate) unsafe fn online() -> Result<Self> {
            let mut words = [0; WORDS];
            for cpu in 0..4 { if bindings::online(cpu) { words[0] |= 1 << cpu; } }
            Ok(Self {words})
        }
    }
    pub(crate) unsafe fn capture(cpu: usize) -> Result<Cpu> {
        let status = bindings::CAPTURE_STATUS.load(std::sync::atomic::Ordering::Acquire);
        if status != 0 { return Err(status); }
        let mut result = fixture_cpu(cpu);
        if bindings::TOPOLOGY_CHANGED.load(std::sync::atomic::Ordering::Acquire) { result.core_id += 1; }
        Ok(result)
    }
    pub(crate) fn fixture_cpu(cpu: usize) -> Cpu {
        Cpu {linux_id:cpu as u32,apic_id:0x20+cpu as u32, package_id:0,core_id:cpu as u32,die_id:0,
            core_siblings:CpuMask{words:[15,0,0,0,0,0,0,0]},
            thread_siblings:CpuMask{words:[1<<cpu,0,0,0,0,0,0,0]},caches:Vec::new()}
    }
}
mod smp_memory {
    use super::smp_resource::OsToken;
    use super::smp_cpu::{Result, EIO};
    use std::sync::atomic::Ordering;
    use std::sync::atomic::{AtomicI32, AtomicU32};
    pub(crate) static STATUS: AtomicI32 = AtomicI32::new(0);
    pub(crate) static COMMITS: AtomicU32 = AtomicU32::new(0);
    pub(crate) struct ShutdownBoot {pub(crate) owner:OsToken,pub(crate) epoch:u64}
    impl ShutdownBoot {
        pub(crate) fn owner(&self)->OsToken{self.owner}
        pub(crate) fn epoch_id(&self)->u64{self.epoch}
        pub(crate) fn matches_owner(&self,owner:OsToken)->bool{self.owner==owner&&self.epoch!=0}
    }
    pub(crate) fn finish_shutdown_claim(boot:&ShutdownBoot,commit:impl FnOnce())->Result {
        if boot.epoch!=17{return Err(EIO);}
        finish_shutdown(boot.owner,commit)
    }
    pub(crate) fn finish_shutdown(_owner:OsToken,commit:impl FnOnce())->Result {
        let status=STATUS.load(Ordering::Acquire);if status!=0{return Err(status);}
        commit();COMMITS.fetch_add(1,Ordering::AcqRel);Ok(())
    }
}
mod smp_cpu {
    use std::{ptr,sync::{Arc,atomic::{AtomicBool,AtomicI32,AtomicPtr,AtomicU32,Ordering}}};
    use std::pin::Pin;
    use super::smp_resource::{CpuChange,CpuEffectCause,CpuState,CpuTable,HostCpuHotplug,HostCpuSnapshot,OsToken};
    const SMP_MAX_CPUS:usize=4;
    pub(crate) const EIO:i32=-5;
    const ENODEV:i32=-19;
    const EINVAL:i32=-22;
    type Error=i32;
    pub(crate) type Result<T=()> = std::result::Result<T,Error>;
    trait ErrorNumber {fn to_errno(self)->i32;}
    impl ErrorNumber for i32 {fn to_errno(self)->i32{self}}
    mod kernel {pub mod error {pub fn to_result(status:i32)->Result<(),i32>{if status==0{Ok(())}else{Err(status)}}}}
    pub(crate) mod bindings {
        use super::{AtomicBool,AtomicI32,AtomicU32,Ordering};
        #[allow(non_camel_case_types)] pub struct device;
        pub const EALREADY:u32=114;
        static ONLINE:[AtomicBool;4]=[const{AtomicBool::new(true)};4];
        static DEVICE_DELTA:AtomicI32=AtomicI32::new(0);
        static MISSING:AtomicBool=AtomicBool::new(false);
        pub(crate) static TOPOLOGY_CHANGED:AtomicBool=AtomicBool::new(false);
        pub(crate) static CAPTURE_STATUS:AtomicI32=AtomicI32::new(0);
        pub(crate) static OFFLINE_STATUS:AtomicI32=AtomicI32::new(0);
        pub(crate) static ONLINE_STATUS:AtomicI32=AtomicI32::new(0);
        pub(crate) static OFFLINES:AtomicU32=AtomicU32::new(0);
        pub(crate) static ONLINES:AtomicU32=AtomicU32::new(0);
        pub(crate) static DROPS:AtomicU32=AtomicU32::new(0);
        pub(crate) static REMOVALS:AtomicU32=AtomicU32::new(0);
        pub(crate) static TRACK_TEARDOWN:AtomicBool=AtomicBool::new(false);
        pub(crate) static HARDWARE_CHANGED:AtomicBool=AtomicBool::new(false);
        pub(crate) static NODE_CHANGED:AtomicBool=AtomicBool::new(false);
        pub(crate) fn online(cpu:usize)->bool{ONLINE[cpu].load(Ordering::Acquire)}
        pub(crate) fn set_online(cpu:usize,value:bool){ONLINE[cpu].store(value,Ordering::Release);}
        pub(crate) fn replace(){DEVICE_DELTA.store(32,Ordering::Release);}
        pub(crate) fn missing(){MISSING.store(true,Ordering::Release);}
        pub(crate) unsafe fn get_cpu_device(cpu:u32)->*mut device {
            if MISSING.load(Ordering::Acquire){ptr_null()}else{(0x1000+cpu as usize+DEVICE_DELTA.load(Ordering::Acquire) as usize) as *mut device}
        }
        fn ptr_null()->*mut device{std::ptr::null_mut()}
        pub(crate) unsafe fn put_device(_device:*mut device){
            if TRACK_TEARDOWN.load(Ordering::Acquire){assert_eq!(REMOVALS.load(Ordering::Acquire),2);}
            DROPS.fetch_add(1,Ordering::AcqRel);
        }
        pub(crate) unsafe fn __cpuhp_remove_state(state:i32,invoke:bool){
            assert!(!invoke);assert!(super::PUBLISHED.load(Ordering::Acquire).is_null());
            assert_eq!(DROPS.load(Ordering::Acquire),0);
            let previous=REMOVALS.fetch_add(1,Ordering::AcqRel);assert_eq!(state,if previous==0{12}else{11});
        }
        pub(crate) unsafe fn device_offline(cpu_device:*mut device)->i32 {
            OFFLINES.fetch_add(1,Ordering::AcqRel);let status=OFFLINE_STATUS.load(Ordering::Acquire);
            if status==0{set_online(cpu_device as usize-0x1000,false);}status
        }
        pub(crate) unsafe fn device_online(cpu_device:*mut device)->i32 {
            ONLINES.fetch_add(1,Ordering::AcqRel);let status=ONLINE_STATUS.load(Ordering::Acquire);
            if status==0{set_online(cpu_device as usize-0x1000,true);}status
        }
        pub(crate) fn reset(){
            for value in &ONLINE{value.store(true,Ordering::Release);}
            for value in [&MISSING,&TOPOLOGY_CHANGED,&HARDWARE_CHANGED,&NODE_CHANGED,&TRACK_TEARDOWN]{value.store(false,Ordering::Release);}
            for value in [&DEVICE_DELTA,&CAPTURE_STATUS,&OFFLINE_STATUS,&ONLINE_STATUS]{value.store(0,Ordering::Release);}
            for value in [&OFFLINES,&ONLINES,&DROPS,&REMOVALS]{value.store(0,Ordering::Release);}
        }
    }
    struct DeviceHotplugGuard;
    impl DeviceHotplugGuard{fn lock()->Self{Self}}
    struct CpuReadGuard;
    impl CpuReadGuard{fn lock()->Self{Self}}
    struct TransitionTask;
    impl TransitionTask{fn new(_cpu:usize)->Self{Self}}
    static PIN_STATUS:AtomicI32=AtomicI32::new(0);
    static PIN_DROPS:AtomicU32=AtomicU32::new(0);
    struct ResourceModulePin;
    impl ResourceModulePin{fn acquire()->Result<Self>{let status=PIN_STATUS.load(Ordering::Acquire);if status==0{Ok(Self)}else{Err(status)}}}
    impl Drop for ResourceModulePin{fn drop(&mut self){PIN_DROPS.fetch_add(1,Ordering::AcqRel);}}
    static BLOCK_ONLINE:[AtomicBool;SMP_MAX_CPUS]=[const{AtomicBool::new(false)};SMP_MAX_CPUS];
    struct Mutex<T>(std::sync::Mutex<T>);
    impl<T> Mutex<T>{fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
    type ContextMutex=Mutex<&'static mut CpuContext>;
    static PUBLISHED:AtomicPtr<Mutex<&'static mut CpuContext>>=AtomicPtr::new(ptr::null_mut());
    struct CpuRequest{array:usize,count:usize}
    struct UserSlice{array:usize,length:usize}
    impl UserSlice{
        fn new(array:usize,length:usize)->Self{Self{array,length}}
        fn reader(self)->Self{self}
        fn read<T:Copy>(&mut self)->Result<T>{
            if self.length<std::mem::size_of::<T>(){return Err(EINVAL);}
            let result=unsafe{ptr::read_unaligned(self.array as *const T)};
            self.array+=std::mem::size_of::<T>();self.length-=std::mem::size_of::<T>();Ok(result)
        }
    }
    fn observed_cpu(cpu:usize,_read:&CpuReadGuard,_hotplug:&DeviceHotplugGuard)->Result<HostCpuSnapshot>{
        Ok(HostCpuSnapshot{hardware_id:0x20+cpu as u32+if bindings::HARDWARE_CHANGED.load(Ordering::Acquire){1}else{0},
            numa_node:1+u32::from(bindings::NODE_CHANGED.load(Ordering::Acquire)),online:bindings::online(cpu)})
    }
    unsafe fn native_reset_secondary_cpu_via_init(_apic_id:u32){}
    // REAL_CPU_TYPES
    impl CpuContext {
        // REAL_CPU_METHODS
    }
    fn owner()->OsToken{unsafe{OsToken::from_ihk_lease_v2(7,91).unwrap()}}
    fn boot()->super::smp_memory::ShutdownBoot{super::smp_memory::ShutdownBoot{owner:owner(),epoch:17}}
    fn request(context:&mut CpuContext,cpus:&[i32],reserve:bool)->Result<isize>{context.change(&CpuRequest{array:cpus.as_ptr() as usize,count:cpus.len()},reserve)}
    fn setup()->&'static Mutex<&'static mut CpuContext>{
        bindings::reset();super::smp_memory::STATUS.store(0,Ordering::Release);super::smp_memory::COMMITS.store(0,Ordering::Release);
        PIN_STATUS.store(0,Ordering::Release);PIN_DROPS.store(0,Ordering::Release);
        let mut context=Box::new(CpuContext::new());
        for cpu in 0..4{context.table.add_online_cpu(cpu,0x20+cpu as u32,1).unwrap();
            context.devices[cpu]=Some(CpuDevice((0x1000+cpu) as *mut bindings::device,Arc::new(super::smp_topology::fixture_cpu(cpu))));}
        for flag in &BLOCK_ONLINE{flag.store(false,Ordering::Release);}
        let mutex=Box::leak(Box::new(Mutex(std::sync::Mutex::new(Box::leak(context)))));
        PUBLISHED.store(mutex,Ordering::Release);mutex
    }
    fn assign(context:&mut CpuContext,owner:OsToken){let mut transaction=context.table.prepare_assign(owner,&[1,2],&mut context.journal).unwrap();transaction.begin_external_effects().unwrap();transaction.commit().unwrap();}
    fn assigned()->&'static Mutex<&'static mut CpuContext>{
        let mutex=setup();let mut context=mutex.lock();request(&mut context,&[1,2],true).unwrap();
        let context=&mut **context;assign(context,owner());
        context.reset_shutdown_boot(&boot(),&DeviceHotplugGuard::lock()).unwrap();mutex
    }
    fn shutdown()->&'static Mutex<&'static mut CpuContext>{let mutex=assigned();reconcile_shutdown_boot(boot()).unwrap();mutex}
    fn assert_clean_online(context:&CpuContext){
        for cpu in [1,2]{let slot=context.table.slot(cpu).unwrap();assert_eq!(slot.state(),CpuState::Online);assert_eq!(slot.owner(),None);
            assert!(context.devices[cpu].is_some());assert!(!context.shutdown_journal[cpu-1].recorded);assert!(!BLOCK_ONLINE[cpu].load(Ordering::Acquire));assert!(bindings::online(cpu));}
        assert!(!context.poisoned);assert!(context.pin.is_none());
    }
    #[test]fn same_device_shutdown_then_reserve_keeps_discovery_and_releases_os_owners(){
        let mutex=shutdown();let mut context=mutex.lock();assert_clean_online(&context);
        assert_eq!(bindings::DROPS.load(Ordering::Acquire),0);assert_eq!(super::smp_memory::COMMITS.load(Ordering::Acquire),1);
        assert_eq!(PIN_DROPS.load(Ordering::Acquire),1);
        assert_eq!(request(&mut context,&[1,2],true),Ok(0));
        for cpu in [1,2]{assert_eq!(context.table.slot(cpu).unwrap().state(),CpuState::Available);assert!(BLOCK_ONLINE[cpu].load(Ordering::Acquire));assert!(!bindings::online(cpu));}
        assert_eq!(request(&mut context,&[1,2],false),Ok(0));assert_clean_online(&context);
        drop(context);bindings::TRACK_TEARDOWN.store(true,Ordering::Release);
        let mutex=unsafe{Box::from_raw(mutex as *const _ as *mut Mutex<&'static mut CpuContext>)};
        drop(CpuController{mutex:Pin::new(mutex),hotplug_state:11,irq_target_state:12});
        assert!(PUBLISHED.load(Ordering::Acquire).is_null());assert_eq!(bindings::REMOVALS.load(Ordering::Acquire),2);
        assert_eq!(bindings::DROPS.load(Ordering::Acquire),4);
    }
    #[test]fn repeated_second_boot_assignment_and_shutdown_preserve_new_generation(){
        let mutex=shutdown();{let mut guard=mutex.lock();let context=&mut **guard;
            request(context,&[1,2],true).unwrap();let next=unsafe{OsToken::from_ihk_lease_v2(7,92).unwrap()};
            assign(context,next);
            let next_boot=super::smp_memory::ShutdownBoot{owner:next,epoch:17};context.reset_shutdown_boot(&next_boot,&DeviceHotplugGuard::lock()).unwrap();}
        assert_eq!(reconcile_shutdown_boot(boot()),Err(EIO));
        assert_eq!(super::smp_memory::COMMITS.load(Ordering::Acquire),1);
        let next=unsafe{OsToken::from_ihk_lease_v2(7,92).unwrap()};reconcile_shutdown_boot(super::smp_memory::ShutdownBoot{owner:next,epoch:17}).unwrap();
        assert_clean_online(&mutex.lock());assert_eq!(super::smp_memory::COMMITS.load(Ordering::Acquire),2);
    }
    #[test]fn missing_replaced_offline_topology_hardware_and_node_fail_before_effect(){
        for kind in 0..7{let mutex=shutdown();let mut context=mutex.lock();let before=bindings::OFFLINES.load(Ordering::Acquire);
            match kind{0=>bindings::missing(),1=>bindings::replace(),2=>bindings::set_online(1,false),3=>bindings::TOPOLOGY_CHANGED.store(true,Ordering::Release),
                4=>bindings::HARDWARE_CHANGED.store(true,Ordering::Release),5=>bindings::NODE_CHANGED.store(true,Ordering::Release),_=>{context.devices[1].take();}}
            assert!(request(&mut context,&[1,2],true).is_err(),"kind={kind}");assert_eq!(bindings::OFFLINES.load(Ordering::Acquire),before);
            for cpu in [1,2]{assert_eq!(context.table.slot(cpu).unwrap().state(),CpuState::Online);assert_eq!(context.table.slot(cpu).unwrap().owner(),None);assert!(!BLOCK_ONLINE[cpu].load(Ordering::Acquire));}
            assert!(!context.poisoned);assert!(context.pin.is_none());}
    }
    #[test]fn module_pin_capture_and_offline_errors_unwind_without_discarding_device(){
        for kind in 0..3{let mutex=shutdown();let mut context=mutex.lock();
            match kind{0=>PIN_STATUS.store(-19,Ordering::Release),1=>bindings::CAPTURE_STATUS.store(-12,Ordering::Release),_=>bindings::OFFLINE_STATUS.store(-5,Ordering::Release)}
            assert_eq!(request(&mut context,&[1,2],true),Err(match kind{0=>-19,1=>-12,_=>-5}));assert_clean_online(&context);
            assert_eq!(bindings::DROPS.load(Ordering::Acquire),0);}
    }
    #[test]fn failed_memory_commit_epoch_and_owner_preserve_owners_devices_and_journal(){
        for kind in 0..4{let mutex=assigned();let mut target=boot();
            match kind{0=>super::smp_memory::STATUS.store(-5,Ordering::Release),1=>target.epoch=18,2=>target.owner=unsafe{OsToken::from_ihk_lease_v2(7,90).unwrap()},_=>target.owner=unsafe{OsToken::from_ihk_lease_v2(8,91).unwrap()}}
            assert!(reconcile_shutdown_boot(target).is_err());let mut context=mutex.lock();
            assert_eq!(super::smp_memory::COMMITS.load(Ordering::Acquire),0);assert_eq!(bindings::DROPS.load(Ordering::Acquire),0);
            for cpu in [1,2]{assert_eq!(context.table.slot(cpu).unwrap().owner(),Some(owner()));assert!(context.devices[cpu].is_some());assert!(context.shutdown_journal[cpu-1].recorded);assert!(BLOCK_ONLINE[cpu].load(Ordering::Acquire));}
            assert!(context.pin.is_some());assert_eq!(request(&mut context,&[1],true),Err(EIO));assert!(context.poisoned);}
    }
    #[test]fn unscoped_compatibility_consumer_retains_discovery_for_reservation(){
        let mutex=assigned();assert_eq!(reconcile_shutdown(owner()),Ok(()));let mut context=mutex.lock();assert_clean_online(&context);assert_eq!(request(&mut context,&[1,2],true),Ok(0));
    }
}
