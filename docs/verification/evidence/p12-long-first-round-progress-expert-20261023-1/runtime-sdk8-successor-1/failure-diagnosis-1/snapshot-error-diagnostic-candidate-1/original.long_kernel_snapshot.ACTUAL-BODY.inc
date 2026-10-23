static int long_kernel_snapshot(char *data,size_t count)
{ return count>INT_MAX?-1:long_provider.snapshot(3,data,(int)count); }
