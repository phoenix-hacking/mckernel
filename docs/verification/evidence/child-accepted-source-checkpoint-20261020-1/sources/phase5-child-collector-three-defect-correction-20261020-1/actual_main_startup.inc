#if defined(ND_PAIR_STARTUP)
    errno = 0;
    if (pair_prepare_challenge()) {
        refuse_startup("challenge-prepare"); good = 0; goto finish;
    }
#endif
#if defined(ND_FUTEX) || defined(ND_PROCESS_EXEC_WAIT)
    if (helper("boot", "/bin/native-boot", oversubscribed_boot_argv, &safe)) { good = 0; goto finish; }
#else
    if (helper("boot", "/bin/native-boot", (char *const[]){"/bin/native-boot",NULL}, &safe)) { good = 0; goto finish; }
#endif
#if defined(ND_PAIR_STARTUP)
    int cpus[2]; errno = 0;
    if (pair_discover(cpus)) {
        refuse_startup("assignment-readback"); good = 0; goto finish;
    }
#endif
    supervise("/bin/mcexec", payload_argv, payload_env, "/case/work", 10000, &payload);
