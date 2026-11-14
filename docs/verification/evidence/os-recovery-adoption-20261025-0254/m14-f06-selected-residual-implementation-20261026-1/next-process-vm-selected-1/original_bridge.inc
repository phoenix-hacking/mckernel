
int
arch_prctl_set_register_bridge(int type, unsigned long value)
{
	return ihk_mc_arch_set_special_register(type, value);
}
