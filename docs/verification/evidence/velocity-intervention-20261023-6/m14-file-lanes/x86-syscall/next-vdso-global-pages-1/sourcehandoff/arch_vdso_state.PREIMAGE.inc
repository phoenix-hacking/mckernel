unsafe fn arch_vdso_state() -> Result<(*mut ArchVdso, *mut SizeT, *mut isize), CInt> {
    let mut vdso: *mut ArchVdso = null_mut();
    let mut container_size: *mut SizeT = null_mut();
    let mut vdso_offset: *mut isize = null_mut();

    arch_vdso_state_bridge(
        addr_of_mut!(vdso),
        addr_of_mut!(container_size),
        addr_of_mut!(vdso_offset),
    );
    if vdso.is_null() || container_size.is_null() || vdso_offset.is_null() {
        return Err(-EFAULT);
    }
    Ok((vdso, container_size, vdso_offset))
}
