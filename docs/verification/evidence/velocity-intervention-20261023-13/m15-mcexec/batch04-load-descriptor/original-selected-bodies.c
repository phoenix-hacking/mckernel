struct program_load_desc *mcexec_load_alloc_desc_bridge(int nsections)
{
	struct program_load_desc *desc;
	size_t size = sizeof(struct program_load_desc) +
		sizeof(struct program_image_section) * nsections;

	desc = malloc(size);
	if (!desc) {
		return NULL;
	}
	memset(desc, '\0', size);
	desc->magic = PLD_MAGIC;
	desc->num_sections = nsections;
	desc->stack_prot = PROT_READ | PROT_WRITE | PROT_EXEC;
	return desc;
}

void mcexec_load_publish_main_section_bridge(
		struct program_load_desc *desc, int index,
		unsigned long vaddr, unsigned long filesz,
		unsigned long offset, unsigned long len, int prot, void *fp)
{
	desc->sections[index].vaddr = vaddr;
	desc->sections[index].filesz = filesz;
	desc->sections[index].offset = offset;
	desc->sections[index].len = len;
	desc->sections[index].interp = 0;
	desc->sections[index].fp = fp;
	desc->sections[index].prot = prot;
}

void mcexec_desc_publish_interp_section_bridge(
		struct program_load_desc *desc, int index,
		unsigned long vaddr, unsigned long filesz,
		unsigned long offset, unsigned long len, int prot, void *fp)
{
	desc->sections[index].vaddr = vaddr;
	desc->sections[index].filesz = filesz;
	desc->sections[index].offset = offset;
	desc->sections[index].len = len;
	desc->sections[index].interp = 1;
	desc->sections[index].fp = fp;
	desc->sections[index].prot = prot;
}

int *mcexec_load_cred_bridge(struct program_load_desc *desc)
{
	return desc->cred;
}

long mcexec_load_clk_tck_bridge(void)
{
	return sysconf(_SC_CLK_TCK);
}

void mcexec_load_finalize_desc_bridge(struct program_load_desc *desc,
		int pid, int pgid, int reloc, unsigned long entry,
		unsigned long at_phdr, unsigned long at_phent,
		unsigned long at_phnum, unsigned long at_entry,
		unsigned long at_clktck, int stack_prot)
{
	desc->pid = pid;
	desc->pgid = pgid;
	desc->reloc = reloc;
	desc->entry = entry;
	desc->at_phdr = at_phdr;
	desc->at_phent = at_phent;
	desc->at_phnum = at_phnum;
	desc->at_entry = at_entry;
	desc->at_clktck = at_clktck;
	desc->stack_prot = stack_prot;
}

size_t mcexec_program_load_desc_size_bridge(void)
{
	return sizeof(struct program_load_desc);
}

size_t mcexec_program_image_section_size_bridge(void)
{
	return sizeof(struct program_image_section);
}

void mcexec_desc_set_num_sections_bridge(struct program_load_desc *desc,
		int count)
{
	desc->num_sections = count;
}

void mcexec_desc_set_entry_bridge(struct program_load_desc *desc,
		unsigned long entry)
{
	desc->entry = entry;
}

void mcexec_desc_set_interp_align_bridge(struct program_load_desc *desc,
		unsigned long align)
{
	desc->interp_align = align;
}

void mcexec_desc_set_args_len_bridge(struct program_load_desc *desc,
		unsigned long args_len)
{
	desc->args_len = args_len;
}

int mcexec_desc_num_sections_bridge(const struct program_load_desc *desc)
{
	return desc->num_sections;
}

int mcexec_desc_cpu_bridge(const struct program_load_desc *desc)
{
	return desc->cpu;
}

int mcexec_desc_pid_bridge(const struct program_load_desc *desc)
{
	return desc->pid;
}

unsigned long mcexec_desc_entry_bridge(const struct program_load_desc *desc)
{
	return desc->entry;
}

unsigned long mcexec_desc_rprocess_bridge(const struct program_load_desc *desc)
{
	return desc->rprocess;
}

unsigned long mcexec_desc_section_vaddr_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].vaddr;
}

unsigned long mcexec_desc_section_len_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].len;
}

unsigned long mcexec_desc_section_remote_pa_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].remote_pa;
}

unsigned long mcexec_desc_section_filesz_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].filesz;
}

unsigned long mcexec_desc_section_offset_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].offset;
}

void *mcexec_desc_section_fp_bridge(
		const struct program_load_desc *desc, int index)
{
	return desc->sections[index].fp;
}

void mcexec_partition_publish_cpu_rank_bridge(struct program_load_desc *desc,
		int target_core, int process_rank)
{
	desc->cpu = target_core;
	desc->process_rank = process_rank;
}

void mcexec_partition_publish_rank_bridge(struct program_load_desc *desc,
		int process_rank)
{
	desc->process_rank = process_rank;
}

void mcexec_desc_publish_mpol_base_bridge(struct program_load_desc *desc,
		int profile_arg, int nr_processes_arg, unsigned long flags,
		unsigned long threshold, unsigned long heap_ext,
		int pld_mpol_max)
{
	desc->profile = profile_arg;
	desc->nr_processes = nr_processes_arg;
	desc->mpol_flags = flags;
	desc->mpol_threshold = threshold;
	desc->heap_extension = heap_ext;
	desc->mpol_bind_mask = 0;
	desc->mpol_mode = pld_mpol_max;
}

void mcexec_desc_apply_bind_nodes_bridge(struct program_load_desc *desc,
		const char *nodes)
{
	struct bitmask *bind_mask;

	bind_mask = numa_parse_nodestring_all(nodes);
	if (bind_mask) {
		int node;

		for (node = 0; node <= numa_max_possible_node(); ++node) {
			if (numa_bitmask_isbitset(bind_mask, node)) {
				desc->mpol_bind_mask |= (1UL << node);
			}
		}
	}
}

void mcexec_desc_apply_ompi_policy_bridge(struct program_load_desc *desc,
		int mode, int nodemask_action)
{
	desc->mpol_mode = mode;
	if (nodemask_action == 1) {
		numa_local(desc->cpu_set, desc->mpol_nodemask);
	}
	else if (nodemask_action == 2) {
		numa_nonlocal(desc->cpu_set, desc->mpol_nodemask);
	}
	else if (nodemask_action == 3) {
		numa_all(desc->mpol_nodemask);
	}
}

void mcexec_desc_publish_runtime_flags_bridge(struct program_load_desc *desc,
		int enable_uti_arg, int uti_thread_rank_arg,
		int uti_use_last_cpu_arg, int thp_disable_arg,
		int straight_map_arg, unsigned long straight_map_threshold_arg,
		int enable_tofu_arg, unsigned long mcexec_flags_arg)
{
	desc->enable_uti = enable_uti_arg;
	desc->uti_thread_rank = uti_thread_rank_arg;
	desc->uti_use_last_cpu = uti_use_last_cpu_arg;
	desc->thp_disable = thp_disable_arg;
	desc->straight_map = straight_map_arg;
	desc->straight_map_threshold = straight_map_threshold_arg;
#ifdef ENABLE_TOFU
	desc->enable_tofu = enable_tofu_arg;
#else
	(void)enable_tofu_arg;
#endif
	if (mcexec_flags_arg) {
		desc->mcexec_flags = mcexec_flags_arg;
	}
}

void mcexec_desc_set_execve1_runtime_bridge(struct program_load_desc *desc,
		int vdso, unsigned long rlim_cur, unsigned long rlim_max,
		long prem)
{
	desc->enable_vdso = vdso;
	desc->rlimit[RLIMIT_STACK].rlim_cur = rlim_cur;
	desc->rlimit[RLIMIT_STACK].rlim_max = rlim_max;
	desc->stack_premap = prem;
}

void mcexec_main_stack_publish_bridge(struct program_load_desc *desc,
		rlim_t cur, rlim_t max, long prem)
{
	desc->rlimit[MCK_RLIMIT_STACK].rlim_cur = cur;
	desc->rlimit[MCK_RLIMIT_STACK].rlim_max = max;
	desc->stack_premap = prem;
	__dprintf("desc->rlimit[MCK_RLIMIT_STACK]=%ld,%ld\n",
			desc->rlimit[MCK_RLIMIT_STACK].rlim_cur,
			desc->rlimit[MCK_RLIMIT_STACK].rlim_max);
}

void mcexec_desc_snapshot_rlimits_bridge(struct program_load_desc *desc)
{
	int i;

	for (i = 0; i < sizeof(rlimits) / sizeof(int); i += 2) {
		getrlimit(rlimits[i], &desc->rlimit[rlimits[i + 1]]);
	}
}

void mcexec_desc_publish_env_bridge(struct program_load_desc *desc,
		int envs_len, char *envs)
{
	desc->envs_len = envs_len;
	desc->envs = envs;
}

void mcexec_desc_publish_args_cpu_bridge(struct program_load_desc *desc,
		unsigned long args_len, char *args, int cpu, int vdso)
{
	desc->args_len = args_len;
	desc->args = args;
	desc->cpu = cpu;
	desc->enable_vdso = vdso;
}

void mcexec_desc_clear_flags_bridge(struct program_load_desc *desc)
{
	desc->mcexec_flags = 0;
}
