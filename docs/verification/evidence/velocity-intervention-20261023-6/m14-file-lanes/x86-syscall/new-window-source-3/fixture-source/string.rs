use core::ffi::c_void;
use core::ptr::write_volatile;
use crate::abi::{CULong,SizeT};
#[no_mangle]
pub unsafe extern "C" fn __inline_memset(
    s: *mut c_void,
    c: CULong,
    mut count: SizeT,
) -> *mut c_void {
    let mut ptr = s.cast::<u8>();
    let bytes = (c as u32).to_le_bytes();

    while count >= 4 {
        write_volatile(ptr, bytes[0]);
        write_volatile(ptr.add(1), bytes[1]);
        write_volatile(ptr.add(2), bytes[2]);
        write_volatile(ptr.add(3), bytes[3]);
        ptr = ptr.add(4);
        count -= 4;
    }
    if count >= 2 {
        write_volatile(ptr, bytes[0]);
        write_volatile(ptr.add(1), bytes[1]);
        ptr = ptr.add(2);
        count -= 2;
    }
    if count != 0 {
        write_volatile(ptr, bytes[0]);
    }

    s
}
