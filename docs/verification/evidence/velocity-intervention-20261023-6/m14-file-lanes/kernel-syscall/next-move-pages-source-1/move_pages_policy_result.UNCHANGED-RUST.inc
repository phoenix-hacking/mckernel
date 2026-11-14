#[no_mangle]
pub extern "C" fn move_pages_policy_result(pid: CInt, flags: CInt) -> CInt {
    if pid != 0 {
        return -EINVAL;
    }

    if (flags & !(MPOL_MF_MOVE | MPOL_MF_MOVE_ALL)) != 0 || (flags & MPOL_MF_MOVE_ALL) != 0 {
        return -EINVAL;
    }

    0
}
