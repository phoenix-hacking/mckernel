int mcexec_numa_node_cpu_isset_bridge(int node, int cpu)
{
	return CPU_ISSET_S(cpu, cpu_set_size, numa_node_set(node));
}

int mcexec_main_get_cpu_bridge(void)
{
	return ioctl(fd, MCEXEC_UP_GET_CPU, 0);
}

int mcexec_main_get_nodes_bridge(void)
{
	return ioctl(fd, MCEXEC_UP_GET_NODES, 0);
}

void mcexec_main_no_cpu_bridge(void)
{
	fprintf(stderr, "No CPU found.\n");
}

void mcexec_main_no_numa_node_bridge(void)
{
	fprintf(stderr, "No numa node found.\n");
}

void mcexec_main_alloc_nodes_error_bridge(void)
{
	fprintf(stderr, "Error allocating nodes cpu sets\n");
}

size_t mcexec_main_cpu_alloc_size_bridge(int cpu_count)
{
	return CPU_ALLOC_SIZE(cpu_count);
}

void mcexec_main_publish_topology_bridge(int cpu_count, int node_count,
		size_t node_set_size, void *nodes)
{
	ncpu = cpu_count;
	nnodes = node_count;
	cpu_set_size = node_set_size;
	numa_nodes = nodes;
}

void mcexec_main_numa_node_zero_bridge(void *nodes, size_t node_set_size,
		int node_id)
{
	CPU_ZERO_S(node_set_size,
			(cpu_set_t *)((char *)nodes + node_id * node_set_size));
}

int mcexec_main_node_cpu_exists_bridge(int node_id, int cpu)
{
	struct stat sb;
	char buf[PATH_MAX];

	snprintf(buf, PATH_MAX,
			"/sys/class/mcos/mcos0/sys/devices/system/node/node%d/cpu%d",
			node_id, cpu);
	return stat(buf, &sb) == 0;
}

void mcexec_main_numa_node_set_cpu_bridge(void *nodes, size_t node_set_size,
		int node_id, int cpu)
{
	CPU_SET_S(cpu, node_set_size,
			(cpu_set_t *)((char *)nodes + node_id * node_set_size));
}

int mcexec_overlay_cpu_in_node_bridge(int cpu, int node)
{
	if (node < 0 || node >= nnodes || cpu < 0 || cpu >= ncpu)
		return 0;

	return CPU_ISSET_S(cpu, cpu_set_size, numa_node_set(node));
}

int mcexec_partition_get_cpuset_bridge(struct program_load_desc *desc,
		int nr_processes, int *target_core, int *process_rank,
		int *mcexec_linux_numa, int *ikc_mapped)
{
	struct get_cpu_set_arg cpu_set_arg;

	CPU_ZERO(&mcexec_partition_cpu_set_storage);

	cpu_set_arg.req_cpu_list = NULL;
	cpu_set_arg.req_cpu_list_len = 0;
	cpu_set_arg.cpu_set = (void *)&desc->cpu_set;
	cpu_set_arg.cpu_set_size = sizeof(desc->cpu_set);
	cpu_set_arg.nr_processes = nr_processes;
	cpu_set_arg.ppid = getppid();
	cpu_set_arg.target_core = target_core;
	cpu_set_arg.process_rank = process_rank;
	cpu_set_arg.mcexec_linux_numa = mcexec_linux_numa;
	cpu_set_arg.mcexec_cpu_set = &mcexec_partition_cpu_set_storage;
	cpu_set_arg.mcexec_cpu_set_size =
		sizeof(mcexec_partition_cpu_set_storage);
	cpu_set_arg.ikc_mapped = ikc_mapped;

	/* Fugaku specific: Fujitsu CPU binding */
	if (getenv("FLIB_AFFINITY_ON_PROCESS")) {
		cpu_set_arg.req_cpu_list =
			getenv("FLIB_AFFINITY_ON_PROCESS");
		cpu_set_arg.req_cpu_list_len =
			strlen(cpu_set_arg.req_cpu_list) + 1;
		__dprintf("%s: requesting CPUs: %s\n",
			"main", cpu_set_arg.req_cpu_list);
	}

	return ioctl(fd, MCEXEC_UP_GET_CPUSET, (void *)&cpu_set_arg);
}

void mcexec_partition_get_cpuset_failed_bridge(void)
{
	perror("getting CPU set for partitioned execution");
	close(fd);
}

int mcexec_partition_sched_setaffinity_bridge(void)
{
	return sched_setaffinity(0, sizeof(mcexec_partition_cpu_set_storage),
			&mcexec_partition_cpu_set_storage);
}

int mcexec_partition_numa_run_bridge(int mcexec_linux_numa)
{
	return numa_run_on_node(mcexec_linux_numa);
}

void mcexec_numa_local_cpu_log_bridge(int cpu)
{
	__dprintf("%d belongs to local set\n", cpu);
}

void mcexec_numa_node_cpu_log_bridge(int cpu, int node)
{
	__dprintf("%d belongs to node %d\n", cpu, node);
}

void mcexec_process_thread_plan_flib_log_bridge(int planned_nr_processes)
{
	__dprintf("%s: using FLIB_NUM_PROCESS_ON_NODE: %d\n",
			"main", planned_nr_processes);
}

void mcexec_partition_rank_log_bridge(int process_rank, int target_core)
{
	__dprintf("%s: rank: %d, target CPU: %d\n",
		"main", process_rank, target_core);
}

void mcexec_partition_sched_setaffinity_warning_bridge(void)
{
	__dprintf("WARNING: couldn't bind to mcexec_cpu_set\n");
}

void mcexec_partition_numa_run_warning_bridge(int mcexec_linux_numa)
{
	__dprintf("WARNING: couldn't bind to NUMA %d\n",
			mcexec_linux_numa);
}
