unsigned long x86_kprintf_lock_bridge(void)
{
	return kprintf_lock();
}

void x86_kprintf_unlock_bridge(unsigned long flags)
{
	kprintf_unlock(flags);
}
