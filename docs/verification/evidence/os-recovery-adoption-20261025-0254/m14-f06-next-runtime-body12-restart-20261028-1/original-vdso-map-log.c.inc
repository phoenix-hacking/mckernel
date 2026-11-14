void
arch_vdso_map_log_bridge(int event, int error, struct process_vm *vm,
		unsigned long a, unsigned long b, unsigned long c,
		unsigned long d, int pages)
{
	switch (event) {
	case ARCH_VDSO_MAP_LOG_NOT_AVAILABLE:
		dkprintf("arch_map_vdso(): not available\n");
		break;
	case ARCH_VDSO_MAP_LOG_ADD_VDSO_FAILED:
		ekprintf("ERROR: adding memory range for vdso. %d\n", error);
		break;
	case ARCH_VDSO_MAP_LOG_MAPPED:
		kprintf("mcexec_v10: vdso_map pid=%d container=0x%lx vdso=0x%lx vdso_end=0x%lx offset=0x%lx size=0x%lx pages=%d\n",
			vm && vm->proc ? vm->proc->pid : -1, a, b, c,
			(unsigned long)vdso_offset, d, pages);
		break;
	case ARCH_VDSO_MAP_LOG_SET_RANGE_FAILED:
		ekprintf("ihk_mc_pt_set_range failed. %d\n", error);
		break;
	case ARCH_VDSO_MAP_LOG_ADD_VVAR_FAILED:
		ekprintf("ERROR: adding memory range for vvar. %d\n", error);
		break;
	}
}
