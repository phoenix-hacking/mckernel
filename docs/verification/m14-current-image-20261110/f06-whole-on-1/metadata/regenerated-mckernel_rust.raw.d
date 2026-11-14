/work/output/build/kernel/rust/mckernel_rust.o: /src/kernel/rust/lib.rs /src/kernel/rust/abi.rs /src/kernel/rust/abort.rs /src/kernel/rust/affinity.rs /src/kernel/rust/ap.rs /src/kernel/rust/atomic_helpers.rs /src/kernel/rust/bitmap.rs /src/kernel/rust/bitops.rs /src/kernel/rust/builtin_dma.rs /src/kernel/rust/cls.rs /src/kernel/rust/cls_helpers.rs /src/kernel/rust/debug.rs /src/kernel/rust/devobj.rs /src/kernel/rust/fileobj.rs /src/kernel/rust/fork_control_guest.rs /src/kernel/rust/fork_child_credits.rs /src/kernel/rust/fork_constructed_credits.rs /src/kernel/rust/fork_final_ack.rs /src/kernel/rust/fork_runnable_child.rs /src/kernel/rust/fork_control_registry.rs /src/kernel/rust/freeze.rs /src/kernel/rust/futex.rs /src/kernel/rust/gencore.rs /src/kernel/rust/hash.rs /src/kernel/rust/host_helpers.rs /src/kernel/rust/hugefileobj.rs /src/kernel/rust/ikc_manycore.rs /src/kernel/rust/ikc_master.rs /src/kernel/rust/ikc_queue.rs /src/kernel/rust/init.rs /src/kernel/rust/list_helpers.rs /src/kernel/rust/listeners.rs /src/kernel/rust/llist.rs /src/kernel/rust/lock_helpers.rs /src/kernel/rust/mem_helpers.rs /src/kernel/rust/mikc.rs /src/kernel/rust/numparse.rs /src/kernel/rust/object_helpers.rs /src/kernel/rust/page_alloc.rs /src/kernel/rust/page_helpers.rs /src/kernel/rust/pager.rs /src/kernel/rust/plist.rs /src/kernel/rust/process_helpers.rs /src/kernel/rust/process_verbose_data.rs /src/kernel/rust/procfs.rs /src/kernel/rust/profile.rs /src/kernel/rust/pte_helpers.rs /src/kernel/rust/rbtree.rs /src/kernel/rust/refcount_helpers.rs /src/kernel/rust/rlimit_helpers.rs /src/kernel/rust/sched_helpers.rs /src/kernel/rust/shmid_helpers.rs /src/kernel/rust/f06_shmget_dispatch.rs /src/kernel/rust/shmobj.rs /src/kernel/rust/smp_ikc.rs /src/kernel/rust/spinlock_helpers.rs /src/kernel/rust/string.rs /src/kernel/rust/syscall_policy.rs /src/kernel/rust/f06_signal_tail.rs /src/kernel/rust/f06_mmap_flags.rs /src/kernel/rust/f06_prctl_set_register.rs /src/kernel/rust/f06_prctl_get_register.rs /src/kernel/rust/f06_mmap_dispatch_bridge.rs /src/kernel/rust/f06_ptrace_context.rs /src/kernel/rust/f06_ptrace_alloc.rs /src/kernel/rust/f06_vdso_add_range.rs /src/kernel/rust/f06_vdso_set_range.rs /src/kernel/rust/f06_process_vm_entry.rs /src/kernel/rust/arch_copy_to_user_bridge.rs /src/kernel/rust/arch_copy_from_user_bridge.rs /src/kernel/rust/arch_syscall_forward_context_bridge.rs /src/kernel/rust/arch_rt_sigreturn_syscall_bridge.rs /src/kernel/rust/arch_rt_sigreturn_set_signal_bridge.rs /src/kernel/rust/arch_rt_sigreturn_check_signal_bridge.rs /src/kernel/rust/f06_rt_sigreturn_alloc_free.rs /src/kernel/rust/f06_clone_reader_lock.rs /src/kernel/rust/f06_clone_reader_unlock.rs /src/kernel/rust/f06_ptrace_find_thread.rs /src/kernel/rust/f06_ptrace_thread_unlock.rs /src/kernel/rust/f06_clone_ptrace_provider_abi.rs /src/kernel/rust/f06_obtain_clone_cpuid.rs /src/kernel/rust/f06_vdso_info.rs /src/kernel/rust/syscall_offload_entry.rs /src/kernel/rust/f06_rt_sigreturn_xrstor.rs /src/kernel/rust/f03_host_cleanup.rs /src/kernel/rust/f03_credential_refresh.rs /src/kernel/rust/f03_interrupt_syscall.rs /src/kernel/rust/f06_signal_ptrace_diagnostics.rs /src/kernel/rust/f06_signal_trap_info.rs /src/kernel/rust/native_signal.rs /src/kernel/rust/native_fault.rs /src/kernel/rust/native_futex.rs /src/kernel/rust/native_xstate.rs /src/kernel/rust/sysfs.rs /src/kernel/rust/timer.rs /src/kernel/rust/tofu_uapi.rs /src/kernel/rust/ubsan.rs /src/kernel/rust/waitq.rs /src/kernel/rust/x86_coredump.rs /src/kernel/rust/x86_cpu_helpers.rs /src/kernel/rust/x86_cpu_log_providers.rs /src/kernel/rust/x86_local.rs /src/kernel/rust/x86_memory_helpers.rs /src/kernel/rust/x86_memory_loggers.rs /src/kernel/rust/x86_memory_logger_bridges.rs /src/kernel/rust/x86_perfctr.rs /src/kernel/rust/x86_setup.rs /src/kernel/rust/x86_vsyscall.rs /src/kernel/rust/../../host-kernel/native-rust/abi/vdso.rs /src/kernel/rust/native_vdso.rs /src/kernel/rust/../../host-kernel/native-rust/zero_pages.rs /src/kernel/rust/clone3.rs /src/kernel/rust/xpmem_helpers.rs /src/kernel/rust/zeroobj.rs /src/kernel/rust/f03_perf_attr_callbacks.rs /src/kernel/rust/f03_prlimit.rs /src/kernel/rust/f06_native_signal_restore_fp.rs /src/kernel/rust/f06_ptrace_xstate_copy_to.rs /src/kernel/rust/f06_ptrace_xstate_copy_from.rs /src/kernel/rust/f06_vdso_setup_log.rs /src/kernel/rust/f06_vdso_state.rs /src/kernel/rust/f06_vdso_storage.rs /src/kernel/rust/f06_ptrace_user_bridges.rs /src/kernel/rust/f06_ptrace_gpregs_bridges.rs /src/kernel/rust/f06_prctl_log.rs /src/kernel/rust/f06_prctl_log_storage.rs /src/kernel/rust/f06_vdso_map_log.rs /work/output/build/kernel/rust/f06-origin/f06_signal_metadata.rs /work/output/build/kernel/rust/f06-origin/f06_clone_cpuid_metadata.rs /src/kernel/rust/f03_perf_event_attr_abi.rs /home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-gnu/lib/libcore-5202d9b43b836218.rmeta /home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-gnu/lib/libcompiler_builtins-bbfdd99d24659dd7.rmeta

/src/kernel/rust/lib.rs:
/src/kernel/rust/abi.rs:
/src/kernel/rust/abort.rs:
/src/kernel/rust/affinity.rs:
/src/kernel/rust/ap.rs:
/src/kernel/rust/atomic_helpers.rs:
/src/kernel/rust/bitmap.rs:
/src/kernel/rust/bitops.rs:
/src/kernel/rust/builtin_dma.rs:
/src/kernel/rust/cls.rs:
/src/kernel/rust/cls_helpers.rs:
/src/kernel/rust/debug.rs:
/src/kernel/rust/devobj.rs:
/src/kernel/rust/fileobj.rs:
/src/kernel/rust/fork_control_guest.rs:
/src/kernel/rust/fork_child_credits.rs:
/src/kernel/rust/fork_constructed_credits.rs:
/src/kernel/rust/fork_final_ack.rs:
/src/kernel/rust/fork_runnable_child.rs:
/src/kernel/rust/fork_control_registry.rs:
/src/kernel/rust/freeze.rs:
/src/kernel/rust/futex.rs:
/src/kernel/rust/gencore.rs:
/src/kernel/rust/hash.rs:
/src/kernel/rust/host_helpers.rs:
/src/kernel/rust/hugefileobj.rs:
/src/kernel/rust/ikc_manycore.rs:
/src/kernel/rust/ikc_master.rs:
/src/kernel/rust/ikc_queue.rs:
/src/kernel/rust/init.rs:
/src/kernel/rust/list_helpers.rs:
/src/kernel/rust/listeners.rs:
/src/kernel/rust/llist.rs:
/src/kernel/rust/lock_helpers.rs:
/src/kernel/rust/mem_helpers.rs:
/src/kernel/rust/mikc.rs:
/src/kernel/rust/numparse.rs:
/src/kernel/rust/object_helpers.rs:
/src/kernel/rust/page_alloc.rs:
/src/kernel/rust/page_helpers.rs:
/src/kernel/rust/pager.rs:
/src/kernel/rust/plist.rs:
/src/kernel/rust/process_helpers.rs:
/src/kernel/rust/process_verbose_data.rs:
/src/kernel/rust/procfs.rs:
/src/kernel/rust/profile.rs:
/src/kernel/rust/pte_helpers.rs:
/src/kernel/rust/rbtree.rs:
/src/kernel/rust/refcount_helpers.rs:
/src/kernel/rust/rlimit_helpers.rs:
/src/kernel/rust/sched_helpers.rs:
/src/kernel/rust/shmid_helpers.rs:
/src/kernel/rust/f06_shmget_dispatch.rs:
/src/kernel/rust/shmobj.rs:
/src/kernel/rust/smp_ikc.rs:
/src/kernel/rust/spinlock_helpers.rs:
/src/kernel/rust/string.rs:
/src/kernel/rust/syscall_policy.rs:
/src/kernel/rust/f06_signal_tail.rs:
/src/kernel/rust/f06_mmap_flags.rs:
/src/kernel/rust/f06_prctl_set_register.rs:
/src/kernel/rust/f06_prctl_get_register.rs:
/src/kernel/rust/f06_mmap_dispatch_bridge.rs:
/src/kernel/rust/f06_ptrace_context.rs:
/src/kernel/rust/f06_ptrace_alloc.rs:
/src/kernel/rust/f06_vdso_add_range.rs:
/src/kernel/rust/f06_vdso_set_range.rs:
/src/kernel/rust/f06_process_vm_entry.rs:
/src/kernel/rust/arch_copy_to_user_bridge.rs:
/src/kernel/rust/arch_copy_from_user_bridge.rs:
/src/kernel/rust/arch_syscall_forward_context_bridge.rs:
/src/kernel/rust/arch_rt_sigreturn_syscall_bridge.rs:
/src/kernel/rust/arch_rt_sigreturn_set_signal_bridge.rs:
/src/kernel/rust/arch_rt_sigreturn_check_signal_bridge.rs:
/src/kernel/rust/f06_rt_sigreturn_alloc_free.rs:
/src/kernel/rust/f06_clone_reader_lock.rs:
/src/kernel/rust/f06_clone_reader_unlock.rs:
/src/kernel/rust/f06_ptrace_find_thread.rs:
/src/kernel/rust/f06_ptrace_thread_unlock.rs:
/src/kernel/rust/f06_clone_ptrace_provider_abi.rs:
/src/kernel/rust/f06_obtain_clone_cpuid.rs:
/src/kernel/rust/f06_vdso_info.rs:
/src/kernel/rust/syscall_offload_entry.rs:
/src/kernel/rust/f06_rt_sigreturn_xrstor.rs:
/src/kernel/rust/f03_host_cleanup.rs:
/src/kernel/rust/f03_credential_refresh.rs:
/src/kernel/rust/f03_interrupt_syscall.rs:
/src/kernel/rust/f06_signal_ptrace_diagnostics.rs:
/src/kernel/rust/f06_signal_trap_info.rs:
/src/kernel/rust/native_signal.rs:
/src/kernel/rust/native_fault.rs:
/src/kernel/rust/native_futex.rs:
/src/kernel/rust/native_xstate.rs:
/src/kernel/rust/sysfs.rs:
/src/kernel/rust/timer.rs:
/src/kernel/rust/tofu_uapi.rs:
/src/kernel/rust/ubsan.rs:
/src/kernel/rust/waitq.rs:
/src/kernel/rust/x86_coredump.rs:
/src/kernel/rust/x86_cpu_helpers.rs:
/src/kernel/rust/x86_cpu_log_providers.rs:
/src/kernel/rust/x86_local.rs:
/src/kernel/rust/x86_memory_helpers.rs:
/src/kernel/rust/x86_memory_loggers.rs:
/src/kernel/rust/x86_memory_logger_bridges.rs:
/src/kernel/rust/x86_perfctr.rs:
/src/kernel/rust/x86_setup.rs:
/src/kernel/rust/x86_vsyscall.rs:
/src/kernel/rust/../../host-kernel/native-rust/abi/vdso.rs:
/src/kernel/rust/native_vdso.rs:
/src/kernel/rust/../../host-kernel/native-rust/zero_pages.rs:
/src/kernel/rust/clone3.rs:
/src/kernel/rust/xpmem_helpers.rs:
/src/kernel/rust/zeroobj.rs:
/src/kernel/rust/f03_perf_attr_callbacks.rs:
/src/kernel/rust/f03_prlimit.rs:
/src/kernel/rust/f06_native_signal_restore_fp.rs:
/src/kernel/rust/f06_ptrace_xstate_copy_to.rs:
/src/kernel/rust/f06_ptrace_xstate_copy_from.rs:
/src/kernel/rust/f06_vdso_setup_log.rs:
/src/kernel/rust/f06_vdso_state.rs:
/src/kernel/rust/f06_vdso_storage.rs:
/src/kernel/rust/f06_ptrace_user_bridges.rs:
/src/kernel/rust/f06_ptrace_gpregs_bridges.rs:
/src/kernel/rust/f06_prctl_log.rs:
/src/kernel/rust/f06_prctl_log_storage.rs:
/src/kernel/rust/f06_vdso_map_log.rs:
/work/output/build/kernel/rust/f06-origin/f06_signal_metadata.rs:
/work/output/build/kernel/rust/f06-origin/f06_clone_cpuid_metadata.rs:
/src/kernel/rust/f03_perf_event_attr_abi.rs:
/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-gnu/lib/libcore-5202d9b43b836218.rmeta:
/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/lib/rustlib/x86_64-unknown-linux-gnu/lib/libcompiler_builtins-bbfdd99d24659dd7.rmeta:

# env-dep:MCKERNEL_CPU_C_FILE=/src/arch/x86_64/kernel/cpu.c
# env-dep:MCKERNEL_DO_SYSCALL_C_FILE=/src/kernel/syscall.c
# env-dep:MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS=0
# env-dep:MCKERNEL_F06_CLONE_CPUID_METADATA_RS=/work/output/build/kernel/rust/f06-origin/f06_clone_cpuid_metadata.rs
# env-dep:MCKERNEL_F06_RT_SIGRETURN_ORIGIN=/src/arch/x86_64/kernel/syscall.c
# env-dep:MCKERNEL_F06_SIGNAL_METADATA_RS=/work/output/build/kernel/rust/f06-origin/f06_signal_metadata.rs
# env-dep:MCKERNEL_INTERRUPT_SYSCALL_C_FILE=/src/kernel/syscall.c
# env-dep:MCKERNEL_PROCESS_C_FILE=/src/kernel/process.c
# env-dep:MCKERNEL_PROCESS_DDEBUG_FLAGS=0
# env-dep:MCKERNEL_RUST_BUILDID=8d288b8
# env-dep:MCKERNEL_RUST_VERSION=1.8.0
# env-dep:MCKERNEL_X86_ENABLE_SSE=1
