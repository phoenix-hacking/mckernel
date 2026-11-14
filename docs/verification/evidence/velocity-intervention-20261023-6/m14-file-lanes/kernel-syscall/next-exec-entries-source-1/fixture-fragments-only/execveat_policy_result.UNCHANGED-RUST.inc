#[no_mangle]
pub extern "C" fn execveat_policy_result(flags: CInt, dirfd: CInt, filename_first: CInt) -> CInt {
    if (flags & !(AT_SYMLINK_NOFOLLOW | AT_EMPTY_PATH)) != 0 {
        return -EINVAL;
    }

    if filename_first == '/' as CInt || dirfd == AT_FDCWD {
        return 0;
    }

    if dirfd < 0 {
        return -EBADF;
    }

    0
}
