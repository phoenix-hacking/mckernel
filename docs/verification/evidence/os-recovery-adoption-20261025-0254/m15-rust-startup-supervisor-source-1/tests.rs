// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Applicable generic controls reused from the accepted36-control cohort.
use crate::supervisor::{bounded_deadline, ResultRecord, Stream};
#[test]
fn stream_capture_retains_1024_and_counts_all_bytes() {
    let mut stream = Stream::default();
    stream.append(&[42; 1024]).unwrap();
    stream.append(&[9; 20]).unwrap();
    assert_eq!(stream.data, [42; 1024]);
    assert_eq!(stream.observed, 1044);
    assert!(crate::report::stream_json(&stream).contains("\"discarded\":20,\"limit\":1024"));
}
#[test]
fn report_and_execution_share_exact_startup_argv_with_empty_element() {
    assert_eq!(
        crate::profile::PAYLOAD_ARGV,
        ["/bin/mcexec", "-t", "1", "0", "app", "A", "", "B"]
    );
    assert_eq!(
        crate::profile::argv_json(),
        "[\"/bin/mcexec\",\"-t\",\"1\",\"0\",\"app\",\"A\",\"\",\"B\"]"
    );
    assert_eq!(crate::profile::BOOT_ARGV, ["/bin/native-boot"]);
    assert!(crate::profile::PAYLOAD_ARGV
        .iter()
        .flat_map(|s| s.bytes())
        .all(|b| b.is_ascii() && b != b'"' && b != b'\\' && !b.is_ascii_control()));
    let mut result = ResultRecord::default();
    result.clean = true;
    result.status = 37 << 8;
    let frame = String::from_utf8(crate::report::frame(&result, true).unwrap()).unwrap();
    let prefix=format!("ND_PAYLOAD {{\"argv\":{},\"cwd\":\"/case/work\",\"env\":{{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"}},\"raw_wait_status\":9472,",crate::profile::argv_json());
    assert!(frame.starts_with(&prefix));
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
fn original_deadlines_clamp_without_renewal() {
    assert_eq!(bounded_deadline(10_000, 9_000, 2_000), 7_000);
    assert_eq!(bounded_deadline(5_000, 9_000, 2_000), 5_000);
    assert_eq!(bounded_deadline(10_000, 1_000, 2_000), 0);
}
#[test]
fn original_startup_retirement_requires_readable_empty_namespace_before_deadline() {
    use crate::supervisor::startup_retirement_ready;
    assert!(!startup_retirement_ready(10, 20, Ok(false)).unwrap());
    assert!(startup_retirement_ready(10, 20, Ok(true)).unwrap());
    assert!(startup_retirement_ready(10, 20, Err("unreadable".into())).is_err());
    assert!(startup_retirement_ready(20, 20, Ok(true)).is_err());
    assert!(startup_retirement_ready(0, 20, Ok(true)).is_err());
}
