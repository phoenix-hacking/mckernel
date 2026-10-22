use core::ffi::c_void;
type CInt=i32;type CLong=i64;type CULong=u64;type SizeT=usize;
#[repr(C)]
pub struct X86BasicRegs {
    pub r15: CULong,
    pub r14: CULong,
    pub r13: CULong,
    pub r12: CULong,
    pub rbp: CULong,
    pub rbx: CULong,
    pub r11: CULong,
    pub r10: CULong,
    pub r9: CULong,
    pub r8: CULong,
    pub rax: CULong,
    pub rcx: CULong,
    pub rdx: CULong,
    pub rsi: CULong,
    pub rdi: CULong,
    pub orig_rax: CULong,
    pub rip: CULong,
    pub cs: CULong,
    pub rflags: CULong,
    pub rsp: CULong,
    pub ss: CULong,
}
#[repr(C)]
pub struct X86Sregs {
    pub fs_base: CULong,
    pub gs_base: CULong,
    pub ds: CULong,
    pub es: CULong,
    pub fs: CULong,
    pub gs: CULong,
}
#[repr(C)]
pub struct X86UserContext {
    pub sr: X86Sregs,
    pub is_gpr_valid: u8,
    pub is_sr_valid: u8,
    pub spare_flags6: u8,
    pub spare_flags5: u8,
    pub spare_flags4: u8,
    pub spare_flags3: u8,
    pub spare_flags2: u8,
    pub spare_flags1: u8,
    pub gpr: X86BasicRegs,
}
#[repr(C)]
pub struct SigStack {
    pub ss_sp: *mut c_void,
    pub ss_flags: CInt,
    pub padding: CInt,
    pub ss_size: SizeT,
}
#[repr(C)]
pub union SigVal {
    pub sival_int: CInt,
    pub sival_ptr: *mut c_void,
}
#[repr(C)]
pub struct SigInfoKill {
    pub si_pid: CInt,
    pub si_uid: CInt,
}
#[repr(C)]
pub struct SigInfoTimer {
    pub si_tid: CInt,
    pub si_overrun: CInt,
    pub si_sigval: SigVal,
}
#[repr(C)]
pub struct SigInfoRt {
    pub si_pid: CInt,
    pub si_uid: CInt,
    pub si_sigval: SigVal,
}
#[repr(C)]
pub struct SigInfoChild {
    pub si_pid: CInt,
    pub si_uid: CInt,
    pub si_status: CInt,
    pub padding: CInt,
    pub si_utime: CLong,
    pub si_stime: CLong,
}
#[repr(C)]
pub struct SigInfoFault {
    pub si_addr: *mut c_void,
}
#[repr(C)]
pub struct SigInfoPoll {
    pub si_band: CLong,
    pub si_fd: CInt,
}
#[repr(C)]
pub union SigInfoFields {
    pub pad: [CInt; 28],
    pub kill: core::mem::ManuallyDrop<SigInfoKill>,
    pub timer: core::mem::ManuallyDrop<SigInfoTimer>,
    pub rt: core::mem::ManuallyDrop<SigInfoRt>,
    pub sigchld: core::mem::ManuallyDrop<SigInfoChild>,
    pub sigfault: core::mem::ManuallyDrop<SigInfoFault>,
    pub sigpoll: core::mem::ManuallyDrop<SigInfoPoll>,
}
#[repr(C)]
pub struct SigInfo {
    pub si_signo: CInt,
    pub si_errno: CInt,
    pub si_code: CInt,
    pub padding: CInt,
    pub sifields: SigInfoFields,
}
const UNBLOCKABLE:CULong=(1<<8)|(1<<18);
type CopyFrom=unsafe extern "C" fn(*mut u8,CULong,SizeT)->CLong;
#[repr(C)]
pub struct Frame {
    pub(crate) flags: CULong,
    pub(crate) link: *mut c_void,
    pub(crate) sigstack: SigStack,
    pub(crate) regs: [CULong; 23],
    pub(crate) fpregs: *mut c_void,
    pub(crate) reserve: [CULong; 8],
    pub(crate) sigmask: [CULong; 16],
    pub(crate) info: SigInfo,
}
#[no_mangle]
pub unsafe extern "C" fn native_signal_context_prepare_result(
    regs: *const X86UserContext,
    saved_mask: CULong,
    result: CULong,
    number: CInt,
    restart: CInt,
    frame: *mut Frame,
    copy_from: Option<CopyFrom>,
) -> CLong {
    if regs.is_null() || frame.is_null() {
        return -14;
    }
    let gpr = &(*regs).gpr;
    let mut rip = gpr.rip;
    let mut rax = result;
    if restart != 0 {
        if number < 0 {
            return -22;
        }
        let Some(instruction) = rip.checked_sub(2) else {
            return -14;
        };
        let Some(copy) = copy_from else { return -14 };
        let mut opcode = [0u8; 2];
        if copy(opcode.as_mut_ptr(), instruction, opcode.len()) != 0 {
            return -14;
        }
        if opcode != [0x0f, 0x05] {
            return -22;
        }
        rip = instruction;
        rax = number as CULong;
    }
    let frame = &mut *frame;
    frame.regs = [
        gpr.r8,
        gpr.r9,
        gpr.r10,
        gpr.r11,
        gpr.r12,
        gpr.r13,
        gpr.r14,
        gpr.r15,
        gpr.rdi,
        gpr.rsi,
        gpr.rbp,
        gpr.rbx,
        gpr.rdx,
        rax,
        gpr.rcx,
        gpr.rsp,
        rip,
        gpr.rflags,
        (gpr.cs & 0xffff) | ((gpr.ss & 0xffff) << 48),
        gpr.orig_rax,
        0,
        saved_mask & !UNBLOCKABLE,
        0,
    ];
    frame.sigmask = [0; 16];
    frame.sigmask[0] = saved_mask & !UNBLOCKABLE;
    0
}


extern "C" {fn fixture_produce(vector:u64);}
static mut LAST:(u64,u64,u64,u8,u8)=(0,0,0,0,0);
static mut NEST:bool=false;
#[no_mangle]
pub unsafe extern "C" fn handle_interrupt(vector:u64, ctx:*const X86UserContext){
 assert_eq!((*ctx).gpr.orig_rax,vector,"kernel dispatch convention");
 assert_eq!((*ctx).is_gpr_valid,1);
 if vector==6 && !NEST {
  NEST=true;fixture_produce(32);NEST=false;
  assert_eq!(LAST.0,32);assert_eq!(LAST.1,0);assert_eq!(LAST.2,32);
 }
 let mut f:Frame=core::mem::zeroed();
 assert_eq!(native_signal_context_prepare_result(ctx,0,17,-1,0,&mut f,None),0);
 assert_eq!((*ctx).gpr.orig_rax,vector,"user frame must not mutate kernel context");
 LAST=(f.regs[19],f.regs[20],vector,(*ctx).spare_flags6,(*ctx).spare_flags5);
}
fn main(){unsafe{
 assert_eq!(core::mem::size_of::<X86UserContext>(),224);
 assert_eq!(core::mem::offset_of!(X86UserContext,spare_flags6),50);
 assert_eq!(core::mem::offset_of!(X86UserContext,spare_flags5),51);
 assert_eq!(core::mem::offset_of!(X86UserContext,gpr),56);
 assert_eq!(core::mem::offset_of!(Frame,regs)+19*8,192);
 assert_eq!(core::mem::offset_of!(Frame,regs)+20*8,200);
 // Repeated #UD and non-UD entries exercise reused dirty stack flags.
 let candidate=cfg!(candidate);
 for vector in [6,32,0,6,4,7,255,6,32]{
  fixture_produce(vector);
  let expected=if candidate&&vector==6 {(0,6)}else{(vector,0)};
  assert_eq!((LAST.0,LAST.1),expected);
  if vector!=6 {assert_eq!((LAST.3,LAST.4),(0,0));}
 }
 // Unknown/partial/stale metadata must never be inferred as #UD.
 for (a,b,e) in [(0,0,6),(0xa5,0,6),(0,6,6),(0xa5,6,5),(0xa5,0xa5,6),(0xff,6,6)]{
  let mut c:X86UserContext=core::mem::zeroed();c.spare_flags6=a;c.spare_flags5=b;c.gpr.orig_rax=e;
  let mut f:Frame=core::mem::zeroed();
  assert_eq!(native_signal_context_prepare_result(&c,0,17,-1,0,&mut f,None),0);
  assert_eq!((f.regs[19],f.regs[20]),(e,0));
 }
 println!("actual producer/consumer {}: 9 sequential + 3 nested + 6 unknown metadata cases PASS; kernel synthetic dispatch word unchanged",if candidate{"candidate"}else{"baseline"});
 fixture_produce(6);println!("actual #UD userframe REG_ERR={} REG_TRAPNO={}",LAST.0,LAST.1);
}}
