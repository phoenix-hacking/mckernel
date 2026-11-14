SYSCALL_POLICY_HELPER_SCOPE int
do_sigaction_body_result(int sig, const struct k_sigaction *act,
		struct k_sigaction *oact, void *sigcommon,
		size_t action_offset, size_t action_stride,
		size_t lock_offset, void *lock_node,
		syscall_sigcommon_lock_fn_t lock_fn,
		syscall_sigcommon_lock_fn_t unlock_fn,
		syscall_sigaction_forward_fn_t forward_fn)
{
	struct k_sigaction *k;
	size_t action_index;
	size_t action_delta;
	char *sigcommon_bytes = sigcommon;
	int error;

	error = sigaction_validate(sig, act != NULL);
	if (error) {
		return error;
	}
	if (!sigcommon || !lock_node ||
			action_stride < sizeof(struct k_sigaction) ||
			!lock_fn || !unlock_fn || (act && !forward_fn)) {
		return -EFAULT;
	}

	action_index = sig - 1;
	if (action_index &&
			action_stride > (~(size_t)0 - action_offset) /
			action_index) {
		return -EINVAL;
	}
	action_delta = action_offset + action_stride * action_index;
	k = (struct k_sigaction *)(sigcommon_bytes + action_delta);

	lock_fn(sigcommon_bytes + lock_offset, lock_node);
	if (oact) {
		memcpy(oact, k, action_stride);
	}
	if (act) {
		memcpy(k, act, action_stride);
	}
	unlock_fn(sigcommon_bytes + lock_offset, lock_node);

	if (act) {
		forward_fn(sig, act);
	}
	return 0;
}
