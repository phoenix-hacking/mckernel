void
arch_vdso_setup_log_bridge(int event, int error)
{
	switch (event) {
	case ARCH_VDSO_SETUP_LOG_GET_INFO_FAILED:
		ekprintf("arch_setup_vdso: vdso_get_vdso_info failed. %d\n",
				error);
		break;
	case ARCH_VDSO_SETUP_LOG_LOCAL_GETTIME_DISABLED:
		kprintf("x86 local gettime disabled: host vgtod data unavailable\n");
		break;
	case ARCH_VDSO_SETUP_LOG_VDSO_DISABLED:
		kprintf("vdso disabled: host vgtod data unavailable\n");
		break;
	case ARCH_VDSO_SETUP_LOG_MAP_GLOBAL_FAILED:
		ekprintf("arch_setup_vdso: vdso_map_global_pages failed. %d\n",
				error);
		break;
	}
}
