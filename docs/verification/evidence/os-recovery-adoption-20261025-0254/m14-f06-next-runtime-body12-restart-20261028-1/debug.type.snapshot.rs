#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}

unsafe extern "C" {pub fn kprintf(format:*const i8,...)->crate::abi::CInt;}
