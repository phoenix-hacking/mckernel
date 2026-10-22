#if NATIVE_BOOT_CALLBACK_ABI2
    long boot_status = call(SYS_IOCTL, os, OS_STATUS, 0);
    message("NATIVE_BOOT_STATUS " ARCH_LABEL " raw_status=");
    if (boot_status < 0) message("-");
    print_number(boot_status < 0 ? 0UL - (unsigned long)boot_status : (unsigned long)boot_status);
    message(" expected=5 callback_abi=2\n");
    require(boot_status == 5);
#else
    require(call(SYS_IOCTL, os, OS_STATUS, 0) == 4);
#endif
