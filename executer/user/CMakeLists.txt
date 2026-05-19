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
			COMMAND ${RUSTC}
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

add_executable(mcinspect mcinspect.c)
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

add_executable(eclair eclair.c arch/${ARCH}/arch-eclair.c)
target_link_libraries(eclair ${LIBBFD})
set_property(TARGET eclair PROPERTY POSITION_INDEPENDENT_CODE ON)
set_property(TARGET eclair PROPERTY LINK_FLAGS "-fPIE -pie")

add_library(sched_yield SHARED libsched_yield.c)
target_link_libraries(sched_yield dl)
set_property(TARGET sched_yield PROPERTY VERSION 1.0.0)

if (ENABLE_QLMPI)
	target_link_libraries(mcexec ${MPI_C_LIBRARIES})
	target_include_directories(mcexec PRIVATE ${MPI_INCLUDE_PATH})

	add_library(qlmpi qlmpilib.c)
	target_link_libraries(qlmpi ${MPI_C_LIBRARIES})
	target_include_directories(qlmpi PRIVATE ${MPI_INCLUDE_PATH})

	add_library(qlfort libqlfort.c)
	target_link_libraries(qlfort dl ${MPI_C_LIBRARIES})
	target_include_directories(qlfort PRIVATE ${MPI_INCLUDE_PATH})

	add_executable(ql_server ql_server.c)
	add_executable(ql_talker ql_talker.c)

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

	add_library(mck_syscall_intercept SHARED syscall_intercept.c arch/${ARCH}/archdep_c.c)

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

add_library(ldump2mcdump SHARED ldump2mcdump.c)
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
