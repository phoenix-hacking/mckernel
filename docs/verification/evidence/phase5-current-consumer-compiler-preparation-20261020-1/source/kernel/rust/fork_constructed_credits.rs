//! Constructor-issued ownership graph for the disabled normal-fork route.
//! Two Thread references are issued by the successful constructor. Its final
//! Thread owns the VM release; that VM owns one Process release. Only the extra
//! constructor Process reference is independent. No count supplies a token.
use super::*;
use core::ffi::c_void;
// Coupled to the real process.h assertions supplied to the genuine complete C
// consumers. A fixture compile alone cannot close this production ABI check.
const _:()={assert!(core::mem::offset_of!(crate::abi::AddressSpace,nslots)==164);
    assert!(size_of::<crate::abi::CInt>()==4);
    assert!(core::mem::offset_of!(crate::abi::AddressSpace,nslots)+size_of::<crate::abi::CInt>()==168);};
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
enum Stage {Constructed,Permitted,FirstConsumed,ThreadVmDestroyed,Destroyed,
    RuntimePrepared,RuntimePublished,Uncertain}
pub(super) struct ConstructedFork {
    parent:NonNull<Thread>,child:NonNull<Thread>,process:NonNull<Process>,vm:NonNull<ProcessVm>,
    reserved_cpu:i32,stage:Stage,runtime_pin:bool,
}
unsafe extern "C" {
    fn clone_thread(parent:*mut Thread,pc:u64,sp:u64,flags:i32)->*mut Thread;
    pub(super) fn release_cpuid(cpu:i32);
}
/// # Safety
/// The actual normal do_fork callsite passes its existing reservation and live
/// parent. Output receives one unique opaque constructor result. C may borrow
/// child but must not drop/reset constructor credits while this result exists.
#[no_mangle]
pub(crate) unsafe extern "C" fn process_fork_construct_current_v1(parent:*mut Thread,pc:u64,sp:u64,
    flags:i32,reserved_cpu:i32,out:*mut *mut c_void)->*mut Thread {
    if out.is_null(){return core::ptr::null_mut();}core::ptr::write(out,core::ptr::null_mut());
    let cls=crate::cls::get_this_cpu_local_var();
    if parent.is_null()||cls.is_null()||(*cls).current!=parent||flags&0x100!=0||reserved_cpu<0{return core::ptr::null_mut();}
    // Allocate the result before entering the actual constructor. On failure
    // it has minted no child references and no destructor may be inferred.
    let storage=crate::mem_helpers::kmalloc(size_of::<ConstructedFork>() as i32,0).cast::<ConstructedFork>();
    if storage.is_null(){return core::ptr::null_mut();}
    let child=clone_thread(parent,pc,sp,flags);
    if child.is_null(){crate::mem_helpers::kfree(storage.cast());return child;}
    // This is the exact successful constructor return, before publication or
    // any C borrow. Its normal-fork contract creates the ownership graph.
    let graph=ConstructedFork{parent:NonNull::new_unchecked(parent),child:NonNull::new_unchecked(child),
        process:NonNull::new_unchecked((*child).proc),vm:NonNull::new_unchecked((*child).vm),reserved_cpu,stage:Stage::Constructed,runtime_pin:false};
    core::ptr::write(storage,graph);core::ptr::write(out,storage.cast());child
}
impl ConstructedFork {
    /// Transfer starts with a NEW checked Thread pin while the constructor
    /// still owns the unpublished child. Counts only guard this increment;
    /// constructor provenance, not a count, supplies the original graph.
    pub(super) unsafe fn prepare_runtime(&mut self)->Result<RuntimePermit,i32> {
        if self.stage!=Stage::Constructed||self.runtime_pin{return Err(EBUSY);}
        let counter=AtomicI32::from_ptr(addr_of_mut!((*self.child.as_ptr()).refcount.counter));
        let mut old=counter.load(Ordering::SeqCst);
        loop {
            if old<=0{return Err(EBUSY);}if old==i32::MAX{return Err(EOVERFLOW);}
            match counter.compare_exchange_weak(old,old+1,Ordering::SeqCst,Ordering::SeqCst){
                Ok(_)=>break,Err(actual)=>old=actual,
            }
        }
        self.runtime_pin=true;self.stage=Stage::RuntimePrepared;
        Ok(RuntimePermit{graph:NonNull::from(self)})
    }
    pub(super) fn permit(&mut self)->Result<DestructionPermit,i32>{
        if self.stage!=Stage::Constructed{return Err(EBUSY);}
        self.stage=Stage::Permitted;Ok(DestructionPermit{graph:NonNull::from(self)})
    }
    pub(super) unsafe fn matches(&self,parent:*mut Thread,child:*mut Thread,cpu:i32)->bool {
        self.stage==Stage::Constructed&&self.parent.as_ptr()==parent&&self.child.as_ptr()==child
            &&self.reserved_cpu==cpu&&(*child).proc==self.process.as_ptr()&&(*child).vm==self.vm.as_ptr()
    }
    /// Each call consumes exactly the constructor-issued graph edge once.
    /// Mark uncertain BEFORE a destructive call; no error is retried and no
    /// child/VM pointer is read after that call may have destroyed it.
    unsafe fn destroy(&mut self)->Result<(),i32> {
        if !matches!(self.stage,Stage::Constructed|Stage::Permitted){return Err(EBUSY);}
        self.stage=Stage::Uncertain;
        if crate::process_helpers::release_thread_checked(self.child.as_ptr())!=0{return Err(EBUSY);}
        self.stage=Stage::FirstConsumed;
        // The retained extra Process token pins this independent allocation.
        let command=(*self.process.as_ptr()).saved_cmdline;
        (*self.process.as_ptr()).saved_cmdline=core::ptr::null_mut();
        if !command.is_null(){crate::mem_helpers::kfree(command.cast());}
        self.stage=Stage::Uncertain;
        if crate::process_helpers::release_thread_checked(self.child.as_ptr())!=2{return Err(EBUSY);}
        self.stage=Stage::ThreadVmDestroyed;
        // The VM's embedded Process edge was consumed. This is the ONE extra
        // constructor Process edge, which still pins its main Thread pages.
        self.stage=Stage::Uncertain;
        if crate::process_helpers::release_process_checked(self.process.as_ptr())!=1{return Err(EBUSY);}
        self.stage=Stage::Destroyed;Ok(())
    }
    pub(super) fn destroyed(&self)->bool{self.stage==Stage::Destroyed}
}
/// The original graph is surrendered before the first discoverable list
/// insertion. The additional Thread pin remains Carrier-owned across exit
/// and wait. No failure/Drop retries a release or restores private cleanup.
pub(crate) struct RuntimePermit{graph:NonNull<ConstructedFork>}
impl RuntimePermit {
    pub(crate) unsafe fn publish(mut self,pid:i32,parent_cpu:i32,flags:i32,child_tid:u64)->i32 {
        let graph=self.graph.as_mut();
        if graph.stage!=Stage::RuntimePrepared||!graph.runtime_pin||pid<=0||parent_cpu<0{return EINVAL;}
        let child=graph.child.as_ptr();let process=graph.process.as_ptr();let vm=graph.vm.as_ptr();
        let space=(*vm).address_space;
        if space.is_null()||(*space).nslots<=0{return EINVAL;}
        // Real process.h has int nslots immediately followed by int pids[].
        // The successful constructor owns that flexible-array allocation.
        // sizeof(AddressSpace) may include tail padding: use the actual last
        // field's end, never assume sizeof(prefix) is offsetof(pids).
        core::ptr::write_volatile(core::ptr::addr_of_mut!((*space).nslots).add(1),pid);
        (*process).pid=pid;(*child).tid=pid;
        if flags&0x00200000!=0{(*child).clear_child_tid=child_tid as *mut i32;}
        if flags&0x01000000!=0 {
            // Match the existing native child-start put_user contract: a
            // fault, including a partial store, does not cancel the clone.
            // This exact VM, graph and new runtime pin remain owned across
            // all fault/COW effects; publication follows the store attempt.
            let _=crate::x86_memory_helpers::write_process_vm(vm,child_tid as *mut c_void,
                core::ptr::addr_of!((*child).tid).cast(),size_of::<i32>());
        }
        (*child).tlsblock_base=(*graph.parent.as_ptr()).tlsblock_base;
        (*child).parent_cpuid=parent_cpu;
        crate::x86_cpu_helpers::ihk_mc_syscall_set_ret((*child).uctx,0);
        (*child).status=1;(*process).status=1;
        if crate::process_helpers::chain_thread_checked(child)<0
            ||crate::process_helpers::chain_process_checked(process)<0 {
            graph.stage=Stage::Uncertain;return EBUSY;
        }
        // chain_thread issued the normal additional VM edge. Terminate,
        // scheduler and wait now consume the ordinary constructor graph.
        // runq_add consumes the CPU reservation; never release_cpuid here.
        let result=crate::sched_helpers::runq_add_thread_checked(child,graph.reserved_cpu);
        if result!=0{graph.stage=Stage::Uncertain;return result;}
        graph.stage=Stage::RuntimePublished;0
    }
}
/// Issued once from the Carrier-owned graph. It grants only the destructive
/// critical scope; the Carrier retains all graph/parent/CPU obligations.
pub(crate) struct DestructionPermit {graph:NonNull<ConstructedFork>}
impl DestructionPermit {
    pub(crate) unsafe fn destroy(mut self)->Result<(),i32>{self.graph.as_mut().destroy()}
}
/// Private pre-publication cleanup only. A failed/partial destructor retains
/// its opaque result and CPU obligation; C must bypass its reset-based cleanup.
#[no_mangle]
pub(crate) unsafe extern "C" fn process_fork_cancel_constructed_current_v1(token:*mut c_void)->i32 {
    if token.is_null(){return EINVAL;}
    let graph=&mut*token.cast::<ConstructedFork>();
    if graph.destroy().is_err(){return EBUSY;}
    crate::mem_helpers::kfree(token);0
}
