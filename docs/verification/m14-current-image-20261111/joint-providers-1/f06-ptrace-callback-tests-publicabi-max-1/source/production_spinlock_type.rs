use core::sync::atomic::AtomicU32;
#[repr(C)]
pub struct IhkSpinlock {
    head_tail: AtomicU32,
}
