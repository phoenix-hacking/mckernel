		found = 0;
		hash = thread_hash(tid);
		mcs_rwlock_reader_lock_noirq(&thash->lock[hash], &lock);
		for (tthread = ((typeof(*tthread) *)((char *)((&thash->list[hash])->next) - offsetof(typeof(*tthread), hash_list))); &tthread->hash_list != (&thash->list[hash]); tthread = ((typeof(*tthread) *)((char *)(tthread->hash_list.next) - offsetof(typeof(*tthread), hash_list)))){
			if(pid != -1 && tthread->proc->pid != pid){
				continue;
			}
			if (tthread->tid == tid &&
			    tthread->status != PS_EXITED) {
				found = 1;
				break;
			}
		}

		if(!found){
			mcs_rwlock_reader_unlock_noirq(&thash->lock[hash], &lock);
			cpu_restore_interrupt(irqstate);
			return -ESRCH;
		}

		tproc = tthread->proc;
		mcs_rwlock_reader_lock_noirq(&tproc->update_lock, &updatelock);
		savelock = &tthread->sigpendinglock;
		head = &tthread->sigpending;
		mcs_rwlock_reader_lock_noirq(&tproc->threads_lock, &lock);
		if (tthread->status != PS_EXITED &&
			(sig == SIGKILL ||
			 (tproc->status != PS_EXITED && tproc->status != PS_ZOMBIE))) {
			if ((rc = hold_thread(tthread))) {
				kprintf("%s: ERROR hold_thread returned %d,tid=%d\n", __FUNCTION__, rc, tthread->tid);
				tthread = NULL;
			}
		}
		else{
			tthread = NULL;
		}
		mcs_rwlock_reader_unlock_noirq(&tproc->threads_lock, &lock);
		mcs_rwlock_reader_unlock_noirq(&tproc->update_lock, &updatelock);
		mcs_rwlock_reader_unlock_noirq(&thash->lock[hash], &lock);
