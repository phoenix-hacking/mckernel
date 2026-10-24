// Real current abi.rs; no model layouts.
#[no_mangle]
pub static M14_RUST_DEBUG_ABI:[usize;10]=[
 core::mem::size_of::<crate::abi::X86UserContext>(),
 core::mem::size_of::<crate::abi::SigInfo>(),core::mem::align_of::<crate::abi::SigInfo>(),
 core::mem::offset_of!(crate::abi::SigInfo,si_code),core::mem::offset_of!(crate::abi::SigInfo,sifields),
 core::mem::offset_of!(crate::abi::X86UserContext,gpr)+core::mem::offset_of!(crate::abi::X86BasicRegs,rflags),
 core::mem::size_of::<u32>(),1<<14,0xf,1<<8];
