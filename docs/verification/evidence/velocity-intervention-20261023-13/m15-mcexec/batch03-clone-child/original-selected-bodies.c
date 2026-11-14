void mcexec_fork_sync_lock_bridge(void)
{
	pthread_mutex_lock(&fork_sync_mutex);
}

void mcexec_fork_sync_unlock_bridge(void)
{
	pthread_mutex_unlock(&fork_sync_mutex);
}

void mcexec_fork_sync_munmap_bridge(void *fs)
{
	munmap(fs, sizeof(struct fork_sync));
}

void mcexec_fork_sync_free_bridge(void *node)
{
	free(node);
}

void *mcexec_clone_alloc_fork_sync_bridge(void)
{
	struct fork_sync *fs;

	fs = mmap(NULL, sizeof(struct fork_sync), PROT_READ | PROT_WRITE,
			MAP_SHARED | MAP_ANONYMOUS, -1, 0);
	if (fs == (void *)-1)
		return NULL;

	memset(fs, '\0', sizeof(struct fork_sync));
	sem_init(&fs->sem, 1, 0);
	return fs;
}

void *mcexec_clone_alloc_container_bridge(void)
{
	struct fork_sync_container *fsc;

	fsc = malloc(sizeof(struct fork_sync_container));
	if (!fsc)
		return NULL;

	memset(fsc, '\0', sizeof(struct fork_sync_container));
	return fsc;
}

int mcexec_clone_fork_bridge(void)
{
	return fork();
}

void mcexec_clone_fork_failed_bridge(void)
{
	fprintf(stderr, "fork(): error forking child process\n");
}

long mcexec_clone_child_bridge(struct syscall_wait_desc *w, void *sync)
{
	struct fork_sync *fs = sync;
	struct fork_sync_container *fp;
	struct fork_sync_container *fb;
	struct rpgtable_desc rpt;
	int ret = 1;

	ischild = 1;
	close(fd);
	fd = opendev();
	if (fd < 0) {
		fs->status = -errno;
		fprintf(stderr, "ERROR: opening %s\n", dev);
		goto fork_child_sync_pipe;
	}

	rpt.start = w->sr.args[1];
	rpt.len = w->sr.args[2];
	rpt.rpgtable = w->sr.args[3];
	if (ioctl(fd, MCEXEC_UP_CREATE_PPD, &rpt)) {
		fs->status = -errno;
		fprintf(stderr, "ERROR: creating PPD %s\n", dev);
		goto fork_child_sync_pipe;
	}

	init_sigaction();
	thread_data = NULL;
	__dprintf("pid(%d): signals and syscall threads OK\n", getpid());

	if ((ret = ioctl(fd, MCEXEC_UP_GET_NUM_POOL_THREADS)) < 0) {
		fprintf(stderr, "Error: obtaining thread pool count\n");
	}

	if (ret == 1) {
		n_threads = 4;
	}

	if ((ret = init_worker_threads(fd)) != 0) {
		fprintf(stderr, "%s: Error: creating worker threads: %s\n",
			__func__, strerror(-ret));
		close(fd);
		exit(1);
	}

fork_child_sync_pipe:
	for (fp = fork_sync_top; fp;) {
		fb = fp->next;
		if (fp->fs && fp->fs != fs) {
			munmap(fp->fs, sizeof(struct fork_sync));
		}
		free(fp);
		fp = fb;
	}
	fork_sync_top = NULL;

	sem_post(&fs->sem);
	if (fs->status) {
		exit(1);
	}

	pthread_mutex_init(&fork_sync_mutex, NULL);

	while (getppid() != 1 && fs->success == 0) {
		sched_yield();
	}

	if (fs->success == 0) {
		exit(1);
	}

	sem_destroy(&fs->sem);
	munmap(fs, sizeof(struct fork_sync));
	join_all_threads();
	return ret;
}

int mcexec_clone_sem_trywait_bridge(void *fs)
{
	return sem_trywait(&((struct fork_sync *)fs)->sem);
}

int mcexec_clone_waitpid_nohang_bridge(int pid)
{
	int st;

	return waitpid(pid, &st, WNOHANG);
}

void mcexec_clone_sched_yield_bridge(void)
{
	sched_yield();
}

void mcexec_clone_child_after_fork_failed_bridge(void)
{
	fprintf(stderr, "fork(): error with child process after fork\n");
}

void mcexec_clone_sem_destroy_bridge(void *fs)
{
	sem_destroy(&((struct fork_sync *)fs)->sem);
}
