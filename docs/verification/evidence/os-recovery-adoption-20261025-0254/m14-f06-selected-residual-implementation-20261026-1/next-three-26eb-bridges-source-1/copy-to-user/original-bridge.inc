
long
arch_copy_to_user_bridge(unsigned long dst_addr, const void *src, size_t bytes)
{
	return copy_to_user((void *)dst_addr, src, bytes);
}
