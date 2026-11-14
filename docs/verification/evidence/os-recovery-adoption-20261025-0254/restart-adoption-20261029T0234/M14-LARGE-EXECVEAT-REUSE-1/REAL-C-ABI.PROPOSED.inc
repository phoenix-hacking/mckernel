/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Declarative source proposal. The two request providers are NOT implemented. */
struct f03_execveat_origins {
    const char *file;
    int filename_argv_alloc_line, filename_argv_free_line;
    int filename_envp_alloc_line, filename_envp_free_line;
    unsigned long ranges_attr;
    int sigkill;
};
const struct f03_execveat_origins f03_execveat_origins_v1 = {
    __FILE__, 7623, 7628, 7640, 7645,
    PTATTR_NO_EXECUTE | PTATTR_WRITABLE | PTATTR_FOR_USER, SIGKILL
};
struct ddebug __attribute__((aligned(8), section("__verbose"))) f03_execveat_debug_v1[3] = {
    { .file=__FILE__, .func="do_execveat", .line=7600, .flags=DDEBUG_DEFAULT },
    { .file=__FILE__, .func="do_execveat", .line=7606, .flags=DDEBUG_DEFAULT },
    { .file=__FILE__, .func="do_execveat", .line=7727, .flags=DDEBUG_DEFAULT },
};
extern void f03_execveat_phase1_request_init_v1(struct syscall_request *, int,
        const char *, unsigned long, int);
extern void f03_execveat_phase2_request_init_v1(struct syscall_request *,
        unsigned long, unsigned long);
extern int f03_do_execveat_whole_v1(ihk_mc_user_context_t *, int,
        const char *, char **, char **, int);
const unsigned long f03_execveat_C_ABI_v1[32] = {
    sizeof(struct thread), _Alignof(struct thread),
    __builtin_offsetof(struct thread, vm), __builtin_offsetof(struct thread, proc),
    __builtin_offsetof(struct thread, tid),
    sizeof(struct process_vm), __builtin_offsetof(struct process_vm, region),
    __builtin_offsetof(struct vm_regions, user_start), __builtin_offsetof(struct vm_regions, user_end),
    __builtin_offsetof(struct process, pid), __builtin_offsetof(struct process, execed),
    sizeof(struct program_load_desc), _Alignof(struct program_load_desc),
    __builtin_offsetof(struct program_load_desc, num_sections),
    __builtin_offsetof(struct program_load_desc, entry),
    __builtin_offsetof(struct program_load_desc, args),
    __builtin_offsetof(struct program_load_desc, args_len),
    sizeof(struct program_image_section), sizeof(ihk_mc_user_context_t),
    sizeof(struct syscall_request), _Alignof(struct syscall_request),
    __builtin_offsetof(struct syscall_request, number), __builtin_offsetof(struct syscall_request, args),
    sizeof(struct f03_execveat_origins), _Alignof(struct f03_execveat_origins),
    __builtin_offsetof(struct f03_execveat_origins, file),
    __builtin_offsetof(struct f03_execveat_origins, filename_argv_alloc_line),
    __builtin_offsetof(struct f03_execveat_origins, filename_argv_free_line),
    __builtin_offsetof(struct f03_execveat_origins, filename_envp_alloc_line),
    __builtin_offsetof(struct f03_execveat_origins, filename_envp_free_line),
    __builtin_offsetof(struct f03_execveat_origins, ranges_attr),
    __builtin_offsetof(struct f03_execveat_origins, sigkill),
};
/* Pair with a guarded C fallback retaining the entire original body byte for byte. */
