#![no_std]
type CULong=u64;
extern "C" { #[link_name="_end"] static X86_END:u8; }
#[no_mangle]
pub extern "C" fn x86_init_text_end_bridge() -> CULong {
    // The linker boundary may be one-past storage: form its address, never read it.
    core::ptr::addr_of!(X86_END) as CULong
}
