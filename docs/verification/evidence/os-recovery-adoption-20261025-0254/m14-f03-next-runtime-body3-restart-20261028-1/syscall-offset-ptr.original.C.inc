static inline void *syscall_offset_ptr(void *base, size_t offset)
{
	return (char *)base + offset;
}
