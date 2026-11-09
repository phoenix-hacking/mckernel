#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}


const _: () = {
    use core::mem::{align_of, offset_of, size_of};
    assert!(size_of::<Ddebug>() == 32);
    assert!(align_of::<Ddebug>() == 8);
    assert!(offset_of!(Ddebug, file) == 0);
    assert!(offset_of!(Ddebug, func) == 8);
    assert!(offset_of!(Ddebug, fmt) == 16);
    assert!(offset_of!(Ddebug, line_flags) == 24);
};
