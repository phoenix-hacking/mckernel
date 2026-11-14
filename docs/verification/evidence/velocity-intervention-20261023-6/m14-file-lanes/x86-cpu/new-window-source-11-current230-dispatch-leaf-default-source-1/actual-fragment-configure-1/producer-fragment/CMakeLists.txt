cmake_minimum_required(VERSION 3.11)
project(f03_current230_dispatch_leaf_paired_producer_selection LANGUAGES NONE)
set(RUST_KERNEL_ENABLED OFF)
if (ENABLE_RUST_KERNEL AND "${ARCH}" STREQUAL "x86_64")
set(RUST_KERNEL_CFG)
		# Pair the existing F03 Rust providers with syscall.c source selectors below.
		list(APPEND RUST_KERNEL_CFG
			"--cfg" "f03_io_diagnostic_callbacks_candidate"
			"--cfg" "f03_mincore_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_move_pages_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_sched_bridges_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_signal_process_bridges_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_dispatch_context_candidate")
		list(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")
set(RUST_KERNEL_ENABLED ON)
endif()
if (RUST_KERNEL_ENABLED)
set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/syscall.c"
		PROPERTIES COMPILE_DEFINITIONS
		"MCKERNEL_RUST_SHMID_HELPERS;MCKERNEL_RUST_SHM_PERM_HELPERS;MCKERNEL_RUST_RLIMIT_HELPERS;MCKERNEL_RUST_SCHED_PRIO_HELPERS;MCKERNEL_RUST_SCHED_POLICY_HELPERS;MCKERNEL_RUST_SYSCALL_POLICY_HELPERS;MCKERNEL_RUST_SYSCALL_OFFLOAD;MCKERNEL_RUST_SIGNAL_HELPERS;MCKERNEL_RUST_F03_IO_DIAGNOSTICS;MCKERNEL_RUST_F03_MINCORE;MCKERNEL_RUST_F03_MOVE_PAGES;MCKERNEL_RUST_F03_SCHED_BRIDGES;MCKERNEL_RUST_F03_SIGNAL_PROCESS_BRIDGES;MCKERNEL_RUST_F03_DISPATCH_CONTEXT;MCKERNEL_RUST_F03_LEAF_CALLBACKS")
endif()
get_source_file_property(_cdefs "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" COMPILE_DEFINITIONS)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/selection.txt" "rust=${RUST_KERNEL_ENABLED}
cfg=${RUST_KERNEL_CFG}
cdefs=${_cdefs}
")
