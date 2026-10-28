// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Fixed valid paired idle diagnostic frame, with a distinct case prefix.
use crate::profile::{argv_json, PAYLOAD_CWD};
use crate::supervisor::Check;
use crate::supervisor::{ResultRecord, Stream, STREAM_LIMIT};
use std::fmt::Write;

pub fn stream_json(stream: &Stream) -> String {
    let mut hex = String::with_capacity(stream.data.len() * 2);
    for byte in &stream.data {
        write!(hex, "{byte:02x}").unwrap();
    }
    format!("{{\"hex\":\"{}\",\"eof\":{},\"truncated\":{},\"observed\":{},\"retained\":{},\"discarded\":{},\"limit\":{},\"eof_ns\":{}}}",
        hex, stream.eof, stream.observed != stream.data.len() as u64,
        stream.observed, stream.data.len(), stream.observed - stream.data.len() as u64,
        STREAM_LIMIT, stream.eof_ns)
}
fn summary_json(stream: &Stream) -> String {
    // Complete bytes are emitted once in bounded M15_BFD_PROBE_STREAM records.
    // The final <=4096-byte status envelope carries counts rather than copies.
    format!("{{\"eof\":{},\"truncated\":{},\"observed\":{},\"retained\":{},\"discarded\":{},\"limit\":{},\"eof_ns\":{}}}",
        stream.eof, stream.observed != stream.data.len() as u64,
        stream.observed, stream.data.len(), stream.observed - stream.data.len() as u64,
        STREAM_LIMIT, stream.eof_ns)
}
fn frame_inner(result: &ResultRecord, empty: bool) -> String {
    format!(
        concat!(
            "M15_BFD_PS_RESULT {{\"argv\":{},",
            "\"cwd\":\"{}\",\"env\":{{\"PATH\":\"/bin:/sbin:/usr/bin:/usr/sbin\",\"LC_ALL\":\"C\"}},",
            "\"raw_wait_status\":{},\"started_ns\":{},\"reaped_ns\":{},\"finished_ns\":{},",
            "\"streams\":{{\"stdout\":{},\"stderr\":{}}},\"procfs_empty\":{}}}\n"
        ),
        argv_json(),
        PAYLOAD_CWD,
        result.status,
        result.started,
        result.reaped,
        result.finished,
        summary_json(&result.out),
        summary_json(&result.err),
        empty && result.clean && !result.fault && !result.timeout
    )
}
pub fn frame(result: &ResultRecord, empty: bool) -> Check<Vec<u8>> {
    let mut text = frame_inner(result, empty);
    // Preserve predecessor fallback on a full pair of retained streams, rather
    // than extending FRAME_LIMIT or claiming an incomplete frame was valid.
    if text.len() >= 4096 {
        let mut failed = result.clone();
        failed.fault = true;
        failed.out.data.clear();
        failed.err.data.clear();
        text = frame_inner(&failed, false);
    }
    if text.len() >= 4096 {
        return Err("M15_BFD_PS_RESULT frame overflow".into());
    }
    Ok(text.into_bytes())
}
