Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private source only. The CPU batch and its single queued fixture are unchanged.
Added public ihk_reserve_mem, ihk_get_num_os_instances and ihk_get_os_instances.
No ABI fixture, compiler, workload, device ioctl or directory enumeration has executed.

Current C memory reservation overwrites req.sizes/req.numa_ids in balanced mode without freeing the first arrays, and resets one-shot configuration BEFORE checking balanced_enable to free query arrays. The private translation preserves this observable lifetime rather than silently fixing ownership during an equivalence port. These remain concrete qualification debt: no leak-free or accepted replacement claim. Balanced successful producer inputs must have nonzero node/compensation/release divisors, just as defined C executions require; malformed producer behavior remains unqualified. The original two-pass OS census can grow between count/list and exceed caller space; no concurrency guarantee or fix is invented. The original prefix test counts every mcos-prefixed name and passes its suffix to libc atoi, including nonnumeric suffixes, in readdir order.

Actual selected glibc target dirent header ABI and LP64 memory request/config layout need checks in the next already queued fixture family only after root grant; host header similarity is not target authority. WITH_KRM and Fugaku configuration successors are refused. Default memory reset is selected PAGE_SIZE4096/maxratio98/timeout30. Remaining mem query/release/config functions and global reserve_mem_conf are existing C dependencies, explicitly not retired.
