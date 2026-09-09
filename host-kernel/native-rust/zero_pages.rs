// SPDX-License-Identifier: GPL-2.0-only
//! Native one-way allocator zeroing contract and checked address geometry.
//!
//! Geometry grants no memory access. The service must retain the original OS,
//! validate every complete span against its assigned extents and claim each
//! detached batch in the continuing-service ledger before clearing any data.

pub(crate) const BATCH_MARKER: u64 = u64::from_le_bytes(*b"MCZB0001");
pub(crate) const NUMBER: u64 = 279;
pub(crate) const NODE_BYTES: usize = 256;
pub(crate) const NODE_ALIGN: u64 = 64;
pub(crate) const CONTROL_OFFSET: u64 = 40;
pub(crate) const CONTROL_BYTES: usize = 24;
pub(crate) const HEADER_BYTES: usize = 48;
pub(crate) const LINK_OFFSET: u64 = 40;
pub(crate) const PAGE_BYTES: u64 = 4096;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Request {
    pub(crate) cpu: i32,
    pub(crate) pid: i32,
    pub(crate) node: u64,
}

impl Request {
    /// Distinguish this producer from a response-bearing move_pages syscall.
    /// A candidate still needs full decoding, including the batch marker.
    pub(crate) fn candidate(packet: &[u8]) -> bool {
        packet.len() == 128
            && packet[8..12] == 4i32.to_le_bytes()
            && packet[64..72] == NUMBER.to_le_bytes()
            && packet[48..52] == 0i32.to_le_bytes()
            && packet[120..128] == 0u64.to_le_bytes()
    }

    pub(crate) fn decode(packet: &[u8], cpus: usize) -> Result<Self, i32> {
        if !Self::candidate(packet) {
            return Err(-22);
        }
        let integer = |offset| i32::from_le_bytes(packet[offset..offset + 4].try_into().unwrap());
        let word = |offset| u64::from_le_bytes(packet[offset..offset + 8].try_into().unwrap());
        let cpu = integer(24);
        let pid = integer(32);
        let node = word(72);
        if cpu < 0
            || cpu as usize >= cpus
            || integer(28) != 0
            || pid <= 0
            || integer(52) != 0
            || word(56) != 1
            || node == 0
            || node % NODE_ALIGN != 0
            || node.checked_add(NODE_BYTES as u64).is_none()
            || word(80) != BATCH_MARKER
            || packet[88..120].iter().any(|byte| *byte != 0)
        {
            return Err(-22);
        }
        Ok(Self { cpu, pid, node })
    }

    pub(crate) fn node_physical(
        self,
        kernel_virtual: u64,
        kernel_physical: u64,
        window_bytes: u64,
    ) -> Result<u64, i32> {
        let offset = self.node.checked_sub(kernel_virtual).ok_or(-22)?;
        if offset.checked_add(NODE_BYTES as u64).ok_or(-22)? > window_bytes {
            return Err(-22);
        }
        let physical = kernel_physical.checked_add(offset).ok_or(-22)?;
        physical.checked_add(NODE_BYTES as u64).ok_or(-22)?;
        if physical == 0 || physical % NODE_ALIGN != 0 {
            return Err(-22);
        }
        Ok(physical)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Chunk {
    pub(crate) physical: u64,
    pub(crate) bytes: usize,
    pub(crate) pages: i32,
}

impl Chunk {
    /// Validate a list link before reading its bounded header. Only the Linux
    /// direct-map representation is valid for post-initialization free chunks.
    pub(crate) fn header_physical(link: u64, direct_map: u64) -> Result<u64, i32> {
        let physical = link
            .checked_sub(direct_map)
            .and_then(|value| value.checked_sub(LINK_OFFSET))
            .ok_or(-22)?;
        if physical == 0 || physical % PAGE_BYTES != 0 {
            return Err(-22);
        }
        physical.checked_add(HEADER_BYTES as u64).ok_or(-22)?;
        Ok(physical)
    }

    pub(crate) fn decode(
        link: u64,
        direct_map: u64,
        header_address: u64,
        size: u64,
    ) -> Result<Self, i32> {
        let physical = Self::header_physical(link, direct_map)?;
        if header_address != physical
            || size == 0
            || size % PAGE_BYTES != 0
            || size / PAGE_BYTES > i32::MAX as u64
        {
            return Err(-22);
        }
        let end = physical.checked_add(size).ok_or(-22)?;
        direct_map.checked_add(end).ok_or(-22)?;
        Ok(Self {
            physical,
            bytes: usize::try_from(size).map_err(|_| -22)?,
            pages: (size / PAGE_BYTES) as i32,
        })
    }
}
