#[repr(C)]
pub struct SyscallRequest {
    pub rtid: CInt,
    pub ttid: CInt,
    pub valid: CULong,
    pub number: CULong,
    pub args: [CULong; 6],
}
