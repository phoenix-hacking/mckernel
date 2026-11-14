#line 382 "arch/x86_64/kernel/syscall.c"
void *
arch_rt_sigreturn_alloc_bridge(size_t size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}

void
arch_rt_sigreturn_free_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}

