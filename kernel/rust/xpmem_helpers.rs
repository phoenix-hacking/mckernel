use core::ptr::write;

use crate::abi::{CInt, CLong, CULong, OffT, SizeT};

const EINVAL: CInt = 22;
const EACCES: CInt = 13;
const ENOENT: CInt = 2;
const EBUSY: CInt = 16;
const EFAULT: CInt = 14;

const PAGE_SIZE: CULong = 1 << 12;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);

const XPMEM_TG_HASHTABLE_SIZE: CInt = 8;
const XPMEM_AP_HASHTABLE_SIZE: CInt = 8;
const XPMEM_MAX_UNIQ_ID: CInt = CInt::MAX >> 1;

const XPMEM_RDONLY: CInt = 0x1;
const XPMEM_RDWR: CInt = 0x2;
const XPMEM_PERMIT_MODE: CInt = 0x1;
const XPMEM_PERM_IRUSR: CInt = 0o400;
const XPMEM_PERM_IWUSR: CInt = 0o200;
const XPMEM_FLAG_DESTROYING: CInt = 0x00040;
const XPMEM_FLAG_DESTROYED: CInt = 0x00080;
const XPMEM_FLAG_VALIDPTES: CInt = 0x00200;
const XPMEM_DETACH_LOOKUP_CONTINUE: CInt = 1;
const XPMEM_LOOKUP_SKIP: CInt = 0;
const XPMEM_LOOKUP_TAKE: CInt = 1;
const XPMEM_LOOKUP_STOP: CInt = 2;
const VR_PROT_WRITE: CULong = 0x00020000;

#[inline(always)]
fn offset_in_page(value: CULong) -> CULong {
    value & !PAGE_MASK
}

#[inline(always)]
fn low_u32(value: CLong) -> u32 {
    value as u64 as u32
}

#[inline(always)]
fn high_u32(value: CLong) -> u32 {
    (value as u64 >> 32) as u32
}

#[inline(always)]
fn xpmem_perms_inner(
    perm_uid: CInt,
    perm_gid: CInt,
    perm_mode: CULong,
    flag: CInt,
    current_ruid: CInt,
    current_rgid: CInt,
) -> CInt {
    let requested_mode = (flag >> 6) | (flag >> 3) | flag;
    let mut granted_mode = perm_mode;

    if perm_uid == current_ruid {
        granted_mode >>= 6;
    } else if perm_gid == current_rgid {
        granted_mode >>= 3;
    }

    if (requested_mode as CULong & !granted_mode & 0o7) != 0 {
        -1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_id_to_tgid_result(id: CLong) -> CInt {
    low_u32(id) as CInt
}

#[no_mangle]
pub extern "C" fn xpmem_tg_hashtable_index_result(tgid: CInt) -> CInt {
    (tgid as u32 % XPMEM_TG_HASHTABLE_SIZE as u32) as CInt
}

#[no_mangle]
pub extern "C" fn xpmem_ap_hashtable_index_result(apid: CLong) -> CInt {
    (high_u32(apid) % XPMEM_AP_HASHTABLE_SIZE as u32) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_make_id_result(tgid: CInt, uniq: CInt, idp: *mut CLong) -> CInt {
    if uniq > XPMEM_MAX_UNIQ_ID {
        return -EBUSY;
    }

    let id = ((uniq as u32 as u64) << 32) | (tgid as u32 as u64);
    write(idp, id as CLong);
    0
}

#[no_mangle]
pub extern "C" fn xpmem_positive_id_result(id: CLong) -> CInt {
    if id <= 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_owner_policy_result(current_pid: CInt, owner_tgid: CInt) -> CInt {
    if current_pid != owner_tgid {
        -EACCES
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_make_initial_policy_result(
    permit_type: CInt,
    permit_value: CULong,
    size: SizeT,
) -> CInt {
    if permit_type != XPMEM_PERMIT_MODE || (permit_value & !0o777) != 0 || size == 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_make_alignment_result(vaddr: CULong, size: SizeT) -> CInt {
    if offset_in_page(vaddr) != 0 || (offset_in_page(size as CULong) != 0 && size != SizeT::MAX) {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_get_policy_result(
    segid: CLong,
    flags: CInt,
    permit_type: CInt,
    has_permit_value: CInt,
) -> CInt {
    if segid <= 0 {
        return -EINVAL;
    }

    if (flags & !(XPMEM_RDONLY | XPMEM_RDWR)) != 0
        || (flags & (XPMEM_RDONLY | XPMEM_RDWR)) == (XPMEM_RDONLY | XPMEM_RDWR)
    {
        return -EINVAL;
    }

    if permit_type != XPMEM_PERMIT_MODE || has_permit_value != 0 {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub extern "C" fn xpmem_perms_result(
    perm_uid: CInt,
    perm_gid: CInt,
    perm_mode: CULong,
    flag: CInt,
    current_ruid: CInt,
    current_rgid: CInt,
) -> CInt {
    xpmem_perms_inner(
        perm_uid,
        perm_gid,
        perm_mode,
        flag,
        current_ruid,
        current_rgid,
    )
}

#[no_mangle]
pub extern "C" fn xpmem_check_permit_mode_result(
    flags: CInt,
    seg_uid: CInt,
    seg_gid: CInt,
    seg_mode: CULong,
    current_ruid: CInt,
    current_rgid: CInt,
) -> CInt {
    let ret = xpmem_perms_inner(
        seg_uid,
        seg_gid,
        seg_mode,
        XPMEM_PERM_IRUSR,
        current_ruid,
        current_rgid,
    );
    if ret == 0 && (flags & XPMEM_RDWR) != 0 {
        xpmem_perms_inner(
            seg_uid,
            seg_gid,
            seg_mode,
            XPMEM_PERM_IWUSR,
            current_ruid,
            current_rgid,
        )
    } else {
        ret
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_attach_initial_policy_result(
    apid: CLong,
    offset: OffT,
    vaddr: CULong,
    size: SizeT,
    fjmpi_workaround: CInt,
    adjusted_sizep: *mut SizeT,
) -> CInt {
    if apid <= 0 {
        return -EINVAL;
    }

    if offset_in_page(vaddr) != 0 || offset_in_page(offset as CULong) != 0 {
        return -EINVAL;
    }

    let adjusted = if fjmpi_workaround != 0 {
        size & !(PAGE_SIZE as SizeT - 1)
    } else {
        let offset = offset_in_page(size as CULong) as SizeT;
        if offset != 0 {
            size.wrapping_add(PAGE_SIZE as SizeT - offset)
        } else {
            size
        }
    };

    write(adjusted_sizep, adjusted);
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_validate_access_result(
    current_pid: CInt,
    ap_tgid: CInt,
    ap_mode: CInt,
    seg_vaddr: CULong,
    seg_size: SizeT,
    offset: CLong,
    size: SizeT,
    mode: CInt,
    vaddrp: *mut CULong,
) -> CInt {
    if current_pid != ap_tgid || (mode == XPMEM_RDWR && ap_mode == XPMEM_RDONLY) {
        return -EACCES;
    }

    if offset < 0
        || size == 0
        || (offset as CULong).wrapping_add(size as CULong) > seg_size as CULong
    {
        return -EINVAL;
    }

    write(vaddrp, seg_vaddr.wrapping_add(offset as CULong));
    0
}

#[no_mangle]
pub extern "C" fn xpmem_destroying_state_result(flags: CInt, return_destroying: CInt) -> CInt {
    if (flags & XPMEM_FLAG_DESTROYING) != 0 && return_destroying == 0 {
        0
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn xpmem_is_destroying_result(flags: CInt) -> CInt {
    if (flags & XPMEM_FLAG_DESTROYING) != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_destroying_error_result(flags: CInt, error: CInt) -> CInt {
    if (flags & XPMEM_FLAG_DESTROYING) != 0 {
        error
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_two_destroying_error_result(
    first_flags: CInt,
    second_flags: CInt,
    error: CInt,
) -> CInt {
    if ((first_flags | second_flags) & XPMEM_FLAG_DESTROYING) != 0 {
        error
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_three_destroying_error_result(
    first_flags: CInt,
    second_flags: CInt,
    third_flags: CInt,
    error: CInt,
) -> CInt {
    if ((first_flags | second_flags | third_flags) & XPMEM_FLAG_DESTROYING) != 0 {
        error
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_attach_destroying_result(seg_flags: CInt, seg_tg_flags: CInt) -> CInt {
    if ((seg_flags | seg_tg_flags) & XPMEM_FLAG_DESTROYING) != 0 {
        -ENOENT
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_close_decision_result(
    n_opened: CInt,
    has_data: CInt,
    flush_objectsp: *mut CInt,
    exit_partitionp: *mut CInt,
) -> CInt {
    write(flush_objectsp, if has_data != 0 { 1 } else { 0 });
    write(exit_partitionp, if n_opened == 0 { 1 } else { 0 });
    0
}

#[no_mangle]
pub extern "C" fn xpmem_ref_drop_should_free_result(refcnt_after_dec: CInt) -> CInt {
    if refcnt_after_dec == 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_begin_destroy_result(flags: CInt, new_flagsp: *mut CInt) -> CInt {
    if (flags & XPMEM_FLAG_DESTROYING) != 0 {
        write(new_flagsp, flags);
        0
    } else {
        write(new_flagsp, flags | XPMEM_FLAG_DESTROYING);
        1
    }
}

#[no_mangle]
pub extern "C" fn xpmem_finish_destroy_result(flags: CInt) -> CInt {
    flags | XPMEM_FLAG_DESTROYED
}

#[no_mangle]
pub extern "C" fn xpmem_object_lookup_decision_result(
    candidate_id: CLong,
    requested_id: CLong,
    flags: CInt,
    return_destroying: CInt,
    stop_on_destroying: CInt,
) -> CInt {
    if candidate_id != requested_id {
        return XPMEM_LOOKUP_SKIP;
    }

    if (flags & XPMEM_FLAG_DESTROYING) != 0 && return_destroying == 0 {
        if stop_on_destroying != 0 {
            XPMEM_LOOKUP_STOP
        } else {
            XPMEM_LOOKUP_SKIP
        }
    } else {
        XPMEM_LOOKUP_TAKE
    }
}

#[no_mangle]
pub extern "C" fn xpmem_detach_lookup_result(
    has_range: CInt,
    range_start: CULong,
    at_vaddr: CULong,
    has_private_data: CInt,
) -> CInt {
    if has_range == 0 || range_start > at_vaddr {
        return 0;
    }

    if has_private_data == 0 {
        return -EINVAL;
    }

    XPMEM_DETACH_LOOKUP_CONTINUE
}

#[no_mangle]
pub extern "C" fn xpmem_attach_overlap_result(
    current_pid: CInt,
    seg_tgid: CInt,
    requested_vaddr: CULong,
    size: SizeT,
    seg_vaddr: CULong,
) -> CInt {
    if current_pid == seg_tgid
        && requested_vaddr != 0
        && requested_vaddr.wrapping_add(size as CULong) > seg_vaddr
        && requested_vaddr < seg_vaddr.wrapping_add(size as CULong)
    {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_range_step_result(
    range_start: CULong,
    range_end: CULong,
    start: CULong,
    end: CULong,
    range_flags: CULong,
    has_private_data: CInt,
    split_startp: *mut CInt,
    split_endp: *mut CInt,
    ro_freedp: *mut CInt,
    remove_privatep: *mut CInt,
) -> CInt {
    write(split_startp, if range_start < start { 1 } else { 0 });
    write(split_endp, if end < range_end { 1 } else { 0 });
    write(
        ro_freedp,
        if (range_flags & VR_PROT_WRITE) == 0 {
            1
        } else {
            0
        },
    );
    write(remove_privatep, if has_private_data != 0 { 1 } else { 0 });
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_remove_memory_range_action_result(
    vmr_start: CULong,
    vmr_end: CULong,
    att_at_vaddr: CULong,
    att_at_size: SizeT,
    remaining_vaddrp: *mut CULong,
    middle_lookup_vaddrp: *mut CULong,
    full_detachp: *mut CInt,
    needs_middle_lookupp: *mut CInt,
) -> CInt {
    let att_end = att_at_vaddr.wrapping_add(att_at_size as CULong);

    if vmr_start == att_at_vaddr && vmr_end.wrapping_sub(vmr_start) == att_at_size as CULong {
        write(full_detachp, 1);
        write(needs_middle_lookupp, 0);
        write(remaining_vaddrp, 0);
        write(middle_lookup_vaddrp, 0);
        return 0;
    }

    write(full_detachp, 0);
    if vmr_start == att_at_vaddr {
        write(remaining_vaddrp, vmr_end);
        write(middle_lookup_vaddrp, 0);
        write(needs_middle_lookupp, 0);
    } else if vmr_end == att_end {
        write(remaining_vaddrp, att_at_vaddr);
        write(middle_lookup_vaddrp, 0);
        write(needs_middle_lookupp, 0);
    } else {
        write(remaining_vaddrp, att_at_vaddr);
        write(middle_lookup_vaddrp, vmr_end);
        write(needs_middle_lookupp, 1);
    }

    0
}

#[no_mangle]
pub extern "C" fn xpmem_range_private_invalid_result(
    has_range: CInt,
    range_start: CULong,
    vaddr: CULong,
    private_matches: CInt,
) -> CInt {
    if has_range == 0 || range_start > vaddr || private_matches == 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_clear_pte_range_result(
    att_flags: CInt,
    att_vaddr: CULong,
    att_at_vaddr: CULong,
    att_at_size: SizeT,
    start: CULong,
    end: CULong,
    unpin_atp: *mut CULong,
    invalidate_lenp: *mut CULong,
    clear_validp: *mut CInt,
) -> CInt {
    write(unpin_atp, 0);
    write(invalidate_lenp, 0);
    write(clear_validp, 0);

    if (att_flags & XPMEM_FLAG_VALIDPTES) == 0 {
        return 0;
    }

    let att_vaddr_end = att_vaddr.wrapping_add(att_at_size as CULong);
    let invalidate_start = if start > att_vaddr { start } else { att_vaddr };
    let invalidate_end = if end < att_vaddr_end {
        end
    } else {
        att_vaddr_end
    };

    if invalidate_start >= att_vaddr_end || invalidate_end <= att_vaddr {
        return 0;
    }

    let offset_start = invalidate_start.wrapping_sub(att_vaddr);
    let offset_end = invalidate_end.wrapping_sub(att_vaddr);
    let invalidate_len = offset_end.wrapping_sub(offset_start);

    write(unpin_atp, att_at_vaddr.wrapping_add(offset_start));
    write(invalidate_lenp, invalidate_len);
    write(
        clear_validp,
        if offset_start == 0 && att_at_size as CULong == invalidate_len {
            1
        } else {
            0
        },
    );
    1
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_fault_vaddr_result(
    vaddr: CULong,
    att_at_vaddr: CULong,
    att_at_size: SizeT,
    att_vaddr: CULong,
    seg_vaddrp: *mut CULong,
) -> CInt {
    if vaddr < att_at_vaddr
        || vaddr.wrapping_add(1) > att_at_vaddr.wrapping_add(att_at_size as CULong)
    {
        return -EFAULT;
    }

    write(
        seg_vaddrp,
        att_vaddr.wrapping_add(vaddr.wrapping_sub(att_at_vaddr)),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_straight_phys_result(
    seg_vaddr: CULong,
    straight_va: CULong,
    straight_len: SizeT,
    straight_pa: CULong,
    seg_physp: *mut CULong,
    seg_pgsizep: *mut SizeT,
) -> CInt {
    if straight_va != 0
        && seg_vaddr >= straight_va
        && seg_vaddr < straight_va.wrapping_add(straight_len as CULong)
    {
        write(
            seg_physp,
            ((seg_vaddr & PAGE_MASK).wrapping_sub(straight_va)).wrapping_add(straight_pa),
        );
        write(seg_pgsizep, 1usize << 29);
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn xpmem_remote_pte_missing_result(
    has_pte: CInt,
    pte_is_empty: CInt,
    page_in_remote: CInt,
) -> CInt {
    if has_pte == 0 || pte_is_empty != 0 {
        if page_in_remote != 0 {
            -EFAULT
        } else {
            0
        }
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn xpmem_seg_phys_plus_off_result(
    seg_phys: CULong,
    seg_pgsize: SizeT,
    seg_vaddr: CULong,
) -> CULong {
    (seg_phys & !(seg_pgsize as CULong - 1)) | (seg_vaddr & (seg_pgsize as CULong - 1))
}

#[no_mangle]
pub extern "C" fn xpmem_att_page_fits_result(
    att_pgaddr: CULong,
    att_pgsize: SizeT,
    vmr_start: CULong,
    vmr_end: CULong,
    seg_pgsize: SizeT,
) -> CInt {
    if att_pgaddr < vmr_start
        || vmr_end < att_pgaddr.wrapping_add(att_pgsize as CULong)
        || att_pgsize > seg_pgsize
    {
        0
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn xpmem_pte_mismatch_result(att_phys: CULong, seg_phys_aligned: CULong) -> CInt {
    if att_phys != seg_phys_aligned {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn xpmem_unpin_step_result(
    vaddr: CULong,
    vsize: SizeT,
    has_present_pte: CInt,
    next_vaddrp: *mut CULong,
    unpinnedp: *mut CInt,
) -> CInt {
    if has_present_pte != 0 {
        write(next_vaddrp, vaddr.wrapping_add(vsize as CULong));
        write(unpinnedp, 1);
    } else {
        write(
            next_vaddrp,
            (vaddr.wrapping_add(vsize as CULong)) & !(vsize as CULong - 1),
        );
        write(unpinnedp, 0);
    }
    0
}
