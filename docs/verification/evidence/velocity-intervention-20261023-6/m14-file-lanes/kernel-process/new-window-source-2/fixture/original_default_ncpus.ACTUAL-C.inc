int process_default_ncpus_bridge(void)
{
	struct ihk_mc_cpu_info *infop = ihk_mc_get_cpu_info();

	return infop ? infop->ncpus : -EINVAL;
}
