set(CMAKE_SHARED_LIBRARY_LINK_C_FLAGS)
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
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/bitmap.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/cls_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/llist.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/mem_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/numparse.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/object_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/page_alloc.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/page_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/plist.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/process_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/rbtree.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/rlimit_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/sched_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/shmid_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/string.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/waitq.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/x86_memory_helpers.rs"
		"${CMAKE_CURRENT_SOURCE_DIR}/rust/xpmem_helpers.rs"
	)
	set(RUST_KERNEL_CFG)
	if (ENABLE_TOFU)
		list(APPEND RUST_KERNEL_CFG "--cfg" "enable_tofu")
	endif()
	if (ENABLE_PER_CPU_ALLOC_CACHE)
		list(APPEND RUST_KERNEL_CFG "--cfg" "enable_per_cpu_alloc_cache")
	endif()
	add_custom_command(
		OUTPUT "${RUST_KERNEL_OBJ}"
		COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
		COMMAND ${RUSTC}
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
	init.c mem.c debug.c mikc.c listeners.c ap.c syscall.c cls.c host.c process.c process_helpers.c sched_helpers.c
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
	list(APPEND MCKERNEL_SRCS
		"${RUST_KERNEL_OBJ}"
		rust/abi_checks.c
	)
	set_source_files_properties("${PROJECT_SOURCE_DIR}/lib/bitmap.c"
		PROPERTIES COMPILE_DEFINITIONS
		"MCKERNEL_RUST_BITMAP_CORE;MCKERNEL_RUST_BITMAP_PARSE")
	set_source_files_properties("${PROJECT_SOURCE_DIR}/lib/bitops.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_BITOPS)
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
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/mem.c"
		PROPERTIES COMPILE_DEFINITIONS
		"MCKERNEL_RUST_MEM_HELPERS;MCKERNEL_RUST_PAGE_HELPERS")
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
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/devobj.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/procfs.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/sysfs.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_OBJECT_HELPERS)
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/syscall.c"
		PROPERTIES COMPILE_DEFINITIONS
		"MCKERNEL_RUST_SHMID_HELPERS;MCKERNEL_RUST_SHM_PERM_HELPERS;MCKERNEL_RUST_RLIMIT_HELPERS;MCKERNEL_RUST_SCHED_PRIO_HELPERS;MCKERNEL_RUST_SCHED_POLICY_HELPERS;MCKERNEL_RUST_SYSCALL_POLICY_HELPERS")
	set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/xpmem.c"
		PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_XPMEM_HELPERS)
else()
	list(APPEND MCKERNEL_SRCS rbtree.c llist.c)
endif()

if (ENABLE_TOFU)
	list(APPEND MCKERNEL_SRCS
		tofu/tof_utofu_main.c
	)
endif()

if (ENABLE_UBSAN)
	add_compile_options(-fsanitize=undefined)
	list(APPEND MCKERNEL_SRCS ubsan.c)
endif(ENABLE_UBSAN)

if (BUILD_TARGET STREQUAL "smp-x86")
	list(APPEND MCKERNEL_SRCS
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/context.S
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/coredump.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/cpu.c
		${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/interrupt.S
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
		set_source_files_properties(
			"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/memory_helpers.c"
			PROPERTIES COMPILE_DEFINITIONS MCKERNEL_RUST_X86_MEMORY_HELPERS)
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

add_executable(mckernel.img ${MCKERNEL_SRCS})
if (RUST_KERNEL_ENABLED)
	add_dependencies(mckernel.img mckernel_rust_obj)
endif()

set_target_properties(mckernel.img PROPERTIES INSTALL_RPATH "")
set_target_properties(mckernel.img PROPERTIES LINK_FLAGS
	"-e arch_start -T ${CMAKE_CURRENT_BINARY_DIR}/config/${LINKER_SCRIPT} --build-id")

install(TARGETS "mckernel.img"
	DESTINATION "${MCKERNELDIR}")
