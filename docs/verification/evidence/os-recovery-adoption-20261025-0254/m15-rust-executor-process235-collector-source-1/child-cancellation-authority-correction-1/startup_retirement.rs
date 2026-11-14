// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Original process235 retirement observer with source-bound child authority. It observes existing real
//! exchanges; it does not send an ACK/query, gate the app or change ownership.
use crate::supervisor::{startup_retirement_ready, Check};
use std::collections::{BTreeMap, BTreeSet};
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
fn owner(
    values: &[i128],
    target: i32,
    parent: i32,
    children: &BTreeMap<i32, usize>,
) -> Check<bool> {
    need(
        values[0] == 0 && values[1] == 1 && values[2] > 0 && values[2] <= i32::MAX as i128,
        "foreign process235 lifecycle OS/generation/PID",
    )?;
    let pid = values[2] as i32;
    need(
        pid == parent || children.contains_key(&pid),
        "unlinked process235 lifecycle PID",
    )?;
    Ok(pid == target)
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

// Exact existing5298 _audit_begin_children authority/correspondence algorithm.
// Full snapshots permit child rows before parent RET logging. No PID is adopted
// from first publication, numeric procfs visibility or heuristic ordering.
#[derive(Default)]
struct Syscalls {
    delivered: BTreeMap<(i128, i128), (i128, i128, usize)>,
    returned: BTreeMap<(i128, i128), (i128, i128, usize)>,
    routes: BTreeMap<(i128, i128), (i128, i128, usize)>,
}
fn audit_children(messages: &[&str], parent: i32) -> Check<Option<BTreeMap<i32, usize>>> {
    let mut groups: BTreeMap<i32, Syscalls> = BTreeMap::new();
    let mut publications: BTreeMap<i32, Vec<usize>> = BTreeMap::new();
    for (position, message) in messages.iter().enumerate() {
        if let Some((_, row)) = message.split_once("application_syscall=") {
            let (kind, row) = row
                .split_once(' ')
                .ok_or("malformed process235 syscall row")?;
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
                _ => return Err("unknown process235 syscall row kind".into()),
            };
            let values = fields(row, &names)?;
            need(
                values[0] == 0 && values[1] == 1 && values[2] > 0 && values[2] <= i32::MAX as i128,
                "foreign process235 syscall identity",
            )?;
            need(
                values[3] > 0
                    && values[3] <= u64::MAX as i128
                    && values[4] > 0
                    && values[4] <= u64::MAX as i128,
                "invalid process235 worker/delivery",
            )?;
            let group = groups.entry(values[2] as i32).or_default();
            let records = match kind {
                "delivered" => &mut group.delivered,
                "returned" => &mut group.returned,
                _ => &mut group.routes,
            };
            need(
                records
                    .insert((values[3], values[4]), (values[5], values[6], position))
                    .is_none(),
                "duplicate process235 syscall row",
            )?;
        } else if let Some((_, row)) = message.split_once("application procfs ") {
            let (operation, row) = row
                .split_once(' ')
                .ok_or("malformed process235 procfs row")?;
            let values = fields(row, &["os", "generation", "pid", "tid"])?;
            need(
                values[0] == 0
                    && values[1] == 1
                    && values[2] > 0
                    && values[2] <= i32::MAX as i128
                    && values[2] == values[3],
                "foreign process235 procfs identity",
            )?;
            need(
                matches!(operation, "published" | "deleted"),
                "unknown process235 procfs operation",
            )?;
            if operation == "published" {
                publications
                    .entry(values[2] as i32)
                    .or_default()
                    .push(position);
            }
        }
    }
    let Some(parent_calls)=groups.get(&parent) else { return Ok(None); };
    let mut children = BTreeMap::new();
    let mut clone_pending = false;
    for (key, (cpu, number, begin)) in &parent_calls.delivered {
        if *number != 56 {
            continue;
        }
        let Some((retcpu,value,end))=parent_calls.returned.get(key) else { clone_pending=true; continue; };
        need(
            *retcpu == 0 && *cpu == 0 && begin < end,
            "parent process235 clone correspondence",
        )?;
        if *value <= 0 {
            continue;
        }
        need(
            *value <= i32::MAX as i128
                && *value != parent as i128
                && children.insert(*value as i32, *begin).is_none(),
            "duplicate/parent process235 clone child",
        )?;
    }
    // This is the original235 payload's exact twochildren contract, not a new
    // runtime quota or a general process tree generator.
    need(
        children.len() <= 2,
        "unexpected extra process235 linked child",
    )?;
    let observed: BTreeSet<i32> = groups.keys().chain(publications.keys()).copied().collect();
    let unlinked = observed
        .iter()
        .any(|pid| *pid != parent && !children.contains_key(pid));
    if unlinked {
        if clone_pending {
            return Ok(None);
        }
        return Err("unlinked process235 child syscall/publication PID".into());
    }
    if children.len() != 2 {
        return Ok(None);
    }
    for (child, clone_position) in &children {
        let Some(publication)=publications.get(child) else { return Ok(None); };
        need(
            publication.len() == 1 && publication[0] > *clone_position,
            "missing/duplicate/premature process235 child publication",
        )?;
        let Some(group)=groups.get(child) else { continue; };
        need(
            !group.delivered.is_empty(),
            "process235 child missing actual delivery",
        )?;
        let terminals: BTreeSet<_> = group
            .delivered
            .iter()
            .filter_map(|(key, (_, number, _))| (*number == 60 || *number == 231).then_some(*key))
            .collect();
        need(terminals.len() <= 1, "duplicate process235 child terminal")?;
        let ordinary: BTreeSet<_> = group
            .delivered
            .keys()
            .filter(|key| !terminals.contains(*key))
            .copied()
            .collect();
        need(
            group.returned.keys().copied().collect::<BTreeSet<_>>() == ordinary
                && group
                    .routes
                    .keys()
                    .all(|key| group.returned.contains_key(key)),
            "process235 child syscall correspondence",
        )?;
        let terminal = terminals.iter().next().map(|key| group.delivered[key].2);
        let mut worker_slots = BTreeMap::new();
        for (key, (cpu, _, begin)) in &group.delivered {
            need(
                *cpu == 0 && *begin > publication[0],
                "process235 child CPU/publication order",
            )?;
            if terminals.contains(key) {
                continue;
            }
            let (retcpu, _, end) = group.returned[key];
            need(
                retcpu == 0 && *begin < end && terminal.is_none_or(|terminal| end < terminal),
                "process235 child syscall/terminal order",
            )?;
            let mut slot = 0;
            if let Some((launcher, guest, position)) = group.routes.get(key) {
                need(
                    *launcher == 1 && *guest == 0 && *begin < *position && *position < end,
                    "process235 child route identity/order",
                )?;
                slot = *launcher;
            }
            need(
                *worker_slots.entry(key.0).or_insert(slot) == slot,
                "process235 child worker route changed",
            )?;
        }
    }
    Ok(Some(children))
}
fn lifecycle_complete(snapshot: &[u8], parent: i32) -> Check<bool> {
    let messages = snapshot_messages(snapshot)?;
    let Some(children)=audit_children(&messages,parent)? else { return Ok(false); };
    let complete = lifecycle_for_owner(&messages, parent, parent, &children)?;
    // Validate every genuine child lifecycle row under independently established
    // authority. Child final0 is not a new gate/deadline: original5298 requires
    // parent final0 and full child correspondence, not a per-child run quota.
    for child in children.keys() {
        let _ = lifecycle_for_owner(&messages, *child, parent, &children)?;
    }
    Ok(complete)
}
fn lifecycle_for_owner(
    messages: &[&str],
    pid: i32,
    parent: i32,
    children: &BTreeMap<i32, usize>,
) -> Check<bool> {
    let mut registered = false;
    let mut scheduled = false;
    let mut published = false;
    let mut deleted = false;
    let mut terminal = false;
    let mut intent = false;
    let mut ack = false;
    let mut retired = false;
    let mut query_tokens = BTreeSet::new();
    for message in messages {
        if let Some((_, row)) = message.split_once("application SCHEDULE ") {
            let values = fields(row, &["os", "generation", "pid", "cpu"])?;
            if !owner(&values, pid, parent, children)? {
                continue;
            }
            need(pid == parent, "unexpected child process235 SCHEDULE")?;
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
            if !owner(&values, pid, parent, children)? {
                continue;
            }
            need(values[3] == pid as i128, "unexpected startup nonleader TID")?;
            match operation {
                "published" => {
                    need(
                        (pid != parent || scheduled) && !published && !deleted,
                        "duplicate/premature startup publication",
                    )?;
                    published = true;
                }
                "deleted" => {
                    need(
                        published && (pid != parent || terminal) && !deleted,
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
                    if !owner(&values, pid, parent, children)? {
                        continue;
                    }
                    need(!registered, "duplicate startup registration")?;
                    registered = true;
                }
                "cleanup_requested" => {
                    let values = fields(row, &["os", "generation", "pid", "intent_errno"])?;
                    if !owner(&values, pid, parent, children)? {
                        continue;
                    }
                    need(
                        (pid != parent || terminal) && !intent && values[3] == 0,
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
            if !owner(&values, pid, parent, children)? {
                continue;
            }
            need(
                (pid != parent || terminal)
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
            if !owner(&values, pid, parent, children)? {
                continue;
            }
            need(
                (pid != parent || terminal)
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
            if !owner(&values, pid, parent, children)? {
                continue;
            }
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
                        (pid != parent || values[6] == 231) && published && !terminal,
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
    const CHILD_ROWS: [&str;14] = [
        "application_syscall=delivered os=0 generation=1 pid=258 worker=6 delivery=10 cpu=0 number=56",
        "application procfs published os=0 generation=1 pid=259 tid=259",
        "application_syscall=delivered os=0 generation=1 pid=259 worker=16 delivery=11 cpu=0 number=1",
        "application_syscall=returned os=0 generation=1 pid=259 worker=16 delivery=11 cpu=0 value=0",
        "application_syscall=delivered os=0 generation=1 pid=259 worker=16 delivery=12 cpu=0 number=231",
        "application_syscall=returned os=0 generation=1 pid=258 worker=6 delivery=10 cpu=0 value=259",
        "application procfs deleted os=0 generation=1 pid=259 tid=259",
        "application_syscall=delivered os=0 generation=1 pid=258 worker=6 delivery=20 cpu=0 number=56",
        "application_syscall=returned os=0 generation=1 pid=258 worker=6 delivery=20 cpu=0 value=260",
        "application procfs published os=0 generation=1 pid=260 tid=260",
        "application_syscall=delivered os=0 generation=1 pid=260 worker=26 delivery=21 cpu=0 number=1",
        "application_syscall=returned os=0 generation=1 pid=260 worker=26 delivery=21 cpu=0 value=0",
        "application_syscall=delivered os=0 generation=1 pid=260 worker=26 delivery=22 cpu=0 number=231",
        "application procfs deleted os=0 generation=1 pid=260 tid=260",
    ];
    fn raw_rows(rows: &[&str]) -> Vec<u8> {
        rows.iter()
            .map(|row| format!("<6>[   34.000000] {row}\n"))
            .collect::<String>()
            .into_bytes()
    }
    fn snapshot(rows: &[&str]) -> Vec<u8> {
        let mut actual = Vec::new();
        for row in rows {
            actual.push(*row);
            if *row == "application procfs published os=0 generation=1 pid=258 tid=258" {
                actual.extend(CHILD_ROWS);
            }
        }
        raw_rows(&actual)
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
            "application retirement os=0 generation=1 pid=999 token=514 errno=0",
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
    #[test]
    fn original_two_children_bind_only_by_parent_clone_ret_with_early_publication_allowed() {
        let raw = complete();
        let messages = snapshot_messages(&raw).unwrap();
        let children = audit_children(&messages, 258).unwrap().unwrap();
        assert_eq!(children.keys().copied().collect::<Vec<_>>(), [259, 260]);
        assert!(StartupRetirement::new(258)
            .unwrap()
            .observe(&raw, 10, 50, Ok(true))
            .unwrap());
        assert!(
            raw.windows(CHILD_ROWS[1].len())
                .position(|x| x == CHILD_ROWS[1].as_bytes())
                .unwrap()
                < raw
                    .windows(CHILD_ROWS[5].len())
                    .position(|x| x == CHILD_ROWS[5].as_bytes())
                    .unwrap()
        );
    }
    #[test]
    fn foreign_or_duplicate_child_authority_and_premature_publication_fail() {
        let raw = String::from_utf8(complete()).unwrap();
        for changed in [
            raw.replace("value=260", "value=259"),
            raw.replace("pid=260", "pid=999"),
            raw.replace("number=56", "number=57"),
        ] {
            assert!(StartupRetirement::new(258)
                .unwrap()
                .observe(changed.as_bytes(), 10, 50, Ok(true))
                .is_err());
        }
        let mut rows = vec![CHILD_ROWS[1], CHILD_ROWS[0]];
        rows.extend_from_slice(&CHILD_ROWS[2..]);
        let raw = raw_rows(&rows);
        let messages = snapshot_messages(&raw).unwrap();
        assert!(audit_children(&messages, 258).is_err());
    }
    #[test]
    fn child_missing_return_duplicate_or_foreign_rows_are_never_filtered() {
        let raw = String::from_utf8(complete()).unwrap();
        let returned = format!("<6>[   34.000000] {}\n", CHILD_ROWS[3]);
        for changed in [
            raw.replace(&returned, ""),
            raw.replace(&returned, &format!("{returned}{returned}")),
            raw.replace("generation=1 pid=259", "generation=2 pid=259"),
            raw.replace("cpu=0 number=1", "cpu=2 number=1"),
        ] {
            assert!(StartupRetirement::new(258)
                .unwrap()
                .observe(changed.as_bytes(), 10, 50, Ok(true))
                .is_err());
        }
    }
    #[test]
    fn original_cancelled_child_without_terminal_accepts_owned_delete_and_optional_cleanup_rows() {
        let mut raw = String::from_utf8(complete()).unwrap();
        for row in [CHILD_ROWS[4], CHILD_ROWS[12]] {
            raw = raw.replace(&format!("<6>[   34.000000] {row}\n"), "");
        }
        let deleted = format!("<6>[   34.000000] {}\n", CHILD_ROWS[6]);
        let optional = raw_rows(&[
            "application_process=cleanup_requested os=0 generation=1 pid=259 intent_errno=0",
            "application cleanup ACK os=0 generation=1 pid=259 token=30 errno=0 abandoned=1",
            "application retirement os=0 generation=1 pid=259 token=31 errno=-11",
        ]);
        raw = raw.replace(
            &deleted,
            &format!("{deleted}{}", String::from_utf8(optional).unwrap()),
        );
        // Both children retain actual clone authority/publication and complete
        // ordinary correspondence. There is no childterminal or childfinal0.
        assert!(StartupRetirement::new(258)
            .unwrap()
            .observe(raw.as_bytes(), 10, 50, Ok(true))
            .unwrap());
        // The parent's terminal remains mandatory; this is not a global waiver.
        let parent_terminal = format!("<6>[   34.000000] {}\n", PREFIX[3]);
        let missing_parent = raw.replace(&parent_terminal, "");
        assert!(StartupRetirement::new(258)
            .unwrap()
            .observe(missing_parent.as_bytes(), 10, 50, Ok(true))
            .is_err());
    }
}
