
int do_process_vm_read_writev(int pid, 
		const struct iovec *local_iov,
		unsigned long liovcnt,
		const struct iovec *remote_iov,
		unsigned long riovcnt,
		unsigned long flags,
		int op)
{
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
	struct mcs_rwlock_node_irqsave lock;
	struct mcs_rwlock_node update_lock;

	return arch_process_vm_read_writev_body_result(pid, local_iov,
			liovcnt, remote_iov, riovcnt, flags, op,
			get_this_cpu_local_var()->current, &lock, &update_lock,
			&arch_process_vm_rw_kernel_offsets,
			arch_process_vm_rw_read_lock_bridge,
			arch_process_vm_rw_read_unlock_bridge,
			arch_process_vm_rw_lookup_range_bridge,
			arch_process_vm_rw_find_process_bridge,
			arch_process_vm_rw_process_unlock_bridge,
			arch_process_vm_rw_update_lock_bridge,
			arch_process_vm_rw_update_unlock_bridge,
			arch_process_vm_rw_hold_vm_bridge,
			arch_process_vm_rw_release_vm_bridge,
			arch_process_vm_rw_vtop_bridge,
			arch_process_vm_rw_page_fault_bridge,
			arch_process_vm_rw_phys_to_virt_bridge,
			arch_process_vm_rw_memcpy_bridge,
			arch_process_vm_rw_log_bridge);
#else
	int ret = -EINVAL;	
	int li, ri;
	int pli, pri;
	off_t loff, roff;
	size_t llen = 0, rlen = 0;
	size_t copied = 0;
	size_t to_copy;
	struct thread *lthread = get_this_cpu_local_var()->current;
	struct process *rproc;
	struct process *lproc = lthread->proc;
	struct process_vm *rvm = NULL;
	unsigned long rphys;
	unsigned long rpage_left;
	unsigned long psize;
	void *rva;
	struct vm_range *range;
	struct mcs_rwlock_node_irqsave lock;
	struct mcs_rwlock_node update_lock;

	/* Sanity checks */
	if (flags) {
		return -EINVAL;
	}
	
	if (liovcnt > IOV_MAX || riovcnt > IOV_MAX) {
		return -EINVAL;
	}

	/* Check if parameters are okay */
	ihk_rwspinlock_read_lock_noirq(&lthread->vm->memory_range_lock);

	range = lookup_process_memory_range(lthread->vm, 
			(uintptr_t)local_iov, 
			(uintptr_t)(local_iov + liovcnt));

	if (!range) {
		ret = -EFAULT; 
		goto arg_out;
	}

	range = lookup_process_memory_range(lthread->vm, 
			(uintptr_t)remote_iov, 
			(uintptr_t)(remote_iov + riovcnt));

	if (!range) {
		ret = -EFAULT; 
		goto arg_out;
	}

	ret = 0;
arg_out:
	ihk_rwspinlock_read_unlock_noirq(&lthread->vm->memory_range_lock);

	if (ret != 0) {
		goto out;
	}

	for (li = 0; li < liovcnt; ++li) {
		llen += local_iov[li].iov_len;
		dkprintf("local_iov[%d].iov_base: 0x%lx, len: %lu\n",
			li, local_iov[li].iov_base, local_iov[li].iov_len);
	}

	for (ri = 0; ri < riovcnt; ++ri) {
		rlen += remote_iov[ri].iov_len;
		dkprintf("remote_iov[%d].iov_base: 0x%lx, len: %lu\n",
			ri, remote_iov[ri].iov_base, remote_iov[ri].iov_len);
	}

	if (llen != rlen) {
		return -EINVAL;
	}
	
	/* Find remote process */
	rproc = find_process(pid, &lock);
	if (!rproc) {
		ret = -ESRCH;
		goto out;
	}

	mcs_rwlock_reader_lock_noirq(&rproc->update_lock, &update_lock);
	if(rproc->status == PS_EXITED ||
	   rproc->status == PS_ZOMBIE){
		mcs_rwlock_reader_unlock_noirq(&rproc->update_lock, &update_lock);
		process_unlock(rproc, &lock);
		ret = -ESRCH;
		goto out;
	}
	rvm = rproc->vm;
	hold_process_vm(rvm);
	mcs_rwlock_reader_unlock_noirq(&rproc->update_lock, &update_lock);
	process_unlock(rproc, &lock);

	if (lproc->euid != 0 &&
	    (lproc->ruid != rproc->ruid ||
	     lproc->ruid != rproc->euid ||
	     lproc->ruid != rproc->suid ||
	     lproc->rgid != rproc->rgid ||
	     lproc->rgid != rproc->egid ||
	     lproc->rgid != rproc->sgid)) {
		ret = -EPERM;
		goto out;
	}

	dkprintf("pid %d found, doing %s: liovcnt: %d, riovcnt: %d \n", pid,
		(op == PROCESS_VM_READ) ? "PROCESS_VM_READ" : "PROCESS_VM_WRITE",
		liovcnt, riovcnt);

	pli = pri = -1; /* Previous indeces in iovecs */
	li = ri = 0; /* Current indeces in iovecs */
	loff = roff = 0; /* Offsets in current iovec */

	/* Now iterate and do the copy */
	while (copied < llen) {
		int faulted = 0;

		/* New local vector? */
		if (pli != li) {
			struct vm_range *range;

			ihk_rwspinlock_read_lock_noirq(&lthread->vm->memory_range_lock);

			/* Is base valid? */
			range = lookup_process_memory_range(lthread->vm,
					(uintptr_t)local_iov[li].iov_base,
					(uintptr_t)(local_iov[li].iov_base + 1));

			if (!range) {
				ret = -EFAULT;
				goto pli_out;
			}

			/* Is range valid? */
			range = lookup_process_memory_range(lthread->vm,
					(uintptr_t)local_iov[li].iov_base,
					(uintptr_t)(local_iov[li].iov_base + local_iov[li].iov_len));

			if (range == NULL) {
				ret = -EINVAL;
				goto pli_out;
			}

			if (!(range->flag & ((op == PROCESS_VM_READ) ?
				VR_PROT_WRITE : VR_PROT_READ))) {
				ret = -EFAULT;
				goto pli_out;
			}

			ret = 0;
pli_out:
			ihk_rwspinlock_read_unlock_noirq(&lthread->vm->memory_range_lock);

			if (ret != 0) {
				goto out;
			}

			pli = li;
		}

		/* New remote vector? */
		if (pri != ri) {
			struct vm_range *range;

			ihk_rwspinlock_read_lock_noirq(&rvm->memory_range_lock);

			/* Is base valid? */
			range = lookup_process_memory_range(rvm,
					(uintptr_t)remote_iov[li].iov_base,
					(uintptr_t)(remote_iov[li].iov_base + 1));

			if (range == NULL) {
				ret = -EFAULT;
				goto pri_out;
			}

			/* Is range valid? */
			range = lookup_process_memory_range(rvm,
					(uintptr_t)remote_iov[li].iov_base,
					(uintptr_t)(remote_iov[li].iov_base + remote_iov[li].iov_len));

			if (range == NULL) {
				ret = -EINVAL;
				goto pri_out;
			}

			if (!(range->flag & ((op == PROCESS_VM_READ) ?
				VR_PROT_READ : VR_PROT_WRITE))) {
				ret = -EFAULT;
				goto pri_out;
			}

			ret = 0;
pri_out:
			ihk_rwspinlock_read_unlock_noirq(&rvm->memory_range_lock);

			if (ret != 0) {
				goto out;
			}

			pri = ri;
		}

		/* Figure out how much we can copy at most in this iteration */
		to_copy = (local_iov[li].iov_len - loff);	
		if ((remote_iov[ri].iov_len - roff) < to_copy) {
			to_copy = remote_iov[ri].iov_len - roff;
		}

retry_lookup:
		/* TODO: remember page and do this only if necessary */
		ret = ihk_mc_pt_virt_to_phys_size(rvm->address_space->page_table,
				remote_iov[ri].iov_base + roff, &rphys, &psize);

		if (ret) {
			uint64_t reason = PF_POPULATE | PF_WRITE | PF_USER;
			void *addr;

			if (faulted) {
				ret = -EFAULT;
				goto out;
			}

			/* Fault in pages */
			for (addr = (void *)
					(((unsigned long)remote_iov[ri].iov_base + roff)
					& PAGE_MASK);
					addr < (remote_iov[ri].iov_base + roff + to_copy);
					addr += PAGE_SIZE) {

				ret = page_fault_process_vm(rvm, addr, reason);
				if (ret) {
					ret = -EFAULT;
					goto out;
				}
			}

			faulted = 1;
			goto retry_lookup;
		}

		rpage_left = ((((unsigned long)remote_iov[ri].iov_base + roff +
			psize) & ~(psize - 1)) -
			((unsigned long)remote_iov[ri].iov_base + roff));
		if (rpage_left < to_copy) {
			to_copy = rpage_left;
		}

		rva = phys_to_virt(rphys);

		fast_memcpy(
				(op == PROCESS_VM_READ) ? local_iov[li].iov_base + loff : rva,
				(op == PROCESS_VM_READ) ? rva : local_iov[li].iov_base + loff,
				to_copy);

		copied += to_copy;
		dkprintf("local_iov[%d]: 0x%lx %s remote_iov[%d]: 0x%lx, %lu copied, psize: %lu, rpage_left: %lu\n",
			li, local_iov[li].iov_base + loff, 
			(op == PROCESS_VM_READ) ? "<-" : "->", 
			ri, remote_iov[ri].iov_base + roff, to_copy,
			psize, rpage_left);

		loff += to_copy;
		roff += to_copy;

		if (loff == local_iov[li].iov_len) {
			li++;
			loff = 0;
		}

		if (roff == remote_iov[ri].iov_len) {
			ri++;
			roff = 0;
		}
	}

	release_process_vm(rvm);

	return copied;

out:
	if(rvm)
		release_process_vm(rvm);
	return ret;
#endif
}
