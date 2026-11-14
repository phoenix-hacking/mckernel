void *mcexec_create_worker_thread_alloc_bridge(void)
{
	return malloc(sizeof(struct thread_data_s));
}

void mcexec_create_worker_thread_alloc_error_bridge(void)
{
	fprintf(stderr, "%s: error: allocating thread structure\n",
		"create_worker_thread");
}

int mcexec_create_worker_thread_next_cpu_bridge(void)
{
	return max_cpuid++;
}

void *mcexec_create_worker_thread_lock_bridge(void)
{
	return &lock;
}

void mcexec_create_worker_thread_publish_bridge(struct thread_data_s *tp,
		struct thread_data_s **tp_out)
{
	tp->next = thread_data;
	thread_data = tp;

	if (tp_out) {
		*tp_out = tp;
	}
}

int mcexec_create_worker_thread_pthread_create_bridge(struct thread_data_s *tp)
{
	return pthread_create(&tp->thread_id, NULL,
			      &main_loop_thread_func, tp);
}

int mcexec_main_loop_thread_barrier_wait_bridge(void *barrier)
{
	return pthread_barrier_wait((pthread_barrier_t *)barrier);
}

void mcexec_init_worker_threads_lock_init_bridge(void)
{
	pthread_mutex_init(&lock, NULL);
}

void mcexec_init_worker_threads_barrier_init_bridge(int count)
{
	pthread_barrier_init(&init_ready, NULL, count);
}

void mcexec_init_worker_threads_reset_cpuid_bridge(void)
{
	max_cpuid = 0;
}

int mcexec_init_worker_threads_create_bridge(void)
{
	return create_worker_thread(NULL, &init_ready);
}

void mcexec_init_worker_threads_wait_bridge(void)
{
	pthread_barrier_wait(&init_ready);
}

void mcexec_init_worker_threads_error_bridge(int ret)
{
	printf("ERROR: creating worker threads (%d), check ulimit?\n", ret);
}

void *mcexec_join_all_threads_head_bridge(void)
{
	return thread_data;
}

void mcexec_join_all_threads_join_bridge(struct thread_data_s *tp)
{
	pthread_join(tp->thread_id, NULL);
}

void *mcexec_kill_thread_head_bridge(void)
{
	return thread_data;
}

int mcexec_kill_thread_pthread_kill_bridge(struct thread_data_s *tp, int sig)
{
	return pthread_kill(tp->thread_id, sig);
}

void mcexec_util_thread_barrier_init_bridge(void)
{
	pthread_barrier_init(&uti_init_ready, NULL, 2);
}

int mcexec_util_thread_create_worker_bridge(struct thread_data_s **tp_out)
{
	return create_worker_thread(tp_out, &uti_init_ready);
}

void mcexec_util_thread_worker_error_bridge(int rc)
{
	printf("%s: Error: create_worker_thread failed (%d)\n",
	       "util_thread", rc);
}

void mcexec_util_thread_barrier_wait_bridge(void)
{
	pthread_barrier_wait(&uti_init_ready);
}
