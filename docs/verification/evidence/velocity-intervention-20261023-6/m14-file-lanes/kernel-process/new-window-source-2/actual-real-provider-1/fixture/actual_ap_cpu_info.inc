#[repr(C)]
pub(crate) struct IhkMcCpuInfo {
    pub(crate) ncpus: CInt,
    pub(crate) hw_ids: *mut CInt,
    pub(crate) nodes: *mut CInt,
    pub(crate) linux_cpu_ids: *mut CInt,
    pub(crate) ikc_cpus: *mut CInt,
}
