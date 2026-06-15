include_directories(
	"${CMAKE_CURRENT_BINARY_DIR}"
	"${PROJECT_BINARY_DIR}"
	"${IHK_FULL_SOURCE_DIR}/linux/include"
	"${CMAKE_CURRENT_SOURCE_DIR}/../../executer/include"
	"${CMAKE_CURRENT_SOURCE_DIR}"
)

option(ENABLE_RUST_USER_TOOLS "Enable Rust helpers in McKernel user tools" ON)

set(MCSTAT_SRCS mcstat.c)
if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
	find_program(RUSTC rustc)
	if (RUSTC)
		set(MCSTAT_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/mcstat.o")
		add_custom_command(
			OUTPUT "${MCSTAT_RUST_OBJ}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
				--crate-name mcstat
				--crate-type lib
				--edition=2021
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C force-unwind-tables=no
				--emit=obj=${MCSTAT_RUST_OBJ}
				"${CMAKE_CURRENT_SOURCE_DIR}/rust/mcstat.rs"
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/mcstat.rs"
			COMMENT "Building Rust mcstat"
			VERBATIM
		)
		add_custom_target(mcstat_rust_main DEPENDS "${MCSTAT_RUST_OBJ}")
		set_source_files_properties("${MCSTAT_RUST_OBJ}"
			PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
		set(MCSTAT_SRCS "${MCSTAT_RUST_OBJ}")
	endif()
endif()

add_executable(mcstat ${MCSTAT_SRCS})
if (TARGET mcstat_rust_main)
	add_dependencies(mcstat mcstat_rust_main)
	set_target_properties(mcstat PROPERTIES LINKER_LANGUAGE C)
endif()
target_link_libraries(mcstat ihklib)

set(MCSTAT_RUNTEST_SRCS runtest.c)
if (ENABLE_RUST_USER_TOOLS AND "${ARCH}" STREQUAL "x86_64")
	find_program(RUSTC rustc)
	if (RUSTC)
		set(MCSTAT_RUNTEST_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/runtest.o")
		add_custom_command(
			OUTPUT "${MCSTAT_RUNTEST_RUST_OBJ}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${RUSTC}
				--crate-name mcstat_runtest
				--crate-type lib
				--edition=2021
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C force-unwind-tables=no
				--emit=obj=${MCSTAT_RUNTEST_RUST_OBJ}
				"${CMAKE_CURRENT_SOURCE_DIR}/rust/runtest.rs"
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/runtest.rs"
			COMMENT "Building Rust mcstat runtest"
			VERBATIM
		)
		add_custom_target(mcstat_runtest_rust_main
			DEPENDS "${MCSTAT_RUNTEST_RUST_OBJ}")
		set_source_files_properties("${MCSTAT_RUNTEST_RUST_OBJ}"
			PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
		set(MCSTAT_RUNTEST_SRCS "${MCSTAT_RUNTEST_RUST_OBJ}")
	endif()
endif()

add_executable(mcstat_runtest EXCLUDE_FROM_ALL ${MCSTAT_RUNTEST_SRCS})
if (TARGET mcstat_runtest_rust_main)
	add_dependencies(mcstat_runtest mcstat_runtest_rust_main)
	set_target_properties(mcstat_runtest PROPERTIES LINKER_LANGUAGE C)
endif()

install(TARGETS mcstat
	DESTINATION "${CMAKE_INSTALL_BINDIR}")
