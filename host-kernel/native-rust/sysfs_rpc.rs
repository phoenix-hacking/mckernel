// SPDX-License-Identifier: GPL-2.0-only
//! Single-buffer remote sysfs exchange adapted from mcctrl's Rust RPC bodies.
//!
//! The Linux adapter serializes access to this state and the owned data page.
//! A waiter leaving does not cancel publication: only a matching response or
//! a proven pre-publication send failure permits the data page to be reused.

use super::sysfs_request::Client;
use core::sync::atomic::{AtomicU64, Ordering};

pub(crate) const PACKET_BYTES: usize = 128;
pub(crate) const DATA_BYTES: usize = 4096;
static NEXT_TOKEN: AtomicU64 = AtomicU64::new(1);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Token(u64);

impl Token {
    pub(crate) fn wire(self) -> u64 {
        self.0
    }

    fn allocate() -> Result<Self, i32> {
        NEXT_TOKEN
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |value| {
                (value < i64::MAX as u64).then(|| value + 1)
            })
            .map(Self)
            .map_err(|_| -75)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Call {
    Show { capacity: usize },
    Store { bytes: usize },
    Release,
}

impl Call {
    fn message(self) -> i32 {
        match self {
            Self::Show { .. } => 0x3a,
            Self::Store { .. } => 0x3c,
            Self::Release => 0x3e,
        }
    }

    fn limit(self) -> usize {
        match self {
            Self::Show { capacity } => capacity,
            Self::Store { bytes } => bytes,
            Self::Release => 0,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Phase {
    Queued,
    Published,
    Complete(Result<usize, i32>),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Pending {
    token: Token,
    client: Client,
    call: Call,
    phase: Phase,
}

pub(crate) struct Exchange {
    pending: Option<Pending>,
}

impl Exchange {
    pub(crate) const fn new() -> Self {
        Self { pending: None }
    }

    pub(crate) fn token(&self) -> Option<Token> {
        self.pending.map(|pending| pending.token)
    }

    /// The caller must fill store bytes before releasing its shared-state lock.
    /// Special ops are mapped snooping requests, never remote function tokens.
    pub(crate) fn begin(&mut self, client: Client, call: Call) -> Result<Token, i32> {
        if self.pending.is_some() {
            return Err(-16);
        }
        if (1..=1000).contains(&client.operations) || call.limit() > DATA_BYTES {
            return Err(-22);
        }
        let token = Token::allocate()?;
        self.pending = Some(Pending {
            token,
            client,
            call,
            phase: Phase::Queued,
        });
        Ok(token)
    }

    /// Peeking does not transfer ownership. A full transport queue may retry
    /// these exact bytes until publication, with no duplicated guest request.
    pub(crate) fn outgoing(&self) -> Option<(Token, [u8; PACKET_BYTES])> {
        let pending = self.pending?;
        if pending.phase != Phase::Queued {
            return None;
        }
        let mut packet = [0; PACKET_BYTES];
        packet[8..12].copy_from_slice(&pending.call.message().to_le_bytes());
        if let Call::Store { bytes } = pending.call {
            packet[12..16].copy_from_slice(&(bytes as i32).to_le_bytes());
        }
        packet[24..32].copy_from_slice(&pending.token.wire().to_le_bytes());
        packet[32..40].copy_from_slice(&pending.client.operations.to_le_bytes());
        packet[40..48].copy_from_slice(&pending.client.instance.to_le_bytes());
        Some((pending.token, packet))
    }

    /// The adapter holds its state lock across queue publication and this
    /// transition, before notification or response dispatch can acquire it.
    pub(crate) fn published(&mut self, token: Token) -> Result<(), i32> {
        let pending = self.pending.as_mut().ok_or(-2)?;
        if pending.token != token || pending.phase != Phase::Queued {
            return Err(-16);
        }
        pending.phase = Phase::Published;
        Ok(())
    }

    /// Only a transport failure proven to precede publication can use this.
    /// IPI failure after queue publication leaves the exchange outstanding.
    pub(crate) fn fail_unpublished(&mut self, token: Token, error: i32) -> Result<(), i32> {
        if !(-4095..0).contains(&error) {
            return Err(-22);
        }
        let pending = self.pending.as_mut().ok_or(-2)?;
        if pending.token != token || pending.phase != Phase::Queued {
            return Err(-16);
        }
        pending.phase = Phase::Complete(Err(error));
        Ok(())
    }

    /// Queue acquisition must already synchronize the peer's preceding data
    /// writes. Stale, foreign or wrong-kind replies never complete this call.
    pub(crate) fn accept(&mut self, packet: &[u8]) -> Result<(), i32> {
        if packet.len() != PACKET_BYTES {
            return Err(-22);
        }
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        let error = i32::from_le_bytes(packet[12..16].try_into().unwrap());
        let token = u64::from_le_bytes(packet[24..32].try_into().unwrap());
        let result = i64::from_le_bytes(packet[32..40].try_into().unwrap());
        let pending = self.pending.as_mut().ok_or(-2)?;
        if pending.token.wire() != token || message != pending.call.message() + 1 {
            return Err(-2);
        }
        if pending.phase != Phase::Published {
            return Err(-16);
        }
        // The matching response retires the peer callback even when its count
        // is invalid. Record an error without exposing any out-of-bounds data.
        let status = if error != if result < 0 { result as i32 } else { 0 } || result < -4095 {
            Err(-71)
        } else if result < 0 {
            Err(result as i32)
        } else if result as u64 > pending.call.limit() as u64 {
            Err(-75)
        } else {
            Ok(result as usize)
        };
        pending.phase = Phase::Complete(status);
        Ok(())
    }

    pub(crate) fn completed(&self, token: Token) -> Result<bool, i32> {
        let pending = self.pending.ok_or(-2)?;
        if pending.token != token {
            return Err(-2);
        }
        Ok(matches!(pending.phase, Phase::Complete(_)))
    }

    /// The same serial caller keeps the data page excluded until it has copied
    /// a successful show result. No timeout/interruption may invoke this early.
    pub(crate) fn finish(&mut self, token: Token) -> Result<Result<usize, i32>, i32> {
        let pending = self.pending.ok_or(-2)?;
        if pending.token != token {
            return Err(-2);
        }
        let Phase::Complete(result) = pending.phase else {
            return Err(-16);
        };
        self.pending = None;
        Ok(result)
    }
}
