#[repr(C)]
pub struct X86BasicRegs {
    pub r15: CULong,
    pub r14: CULong,
    pub r13: CULong,
    pub r12: CULong,
    pub rbp: CULong,
    pub rbx: CULong,
    pub r11: CULong,
    pub r10: CULong,
    pub r9: CULong,
    pub r8: CULong,
    pub rax: CULong,
    pub rcx: CULong,
    pub rdx: CULong,
    pub rsi: CULong,
    pub rdi: CULong,
    pub orig_rax: CULong,
    pub rip: CULong,
    pub cs: CULong,
    pub rflags: CULong,
    pub rsp: CULong,
    pub ss: CULong,
}

#[repr(C)]
pub struct X86Sregs {
    pub fs_base: CULong,
    pub gs_base: CULong,
    pub ds: CULong,
    pub es: CULong,
    pub fs: CULong,
    pub gs: CULong,
}

#[repr(C)]
pub struct X86UserContext {
    pub sr: X86Sregs,
    pub is_gpr_valid: u8,
    pub is_sr_valid: u8,
    pub spare_flags6: u8,
    pub spare_flags5: u8,
    pub spare_flags4: u8,
    pub spare_flags3: u8,
    pub spare_flags2: u8,
    pub spare_flags1: u8,
    pub gpr: X86BasicRegs,
}
