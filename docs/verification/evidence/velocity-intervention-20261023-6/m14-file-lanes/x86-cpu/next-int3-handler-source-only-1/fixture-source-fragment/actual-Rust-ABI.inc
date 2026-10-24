// Include only with actual current abi.rs.
#[no_mangle]
pub static M14_RUST_INT3_ABI:[usize;13]=[
 core::mem::size_of::<crate::abi::X86UserContext>(),
 core::mem::align_of::<crate::abi::X86UserContext>(),
 core::mem::size_of::<crate::abi::SigInfo>(),
 core::mem::align_of::<crate::abi::SigInfo>(),
 core::mem::offset_of!(crate::abi::SigInfo,si_code),
 core::mem::offset_of!(crate::abi::SigInfo,sifields),
 core::mem::size_of::<u32>(),core::mem::size_of::<u32>(),
 core::mem::offset_of!(crate::abi::X86UserContext,gpr)+core::mem::offset_of!(crate::abi::X86BasicRegs,rsp),
 5,1,2,3];
