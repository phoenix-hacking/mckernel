mod local_accessor {
    use crate::abi::{CInt, X86CpuLocalVariables};

const PAGE_SIZE: usize = 4096;
const LOCALS_SPAN: usize = 4 * PAGE_SIZE;

    // Borrow the genuine existing pointer slot; never define another locals.
    unsafe extern "C" {
        static mut locals: *mut X86CpuLocalVariables;
    }

#[inline(always)]
unsafe fn local_addr(id: CInt) -> *mut X86CpuLocalVariables {
    (locals as *mut u8).add(LOCALS_SPAN.wrapping_mul(id as usize)) as *mut X86CpuLocalVariables
}

#[no_mangle]
pub unsafe extern "C" fn get_x86_cpu_local_variable(id: CInt) -> *mut X86CpuLocalVariables {
    local_addr(id)
}
}
