long arch_native_signal_restore_fp_bridge(unsigned long user_address, int size)
{
	int configured = get_xsave_size();
	long bytes, result;
	void *allocation;
	unsigned char *aligned;
	uint64_t mask;

	if (!user_address)
		return arch_native_signal_reset_fp_bridge();
	bytes = native_xstate_buffer_size_result(size, configured);
	if (bytes < 0)
		return bytes;
	/* Rust bounds bytes to 64 KiB; retain the original pointer for cleanup. */
	allocation = kmalloc_tracked((size_t)bytes + 63, IHK_MC_AP_NOWAIT,
			__FILE__, __LINE__);
	if (!allocation)
		return -ENOMEM;
	aligned = (unsigned char *)(((unsigned long)allocation + 63) & ~63UL);
	result = copy_from_user(aligned, (const void *)user_address, (size_t)bytes);
	if (result) {
		result = -EFAULT;
		goto out;
	}
	mask = get_xsave_mask();
	result = native_xstate_validate_result(aligned, (size_t)bytes, configured,
			mask, arch_native_signal_mxcsr_mask_bridge());
	if (!result)
		result = native_xrstor_checked(aligned, mask);
out:
	kfree_tracked(allocation, __FILE__, __LINE__);
	return result;
}
