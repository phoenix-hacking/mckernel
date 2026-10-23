use super::*;

struct Fixture {
    now: u64, count: u32, serial: Vec<u8>, trace: Vec<u8>, report: Vec<u8>,
    round_trace: Vec<u8>, gap: u64, union: u64, fail: &'static str,
}
impl Fixture {
    fn new() -> Self {
        Self { now: 1_000_000, count: 0, serial: vec![], trace: vec![],
               report: b"ND_PAIR {}\n".to_vec(), round_trace: b"actual-controlled-trace\n".to_vec(),
               gap: 0, union: 10_000_000_000, fail: "" }
    }
    fn execute(&mut self) -> (i32, Summary) {
        let mut summary = Summary::default();
        let code = unsafe { pair_run_long_session((self as *mut Self).cast(), &OPS, &mut summary) };
        (code, summary)
    }
    fn wire(&self) -> &str { core::str::from_utf8(&self.serial).unwrap() }
}
unsafe fn fixture<'a>(p: *mut c_void) -> &'a mut Fixture { &mut *p.cast::<Fixture>() }
unsafe extern "C" fn now(p: *mut c_void) -> u64 {
    let f = fixture(p);
    if f.fail == "zero-clock" { return 0; }
    if f.fail == "backward" && f.count > 0 { return 1; }
    f.now
}
unsafe extern "C" fn empty(p: *mut c_void, _: u32, _: u64) -> i32 {
    if fixture(p).fail == "state" || (fixture(p).fail == "post-state" && fixture(p).count>0) { 0 } else { 1 }
}
unsafe extern "C" fn pair(p: *mut c_void, round: u32, _: u64, out: *mut Pair) -> i32 {
    let f = fixture(p);
    f.count += 1;
    if f.fail=="real-wire" {
        let root=std::path::PathBuf::from(std::env::var("REAL_WIRE_ROOT").unwrap());
        f.report=std::fs::read(root.join(format!("{round}.report"))).unwrap();
        f.round_trace=std::fs::read(root.join(format!("{round}.trace"))).unwrap();
    }
    let start = f.now;
    let mut apps = [App { pid: round as u64 * 2 + 1, started_ns: start,
        reaped_ns: start + f.union - 1, finished_ns: start + f.union,
        raw_wait_status: 0, clean: 1, stdout_eof: 1, stderr_eof: 1 }; 2];
    apps[1].pid += 1;
    apps[1].started_ns += 1;
    apps[1].reaped_ns += 1;
    if f.fail == "duplicate-pid" { apps[1].pid = apps[0].pid; }
    if f.fail == "reuse-pid" { apps[0].pid = 1; }
    if f.fail == "no-overlap" { apps[1].started_ns = apps[0].reaped_ns; }
    if f.fail == "bad-status" { apps[0].raw_wait_status = 37 << 8; }
    if f.fail == "missing-eof" { apps[0].stderr_eof = 0; }
    if f.fail == "uncertain-owner" { apps[0].clean = 0; }
    if f.fail == "over10s" { apps[0].reaped_ns = start + APP_NS + 1; apps[0].finished_ns = start + APP_NS + 1; }
    f.now += f.union + f.gap;
    if f.fail == "deadline" { f.now = start + WALL_NS; }
    *out = Pair { apps, os: 0, generation: if f.fail == "wrong-generation" { 2 } else { 1 },
        strict_gate_result: if f.fail == "strict-gate" { -1 } else { 0 },
        ownership_complete: if f.fail == "uncertain-owner" { 0 } else { 1 },
        report: Bytes { ptr: f.report.as_ptr(), len: f.report.len() },
        trace: Bytes { ptr: f.round_trace.as_ptr(), len: f.round_trace.len() } };
    if f.fail == "pair-error" { -1 } else { 0 }
}
unsafe extern "C" fn retain(p: *mut c_void, data: *const u8, n: usize) -> isize {
    let f = fixture(p);
    if f.fail == "retain-short" { return n as isize - 1; }
    f.trace.extend_from_slice(core::slice::from_raw_parts(data, n));
    n as isize
}
unsafe extern "C" fn read(p: *mut c_void, offset: u64, data: *mut u8, n: usize) -> isize {
    let f = fixture(p);
    if f.fail == "read-short" { return n as isize - 1; }
    if f.fail == "last-read-deadline" && offset as usize+n == f.trace.len() { f.now=1_000_000+WALL_NS; }
    let slice = &f.trace[offset as usize..offset as usize+n];
    core::ptr::copy_nonoverlapping(slice.as_ptr(), data, n);
    n as isize
}
unsafe extern "C" fn write(p: *mut c_void, data: *const u8, n: usize) -> isize {
    let f = fixture(p);
    if f.fail == "write-short" { return n as isize - 1; }
    let bytes=core::slice::from_raw_parts(data,n);
    if (f.fail=="last-write-deadline" && !bytes.starts_with(b"ND_")) ||
       (f.fail=="trace-end-deadline" && bytes.starts_with(b"ND_PAIR_LONG_TRACE_END ")) ||
       (f.fail=="complete-deadline" && bytes.starts_with(b"ND_PAIR_LONG_COMPLETE ")) { f.now=1_000_000+WALL_NS; }
    f.serial.extend_from_slice(bytes);
    n as isize
}
static OPS: Operations = Operations { now_ns: now, empty, run_pair: pair, retain_trace: retain, read_trace: read, write_serial: write };

#[test]
fn exact_profile_actual_union_and_bounded_wire() {
    let mut f = Fixture::new();
    let (code, summary) = f.execute();
    assert_eq!(code, 0);
    assert_eq!(f.count, 360);
    assert_eq!(summary.rounds, 360);
    assert_eq!(summary.launches, 720);
    assert_eq!(summary.work_ns, WORK_NS);
    assert_eq!(summary.elapsed_ns, WORK_NS);
    assert_eq!(summary.trace_bytes, f.trace.len() as u64);
    assert_eq!(summary.completed, 1);
    assert_eq!(summary.ownership_complete, 1);
    let wire = f.wire();
    assert!(wire.starts_with("ND_PAIR_LONG_PROFILE {\"version\":1,\"work_ns\":3600000000000,\"wall_ns\":7200000000000,\"min_launches\":100,\"round_cap\":2048,\"trace_cap\":268435456}\n"));
    assert_eq!(wire.matches("ND_PAIR_LONG_PROGRESS ").count(), 360);
    assert_eq!(wire.matches("ND_PAIR_ROUND_START ").count(), 360);
    assert_eq!(wire.matches("ND_PAIR_ROUND_END ").count(), 360);
    assert_eq!(wire.matches("ND_PAIR {}\n").count(), 360);
    assert_eq!(wire.matches("ND_PAIR_LONG_COMPLETE ").count(), 1);
    assert!(wire.contains("\"round\":359,\"work_ns\":10000000000,\"cumulative_work_ns\":3600000000000,\"launches\":720}"));
    let begin = wire.find("ND_PAIR_LONG_TRACE_BEGIN ").unwrap();
    let end = wire.find("ND_PAIR_LONG_TRACE_END ").unwrap();
    assert!(begin < end && end < wire.find("ND_PAIR_LONG_COMPLETE ").unwrap());
    assert!(wire.lines().filter(|line| line.starts_with("ND_")).all(|line| line.len() < 1024));
}

#[test]
fn setup_and_gap_never_count_as_work() {
    let mut f = Fixture::new(); f.gap = 100_000_000;
    let (code, s) = f.execute();
    assert_eq!(code, 0); assert_eq!(s.work_ns, WORK_NS);
    assert_eq!(s.launches, 720); assert!(s.elapsed_ns > s.work_ns);
}

#[test]
fn fast_pairs_fail_round_cap_instead_of_sleeping_or_faking_work() {
    let mut f = Fixture::new(); f.union = 1000;
    let (code, s) = f.execute();
    assert_eq!(code, Failure::Limit as i32); assert_eq!(f.count, ROUND_CAP);
    assert_eq!(s.work_ns, ROUND_CAP as u64 * 1000); assert_eq!(s.completed, 0);
    assert!(!f.wire().contains("ND_PAIR_LONG_COMPLETE "));
}

#[test]
fn every_actual_pair_gate_and_identity_is_required() {
    for (name, expected) in [("strict-gate", Failure::Oracle), ("wrong-generation", Failure::Oracle),
        ("uncertain-owner", Failure::Oracle), ("bad-status", Failure::Timing),
        ("missing-eof", Failure::Timing), ("no-overlap", Failure::Timing),
        ("duplicate-pid", Failure::Identity), ("over10s", Failure::Timing),
        ("pair-error", Failure::Pair), ("state", Failure::State)] {
        let mut f = Fixture::new(); f.fail = name;
        let (code, s) = f.execute(); assert_eq!(code, expected as i32, "{name}");
        assert_eq!(s.launches, 0, "{name}"); assert_eq!(s.completed, 0);
        if name == "uncertain-owner" { assert_eq!(s.ownership_complete, 0); }
    }
}

#[test]
fn pids_cannot_reappear_across_rounds() {
    let mut f = Fixture::new(); f.fail = "reuse-pid";
    let (code, s) = f.execute(); assert_eq!(code, Failure::Identity as i32);
    assert_eq!(s.launches, 2); assert_eq!(f.count, 2);
}

#[test]
fn clocks_and_fixed_wall_cannot_be_waived() {
    for (name, error) in [("zero-clock", Failure::Clock), ("backward", Failure::Clock), ("deadline", Failure::Deadline)] {
        let mut f = Fixture::new(); f.fail = name;
        let (code, s) = f.execute(); assert_eq!(code, error as i32); assert_eq!(s.completed, 0);
    }
    let mut f = Fixture::new(); f.gap = WALL_NS / 2;
    let (code, s) = f.execute(); assert_eq!(code, Failure::Deadline as i32);
    assert!(s.work_ns < WORK_NS); assert_eq!(s.completed, 0);
}

#[test]
fn wire_record_injection_and_size_are_rejected() {
    for report in [b"ND_WRONG {}\n".as_slice(), b"ND_PAIR {}\nND_PAIR {}\n", b"ND_PAIR {}\r\n", b"ND_PAIR {\0}\n"] {
        let mut f = Fixture::new(); f.report = report.to_vec();
        let (code, s) = f.execute(); assert_eq!(code, Failure::Wire as i32); assert_eq!(s.launches, 0);
    }
    let mut f = Fixture::new(); f.report = vec![b'x'; 4096];
    assert_eq!(f.execute().0, Failure::Wire as i32);
}

#[test]
fn all_trace_and_write_outcomes_require_exact_counts() {
    for (name, expected) in [("retain-short", Failure::Trace), ("read-short", Failure::Trace), ("write-short", Failure::Write)] {
        let mut f = Fixture::new(); f.fail = name;
        let (code, s) = f.execute(); assert_eq!(code, expected as i32); assert_eq!(s.completed, 0);
        assert!(!f.wire().contains("ND_PAIR_LONG_COMPLETE "));
    }
    let mut f = Fixture::new(); f.round_trace = vec![b'x'; ROUND_TRACE_CAP as usize + 1];
    assert_eq!(f.execute().0, Failure::Trace as i32);
}

#[test]
fn global_trace_limit_fails_before_quota_without_completion() {
    let mut f = Fixture::new(); f.round_trace = vec![b'x'; ROUND_TRACE_CAP as usize];
    let (code, s) = f.execute(); assert_eq!(code, Failure::Trace as i32);
    assert_eq!(s.trace_bytes, TRACE_CAP); assert_eq!(s.rounds, 256); assert_eq!(s.completed, 0);
}

#[test]
fn rust_ffi_layout_and_null_entrypoint() {
    assert_eq!(core::mem::size_of::<App>(), 48);
    assert_eq!(core::mem::size_of::<Pair>(), 152);
    assert_eq!(core::mem::size_of::<Operations>(), 48);
    assert_eq!(core::mem::size_of::<Summary>(), 48);
    assert_eq!(unsafe { pair_run_long_session(core::ptr::null_mut(), core::ptr::null(), core::ptr::null_mut()) }, Failure::Invalid as i32);
}

#[test]
fn postflight_uncertainty_clears_ownership() {
    let mut f=Fixture::new(); f.fail="post-state";
    let (code,s)=f.execute();
    assert_eq!(code,Failure::State as i32);
    assert_eq!(s.ownership_complete,0);assert_eq!(s.completed,0);
}
#[test]
fn final_io_clock_crossings_cannot_complete() {
    for stage in ["last-read-deadline","last-write-deadline","trace-end-deadline","complete-deadline"] {
        let mut f=Fixture::new();f.fail=stage;
        let (code,s)=f.execute();assert_eq!(code,Failure::Deadline as i32,"{stage}");
        assert_eq!(s.completed,0,"{stage}");
        if stage!="complete-deadline" { assert!(!f.wire().contains("ND_PAIR_LONG_COMPLETE "),"{stage}"); }
    }
}
extern "C" { fn bridge_fixture(mode:i32)->i32; }
#[test]
fn actual_bridge_controlled_launch_and_strict_gate() {
    let mode=std::env::var("BRIDGE_MODE").unwrap().parse::<i32>().unwrap();
    assert_eq!(unsafe{bridge_fixture(mode)},0,"bridge mode {mode}");
}
#[test]
fn actual_loop_full_report_trace_consumer_wire() {
    let root=std::env::var("REAL_WIRE_ROOT").unwrap();
    let mut f=Fixture::new();f.fail="real-wire";
    let (code,s)=f.execute();assert_eq!(code,0);assert_eq!(s.completed,1);
    std::fs::write(std::path::Path::new(&root).join("../actual-rust-full-consumer-wire-data"),&f.serial).unwrap();
}
