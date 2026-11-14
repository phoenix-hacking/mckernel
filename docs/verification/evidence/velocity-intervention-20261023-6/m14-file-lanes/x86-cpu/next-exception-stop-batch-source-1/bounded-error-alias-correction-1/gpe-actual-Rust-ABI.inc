// Include with actual abi.rs; no model context layout.
#[no_mangle]
pub static M14_RUST_GPE_ABI:[usize;11]=[
 core::mem::size_of::<crate::abi::X86UserContext>(),
 core::mem::align_of::<crate::abi::X86UserContext>(),
 core::mem::offset_of!(crate::abi::X86UserContext,gpr)+core::mem::offset_of!(crate::abi::X86BasicRegs,orig_rax),
 core::mem::offset_of!(crate::abi::X86UserContext,gpr)+core::mem::offset_of!(crate::abi::X86BasicRegs,cs),
 core::mem::offset_of!(crate::abi::X86UserContext,gpr)+core::mem::offset_of!(crate::abi::X86BasicRegs,rip),
 core::mem::offset_of!(crate::abi::X86UserContext,gpr)+core::mem::offset_of!(crate::abi::X86BasicRegs,rsp),
 core::mem::size_of::<u32>(),0,1,2,3];
