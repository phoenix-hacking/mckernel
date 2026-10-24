	if (sig < 33) { // SIGRTMIN - SIGRTMAX
		for (pending = ((typeof(*pending) *)((char *)((head)->next) - offsetof(typeof(*pending), list))); &pending->list != (head); pending = ((typeof(*pending) *)((char *)(pending->list.next) - offsetof(typeof(*pending), list)))) {
			if (pending->sigmask.__val[0] == mask &&
			    pending->ptracecont == ptracecont)
				break;
		}
		if (&pending->list == head)
			pending = NULL;
	}
	if (pending == NULL) {
		doint = 1;
		pending = kmalloc_tracked(sizeof(struct sig_pending), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if (!pending) {
			rc = -ENOMEM;
		}
		else {
			memset(pending, 0, sizeof(struct sig_pending));
			pending->sigmask.__val[0] = mask;
			memcpy(&pending->info, info, sizeof(siginfo_t));
			pending->ptracecont = ptracecont;
			if (sig == SIGKILL || sig == SIGSTOP)
				list_add(&pending->list, head);
			else
				list_add_tail(&pending->list, head);
			tthread->sigevent = 1;
		}
	}

