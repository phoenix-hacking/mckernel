const ENOMEM: CInt = 12;
const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const PROFILE_SYSCALL_MAX: usize = 2000;
const PROFILE_OFFLOAD_MAX: usize = PROFILE_SYSCALL_MAX << 1;
const PROFILE_EVENT_MIN: usize = PROFILE_OFFLOAD_MAX;
const PROFILE_EVENT_MAX: usize = PROFILE_EVENT_MIN + PROFILE_EVENT_NAMES.len();
const PROFILE_FILE: &[u8] = b"kernel/rust/profile.rs\0";
const JOB_ALLOC_ERR_FMT: &[u8] = b"%s: ERROR: allocating job profile counters\n\0";
const PROFILE_ACC_JOB_NAME: &[u8] = b"profile_accumulate_and_print_job_events\0";
const JOB_HDR_FMT: &[u8] = b"JOB: (%2d) elapsed cycles for all threads (excluding idle): %luk\n\0";
const JOB_LABEL: &[u8] = b"JOB\0";
const PROFILE_EVENT_NAMES: [&[u8]; 24] = [
    b"remote_tlb_invalidate\0",
    b"page_fault\0",
    b"page_fault_anon_clr_mem\0",
    b"page_fault_file\0",
    b"page_fault_dev_file\0",
    b"page_fault_file_clr_mem\0",
    b"remote_page_fault\0",
    b"mpol_alloc_missed\0",
    b"mmap_anon_contig_phys\0",
    b"|-------mmap_straight\0",
    b"|---mmap_not_straight\0",
    b"mmap_anon_no_contig_phys\0",
    b"mmap_regular_file\0",
    b"mmap_device_file\0",
    b"tofu_stag_alloc \0",
    b"|--new_steering \0",
    b"   |-alloc_mbpt \0",
    b"   |-update_mbpt\0",
    b"tofu_stag_free_stags\0",
    b"tofu_stag_free_stag\0",
    b"   |--------pre\0",
    b"   |----cqflush\0",
    b"   |----dealloc\0",
    b"      |---free_pages\0",
];
