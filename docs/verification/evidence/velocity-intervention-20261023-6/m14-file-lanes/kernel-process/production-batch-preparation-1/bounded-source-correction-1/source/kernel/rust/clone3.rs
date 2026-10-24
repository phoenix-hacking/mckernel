// SPDX-License-Identifier: GPL-2.0-only
//! Checked Linux clone3 arguments for the existing McKernel clone lifecycle.

pub(crate) const NUMBER: u64 = 435;
const BYTES: usize = 88;
const VERSION_0: usize = 64;
const MAX_BYTES: usize = 4096;
const MAX_PID_NS_LEVEL: u64 = 32;
const CLONE_NEWTIME: u64 = 0x80;
const CLONE_SIGHAND: u64 = 0x800;
const CLONE_PARENT: u64 = 0x8000;
const CLONE_THREAD: u64 = 0x10000;
const CLONE_DETACHED: u64 = 0x400000;
const CLONE_CLEAR_SIGHAND: u64 = 0x100000000;
const CLONE_INTO_CGROUP: u64 = 0x200000000;
// These features need owners that the existing guest clone path does not have.
const UNSUPPORTED_FLAGS: u64 = 0x80 // NEWTIME
    | 0x1000 // PIDFD
    | 0x20000 // NEWNS
    | 0x02000000 // NEWCGROUP
    | 0x04000000 // NEWUTS
    | 0x08000000 // NEWIPC
    | 0x10000000 // NEWUSER
    | 0x20000000 // NEWPID
    | 0x40000000 // NEWNET
    | 0x80000000 // IO
    | CLONE_CLEAR_SIGHAND
    | CLONE_INTO_CGROUP;

#[derive(Debug, PartialEq, Eq)]
pub(crate) struct Legacy {
    pub(crate) flags: u64,
    pub(crate) stack: u64,
    pub(crate) parent_tid: u64,
    pub(crate) child_tid: u64,
    pub(crate) tls: u64,
}

/// The copier must check guest access and return the actual copy error. No
/// guest reference or lock is retained across its calls. Nothing in this
/// operation creates a thread or writes to user memory.
pub(crate) fn read(
    address: u64,
    size: usize,
    user_start: u64,
    user_end: u64,
    mut copy: impl FnMut(u64, &mut [u8]) -> Result<(), i64>,
) -> Result<Legacy, i64> {
    if size > MAX_BYTES {
        return Err(-7); // E2BIG
    }
    if size < VERSION_0 {
        return Err(-22);
    }
    let end = address.checked_add(size as u64).ok_or(-14)?;
    if address < user_start || address >= user_end || end > user_end {
        return Err(-14);
    }

    // Match copy_struct_from_user: validate unknown trailing bytes before
    // reading the interoperable prefix. Bound temporary stack storage.
    let mut offset = BYTES;
    let mut tail = [0; 64];
    while offset < size {
        let count = tail.len().min(size - offset);
        copy(address + offset as u64, &mut tail[..count])?;
        if tail[..count].iter().any(|byte| *byte != 0) {
            return Err(-7);
        }
        offset += count;
    }
    let mut bytes = [0; BYTES];
    copy(address, &mut bytes[..size.min(BYTES)])?;
    let word = |index: usize| {
        let mut value = [0; 8];
        value.copy_from_slice(&bytes[index * 8..index * 8 + 8]);
        u64::from_le_bytes(value)
    };
    let flags = word(0);
    let child_tid = word(2);
    let parent_tid = word(3);
    let exit_signal = word(4);
    let stack = word(5);
    let stack_size = word(6);
    let tls = word(7);
    let set_tid = word(8);
    let set_tid_size = word(9);
    let cgroup = word(10);
    if set_tid_size > MAX_PID_NS_LEVEL
        || (set_tid == 0) != (set_tid_size == 0)
        || exit_signal > 64
        || (flags & CLONE_INTO_CGROUP != 0 && (cgroup > i32::MAX as u64 || size < BYTES))
        || flags & !(u32::MAX as u64 | CLONE_CLEAR_SIGHAND | CLONE_INTO_CGROUP) != 0
        || flags & (CLONE_DETACHED | (0xff & !CLONE_NEWTIME)) != 0
        || flags & (CLONE_SIGHAND | CLONE_CLEAR_SIGHAND) == CLONE_SIGHAND | CLONE_CLEAR_SIGHAND
        || (flags & (CLONE_THREAD | CLONE_PARENT) != 0 && exit_signal != 0)
    {
        return Err(-22);
    }
    let stack_top = if stack == 0 {
        if stack_size != 0 {
            return Err(-22);
        }
        0
    } else {
        let end = stack.checked_add(stack_size).ok_or(-22)?;
        if stack_size == 0 || stack < user_start || stack >= user_end || end > user_end {
            return Err(-22);
        }
        end
    };
    if flags & UNSUPPORTED_FLAGS != 0 || set_tid_size != 0 {
        return Err(-95); // EOPNOTSUPP; never discard requested semantics.
    }
    Ok(Legacy {
        flags: flags | exit_signal,
        stack: stack_top,
        parent_tid,
        child_tid,
        tls,
    })
}
