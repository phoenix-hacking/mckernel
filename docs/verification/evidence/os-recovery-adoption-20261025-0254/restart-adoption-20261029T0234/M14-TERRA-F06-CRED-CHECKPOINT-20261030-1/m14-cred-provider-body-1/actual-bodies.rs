unsafe fn mcctrl_control_fill_cred_values(
    out: *mut c_int,
    current_uid: McctrlControlCredValueFn,
    current_euid: McctrlControlCredValueFn,
    current_suid: McctrlControlCredValueFn,
    current_fsuid: McctrlControlCredValueFn,
    current_gid: McctrlControlCredValueFn,
    current_egid: McctrlControlCredValueFn,
    current_sgid: McctrlControlCredValueFn,
    current_fsgid: McctrlControlCredValueFn,
) {
    *out.add(0) = current_uid();
    *out.add(1) = current_euid();
    *out.add(2) = current_suid();
    *out.add(3) = current_fsuid();
    *out.add(4) = current_gid();
    *out.add(5) = current_egid();
    *out.add(6) = current_sgid();
    *out.add(7) = current_fsgid();
}

pub unsafe extern "C" fn mcctrl_control_getcred_body_result(
    phys: c_ulong,
    phys_to_virt: Option<McctrlControlPhysToVirtFn>,
    current_uid: Option<McctrlControlCredValueFn>,
    current_euid: Option<McctrlControlCredValueFn>,
    current_suid: Option<McctrlControlCredValueFn>,
    current_fsuid: Option<McctrlControlCredValueFn>,
    current_gid: Option<McctrlControlCredValueFn>,
    current_egid: Option<McctrlControlCredValueFn>,
    current_sgid: Option<McctrlControlCredValueFn>,
    current_fsgid: Option<McctrlControlCredValueFn>,
) -> c_int {
    let (
        Some(phys_to_virt),
        Some(current_uid),
        Some(current_euid),
        Some(current_suid),
        Some(current_fsuid),
        Some(current_gid),
        Some(current_egid),
        Some(current_sgid),
        Some(current_fsgid),
    ) = (
        phys_to_virt,
        current_uid,
        current_euid,
        current_suid,
        current_fsuid,
        current_gid,
        current_egid,
        current_sgid,
        current_fsgid,
    )
    else {
        return -EINVAL;
    };

    let out = phys_to_virt(phys) as *mut c_int;
    mcctrl_control_fill_cred_values(
        out,
        current_uid,
        current_euid,
        current_suid,
        current_fsuid,
        current_gid,
        current_egid,
        current_sgid,
        current_fsgid,
    );
    0
}
