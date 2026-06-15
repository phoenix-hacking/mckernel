include_directories(
	"${CMAKE_CURRENT_BINARY_DIR}"
	"${PROJECT_BINARY_DIR}"
	"${IHK_FULL_SOURCE_DIR}/linux/include"
	"${CMAKE_CURRENT_SOURCE_DIR}/arch/${ARCH}/include"
	"${CMAKE_CURRENT_SOURCE_DIR}"
	"${CMAKE_CURRENT_SOURCE_DIR}/arch/${ARCH}"
	"${PROJECT_BINARY_DIR}/ihk/linux/include"
)
include(CheckCSourceCompiles)

set(_executer_saved_required_libraries "${CMAKE_REQUIRED_LIBRARIES}")
set(CMAKE_REQUIRED_LIBRARIES ${LIBBFD} ${CMAKE_REQUIRED_LIBRARIES})
check_c_source_compiles("
#include <bfd.h>
int main(void)
{
	bfd *abfd = 0;
	asection *scn = 0;

	return bfd_set_section_size(abfd, scn, 0) ? 0 : 1;
}
" EXECUTER_BFD_SET_SECTION_NEEDS_BFD)
set(CMAKE_REQUIRED_LIBRARIES "${_executer_saved_required_libraries}")

add_subdirectory(lib)
add_library(libmcexec STATIC arch/${ARCH}/archdep.S)
SET_TARGET_PROPERTIES(libmcexec PROPERTIES OUTPUT_NAME mcexec)
set_property(TARGET libmcexec PROPERTY POSITION_INDEPENDENT_CODE ON)

option(ENABLE_RUST_USER_TOOLS "Enable Rust helpers in McKernel user tools" ON)

set(MCEXEC_SRCS mcexec.c)
if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
	find_program(RUSTC rustc)
	if (RUSTC)
		set(MCEXEC_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/mcexec_helpers.o")
		add_custom_command(
			OUTPUT "${MCEXEC_RUST_OBJ}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
				--crate-name mcexec_helpers
				--crate-type lib
				--edition=2021
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C force-unwind-tables=no
				--emit=obj=${MCEXEC_RUST_OBJ}
				"${CMAKE_CURRENT_SOURCE_DIR}/rust/mcexec_helpers.rs"
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/mcexec_helpers.rs"
			COMMENT "Building Rust mcexec helpers"
			VERBATIM
		)
		add_custom_target(mcexec_rust_helpers DEPENDS "${MCEXEC_RUST_OBJ}")
		set_source_files_properties("${MCEXEC_RUST_OBJ}"
			PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
		list(APPEND MCEXEC_SRCS "${MCEXEC_RUST_OBJ}")
	endif()
endif()

add_executable(mcexec ${MCEXEC_SRCS})
if (TARGET mcexec_rust_helpers)
	add_dependencies(mcexec mcexec_rust_helpers)
	target_compile_definitions(mcexec PRIVATE MCEXEC_RUST_HELPERS)
endif()
target_link_libraries(mcexec
	libmcexec ${LIBRT} ${LIBNUMA} $<$<BOOL:ENABLE_QLMPI>:${LIBMPI}> pthread)
target_include_directories(mcexec PUBLIC "${KERNEL_DIR}")
set_property(TARGET mcexec PROPERTY POSITION_INDEPENDENT_CODE ON)
set_property(TARGET mcexec PROPERTY LINK_FLAGS "-fPIE -pie")

set(MCINSPECT_SRCS mcinspect.c)
if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
	find_program(RUSTC rustc)
	if (RUSTC)
		set(MCINSPECT_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/mcinspect_helpers.o")
		add_custom_command(
			OUTPUT "${MCINSPECT_RUST_OBJ}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
				--crate-name mcinspect_helpers
				--crate-type lib
				--edition=2021
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C force-unwind-tables=no
				--emit=obj=${MCINSPECT_RUST_OBJ}
				"${CMAKE_CURRENT_SOURCE_DIR}/rust/mcinspect_helpers.rs"
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/mcinspect_helpers.rs"
			COMMENT "Building Rust mcinspect helpers"
			VERBATIM
		)
		add_custom_target(mcinspect_rust_helpers DEPENDS "${MCINSPECT_RUST_OBJ}")
		set_source_files_properties("${MCINSPECT_RUST_OBJ}"
			PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
		list(APPEND MCINSPECT_SRCS "${MCINSPECT_RUST_OBJ}")
	endif()
endif()

add_executable(mcinspect ${MCINSPECT_SRCS})
if (TARGET mcinspect_rust_helpers)
	add_dependencies(mcinspect mcinspect_rust_helpers)
	target_compile_definitions(mcinspect PRIVATE MCINSPECT_RUST_HELPERS)
endif()
if (NOT LIBDWARF)
	target_include_directories(mcinspect PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/lib/")
	target_include_directories(mcinspect PRIVATE
		"${CMAKE_CURRENT_SOURCE_DIR}/lib/libdwarf/libdwarf/libdwarf/")
	target_link_libraries(mcinspect dwarf z elf)
else()
	target_include_directories(mcinspect PRIVATE ${DWARF_H})
	target_link_libraries(mcinspect ${LIBDWARF})
endif()
target_link_libraries(mcinspect ${LIBBFD})
set_property(TARGET mcinspect PROPERTY POSITION_INDEPENDENT_CODE ON)
set_property(TARGET mcinspect PROPERTY LINK_FLAGS "-fPIE -pie")

set(ECLAIR_SRCS eclair.c arch/${ARCH}/arch-eclair.c)
if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
	find_program(RUSTC rustc)
	if (RUSTC)
		set(ECLAIR_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/eclair_helpers.o")
		set(ECLAIR_ARCH_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/arch_eclair_x86_64.o")
		add_custom_command(
			OUTPUT "${ECLAIR_RUST_OBJ}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
				--crate-name eclair_helpers
				--crate-type lib
				--edition=2021
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C force-unwind-tables=no
				--emit=obj=${ECLAIR_RUST_OBJ}
				"${CMAKE_CURRENT_SOURCE_DIR}/rust/eclair_helpers.rs"
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/eclair_helpers.rs"
			COMMENT "Building Rust eclair helpers"
			VERBATIM
		)
		add_custom_command(
			OUTPUT "${ECLAIR_ARCH_RUST_OBJ}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
				--crate-name arch_eclair_x86_64
				--crate-type lib
				--edition=2021
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C force-unwind-tables=no
				--emit=obj=${ECLAIR_ARCH_RUST_OBJ}
				"${CMAKE_CURRENT_SOURCE_DIR}/rust/arch_eclair_x86_64.rs"
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/arch_eclair_x86_64.rs"
			COMMENT "Building Rust x86_64 eclair arch glue"
			VERBATIM
		)
		add_custom_target(eclair_rust_helpers DEPENDS "${ECLAIR_RUST_OBJ}")
		add_custom_target(eclair_arch_rust DEPENDS "${ECLAIR_ARCH_RUST_OBJ}")
		set_source_files_properties("${ECLAIR_RUST_OBJ}"
			PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
		set_source_files_properties("${ECLAIR_ARCH_RUST_OBJ}"
			PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
		list(REMOVE_ITEM ECLAIR_SRCS arch/${ARCH}/arch-eclair.c)
		list(APPEND ECLAIR_SRCS "${ECLAIR_RUST_OBJ}")
		list(APPEND ECLAIR_SRCS "${ECLAIR_ARCH_RUST_OBJ}")
	endif()
endif()

add_executable(eclair ${ECLAIR_SRCS})
if (TARGET eclair_rust_helpers)
	add_dependencies(eclair eclair_rust_helpers)
	target_compile_definitions(eclair PRIVATE ECLAIR_RUST_HELPERS)
endif()
if (TARGET eclair_arch_rust)
	add_dependencies(eclair eclair_arch_rust)
endif()
target_link_libraries(eclair ${LIBBFD})
set_property(TARGET eclair PROPERTY POSITION_INDEPENDENT_CODE ON)
set_property(TARGET eclair PROPERTY LINK_FLAGS "-fPIE -pie")

set(SCHED_YIELD_SRCS libsched_yield.c)
if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
	find_program(RUSTC rustc)
	if (RUSTC)
		set(SCHED_YIELD_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/libsched_yield.o")
		add_custom_command(
			OUTPUT "${SCHED_YIELD_RUST_OBJ}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
				--crate-name libsched_yield
				--crate-type lib
				--edition=2021
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C relocation-model=pic
				-C force-unwind-tables=no
				--emit=obj=${SCHED_YIELD_RUST_OBJ}
				"${CMAKE_CURRENT_SOURCE_DIR}/rust/libsched_yield.rs"
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/libsched_yield.rs"
			COMMENT "Building Rust sched_yield interposer"
			VERBATIM
		)
		add_custom_target(sched_yield_rust_main DEPENDS "${SCHED_YIELD_RUST_OBJ}")
		set_source_files_properties("${SCHED_YIELD_RUST_OBJ}"
			PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
		set(SCHED_YIELD_SRCS "${SCHED_YIELD_RUST_OBJ}")
	endif()
endif()

add_library(sched_yield SHARED ${SCHED_YIELD_SRCS})
if (TARGET sched_yield_rust_main)
	add_dependencies(sched_yield sched_yield_rust_main)
	set_target_properties(sched_yield PROPERTIES LINKER_LANGUAGE C)
endif()
target_link_libraries(sched_yield dl)
set_property(TARGET sched_yield PROPERTY VERSION 1.0.0)

if (ENABLE_QLMPI)
	target_link_libraries(mcexec ${MPI_C_LIBRARIES})
	target_include_directories(mcexec PRIVATE ${MPI_INCLUDE_PATH})

	set(QLMPI_SRCS qlmpilib.c)
	if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
		find_program(RUSTC rustc)
		if (RUSTC)
			set(QLMPI_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/qlmpilib.o")
			add_custom_command(
				OUTPUT "${QLMPI_RUST_OBJ}"
				COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
				COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
					--crate-name qlmpilib
					--crate-type lib
					--edition=2021
					-C panic=abort
					-C opt-level=2
					-C debuginfo=1
					-C relocation-model=pic
					-C force-unwind-tables=no
					--emit=obj=${QLMPI_RUST_OBJ}
					"${CMAKE_CURRENT_SOURCE_DIR}/rust/qlmpilib.rs"
				DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/qlmpilib.rs"
				COMMENT "Building Rust qlmpi library body"
				VERBATIM
			)
			add_custom_target(qlmpi_rust_main DEPENDS "${QLMPI_RUST_OBJ}")
			set_source_files_properties("${QLMPI_RUST_OBJ}"
				PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
			set(QLMPI_SRCS "${QLMPI_RUST_OBJ}" qlmpi_mpi_abi.c)
		endif()
	endif()
	add_library(qlmpi ${QLMPI_SRCS})
	if (TARGET qlmpi_rust_main)
		add_dependencies(qlmpi qlmpi_rust_main)
		set_target_properties(qlmpi PROPERTIES LINKER_LANGUAGE C)
	endif()
	target_link_libraries(qlmpi ${MPI_C_LIBRARIES})
	target_include_directories(qlmpi PRIVATE ${MPI_INCLUDE_PATH})

	set(QLFORT_SRCS libqlfort.c)
	if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
		find_program(RUSTC rustc)
		if (RUSTC)
			set(QLFORT_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/qlfort.o")
			add_custom_command(
				OUTPUT "${QLFORT_RUST_OBJ}"
				COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
				COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
					--crate-name qlfort
					--crate-type lib
					--edition=2021
					-C panic=abort
					-C opt-level=2
					-C debuginfo=1
					-C relocation-model=pic
					-C force-unwind-tables=no
					--emit=obj=${QLFORT_RUST_OBJ}
					"${CMAKE_CURRENT_SOURCE_DIR}/rust/qlfort.rs"
				DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/qlfort.rs"
				COMMENT "Building Rust qlfort interposer"
				VERBATIM
			)
			add_custom_target(qlfort_rust_main DEPENDS "${QLFORT_RUST_OBJ}")
			set_source_files_properties("${QLFORT_RUST_OBJ}"
				PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
			set(QLFORT_SRCS "${QLFORT_RUST_OBJ}")
		endif()
	endif()
	add_library(qlfort ${QLFORT_SRCS})
	if (TARGET qlfort_rust_main)
		add_dependencies(qlfort qlfort_rust_main)
		set_target_properties(qlfort PROPERTIES LINKER_LANGUAGE C)
	endif()
	target_link_libraries(qlfort dl ${MPI_C_LIBRARIES})
	target_include_directories(qlfort PRIVATE ${MPI_INCLUDE_PATH})

	set(QL_SERVER_SRCS ql_server.c)
	if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
		find_program(RUSTC rustc)
		if (RUSTC)
			set(QL_SERVER_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/ql_server.o")
			add_custom_command(
				OUTPUT "${QL_SERVER_RUST_OBJ}"
				COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
				COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
					--crate-name ql_server
					--crate-type lib
					--edition=2021
					-C panic=abort
					-C opt-level=2
					-C debuginfo=1
					-C force-unwind-tables=no
					--emit=obj=${QL_SERVER_RUST_OBJ}
					"${CMAKE_CURRENT_SOURCE_DIR}/rust/ql_server.rs"
				DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/ql_server.rs"
				COMMENT "Building Rust ql_server"
				VERBATIM
			)
			add_custom_target(ql_server_rust_main DEPENDS "${QL_SERVER_RUST_OBJ}")
			set_source_files_properties("${QL_SERVER_RUST_OBJ}"
				PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
			set(QL_SERVER_SRCS "${QL_SERVER_RUST_OBJ}")
		endif()
	endif()
	add_executable(ql_server ${QL_SERVER_SRCS})
	if (TARGET ql_server_rust_main)
		add_dependencies(ql_server ql_server_rust_main)
		set_target_properties(ql_server PROPERTIES LINKER_LANGUAGE C)
	endif()
	set(QL_TALKER_SRCS ql_talker.c)
	if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
		find_program(RUSTC rustc)
		if (RUSTC)
			set(QL_TALKER_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/ql_talker.o")
			add_custom_command(
				OUTPUT "${QL_TALKER_RUST_OBJ}"
				COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
				COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
					--crate-name ql_talker
					--crate-type lib
					--edition=2021
					-C panic=abort
					-C opt-level=2
					-C debuginfo=1
					-C force-unwind-tables=no
					--emit=obj=${QL_TALKER_RUST_OBJ}
					"${CMAKE_CURRENT_SOURCE_DIR}/rust/ql_talker.rs"
				DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/ql_talker.rs"
				COMMENT "Building Rust ql_talker"
				VERBATIM
			)
			add_custom_target(ql_talker_rust_main DEPENDS "${QL_TALKER_RUST_OBJ}")
			set_source_files_properties("${QL_TALKER_RUST_OBJ}"
				PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
			set(QL_TALKER_SRCS "${QL_TALKER_RUST_OBJ}")
		endif()
	endif()
	add_executable(ql_talker ${QL_TALKER_SRCS})
	if (TARGET ql_talker_rust_main)
		add_dependencies(ql_talker ql_talker_rust_main)
		set_target_properties(ql_talker PROPERTIES LINKER_LANGUAGE C)
	endif()

	add_executable(ql_mpiexec_start ql_mpiexec_start.c md5.c)
	target_link_libraries(ql_mpiexec_start pthread)

	add_executable(ql_mpiexec_finalize ql_mpiexec_start.c md5.c)
	set_target_properties(ql_mpiexec_finalize PROPERTIES COMPILE_DEFINITIONS
		QL_MPIEXEC_FINALIZE)
	target_link_libraries(ql_mpiexec_finalize pthread)

	install(TARGETS ql_server ql_talker ql_mpiexec_start ql_mpiexec_finalize
		DESTINATION "${CMAKE_INSTALL_BINDIR}")
	install(TARGETS qlmpi qlfort
		DESTINATION "${CMAKE_INSTALL_LIBDIR}")
endif()

if (ENABLE_UTI)
	link_directories("${CMAKE_CURRENT_BINARY_DIR}/lib/syscall_intercept")

	set(MCK_SYSCALL_INTERCEPT_SRCS syscall_intercept.c arch/${ARCH}/archdep_c.c)
	if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
		find_program(RUSTC rustc)
		if (RUSTC)
			set(SYSCALL_INTERCEPT_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/syscall_intercept.o")
			set(UTI_ARCH_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/archdep_uti_x86_64.o")
			add_custom_command(
				OUTPUT "${SYSCALL_INTERCEPT_RUST_OBJ}"
				COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
				COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
					--crate-name syscall_intercept
					--crate-type lib
					--edition=2021
					-C panic=abort
					-C opt-level=2
					-C debuginfo=1
					-C relocation-model=pic
					-C force-unwind-tables=no
					--emit=obj=${SYSCALL_INTERCEPT_RUST_OBJ}
					"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_intercept.rs"
				DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_intercept.rs"
				COMMENT "Building Rust UTI syscall intercept hook"
				VERBATIM
			)
			add_custom_command(
				OUTPUT "${UTI_ARCH_RUST_OBJ}"
				COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
				COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
					--crate-name archdep_uti_x86_64
					--crate-type lib
					--edition=2021
					-C panic=abort
					-C opt-level=2
					-C debuginfo=1
					-C relocation-model=pic
					-C force-unwind-tables=no
					--emit=obj=${UTI_ARCH_RUST_OBJ}
					"${CMAKE_CURRENT_SOURCE_DIR}/rust/archdep_uti_x86_64.rs"
				DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/archdep_uti_x86_64.rs"
				COMMENT "Building Rust x86_64 UTI syscall wrappers"
				VERBATIM
			)
			add_custom_target(syscall_intercept_rust_main DEPENDS "${SYSCALL_INTERCEPT_RUST_OBJ}")
			add_custom_target(uti_arch_rust DEPENDS "${UTI_ARCH_RUST_OBJ}")
			set_source_files_properties("${SYSCALL_INTERCEPT_RUST_OBJ}"
				PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
			set_source_files_properties("${UTI_ARCH_RUST_OBJ}"
				PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
			list(REMOVE_ITEM MCK_SYSCALL_INTERCEPT_SRCS syscall_intercept.c)
			list(REMOVE_ITEM MCK_SYSCALL_INTERCEPT_SRCS arch/${ARCH}/archdep_c.c)
			list(APPEND MCK_SYSCALL_INTERCEPT_SRCS "${SYSCALL_INTERCEPT_RUST_OBJ}")
			list(APPEND MCK_SYSCALL_INTERCEPT_SRCS "${UTI_ARCH_RUST_OBJ}")
		endif()
	endif()

	add_library(mck_syscall_intercept SHARED ${MCK_SYSCALL_INTERCEPT_SRCS})
	if (TARGET syscall_intercept_rust_main)
		add_dependencies(mck_syscall_intercept syscall_intercept_rust_main)
		set_target_properties(mck_syscall_intercept PROPERTIES LINKER_LANGUAGE C)
	endif()
	if (TARGET uti_arch_rust)
		add_dependencies(mck_syscall_intercept uti_arch_rust)
	endif()

	# target name is defined by add_library(), not project() or add_subdirectory()
	add_dependencies(mck_syscall_intercept syscall_intercept_shared)
	if (${ARCH} STREQUAL "arm64")
		set_source_files_properties(syscall_intercept.c PROPERTIES COMPILE_FLAGS -mgeneral-regs-only)
	endif()
	target_link_libraries(mck_syscall_intercept syscall_intercept)
	target_include_directories(mck_syscall_intercept PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/lib/syscall_intercept/include)
	set_target_properties(mck_syscall_intercept PROPERTIES INSTALL_RPATH ${CMAKE_INSTALL_PREFIX}/lib64)

	install(TARGETS mck_syscall_intercept
		DESTINATION "${CMAKE_INSTALL_LIBDIR}")
endif()

set(LDUMP2MCDUMP_SRCS ldump2mcdump.c)
if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
	find_program(RUSTC rustc)
	if (RUSTC)
		set(LDUMP2MCDUMP_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/ldump2mcdump_helpers.o")
		add_custom_command(
			OUTPUT "${LDUMP2MCDUMP_RUST_OBJ}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
				--crate-name ldump2mcdump_helpers
				--crate-type lib
				--edition=2021
				--cfg ldump2_full_body
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C relocation-model=pic
				-C force-unwind-tables=no
				--emit=obj=${LDUMP2MCDUMP_RUST_OBJ}
				"${CMAKE_CURRENT_SOURCE_DIR}/rust/ldump2mcdump_helpers.rs"
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/ldump2mcdump_helpers.rs"
			COMMENT "Building Rust ldump2mcdump helpers"
			VERBATIM
		)
		add_custom_target(ldump2mcdump_rust_helpers DEPENDS "${LDUMP2MCDUMP_RUST_OBJ}")
		set_source_files_properties("${LDUMP2MCDUMP_RUST_OBJ}"
			PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
		set(LDUMP2MCDUMP_SRCS "${LDUMP2MCDUMP_RUST_OBJ}")
	endif()
endif()

add_library(ldump2mcdump SHARED ${LDUMP2MCDUMP_SRCS})
if (TARGET ldump2mcdump_rust_helpers)
	add_dependencies(ldump2mcdump ldump2mcdump_rust_helpers)
	set_target_properties(ldump2mcdump PROPERTIES LINKER_LANGUAGE C)
endif()
if(EXECUTER_BFD_SET_SECTION_NEEDS_BFD)
	target_compile_definitions(ldump2mcdump PRIVATE -DEXECUTER_BFD_SET_SECTION_NEEDS_BFD)
endif()

configure_file(vmcore2mckdump.in vmcore2mckdump @ONLY)

configure_file(mcexec.1in mcexec.1 @ONLY)
configure_file(mcps.in mcps @ONLY)

install(TARGETS mcexec eclair mcinspect
	DESTINATION "${CMAKE_INSTALL_BINDIR}")
install(PROGRAMS
	"${CMAKE_CURRENT_BINARY_DIR}/vmcore2mckdump"
	"${CMAKE_CURRENT_BINARY_DIR}/mcps"
	DESTINATION "${CMAKE_INSTALL_BINDIR}")
install(TARGETS sched_yield ldump2mcdump
	DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(FILES "${IHK_FULL_SOURCE_DIR}/linux/include/ihk/ihk_rusage.h"
	DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/ihk")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/mcexec.1"
	DESTINATION "${CMAKE_INSTALL_MANDIR}/man1")
