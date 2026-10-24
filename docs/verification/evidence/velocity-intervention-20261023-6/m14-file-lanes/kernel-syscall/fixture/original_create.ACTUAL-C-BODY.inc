long
syscall_signalfd_create_bridge(int syscall_nr, int flags)
{
	struct syscall_request request IHK_DMA_ALIGN;

	memset(&request, 0, sizeof(request));
	request.number = syscall_nr;
	request.args[0] = 0;
	request.args[1] = flags;
	return do_syscall(&request, ihk_mc_get_processor_id());
}
