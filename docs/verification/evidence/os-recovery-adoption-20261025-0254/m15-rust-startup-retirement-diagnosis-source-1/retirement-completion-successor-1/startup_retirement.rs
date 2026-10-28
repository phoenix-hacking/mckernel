// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! One parent-only startup retirement observer. It observes existing real
//! exchanges; it does not send an ACK/query, gate the app or change ownership.
use crate::supervisor::{startup_retirement_ready, Check};
use std::collections::BTreeSet;
const RAW_LIMIT: usize = 262_144;
fn need(ok: bool, why: &str) -> Check<()> {
    if ok {
        Ok(())
    } else {
        Err(why.to_owned())
    }
}
fn fields(row: &str, names: &[&str]) -> Check<Vec<i128>> {
    let words: Vec<_> = row.split_whitespace().collect();
    need(
        words.len() == names.len(),
        "startup lifecycle row field count",
    )?;
    words
        .iter()
        .zip(names)
        .map(|(word, name)| {
            let value = word
                .strip_prefix(&format!("{name}="))
                .ok_or_else(|| format!("startup lifecycle expected {name}: {row}"))?;
            need(
                !value.is_empty() && !value.starts_with('+'),
                "invalid startup lifecycle number",
            )?;
            value
                .parse::<i128>()
                .map_err(|_| format!("invalid startup lifecycle integer: {row}"))
        })
        .collect()
}
fn owner(values: &[i128], pid: i32) -> Check<()> {
    need(
        values[0] == 0 && values[1] == 1 && values[2] == pid as i128,
        "foreign startup lifecycle OS/generation/PID",
    )
}

/// Exact selected raw klogctl envelope grammar reused from the reviewed F05
/// source. Every body remains byte-exact and in order; unknown envelopes fail.
fn snapshot_messages(snapshot: &[u8]) -> Check<Vec<&str>> {
    let text = std::str::from_utf8(snapshot).map_err(|_| "startup raw snapshot is not UTF8")?;
    need(
        text.is_empty() || text.ends_with('\n'),
        "incomplete startup raw kernel record",
    )?;
    let mut messages = Vec::new();
    for line in text.split_terminator('\n') {
        let after_open = line
            .strip_prefix('<')
            .ok_or("unexpected startup raw envelope/continuation")?;
        let (priority, after_priority) = after_open
            .split_once('>')
            .ok_or("missing startup raw priority delimiter")?;
        need(
            !priority.is_empty() && priority.bytes().all(|b| b.is_ascii_digit()),
            "invalid startup raw priority",
        )?;
        need(
            priority
                .parse::<u32>()
                .map_err(|_| "startup priority overflow")?
                <= 191,
            "startup priority range",
        )?;
        let after_bracket = after_priority
            .strip_prefix('[')
            .ok_or("missing startup raw timestamp")?;
        let (timestamp, body) = after_bracket
            .split_once("] ")
            .ok_or("invalid startup raw timestamp delimiter")?;
        let timestamp = timestamp.trim_start_matches(' ');
        let (seconds, fraction) = timestamp
            .split_once('.')
            .ok_or("invalid startup raw timestamp precision")?;
        need(
            !seconds.is_empty()
                && seconds.bytes().all(|b| b.is_ascii_digit())
                && fraction.len() == 6
                && fraction.bytes().all(|b| b.is_ascii_digit()),
            "invalid startup raw timestamp grammar",
        )?;
        messages.push(body);
    }
    Ok(messages)
}

fn lifecycle_complete(snapshot: &[u8], pid: i32) -> Check<bool> {
    let mut registered = false;
    let mut scheduled = false;
    let mut published = false;
    let mut deleted = false;
    let mut terminal = false;
    let mut intent = false;
    let mut ack = false;
    let mut retired = false;
    let mut query_tokens = BTreeSet::new();
    for message in snapshot_messages(snapshot)? {
        if let Some((_, row)) = message.split_once("application SCHEDULE ") {
            let values = fields(row, &["os", "generation", "pid", "cpu"])?;
            owner(&values, pid)?;
            need(
                !scheduled && values[3] == 0,
                "duplicate/foreign startup schedule",
            )?;
            scheduled = true;
        } else if let Some((_, row)) = message.split_once("application procfs ") {
            let (operation, row) = row
                .split_once(' ')
                .ok_or("malformed startup procfs lifecycle")?;
            let values = fields(row, &["os", "generation", "pid", "tid"])?;
            owner(&values, pid)?;
            need(values[3] == pid as i128, "unexpected startup nonleader TID")?;
            match operation {
                "published" => {
                    need(
                        scheduled && !published && !deleted,
                        "duplicate/premature startup publication",
                    )?;
                    published = true;
                }
                "deleted" => {
                    need(
                        published && terminal && !deleted,
                        "duplicate/premature startup DELETE",
                    )?;
                    deleted = true;
                }
                _ => return Err("unknown startup procfs lifecycle operation".into()),
            }
        } else if let Some((_, row)) = message.split_once("application_process=") {
            let (operation, row) = row
                .split_once(' ')
                .ok_or("malformed startup process lifecycle")?;
            match operation {
                "registered" => {
                    let values = fields(row, &["os", "generation", "pid"])?;
                    owner(&values, pid)?;
                    need(!registered, "duplicate startup registration")?;
                    registered = true;
                }
                "cleanup_requested" => {
                    let values = fields(row, &["os", "generation", "pid", "intent_errno"])?;
                    owner(&values, pid)?;
                    need(
                        terminal && !intent && values[3] == 0,
                        "premature/duplicate/failed startup cleanup intent",
                    )?;
                    intent = true;
                }
                _ => return Err("unexpected startup process lifecycle operation".into()),
            }
        } else if let Some((_, row)) = message.split_once("application cleanup ACK ") {
            let values = fields(
                row,
                &["os", "generation", "pid", "token", "errno", "abandoned"],
            )?;
            owner(&values, pid)?;
            need(
                terminal
                    && !ack
                    && values[3] > 0
                    && values[3] <= u64::MAX as i128
                    && values[4] == 0
                    && (values[5] == 0 || values[5] == 1),
                "premature/duplicate/failed startup cleanup ACK",
            )?;
            // ACK may precede intent logging; abandoned1 is explicitly allowed
            // by the unchanged original checker. Neither is final retirement.
            ack = true;
        } else if let Some((_, row)) = message.split_once("application retirement ") {
            let values = fields(row, &["os", "generation", "pid", "token", "errno"])?;
            owner(&values, pid)?;
            need(
                terminal
                    && ack
                    && !retired
                    && query_tokens.len() < 12
                    && values[3] > 0
                    && values[3] <= u64::MAX as i128,
                "premature/excess/finalized startup retirement query",
            )?;
            need(
                query_tokens.insert(values[3] as u64),
                "duplicate startup retirement query token",
            )?;
            need(
                values[4] == -11 || values[4] == 0,
                "unexpected startup retirement errno",
            )?;
            retired = values[4] == 0;
        } else if let Some((_, row)) = message.split_once("application_syscall=") {
            let (kind, row) = row.split_once(' ').ok_or("malformed startup syscall row")?;
            let names = match kind {
                "delivered" => [
                    "os",
                    "generation",
                    "pid",
                    "worker",
                    "delivery",
                    "cpu",
                    "number",
                ],
                "returned" => [
                    "os",
                    "generation",
                    "pid",
                    "worker",
                    "delivery",
                    "cpu",
                    "value",
                ],
                "return_route" => [
                    "os",
                    "generation",
                    "pid",
                    "worker",
                    "delivery",
                    "launcher_cpu",
                    "guest_cpu",
                ],
                _ => return Err("unknown startup syscall row kind".into()),
            };
            let values = fields(row, &names)?;
            owner(&values, pid)?;
            need(
                values[3] > 0
                    && values[3] <= u64::MAX as i128
                    && values[4] > 0
                    && values[4] <= u64::MAX as i128,
                "invalid startup syscall worker/delivery",
            )?;
            need(
                if kind == "return_route" {
                    values[5] == 1 && values[6] == 0
                } else {
                    values[5] == 0
                },
                "invalid startup syscall CPU/route",
            )?;
            if kind == "delivered" {
                need(values[6] >= 0, "negative startup syscall number")?;
                if values[6] == 60 || values[6] == 231 {
                    need(
                        values[6] == 231 && published && !terminal,
                        "unexpected/premature/duplicate startup terminal",
                    )?;
                    terminal = true;
                }
            }
            // Keep every ordinary row in the actual raw snapshot. The unchanged
            // full evaluator remains the authority for its full correspondence
            // and trace predicates; this observer does not project/filter it.
        }
    }
    Ok(registered && scheduled && published && terminal && intent && ack && deleted && retired)
}

pub struct StartupRetirement {
    leader_pid: i32,
    previous: Vec<u8>,
}
impl StartupRetirement {
    pub fn new(leader_pid: i32) -> Check<Self> {
        need(
            leader_pid > 1,
            "missing actual spawned startup launcher PID",
        )?;
        Ok(Self {
            leader_pid,
            previous: Vec::new(),
        })
    }
    pub fn observe(
        &mut self,
        raw: &[u8],
        current: u64,
        end: u64,
        namespace: Check<bool>,
    ) -> Check<bool> {
        let namespace_empty = startup_retirement_ready(current, end, namespace)?;
        need(
            raw.len() < RAW_LIMIT,
            "startup retirement raw snapshot overflow",
        )?;
        need(
            raw.starts_with(&self.previous),
            "startup raw snapshot prefix lost/rewritten/wrapped",
        )?;
        let complete = lifecycle_complete(raw, self.leader_pid)?;
        self.previous.clear();
        self.previous.extend_from_slice(raw);
        Ok(namespace_empty && complete)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn snapshot(rows: &[&str]) -> Vec<u8> {
        rows.iter()
            .map(|row| format!("<6>[   34.000000] {row}\n"))
            .collect::<String>()
            .into_bytes()
    }
    const PREFIX: [&str;6]=[
        "application_process=registered os=0 generation=1 pid=258",
        "application SCHEDULE os=0 generation=1 pid=258 cpu=0",
        "application procfs published os=0 generation=1 pid=258 tid=258",
        "application_syscall=delivered os=0 generation=1 pid=258 worker=6 delivery=512 cpu=0 number=231",
        "application_process=cleanup_requested os=0 generation=1 pid=258 intent_errno=0",
        "application cleanup ACK os=0 generation=1 pid=258 token=3 errno=0 abandoned=1",
    ];
    const NEGATIVE: &str = "application retirement os=0 generation=1 pid=258 token=513 errno=-11";
    const DELETE: &str = "application procfs deleted os=0 generation=1 pid=258 tid=258";
    const FINAL: &str = "application retirement os=0 generation=1 pid=258 token=514 errno=0";
    fn pending() -> Vec<u8> {
        snapshot(&[PREFIX.as_slice(), &[NEGATIVE, DELETE]].concat())
    }
    fn complete() -> Vec<u8> {
        snapshot(&[PREFIX.as_slice(), &[NEGATIVE, DELETE, FINAL]].concat())
    }
    #[test]
    fn actual_negative_delete_empty_then_fresh_late_zero_completes() {
        let mut state = StartupRetirement::new(258).unwrap();
        assert!(!state.observe(&pending(), 10, 50, Ok(true)).unwrap());
        assert!(state.observe(&complete(), 20, 50, Ok(true)).unwrap());
    }
    #[test]
    fn permanent_negative_and_shortcuts_cannot_complete_at_original_deadline() {
        for raw in [
            pending(),
            snapshot(&PREFIX),
            snapshot(&PREFIX[..3]),
            Vec::new(),
        ] {
            let mut state = StartupRetirement::new(258).unwrap();
            assert!(!state.observe(&raw, 10, 50, Ok(true)).unwrap());
            assert!(state.observe(&raw, 50, 50, Ok(true)).is_err());
        }
        assert!(!StartupRetirement::new(258)
            .unwrap()
            .observe(&complete(), 10, 50, Ok(false))
            .unwrap());
    }
    #[test]
    fn wrong_owner_duplicate_token_bad_errno_and_excess_queries_fail() {
        for bad in [
            "application retirement os=0 generation=2 pid=258 token=514 errno=0",
            "application retirement os=0 generation=1 pid=259 token=514 errno=0",
            "application retirement os=0 generation=1 pid=258 token=513 errno=0",
            "application retirement os=0 generation=1 pid=258 token=514 errno=-5",
        ] {
            let raw = snapshot(&[PREFIX.as_slice(), &[NEGATIVE, DELETE, bad]].concat());
            assert!(StartupRetirement::new(258)
                .unwrap()
                .observe(&raw, 10, 50, Ok(true))
                .is_err());
        }
        let mut raw = snapshot(&PREFIX);
        for token in 500..512 {
            raw.extend(snapshot(&[&format!(
                "application retirement os=0 generation=1 pid=258 token={token} errno=-11"
            )]));
        }
        raw.extend(snapshot(&[FINAL]));
        assert!(StartupRetirement::new(258)
            .unwrap()
            .observe(&raw, 10, 50, Ok(true))
            .is_err());
    }
    #[test]
    fn query_before_ack_or_terminal_and_duplicate_delete_or_unknown_rows_fail() {
        for rows in [
            [&PREFIX[..3], &[FINAL]].concat(),
            [&PREFIX[..5], &[FINAL]].concat(),
            [PREFIX.as_slice(), &[NEGATIVE, DELETE, DELETE, FINAL]].concat(),
            [
                PREFIX.as_slice(),
                &["application procfs invented os=0 generation=1 pid=258 tid=258"],
            ]
            .concat(),
        ] {
            assert!(StartupRetirement::new(258)
                .unwrap()
                .observe(&snapshot(&rows), 10, 50, Ok(true))
                .is_err());
        }
    }
    #[test]
    fn missing_delete_unreadable_namespace_and_late_zero_do_not_complete() {
        let raw = snapshot(&[PREFIX.as_slice(), &[NEGATIVE, FINAL]].concat());
        assert!(!StartupRetirement::new(258)
            .unwrap()
            .observe(&raw, 10, 50, Ok(true))
            .unwrap());
        assert!(StartupRetirement::new(258)
            .unwrap()
            .observe(&complete(), 10, 50, Err("unreadable".into()))
            .is_err());
        assert!(StartupRetirement::new(258)
            .unwrap()
            .observe(&complete(), 50, 50, Ok(true))
            .is_err());
    }
    #[test]
    fn raw_prefix_loss_overflow_and_incomplete_envelope_fail_without_reconstruction() {
        let mut state = StartupRetirement::new(258).unwrap();
        state.observe(&pending(), 10, 50, Ok(true)).unwrap();
        assert!(state
            .observe(&snapshot(&[FINAL]), 20, 50, Ok(true))
            .is_err());
        assert!(StartupRetirement::new(258)
            .unwrap()
            .observe(&vec![b'x'; RAW_LIMIT], 10, 50, Ok(true))
            .is_err());
        assert!(StartupRetirement::new(258)
            .unwrap()
            .observe(b"unknown raw continuation\n", 10, 50, Ok(true))
            .is_err());
    }
}
