void process_range_kfree_bridge(struct vm_range *range)
{
	kfree_tracked(range, __FILE__, __LINE__);
}
