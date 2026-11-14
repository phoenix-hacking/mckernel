use core::ffi::c_char;

use crate::abi::{CInt, CULong};

const REPORTED_BIT: u32 = 31;
const COLUMN_MASK: u32 = !(1_u32 << REPORTED_BIT);
const LINE_MASK: u32 = !0_u32;

const PROLOGUE_FMT: &[u8] = b"UBSAN: Undefined behaviour in %s:%d:%d\n\0";
const NULL_PTR_FMT: &[u8] = b"%s: null pointer deref\n\0";
const ALIGN_FMT: &[u8] = b"%s: pointer %#16lx of type %s is not aligned at %#lx\n\0";
const SPACE_FMT: &[u8] =
    b"%s: %s address %#16lx with insufficient space for an object of type %s\n\0";
const POINTER_OVERFLOW_FMT: &[u8] = b"%s: pointer overflow from %lx to %lx\n\0";
const TWO_VAL_FMT: &[u8] = b"%s: %lx %lx\n\0";
const ONE_VAL_FMT: &[u8] = b"%s: %lx\n\0";
const NAME_FMT: &[u8] = b"%s\n\0";
const UNKNOWN_KIND: &[u8] = b"unknown\0";

const TYPE_CHECK_LOAD: &[u8] = b"load of\0";
const TYPE_CHECK_STORE: &[u8] = b"store to\0";
const TYPE_CHECK_REFERENCE: &[u8] = b"reference binding to\0";
const TYPE_CHECK_MEMBER_ACCESS: &[u8] = b"member access within\0";
const TYPE_CHECK_MEMBER_CALL: &[u8] = b"member call on\0";
const TYPE_CHECK_CONSTRUCTOR: &[u8] = b"constructor call on\0";
const TYPE_CHECK_DOWNCAST_0: &[u8] = b"downcast of\0";
const TYPE_CHECK_DOWNCAST_1: &[u8] = b"downcast of\0";

const TYPE_MISMATCH_NAME: &[u8] = b"__ubsan_handle_type_mismatch\0";
const POINTER_OVERFLOW_NAME: &[u8] = b"__ubsan_handle_pointer_overflow\0";
const ADD_OVERFLOW_NAME: &[u8] = b"__ubsan_handle_add_overflow\0";
const SUB_OVERFLOW_NAME: &[u8] = b"__ubsan_handle_sub_overflow\0";
const MUL_OVERFLOW_NAME: &[u8] = b"__ubsan_handle_mul_overflow\0";
const NEGATE_OVERFLOW_NAME: &[u8] = b"__ubsan_handle_negate_overflow\0";
const DIVREM_OVERFLOW_NAME: &[u8] = b"__ubsan_handle_divrem_overflow\0";
const VLA_BOUND_NAME: &[u8] = b"__ubsan_handle_vla_bound_not_positive\0";
const OUT_OF_BOUNDS_NAME: &[u8] = b"__ubsan_handle_out_of_bounds\0";
const SHIFT_OUT_OF_BOUNDS_NAME: &[u8] = b"__ubsan_handle_shift_out_of_bounds\0";
const BUILTIN_UNREACHABLE_NAME: &[u8] = b"__ubsan_handle_builtin_unreachable\0";
const LOAD_INVALID_VALUE_NAME: &[u8] = b"__ubsan_handle_load_invalid_value\0";

#[repr(C)]
pub struct TypeDescriptor {
    type_kind: i16,
    type_info: i16,
    type_name: [c_char; 1],
}

#[repr(C)]
pub struct SourceLocation {
    file_name: *const c_char,
    line: CInt,
    column: CInt,
}

#[repr(C)]
pub struct TypeMismatchDataV1 {
    location: SourceLocation,
    typ: *mut TypeDescriptor,
    log_alignment: u8,
    type_check_kind: u8,
}

#[repr(C)]
pub struct TypeMismatchData {
    location: SourceLocation,
    typ: *mut TypeDescriptor,
    alignment: CULong,
    type_check_kind: u8,
}

#[repr(C)]
pub struct OverflowData {
    location: SourceLocation,
    typ: *mut TypeDescriptor,
}

#[repr(C)]
pub struct VlaBoundData {
    location: SourceLocation,
    typ: *mut TypeDescriptor,
}

#[repr(C)]
pub struct OutOfBoundsData {
    location: SourceLocation,
    array_type: *mut TypeDescriptor,
    index_type: *mut TypeDescriptor,
}

#[repr(C)]
pub struct ShiftOutOfBoundsData {
    location: SourceLocation,
    lhs_type: *mut TypeDescriptor,
    rhs_type: *mut TypeDescriptor,
}

#[repr(C)]
pub struct UnreachableData {
    location: SourceLocation,
}

#[repr(C)]
pub struct InvalidValueData {
    location: SourceLocation,
    typ: *mut TypeDescriptor,
}

#[repr(C)]
pub struct PointerOverflowData {
    location: SourceLocation,
}

extern "C" {
    fn kprintf(format: *const c_char, ...) -> CInt;
    #[link_name = "panic"]
    fn kernel_panic(message: *const c_char) -> !;
}

#[inline(always)]
unsafe fn type_name(typ: *mut TypeDescriptor) -> *const c_char {
    unsafe { &raw const (*typ).type_name as *const c_char }
}

#[inline(always)]
fn type_check_kind(kind: u8) -> *const c_char {
    match kind {
        0 => TYPE_CHECK_LOAD.as_ptr().cast(),
        1 => TYPE_CHECK_STORE.as_ptr().cast(),
        2 => TYPE_CHECK_REFERENCE.as_ptr().cast(),
        3 => TYPE_CHECK_MEMBER_ACCESS.as_ptr().cast(),
        4 => TYPE_CHECK_MEMBER_CALL.as_ptr().cast(),
        5 => TYPE_CHECK_CONSTRUCTOR.as_ptr().cast(),
        6 => TYPE_CHECK_DOWNCAST_0.as_ptr().cast(),
        7 => TYPE_CHECK_DOWNCAST_1.as_ptr().cast(),
        _ => UNKNOWN_KIND.as_ptr().cast(),
    }
}

#[inline(always)]
fn is_aligned(ptr: CULong, alignment: CULong) -> bool {
    alignment != 0 && (ptr & (alignment - 1)) == 0
}

#[no_mangle]
pub unsafe extern "C" fn ubsan_prologue(loc: *mut SourceLocation) {
    unsafe {
        kprintf(
            PROLOGUE_FMT.as_ptr().cast(),
            (*loc).file_name,
            (*loc).line as u32 & LINE_MASK,
            (*loc).column as u32 & COLUMN_MASK,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_type_mismatch(data: *mut TypeMismatchData, ptr: CULong) {
    unsafe {
        ubsan_prologue(&raw mut (*data).location);
        if ptr == 0 {
            kprintf(NULL_PTR_FMT.as_ptr().cast(), TYPE_MISMATCH_NAME.as_ptr());
        } else if (*data).alignment != 0 && !is_aligned(ptr, (*data).alignment) {
            kprintf(
                ALIGN_FMT.as_ptr().cast(),
                TYPE_MISMATCH_NAME.as_ptr(),
                ptr,
                type_name((*data).typ),
                (*data).alignment,
            );
        } else {
            kprintf(
                SPACE_FMT.as_ptr().cast(),
                TYPE_MISMATCH_NAME.as_ptr(),
                type_check_kind((*data).type_check_kind),
                ptr,
                type_name((*data).typ),
            );
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_type_mismatch_v1(
    data_v1: *mut TypeMismatchDataV1,
    ptr: CULong,
) {
    let mut data = unsafe {
        TypeMismatchData {
            location: SourceLocation {
                file_name: (*data_v1).location.file_name,
                line: (*data_v1).location.line,
                column: (*data_v1).location.column,
            },
            typ: (*data_v1).typ,
            alignment: 1_u64.wrapping_shl((*data_v1).log_alignment as u32) as CULong,
            type_check_kind: (*data_v1).type_check_kind,
        }
    };
    unsafe {
        __ubsan_handle_type_mismatch(&raw mut data, ptr);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_pointer_overflow(
    data: *mut PointerOverflowData,
    base: CULong,
    result: CULong,
) {
    unsafe {
        ubsan_prologue(&raw mut (*data).location);
        kprintf(
            POINTER_OVERFLOW_FMT.as_ptr().cast(),
            POINTER_OVERFLOW_NAME.as_ptr(),
            base,
            result,
        );
    }
}

unsafe fn print_overflow(data: *mut OverflowData, name: &[u8], lhs: CULong, rhs: CULong) {
    unsafe {
        ubsan_prologue(&raw mut (*data).location);
        kprintf(TWO_VAL_FMT.as_ptr().cast(), name.as_ptr(), lhs, rhs);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_add_overflow(
    data: *mut OverflowData,
    lhs: CULong,
    rhs: CULong,
) {
    unsafe {
        print_overflow(data, ADD_OVERFLOW_NAME, lhs, rhs);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_sub_overflow(
    data: *mut OverflowData,
    lhs: CULong,
    rhs: CULong,
) {
    unsafe {
        print_overflow(data, SUB_OVERFLOW_NAME, lhs, rhs);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_mul_overflow(
    data: *mut OverflowData,
    lhs: CULong,
    rhs: CULong,
) {
    unsafe {
        print_overflow(data, MUL_OVERFLOW_NAME, lhs, rhs);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_negate_overflow(data: *mut OverflowData, old_val: CULong) {
    unsafe {
        ubsan_prologue(&raw mut (*data).location);
        kprintf(
            ONE_VAL_FMT.as_ptr().cast(),
            NEGATE_OVERFLOW_NAME.as_ptr(),
            old_val,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_divrem_overflow(
    data: *mut OverflowData,
    lhs: CULong,
    rhs: CULong,
) {
    unsafe {
        print_overflow(data, DIVREM_OVERFLOW_NAME, lhs, rhs);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_vla_bound_not_positive(
    data: *mut VlaBoundData,
    bound: CULong,
) {
    unsafe {
        ubsan_prologue(&raw mut (*data).location);
        kprintf(ONE_VAL_FMT.as_ptr().cast(), VLA_BOUND_NAME.as_ptr(), bound);
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_out_of_bounds(data: *mut OutOfBoundsData, index: CULong) {
    unsafe {
        ubsan_prologue(&raw mut (*data).location);
        kprintf(
            ONE_VAL_FMT.as_ptr().cast(),
            OUT_OF_BOUNDS_NAME.as_ptr(),
            index,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_shift_out_of_bounds(
    data: *mut ShiftOutOfBoundsData,
    lhs: CULong,
    rhs: CULong,
) {
    unsafe {
        ubsan_prologue(&raw mut (*data).location);
        kprintf(
            TWO_VAL_FMT.as_ptr().cast(),
            SHIFT_OUT_OF_BOUNDS_NAME.as_ptr(),
            lhs,
            rhs,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_builtin_unreachable(data: *mut UnreachableData) {
    unsafe {
        ubsan_prologue(&raw mut (*data).location);
        kprintf(NAME_FMT.as_ptr().cast(), BUILTIN_UNREACHABLE_NAME.as_ptr());
        kernel_panic(BUILTIN_UNREACHABLE_NAME.as_ptr().cast());
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ubsan_handle_load_invalid_value(
    data: *mut InvalidValueData,
    val: CULong,
) {
    unsafe {
        ubsan_prologue(&raw mut (*data).location);
        kprintf(
            ONE_VAL_FMT.as_ptr().cast(),
            LOAD_INVALID_VALUE_NAME.as_ptr(),
            val,
        );
    }
}

const _: () = {
    use core::mem::{offset_of, size_of};

    assert!(size_of::<SourceLocation>() == 16);
    assert!(offset_of!(SourceLocation, line) == 8);
    assert!(offset_of!(SourceLocation, column) == 12);
    assert!(offset_of!(TypeMismatchData, alignment) == 24);
};
