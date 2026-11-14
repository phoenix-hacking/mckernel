from pathlib import Path
p=Path('postimage/CMakeLists.txt'); s=Path('preimage/CMakeLists.txt').read_text()
def replace(old,new,count=1):
 global s
 assert s.count(old)==count,(old[:80],s.count(old),count)
 s=s.replace(old,new)
anchor='option(ENABLE_RUST_KERNEL "Enable Rust code in the McKernel image" ON)'
replace(anchor,anchor+'''
# Private nonheld 13-function plus data32 candidate; no default change.
option(MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL "Select the nonheld M14 13-function and data candidate" OFF)''')
anchor='set(RUST_KERNEL_ENABLED OFF)'
replace(anchor,'''if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL AND
    (NOT ENABLE_RUST_KERNEL OR NOT "${ARCH}" STREQUAL "x86_64" OR
     NOT BUILD_TARGET STREQUAL "smp-x86" OR ENABLE_UBSAN OR
     NOT MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12" OR NOT ENABLE_PERF))
    message(FATAL_ERROR "M14 nonheld13/data32 requires Rust smp-x86 linux-6.12, PERF, and no UBSAN")
endif()
'''+anchor)
for name in ['MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL','MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL']:
 replace(f'if ({name})',f'if ({name} OR MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)',2)
anchor='''				list(APPEND RUST_KERNEL_CFG "--cfg" "f03_wakeup_writer_pair_candidate")'''
replace(anchor,'''				if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
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
'''+anchor)
anchor='''			set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY
				COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR;'''
replace(anchor,'''			if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
				set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY
					COMPILE_DEFINITIONS MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL)
				set_property(SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" APPEND PROPERTY
					COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_XRSTOR_LEAF;MCKERNEL_RUST_F06_BAD_FRAME_LEAF;MCKERNEL_RUST_F06_SIGNAL_CONTEXT;MCKERNEL_RUST_F06_REGSET_DEFINED_DIAGNOSTIC;MCKERNEL_RUST_F06_DO_SIGNAL_WHOLE;MCKERNEL_RUST_F06_DEBUG_CONSTANTS")
			endif()
'''+anchor)
old='''		set_source_files_properties(
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c"
			PROPERTIES COMPILE_DEFINITIONS
			"MCKERNEL_RUST_SYSCALL_POLICY_HELPERS;MCKERNEL_RUST_X86_CPU_HELPERS")'''
new='''		if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
			# Keep selectors already appended in the supported Rust branch above.
			set_property(SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" APPEND PROPERTY
				COMPILE_DEFINITIONS "MCKERNEL_RUST_SYSCALL_POLICY_HELPERS;MCKERNEL_RUST_X86_CPU_HELPERS")
		else()
'''+old+'''
		endif()'''
replace(old,new)
p.write_text(s)
