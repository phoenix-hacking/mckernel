// Private P-M07-02 userland app. No compute-kernel implementation is added.
// All live FP checks and kernel crossings are in fp_state.S, never Rust calls.
use std::arch::{asm, global_asm};
use std::sync::{Arc, Barrier};
use std::sync::atomic::AtomicU32;

global_asm!(include_str!("fp_state.S"), options(att_syntax));
const ROUNDS: u32 = 64;
#[repr(C)]
struct Slot { ready: AtomicU32, progress: AtomicU32, error: AtomicU32, pad: u32 }
impl Slot { fn new() -> Self { Self { ready: AtomicU32::new(0), progress: AtomicU32::new(0), error: AtomicU32::new(0), pad: 0 } } }
#[repr(C)]
#[derive(Default, Debug)]
struct Report { code: u32, checks: u32, peer: u32, yields: u32, restored: u32, pad: u32, original_cw: u32, original_mxcsr: u32, restored_cw: u32, restored_mxcsr: u32, syscall_result: i64 }
extern "C" { fn fp_state_probe(me: *const Slot, peer: *const Slot, pattern: *const u64, cw: u32, mxcsr: u32, report: *mut Report) -> u32; }

// Only outside the live interval. Syscall clobbers are explicit, including
// rcx/r11. No vector state is expected to survive this ordinary Rust wrapper.
unsafe fn syscall3(n: usize, a: usize, b: usize, c: usize) -> isize {
    let r: isize;
    asm!("syscall", inlateout("rax") n => r, in("rdi") a, in("rsi") b, in("rdx") c, lateout("rcx") _, lateout("r11") _, options(nostack));
    r
}
fn permitted() -> Result<[u8;128], String> {
    let mut m = [0u8;128];
    let r = unsafe { syscall3(204, 0, m.len(), m.as_mut_ptr() as usize) };
    if r <= 0 || r as usize > m.len() { return Err(format!("sched_getaffinity result={r}")); }
    if m.iter().all(|v| *v == 0) { return Err("sched_getaffinity empty".into()); }
    Ok(m)
}
fn bind(cpu: usize) -> Result<(), String> {
    let mut one = [0u8;128]; one[cpu/8] = 1 << (cpu%8);
    let r = unsafe { syscall3(203, 0, one.len(), one.as_ptr() as usize) };
    if r != 0 { return Err(format!("sched_setaffinity result={r} cpu={cpu}")); }
    if permitted()? != one { return Err("sched_getaffinity did not confirm exact one-CPU mask".into()); }
    Ok(())
}
fn gate_avx() -> Result<(), String> {
    unsafe {
        let p = std::arch::x86_64::__cpuid(1);
        if p.ecx & (1<<26 | 1<<27 | 1<<28) != (1<<26 | 1<<27 | 1<<28) { return Err("AVX/XSAVE/OSXSAVE missing".into()); }
        let lo: u32; let hi: u32;
        asm!("xgetbv", in("ecx") 0u32, out("eax") lo, out("edx") hi, options(nostack, nomem));
        if lo & 7 != 7 { return Err(format!("XCR0 x87/SSE/AVX missing lo={lo:x} hi={hi:x}")); }
    }
    Ok(())
}
fn worker(id: usize, cpu: usize, slots: Arc<[Slot;2]>, start: Arc<Barrier>) -> Result<(isize, Report), String> {
    // Perform all fallible ABI setup before the common barrier. A setup failure
    // exits the process, avoiding a stranded peer waiting at the barrier.
    if let Err(e) = bind(cpu) { eprintln!("PREREQUISITE thread{id} {e}"); std::process::exit(77); }
    let tid = unsafe { syscall3(186, 0, 0, 0) };
    if tid <= 0 { eprintln!("PREREQUISITE thread{id} gettid result={tid}"); std::process::exit(77); }
    let mut pattern = [0u64;64];
    for (lane, value) in pattern.iter_mut().enumerate() {
        *value = if id == 0 { 0x1122_3344_0000_0000 } else { 0xaabb_ccdd_0000_0000 } | (lane as u64 + 1);
    }
    let (cw, mxcsr) = if id == 0 { (0x077f, 0x3f80) } else { (0x0b7f, 0x5f80) };
    let mut report = Report::default();
    start.wait();
    let rc = unsafe { fp_state_probe(&slots[id], &slots[1-id], pattern.as_ptr(), cw, mxcsr, &mut report) };
    if rc == 110 && report.syscall_result == -38 { eprintln!("PREREQUISITE thread{id} sched_yield result=-38 (ENOSYS)"); std::process::exit(77); }
    if rc != 0 || report.code != 0 { return Err(format!("thread{id} probe {report:?} rc={rc}")); }
    if report.checks != ROUNDS || report.peer != ROUNDS || report.yields < ROUNDS || report.restored != 1 || report.original_cw != report.restored_cw || report.original_mxcsr != report.restored_mxcsr {
        return Err(format!("thread{id} report invariant {report:?}"));
    }
    if permitted()?.iter().enumerate().any(|(i, b)| *b != if i == cpu/8 { 1 << (cpu%8) } else { 0 }) { return Err(format!("thread{id} post affinity changed")); }
    Ok((tid, report))
}
fn run() -> Result<(), String> {
    if let Err(e) = gate_avx() { eprintln!("PREREQUISITE {e}"); std::process::exit(77); }
    let allowed = match permitted() { Ok(x) => x, Err(e) => { eprintln!("PREREQUISITE {e}"); std::process::exit(77); } };
    let cpu = (0..1024).find(|i| allowed[i/8] & (1 << (i%8)) != 0).unwrap();
    let slots = Arc::new([Slot::new(), Slot::new()]); let start = Arc::new(Barrier::new(2));
    let mut handles = Vec::new();
    for id in 0..2 {
        let s = Arc::clone(&slots); let b = Arc::clone(&start);
        match std::thread::Builder::new().name(format!("fp-state-{id}")).stack_size(128*1024).spawn(move || worker(id,cpu,s,b)) {
            Ok(h) => handles.push(h),
            Err(e) => { eprintln!("PREREQUISITE std thread spawn {e}"); std::process::exit(77); }
        }
    }
    let first = handles.remove(0).join().map_err(|_| "thread0 panic".to_string())??;
    let second = handles.remove(0).join().map_err(|_| "thread1 panic".to_string())??;
    if first.0 == second.0 { return Err("gettid identities are not distinct".into()); }
    println!("FPTHREAD v1 threads=2 same_permitted_cpu=1 distinct_tid=1");
    println!("thread0 rounds=64 ymm_lanes=64 peer_progress=64 yield_min=64 controls=077f/3f80 restored=1");
    println!("thread1 rounds=64 ymm_lanes=64 peer_progress=64 yield_min=64 controls=0b7f/5f80 restored=1");
    println!("FPTHREAD PASS");
    Ok(())
}
fn main() {
    if let Err(e)=pair_pin() { eprintln!("PREREQUISITE {e}"); std::process::exit(77); }
 if let Err(e) = run() { eprintln!("FAIL {e}"); std::process::exit(1); } }

// Linux x86_64/McKernel ABI. Called before any accepted body or worker spawn.
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
