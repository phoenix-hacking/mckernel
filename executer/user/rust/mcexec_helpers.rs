#![no_std]

use core::ffi::{c_int, c_long, c_ulong, c_void};
use core::panic::PanicInfo;
use core::ptr::{read_volatile, write_volatile};
use core::sync::atomic::{AtomicU32, Ordering};

const PTRACE_GETREGS: c_int = 12;
const PTRACE_SETREGS: c_int = 13;
const ENOSYS_RET: u64 = u64::MAX - 37;
const SYS_GETTID: c_long = 186;
const SYS_TGKILL: c_long = 234;
const SYS_EXIT_GROUP: c_long = 231;
const SYS_RT_SIGACTION: c_int = 13;
const SYS_WRITE: c_long = 1;
const SYS_OPEN: c_long = 2;
const SYS_CLOSE: c_long = 3;
const SYS_STAT: c_long = 4;
const SYS_MMAP: c_long = 9;
const SYS_MPROTECT: c_long = 10;
const SYS_MUNMAP: c_long = 11;
const SYS_RT_SIGPROCMASK: c_long = 14;
const SYS_ACCESS: c_long = 21;
const SYS_CLONE: c_long = 56;
const SYS_EXECVE: c_long = 59;
const SYS_EXIT: c_long = 60;
const SYS_WAIT4: c_long = 61;
const SYS_KILL: c_long = 62;
const SYS_GETDENTS: c_long = 78;
const SYS_READLINK: c_long = 89;
const SYS_SETUID: c_long = 105;
const SYS_SETGID: c_long = 106;
const SYS_SETREUID: c_long = 113;
const SYS_SETREGID: c_long = 114;
const SYS_SETRESUID: c_long = 117;
const SYS_SETRESGID: c_long = 119;
const SYS_SETFSUID: c_long = 122;
const SYS_SETFSGID: c_long = 123;
const SYS_GETXATTR: c_long = 191;
const SYS_LGETXATTR: c_long = 192;
const SYS_FUTEX: c_long = 202;
const SYS_SCHED_SETAFFINITY: c_long = 203;
const SYS_GETDENTS64: c_long = 217;
const SYS_OPENAT: c_long = 257;
const SYS_NEWFSTATAT: c_long = 262;
const SYS_READLINKAT: c_long = 267;
const SYS_FACCESSAT: c_long = 269;
const SYS_SIGNALFD4: c_long = 289;
const SYS_PERF_EVENT_OPEN: c_long = 298;
const MCEXEC_SWAPOUT_SYSCALL: c_long = 801;
const MCEXEC_DEBUG_MLOCK_SYSCALL: c_long = 802;
const MCEXEC_LINUX_SPAWN_SYSCALL: c_long = 811;
const MCEXEC_UP_PREPARE_IMAGE: c_ulong = 0x30a02900;
const MCEXEC_UP_TRANSFER: c_ulong = 0x30a02901;
const MCEXEC_UP_START_IMAGE: c_ulong = 0x30a02902;
const MCEXEC_UP_WAIT_SYSCALL: c_ulong = 0x30a02903;
const MCEXEC_UP_TRANSFER_TO_REMOTE: u8 = 0;
const MCEXEC_UP_TRANSFER_FROM_REMOTE: u8 = 1;
const MCEXEC_UP_RET_SYSCALL: c_ulong = 0x30a02904;
const MCEXEC_UP_LOAD_SYSCALL: c_ulong = 0x30a02905;
const MCEXEC_UP_SEND_SIGNAL: c_ulong = 0x30a02906;
const MCEXEC_UP_STRNCPY_FROM_USER: c_ulong = 0x30a02908;
const MCEXEC_UP_GET_CREDV: c_ulong = 0x30a0290b;
const MCEXEC_UP_OPEN_EXEC: c_ulong = 0x30a02912;
const MCEXEC_UP_CLOSE_EXEC: c_ulong = 0x30a02913;
const MCEXEC_UP_UTI_GET_CTX: c_ulong = 0x30a02920;
const MCEXEC_UP_UTI_ATTR: c_ulong = 0x30a02927;
const MCEXEC_UP_SIG_THREAD: c_ulong = 0x30a02922;
const MCEXEC_UP_SYSCALL_THREAD: c_ulong = 0x30a02924;
const PATH_MAX: usize = 4096;
const PLD_PROCESS_NUMA_MASK_BITS: usize = 256;
const KIB: u64 = 1024;
const MIB: u64 = KIB * 1024;
const GIB: u64 = MIB * 1024;
const ULONG_MAX: u64 = u64::MAX;

const MPOL_NO_HEAP: u64 = 0x01;
const MPOL_NO_STACK: u64 = 0x02;
const MPOL_NO_BSS: u64 = 0x04;
const MPOL_SHM_PREMAP: u64 = 0x08;
const MPOL_DEFAULT: c_int = 0;
const MPOL_PREFERRED: c_int = 1;
const MPOL_BIND: c_int = 2;
const MPOL_INTERLEAVE: c_int = 3;
const PLD_MPOL_MAX: c_int = 4;

const MPOL_NODEMASK_NONE: i32 = 0;
const MPOL_NODEMASK_LOCAL: i32 = 1;
const MPOL_NODEMASK_NONLOCAL: i32 = 2;
const MPOL_NODEMASK_ALL: i32 = 3;

const EINVAL: i32 = 22;
const ENOENT: i32 = 2;
const EBADF: i32 = 9;
const ENOEXEC: i32 = 8;
const EFAULT: i32 = 14;
const ENOMEM: i32 = 12;
const ENAMETOOLONG: i32 = 36;
const ELOOP: i32 = 40;
const EINTR: i32 = 4;
const EAGAIN: i32 = 11;
const ESRCH: i32 = 3;
const ERANGE: i32 = 34;
const ENOSYS: i32 = 38;
const X_OK: c_int = 1;
const SC_OPEN_MAX: c_int = 4;
const F_GETFD: c_int = 1;
const FD_CLOEXEC: c_int = 1;
const SIGKILL: c_int = 9;
const SIGSTOP: c_int = 19;
const SIGCHLD: c_int = 17;
const SIGTSTP: c_int = 20;
const SIGTTIN: c_int = 21;
const SIGTTOU: c_int = 22;
const SIGURG: c_int = 23;
const SIGCONT: c_int = 18;
const SIG_DFL_PTR: c_ulong = 0;
const SIG_IGN_PTR: c_ulong = 1;
const SFD_CLOEXEC: c_int = 0o2000000;
const SFD_NONBLOCK: c_int = 0o4000;
const O_CLOEXEC: c_int = 0o2000000;
const O_NONBLOCK: c_int = 0o4000;
const AT_FDCWD: c_int = -100;
const AT_EMPTY_PATH: c_int = 0x1000;
const AT_SYMLINK_NOFOLLOW: c_int = 0x100;
const SIGNALFD_SIGINFO_SIZE: usize = 128;
const SEEK_SET: c_int = 0;
const SEEK_CUR: c_int = 1;
const EI_NIDENT: usize = 16;
const ELFMAG: &[u8] = b"\x7fELF";
const PT_LOAD: u32 = 1;
const PT_INTERP: u32 = 3;
const PT_PHDR: u32 = 6;
const PT_GNU_STACK: u32 = 0x6474e551;
const ET_DYN: u16 = 3;
const PF_X: u32 = 1;
const PF_W: u32 = 2;
const PF_R: u32 = 4;
const PROT_NONE: c_int = 0;
const PROT_READ: c_int = 1;
const PROT_WRITE: c_int = 2;
const PROT_EXEC: c_int = 4;
const WEXITED: c_int = 0x00000004;
const WNOWAIT: c_int = 0x01000000;
const MCEXEC_LINUX_SPAWN_ARG_MAX: usize = 256;
const MCEXEC_STACK_SIZE: u64 = 10 * 1024 * 1024;

static LD_MCK_SYSCALL_INTERCEPT: &[u8] = b"libmck_syscall_intercept.so";
static LD_SCHED_YIELD: &[u8] = b"libsched_yield.so.1.0.0";
static LD_QLFORT: &[u8] = b"libqlfort.so";
static PROC_PREFIX: &[u8] = b"/proc/";
static SYS_PREFIX: &[u8] = b"/sys/";
static DEV_XPMEM: &[u8] = b"/dev/xpmem";
static DEV_NULL_PATH: &[u8] = b"/dev/null\0";
static NONEXISTING_PATH: &[u8] = b"/nonexisting\0";
static LIBUTI: &[u8] = b"libuti.so";
static PROC_SELF_PREFIX: &[u8] = b"/proc/self";
static SYS_MCOS_PREFIX: &[u8] = b"/sys/devices/virtual/mcos/mcos";
static COKERNEL_PATH_ENV: &[u8] = b"COKERNEL_PATH\0";
static PATH_ENV: &[u8] = b"PATH\0";
static COKERNEL_EXEC_ROOT_ENV: &[u8] = b"COKERNEL_EXEC_ROOT\0";
static PROC_SELF_EXE: &[u8] = b"/proc/self/exe";
static MCKERNEL_RLIMIT_STACK_ENV: &[u8] = b"MCKERNEL_RLIMIT_STACK\0";
static MCKERNEL_LD_PRELOAD_ENV: &[u8] = b"MCKERNEL_LD_PRELOAD\0";
static UTI_CPU_SET_ENV: &[u8] = b"UTI_CPU_SET\0";
static FLIB_AFFINITY_ON_PROCESS_ENV: &[u8] = b"FLIB_AFFINITY_ON_PROCESS\0";
static FLIB_RANK_ON_NODE_ENV: &[u8] = b"FLIB_RANK_ON_NODE\0";
static FLIB_NUM_PROCESS_ON_NODE_ENV: &[u8] = b"FLIB_NUM_PROCESS_ON_NODE\0";
static OMP_NUM_THREADS_ENV: &[u8] = b"OMP_NUM_THREADS\0";
static OMPI_MCA_PLE_MEMORY_POLICY_ENV: &[u8] = b"OMPI_MCA_plm_ple_memory_allocation_policy\0";
static MCEXEC_ALT_ROOT_ENV: &[u8] = b"MCEXEC_ALT_ROOT\0";
static MCEXEC_DEFAULT_ALTROOT: &[u8] = b"/usr/linux-k1om-4.7/linux-k1om\0";
static LD_PRELOAD_ENVNAME_LITERAL: &[u8] = b"ld_preload_envname\0";
static OBJDUMP_RPATH_PREFIX: &[u8] = b"objdump -x ";
static OBJDUMP_RPATH_SUFFIX: &[u8] = b" | awk '/RPATH/ { print $2 }'";
static MCEXEC_USAGE_PREFIX: &[u8] = b"usage: ";
static MCEXEC_USAGE_WITH_ENVS: &[u8] = b" [-c target_core] [-n nr_partitions] [<-e ENV_NAME=value>...] [--mpol-threshold=N] [--enable-straight-map] [--extend-heap-by=N] [-s (--stack-premap=)[premap_size][,max]] [--mpol-no-heap] [--mpol-no-bss] [--mpol-no-stack] [--mpol-shm-premap] [--disable-sched-yield] [--enable-uti] [--uti-thread-rank=N] [--uti-use-last-cpu] [<mcos-id>] (program) [args...]\n";
static MCEXEC_USAGE_WITHOUT_ENVS: &[u8] = b" [-c target_core] [-n nr_partitions] [--mpol-threshold=N] [--enable-straight-map] [--extend-heap-by=N] [-s (--stack-premap=)[premap_size][,max]] [--mpol-no-heap] [--mpol-no-bss] [--mpol-no-stack] [--mpol-shm-premap] [--disable-sched-yield]  [--enable-uti] [--uti-thread-rank=N] [--uti-use-last-cpu] [<mcos-id>] (program) [args...]\n";
static RET_PERROR_TAG: &[u8] = b"ret\0";
static LOAD_PERROR_TAG: &[u8] = b"load\0";
static STRNCPY_FROM_USER_PERROR_TAG: &[u8] = b"strncpy_from_user:ioctl\0";
static PIPE2_FAILED_TAG: &[u8] = b"pipe2 failed:\0";
static DMA_PERROR_TAG: &[u8] = b"dma\0";
static READ_BINARY_MODE: &[u8] = b"rb\0";
static mut SEARCH_FILE_MODPATH: [u8; PATH_MAX] = [0; PATH_MAX];
static mut LOAD_INTERP_PATH: [u8; PATH_MAX + 1] = [0; PATH_MAX + 1];

const DIRENT32_OFF_OFFSET: usize = core::mem::size_of::<usize>();
const DIRENT32_RECLEN_OFFSET: usize = core::mem::size_of::<usize>() * 2;
const DIRENT32_NAME_OFFSET: usize = DIRENT32_RECLEN_OFFSET + core::mem::size_of::<u16>();
const DIRENT64_OFF_OFFSET: usize = core::mem::size_of::<u64>();
const DIRENT64_RECLEN_OFFSET: usize = core::mem::size_of::<u64>() + core::mem::size_of::<i64>();
const DIRENT64_NAME_OFFSET: usize =
    DIRENT64_RECLEN_OFFSET + core::mem::size_of::<u16>() + core::mem::size_of::<u8>();

unsafe extern "C" {
    static mut environ: *mut *mut u8;
    fn __errno_location() -> *mut c_int;
    fn getenv(name: *const u8) -> *mut u8;
    fn setenv(name: *const u8, value: *const u8, overwrite: c_int) -> c_int;
    fn access(path: *const u8, mode: c_int) -> c_int;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn perror(s: *const u8);
    fn fseek(stream: *mut c_void, offset: c_long, whence: c_int) -> c_int;
    fn fread(ptr: *mut c_void, size: usize, nmemb: usize, stream: *mut c_void) -> usize;
    fn ferror(stream: *mut c_void) -> c_int;
    fn feof(stream: *mut c_void) -> c_int;
    fn readlink(path: *const u8, buf: *mut u8, bufsiz: usize) -> isize;
    fn fopen(path: *const u8, mode: *const u8) -> *mut c_void;
    fn fclose(stream: *mut c_void) -> c_int;
    fn rewind(stream: *mut c_void);
    fn getline(lineptr: *mut *mut u8, n: *mut usize, stream: *mut c_void) -> isize;
    fn getcwd(buf: *mut u8, size: usize) -> *mut u8;
    fn lseek(fd: c_int, offset: c_long, whence: c_int) -> c_long;
    fn strdup(s: *const u8) -> *mut u8;
    fn getpid() -> c_int;
    fn getpgid(pid: c_int) -> c_int;
    fn syscall(number: c_long, ...) -> c_long;
    fn ptrace(request: c_int, ...) -> c_long;
    fn sysconf(name: c_int) -> c_long;
    fn fcntl(fd: c_int, cmd: c_int, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn pipe2(pipefd: *mut c_int, flags: c_int) -> c_int;
    fn free(ptr: *mut u8);
    fn malloc(size: usize) -> *mut u8;
    fn realloc(ptr: *mut u8, size: usize) -> *mut u8;
    fn fileno(stream: *mut c_void) -> c_int;
    fn pread(fd: c_int, buf: *mut c_void, count: usize, offset: c_long) -> isize;
    fn strcmp(s1: *const u8, s2: *const u8) -> i32;
    fn strlen(s: *const u8) -> usize;
    fn strtol(nptr: *const u8, endptr: *mut *mut u8, base: i32) -> i64;
    fn strtoul(nptr: *const u8, endptr: *mut *mut u8, base: i32) -> u64;
    fn posix_spawn(
        pid: *mut c_int,
        path: *const u8,
        file_actions: *const c_void,
        attrp: *const c_void,
        argv: *const *mut u8,
        envp: *const *mut u8,
    ) -> c_int;
    fn mcexec_altroot_bridge() -> *const u8;
    fn mcexec_search_file_path_too_long_bridge(root: *const u8, path: *const u8);
    fn mcexec_desc_num_sections_bridge(desc: *const c_void) -> c_int;
    fn mcexec_desc_cpu_bridge(desc: *const c_void) -> c_int;
    fn mcexec_desc_pid_bridge(desc: *const c_void) -> c_int;
    fn mcexec_desc_entry_bridge(desc: *const c_void) -> c_ulong;
    fn mcexec_desc_rprocess_bridge(desc: *const c_void) -> c_ulong;
    fn mcexec_desc_section_vaddr_bridge(desc: *const c_void, index: c_int) -> c_ulong;
    fn mcexec_desc_section_len_bridge(desc: *const c_void, index: c_int) -> c_ulong;
    fn mcexec_desc_section_remote_pa_bridge(desc: *const c_void, index: c_int) -> c_ulong;
    fn mcexec_desc_section_filesz_bridge(desc: *const c_void, index: c_int) -> c_ulong;
    fn mcexec_desc_section_offset_bridge(desc: *const c_void, index: c_int) -> c_ulong;
    fn mcexec_desc_section_fp_bridge(desc: *const c_void, index: c_int) -> *mut c_void;
    fn mcexec_transfer_seek_error_bridge();
    fn mcexec_transfer_access_error_bridge();
    fn mcexec_transfer_short_error_bridge();
    fn mcexec_transfer_seeked_bridge(offset: c_ulong, size: c_ulong);
    fn mcexec_load_shebang_find_error_bridge(path: *const u8);
    fn mcexec_load_shebang_load_error_bridge(path: *const u8);
    fn mcexec_load_desc_stat_size_bridge(filename: *const u8, size_out: *mut c_long) -> c_int;
    fn mcexec_load_desc_not_executable_bridge(filename: *const u8, error: c_int);
    fn mcexec_load_desc_zero_length_bridge(filename: *const u8);
    fn mcexec_load_desc_open_failed_bridge(filename: *const u8);
    fn mcexec_load_desc_header_failed_bridge(filename: *const u8);
    fn mcexec_load_desc_shebang_read_failed_bridge(filename: *const u8);
    fn mcexec_load_desc_open_exec_failed_bridge(filename: *const u8, ret: c_int, fd: c_int);
    fn mcexec_load_desc_publish_exec_path_bridge(path: *mut u8);
    fn mcexec_load_desc_strdup_failed_bridge();
    fn mcexec_load_desc_getcwd_failed_bridge();
    fn mcexec_load_desc_alloc_exec_path_failed_bridge();
    fn mcexec_load_desc_build_exec_path_failed_bridge();
    fn mcexec_load_desc_parse_elf_failed_bridge();
    fn mcexec_load_desc_interp_not_found_bridge(path: *const u8);
    fn mcexec_load_desc_interp_open_failed_bridge(path: *const u8);
    fn mcexec_load_desc_parse_interp_failed_bridge();
    fn mcexec_load_desc_sections_bridge(count: c_int);
    fn mcexec_program_load_desc_size_bridge() -> usize;
    fn mcexec_program_image_section_size_bridge() -> usize;
    fn mcexec_load_cannot_read_ehdr_bridge();
    fn mcexec_load_elfmag_mismatch_bridge();
    fn mcexec_load_phdr_failed_bridge(index: c_int);
    fn mcexec_load_too_large_interp_bridge();
    fn mcexec_load_cannot_read_interp_bridge();
    fn mcexec_load_alloc_desc_bridge(nsections: c_int) -> *mut c_void;
    fn mcexec_load_publish_main_section_bridge(
        desc: *mut c_void,
        index: c_int,
        vaddr: c_ulong,
        filesz: c_ulong,
        offset: c_ulong,
        len: c_ulong,
        prot: c_int,
        fp: *mut c_void,
    );
    fn mcexec_load_cred_bridge(desc: *mut c_void) -> *mut c_int;
    fn mcexec_load_clk_tck_bridge() -> c_long;
    fn mcexec_load_finalize_desc_bridge(
        desc: *mut c_void,
        pid: c_int,
        pgid: c_int,
        reloc: c_int,
        entry: c_ulong,
        at_phdr: c_ulong,
        at_phent: c_ulong,
        at_phnum: c_ulong,
        at_entry: c_ulong,
        at_clktck: c_ulong,
        stack_prot: c_int,
    );
    fn mcexec_load_realloc_failed_bridge(size: c_ulong);
    fn mcexec_load_pt_interp_on_interp_bridge();
    fn mcexec_desc_set_num_sections_bridge(desc: *mut c_void, count: c_int);
    fn mcexec_desc_set_entry_bridge(desc: *mut c_void, entry: c_ulong);
    fn mcexec_desc_set_interp_align_bridge(desc: *mut c_void, align: c_ulong);
    fn mcexec_desc_publish_interp_section_bridge(
        desc: *mut c_void,
        index: c_int,
        vaddr: c_ulong,
        filesz: c_ulong,
        offset: c_ulong,
        len: c_ulong,
        prot: c_int,
        fp: *mut c_void,
    );
    fn mcexec_load_section_log_bridge(
        index: c_int,
        vaddr: c_ulong,
        filesz: c_ulong,
        offset: c_ulong,
        len: c_ulong,
        prot: c_int,
    );
    fn mcexec_print_desc_intro_bridge(desc: *const c_void);
    fn mcexec_print_desc_main_bridge(cpu: c_int, pid: c_int, entry: c_ulong, rprocess: c_ulong);
    fn mcexec_print_desc_section_bridge(
        vaddr: c_ulong,
        len: c_ulong,
        remote_pa: c_ulong,
        filesz: c_ulong,
    );
    fn mcexec_print_flat_count_bridge(count: c_long);
    fn mcexec_print_flat_entry_bridge(entry: *const u8);
    fn mcexec_print_usage_add_envs_bridge() -> c_int;
    fn mcexec_print_usage_write_bridge(line: *const u8, len: usize);
    fn mcexec_atobytes_set_errno_bridge(value: c_int);
    fn mcexec_init_sigaction_set_master_tid_bridge(tid: c_int);
    fn mcexec_init_sigaction_install_bridge(sig: c_int);
    fn mcexec_act_sigaction_install_bridge(sig: c_int, ignored: c_int);
    fn mcexec_act_sigprocmask_apply_bridge(mask: c_ulong);
    fn mcexec_act_signalfd4_write_bridge(fd: c_int, info: *const c_void, len: usize) -> isize;
    fn mcexec_act_signalfd4_write_error_bridge();
    fn mcexec_sendsig_si_pid_bridge(siginfo: *const c_void) -> c_int;
    fn mcexec_sendsig_si_signo_bridge(siginfo: *const c_void) -> c_int;
    fn mcexec_sendsig_default_action_bridge(sig: c_int);
    fn mcexec_init_worker_threads_lock_init_bridge();
    fn mcexec_init_worker_threads_barrier_init_bridge(count: c_int);
    fn mcexec_init_worker_threads_reset_cpuid_bridge();
    fn mcexec_init_worker_threads_create_bridge() -> c_int;
    fn mcexec_init_worker_threads_wait_bridge();
    fn mcexec_init_worker_threads_error_bridge(ret: c_int);
    fn mcexec_process_thread_plan_flib_log_bridge(planned_nr_processes: c_int);
    fn mcexec_dma_mmap_bridge() -> *mut c_void;
    fn mcexec_dma_mlock_bridge(buf: *mut c_void) -> c_int;
    fn mcexec_dma_mmap_failed_bridge() -> !;
    fn mcexec_dma_mlock_failed_bridge() -> !;
    fn mcexec_create_ppd_bridge() -> c_int;
    fn mcexec_create_ppd_failed_bridge() -> !;
    fn mcexec_get_thp_disable_prctl_bridge() -> c_int;
    fn mcexec_numa_node_cpu_isset_bridge(node: c_int, cpu: c_int) -> c_int;
    fn mcexec_numa_local_cpu_log_bridge(cpu: c_int);
    fn mcexec_numa_node_cpu_log_bridge(cpu: c_int, node: c_int);
    fn mcexec_main_get_cpu_bridge() -> c_int;
    fn mcexec_main_get_nodes_bridge() -> c_int;
    fn mcexec_main_no_cpu_bridge();
    fn mcexec_main_no_numa_node_bridge();
    fn mcexec_main_cpu_alloc_size_bridge(cpu_count: c_int) -> usize;
    fn mcexec_main_alloc_nodes_error_bridge();
    fn mcexec_main_publish_topology_bridge(
        cpu_count: c_int,
        node_count: c_int,
        node_set_size: usize,
        nodes: *mut c_void,
    );
    fn mcexec_main_numa_node_zero_bridge(nodes: *mut c_void, node_set_size: usize, node_id: c_int);
    fn mcexec_main_node_cpu_exists_bridge(node_id: c_int, cpu: c_int) -> c_int;
    fn mcexec_main_numa_node_set_cpu_bridge(
        nodes: *mut c_void,
        node_set_size: usize,
        node_id: c_int,
        cpu: c_int,
    );
    fn mcexec_partition_get_cpuset_bridge(
        desc: *mut c_void,
        nr_processes: c_int,
        target_core: *mut c_int,
        process_rank: *mut c_int,
        mcexec_linux_numa: *mut c_int,
        ikc_mapped: *mut c_int,
    ) -> c_int;
    fn mcexec_partition_get_cpuset_failed_bridge();
    fn mcexec_partition_publish_cpu_rank_bridge(
        desc: *mut c_void,
        target_core: c_int,
        process_rank: c_int,
    );
    fn mcexec_partition_publish_rank_bridge(desc: *mut c_void, process_rank: c_int);
    fn mcexec_partition_rank_log_bridge(process_rank: c_int, target_core: c_int);
    fn mcexec_partition_sched_setaffinity_bridge() -> c_int;
    fn mcexec_partition_sched_setaffinity_warning_bridge();
    fn mcexec_partition_debug_ikc_binding_bridge();
    fn mcexec_partition_numa_run_bridge(mcexec_linux_numa: c_int) -> c_int;
    fn mcexec_partition_numa_run_warning_bridge(mcexec_linux_numa: c_int);
    fn mcexec_partition_debug_numa_binding_bridge();
    fn mcexec_desc_publish_mpol_base_bridge(
        desc: *mut c_void,
        profile: c_int,
        nr_processes: c_int,
        flags: c_ulong,
        threshold: c_ulong,
        heap_extension: c_ulong,
        pld_mpol_max: c_int,
    );
    fn mcexec_desc_apply_bind_nodes_bridge(desc: *mut c_void, nodes: *const u8);
    fn mcexec_desc_ompi_policy_log_bridge(mpol: *const u8);
    fn mcexec_desc_apply_ompi_policy_bridge(desc: *mut c_void, mode: c_int, nodemask_action: c_int);
    fn mcexec_desc_mpol_log_bridge(desc: *const c_void);
    fn mcexec_desc_publish_runtime_flags_bridge(
        desc: *mut c_void,
        enable_uti: c_int,
        uti_thread_rank: c_int,
        uti_use_last_cpu: c_int,
        thp_disable: c_int,
        straight_map: c_int,
        straight_map_threshold: c_ulong,
        enable_tofu: c_int,
        mcexec_flags: c_ulong,
    );
    fn mcexec_main_publish_mcosid_bridge(new_mcosid: c_int);
    fn mcexec_main_uti_unavailable_bridge(enable_uti: c_int) -> c_int;
    fn mcexec_main_overlay_lock_init_bridge();
    fn mcexec_main_load_desc_error_bridge(path: *const u8, ret: c_int);
    fn mcexec_desc_clear_flags_bridge(desc: *mut c_void);
    fn mcexec_opendev_mcosid_bridge() -> c_int;
    fn mcexec_opendev_dev_bridge() -> *mut u8;
    fn mcexec_opendev_dev_size_bridge() -> usize;
    fn mcexec_opendev_path_error_bridge();
    fn mcexec_opendev_open_bridge(path: *const u8) -> c_int;
    fn mcexec_opendev_open_error_bridge(path: *const u8);
    fn mcexec_opendev_publish_fd_bridge(value: c_int);
    fn mcexec_opendev_buildid_size_bridge() -> usize;
    fn mcexec_opendev_buildid_bridge() -> *const u8;
    fn mcexec_opendev_query_result_bridge() -> *mut u8;
    fn mcexec_opendev_query_buildid_bridge(target_fd: c_int, query_result: *mut u8) -> c_int;
    fn mcexec_opendev_query_error_bridge();
    fn mcexec_opendev_close_bridge(target_fd: c_int);
    fn mcexec_opendev_buildid_mismatch_bridge(buildid: *const u8, query_result: *const u8);
    fn mcexec_find_libdir_readlink_bridge(path: *mut u8, size: usize) -> isize;
    fn mcexec_find_libdir_popen_bridge(cmd: *const u8) -> *mut c_void;
    fn mcexec_find_libdir_getline_bridge(
        line: *mut *mut u8,
        linelen: *mut usize,
        filep: *mut c_void,
    ) -> isize;
    fn mcexec_find_libdir_pclose_bridge(filep: *mut c_void);
    fn mcexec_find_libdir_free_bridge(line: *mut u8);
    fn mcexec_find_libdir_readlink_failed_bridge(error: c_int);
    fn mcexec_find_libdir_objdump_failed_bridge(error: c_int);
    fn mcexec_find_libdir_rpath_not_found_bridge(error: c_int);
    fn mcexec_ld_preload_getenv_bridge(name: *const u8) -> *mut u8;
    fn mcexec_ld_preload_setenv_bridge(value: *const u8) -> c_int;
    fn mcexec_ld_preload_unsetenv_bridge() -> c_int;
    fn mcexec_ld_preload_enable_uti_bridge() -> c_int;
    fn mcexec_ld_preload_disable_sched_yield_bridge() -> c_int;
    fn mcexec_ld_preload_enable_qlmpi_bridge() -> c_int;
    fn mcexec_ld_preload_find_failed_bridge();
    fn mcexec_ld_preload_line_too_long_bridge();
    fn mcexec_ld_preload_setenv_failed_bridge();
    fn mcexec_ld_preload_debug_bridge(envbuf: *const u8);
    fn mcexec_main_page_size_bridge() -> c_ulong;
    fn mcexec_main_publish_page_altroot_bridge(page_size: c_ulong, altroot: *const u8);
    fn mcexec_create_worker_thread_alloc_bridge() -> *mut McexecThreadData;
    fn mcexec_create_worker_thread_alloc_error_bridge();
    fn mcexec_create_worker_thread_next_cpu_bridge() -> c_int;
    fn mcexec_create_worker_thread_lock_bridge() -> *mut c_void;
    fn mcexec_create_worker_thread_publish_bridge(
        tp: *mut McexecThreadData,
        tp_out: *mut *mut McexecThreadData,
    );
    fn mcexec_create_worker_thread_pthread_create_bridge(tp: *mut McexecThreadData) -> c_int;
    fn mcexec_join_all_threads_head_bridge() -> *mut McexecThreadData;
    fn mcexec_join_all_threads_join_bridge(tp: *mut McexecThreadData);
    fn mcexec_overlay_mcosid_bridge() -> c_int;
    fn mcexec_overlay_addfd_path_too_long_bridge();
    fn mcexec_overlay_addfd_publish_bridge(
        fd: c_int,
        linux_path: *const u8,
        mck_path: *const u8,
        pathlen: usize,
    ) -> c_int;
    fn mcexec_overlay_delfd_bridge(fd: c_int);
    fn mcexec_overlay_stat_exists_bridge(path: *const u8) -> c_int;
    fn mcexec_overlay_cpu_in_node_bridge(cpu: c_int, node: c_int) -> c_int;
    fn mcexec_overlay_enable_uti_bridge() -> c_int;
    fn mcexec_overlay_find_libdir_bridge(out: *mut u8, size: usize) -> c_int;
    fn mcexec_overlay_readlink_bridge(path: *const u8, out: *mut u8, size: usize) -> isize;
    fn mcexec_overlay_lstat_is_symlink_bridge(path: *const u8, is_symlink: *mut c_int) -> c_int;
    fn mcexec_overlay_stat_errno_bridge(path: *const u8) -> c_int;
    fn mcexec_overlay_considering_bridge(dirfd: c_int, path: *const u8);
    fn mcexec_overlay_fd_path_truncated_bridge(dirfd: c_int);
    fn mcexec_overlay_readlink_fd_failed_bridge(dirfd: c_int, error: c_int);
    fn mcexec_overlay_truncated_bridge(path: *const u8);
    fn mcexec_overlay_getcwd_failed_bridge(error: c_int);
    fn mcexec_overlay_glued_bridge(path: *const u8);
    fn mcexec_overlay_find_libdir_failed_bridge();
    fn mcexec_overlay_replaced_bridge(path: *const u8, mapped: *const u8);
    fn mcexec_overlay_trying_bridge(path: *const u8, error: c_int);
    fn mcexec_overlay_blacklisted_bridge(path: *const u8);
    fn mcexec_overlay_getdents_find_bridge(fd: c_int) -> *mut c_void;
    fn mcexec_overlay_getdents_hide_orig_bridge(ofd: *mut c_void) -> c_int;
    fn mcexec_overlay_getdents_linux_path_bridge(ofd: *mut c_void) -> *const u8;
    fn mcexec_overlay_getdents_pathlen_bridge(ofd: *mut c_void) -> usize;
    fn mcexec_overlay_getdents_mck_dirents_bridge(ofd: *mut c_void) -> *mut u8;
    fn mcexec_overlay_getdents_mck_size_bridge(ofd: *mut c_void) -> usize;
    fn mcexec_overlay_getdents_linux_dirents_bridge(ofd: *mut c_void) -> *mut u8;
    fn mcexec_overlay_getdents_linux_size_bridge(ofd: *mut c_void) -> usize;
    fn mcexec_overlay_getdents_mck_fd_bridge(ofd: *mut c_void) -> c_int;
    fn mcexec_overlay_getdents_linux_fd_bridge(ofd: *mut c_void) -> c_int;
    fn mcexec_overlay_getdents_append_mck_bridge(
        ofd: *mut c_void,
        dirp: *const u8,
        len: usize,
        is64: c_int,
    ) -> c_int;
    fn mcexec_overlay_getdents_append_linux_bridge(
        ofd: *mut c_void,
        dirp: *const u8,
        len: usize,
        is64: c_int,
        old_ret: c_int,
    ) -> c_int;
    fn mcexec_overlay_getdents_offset_bridge(offset: c_long);
    fn mcexec_overlay_getdents_upper_bridge(mck_ret: c_int, ret: c_int, count: u32);
    fn mcexec_overlay_getdents_lower_failed_bridge(error: c_int);
    fn mcexec_overlay_getdents_blacklisted_bridge(path: *const u8);
    fn mcexec_overlay_getdents_dupe_bridge(name: *const u8);
    fn mcexec_overlay_getdents_lower_bridge(linux_ret: c_int, ret: c_int, count: u32);
    fn mcexec_overlay_getdents_offset_too_large_bridge(
        offset: c_long,
        mck_size: usize,
        linux_size: usize,
    );
    fn mcexec_overlay_getdents_upper_small_bridge();
    fn mcexec_overlay_getdents_lower_small_bridge();
    fn mcexec_overlay_getdents_mck_size_log_bridge(
        size: usize,
        offset: c_long,
        len: c_int,
        count: u32,
    );
    fn mcexec_overlay_getdents_linux_size_log_bridge(
        size: usize,
        offset: c_long,
        len: c_int,
        count: u32,
    );
    fn mcexec_path_readlinkat_bridge(
        dirfd: c_int,
        path: *const u8,
        buf: *mut u8,
        size: usize,
    ) -> c_long;
    fn mcexec_path_readlink_bridge(path: *const u8, buf: *mut u8, size: usize) -> c_long;
    fn mcexec_path_fstatat_bridge(
        dirfd: c_int,
        path: *const u8,
        statbuf: *mut c_void,
        flags: c_int,
    ) -> c_long;
    fn mcexec_path_stat_bridge(path: *const u8, statbuf: *mut c_void) -> c_long;
    fn mcexec_path_faccessat_bridge(
        dirfd: c_int,
        path: *const u8,
        mode: c_int,
        flags: c_int,
    ) -> c_long;
    fn mcexec_path_access_bridge(path: *const u8, mode: c_int) -> c_long;
    fn mcexec_path_getxattr_bridge(
        path: *const u8,
        name: *const u8,
        value: *mut c_void,
        size: usize,
    ) -> c_long;
    fn mcexec_path_lgetxattr_bridge(
        path: *const u8,
        name: *const u8,
        value: *mut c_void,
        size: usize,
    ) -> c_long;
    fn mcexec_path_openat_log_bridge(dirfd: c_int, path: *const u8, tid: c_int);
    fn mcexec_path_open_log_bridge(path: *const u8);
    fn mcexec_path_openat_bridge(
        dirfd: c_int,
        path: *const u8,
        flags: c_ulong,
        mode: c_ulong,
    ) -> c_long;
    fn mcexec_path_open_bridge(path: *const u8, flags: c_ulong, mode: c_ulong) -> c_long;
    fn mcexec_cred_get_bridge(fd: c_int, arg: c_ulong);
    fn mcexec_cred_setfsuid_bridge(uid: c_ulong) -> c_long;
    fn mcexec_cred_setresuid_bridge(ruid: c_ulong, euid: c_ulong, suid: c_ulong) -> c_long;
    fn mcexec_cred_setreuid_bridge(ruid: c_ulong, euid: c_ulong) -> c_long;
    fn mcexec_cred_setuid_bridge(uid: c_ulong) -> c_long;
    fn mcexec_cred_setresgid_bridge(rgid: c_ulong, egid: c_ulong, sgid: c_ulong) -> c_long;
    fn mcexec_cred_setregid_bridge(rgid: c_ulong, egid: c_ulong) -> c_long;
    fn mcexec_cred_setgid_bridge(gid: c_ulong) -> c_long;
    fn mcexec_cred_setfsgid_bridge(gid: c_ulong) -> c_long;
    fn mcexec_do_generic_syscall_bridge(w: *const McexecSyscallWaitDesc) -> c_long;
    fn mcexec_do_generic_syscall_raw_bridge(w: *const McexecSyscallWaitDesc) -> c_long;
    fn mcexec_do_generic_syscall_start_bridge(number: c_ulong);
    fn mcexec_do_generic_syscall_done_bridge(number: c_ulong, ret: c_long);
    fn mcexec_sched_setaffinity_util_bridge(
        my_thread: *mut c_void,
        rp_rctx: c_ulong,
        remote_tid: c_int,
        pattr: c_ulong,
        uti_info: c_ulong,
        uti_desc: c_ulong,
    ) -> c_long;
    fn mcexec_util_thread_missing_desc_bridge();
    fn mcexec_util_thread_desc_log_bridge(desc: *mut c_void);
    fn mcexec_util_thread_barrier_init_bridge();
    fn mcexec_util_thread_create_worker_bridge(tp_out: *mut *mut McexecThreadData) -> c_int;
    fn mcexec_util_thread_worker_error_bridge(rc: c_int);
    fn mcexec_util_thread_barrier_wait_bridge();
    fn mcexec_util_thread_worker_tid_log_bridge(tid: c_int);
    fn mcexec_util_thread_intercept_warning_bridge(rc: c_int);
    fn mcexec_util_thread_get_ctx_error_bridge(errno_value: c_int);
    fn mcexec_util_thread_param_large_bridge();
    fn mcexec_util_thread_attr_error_bridge(errno_value: c_int);
    fn mcexec_util_thread_switch_ctx_bridge(
        desc: *mut McexecUtiSwitchCtxDesc,
        lctx: *mut c_void,
        rctx: *mut c_void,
    ) -> c_int;
    fn mcexec_util_thread_switch_failed_bridge(rc: c_int);
    fn mcexec_util_thread_switch_returned_bridge(rc: c_int);
    fn mcexec_sched_setaffinity_invalid_bridge(pid_arg: c_ulong);
    fn mcexec_perf_event_open_bridge() -> c_long;
    fn mcexec_clock_gettime_bridge(clock_id: c_int, tv: *mut McexecTimespec) -> c_long;
    fn mcexec_clock_gettime_log_bridge(sec: c_long, nsec: c_long);
    fn mcexec_kill_thread_bridge(tid: c_ulong, sig: c_ulong, my_thread: *mut c_void);
    fn mcexec_kill_thread_head_bridge() -> *mut McexecThreadData;
    fn mcexec_kill_thread_pthread_kill_bridge(tp: *mut McexecThreadData, sig: c_int) -> c_int;
    fn mcexec_kill_thread_not_found_bridge(tid: c_ulong, sig: c_int);
    fn mcexec_waitid_pid_bridge(pid: c_int, opt: c_int, errno_out: *mut c_int) -> c_int;
    fn mcexec_wait4_error_bridge(requested_pid: c_ulong, ret: c_int, errno_value: c_int);
    fn mcexec_gettid_alloc_error_bridge();
    fn mcexec_gettid_transfer_error_bridge();
    fn mcexec_debug_mlock_log_bridge(addr: c_ulong, len: c_ulong);
    fn mcexec_debug_mlock_bridge(addr: c_ulong, len: c_ulong) -> c_long;
    fn mcexec_swapout_unavailable_bridge();
    fn mcexec_linux_spawn_invalid_arg_bridge();
    fn mcexec_linux_spawn_invalid_exec_path_bridge();
    fn mcexec_linux_spawn_alloc_exec_path_failed_bridge();
    fn mcexec_linux_spawn_strncpy_failed_bridge();
    fn mcexec_linux_spawn_alloc_argv_failed_bridge(index: c_int);
    fn mcexec_linux_spawn_posix_spawn_failed_bridge(rc: c_int);
    fn mcexec_fork_sync_lock_bridge();
    fn mcexec_fork_sync_unlock_bridge();
    fn mcexec_fork_sync_munmap_bridge(fs: *mut c_void);
    fn mcexec_fork_sync_free_bridge(node: *mut c_void);
    fn mcexec_clone_alloc_fork_sync_bridge() -> *mut c_void;
    fn mcexec_clone_alloc_container_bridge() -> *mut c_void;
    fn mcexec_clone_fork_bridge() -> c_int;
    fn mcexec_clone_fork_failed_bridge();
    fn mcexec_clone_child_bridge(w: *const McexecSyscallWaitDesc, fs: *mut c_void) -> c_long;
    fn mcexec_clone_sem_trywait_bridge(fs: *mut c_void) -> c_int;
    fn mcexec_clone_waitpid_nohang_bridge(pid: c_int) -> c_int;
    fn mcexec_clone_sched_yield_bridge();
    fn mcexec_clone_child_after_fork_failed_bridge();
    fn mcexec_clone_sem_destroy_bridge(fs: *mut c_void);
    fn mcexec_exit_debug_bridge(status: c_ulong, cpu: c_int);
    fn mcexec_exit_isatty_bridge(target_fd: c_int) -> c_int;
    fn mcexec_exit_report_signal_bridge(sig: c_int);
    fn mcexec_exit_report_status_bridge(term: c_int);
    fn mcexec_exit_cmd_servers_bridge();
    fn mcexec_exit_replay_signal_bridge(sig: c_int);
    fn mcexec_exit_process_bridge(term: c_int);
    fn mcexec_execve2_alloc_desc_failed_bridge();
    fn mcexec_execve2_transfer_desc_failed_bridge();
    fn mcexec_execve2_transfer_desc_ok_bridge();
    fn mcexec_execve2_transfer_image_failed_bridge();
    fn mcexec_execve2_image_transferred_bridge();
    fn mcexec_execve2_close_exec_failed_bridge(ret: c_int);
    fn mcexec_main_prepare_image_failed_bridge();
    fn mcexec_main_flush_bridge();
    fn mcexec_main_cmd_servers_init_bridge() -> c_int;
    fn mcexec_main_worker_threads_failed_bridge(error: c_int);
    fn mcexec_main_start_image_failed_bridge();
    fn mcexec_flib_affinity_alloc_failed_bridge() -> !;
    fn mcexec_flib_affinity_log_bridge(old_affinity: *const u8, new_affinity: *const u8);
    fn mcexec_main_stack_parse_failed_bridge(parse_rc: c_int);
    fn mcexec_main_stack_publish_bridge(
        desc: *mut c_void,
        cur: c_ulong,
        max: c_ulong,
        prem: c_long,
    );
    fn mcexec_desc_snapshot_rlimits_bridge(desc: *mut c_void);
    fn mcexec_desc_publish_env_bridge(desc: *mut c_void, envs_len: c_int, envs: *mut u8);
    fn mcexec_desc_publish_args_cpu_bridge(
        desc: *mut c_void,
        args_len: c_ulong,
        args: *mut u8,
        cpu: c_int,
        vdso: c_int,
    );
    fn mcexec_execve1_enable_vdso_bridge() -> c_int;
    fn mcexec_execve1_rlim_cur_bridge() -> c_ulong;
    fn mcexec_execve1_rlim_max_bridge() -> c_ulong;
    fn mcexec_execve1_stack_premap_bridge() -> c_long;
    fn mcexec_desc_set_execve1_runtime_bridge(
        desc: *mut c_void,
        vdso: c_int,
        rlim_cur: c_ulong,
        rlim_max: c_ulong,
        prem: c_long,
    );
    fn mcexec_desc_set_args_len_bridge(desc: *mut c_void, args_len: c_ulong);
    fn mcexec_execve1_load_desc_ok_bridge(filename: *const u8, sections: c_int);
    fn mcexec_execve1_transfer_alloc_failed_bridge(filename: *const u8);
    fn mcexec_execve1_transfer_failed_bridge(filename: *const u8);
    fn mcexec_execve1_transfer_ok_bridge(filename: *const u8);
    fn mcexec_execve_invalid_phase_bridge();
    fn mcexec_main_load_stack_rlimit_bridge(cur: *mut c_ulong, max: *mut c_ulong) -> c_int;
    fn mcexec_main_reduce_stack_failed_bridge();
    fn mcexec_reduce_stack_newval_overflow_bridge();
    fn mcexec_reduce_stack_setenv_bridge(value: *const u8) -> c_int;
    fn mcexec_reduce_stack_setenv_failed_bridge();
    fn mcexec_reduce_stack_setrlimit_bridge(cur: u64, max: u64) -> c_int;
    fn mcexec_reduce_stack_setrlimit_failed_bridge();
    fn mcexec_reduce_stack_readlink_bridge(path: *mut u8, size: usize) -> isize;
    fn mcexec_reduce_stack_readlink_failed_bridge();
    fn mcexec_reduce_stack_execv_bridge(path: *const u8, argv: *mut *mut u8) -> c_int;
    fn mcexec_reduce_stack_execv_failed_bridge();
    fn mcexec_main_loop_log_syscall_bridge(cpu: c_int, number: c_long);
    fn mcexec_main_loop_timeout_bridge();
    fn mcexec_main_loop_thread_barrier_wait_bridge(barrier: *mut c_void) -> c_int;
    fn mcexec_main_loop_is_child_bridge() -> c_int;
    fn mcexec_lookup_lstat_errno_bridge(path: *const u8) -> c_int;
    fn mcexec_lookup_array_too_small_bridge();
    fn mcexec_lookup_stat_error_bridge(path: *const u8, error: c_int);
    fn mcexec_lookup_not_found_bridge(filename: *const u8);
    fn mcexec_lookup_success_bridge(path: *const u8);
    fn mcexec_add_env_list_invalid_bridge(add_string: *const u8);
    fn mcexec_main_publish_args_bridge(argc: c_int, argv: *mut *mut u8);
    fn mcexec_main_state_ptrs_bridge(state: *mut McexecMainStatePtrs);
    fn mcexec_main_personality_bridge(argv: *mut *mut u8) -> c_int;
    fn mcexec_main_next_option_bridge(argc: c_int, argv: *mut *mut u8) -> c_int;
    fn mcexec_main_optarg_bridge() -> *mut u8;
    fn mcexec_main_optind_bridge() -> c_int;
    fn mcexec_main_invalid_option_bridge(opt: c_int, argv: *mut *mut u8);
    fn mcexec_main_stack_debug_bridge(prem: c_long, max: c_long);
    fn mcexec_main_thread_plan_error_bridge();
    fn mcexec_main_bind_mount_bridge() -> c_int;
    fn exit(status: c_int) -> !;

    #[link_name = "fd"]
    static mut MCEXEC_FD: c_int;
    #[link_name = "dma_buf"]
    static mut MCEXEC_DMA_BUF: *mut u8;
    #[link_name = "page_size"]
    static mut MCEXEC_PAGE_SIZE: c_ulong;
    #[link_name = "page_mask"]
    static mut MCEXEC_PAGE_MASK: c_ulong;
    #[link_name = "ncpu"]
    static mut MCEXEC_NCPU: c_int;
    #[link_name = "nnodes"]
    static mut MCEXEC_NNODES: c_int;
    #[link_name = "n_threads"]
    static mut MCEXEC_N_THREADS: c_int;
    #[link_name = "thread_data"]
    static mut MCEXEC_THREAD_DATA: *mut McexecThreadData;
    #[link_name = "fork_sync_top"]
    static mut MCEXEC_FORK_SYNC_TOP: *mut ForkSyncContainer;
}

#[repr(C)]
struct McexecMainStatePtrs {
    nr_processes: *mut c_int,
    nr_threads: *mut c_int,
    mpol_threshold: *mut c_ulong,
    heap_extension: *mut c_ulong,
    straight_map_threshold: *mut c_ulong,
    stack_premap: *mut c_long,
    stack_max: *mut c_long,
    uti_thread_rank: *mut c_int,
    mcexec_flags: *mut c_ulong,
    mpol_bind_nodes: *mut *mut u8,
    enable_uti: *mut c_int,
    enable_vdso: *mut c_int,
    profile: *mut c_int,
    mpol_no_heap: *mut c_int,
    mpol_no_stack: *mut c_int,
    mpol_no_bss: *mut c_int,
    mpol_shm_premap: *mut c_int,
    no_bind_ikc_map: *mut c_int,
    straight_map: *mut c_int,
    uti_use_last_cpu: *mut c_int,
    enable_tofu: *mut c_int,
    rlim_cur: *mut c_ulong,
    rlim_max: *mut c_ulong,
}

#[repr(C)]
pub struct SyscallArgs {
    r15: u64,
    r14: u64,
    r13: u64,
    r12: u64,
    rbp: u64,
    rbx: u64,
    r11: u64,
    r10: u64,
    r9: u64,
    r8: u64,
    rax: u64,
    rcx: u64,
    rdx: u64,
    rsi: u64,
    rdi: u64,
    orig_rax: u64,
    rip: u64,
    cs: u64,
    eflags: u64,
    rsp: u64,
    ss: u64,
    fs_base: u64,
    gs_base: u64,
    ds: u64,
    es: u64,
    fs: u64,
    gs: u64,
}

#[repr(C)]
pub struct McexecListHead {
    next: *mut McexecListHead,
    prev: *mut McexecListHead,
}

const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;

#[repr(C)]
struct SyscallLoadDesc {
    cpu: c_ulong,
    src: c_ulong,
    dest: c_ulong,
    size: c_ulong,
}

#[repr(C)]
struct SyscallRetDesc {
    cpu: c_long,
    ret: c_long,
    src: c_ulong,
    dest: c_ulong,
    size: c_ulong,
}

#[repr(C)]
struct StrncpyFromUserDesc {
    dest: *mut c_void,
    src: *mut c_void,
    n: c_ulong,
    result: c_long,
}

#[repr(C)]
struct RemoteTransfer {
    rphys: c_ulong,
    userp: *mut c_void,
    size: c_ulong,
    direction: u8,
}

#[repr(C)]
struct Elf64Ehdr {
    e_ident: [u8; EI_NIDENT],
    e_type: u16,
    e_machine: u16,
    e_version: u32,
    e_entry: u64,
    e_phoff: u64,
    e_shoff: u64,
    e_flags: u32,
    e_ehsize: u16,
    e_phentsize: u16,
    e_phnum: u16,
    e_shentsize: u16,
    e_shnum: u16,
    e_shstrndx: u16,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct Elf64Phdr {
    p_type: u32,
    p_flags: u32,
    p_offset: u64,
    p_vaddr: u64,
    p_paddr: u64,
    p_filesz: u64,
    p_memsz: u64,
    p_align: u64,
}

#[repr(C)]
struct McexecSignalDesc {
    cpu: c_int,
    pid: c_int,
    tid: c_int,
    sig: c_int,
    info: [u8; 128],
}

#[repr(C)]
struct McexecSyscallStruct {
    number: c_int,
    args: [c_ulong; 6],
    ret: c_ulong,
    uti_info: c_ulong,
}

#[repr(C)]
struct McexecUtiDesc {
    lctx: [u8; 4096],
    rctx: [u8; 4096],
    mck_tid: c_int,
    key: c_ulong,
    pid: c_int,
    tid: c_int,
    uti_info: c_ulong,
    fd: c_int,
    syscall_stack: [McexecSyscallStruct; 16],
    syscall_stack_top: c_int,
    syscalls: [c_long; 512],
    syscalls2: [c_long; 512],
    start_syscall_intercept: c_int,
}

#[repr(C)]
struct McexecUtiGetCtxDesc {
    rp_rctx: c_ulong,
    rctx: *mut c_void,
    lctx: *mut c_void,
    uti_refill_tid: c_int,
    key: c_ulong,
}

#[repr(C)]
struct McexecUtiSwitchCtxDesc {
    rctx: *mut c_void,
    lctx: *mut c_void,
}

#[repr(C)]
struct McexecUtiAttrDesc {
    phys_attr: c_ulong,
    uti_cpu_set_str: *mut u8,
    uti_cpu_set_len: usize,
}

#[repr(C)]
pub struct McexecSyscallRequest {
    rtid: c_int,
    ttid: c_int,
    valid: c_ulong,
    number: c_ulong,
    args: [c_ulong; 6],
}

#[repr(C)]
pub struct McexecSyscallWaitDesc {
    cpu: c_ulong,
    sr: McexecSyscallRequest,
    pid: c_int,
}

#[repr(C)]
struct McexecSigfd {
    next: *mut McexecSigfd,
    sigpipe: [c_int; 2],
}

#[repr(C)]
struct McexecTimespec {
    tv_sec: c_long,
    tv_nsec: c_long,
}

static mut SIGFDTOP: *mut McexecSigfd = core::ptr::null_mut();

#[no_mangle]
pub unsafe extern "C" fn gettid() -> c_int {
    unsafe { syscall(SYS_GETTID) as c_int }
}

#[no_mangle]
pub unsafe extern "C" fn tgkill(tgid: c_int, tid: c_int, sig: c_int) -> c_int {
    unsafe { syscall(SYS_TGKILL, tgid, tid, sig) as c_int }
}

#[no_mangle]
pub unsafe extern "C" fn do_syscall_return(
    fd: c_int,
    cpu: c_int,
    ret: c_long,
    _n: c_int,
    src: c_ulong,
    dest: c_ulong,
    sz: c_ulong,
) {
    let desc = SyscallRetDesc {
        cpu: cpu as c_long,
        ret,
        src,
        dest,
        size: sz,
    };

    if unsafe {
        ioctl(
            fd,
            MCEXEC_UP_RET_SYSCALL,
            &desc as *const SyscallRetDesc as c_ulong,
        )
    } != 0
    {
        unsafe { perror(RET_PERROR_TAG.as_ptr()) };
    }
}

#[no_mangle]
pub unsafe extern "C" fn do_syscall_load(
    fd: c_int,
    cpu: c_int,
    dest: c_ulong,
    src: c_ulong,
    sz: c_ulong,
) {
    let desc = SyscallLoadDesc {
        cpu: cpu as c_ulong,
        src,
        dest,
        size: sz,
    };

    if unsafe {
        ioctl(
            fd,
            MCEXEC_UP_LOAD_SYSCALL,
            &desc as *const SyscallLoadDesc as c_ulong,
        )
    } != 0
    {
        unsafe { perror(LOAD_PERROR_TAG.as_ptr()) };
    }
}

#[no_mangle]
pub unsafe extern "C" fn do_strncpy_from_user(
    fd: c_int,
    dest: *mut c_void,
    src: *mut c_void,
    n: c_ulong,
) -> c_long {
    let mut desc = StrncpyFromUserDesc {
        dest,
        src,
        n,
        result: 0,
    };

    let ret = unsafe {
        ioctl(
            fd,
            MCEXEC_UP_STRNCPY_FROM_USER,
            &mut desc as *mut StrncpyFromUserDesc as c_ulong,
        )
    };
    if ret != 0 {
        let errno = unsafe { *__errno_location() };
        unsafe { perror(STRNCPY_FROM_USER_PERROR_TAG.as_ptr()) };
        return -(errno as c_long);
    }

    desc.result
}

#[no_mangle]
pub unsafe extern "C" fn close_cloexec_fds(mcos_fd: c_int) -> c_int {
    let max_fd = unsafe { sysconf(SC_OPEN_MAX) };
    let mut fd: c_int = 0;

    while (fd as c_long) < max_fd {
        if fd != mcos_fd {
            let flags = unsafe { fcntl(fd, F_GETFD, 0) };
            if flags & FD_CLOEXEC != 0 {
                unsafe { close(fd) };
            }
        }
        fd += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn init_sigaction() {
    unsafe { mcexec_init_sigaction_set_master_tid_bridge(gettid()) };

    let mut sig: c_int = 1;
    while sig <= 64 {
        if sig != SIGKILL
            && sig != SIGSTOP
            && sig != SIGCHLD
            && sig != SIGTSTP
            && sig != SIGTTIN
            && sig != SIGTTOU
        {
            unsafe { mcexec_init_sigaction_install_bridge(sig) };
        }
        sig += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn sendsig(sig: c_int, siginfo: *mut c_void, context: *mut c_void) {
    let not_uti = unsafe { ioctl(MCEXEC_FD, MCEXEC_UP_SIG_THREAD, 1 as c_ulong) };
    let pid = unsafe { getpid() };
    let tid = unsafe { gettid() };
    let si_pid = unsafe { mcexec_sendsig_si_pid_bridge(siginfo) };
    let si_signo = unsafe { mcexec_sendsig_si_signo_bridge(siginfo) };

    if si_pid == pid && si_signo == SIGURG {
        unsafe {
            if not_uti == 0 {
                ioctl(MCEXEC_FD, MCEXEC_UP_SIG_THREAD, 0 as c_ulong);
            }
        }
        return;
    }

    if si_signo == SIGCHLD {
        unsafe {
            if not_uti == 0 {
                ioctl(MCEXEC_FD, MCEXEC_UP_SIG_THREAD, 0 as c_ulong);
            }
        }
        return;
    }

    let mut tp = unsafe { MCEXEC_THREAD_DATA };
    while !tp.is_null() {
        let thread = unsafe { &*tp };
        if si_pid == pid && thread.tid == tid {
            if thread.terminate != 0 {
                unsafe {
                    if not_uti == 0 {
                        ioctl(MCEXEC_FD, MCEXEC_UP_SIG_THREAD, 0 as c_ulong);
                    }
                }
                return;
            }
            break;
        }
        if si_pid != pid && thread.remote_tid == tid {
            if thread.terminate != 0 {
                unsafe {
                    if not_uti == 0 {
                        ioctl(MCEXEC_FD, MCEXEC_UP_SIG_THREAD, 0 as c_ulong);
                    }
                }
                return;
            }
            break;
        }
        tp = thread.next;
    }

    let (remote_tid, cpu) = if tp.is_null() {
        (-1, 0)
    } else {
        let thread = unsafe { &*tp };
        (thread.remote_tid, thread.remote_cpu)
    };

    if not_uti != 0 {
        let mut desc = McexecSignalDesc {
            cpu,
            pid,
            tid: remote_tid,
            sig,
            info: [0; 128],
        };
        unsafe {
            core::ptr::copy_nonoverlapping(siginfo.cast::<u8>(), desc.info.as_mut_ptr(), 128);
        }
        if unsafe {
            ioctl(
                MCEXEC_FD,
                MCEXEC_UP_SEND_SIGNAL,
                &desc as *const McexecSignalDesc as c_ulong,
            )
        } != 0
        {
            unsafe {
                close(MCEXEC_FD);
                exit(1);
            }
        }
    } else {
        let mut param = McexecSyscallStruct {
            number: SYS_RT_SIGACTION,
            args: [0; 6],
            ret: 0,
            uti_info: 0,
        };
        param.args[0] = sig as c_ulong;
        let rc = unsafe {
            ioctl(
                MCEXEC_FD,
                MCEXEC_UP_SYSCALL_THREAD,
                &mut param as *mut McexecSyscallStruct as c_ulong,
            )
        };
        if rc == -1 {
        } else if param.ret == SIG_IGN_PTR {
        } else if param.ret == SIG_DFL_PTR {
            if sig != SIGCHLD && sig != SIGURG && sig != SIGCONT {
                unsafe { mcexec_sendsig_default_action_bridge(sig) };
            }
        } else {
            unsafe {
                ioctl(MCEXEC_FD, MCEXEC_UP_SIG_THREAD, 0 as c_ulong);
                let handler: unsafe extern "C" fn(c_int, *mut c_void, *mut c_void) =
                    core::mem::transmute(param.ret as usize);
                handler(sig, siginfo, context);
                ioctl(MCEXEC_FD, MCEXEC_UP_SIG_THREAD, 1 as c_ulong);
            }
        }
    }

    unsafe {
        if not_uti == 0 {
            ioctl(MCEXEC_FD, MCEXEC_UP_SIG_THREAD, 0 as c_ulong);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn init_worker_threads(_fd: c_int) -> c_int {
    let thread_count = unsafe { MCEXEC_N_THREADS };

    unsafe {
        mcexec_init_worker_threads_lock_init_bridge();
        mcexec_init_worker_threads_barrier_init_bridge(thread_count + 2);
        mcexec_init_worker_threads_reset_cpuid_bridge();
    }

    let mut i: c_int = 0;
    while i <= thread_count {
        let ret = unsafe { mcexec_init_worker_threads_create_bridge() };
        if ret != 0 {
            unsafe { mcexec_init_worker_threads_error_bridge(ret) };
            return -ret;
        }
        i += 1;
    }

    unsafe { mcexec_init_worker_threads_wait_bridge() };
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_setup_dma_ppd_body() {
    let mapped = unsafe { mcexec_dma_mmap_bridge() };
    if mapped as isize == -1 {
        unsafe { mcexec_dma_mmap_failed_bridge() };
    }

    unsafe {
        MCEXEC_DMA_BUF = mapped as *mut u8;
    }

    if unsafe { mcexec_dma_mlock_bridge(mapped) } != 0 {
        unsafe { mcexec_dma_mlock_failed_bridge() };
    }

    if unsafe { mcexec_create_ppd_bridge() } != 0 {
        unsafe { mcexec_create_ppd_failed_bridge() };
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_get_thp_disable_body() -> c_int {
    let ret = unsafe { mcexec_get_thp_disable_prctl_bridge() };
    if ret < 0 {
        0
    } else {
        ret
    }
}

unsafe fn signalfd_find(fd: c_int) -> (*mut McexecSigfd, *mut McexecSigfd) {
    let mut previous = core::ptr::null_mut();
    let mut current = unsafe { SIGFDTOP };

    while !current.is_null() {
        if unsafe { (*current).sigpipe[0] } == fd {
            return (previous, current);
        }
        previous = current;
        current = unsafe { (*current).next };
    }

    (previous, core::ptr::null_mut())
}

#[no_mangle]
pub unsafe extern "C" fn act_signalfd4(w: *const McexecSyscallWaitDesc) -> c_long {
    let mode = unsafe { (*w).sr.args[0] } as c_int;

    match mode {
        0 => {
            let sfd = unsafe { malloc(core::mem::size_of::<McexecSigfd>()) as *mut McexecSigfd };
            if sfd.is_null() {
                return -12;
            }
            unsafe {
                zero_bytes(sfd.cast::<u8>(), core::mem::size_of::<McexecSigfd>());
            }

            let tmp = unsafe { (*w).sr.args[1] } as c_int;
            let mut flags = 0;
            if tmp & SFD_NONBLOCK != 0 {
                flags |= O_NONBLOCK;
            }
            if tmp & SFD_CLOEXEC != 0 {
                flags |= O_CLOEXEC;
            }

            if unsafe { pipe2((*sfd).sigpipe.as_mut_ptr(), flags) } < 0 {
                unsafe { perror(PIPE2_FAILED_TAG.as_ptr()) };
                return -1;
            }

            unsafe {
                (*sfd).next = SIGFDTOP;
                SIGFDTOP = sfd;
                (*sfd).sigpipe[0] as c_long
            }
        }
        1 => {
            let tmp = unsafe { (*w).sr.args[1] } as c_int;
            let (previous, sfd) = unsafe { signalfd_find(tmp) };
            if sfd.is_null() {
                return -(EBADF as c_long);
            }

            unsafe {
                if previous.is_null() {
                    SIGFDTOP = (*sfd).next;
                } else {
                    (*previous).next = (*sfd).next;
                }
                close((*sfd).sigpipe[0]);
                close((*sfd).sigpipe[1]);
                free(sfd.cast::<u8>());
            }
            0
        }
        2 => {
            let tmp = unsafe { (*w).sr.args[1] } as c_int;
            let (_, sfd) = unsafe { signalfd_find(tmp) };
            if sfd.is_null() {
                return -(EBADF as c_long);
            }

            let info = unsafe { (*w).sr.args[2] as *const c_void };
            if unsafe {
                mcexec_act_signalfd4_write_bridge((*sfd).sigpipe[1], info, SIGNALFD_SIGINFO_SIZE)
            } != SIGNALFD_SIGINFO_SIZE as isize
            {
                unsafe { mcexec_act_signalfd4_write_error_bridge() };
                return -(EBADF as c_long);
            }
            0
        }
        _ => 0,
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_sigaction(w: *const McexecSyscallWaitDesc) {
    let sig = unsafe { (*w).sr.args[0] } as c_int;
    if sig == SIGCHLD || sig == SIGURG {
        return;
    }

    let ignored = if unsafe { (*w).sr.args[1] } == SIG_IGN_PTR {
        1
    } else {
        0
    };
    unsafe { mcexec_act_sigaction_install_bridge(sig, ignored) };
}

#[no_mangle]
pub unsafe extern "C" fn act_sigprocmask(w: *const McexecSyscallWaitDesc) {
    let mask = unsafe { (*w).sr.args[0] };
    unsafe { mcexec_act_sigprocmask_apply_bridge(mask) };
}

#[no_mangle]
pub unsafe extern "C" fn act_signalfd4_syscall(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) {
    let ret = unsafe { act_signalfd4(w) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_rt_sigaction(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    unsafe {
        act_sigaction(w);
        do_syscall_return(fd, cpu, 0, 0, 0, 0, 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_rt_sigprocmask(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) {
    unsafe {
        act_sigprocmask(w);
        do_syscall_return(fd, cpu, 0, 0, 0, 0, 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_setfsuid(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let ret = if mcexec_setfsuid_needs_cred_result(unsafe { (*w).sr.args[1] }) != 0 {
        unsafe { mcexec_cred_get_bridge(fd, (*w).sr.args[0]) };
        0
    } else {
        unsafe { mcexec_cred_setfsuid_bridge((*w).sr.args[0]) }
    };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_setresuid(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let ret =
        unsafe { mcexec_cred_setresuid_bridge((*w).sr.args[0], (*w).sr.args[1], (*w).sr.args[2]) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_setreuid(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let ret = unsafe { mcexec_cred_setreuid_bridge((*w).sr.args[0], (*w).sr.args[1]) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_setuid(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let ret = unsafe { mcexec_cred_setuid_bridge((*w).sr.args[0]) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_setresgid(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let ret =
        unsafe { mcexec_cred_setresgid_bridge((*w).sr.args[0], (*w).sr.args[1], (*w).sr.args[2]) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_setregid(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let ret = unsafe { mcexec_cred_setregid_bridge((*w).sr.args[0], (*w).sr.args[1]) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_setgid(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let ret = unsafe { mcexec_cred_setgid_bridge((*w).sr.args[0]) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_setfsgid(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let ret = unsafe { mcexec_cred_setfsgid_bridge((*w).sr.args[0]) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_close(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let remote_fd = unsafe { (*w).sr.args[0] };
    let mut ret = mcexec_close_plan_result(remote_fd, fd);
    if ret == 0 {
        ret = unsafe { mcexec_do_generic_syscall_bridge(w) };
    }
    unsafe {
        overlay_delfd(remote_fd as c_int);
        do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_do_generic_syscall_body(w: *const McexecSyscallWaitDesc) -> c_long {
    let number = unsafe { (*w).sr.number };
    unsafe { mcexec_do_generic_syscall_start_bridge(number) };
    let ret = unsafe { mcexec_do_generic_syscall_raw_bridge(w) };
    let shaped = mcexec_errno_return_result(ret, unsafe { *__errno_location() });
    unsafe { mcexec_do_generic_syscall_done_bridge(number, shaped) };
    shaped
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_body(
    _my_thread: *mut McexecThreadData,
    rp_rctx: c_ulong,
    remote_tid: c_int,
    pattr: c_ulong,
    uti_info: c_ulong,
    uti_desc_arg: c_ulong,
) -> c_long {
    let uti_desc = uti_desc_arg as *mut McexecUtiDesc;
    if uti_desc.is_null() {
        unsafe { mcexec_util_thread_missing_desc_bridge() };
        return -(EINVAL as c_long);
    }
    unsafe { mcexec_util_thread_desc_log_bridge(uti_desc as *mut c_void) };

    unsafe { mcexec_util_thread_barrier_init_bridge() };
    let mut tp: *mut McexecThreadData = core::ptr::null_mut();
    let mut rc = unsafe { mcexec_util_thread_create_worker_bridge(&mut tp) };
    if rc != 0 {
        unsafe { mcexec_util_thread_worker_error_bridge(rc) };
        return -(EINVAL as c_long);
    }
    unsafe { mcexec_util_thread_barrier_wait_bridge() };

    let worker_tid = if tp.is_null() {
        0
    } else {
        unsafe { (*tp).tid }
    };
    unsafe { mcexec_util_thread_worker_tid_log_bridge(worker_tid) };

    unsafe {
        (*uti_desc).fd = MCEXEC_FD;
    }

    rc = unsafe { syscall(888) as c_int };
    if rc != -1 {
        unsafe { mcexec_util_thread_intercept_warning_bridge(rc) };
    }

    let mut get_ctx_desc = McexecUtiGetCtxDesc {
        rp_rctx,
        rctx: unsafe { (*uti_desc).rctx.as_mut_ptr() as *mut c_void },
        lctx: unsafe { (*uti_desc).lctx.as_mut_ptr() as *mut c_void },
        uti_refill_tid: worker_tid,
        key: 0,
    };

    rc = unsafe {
        ioctl(
            MCEXEC_FD,
            MCEXEC_UP_UTI_GET_CTX,
            &mut get_ctx_desc as *mut McexecUtiGetCtxDesc as c_ulong,
        )
    };
    if rc != 0 {
        let errno_value = unsafe { *__errno_location() };
        unsafe { mcexec_util_thread_get_ctx_error_bridge(errno_value) };
        return -(errno_value as c_long);
    }

    unsafe {
        (*uti_desc).mck_tid = remote_tid;
        (*uti_desc).key = get_ctx_desc.key;
        (*uti_desc).pid = getpid();
        (*uti_desc).tid = gettid();
        (*uti_desc).uti_info = uti_info;
    }

    if core::mem::size_of::<McexecSyscallStruct>() * 11 > unsafe { MCEXEC_PAGE_SIZE as usize } {
        unsafe { mcexec_util_thread_param_large_bridge() };
        return -(ENOMEM as c_long);
    }

    if pattr != 0 {
        let cpu_set = unsafe { getenv(UTI_CPU_SET_ENV.as_ptr()) };
        let cpu_set_len = if cpu_set.is_null() {
            0
        } else {
            unsafe { strlen(cpu_set as *const u8) + 1 }
        };
        let mut attr_desc = McexecUtiAttrDesc {
            phys_attr: pattr,
            uti_cpu_set_str: cpu_set,
            uti_cpu_set_len: cpu_set_len,
        };

        rc = unsafe {
            ioctl(
                MCEXEC_FD,
                MCEXEC_UP_UTI_ATTR,
                &mut attr_desc as *mut McexecUtiAttrDesc as c_ulong,
            )
        };
        if rc != 0 {
            let errno_value = unsafe { *__errno_location() };
            unsafe { mcexec_util_thread_attr_error_bridge(errno_value) };
            return -(errno_value as c_long);
        }
    }

    unsafe {
        (*uti_desc).start_syscall_intercept = 1;
    }

    let mut switch_ctx_desc = McexecUtiSwitchCtxDesc {
        rctx: unsafe { (*uti_desc).rctx.as_mut_ptr() as *mut c_void },
        lctx: unsafe { (*uti_desc).lctx.as_mut_ptr() as *mut c_void },
    };
    rc = unsafe {
        mcexec_util_thread_switch_ctx_bridge(
            &mut switch_ctx_desc,
            (*uti_desc).lctx.as_mut_ptr() as *mut c_void,
            (*uti_desc).rctx.as_mut_ptr() as *mut c_void,
        )
    };
    if rc < 0 {
        unsafe { mcexec_util_thread_switch_failed_bridge(rc) };
        return rc as c_long;
    }

    unsafe { mcexec_util_thread_switch_returned_bridge(rc) };
    -(EINVAL as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn act_generic_syscall(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) {
    let ret = unsafe { mcexec_do_generic_syscall_bridge(w) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_sched_setaffinity(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    my_thread: *mut c_void,
) {
    let action = mcexec_sched_setaffinity_action_result(unsafe { (*w).sr.args[0] });
    let ret = if action > 0 {
        unsafe {
            mcexec_sched_setaffinity_util_bridge(
                my_thread,
                (*w).sr.args[1],
                (*w).sr.rtid,
                (*w).sr.args[2],
                (*w).sr.args[3],
                (*w).sr.args[4],
            )
        }
    } else {
        unsafe { mcexec_sched_setaffinity_invalid_bridge((*w).sr.args[0]) };
        action
    };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_getdents(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let ret = unsafe {
        overlay_getdents(
            (*w).sr.number as c_int,
            (*w).sr.args[0] as c_int,
            (*w).sr.args[1] as *mut c_void,
            (*w).sr.args[2] as u32,
        )
    };
    unsafe { do_syscall_return(fd, cpu, ret as c_long, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_perf_event_open(
    _w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) {
    let ret = unsafe { mcexec_perf_event_open_bridge() };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_futex_clock(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let mut tv = McexecTimespec {
        tv_sec: 0,
        tv_nsec: 0,
    };
    let ret = unsafe { mcexec_clock_gettime_bridge((*w).sr.args[1] as c_int, &mut tv) };
    unsafe {
        mcexec_clock_gettime_log_bridge(tv.tv_sec, tv.tv_nsec);
        do_syscall_return(
            fd,
            cpu,
            ret,
            1,
            (&tv as *const McexecTimespec) as c_ulong,
            (*w).sr.args[0],
            core::mem::size_of::<McexecTimespec>() as c_ulong,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_kill(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    my_thread: *mut c_void,
) {
    unsafe {
        mcexec_kill_thread_bridge((*w).sr.args[1], (*w).sr.args[2], my_thread);
        do_syscall_return(fd, cpu, 0, 0, 0, 0, 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_kill_thread_body(
    tid: c_ulong,
    sig: c_ulong,
    my_thread: *mut McexecThreadData,
) {
    let signal = if sig == 0 { SIGURG } else { sig as c_int };
    let mut tp = unsafe { mcexec_kill_thread_head_bridge() };

    while !tp.is_null() {
        if tp != my_thread && unsafe { (*tp).remote_tid as c_ulong == tid } {
            let ret = unsafe { mcexec_kill_thread_pthread_kill_bridge(tp, signal) };
            if ret == ESRCH {
                unsafe { mcexec_kill_thread_not_found_bridge(tid, signal) };
            }
        }

        tp = unsafe { (*tp).next };
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_wait4(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let requested_pid = unsafe { (*w).sr.args[0] };
    let pid = requested_pid as c_int;
    let options = unsafe { (*w).sr.args[2] } as c_int;
    let opt = WEXITED | (options & WNOWAIT);
    let mut errno_value = 0;
    let ret = unsafe { mcexec_waitid_pid_bridge(pid, opt, &mut errno_value) };
    if ret != pid {
        unsafe { mcexec_wait4_error_bridge(requested_pid, ret, errno_value) };
    }
    unsafe { do_syscall_return(fd, cpu, ret as c_long, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_gettid(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let count = unsafe { (*w).sr.args[4] } as usize;
    let mut rc = 0;

    if count > 0 {
        let elem_size = core::mem::size_of::<i32>();
        if count > usize::MAX / elem_size {
            unsafe { mcexec_gettid_alloc_error_bridge() };
            rc = -(ENOMEM as c_long);
        } else {
            let bytes = count * elem_size;
            let tids = unsafe { malloc(bytes) as *mut i32 };
            if tids.is_null() {
                unsafe { mcexec_gettid_alloc_error_bridge() };
                rc = -(ENOMEM as c_long);
            } else if unsafe { mcexec_collect_active_tids_result(MCEXEC_THREAD_DATA, tids, count) }
                < 0
            {
                rc = -(EINVAL as c_long);
                unsafe { free(tids as *mut u8) };
            } else {
                let transfer = RemoteTransfer {
                    rphys: unsafe { (*w).sr.args[5] },
                    userp: tids as *mut c_void,
                    size: bytes as c_ulong,
                    direction: MCEXEC_UP_TRANSFER_TO_REMOTE,
                };
                if unsafe {
                    ioctl(
                        fd,
                        MCEXEC_UP_TRANSFER,
                        &transfer as *const RemoteTransfer as c_ulong,
                    )
                } != 0
                {
                    rc = -(EFAULT as c_long);
                    unsafe { mcexec_gettid_transfer_error_bridge() };
                }
                unsafe { free(tids as *mut u8) };
            }
        }
    }

    unsafe { do_syscall_return(fd, cpu, rc, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_debug_mlock(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let addr = unsafe { (*w).sr.args[0] };
    let len = unsafe { (*w).sr.args[1] };
    unsafe { mcexec_debug_mlock_log_bridge(addr, len) };
    let ret = unsafe { mcexec_debug_mlock_bridge(addr, len) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_swapout_unavailable(
    _w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) {
    unsafe {
        mcexec_swapout_unavailable_bridge();
        do_syscall_return(fd, cpu, -1, 0, 0, 0, 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_linux_spawn(w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int) {
    let mut ret: c_long = -1;
    let mut exec_path: *mut u8 = core::ptr::null_mut();
    let mut argv: [*mut u8; MCEXEC_LINUX_SPAWN_ARG_MAX] =
        [core::ptr::null_mut(); MCEXEC_LINUX_SPAWN_ARG_MAX];

    loop {
        let exec_src = unsafe { (*w).sr.args[0] as *mut u8 };
        let spawn_args = unsafe { (*w).sr.args[1] as *mut *mut u8 };
        if exec_src.is_null() || spawn_args.is_null() {
            unsafe { mcexec_linux_spawn_invalid_arg_bridge() };
            break;
        }

        let exec_len = match unsafe { strlen(exec_src as *const u8) }.checked_add(1) {
            Some(value) => value,
            None => {
                unsafe { mcexec_linux_spawn_invalid_exec_path_bridge() };
                break;
            }
        };
        if exec_len == 0 || exec_len >= PATH_MAX {
            unsafe { mcexec_linux_spawn_invalid_exec_path_bridge() };
            break;
        }

        exec_path = unsafe { malloc(exec_len) };
        if exec_path.is_null() {
            unsafe { mcexec_linux_spawn_alloc_exec_path_failed_bridge() };
            break;
        }
        unsafe { zero_bytes(exec_path, exec_len) };

        if unsafe {
            do_strncpy_from_user(
                fd,
                exec_path as *mut c_void,
                exec_src as *mut c_void,
                exec_len as c_ulong,
            )
        } < 0
        {
            unsafe { mcexec_linux_spawn_strncpy_failed_bridge() };
            break;
        }

        let mut failed = false;
        let mut index = 0usize;
        while index < MCEXEC_LINUX_SPAWN_ARG_MAX - 1 {
            let arg_src = unsafe { *spawn_args.add(index) };
            if arg_src.is_null() {
                break;
            }

            let arg_len = match unsafe { strlen(arg_src as *const u8) }.checked_add(1) {
                Some(value) => value,
                None => {
                    unsafe { mcexec_linux_spawn_alloc_argv_failed_bridge(index as c_int) };
                    failed = true;
                    break;
                }
            };

            let arg = unsafe { malloc(arg_len) };
            if arg.is_null() {
                unsafe { mcexec_linux_spawn_alloc_argv_failed_bridge(index as c_int) };
                failed = true;
                break;
            }
            unsafe { zero_bytes(arg, arg_len) };

            if unsafe {
                do_strncpy_from_user(
                    fd,
                    arg as *mut c_void,
                    arg_src as *mut c_void,
                    arg_len as c_ulong,
                )
            } < 0
            {
                unsafe {
                    mcexec_linux_spawn_strncpy_failed_bridge();
                    free(arg);
                }
                failed = true;
                break;
            }

            argv[index] = arg;
            index += 1;
        }

        if !failed
            && index == MCEXEC_LINUX_SPAWN_ARG_MAX - 1
            && unsafe { !(*spawn_args.add(index)).is_null() }
        {
            unsafe { mcexec_linux_spawn_invalid_arg_bridge() };
            failed = true;
        }
        if failed {
            break;
        }

        let mut pid: c_int = 0;
        let rc = unsafe {
            posix_spawn(
                &mut pid,
                exec_path as *const u8,
                core::ptr::null::<c_void>(),
                core::ptr::null::<c_void>(),
                argv.as_ptr(),
                core::ptr::null::<*mut u8>(),
            )
        };
        if rc != 0 {
            unsafe { mcexec_linux_spawn_posix_spawn_failed_bridge(rc) };
            break;
        }

        ret = 0;
        break;
    }

    if !exec_path.is_null() {
        unsafe { free(exec_path) };
    }
    let mut index = 0usize;
    while index < MCEXEC_LINUX_SPAWN_ARG_MAX {
        let arg = argv[index];
        if arg.is_null() {
            break;
        }
        unsafe { free(arg) };
        index += 1;
    }

    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_clone_complete(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) {
    let pid = unsafe { (*w).sr.args[1] as c_int };
    let mut fs: *mut ForkSync = core::ptr::null_mut();
    let mut node: *mut ForkSyncContainer = core::ptr::null_mut();

    unsafe {
        mcexec_fork_sync_lock_bridge();
        if mcexec_fork_sync_complete_result(
            core::ptr::addr_of_mut!(MCEXEC_FORK_SYNC_TOP),
            pid,
            &mut fs,
            &mut node,
        ) > 0
        {
            if !fs.is_null() {
                mcexec_fork_sync_munmap_bridge(fs as *mut c_void);
            }
            if !node.is_null() {
                mcexec_fork_sync_free_bridge(node as *mut c_void);
            }
        }
        mcexec_fork_sync_unlock_bridge();
        do_syscall_return(fd, cpu, 0, 0, 0, 0, 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_clone_start(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    main_loop_ret: *mut c_long,
) -> c_int {
    let mut rc: c_long = -1;
    let fs = unsafe { mcexec_clone_alloc_fork_sync_bridge() as *mut ForkSync };

    if fs.is_null() {
        unsafe { do_syscall_return(fd, cpu, rc, 0, 0, 0, 0) };
        return 0;
    }

    let fsc = unsafe { mcexec_clone_alloc_container_bridge() as *mut ForkSyncContainer };
    if fsc.is_null() {
        unsafe {
            mcexec_clone_sem_destroy_bridge(fs as *mut c_void);
            mcexec_fork_sync_munmap_bridge(fs as *mut c_void);
            do_syscall_return(fd, cpu, rc, 0, 0, 0, 0);
        }
        return 0;
    }

    unsafe {
        mcexec_fork_sync_lock_bridge();
        (*fsc).next = MCEXEC_FORK_SYNC_TOP;
        MCEXEC_FORK_SYNC_TOP = fsc;
        mcexec_fork_sync_unlock_bridge();
        (*fsc).fs = fs;
    }

    let pid = unsafe { mcexec_clone_fork_bridge() };
    unsafe {
        (*fsc).pid = pid;
    }

    if pid == -1 {
        let errno = unsafe { *__errno_location() };
        unsafe { mcexec_clone_fork_failed_bridge() };
        rc = -(errno as c_long);
    } else if pid == 0 {
        let child_ret = unsafe { mcexec_clone_child_bridge(w, fs as *mut c_void) };
        if !main_loop_ret.is_null() {
            unsafe {
                *main_loop_ret = child_ret;
            }
        }
        return 1;
    } else {
        loop {
            let wait_rc = unsafe { mcexec_clone_sem_trywait_bridge(fs as *mut c_void) };
            if wait_rc != -1 {
                break;
            }

            let errno = unsafe { *__errno_location() };
            if errno != EAGAIN && errno != EINTR {
                break;
            }

            let wrc = unsafe { mcexec_clone_waitpid_nohang_bridge(pid) };
            if wrc == pid {
                unsafe {
                    (*fs).status = -ENOMEM;
                }
                break;
            }
            unsafe { mcexec_clone_sched_yield_bridge() };
        }

        let status = unsafe { (*fs).status };
        if status != 0 {
            unsafe { mcexec_clone_child_after_fork_failed_bridge() };
            rc = status as c_long;
        } else {
            rc = pid as c_long;
        }
    }

    unsafe {
        mcexec_clone_sem_destroy_bridge(fs as *mut c_void);
        if rc < 0 {
            mcexec_fork_sync_munmap_bridge(fs as *mut c_void);
            mcexec_fork_sync_lock_bridge();
            if mcexec_fork_sync_remove_node_result(
                core::ptr::addr_of_mut!(MCEXEC_FORK_SYNC_TOP),
                fsc,
            ) > 0
            {
                mcexec_fork_sync_free_bridge(fsc as *mut c_void);
            }
            mcexec_fork_sync_unlock_bridge();
        }
        do_syscall_return(fd, cpu, rc, 0, 0, 0, 0);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn act_exit(w: *const McexecSyscallWaitDesc, cpu: c_int, is_child: c_int) {
    let status = unsafe { (*w).sr.args[0] };
    let number = unsafe { (*w).sr.number as c_long };
    let mut sig = 0;
    let mut term = 0;
    let mut report_sig = 0;
    let mut report_status = 0;

    unsafe {
        mcexec_exit_debug_bridge(status, cpu);
        mcexec_exit_status_plan_result(
            number,
            status,
            SYS_EXIT_GROUP,
            is_child,
            mcexec_exit_isatty_bridge(2),
            &mut sig,
            &mut term,
            &mut report_sig,
            &mut report_status,
        );
        if report_sig != 0 {
            mcexec_exit_report_signal_bridge(sig);
        } else if report_status != 0 {
            mcexec_exit_report_status_bridge(term);
        }
        mcexec_exit_cmd_servers_bridge();
        if sig != 0 {
            mcexec_exit_replay_signal_bridge(sig);
        }
        mcexec_exit_process_bridge(term);
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_execve_phase1(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
) {
    let mut ret: c_long;
    let mut desc: *mut c_void = core::ptr::null_mut();
    let mut shebang_argv: *mut *mut u8 = core::ptr::null_mut();
    let mut shebang_argv_flat: *mut u8 = core::ptr::null_mut();
    let mut buffer: *mut u8;
    let mut size: usize;
    let mut check_symlink = 0;
    let mut filename = unsafe { (*w).sr.args[2] as *mut u8 };

    ret = unsafe {
        mcexec_getpath_execveat_prepare_result(
            (*w).sr.args[1] as c_int,
            filename as *const u8,
            (*w).sr.args[4] as c_int,
            AT_FDCWD,
            AT_EMPTY_PATH,
            AT_SYMLINK_NOFOLLOW,
            pathbuf,
            PATH_MAX,
            &mut check_symlink,
        ) as c_long
    };
    if ret != 0 {
        unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
        return;
    }
    if check_symlink != 0 && unsafe { readlink(filename as *const u8, pathbuf, PATH_MAX) } != -1 {
        unsafe { do_syscall_return(fd, cpu, ELOOP as c_long, 0, 0, 0, 0) };
        return;
    }
    filename = pathbuf;

    ret = unsafe { load_elf_desc_shebang(filename, &mut desc, &mut shebang_argv, 0) as c_long };
    if ret != 0 {
        unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
        return;
    }

    let sections = unsafe { mcexec_desc_num_sections_bridge(desc as *const c_void) };
    unsafe {
        mcexec_execve1_load_desc_ok_bridge(filename as *const u8, sections);
        mcexec_desc_set_execve1_runtime_bridge(
            desc,
            mcexec_execve1_enable_vdso_bridge(),
            mcexec_execve1_rlim_cur_bridge(),
            mcexec_execve1_rlim_max_bridge(),
            mcexec_execve1_stack_premap_bridge(),
        );
    }

    if sections < 0 {
        unsafe {
            free(desc as *mut u8);
            do_syscall_return(fd, cpu, ENOMEM as c_long, 0, 0, 0, 0);
        }
        return;
    }
    let desc_head = unsafe { mcexec_program_load_desc_size_bridge() };
    let section_size = unsafe { mcexec_program_image_section_size_bridge() };
    let Some(section_bytes) = (sections as usize).checked_mul(section_size) else {
        unsafe {
            free(desc as *mut u8);
            do_syscall_return(fd, cpu, ENOMEM as c_long, 0, 0, 0, 0);
        }
        return;
    };
    let Some(desc_size) = desc_head.checked_add(section_bytes) else {
        unsafe {
            free(desc as *mut u8);
            do_syscall_return(fd, cpu, ENOMEM as c_long, 0, 0, 0, 0);
        }
        return;
    };
    buffer = desc as *mut u8;
    size = desc_size;

    if !shebang_argv.is_null() {
        let args_len =
            unsafe { flatten_strings(core::ptr::null_mut(), shebang_argv, &mut shebang_argv_flat) };
        unsafe { mcexec_desc_set_args_len_bridge(desc, args_len as c_ulong) };
        ret = unsafe {
            mcexec_execve1_transfer_buffer_result(
                desc as *const u8,
                desc_size,
                shebang_argv_flat as *const u8,
                args_len as usize,
                &mut buffer,
                &mut size,
            ) as c_long
        };
        if ret != 0 {
            unsafe {
                mcexec_execve1_transfer_alloc_failed_bridge(filename as *const u8);
                if !shebang_argv_flat.is_null() {
                    free(shebang_argv_flat);
                }
                if buffer != desc as *mut u8 && !buffer.is_null() {
                    free(buffer);
                }
                if !desc.is_null() {
                    free(desc as *mut u8);
                }
                do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
            }
            return;
        }
        unsafe { free(shebang_argv_flat) };
    }

    let transfer = RemoteTransfer {
        rphys: unsafe { (*w).sr.args[3] },
        userp: buffer as *mut c_void,
        size: size as c_ulong,
        direction: MCEXEC_UP_TRANSFER_TO_REMOTE,
    };
    if unsafe {
        ioctl(
            fd,
            MCEXEC_UP_TRANSFER,
            &transfer as *const RemoteTransfer as c_ulong,
        )
    } != 0
    {
        let errno = unsafe { *__errno_location() };
        ret = -(errno as c_long);
        unsafe { mcexec_execve1_transfer_failed_bridge(filename as *const u8) };
    } else {
        unsafe { mcexec_execve1_transfer_ok_bridge(filename as *const u8) };
        ret = 0;
    }

    unsafe {
        if buffer != desc as *mut u8 && !buffer.is_null() {
            free(buffer);
        }
        if !desc.is_null() {
            free(desc as *mut u8);
        }
        do_syscall_return(fd, cpu, ret, 0, 0, 0, 0);
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_execve_phase2(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) -> c_long {
    let size = unsafe { (*w).sr.args[2] as usize };
    let desc = unsafe { malloc(size) };
    if desc.is_null() {
        unsafe {
            mcexec_execve2_alloc_desc_failed_bridge();
            do_syscall_return(fd, cpu, -1, 0, 0, 0, 0);
        }
        return 0;
    }
    unsafe { zero_bytes(desc, size) };

    let transfer = RemoteTransfer {
        rphys: unsafe { (*w).sr.args[1] },
        userp: desc as *mut c_void,
        size: size as c_ulong,
        direction: MCEXEC_UP_TRANSFER_FROM_REMOTE,
    };
    if unsafe {
        ioctl(
            fd,
            MCEXEC_UP_TRANSFER,
            &transfer as *const RemoteTransfer as c_ulong,
        )
    } != 0
    {
        unsafe {
            mcexec_execve2_transfer_desc_failed_bridge();
            do_syscall_return(fd, cpu, EINVAL as c_long, 0, 0, 0, 0);
        }
        return 0;
    }

    unsafe { mcexec_execve2_transfer_desc_ok_bridge() };
    if unsafe { transfer_image(fd, desc as *mut c_void) } != 0 {
        unsafe { mcexec_execve2_transfer_image_failed_bridge() };
        return -1;
    }
    unsafe { mcexec_execve2_image_transferred_bridge() };

    let close_ret = unsafe { ioctl(fd, MCEXEC_UP_CLOSE_EXEC, 0 as c_ulong) };
    if close_ret != 0 {
        unsafe { mcexec_execve2_close_exec_failed_bridge(close_ret) };
        return 1;
    }

    if unsafe { close_cloexec_fds(fd) } < 0 {
        unsafe { do_syscall_return(fd, cpu, EINVAL as c_long, 0, 0, 0, 0) };
        return 0;
    }

    unsafe { do_syscall_return(fd, cpu, 0, 0, 0, 0, 0) };
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_finish_main_image_body(desc: *mut c_void) -> c_int {
    if unsafe { ioctl(MCEXEC_FD, MCEXEC_UP_PREPARE_IMAGE, desc as c_ulong) } != 0 {
        unsafe { mcexec_main_prepare_image_failed_bridge() };
        return 1;
    }

    unsafe { print_desc(desc as *const c_void) };
    if unsafe { transfer_image(MCEXEC_FD, desc) } < 0 {
        unsafe { mcexec_execve2_transfer_image_failed_bridge() };
        return -1;
    }

    let close_ret = unsafe { ioctl(MCEXEC_FD, MCEXEC_UP_CLOSE_EXEC, 0 as c_ulong) };
    if close_ret != 0 {
        unsafe { mcexec_execve2_close_exec_failed_bridge(close_ret) };
        return 1;
    }

    unsafe { mcexec_main_flush_bridge() };
    let cmd_rc = unsafe { mcexec_main_cmd_servers_init_bridge() };
    if cmd_rc != 0 {
        return cmd_rc;
    }

    unsafe { init_sigaction() };
    let worker_rc = unsafe { init_worker_threads(MCEXEC_FD) };
    if worker_rc != 0 {
        unsafe { mcexec_main_worker_threads_failed_bridge(worker_rc) };
        return 1;
    }

    if unsafe { ioctl(MCEXEC_FD, MCEXEC_UP_START_IMAGE, desc as c_ulong) } != 0 {
        unsafe { mcexec_main_start_image_failed_bridge() };
        return 1;
    }

    unsafe { mcexec_join_all_threads_body() };
    0
}

#[no_mangle]
pub unsafe extern "C" fn act_execve(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    main_loop_ret: *mut c_long,
) -> c_int {
    let phase = unsafe { (*w).sr.args[0] };

    match phase {
        1 => unsafe {
            act_execve_phase1(w, fd, cpu, pathbuf);
            0
        },
        2 => {
            let ret = unsafe { act_execve_phase2(w, fd, cpu) };
            if ret != 0 {
                if !main_loop_ret.is_null() {
                    unsafe {
                        *main_loop_ret = ret;
                    }
                }
                1
            } else {
                0
            }
        }
        _ => unsafe {
            mcexec_execve_invalid_phase_bridge();
            0
        },
    }
}

#[no_mangle]
pub unsafe extern "C" fn act_reserved_memory_syscall(
    _w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) {
    unsafe { do_syscall_return(fd, cpu, -(ENOSYS as c_long), 0, 0, 0, 0) };
}

unsafe fn path_arg_or_return(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    arg_index: usize,
) -> c_long {
    if w.is_null() || pathbuf.is_null() || arg_index >= 6 {
        unsafe { do_syscall_return(fd, cpu, -(EINVAL as c_long), 0, 0, 0, 0) };
        return -(EINVAL as c_long);
    }

    let src = unsafe { (*w).sr.args[arg_index] as *mut c_void };
    let copy_ret =
        unsafe { do_strncpy_from_user(fd, pathbuf as *mut c_void, src, PATH_MAX as c_ulong) };
    let ret = mcexec_path_copy_return_result(copy_ret, PATH_MAX as u64) as c_long;
    if ret < 0 {
        unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
        return ret;
    }

    unsafe {
        *pathbuf.add(ret as usize) = 0;
    }
    ret
}

unsafe fn path_overlay_or_return(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
    arg_index: usize,
    dirfd: c_int,
    resolvelinks: *mut c_int,
) -> *const u8 {
    if tmpbuf.is_null() {
        unsafe { do_syscall_return(fd, cpu, -(EINVAL as c_long), 0, 0, 0, 0) };
        return core::ptr::null();
    }
    if unsafe { path_arg_or_return(w, fd, cpu, pathbuf, arg_index) } < 0 {
        return core::ptr::null();
    }
    unsafe { overlay_path(dirfd, pathbuf as *const u8, tmpbuf, resolvelinks) }
}

#[no_mangle]
pub unsafe extern "C" fn act_openat(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    let dirfd = unsafe { (*w).sr.args[0] } as c_int;
    if unsafe { path_arg_or_return(w, fd, cpu, pathbuf, 1) } < 0 {
        return;
    }

    unsafe { mcexec_path_openat_log_bridge(dirfd, pathbuf as *const u8, (*w).sr.rtid) };
    let path = unsafe { overlay_path(dirfd, pathbuf as *const u8, tmpbuf, core::ptr::null_mut()) };
    let ret = unsafe { mcexec_path_openat_bridge(dirfd, path, (*w).sr.args[2], (*w).sr.args[3]) };
    if ret >= 0 && path == tmpbuf as *const u8 {
        unsafe { overlay_addfd(ret as c_int, path) };
    }
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_open(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    if unsafe { path_arg_or_return(w, fd, cpu, pathbuf, 0) } < 0 {
        return;
    }

    unsafe { mcexec_path_open_log_bridge(pathbuf as *const u8) };
    let path = unsafe {
        overlay_path(
            AT_FDCWD,
            pathbuf as *const u8,
            tmpbuf,
            core::ptr::null_mut(),
        )
    };
    let ret = unsafe { mcexec_path_open_bridge(path, (*w).sr.args[1], (*w).sr.args[2]) };
    if ret >= 0 && path == tmpbuf as *const u8 {
        unsafe { overlay_addfd(ret as c_int, path) };
    }
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_readlinkat(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    let dirfd = unsafe { (*w).sr.args[0] } as c_int;
    let path = unsafe {
        path_overlay_or_return(w, fd, cpu, pathbuf, tmpbuf, 1, dirfd, core::ptr::null_mut())
    };
    if path.is_null() {
        return;
    }

    let ret = unsafe {
        mcexec_path_readlinkat_bridge(
            dirfd,
            path,
            (*w).sr.args[2] as *mut u8,
            (*w).sr.args[3] as usize,
        )
    };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_readlink(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    let path = unsafe {
        path_overlay_or_return(
            w,
            fd,
            cpu,
            pathbuf,
            tmpbuf,
            0,
            AT_FDCWD,
            core::ptr::null_mut(),
        )
    };
    if path.is_null() {
        return;
    }

    let ret = unsafe {
        mcexec_path_readlink_bridge(path, (*w).sr.args[1] as *mut u8, (*w).sr.args[2] as usize)
    };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_newfstatat(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    let dirfd = unsafe { (*w).sr.args[0] } as c_int;
    let path = unsafe {
        path_overlay_or_return(w, fd, cpu, pathbuf, tmpbuf, 1, dirfd, core::ptr::null_mut())
    };
    if path.is_null() {
        return;
    }

    let ret = unsafe {
        mcexec_path_fstatat_bridge(
            dirfd,
            path,
            (*w).sr.args[2] as *mut c_void,
            (*w).sr.args[3] as c_int,
        )
    };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_stat(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    let path = unsafe {
        path_overlay_or_return(
            w,
            fd,
            cpu,
            pathbuf,
            tmpbuf,
            0,
            AT_FDCWD,
            core::ptr::null_mut(),
        )
    };
    if path.is_null() {
        return;
    }

    let ret = unsafe { mcexec_path_stat_bridge(path, (*w).sr.args[1] as *mut c_void) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_faccessat(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    let dirfd = unsafe { (*w).sr.args[0] } as c_int;
    let mut resolvelinks = 0;
    let path =
        unsafe { path_overlay_or_return(w, fd, cpu, pathbuf, tmpbuf, 1, dirfd, &mut resolvelinks) };
    if path.is_null() {
        return;
    }

    let flags = if resolvelinks == 0 {
        0
    } else {
        AT_SYMLINK_NOFOLLOW
    };
    let ret = unsafe { mcexec_path_faccessat_bridge(dirfd, path, (*w).sr.args[2] as c_int, flags) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_access(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    let path = unsafe {
        path_overlay_or_return(
            w,
            fd,
            cpu,
            pathbuf,
            tmpbuf,
            0,
            AT_FDCWD,
            core::ptr::null_mut(),
        )
    };
    if path.is_null() {
        return;
    }

    let ret = unsafe { mcexec_path_access_bridge(path, (*w).sr.args[1] as c_int) };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_getxattr(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    let path = unsafe {
        path_overlay_or_return(
            w,
            fd,
            cpu,
            pathbuf,
            tmpbuf,
            0,
            AT_FDCWD,
            core::ptr::null_mut(),
        )
    };
    if path.is_null() {
        return;
    }

    let ret = unsafe {
        mcexec_path_getxattr_bridge(
            path,
            (*w).sr.args[1] as *const u8,
            (*w).sr.args[2] as *mut c_void,
            (*w).sr.args[3] as usize,
        )
    };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_lgetxattr(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
) {
    let path = unsafe {
        path_overlay_or_return(
            w,
            fd,
            cpu,
            pathbuf,
            tmpbuf,
            0,
            AT_FDCWD,
            core::ptr::null_mut(),
        )
    };
    if path.is_null() {
        return;
    }

    let ret = unsafe {
        mcexec_path_lgetxattr_bridge(
            path,
            (*w).sr.args[1] as *const u8,
            (*w).sr.args[2] as *mut c_void,
            (*w).sr.args[3] as usize,
        )
    };
    unsafe { do_syscall_return(fd, cpu, ret, 0, 0, 0, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn act_main_loop_syscall(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    my_thread: *mut c_void,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
    main_loop_ret: *mut c_long,
    is_child: c_int,
) -> c_int {
    let number = unsafe { (*w).sr.number as c_long };

    match number {
        SYS_OPENAT => unsafe { act_openat(w, fd, cpu, pathbuf, tmpbuf) },
        SYS_FUTEX => unsafe { act_futex_clock(w, fd, cpu) },
        SYS_KILL => unsafe { act_kill(w, fd, cpu, my_thread) },
        SYS_EXIT | SYS_EXIT_GROUP => {
            unsafe { act_exit(w, cpu, is_child) };
            if !main_loop_ret.is_null() {
                unsafe {
                    *main_loop_ret = (*w).sr.args[0] as c_long;
                }
            }
            return 1;
        }
        SYS_MMAP | SYS_MUNMAP | SYS_MPROTECT => unsafe { act_reserved_memory_syscall(w, fd, cpu) },
        SYS_GETTID => unsafe { act_gettid(w, fd, cpu) },
        SYS_CLONE => {
            let flag = unsafe { (*w).sr.args[0] };
            if flag == 1 {
                unsafe { act_clone_complete(w, fd, cpu) };
            } else if unsafe { act_clone_start(w, fd, cpu, main_loop_ret) } != 0 {
                return 1;
            }
        }
        SYS_WAIT4 => unsafe { act_wait4(w, fd, cpu) },
        SYS_EXECVE => {
            if unsafe { act_execve(w, fd, cpu, pathbuf, main_loop_ret) } != 0 {
                return 1;
            }
        }
        SYS_SIGNALFD4 => unsafe { act_signalfd4_syscall(w, fd, cpu) },
        SYS_PERF_EVENT_OPEN => unsafe { act_perf_event_open(w, fd, cpu) },
        value if value == SYS_RT_SIGACTION as c_long => unsafe { act_rt_sigaction(w, fd, cpu) },
        SYS_RT_SIGPROCMASK => unsafe { act_rt_sigprocmask(w, fd, cpu) },
        SYS_SETFSUID => unsafe { act_setfsuid(w, fd, cpu) },
        SYS_SETRESUID => unsafe { act_setresuid(w, fd, cpu) },
        SYS_SETREUID => unsafe { act_setreuid(w, fd, cpu) },
        SYS_SETUID => unsafe { act_setuid(w, fd, cpu) },
        SYS_SETRESGID => unsafe { act_setresgid(w, fd, cpu) },
        SYS_SETREGID => unsafe { act_setregid(w, fd, cpu) },
        SYS_SETGID => unsafe { act_setgid(w, fd, cpu) },
        SYS_SETFSGID => unsafe { act_setfsgid(w, fd, cpu) },
        SYS_CLOSE => unsafe { act_close(w, fd, cpu) },
        SYS_READLINKAT => unsafe { act_readlinkat(w, fd, cpu, pathbuf, tmpbuf) },
        SYS_READLINK => unsafe { act_readlink(w, fd, cpu, pathbuf, tmpbuf) },
        SYS_NEWFSTATAT => unsafe { act_newfstatat(w, fd, cpu, pathbuf, tmpbuf) },
        SYS_STAT => unsafe { act_stat(w, fd, cpu, pathbuf, tmpbuf) },
        SYS_FACCESSAT => unsafe { act_faccessat(w, fd, cpu, pathbuf, tmpbuf) },
        SYS_ACCESS => unsafe { act_access(w, fd, cpu, pathbuf, tmpbuf) },
        SYS_GETXATTR => unsafe { act_getxattr(w, fd, cpu, pathbuf, tmpbuf) },
        SYS_LGETXATTR => unsafe { act_lgetxattr(w, fd, cpu, pathbuf, tmpbuf) },
        SYS_GETDENTS | SYS_GETDENTS64 => unsafe { act_getdents(w, fd, cpu) },
        SYS_SCHED_SETAFFINITY => unsafe { act_sched_setaffinity(w, fd, cpu, my_thread) },
        MCEXEC_SWAPOUT_SYSCALL => unsafe { act_swapout_unavailable(w, fd, cpu) },
        MCEXEC_DEBUG_MLOCK_SYSCALL => unsafe { act_debug_mlock(w, fd, cpu) },
        MCEXEC_LINUX_SPAWN_SYSCALL => unsafe { act_linux_spawn(w, fd, cpu) },
        SYS_OPEN => unsafe { act_open(w, fd, cpu, pathbuf, tmpbuf) },
        _ => unsafe { act_generic_syscall(w, fd, cpu) },
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn act_main_loop_iteration(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    my_thread: *mut McexecThreadData,
    pathbuf: *mut u8,
    tmpbuf: *mut u8,
    main_loop_ret: *mut c_long,
    is_child: c_int,
) -> c_int {
    let cpu = unsafe { (*my_thread).cpu };
    let number = unsafe { (*w).sr.number };
    let arg0 = unsafe { (*w).sr.args[0] };

    if mcexec_syscall_should_log_result(number as i64, arg0, SYS_WRITE) != 0 {
        unsafe { mcexec_main_loop_log_syscall_bridge(cpu, number as c_long) };
    }

    unsafe {
        (*my_thread).remote_tid = (*w).sr.rtid;
        (*my_thread).remote_cpu = (*w).cpu as c_int;
    }

    let should_return = unsafe {
        act_main_loop_syscall(
            w,
            fd,
            cpu,
            my_thread as *mut c_void,
            pathbuf,
            tmpbuf,
            main_loop_ret,
            is_child,
        )
    };

    if should_return == 0 {
        unsafe {
            (*my_thread).remote_tid = -1;
        }
    }

    should_return
}

#[no_mangle]
pub unsafe extern "C" fn act_main_loop_body(
    my_thread: *mut McexecThreadData,
    fd: c_int,
    is_child: c_int,
) -> c_int {
    let cpu = unsafe { (*my_thread).cpu };
    let mut w = McexecSyscallWaitDesc {
        cpu: cpu as c_ulong,
        sr: McexecSyscallRequest {
            rtid: 0,
            ttid: 0,
            valid: 0,
            number: 0,
            args: [0; 6],
        },
        pid: unsafe { getpid() },
    };
    let mut pathbuf = [0u8; PATH_MAX];
    let mut tmpbuf = [0u8; PATH_MAX];

    loop {
        let wait_ret = unsafe {
            ioctl(
                fd,
                MCEXEC_UP_WAIT_SYSCALL,
                (&mut w as *mut McexecSyscallWaitDesc) as c_ulong,
            )
        };

        if wait_ret == 0 {
            let mut main_loop_ret: c_long = 0;
            let should_return = unsafe {
                act_main_loop_iteration(
                    &w,
                    fd,
                    my_thread,
                    pathbuf.as_mut_ptr(),
                    tmpbuf.as_mut_ptr(),
                    &mut main_loop_ret,
                    is_child,
                )
            };
            if should_return != 0 {
                return main_loop_ret as c_int;
            }

            unsafe {
                (*my_thread).remote_tid = -1;
            }
            continue;
        }

        if wait_ret == -1 && unsafe { *__errno_location() } == EINTR {
            continue;
        }

        break;
    }

    unsafe { mcexec_main_loop_timeout_bridge() };
    1
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_loop_thread_func_body(arg: *mut c_void) -> *mut c_void {
    let td = arg as *mut McexecThreadData;

    unsafe {
        (*td).tid = gettid();
        (*td).remote_tid = -1;
        if !(*td).init_ready.is_null() {
            mcexec_main_loop_thread_barrier_wait_bridge((*td).init_ready as *mut c_void);
        }
        (*td).ret = act_main_loop_body(td, MCEXEC_FD, mcexec_main_loop_is_child_bridge());
    }

    core::ptr::null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_create_worker_thread_body(
    tp_out: *mut *mut McexecThreadData,
    init_ready: *mut c_void,
) -> c_int {
    let tp = unsafe { mcexec_create_worker_thread_alloc_bridge() };
    if tp.is_null() {
        unsafe { mcexec_create_worker_thread_alloc_error_bridge() };
        return ENOMEM;
    }

    unsafe {
        core::ptr::write_bytes(tp, 0, 1);
        (*tp).cpu = mcexec_create_worker_thread_next_cpu_bridge();
        (*tp).lock = mcexec_create_worker_thread_lock_bridge() as *mut u8;
        (*tp).init_ready = init_ready as *mut u8;
        (*tp).terminate = 0;
        mcexec_create_worker_thread_publish_bridge(tp, tp_out);
        mcexec_create_worker_thread_pthread_create_bridge(tp)
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_join_all_threads_body() {
    loop {
        let mut live_thread = 0;
        let mut tp = unsafe { mcexec_join_all_threads_head_bridge() };

        while !tp.is_null() {
            if unsafe { (*tp).joined != 0 || (*tp).detached != 0 } {
                tp = unsafe { (*tp).next };
                continue;
            }

            live_thread = 1;
            unsafe {
                mcexec_join_all_threads_join_bridge(tp);
                (*tp).joined = 1;
                tp = (*tp).next;
            }
        }

        if live_thread == 0 {
            break;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn search_file(orgpath: *mut u8, mode: c_int) -> *mut u8 {
    if unsafe { access(orgpath as *const u8, mode) } == 0 {
        return orgpath;
    }

    let altroot = unsafe { mcexec_altroot_bridge() };
    let modpath = core::ptr::addr_of_mut!(SEARCH_FILE_MODPATH).cast::<u8>();
    let n = unsafe { mcexec_join_path_result(altroot, orgpath as *const u8, modpath, PATH_MAX) };
    if n < 0 || n as usize >= PATH_MAX {
        unsafe { mcexec_search_file_path_too_long_bridge(altroot, orgpath as *const u8) };
        return core::ptr::null_mut();
    }

    if unsafe { access(modpath as *const u8, mode) } == 0 {
        return modpath;
    }

    core::ptr::null_mut()
}

unsafe fn transfer_read_exact(fp: *mut c_void, dst: *mut u8, len: usize) -> c_int {
    if unsafe { fread(dst as *mut c_void, 1, len, fp) } != len {
        if unsafe { ferror(fp) } > 0 {
            unsafe { mcexec_transfer_access_error_bridge() };
        } else if unsafe { feof(fp) } > 0 {
            unsafe { mcexec_transfer_short_error_bridge() };
        }
        return -EINVAL;
    }
    0
}

unsafe fn read_one<T>(fp: *mut c_void, out: *mut T) -> bool {
    (unsafe { fread(out as *mut c_void, core::mem::size_of::<T>(), 1, fp) }) >= 1
}

fn elf_segment_prot(flags: u32) -> c_int {
    let mut prot = PROT_NONE;
    if flags & PF_R != 0 {
        prot |= PROT_READ;
    }
    if flags & PF_W != 0 {
        prot |= PROT_WRITE;
    }
    if flags & PF_X != 0 {
        prot |= PROT_EXEC;
    }
    prot
}

#[no_mangle]
pub unsafe extern "C" fn load_elf(fp: *mut c_void, interp_pathp: *mut *mut u8) -> *mut c_void {
    let mut hdr = unsafe { core::mem::zeroed::<Elf64Ehdr>() };
    let mut phdr = unsafe { core::mem::zeroed::<Elf64Phdr>() };
    let mut load_count = 0i32;

    unsafe {
        *interp_pathp = core::ptr::null_mut();
    }

    if !unsafe { read_one(fp, &mut hdr) } {
        unsafe { mcexec_load_cannot_read_ehdr_bridge() };
        return core::ptr::null_mut();
    }
    if unsafe { bytes_range(&hdr.e_ident, 0, ELFMAG.len()) } != ELFMAG {
        unsafe { mcexec_load_elfmag_mismatch_bridge() };
        return core::ptr::null_mut();
    }

    unsafe {
        fseek(fp, hdr.e_phoff as c_long, SEEK_SET);
    }
    let mut index = 0u16;
    while index < hdr.e_phnum {
        if !unsafe { read_one(fp, &mut phdr) } {
            unsafe { mcexec_load_phdr_failed_bridge(index as c_int) };
            return core::ptr::null_mut();
        }
        if phdr.p_type == PT_LOAD {
            load_count += 1;
        }
        index += 1;
    }

    let desc = unsafe { mcexec_load_alloc_desc_bridge(load_count) };
    if desc.is_null() {
        return core::ptr::null_mut();
    }

    unsafe {
        fseek(fp, hdr.e_phoff as c_long, SEEK_SET);
    }
    let mut out_index = 0i32;
    let mut load_addr = 0u64;
    let mut load_addr_set = false;
    let mut at_phdr = 0u64;
    let mut at_phdr_set = false;
    let mut stack_prot = PROT_READ | PROT_WRITE | PROT_EXEC;
    index = 0;
    while index < hdr.e_phnum {
        if !unsafe { read_one(fp, &mut phdr) } {
            unsafe { mcexec_load_phdr_failed_bridge(index as c_int) };
            return core::ptr::null_mut();
        }

        if phdr.p_type == PT_INTERP {
            if phdr.p_filesz > PATH_MAX as u64 {
                unsafe { mcexec_load_too_large_interp_bridge() };
                return core::ptr::null_mut();
            }

            let interp_path = core::ptr::addr_of_mut!(LOAD_INTERP_PATH).cast::<u8>();
            let read_len = unsafe {
                pread(
                    fileno(fp),
                    interp_path as *mut c_void,
                    phdr.p_filesz as usize,
                    phdr.p_offset as c_long,
                )
            };
            if read_len <= 0 {
                unsafe { mcexec_load_cannot_read_interp_bridge() };
                return core::ptr::null_mut();
            }
            unsafe {
                *interp_path.add(read_len as usize) = 0;
                *interp_pathp = interp_path;
            }
        }

        if phdr.p_type == PT_PHDR {
            at_phdr = phdr.p_vaddr;
            at_phdr_set = true;
        }

        if phdr.p_type == PT_LOAD {
            let prot = elf_segment_prot(phdr.p_flags);
            unsafe {
                mcexec_load_publish_main_section_bridge(
                    desc,
                    out_index,
                    phdr.p_vaddr,
                    phdr.p_filesz,
                    phdr.p_offset,
                    phdr.p_memsz,
                    prot,
                    fp,
                );
                mcexec_load_section_log_bridge(
                    out_index,
                    phdr.p_vaddr,
                    phdr.p_filesz,
                    phdr.p_offset,
                    phdr.p_memsz,
                    prot,
                );
            }
            out_index += 1;

            if !load_addr_set {
                load_addr_set = true;
                load_addr = phdr.p_vaddr.wrapping_sub(phdr.p_offset);
            }
        }

        if phdr.p_type == PT_GNU_STACK {
            stack_prot = elf_segment_prot(phdr.p_flags);
        }

        index += 1;
    }

    let has_interp = unsafe { !(*interp_pathp).is_null() };
    let reloc = if has_interp && hdr.e_type == ET_DYN {
        1
    } else {
        0
    };
    let final_at_phdr = if at_phdr_set {
        at_phdr
    } else {
        load_addr.wrapping_add(hdr.e_phoff)
    };

    unsafe {
        ioctl(
            MCEXEC_FD,
            MCEXEC_UP_GET_CREDV,
            mcexec_load_cred_bridge(desc) as c_ulong,
        );
        mcexec_load_finalize_desc_bridge(
            desc,
            getpid(),
            getpgid(0),
            reloc,
            hdr.e_entry,
            final_at_phdr,
            core::mem::size_of::<Elf64Phdr>() as c_ulong,
            hdr.e_phnum as c_ulong,
            hdr.e_entry,
            mcexec_load_clk_tck_bridge() as c_ulong,
            stack_prot,
        );
    }

    desc
}

#[no_mangle]
pub unsafe extern "C" fn load_interp(desc0: *mut c_void, fp: *mut c_void) -> *mut c_void {
    let mut hdr = unsafe { core::mem::zeroed::<Elf64Ehdr>() };
    let mut phdr = unsafe { core::mem::zeroed::<Elf64Phdr>() };
    let mut load_count = 0usize;

    if !unsafe { read_one(fp, &mut hdr) } {
        unsafe { mcexec_load_cannot_read_ehdr_bridge() };
        return core::ptr::null_mut();
    }
    if unsafe { bytes_range(&hdr.e_ident, 0, ELFMAG.len()) } != ELFMAG {
        unsafe { mcexec_load_elfmag_mismatch_bridge() };
        return core::ptr::null_mut();
    }

    unsafe {
        fseek(fp, hdr.e_phoff as c_long, SEEK_SET);
    }
    let mut index = 0u16;
    while index < hdr.e_phnum {
        if !unsafe { read_one(fp, &mut phdr) } {
            unsafe { mcexec_load_phdr_failed_bridge(index as c_int) };
            return core::ptr::null_mut();
        }
        if phdr.p_type == PT_LOAD {
            load_count += 1;
        }
        index += 1;
    }

    let old_sections = unsafe { mcexec_desc_num_sections_bridge(desc0 as *const c_void) };
    let new_sections = old_sections as usize + load_count;
    let new_size = unsafe { mcexec_program_load_desc_size_bridge() }
        + new_sections * unsafe { mcexec_program_image_section_size_bridge() };
    let desc = unsafe { realloc(desc0 as *mut u8, new_size) as *mut c_void };
    if desc.is_null() {
        unsafe { mcexec_load_realloc_failed_bridge(new_size as c_ulong) };
        return core::ptr::null_mut();
    }

    unsafe {
        fseek(fp, hdr.e_phoff as c_long, SEEK_SET);
    }
    let mut align = 1u64;
    let mut out_index = old_sections;
    index = 0;
    while index < hdr.e_phnum {
        if !unsafe { read_one(fp, &mut phdr) } {
            unsafe {
                mcexec_load_phdr_failed_bridge(index as c_int);
                free(desc as *mut u8);
            }
            return core::ptr::null_mut();
        }

        if phdr.p_type == PT_INTERP {
            unsafe {
                mcexec_load_pt_interp_on_interp_bridge();
                free(desc as *mut u8);
            }
            return core::ptr::null_mut();
        }

        if phdr.p_type == PT_LOAD {
            let prot = elf_segment_prot(phdr.p_flags);
            if phdr.p_align > align {
                align = phdr.p_align;
            }
            unsafe {
                mcexec_desc_publish_interp_section_bridge(
                    desc,
                    out_index,
                    phdr.p_vaddr,
                    phdr.p_filesz,
                    phdr.p_offset,
                    phdr.p_memsz,
                    prot,
                    fp,
                );
                mcexec_load_section_log_bridge(
                    out_index,
                    phdr.p_vaddr,
                    phdr.p_filesz,
                    phdr.p_offset,
                    phdr.p_memsz,
                    prot,
                );
            }
            out_index += 1;
        }
        index += 1;
    }

    unsafe {
        mcexec_desc_set_num_sections_bridge(desc, out_index);
        mcexec_desc_set_entry_bridge(desc, hdr.e_entry);
        mcexec_desc_set_interp_align_bridge(desc, align);
    }

    desc
}

#[no_mangle]
pub unsafe extern "C" fn transfer_image(fd: c_int, desc: *mut c_void) -> c_int {
    let sections = unsafe { mcexec_desc_num_sections_bridge(desc as *const c_void) };
    let page_size = unsafe { MCEXEC_PAGE_SIZE };
    let page_mask = unsafe { MCEXEC_PAGE_MASK };
    let dma_buf = unsafe { MCEXEC_DMA_BUF };
    let mut index = 0;

    while index < sections {
        let fp = unsafe { mcexec_desc_section_fp_bridge(desc as *const c_void, index) };
        let vaddr = unsafe { mcexec_desc_section_vaddr_bridge(desc as *const c_void, index) };
        let len = unsafe { mcexec_desc_section_len_bridge(desc as *const c_void, index) };
        let offset = unsafe { mcexec_desc_section_offset_bridge(desc as *const c_void, index) };
        let mut s = vaddr & page_mask;
        let e = vaddr
            .wrapping_add(len)
            .wrapping_add(page_size.wrapping_sub(1))
            & page_mask;
        let mut rpa = unsafe { mcexec_desc_section_remote_pa_bridge(desc as *const c_void, index) };

        if unsafe { fseek(fp, offset as c_long, SEEK_SET) } != 0 {
            unsafe { mcexec_transfer_seek_error_bridge() };
            return -1;
        }

        let mut flen = unsafe { mcexec_desc_section_filesz_bridge(desc as *const c_void, index) };
        unsafe { mcexec_transfer_seeked_bridge(offset, flen) };

        while s < e {
            let mut transfer = RemoteTransfer {
                rphys: rpa,
                userp: dma_buf as *mut c_void,
                size: page_size,
                direction: MCEXEC_UP_TRANSFER_TO_REMOTE,
            };
            let mut lr = 0usize;

            unsafe { zero_bytes(dma_buf, page_size as usize) };
            if s < vaddr {
                let l = vaddr & page_size.wrapping_sub(1);
                let mut read_len = page_size - l;
                if read_len > flen {
                    read_len = flen;
                }
                lr = read_len as usize;
                if unsafe { transfer_read_exact(fp, dma_buf.add(l as usize), lr) } != 0 {
                    return -EINVAL;
                }
                flen -= read_len;
            } else if flen > 0 {
                let read_len = if flen > page_size { page_size } else { flen };
                lr = read_len as usize;
                if unsafe { transfer_read_exact(fp, dma_buf, lr) } != 0 {
                    return -EINVAL;
                }
                flen -= read_len;
            }

            s = s.wrapping_add(page_size);
            rpa = rpa.wrapping_add(page_size);

            if lr == 0 && flen == 0 {
                break;
            }

            if unsafe {
                ioctl(
                    fd,
                    MCEXEC_UP_TRANSFER,
                    &mut transfer as *mut RemoteTransfer as c_ulong,
                )
            } != 0
            {
                unsafe { perror(DMA_PERROR_TAG.as_ptr()) };
                break;
            }
        }

        index += 1;
    }

    0
}

unsafe fn trim_shebang_line(mut shebang: *mut u8) -> *mut u8 {
    if shebang.is_null() {
        return shebang;
    }

    let mut len = unsafe { cstr_len(shebang as *const u8) };
    if len > 0 {
        len -= 1;
        unsafe {
            *shebang.add(len) = 0;
        }
    }

    while len > 0 {
        let ch = unsafe { *shebang.add(len - 1) };
        if ch != b' ' && ch != b'\t' {
            break;
        }
        len -= 1;
        unsafe {
            *shebang.add(len) = 0;
        }
    }

    while len > 0 {
        let ch = unsafe { *shebang };
        if ch != b' ' && ch != b'\t' {
            break;
        }
        unsafe {
            shebang = shebang.add(1);
        }
        len -= 1;
    }

    shebang
}

unsafe fn load_desc_publish_exec_path(filename: *const u8) -> c_int {
    if unsafe { *filename } == b'/' {
        let path = unsafe { strdup(filename) };
        if path.is_null() {
            unsafe { mcexec_load_desc_strdup_failed_bridge() };
            return ENOMEM;
        }
        unsafe { mcexec_load_desc_publish_exec_path_bridge(path) };
        return 0;
    }

    let cwd = unsafe { getcwd(core::ptr::null_mut(), 0) };
    if cwd.is_null() {
        unsafe { mcexec_load_desc_getcwd_failed_bridge() };
        return ENOMEM;
    }

    let path_len = unsafe { cstr_len(cwd as *const u8) }
        .saturating_add(unsafe { cstr_len(filename) })
        .saturating_add(2);
    let path = unsafe { malloc(path_len) };
    if path.is_null() {
        unsafe {
            mcexec_load_desc_alloc_exec_path_failed_bridge();
            free(cwd);
        }
        return ENOMEM;
    }

    if unsafe { write_joined_path(cwd as *const u8, filename, path, path_len) } < 0 {
        unsafe {
            mcexec_load_desc_build_exec_path_failed_bridge();
            free(path);
            free(cwd);
        }
        return ENOMEM;
    }

    unsafe {
        free(cwd);
        mcexec_load_desc_publish_exec_path_bridge(path);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn load_elf_desc(
    filename: *mut u8,
    desc_p: *mut *mut c_void,
    shebang_p: *mut *mut u8,
) -> c_int {
    if unsafe { access(filename as *const u8, X_OK) } != 0 {
        let error = unsafe { *__errno_location() };
        unsafe { mcexec_load_desc_not_executable_bridge(filename as *const u8, error) };
        return error;
    }

    let mut file_size: c_long = 0;
    let ret = unsafe { mcexec_load_desc_stat_size_bridge(filename as *const u8, &mut file_size) };
    if ret != 0 {
        return ret;
    }
    if file_size == 0 {
        unsafe { mcexec_load_desc_zero_length_bridge(filename as *const u8) };
        return ENOEXEC;
    }

    let fp = unsafe { fopen(filename as *const u8, READ_BINARY_MODE.as_ptr()) };
    if fp.is_null() {
        let error = unsafe { *__errno_location() };
        unsafe { mcexec_load_desc_open_failed_bridge(filename as *const u8) };
        return error;
    }

    let mut header = [0u8; 1024];
    if unsafe { fread(header.as_mut_ptr() as *mut c_void, 1, 2, fp) } != 2 {
        let error = unsafe { *__errno_location() };
        unsafe {
            mcexec_load_desc_header_failed_bridge(filename as *const u8);
            fclose(fp);
        }
        return error;
    }

    if header[0] == b'#' && header[1] == b'!' {
        let mut shebang: *mut u8 = core::ptr::null_mut();
        let mut shebang_len = 0usize;

        if unsafe { getline(&mut shebang, &mut shebang_len, fp) } == -1 {
            unsafe { mcexec_load_desc_shebang_read_failed_bridge(filename as *const u8) };
        }

        unsafe {
            fclose(fp);
            *shebang_p = trim_shebang_line(shebang);
        }
        return 0;
    }

    unsafe { rewind(fp) };
    let ret = unsafe { ioctl(MCEXEC_FD, MCEXEC_UP_OPEN_EXEC, filename as c_ulong) };
    if ret != 0 {
        unsafe {
            mcexec_load_desc_open_exec_failed_bridge(filename as *const u8, ret, MCEXEC_FD);
            fclose(fp);
        }
        return ret;
    }

    let ret = unsafe { load_desc_publish_exec_path(filename as *const u8) };
    if ret != 0 {
        unsafe { fclose(fp) };
        return ret;
    }

    let mut interp_path: *mut u8 = core::ptr::null_mut();
    let mut desc = unsafe { load_elf(fp, &mut interp_path) };
    if desc.is_null() {
        unsafe {
            mcexec_load_desc_parse_elf_failed_bridge();
            fclose(fp);
        }
        return 1;
    }

    if !interp_path.is_null() {
        let path = unsafe { search_file(interp_path, X_OK) };
        if path.is_null() {
            unsafe {
                mcexec_load_desc_interp_not_found_bridge(interp_path as *const u8);
                fclose(fp);
            }
            return 1;
        }

        let interp = unsafe { fopen(path as *const u8, READ_BINARY_MODE.as_ptr()) };
        if interp.is_null() {
            unsafe {
                mcexec_load_desc_interp_open_failed_bridge(path as *const u8);
                fclose(fp);
            }
            return 1;
        }

        desc = unsafe { load_interp(desc, interp) };
        if desc.is_null() {
            unsafe {
                mcexec_load_desc_parse_interp_failed_bridge();
                fclose(fp);
                fclose(interp);
            }
            return 1;
        }
    }

    unsafe {
        mcexec_load_desc_sections_bridge(mcexec_desc_num_sections_bridge(desc as *const c_void));
        *desc_p = desc;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn load_elf_desc_shebang(
    shebang_argv0: *mut u8,
    desc_p: *mut *mut c_void,
    shebang_argv_p: *mut *mut *mut u8,
    execvp: c_int,
) -> c_int {
    let mut path = [0u8; PATH_MAX];
    let mut shebang: *mut u8 = core::ptr::null_mut();

    let ret =
        unsafe { lookup_exec_path(shebang_argv0, path.as_mut_ptr(), PATH_MAX as c_int, execvp) };
    if ret != 0 {
        unsafe { mcexec_load_shebang_find_error_bridge(shebang_argv0 as *const u8) };
        return ret;
    }

    let ret = unsafe { load_elf_desc(path.as_mut_ptr(), desc_p, &mut shebang) };
    if ret != 0 {
        unsafe { mcexec_load_shebang_load_error_bridge(shebang_argv0 as *const u8) };
        return ret;
    }

    if !shebang.is_null() {
        if shebang_argv_p.is_null() {
            return unsafe {
                load_elf_desc_shebang(shebang, desc_p, core::ptr::null_mut(), execvp)
            };
        }

        if unsafe { mcexec_shebang_argv_extend_result(shebang_argv_p, shebang) } < 0 {
            return ENOMEM;
        }

        return unsafe { load_elf_desc_shebang(shebang, desc_p, shebang_argv_p, execvp) };
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn print_desc(desc: *const c_void) {
    unsafe { mcexec_print_desc_intro_bridge(desc) };
    unsafe {
        mcexec_print_desc_main_bridge(
            mcexec_desc_cpu_bridge(desc),
            mcexec_desc_pid_bridge(desc),
            mcexec_desc_entry_bridge(desc),
            mcexec_desc_rprocess_bridge(desc),
        );
    }

    let sections = unsafe { mcexec_desc_num_sections_bridge(desc) };
    let mut index = 0;
    while index < sections {
        unsafe {
            mcexec_print_desc_section_bridge(
                mcexec_desc_section_vaddr_bridge(desc, index),
                mcexec_desc_section_len_bridge(desc, index),
                mcexec_desc_section_remote_pa_bridge(desc, index),
                mcexec_desc_section_filesz_bridge(desc, index),
            );
        }
        index += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn print_flat(flat: *mut u8) {
    let words = flat as *const c_long;
    let count = unsafe { *words };

    unsafe { mcexec_print_flat_count_bridge(count) };
    let mut index: c_long = 0;
    while index < count {
        let offset = unsafe { *words.add((index + 1) as usize) };
        let entry = unsafe { flat.offset(offset as isize) };
        unsafe { mcexec_print_flat_entry_bridge(entry as *const u8) };
        index += 1;
    }
}

#[repr(C)]
pub struct EnvListEntry {
    str_ptr: *mut u8,
    name: *mut u8,
    value: *mut u8,
    next: *mut EnvListEntry,
}

unsafe fn main_read_i32(ptr: *mut c_int) -> c_int {
    if ptr.is_null() {
        0
    } else {
        unsafe { *ptr }
    }
}

unsafe fn main_read_ulong(ptr: *mut c_ulong) -> c_ulong {
    if ptr.is_null() {
        0
    } else {
        unsafe { *ptr }
    }
}

unsafe fn main_read_long(ptr: *mut c_long) -> c_long {
    if ptr.is_null() {
        0
    } else {
        unsafe { *ptr }
    }
}

unsafe fn main_read_cstr_ptr(ptr: *mut *mut u8) -> *const u8 {
    if ptr.is_null() {
        core::ptr::null()
    } else {
        unsafe { *ptr as *const u8 }
    }
}

unsafe fn main_write_ulong(ptr: *mut c_ulong, value: c_ulong) {
    if !ptr.is_null() {
        unsafe {
            *ptr = value;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_body(argc: c_int, argv: *mut *mut u8) -> c_int {
    let mut desc: *mut c_void = core::ptr::null_mut();
    let mut envs_len: c_int = 0;
    let mut envs: *mut u8 = core::ptr::null_mut();
    let mut target_core: c_int = 0;
    let mut shebang_argv: *mut *mut u8 = core::ptr::null_mut();
    let mut mcosid: c_int = 0;
    let mut extra_env: *mut EnvListEntry = core::ptr::null_mut();
    let mut state: McexecMainStatePtrs = unsafe { core::mem::zeroed() };

    unsafe {
        mcexec_main_publish_args_bridge(argc, argv);
        mcexec_init_page_altroot_body();
    }

    if unsafe { mcexec_main_personality_bridge(argv) } != 0 {
        return 1;
    }
    if unsafe { mcexec_init_stack_limit_body(argv) } != 0 {
        return 1;
    }

    unsafe {
        mcexec_main_state_ptrs_bridge(&mut state);
    }

    loop {
        let opt = unsafe { mcexec_main_next_option_bridge(argc, argv) };
        if opt == -1 {
            break;
        }

        match opt {
            x if x == b'c' as c_int
                || x == b'n' as c_int
                || x == b't' as c_int
                || x == b'M' as c_int
                || x == b'h' as c_int
                || x == b'S' as c_int
                || x == b's' as c_int
                || x == b'u' as c_int
                || x == b'f' as c_int =>
            {
                let optarg = unsafe { mcexec_main_optarg_bridge() };
                let rc = unsafe {
                    mcexec_apply_option_result(
                        opt,
                        optarg as *const u8,
                        &mut target_core,
                        state.nr_processes,
                        state.nr_threads,
                        state.mpol_threshold,
                        state.heap_extension,
                        state.straight_map_threshold,
                        state.stack_premap,
                        state.stack_max,
                        state.uti_thread_rank,
                        state.mcexec_flags,
                    )
                };
                if rc < 0 {
                    unsafe { mcexec_main_invalid_option_bridge(opt, argv) };
                    return 1;
                }
                if opt == b's' as c_int {
                    unsafe {
                        *__errno_location() = 0;
                        mcexec_main_stack_debug_bridge(
                            main_read_long(state.stack_premap),
                            main_read_long(state.stack_max),
                        );
                    }
                }
            }
            x if x == b'm' as c_int => {
                if !state.mpol_bind_nodes.is_null() {
                    unsafe {
                        *state.mpol_bind_nodes = mcexec_main_optarg_bridge();
                    }
                }
            }
            x if x == b'e' as c_int => {
                if unsafe { mcexec_print_usage_add_envs_bridge() } != 0 {
                    let optarg = unsafe { mcexec_main_optarg_bridge() };
                    unsafe {
                        mcexec_add_env_list_body(&mut extra_env, optarg);
                    }
                } else {
                    unsafe { mcexec_main_invalid_option_bridge(opt, argv) };
                    return 1;
                }
            }
            0 => {}
            _ => {
                unsafe { mcexec_main_invalid_option_bridge(opt, argv) };
                return 1;
            }
        }
    }

    let mut optind = unsafe { mcexec_main_optind_bridge() };
    let candidate = if !argv.is_null() && optind < argc {
        unsafe { *argv.add(optind as usize) as *const u8 }
    } else {
        core::ptr::null()
    };
    let mut planned_heap_extension = unsafe { main_read_ulong(state.heap_extension) };
    let mut planned_mcosid = mcosid;
    let mut planned_optind = optind;
    if unsafe {
        mcexec_post_options_plan_result(
            optind,
            argc,
            candidate,
            main_read_ulong(state.heap_extension),
            MCEXEC_PAGE_SIZE,
            mcosid,
            &mut planned_heap_extension,
            &mut planned_mcosid,
            &mut planned_optind,
        )
    } < 0
    {
        unsafe {
            print_usage(argv);
            exit(1);
        }
    }

    unsafe {
        main_write_ulong(state.heap_extension, planned_heap_extension);
    }
    mcosid = planned_mcosid;
    optind = planned_optind;

    if unsafe { mcexec_post_option_setup_body(mcosid, main_read_i32(state.enable_uti)) } != 0 {
        unsafe { exit(1) };
    }

    let add_envs_option = unsafe { mcexec_print_usage_add_envs_bridge() };
    if add_envs_option == 0 {
        unsafe {
            mcexec_collect_default_envs_body(&mut envs_len, &mut envs);
        }
    }

    if unsafe { mcexec_main_bind_mount_bridge() } != 0 {
        return 1;
    }

    let argv_tail = unsafe { argv.add(optind as usize) };
    if unsafe { mcexec_load_main_desc_body(*argv_tail, &mut desc, &mut shebang_argv) } != 0 {
        return 1;
    }

    if add_envs_option != 0 {
        unsafe {
            mcexec_collect_main_envs_body(&mut extra_env, &mut envs_len, &mut envs);
        }
    }

    unsafe {
        mcexec_prepare_main_desc_body(
            desc,
            argv_tail,
            shebang_argv,
            envs_len,
            envs,
            target_core,
            main_read_i32(state.enable_vdso),
        );
    }

    if unsafe {
        mcexec_apply_main_stack_body(
            desc,
            getenv(MCKERNEL_RLIMIT_STACK_ENV.as_ptr()) as *const u8,
            main_read_long(state.stack_max),
            main_read_long(state.stack_premap),
            state.rlim_cur,
            state.rlim_max,
        )
    } != 0
    {
        return 1;
    }

    if unsafe { mcexec_setup_cpu_topology_body() } != 0 {
        return 1;
    }

    if unsafe {
        mcexec_plan_process_threads_result(
            state.nr_processes,
            main_read_i32(state.nr_threads),
            MCEXEC_NCPU,
            core::ptr::addr_of_mut!(MCEXEC_N_THREADS),
        )
    } < 0
    {
        unsafe { mcexec_main_thread_plan_error_bridge() };
        return EINVAL;
    }

    unsafe {
        mcexec_setup_dma_ppd_body();
    }

    if unsafe {
        mcexec_apply_partitioned_cpu_body(
            desc,
            main_read_i32(state.nr_processes),
            &mut target_core,
            main_read_i32(state.no_bind_ikc_map),
        )
    } != 0
    {
        return 1;
    }

    unsafe {
        mcexec_apply_desc_runtime_body(
            desc,
            main_read_i32(state.profile),
            main_read_i32(state.nr_processes),
            main_read_i32(state.mpol_no_heap),
            main_read_i32(state.mpol_no_stack),
            main_read_i32(state.mpol_no_bss),
            main_read_i32(state.mpol_shm_premap),
            main_read_ulong(state.mpol_threshold),
            main_read_ulong(state.heap_extension),
            main_read_cstr_ptr(state.mpol_bind_nodes),
            MPOL_DEFAULT,
            MPOL_INTERLEAVE,
            MPOL_BIND,
            MPOL_PREFERRED,
            PLD_MPOL_MAX,
            main_read_i32(state.enable_uti),
            main_read_i32(state.uti_thread_rank),
            main_read_i32(state.uti_use_last_cpu),
            main_read_i32(state.straight_map),
            main_read_ulong(state.straight_map_threshold),
            main_read_i32(state.enable_tofu),
            main_read_ulong(state.mcexec_flags),
        );
    }

    unsafe { mcexec_finish_main_image_body(desc) }
}

#[repr(C)]
pub struct McexecThreadData {
    next: *mut McexecThreadData,
    thread_id: usize,
    cpu: i32,
    ret: i32,
    tid: i32,
    terminate: i32,
    remote_tid: i32,
    remote_cpu: i32,
    joined: i32,
    detached: i32,
    lock: *mut u8,
    init_ready: *mut u8,
}

#[repr(C)]
pub struct ForkSync {
    status: i32,
    success: i32,
}

#[repr(C)]
pub struct ForkSyncContainer {
    pid: i32,
    next: *mut ForkSyncContainer,
    fs: *mut ForkSync,
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_args(pid: c_int, args: *mut SyscallArgs) -> c_int {
    unsafe { ptrace(PTRACE_GETREGS, pid, core::ptr::null_mut::<c_void>(), args) as c_int }
}

#[no_mangle]
pub unsafe extern "C" fn set_syscall_args(pid: c_int, args: *mut SyscallArgs) -> c_int {
    unsafe { ptrace(PTRACE_SETREGS, pid, core::ptr::null_mut::<c_void>(), args) as c_int }
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_number(args: *const SyscallArgs) -> u64 {
    unsafe { (*args).orig_rax }
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_return(args: *const SyscallArgs) -> u64 {
    unsafe { (*args).rax }
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_arg1(args: *const SyscallArgs) -> u64 {
    unsafe { (*args).rdi }
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_arg2(args: *const SyscallArgs) -> u64 {
    unsafe { (*args).rsi }
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_arg3(args: *const SyscallArgs) -> u64 {
    unsafe { (*args).rdx }
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_arg4(args: *const SyscallArgs) -> u64 {
    unsafe { (*args).r10 }
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_arg5(args: *const SyscallArgs) -> u64 {
    unsafe { (*args).r8 }
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_arg6(args: *const SyscallArgs) -> u64 {
    unsafe { (*args).r9 }
}

#[no_mangle]
pub unsafe extern "C" fn get_syscall_rip(args: *const SyscallArgs) -> u64 {
    unsafe { (*args).rip }
}

#[no_mangle]
pub unsafe extern "C" fn set_syscall_number(args: *mut SyscallArgs, value: u64) {
    unsafe {
        (*args).orig_rax = value;
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_syscall_return(args: *mut SyscallArgs, value: u64) {
    unsafe {
        (*args).rax = value;
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_syscall_arg1(args: *mut SyscallArgs, value: u64) {
    unsafe {
        (*args).rdi = value;
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_syscall_arg2(args: *mut SyscallArgs, value: u64) {
    unsafe {
        (*args).rsi = value;
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_syscall_arg3(args: *mut SyscallArgs, value: u64) {
    unsafe {
        (*args).rdx = value;
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_syscall_arg4(args: *mut SyscallArgs, value: u64) {
    unsafe {
        (*args).r10 = value;
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_syscall_arg5(args: *mut SyscallArgs, value: u64) {
    unsafe {
        (*args).r8 = value;
    }
}

#[no_mangle]
pub unsafe extern "C" fn set_syscall_arg6(args: *mut SyscallArgs, value: u64) {
    unsafe {
        (*args).r9 = value;
    }
}

#[no_mangle]
pub unsafe extern "C" fn syscall_enter(args: *const SyscallArgs) -> c_int {
    (unsafe { get_syscall_return(args) } == ENOSYS_RET) as c_int
}

#[inline(always)]
unsafe fn bitop_word(addr: *mut u64, nr: c_int) -> *mut AtomicU32 {
    unsafe { (addr as *mut AtomicU32).offset((nr >> 5) as isize) }
}

#[inline(always)]
fn bitop_mask(nr: c_int) -> u32 {
    1u32 << ((nr & 31) as u32)
}

#[no_mangle]
pub unsafe extern "C" fn set_bit(nr: c_int, addr: *mut u64) {
    let word = unsafe { &*bitop_word(addr, nr) };
    word.fetch_or(bitop_mask(nr), Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn clear_bit(nr: c_int, addr: *mut u64) {
    let word = unsafe { &*bitop_word(addr, nr) };
    word.fetch_and(!bitop_mask(nr), Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn test_bit(nr: c_int, addr: *const c_void) -> c_int {
    let words = addr as *const u32;
    let word = unsafe { read_volatile(words.offset((nr >> 5) as isize)) };
    ((word & bitop_mask(nr)) != 0) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_numa_local_body(
    localset: *mut c_ulong,
    nodemask: *mut c_ulong,
    nonlocal: c_int,
) {
    unsafe {
        core::ptr::write_bytes(nodemask as *mut u8, 0, PLD_PROCESS_NUMA_MASK_BITS / 8);
    }

    let mut node = 0;
    while node < unsafe { MCEXEC_NNODES } {
        if nonlocal != 0 {
            unsafe { set_bit(node, nodemask) };
        }

        let mut cpu = 0;
        while cpu < unsafe { MCEXEC_NCPU } {
            let in_local = unsafe { test_bit(cpu, localset as *const c_void) } != 0;
            if in_local {
                unsafe { mcexec_numa_local_cpu_log_bridge(cpu) };
            }

            let in_node = unsafe { mcexec_numa_node_cpu_isset_bridge(node, cpu) } != 0;
            if in_node {
                unsafe { mcexec_numa_node_cpu_log_bridge(cpu, node) };
            }

            if in_local && in_node {
                if nonlocal != 0 {
                    unsafe { clear_bit(node, nodemask) };
                } else {
                    unsafe { set_bit(node, nodemask) };
                }
            }

            cpu += 1;
        }

        node += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_numa_node_set_body(
    n: c_int,
    numa_nodes: *mut c_void,
    cpu_set_size: usize,
) -> *mut c_void {
    unsafe { (numa_nodes as *mut u8).offset((n as isize) * (cpu_set_size as isize)) as *mut c_void }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_setup_cpu_topology_body() -> c_int {
    let cpu_count = unsafe { mcexec_main_get_cpu_bridge() };
    if cpu_count <= 0 {
        unsafe { mcexec_main_no_cpu_bridge() };
        return 1;
    }

    let node_count = unsafe { mcexec_main_get_nodes_bridge() };
    if node_count <= 0 {
        unsafe { mcexec_main_no_numa_node_bridge() };
        return 1;
    }

    let node_set_size = unsafe { mcexec_main_cpu_alloc_size_bridge(cpu_count) };
    let alloc_size = node_set_size.wrapping_mul(node_count as usize);
    let nodes = unsafe { malloc(alloc_size) as *mut c_void };
    if nodes.is_null() {
        unsafe { mcexec_main_alloc_nodes_error_bridge() };
        return 1;
    }

    let mut node_id = 0;
    while node_id < node_count {
        unsafe { mcexec_main_numa_node_zero_bridge(nodes, node_set_size, node_id) };
        let mut cpu = 0;
        while cpu < cpu_count {
            if unsafe { mcexec_main_node_cpu_exists_bridge(node_id, cpu) } != 0 {
                unsafe { mcexec_main_numa_node_set_cpu_bridge(nodes, node_set_size, node_id, cpu) };
            }
            cpu += 1;
        }
        node_id += 1;
    }

    unsafe {
        mcexec_main_publish_topology_bridge(cpu_count, node_count, node_set_size, nodes);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_apply_partitioned_cpu_body(
    desc: *mut c_void,
    nr_processes: c_int,
    target_core: *mut c_int,
    no_bind_ikc_map: c_int,
) -> c_int {
    if desc.is_null() || target_core.is_null() {
        return 1;
    }

    if unsafe { *target_core } != 0 || nr_processes <= 0 {
        return 0;
    }

    let mut mcexec_linux_numa = 0;
    let mut ikc_mapped = 0;
    let mut process_rank = -1;
    if unsafe {
        mcexec_partition_get_cpuset_bridge(
            desc,
            nr_processes,
            target_core,
            &mut process_rank,
            &mut mcexec_linux_numa,
            &mut ikc_mapped,
        )
    } != 0
    {
        unsafe { mcexec_partition_get_cpuset_failed_bridge() };
        return 1;
    }

    let target = unsafe { *target_core };
    unsafe {
        mcexec_partition_publish_cpu_rank_bridge(desc, target, process_rank);
    }

    let rank_env = unsafe { getenv(FLIB_RANK_ON_NODE_ENV.as_ptr()) };
    if !rank_env.is_null() {
        process_rank = unsafe { strtol(rank_env as *const u8, core::ptr::null_mut(), 10) as c_int };
        unsafe {
            mcexec_partition_publish_rank_bridge(desc, process_rank);
            mcexec_partition_rank_log_bridge(process_rank, target);
        }
    }

    if ikc_mapped != 0 && no_bind_ikc_map == 0 {
        if unsafe { mcexec_partition_sched_setaffinity_bridge() } < 0 {
            unsafe { mcexec_partition_sched_setaffinity_warning_bridge() };
        } else {
            unsafe { mcexec_partition_debug_ikc_binding_bridge() };
        }
    } else if unsafe { mcexec_partition_numa_run_bridge(mcexec_linux_numa) } < 0 {
        unsafe { mcexec_partition_numa_run_warning_bridge(mcexec_linux_numa) };
    } else {
        unsafe { mcexec_partition_debug_numa_binding_bridge() };
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_numa_all_body(nodemask: *mut c_ulong) {
    unsafe {
        core::ptr::write_bytes(nodemask as *mut u8, 0, PLD_PROCESS_NUMA_MASK_BITS / 8);
    }

    let mut node = 0;
    while node < unsafe { MCEXEC_NNODES } {
        unsafe { set_bit(node, nodemask) };
        node += 1;
    }
}

unsafe fn fixed_c_bytes_equal(left: *const u8, right: *const u8, len: usize) -> bool {
    let mut index = 0;
    while index < len {
        if unsafe { *left.add(index) != *right.add(index) } {
            return false;
        }
        index += 1;
    }
    true
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_body() -> c_int {
    let dev = unsafe { mcexec_opendev_dev_bridge() };
    let dev_size = unsafe { mcexec_opendev_dev_size_bridge() };
    let mcosid = unsafe { mcexec_opendev_mcosid_bridge() };

    if unsafe { mcexec_mcos_device_path_result(dev, dev_size, mcosid) } < 0 {
        unsafe { mcexec_opendev_path_error_bridge() };
        return -1;
    }

    let opened = unsafe { mcexec_opendev_open_bridge(dev as *const u8) };
    if opened < 0 {
        unsafe { mcexec_opendev_open_error_bridge(dev as *const u8) };
        return -1;
    }

    unsafe { mcexec_opendev_publish_fd_bridge(opened) };

    let query_result = unsafe { mcexec_opendev_query_result_bridge() };
    if unsafe { mcexec_opendev_query_buildid_bridge(opened, query_result) } != 0 {
        unsafe {
            mcexec_opendev_query_error_bridge();
            mcexec_opendev_close_bridge(opened);
        }
        return -1;
    }

    let buildid = unsafe { mcexec_opendev_buildid_bridge() };
    let buildid_size = unsafe { mcexec_opendev_buildid_size_bridge() };
    if unsafe { !fixed_c_bytes_equal(buildid, query_result as *const u8, buildid_size) } {
        unsafe {
            mcexec_opendev_buildid_mismatch_bridge(buildid, query_result as *const u8);
            mcexec_opendev_close_bridge(opened);
        }
        return -1;
    }

    opened
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_post_option_setup_body(
    new_mcosid: c_int,
    enable_uti: c_int,
) -> c_int {
    unsafe {
        mcexec_main_publish_mcosid_bridge(new_mcosid);
    }

    if unsafe { mcexec_opendev_body() } == -1 {
        return 1;
    }

    if unsafe { mcexec_main_uti_unavailable_bridge(enable_uti) } != 0 {
        return 1;
    }

    unsafe {
        mcexec_main_overlay_lock_init_bridge();
        mcexec_apply_flib_affinity_body();
        mcexec_ld_preload_init_body();
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_main_desc_body(
    path: *mut u8,
    desc_p: *mut *mut c_void,
    shebang_argv_p: *mut *mut *mut u8,
) -> c_int {
    let ret = unsafe { load_elf_desc_shebang(path, desc_p, shebang_argv_p, 1) };
    if ret != 0 {
        unsafe { mcexec_main_load_desc_error_bridge(path as *const u8, ret) };
        return 1;
    }

    let desc = unsafe { *desc_p };
    unsafe { mcexec_desc_clear_flags_bridge(desc) };
    0
}

unsafe fn cstr_bytes<'a>(ptr: *const u8) -> &'a [u8] {
    if ptr.is_null() {
        return &[];
    }

    let len = unsafe { cstr_len(ptr) };
    unsafe { core::slice::from_raw_parts(ptr, len) }
}

unsafe fn cstr_len(ptr: *const u8) -> usize {
    let mut len = 0usize;
    while unsafe { *ptr.add(len) } != 0 {
        len += 1;
    }
    len
}

fn is_space(b: u8) -> bool {
    matches!(b, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
}

fn byte_at(bytes: &[u8], idx: usize) -> u8 {
    unsafe { *bytes.as_ptr().add(idx) }
}

fn has_prefix_at(bytes: &[u8], start: usize, prefix: &[u8]) -> bool {
    if start > bytes.len() || bytes.len() - start < prefix.len() {
        return false;
    }

    let mut idx = 0usize;
    while idx < prefix.len() {
        if byte_at(bytes, start + idx) != byte_at(prefix, idx) {
            return false;
        }
        idx += 1;
    }
    true
}

fn has_exact_bytes(bytes: &[u8], expected: &[u8]) -> bool {
    bytes.len() == expected.len() && has_prefix_at(bytes, 0, expected)
}

fn contains_byte(bytes: &[u8], needle: u8) -> bool {
    let mut idx = 0usize;
    while idx < bytes.len() {
        if byte_at(bytes, idx) == needle {
            return true;
        }
        idx += 1;
    }
    false
}

fn path_boundary(bytes: &[u8], prefix_len: usize) -> bool {
    bytes.len() == prefix_len || byte_at(bytes, prefix_len) == b'/'
}

fn parse_decimal_segment(bytes: &[u8], mut idx: usize) -> Option<usize> {
    while idx < bytes.len() && is_space(byte_at(bytes, idx)) {
        idx += 1;
    }
    if idx < bytes.len() {
        let sign = byte_at(bytes, idx);
        if sign == b'-' || sign == b'+' {
            idx += 1;
        }
    }

    let first_digit = idx;
    while idx < bytes.len() && byte_at(bytes, idx).is_ascii_digit() {
        idx += 1;
    }
    if idx == first_digit {
        None
    } else {
        Some(idx)
    }
}

fn parse_i32_segment(bytes: &[u8], mut idx: usize) -> Option<(i32, usize)> {
    while idx < bytes.len() && is_space(byte_at(bytes, idx)) {
        idx += 1;
    }

    let mut neg = false;
    if idx < bytes.len() {
        let sign = byte_at(bytes, idx);
        if sign == b'-' {
            neg = true;
            idx += 1;
        } else if sign == b'+' {
            idx += 1;
        }
    }

    let first_digit = idx;
    let mut value = 0i32;
    while idx < bytes.len() {
        let ch = byte_at(bytes, idx);
        if !ch.is_ascii_digit() {
            break;
        }
        value = value.saturating_mul(10).saturating_add((ch - b'0') as i32);
        idx += 1;
    }
    if idx == first_digit {
        return None;
    }

    if neg {
        Some((value.saturating_neg(), idx))
    } else {
        Some((value, idx))
    }
}

fn atol_prefix(bytes: &[u8]) -> i64 {
    let mut idx = 0usize;
    while idx < bytes.len() && is_space(bytes[idx]) {
        idx += 1;
    }

    let mut neg = false;
    if idx < bytes.len() {
        if bytes[idx] == b'-' {
            neg = true;
            idx += 1;
        } else if bytes[idx] == b'+' {
            idx += 1;
        }
    }

    let mut value = 0i64;
    while idx < bytes.len() && bytes[idx].is_ascii_digit() {
        value = value
            .saturating_mul(10)
            .saturating_add((bytes[idx] - b'0') as i64);
        idx += 1;
    }

    if neg {
        value.saturating_neg()
    } else {
        value
    }
}

fn atobytes_bytes(bytes: &[u8]) -> u64 {
    if bytes.is_empty() {
        return 0;
    }

    let last = bytes[bytes.len() - 1];
    let (number, mult) = match last {
        b'k' | b'K' => (&bytes[..bytes.len() - 1], KIB),
        b'm' | b'M' => (&bytes[..bytes.len() - 1], MIB),
        b'g' | b'G' => (&bytes[..bytes.len() - 1], GIB),
        _ => (bytes, 1),
    };

    (atol_prefix(number) as u64).wrapping_mul(mult)
}

fn atoi_segment(bytes: &[u8], start: usize, end: usize) -> i32 {
    let mut idx = start;
    while idx < end && is_space(byte_at(bytes, idx)) {
        idx += 1;
    }

    let mut neg = false;
    if idx < end {
        let sign = byte_at(bytes, idx);
        if sign == b'-' {
            neg = true;
            idx += 1;
        } else if sign == b'+' {
            idx += 1;
        }
    }

    let mut value = 0i32;
    while idx < end {
        let ch = byte_at(bytes, idx);
        if !ch.is_ascii_digit() {
            break;
        }
        value = value.saturating_mul(10).saturating_add((ch - b'0') as i32);
        idx += 1;
    }

    if neg {
        value.saturating_neg()
    } else {
        value
    }
}

fn next_comma_token(bytes: &[u8], cursor: &mut usize) -> Option<(usize, usize)> {
    while *cursor < bytes.len() && byte_at(bytes, *cursor) == b',' {
        *cursor += 1;
    }
    if *cursor >= bytes.len() {
        return None;
    }

    let start = *cursor;
    while *cursor < bytes.len() && byte_at(bytes, *cursor) != b',' {
        *cursor += 1;
    }
    let end = *cursor;
    Some((start, end))
}

fn decimal_len_i32(value: i32) -> usize {
    if value == 0 {
        return 1;
    }

    let mut len = 0usize;
    let mut val = value as i64;
    if val < 0 {
        len += 1;
        val = -val;
    }
    while val > 0 {
        len += 1;
        val /= 10;
    }
    len
}

unsafe fn write_i32_decimal(dst: *mut u8, value: i32) -> usize {
    let mut out = dst;
    let mut val = value as i64;

    if val == 0 {
        unsafe {
            *out = b'0';
        }
        return 1;
    }

    if val < 0 {
        unsafe {
            *out = b'-';
            out = out.add(1);
        }
        val = -val;
    }

    let mut tmp = [0u8; 20];
    let mut digits = 0usize;
    while val > 0 {
        unsafe {
            *tmp.as_mut_ptr().add(digits) = b'0' + (val % 10) as u8;
        }
        digits += 1;
        val /= 10;
    }

    let mut idx = digits;
    while idx > 0 {
        idx -= 1;
        unsafe {
            *out = *tmp.as_ptr().add(idx);
            out = out.add(1);
        }
    }
    if value < 0 {
        digits + 1
    } else {
        digits
    }
}

fn decimal_len_u64(mut value: u64) -> usize {
    let mut len = 1usize;

    while value >= 10 {
        value /= 10;
        len += 1;
    }
    len
}

unsafe fn write_u64_decimal(dst: *mut u8, mut value: u64) -> usize {
    let len = decimal_len_u64(value);
    let mut pos = len;

    while pos > 0 {
        pos -= 1;
        unsafe {
            *dst.add(pos) = b'0' + (value % 10) as u8;
        }
        value /= 10;
    }

    len
}

unsafe fn copy_bytes(dst: *mut u8, src: &[u8]) -> *mut u8 {
    let mut out = dst;
    let mut idx = 0usize;
    while idx < src.len() {
        unsafe {
            *out = byte_at(src, idx);
            out = out.add(1);
        }
        idx += 1;
    }
    out
}

unsafe fn write_nul(dst: *mut u8) {
    unsafe {
        *dst = 0;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_init_stack_limit_body(argv: *mut *mut u8) -> c_int {
    const MCEXEC_MAX_STACK_SIZE: u64 = 16 * 1024 * 1024;

    let mut cur = 0u64;
    let mut max = 0u64;
    if unsafe { mcexec_main_load_stack_rlimit_bridge(&mut cur, &mut max) } != 0 {
        return 1;
    }

    if cur > MCEXEC_MAX_STACK_SIZE {
        unsafe {
            mcexec_reduce_stack_body(cur, max, argv);
            mcexec_main_reduce_stack_failed_bridge();
        }
        return 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_reduce_stack_body(
    orig_cur: u64,
    orig_max: u64,
    argv: *mut *mut u8,
) -> c_int {
    let total = decimal_len_u64(orig_cur) + 1 + decimal_len_u64(orig_max);
    if total >= 40 {
        unsafe { mcexec_reduce_stack_newval_overflow_bridge() };
        return 1;
    }

    let mut newval = [0u8; 40];
    let mut out = newval.as_mut_ptr();
    unsafe {
        let written = write_u64_decimal(out, orig_cur);
        out = out.add(written);
        *out = b',';
        out = out.add(1);
        let written = write_u64_decimal(out, orig_max);
        out = out.add(written);
        write_nul(out);
    }

    if unsafe { mcexec_reduce_stack_setenv_bridge(newval.as_ptr()) } != 0 {
        unsafe { mcexec_reduce_stack_setenv_failed_bridge() };
        return 1;
    }

    if unsafe { mcexec_reduce_stack_setrlimit_bridge(MCEXEC_STACK_SIZE, orig_max) } != 0 {
        unsafe { mcexec_reduce_stack_setrlimit_failed_bridge() };
        return 1;
    }

    let mut path = [0u8; PATH_MAX];
    let rc = unsafe { mcexec_reduce_stack_readlink_bridge(path.as_mut_ptr(), PATH_MAX) };
    if rc < 0 {
        unsafe { mcexec_reduce_stack_readlink_failed_bridge() };
        return 1;
    }

    if rc as usize >= PATH_MAX {
        let mut dst = path.as_mut_ptr();
        unsafe {
            dst = copy_bytes(dst, PROC_SELF_EXE);
            write_nul(dst);
        }
    } else {
        unsafe {
            *path.as_mut_ptr().add(rc as usize) = 0;
        }
    }

    unsafe {
        mcexec_reduce_stack_execv_bridge(path.as_ptr(), argv);
        mcexec_reduce_stack_execv_failed_bridge();
    }
    1
}

unsafe fn zero_bytes(dst: *mut u8, len: usize) {
    let mut idx = 0usize;
    while idx < len {
        unsafe {
            *dst.add(idx) = 0;
        }
        idx += 1;
    }
}

unsafe fn copy_ptr_bytes(dst: *mut u8, src: *const u8, len: usize) {
    let mut idx = 0usize;
    while idx < len {
        unsafe {
            *dst.add(idx) = *src.add(idx);
        }
        idx += 1;
    }
}

unsafe fn count_cstr_array(strings: *mut *mut u8) -> usize {
    if strings.is_null() {
        return 0;
    }

    let mut count = 0usize;
    while unsafe { !(*strings.add(count)).is_null() } {
        count += 1;
    }
    count
}

unsafe fn write_joined_path(prefix: *const u8, path: *const u8, out: *mut u8, size: usize) -> i32 {
    if prefix.is_null() || path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let prefix_bytes = unsafe { cstr_bytes(prefix) };
    let path_bytes = unsafe { cstr_bytes(path) };
    let Some(total) = prefix_bytes
        .len()
        .checked_add(1)
        .and_then(|v| v.checked_add(path_bytes.len()))
    else {
        return -ENAMETOOLONG;
    };

    if total >= size || total > i32::MAX as usize {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, prefix_bytes);
        *dst = b'/';
        dst = dst.add(1);
        dst = copy_bytes(dst, path_bytes);
        write_nul(dst);
    }
    total as i32
}

unsafe fn write_cstr_bytes(path: *const u8, out: *mut u8, max_len: c_int) -> i32 {
    if path.is_null() || out.is_null() || max_len <= 0 {
        return -ENAMETOOLONG;
    }

    let bytes = unsafe { cstr_bytes(path) };
    if bytes.len() >= max_len as usize || bytes.len() > i32::MAX as usize {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, bytes);
        write_nul(dst);
    }
    bytes.len() as i32
}

unsafe fn write_joined_path_bytes(prefix: &[u8], path: &[u8], out: *mut u8, max_len: c_int) -> i32 {
    if out.is_null() || max_len <= 0 {
        return -ENAMETOOLONG;
    }

    let Some(total) = prefix
        .len()
        .checked_add(1)
        .and_then(|v| v.checked_add(path.len()))
    else {
        return -ENAMETOOLONG;
    };
    if total >= max_len as usize || total > i32::MAX as usize {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, prefix);
        *dst = b'/';
        dst = dst.add(1);
        dst = copy_bytes(dst, path);
        write_nul(dst);
    }
    total as i32
}

unsafe fn lookup_access_errno(path: *const u8) -> c_int {
    if unsafe { access(path, X_OK) } == 0 {
        0
    } else {
        unsafe { *__errno_location() }
    }
}

unsafe fn bytes_range<'a>(bytes: &[u8], start: usize, end: usize) -> &'a [u8] {
    unsafe { core::slice::from_raw_parts(bytes.as_ptr().add(start), end - start) }
}

fn last_slash_pos(bytes: &[u8]) -> Option<usize> {
    let mut idx = bytes.len();
    while idx > 0 {
        idx -= 1;
        if byte_at(bytes, idx) == b'/' {
            return Some(idx);
        }
    }
    None
}

unsafe fn write_prefixed_i32_path(
    out: *mut u8,
    size: usize,
    prefix: &[u8],
    id: i32,
    suffix: &[u8],
) -> i32 {
    let total = prefix.len() + decimal_len_i32(id) + suffix.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, prefix);
        let written = write_i32_decimal(dst, id);
        dst = dst.add(written);
        dst = copy_bytes(dst, suffix);
        write_nul(dst);
    }
    total as i32
}

unsafe fn write_prefixed_i32_i32_path(
    out: *mut u8,
    size: usize,
    prefix: &[u8],
    first: i32,
    middle: &[u8],
    second: i32,
    suffix: &[u8],
) -> i32 {
    let total = prefix.len()
        + decimal_len_i32(first)
        + middle.len()
        + decimal_len_i32(second)
        + suffix.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, prefix);
        let written = write_i32_decimal(dst, first);
        dst = dst.add(written);
        dst = copy_bytes(dst, middle);
        let written = write_i32_decimal(dst, second);
        dst = dst.add(written);
        dst = copy_bytes(dst, suffix);
        write_nul(dst);
    }
    total as i32
}

fn find_subslice(bytes: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || bytes.len() < needle.len() {
        return None;
    }

    let mut pos = 0usize;
    while pos + needle.len() <= bytes.len() {
        if has_prefix_at(bytes, pos, needle) {
            return Some(pos);
        }
        pos += 1;
    }
    None
}

unsafe fn dup_cstr(src: *const u8) -> *mut u8 {
    let bytes = unsafe { cstr_bytes(src) };
    let dst = unsafe { malloc(bytes.len() + 1) };
    if dst.is_null() {
        return core::ptr::null_mut();
    }

    let mut idx = 0usize;
    while idx < bytes.len() {
        unsafe {
            *dst.add(idx) = byte_at(bytes, idx);
        }
        idx += 1;
    }
    unsafe {
        *dst.add(idx) = 0;
    }
    dst
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_build_ld_preload_result(
    libdir: *const u8,
    existing: *const u8,
    enable_uti: i32,
    disable_sched_yield: i32,
    enable_qlmpi: i32,
    out: *mut u8,
    size: usize,
) -> i32 {
    if libdir.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let libdir_bytes = unsafe { cstr_bytes(libdir) };
    let existing_bytes = if existing.is_null() {
        &[]
    } else {
        unsafe { cstr_bytes(existing) }
    };

    let mut entries = 0usize;
    let mut required = 0usize;
    let mut add_entry_len = |entry_len: usize| {
        if entries > 0 {
            required += 1;
        }
        required += entry_len;
        entries += 1;
    };

    if enable_uti != 0 {
        add_entry_len(libdir_bytes.len() + 1 + LD_MCK_SYSCALL_INTERCEPT.len());
    }
    if disable_sched_yield != 0 {
        add_entry_len(libdir_bytes.len() + 1 + LD_SCHED_YIELD.len());
    }
    if enable_qlmpi != 0 {
        add_entry_len(libdir_bytes.len() + 1 + LD_QLFORT.len());
    }
    if !existing.is_null() {
        if entries > 0 {
            required += 1;
        }
        required += existing_bytes.len();
    }

    if required >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    let mut written_entries = 0usize;
    unsafe fn append_entry(
        dst: &mut *mut u8,
        written_entries: &mut usize,
        libdir: &[u8],
        name: &[u8],
    ) {
        if *written_entries > 0 {
            unsafe {
                **dst = b':';
                *dst = (*dst).add(1);
            }
        }
        unsafe {
            *dst = copy_bytes(*dst, libdir);
            **dst = b'/';
            *dst = (*dst).add(1);
            *dst = copy_bytes(*dst, name);
        }
        *written_entries += 1;
    }

    if enable_uti != 0 {
        unsafe {
            append_entry(
                &mut dst,
                &mut written_entries,
                libdir_bytes,
                LD_MCK_SYSCALL_INTERCEPT,
            );
        }
    }
    if disable_sched_yield != 0 {
        unsafe {
            append_entry(&mut dst, &mut written_entries, libdir_bytes, LD_SCHED_YIELD);
        }
    }
    if enable_qlmpi != 0 {
        unsafe {
            append_entry(&mut dst, &mut written_entries, libdir_bytes, LD_QLFORT);
        }
    }
    if !existing.is_null() {
        if written_entries > 0 {
            unsafe {
                *dst = b':';
                dst = dst.add(1);
            }
        }
        dst = unsafe { copy_bytes(dst, existing_bytes) };
    }
    unsafe {
        write_nul(dst);
    }
    required as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_atobytes_result(string: *const u8) -> u64 {
    atobytes_bytes(unsafe { cstr_bytes(string) })
}

#[no_mangle]
pub unsafe extern "C" fn atobytes(string: *mut u8) -> u64 {
    if string.is_null() || unsafe { cstr_len(string as *const u8) } == 0 {
        unsafe {
            mcexec_atobytes_set_errno_bridge(ERANGE);
        }
        return 0;
    }
    unsafe {
        mcexec_atobytes_set_errno_bridge(0);
        mcexec_atobytes_result(string as *const u8)
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_parse_stack_arg_result(
    string: *const u8,
    stack_premap: *mut i64,
    stack_max: *mut i64,
) {
    let bytes = unsafe { cstr_bytes(string) };
    let comma = bytes.iter().position(|&b| b == b',');
    let (first, rest) = match comma {
        Some(pos) => (&bytes[..pos], Some(&bytes[pos + 1..])),
        None => (bytes, None),
    };

    if !first.is_empty() && !stack_premap.is_null() {
        unsafe {
            *stack_premap = atobytes_bytes(first) as i64;
        }
    }

    if let Some(second_and_more) = rest {
        let second_end = second_and_more
            .iter()
            .position(|&b| b == b',')
            .unwrap_or(second_and_more.len());
        let second = &second_and_more[..second_end];
        if !second.is_empty() && !stack_max.is_null() {
            unsafe {
                *stack_max = atobytes_bytes(second) as i64;
            }
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_apply_option_result(
    opt: i32,
    optarg: *const u8,
    target_core: *mut i32,
    nr_processes: *mut i32,
    nr_threads: *mut i32,
    mpol_threshold: *mut u64,
    heap_extension: *mut u64,
    straight_map_threshold: *mut u64,
    stack_premap: *mut i64,
    stack_max: *mut i64,
    uti_thread_rank: *mut i32,
    mcexec_flags: *mut u64,
) -> i32 {
    match opt as u8 {
        b'c' => unsafe { mcexec_parse_int_base0_full_result(optarg, 0, target_core) },
        b'n' => unsafe { mcexec_parse_int_base0_full_result(optarg, 1, nr_processes) },
        b't' => unsafe { mcexec_parse_int_base0_full_result(optarg, 1, nr_threads) },
        b'M' => {
            if mpol_threshold.is_null() {
                return -EINVAL;
            }
            unsafe {
                *mpol_threshold = mcexec_atobytes_result(optarg);
            }
            0
        }
        b'h' => {
            if heap_extension.is_null() {
                return -EINVAL;
            }
            unsafe {
                *heap_extension = mcexec_atobytes_result(optarg);
            }
            0
        }
        b'S' => {
            if straight_map_threshold.is_null() {
                return -EINVAL;
            }
            unsafe {
                *straight_map_threshold = mcexec_atobytes_result(optarg);
            }
            0
        }
        b's' => {
            unsafe {
                mcexec_parse_stack_arg_result(optarg, stack_premap, stack_max);
            }
            0
        }
        b'u' => {
            if uti_thread_rank.is_null() {
                return -EINVAL;
            }
            unsafe {
                *uti_thread_rank = mcexec_atoi_result(optarg);
            }
            0
        }
        b'f' => {
            if mcexec_flags.is_null() {
                return -EINVAL;
            }
            unsafe {
                *mcexec_flags = mcexec_strtoul_hex_result(optarg);
            }
            0
        }
        _ => 1,
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_parse_int_base0_full_result(
    string: *const u8,
    require_positive: i32,
    result: *mut i32,
) -> i32 {
    if string.is_null() || result.is_null() {
        return -22;
    }

    let mut end: *mut u8 = core::ptr::null_mut();
    let value = unsafe { strtol(string, &mut end, 0) };
    if end.is_null() || unsafe { *end } != 0 {
        return -22;
    }
    if require_positive != 0 && value <= 0 {
        return -22;
    }

    unsafe {
        *result = value as i32;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_atoi_result(string: *const u8) -> i32 {
    if string.is_null() {
        return 0;
    }
    unsafe { strtol(string, core::ptr::null_mut(), 10) as i32 }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_strtoul_hex_result(string: *const u8) -> u64 {
    if string.is_null() {
        return 0;
    }
    unsafe { strtoul(string, core::ptr::null_mut(), 16) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_parse_optional_mcosid_result(
    string: *const u8,
    result: *mut i32,
) -> i32 {
    if string.is_null() || result.is_null() {
        return 0;
    }

    let bytes = unsafe { cstr_bytes(string) };
    if bytes.is_empty() || !byte_at(bytes, 0).is_ascii_digit() {
        return 0;
    }

    unsafe {
        *result = strtol(string, core::ptr::null_mut(), 10) as i32;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_post_options_plan_result(
    optind: i32,
    argc: i32,
    candidate: *const u8,
    heap_extension: u64,
    page_size: u64,
    current_mcosid: i32,
    planned_heap_extension: *mut u64,
    planned_mcosid: *mut i32,
    planned_optind: *mut i32,
) -> i32 {
    if planned_heap_extension.is_null() || planned_mcosid.is_null() || planned_optind.is_null() {
        return -EINVAL;
    }

    let mut next_optind = optind;
    let mut next_mcosid = current_mcosid;
    let next_heap_extension = if heap_extension == ULONG_MAX {
        page_size
    } else {
        heap_extension
    };

    unsafe {
        *planned_heap_extension = next_heap_extension;
        *planned_mcosid = next_mcosid;
        *planned_optind = next_optind;
    }

    if next_optind >= argc || candidate.is_null() {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(candidate) };
    if !bytes.is_empty() && byte_at(bytes, 0).is_ascii_digit() {
        unsafe {
            next_mcosid = strtol(candidate, core::ptr::null_mut(), 10) as i32;
        }
        next_optind = next_optind.saturating_add(1);
    }

    unsafe {
        *planned_mcosid = next_mcosid;
        *planned_optind = next_optind;
    }

    if next_optind >= argc {
        return -EINVAL;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_usage_line_result(
    buf: *mut u8,
    size: usize,
    prog: *const u8,
    add_envs_option: i32,
) -> i32 {
    if buf.is_null() || size == 0 {
        return -EINVAL;
    }

    let prog_bytes = unsafe { cstr_bytes(prog) };
    let suffix = if add_envs_option != 0 {
        MCEXEC_USAGE_WITH_ENVS
    } else {
        MCEXEC_USAGE_WITHOUT_ENVS
    };

    let Some(total) = MCEXEC_USAGE_PREFIX
        .len()
        .checked_add(prog_bytes.len())
        .and_then(|value| value.checked_add(suffix.len()))
    else {
        return -ENAMETOOLONG;
    };
    if total >= size || total > i32::MAX as usize {
        return -ENAMETOOLONG;
    }

    let mut dst = buf;
    unsafe {
        dst = copy_bytes(dst, MCEXEC_USAGE_PREFIX);
        dst = copy_bytes(dst, prog_bytes);
        dst = copy_bytes(dst, suffix);
        write_nul(dst);
    }
    total as i32
}

#[no_mangle]
pub unsafe extern "C" fn print_usage(argv: *mut *mut u8) {
    let prog = if argv.is_null() {
        core::ptr::null()
    } else {
        unsafe { *argv as *const u8 }
    };
    let add_envs_option = unsafe { mcexec_print_usage_add_envs_bridge() };
    let mut line = [0u8; 1024];
    let len =
        unsafe { mcexec_usage_line_result(line.as_mut_ptr(), line.len(), prog, add_envs_option) };
    if len >= 0 {
        unsafe {
            mcexec_print_usage_write_bridge(line.as_ptr(), len as usize);
        }
        return;
    }

    let prog_bytes = unsafe { cstr_bytes(prog) };
    let suffix = if add_envs_option != 0 {
        MCEXEC_USAGE_WITH_ENVS
    } else {
        MCEXEC_USAGE_WITHOUT_ENVS
    };
    unsafe {
        mcexec_print_usage_write_bridge(MCEXEC_USAGE_PREFIX.as_ptr(), MCEXEC_USAGE_PREFIX.len());
        mcexec_print_usage_write_bridge(prog_bytes.as_ptr(), prog_bytes.len());
        mcexec_print_usage_write_bridge(suffix.as_ptr(), suffix.len());
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_env_list_count_result(head: *const EnvListEntry) -> i32 {
    let mut count = 0i32;
    let mut current = head;

    while !current.is_null() {
        count = count.saturating_add(1);
        current = unsafe { (*current).next };
    }
    count
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_search_env_list_result(
    head: *mut EnvListEntry,
    name: *const u8,
) -> *mut EnvListEntry {
    let mut current = head;

    while !current.is_null() {
        let current_name = unsafe { (*current).name as *const u8 };
        if !name.is_null() && !current_name.is_null() && unsafe { strcmp(name, current_name) } == 0
        {
            return current;
        }
        current = unsafe { (*current).next };
    }
    core::ptr::null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_add_env_list_result(
    headp: *mut *mut EnvListEntry,
    add_string: *mut u8,
) -> i32 {
    if headp.is_null() || add_string.is_null() {
        return -22;
    }

    let name = unsafe { dup_cstr(add_string) };
    if name.is_null() {
        return -12;
    }

    let mut idx = 0usize;
    while unsafe { *name.add(idx) } != 0 && unsafe { *name.add(idx) } != b'=' {
        idx += 1;
    }
    if unsafe { *name.add(idx) } != b'=' {
        unsafe {
            free(name);
        }
        return -22;
    }

    unsafe {
        *name.add(idx) = 0;
    }
    let value = unsafe { name.add(idx + 1) };

    let head = unsafe { *headp };
    if !head.is_null() {
        let exist = unsafe { mcexec_search_env_list_result(head, name) };
        if !exist.is_null() {
            unsafe {
                free(name);
            }
            return 0;
        }
    }

    let current = unsafe { malloc(core::mem::size_of::<EnvListEntry>()) as *mut EnvListEntry };
    if current.is_null() {
        unsafe {
            free(name);
        }
        return -12;
    }

    unsafe {
        (*current).str_ptr = add_string;
        (*current).name = name;
        (*current).value = value;
        (*current).next = head;
        *headp = current;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_add_env_list_body(
    headp: *mut *mut EnvListEntry,
    add_string: *mut u8,
) {
    if unsafe { mcexec_add_env_list_result(headp, add_string) } == -EINVAL {
        unsafe { mcexec_add_env_list_invalid_bridge(add_string as *const u8) };
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_destroy_env_list_result(head: *mut EnvListEntry) {
    let mut current = head;
    while !current.is_null() {
        let next = unsafe { (*current).next };
        unsafe {
            free((*current).name);
            free(current as *mut u8);
        }
        current = next;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_create_local_environ_result(
    inc_list: *mut EnvListEntry,
) -> *mut *mut u8 {
    let count = unsafe { mcexec_env_list_count_result(inc_list) };
    let slots = (count as usize).saturating_add(1);
    let local_env = unsafe { malloc(core::mem::size_of::<*mut u8>() * slots) as *mut *mut u8 };
    if local_env.is_null() {
        return core::ptr::null_mut();
    }
    unsafe {
        *local_env.add(count as usize) = core::ptr::null_mut();
    }

    let mut current = inc_list;
    let mut idx = 0usize;
    while !current.is_null() {
        let dup = unsafe { dup_cstr((*current).str_ptr) };
        if dup.is_null() {
            unsafe {
                *local_env.add(idx) = core::ptr::null_mut();
                mcexec_destroy_local_environ_result(local_env);
            }
            return core::ptr::null_mut();
        }
        unsafe {
            *local_env.add(idx) = dup;
            current = (*current).next;
        }
        idx += 1;
    }
    local_env
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_destroy_local_environ_result(local_env: *mut *mut u8) {
    if local_env.is_null() {
        return;
    }

    let mut idx = 0usize;
    while unsafe { !(*local_env.add(idx)).is_null() } {
        unsafe {
            free(*local_env.add(idx));
            *local_env.add(idx) = core::ptr::null_mut();
        }
        idx += 1;
    }
    unsafe {
        free(local_env as *mut u8);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_collect_main_envs_body(
    extra_env_headp: *mut *mut EnvListEntry,
    envs_len: *mut c_int,
    envs: *mut *mut u8,
) {
    if extra_env_headp.is_null() || envs_len.is_null() || envs.is_null() {
        return;
    }

    let envp = unsafe { environ };
    if !envp.is_null() {
        let mut idx = 0usize;
        while unsafe { !(*envp.add(idx)).is_null() } {
            unsafe {
                mcexec_add_env_list_body(extra_env_headp, *envp.add(idx));
            }
            idx += 1;
        }
    }

    let local_env = unsafe { mcexec_create_local_environ_result(*extra_env_headp) };
    let len = unsafe { flatten_strings(core::ptr::null_mut(), local_env, envs) };
    unsafe {
        *envs_len = len;
        mcexec_destroy_local_environ_result(local_env);
        mcexec_destroy_env_list_result(*extra_env_headp);
        *extra_env_headp = core::ptr::null_mut();
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_collect_default_envs_body(
    envs_len: *mut c_int,
    envs: *mut *mut u8,
) {
    if envs_len.is_null() || envs.is_null() {
        return;
    }

    let len = unsafe { flatten_strings(core::ptr::null_mut(), environ, envs) };
    unsafe {
        *envs_len = len;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_init_page_altroot_body() {
    let page_size = unsafe { mcexec_main_page_size_bridge() };
    let mut altroot = unsafe { getenv(MCEXEC_ALT_ROOT_ENV.as_ptr()) };
    if altroot.is_null() {
        altroot = MCEXEC_DEFAULT_ALTROOT.as_ptr() as *mut u8;
    }
    unsafe { mcexec_main_publish_page_altroot_bridge(page_size, altroot as *const u8) };
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_shift_flib_affinity_result(
    affinity: *const u8,
    shift: i32,
) -> *mut u8 {
    if affinity.is_null() {
        return core::ptr::null_mut();
    }
    let bytes = unsafe { cstr_bytes(affinity) };

    let mut cursor = 0usize;
    let mut tokens = 0usize;
    let mut out_len = 0usize;
    while let Some((start, end)) = next_comma_token(bytes, &mut cursor) {
        let shifted = atoi_segment(bytes, start, end).saturating_sub(shift);
        if tokens > 0 {
            out_len += 1;
        }
        out_len += decimal_len_i32(shifted);
        tokens += 1;
    }

    let result = unsafe { malloc(out_len + 1) };
    if result.is_null() {
        return core::ptr::null_mut();
    }

    cursor = 0;
    tokens = 0;
    let mut out = result;
    while let Some((start, end)) = next_comma_token(bytes, &mut cursor) {
        let shifted = atoi_segment(bytes, start, end).saturating_sub(shift);
        if tokens > 0 {
            unsafe {
                *out = b',';
                out = out.add(1);
            }
        }
        let written = unsafe { write_i32_decimal(out, shifted) };
        unsafe {
            out = out.add(written);
        }
        tokens += 1;
    }
    unsafe {
        *out = 0;
    }
    result
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_apply_flib_affinity_body() {
    let current = unsafe { getenv(FLIB_AFFINITY_ON_PROCESS_ENV.as_ptr()) };
    if current.is_null() {
        return;
    }

    let shifted = unsafe { mcexec_shift_flib_affinity_result(current as *const u8, 12) };
    if shifted.is_null() {
        unsafe { mcexec_flib_affinity_alloc_failed_bridge() };
    }

    unsafe {
        mcexec_flib_affinity_log_bridge(current as *const u8, shifted as *const u8);
        setenv(
            FLIB_AFFINITY_ON_PROCESS_ENV.as_ptr(),
            shifted as *const u8,
            1,
        );
        free(shifted);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_parse_rlimit_stack_env_result(
    env: *const u8,
    cur: *mut u64,
    max: *mut u64,
) -> i32 {
    if env.is_null() || cur.is_null() || max.is_null() {
        return 1;
    }
    let bytes = unsafe { cstr_bytes(env) };
    let mut cursor = 0usize;

    let Some((cur_start, cur_end)) = next_comma_token(bytes, &mut cursor) else {
        return 1;
    };
    let cur_value = atobytes_bytes(unsafe { bytes_range(bytes, cur_start, cur_end) });
    if cur_value == 0 {
        return 2;
    }

    let Some((max_start, max_end)) = next_comma_token(bytes, &mut cursor) else {
        return 4;
    };
    let max_value = atobytes_bytes(unsafe { bytes_range(bytes, max_start, max_end) });
    if max_value == 0 {
        return 5;
    }

    unsafe {
        *cur = cur_value;
        *max = max_value;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_apply_main_stack_body(
    desc: *mut c_void,
    env: *const u8,
    stack_max: c_long,
    stack_premap: c_long,
    rlim_cur: *mut c_ulong,
    rlim_max: *mut c_ulong,
) -> c_int {
    if rlim_cur.is_null() || rlim_max.is_null() {
        return 1;
    }

    if !env.is_null() {
        let mut saved_cur = 0u64;
        let mut saved_max = 0u64;
        let parse_rc =
            unsafe { mcexec_parse_rlimit_stack_env_result(env, &mut saved_cur, &mut saved_max) };
        if parse_rc != 0 {
            unsafe { mcexec_main_stack_parse_failed_bridge(parse_rc) };
            return 1;
        }
        unsafe {
            mcexec_apply_saved_stack_limit_result(saved_cur, saved_max, rlim_cur, rlim_max);
        }
    }

    unsafe {
        mcexec_apply_stack_max_result(stack_max, rlim_cur, rlim_max);
        mcexec_main_stack_publish_bridge(desc, *rlim_cur, *rlim_max, stack_premap);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_apply_saved_stack_limit_result(
    mut saved_cur: u64,
    saved_max: u64,
    rlim_cur: *mut u64,
    rlim_max: *mut u64,
) {
    if rlim_cur.is_null() || rlim_max.is_null() {
        return;
    }

    if saved_cur > saved_max {
        saved_cur = saved_max;
    }
    unsafe {
        if saved_max > *rlim_max {
            *rlim_max = saved_max;
        }
        if saved_cur > *rlim_cur {
            *rlim_cur = saved_cur;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_flatten_strings_result(
    pre_strings: *mut u8,
    strings: *mut *mut u8,
    flat: *mut *mut u8,
) -> i32 {
    if strings.is_null() || flat.is_null() {
        return 0;
    }

    let nr_strings = unsafe { count_cstr_array(strings) };
    let mut pre_strings_count = 0usize;
    let mut pre_strings_len = 0usize;
    let pre_strings_flat = pre_strings as *const isize;

    let mut full_len = core::mem::size_of::<isize>() + core::mem::size_of::<*mut u8>();
    if !pre_strings.is_null() {
        pre_strings_count = unsafe { *pre_strings_flat } as usize;
        let pre_end = unsafe { *pre_strings_flat.add(pre_strings_count + 1) } as usize;
        let pre_header_len = core::mem::size_of::<isize>() * (pre_strings_count + 2);
        if pre_end < pre_header_len {
            return 0;
        }
        pre_strings_len = pre_end - pre_header_len;
        let Some(next_len) = full_len
            .checked_add(pre_strings_count * core::mem::size_of::<isize>())
            .and_then(|v| v.checked_add(pre_strings_len))
        else {
            return 0;
        };
        full_len = next_len;
    }

    let mut idx = 0usize;
    while idx < nr_strings {
        let string = unsafe { *strings.add(idx) };
        let len = unsafe { cstr_len(string as *const u8) } + 1;
        let Some(next_len) = full_len
            .checked_add(core::mem::size_of::<*mut u8>())
            .and_then(|v| v.checked_add(len))
        else {
            return 0;
        };
        full_len = next_len;
        idx += 1;
    }

    let align = core::mem::size_of::<isize>() - 1;
    full_len = (full_len + align) & !align;
    let base = unsafe { malloc(full_len) };
    if base.is_null() {
        return 0;
    }
    unsafe {
        zero_bytes(base, full_len);
    }

    let flat_words = base as *mut isize;
    unsafe {
        *flat_words = (nr_strings + pre_strings_count) as isize;
    }

    let mut out =
        unsafe { base.add((nr_strings + pre_strings_count + 2) * core::mem::size_of::<isize>()) };
    if !pre_strings.is_null() {
        idx = 0;
        while idx < pre_strings_count {
            let old_offset = unsafe { *pre_strings_flat.add(idx + 1) };
            unsafe {
                *flat_words.add(idx + 1) =
                    old_offset + (nr_strings * core::mem::size_of::<isize>()) as isize;
            }
            idx += 1;
        }

        let start = unsafe { *pre_strings_flat.add(1) } as usize;
        unsafe {
            copy_ptr_bytes(out, pre_strings.add(start), pre_strings_len);
            out = out.add(pre_strings_len);
        }
    }

    idx = 0;
    while idx < nr_strings {
        let string = unsafe { *strings.add(idx) };
        let len = unsafe { cstr_len(string as *const u8) } + 1;
        unsafe {
            *flat_words.add(idx + pre_strings_count + 1) = out.offset_from(base) as isize;
            copy_ptr_bytes(out, string as *const u8, len);
            out = out.add(len);
        }
        idx += 1;
    }

    let len = unsafe { out.offset_from(base) } as usize;
    unsafe {
        *flat_words.add(nr_strings + pre_strings_count + 1) = len as isize;
        *flat = base;
    }

    if len > i32::MAX as usize {
        unsafe {
            free(base);
            *flat = core::ptr::null_mut();
        }
        return 0;
    }
    len as i32
}

#[no_mangle]
pub unsafe extern "C" fn flatten_strings(
    pre_strings: *mut u8,
    strings: *mut *mut u8,
    flat: *mut *mut u8,
) -> i32 {
    unsafe { mcexec_flatten_strings_result(pre_strings, strings, flat) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_prepare_main_desc_body(
    desc: *mut c_void,
    argv_tail: *mut *mut u8,
    shebang_argv: *mut *mut u8,
    envs_len: c_int,
    envs: *mut u8,
    target_core: c_int,
    enable_vdso: c_int,
) {
    if desc.is_null() {
        return;
    }

    unsafe {
        mcexec_desc_snapshot_rlimits_bridge(desc);
        mcexec_desc_publish_env_bridge(desc, envs_len, envs);
    }

    let mut shebang_argv_flat: *mut u8 = core::ptr::null_mut();
    if !shebang_argv.is_null() {
        unsafe {
            flatten_strings(core::ptr::null_mut(), shebang_argv, &mut shebang_argv_flat);
        }
    }

    let mut args: *mut u8 = core::ptr::null_mut();
    let args_len = unsafe { flatten_strings(shebang_argv_flat, argv_tail, &mut args) };
    unsafe {
        mcexec_desc_publish_args_cpu_bridge(
            desc,
            args_len as c_ulong,
            args,
            target_core,
            enable_vdso,
        );
        free(shebang_argv as *mut u8);
        free(shebang_argv_flat);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_shebang_argv_extend_result(
    shebang_argv_p: *mut *mut *mut u8,
    shebang: *mut u8,
) -> i32 {
    if shebang_argv_p.is_null() || shebang.is_null() {
        return -EINVAL;
    }

    let mut param_count = 1usize;
    let mut params = core::ptr::null_mut();
    let mut idx = 0usize;
    while unsafe { *shebang.add(idx) } != 0 {
        if unsafe { *shebang.add(idx) } == b' ' {
            unsafe {
                *shebang.add(idx) = 0;
                params = shebang.add(idx + 1);
            }
            param_count += 1;
            break;
        }
        idx += 1;
    }

    let old = unsafe { *shebang_argv_p };
    let old_count = unsafe { count_cstr_array(old) };
    let new_count = old_count + param_count;
    let bytes = (new_count + 1) * core::mem::size_of::<*mut u8>();
    let new_argv = unsafe { malloc(bytes) as *mut *mut u8 };
    if new_argv.is_null() {
        return -12;
    }
    unsafe {
        zero_bytes(new_argv as *mut u8, bytes);
        *new_argv = shebang;
        if !params.is_null() {
            *new_argv.add(1) = params;
        }

        let mut copy_idx = 0usize;
        while copy_idx < old_count {
            *new_argv.add(param_count + copy_idx) = *old.add(copy_idx);
            copy_idx += 1;
        }
        *new_argv.add(new_count) = core::ptr::null_mut();
        if !old.is_null() {
            free(old as *mut u8);
        }
        *shebang_argv_p = new_argv;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_execve1_transfer_buffer_result(
    desc: *const u8,
    desc_size: usize,
    args: *const u8,
    args_len: usize,
    buffer_out: *mut *mut u8,
    size_out: *mut usize,
) -> i32 {
    if desc.is_null() || args.is_null() || buffer_out.is_null() || size_out.is_null() {
        return -EINVAL;
    }

    let Some(total) = desc_size.checked_add(args_len) else {
        return -12;
    };
    let buffer = unsafe { malloc(total) };
    if buffer.is_null() {
        return -12;
    }
    unsafe {
        copy_ptr_bytes(buffer, desc, desc_size);
        copy_ptr_bytes(buffer.add(desc_size), args, args_len);
        *buffer_out = buffer;
        *size_out = total;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_addfd_prepare_result(
    path: *const u8,
    mcosid: i32,
    linux_path: *mut u8,
    linux_size: usize,
    mck_path: *mut u8,
    mck_size: usize,
    pathlen: *mut usize,
) -> i32 {
    if path.is_null()
        || linux_path.is_null()
        || mck_path.is_null()
        || pathlen.is_null()
        || linux_size == 0
        || mck_size == 0
    {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    let prefix = if has_prefix_at(bytes, 0, PROC_PREFIX) {
        &PROC_PREFIX[..PROC_PREFIX.len() - 1]
    } else if has_prefix_at(bytes, 0, SYS_PREFIX) {
        &SYS_PREFIX[..SYS_PREFIX.len() - 1]
    } else {
        return 0;
    };

    let mut mcos_buf = [0u8; 32];
    let mut mcos_out = mcos_buf.as_mut_ptr();
    unsafe {
        mcos_out = copy_bytes(mcos_out, b"mcos");
        let len = write_i32_decimal(mcos_out, mcosid);
        mcos_out = mcos_out.add(len);
        write_nul(mcos_out);
    }
    let mcos_len = unsafe { mcos_out.offset_from(mcos_buf.as_ptr()) as usize };
    let mcos = unsafe { core::slice::from_raw_parts(mcos_buf.as_ptr(), mcos_len) };
    let Some(mcos_pos) = find_subslice(bytes, mcos) else {
        return 0;
    };
    let real_path = unsafe { bytes_range(bytes, mcos_pos + mcos_len, bytes.len()) };

    let linux_len = prefix.len() + real_path.len();
    if linux_len >= linux_size || bytes.len() >= mck_size {
        return -ENAMETOOLONG;
    }

    let mut out = linux_path;
    unsafe {
        out = copy_bytes(out, prefix);
        out = copy_bytes(out, real_path);
        write_nul(out);

        out = copy_bytes(mck_path, bytes);
        write_nul(out);
        *pathlen = linux_len;
    }
    1
}

unsafe fn mcexec_list_next(list: *const McexecListHead) -> *mut McexecListHead {
    unsafe { read_volatile(&(*list).next) }
}

unsafe fn mcexec_list_prev(list: *const McexecListHead) -> *mut McexecListHead {
    unsafe { read_volatile(&(*list).prev) }
}

unsafe fn mcexec_list_set_next(list: *mut McexecListHead, value: *mut McexecListHead) {
    unsafe { write_volatile(&mut (*list).next, value) };
}

unsafe fn mcexec_list_set_prev(list: *mut McexecListHead, value: *mut McexecListHead) {
    unsafe { write_volatile(&mut (*list).prev, value) };
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_list_add_body(
    new: *mut McexecListHead,
    head: *mut McexecListHead,
) {
    let next = unsafe { mcexec_list_next(head) };
    unsafe {
        mcexec_list_set_prev(next, new);
        mcexec_list_set_next(new, next);
        mcexec_list_set_prev(new, head);
        mcexec_list_set_next(head, new);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_list_del_body(entry: *mut McexecListHead) {
    let next = unsafe { mcexec_list_next(entry) };
    let prev = unsafe { mcexec_list_prev(entry) };
    unsafe {
        mcexec_list_set_prev(next, prev);
        mcexec_list_set_next(prev, next);
        mcexec_list_set_next(entry, LIST_POISON1 as *mut McexecListHead);
        mcexec_list_set_prev(entry, LIST_POISON2 as *mut McexecListHead);
    }
}

#[no_mangle]
pub unsafe extern "C" fn overlay_addfd(fd: c_int, path: *const u8) {
    let mut linux_path = [0u8; PATH_MAX];
    let mut mck_path = [0u8; PATH_MAX];
    let mut pathlen = 0usize;

    let rc = unsafe {
        mcexec_overlay_addfd_prepare_result(
            path,
            mcexec_overlay_mcosid_bridge(),
            linux_path.as_mut_ptr(),
            linux_path.len(),
            mck_path.as_mut_ptr(),
            mck_path.len(),
            &mut pathlen,
        )
    };
    if rc <= 0 {
        if rc < 0 {
            unsafe { mcexec_overlay_addfd_path_too_long_bridge() };
        }
        return;
    }

    unsafe {
        mcexec_overlay_addfd_publish_bridge(fd, linux_path.as_ptr(), mck_path.as_ptr(), pathlen);
    }
}

#[no_mangle]
pub unsafe extern "C" fn overlay_delfd(fd: c_int) {
    unsafe { mcexec_overlay_delfd_bridge(fd) };
}

#[no_mangle]
pub extern "C" fn mcexec_default_heap_extension_result(heap_extension: u64, page_size: u64) -> u64 {
    if heap_extension == ULONG_MAX {
        page_size
    } else {
        heap_extension
    }
}

#[no_mangle]
pub extern "C" fn mcexec_default_thread_count_result(
    nr_threads: i32,
    omp_present: i32,
    omp_threads: i32,
    nr_processes: i32,
    ncpu: i32,
) -> i32 {
    if nr_threads > 0 {
        nr_threads
    } else if omp_present != 0 {
        omp_threads + 4
    } else if nr_processes > 0 && nr_processes < ncpu {
        let result = (ncpu / nr_processes) + 4;
        if result == 0 {
            2
        } else {
            result
        }
    } else if nr_processes == ncpu {
        1
    } else {
        ncpu
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_plan_process_threads_result(
    nr_processes: *mut c_int,
    nr_threads: c_int,
    ncpu: c_int,
    planned_threads: *mut c_int,
) -> c_int {
    if nr_processes.is_null() || planned_threads.is_null() {
        return -EINVAL;
    }

    let mut processes = unsafe { *nr_processes };
    let flib_processes = unsafe { getenv(FLIB_NUM_PROCESS_ON_NODE_ENV.as_ptr()) };
    if !flib_processes.is_null() && processes == 0 {
        processes =
            unsafe { strtol(flib_processes as *const u8, core::ptr::null_mut(), 10) as c_int };
        unsafe {
            *nr_processes = processes;
            mcexec_process_thread_plan_flib_log_bridge(processes);
        }
    }

    if processes > ncpu {
        return -EINVAL;
    }

    let omp_threads = unsafe { getenv(OMP_NUM_THREADS_ENV.as_ptr()) };
    let planned = if omp_threads.is_null() {
        mcexec_default_thread_count_result(nr_threads, 0, 0, processes, ncpu)
    } else {
        mcexec_default_thread_count_result(
            nr_threads,
            1,
            unsafe { strtol(omp_threads as *const u8, core::ptr::null_mut(), 10) as c_int },
            processes,
            ncpu,
        )
    };

    unsafe {
        *planned_threads = planned;
    }
    0
}

#[no_mangle]
pub extern "C" fn mcexec_mpol_flags_result(
    no_heap: i32,
    no_stack: i32,
    no_bss: i32,
    shm_premap: i32,
) -> u64 {
    let mut flags = 0u64;
    if no_heap != 0 {
        flags |= MPOL_NO_HEAP;
    }
    if no_stack != 0 {
        flags |= MPOL_NO_STACK;
    }
    if no_bss != 0 {
        flags |= MPOL_NO_BSS;
    }
    if shm_premap != 0 {
        flags |= MPOL_SHM_PREMAP;
    }
    flags
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ompi_mpol_policy_result(
    mpol: *const u8,
    mpol_default: i32,
    mpol_interleave: i32,
    mpol_bind: i32,
    mpol_preferred: i32,
    mode: *mut i32,
    nodemask_action: *mut i32,
) -> i32 {
    if mpol.is_null() || mode.is_null() || nodemask_action.is_null() {
        return 0;
    }
    let bytes = unsafe { cstr_bytes(mpol) };

    let (selected_mode, action) = if has_prefix_at(bytes, 0, b"localalloc") {
        (mpol_default, MPOL_NODEMASK_NONE)
    } else if has_prefix_at(bytes, 0, b"interleave_local") {
        (mpol_interleave, MPOL_NODEMASK_LOCAL)
    } else if has_prefix_at(bytes, 0, b"interleave_nonlocal") {
        (mpol_interleave, MPOL_NODEMASK_NONLOCAL)
    } else if has_prefix_at(bytes, 0, b"interleave_all") {
        (mpol_interleave, MPOL_NODEMASK_ALL)
    } else if has_prefix_at(bytes, 0, b"bind_local") {
        (mpol_bind, MPOL_NODEMASK_LOCAL)
    } else if has_prefix_at(bytes, 0, b"bind_nonlocal") {
        (mpol_bind, MPOL_NODEMASK_NONLOCAL)
    } else if has_prefix_at(bytes, 0, b"bind_all") {
        (mpol_bind, MPOL_NODEMASK_ALL)
    } else if has_prefix_at(bytes, 0, b"prefer_local") {
        (mpol_preferred, MPOL_NODEMASK_LOCAL)
    } else if has_prefix_at(bytes, 0, b"prefer_nonlocal") {
        (mpol_preferred, MPOL_NODEMASK_NONLOCAL)
    } else {
        return 0;
    };

    unsafe {
        *mode = selected_mode;
        *nodemask_action = action;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_apply_desc_runtime_body(
    desc: *mut c_void,
    profile: c_int,
    nr_processes: c_int,
    mpol_no_heap: c_int,
    mpol_no_stack: c_int,
    mpol_no_bss: c_int,
    mpol_shm_premap: c_int,
    mpol_threshold: c_ulong,
    heap_extension: c_ulong,
    mpol_bind_nodes: *const u8,
    mpol_default: c_int,
    mpol_interleave: c_int,
    mpol_bind: c_int,
    mpol_preferred: c_int,
    pld_mpol_max: c_int,
    enable_uti: c_int,
    uti_thread_rank: c_int,
    uti_use_last_cpu: c_int,
    straight_map: c_int,
    straight_map_threshold: c_ulong,
    enable_tofu: c_int,
    mcexec_flags: c_ulong,
) {
    if desc.is_null() {
        return;
    }

    let flags = mcexec_mpol_flags_result(mpol_no_heap, mpol_no_stack, mpol_no_bss, mpol_shm_premap)
        as c_ulong;
    unsafe {
        mcexec_desc_publish_mpol_base_bridge(
            desc,
            profile,
            nr_processes,
            flags,
            mpol_threshold,
            heap_extension,
            pld_mpol_max,
        );
    }

    if !mpol_bind_nodes.is_null() {
        unsafe { mcexec_desc_apply_bind_nodes_bridge(desc, mpol_bind_nodes) };
    } else {
        let mpol = unsafe { getenv(OMPI_MCA_PLE_MEMORY_POLICY_ENV.as_ptr()) };
        if !mpol.is_null() {
            let mut mode = 0;
            let mut nodemask_action = MPOL_NODEMASK_NONE;
            unsafe { mcexec_desc_ompi_policy_log_bridge(mpol as *const u8) };
            if unsafe {
                mcexec_ompi_mpol_policy_result(
                    mpol as *const u8,
                    mpol_default,
                    mpol_interleave,
                    mpol_bind,
                    mpol_preferred,
                    &mut mode,
                    &mut nodemask_action,
                )
            } != 0
            {
                unsafe { mcexec_desc_apply_ompi_policy_bridge(desc, mode, nodemask_action) };
            }
            unsafe { mcexec_desc_mpol_log_bridge(desc as *const c_void) };
        }
    }

    let thp_disable = unsafe { mcexec_get_thp_disable_body() };
    unsafe {
        mcexec_desc_publish_runtime_flags_bridge(
            desc,
            enable_uti,
            uti_thread_rank,
            uti_use_last_cpu,
            thp_disable,
            straight_map,
            straight_map_threshold,
            enable_tofu,
            mcexec_flags,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_apply_stack_max_result(
    stack_max: i64,
    rlim_cur: *mut u64,
    rlim_max: *mut u64,
) {
    if stack_max == -1 || rlim_cur.is_null() || rlim_max.is_null() {
        return;
    }

    let stack_max = stack_max as u64;
    unsafe {
        *rlim_cur = stack_max;
        if *rlim_max != ULONG_MAX && *rlim_max < *rlim_cur {
            *rlim_max = *rlim_cur;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_is_absolute_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    (!bytes.is_empty() && byte_at(bytes, 0) == b'/') as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_is_single_component_exec_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    let dot_prefixed = !bytes.is_empty() && byte_at(bytes, 0) == b'.';
    (!dot_prefixed && !contains_byte(bytes, b'/')) as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_len_less_than_result(path: *const u8, limit: usize) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    (bytes.len() < limit) as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_copy_path_result(
    path: *const u8,
    out: *mut u8,
    size: usize,
) -> i32 {
    if path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    if bytes.len() >= size || bytes.len() > i32::MAX as usize {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, bytes);
        write_nul(dst);
    }
    bytes.len() as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_join_path_result(
    prefix: *const u8,
    path: *const u8,
    out: *mut u8,
    size: usize,
) -> i32 {
    unsafe { write_joined_path(prefix, path, out, size) }
}

#[no_mangle]
pub unsafe extern "C" fn lookup_exec_path(
    filename: *mut u8,
    path: *mut u8,
    max_len: c_int,
    execvp: c_int,
) -> c_int {
    if filename.is_null() || path.is_null() {
        return EINVAL;
    }

    let filename_bytes = unsafe { cstr_bytes(filename as *const u8) };
    let filename_absolute = !filename_bytes.is_empty() && byte_at(filename_bytes, 0) == b'/';
    let filename_single_component = {
        let dot_prefixed = !filename_bytes.is_empty() && byte_at(filename_bytes, 0) == b'.';
        !dot_prefixed && !contains_byte(filename_bytes, b'/')
    };
    let filename_len_lt_255 = filename_bytes.len() < 255;
    let mut found = false;

    if !filename_absolute {
        if filename_single_component {
            if execvp == 0 {
                let copy_rc = unsafe { write_cstr_bytes(filename as *const u8, path, max_len) };
                if copy_rc < 0 {
                    return if copy_rc == -ENAMETOOLONG {
                        ENAMETOOLONG
                    } else {
                        EINVAL
                    };
                }

                let access_errno = unsafe { lookup_access_errno(path as *const u8) };
                if access_errno != 0 {
                    return access_errno;
                }
                found = true;
            } else {
                let mut path_env = unsafe { getenv(COKERNEL_PATH_ENV.as_ptr()) };
                if path_env.is_null() {
                    path_env = unsafe { getenv(PATH_ENV.as_ptr()) };
                }
                if path_env.is_null() {
                    return ENOENT;
                }
                if !filename_len_lt_255 {
                    return ENAMETOOLONG;
                }

                let path_bytes = unsafe { cstr_bytes(path_env as *const u8) };
                let mut start = 0usize;
                while start <= path_bytes.len() {
                    let mut end = start;
                    while end < path_bytes.len() && byte_at(path_bytes, end) != b':' {
                        end += 1;
                    }

                    let token = unsafe { bytes_range(path_bytes, start, end) };
                    let join_rc =
                        unsafe { write_joined_path_bytes(token, filename_bytes, path, max_len) };
                    if join_rc < 0 {
                        unsafe { mcexec_lookup_array_too_small_bridge() };
                    } else if unsafe { access(path as *const u8, X_OK) } == 0 {
                        found = true;
                        break;
                    }

                    if end == path_bytes.len() {
                        break;
                    }
                    start = end + 1;
                }

                if !found {
                    return ENOENT;
                }
            }
        }

        if !found {
            let copy_rc = unsafe { write_cstr_bytes(filename as *const u8, path, max_len) };
            if copy_rc < 0 {
                unsafe { mcexec_lookup_array_too_small_bridge() };
                return ENOMEM;
            }
            found = true;
        }
    } else {
        let root = unsafe { getenv(COKERNEL_EXEC_ROOT_ENV.as_ptr()) };
        let copy_rc = if !root.is_null() {
            unsafe {
                write_joined_path_bytes(
                    cstr_bytes(root as *const u8),
                    filename_bytes,
                    path,
                    max_len,
                )
            }
        } else {
            unsafe { write_cstr_bytes(filename as *const u8, path, max_len) }
        };

        if copy_rc < 0 {
            unsafe { mcexec_lookup_array_too_small_bridge() };
            return ENOMEM;
        }
        found = true;
    }

    let stat_errno = unsafe { mcexec_lookup_lstat_errno_bridge(path as *const u8) };
    if stat_errno != 0 {
        unsafe { mcexec_lookup_stat_error_bridge(path as *const u8, stat_errno) };
        return stat_errno;
    }

    if !found {
        unsafe { mcexec_lookup_not_found_bridge(filename as *const u8) };
        return ENOENT;
    }

    unsafe { mcexec_lookup_success_bridge(path as *const u8) };
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_objdump_rpath_cmd_result(
    path: *const u8,
    out: *mut u8,
    size: usize,
) -> i32 {
    if path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let path_bytes = unsafe { cstr_bytes(path) };
    let Some(total) = OBJDUMP_RPATH_PREFIX
        .len()
        .checked_add(path_bytes.len())
        .and_then(|v| v.checked_add(OBJDUMP_RPATH_SUFFIX.len()))
    else {
        return -ENAMETOOLONG;
    };

    if total >= size || total > i32::MAX as usize {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, OBJDUMP_RPATH_PREFIX);
        dst = copy_bytes(dst, path_bytes);
        dst = copy_bytes(dst, OBJDUMP_RPATH_SUFFIX);
        write_nul(dst);
    }
    total as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_find_libdir_body(libdir: *mut u8, len: usize) -> isize {
    if libdir.is_null() || len == 0 {
        return -(EINVAL as isize);
    }

    let mut path = [0u8; PATH_MAX];
    let mut cmd = [0u8; PATH_MAX];
    let mut line: *mut u8 = core::ptr::null_mut();
    let mut linelen = 0usize;

    let mut rc = unsafe { mcexec_find_libdir_readlink_bridge(path.as_mut_ptr(), path.len()) };
    if rc < 0 {
        let error = unsafe { *__errno_location() };
        unsafe { mcexec_find_libdir_readlink_failed_bridge(error) };
        return -(error as isize);
    }

    if rc as usize >= path.len() {
        let mut dst = path.as_mut_ptr();
        unsafe {
            dst = copy_bytes(dst, PROC_SELF_EXE);
            write_nul(dst);
        }
    } else {
        unsafe {
            *path.as_mut_ptr().add(rc as usize) = 0;
        }
    }

    if unsafe { mcexec_objdump_rpath_cmd_result(path.as_ptr(), cmd.as_mut_ptr(), cmd.len()) } < 0 {
        return -(ERANGE as isize);
    }

    let filep = unsafe { mcexec_find_libdir_popen_bridge(cmd.as_ptr()) };
    if filep.is_null() {
        let error = unsafe { *__errno_location() };
        unsafe { mcexec_find_libdir_objdump_failed_bridge(error) };
        return -(error as isize);
    }

    rc = unsafe { mcexec_find_libdir_getline_bridge(&mut line, &mut linelen, filep) };
    if rc <= 0 {
        let error = unsafe { *__errno_location() };
        unsafe {
            mcexec_find_libdir_rpath_not_found_bridge(error);
            mcexec_find_libdir_pclose_bridge(filep);
            if !line.is_null() {
                mcexec_find_libdir_free_bridge(line);
            }
        }
        return -(error as isize);
    }

    unsafe {
        *line.add((rc - 1) as usize) = 0;
    }

    let line_bytes = unsafe { cstr_bytes(line as *const u8) };
    if !contains_byte(line_bytes, b'/') {
        rc = -(EINVAL as isize);
    } else if unsafe { mcexec_copy_path_result(line as *const u8, libdir, len) } < 0 {
        rc = -(ERANGE as isize);
    } else {
        rc = line_bytes.len() as isize;
    }

    unsafe {
        mcexec_find_libdir_pclose_bridge(filep);
        mcexec_find_libdir_free_bridge(line);
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_ld_preload_init_body() {
    let mut libdir = [0u8; PATH_MAX];
    let mut envbuf = [0u8; PATH_MAX];

    if unsafe { mcexec_find_libdir_body(libdir.as_mut_ptr(), libdir.len()) } < 0 {
        unsafe { mcexec_ld_preload_find_failed_bridge() };
        return;
    }

    let existing = unsafe { mcexec_ld_preload_getenv_bridge(MCKERNEL_LD_PRELOAD_ENV.as_ptr()) };
    let rc = unsafe {
        mcexec_build_ld_preload_result(
            libdir.as_ptr(),
            existing as *const u8,
            mcexec_ld_preload_enable_uti_bridge(),
            mcexec_ld_preload_disable_sched_yield_bridge(),
            mcexec_ld_preload_enable_qlmpi_bridge(),
            envbuf.as_mut_ptr(),
            envbuf.len(),
        )
    };
    if rc < 0 {
        unsafe { mcexec_ld_preload_line_too_long_bridge() };
        return;
    }

    if unsafe { cstr_len(envbuf.as_ptr()) } != 0 {
        if unsafe { mcexec_ld_preload_setenv_bridge(envbuf.as_ptr()) } < 0 {
            unsafe { mcexec_ld_preload_setenv_failed_bridge() };
        }
        unsafe { mcexec_ld_preload_debug_bridge(envbuf.as_ptr()) };
    }

    if !unsafe { mcexec_ld_preload_getenv_bridge(LD_PRELOAD_ENVNAME_LITERAL.as_ptr()) }.is_null() {
        unsafe {
            mcexec_ld_preload_unsetenv_bridge();
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_getpath_execveat_prepare_result(
    dirfd: i32,
    filename: *const u8,
    flags: i32,
    at_fdcwd: i32,
    at_empty_path: i32,
    at_symlink_nofollow: i32,
    pathbuf: *mut u8,
    size: usize,
    check_symlink: *mut i32,
) -> i32 {
    if filename.is_null() || pathbuf.is_null() || check_symlink.is_null() {
        return EINVAL;
    }

    unsafe {
        *check_symlink = if flags & at_symlink_nofollow != 0 {
            1
        } else {
            0
        };
    }

    let filename_bytes = unsafe { cstr_bytes(filename) };
    let dev_fd = b"/dev/fd/";
    let absolute_or_cwd =
        !filename_bytes.is_empty() && byte_at(filename_bytes, 0) == b'/' || dirfd == at_fdcwd;
    let empty_path = flags & at_empty_path != 0 && filename_bytes.is_empty();

    let total_len = if absolute_or_cwd {
        filename_bytes.len()
    } else if empty_path {
        dev_fd.len() + decimal_len_i32(dirfd)
    } else {
        dev_fd.len() + decimal_len_i32(dirfd) + 1 + filename_bytes.len()
    };

    if total_len >= size {
        return ENAMETOOLONG;
    }

    let mut out = pathbuf;
    if absolute_or_cwd {
        out = unsafe { copy_bytes(out, filename_bytes) };
    } else {
        out = unsafe { copy_bytes(out, dev_fd) };
        let written = unsafe { write_i32_decimal(out, dirfd) };
        unsafe {
            out = out.add(written);
        }
        if !empty_path {
            unsafe {
                *out = b'/';
                out = out.add(1);
            }
            out = unsafe { copy_bytes(out, filename_bytes) };
        }
    }
    unsafe {
        *out = 0;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_getpath_execveat_body(
    dirfd: c_int,
    filename: *const u8,
    flags: c_int,
    pathbuf: *mut u8,
    size: usize,
) -> c_int {
    let mut check_symlink = 0;
    let ret = unsafe {
        mcexec_getpath_execveat_prepare_result(
            dirfd,
            filename,
            flags,
            AT_FDCWD,
            AT_EMPTY_PATH,
            AT_SYMLINK_NOFOLLOW,
            pathbuf,
            size,
            &mut check_symlink,
        )
    };
    if ret != 0 {
        return ret;
    }

    if check_symlink != 0 && unsafe { readlink(filename, pathbuf, PATH_MAX) } != -1 {
        return ELOOP;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_mcos_device_path_result(
    out: *mut u8,
    size: usize,
    mcosid: i32,
) -> i32 {
    if out.is_null() || size == 0 {
        return -EINVAL;
    }

    unsafe { write_prefixed_i32_path(out, size, b"/dev/mcos", mcosid, b"") }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_proc_self_fd_path_result(
    out: *mut u8,
    size: usize,
    dirfd: i32,
) -> i32 {
    if out.is_null() || size == 0 {
        return -EINVAL;
    }

    unsafe { write_prefixed_i32_path(out, size, b"/proc/self/fd/", dirfd, b"") }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_join_path_inplace_result(
    path: *mut u8,
    size: usize,
    leaf: *const u8,
) -> i32 {
    if path.is_null() || leaf.is_null() || size == 0 {
        return -EINVAL;
    }

    let base_len = unsafe { cstr_len(path as *const u8) };
    let leaf_bytes = unsafe { cstr_bytes(leaf) };
    let mut base_end = base_len;
    if base_end > 0 && unsafe { *path.add(base_end - 1) } == b'/' {
        base_end -= 1;
    }

    let total = base_end + 1 + leaf_bytes.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = unsafe { path.add(base_end) };
    unsafe {
        *dst = b'/';
        dst = dst.add(1);
        dst = copy_bytes(dst, leaf_bytes);
        write_nul(dst);
    }
    total as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_is_dev_xpmem_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    has_exact_bytes(bytes, DEV_XPMEM) as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_has_libuti_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    find_subslice(bytes, LIBUTI).is_some() as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_uti_path_result(
    libdir: *const u8,
    path: *const u8,
    out: *mut u8,
    size: usize,
) -> i32 {
    if libdir.is_null() || path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let libdir_bytes = unsafe { cstr_bytes(libdir) };
    let path_bytes = unsafe { cstr_bytes(path) };
    let basename_start = match last_slash_pos(path_bytes) {
        Some(pos) => pos + 1,
        None => 0,
    };
    let basename = unsafe { bytes_range(path_bytes, basename_start, path_bytes.len()) };
    let middle = b"/mck/";
    let total = libdir_bytes.len() + middle.len() + basename.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, libdir_bytes);
        dst = copy_bytes(dst, middle);
        dst = copy_bytes(dst, basename);
        write_nul(dst);
    }
    total as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_proc_self_path_result(
    path: *const u8,
    mcosid: i32,
    pid: i32,
    out: *mut u8,
    size: usize,
) -> i32 {
    if path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    if !has_prefix_at(bytes, 0, PROC_SELF_PREFIX) || !path_boundary(bytes, PROC_SELF_PREFIX.len()) {
        return 0;
    }

    let suffix = unsafe { bytes_range(bytes, PROC_SELF_PREFIX.len(), bytes.len()) };
    unsafe { write_prefixed_i32_i32_path(out, size, b"/proc/mcos", mcosid, b"/", pid, suffix) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_proc_path_result(
    path: *const u8,
    mcosid: i32,
    out: *mut u8,
    size: usize,
) -> i32 {
    if path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    if !has_prefix_at(bytes, 0, b"/proc") || !path_boundary(bytes, b"/proc".len()) {
        return 0;
    }

    let suffix = unsafe { bytes_range(bytes, b"/proc".len(), bytes.len()) };
    unsafe { write_prefixed_i32_path(out, size, b"/proc/mcos", mcosid, suffix) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_sys_path_result(
    path: *const u8,
    mcosid: i32,
    out: *mut u8,
    size: usize,
    mapped_offset: *mut usize,
) -> i32 {
    if path.is_null() || out.is_null() || mapped_offset.is_null() || size == 0 {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    let sys_root = b"/sys";
    if !has_prefix_at(bytes, 0, sys_root) || !path_boundary(bytes, sys_root.len()) {
        return 0;
    }

    let suffix = unsafe { bytes_range(bytes, sys_root.len(), bytes.len()) };
    let mcos_digits = decimal_len_i32(mcosid);
    let mapped_start_len = SYS_MCOS_PREFIX.len() + mcos_digits;
    let sys_prefix = b"/sys/";
    let total = mapped_start_len + sys_prefix.len() + suffix.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, SYS_MCOS_PREFIX);
        let written = write_i32_decimal(dst, mcosid);
        dst = dst.add(written);
        *mapped_offset = mapped_start_len;
        dst = copy_bytes(dst, sys_prefix);
        dst = copy_bytes(dst, suffix);
        write_nul(dst);
    }
    total as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_normalize_overlay_path_result(
    path: *mut u8,
    len_out: *mut usize,
) -> i32 {
    if path.is_null() || len_out.is_null() {
        return -EINVAL;
    }

    let len = unsafe { cstr_len(path as *const u8) };
    let mut read = 0usize;
    let mut write = 0usize;
    let mut prev_slash = false;

    while read < len {
        let ch = unsafe { *path.add(read) };
        if ch == b'/' {
            if prev_slash {
                read += 1;
                continue;
            }
            prev_slash = true;
        } else {
            prev_slash = false;
        }
        unsafe {
            *path.add(write) = ch;
        }
        read += 1;
        write += 1;
    }

    while write > 0 && unsafe { *path.add(write - 1) } == b'/' {
        write -= 1;
    }

    unsafe {
        *path.add(write) = 0;
        *len_out = write;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_parse_proc_task_ids_result(
    path: *const u8,
    current_pid: i32,
    pid_out: *mut i32,
    tid_out: *mut i32,
) -> i32 {
    if path.is_null() || pid_out.is_null() || tid_out.is_null() {
        return 0;
    }

    let bytes = unsafe { cstr_bytes(path) };
    let self_task_prefix = b"/proc/self/task/";
    if has_prefix_at(bytes, 0, self_task_prefix) {
        if let Some((tid, tid_end)) = parse_i32_segment(bytes, self_task_prefix.len()) {
            if tid_end < bytes.len() && byte_at(bytes, tid_end) == b'/' {
                unsafe {
                    *pid_out = current_pid;
                    *tid_out = tid;
                }
                return 1;
            }
        }
    }

    let proc_prefix = b"/proc/";
    if !has_prefix_at(bytes, 0, proc_prefix) {
        return 0;
    }

    let Some((pid, pid_end)) = parse_i32_segment(bytes, proc_prefix.len()) else {
        return 0;
    };
    let task_prefix = b"/task/";
    if !has_prefix_at(bytes, pid_end, task_prefix) {
        return 0;
    }

    let tid_start = pid_end + task_prefix.len();
    if let Some((tid, tid_end)) = parse_i32_segment(bytes, tid_start) {
        if tid_end < bytes.len() && byte_at(bytes, tid_end) == b'/' {
            unsafe {
                *pid_out = pid;
                *tid_out = tid;
            }
            return 1;
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_proc_task_check_path_result(
    out: *mut u8,
    size: usize,
    mcosid: i32,
    pid: i32,
    tid: i32,
) -> i32 {
    if out.is_null() || size == 0 {
        return -EINVAL;
    }

    let total = b"/proc/mcos".len()
        + decimal_len_i32(mcosid)
        + 1
        + decimal_len_i32(pid)
        + b"/task/".len()
        + decimal_len_i32(tid);
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, b"/proc/mcos");
        let written = write_i32_decimal(dst, mcosid);
        dst = dst.add(written);
        *dst = b'/';
        dst = dst.add(1);
        let written = write_i32_decimal(dst, pid);
        dst = dst.add(written);
        dst = copy_bytes(dst, b"/task/");
        let written = write_i32_decimal(dst, tid);
        dst = dst.add(written);
        write_nul(dst);
    }
    total as i32
}

fn parse_i32_with_prefix(bytes: &[u8], prefix: &[u8]) -> Option<(i32, usize)> {
    if !has_prefix_at(bytes, 0, prefix) {
        return None;
    }
    parse_i32_segment(bytes, prefix.len())
}

fn parse_i32_after_prefix(bytes: &[u8], index: usize, prefix: &[u8]) -> Option<(i32, usize)> {
    if !has_prefix_at(bytes, index, prefix) {
        return None;
    }
    parse_i32_segment(bytes, index + prefix.len())
}

fn char_after_prefix(bytes: &[u8], prefix: &[u8], ch: u8) -> bool {
    has_prefix_at(bytes, 0, prefix)
        && prefix.len() < bytes.len()
        && byte_at(bytes, prefix.len()) == ch
}

fn pci_local_cpus_path(bytes: &[u8]) -> bool {
    let prefix = b"/sys/devices/pci";
    if !has_prefix_at(bytes, 0, prefix) {
        return false;
    }

    let mut index = prefix.len();
    let first_start = index;
    while index < bytes.len() && byte_at(bytes, index) != b'/' {
        index += 1;
    }
    if index == first_start || index >= bytes.len() {
        return false;
    }

    index += 1;
    let second_start = index;
    while index < bytes.len() && byte_at(bytes, index) != b'/' {
        index += 1;
    }
    if index == second_start || index >= bytes.len() {
        return false;
    }

    index += 1;
    let local_cpu = b"local_cpu";
    has_prefix_at(bytes, index, local_cpu)
        && index + local_cpu.len() < bytes.len()
        && byte_at(bytes, index + local_cpu.len()) == b's'
}

fn overlay_check_cpu(cpu: c_int) -> c_int {
    if cpu >= unsafe { MCEXEC_NCPU } {
        -ENOENT
    } else {
        0
    }
}

fn overlay_check_node(node: c_int) -> c_int {
    if node >= unsafe { MCEXEC_NNODES } {
        -ENOENT
    } else {
        0
    }
}

fn overlay_check_cpu_node(cpu: c_int, node: c_int) -> c_int {
    if cpu >= unsafe { MCEXEC_NCPU } || node >= unsafe { MCEXEC_NNODES } {
        return -ENOENT;
    }
    if unsafe { mcexec_overlay_cpu_in_node_bridge(cpu, node) } == 0 {
        return -ENOENT;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn overlay_blacklist(path: *const u8) -> c_int {
    if path.is_null() {
        return 0;
    }

    let mut pid = -1;
    let mut tid = -1;
    if unsafe { mcexec_parse_proc_task_ids_result(path, getpid(), &mut pid, &mut tid) } != 0 {
        let mut check_path = [0u8; PATH_MAX];
        let rc = unsafe {
            mcexec_proc_task_check_path_result(
                check_path.as_mut_ptr(),
                check_path.len(),
                mcexec_overlay_mcosid_bridge(),
                pid,
                tid,
            )
        };
        if rc < 0 {
            return -ENOENT;
        }
        if pid > 0
            && tid > 0
            && unsafe { mcexec_overlay_stat_exists_bridge(check_path.as_ptr()) } < 0
        {
            return -ENOENT;
        }
    }

    let bytes = unsafe { cstr_bytes(path) };
    if !has_prefix_at(bytes, 0, b"/sys/") {
        return 0;
    }

    if let Some((cpu, cpu_end)) = parse_i32_with_prefix(bytes, b"/sys/devices/system/cpu/cpu") {
        if let Some((node, _)) = parse_i32_after_prefix(bytes, cpu_end, b"/node") {
            return overlay_check_cpu_node(cpu, node);
        }
        return overlay_check_cpu(cpu);
    }

    if let Some((cpu, _)) = parse_i32_with_prefix(bytes, b"/sys/bus/cpu/devices/cpu") {
        return overlay_check_cpu(cpu);
    }

    if let Some((cpu, _)) = parse_i32_with_prefix(bytes, b"/sys/bus/cpu/drivers/processor/cpu") {
        return overlay_check_cpu(cpu);
    }

    if let Some((node, node_end)) = parse_i32_with_prefix(bytes, b"/sys/devices/system/node/node") {
        if let Some((cpu, _)) = parse_i32_after_prefix(bytes, node_end, b"/cpu") {
            return overlay_check_cpu_node(cpu, node);
        }
        if has_prefix_at(bytes, node_end, b"/memor")
            && node_end + b"/memor".len() < bytes.len()
            && byte_at(bytes, node_end + b"/memor".len()) == b'y'
        {
            return -ENOENT;
        }
        return overlay_check_node(node);
    }

    if let Some((node, _)) = parse_i32_with_prefix(bytes, b"/sys/bus/node/devices/node") {
        return overlay_check_node(node);
    }

    if char_after_prefix(bytes, b"/sys/devices/system/node/has", b'_')
        || char_after_prefix(bytes, b"/sys/fs/cgrou", b'p')
        || pci_local_cpus_path(bytes)
    {
        return -ENOENT;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_is_proc_task_leaf_path_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };

    let self_prefix = b"/proc/self/task/";
    if has_prefix_at(bytes, 0, self_prefix) {
        if let Some(idx) = parse_decimal_segment(bytes, self_prefix.len()) {
            if idx < bytes.len() && byte_at(bytes, idx) == b'/' && idx + 1 < bytes.len() {
                return 1;
            }
        }
    }

    let proc_prefix = b"/proc/";
    if !has_prefix_at(bytes, 0, proc_prefix) {
        return 0;
    }

    let Some(pid_end) = parse_decimal_segment(bytes, proc_prefix.len()) else {
        return 0;
    };
    let task_prefix = b"/task/";
    if !has_prefix_at(bytes, pid_end, task_prefix) {
        return 0;
    }

    let tid_start = pid_end + task_prefix.len();
    if let Some(tid_end) = parse_decimal_segment(bytes, tid_start) {
        if tid_end < bytes.len() && byte_at(bytes, tid_end) == b'/' && tid_end + 1 < bytes.len() {
            return 1;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_mapped_proc_task_parent_exists_body(mapped: *const u8) -> i32 {
    if mapped.is_null() {
        return 0;
    }

    let mut parent = [0u8; PATH_MAX];
    let mut len = 0usize;
    while len + 1 < PATH_MAX {
        let byte = unsafe { *mapped.add(len) };
        if byte == 0 {
            break;
        }
        unsafe {
            *parent.as_mut_ptr().add(len) = byte;
        }
        len += 1;
    }
    unsafe {
        *parent.as_mut_ptr().add(len) = 0;
    }

    let mut slash = None;
    let mut idx = 0usize;
    while idx < len {
        if unsafe { *parent.as_ptr().add(idx) } == b'/' {
            slash = Some(idx);
        }
        idx += 1;
    }

    let Some(slash) = slash else {
        return 0;
    };
    unsafe {
        *parent.as_mut_ptr().add(slash) = 0;
    }

    (unsafe { mcexec_overlay_stat_exists_bridge(parent.as_ptr()) } == 0) as i32
}

fn is_sys_root_path(path: *const u8) -> bool {
    let bytes = unsafe { cstr_bytes(path) };
    has_prefix_at(bytes, 0, b"/sys") && path_boundary(bytes, b"/sys".len())
}

unsafe fn fixed_copy_cstr(dst: &mut [u8; PATH_MAX], src: *const u8) -> Option<usize> {
    let len = unsafe { cstr_len(src) };
    if len >= PATH_MAX {
        return None;
    }
    unsafe {
        copy_ptr_bytes(dst.as_mut_ptr(), src, len);
    }
    unsafe {
        fixed_set(dst, len, 0);
    }
    Some(len)
}

unsafe fn fixed_get(buf: &[u8; PATH_MAX], idx: usize) -> u8 {
    unsafe { *buf.as_ptr().add(idx) }
}

unsafe fn fixed_set(buf: &mut [u8; PATH_MAX], idx: usize, value: u8) {
    unsafe {
        *buf.as_mut_ptr().add(idx) = value;
    }
}

fn fixed_next_slash(buf: &[u8; PATH_MAX], mut idx: usize, len: usize) -> Option<usize> {
    while idx < len {
        if unsafe { fixed_get(buf, idx) } == b'/' {
            return Some(idx);
        }
        idx += 1;
    }
    None
}

fn fixed_prev_slash(buf: &[u8; PATH_MAX], mut end: usize) -> Option<usize> {
    while end > 0 {
        end -= 1;
        if unsafe { fixed_get(buf, end) } == b'/' {
            return Some(end);
        }
    }
    None
}

unsafe fn overlay_resolve_sys_links(
    path: *const u8,
    buf: *mut u8,
    resolvelinks: *mut c_int,
    tmpbuf: &mut [u8; PATH_MAX],
    tmpbuf2: &mut [u8; PATH_MAX],
) -> Option<usize> {
    let mut len = unsafe { fixed_copy_cstr(tmpbuf, path)? };
    let mut scan = 1usize;

    while let Some(slash) = fixed_next_slash(tmpbuf, scan, len) {
        unsafe {
            fixed_set(tmpbuf, slash, 0);
        }
        let mut is_symlink = 0;
        let rc =
            unsafe { mcexec_overlay_lstat_is_symlink_bridge(tmpbuf.as_ptr(), &mut is_symlink) };

        if rc < 0 {
            unsafe {
                fixed_set(tmpbuf, slash, b'/');
            }
            break;
        }

        if is_symlink == 0 {
            unsafe {
                fixed_set(tmpbuf, slash, b'/');
            }
            scan = slash + 2;
            continue;
        }

        let link_len = unsafe { mcexec_overlay_readlink_bridge(tmpbuf.as_ptr(), buf, PATH_MAX) };
        if link_len < 0 || link_len as usize >= PATH_MAX {
            return None;
        }
        let target_len = link_len as usize;
        unsafe {
            *buf.add(target_len) = 0;
        }

        let suffix_start = slash + 1;
        let suffix_len = len - suffix_start;
        if unsafe { *buf } == b'/' {
            let total = target_len + 1 + suffix_len;
            if total >= PATH_MAX {
                return None;
            }

            unsafe {
                copy_ptr_bytes(tmpbuf2.as_mut_ptr(), buf as *const u8, target_len);
            }
            unsafe {
                fixed_set(tmpbuf2, target_len, b'/');
            }
            let mut idx = 0usize;
            while idx < suffix_len {
                let value = unsafe { fixed_get(tmpbuf, suffix_start + idx) };
                unsafe {
                    fixed_set(tmpbuf2, target_len + 1 + idx, value);
                }
                idx += 1;
            }
            unsafe {
                fixed_set(tmpbuf2, total, 0);
            }

            let mut copy = 0usize;
            while copy <= total {
                let value = unsafe { fixed_get(tmpbuf2, copy) };
                unsafe {
                    fixed_set(tmpbuf, copy, value);
                }
                copy += 1;
            }
            len = total;
            scan = 2;
        } else {
            if suffix_len >= PATH_MAX {
                return None;
            }
            let mut idx = 0usize;
            while idx < suffix_len {
                let value = unsafe { fixed_get(tmpbuf, suffix_start + idx) };
                unsafe {
                    fixed_set(tmpbuf2, idx, value);
                }
                idx += 1;
            }
            unsafe {
                fixed_set(tmpbuf2, suffix_len, 0);
            }

            let mut append_pos = match fixed_prev_slash(tmpbuf, slash) {
                Some(0) => {
                    unsafe {
                        fixed_set(tmpbuf, 1, 0);
                    }
                    0
                }
                Some(pos) => {
                    unsafe {
                        fixed_set(tmpbuf, pos, 0);
                    }
                    pos
                }
                None => return None,
            };

            let mut target_start = 0usize;
            while target_start + 3 <= target_len
                && unsafe { *buf.add(target_start) } == b'.'
                && unsafe { *buf.add(target_start + 1) } == b'.'
                && unsafe { *buf.add(target_start + 2) } == b'/'
            {
                if append_pos != 0 {
                    let prev = fixed_prev_slash(tmpbuf, append_pos)?;
                    if prev == 0 {
                        unsafe {
                            fixed_set(tmpbuf, 1, 0);
                        }
                        append_pos = 0;
                    } else {
                        unsafe {
                            fixed_set(tmpbuf, prev, 0);
                        }
                        append_pos = prev;
                    }
                } else {
                    unsafe {
                        fixed_set(tmpbuf, 1, 0);
                    }
                }
                target_start += 3;
            }

            let target_rem_len = target_len - target_start;
            let total = append_pos + 1 + target_rem_len + 1 + suffix_len;
            if total >= PATH_MAX {
                return None;
            }

            let mut pos = append_pos;
            unsafe {
                fixed_set(tmpbuf, pos, b'/');
            }
            pos += 1;
            let mut copy = 0usize;
            while copy < target_rem_len {
                unsafe {
                    fixed_set(tmpbuf, pos + copy, *buf.add(target_start + copy));
                }
                copy += 1;
            }
            pos += target_rem_len;
            unsafe {
                fixed_set(tmpbuf, pos, b'/');
            }
            pos += 1;
            copy = 0;
            while copy < suffix_len {
                let value = unsafe { fixed_get(tmpbuf2, copy) };
                unsafe {
                    fixed_set(tmpbuf, pos + copy, value);
                }
                copy += 1;
            }
            pos += suffix_len;
            unsafe {
                fixed_set(tmpbuf, pos, 0);
            }
            len = pos;
            scan = append_pos + 2;
        }

        if !resolvelinks.is_null() {
            unsafe {
                *resolvelinks = 1;
            }
        }
    }

    Some(len)
}

unsafe fn overlay_checkexist(
    input: *const u8,
    buf: *mut u8,
    n: isize,
    logical_path: *const u8,
) -> *const u8 {
    if n < 0 || n as usize >= PATH_MAX {
        unsafe { mcexec_overlay_truncated_bridge(buf as *const u8) };
        return input;
    }

    let mut normalized_len = n as usize;
    if unsafe { mcexec_normalize_overlay_path_result(buf, &mut normalized_len) } < 0 {
        return input;
    }

    let stat_error = unsafe { mcexec_overlay_stat_errno_bridge(buf as *const u8) };
    unsafe { mcexec_overlay_trying_bridge(buf as *const u8, stat_error) };
    if stat_error == ENOENT {
        if unsafe { mcexec_is_proc_task_leaf_path_result(logical_path) } != 0
            && unsafe { mcexec_mapped_proc_task_parent_exists_body(buf as *const u8) } != 0
        {
            return buf as *const u8;
        }
        if unsafe { overlay_blacklist(logical_path) } != 0 {
            unsafe { mcexec_overlay_blacklisted_bridge(logical_path) };
            return NONEXISTING_PATH.as_ptr();
        }
        return input;
    }

    buf as *const u8
}

#[no_mangle]
pub unsafe extern "C" fn overlay_path(
    dirfd: c_int,
    input: *const u8,
    buf: *mut u8,
    resolvelinks: *mut c_int,
) -> *const u8 {
    if input.is_null() || buf.is_null() {
        return input;
    }

    if !resolvelinks.is_null() {
        unsafe {
            *resolvelinks = 0;
        }
    }

    unsafe { mcexec_overlay_considering_bridge(dirfd, input) };

    let mut tmpbuf = [0u8; PATH_MAX];
    let mut tmpbuf2 = [0u8; PATH_MAX];
    let mut path = input;

    if dirfd != AT_FDCWD && unsafe { *input } != b'/' {
        let rc = unsafe { mcexec_proc_self_fd_path_result(buf, PATH_MAX, dirfd) };
        if rc < 0 {
            unsafe { mcexec_overlay_fd_path_truncated_bridge(dirfd) };
            return input;
        }

        let link_len = unsafe {
            mcexec_overlay_readlink_bridge(buf as *const u8, tmpbuf.as_mut_ptr(), PATH_MAX)
        };
        if link_len < 0 || link_len as usize == PATH_MAX {
            let error = if link_len as usize == PATH_MAX {
                ENAMETOOLONG
            } else {
                unsafe { *__errno_location() }
            };
            unsafe { mcexec_overlay_readlink_fd_failed_bridge(dirfd, error) };
            return input;
        }
        unsafe {
            fixed_set(&mut tmpbuf, link_len as usize, 0);
        }

        let joined =
            unsafe { mcexec_join_path_inplace_result(tmpbuf.as_mut_ptr(), PATH_MAX, input) };
        if joined < 0 {
            unsafe { mcexec_overlay_truncated_bridge(tmpbuf.as_ptr()) };
            return input;
        }
        path = tmpbuf.as_ptr();
    } else if unsafe { *input } != b'/' {
        if unsafe { getcwd(tmpbuf.as_mut_ptr(), PATH_MAX) }.is_null() {
            unsafe { mcexec_overlay_getcwd_failed_bridge(*__errno_location()) };
            return input;
        }

        let joined =
            unsafe { mcexec_join_path_inplace_result(tmpbuf.as_mut_ptr(), PATH_MAX, input) };
        if joined < 0 {
            unsafe { mcexec_overlay_truncated_bridge(tmpbuf.as_ptr()) };
            return input;
        }
        path = tmpbuf.as_ptr();
    }

    unsafe { mcexec_overlay_glued_bridge(path) };

    if unsafe { mcexec_path_is_dev_xpmem_result(path) } != 0 {
        return DEV_NULL_PATH.as_ptr();
    }

    if unsafe { mcexec_overlay_enable_uti_bridge() } != 0
        && unsafe { mcexec_path_has_libuti_result(path) } != 0
    {
        let mut libdir = [0u8; PATH_MAX];
        if unsafe { mcexec_overlay_find_libdir_bridge(libdir.as_mut_ptr(), libdir.len()) } < 0 {
            unsafe { mcexec_overlay_find_libdir_failed_bridge() };
            return input;
        }
        let mapped =
            unsafe { mcexec_overlay_uti_path_result(libdir.as_ptr(), path, buf, PATH_MAX) };
        if mapped < 0 {
            unsafe { mcexec_overlay_truncated_bridge(path) };
            return input;
        }
        unsafe { mcexec_overlay_replaced_bridge(path, buf as *const u8) };
        return unsafe { overlay_checkexist(input, buf, mapped as isize, path) };
    }

    let mcosid = unsafe { mcexec_overlay_mcosid_bridge() };
    let mut mapped =
        unsafe { mcexec_overlay_proc_self_path_result(path, mcosid, getpid(), buf, PATH_MAX) };
    if mapped > 0 {
        return unsafe { overlay_checkexist(input, buf, mapped as isize, path) };
    }
    if mapped < 0 {
        unsafe { mcexec_overlay_truncated_bridge(path) };
        return input;
    }

    mapped = unsafe { mcexec_overlay_proc_path_result(path, mcosid, buf, PATH_MAX) };
    if mapped > 0 {
        return unsafe { overlay_checkexist(input, buf, mapped as isize, path) };
    }
    if mapped < 0 {
        unsafe { mcexec_overlay_truncated_bridge(path) };
        return input;
    }

    if !is_sys_root_path(path) {
        return input;
    }

    if unsafe { overlay_resolve_sys_links(path, buf, resolvelinks, &mut tmpbuf, &mut tmpbuf2) }
        .is_none()
    {
        return input;
    }

    let mut mapped_offset = 0usize;
    mapped = unsafe {
        mcexec_overlay_sys_path_result(tmpbuf.as_ptr(), mcosid, buf, PATH_MAX, &mut mapped_offset)
    };
    if mapped <= 0 {
        return input;
    }

    let logical_path = unsafe { buf.add(mapped_offset) as *const u8 };
    unsafe { overlay_checkexist(input, buf, mapped as isize, logical_path) }
}

unsafe fn read_u16(ptr: *const u8, offset: usize) -> u16 {
    unsafe { *((ptr.add(offset)) as *const u16) }
}

unsafe fn add_mut(ptr: *mut u8, offset: usize) -> *mut u8 {
    unsafe { ptr.add(offset) }
}

fn dirent_reclen_offset(is64: i32) -> usize {
    if is64 != 0 {
        DIRENT64_RECLEN_OFFSET
    } else {
        DIRENT32_RECLEN_OFFSET
    }
}

fn dirent_name_offset(is64: i32) -> usize {
    if is64 != 0 {
        DIRENT64_NAME_OFFSET
    } else {
        DIRENT32_NAME_OFFSET
    }
}

fn dirent_off_offset(is64: i32) -> usize {
    if is64 != 0 {
        DIRENT64_OFF_OFFSET
    } else {
        DIRENT32_OFF_OFFSET
    }
}

unsafe fn dirent_reclen_kind(dirp: *const u8, is64: i32) -> usize {
    if dirp.is_null() {
        return 0;
    }
    unsafe { read_u16(dirp, dirent_reclen_offset(is64)) as usize }
}

unsafe fn dirent_name_kind(dirp: *const u8, is64: i32) -> *const u8 {
    if dirp.is_null() {
        return core::ptr::null();
    }
    unsafe { dirp.add(dirent_name_offset(is64)) }
}

unsafe fn dirent_names_equal(lhs: *const u8, rhs: *const u8) -> bool {
    if lhs.is_null() || rhs.is_null() {
        return false;
    }
    let mut idx = 0usize;
    loop {
        let l = unsafe { *lhs.add(idx) };
        let r = unsafe { *rhs.add(idx) };
        if l != r {
            return false;
        }
        if l == 0 {
            return true;
        }
        idx += 1;
    }
}

unsafe fn dirent_write_off_kind(dirp: *mut u8, is64: i32, value: usize) {
    unsafe {
        *((dirp.add(dirent_off_offset(is64))) as *mut usize) = value;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent32_reclen_result(dirp: *const u8) -> u16 {
    if dirp.is_null() {
        return 0;
    }
    unsafe { read_u16(dirp, DIRENT32_RECLEN_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent32_name_result(dirp: *mut u8) -> *mut u8 {
    if dirp.is_null() {
        return core::ptr::null_mut();
    }
    unsafe { add_mut(dirp, DIRENT32_NAME_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent32_off_result(dirp: *mut u8) -> *mut u8 {
    if dirp.is_null() {
        return core::ptr::null_mut();
    }
    unsafe { add_mut(dirp, DIRENT32_OFF_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent64_reclen_result(dirp: *const u8) -> u16 {
    if dirp.is_null() {
        return 0;
    }
    unsafe { read_u16(dirp, DIRENT64_RECLEN_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent64_name_result(dirp: *mut u8) -> *mut u8 {
    if dirp.is_null() {
        return core::ptr::null_mut();
    }
    unsafe { add_mut(dirp, DIRENT64_NAME_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent64_off_result(dirp: *mut u8) -> *mut u8 {
    if dirp.is_null() {
        return core::ptr::null_mut();
    }
    unsafe { add_mut(dirp, DIRENT64_OFF_OFFSET) }
}

#[no_mangle]
pub extern "C" fn mcexec_dirent_is64_body(sysnum: c_int, getdents64: c_int) -> c_int {
    (sysnum == getdents64) as c_int
}

#[no_mangle]
pub extern "C" fn mcexec_syscall_should_log_result(number: i64, arg0: u64, nr_write: i64) -> i32 {
    if number == nr_write && arg0 == 1 {
        0
    } else {
        1
    }
}

#[no_mangle]
pub extern "C" fn mcexec_errno_return_result(ret: i64, errno_value: i32) -> i64 {
    if ret == -1 {
        -(errno_value as i64)
    } else {
        ret
    }
}

#[no_mangle]
pub extern "C" fn mcexec_path_copy_return_result(copy_ret: i64, limit: u64) -> i64 {
    if copy_ret >= 0 && (copy_ret as u64) >= limit {
        -(ENAMETOOLONG as i64)
    } else {
        copy_ret
    }
}

#[no_mangle]
pub extern "C" fn mcexec_close_plan_result(remote_fd: u64, mcos_fd: i32) -> i64 {
    if remote_fd == mcos_fd as u64 {
        -(EBADF as i64)
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn mcexec_setfsuid_needs_cred_result(mode: u64) -> i32 {
    if mode == 1 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn mcexec_sched_setaffinity_action_result(pid_arg: u64) -> i64 {
    if pid_arg == 0 {
        1
    } else {
        -(EINVAL as i64)
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_exit_status_plan_result(
    number: i64,
    status: u64,
    nr_exit_group: i64,
    is_child: i32,
    is_tty: i32,
    sig_out: *mut i32,
    term_out: *mut i32,
    report_sig_out: *mut i32,
    report_status_out: *mut i32,
) {
    if sig_out.is_null()
        || term_out.is_null()
        || report_sig_out.is_null()
        || report_status_out.is_null()
    {
        return;
    }

    let mut sig = 0i32;
    let mut term = 0i32;
    let mut report_sig = 0i32;
    let mut report_status = 0i32;

    if number == nr_exit_group {
        sig = (status & 0x7f) as i32;
        term = ((status & 0xff00) >> 8) as i32;
        if is_tty != 0 {
            if sig != 0 {
                if is_child == 0 {
                    report_sig = 1;
                }
            } else if term != 0 {
                report_status = 1;
            }
        }
    }

    unsafe {
        *sig_out = sig;
        *term_out = term;
        *report_sig_out = report_sig;
        *report_status_out = report_status;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_collect_active_tids_result(
    head: *const McexecThreadData,
    tids: *mut i32,
    count: usize,
) -> i32 {
    if count == 0 {
        return 0;
    }
    if tids.is_null() {
        return -EINVAL;
    }

    let mut cursor = head;
    let mut idx = 0usize;
    while !cursor.is_null() && idx < count {
        let thread = unsafe { &*cursor };
        if thread.joined == 0 && thread.terminate == 0 {
            unsafe {
                *tids.add(idx) = thread.tid;
            }
            idx += 1;
        }
        cursor = thread.next;
    }

    while idx < count {
        unsafe {
            *tids.add(idx) = 0;
        }
        idx += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_fork_sync_complete_result(
    top: *mut *mut ForkSyncContainer,
    pid: i32,
    fs_out: *mut *mut ForkSync,
    node_out: *mut *mut ForkSyncContainer,
) -> i32 {
    if top.is_null() || fs_out.is_null() || node_out.is_null() {
        return -EINVAL;
    }

    unsafe {
        *fs_out = core::ptr::null_mut();
        *node_out = core::ptr::null_mut();
    }

    let mut prev: *mut ForkSyncContainer = core::ptr::null_mut();
    let mut current = unsafe { *top };
    while !current.is_null() {
        let next = unsafe { (*current).next };
        if unsafe { (*current).pid } == pid {
            if prev.is_null() {
                unsafe {
                    *top = next;
                }
            } else {
                unsafe {
                    (*prev).next = next;
                }
            }

            let fs = unsafe { (*current).fs };
            if !fs.is_null() {
                unsafe {
                    (*fs).success = 1;
                }
            }
            unsafe {
                *fs_out = fs;
                *node_out = current;
            }
            return 1;
        }
        prev = current;
        current = next;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_fork_sync_remove_node_result(
    top: *mut *mut ForkSyncContainer,
    target: *mut ForkSyncContainer,
) -> i32 {
    if top.is_null() || target.is_null() {
        return 0;
    }

    let mut prev: *mut ForkSyncContainer = core::ptr::null_mut();
    let mut current = unsafe { *top };
    while !current.is_null() {
        let next = unsafe { (*current).next };
        if current == target {
            if prev.is_null() {
                unsafe {
                    *top = next;
                }
            } else {
                unsafe {
                    (*prev).next = next;
                }
            }
            return 1;
        }
        prev = current;
        current = next;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent_rewrite_offsets_result(
    dirents: *mut u8,
    start: usize,
    end: usize,
    base: usize,
    is64: i32,
) -> i32 {
    if dirents.is_null() || start > end {
        return -EINVAL;
    }

    let mut pos = start;
    while pos < end {
        let entry = unsafe { dirents.add(pos) };
        let reclen = unsafe { dirent_reclen_kind(entry, is64) };
        if reclen == 0 || pos.checked_add(reclen).map_or(true, |next| next > end) {
            return -EINVAL;
        }
        unsafe {
            dirent_write_off_kind(entry, is64, base + pos + reclen);
        }
        pos += reclen;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_copy_dirents_result(
    dst: *mut u8,
    dirents: *const u8,
    dirents_size: usize,
    offset: usize,
    count: *mut u32,
    is64: i32,
) -> i32 {
    if dst.is_null() || dirents.is_null() || count.is_null() {
        return -EINVAL;
    }
    if offset > dirents_size {
        unsafe {
            *count = 0;
        }
        return 0;
    }

    let requested = unsafe { *count as usize };
    let available = dirents_size - offset;
    let max_len = if available > requested {
        requested
    } else {
        available
    };

    let mut len = 0usize;
    while len < max_len {
        let entry = unsafe { dirents.add(offset + len) };
        let reclen = unsafe { dirent_reclen_kind(entry, is64) };
        if reclen == 0 {
            unsafe {
                *count = 0;
            }
            return len as i32;
        }
        let Some(next_len) = len.checked_add(reclen) else {
            unsafe {
                *count = 0;
            }
            return len as i32;
        };
        if next_len > max_len {
            unsafe {
                *count = 0;
            }
            return len as i32;
        }
        unsafe {
            core::ptr::copy_nonoverlapping(entry, dst.add(len), reclen);
        }
        len = next_len;
    }

    unsafe {
        *count = (requested - len) as u32;
    }
    len as i32
}

#[no_mangle]
pub unsafe extern "C" fn copy_dirents(
    dst: *mut c_void,
    dirents: *mut c_void,
    dirents_size: usize,
    offset: c_long,
    count: *mut u32,
    sysnum: c_int,
) -> i32 {
    let offset = if offset < 0 {
        usize::MAX
    } else {
        offset as usize
    };
    let is64 = mcexec_dirent_is64_body(sysnum, SYS_GETDENTS64 as c_int);
    unsafe {
        mcexec_copy_dirents_result(
            dst as *mut u8,
            dirents as *const u8,
            dirents_size,
            offset,
            count,
            is64,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent_buffer_contains_name_result(
    dirents: *const u8,
    dirents_size: usize,
    entry: *const u8,
    is64: i32,
) -> i32 {
    if dirents.is_null() || entry.is_null() {
        return 0;
    }

    let needle = unsafe { dirent_name_kind(entry, is64) };
    let mut pos = 0usize;
    while pos < dirents_size {
        let current = unsafe { dirents.add(pos) };
        let reclen = unsafe { dirent_reclen_kind(current, is64) };
        if reclen == 0
            || pos
                .checked_add(reclen)
                .map_or(true, |next| next > dirents_size)
        {
            return 0;
        }
        let name = unsafe { dirent_name_kind(current, is64) };
        if unsafe { dirent_names_equal(name, needle) } {
            return 1;
        }
        pos += reclen;
    }

    0
}

unsafe fn overlay_getdents_call(sysnum: c_int, fd: c_int, dirp: *mut u8, count: u32) -> c_long {
    unsafe { syscall(sysnum as c_long, fd, dirp as *mut c_void, count as c_ulong) }
}

unsafe fn overlay_getdents_child_path(
    out: &mut [u8; PATH_MAX],
    base: *const u8,
    pathlen: usize,
    name: *const u8,
) -> bool {
    if base.is_null() || name.is_null() || pathlen >= PATH_MAX {
        return false;
    }
    let name_len = unsafe { cstr_len(name) };
    let Some(total) = pathlen
        .checked_add(1)
        .and_then(|value| value.checked_add(name_len))
    else {
        return false;
    };
    if total >= PATH_MAX {
        return false;
    }

    unsafe {
        copy_ptr_bytes(out.as_mut_ptr(), base, pathlen);
        fixed_set(out, pathlen, b'/');
        copy_ptr_bytes(out.as_mut_ptr().add(pathlen + 1), name, name_len);
        fixed_set(out, total, 0);
    }
    true
}

unsafe fn overlay_getdents_filter_lower(
    ofd: *mut c_void,
    dirp: *mut u8,
    ret: c_int,
    is64: c_int,
) -> c_int {
    let linux_path = unsafe { mcexec_overlay_getdents_linux_path_bridge(ofd) };
    let pathlen = unsafe { mcexec_overlay_getdents_pathlen_bridge(ofd) };
    let mck_dirents = unsafe { mcexec_overlay_getdents_mck_dirents_bridge(ofd) };
    let mck_size = unsafe { mcexec_overlay_getdents_mck_size_bridge(ofd) };
    let mut check_path = [0u8; PATH_MAX];
    let mut edited = ret;
    let mut pos = 0usize;

    while pos < edited as usize {
        let entry = unsafe { dirp.add(pos) };
        let reclen = unsafe { dirent_reclen_kind(entry, is64) };
        if reclen == 0
            || pos
                .checked_add(reclen)
                .map_or(true, |next| next > edited as usize)
        {
            return -EINVAL;
        }

        let name = unsafe { dirent_name_kind(entry, is64) };
        if unsafe { overlay_getdents_child_path(&mut check_path, linux_path, pathlen, name) }
            && unsafe { overlay_blacklist(check_path.as_ptr()) } != 0
        {
            unsafe { mcexec_overlay_getdents_blacklisted_bridge(check_path.as_ptr()) };
            let tail = edited as usize - pos - reclen;
            unsafe {
                core::ptr::copy(entry.add(reclen), entry, tail);
            }
            edited -= reclen as c_int;
            continue;
        }

        if unsafe { mcexec_dirent_buffer_contains_name_result(mck_dirents, mck_size, entry, is64) }
            != 0
        {
            unsafe { mcexec_overlay_getdents_dupe_bridge(name) };
            let tail = edited as usize - pos - reclen;
            unsafe {
                core::ptr::copy(entry.add(reclen), entry, tail);
            }
            edited -= reclen as c_int;
            continue;
        }

        pos += reclen;
    }

    edited
}

#[no_mangle]
pub unsafe extern "C" fn overlay_getdents(
    sysnum: c_int,
    fd: c_int,
    out_dirp: *mut c_void,
    count: u32,
) -> c_int {
    let ofd = unsafe { mcexec_overlay_getdents_find_bridge(fd) };

    if ofd.is_null() || unsafe { mcexec_overlay_getdents_hide_orig_bridge(ofd) } != 0 {
        let raw = unsafe { overlay_getdents_call(sysnum, fd, out_dirp as *mut u8, count) };
        if raw == -1 {
            return -(unsafe { *__errno_location() });
        }
        return raw as c_int;
    }

    let dirp = unsafe { malloc(count as usize) };
    if dirp.is_null() {
        return -ENOMEM;
    }

    let mut ret: c_int;
    let mut mck_ret: c_int = 0;
    let mut linux_ret: c_int = 0;
    let is64 = mcexec_dirent_is64_body(sysnum, SYS_GETDENTS64 as c_int);
    let mut offset = unsafe { lseek(fd, 0, SEEK_CUR) };
    if offset == -1 {
        ret = -(unsafe { *__errno_location() });
        unsafe { free(dirp) };
        return ret;
    }
    unsafe { mcexec_overlay_getdents_offset_bridge(offset) };

    let mck_fd = unsafe { mcexec_overlay_getdents_mck_fd_bridge(ofd) };
    if mck_fd < 0 {
        unsafe { free(dirp) };
        return mck_fd;
    }

    loop {
        let raw = unsafe { overlay_getdents_call(sysnum, mck_fd, dirp, count) };
        if raw < 0 {
            ret = -(unsafe { *__errno_location() });
            unsafe { free(dirp) };
            return ret;
        }
        ret = raw as c_int;
        mck_ret += ret;
        unsafe { mcexec_overlay_getdents_upper_bridge(mck_ret, ret, count) };

        if ret > 0 {
            let rc = unsafe {
                mcexec_overlay_getdents_append_mck_bridge(
                    ofd,
                    dirp as *const u8,
                    ret as usize,
                    is64,
                )
            };
            if rc < 0 {
                unsafe { free(dirp) };
                return rc;
            }
        }

        if !(ret > 0 && (mck_ret as u32) < count) {
            break;
        }
    }

    let linux_fd = unsafe { mcexec_overlay_getdents_linux_fd_bridge(ofd) };
    if linux_fd < 0 {
        unsafe { free(dirp) };
        return linux_fd;
    }

    loop {
        let raw = unsafe { overlay_getdents_call(sysnum, linux_fd, dirp, count) };
        if raw < 0 {
            let error = unsafe { *__errno_location() };
            unsafe {
                mcexec_overlay_getdents_lower_failed_bridge(error);
                free(dirp);
            }
            return -error;
        }

        let ret_before_edit = raw as c_int;
        ret = unsafe { overlay_getdents_filter_lower(ofd, dirp, ret_before_edit, is64) };
        if ret < 0 {
            unsafe { free(dirp) };
            return ret;
        }
        linux_ret += ret;
        unsafe { mcexec_overlay_getdents_lower_bridge(linux_ret, ret, count) };

        if ret > 0 {
            let rc = unsafe {
                mcexec_overlay_getdents_append_linux_bridge(
                    ofd,
                    dirp as *const u8,
                    ret as usize,
                    is64,
                    ret,
                )
            };
            if rc < 0 {
                unsafe { free(dirp) };
                return rc;
            }
            if rc > 0 {
                unsafe { free(dirp) };
                return rc;
            }
        }

        if !(ret_before_edit > 0 && ((mck_ret + linux_ret) as u32) < count) {
            break;
        }
    }

    let mck_size = unsafe { mcexec_overlay_getdents_mck_size_bridge(ofd) };
    let linux_size = unsafe { mcexec_overlay_getdents_linux_size_bridge(ofd) };
    if offset < 0 || offset as usize > mck_size + linux_size {
        unsafe {
            mcexec_overlay_getdents_offset_too_large_bridge(offset, mck_size, linux_size);
            free(dirp);
        }
        return -EINVAL;
    }

    let mut remaining = count;
    let mut mck_len = 0i32;
    let mut linux_len = 0i32;
    if remaining > 0 && (offset as usize) < mck_size {
        mck_len = unsafe {
            copy_dirents(
                out_dirp,
                mcexec_overlay_getdents_mck_dirents_bridge(ofd) as *mut c_void,
                mck_size,
                offset,
                &mut remaining,
                sysnum,
            )
        };
        if mck_len < 0 {
            unsafe { free(dirp) };
            return mck_len;
        }
        if mck_len == 0 {
            unsafe {
                mcexec_overlay_getdents_upper_small_bridge();
                free(dirp);
            }
            return -EINVAL;
        }
        offset = 0;
    } else {
        offset -= mck_size as c_long;
    }
    unsafe { mcexec_overlay_getdents_mck_size_log_bridge(mck_size, offset, mck_len, remaining) };

    if remaining > 0 && (offset as usize) < linux_size {
        linux_len = unsafe {
            copy_dirents(
                (out_dirp as *mut u8).add(mck_len as usize) as *mut c_void,
                mcexec_overlay_getdents_linux_dirents_bridge(ofd) as *mut c_void,
                linux_size,
                offset,
                &mut remaining,
                sysnum,
            )
        };
        if linux_len < 0 {
            unsafe { free(dirp) };
            return linux_len;
        }
        if mck_len == 0 && linux_len == 0 {
            unsafe {
                mcexec_overlay_getdents_lower_small_bridge();
                free(dirp);
            }
            return -EINVAL;
        }
        unsafe {
            mcexec_overlay_getdents_linux_size_log_bridge(linux_size, offset, linux_len, remaining)
        };
    }

    ret = mck_len + linux_len;
    unsafe {
        lseek(fd, ret as c_long, SEEK_CUR);
        free(dirp);
    }
    ret
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
