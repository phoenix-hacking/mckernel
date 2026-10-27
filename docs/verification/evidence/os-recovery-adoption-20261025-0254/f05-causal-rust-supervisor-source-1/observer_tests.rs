// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Mocked kmsg transport uses private nonblocking Unix datagrams (one genuine
//! read per injected record), never /dev/kmsg, /proc/mcos0 or PID1 main.
use super::*;
use std::os::fd::{FromRawFd, IntoRawFd};
use std::os::unix::net::UnixDatagram;
struct Fixture {
    observer: Observer,
    writer: UnixDatagram,
    directory: PathBuf,
}
impl Fixture {
    fn new() -> Self {
        let directory = std::env::temp_dir().join(format!(
            "f05-causal-observer-{}-{}",
            std::process::id(),
            now_ns()
        ));
        std::fs::create_dir(&directory).unwrap();
        let gate_path = directory.join("gate");
        let gate = OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&gate_path)
            .unwrap();
        let metadata = gate.metadata().unwrap();
        let retained = OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(directory.join("raw"))
            .unwrap();
        let (reader, writer) = UnixDatagram::pair().unwrap();
        reader.set_nonblocking(true).unwrap();
        // into_raw_fd transfers ownership of this test-only socket to File;
        // File::read calls read(2), which preserves a single datagram here.
        let ring = unsafe { File::from_raw_fd(reader.into_raw_fd()) };
        Self {
            observer: Observer {
                gate,
                gate_path,
                ring,
                retained,
                sequence: KmsgSequence::default(),
                lifecycle: Some(crate::tests::initial()),
                original_gate_identity: (metadata.dev(), metadata.ino()),
                messages: BTreeMap::new(),
                caught_up: false,
                failure: None,
            },
            writer,
            directory,
        }
    }
    fn row(&self, sequence: u64, text: &str) -> Vec<u8> {
        let record = format!("6,{sequence},{sequence},-;{text}\n").into_bytes();
        assert_eq!(self.writer.send(&record).unwrap(), record.len());
        record
    }
    fn finish_child(&self, final_sequence: u64) -> Vec<u8> {
        let mut bytes = self.row(
            1,
            "application procfs deleted os=0 generation=1 pid=257 tid=257",
        );
        bytes.extend(self.row(
            final_sequence,
            "application retirement os=0 generation=1 pid=257 token=42 errno=0",
        ));
        bytes
    }
    fn gate_bytes(&self) -> Vec<u8> {
        std::fs::read(self.directory.join("gate")).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.directory).unwrap();
    }
}
#[test]
fn mocked_observer_writes_one_real_g_and_retains_exact_raw_records() {
    let mut fixture = Fixture::new();
    assert!(fixture.observer.service(true));
    assert!(fixture.gate_bytes().is_empty());
    let records = fixture.finish_child(2);
    assert!(fixture.observer.service(true));
    assert_eq!(fixture.gate_bytes(), b"G");
    assert!(fixture.observer.service(true));
    assert_eq!(fixture.gate_bytes(), b"G");
    assert_eq!(
        std::fs::read(fixture.directory.join("raw")).unwrap(),
        records
    );
    let snapshot=b"<6>[ 1.0] application procfs deleted os=0 generation=1 pid=257 tid=257\n<6>[ 2.0] application retirement os=0 generation=1 pid=257 token=42 errno=0\n";
    assert!(fixture
        .observer
        .final_snapshot_covers_observation(snapshot)
        .is_ok());
    assert!(fixture
        .observer
        .final_snapshot_covers_observation(b"missing actual record\n")
        .is_err());
}
#[test]
fn mocked_gap_poison_preserves_offending_record_and_never_releases() {
    let mut fixture = Fixture::new();
    let records = fixture.finish_child(3);
    assert!(!fixture.observer.service(true));
    assert!(fixture.gate_bytes().is_empty());
    assert_eq!(
        std::fs::read(fixture.directory.join("raw")).unwrap(),
        records
    );
    assert!(!fixture.observer.service(true));
}
#[test]
fn mocked_foreign_owner_never_releases() {
    let mut fixture = Fixture::new();
    fixture.row(
        1,
        "application procfs deleted os=0 generation=2 pid=257 tid=257",
    );
    assert!(!fixture.observer.service(true));
    assert!(fixture.gate_bytes().is_empty());
}
#[test]
fn mocked_missing_or_replaced_gate_refuses_actual_write() {
    for replace in [false, true] {
        let mut fixture = Fixture::new();
        fixture.finish_child(2);
        std::fs::rename(
            fixture.directory.join("gate"),
            fixture.directory.join("original-gate"),
        )
        .unwrap();
        if replace {
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .open(fixture.directory.join("gate"))
                .unwrap();
        }
        assert!(!fixture.observer.service(true));
        assert!(std::fs::read(fixture.directory.join("original-gate"))
            .unwrap()
            .is_empty());
    }
}
#[test]
fn mocked_actual_gate_write_failure_is_not_recorded_as_release() {
    let mut fixture = Fixture::new();
    fixture.finish_child(2);
    fixture.observer.gate = File::open(fixture.directory.join("gate")).unwrap();
    assert!(!fixture.observer.service(true));
    assert!(fixture.gate_bytes().is_empty());
    assert!(!fixture.observer.complete());
}
#[test]
fn mocked_post_reap_service_cannot_release_gate() {
    let mut fixture = Fixture::new();
    fixture.finish_child(2);
    assert!(fixture.observer.service(false));
    assert!(fixture.gate_bytes().is_empty());
    assert!(!fixture.observer.complete());
}
#[test]
fn mocked_backlog_defers_gate_until_all_queued_rows_are_validated() {
    let mut fixture = Fixture::new();
    fixture.finish_child(2);
    for sequence in 3..43 {
        fixture.row(sequence, "unrelated ordinary kernel message");
    }
    assert!(fixture.observer.service(true));
    assert!(fixture.gate_bytes().is_empty());
    assert!(!fixture.observer.complete());
    assert!(fixture.observer.service(true));
    assert_eq!(fixture.gate_bytes(), b"G");
}
