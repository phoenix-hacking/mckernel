    char teardown[160];
    int length = snprintf(teardown, sizeof teardown,
                          "modules_loaded=%d processes_reaped=%d procfs_empty=%d nested_os_retained=1\n",
                          loaded, safe, empty);
    if (length < 0 || (size_t)length >= sizeof teardown ||
        save_file("/case/evidence/teardown", teardown, (size_t)length)) good = 0;
#ifdef ND_PAIR_LAUNCH_EXPANSION
    static char kernel_log[1048576];
#else
    static char kernel_log[262144];
#endif
    int n = klogctl(3, kernel_log, sizeof kernel_log);
    if (n < 0 || n == (int)sizeof kernel_log) good = 0;
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
    /* Exercise restoration before publication so a restoration failure is
     * represented by procfs_empty=false; suppress again for the one write. */
    if (saved_level < 0 || klogctl(8, NULL, saved_level) || klogctl(6, NULL, 0)) good = 0;
    int evidence_fd = open("/case/evidence", O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (evidence_fd < 0) good = 0;
    else { if (syncfs(evidence_fd)) good = 0; if (close(evidence_fd)) good = 0; }
    if (!good || !safe) payload.fault = 1;
    payload.finished = now_ns();
    if (console >= 0 && safe) {
#if defined(ND_PAIR_LAUNCH_EXPANSION)
        #if defined(ND_PAIR_LONG)
        int publication=good && empty ? 0 : -1;
        #else
        static const char complete[]="ND_PAIR_ROUNDS_COMPLETE {\"rounds\":10,\"os\":0,\"generation\":1,\"procfs_empty\":true}\n";
        int publication = good && empty ? write_all(console,complete,sizeof complete-1) : -1;
        #endif
#else
        int publication = publish_pair(console, empty && good);
#endif
        if (publication) payload.fault = 1;
    }
    if (saved_level >= 0 && klogctl(8, NULL, saved_level)) {
        const char message[] = "native diagnostic teardown error: printk restoration\n";
        if (console >= 0) (void)write_all(console, message, sizeof message - 1);
        remain_pid1(); /* Host deadline rejects the uncompleted teardown. */
    }
#if defined(ND_PAIR_LONG)
    /* No fallible evidence/restoration gate follows terminal LONG publication.
     * A short write or post-write clock failure retains PID1 for host rejection. */
    if (!good || !safe || !empty || payload.fault || long_complete()) remain_pid1();
#endif
