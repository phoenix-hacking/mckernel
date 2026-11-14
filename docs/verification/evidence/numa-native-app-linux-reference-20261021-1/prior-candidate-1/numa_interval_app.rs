// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Standalone diagnostic payload; source preparation does not release execution.
#[cfg(not(all(target_os = "linux", target_arch = "x86_64", target_pointer_width = "64")))]
compile_error!("requires Linux x86_64 LP64 syscall ABI and 4-KiB base pages");

use std::arch::asm;
use std::io::{self, Write};

const PAGE: usize = 4096;
const LEN: usize = 3 * PAGE;
const GET_MEMPOLICY: usize = 239;
const MBIND: usize = 237;
const GUARD: u64 = 0x6b9ac318e52704df;
const PASS: &[u8] = b"numa allowed=1 interval=1 queries=3 mode=1 mask=1 guards=1 bytes=12288 preserved=1 unmapped=1\n";

// No nomem option: the kernel reads and writes pointed-to application bytes.
unsafe fn syscall6(n: usize, a: [usize; 6]) -> isize {
    let result: isize;
    unsafe {
        asm!("syscall", inlateout("rax") n as isize => result,
             in("rdi") a[0], in("rsi") a[1], in("rdx") a[2],
             in("r10") a[3], in("r8") a[4], in("r9") a[5],
             lateout("rcx") _, lateout("r11") _, options(nostack));
    }
    result
}

#[derive(Debug)]
struct Failure { stage: &'static str, raw: isize }
fn require(ok: bool, stage: &'static str, raw: isize) -> Result<(), Failure> {
    if ok { Ok(()) } else { Err(Failure { stage, raw }) }
}

fn consume(base: usize) -> Result<(), Failure> {
    let mut allowed = [GUARD, 0, 0, 0, 0, GUARD];
    let raw = unsafe { syscall6(GET_MEMPOLICY, [0, allowed[1..].as_mut_ptr() as usize, 256, 0, 4, 0]) };
    require(raw == 0, "allowed", raw)?;
    require(allowed[0] == GUARD && allowed[5] == GUARD, "allowed-guards", 0)?;
    let (word, value) = allowed[1..5].iter().copied().enumerate()
        .find(|(_, value)| *value != 0).ok_or(Failure { stage: "allowed-empty", raw: 0 })?;
    // Select from the actual exposed mask, never from assumed node numbering.
    let mut selected = [0u64; 4];
    selected[word] = 1u64 << value.trailing_zeros();

    let mut baseline = -1i32;
    let raw = unsafe { syscall6(GET_MEMPOLICY, [&mut baseline as *mut i32 as usize, 0, 0, 0, 0, 0]) };
    require(raw == 0, "process-mode", raw)?;
    // Distinct from fallback: BIND=2, or PREFERRED=1 if already BIND.
    let mode: i32 = if baseline == 2 { 1 } else { 2 };
    let start = base + PAGE;
    let raw = unsafe { syscall6(MBIND, [start, PAGE, mode as usize, selected.as_ptr() as usize, 256, 0]) };
    require(raw == 0, "mbind", raw)?;

    for address in [start, start + PAGE / 2, start + PAGE - 1] {
        let mut modes = [0x3b5a7c19i32, -1, 0x3b5a7c19];
        let mut mask = [GUARD, !0, !0, !0, !0, GUARD];
        let raw = unsafe { syscall6(GET_MEMPOLICY, [modes[1..].as_mut_ptr() as usize,
            mask[1..].as_mut_ptr() as usize, 256, address, 2, 0]) };
        require(raw == 0, "address-policy", raw)?;
        require(modes[1] == mode, "policy-mode", modes[1] as isize)?;
        require(mask[1..5] == selected, "policy-mask", 0)?;
        require(modes[0] == 0x3b5a7c19 && modes[2] == 0x3b5a7c19
            && mask[0] == GUARD && mask[5] == GUARD, "snapshot-guards", 0)?;
    }
    for i in 0..LEN {
        let byte = unsafe { (base as *const u8).add(i).read_volatile() };
        require(byte == ((i * 37 + 11) % 251) as u8, "mapping-bytes", i as isize)?;
    }
    Ok(())
}

fn main() {
    // mmap(PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, fd=-1).
    let mapped = unsafe { syscall6(9, [0, LEN, 3, 0x22, usize::MAX, 0]) };
    if (-4095..0).contains(&mapped) {
        eprintln!("FAIL stage=mmap raw={mapped}");
        std::process::exit(1);
    }
    let base = mapped as usize;
    // This target's base-page ABI is checked by the kernel source. A usable
    // nonzero aligned user allocation is required before touching its bytes.
    if base == 0 || base % PAGE != 0 || base.checked_add(LEN).is_none() {
        let raw = unsafe { syscall6(11, [base, LEN, 0, 0, 0, 0]) };
        eprintln!("FAIL stage=mmap-geometry unmap_raw={raw}");
        std::process::exit(1);
    }
    for i in 0..LEN {
        unsafe { (base as *mut u8).add(i).write_volatile(((i * 37 + 11) % 251) as u8) };
    }
    let outcome = consume(base);
    // Always attempt exactly one unmap, including failed mbind/getter cases.
    let unmap = unsafe { syscall6(11, [base, LEN, 0, 0, 0, 0]) };
    if let Err(failure) = outcome {
        eprintln!("FAIL stage={} raw={} unmap_raw={unmap}", failure.stage, failure.raw);
        std::process::exit(1);
    }
    if unmap != 0 {
        eprintln!("FAIL stage=munmap raw={unmap}");
        std::process::exit(1);
    }
    let mut output = io::stdout().lock();
    if output.write_all(PASS).and_then(|_| output.flush()).is_err() {
        eprintln!("FAIL stage=stdout");
        std::process::exit(1);
    }
    std::process::exit(37);
}
