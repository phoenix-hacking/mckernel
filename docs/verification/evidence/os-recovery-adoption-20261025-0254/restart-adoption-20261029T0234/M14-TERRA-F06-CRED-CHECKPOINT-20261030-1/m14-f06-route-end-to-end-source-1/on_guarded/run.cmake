set(PROJECT_SOURCE_DIR "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-f06-route-end-to-end-source-1/on_guarded/src")
set(ARCH x86_64)
set(ENABLE_RUST_KERNEL ON)
set(ENABLE_UBSAN OFF)
set(MCKERNEL_HOST_IRQ_ABI linux-6.12)
if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
					set(MCKERNEL_F06_ORIGIN_PROFILE "${PROJECT_SOURCE_DIR}/scripts/f06_origin_command_profile_e6a_guarded.json")
					set(MCKERNEL_F06_ORIGIN_PRODUCER "${PROJECT_SOURCE_DIR}/scripts/derive_f06_origin_e6a_guarded.py")
				else()
					set(MCKERNEL_F06_ORIGIN_PROFILE "${PROJECT_SOURCE_DIR}/scripts/f06_origin_command_profile.json")
					set(MCKERNEL_F06_ORIGIN_PRODUCER "${PROJECT_SOURCE_DIR}/scripts/derive_f06_origin.py")
				endif()
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
