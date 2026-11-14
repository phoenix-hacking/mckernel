// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// NEW private app, source review/compile/runtime acceptance all remain open.
// Reuses the existing raw getpid/futex/tgkill sequence. Old mask7 acceptance is
// retained separately; this app tests ONLY components3/4/9 when executable.
mod eligibility;
use eligibility::{Area, Exposure, Component, Range, CAPACITY, REQUIRED};
use std::arch::{asm, global_asm};
use std::sync::{Arc, atomic::{AtomicI32, AtomicUsize, Ordering}};
use std::time::Duration;
global_asm!(include_str!("component_state.S"), options(att_syntax));
#[repr(C)]
struct Control { gate: AtomicI32, ready: AtomicI32, pid: i32, tid: i32 }
#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
struct Report { seeded: u32, checked: u32, restored: u32, restore_checked: u32, syscall_result: i64 }
#[repr(C)]
struct Context { mask: u64, seed: *mut Area, original: *mut Area, observed: *mut Area, ranges: *const Range, report: *mut Report, pkru_offset: u64 }
const _: () = {
    assert!(std::mem::size_of::<usize>() == 8);
    assert!(std::mem::size_of::<Control>() == 16);
    assert!(std::mem::offset_of!(Control, ready) == 4);
    assert!(std::mem::offset_of!(Control, pid) == 8);
    assert!(std::mem::offset_of!(Control, tid) == 12);
    assert!(std::mem::size_of::<Context>() == 56);
    assert!(std::mem::offset_of!(Context, seed) == 8);
    assert!(std::mem::offset_of!(Context, original) == 16);
    assert!(std::mem::offset_of!(Context, observed) == 24);
    assert!(std::mem::offset_of!(Context, ranges) == 32);
    assert!(std::mem::offset_of!(Context, report) == 40);
    assert!(std::mem::offset_of!(Context, pkru_offset) == 48);
    assert!(std::mem::size_of::<Report>() == 24);
    assert!(std::mem::offset_of!(Report, syscall_result) == 16);
    assert!(std::mem::size_of::<Range>() == 24);
    assert!(std::mem::size_of::<Area>() == CAPACITY);
    assert!(std::mem::align_of::<Area>() == 64);
};
#[no_mangle]
static COMPONENT_SIGNAL_SEEN: AtomicI32 = AtomicI32::new(0);
#[no_mangle]
static COMPONENT_HANDLER_CONTEXT: AtomicUsize = AtomicUsize::new(0);
extern "C" {
    fn component_probe(kind: u32, control: *const Control, context: *mut Context) -> i32;
    fn component_handler(signal: i32);
    // x86_64 libc signal pointer word ABI; usize also represents SIG_DFL/IGN/ERR.
    fn signal(signum: i32, handler: usize) -> usize;
}
unsafe fn raw(n: usize, a: usize, b: usize, c: usize, d: usize) -> isize {
    let r: isize;
    asm!("syscall", inlateout("rax") n => r, in("rdi") a, in("rsi") b,
         in("rdx") c, in("r10") d, lateout("rcx") _, lateout("r11") _, options(nostack));
    r
}
fn exposure() -> Exposure {
    unsafe {
        let mut e = Exposure::default();
        let max = std::arch::x86_64::__cpuid(0).eax;
        if max < 0xd { println!("USED_STATE_CPUID maximum={max:08x} insufficient"); return e; }
        let p = std::arch::x86_64::__cpuid(1); e.cpuid1_ecx = p.ecx;
        let p = std::arch::x86_64::__cpuid_count(7,0); e.cpuid7_ebx = p.ebx; e.cpuid7_ecx = p.ecx;
        println!("USED_STATE_CPUID1 ecx={:08x}",e.cpuid1_ecx);
        println!("USED_STATE_CPUID7 ebx={:08x} ecx={:08x}",e.cpuid7_ebx,e.cpuid7_ecx);
        // XGETBV itself is forbidden until both XSAVE and OSXSAVE are exposed.
        if e.cpuid1_ecx & (3<<26) != 3<<26 { return e; }
        let lo: u32; let hi: u32;
        asm!("xgetbv",in("ecx")0u32,out("eax")lo,out("edx")hi,options(nostack,nomem));
        e.xcr0 = (hi as u64)<<32 | lo as u64;
        let p = std::arch::x86_64::__cpuid_count(0xd,0);
        e.supported = (p.edx as u64)<<32 | p.eax as u64; e.extent = p.ebx;
        println!("USED_STATE_XCR0={:016x} CPUIDD0 eax={:08x} ebx={:08x} ecx={:08x} edx={:08x}",e.xcr0,p.eax,p.ebx,p.ecx,p.edx);
        for (i,id) in [3,4,9].iter().enumerate() {
            let p = std::arch::x86_64::__cpuid_count(0xd,*id);
            e.components[i] = Component { size:p.eax, offset:p.ebx, ecx:p.ecx, edx:p.edx };
            println!("USED_STATE_COMPONENT id={id} size={} offset={} ecx={:08x} edx={:08x}",p.eax,p.ebx,p.ecx,p.edx);
        }
        e
    }
}
struct Buffers { seed: Box<Area>, original: Box<Area>, observed: Box<Area>, ranges: Box<[Range;4]>, report: Box<Report>, mask:u64, pkru_offset:u64 }
impl Buffers {
    fn new(e: &Exposure, mask:u64, role:u64) -> Self {
        let (seed,ranges) = eligibility::seed(e,mask,role);
        Self { seed:Box::new(seed),original:Box::new(Area::zero()),observed:Box::new(Area::zero()),ranges:Box::new(ranges),report:Box::new(Report::default()),mask,pkru_offset:e.components[2].offset as u64 }
    }
    fn context(&mut self) -> Context { Context { mask:self.mask,seed:&mut *self.seed,original:&mut *self.original,observed:&mut *self.observed,ranges:self.ranges.as_ptr(),report:&mut *self.report,pkru_offset:self.pkru_offset } }
    fn probe(&mut self, kind:u32, c:&Control) -> Result<Report,String> {
        *self.report=Report::default(); let mut ctx=self.context();
        let rc=unsafe {component_probe(kind,c,&mut ctx)};
        let r=*self.report;
        if rc!=0 || (r.seeded,r.checked,r.restored,r.restore_checked)!=(1,1,1,1) { return Err(format!("probe kind={kind} rc={rc} report={r:?}")); }
        Ok(r)
    }
}
// Install/unblock only outside all live-register intervals. Restore both the
// previous handler and previous signal mask after the synchronous signal probe.
struct SignalGuard { old_handler:usize, old_mask:u64 }
impl SignalGuard {
    fn install() -> Result<Self,String> {
        let old_handler=unsafe {signal(10,component_handler as *const () as usize)};
        if old_handler==usize::MAX { return Err("signal install".into()); }
        let usr1=1u64<<9; let mut old_mask=0u64;
        let rc=unsafe {raw(14,1,&usr1 as *const u64 as usize,&mut old_mask as *mut u64 as usize,8)};
        if rc!=0 { unsafe {signal(10,old_handler)};return Err(format!("signal unblock={rc}")); }
        Ok(Self{old_handler,old_mask})
    }
}
impl Drop for SignalGuard {
    fn drop(&mut self) {
        COMPONENT_HANDLER_CONTEXT.store(0,Ordering::Release);
        unsafe {raw(14,2,&self.old_mask as *const u64 as usize,0,8);signal(10,self.old_handler);}
    }
}
fn run() -> Result<i32,String> {
    pair_pin()?; let e=exposure(); let s=e.select();
    for (i,id) in [3,4,9].iter().enumerate() { println!("USED_STATE_ELIGIBILITY id={id} {}",s.reasons[i]); }
    println!("USED_STATE_REQUIRED={REQUIRED:016x} SELECTED={:016x}",s.mask);
    if s.mask==0 { println!("USED_STATE_NOTEXECUTED no executable selected component"); return Ok(77); }
    let pid=unsafe {raw(39,0,0,0,0)}; let tid=unsafe {raw(186,0,0,0,0)};
    if pid<=0 || tid<=0 { return Err("positive pid/tid required".into()); }
    let self_control=Control{gate:AtomicI32::new(0),ready:AtomicI32::new(0),pid:pid as i32,tid:tid as i32};
    let mut own=Buffers::new(&e,s.mask,1);
    own.probe(0,&self_control)?;
    println!("USED_STATE_SYSCALL_PRESERVED mask={:016x} original_restored=1",s.mask);
    let c=Arc::new(Control{gate:AtomicI32::new(0),ready:AtomicI32::new(0),pid:pid as i32,tid:0});
    let wc=Arc::clone(&c);let mask=s.mask;
    let worker=std::thread::Builder::new().name("used-state-wait".into()).stack_size(128*1024).spawn(move || {
        let mut state=Buffers::new(&e,mask,1);state.probe(1,&wc)
    }).map_err(|x|format!("spawn {x}"))?;
    let mut ready=false;
    for _ in 0..2000 { if c.ready.load(Ordering::Acquire)==1 {ready=true;break;} std::thread::sleep(Duration::from_millis(1)); }
    let mut wake=Buffers::new(&e,s.mask,2);let mut woke=false;let mut wake_error=None;
    if ready {for _ in 0..2000 {
        match wake.probe(3,&c) {
            Ok(r) if r.syscall_result==1 => {woke=true;break;},
            Ok(r) if r.syscall_result==0 => {},
            Ok(r) => {wake_error=Some(format!("wake count {}",r.syscall_result));break;},
            Err(x) => {wake_error=Some(x);break;},
        }
        std::thread::sleep(Duration::from_millis(1));
    }}
    // Always join the bounded 3s raw waiter before propagating a wake/setup error.
    let wr=worker.join().map_err(|_|"waiter panic".to_string())?;
    if let Some(x)=wake_error {return Err(x);}
    if !ready || !woke {return Err("bounded blocking futex handoff absent".into());} wr?;
    println!("USED_STATE_FUTEX_PRESERVED mask={:016x} waiter_and_distinct_waker_restored=1",s.mask);
    let mut handler=Buffers::new(&e,s.mask,3);let mut handler_ctx=Box::new(handler.context());
    let guard=SignalGuard::install()?;
    COMPONENT_HANDLER_CONTEXT.store(&mut *handler_ctx as *mut Context as usize,Ordering::Release);
    own.probe(2,&self_control)?;
    if COMPONENT_SIGNAL_SEEN.load(Ordering::Acquire)!=1 {return Err("signal handler did not seed/readback distinct state".into());}
    drop(guard);
    println!("USED_STATE_SIGNAL_PRESERVED mask={:016x} distinct_handler_observed=1 original_restored=1",s.mask);
    for id in [3,4,9] {if s.mask&(1<<id)!=0 {println!("USED_STATE_COMPONENT_PRESERVED id={id} syscall=1 blocking_futex=1 signal=1 original_restore=1");}}
    if s.mask!=REQUIRED {println!("USED_STATE_PARTIAL required={REQUIRED:016x} notexecuted={:016x}",REQUIRED&!s.mask);return Ok(77);}
    println!("USED_STATE_ALL_SELECTED_PRESERVED mask={REQUIRED:016x}");Ok(0)
}
fn main() {match run() {Ok(code)=>std::process::exit(code),Err(x)=>{eprintln!("USED_STATE_FAIL {x}");std::process::exit(1);}}}

// Exact existing Rust app pair-affinity setup, outside live state.
fn pair_pin() -> Result<(), String> {
    use std::arch::asm;
    unsafe fn raw(n: usize, p: *mut u8) -> isize {
        let r: isize;
        asm!("syscall", inlateout("rax") n => r, in("rdi") 0usize,
             in("rsi") 128usize, in("rdx") p, lateout("rcx") _, lateout("r11") _, options(nostack));
        r
    }
    let text=std::env::var("PAIR_CPU").map_err(|_| "missing PAIR_CPU")?;
    let cpu:usize=text.parse().map_err(|_| "invalid PAIR_CPU")?;
    if cpu>=1024 || cpu.to_string()!=text { return Err("noncanonical PAIR_CPU".into()); }
    let mut mask=[0u8;128];
    let n=unsafe {raw(204,mask.as_mut_ptr())};
    if n<=0 || n>128 || mask[cpu/8]&(1<<(cpu%8))==0 { return Err("assigned CPU not inherited".into()); }
    let mut one=[0u8;128]; one[cpu/8]=1<<(cpu%8);
    if unsafe {raw(203,one.as_mut_ptr())}!=0 { return Err("setaffinity failed".into()); }
    mask.fill(0);
    let n=unsafe {raw(204,mask.as_mut_ptr())};
    if n<=0 || n>128 || mask!=one { return Err("exact assigned CPU not confirmed".into()); }
    Ok(())
}
