// Appended to the existing complete os_runtime fixture; production module
// bodies come byte-for-byte from compiled candidate 3f7b. No gate alteration.
#[test]
fn resource_v2_closed_admission_status_bypass() {
    with_family(|| {
        reset_backend();
        BOOT_PREPARE_STATUS.store(0, Ordering::SeqCst);
        BOOT_START_STATUS.store(0, Ordering::SeqCst);
        SHUTDOWN_V6_STATUS.store(0, Ordering::SeqCst);
        assert_eq!(create_shutdown_backend_v6_abi(2, Some(backend_shutdown_v6)), 0);
        let mut file = open(0).unwrap();
        assert_eq!(status(&mut file, false, abi::IHK_OS_BOOT), 0);
        assert_eq!(status(&mut file, false, abi::IHK_OS_QUERY_STATUS), 5);
        assert_eq!(status(&mut file, false, abi::IHK_OS_SHUTDOWN), 0);
        let before = BACKEND_CALLS.lock().unwrap().len();
        let mut native = [0_i64; 3];
        for compat in [false, true] {
            let observed = [
                status(&mut file, compat, abi::IHK_OS_QUERY_STATUS),
                status(&mut file, compat, abi::IHK_OS_QUERY_CPU),
                status(&mut file, compat, abi::IHK_OS_QUERY_MEM),
            ];
            assert_eq!(observed, [0, -16, -16]);
            assert_eq!(BACKEND_CALLS.lock().unwrap().len(), before);
            if !compat { native = observed; }
        }
        close(file);
        assert_eq!(destroy(0), 0);
        let path = std::env::var("NATIVE_RESOURCE_ADMISSION_TRACE").unwrap();
        let mut output = std::fs::OpenOptions::new().write(true).create_new(true)
            .open(path).unwrap();
        use std::io::Write;
        writeln!(output, "{} {} {}", native[0], native[1], native[2]).unwrap();
    });
}
