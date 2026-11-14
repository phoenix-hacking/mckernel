/* Actual source-only contracts; metadata witness only. */

extern int _ihk_os_assign_cpu_str(int os_index, char *list, char *err_msg);

extern int _ihk_os_set_ikc_map_str(int os_index, char *list, char *err_msg);

extern int parse_env(const char *envp, int num_env, char ***_name, char ***_value);

extern void dump_reserve_mem_conf(void);

int __argc;

char **__argv;

struct namespace_file namespace_files[] = {
	{ .nstype = CLONE_NEWUSER,	.name = "ns/user", .fd = -1 },
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4,6,0)
	{ .nstype = CLONE_NEWCGROUP,	.name = "ns/cgroup", .fd = -1 },
#endif
	{ .nstype = CLONE_NEWIPC,	.name = "ns/ipc", .fd = -1 },
	{ .nstype = CLONE_NEWUTS,	.name = "ns/uts", .fd = -1 },
	{ .nstype = CLONE_NEWNET,	.name = "ns/net", .fd = -1 },
	{ .nstype = CLONE_NEWPID,	.name = "ns/pid", .fd = -1 },
	{ .nstype = CLONE_NEWNS,	.name = "ns/mnt", .fd = -1 },
	{ .nstype = 0, .name = NULL, .fd = -1 }
};
