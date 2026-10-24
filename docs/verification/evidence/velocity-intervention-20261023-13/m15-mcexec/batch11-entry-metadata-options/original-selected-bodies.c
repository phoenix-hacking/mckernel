size_t mcexec_opendev_buildid_size_bridge(void)
{
	return sizeof(BUILDID);
}

const char *mcexec_opendev_buildid_bridge(void)
{
	static char buildid[] = BUILDID;

	return buildid;
}

char *mcexec_opendev_query_result_bridge(void)
{
	static char query_result[sizeof(BUILDID)];

	memset(query_result, '\0', sizeof(query_result));
	return query_result;
}

void mcexec_exit_cmd_servers_bridge(void)
{
#ifdef USE_SYSCALL_MOD_CALL
#ifdef CMD_DCFA
	ibmic_cmd_server_exit();
#endif

#ifdef CMD_DCFAMPI
	dcfampi_cmd_server_exit();
#endif
	mc_cmd_server_exit();
	__dprintf("mccmd server exited\n");
#endif
}

int mcexec_main_cmd_servers_init_bridge(void)
{
#ifdef USE_SYSCALL_MOD_CALL
	if(mc_cmd_server_init()){
		fprintf(stderr, "Error: cmd server init failed\n");
		return 1;
	}

#ifdef CMD_DCFA
	if(ibmic_cmd_server_init()){
		fprintf(stderr, "Error: Failed to initialize ibmic_cmd_server.\n");
		return -1;
	}
#endif

#ifdef CMD_DCFAMPI
	if(dcfampi_cmd_server_init()){
		fprintf(stderr, "Error: Failed to initialize dcfampi_cmd_server.\n");
		return -1;
	}
#endif
	__dprintf("mccmd server initialized\n");
#endif

	return 0;
}

int mcexec_main_bind_mount_bridge(void)
{
#ifdef MCEXEC_BIND_MOUNT
	int error;

	error = isunshare();
	if (error == 0) {
		struct sys_unshare_desc unshare_desc;
		struct sys_mount_desc mount_desc;
		struct sys_umount_desc umount_desc;

		/* Unshare mount namespace */
		memset(&unshare_desc, '\0', sizeof unshare_desc);
		memset(&mount_desc, '\0', sizeof mount_desc);
		unshare_desc.unshare_flags = CLONE_NEWNS;
		if (ioctl(fd, MCEXEC_UP_SYS_UNSHARE,
			(unsigned long)&unshare_desc) != 0) {
			fprintf(stderr, "Error: Failed to unshare. (%s)\n",
				strerror(errno));
			return 1;
		}

		/* Privatize mount namespace */
		mount_desc.dev_name = NULL;
		mount_desc.dir_name = "/";
		mount_desc.type = NULL;
		mount_desc.flags = MS_PRIVATE | MS_REC;
		mount_desc.data = NULL;
		if (ioctl(fd, MCEXEC_UP_SYS_MOUNT,
			(unsigned long)&mount_desc) != 0) {
			fprintf(stderr, "Error: Failed to privatize mounts. (%s)\n",
				strerror(errno));
			return 1;
		}

		// bind_mount_recursive(<root>, <prefix>);
		(void)umount_desc;
	} else if (error == -1) {
		return 1;
	}
#endif
	return 0;
}

void mcexec_partition_debug_ikc_binding_bridge(void)
{
#ifdef DEBUG
	int i;

	for (i = 0; i < numa_num_possible_cpus(); ++i) {
		if (CPU_ISSET(i, &mcexec_partition_cpu_set_storage)) {
			__dprintf("PID %d bound to CPU %d\n",
				getpid(), i);
		}
	}
#endif
}

void mcexec_partition_debug_numa_binding_bridge(void)
{
#ifdef DEBUG
	int i;
	cpu_set_t cpuset;
	char affinity[BUFSIZ];

	CPU_ZERO(&cpuset);
	if ((sched_getaffinity(0, sizeof(cpu_set_t), &cpuset)) != 0) {
		perror("Error sched_getaffinity");
		exit(1);
	}

	affinity[0] = '\0';
	for (i = 0; i < 512; i++) {
		if (CPU_ISSET(i, &cpuset) == 1) {
			sprintf(affinity, "%s %d", affinity, i);
		}
	}
	__dprintf("PID: %d affinity: %s\n",
			getpid(), affinity);
#endif
}
