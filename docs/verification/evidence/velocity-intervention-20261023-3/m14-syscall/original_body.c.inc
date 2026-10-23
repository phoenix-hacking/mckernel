long
syscall_signalfd_publish_bridge(void *threadp, int fd,
		const unsigned long *maskp, int create)
{
	struct thread *thread = threadp;
	struct process *proc = thread->proc;
	struct mckfd *sfd;
	long irqstate;

	if (create) {
		sfd = kmalloc_tracked(sizeof(struct mckfd), IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
		if (!sfd)
			return -ENOMEM;
		memset(sfd, '\0', sizeof(struct mckfd));
		sfd->fd = fd;
		irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
		sfd->next = proc->mckfd;
		proc->mckfd = sfd;
	} else {
		irqstate = ihk_mc_spinlock_lock(&proc->mckfd_lock);
		for (sfd = proc->mckfd; sfd; sfd = sfd->next) {
			if (sfd->fd == fd)
				break;
		}
		if (!sfd) {
			ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
			return -EINVAL;
		}
	}

	memcpy(&sfd->data, maskp, sizeof(*maskp));
	ihk_mc_spinlock_unlock(&proc->mckfd_lock, irqstate);
	return sfd->fd;
}
