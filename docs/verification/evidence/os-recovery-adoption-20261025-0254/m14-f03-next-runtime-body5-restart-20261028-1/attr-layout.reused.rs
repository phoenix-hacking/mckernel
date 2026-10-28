// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete selected runtime layout from genuine lib/include/mc_perf_event.h.
// __GENKSYMS__ is a distinct Linux metadata projection and is not this runtime ABI.
use crate::abi::{CInt, CULong};

#[repr(C)]
#[derive(Clone, Copy)]
pub union PerfSample {
    pub sample_period: CULong,
    pub sample_freq: CULong,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub union PerfWakeup {
    pub wakeup_events: u32,
    pub wakeup_watermark: u32,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub union PerfConfigOne {
    pub bp_addr: CULong,
    pub config1: CULong,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub union PerfConfigTwo {
    pub bp_len: CULong,
    pub config2: CULong,
}

#[repr(C)]
pub struct PerfEventAttr {
    pub type_: u32,
    pub size: u32,
    pub config: CULong,
    pub sampling: PerfSample,
    pub sample_type: CULong,
    pub read_format: CULong,
    // The genuine C unsigned-long bitfield allocation unit. Every one of its
    // 64 source-declared bits is independently checked against C object bytes.
    pub flags: CULong,
    pub wakeup: PerfWakeup,
    pub bp_type: u32,
    pub config_one: PerfConfigOne,
    pub config_two: PerfConfigTwo,
    pub branch_sample_type: CULong,
    pub sample_regs_user: CULong,
    pub sample_stack_user: u32,
    pub reserved_two: u32,
    pub sample_regs_intr: CULong,
}

impl PerfEventAttr {
    // Ten preceding one-bit members in the actual selected header; this is
    // qualified by the genuine C .freq=1 image, not an assumed Linux ABI.
    pub const FREQUENCY_SHIFT: u32 = 10;

    pub fn frequency(&self) -> CInt {
        ((self.flags >> Self::FREQUENCY_SHIFT) & 1) as CInt
    }
}
