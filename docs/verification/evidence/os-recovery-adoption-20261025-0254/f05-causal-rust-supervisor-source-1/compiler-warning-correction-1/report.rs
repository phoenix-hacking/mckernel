// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Literal selected ND_PROCESS_EXEC_WAIT frame, retaining the existing wire keys.
use crate::lifecycle::Check;
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
fn frame_inner(result: &ResultRecord, empty: bool) -> String {
    format!(concat!("ND_PAYLOAD {{\"argv\":[\"/bin/mcexec\",\"-t\",\"1\",\"0\",\"/apps/app\"],",
        "\"cwd\":\"/case/work\",\"env\":{{\"PATH\":\"/usr/bin:/bin\",\"COKERNEL_PATH\":\"/apps\"}},",
        "\"raw_wait_status\":{},\"started_ns\":{},\"reaped_ns\":{},\"finished_ns\":{},",
        "\"streams\":{{\"stdout\":{},\"stderr\":{}}},\"procfs_empty\":{}}}\n"),
        result.status, result.started, result.reaped, result.finished,
        stream_json(&result.out), stream_json(&result.err),
        empty && result.clean && !result.fault && !result.timeout)
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
        return Err("ND_PAYLOAD frame overflow".into());
    }
    Ok(text.into_bytes())
}
