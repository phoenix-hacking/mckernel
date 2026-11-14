void process_optional_free_bridge(void *ptr)
{
	kfree_tracked(ptr, __FILE__, __LINE__);
}
