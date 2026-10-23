#ifdef ND_PAIR_LAUNCH_EXPANSION
    static char kernel_log[1048576];
#else
    static char kernel_log[262144];
#endif
    int n = klogctl(3, kernel_log, sizeof kernel_log);
#ifdef ND_PAIR_LONG
    if (n < 0 || n > (int)sizeof kernel_log) good = 0;
#else
    if (n < 0 || n == (int)sizeof kernel_log) good = 0;
#endif
    else if (save_file("/case/evidence/kernel.log", kernel_log, (size_t)n) || console < 0) good = 0;
    else {
#ifdef ND_PAIR_LAUNCH_EXPANSION
        #if defined(ND_PAIR_LONG)
        /* LONG trace is already authenticated/published by Rust; raw final
         * kernel.log remains saved above, without a duplicate success trace. */
        if(!good && write_all(console,"ND_PAIR_LONG_ABORT\n",19))good=0;
        #else
        if(good) { if(pair_trace_publish(console,kernel_log,(size_t)n))good=0; }
        else if(safe && pair_rounds_initialized && pair_failure_export(console,kernel_log,(size_t)n))good=0;
        #endif
#else
        if(write_all(console,kernel_log,(size_t)n) || write_all(console,"\n",1))good=0;
#endif
    }
