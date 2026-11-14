// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private v3 causal guest payload proposal: one parent, its own traced child and private bytes.
use std::arch::asm;
use std::sync::atomic::{AtomicU32, Ordering};

const SYS_READ: usize = 0;
const SYS_WRITE: usize = 1;
const SYS_OPEN: usize = 2;
const SYS_CLOSE: usize = 3;
const SYS_CLOCK_GETTIME: usize = 228;
const SYS_MMAP: usize = 9;
const SYS_MUNMAP: usize = 11;
const SYS_NANOSLEEP: usize = 35;
const SYS_CLONE: usize = 56;
const SYS_GETPID: usize = 39;
const SYS_PTRACE: usize = 101;
const SYS_EXIT: usize = 60;
const SYS_WAIT4: usize = 61;
const SYS_KILL: usize = 62;
const MAP_BYTES: usize = 8192;
const OFFSET: usize = 4096 - 4;
const BYTES: usize = 8;
const POLLS: usize = 2000;
const APP_TIMEOUT_NS: u64 = 10_000_000_000;
const GATE_POLLS: usize = 32;
const GATE_POLL_NS: i64 = 125_000_000;
const GATE_PATH: &[u8] = b".f05-gate-31770ebb739fea402ded939617921dda\0";


#[repr(C)]
struct Timespec {
    seconds: i64,
    nanoseconds: i64,
}
#[repr(C)]
struct Control {
    ready: AtomicU32,
    command: AtomicU32,
    verified: AtomicU32,
}

// SAFETY: Linux x86_64 syscall ABI: six word arguments, signed raw result,
// rcx/r11 clobbered. Memory can change across syscall; no nomem/readonly claim.
// Callers provide live mapped ABI objects and do not retain mutable references
// to any buffer while the kernel or child may modify it.
unsafe fn syscall(n: usize, args: [usize; 6]) -> isize {
    let result: isize;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") n => result,
            in("rdi") args[0], in("rsi") args[1], in("rdx") args[2],
            in("r10") args[3], in("r8") args[4], in("r9") args[5],
            lateout("rcx") _, lateout("r11") _, options(nostack),
        );
    }
    result
}

#[derive(Clone, Copy)]
struct Budget {
    deadline_ns: u64,
}

fn monotonic_ns() -> Option<u64> {
    let mut now = Timespec { seconds: 0, nanoseconds: 0 };
    // SAFETY: live output timespec, CLOCK_MONOTONIC=1 on x86_64 Linux.
    let result = unsafe {
        syscall(SYS_CLOCK_GETTIME, [1, (&mut now as *mut Timespec) as usize, 0, 0, 0, 0])
    };
    if result != 0 || now.seconds < 0 || !(0..1_000_000_000).contains(&now.nanoseconds) {
        return None;
    }
    (now.seconds as u64).checked_mul(1_000_000_000)?.checked_add(now.nanoseconds as u64)
}

impl Budget {
    fn start() -> Result<Self, String> {
        let deadline_ns = monotonic_ns()
            .and_then(|now| now.checked_add(APP_TIMEOUT_NS))
            .ok_or_else(|| "monotonic application deadline unavailable".to_string())?;
        Ok(Self { deadline_ns })
    }

    fn live(self) -> bool {
        monotonic_ns().is_some_and(|now| now < self.deadline_ns)
    }
}

fn pause(budget: Budget, nanoseconds: i64) -> bool {
    if !budget.live() {
        return false;
    }
    let delay = Timespec { seconds: 0, nanoseconds };
    // SAFETY: delay is live. EINTR consumes a poll; no unbounded restart.
    let result = unsafe {
        syscall(SYS_NANOSLEEP, [(&delay as *const Timespec) as usize, 0, 0, 0, 0, 0])
    };
    (result == 0 || result == -4) && budget.live()
}

fn await_value(value: &AtomicU32, expected: u32, budget: Budget) -> bool {
    for _ in 0..POLLS {
        if !budget.live() {
            return false;
        }
        if value.load(Ordering::Acquire) == expected {
            return true;
        }
        if !pause(budget, 1_000_000) {
            return false;
        }
    }
    false
}

fn await_causal_gate(budget: Budget) -> Result<(), String> {
    // The agreed native supervisor creates the empty regular file in /case/work
    // before launch. HOST qualification uses an explicit controlled reference
    // gate in its own fresh cwd; that reference is never native causal proof.
    // Open/read/close entries also retry the EXISTING live-parent fork drain.
    // No kernel count, destructor or success acknowledgment is manufactured.
    for _ in 0..GATE_POLLS {
        if !budget.live() {
            return Err("original 10s application deadline exhausted at causal gate".into());
        }
        // O_RDONLY|O_NONBLOCK|O_CLOEXEC. A missing gate/empty regular-file EOF is
        // pending. Never use a FIFO or a single blocking read as the barrier.
        let fd = unsafe { syscall(SYS_OPEN, [GATE_PATH.as_ptr() as usize, 0x80800, 0, 0, 0, 0]) };
        if fd >= 0 {
            let mut bytes = [0u8; 2];
            let read = unsafe {
                syscall(SYS_READ, [fd as usize, bytes.as_mut_ptr() as usize, bytes.len(), 0, 0, 0])
            };
            let closed = unsafe { syscall(SYS_CLOSE, [fd as usize, 0, 0, 0, 0, 0]) };
            if closed != 0 {
                return Err(format!("causal gate close result={closed}"));
            }
            if read == 1 && bytes[0] == b'G' {
                if budget.live() {
                    return Ok(());
                }
                return Err("causal gate token arrived after original deadline".into());
            }
            if read > 0 {
                return Err(format!("causal gate rejected nonempty token length={read}"));
            }
            if read < 0 {
                return Err(format!("causal gate read result={read}"));
            }
        } else if fd != -2 {
            return Err(format!("causal gate open result={fd}"));
        }
        if !pause(budget, GATE_POLL_NS) {
            return Err("causal gate pacing/deadline failed".into());
        }
    }
    Err("bounded causal gate polls exhausted; parent terminal not authorized".into())
}

fn initial_byte(index: usize) -> u8 {
    0x40 + index as u8
}
fn replacement_byte(index: usize) -> u8 {
    0xa5 ^ index as u8
}

unsafe fn child(bytes: *mut u8, child_tid: *const i32, control: &Control, budget: Budget) -> ! {
    let own_pid = unsafe { syscall(SYS_GETPID, [0; 6]) };
    let tid_matches = own_pid > 0 && unsafe { child_tid.read_volatile() } == own_pid as i32;
    if tid_matches {
        for index in 0..BYTES {
            unsafe {
                bytes.add(index).write_volatile(initial_byte(index));
            }
        }
        // Exact selected slot1 is delegated: even count0 publishes a real host
        // request. Own inherited stderr and mapped buffer stay valid; no bytes
        // are written. Require the actual return before TRACEME/readiness/stop.
        let forwarded = unsafe { syscall(SYS_WRITE, [2, bytes as usize, 0, 0, 0, 0]) };
        if forwarded != 0 {
            unsafe {
                syscall(SYS_EXIT, [24, 0, 0, 0, 0, 0]);
            }
            loop {
                std::hint::spin_loop();
            }
        }
        let traced = unsafe { syscall(SYS_PTRACE, [0, 0, 0, 0, 0, 0]) };
        if traced == 0 {
            control.ready.store(1, Ordering::Release);
            let stopped = unsafe { syscall(SYS_KILL, [own_pid as usize, 19, 0, 0, 0, 0]) };
            if stopped == 0 && await_value(&control.command, 1, budget) {
                let mut matches = true;
                for index in 0..BYTES {
                    matches &=
                        unsafe { bytes.add(index).read_volatile() } == replacement_byte(index);
                }
                if matches {
                    control.verified.store(1, Ordering::Release);
                    if await_value(&control.command, 2, budget) {
                        unsafe {
                            syscall(SYS_EXIT, [0; 6]);
                        }
                    }
                }
            }
        }
    }
    // Raw exit avoids post-clone allocator/stdio/unwind and parent destructors.
    unsafe {
        syscall(SYS_EXIT, [21, 0, 0, 0, 0, 0]);
    }
    loop {
        std::hint::spin_loop();
    }
}

fn ptrace(request: usize, pid: isize, address: usize, data: usize) -> isize {
    // Raw PEEKDATA returns 0 and stores a word at the fourth argument. POKEDATA
    // consumes the fourth argument as the word itself. No libc ptrace wrapper.
    unsafe { syscall(SYS_PTRACE, [request, pid as usize, address, data, 0, 0]) }
}

fn wait_event(pid: isize, options: usize, budget: Budget) -> Result<i32, String> {
    for _ in 0..POLLS {
        if !budget.live() {
            return Err("original 10s application wait deadline exhausted".into());
        }
        let mut status = 0i32;
        // SAFETY: pid is only our unreaped positive clone result; status is live.
        let result = unsafe {
            syscall(
                SYS_WAIT4,
                [
                    pid as usize,
                    (&mut status as *mut i32) as usize,
                    options,
                    0,
                    0,
                    0,
                ],
            )
        };
        if result == pid {
            return Ok(status);
        }
        if result != 0 && result != -4 {
            return Err(format!("wait4 raw result={result}"));
        }
        if !pause(budget, 1_000_000) {
            return Err("nanosleep during reap failed".into());
        }
    }
    Err("bounded wait4 budget exhausted; retirement not established".into())
}

fn exercise(
    pid: isize,
    private: *mut u8,
    control: &Control,
    terminal_status: &mut Option<i32>,
    budget: Budget,
) -> Result<(), String> {
    let status = wait_event(pid, 3, budget)?; // WNOHANG | WUNTRACED.
    if status & 0x7f != 0x7f {
        *terminal_status = Some(status); // Terminal status was consumed: never signal that PID again.
        return Err(format!("child terminated before stop status={status}"));
    }
    if status != ((19 << 8) | 0x7f) || control.ready.load(Ordering::Acquire) != 1 {
        return Err(format!(
            "expected explicit SIGSTOP after TRACEME status={status}"
        ));
    }
    for index in 0..BYTES {
        if unsafe { private.add(index).read_volatile() } != 0 {
            return Err("parent private bytes changed after child initialization".into());
        }
    }
    let mut word = 0u64;
    let result = ptrace(2, pid, private as usize, (&mut word as *mut u64) as usize);
    let expected = u64::from_le_bytes(std::array::from_fn(initial_byte));
    if result != 0 || word != expected {
        return Err(format!("PEEKDATA raw result={result} value={word:016x}"));
    }
    let replacement = u64::from_le_bytes(std::array::from_fn(replacement_byte));
    let result = ptrace(5, pid, private as usize, replacement as usize);
    if result != 0 {
        return Err(format!("POKEDATA raw result={result}"));
    }
    word = 0;
    let result = ptrace(2, pid, private as usize, (&mut word as *mut u64) as usize);
    if result != 0 || word != replacement {
        return Err(format!(
            "PEEKDATA readback raw result={result} value={word:016x}"
        ));
    }
    // All parent memory/process-VM/COW assertions precede DETACH while the
    // child is still stopped. Keep the post-verification private check as well.
    for index in 0..BYTES {
        if unsafe { private.add(index).read_volatile() } != 0 {
            return Err("parent private bytes changed before detach".into());
        }
    }
    // Existing selected DETACH unlinks ptrace/report ownership, drops its real
    // TRACEME Thread reference and resumes. Do not CONT an already detached child.
    control.command.store(1, Ordering::Release);
    let result = ptrace(17, pid, 0, 0);
    if result != 0 || !await_value(&control.verified, 1, budget) {
        return Err(format!(
            "DETACH result={result} or child verification timeout"
        ));
    }
    for index in 0..BYTES {
        if unsafe { private.add(index).read_volatile() } != 0 {
            return Err("parent private bytes changed after child patch".into());
        }
    }
    control.command.store(2, Ordering::Release);
    Ok(())
}

fn run() -> Result<(), String> {
    let budget = Budget::start()?; // One deadline shared by every phase, including the gate.
    // Two separate mappings: private data and shared coordination. The shared
    // mapping contains only lock-free x86_64 AtomicU32 values, never test bytes.
    let private = unsafe { syscall(SYS_MMAP, [0, MAP_BYTES, 3, 0x22, usize::MAX, 0]) };
    if (-4095..0).contains(&private) {
        return Err(format!("private mmap result={private}"));
    }
    let shared = unsafe { syscall(SYS_MMAP, [0, 4096, 3, 0x21, usize::MAX, 0]) };
    if (-4095..0).contains(&shared) {
        unsafe {
            syscall(SYS_MUNMAP, [private as usize, MAP_BYTES, 0, 0, 0, 0]);
        }
        return Err(format!("shared mmap result={shared}"));
    }
    let control_ptr = shared as *mut Control;
    unsafe {
        control_ptr.write(Control {
            ready: AtomicU32::new(0),
            command: AtomicU32::new(0),
            verified: AtomicU32::new(0),
        });
    }
    let bytes = unsafe { (private as *mut u8).add(OFFSET) };
    let control = unsafe { &*control_ptr };
    // x86_64 raw clone(flags, child_stack, parent_tid, child_tid, tls).
    // Exact existing admitted native-libc flags: CHILD_SETTID|CHILD_CLEARTID
    // plus SIGCHLD. No CLONE_VM; stack=0 preserves the private current stack.
    // CLEAR_CHILD_TID writes/futex-wakes only this child's private mapped slot.
    // MCKERNEL_NATIVE_CLONE_TID must be proven in the selected build: otherwise
    // the original fallback may store physically without exercising F05 write.
    let child_tid = unsafe { (private as *mut u8).add(128).cast::<i32>() };
    let pid = unsafe {
        syscall(
            SYS_CLONE,
            [0x0120_0000 | 17, 0, 0, child_tid as usize, 0, 0],
        )
    };
    if pid == 0 {
        unsafe {
            child(bytes, child_tid, control, budget);
        }
    }
    let outcome = if pid < 0 {
        Err(format!("clone result={pid}"))
    } else {
        let mut terminal_status = None;
        let exercised = exercise(pid, bytes, control, &mut terminal_status, budget);
        let parent_tid_unchanged = unsafe { child_tid.read_volatile() } == 0;
        if exercised.is_err() && terminal_status.is_none() {
            // Only this parent's own, still unreaped child can be targeted.
            let killed = unsafe { syscall(SYS_KILL, [pid as usize, 9, 0, 0, 0, 0]) };
            if killed != 0 && killed != -3 {
                eprintln!("CLEANUP kill result={killed}");
            }
        }
        let waited = match terminal_status {
            Some(status) => Ok(status),
            None => wait_event(pid, 1, budget),
        };
        let exercised = exercised.and_then(|()| {
            if parent_tid_unchanged {
                Ok(())
            } else {
                Err("parent child_tid slot changed".into())
            }
        });
        match (exercised, waited) {
            (Ok(()), Ok(0)) => Ok(()),
            (Ok(()), Ok(status)) => Err(format!("child wait status={status}")),
            (Err(error), Ok(_)) => Err(error),
            (result, Err(error)) => Err(format!("reap failed: {error}; exercise={result:?}")),
        }
    };
    let unmap_private = unsafe { syscall(SYS_MUNMAP, [private as usize, MAP_BYTES, 0, 0, 0, 0]) };
    let unmap_shared = unsafe { syscall(SYS_MUNMAP, [shared as usize, 4096, 0, 0, 0, 0]) };
    outcome?;
    if unmap_private != 0 || unmap_shared != 0 {
        return Err(format!("munmap results={unmap_private}/{unmap_shared}"));
    }
    await_causal_gate(budget)?;
    println!("OWNED_F05 v3 children=1 clone_child_settid=1 parent_tid_unchanged=1");
    println!("traceme=0 sigstop=19 peek=0 poke=0 readback=0 cross_4k_word=1");
    println!("child_verified=1 private_unchanged=1 child_exit=0 reaped=1");
    println!("OWNED_F05 PASS");
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("FAIL {error}");
        std::process::exit(1);
    }
}
