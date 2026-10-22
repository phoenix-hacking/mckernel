    if (pair_prepare_challenge()) { good = 0; goto finish; }
#if defined(ND_FUTEX) || defined(ND_CORE_THREADS)
    if (helper("boot", "/bin/native-boot", futex_boot_argv, &safe)) { good = 0; goto finish; }
#else
    if (helper("boot", "/bin/native-boot", (char *const[]){"/bin/native-boot",NULL}, &safe)) { good = 0; goto finish; }
#endif
    int boot_logical_cpus[2];
    if (pair_discover(boot_logical_cpus)) { good = 0; goto finish; }
    supervise("/bin/mcexec", payload_argv, payload_env, "/case/work", 10000, &payload);
