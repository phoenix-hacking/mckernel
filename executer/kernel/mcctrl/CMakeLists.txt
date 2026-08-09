option(ENABLE_GCOV "Enable GCOV" OFF)
if (ENABLE_GCOV)
       add_compile_options("-fprofile-arcs" "-ftest-coverage")
       add_link_options("-lgcov" "--coverage")
endif(ENABLE_GCOV)

file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/arch/${ARCH})

if(ARCH STREQUAL "x86_64")
	set(ARCH_C_FLAGS "-mno-red-zone -mcmodel=kernel")
endif()

set(MCEXEC_PATH "${CMAKE_INSTALL_FULL_BINDIR}/mcexec" CACHE STRING "mcexec path for binfmt")

option(ENABLE_RUST_IHK_MODULE_HELPERS "Enable Rust helpers in IHK Linux modules" ON)
set(MCCTRL_RUST_KBUILD_OBJECTS)
set(MCCTRL_RUST_C_FLAGS)
set(MCCTRL_RUST_DEPENDS)
set(MCCTRL_CORE_SOURCES
	driver.c control.c ikc.c syscall.c procfs.c binfmt_mcexec.c
	sysfs.c sysfs_files.c mc_plist.c futex.c arch/${ARCH}/archdeps.c arch/${ARCH}/cpu.c)

if (ENABLE_RUST_IHK_MODULE_HELPERS AND "${ARCH}" STREQUAL "x86_64")
	find_program(RUSTC rustc)
	if (RUSTC)
		set(MCCTRL_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/mcctrl_helpers.o")
		set(MCCTRL_RUST_CMD "${CMAKE_CURRENT_BINARY_DIR}/rust/.mcctrl_helpers.o.cmd")
		set(MCCTRL_RUST_SRC "${CMAKE_CURRENT_SOURCE_DIR}/rust/mcctrl_helpers.rs")
		add_custom_command(
			OUTPUT "${MCCTRL_RUST_OBJ}" "${MCCTRL_RUST_CMD}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
				--crate-name mcctrl_helpers
				--crate-type lib
				--edition=2021
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C code-model=kernel
				-C relocation-model=static
				-C no-redzone=yes
				-C force-frame-pointers=yes
				-C overflow-checks=off
				-C force-unwind-tables=no
				-C no-vectorize-loops
				-C no-vectorize-slp
				-C target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma
				--emit=obj=${MCCTRL_RUST_OBJ}
				"${MCCTRL_RUST_SRC}"
			COMMAND ${CMAKE_COMMAND}
				-DOBJ_FILE=${MCCTRL_RUST_OBJ}
				-DSRC_FILE=${MCCTRL_RUST_SRC}
				-DCMD_FILE=${MCCTRL_RUST_CMD}
				-DRUSTC=${RUSTC}
				-P ${CMAKE_SOURCE_DIR}/cmake/modules/WriteKbuildPrebuiltCmd.cmake
			DEPENDS "${MCCTRL_RUST_SRC}"
			COMMENT "Building Rust mcctrl helpers"
			VERBATIM
		)
		add_custom_target(mcctrl_rust_helpers
			DEPENDS "${MCCTRL_RUST_OBJ}" "${MCCTRL_RUST_CMD}")
		list(APPEND MCCTRL_RUST_KBUILD_OBJECTS rust/mcctrl_helpers.o)
		list(APPEND MCCTRL_RUST_C_FLAGS -DMCCTRL_RUST_HELPERS)
		list(APPEND MCCTRL_RUST_DEPENDS mcctrl_rust_helpers)
		list(REMOVE_ITEM MCCTRL_CORE_SOURCES binfmt_mcexec.c)
		list(REMOVE_ITEM MCCTRL_CORE_SOURCES ikc.c)
		list(REMOVE_ITEM MCCTRL_CORE_SOURCES mc_plist.c)
		list(REMOVE_ITEM MCCTRL_CORE_SOURCES sysfs_files.c)
		list(REMOVE_ITEM MCCTRL_CORE_SOURCES arch/${ARCH}/cpu.c)
		list(REMOVE_ITEM MCCTRL_CORE_SOURCES arch/${ARCH}/archdeps.c)
	endif()
endif()

kmod(mcctrl
	C_FLAGS
		-I${IHK_FULL_SOURCE_DIR}/linux/include
		-I${IHK_FULL_SOURCE_DIR}/linux/include/ihk/arch/${ARCH}
		-I${IHK_FULL_SOURCE_DIR}/ikc/include
		-I${IHK_FULL_SOURCE_DIR}/ikc/include/ikc/arch/${ARCH}
		-I${IHK_FULL_SOURCE_DIR}/include
		-I${IHK_FULL_SOURCE_DIR}/include/arch/${ARCH}
		-I${PROJECT_SOURCE_DIR}/executer/include
		-I${CMAKE_CURRENT_SOURCE_DIR}/arch/${ARCH}/include
		-I${CMAKE_CURRENT_SOURCE_DIR}/include
		-I${PROJECT_BINARY_DIR}
		-I${PROJECT_SOURCE_DIR}/kernel/include
		-I${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/include
		-DMCEXEC_PATH=\\"${MCEXEC_PATH}\\"
		${ARCH_C_FLAGS}
		${MCCTRL_RUST_C_FLAGS}
	SOURCES
		${MCCTRL_CORE_SOURCES}
	PREBUILT_OBJECTS
		${MCCTRL_RUST_KBUILD_OBJECTS}
	EXTRA_SYMBOLS
		${PROJECT_BINARY_DIR}/ihk/linux/core/Module.symvers
	DEPENDS
		ihk_ko
		${MCCTRL_RUST_DEPENDS}
	INSTALL_DEST
		${KMODDIR}
)
