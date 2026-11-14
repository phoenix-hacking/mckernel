/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
/* Declarative conflict-query ABI; stack token stays exclusively Rust-owned. */
struct process_vm;
struct vm_range;
/* Caller holds VM writer; NULL range requests any reservation for VM teardown. */
extern int f03_mmap_range_conflicts_write_v1(struct process_vm *, struct vm_range *);
