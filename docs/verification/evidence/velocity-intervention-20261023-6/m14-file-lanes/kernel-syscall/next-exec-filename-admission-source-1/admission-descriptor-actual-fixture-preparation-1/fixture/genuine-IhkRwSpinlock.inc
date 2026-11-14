#[repr(C)]
pub struct IhkRwSpinlock {
    counter: AtomicI32,
}
