#[repr(C)]
pub struct HwPerfEventExtra {
    pub config: CULong,
    pub reg: u32,
    pub idx: CInt,
}
