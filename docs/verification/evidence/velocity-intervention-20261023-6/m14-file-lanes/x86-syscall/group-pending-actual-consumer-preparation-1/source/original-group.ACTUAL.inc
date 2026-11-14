	if(tid == -1 && pid <= 0){
		struct process *p;
		struct mcs_rwlock_node_irqsave slock;
		int	pgid = -pid;
		int	rc = -ESRCH;
		int	*pids = NULL;
		int	n = 0, nr_pids = 0;
		int	sendme = 0;

		if(pid == 0){
			if(thread == NULL || thread->proc->pid <= 0)
				return -ESRCH;
			pgid = thread->proc->pgid;
		}

		// Count nr of pids
		for(i = 0; i < HASH_SIZE; i++){
			mcs_rwlock_reader_lock(&phash->lock[i], &slock);
			for (p = ((typeof(*p) *)((char *)((&phash->list[i])->next) - offsetof(typeof(*p), hash_list))); &p->hash_list != (&phash->list[i]); p = ((typeof(*p) *)((char *)(p->hash_list.next) - offsetof(typeof(*p), hash_list)))){
				if(pgid != 1 && p->pgid != pgid)
					continue;

				if(thread && p->pid == thread->proc->pid){
					sendme = 1;
					continue;
				}

				++nr_pids;
			}
			mcs_rwlock_reader_unlock(&phash->lock[i], &slock);
		}

		if (nr_pids) {
			pids = kmalloc_tracked(sizeof(int) * nr_pids, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
			if(!pids)
				return -ENOMEM;
		}
		else {
			if (sendme) {
				goto sendme;
			}
			return rc;
		}

		// Collect pids and do the kill
		for(i = 0; i < HASH_SIZE; i++){
			if (n == nr_pids) {
				break;
			}
			mcs_rwlock_reader_lock(&phash->lock[i], &slock);
			for (p = ((typeof(*p) *)((char *)((&phash->list[i])->next) - offsetof(typeof(*p), hash_list))); &p->hash_list != (&phash->list[i]); p = ((typeof(*p) *)((char *)(p->hash_list.next) - offsetof(typeof(*p), hash_list)))){
				if(pgid != 1 && p->pgid != pgid)
					continue;

				if(thread && p->pid == thread->proc->pid){
					sendme = 1;
					continue;
				}

				pids[n] = p->pid;
				n++;
				if (n == nr_pids) {
					break;
				}
			}
			mcs_rwlock_reader_unlock(&phash->lock[i], &slock);
		}
		for(i = 0; i < n; i++)
			rc = do_kill(thread, pids[i], -1, sig, info, ptracecont);
sendme:
		if(sendme)
			rc = do_kill(thread, thread->proc->pid, -1, sig, info, ptracecont);

		kfree_tracked(pids, __FILE__, __LINE__);
		return rc;
	}
