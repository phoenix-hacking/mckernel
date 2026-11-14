set(CMAKE_SHARED_LIBRARY_LINK_C_FLAGS)
set(CMAKE_C_LINKER_WRAPPER_FLAG "")
set(CMAKE_C_LINKER_WRAPPER_FLAG_SEP "")
set(CMAKE_C_LINK_EXECUTABLE "<CMAKE_LINKER> <LINK_FLAGS> <OBJECTS> -o <TARGET> <LINK_LIBRARIES>")
set(CMAKE_ASM_FLAGS "${CMAKE_ASM_FLAGS} -D__ASSEMBLY__")

configure_file(include/swapfmt.h.in include/swapfmt.h)

execute_process(COMMAND ${CMAKE_C_COMPILER} -print-file-name=include
	OUTPUT_VARIABLE SYSTEM_INCLUDE OUTPUT_STRIP_TRAILING_WHITESPACE)
add_definitions(-D__KERNEL__ -DIHK_OS_MANYCORE
	-DMAP_KERNEL_START=${MAP_KERNEL_START}UL -DKERNEL_RAM_VADDR=${MAP_KERNEL_START})
add_compile_options(-ffreestanding -O2 -nostdinc -isystem ${SYSTEM_INCLUDE} -fno-omit-frame-pointer)
include_directories(
	"${CMAKE_CURRENT_BINARY_DIR}/include"
	"include"
	"${CMAKE_CURRENT_BINARY_DIR}"
	"${PROJECT_BINARY_DIR}"
	"${IHK_FULL_SOURCE_DIR}/cokernel/smp/${ARCH}/include"
	"${IHK_FULL_SOURCE_DIR}/cokernel/smp/${ARCH}/"
	"${IHK_FULL_SOURCE_DIR}/ikc/include"
	"${IHK_FULL_SOURCE_DIR}/linux/include"
	"${PROJECT_SOURCE_DIR}/lib/include"
	"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/include"
)
if (${ARCH} STREQUAL "x86_64")
	add_compile_options(-mcmodel=large -mno-red-zone -mno-sse)
endif()

if (${ARCH} STREQUAL "arm64")
	add_compile_options(-mgeneral-regs-only)
endif()

option(ENABLE_RUST_KERNEL "Enable Rust code in the McKernel image" ON)
# Private nonheld 13-function plus data32 candidate; no default change.
option(MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL "Select the nonheld M14 13-function and data candidate" OFF)
# Functional OS migration: paired typed Rust storage for 32 public debug objects.
# Internal descriptors and their three configs use a separate atomic selector.
option(ENABLE_RUST_PROCESS_VERBOSE_DATA "Use typed Rust process debug globals" ON)
option(ENABLE_RUST_PROCESS_VERBOSE_LOCAL_COMPANIONS "Use joint Rust local debug/config storage" ON)
set(MCKERNEL_PROCESS_VERBOSE_LOCAL_SELECTED OFF)
option(ENABLE_PROCESS_DEBUG_PRINT "Initialize process dynamic debug as enabled" OFF)
set(MCKERNEL_PROCESS_DDEBUG_FLAGS 0)
if (ENABLE_PROCESS_DEBUG_PRINT)
    set(MCKERNEL_PROCESS_DDEBUG_FLAGS 1)
endif()
set(MCKERNEL_PROCESS_C_FILE "${CMAKE_CURRENT_SOURCE_DIR}/process.c")
# Restrict unsupported C literal spellings; C also asserts the actual __FILE__.
if (NOT MCKERNEL_PROCESS_C_FILE MATCHES "^/[A-Za-z0-9_./+-]+$")
    message(FATAL_ERROR "Unsupported process.c path for exact C/Rust debug identity")
endif()
option(ENABLE_NATIVE_SYSFS_VERIFY "Enable guest sysfs verification with a Linux test controller" OFF)
option(ENABLE_NATIVE_FORK_OWNED_TRANSACTION "Enable the existing native owned-fork transaction" OFF)
set(MCKERNEL_HOST_IRQ_ABI "legacy" CACHE STRING "Linux control-kernel IRQ-work ABI")
set_property(CACHE MCKERNEL_HOST_IRQ_ABI PROPERTY STRINGS legacy linux-6.12)
if (NOT MCKERNEL_HOST_IRQ_ABI STREQUAL "legacy" AND
    NOT MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12")
	message(FATAL_ERROR "MCKERNEL_HOST_IRQ_ABI must be legacy or linux-6.12")
endif()
if (MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12" AND
    (NOT ENABLE_RUST_KERNEL OR NOT "${ARCH}" STREQUAL "x86_64"))
	message(FATAL_ERROR "linux-6.12 IRQ ABI requires the x86_64 Rust kernel")
endif()
if (ENABLE_NATIVE_SYSFS_VERIFY AND
    (NOT ENABLE_RUST_KERNEL OR NOT "${ARCH}" STREQUAL "x86_64" OR
     NOT MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12"))
	message(FATAL_ERROR "Native sysfs verification requires the x86_64 Rust kernel and linux-6.12 IRQ ABI")
endif()
if (ENABLE_NATIVE_FORK_OWNED_TRANSACTION AND
    (NOT ENABLE_RUST_KERNEL OR NOT "${ARCH}" STREQUAL "x86_64" OR
     NOT MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12"))
	message(FATAL_ERROR "Native owned-fork transaction requires the x86_64 Rust kernel and linux-6.12 IRQ ABI")
endif()
if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL AND
    (NOT ENABLE_RUST_KERNEL OR NOT "${ARCH}" STREQUAL "x86_64" OR
     NOT BUILD_TARGET STREQUAL "smp-x86" OR ENABLE_UBSAN OR
     NOT MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12" OR NOT ENABLE_PERF))
    message(FATAL_ERROR "M14 nonheld13/data32 requires Rust smp-x86 linux-6.12, PERF, and no UBSAN")
endif()
set(RUST_KERNEL_ENABLED OFF)
if (ENABLE_RUST_KERNEL AND "${ARCH}" STREQUAL "x86_64")
	find_program(RUSTC rustc)
	if (NOT RUSTC)
		message(FATAL_ERROR "ENABLE_RUST_KERNEL requires rustc")
	endif()
	execute_process(
		COMMAND ${RUSTC} --version
		OUTPUT_VARIABLE RUSTC_VERSION
		OUTPUT_STRIP_TRAILING_WHITESPACE
	)
	if (NOT RUSTC_VERSION MATCHES "nightly")
		message(FATAL_ERROR "ENABLE_RUST_KERNEL requires nightly rustc; found ${RUSTC_VERSION}")
	endif()
	set(RUST_KERNEL_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/mckernel_rust.o")
	set(RUST_KERNEL_SRCS
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/lib.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/abi.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/abort.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/affinity.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/ap.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/atomic_helpers.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/bitmap.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/bitops.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/builtin_dma.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/cls.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/cls_helpers.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/debug.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/devobj.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/fileobj.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/fork_control_guest.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/fork_control_registry.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/fork_child_credits.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/fork_constructed_credits.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/fork_final_ack.rs"
        "${CMAKE_CURRENT_SOURCE_DIR}/rust/fork_runnable_child.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/futex.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/gencore.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/freeze.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/hash.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/hugefileobj.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/ikc_manycore.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/ikc_master.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/ikc_queue.rs"
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/init.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/host_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/llist.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/listeners.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/list_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/lock_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/ptrace_clone_noirq.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/mem_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/mikc.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/numparse.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/object_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/pager.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/page_alloc.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/page_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/plist.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/profile.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/procfs.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/process_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/pte_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/rbtree.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/refcount_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/rlimit_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/sched_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/shmid_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/shmobj.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/spinlock_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/string.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/smp_ikc.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/sysfs.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_perf_entry_candidate.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_perf_group_cleanup.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_signal_forward_defined_candidate.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_regset_defined_logger.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_signal_leaf_adapters.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_signal_log_budget.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_request_constructors.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_perf_open_forward.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_terminate_mcexec_forward.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_detach_wakeup.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_wakeup_writer_pair.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_exit_group_terminate.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_detach_kfree.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_context_forward_pair.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_munmap_clear_host_forward.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_exit_group_current_pid.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_util_clone_disabled_logger.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_settid_logger.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/timer.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/tofu_uapi.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/ubsan.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/waitq.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_coredump.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_exit_group_logger.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_cpu_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_cpu_log_providers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_clone_logger.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_local.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_memory_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_memory_logger_bridges.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_clear_host_pte_logger.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_memory_loggers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_perfctr.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_setup.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_vsyscall.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/xpmem_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/zeroobj.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/../host-kernel/native-rust/abi/vdso.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/native_vdso.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/../host-kernel/native-rust/zero_pages.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/clone3.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/native_signal.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/native_fault.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/native_futex.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/native_xstate.rs"
	)
		set(RUST_KERNEL_CFG)
        # Existing config literals are qualified for this production profile.
        if (ENABLE_RUST_PROCESS_VERBOSE_DATA AND
            ENABLE_RUST_PROCESS_VERBOSE_LOCAL_COMPANIONS AND
            MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12" AND
            NOT ENABLE_UBSAN AND NOT ENABLE_PROCESS_DEBUG_PRINT AND
            NOT ENABLE_FUGAKU_HACKS)
            set(MCKERNEL_PROCESS_VERBOSE_LOCAL_SELECTED ON)
        endif()
        file(GENERATE OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/rust/process_verbose_build_inputs.txt"
            CONTENT "selected=${ENABLE_RUST_PROCESS_VERBOSE_DATA}\nlocal=${MCKERNEL_PROCESS_VERBOSE_LOCAL_SELECTED}\nfile=${MCKERNEL_PROCESS_C_FILE}\nflags=${MCKERNEL_PROCESS_DDEBUG_FLAGS}\n")
        list(APPEND RUST_KERNEL_SRCS
            "${CMAKE_CURRENT_BINARY_DIR}/rust/process_verbose_build_inputs.txt")
        if (ENABLE_RUST_PROCESS_VERBOSE_DATA)
            list(APPEND RUST_KERNEL_CFG "--cfg" "process_verbose_data")
            if (MCKERNEL_PROCESS_VERBOSE_LOCAL_SELECTED)
                list(APPEND RUST_KERNEL_CFG "--cfg" "process_verbose_local_companions")
            endif()
            list(APPEND RUST_KERNEL_SRCS
                "${CMAKE_CURRENT_SOURCE_DIR}/rust/process_verbose_data.rs"
                "${MCKERNEL_PROCESS_C_FILE}"
                "${PROJECT_SOURCE_DIR}/lib/include/ihk/debug.h")
        endif()
		# Pair the existing F03 Rust providers with syscall.c source selectors below.
		list(APPEND RUST_KERNEL_CFG
			"--cfg" "f03_io_diagnostic_callbacks_candidate"
			"--cfg" "f03_mincore_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_move_pages_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_sched_bridges_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_signal_process_bridges_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_dispatch_context_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")
		if (ENABLE_NATIVE_SYSFS_VERIFY)
			list(APPEND RUST_KERNEL_CFG "--cfg" "native_sysfs_verify")
			list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/../scripts/tests/fixtures/mckernel_guest_sysfs.rs")
		endif()
		if (MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12")
			list(APPEND RUST_KERNEL_CFG "--cfg" "native_linux_irq_work_v6_12")
			# Pair qualified current290 providers with the Linux6.12 C selectors.
			list(APPEND RUST_KERNEL_CFG "--cfg" "f03_syscall_entry_candidate")
			list(APPEND RUST_KERNEL_CFG "--cfg" "f03_futex_atomic_candidate")
			list(APPEND RUST_KERNEL_CFG "--cfg" "f03_futex_no_uaccess_candidate")
			list(APPEND RUST_KERNEL_CFG "--cfg" "process_global_storage_candidate")
			list(APPEND RUST_KERNEL_CFG "--cfg" "f03_syscall_table_candidate")
			list(APPEND RUST_KERNEL_CFG "--cfg" "f03_ptrace_entry_candidate")
			list(APPEND RUST_KERNEL_CFG "--cfg" "f03_syscall_table_clone3")
			# Qualified next cohort: current native x86_64 Linux6.12, no UBSAN.
			if (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)
				if (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL OR MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
					list(APPEND RUST_KERNEL_CFG "--cfg" "f03_request_constructors_candidate")
				endif()
				if (MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL OR MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
					list(APPEND RUST_KERNEL_CFG "--cfg" "f03_signal_forward_defined_candidate")
				endif()
				if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
					list(APPEND RUST_KERNEL_CFG
						"--cfg" "f03_perf_entry_candidate"
						"--cfg" "f06_signal_leaf_adapters_candidate"
						"--cfg" "f06_signal_context_candidate"
						"--cfg" "f06_regset_defined_diagnostic_candidate"
						"--cfg" "f06_do_signal_whole_candidate"
						"--cfg" "f06_do_signal_reuse_qualified_context"
						"--cfg" "f06_debug_constants_candidate")
					list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_debug_constants.rs")
				endif()
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_wakeup_writer_pair_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_context_forward_pair_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_ptrace_clone_noirq_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_prlimit_body_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_do_exit_supported_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_unmap_begin_selected_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_unmap_remove_selected_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_unmap_finish_selected_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_mmap_page_callback_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_wait_release_selected_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_wait_process_release_selected_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_terminate_refcount_selected_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_ptrace_io_find_selected_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_ptrace_io_unlock_selected_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_mmap_flag_providers")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_prctl_set_register_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_prctl_get_register_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_mmap_dispatch_bridge_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_ptrace_context_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_ptrace_alloc_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_vdso_add_range_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_vdso_set_range_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_process_vm_entry_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_exit_waitq_wake_selected_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_copy_to_user_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_copy_from_user_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_forward_context_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_rt_sigreturn_syscall_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_rt_sigreturn_set_signal_candidate")
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_rt_sigreturn_check_signal_candidate")
				# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
				# Source-only default OFF. Root inserts only in existing selected
				# linux-6.12/x86_64/NOT ENABLE_UBSAN branch, alongside exact F06 providers.
				list(APPEND RUST_KERNEL_CFG
				    "--cfg" "f06_clone_reader_lock_candidate"
				    "--cfg" "f06_clone_reader_unlock_candidate"
				    "--cfg" "f06_ptrace_find_thread_candidate"
				    "--cfg" "f06_ptrace_thread_unlock_candidate")
				list(APPEND RUST_KERNEL_SRCS
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_clone_reader_lock.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_clone_reader_unlock.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_find_thread.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_thread_unlock.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_clone_ptrace_provider_abi.rs")
				set_property(SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" APPEND PROPERTY
				    COMPILE_DEFINITIONS
				    "MCKERNEL_RUST_F06_CLONE_READER_LOCK;MCKERNEL_RUST_F06_CLONE_READER_UNLOCK;MCKERNEL_RUST_F06_PTRACE_FIND_THREAD;MCKERNEL_RUST_F06_PTRACE_THREAD_UNLOCK")
				set(MCKERNEL_F06_ORIGIN_PROFILE "${PROJECT_SOURCE_DIR}/scripts/f06_origin_command_profile.json")
				# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
				# SOURCE ONLY. Root inserts in existing linux-6.12/x86_64/NOT ENABLE_UBSAN
				# selected-candidate branch. No broad profile or default-enabling claim.
				# Root installs derive_origin.py as scripts/derive_f06_origin.py before use.
				if (NOT ENABLE_RUST_KERNEL OR NOT ARCH STREQUAL "x86_64" OR
				    ENABLE_UBSAN OR NOT MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12")
				    message(FATAL_ERROR "F06 original source origin has no qualified profile")
				endif()
				if (NOT MCKERNEL_F06_ORIGIN_PROFILE)
				    message(FATAL_ERROR "F06 requires exact adopted SDK C argv profile")
				endif()
				find_package(Python3 REQUIRED COMPONENTS Interpreter)
				set(MCKERNEL_F06_ORIGIN_PRODUCER "${PROJECT_SOURCE_DIR}/scripts/derive_f06_origin.py")
				set(MCKERNEL_F06_C_SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c")
				set(MCKERNEL_F06_ORIGIN_DIR "${CMAKE_CURRENT_BINARY_DIR}/rust/f06-origin")
				execute_process(
				    COMMAND "${Python3_EXECUTABLE}" "${MCKERNEL_F06_ORIGIN_PRODUCER}"
				        --profile "${MCKERNEL_F06_ORIGIN_PROFILE}"
				        --source "${MCKERNEL_F06_C_SOURCE}"
				        --output "${MCKERNEL_F06_ORIGIN_DIR}"
				    RESULT_VARIABLE MCKERNEL_F06_ORIGIN_RESULT
				)
				if (NOT MCKERNEL_F06_ORIGIN_RESULT EQUAL 0)
				    message(FATAL_ERROR "F06 source origin producer rejected the profile/source")
				endif()
				include("${MCKERNEL_F06_ORIGIN_DIR}/f06_rt_sigreturn_origin.cmake")
				# Existing supported x86/linux6.12/non-UBSAN branch only; no new native profile.
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_obtain_clone_cpuid_candidate")
				list(APPEND RUST_KERNEL_SRCS
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_obtain_clone_cpuid.rs"
				    "${MCKERNEL_F06_ORIGIN_DIR}/f06_clone_cpuid_metadata.rs")
				set_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
				    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID")
				# Existing genuine-ABI shmget adapter; same supported profile/provider.
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_shmget_dispatch_candidate")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_shmget_dispatch.rs")
				set_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
				    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_SHMGET_DISPATCH")
				# Complete existing native signal-return FP ownership transaction.
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_native_signal_restore_fp_candidate")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_native_signal_restore_fp.rs")
				set_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
				    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP")
				# Complete legacy VDSO info body under the same supported profile.
				list(APPEND RUST_KERNEL_CFG "--cfg" "f06_vdso_info_candidate")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_info.rs")
				set_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
				    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_VDSO_INFO")

				# Exact F06 BODY3-9 cumulative selection; storage has one Rust owner each.
				list(APPEND RUST_KERNEL_CFG
				    "--cfg" "f06_ptrace_xstate_copy_to_candidate"
				    "--cfg" "f06_ptrace_xstate_copy_from_candidate"
				    "--cfg" "f06_vdso_setup_log_candidate"
				    "--cfg" "f06_vdso_state_candidate"
				    "--cfg" "f06_vdso_storage_candidate"
				    "--cfg" "f06_ptrace_user_bridges_candidate"
				    "--cfg" "f06_ptrace_gpregs_bridges_candidate"
				    "--cfg" "f06_prctl_log_candidate"
				    "--cfg" "f06_prctl_log_storage_candidate"
				    "--cfg" "f06_vdso_map_log_candidate"
				)
				list(APPEND RUST_KERNEL_SRCS
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_xstate_copy_to.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_xstate_copy_from.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_setup_log.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_state.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_storage.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_user_bridges.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_gpregs_bridges.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_prctl_log.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_prctl_log_storage.rs"
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_map_log.rs"
				)
				set_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
				    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_PTRACE_XSTATE_COPY_TO;MCKERNEL_RUST_F06_PTRACE_XSTATE_COPY_FROM;MCKERNEL_RUST_F06_VDSO_SETUP_LOG;MCKERNEL_RUST_F06_VDSO_STATE;MCKERNEL_RUST_F06_VDSO_STORAGE;MCKERNEL_RUST_F06_PTRACE_USER_BRIDGES;MCKERNEL_RUST_F06_PTRACE_GPREGS_BRIDGES;MCKERNEL_RUST_F06_PRCTL_LOG;MCKERNEL_RUST_F06_PRCTL_LOG_STORAGE;MCKERNEL_RUST_F06_VDSO_MAP_LOG")

				set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
				    "${MCKERNEL_F06_ORIGIN_PROFILE}"
				    "${MCKERNEL_F06_ORIGIN_PRODUCER}"
				    "${PROJECT_SOURCE_DIR}/lib/include/ihk/debug.h"
				    "${MCKERNEL_F06_C_SOURCE}")
				list(APPEND RUST_KERNEL_SRCS
				    "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_rt_sigreturn_alloc_free.rs"
				    "${MCKERNEL_F06_ORIGIN_DIR}/f06_rt_sigreturn_origin.cmake"
				    "${MCKERNEL_F06_ORIGIN_DIR}/f06_rt_sigreturn_origin.h")
				list(APPEND RUST_KERNEL_CFG
				    "--cfg" "f06_rt_sigreturn_alloc_candidate"
				    "--cfg" "f06_rt_sigreturn_free_candidate")
				set_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
				    COMPILE_DEFINITIONS
				    "MCKERNEL_RUST_F06_RT_SIGRETURN_ALLOC;MCKERNEL_RUST_F06_RT_SIGRETURN_FREE")
				set_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
				    INCLUDE_DIRECTORIES "${MCKERNEL_F06_ORIGIN_DIR}")
				set_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
				    OBJECT_DEPENDS "${MCKERNEL_F06_ORIGIN_DIR}/f06_rt_sigreturn_origin.h")
				if (ENABLE_PERF)
					list(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_alloc_bridges_selected_candidate")
					list(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_counter_control_bridges_selected_candidate")
					list(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_provider_next3_bridges_selected_candidate")
					list(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_event_provider_bridges_selected_candidate")
				endif()
				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_sync_child_event_candidate")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_perf_attr_callbacks.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_perf_event_attr_abi.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_prlimit.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_mmap_dispatch_bridge.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_context.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_alloc.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_add_range.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_set_range.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_process_vm_entry.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/arch_copy_to_user_bridge.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/arch_copy_from_user_bridge.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/arch_syscall_forward_context_bridge.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/arch_rt_sigreturn_syscall_bridge.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/arch_rt_sigreturn_set_signal_bridge.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/arch_rt_sigreturn_check_signal_bridge.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_prctl_set_register.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_mmap_flags.rs")
				list(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_prctl_get_register.rs")
			endif()
			add_definitions(-DMCKERNEL_NATIVE_CLONE3)
			add_definitions(-DMCKERNEL_NATIVE_SIGNAL_STACK)
			add_definitions(-DMCKERNEL_NATIVE_FAULT_FIXUP)
			add_definitions(-DMCKERNEL_NATIVE_FUTEX)
			add_definitions(-DMCKERNEL_NATIVE_CLONE_TID)
		endif()
		if (ENABLE_TOFU)
			list(APPEND RUST_KERNEL_CFG "--cfg" "enable_tofu")
		endif()
		if (ENABLE_PER_CPU_ALLOC_CACHE)
			list(APPEND RUST_KERNEL_CFG "--cfg" "enable_per_cpu_alloc_cache")
		endif()
		if (ENABLE_FUGAKU_HACKS)
			list(APPEND RUST_KERNEL_CFG "--cfg" "enable_fugaku_hacks")
		endif()
		if (PROFILE_ENABLE)
			list(APPEND RUST_KERNEL_CFG "--cfg" "enable_profile")
		endif()
		if (ENABLE_PERF)
			list(APPEND RUST_KERNEL_CFG "--cfg" "enable_perf")
		endif()
		if (ENABLE_RUSAGE)
			list(APPEND RUST_KERNEL_CFG "--cfg" "enable_rusage")
		endif()
		# Source-bound x86 policy and exact C diagnostic filename for these Rust providers.
		set(MCKERNEL_CPU_MARCH_HEADER
			"${IHK_FULL_SOURCE_DIR}/cokernel/smp/x86_64/include/march.h")
		file(SHA256 "${MCKERNEL_CPU_MARCH_HEADER}" MCKERNEL_CPU_MARCH_SHA256)
		if (NOT MCKERNEL_CPU_MARCH_SHA256 STREQUAL
		    "32984f29c20133f89b2410c922fc291cd675f2942b6128cea55d0e0ff3826f49")
			message(FATAL_ERROR "Unqualified x86 march.h SSE policy; qualify actual header first")
		endif()
		# The exact qualified header has one unconditional #define ENABLE_SSE.
		set(MCKERNEL_X86_ENABLE_SSE 1)
		# Same absolute spelling used in MCKERNEL_SRCS below, preserving C __FILE__.
		set(MCKERNEL_CPU_C_FILE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/cpu.c")
		list(APPEND RUST_KERNEL_SRCS "${MCKERNEL_CPU_MARCH_HEADER}" "${MCKERNEL_CPU_C_FILE}")
		set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
			"${MCKERNEL_CPU_MARCH_HEADER}")
		add_custom_command(
		OUTPUT "${RUST_KERNEL_OBJ}"
		COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
		COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS=
			MCKERNEL_RUST_VERSION=${MCKERNEL_VERSION}
			MCKERNEL_RUST_BUILDID=${BUILDID}
			MCKERNEL_X86_ENABLE_SSE=${MCKERNEL_X86_ENABLE_SSE}
			MCKERNEL_CPU_C_FILE=${MCKERNEL_CPU_C_FILE}
            "MCKERNEL_PROCESS_C_FILE=${MCKERNEL_PROCESS_C_FILE}"
            "MCKERNEL_PROCESS_DDEBUG_FLAGS=${MCKERNEL_PROCESS_DDEBUG_FLAGS}"
			"MCKERNEL_F06_RT_SIGRETURN_ORIGIN=${MCKERNEL_F06_RT_SIGRETURN_ORIGIN}"
			"MCKERNEL_F06_CLONE_CPUID_METADATA_RS=${MCKERNEL_F06_CLONE_CPUID_METADATA_RS}"
			${RUSTC}
			--crate-name mckernel_rust
			--crate-type lib
			--edition=2021
			-C panic=abort
			-C opt-level=2
			-C debuginfo=2
			-C code-model=large
			-C relocation-model=static
			-C no-redzone=yes
			-C force-frame-pointers=yes
			-C overflow-checks=off
			-C force-unwind-tables=no
			-C no-vectorize-loops
			-C no-vectorize-slp
			-C target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma
			${RUST_KERNEL_CFG}
			--emit=obj=${RUST_KERNEL_OBJ}
			"${CMAKE_CURRENT_SOURCE_DIR}/rust/lib.rs"
		DEPENDS ${RUST_KERNEL_SRCS}
		COMMENT "Building Rust kernel object"
		VERBATIM
	)
	add_custom_target(mckernel_rust_obj DEPENDS "${RUST_KERNEL_OBJ}")
	set_source_files_properties("${RUST_KERNEL_OBJ}"
		PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
	set(RUST_KERNEL_ENABLED ON)
endif()

set(MCKERNEL_SRCS
	init.c mem.c debug.c mikc.c listeners.c ap.c syscall.c cls.c host.c host_helpers.c lock_helpers.c process.c process_helpers.c sched_helpers.c
	copy.c waitq.c futex.c timer.c plist.c object_helpers.c fileobj.c shmobj.c zeroobj.c
	procfs.c devobj.c sysfs.c xpmem.c profile.c freeze.c pager.c
	gencore.c hugefileobj.c

	${IHK_FULL_SOURCE_DIR}/ikc/manycore.c
	${IHK_FULL_SOURCE_DIR}/ikc/master.c
	${IHK_FULL_SOURCE_DIR}/ikc/queue.c

	${PROJECT_SOURCE_DIR}/lib/abort.c
	${PROJECT_SOURCE_DIR}/lib/bitmap.c
	${PROJECT_SOURCE_DIR}/lib/bitops.c
	${PROJECT_SOURCE_DIR}/lib/page_alloc.c
	${PROJECT_SOURCE_DIR}/lib/string.c
	${PROJECT_SOURCE_DIR}/lib/vsprintf.c

	${IHK_FULL_SOURCE_DIR}/cokernel/smp/ikc.c
	${IHK_FULL_SOURCE_DIR}/cokernel/smp/${ARCH}/dma.c
	${IHK_FULL_SOURCE_DIR}/cokernel/smp/${ARCH}/setup.c
)

if (RUST_KERNEL_ENABLED)
		add_definitions(-DMCKERNEL_RUST_ATOMIC_HELPERS
			-DMCKERNEL_RUST_BITOPS
			-DMCKERNEL_RUST_LOCK_HELPERS
			-DMCKERNEL_RUST_LIST_HELPERS
		-DMCKERNEL_RUST_MC_RWLOCK_HELPERS
		-DMCKERNEL_RUST_MCS_RWLOCK_HELPERS
		-DMCKERNEL_RUST_PTE_HELPERS
		-DMCKERNEL_RUST_REFCOUNT_HELPERS
		-DMCKERNEL_RUST_SPINLOCK_HELPERS)
	list(APPEND MCKERNEL_SRCS
		"${RUST_KERNEL_OBJ}"
		rust/abi_checks.c
	)
	list(REMOVE_ITEM MCKERNEL_SRCS
		ap.c
		cls.c
		copy.c
		debug.c
		init.c
		fileobj.c
		freeze.c
		futex.c
		gencore.c
		host.c
		host_helpers.c
		lock_helpers.c
		listeners.c
		mikc.c
		object_helpers.c
		pager.c
		plist.c
		profile.c
		procfs.c
		process_helpers.c
		sched_helpers.c
		shmobj.c
		sysfs.c
		timer.c
		zeroobj.c
		waitq.c
		xpmem.c
		"${PROJECT_SOURCE_DIR}/lib/abort.c"
		"${PROJECT_SOURCE_DIR}/lib/bitmap.c"
		"${PROJECT_SOURCE_DIR}/lib/bitops.c"
		"${PROJECT_SOURCE_DIR}/lib/page_alloc.c"
		"${PROJECT_SOURCE_DIR}/lib/string.c"
		"${PROJECT_SOURCE_DIR}/lib/vsprintf.c"
		"${IHK_FULL_SOURCE_DIR}/ikc/manycore.c"
		"${IHK_FULL_SOURCE_DIR}/ikc/master.c"
		"${IHK_FULL_SOURCE_DIR}/ikc/queue.c"
		"${IHK_FULL_SOURCE_DIR}/cokernel/smp/${ARCH}/setup.c"
	)
	if (NOT ENABLE_FUGAKU_HACKS)
		list(REMOVE_ITEM MCKERNEL_SRCS
			devobj.c
			hugefileobj.c)
	endif()
	set_source_files_properties("${PROJECT_SOURCE_DIR}/lib/bitmap.c"
		PROPERTIES COMPILE_DEFINITIONS
		"MCKERNEL_RUST_BITMAP_CORE;MCKERNEL_RUST_BITMAP_PARSE")
	set_source_files_properties("${PROJECT_SOURCE_DIR}/lib/page_alloc.c"
		PROPERTIES COMPILE_DEFINITIONS
		"MCKERNEL_RUST_PAGE_ALLOC_RBTREE;MCKERNEL_RUST_PAGEALLOC_BITMAP")
	set_source_files_properties("${PROJECT_SOURCE_DIR}/lib/string.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_STRING_CORE)
	set_source_files_properties("${PROJECT_SOURCE_DIR}/lib/vsprintf.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_NUMPARSE)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/plist.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_PLIST_CORE)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/waitq.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_WAITQ_CORE)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/cls.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_CLS_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/init.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_INIT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/host_helpers.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_HOST_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/mem.c"
		PROPERTIES COMPILE_DEFINITIONS
		"MCKERNEL_RUST_MEM_HELPERS;MCKERNEL_RUST_PAGE_HELPERS;MCKERNEL_RUST_MMAN_HELPERS;MCKERNEL_RUST_HASH_HELPERS;MCKERNEL_RUST_RUSAGE_PRIVATE_HELPERS")
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/process.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_PROCESS_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/process_helpers.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_PROCESS_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/sched_helpers.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_SCHED_RUNTIME_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/object_helpers.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/fileobj.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/shmobj.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/devobj.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/zeroobj.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/procfs.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/sysfs.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/hugefileobj.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/gencore.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_GENCORE_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/syscall.c"
		PROPERTIES COMPILE_DEFINITIONS
		"MCKERNEL_RUST_SHMID_HELPERS;MCKERNEL_RUST_SHM_PERM_HELPERS;MCKERNEL_RUST_RLIMIT_HELPERS;MCKERNEL_RUST_SCHED_PRIO_HELPERS;MCKERNEL_RUST_SCHED_POLICY_HELPERS;MCKERNEL_RUST_SYSCALL_POLICY_HELPERS;MCKERNEL_RUST_SYSCALL_OFFLOAD;MCKERNEL_RUST_SIGNAL_HELPERS;MCKERNEL_RUST_F03_IO_DIAGNOSTICS;MCKERNEL_RUST_F03_MINCORE;MCKERNEL_RUST_F03_MOVE_PAGES;MCKERNEL_RUST_F03_SCHED_BRIDGES;MCKERNEL_RUST_F03_SIGNAL_PROCESS_BRIDGES;MCKERNEL_RUST_F03_DISPATCH_CONTEXT;MCKERNEL_RUST_F03_LEAF_CALLBACKS")
	if (MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12")
		# Pair the existing Rust process_global_storage_candidate provider above.
		set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/process.c" APPEND PROPERTY
			COMPILE_DEFINITIONS MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE)
		if (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)
			if (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL OR MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
				set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)
			endif()

			if (MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL OR MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
				set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL)
			endif()
			if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
				set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY
					COMPILE_DEFINITIONS MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)
				set_property(SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" APPEND PROPERTY
					COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_XRSTOR_LEAF;MCKERNEL_RUST_F06_BAD_FRAME_LEAF;MCKERNEL_RUST_F06_SIGNAL_CONTEXT;MCKERNEL_RUST_F06_REGSET_DEFINED_DIAGNOSTIC;MCKERNEL_RUST_F06_DO_SIGNAL_WHOLE;MCKERNEL_RUST_F06_DEBUG_CONSTANTS;MCKERNEL_M14_F06_ORIGIN_GUARD")
			endif()
			set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY
				COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR;MCKERNEL_RUST_F03_CONTEXT_FORWARD_PAIR;MCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ;MCKERNEL_RUST_F03_PERF_ATTR_CALLBACKS;MCKERNEL_RUST_F03_PRLIMIT_BODY;MCKERNEL_RUST_F03_EXEC_DEFINED_TAIL;MCKERNEL_RUST_F03_DO_EXIT_V2;MCKERNEL_RUST_F03_UNMAP_BEGIN;MCKERNEL_RUST_F03_UNMAP_REMOVE;MCKERNEL_RUST_F03_UNMAP_FINISH;MCKERNEL_RUST_F03_MMAP_PAGE_CALLBACK;MCKERNEL_RUST_F03_WAIT_RELEASE;MCKERNEL_RUST_F03_WAIT_PROCESS_RELEASE;MCKERNEL_RUST_F03_TERMINATE_REFCOUNT;MCKERNEL_RUST_F03_TERMINATE_CMPXCHG;MCKERNEL_RUST_F03_PTRACE_IO_FIND;MCKERNEL_RUST_F03_PTRACE_IO_UNLOCK;MCKERNEL_RUST_F03_PTRACE_IO_COPY_FROM;MCKERNEL_RUST_F03_SYNC_CHILD_EVENT;MCKERNEL_RUST_F03_WAKEUP_FIND;MCKERNEL_RUST_F03_WAKEUP_UNLOCK;MCKERNEL_RUST_F03_EXIT_WAITQ_WAKE")
			if (ENABLE_PERF)
				set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY
					COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES;MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES;MCKERNEL_RUST_F03_PERF_EVENT_PROVIDER_BRIDGES;MCKERNEL_RUST_F03_PERF_PROVIDER_NEXT3_BRIDGES")
			endif()
			set_property(SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" APPEND PROPERTY
				COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_MMAP_FLAG_PROVIDERS;MCKERNEL_RUST_F06_PRCTL_SET_REGISTER;MCKERNEL_RUST_F06_PRCTL_GET_REGISTER;MCKERNEL_RUST_F06_MMAP_DISPATCH_BRIDGE;MCKERNEL_RUST_F06_PTRACE_CONTEXT;MCKERNEL_RUST_F06_PTRACE_ALLOC;MCKERNEL_RUST_F06_VDSO_ADD_RANGE;MCKERNEL_RUST_F06_VDSO_SET_RANGE;MCKERNEL_RUST_F06_PROCESS_VM_ENTRY;MCKERNEL_RUST_F06_COPY_TO_USER;MCKERNEL_RUST_F06_COPY_FROM_USER;MCKERNEL_RUST_F06_FORWARD_CONTEXT;MCKERNEL_RUST_F06_RT_SIGRETURN_SYSCALL;MCKERNEL_RUST_F06_RT_SIGRETURN_SET_SIGNAL;MCKERNEL_RUST_F06_RT_SIGRETURN_CHECK_SIGNAL")
		endif()
		set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY
			COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_PTRACE_ENTRY;MCKERNEL_RUST_F03_SYSCALL_TABLE;MCKERNEL_RUST_F03_SYSCALL_ENTRY;MCKERNEL_RUST_F03_FUTEX_ATOMIC")
	endif()
	if (ENABLE_NATIVE_FORK_OWNED_TRANSACTION)
		set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY
			COMPILE_DEFINITIONS MCKERNEL_NATIVE_FORK_OWNED_TRANSACTION)
	endif()
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/xpmem.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_XPMEM_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/tofu/tof_utofu_main.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_TOFU_UAPI)
	set_source_files_properties("${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/cpu.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_X86_CPU_HELPERS)
else()
	list(APPEND MCKERNEL_SRCS
		rbtree.c
		llist.c
		"${PROJECT_SOURCE_DIR}/lib/list.c")
	if ("${ARCH}" STREQUAL "x86_64")
		set_source_files_properties("${IHK_FULL_SOURCE_DIR}/cokernel/smp/x86_64/setup.c"
			PROPERTIES COMPILE_DEFINITIONS MCKERNEL_IHK_STATIC_PERF_TABLES)
		set_source_files_properties("${IHK_FULL_SOURCE_DIR}/ikc/queue.c"
			PROPERTIES COMPILE_DEFINITIONS MCKERNEL_IHK_QUEUE_ATOMICS)
	endif()
endif()

if (ENABLE_TOFU)
	list(APPEND MCKERNEL_SRCS
		tofu/tof_utofu_main.c
	)
endif()

if (ENABLE_UBSAN)
	add_compile_options(-fsanitize=undefined)
	list(APPEND MCKERNEL_SRCS ubsan.c)
	if (RUST_KERNEL_ENABLED)
		list(REMOVE_ITEM MCKERNEL_SRCS ubsan.c)
	endif()
endif(ENABLE_UBSAN)

if (BUILD_TARGET STREQUAL "smp-x86")
	list(APPEND MCKERNEL_SRCS
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/context.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/coredump.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/cpu.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/interrupt.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/lock.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/local.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/memory.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/memory_helpers.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/mikc.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/perfctr.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/trampoline.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/vsyscall.c

	)
	set(LINKER_SCRIPT "smp-x86.lds")
	if (RUST_KERNEL_ENABLED)
		list(REMOVE_ITEM MCKERNEL_SRCS
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/coredump.c"
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/lock.c"
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/local.c"
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/memory_helpers.c"
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/mikc.c"
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/perfctr.c"
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/vsyscall.c"
			"${IHK_FULL_SOURCE_DIR}/cokernel/smp/ikc.c"
			"${IHK_FULL_SOURCE_DIR}/cokernel/smp/${ARCH}/dma.c")
		set_source_files_properties(
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/memory.c"
			PROPERTIES COMPILE_DEFINITIONS
			"MCKERNEL_RUST_X86_USER_COPY_PUBLIC;MCKERNEL_RUST_X86_MEMORY_PUBLIC")
		set_source_files_properties(
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/memory_helpers.c"
			PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_X86_MEMORY_HELPERS)
		if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
			# Keep selectors already appended in the supported Rust branch above.
			set_property(SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" APPEND PROPERTY
				COMPILE_DEFINITIONS "MCKERNEL_RUST_SYSCALL_POLICY_HELPERS;MCKERNEL_RUST_X86_CPU_HELPERS")
		else()
		set_source_files_properties(
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c"
			PROPERTIES COMPILE_DEFINITIONS
			"MCKERNEL_RUST_SYSCALL_POLICY_HELPERS;MCKERNEL_RUST_X86_CPU_HELPERS")
		endif()
	endif()
elseif (BUILD_TARGET STREQUAL "smp-arm64")

	configure_file(${KERNEL_DIR}/include/generated/vdso-offsets.h include/vdso-offsets.h)

	list(APPEND MCKERNEL_SRCS
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/assert.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/cache.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/context.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/coredump.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/cpu.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/cpufeature.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/cputable.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/debug-monitors.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/entry-fpsimd.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/entry.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/fault.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/fpsimd.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/head.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/hw_breakpoint.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/hyp-stub.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/imp-sysreg.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/irq-gic-v2.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/irq-gic-v3.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/local.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/memcpy.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/memory.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/memset.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/mikc.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/perfctr.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/perfctr_armv8pmu.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/proc-macros.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/proc.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/psci.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/ptrace.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/smp.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/timer.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/trampoline.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/traps.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/vdso.c

	)

	execute_process(COMMAND awk -F= "$1 == \"CONFIG_NR_CPUS\" { print $2; exit; }" "${KERNEL_DIR}/.config"
			OUTPUT_VARIABLE CONFIG_NR_CPUS OUTPUT_STRIP_TRAILING_WHITESPACE)
	execute_process(COMMAND awk -F= "$1 == \"CONFIG_ARM_ARCH_TIMER_EVTSTREAM\" { print $2; exit; }" "${KERNEL_DIR}/.config"
			OUTPUT_VARIABLE CONFIG_ARM_ARCH_TIMER_EVTSTREAM OUTPUT_STRIP_TRAILING_WHITESPACE)
	execute_process(COMMAND awk -F= "$1 == \"CONFIG_HZ\" { print $2; exit; }" "${KERNEL_DIR}/.config"
			OUTPUT_VARIABLE CONFIG_HZ OUTPUT_STRIP_TRAILING_WHITESPACE)
	execute_process(COMMAND awk -F= "$1 == \"CONFIG_ARM64_VHE\" { print $2; exit; }" "${KERNEL_DIR}/.config"
			OUTPUT_VARIABLE CONFIG_ARM64_VHE OUTPUT_STRIP_TRAILING_WHITESPACE)
	execute_process(COMMAND awk -F= "$1 == \"CONFIG_ARM_GIC_V3\" { print $2; exit; }" "${KERNEL_DIR}/.config"
			OUTPUT_VARIABLE CONFIG_ARM_GIC_V3 OUTPUT_STRIP_TRAILING_WHITESPACE)
	execute_process(COMMAND bash -c "gawk '/CPU implementer/ { print \$4; exit; }' /proc/cpuinfo"
			OUTPUT_VARIABLE CPU_IMPLEMENTER OUTPUT_STRIP_TRAILING_WHITESPACE)
	execute_process(COMMAND bash -c "gawk '/CPU architecture/ { print \$3; exit; }' /proc/cpuinfo"
			OUTPUT_VARIABLE CPU_ARCH OUTPUT_STRIP_TRAILING_WHITESPACE)
	execute_process(COMMAND bash -c "gawk '/CPU variant/ { print \$4; exit; }' /proc/cpuinfo"
			OUTPUT_VARIABLE CPU_VARIANT OUTPUT_STRIP_TRAILING_WHITESPACE)
	execute_process(COMMAND bash -c "gawk '/CPU part/ { print \$4; exit; }' /proc/cpuinfo"
			OUTPUT_VARIABLE CPU_PART OUTPUT_STRIP_TRAILING_WHITESPACE)

	message("Host kernel CONFIG_NR_CPUS=${CONFIG_NR_CPUS}")
	message("Host kernel CONFIG_HZ=${CONFIG_HZ}")

	if(CONFIG_ARM_GIC_V3 STREQUAL "y")
		add_definitions(-DCONFIG_ARM_GIC_V3=y)
		# NMI by priority doesn't work with ThunderX2
		if(CPU_IMPLEMENTER STREQUAL "0x43" AND CPU_ARCH STREQUAL "8" AND
		   CPU_VARIANT STREQUAL "0x1" AND CPU_PART STREQUAL "0x0af")
			# Don't add "-DCONFIG_HAS_NMI=n" because it'll be added to KBUILD_C_FLAGS
			message("CONFIG_HAS_NMI isn't defined for ThunderX2")
		else()
			add_definitions(-DCONFIG_HAS_NMI=y)
			message("CONFIG_HAS_NMI is defined")
		endif()
	else(CONFIG_ARM_GIC_V3 STREQUAL "y")
		message(FATAL_ERROR "Host kernel must have GIC v3 enabled")
	endif(CONFIG_ARM_GIC_V3 STREQUAL "y")
	if(CONFIG_ARM64_VHE STREQUAL "y")
		add_definitions(-DCONFIG_ARM64_VHE)
	endif(CONFIG_ARM64_VHE STREQUAL "y")
	if(CONFIG_ARM_ARCH_TIMER_EVTSTREAM STREQUAL "y")
		add_definitions(-DCONFIG_ARM_ARCH_TIMER_EVTSTREAM)
	endif(CONFIG_ARM_ARCH_TIMER_EVTSTREAM STREQUAL "y")
	add_definitions(-DNR_CPUS=${CONFIG_NR_CPUS} -DCONFIG_HZ=${CONFIG_HZ})
	# Seems to have been hardcoded to 512 in old makefiles
	add_definitions(-DCONFIG_SMP_MAX_CORES=512)
	# Always turned on as well
	add_definitions(-DCONFIG_ARM64_SVE)
endif()

configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/config/${LINKER_SCRIPT}.in
  ${CMAKE_CURRENT_BINARY_DIR}/config/${LINKER_SCRIPT}
  @ONLY
  )

# Apply after existing source properties, which otherwise overwrite definitions.
if (ENABLE_PROCESS_DEBUG_PRINT)
    set_property(SOURCE "${MCKERNEL_PROCESS_C_FILE}" APPEND PROPERTY
        COMPILE_DEFINITIONS DEBUG_PRINT_PROCESS)
endif()
if (RUST_KERNEL_ENABLED AND ENABLE_RUST_PROCESS_VERBOSE_DATA)
    set_property(SOURCE "${MCKERNEL_PROCESS_C_FILE}" APPEND PROPERTY
        COMPILE_DEFINITIONS MCKERNEL_RUST_PROCESS_VERBOSE_DATA
        "MCKERNEL_PROCESS_DDEBUG_FLAGS=${MCKERNEL_PROCESS_DDEBUG_FLAGS}"
        "MCKERNEL_PROCESS_DDEBUG_FILE=\"${MCKERNEL_PROCESS_C_FILE}\"")
endif()

if (RUST_KERNEL_ENABLED AND MCKERNEL_PROCESS_VERBOSE_LOCAL_SELECTED)
    set_property(SOURCE "${MCKERNEL_PROCESS_C_FILE}" APPEND PROPERTY
        COMPILE_DEFINITIONS MCKERNEL_RUST_PROCESS_VERBOSE_LOCAL_COMPANIONS)
endif()

add_executable(mckernel.img ${MCKERNEL_SRCS})
if (RUST_KERNEL_ENABLED)
	add_dependencies(mckernel.img mckernel_rust_obj)
endif()

set_target_properties(mckernel.img PROPERTIES INSTALL_RPATH "")
set_target_properties(mckernel.img PROPERTIES LINK_FLAGS
	"-e arch_start -T ${CMAKE_CURRENT_BINARY_DIR}/config/${LINKER_SCRIPT} --build-id -Map=${CMAKE_CURRENT_BINARY_DIR}/mckernel.img.map")

install(TARGETS "mckernel.img"
	DESTINATION "${MCKERNELDIR}")
