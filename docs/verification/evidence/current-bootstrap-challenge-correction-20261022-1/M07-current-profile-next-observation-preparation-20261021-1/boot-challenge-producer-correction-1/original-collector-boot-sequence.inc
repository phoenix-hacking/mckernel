#if defined(ND_FUTEX) || defined(ND_CORE_THREADS)
    if (helper("boot", "/bin/native-boot", futex_boot_argv, &safe)) { good = 0; goto finish; }
#else
    if (helper("boot", "/bin/native-boot", (char *const[]){"/bin/native-boot",NULL}, &safe)) { good = 0; goto finish; }
#endif
    supervise("/bin/mcexec", payload_argv, payload_env, "/case/work", 10000, &payload);
