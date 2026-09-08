// SPDX-License-Identifier: GPL-2.0-only
//! The unchanged mcctrl sysfs metadata protocol, with owned request snapshots.
use core::{
    mem::{align_of, offset_of, size_of},
    ptr,
    sync::atomic::{AtomicI32, Ordering},
};

pub(crate) const PATH_BYTES: usize = 1024;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Kind {
    Create,
    Mkdir,
    Symlink,
    Lookup,
    Unlink,
}

#[repr(C)]
pub(crate) struct Create {
    pub(crate) mode: i32,
    pub(crate) error: i32,
    pub(crate) client_ops: u64,
    pub(crate) client_instance: u64,
    pub(crate) path: [u8; PATH_BYTES],
    padding: i32,
    pub(crate) busy: i32,
}

/// mkdir and lookup return handle; symlink consumes it as target.
#[repr(C)]
pub(crate) struct WithHandle {
    pub(crate) error: i32,
    padding: i32,
    pub(crate) handle: u64,
    pub(crate) path: [u8; PATH_BYTES],
    padding2: i32,
    pub(crate) busy: i32,
}

#[repr(C)]
pub(crate) struct Unlink {
    pub(crate) flags: i32,
    pub(crate) error: i32,
    pub(crate) path: [u8; PATH_BYTES],
    padding: i32,
    pub(crate) busy: i32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Layout {
    pub(crate) bytes: usize,
    pub(crate) alignment: usize,
    pub(crate) error: usize,
    pub(crate) path: usize,
    pub(crate) busy: usize,
}

impl Kind {
    pub(crate) const fn from_message(message: i32) -> Option<Self> {
        match message {
            0x30 => Some(Self::Create),
            0x32 => Some(Self::Mkdir),
            0x34 => Some(Self::Symlink),
            0x36 => Some(Self::Lookup),
            0x38 => Some(Self::Unlink),
            _ => None,
        }
    }

    pub(crate) const fn layout(self) -> Layout {
        match self {
            Self::Create => Layout {
                bytes: size_of::<Create>(),
                alignment: align_of::<Create>(),
                error: offset_of!(Create, error),
                path: offset_of!(Create, path),
                busy: offset_of!(Create, busy),
            },
            Self::Mkdir | Self::Symlink | Self::Lookup => Layout {
                bytes: size_of::<WithHandle>(),
                alignment: align_of::<WithHandle>(),
                error: offset_of!(WithHandle, error),
                path: offset_of!(WithHandle, path),
                busy: offset_of!(WithHandle, busy),
            },
            Self::Unlink => Layout {
                bytes: size_of::<Unlink>(),
                alignment: align_of::<Unlink>(),
                error: offset_of!(Unlink, error),
                path: offset_of!(Unlink, path),
                busy: offset_of!(Unlink, busy),
            },
        }
    }

    fn returns_handle(self) -> bool {
        matches!(self, Self::Mkdir | Self::Lookup)
    }
}

/// These are tokens in the McKernel address space, never Linux pointers.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Client {
    pub(crate) operations: u64,
    pub(crate) instance: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Operation {
    Create { mode: u16, client: Client },
    Mkdir,
    Symlink { target: u64 },
    Lookup,
    Unlink { flags: u32 },
}

pub(crate) struct Request {
    pub(crate) operation: Operation,
    path: [u8; PATH_BYTES],
    length: usize,
}

impl Request {
    pub(crate) fn path(&self) -> &[u8] {
        &self.path[..self.length]
    }
}

/// # Safety
/// The caller owns an exclusive claim to the complete kind-specific aligned
/// request in retained exact-generation peer RAM, disjoint from every queue,
/// data buffer and other pending request. The peer polls busy without changing
/// its input until completion. No guest-memory Rust reference is returned.
pub(crate) unsafe fn read(kind: Kind, request: *mut u8) -> Result<Request, i32> {
    let layout = kind.layout();
    if request.is_null() || request as usize % layout.alignment != 0 {
        return Err(-22);
    }
    let busy = unsafe { AtomicI32::from_ptr(request.add(layout.busy).cast()) };
    if busy.load(Ordering::Acquire) != 1 {
        return Err(-16);
    }
    let operation = match kind {
        Kind::Create => {
            let mode = unsafe { ptr::read_volatile(request.cast::<i32>()) };
            if mode < 0 || mode & !0o777 != 0 {
                return Err(-22);
            }
            Operation::Create {
                mode: mode as u16,
                client: Client {
                    operations: unsafe { ptr::read_volatile(request.add(8).cast()) },
                    instance: unsafe { ptr::read_volatile(request.add(16).cast()) },
                },
            }
        }
        Kind::Mkdir => Operation::Mkdir,
        Kind::Symlink => {
            let target = unsafe { ptr::read_volatile(request.add(8).cast::<u64>()) };
            if target == 0 || target > i64::MAX as u64 {
                return Err(-22);
            }
            Operation::Symlink { target }
        }
        Kind::Lookup => Operation::Lookup,
        Kind::Unlink => {
            let flags = unsafe { ptr::read_volatile(request.cast::<u32>()) };
            if flags & !1 != 0 {
                return Err(-22);
            }
            Operation::Unlink { flags }
        }
    };
    let mut result = Request {
        operation,
        path: [0; PATH_BYTES],
        length: 0,
    };
    for index in 0..PATH_BYTES {
        let byte = unsafe { ptr::read_volatile(request.add(layout.path + index)) };
        if byte == 0 {
            result.length = index;
            return Ok(result);
        }
        result.path[index] = byte;
    }
    Err(-36)
}

/// # Safety
/// The same claim and complete mapping as read remain live. Namespace effects
/// and all new owners are published (or failure recorded) before this call.
/// This must be the final access: the peer can free/reuse RAM after busy=0.
pub(crate) unsafe fn complete(
    kind: Kind,
    request: *mut u8,
    error: i32,
    handle: Option<u64>,
) -> Result<(), i32> {
    let layout = kind.layout();
    if request.is_null()
        || request as usize % layout.alignment != 0
        || !(-4095..=0).contains(&error)
        || (kind.returns_handle() && error == 0) != handle.is_some()
        || handle.is_some_and(|handle| handle == 0 || handle > i64::MAX as u64)
    {
        return Err(-22);
    }
    let busy = unsafe { AtomicI32::from_ptr(request.add(layout.busy).cast()) };
    if busy.load(Ordering::Relaxed) != 1 {
        return Err(-16);
    }
    if let Some(handle) = handle {
        unsafe { ptr::write_volatile(request.add(8).cast(), handle) };
    }
    unsafe { ptr::write_volatile(request.add(layout.error).cast(), error) };
    busy.store(0, Ordering::Release);
    Ok(())
}
