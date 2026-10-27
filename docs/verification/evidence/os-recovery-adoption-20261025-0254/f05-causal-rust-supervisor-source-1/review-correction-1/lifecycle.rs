// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Observation of the existing real cleanup/retirement protocol, not its producer.
use std::collections::{BTreeMap, BTreeSet};

pub type Check<T> = Result<T, String>;
pub const RAW_LIMIT: usize = 262_144;
pub const GATE_BASENAME: &str = ".f05-gate-31770ebb739fea402ded939617921dda";
pub const GATE_PATH: &str = "/case/work/.f05-gate-31770ebb739fea402ded939617921dda";
pub const CASE_ID: &str = "M14-05-05-owned-processvm-v3-causal-204B";

fn need(ok: bool, why: &str) -> Check<()> {
    if ok {
        Ok(())
    } else {
        Err(why.to_owned())
    }
}
fn fields(row: &str, names: &[&str]) -> Check<Vec<i128>> {
    let words: Vec<_> = row.split_whitespace().collect();
    need(words.len() == names.len(), "lifecycle row field count")?;
    words
        .iter()
        .zip(names)
        .map(|(word, name)| {
            let value = word
                .strip_prefix(&format!("{name}="))
                .ok_or_else(|| format!("lifecycle row expected {name}: {row}"))?;
            need(
                !value.is_empty() && !value.starts_with('+'),
                "invalid signed decimal field",
            )?;
            value
                .parse::<i128>()
                .map_err(|_| format!("invalid lifecycle integer: {row}"))
        })
        .collect()
}

/// Extract only the owner prefix for bounded deferral. Full original row schema
/// and state/order checks still run on every retained row during strict replay.
fn pending_owner(message: &str) -> Check<Option<i128>> {
    for marker in [
        "application procfs ",
        "application_process=",
        "application_syscall=",
        "application cleanup ACK ",
        "application retirement ",
    ] {
        if let Some((_, suffix)) = message.split_once(marker) {
            let row = if matches!(
                marker,
                "application procfs " | "application_process=" | "application_syscall="
            ) {
                suffix
                    .split_once(' ')
                    .ok_or("malformed pending lifecycle row")?
                    .1
            } else {
                suffix
            };
            let prefix = row.split_whitespace().take(3).collect::<Vec<_>>().join(" ");
            let identity = fields(&prefix, &["os", "generation", "pid"])?;
            need(
                identity[0] == 0 && identity[1] == 1,
                "wrong pending lifecycle OS/generation",
            )?;
            need(
                identity[2] > 0 && identity[2] <= i32::MAX as i128,
                "invalid pending lifecycle PID",
            )?;
            return Ok(Some(identity[2]));
        }
    }
    Ok(None)
}
struct PendingRow {
    position: u64,
    message: String,
}

#[derive(Default, Debug)]
struct Owner {
    published: bool,
    deleted: bool,
    terminal: bool,
    intent: bool,
    ack: Option<u64>,
    query_tokens: BTreeSet<u64>,
    retired: bool,
}
impl Owner {
    fn complete(&self) -> bool {
        self.published
            && self.deleted
            && self.terminal
            && self.intent
            && self.ack.is_some()
            && self.retired
    }
}
#[derive(Debug)]
struct Call {
    position: u64,
    number: i64,
    returned: bool,
    routed: bool,
}

/// A single spawned launcher's PID is pinned by the unreaped Linux child.
/// Its McKernel parent identity is checked against that PID, never discovered
/// by accepting the first arbitrary SCHEDULE row. The selected launcher assigns
/// the descriptor PID from getpid(); the frozen source/object join remains a
/// Root adoption prerequisite.
pub struct Lifecycle {
    parent_pid: i32,
    child_pid: Option<i32>,
    parent: Owner,
    child: Owner,
    scheduled: bool,
    registered: bool,
    reaped_child: bool,
    child_write_returned: bool,
    child_write_count: usize,
    gate_released: bool,
    calls: BTreeMap<(i32, u64, u64), Call>,
    position: u64,
    child_clone_position: Option<u64>,
    pending: Vec<PendingRow>,
    pending_bytes: usize,
}
impl Lifecycle {
    pub fn new(parent_pid: i32) -> Check<Self> {
        need(
            parent_pid > 1,
            "actual supervised launcher PID must be positive",
        )?;
        Ok(Self {
            parent_pid,
            child_pid: None,
            parent: Owner::default(),
            child: Owner::default(),
            scheduled: false,
            registered: false,
            reaped_child: false,
            child_write_returned: false,
            child_write_count: 0,
            gate_released: false,
            calls: BTreeMap::new(),
            position: 0,
            child_clone_position: None,
            pending: Vec::new(),
            pending_bytes: 0,
        })
    }
    fn owner(&mut self, pid: i128) -> Check<&mut Owner> {
        if pid == self.parent_pid as i128 {
            return Ok(&mut self.parent);
        }
        if Some(pid) == self.child_pid.map(i128::from) {
            return Ok(&mut self.child);
        }
        Err(format!(
            "foreign lifecycle PID {pid}; expected actual parent and linked child"
        ))
    }
    fn identity(&mut self, values: &[i128]) -> Check<()> {
        need(
            values[0] == 0 && values[1] == 1,
            "wrong lifecycle OS/generation",
        )?;
        self.owner(values[2]).map(|_| ())
    }
    pub fn child_ready(&self) -> bool {
        !self.gate_released
            && self.pending.is_empty()
            && self.scheduled
            && self.registered
            && self.parent.published
            && self.child_pid.is_some()
            && self.child.complete()
            && self.reaped_child
            && self.child_write_count == 1
            && self.child_write_returned
            && !self.parent.terminal
    }
    /// Call only after an actual exactly-one-byte write to the retained gate fd.
    pub fn record_gate_write(&mut self) -> Check<()> {
        need(
            !self.gate_released && self.child_ready(),
            "premature/duplicate gate release",
        )?;
        self.gate_released = true;
        Ok(())
    }
    pub fn complete(&self) -> bool {
        self.pending.is_empty()
            && self.gate_released
            && self.parent.complete()
            && self.child.complete()
    }
    pub fn accept(&mut self, message: &str) -> Check<()> {
        self.position = self
            .position
            .checked_add(1)
            .ok_or("lifecycle row position overflow")?;
        let position = self.position;
        if self.child_pid.is_none() {
            if let Some(pid) = pending_owner(message)? {
                if pid != self.parent_pid as i128 {
                    self.pending_bytes = self
                        .pending_bytes
                        .checked_add(message.len())
                        .ok_or("pending row bytes overflow")?;
                    need(
                        self.pending_bytes <= RAW_LIMIT && self.pending.len() < 256,
                        "unbound lifecycle row storage exceeded original fixed capture bounds",
                    )?;
                    self.pending.push(PendingRow {
                        position,
                        message: message.to_owned(),
                    });
                    return Ok(());
                }
            }
        }
        self.accept_bound(message, position)?;
        if self.child_pid.is_some() && !self.pending.is_empty() {
            let clone_position = self
                .child_clone_position
                .ok_or("missing authoritative clone delivery position")?;
            let pending = std::mem::take(&mut self.pending);
            self.pending_bytes = 0;
            // Only the actual positive matched parent RET supplies authority.
            // Preserve every buffered message and its order; a foreign PID,
            // duplicate, malformed row or publication before clone delivery
            // fails replay. Raw retention/publication was never reordered.
            for row in pending {
                need(
                    row.position > clone_position,
                    "child row before authoritative clone delivery",
                )?;
                self.accept_bound(&row.message, row.position)?;
            }
        }
        Ok(())
    }
    fn accept_bound(&mut self, message: &str, position: u64) -> Check<()> {
        if let Some((_, row)) = message.split_once("application SCHEDULE ") {
            let v = fields(row, &["os", "generation", "pid", "cpu"])?;
            self.identity(&v)?;
            need(
                !self.scheduled && v[2] == self.parent_pid as i128 && v[3] == 0,
                "duplicate/foreign parent schedule",
            )?;
            self.scheduled = true;
        } else if let Some((_, row)) = message.split_once("application procfs ") {
            let (operation, row) = row.split_once(' ').ok_or("malformed procfs lifecycle")?;
            let v = fields(row, &["os", "generation", "pid", "tid"])?;
            self.identity(&v)?;
            need(v[2] == v[3], "unexpected nonleader procfs TID")?;
            let owner = self.owner(v[2])?;
            match operation {
                "published" => {
                    need(
                        !owner.published && !owner.deleted,
                        "duplicate/late publication",
                    )?;
                    owner.published = true;
                }
                "deleted" => {
                    need(
                        owner.published && owner.terminal && !owner.deleted,
                        "premature/duplicate DELETE",
                    )?;
                    owner.deleted = true;
                }
                _ => return Err("unknown procfs lifecycle operation".into()),
            }
        } else if let Some((_, row)) = message.split_once("application_process=") {
            let (operation, row) = row.split_once(' ').ok_or("malformed process lifecycle")?;
            match operation {
                "registered" => {
                    let v = fields(row, &["os", "generation", "pid"])?;
                    self.identity(&v)?;
                    need(
                        !self.registered && v[2] == self.parent_pid as i128,
                        "duplicate/foreign registration",
                    )?;
                    self.registered = true;
                }
                "cleanup_requested" => {
                    let v = fields(row, &["os", "generation", "pid", "intent_errno"])?;
                    self.identity(&v)?;
                    let owner = self.owner(v[2])?;
                    need(
                        owner.terminal && !owner.intent && v[3] == 0,
                        "missing terminal/duplicate/failed cleanup intent",
                    )?;
                    owner.intent = true;
                }
                // A release row denotes an error path, never positive completion.
                _ => {
                    return Err(format!(
                        "unexpected process lifecycle operation {operation}"
                    ))
                }
            }
        } else if let Some((_, row)) = message.split_once("application cleanup ACK ") {
            let v = fields(
                row,
                &["os", "generation", "pid", "token", "errno", "abandoned"],
            )?;
            self.identity(&v)?;
            let owner = self.owner(v[2])?;
            need(
                owner.terminal
                    && owner.ack.is_none()
                    && v[3] > 0
                    && v[3] <= u64::MAX as i128
                    && v[4] == 0
                    && (v[5] == 0 || v[5] == 1),
                "failed/duplicate/invalid real cleanup ACK",
            )?;
            owner.ack = Some(v[3] as u64);
        } else if let Some((_, row)) = message.split_once("application retirement ") {
            let v = fields(row, &["os", "generation", "pid", "token", "errno"])?;
            self.identity(&v)?;
            let owner = self.owner(v[2])?;
            need(
                owner.terminal
                    && owner.ack.is_some()
                    && !owner.retired
                    && owner.query_tokens.len() < 12
                    && v[3] > 0
                    && v[3] <= u64::MAX as i128,
                "premature/excess/finalized retirement query",
            )?;
            need(
                owner.query_tokens.insert(v[3] as u64),
                "duplicate real retirement query token",
            )?;
            need(v[4] == -11 || v[4] == 0, "unexpected real retirement errno")?;
            owner.retired = v[4] == 0;
        } else if let Some((_, row)) = message.split_once("application_syscall=") {
            let (kind, row) = row.split_once(' ').ok_or("malformed syscall lifecycle")?;
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
                _ => return Err(format!("unknown syscall row kind {kind}")),
            };
            let v = fields(row, &names)?;
            self.identity(&v)?;
            need(
                v[3] > 0 && v[3] <= u64::MAX as i128 && v[4] > 0 && v[4] <= u64::MAX as i128,
                "invalid syscall worker/delivery",
            )?;
            need(
                v[5] >= 0 && v[5] <= 3 && (kind != "return_route" || v[6] == 0),
                "invalid syscall CPU route",
            )?;
            let pid = i32::try_from(v[2]).map_err(|_| "syscall PID overflow")?;
            need(
                self.scheduled && self.owner(v[2])?.published,
                "syscall before actual schedule/publication",
            )?;
            let key = (pid, v[3] as u64, v[4] as u64);
            if kind == "delivered" {
                need(
                    self.calls.len() < 256 && !self.calls.contains_key(&key),
                    "duplicate/excess syscall delivery",
                )?;
                let number = i64::try_from(v[6]).map_err(|_| "syscall number overflow")?;
                need(number >= 0, "negative syscall number")?;
                let is_parent = pid == self.parent_pid;
                if number == 60 || number == 231 {
                    need(number == 231, "unexpected forwarded terminal60")?;
                    if is_parent {
                        need(
                            self.gate_released && self.child.complete() && self.reaped_child,
                            "parent terminal before actual causal gate release",
                        )?;
                    } else {
                        need(
                            self.child_write_returned,
                            "child terminal before zero-byte write RET0",
                        )?;
                    }
                    let owner = self.owner(v[2])?;
                    need(
                        owner.published && !owner.terminal,
                        "unpublished/duplicate terminal",
                    )?;
                    owner.terminal = true;
                }
                if !is_parent && number == 1 {
                    self.child_write_count += 1;
                    need(self.child_write_count == 1, "duplicate child write")?;
                }
                self.calls.insert(
                    key,
                    Call {
                        position,
                        number,
                        returned: false,
                        routed: false,
                    },
                );
            } else {
                let call = self
                    .calls
                    .get_mut(&key)
                    .ok_or("syscall response without matching delivery")?;
                if kind == "return_route" {
                    need(
                        !call.routed && !call.returned,
                        "duplicate/late return route",
                    )?;
                    call.routed = true;
                    return Ok(());
                }
                need(!call.returned, "duplicate syscall return")?;
                call.returned = true;
                let number = call.number;
                let delivery_position = call.position;
                if pid == self.parent_pid && number == 56 && v[6] > 0 {
                    need(
                        self.child_pid.is_none()
                            && v[6] != self.parent_pid as i128
                            && v[6] <= i32::MAX as i128,
                        "duplicate/invalid positive linked clone RET",
                    )?;
                    self.child_pid = Some(v[6] as i32);
                    self.child_clone_position = Some(delivery_position);
                }
                if Some(pid) == self.child_pid && number == 1 {
                    need(
                        v[6] == 0 && self.child.published && !self.child.terminal,
                        "child write must genuinely return0 before terminal",
                    )?;
                    self.child_write_returned = true;
                }
                if pid == self.parent_pid
                    && number == 61
                    && Some(v[6]) == self.child_pid.map(i128::from)
                    && self.child.terminal
                {
                    need(
                        !self.reaped_child && !self.parent.terminal,
                        "duplicate/late successful child reap",
                    )?;
                    self.reaped_child = true;
                }
            }
        }
        Ok(())
    }
}

/// Parse only the selected frozen kernel's genuine klogctl(3) line envelope.
/// Preserve every complete body byte; this view is solely for coverage checks.
/// The original raw snapshot remains the only saved/published evaluator input.
pub fn snapshot_bodies(snapshot: &[u8]) -> Check<BTreeMap<String, usize>> {
    let text =
        std::str::from_utf8(snapshot).map_err(|_| "final raw kernel snapshot is not UTF8")?;
    need(
        text.is_empty() || text.ends_with('\n'),
        "incomplete final kernel record",
    )?;
    let mut bodies = BTreeMap::new();
    for line in text.split_terminator('\n') {
        let after_open = line
            .strip_prefix('<')
            .ok_or("unexpected final klog envelope/continuation")?;
        let (priority, after_priority) = after_open
            .split_once('>')
            .ok_or("missing final klog priority delimiter")?;
        need(
            !priority.is_empty() && priority.bytes().all(|b| b.is_ascii_digit()),
            "invalid final klog priority",
        )?;
        let value = priority
            .parse::<u32>()
            .map_err(|_| "final klog priority overflow")?;
        need(value <= 191, "final klog priority range")?;
        let after_bracket = after_priority
            .strip_prefix('[')
            .ok_or("missing final klog timestamp")?;
        let (timestamp, body) = after_bracket
            .split_once("] ")
            .ok_or("invalid final klog timestamp delimiter")?;
        let timestamp = timestamp.trim_start_matches(' ');
        let (seconds, fraction) = timestamp
            .split_once('.')
            .ok_or("invalid final klog timestamp precision")?;
        need(
            !seconds.is_empty()
                && seconds.bytes().all(|b| b.is_ascii_digit())
                && fraction.len() == 6
                && fraction.bytes().all(|b| b.is_ascii_digit()),
            "invalid final klog timestamp grammar",
        )?;
        *bodies.entry(body.to_owned()).or_default() += 1;
    }
    Ok(bodies)
}

/// Non-destructive /dev/kmsg metadata. Original bytes are saved separately;
/// the final console/evaluator stream still comes from exactly one klogctl(3).
#[derive(Default)]
pub struct KmsgSequence {
    last: Option<(u64, u64)>,
    retained: usize,
}
impl KmsgSequence {
    pub fn accept<'a>(&mut self, raw: &'a [u8]) -> Check<&'a str> {
        self.retained = self
            .retained
            .checked_add(raw.len())
            .ok_or("incremental log size overflow")?;
        need(self.retained <= RAW_LIMIT, "incremental log overflow")?;
        let record = std::str::from_utf8(raw).map_err(|_| "non-UTF8 incremental kernel log")?;
        let (header, body) = record
            .split_once(';')
            .ok_or("missing kmsg header delimiter")?;
        let h: Vec<_> = header.split(',').collect();
        need(
            h.len() == 4 && h[0].parse::<u32>().is_ok() && h[3] == "-",
            "invalid/continued kmsg header",
        )?;
        let seq = h[1].parse::<u64>().map_err(|_| "invalid kmsg sequence")?;
        let timestamp = h[2].parse::<u64>().map_err(|_| "invalid kmsg timestamp")?;
        if let Some((last, previous_time)) = self.last {
            need(
                last.checked_add(1) == Some(seq) && timestamp >= previous_time,
                "kmsg gap/duplicate/reversed timestamp",
            )?;
        }
        self.last = Some((seq, timestamp));
        // kmsg dictionary continuation lines are retained verbatim. Only the
        // first actual message line is interpreted; never publish this view.
        Ok(body.split('\n').next().ok_or("missing kernel message")?)
    }
}
