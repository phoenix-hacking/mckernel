// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Pure mocked records only. Prepared for Root's ordinary HOST qualification;
//! this source worker did not compile or execute a Rust test executable.
use crate::lifecycle::{KmsgSequence, Lifecycle};
use crate::supervisor::{bounded_deadline, ResultRecord, Stream};

fn accept(state: &mut Lifecycle, row: &str) {
    state.accept(row).unwrap();
}
pub(crate) fn initial() -> Lifecycle {
    let mut state = Lifecycle::new(254).unwrap();
    for row in [
        "application_process=registered os=0 generation=1 pid=254",
        "application SCHEDULE os=0 generation=1 pid=254 cpu=0",
        "application procfs published os=0 generation=1 pid=254 tid=254",
        "application_syscall=delivered os=0 generation=1 pid=254 worker=6 delivery=26 cpu=0 number=56",
        "application_syscall=returned os=0 generation=1 pid=254 worker=6 delivery=26 cpu=0 value=257",
        "application procfs published os=0 generation=1 pid=257 tid=257",
        "application_syscall=delivered os=0 generation=1 pid=257 worker=29 delivery=31 cpu=0 number=1",
        "application_syscall=returned os=0 generation=1 pid=257 worker=29 delivery=31 cpu=0 value=0",
        "application_syscall=delivered os=0 generation=1 pid=257 worker=29 delivery=36 cpu=0 number=231",
        "application_process=cleanup_requested os=0 generation=1 pid=257 intent_errno=0",
        "application cleanup ACK os=0 generation=1 pid=257 token=27 errno=0 abandoned=0",
        "application retirement os=0 generation=1 pid=257 token=40 errno=-11",
        "application_syscall=delivered os=0 generation=1 pid=254 worker=6 delivery=41 cpu=0 number=61",
        "application_syscall=returned os=0 generation=1 pid=254 worker=6 delivery=41 cpu=0 value=257",
    ] { accept(&mut state, row); }
    state
}
fn child_complete(state: &mut Lifecycle) {
    accept(
        state,
        "application procfs deleted os=0 generation=1 pid=257 tid=257",
    );
    accept(
        state,
        "application retirement os=0 generation=1 pid=257 token=42 errno=0",
    );
}
#[test]
fn namespace_absence_or_ack_or_reap_cannot_release() {
    let mut state = initial();
    assert!(!state.child_ready());
    assert!(state.record_gate_write().is_err());
    // No namespace event exists in Lifecycle: procfs_empty is separately required
    // at completion and cannot be passed as a substitute for any lifecycle row.
    accept(
        &mut state,
        "application procfs deleted os=0 generation=1 pid=257 tid=257",
    );
    assert!(!state.child_ready());
    assert!(!state.complete());
}
#[test]
fn genuine_child_then_parent_sequence_finishes_only_after_real_parent_zero() {
    let mut state = initial();
    child_complete(&mut state);
    assert!(state.child_ready());
    state.record_gate_write().unwrap();
    assert!(!state.child_ready());
    assert!(state.record_gate_write().is_err());
    for row in [
        "application_syscall=delivered os=0 generation=1 pid=254 worker=6 delivery=50 cpu=0 number=231",
        "application cleanup ACK os=0 generation=1 pid=254 token=3 errno=0 abandoned=0",
        "application_process=cleanup_requested os=0 generation=1 pid=254 intent_errno=0",
        "application procfs deleted os=0 generation=1 pid=254 tid=254",
        "application retirement os=0 generation=1 pid=254 token=51 errno=-11",
    ] { accept(&mut state, row); }
    assert!(!state.complete());
    accept(
        &mut state,
        "application retirement os=0 generation=1 pid=254 token=52 errno=0",
    );
    assert!(state.complete());
}
#[test]
fn retirement_zero_alone_does_not_imply_delete() {
    let mut state = initial();
    accept(
        &mut state,
        "application retirement os=0 generation=1 pid=257 token=42 errno=0",
    );
    assert!(!state.child_ready());
    accept(
        &mut state,
        "application procfs deleted os=0 generation=1 pid=257 tid=257",
    );
    assert!(state.child_ready());
}
#[test]
fn unchanged_failed_v2_order_is_refused() {
    let mut state = initial();
    assert!(state.accept("application_syscall=delivered os=0 generation=1 pid=254 worker=6 delivery=50 cpu=0 number=231").is_err());
}
#[test]
fn foreign_generation_pid_and_unlinked_publication_are_refused() {
    for row in [
        "application procfs deleted os=0 generation=2 pid=257 tid=257",
        "application procfs deleted os=1 generation=1 pid=257 tid=257",
        "application procfs deleted os=0 generation=1 pid=258 tid=258",
        "application procfs deleted os=0 generation=1 pid=257 tid=258",
    ] {
        assert!(initial().accept(row).is_err());
    }
    assert!(Lifecycle::new(254)
        .unwrap()
        .accept("application procfs published os=0 generation=1 pid=257 tid=257")
        .is_err());
}
#[test]
fn duplicate_malformed_unknown_rows_and_bad_results_are_refused() {
    for row in [
        "application retirement os=0 generation=1 pid=257 token=40 errno=-11",
        "application retirement os=0 generation=1 pid=257 token=0 errno=0",
        "application retirement os=0 generation=1 pid=257 token=42 errno=-5",
        "application retirement os=0 generation=1 pid=257 token=42 errno=0 extra=1",
        "application cleanup ACK os=0 generation=1 pid=257 token=27 errno=0 abandoned=0",
        "application procfs invalid os=0 generation=1 pid=257 tid=257",
        "application_process=release os=0 generation=1 pid=257",
        "application_syscall=unknown os=0 generation=1 pid=257",
    ] {
        assert!(initial().accept(row).is_err(), "{row}");
    }
    let mut state = initial();
    child_complete(&mut state);
    assert!(state
        .accept("application retirement os=0 generation=1 pid=257 token=43 errno=0")
        .is_err());
    assert!(state
        .accept("application procfs deleted os=0 generation=1 pid=257 tid=257")
        .is_err());
}
#[test]
fn original_twelve_attempt_limit_is_preserved() {
    let mut state = initial();
    for token in 41..52 {
        accept(
            &mut state,
            &format!("application retirement os=0 generation=1 pid=257 token={token} errno=-11"),
        );
    }
    assert!(state
        .accept("application retirement os=0 generation=1 pid=257 token=52 errno=0")
        .is_err());
}
#[test]
fn stream_capture_retains_1024_and_counts_all_bytes() {
    let mut stream = Stream::default();
    stream.append(&[42; 1024]).unwrap();
    stream.append(&[9; 20]).unwrap();
    assert_eq!(stream.data, [42; 1024]);
    assert_eq!(stream.observed, 1044);
    let json = crate::report::stream_json(&stream);
    assert!(json.contains("\"discarded\":20,\"limit\":1024"));
}
#[test]
fn selected_report_preserves_exact_argv_cwd_two_env_and_status() {
    let mut result = ResultRecord::default();
    result.status = 37 << 8;
    result.clean = true;
    let frame = String::from_utf8(crate::report::frame(&result, true).unwrap()).unwrap();
    assert!(frame.starts_with("ND_PAYLOAD {\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\",\"/apps/app\"],\"cwd\":\"/case/work\",\"env\":{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"},\"raw_wait_status\":9472,"));
    assert_eq!(frame.matches("ND_PAYLOAD ").count(), 1);
    assert!(frame.ends_with("\"procfs_empty\":true}\n"));
    result.fault = true;
    assert!(
        String::from_utf8(crate::report::frame(&result, true).unwrap())
            .unwrap()
            .ends_with("\"procfs_empty\":false}\n")
    );
}
#[test]
fn oversize_frame_uses_original_failure_fallback() {
    let mut result = ResultRecord::default();
    result.out.append(&[42; 1024]).unwrap();
    result.err.append(&[42; 1024]).unwrap();
    result.clean = true;
    let frame = String::from_utf8(crate::report::frame(&result, true).unwrap()).unwrap();
    assert!(frame.len() < 4096);
    assert!(frame.contains("\"discarded\":1024"));
    assert!(frame.ends_with("\"procfs_empty\":false}\n"));
}
#[test]
fn sequence_keeps_native_metadata_and_refuses_gaps_duplicates_overflow() {
    let mut sequence = KmsgSequence::default();
    assert_eq!(
        sequence.accept(b"6,55,1000,-;message\n").unwrap(),
        "message"
    );
    assert_eq!(
        sequence.accept(b"6,56,1001,-;message2\n").unwrap(),
        "message2"
    );
    for bad in [
        b"6,58,1002,-;gap\n".as_slice(),
        b"6,56,1001,-;duplicate\n",
        b"6,57,999,-;reverse\n",
        b"6,57,1002,c;continued\n",
        b"broken\n",
    ] {
        let mut s = KmsgSequence::default();
        s.accept(b"6,56,1001,-;baseline\n").unwrap();
        assert!(s.accept(bad).is_err());
    }
    assert!(KmsgSequence::default().accept(&vec![b'x'; 262145]).is_err());
}
#[test]
fn original_deadlines_clamp_without_renewal() {
    assert_eq!(bounded_deadline(10_000, 9_000, 2_000), 7_000);
    assert_eq!(bounded_deadline(5_000, 9_000, 2_000), 5_000);
    assert_eq!(bounded_deadline(10_000, 1_000, 2_000), 0);
}
#[test]
fn unreadable_procfs_and_deadline_never_become_retirement() {
    use crate::supervisor::retirement_ready;
    assert!(!retirement_ready(10, 20, Ok(true), false).unwrap());
    assert!(!retirement_ready(10, 20, Ok(false), true).unwrap());
    assert!(retirement_ready(10, 20, Ok(true), true).unwrap());
    assert!(retirement_ready(10, 20, Err("unreadable procfs".into()), true).is_err());
    assert!(retirement_ready(20, 20, Ok(true), true).is_err());
    assert!(retirement_ready(0, 20, Ok(true), true).is_err());
}
