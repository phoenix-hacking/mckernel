#ifdef MCKERNEL_RUST_PROCESS_HELPERS
/* Existing allocator retains these borrowed static tracking identities. */
const char *const process_page_fault_anon_alloc_file = __FILE__;
const int process_page_fault_anon_alloc_line = 2982;
int process_page_fault_anon_allocate_body_result(struct process_vm *, struct vm_range *,
        uintptr_t, uint64_t, pte_t **, void **, size_t *, int *, void **, int *);
#endif

