int valid_signal(unsigned long sig)
{
	return sig <= _NSIG ? 1 : 0;
}
