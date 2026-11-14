// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Valid idle diagnostics only; reuse the accepted process supervisor unchanged.
use crate::{profile, report, supervisor::*};
use std::fs::File;
use std::os::fd::AsRawFd;

fn capture_one(tag: &str, argv: &[&str], outer: u64, safe: &mut bool,
               console: Option<&File>) -> Check<ResultRecord> {
    let record = supervise(argv[0], argv, HELPER_ENV, Some(profile::PAYLOAD_CWD), 10_000, outer);
    if !record.clean {
        *safe = false;
    }
    for (name, stream) in [("stdout", &record.out), ("stderr", &record.err)] {
        save(&format!("/case/evidence/{tag}.{name}"), &stream.data, outer)?;
        let row = format!("M15_BFD_PROBE_STREAM {{\"tag\":\"{tag}\",\"stream\":\"{name}\",\"capture\":{}}}\n",
                          report::stream_json(stream));
        let console = console.ok_or("missing diagnostic console")?;
        write_all_bounded(console.as_raw_fd(), row.as_bytes(), outer)?;
    }
    let status = format!("M15_BFD_PROBE_STATUS {{\"tag\":\"{tag}\",\"raw_wait_status\":{},\"fault\":{},\"timeout\":{},\"clean\":{},\"stage\":{},\"errno\":{},\"started_ns\":{},\"reaped_ns\":{},\"finished_ns\":{}}}\n",
                         record.status, record.fault, record.timeout, record.clean,
                         record.child_stage, record.child_errno, record.started, record.reaped, record.finished);
    save(&format!("/case/evidence/{tag}.status"), status.as_bytes(), outer)?;
    write_all_bounded(console.ok_or("missing diagnostic console")?.as_raw_fd(), status.as_bytes(), outer)?;
    if record.status != 0 || record.fault || record.timeout || !record.clean ||
       !record.out.eof || !record.err.eof ||
       record.out.observed != record.out.data.len() as u64 ||
       record.err.observed != record.err.data.len() as u64 || !record.err.data.is_empty() {
        return Err(format!("valid idle diagnostic {tag} failed; preserve actual captures"));
    }
    Ok(record)
}

pub fn capture_pair(outer: u64, safe: &mut bool, console: Option<&File>) -> Check<ResultRecord> {
    if !procfs_empty()? {
        return Err("idle baseline has user process nodes".into());
    }
    // Reuse the retained original-C BFD reference artifact. Neither invocation
    // launches a McKernel application or changes the diagnostic tool sources.
    let reference = capture_one("reference", profile::REFERENCE_ARGV, outer, safe, console)?;
    if !procfs_empty()? {
        return Err("reference probe changed idle process namespace".into());
    }
    let current = capture_one("current", profile::PAYLOAD_ARGV, outer, safe, console)?;
    if !procfs_empty()? || reference.out.data != current.out.data || reference.err.data != current.err.data {
        return Err("paired valid idle diagnostic streams/state differ".into());
    }
    // Semantic PS rows/CPU-idle facts are checked independently off-guest.
    // Equality or exit0 alone never supplies valid-diagnostic acceptance.
    Ok(current)
}
