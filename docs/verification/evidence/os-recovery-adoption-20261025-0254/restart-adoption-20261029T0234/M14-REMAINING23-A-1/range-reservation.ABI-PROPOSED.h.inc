/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Declarations only: no implementation, storage, ABI approval or selection. */
struct process_vm;
struct vm_range;
extern void *f03_mmap_range_reserve_write_v1(struct process_vm *, struct vm_range *);
extern int f03_mmap_xpmem_update_reserved_v1(struct process_vm *, struct vm_range *, void *);
extern void f03_mmap_range_release_v1(void *);
