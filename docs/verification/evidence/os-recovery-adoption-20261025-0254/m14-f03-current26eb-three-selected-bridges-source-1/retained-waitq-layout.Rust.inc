#[repr(C)]
pub(crate) struct IhkSpinlock {
    head_tail: CUInt,
}

#[repr(C)]
pub(crate) struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}

#[repr(C)]
pub(crate) struct Waitq {
    lock: IhkSpinlock,
    waitq: ListHead,
}
