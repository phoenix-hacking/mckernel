use crate::abi::CULong;
#[repr(C, align(64))]
pub struct McsRwlockNodeIrqsave {
    irqsave: CULong,
}
