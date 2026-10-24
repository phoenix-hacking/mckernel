#ifdef MCKERNEL_RUST_PROCESS_HELPERS
/* Original page-fault bounds diagnostic: static ABI data, Rust computation. */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_page_fault_prepare_bounds_debug = {
    .file = __FILE__, .func = "page_fault_process_memory_range",
    .line = 2835, .flags = DDEBUG_DEFAULT,
};
int process_page_fault_prepare_body_result(struct process_vm *, struct vm_range *,
        uintptr_t, uint64_t, pte_t **, void **, size_t *, int *, int *);
#endif

