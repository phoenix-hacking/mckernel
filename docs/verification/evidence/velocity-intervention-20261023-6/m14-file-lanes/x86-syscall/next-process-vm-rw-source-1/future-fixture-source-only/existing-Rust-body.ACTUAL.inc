#[no_mangle]
pub unsafe extern "C" fn arch_process_vm_read_writev_body_result(
    pid: CInt,
    local_iov: *const Iovec,
    liovcnt: CULong,
    remote_iov: *const Iovec,
    riovcnt: CULong,
    flags: CULong,
    op: CInt,
    lthread: *mut c_void,
    find_lock_node: *mut c_void,
    update_lock_node: *mut c_void,
    offsets: *const ArchProcessVmRwOffsets,
    vm_read_lock_fn: Option<ArchProcessVmRwLockFn>,
    vm_read_unlock_fn: Option<ArchProcessVmRwLockFn>,
    lookup_range_fn: Option<ArchProcessVmRwLookupRangeFn>,
    find_process_fn: Option<ArchProcessVmRwFindProcessFn>,
    process_unlock_fn: Option<ArchProcessVmRwProcessUnlockFn>,
    update_lock_fn: Option<ArchProcessVmRwProcessLockFn>,
    update_unlock_fn: Option<ArchProcessVmRwProcessLockFn>,
    hold_vm_fn: Option<ArchProcessVmRwVmVoidFn>,
    release_vm_fn: Option<ArchProcessVmRwVmVoidFn>,
    vtop_fn: Option<ArchProcessVmRwVtopFn>,
    page_fault_fn: Option<ArchProcessVmRwFaultFn>,
    phys_to_virt_fn: Option<ArchProcessVmRwPhysToVirtFn>,
    memcpy_fn: Option<ArchProcessVmRwMemcpyFn>,
    log_fn: Option<ArchProcessVmRwLogFn>,
) -> CInt {
    let error = process_vm_validate_args(flags, liovcnt, riovcnt);
    if error != 0 {
        return error;
    }

    if lthread.is_null()
        || find_lock_node.is_null()
        || update_lock_node.is_null()
        || offsets.is_null()
    {
        return -EFAULT;
    }

    let Some(vm_read_lock) = vm_read_lock_fn else {
        return -EFAULT;
    };
    let Some(vm_read_unlock) = vm_read_unlock_fn else {
        return -EFAULT;
    };
    let Some(lookup_range) = lookup_range_fn else {
        return -EFAULT;
    };
    let Some(find_process) = find_process_fn else {
        return -EFAULT;
    };
    let Some(process_unlock) = process_unlock_fn else {
        return -EFAULT;
    };
    let Some(update_lock) = update_lock_fn else {
        return -EFAULT;
    };
    let Some(update_unlock) = update_unlock_fn else {
        return -EFAULT;
    };
    let Some(hold_vm) = hold_vm_fn else {
        return -EFAULT;
    };
    let Some(release_vm) = release_vm_fn else {
        return -EFAULT;
    };
    let Some(vtop) = vtop_fn else {
        return -EFAULT;
    };
    let Some(page_fault) = page_fault_fn else {
        return -EFAULT;
    };
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return -EFAULT;
    };
    let Some(memcpy) = memcpy_fn else {
        return -EFAULT;
    };

    let offsets = &*offsets;
    let lproc = process_vm_read_ptr(lthread, offsets.thread_proc_offset);
    let lvm = process_vm_read_ptr(lthread, offsets.thread_vm_offset);
    if lproc.is_null() || lvm.is_null() {
        return -EFAULT;
    }

    vm_read_lock(lvm);
    let mut ret = 0;
    let mut range = lookup_range(
        lvm,
        local_iov as CULong,
        process_vm_iov_end(local_iov, liovcnt),
    );
    if range.is_null() {
        ret = -EFAULT;
    } else {
        range = lookup_range(
            lvm,
            remote_iov as CULong,
            process_vm_iov_end(remote_iov, riovcnt),
        );
        if range.is_null() {
            ret = -EFAULT;
        }
    }
    vm_read_unlock(lvm);
    if ret != 0 {
        return ret;
    }

    let mut llen: SizeT = 0;
    let mut rlen: SizeT = 0;
    for li in 0..(liovcnt as usize) {
        let base = process_vm_iov_base(local_iov, li);
        let len = process_vm_iov_len(local_iov, li);
        llen = llen.wrapping_add(len);
        process_vm_log_iov(log_fn, 1, li as CInt, base, len as CULong);
    }

    for ri in 0..(riovcnt as usize) {
        let base = process_vm_iov_base(remote_iov, ri);
        let len = process_vm_iov_len(remote_iov, ri);
        rlen = rlen.wrapping_add(len);
        process_vm_log_iov(log_fn, 2, ri as CInt, base, len as CULong);
    }

    if llen != rlen {
        return -EINVAL;
    }

    let rproc = find_process(pid, find_lock_node);
    if rproc.is_null() {
        return -ESRCH;
    }

    update_lock(rproc, update_lock_node);
    let rproc_status = process_vm_read_i32(rproc, offsets.proc_status_offset);
    if rproc_status == PS_EXITED || rproc_status == PS_ZOMBIE {
        update_unlock(rproc, update_lock_node);
        process_unlock(rproc, find_lock_node);
        return -ESRCH;
    }
    let rvm = process_vm_read_ptr(rproc, offsets.proc_vm_offset);
    if rvm.is_null() {
        update_unlock(rproc, update_lock_node);
        process_unlock(rproc, find_lock_node);
        return -EFAULT;
    }
    hold_vm(rvm);
    update_unlock(rproc, update_lock_node);
    process_unlock(rproc, find_lock_node);

    let lproc_euid = process_vm_read_i32(lproc, offsets.proc_euid_offset);
    let lproc_ruid = process_vm_read_i32(lproc, offsets.proc_ruid_offset);
    let lproc_rgid = process_vm_read_i32(lproc, offsets.proc_rgid_offset);
    if lproc_euid != 0
        && (lproc_ruid != process_vm_read_i32(rproc, offsets.proc_ruid_offset)
            || lproc_ruid != process_vm_read_i32(rproc, offsets.proc_euid_offset)
            || lproc_ruid != process_vm_read_i32(rproc, offsets.proc_suid_offset)
            || lproc_rgid != process_vm_read_i32(rproc, offsets.proc_rgid_offset)
            || lproc_rgid != process_vm_read_i32(rproc, offsets.proc_egid_offset)
            || lproc_rgid != process_vm_read_i32(rproc, offsets.proc_sgid_offset))
    {
        release_vm(rvm);
        return -EPERM;
    }

    process_vm_log_found(log_fn, pid, op, liovcnt, riovcnt);

    let mut pli = usize::MAX;
    let mut pri = usize::MAX;
    let mut li = 0usize;
    let mut ri = 0usize;
    let mut loff: SizeT = 0;
    let mut roff: SizeT = 0;
    let mut copied: SizeT = 0;

    while copied < llen {
        let mut faulted = false;

        if pli != li {
            vm_read_lock(lvm);
            let local_base = process_vm_iov_base(local_iov, li);
            let local_len = process_vm_iov_len(local_iov, li);
            range = lookup_range(lvm, local_base, local_base.wrapping_add(1));
            if range.is_null() {
                ret = -EFAULT;
            } else {
                range = lookup_range(
                    lvm,
                    local_base,
                    local_base.wrapping_add(local_len as CULong),
                );
                if range.is_null() {
                    ret = -EINVAL;
                } else {
                    let range_flag = read_volatile(process_vm_field_ptr::<CULong>(
                        range,
                        offsets.vm_range_flag_offset,
                    ));
                    let required = if op == PROCESS_VM_READ {
                        VR_PROT_WRITE
                    } else {
                        VR_PROT_READ
                    };
                    ret = if (range_flag & required) == 0 {
                        -EFAULT
                    } else {
                        0
                    };
                }
            }
            vm_read_unlock(lvm);
            if ret != 0 {
                break;
            }
            pli = li;
        }

        if pri != ri {
            vm_read_lock(rvm);
            let remote_check_index = li;
            let remote_base = process_vm_iov_base(remote_iov, remote_check_index);
            let remote_len = process_vm_iov_len(remote_iov, remote_check_index);
            range = lookup_range(rvm, remote_base, remote_base.wrapping_add(1));
            if range.is_null() {
                ret = -EFAULT;
            } else {
                range = lookup_range(
                    rvm,
                    remote_base,
                    remote_base.wrapping_add(remote_len as CULong),
                );
                if range.is_null() {
                    ret = -EINVAL;
                } else {
                    let range_flag = read_volatile(process_vm_field_ptr::<CULong>(
                        range,
                        offsets.vm_range_flag_offset,
                    ));
                    let required = if op == PROCESS_VM_READ {
                        VR_PROT_READ
                    } else {
                        VR_PROT_WRITE
                    };
                    ret = if (range_flag & required) == 0 {
                        -EFAULT
                    } else {
                        0
                    };
                }
            }
            vm_read_unlock(rvm);
            if ret != 0 {
                break;
            }
            pri = ri;
        }

        let local_base = process_vm_iov_base(local_iov, li);
        let local_len = process_vm_iov_len(local_iov, li);
        let remote_base = process_vm_iov_base(remote_iov, ri);
        let remote_len = process_vm_iov_len(remote_iov, ri);
        let mut to_copy = local_len.wrapping_sub(loff);
        let remote_left = remote_len.wrapping_sub(roff);
        if remote_left < to_copy {
            to_copy = remote_left;
        }

        let mut rphys: CULong = 0;
        let mut psize: CULong = 0;
        let remote_addr = remote_base.wrapping_add(roff as CULong);
        loop {
            let aspace = process_vm_read_ptr(rvm, offsets.process_vm_address_space_offset);
            let page_table = if aspace.is_null() {
                null_mut()
            } else {
                process_vm_read_ptr(aspace, offsets.address_space_page_table_offset)
            };
            ret = vtop(page_table, remote_addr, &mut rphys, &mut psize);
            if ret == 0 {
                break;
            }

            if faulted {
                ret = -EFAULT;
                break;
            }

            let mut addr = remote_addr & PAGE_MASK;
            let fault_end = remote_addr.wrapping_add(to_copy as CULong);
            while addr < fault_end {
                ret = page_fault(rvm, addr, PF_POPULATE | PF_WRITE | PF_USER);
                if ret != 0 {
                    ret = -EFAULT;
                    break;
                }
                addr = addr.wrapping_add(PAGE_SIZE);
            }
            if ret != 0 {
                break;
            }

            faulted = true;
        }
        if ret != 0 {
            break;
        }

        let rpage_left =
            ((remote_addr.wrapping_add(psize)) & !(psize - 1)).wrapping_sub(remote_addr);
        if rpage_left < to_copy as CULong {
            to_copy = rpage_left as SizeT;
        }

        let rva = phys_to_virt(rphys);
        let local_addr = local_base.wrapping_add(loff as CULong);
        if op == PROCESS_VM_READ {
            memcpy(local_addr as *mut c_void, rva as *const c_void, to_copy);
        } else {
            memcpy(rva, local_addr as *const c_void, to_copy);
        }

        copied = copied.wrapping_add(to_copy);
        process_vm_log_copy(
            log_fn,
            li as CInt,
            ri as CInt,
            op,
            local_addr,
            remote_addr,
            to_copy as CULong,
            psize,
            rpage_left,
        );

        loff = loff.wrapping_add(to_copy);
        roff = roff.wrapping_add(to_copy);

        if loff == local_len {
            li = li.wrapping_add(1);
            loff = 0;
        }

        if roff == remote_len {
            ri = ri.wrapping_add(1);
            roff = 0;
        }
    }

    if ret == 0 {
        release_vm(rvm);
        return copied as CInt;
    }

    release_vm(rvm);
    ret
}
