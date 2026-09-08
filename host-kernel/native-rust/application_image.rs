// SPDX-License-Identifier: GPL-2.0
//! Checked x86_64 launcher image bytes. The authoritative layouts remain
//! executer/include/uprotocol.h and kernel/rust/abi.rs; no Rust object crosses
//! the IHK application callback boundary.

pub(crate) const HEADER: usize = 776;
pub(crate) const SECTION: usize = 56;
pub(crate) const MAX_SECTIONS: usize = 16;
pub(crate) const DESCRIPTOR_CAPACITY: usize = HEADER + SECTION * MAX_SECTIONS;
pub(crate) const MAX_FLAT_BYTES: usize = 4096 << 10;
pub(crate) const MAGIC: u64 = 0xcafe_cafe_4433_2211;
pub(crate) const USER_LIMIT: u64 = 0x8000_0000_0000;
pub(crate) const LAUNCHER_GAP: u64 = 0x0080_0000_0000;

pub(crate) const NUM_SECTIONS: usize = 8;
pub(crate) const CPU: usize = 12;
pub(crate) const PID: usize = 16;
pub(crate) const CREDENTIALS: usize = 28;
pub(crate) const ENTRY: usize = 72;
pub(crate) const USER_START: usize = 80;
pub(crate) const USER_END: usize = 88;
pub(crate) const THREAD: usize = 96;
pub(crate) const PAGE_TABLE: usize = 104;
pub(crate) const ARGS: usize = 152;
pub(crate) const ARGS_LEN: usize = 160;
pub(crate) const ENVS: usize = 168;
pub(crate) const ENVS_LEN: usize = 176;
pub(crate) const INTERP_ALIGN: usize = 504;
pub(crate) const CPU_SET: usize = 640;
pub(crate) const PROFILE: usize = 768;

pub(crate) fn word(bytes: &[u8], offset: usize) -> Result<u64, i32> {
    let end = offset.checked_add(8).ok_or(-75)?;
    Ok(u64::from_le_bytes(
        bytes.get(offset..end).ok_or(-22)?.try_into().unwrap(),
    ))
}

pub(crate) fn integer(bytes: &[u8], offset: usize) -> Result<i32, i32> {
    let end = offset.checked_add(4).ok_or(-75)?;
    Ok(i32::from_le_bytes(
        bytes.get(offset..end).ok_or(-22)?.try_into().unwrap(),
    ))
}

pub(crate) fn put_word(bytes: &mut [u8], offset: usize, value: u64) -> Result<(), i32> {
    let end = offset.checked_add(8).ok_or(-75)?;
    bytes
        .get_mut(offset..end)
        .ok_or(-22)?
        .copy_from_slice(&value.to_le_bytes());
    Ok(())
}

pub(crate) fn descriptor_bytes(header: &[u8]) -> Result<usize, i32> {
    if header.len() < HEADER || word(header, 0)? != MAGIC {
        return Err(-22);
    }
    let count = integer(header, NUM_SECTIONS)?;
    if !(1..=MAX_SECTIONS as i32).contains(&count) {
        return Err(-22);
    }
    Ok(HEADER + count as usize * SECTION)
}

/// Same zero-based mirror reservation and launcher gap as reserve_user_space,
/// with checked subtraction instead of wrapping over an existing executable.
pub(crate) fn reservation_end(first_vma: Option<u64>) -> Result<u64, i32> {
    let end = match first_vma {
        Some(start) => start.checked_sub(LAUNCHER_GAP).ok_or(-12)? & !(LAUNCHER_GAP - 1),
        None => USER_LIMIT,
    };
    if end == 0 || end > USER_LIMIT {
        return Err(-12);
    }
    Ok(end)
}

/// The guest reads a signed count, count offsets, a NULL slot, then strings.
/// Check this before the guest performs unchecked count/offset arithmetic.
pub(crate) fn flattened(bytes: &[u8]) -> Result<(), i32> {
    if bytes.len() < 16 || bytes.len() > MAX_FLAT_BYTES {
        return Err(-7);
    }
    let count = word(bytes, 0)?;
    if count > i32::MAX as u64 {
        return Err(-22);
    }
    let strings = (count as usize)
        .checked_add(2)
        .and_then(|n| n.checked_mul(8))
        .ok_or(-75)?;
    if strings > bytes.len() || word(bytes, strings - 8)? != 0 {
        return Err(-22);
    }
    // One scan bounds total work even when every offset names the same string.
    let last_nul = bytes.iter().rposition(|byte| *byte == 0).ok_or(-22)?;
    for index in 0..count as usize {
        let offset = word(bytes, 8 + index * 8)? as usize;
        if offset < strings || offset > last_nul {
            return Err(-22);
        }
    }
    Ok(())
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct Input {
    pub(crate) descriptor: usize,
    pub(crate) args: usize,
    pub(crate) envs: usize,
    pub(crate) cpu: i32,
    pub(crate) pid: i32,
}

impl Input {
    /// Kernel-only invocation storage consists of descriptor, args, then envs.
    /// Its pointers and PID have already been normalized by the caller owner.
    pub(crate) fn parse(bytes: &[u8], cpus: usize) -> Result<Self, i32> {
        let descriptor = descriptor_bytes(bytes)?;
        let args = word(bytes, ARGS_LEN)? as usize;
        let envs = word(bytes, ENVS_LEN)? as usize;
        let total = descriptor
            .checked_add(args)
            .and_then(|n| n.checked_add(envs))
            .ok_or(-75)?;
        if total != bytes.len() || cpus == 0 || cpus > 1024 {
            return Err(-22);
        }
        let cpu = integer(bytes, CPU)?;
        let pid = integer(bytes, PID)?;
        if cpu < 0 || cpu as usize >= cpus || pid <= 0 {
            return Err(-22);
        }
        let start = word(bytes, USER_START)?;
        let end = word(bytes, USER_END)?;
        if start >= end || end > USER_LIMIT || start % 4096 != 0 || end % 4096 != 0 {
            return Err(-22);
        }
        for bit in cpus..1024 {
            if bytes[CPU_SET + bit / 8] & (1 << (bit % 8)) != 0 {
                return Err(-22);
            }
        }
        for section in bytes[HEADER..descriptor].chunks_exact(SECTION) {
            let address = word(section, 0)?;
            let length = word(section, 8)?;
            let filesz = word(section, 24)?;
            let offset = word(section, 32)?;
            let prot = integer(section, 40)?;
            let last = address
                .checked_add(length)
                .and_then(|n| n.checked_add(4095))
                .ok_or(-75)?
                & !4095;
            if length == 0
                || filesz > length
                || last > end
                || prot & !7 != 0
                || section[44] > 1
                || offset.checked_add(filesz).is_none()
            {
                return Err(-22);
            }
            if section[44] != 0 && !word(bytes, INTERP_ALIGN)?.is_power_of_two() {
                return Err(-22);
            }
        }
        flattened(&bytes[descriptor..descriptor + args])?;
        flattened(&bytes[descriptor + args..])?;
        Ok(Self {
            descriptor,
            args,
            envs,
            cpu,
            pid,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Page {
    pub(crate) physical: u64,
    pub(crate) writable: bool,
    pub(crate) executable: bool,
}

/// Adapt the existing x86_64 translate_rva_to_rpa walk. The callback must
/// validate each retained guest page-table word before reading it. Handle 1-GiB,
/// 2-MiB and 4-KiB leaves, including the distinct leaf PAT/large-page bit.
pub(crate) fn translate(
    table: u64,
    address: u64,
    mut read: impl FnMut(u64) -> Result<u64, i32>,
) -> Result<Page, i32> {
    const PHYSICAL: u64 = 0x000f_ffff_ffff_f000;
    if table == 0 || table % 4096 != 0 || address >= USER_LIMIT {
        return Err(-22);
    }
    let mut table = table;
    let mut writable = true;
    let mut executable = true;
    for shift in [39, 30, 21, 12] {
        let pte = read(
            table
                .checked_add(((address >> shift) & 511) * 8)
                .ok_or(-75)?,
        )?;
        if pte & 1 == 0 || pte & 4 == 0 {
            return Err(-14);
        }
        writable &= pte & 2 != 0;
        executable &= pte & (1 << 63) == 0;
        let large = pte & 128 != 0;
        if shift == 39 && large {
            return Err(-71);
        }
        if shift == 12 || large {
            let mask = (1u64 << shift) - 1;
            // Large-leaf bit 12 is PAT; other address bits below the leaf's
            // physical alignment must be zero rather than silently rounded.
            if large && shift != 12 && pte & PHYSICAL & mask & !4096 != 0 {
                return Err(-71);
            }
            return Ok(Page {
                physical: (pte & PHYSICAL & !mask) | (address & mask),
                writable,
                executable,
            });
        }
        table = pte & PHYSICAL;
        if table == 0 {
            return Err(-14);
        }
    }
    Err(-14)
}
