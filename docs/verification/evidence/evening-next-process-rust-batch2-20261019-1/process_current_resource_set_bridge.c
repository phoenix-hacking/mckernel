void *process_current_resource_set_bridge(void)
{
	return get_this_cpu_local_var()->resource_set;
}
