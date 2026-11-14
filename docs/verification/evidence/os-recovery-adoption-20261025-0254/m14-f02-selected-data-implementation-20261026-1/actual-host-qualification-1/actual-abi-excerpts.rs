pub type CInt = i32;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct AbiListHead {
    pub next: *mut AbiListHead,
    pub prev: *mut AbiListHead,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct IhkSpinlock {
    pub head_tail: u32,
}

#[repr(C, align(64))]
pub struct McsRwlockLock {
    pub slock: IhkSpinlock,
}
