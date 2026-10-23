#![no_std]
type CULong=u64;
extern "C" { #[link_name="x86_map_kernel_start_geometry"] static X86_MAP_KERNEL_START_GEOMETRY:CULong; }
#[no_mangle]
pub extern "C" fn x86_init_text_map_kernel_start_bridge() -> CULong {
    // Preserve the build-resolved address; never duplicate its numeric value.
    unsafe { X86_MAP_KERNEL_START_GEOMETRY }
}
