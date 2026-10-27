#define process_mckfd_free_bridge reference_process_mckfd_free_bridge
#line 169 "/src/kernel/process.c"
void process_mckfd_free_bridge(struct mckfd *fdp)
{
	kfree_tracked(fdp, __FILE__, __LINE__);
}
#undef process_mckfd_free_bridge
#define process_policy_free_bridge reference_process_policy_free_bridge
#line 251 "/src/kernel/process.c"
void process_policy_free_bridge(void *policy)
{
	kfree_tracked(policy, __FILE__, __LINE__);
}
#undef process_policy_free_bridge
#define process_optional_free_bridge reference_process_optional_free_bridge
#line 256 "/src/kernel/process.c"
void process_optional_free_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}
#undef process_optional_free_bridge
#define process_alloc_bridge reference_process_alloc_bridge
#line 338 "/src/kernel/process.c"
void *process_alloc_bridge(unsigned long size, unsigned long flags)
{
	return kmalloc_tracked(size, flags, __FILE__, __LINE__);
}
#undef process_alloc_bridge
#define process_free_vm_bridge reference_process_free_vm_bridge
#line 559 "/src/kernel/process.c"
void process_free_vm_bridge(void *vm)
{
	kfree_tracked(vm, __FILE__, __LINE__);
}
#undef process_free_vm_bridge
#define process_range_kfree_bridge reference_process_range_kfree_bridge
#line 1815 "/src/kernel/process.c"
void process_range_kfree_bridge(struct vm_range *range)
{
	kfree_tracked(range, __FILE__, __LINE__);
}
#undef process_range_kfree_bridge
#define process_add_range_alloc_bridge reference_process_add_range_alloc_bridge
#line 2254 "/src/kernel/process.c"
struct vm_range *process_add_range_alloc_bridge(unsigned long size)
{
	return kmalloc_tracked(size, IHK_MC_AP_NOWAIT, __FILE__, __LINE__);
}
#undef process_add_range_alloc_bridge
#define process_add_range_free_bridge reference_process_add_range_free_bridge
#line 2259 "/src/kernel/process.c"
void process_add_range_free_bridge(struct vm_range *range)
{
	kfree_tracked(range, __FILE__, __LINE__);
}
#undef process_add_range_free_bridge
