static long util_thread(struct thread_data_s *my_thread,
		unsigned long rp_rctx, int remote_tid, unsigned long pattr,
		unsigned long uti_info, unsigned long _uti_desc)
{
	return mcexec_util_thread_body(my_thread, rp_rctx, remote_tid, pattr,
			uti_info, _uti_desc);
}
