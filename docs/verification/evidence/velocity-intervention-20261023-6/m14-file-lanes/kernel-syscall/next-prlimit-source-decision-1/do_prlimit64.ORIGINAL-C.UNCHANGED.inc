static int do_prlimit64(int pid, int resource, struct rlimit *_new_limit,
			struct rlimit *old_limit)
{
	struct rlimit new_limit;
	int mcresource;
	struct process *proc;
	struct resource_set *rset = get_this_cpu_local_var()->resource_set;
	int hash;
	struct process_hash *phash = rset->process_hash;
	struct mcs_rwlock_node exist_lock;
	struct mcs_rwlock_node update_lock;
	unsigned long irqstate;
	int found;
	int ret;
	ihk_mc_user_context_t ctx;

	ret = prlimit_validate_resource(resource);
	if (ret) {
		return ret;
	}

	if (_new_limit) {
		if (copy_from_user(&new_limit, _new_limit,
				   sizeof(struct rlimit))) {
			return -EFAULT;
		}

		ret = prlimit_validate_new_limit(new_limit.rlim_cur,
						 new_limit.rlim_max);
		if (ret) {
			return ret;
		}

		/* update Linux side value as well */
		if (prlimit_linux_update_needed(resource)) {
			ihk_mc_syscall_set_arg0(&ctx, pid);
			ihk_mc_syscall_set_arg1(&ctx, resource);
			ihk_mc_syscall_set_arg2(&ctx, (unsigned long)_new_limit);
			ihk_mc_syscall_set_arg3(&ctx, (unsigned long)old_limit);
			ret = syscall_generic_forwarding(__NR_prlimit64, &ctx);
			if (ret < 0)
				return ret;
		}
	}

	/* translate resource */
	mcresource = prlimit_to_mckernel_resource(resource);
	if (mcresource < 0) {
		ihk_mc_syscall_set_arg0(&ctx, pid);
		ihk_mc_syscall_set_arg1(&ctx, resource);
		ihk_mc_syscall_set_arg2(&ctx, (unsigned long)_new_limit);
		ihk_mc_syscall_set_arg3(&ctx, (unsigned long)old_limit);
		return syscall_generic_forwarding(__NR_prlimit64, &ctx);
	}

	/* find process */
	found = 0;

	if (pid == 0) {
		struct thread *thread = get_this_cpu_local_var()->current;

		pid = thread->proc->pid;
	}

	irqstate = cpu_disable_interrupt_save();
	hash = process_hash(pid);
	mcs_rwlock_reader_lock_noirq(&phash->lock[hash], &exist_lock);

	for (proc = ((typeof(*proc) *)((char *)((&phash->list[hash])->next) - offsetof(typeof(*proc), hash_list))); &proc->hash_list != (&phash->list[hash]); proc = ((typeof(*proc) *)((char *)(proc->hash_list.next) - offsetof(typeof(*proc), hash_list)))) {
		if (proc->pid == pid) {
			found = 1;
			break;
		}
	}

	if (!found) {
		mcs_rwlock_reader_unlock_noirq(&phash->lock[hash], &exist_lock);
		cpu_restore_interrupt(irqstate);
		return -ESRCH;
	}

	if (_new_limit) {
		mcs_rwlock_writer_lock_noirq(&proc->update_lock, &update_lock);
	} else {
		mcs_rwlock_reader_lock_noirq(&proc->update_lock, &update_lock);
	}

	if (old_limit) {
		if (copy_to_user(old_limit, proc->rlimit + mcresource,
				 sizeof(struct rlimit))) {
			ret = -EFAULT;
			goto out;
		}
	}

	if (_new_limit) {
		memcpy(proc->rlimit + mcresource, &new_limit,
		       sizeof(struct rlimit));
	}

	ret = 0;
 out:
	if (_new_limit) {
		mcs_rwlock_writer_unlock_noirq(&proc->update_lock,
					       &update_lock);
	} else {
		mcs_rwlock_reader_unlock_noirq(&proc->update_lock,
					       &update_lock);
	}

	mcs_rwlock_reader_unlock_noirq(&phash->lock[hash], &exist_lock);
	cpu_restore_interrupt(irqstate);

	return ret;
}
