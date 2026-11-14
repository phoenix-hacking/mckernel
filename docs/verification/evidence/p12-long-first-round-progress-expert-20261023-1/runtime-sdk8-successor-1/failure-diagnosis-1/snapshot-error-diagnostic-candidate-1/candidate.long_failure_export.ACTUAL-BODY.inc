static int long_failure_export(int console,int ownership_complete)
{
    struct long_context ctx={.console=console};
    char line[512];static char log[1048577];
    const char *failed_phase=long_observed_phase;
    int n=snprintf(line,sizeof line,
        "P12_LONG_FAILURE round=%u stage=%s pair_stage=%s result=%d ownership_complete=%d rounds=%llu launches=%llu trace_bytes=%llu\n",
        long_observed_round,failed_phase,pair_fail_phase,long_observed_result,
        ownership_complete,(unsigned long long)long_observed_summary.rounds,(unsigned long long)long_observed_summary.launches,
        (unsigned long long)long_observed_summary.trace_bytes);
    if(n<=0 || (size_t)n>=sizeof line || write_all(console,line,(size_t)n))return -1;
    /* Reject success first, before an evidence callback can itself stall. */
    static const char abort_line[]="ND_PAIR_LONG_ABORT\n";
    if(write_all(console,abort_line,sizeof abort_line-1) ||
       long_phase(&ctx,long_observed_round,"failure-trace-snapshot"))return -1;
    if(pair_settlement_snapshot_error.valid)
        long_snapshot_error_line(console,"settlement",pair_settlement_snapshot_error.n,
            pair_settlement_snapshot_error.errno_after,pair_settlement_snapshot_error.bound,
            pair_settlement_snapshot_error.round,pair_settlement_snapshot_error.pid0,
            pair_settlement_snapshot_error.pid1);
    n=long_kernel_snapshot(log,sizeof log-1);
    int snapshot_errno=errno;
    if(n<=0 || n==(int)sizeof log-1) {
        long_snapshot_error_line(console,"failure_export",n,snapshot_errno,sizeof log-1,
                                 long_observed_round,pair_results[0].pid,pair_results[1].pid);
        static const char error[]="P12_LONG_FAILURE_TRACE_ERROR stage=snapshot\n";
        (void)write_all(console,error,sizeof error-1);return -1;
    }
    if(long_phase(&ctx,long_observed_round,"failure-trace-save"))return -1;
    int saved=save_file(PAIR_ROOT "/evidence/long-failure.kernel.log",log,(size_t)n);
    if(saved) {
        static const char error[]="P12_LONG_FAILURE_TRACE_ERROR stage=save\n";
        if(write_all(console,error,sizeof error-1))return -1;
    }
    int count=snprintf(line,sizeof line,"P12_LONG_FAILURE_TRACE_BEGIN bytes=%d saved=%d\n",n,!saved);
    if(count<=0 || (size_t)count>=sizeof line || write_all(console,line,(size_t)count) ||
       write_all(console,log,(size_t)n) || (log[n-1]!='\n' && write_all(console,"\n",1)))return -1;
    count=snprintf(line,sizeof line,"P12_LONG_FAILURE_TRACE_END bytes=%d\n",n);
    return count<=0 || (size_t)count>=sizeof line || write_all(console,line,(size_t)count)?-1:0;
}

