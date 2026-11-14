// SOURCE FRAGMENT ONLY, include alongside actual candidate body and existing
// DebugRegisterReader trait. No hardware export is called by this entry.
extern "C" { fn fixture_debug_register_read(reg: CInt) -> CULong; }
struct ControlledDebugReader;
impl DebugRegisterReader for ControlledDebugReader {
    unsafe fn read<const REG: u8>(&mut self) -> CULong {
        unsafe { fixture_debug_register_read(REG as CInt) }
    }
}
#[no_mangle]
pub unsafe extern "C" fn actual_debug_controlled(regs: *mut X86UserContext) {
    unsafe { x86_debug_handler_body(regs, &mut ControlledDebugReader); }
}
