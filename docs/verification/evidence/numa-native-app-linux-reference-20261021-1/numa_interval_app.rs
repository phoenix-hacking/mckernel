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
const PASS: &[u8] = b"numa allowed=1 interval=1 queries=9 mode=1 mask=1 neighbors=2 process=1 guards=1 bytes=12288 preserved=1 unmapped=1\n";

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

#[derive(PartialEq, Eq)]
struct Policy { mode: i32, mask: Option<[u64; 4]> }

fn policy(address: usize, flags: usize) -> Result<Policy, Failure> {
    let mut modes = [0x3b5a7c19i32, -1, 0x3b5a7c19];
    let mut mask = [GUARD, !0, !0, !0, !0, GUARD];
    let raw = unsafe { syscall6(GET_MEMPOLICY, [modes[1..].as_mut_ptr() as usize,
        mask[1..].as_mut_ptr() as usize, 256, address, flags, 0]) };
    require(raw == 0, "read-policy", raw)?;
    require(modes[0] == 0x3b5a7c19 && modes[2] == 0x3b5a7c19
        && mask[0] == GUARD && mask[5] == GUARD, "snapshot-guards", 0)?;
    require((0..=3).contains(&modes[1]), "read-mode", modes[1] as isize)?;
    // McKernel leaves a DEFAULT policy's mask untouched; Linux may clear it.
    // Compare every mask bit for nondefault policies, where it is meaningful.
    Ok(Policy { mode: modes[1], mask: if modes[1] == 0 { None }
        else { Some([mask[1], mask[2], mask[3], mask[4]]) } })
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

    let baseline = policy(0, 0)?;
    // Distinct from fallback: BIND=2, or PREFERRED=1 if already BIND.
    let mode: i32 = if baseline.mode == 2 { 1 } else { 2 };
    let start = base + PAGE;
    // Both addresses remain mapped, immediately outside [start,start+PAGE).
    let neighbors = [start - 1, start + PAGE];
    let before = [policy(neighbors[0], 2)?, policy(neighbors[1], 2)?];
    let expected = Policy { mode, mask: Some(selected) };
    // Even an inherited interval policy must be distinguishable from the
    // selected target policy; otherwise that neighbor cannot witness bounds.
    require(before.iter().all(|p| p != &expected), "neighbor-witness", 0)?;
    let raw = unsafe { syscall6(MBIND, [start, PAGE, mode as usize, selected.as_ptr() as usize, 256, 0]) };
    require(raw == 0, "mbind", raw)?;

    for address in [start, start + PAGE / 2, start + PAGE - 1] {
        require(policy(address, 2)? == expected, "target-policy", 0)?;
    }
    for (address, previous) in neighbors.into_iter().zip(before) {
        require(policy(address, 2)? == previous, "neighbor-policy", 0)?;
    }
    require(policy(0, 0)? == baseline, "process-policy-changed", 0)?;
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
