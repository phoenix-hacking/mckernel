
long
arch_copy_from_user_bridge(void *dst, unsigned long src_addr, size_t bytes)
{
	return copy_from_user(dst, (void *)src_addr, bytes);
}
