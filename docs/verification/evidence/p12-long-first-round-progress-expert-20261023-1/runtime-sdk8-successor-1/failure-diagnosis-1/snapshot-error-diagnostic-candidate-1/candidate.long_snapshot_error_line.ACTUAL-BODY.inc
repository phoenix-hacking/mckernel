static void long_snapshot_error_line(int console,const char *site,int n,int error,
                                     size_t bound,unsigned round,int pid0,int pid1)
{
    int saved_errno=errno;
    char line[320];
    int count=snprintf(line,sizeof line,
        "P12_LONG_SNAPSHOT_ERROR site=%s n=%d errno_after=%d errno_valid=%d bound=%zu round=%u pid0=%d pid1=%d\n",
        site,n,error,n<0,bound,round,pid0,pid1);
    if(count>0 && (size_t)count<sizeof line)(void)write_all(console,line,(size_t)count);
    errno=saved_errno;
}
