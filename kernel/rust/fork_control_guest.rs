//! Current guest carrier and receipt observer. No task-publication, revoke
//! permit, final ACK, or terminal-release API is provided by this module.
#[path="fork_child_credits.rs"]
pub(crate) mod child_credits;
use core::ffi::c_void;
use core::mem::size_of;
use core::ptr::{addr_of, addr_of_mut, read_volatile, write, NonNull};
use crate::abi::{CInt, CLong, SyscallRequest, SyscallResponse, Thread};
use crate::fork_control_registry::{self as registry, Handle};

const EINVAL:i32=-22;const EACCES:i32=-13;const EBUSY:i32=-16;
const ENOMEM:i32=-12;const EIO:i32=-5;const EPROTO:i32=-71;
const NR_CLONE:u64=56;const MARKER:u64=0x313030434b46434d;
const SUBMITTED:u32=0;const FIRST_POSITIVE:u32=1;const RETAINED:u32=3;
const IDLE:u32=0;const PENDING:u32=1;const OBSERVED:u32=2;

// This is the packed guest identity (88 bytes), not ForkIdentityV1's 96-byte
// host ABI with reserved fields. It is metadata, never a destruction permit.
#[repr(C)]
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub struct GuestIdentity {
    pub slot:u32,pub child_pid:i32,pub generation:u64,pub parent:u64,
    pub worker:u64,pub delivery:u64,pub child:u64,pub child_mm:u64,
    pub root:u64,pub start:u64,pub length:u64,pub nonce:u64,
}
impl GuestIdentity {
    const ZERO:Self=Self{slot:0,child_pid:0,generation:0,parent:0,worker:0,
        delivery:0,child:0,child_mm:0,root:0,start:0,length:0,nonce:0};
    fn valid(&self)->bool{self.generation!=0&&self.parent!=0&&self.worker!=0
        &&self.delivery!=0&&self.child!=0&&self.child!=self.parent&&self.child_pid>0
        &&self.child_mm!=0&&geometry(self.root,self.start,self.length)&&self.nonce!=0}
}
#[repr(C)]
#[derive(Clone,Copy)]
pub struct ControlObservation {
    pub identity:GuestIdentity,pub epoch:u64,pub worker:u64,pub delivery:u64,
    pub response:u64,pub state:u32,pub error:i32,
}
impl ControlObservation {
    const ZERO:Self=Self{identity:GuestIdentity::ZERO,epoch:0,worker:0,delivery:0,
        response:0,state:IDLE,error:0};
}
struct ControlPending {
    request:usize,thread:usize,cpu:i32,args:[u64;6],state:u32,error:i32,
    observation:ControlObservation,
}
impl ControlPending {
    const ZERO:Self=Self{request:0,thread:0,cpu:0,args:[0;6],state:IDLE,error:0,
        observation:ControlObservation::ZERO};
}

/// Registry owns this immovable heap object. The unsafe original constructor
/// caller owns the private child/CPU credits; no numeric refcount mints them.
/// After begin, no API frees this object or releases those caller credits.
#[repr(C,align(8))]
pub(crate) struct Carrier {
    handle:Handle,parent:usize,child:usize,request:usize,cpu:i32,initial_args:[u64;6],
    physical:u64,nonce:u64,root:u64,start:u64,length:u64,phase:u32,error:i32,
    owned_credits:Option<child_credits::ChildCredits>,
    owned_request:Option<child_credits::ForkRequestSlot>,
    identity:GuestIdentity,control:ControlPending,bytes:[u8;128],
}
unsafe extern "C" { fn do_syscall(request:*mut SyscallRequest,cpu:CInt)->CLong; }

fn geometry(root:u64,start:u64,length:u64)->bool{root!=0&&root%4096==0&&start%4096==0
    &&length!=0&&length%4096==0&&start.checked_add(length).is_some()}
fn transport_error(result:i64)->i32{
    i32::try_from(result).ok().filter(|error|*error<0).unwrap_or(EPROTO)
}
fn word(bytes:&[u8;128],at:usize)->u64{u64::from_le_bytes(bytes[at..at+8].try_into().unwrap())}
fn integer(bytes:&[u8;128],at:usize)->u32{u32::from_le_bytes(bytes[at..at+4].try_into().unwrap())}
fn put(bytes:&mut[u8;128],at:usize,value:u64){bytes[at..at+8].copy_from_slice(&value.to_le_bytes());}
fn key(bytes:&[u8;128])->GuestIdentity{GuestIdentity{slot:integer(bytes,40),
    child_pid:integer(bytes,44)as i32,generation:word(bytes,48),parent:word(bytes,56),
    worker:word(bytes,64),delivery:word(bytes,72),child:word(bytes,80),child_mm:word(bytes,88),
    root:word(bytes,96),start:word(bytes,104),length:word(bytes,112),nonce:word(bytes,120)}}
unsafe fn snapshot(carrier:&Carrier)->[u8;128]{
    let mut bytes=[0;128];for(i,b)in bytes.iter_mut().enumerate(){*b=read_volatile(carrier.bytes.as_ptr().add(i));}bytes
}
fn carrier_geometry(carrier:&Carrier,identity:&GuestIdentity)->bool{
    identity.valid()&&identity.root==carrier.root&&identity.start==carrier.start
        &&identity.length==carrier.length&&identity.nonce==carrier.nonce}

/// # Safety
/// ONLY the exact successful normal non-CLONE_VM constructor may call this
/// before publication. Caller keeps parent active and the private child/VM,
/// thread/process credits and reserved CPU until a separately authenticated
/// terminal/handoff. This function cannot create that lifetime from pointers.
/// On failure request/output and caller's child credits are unchanged.
#[no_mangle]
pub(crate) unsafe extern "C" fn process_fork_guest_carrier_create_current_v1(
    request:*mut SyscallRequest,parent:*mut Thread,child:*mut Thread,out:*mut Handle,
)->CInt{
    if out.is_null(){return EINVAL;}
    match create_private_carrier_current(request,parent,child){
        Ok(pointer)=>{write(out,pointer.as_ref().handle);0},Err(error)=>error,
    }
}

/// Private producer initialization authority only. On success the registry owns
/// the allocation, but this unique producer may finish direct initialization
/// before begin makes it discoverable. No handle/pointer escapes that interval.
unsafe fn create_private_carrier_current(
    request:*mut SyscallRequest,parent:*mut Thread,child:*mut Thread,
)->Result<NonNull<Carrier>,i32>{
    if request.is_null()||parent.is_null()||child.is_null()||parent==child{return Err(EINVAL);}
    let current=crate::cls::get_this_cpu_local_var();
    if current.is_null()||(*current).current!=parent{return Err(EACCES);}
    let proc=(*child).proc;let parent_proc=(*parent).proc;
    if proc.is_null()||parent_proc.is_null()||proc==parent_proc||(*child).vm.is_null()
        ||(*child).vm==(*parent).vm
        ||(*proc).parent!=parent_proc||(*proc).main_thread!=child
        ||(*proc).vm!=(*child).vm||(*(*child).vm).proc!=proc.cast::<c_void>()
        ||(*child).cpu_id<0||!(*child).sched_list.next.is_null()||!(*child).sched_list.prev.is_null()
    {return Err(EACCES);}
    let original=(*request).args;
    if (*request).number!=NR_CLONE||matches!(original[0],1|2|3)
        ||!geometry(original[3],original[1],original[2]){return Err(EINVAL);}
    let Ok(bytes)=i32::try_from(size_of::<Carrier>())else{return Err(EINVAL);};
    let raw=crate::mem_helpers::kmalloc(bytes,0).cast::<Carrier>();
    let Some(pointer)=NonNull::new(raw)else{return Err(ENOMEM);};
    write(raw,Carrier{handle:Handle::EMPTY,parent:parent as usize,child:child as usize,
        request:request as usize,cpu:(*parent).cpu_id,initial_args:original,physical:0,nonce:0,root:original[3],
        start:original[1],length:original[2],phase:SUBMITTED,error:0,
        owned_credits:None,owned_request:None,
        identity:GuestIdentity::ZERO,control:ControlPending::ZERO,bytes:[0;128]});
    let physical=crate::x86_memory_helpers::virt_to_phys(addr_of_mut!((*raw).bytes).cast::<c_void>())as u64;
    if physical==0||physical%8!=0||physical.checked_add(128).is_none(){crate::mem_helpers::kfree(raw.cast());return Err(EINVAL);}
    let handle=match registry::insert_private(pointer){Ok(handle)=>handle,Err((error,pointer))=>{
        crate::mem_helpers::kfree(pointer.as_ptr().cast());return Err(error);}};
    // Private entries are excluded from discovery; no pointer has escaped.
    (*raw).handle=handle;(*raw).physical=physical;(*raw).nonce=handle.epoch;
    let frame=&mut(*raw).bytes;frame[..8].copy_from_slice(b"MCFKQ001");
    frame[8..10].copy_from_slice(&1u16.to_le_bytes());frame[10..12].copy_from_slice(&56u16.to_le_bytes());
    frame[12..16].copy_from_slice(&128u32.to_le_bytes());frame[16..20].copy_from_slice(&1u32.to_le_bytes());
    put(frame,24,handle.epoch);put(frame,32,original[3]);put(frame,40,original[1]);put(frame,48,original[2]);
    (*request).args[4]=physical;(*request).args[5]=MARKER;(*raw).initial_args=(*request).args;
    Ok(pointer)
}
/// Mark nonfreeable BEFORE actual request publication. No callback/lifetime
/// authority is inferred from the handle, and no strong default hook is added.
#[no_mangle]
pub(crate) unsafe extern "C" fn process_fork_guest_carrier_begin_current_v1(handle:Handle)->CInt{
    registry::begin(handle).map_or_else(|e|e,|_|0)
}
#[no_mangle]
pub(crate) unsafe extern "C" fn process_fork_guest_carrier_cancel_current_v1(handle:Handle)->CInt{
    match registry::cancel(handle){Ok(pointer)=>{crate::mem_helpers::kfree(pointer.as_ptr().cast());0},Err(e)=>e}
}
#[no_mangle]
pub(crate) unsafe extern "C" fn process_fork_guest_carrier_retain_current_v1(handle:Handle)->CInt{
    registry::retain(handle).map_or_else(|e|e,|_|0)
}

fn first_receipt(carrier:&mut Carrier,frame:&[u8;128],result:i64)->Result<(),i32>{
    if frame[..8]!=*b"MCFKW001"||frame[8..12]!=[1,0,40,0]
        ||integer(frame,12)!=128||integer(frame,16)!=1||integer(frame,20)!=0
        ||word(frame,24)!=1||result<=0||word(frame,32)!=result as u64{return Err(EPROTO);}
    let identity=key(frame);
    if !carrier_geometry(carrier,&identity)||identity.child_pid as i64!=result{return Err(EACCES);}
    carrier.identity=identity;carrier.phase=FIRST_POSITIVE;Ok(())
}
fn control_receipt(carrier:&Carrier,frame:&[u8;128],response:u64)->Result<ControlObservation,i32>{
    if frame[..8]!=*b"MCFKR001"{return Err(EPROTO);}
    let identity=key(frame);let epoch=word(frame,8);let worker=word(frame,16);let delivery=word(frame,24);
    if identity!=carrier.identity||!carrier_geometry(carrier,&identity)||epoch==0||worker==0
        ||delivery==0||delivery==identity.delivery||word(frame,32)!=response{return Err(EACCES);}
    Ok(ControlObservation{identity,epoch,worker,delivery,response,state:OBSERVED,error:0})
}

struct ReplyContext{request:*mut SyscallRequest,response:*mut SyscallResponse,cpu:i32,thread:*mut Thread}
unsafe fn observe_one(pointer:NonNull<Carrier>,context:&ReplyContext)->i32{
    let carrier=&mut*pointer.as_ptr();
    let control=carrier.control.state==PENDING&&carrier.control.request==context.request as usize
        &&carrier.control.thread==context.thread as usize;
    let first=carrier.phase==SUBMITTED&&carrier.request==context.request as usize
        &&carrier.parent==context.thread as usize&&(*context.request).args[4]==carrier.physical;
    if !control&&!first{return 0;}
    let request=&*context.request;let response=&*context.response;
    let expected=if control{carrier.control.args}else{carrier.initial_args};
    let physical=crate::x86_memory_helpers::virt_to_phys(context.response.cast::<c_void>())as u64;
    let same_payload=crate::x86_memory_helpers::virt_to_phys(addr_of_mut!(carrier.bytes).cast::<c_void>())as u64==carrier.physical;
    let response_end=physical.checked_add(size_of::<SyscallResponse>()as u64);
    let carrier_end=carrier.physical.checked_add(128);
    let mut error=0;
    if request.number!=NR_CLONE||request.args!=expected||request.rtid!=(*context.thread).tid
        ||request.ttid!=0||request.valid!=0
        ||request.rtid<=0||context.cpu<0||context.cpu!=if first{carrier.cpu}else{carrier.control.cpu}
        ||physical==0||physical%8!=0||response_end.is_none()||carrier_end.is_none()
        ||!same_payload||response.stid<=0
    {error=EACCES;}
    // The real outer wait has just acquired this SAME completed response.
    if crate::x86_cpu_helpers::smp_load_acquire_ulong(addr_of!(response.status))!=1{error=EPROTO;}
    if let(Some(response_end),Some(carrier_end))=(response_end,carrier_end){
        if physical<carrier_end&&carrier.physical<response_end{error=EACCES;}
    }
    if control&&response.ret!=0{error=transport_error(response.ret);}
    if error==0{
        let frame=snapshot(carrier);
        if first{if let Err(e)=first_receipt(carrier,&frame,response.ret){error=e;}}
        else{match control_receipt(carrier,&frame,physical){Ok(observation)=>{
            // First bind of opaque IHK epoch/worker/delivery, ONLY after the
            // exact actual response Acquire. Registry epoch is unrelated.
            carrier.control.observation=observation;carrier.control.state=OBSERVED;
        },Err(e)=>error=e}}
    }
    if error!=0{carrier.error=error;carrier.phase=RETAINED;carrier.control.error=error;carrier.control.state=RETAINED;return error;}
    1
}
/// Actual selected outer syscall-return consumer. Ordinary/nested unrelated
/// returns are no-ops. No Response ret/status or task/destruction phase changes.
pub(crate) unsafe fn observe_fork_control_reply(request:*mut SyscallRequest,response:*mut SyscallResponse,cpu:CInt,thread:*mut Thread){
    if request.is_null()||response.is_null()||thread.is_null()||(*request).number!=NR_CLONE||(*request).args[5]!=MARKER{return;}
    let mut handles=[Handle::EMPTY;registry::CAPACITY];registry::snapshot_handles(&mut handles);
    let context=ReplyContext{request,response,cpu,thread};
    for handle in handles{if handle.epoch==0{continue;}
        let mut matched=false;
        let result=registry::visit(handle,|pointer|{let result=observe_one(pointer,&context);matched=result!=0;result});
        if result==1{break;}if matched&&result<0{let _=registry::retain(handle);break;}
    }
}

struct SubmitGuard{handle:Handle,armed:bool}
impl Drop for SubmitGuard{fn drop(&mut self){if !self.armed{return;}
    unsafe{let _=registry::visit(self.handle,|pointer|{let c=&mut*pointer.as_ptr();
        if c.control.state==PENDING{c.control.state=RETAINED;c.control.error=EIO;c.phase=RETAINED;}0});}
    let _=registry::retain(self.handle);
}}
/// Genuine current-kernel nr56/selector2 producer. The first positive receipt
/// must already have been consumed by the actual wait hook. Success reports
/// observation only, never a revoke permit, final ACK or runnable child.
#[no_mangle]
pub(crate) unsafe extern "C" fn process_fork_guest_control_submit_current_v1(handle:Handle,out:*mut ControlObservation)->CInt{
    if out.is_null(){return EINVAL;}
    let cls=crate::cls::get_this_cpu_local_var();if cls.is_null(){return EACCES;}
    let thread=(*cls).current;if thread.is_null(){return EACCES;}let cpu=(*thread).cpu_id;if cpu<0{return EACCES;}
    let mut request=SyscallRequest{rtid:0,ttid:0,valid:0,number:NR_CLONE,args:[0;6]};
    let address=addr_of_mut!(request)as usize;
    let prepared=registry::visit(handle,|pointer|{
        let c=&mut*pointer.as_ptr();
        if c.handle!=handle||c.parent!=thread as usize||c.phase!=FIRST_POSITIVE
            ||!carrier_geometry(c,&c.identity)||c.control.state!=IDLE{return EBUSY;}
        request.args=[2,c.identity.child_pid as u64,c.length,c.root,c.physical,MARKER];
        c.control=ControlPending{request:address,thread:thread as usize,cpu,args:request.args,
            state:PENDING,error:0,observation:ControlObservation::ZERO};0
    });
    if prepared!=0{return prepared;}
    let mut guard=SubmitGuard{handle,armed:true};
    // No registry guard or mutable Carrier reference survives into FFI. The
    // synchronous actual wait re-enters the observer with the SAME request.
    let actual=do_syscall(addr_of_mut!(request),cpu);
    let mut observation=ControlObservation::ZERO;
    let result=registry::visit(handle,|pointer|{let c=&mut*pointer.as_ptr();
        if c.control.request!=address||c.control.thread!=thread as usize||c.control.cpu!=cpu{return EACCES;}
        if actual!=0{return transport_error(actual);}
        if c.control.state!=OBSERVED{return if c.control.error!=0{c.control.error}else{EIO};}
        observation=c.control.observation;0
    });
    if result!=0{return result;}
    write(out,observation);guard.armed=false;0
}

const _:()={assert!(size_of::<GuestIdentity>()==88);assert!(size_of::<ControlObservation>()==128);};
