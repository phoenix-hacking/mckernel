// SPDX-License-Identifier: GPL-2.0
//! Traditional SCD cleanup exchange, adapted from the existing Rust RPC owner.
//!
//! A registration reserves its descriptor before publication. Caller departure
//! cannot retire queued/published work; only its matching acknowledgement can.

use core::sync::atomic::{AtomicU64, Ordering};

pub(crate) const PACKET_BYTES: usize = 128;
pub(crate) const CLEANUP: i32 = 9;
pub(crate) const CLEANUP_REPLY: i32 = 10;
static NEXT_TOKEN: AtomicU64 = AtomicU64::new(1);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Token(u64);

impl Token {
    pub(crate) fn wire(self) -> u64 { self.0 }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Phase { Reserved, Queued, Published, Complete(i32) }

pub(crate) struct Exchange {
    token: Token,
    os: i32,
    cpu: i32,
    pid: i32,
    phase: Phase,
    waiter: bool,
}

impl Exchange {
    pub(crate) fn new(os: i32, cpu: i32, pid: i32) -> Result<Self, i32> {
        if os < 0 || cpu < 0 || pid <= 0 { return Err(-22); }
        let token = NEXT_TOKEN.fetch_update(Ordering::Relaxed, Ordering::Relaxed,
            |value| (value < i64::MAX as u64).then(|| value + 1))
            .map(Token).map_err(|_| -75)?;
        Ok(Self { token, os, cpu, pid, phase: Phase::Reserved, waiter: true })
    }

    pub(crate) fn token(&self) -> Token { self.token }
    pub(crate) fn pid(&self) -> i32 { self.pid }
    pub(crate) fn reserved(&self) -> bool { self.phase == Phase::Reserved }
    pub(crate) fn queued(&self) -> bool { self.phase == Phase::Queued }
    pub(crate) fn abandoned(&self) -> bool { !self.waiter }

    pub(crate) fn begin(&mut self) -> Result<(), i32> {
        if !self.reserved() { return Err(-16); }
        self.phase = Phase::Queued;
        Ok(())
    }

    pub(crate) fn outgoing(&self) -> Option<[u8; PACKET_BYTES]> {
        if !self.queued() { return None; }
        let mut packet = [0; PACKET_BYTES];
        packet[8..12].copy_from_slice(&CLEANUP.to_le_bytes());
        // Traditional reply is at 16; offset 24 belongs to its CPU reference.
        packet[16..24].copy_from_slice(&self.token.wire().to_le_bytes());
        packet[24..28].copy_from_slice(&self.cpu.to_le_bytes());
        packet[28..32].copy_from_slice(&self.os.to_le_bytes());
        packet[32..36].copy_from_slice(&self.pid.to_le_bytes());
        // This initial registration has no prepared thread or borrowed memory.
        Some(packet)
    }

    pub(crate) fn published(&mut self) -> Result<(), i32> {
        if !self.queued() { return Err(-16); }
        self.phase = Phase::Published;
        Ok(())
    }

    pub(crate) fn accept(&mut self, packet: &[u8]) -> Result<(), i32> {
        if packet.len() != PACKET_BYTES { return Err(-22); }
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        let token = u64::from_le_bytes(packet[16..24].try_into().unwrap());
        let cpu = i32::from_le_bytes(packet[24..28].try_into().unwrap());
        let argument = u64::from_le_bytes(packet[40..48].try_into().unwrap());
        if token != self.token.wire() || message != CLEANUP_REPLY || cpu != self.cpu
            || argument != 0 { return Err(-2); }
        if self.phase != Phase::Published { return Err(-16); }
        let error = i32::from_le_bytes(packet[12..16].try_into().unwrap());
        self.phase = Phase::Complete(if (-4095..=0).contains(&error) { error } else { -71 });
        Ok(())
    }

    pub(crate) fn result(&self) -> Option<i32> {
        if let Phase::Complete(error) = self.phase { Some(error) } else { None }
    }

    pub(crate) fn abandon(&mut self) { self.waiter = false; }
    pub(crate) fn retired(&self) -> bool { self.abandoned() && self.result().is_some() }
}
