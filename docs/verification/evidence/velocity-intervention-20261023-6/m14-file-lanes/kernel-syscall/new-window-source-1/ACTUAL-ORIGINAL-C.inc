void
syscall_swapout_log_bridge(const void *fname, void *buf, size_t size, int flag)
{
	dkprintf("[%d]swapout(%lx,%lx,%lx,%ld)\n",
			ihk_mc_get_processor_id(), (unsigned long)fname,
			(unsigned long)buf, (unsigned long)size, (long)flag);
}

void
syscall_linux_mlock_log_bridge(unsigned long addr, unsigned long len)
{
	kprintf("linux_mlock: %p %ld\n", (void *)addr, len);
}
