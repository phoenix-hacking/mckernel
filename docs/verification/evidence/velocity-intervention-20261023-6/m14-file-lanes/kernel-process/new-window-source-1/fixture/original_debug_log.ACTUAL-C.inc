void
debug_log(unsigned long arg)
{
	struct process *p;
	struct thread *t;
	int i;
	struct mcs_rwlock_node_irqsave lock;
	struct resource_set *rset = get_this_cpu_local_var()->resource_set;
	struct process_hash *phash = rset->process_hash;
	struct thread_hash *thash = rset->thread_hash;
	struct process *pid1 = rset->pid1;
	int found = 0;

	switch(arg){
	    case 1:
		for(i = 0; i < HASH_SIZE; i++){
			__mcs_rwlock_reader_lock(&phash->lock[i], &lock);
			for (p = ((typeof(*p) *)((char *)((&phash->list[i])->next) - offsetof(typeof(*p), hash_list))); &p->hash_list != (&phash->list[i]); p = ((typeof(*p) *)((char *)(p->hash_list.next) - offsetof(typeof(*p), hash_list)))){
				if (p == pid1)
					continue;
				found++;
				kprintf("pid=%d ppid=%d status=%d ref=%d\n",
					p->pid, p->ppid_parent->pid, p->status,
					p->refcount.counter);
			}
			__mcs_rwlock_reader_unlock(&phash->lock[i], &lock);
		}
		kprintf("%d processes are found.\n", found);
		break;
	    case 2:
		for(i = 0; i < HASH_SIZE; i++){
			__mcs_rwlock_reader_lock(&thash->lock[i], &lock);
			for (t = ((typeof(*t) *)((char *)((&thash->list[i])->next) - offsetof(typeof(*t), hash_list))); &t->hash_list != (&thash->list[i]); t = ((typeof(*t) *)((char *)(t->hash_list.next) - offsetof(typeof(*t), hash_list)))){
				found++;
				kprintf("cpu=%d pid=%d tid=%d status=%d "
					"offload=%d ref=%d ptrace=%08x\n",
					t->cpu_id, t->proc->pid, t->tid,
					t->status, t->in_syscall_offload,
					t->refcount.counter, t->ptrace);
			}
			__mcs_rwlock_reader_unlock(&thash->lock[i], &lock);
		}
		kprintf("%d threads are found.\n", found);
		break;
	    case 3:
		for(i = 0; i < HASH_SIZE; i++){
			for (p = ((typeof(*p) *)((char *)((&phash->list[i])->next) - offsetof(typeof(*p), hash_list))); &p->hash_list != (&phash->list[i]); p = ((typeof(*p) *)((char *)(p->hash_list.next) - offsetof(typeof(*p), hash_list)))){
				if (p == pid1)
					continue;
				found++;
				kprintf("pid=%d ppid=%d status=%d\n",
				        p->pid, p->ppid_parent->pid, p->status);
			}
		}
		kprintf("%d processes are found.\n", found);
		break;
	    case 4:
		for(i = 0; i < HASH_SIZE; i++){
			for (t = ((typeof(*t) *)((char *)((&thash->list[i])->next) - offsetof(typeof(*t), hash_list))); &t->hash_list != (&thash->list[i]); t = ((typeof(*t) *)((char *)(t->hash_list.next) - offsetof(typeof(*t), hash_list)))){
				found++;
				kprintf("cpu=%d pid=%d tid=%d status=%d\n",
				        t->cpu_id, t->proc->pid, t->tid,
				        t->status);
			}
		}
		kprintf("%d threads are found.\n", found);
		break;
	}
}
