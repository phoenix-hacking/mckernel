#![no_std]

use core::ffi::{c_char, c_int, c_ulong, c_void};

const MAP_ST_START: usize = 0xffff_8000_0000_0000;
const MAP_FIXED_START: usize = 0xffff_8600_0000_0000;
const NOPHYS: usize = usize::MAX;

#[repr(C)]
pub struct ArchKregs {
    rsp: usize,
    rbp: usize,
    rbx: usize,
    rsi: usize,
    rdi: usize,
    r12: usize,
    r13: usize,
    r14: usize,
    r15: usize,
    rflags: usize,
    rsp0: usize,
}

#[no_mangle]
pub static mut linux_page_offset: c_ulong = 0xffff_8800_0000_0000;

unsafe extern "C" {
    static mut MAP_KERNEL_START: c_ulong;
    static mut kernel_base: c_ulong;
    static mut stderr: *mut c_void;

    fn fprintf(stream: *mut c_void, format: *const c_char, ...) -> c_int;
    fn printf(format: *const c_char, ...) -> c_int;
    fn read_mem(va: usize, buf: *mut c_void, size: usize) -> c_int;
    fn lookup_symbol(name: *mut c_char) -> usize;
    fn read_symbol_64(name: *mut c_char, buf: *mut c_void) -> c_int;
    fn print_bin(buf: *mut c_char, buf_size: usize, data: *mut c_void, size: usize) -> isize;
    fn snprintf(s: *mut c_char, n: usize, format: *const c_char, ...) -> c_int;
}

fn cstr(bytes: &'static [u8]) -> *const c_char {
    bytes.as_ptr() as *const c_char
}

unsafe fn append_placeholder(
    out: &mut *mut c_char,
    out_size: &mut usize,
    total: &mut c_int,
    placeholder: *const c_char,
) -> c_int {
    let ret = unsafe { snprintf(*out, *out_size, cstr(b"%s\0"), placeholder) };
    if ret < 0 {
        return ret;
    }
    unsafe {
        *out = (*out).add(ret as usize);
    }
    *total += ret;
    *out_size = out_size.wrapping_sub(ret as usize);
    ret
}

unsafe fn append_bin(
    out: &mut *mut c_char,
    out_size: &mut usize,
    total: &mut c_int,
    data: *const usize,
    size: usize,
) -> c_int {
    let ret = unsafe { print_bin(*out, *out_size, data as *mut c_void, size) };
    if ret < 0 {
        return ret as c_int;
    }
    unsafe {
        *out = (*out).add(ret as usize);
    }
    *total += ret as c_int;
    *out_size = out_size.wrapping_sub(ret as usize);
    ret as c_int
}

#[no_mangle]
pub unsafe extern "C" fn print_kregs(
    rbp: *mut c_char,
    rbp_size: usize,
    kregs: *const ArchKregs,
) -> c_int {
    let mut out = rbp;
    let mut out_size = rbp_size;
    let mut total = 0;
    let ihk_mc_switch_context =
        unsafe { lookup_symbol(b"ihk_mc_switch_context\0".as_ptr() as *mut c_char) };

    let mut ret = unsafe {
        append_placeholder(
            &mut out,
            &mut out_size,
            &mut total,
            cstr(b"xxxxxxxxxxxxxxxx\0"),
        )
    };
    if ret < 0 {
        return ret;
    }

    ret = unsafe {
        append_bin(
            &mut out,
            &mut out_size,
            &mut total,
            core::ptr::addr_of!((*kregs).rbx),
            core::mem::size_of::<usize>(),
        )
    };
    if ret < 0 {
        return ret;
    }

    let mut idx = 0;
    while idx < 2 {
        ret = unsafe {
            append_placeholder(
                &mut out,
                &mut out_size,
                &mut total,
                cstr(b"xxxxxxxxxxxxxxxx\0"),
            )
        };
        if ret < 0 {
            return ret;
        }
        idx += 1;
    }

    let regs_1 = [
        core::ptr::addr_of!((*kregs).rsi),
        core::ptr::addr_of!((*kregs).rdi),
        core::ptr::addr_of!((*kregs).rbp),
        core::ptr::addr_of!((*kregs).rsp),
    ];
    idx = 0;
    while idx < regs_1.len() {
        ret = unsafe {
            append_bin(
                &mut out,
                &mut out_size,
                &mut total,
                *regs_1.as_ptr().add(idx),
                core::mem::size_of::<usize>(),
            )
        };
        if ret < 0 {
            return ret;
        }
        idx += 1;
    }

    idx = 0;
    while idx < 4 {
        ret = unsafe {
            append_placeholder(
                &mut out,
                &mut out_size,
                &mut total,
                cstr(b"xxxxxxxxxxxxxxxx\0"),
            )
        };
        if ret < 0 {
            return ret;
        }
        idx += 1;
    }

    let regs_2 = [
        core::ptr::addr_of!((*kregs).r12),
        core::ptr::addr_of!((*kregs).r13),
        core::ptr::addr_of!((*kregs).r14),
        core::ptr::addr_of!((*kregs).r15),
    ];
    idx = 0;
    while idx < regs_2.len() {
        ret = unsafe {
            append_bin(
                &mut out,
                &mut out_size,
                &mut total,
                *regs_2.as_ptr().add(idx),
                core::mem::size_of::<usize>(),
            )
        };
        if ret < 0 {
            return ret;
        }
        idx += 1;
    }

    ret = unsafe {
        append_bin(
            &mut out,
            &mut out_size,
            &mut total,
            &ihk_mc_switch_context,
            core::mem::size_of::<usize>(),
        )
    };
    if ret < 0 {
        return ret;
    }

    ret = unsafe {
        print_bin(
            out,
            out_size,
            core::ptr::addr_of!((*kregs).rflags) as *mut c_void,
            core::mem::size_of::<u32>(),
        )
    } as c_int;
    if ret < 0 {
        return ret;
    }
    unsafe {
        out = out.add(ret as usize);
    }
    total += ret;
    out_size = out_size.wrapping_sub(ret as usize);

    idx = 0;
    while idx < 6 {
        ret =
            unsafe { append_placeholder(&mut out, &mut out_size, &mut total, cstr(b"xxxxxxxx\0")) };
        if ret < 0 {
            return ret;
        }
        idx += 1;
    }

    total
}

#[no_mangle]
pub unsafe extern "C" fn virt_to_phys(va: usize) -> usize {
    let map_kernel_start = unsafe { MAP_KERNEL_START as usize };
    let kernel_base_value = unsafe { kernel_base as usize };
    let linux_page_offset_value = unsafe { linux_page_offset as usize };

    if va >= map_kernel_start {
        va.wrapping_sub(map_kernel_start)
            .wrapping_add(kernel_base_value)
    } else if va >= linux_page_offset_value {
        va.wrapping_sub(linux_page_offset_value)
    } else if va >= MAP_FIXED_START {
        va.wrapping_sub(MAP_FIXED_START)
    } else if va >= MAP_ST_START {
        va.wrapping_sub(MAP_ST_START)
    } else {
        NOPHYS
    }
}

#[no_mangle]
pub unsafe extern "C" fn arch_setup_constants(_mcos_fd: c_int) -> c_int {
    unsafe {
        MAP_KERNEL_START = lookup_symbol(b"_head\0".as_ptr() as *mut c_char) as c_ulong;
    }
    if unsafe { MAP_KERNEL_START as usize } == NOPHYS {
        unsafe {
            fprintf(stderr, cstr(b"error: obtaining MAP_KERNEL_START\n\0"));
        }
        return 1;
    }

    unsafe {
        MAP_KERNEL_START = MAP_KERNEL_START.wrapping_sub(0x1000);
        printf(
            cstr(b"x86 MAP_KERNEL_START 0x%lx\n\0"),
            MAP_KERNEL_START as c_ulong,
        );
    }

    if unsafe {
        read_symbol_64(
            b"linux_page_offset_base\0".as_ptr() as *mut c_char,
            core::ptr::addr_of_mut!(linux_page_offset) as *mut c_void,
        )
    } != 0
    {
        unsafe {
            fprintf(stderr, cstr(b"error: obtaining Linux page offset\n\0"));
        }
        return 1;
    }

    unsafe {
        printf(
            cstr(b"x86 linux_page_offset: 0x%lx\n\0"),
            linux_page_offset as c_ulong,
        );
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn arch_read_kregs(ctx: c_ulong, kregs: *mut ArchKregs) -> c_int {
    unsafe {
        read_mem(
            ctx as usize,
            kregs as *mut c_void,
            core::mem::size_of::<ArchKregs>(),
        )
    }
}
