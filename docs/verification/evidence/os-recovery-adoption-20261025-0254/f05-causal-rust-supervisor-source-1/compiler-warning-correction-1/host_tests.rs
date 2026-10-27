// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Prepared ordinary HOST checks of actual supervisor calls. Never invoke main,
//! modules, mounts, kmsg, gate preparation, PID1 poweroff or any guest here.
use crate::supervisor::*;
use std::sync::Mutex;
static PROCESS_TEST: Mutex<()> = Mutex::new(());
unsafe extern "C" {
    fn prctl(option: i32, ...) -> i32;
}
fn own_orphans() {
    // The existing C harness uses the same Linux child-subreaper ownership.
    // Tests are serialized because supervise's genuine waitpid(-1) owns all
    // subprocesses in this dedicated test binary.
    assert_eq!(unsafe { prctl(36, 1usize, 0usize, 0usize, 0usize) }, 0);
}
#[test]
fn host_missing_namespace_is_an_error() {
    assert!(retired_at("/definitely-not-a-collector-test-directory").is_err());
}
#[test]
fn host_real_binary_streams_and_raw_wait_status() {
    let _guard = PROCESS_TEST.lock().unwrap();
    own_orphans();
    let outer = now_ns() + 5_000 * MS;
    let r = supervise(
        "/bin/sh",
        &[
            "/bin/sh",
            "-c",
            "printf '\\000\\377A\\n'; printf 'B\\000\\376' >&2; exit 37",
        ],
        PAYLOAD_ENV,
        None,
        1000,
        outer,
        None,
    );
    assert_eq!(r.status, 37 << 8);
    assert_eq!(r.out.data, [0, 255, 65, 10]);
    assert_eq!(r.err.data, [66, 0, 254]);
    assert!(r.clean && r.out.eof && r.err.eof && !r.fault && !r.timeout);
    assert!(0 < r.started && r.started <= r.reaped && r.reaped <= r.finished);
}
#[test]
fn host_real_exec_and_cwd_failures_keep_exact_setup_stage() {
    let _guard = PROCESS_TEST.lock().unwrap();
    own_orphans();
    for (path, cwd, stage) in [
        ("/definitely-not-a-collector-test-executable", None, 5),
        (
            "/bin/sh",
            Some("/definitely-not-a-collector-test-directory"),
            4,
        ),
    ] {
        let r = supervise(
            path,
            &[path],
            PAYLOAD_ENV,
            cwd,
            1000,
            now_ns() + 5000 * MS,
            None,
        );
        assert_eq!(r.status, 126 << 8);
        assert_eq!(r.child_stage, stage);
        assert_eq!(r.child_errno, 2);
        assert!(r.clean && r.fault && !r.timeout && r.out.eof && r.err.eof);
    }
}
#[test]
fn host_real_timeout_signals_pinned_group_and_reaps_ignored_term() {
    let _guard = PROCESS_TEST.lock().unwrap();
    own_orphans();
    let r = supervise(
        "/bin/sh",
        &["/bin/sh", "-c", "trap '' TERM; while :; do :; done"],
        PAYLOAD_ENV,
        None,
        100,
        now_ns() + 5000 * MS,
        None,
    );
    assert_eq!(r.status, 9);
    assert!(r.timeout && r.clean && !r.fault && r.out.eof && r.err.eof);
    assert!(r.finished - r.started < 3_000 * MS);
}
#[test]
fn host_real_orphan_descendant_is_reaped_before_clean_result() {
    let _guard = PROCESS_TEST.lock().unwrap();
    own_orphans();
    let r = supervise(
        "/bin/sh",
        &["/bin/sh", "-c", "sleep 30 & exit 0"],
        PAYLOAD_ENV,
        None,
        1000,
        now_ns() + 5000 * MS,
        None,
    );
    assert_eq!(r.status, 0);
    assert!(r.clean && !r.fault && !r.timeout && r.out.eof && r.err.eof);
}
#[test]
fn host_real_stream_overflow_counts_without_exceeding_retention() {
    let _guard = PROCESS_TEST.lock().unwrap();
    own_orphans();
    let r = supervise(
        "/bin/sh",
        &[
            "/bin/sh",
            "-c",
            "i=0; while [ $i -lt 1100 ]; do printf x; printf y >&2; i=$((i+1)); done",
        ],
        PAYLOAD_ENV,
        None,
        1000,
        now_ns() + 5000 * MS,
        None,
    );
    assert_eq!(r.status, 0);
    assert!(r.clean && !r.fault && !r.timeout);
    assert_eq!(r.out.observed, 1100);
    assert_eq!(r.err.observed, 1100);
    assert_eq!(r.out.data.len(), 1024);
    assert_eq!(r.err.data.len(), 1024);
}
