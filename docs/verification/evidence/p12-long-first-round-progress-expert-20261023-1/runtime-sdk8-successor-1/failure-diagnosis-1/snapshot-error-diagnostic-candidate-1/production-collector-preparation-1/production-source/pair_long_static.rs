//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Explicit LONG producer. The existing fixed-ten producer is not modified.
//!
//! real-consumer-1/long_bridge.inc supplies the real existing pair launch/load/oracle,
//! workspace/procfs and retained-trace operations. A successful callback is not
//! native acceptance. No production bridge or linked collector is claimed here.
#![cfg_attr(not(test), no_std)]

use core::ffi::c_void;
use core::fmt::{self, Write};

pub const WORK_NS: u64 = 3_600_000_000_000;
pub const WALL_NS: u64 = 7_200_000_000_000;
pub const MIN_LAUNCHES: u64 = 100;
pub const ROUND_CAP: u32 = 2048;
pub const TRACE_CAP: u64 = 268_435_456;
pub const APP_NS: u64 = 10_000_000_000;
const ROUND_TRACE_CAP: u64 = 1_048_576;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct Bytes { pub ptr: *const u8, pub len: usize }
impl Bytes { const EMPTY: Self = Self { ptr: core::ptr::null(), len: 0 }; }

/// Times and identities come from the actual joined application result, never
/// from round sleep/stop/setup duration. Exact bytes/EOF/status/CPU/resource and
/// syscall/BEGIN-retirement proofs must pass the source-bound strict gate.
#[repr(C)]
#[derive(Clone, Copy, Default)]
pub struct App {
    pub pid: u64,
    pub started_ns: u64,
    pub reaped_ns: u64,
    pub finished_ns: u64,
    pub raw_wait_status: i32,
    pub clean: i32,
    pub stdout_eof: i32,
    pub stderr_eof: i32,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct Pair {
    pub apps: [App; 2],
    pub os: u64,
    pub generation: u64,
    /// Zero is the original complete strict pair gate success, not a waiver.
    pub strict_gate_result: i32,
    pub ownership_complete: i32,
    /// Exact original publish_pair JSON line, valid until run_pair is next used.
    pub report: Bytes,
    /// Strictly audited actual trace for these two identities, not a summary.
    pub trace: Bytes,
}
impl Pair {
    fn empty() -> Self {
        Self { apps: [App::default(); 2], os: 0, generation: 0,
               strict_gate_result: -1, ownership_complete: 0,
               report: Bytes::EMPTY, trace: Bytes::EMPTY }
    }
}

/// All operations are synchronous. Buffers remain readable through the next
/// run_pair. run_pair preserves its real ownership result even on failure.
/// empty checks the actual procfs/workspace state with an absolute deadline.
/// retain/read_trace use one bounded existing spool; exact counts are required.
#[repr(C)]
pub struct Operations {
    pub now_ns: unsafe extern "C" fn(*mut c_void) -> u64,
    pub empty: unsafe extern "C" fn(*mut c_void, u32, u64) -> i32,
    pub run_pair: unsafe extern "C" fn(*mut c_void, u32, u64, *mut Pair) -> i32,
    pub retain_trace: unsafe extern "C" fn(*mut c_void, *const u8, usize) -> isize,
    pub read_trace: unsafe extern "C" fn(*mut c_void, u64, *mut u8, usize) -> isize,
    pub write_serial: unsafe extern "C" fn(*mut c_void, *const u8, usize) -> isize,
}

#[repr(C)]
#[derive(Default, Debug)]
pub struct Summary {
    pub rounds: u64,
    pub launches: u64,
    pub work_ns: u64,
    pub elapsed_ns: u64,
    pub trace_bytes: u64,
    pub ownership_complete: i32,
    pub completed: i32,
}

#[repr(i32)]
#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum Failure {
    Invalid = -1, Clock = -2, Deadline = -3, State = -4,
    Pair = -5, Oracle = -6, Timing = -7, Identity = -8,
    Trace = -9, Wire = -10, Limit = -11, Write = -12,
}

struct Line { bytes: [u8; 1024], used: usize }
impl Line { fn new() -> Self { Self { bytes: [0; 1024], used: 0 } } }
impl Write for Line {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        let end = self.used.checked_add(s.len()).ok_or(fmt::Error)?;
        if end >= self.bytes.len() { return Err(fmt::Error); }
        self.bytes[self.used..end].copy_from_slice(s.as_bytes());
        self.used = end;
        Ok(())
    }
}

unsafe fn serial(ctx: *mut c_void, ops: &Operations, bytes: &[u8]) -> Result<(), Failure> {
    if (ops.write_serial)(ctx, bytes.as_ptr(), bytes.len()) != bytes.len() as isize {
        return Err(Failure::Write);
    }
    Ok(())
}
macro_rules! line {
    ($ctx:expr,$ops:expr,$($arg:tt)*) => {{
        let mut value = Line::new();
        write!(&mut value, $($arg)*).map_err(|_| Failure::Wire)?;
        serial($ctx, $ops, &value.bytes[..value.used])
    }};
}

unsafe fn clock(ctx: *mut c_void, ops: &Operations, previous: &mut u64) -> Result<u64, Failure> {
    let now = (ops.now_ns)(ctx);
    if now == 0 || now < *previous { return Err(Failure::Clock); }
    *previous = now;
    Ok(now)
}

/// Exact profile and actual mixed application work accounting. No configurable
/// quota/timeout mode can turn a short run into a LONG completion.
unsafe fn run(ctx: *mut c_void, ops: &Operations, summary: &mut Summary) -> Result<(), Failure> {
    let mut previous = 0;
    let entered = clock(ctx, ops, &mut previous)?;
    let absolute = entered.checked_add(WALL_NS).ok_or(Failure::Clock)?;
    let mut first_work = 0;
    let mut last_reaped = 0;
    let mut seen = [0_u64; ROUND_CAP as usize * 2];
    summary.ownership_complete = 1; // No pair has been launched yet.
    line!(ctx, ops, "ND_PAIR_LONG_PROFILE {{\"version\":1,\"work_ns\":{},\"wall_ns\":{},\"min_launches\":{},\"round_cap\":{},\"trace_cap\":{}}}\n", WORK_NS, WALL_NS, MIN_LAUNCHES, ROUND_CAP, TRACE_CAP)?;
    for round in 0..ROUND_CAP {
        let before = clock(ctx, ops, &mut previous)?;
        if before >= absolute { return Err(Failure::Deadline); }
        if (ops.empty)(ctx, round, absolute) != 1 { summary.ownership_complete = 0; return Err(Failure::State); }
        let started = clock(ctx, ops, &mut previous)?;
        if started >= absolute { return Err(Failure::Deadline); }
        line!(ctx, ops, "ND_PAIR_ROUND_START {{\"round\":{},\"time_ns\":{},\"procfs_empty\":true}}\n", round, started)?;
        summary.ownership_complete = 0;
        let mut pair = Pair::empty();
        let code = (ops.run_pair)(ctx, round, absolute, &mut pair);
        summary.ownership_complete = if pair.ownership_complete == 1 && pair.apps.iter().all(|a| a.clean == 1) { 1 } else { 0 };
        if code != 0 { return Err(Failure::Pair); }
        if summary.ownership_complete != 1 || pair.strict_gate_result != 0 || pair.os != 0 || pair.generation != 1 {
            return Err(Failure::Oracle);
        }
        let ended = clock(ctx, ops, &mut previous)?;
        if ended >= absolute { return Err(Failure::Deadline); }
        let low = pair.apps.iter().map(|a| a.started_ns).min().unwrap();
        let high = pair.apps.iter().map(|a| a.reaped_ns).max().unwrap();
        let latest_start = pair.apps.iter().map(|a| a.started_ns).max().unwrap();
        let earliest_reap = pair.apps.iter().map(|a| a.reaped_ns).min().unwrap();
        if latest_start >= earliest_reap { return Err(Failure::Timing); }
        for app in &pair.apps {
            if app.started_ns < started || app.started_ns == 0 || app.started_ns > app.reaped_ns ||
               app.reaped_ns > app.finished_ns || app.finished_ns > ended ||
               app.reaped_ns - app.started_ns > APP_NS || app.raw_wait_status != 0 ||
               app.stdout_eof != 1 || app.stderr_eof != 1 {
                return Err(Failure::Timing);
            }
            if app.pid == 0 || seen[..summary.launches as usize].contains(&app.pid) {
                return Err(Failure::Identity);
            }
        }
        if pair.apps[0].pid == pair.apps[1].pid { return Err(Failure::Identity); }
        if first_work == 0 { first_work = low; }
        if ended.checked_sub(first_work).ok_or(Failure::Clock)? >= WALL_NS {
            return Err(Failure::Deadline);
        }
        if pair.trace.ptr.is_null() || pair.trace.len == 0 || pair.trace.len as u64 > ROUND_TRACE_CAP ||
           summary.trace_bytes.checked_add(pair.trace.len as u64).ok_or(Failure::Trace)? > TRACE_CAP {
            return Err(Failure::Trace);
        }
        if pair.report.ptr.is_null() || pair.report.len >= 4096 || pair.report.len == 0 {
            return Err(Failure::Wire);
        }
        let report = core::slice::from_raw_parts(pair.report.ptr, pair.report.len);
        if !report.starts_with(b"ND_PAIR {") || !report.ends_with(b"}\n") ||
           !report.is_ascii() || report[..report.len()-1].contains(&b'\n') || report.contains(&0) || report.contains(&b'\r') {
            return Err(Failure::Wire);
        }
        if (ops.empty)(ctx, round, absolute) != 1 { summary.ownership_complete = 0; return Err(Failure::State); }
        if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }
        // Preserve actual trace and original strict report before quota credit.
        if (ops.retain_trace)(ctx, pair.trace.ptr, pair.trace.len) != pair.trace.len as isize {
            return Err(Failure::Trace);
        }
        serial(ctx, ops, report)?;
        line!(ctx, ops, "ND_PAIR_ROUND_END {{\"round\":{},\"time_ns\":{},\"procfs_empty\":true}}\n", round, ended)?;
        let work = high.checked_sub(low).ok_or(Failure::Timing)?;
        summary.work_ns = summary.work_ns.checked_add(work).ok_or(Failure::Limit)?;
        summary.trace_bytes += pair.trace.len as u64;
        seen[summary.launches as usize] = pair.apps[0].pid;
        seen[summary.launches as usize + 1] = pair.apps[1].pid;
        summary.rounds += 1;
        summary.launches += 2;
        last_reaped = high;
        line!(ctx, ops, "ND_PAIR_LONG_PROGRESS {{\"round\":{},\"work_ns\":{},\"cumulative_work_ns\":{},\"launches\":{}}}\n", round, work, summary.work_ns, summary.launches)?;
        if summary.work_ns >= WORK_NS && summary.launches >= MIN_LAUNCHES { break; }
    }
    if summary.work_ns < WORK_NS || summary.launches < MIN_LAUNCHES { return Err(Failure::Limit); }
    summary.elapsed_ns = last_reaped.checked_sub(first_work).ok_or(Failure::Clock)?;
    if summary.elapsed_ns >= WALL_NS || clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }
    line!(ctx, ops, "ND_PAIR_LONG_TRACE_BEGIN {{\"bytes\":{}}}\n", summary.trace_bytes)?;
    let mut buffer = [0_u8; 4096];
    let mut offset = 0;
    while offset < summary.trace_bytes {
        if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }
        let want = core::cmp::min(buffer.len() as u64, summary.trace_bytes - offset) as usize;
        if (ops.read_trace)(ctx, offset, buffer.as_mut_ptr(), want) != want as isize { return Err(Failure::Trace); }
        if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }
        serial(ctx, ops, &buffer[..want])?;
        if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }
        offset += want as u64;
    }
    if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }
    line!(ctx, ops, "ND_PAIR_LONG_TRACE_END {{\"bytes\":{}}}\n", summary.trace_bytes)?;
    if clock(ctx, ops, &mut previous)? >= absolute { return Err(Failure::Deadline); }
    // Collector final evidence/restoration gates must run before terminal publication.
    Ok(())
}

/// `ops`, `summary`, context and callback buffers must stay exclusively owned
/// and valid through this synchronous call. Failed publication never invents
/// ACK/completion. Caller retains any ownership not positively reported safe.
#[no_mangle]
pub unsafe extern "C" fn pair_run_long_session(ctx: *mut c_void, ops: *const Operations, summary: *mut Summary) -> i32 {
    if ops.is_null() || summary.is_null() { return Failure::Invalid as i32; }
    *summary = Summary::default();
    match run(ctx, &*ops, &mut *summary) { Ok(()) => 0, Err(error) => error as i32 }
}

/// One-shot terminal publication after the actual collector final gates. The
/// C owner retains context/summary and supplies the SAME absolute wall bound.
/// A failure after visible bytes requires fail-closed PID1 retention, not poweroff.
#[no_mangle]
pub unsafe extern "C" fn pair_complete_long_session(
    ctx: *mut c_void, operations: *const Operations, result: *mut Summary,
    not_before: u64, absolute: u64,
) -> i32 {
    if operations.is_null() || result.is_null() { return Failure::Invalid as i32; }
    let ops=&*operations;let summary=&mut *result;
    if summary.completed!=0 || summary.ownership_complete!=1 || summary.rounds==0 ||
       summary.rounds>ROUND_CAP as u64 || summary.launches!=summary.rounds*2 ||
       summary.launches<MIN_LAUNCHES || summary.work_ns<WORK_NS ||
       summary.elapsed_ns>=WALL_NS || summary.trace_bytes==0 || summary.trace_bytes>TRACE_CAP ||
       not_before==0 || absolute<=not_before { return Failure::Invalid as i32; }
    let mut previous=not_before;
    let finish=(|| {
        if clock(ctx,ops,&mut previous)? >= absolute { return Err(Failure::Deadline); }
    line!(ctx, ops, "ND_PAIR_LONG_COMPLETE {{\"rounds\":{},\"launches\":{},\"work_ns\":{},\"elapsed_ns\":{},\"trace_bytes\":{},\"os\":0,\"generation\":1,\"procfs_empty\":true}}\n", summary.rounds, summary.launches, summary.work_ns, summary.elapsed_ns, summary.trace_bytes)?;
        if clock(ctx,ops,&mut previous)? >= absolute { return Err(Failure::Deadline); }
        summary.completed=1;
        Ok(())
    })();
    match finish {Ok(())=>0,Err(error)=>error as i32}
}

#[cfg(test)]
mod tests;

// Same accepted no_std panic-abort provider as the M05 archive.
unsafe extern "C" { fn abort() -> !; }
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! { unsafe { abort() } }
