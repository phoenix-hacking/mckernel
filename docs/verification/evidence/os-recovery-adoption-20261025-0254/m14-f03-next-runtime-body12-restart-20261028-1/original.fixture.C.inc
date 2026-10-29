#line 28602 "kernel/syscall.c"
void
syscall_util_register_desc_log_bridge(int tid, unsigned long desc)
{
	dkprintf("%s: tid=%d,uti_desc=%lx\n", "sys_util_register_desc",
			tid, desc);
}
