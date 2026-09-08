// SPDX-License-Identifier: GPL-2.0
//! Traditional SCD application exchange, adapted from the existing Rust RPC owner.
//!
//! A registration reserves its descriptor before publication. Caller departure
//! cannot retire queued/published work. Unscheduled prepared cleanup retains
//! its owner through both acknowledgement and the matching deletion event.

use core::sync::atomic::{AtomicU64, Ordering};

pub(crate) const PACKET_BYTES: usize = 128;
pub(crate) const PREPARE: i32 = 1;
pub(crate) const PREPARE_REPLY: i32 = 2;
pub(crate) const CLEANUP: i32 = 9;
pub(crate) const CLEANUP_REPLY: i32 = 10;
pub(crate) const TID_DELETE: i32 = 0x45;
const PROCFS_ANSWER: i32 = 0x13;
static NEXT_TOKEN: AtomicU64 = AtomicU64::new(1);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Token(u64);

impl Token {
    pub(crate) fn allocate() -> Result<Self, i32> {
        NEXT_TOKEN
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |value| {
                (value < i64::MAX as u64).then(|| value + 1)
            })
            .map(Self)
            .map_err(|_| -75)
    }

    pub(crate) fn wire(self) -> u64 {
        self.0
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Phase {
    Reserved,
    Queued,
    Published,
    Complete(i32),
}

pub(crate) struct Exchange {
    token: Token,
    os: i32,
    cpu: i32,
    pid: i32,
    message: i32,
    reply: i32,
    argument: u64,
    phase: Phase,
    waiter: bool,
    unscheduled_deleted: bool,
}

impl Exchange {
    pub(crate) fn new(os: i32, cpu: i32, pid: i32) -> Result<Self, i32> {
        if pid <= 0 {
            return Err(-22);
        }
        Self::reserve(os, cpu, pid)
    }

    fn reserve(os: i32, cpu: i32, pid: i32) -> Result<Self, i32> {
        if os < 0 || cpu < 0 || pid < 0 {
            return Err(-22);
        }
        let token = Token::allocate()?;
        Ok(Self {
            token,
            os,
            cpu,
            pid,
            message: CLEANUP,
            reply: CLEANUP_REPLY,
            argument: 0,
            phase: Phase::Reserved,
            waiter: true,
            unscheduled_deleted: false,
        })
    }

    /// The caller must retain the descriptor and its pointed-to physical
    /// allocations from publication until the matching prepare acknowledgement.
    pub(crate) fn prepare(os: i32, cpu: i32, pid: i32, descriptor: u64) -> Result<Self, i32> {
        if descriptor == 0 || descriptor % 4096 != 0 {
            return Err(-22);
        }
        let mut exchange = Self::new(os, cpu, pid)?;
        exchange.message = PREPARE;
        exchange.reply = PREPARE_REPLY;
        exchange.argument = descriptor;
        Ok(exchange)
    }

    /// The owner retains the 808-byte request, host data pages, and exact OS
    /// generation until a matching native reply proves guest mapping retirement.
    /// Caller departure or an unmarked legacy answer cannot release these pages.
    #[allow(dead_code)] // Tested prerequisite; the native procfs service is not connected yet.
    pub(crate) fn procfs(
        os: i32,
        cpu: i32,
        pid: i32,
        descriptor: u64,
        release: bool,
    ) -> Result<Self, i32> {
        const PROCFS_REQUEST: i32 = 0x12;
        const PROCFS_RELEASE: i32 = 0x15;
        if descriptor == 0 || descriptor % 4096 != 0 {
            return Err(-22);
        }
        let mut exchange = Self::reserve(os, cpu, pid)?;
        exchange.message = if release {
            PROCFS_RELEASE
        } else {
            PROCFS_REQUEST
        };
        exchange.reply = PROCFS_ANSWER;
        exchange.argument = descriptor;
        Ok(exchange)
    }

    /// Refine the reserved cleanup target only after a checked prepare reply.
    /// It must use the same guest CPU queue as preparation and scheduling.
    pub(crate) fn cleanup_target(&mut self, cpu: i32, thread: u64) -> Result<(), i32> {
        if !self.reserved() || self.message != CLEANUP {
            return Err(-16);
        }
        if cpu < 0 || thread != 0 && thread < 0xffff_8000_0000_0000 {
            return Err(-22);
        }
        self.cpu = cpu;
        self.argument = thread;
        Ok(())
    }

    pub(crate) fn cpu(&self) -> i32 {
        self.cpu
    }

    pub(crate) fn token(&self) -> Token {
        self.token
    }
    pub(crate) fn pid(&self) -> i32 {
        self.pid
    }
    pub(crate) fn reserved(&self) -> bool {
        self.phase == Phase::Reserved
    }
    pub(crate) fn queued(&self) -> bool {
        self.phase == Phase::Queued
    }
    pub(crate) fn abandoned(&self) -> bool {
        !self.waiter
    }

    pub(crate) fn begin(&mut self) -> Result<(), i32> {
        if !self.reserved() {
            return Err(-16);
        }
        self.phase = Phase::Queued;
        Ok(())
    }

    pub(crate) fn outgoing(&self) -> Option<[u8; PACKET_BYTES]> {
        if !self.queued() {
            return None;
        }
        let mut packet = [0; PACKET_BYTES];
        packet[8..12].copy_from_slice(&self.message.to_le_bytes());
        // Traditional reply is at 16; offset 24 belongs to its CPU reference.
        packet[16..24].copy_from_slice(&self.token.wire().to_le_bytes());
        packet[24..28].copy_from_slice(&self.cpu.to_le_bytes());
        packet[28..32].copy_from_slice(&self.os.to_le_bytes());
        packet[32..36].copy_from_slice(&self.pid.to_le_bytes());
        packet[40..48].copy_from_slice(&self.argument.to_le_bytes());
        Some(packet)
    }

    pub(crate) fn published(&mut self) -> Result<(), i32> {
        if !self.queued() {
            return Err(-16);
        }
        self.phase = Phase::Published;
        Ok(())
    }

    pub(crate) fn accept(&mut self, packet: &[u8]) -> Result<(), i32> {
        if packet.len() != PACKET_BYTES {
            return Err(-22);
        }
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        let token = u64::from_le_bytes(packet[16..24].try_into().unwrap());
        let cpu = i32::from_le_bytes(packet[24..28].try_into().unwrap());
        let argument = u64::from_le_bytes(packet[40..48].try_into().unwrap());
        if token != self.token.wire()
            || message != self.reply
            || cpu != self.cpu
            || argument != self.argument
        {
            return Err(-2);
        }
        if self.reply == PROCFS_ANSWER
            && (i32::from_le_bytes(packet[32..36].try_into().unwrap()) != self.pid
                || &packet[120..128] != b"MCPR0001")
        {
            return Err(-2);
        }
        if self.phase != Phase::Published {
            return Err(-16);
        }
        let error = i32::from_le_bytes(packet[12..16].try_into().unwrap());
        self.phase = Phase::Complete(if (-4095..=0).contains(&error) {
            error
        } else {
            -71
        });
        Ok(())
    }

    pub(crate) fn result(&self) -> Option<i32> {
        if let Phase::Complete(error) = self.phase {
            Some(error)
        } else {
            None
        }
    }

    /// A prepared, unscheduled thread emits an advisory procfs deletion with
    /// TID zero after its cleanup reply. Its resp_pa is an expired peer-stack
    /// address, not a reply target. Never map or write it for this operation.
    pub(crate) fn accept_unscheduled_delete(&mut self, packet: &[u8]) -> Result<(), i32> {
        if packet.len() != PACKET_BYTES {
            return Err(-22);
        }
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        let cpu = i32::from_le_bytes(packet[24..28].try_into().unwrap());
        let os = i32::from_le_bytes(packet[28..32].try_into().unwrap());
        let pid = i32::from_le_bytes(packet[32..36].try_into().unwrap());
        let tid = u64::from_le_bytes(packet[40..48].try_into().unwrap());
        if self.message != CLEANUP
            || self.argument == 0
            || message != TID_DELETE
            || cpu != self.cpu
            || os != self.os
            || pid != self.pid
            || tid != 0
        {
            return Err(-2);
        }
        if self.result().is_none() || self.unscheduled_deleted {
            return Err(-16);
        }
        self.unscheduled_deleted = true;
        Ok(())
    }

    /// These wire events allow local exchange release; final guest destruction
    /// still requires the same-CPU handler barrier. Scheduled TIDs need their
    /// full procfs/process lifecycle owner before START is supported.
    pub(crate) fn release_ready(&self) -> bool {
        self.result().is_some()
            && (self.message != CLEANUP || self.argument == 0 || self.unscheduled_deleted)
    }

    pub(crate) fn abandon(&mut self) {
        self.waiter = false;
    }
    pub(crate) fn retired(&self) -> bool {
        self.abandoned() && self.release_ready()
    }
}
