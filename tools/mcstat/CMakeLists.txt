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
		set(MCSTAT_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/mcstat_helpers.o")
		add_custom_command(
			OUTPUT "${MCSTAT_RUST_OBJ}"
			COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
			COMMAND ${RUSTC}
				--crate-name mcstat_helpers
				--crate-type lib
				--edition=2021
				-C panic=abort
				-C opt-level=2
				-C debuginfo=1
				-C force-unwind-tables=no
				--emit=obj=${MCSTAT_RUST_OBJ}
				"${CMAKE_CURRENT_SOURCE_DIR}/rust/mcstat_helpers.rs"
			DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/mcstat_helpers.rs"
			COMMENT "Building Rust mcstat helpers"
			VERBATIM
		)
		add_custom_target(mcstat_rust_helpers DEPENDS "${MCSTAT_RUST_OBJ}")
		set_source_files_properties("${MCSTAT_RUST_OBJ}"
			PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
		list(APPEND MCSTAT_SRCS "${MCSTAT_RUST_OBJ}")
	endif()
endif()

add_executable(mcstat ${MCSTAT_SRCS})
if (TARGET mcstat_rust_helpers)
	add_dependencies(mcstat mcstat_rust_helpers)
	target_compile_definitions(mcstat PRIVATE MCSTAT_RUST_HELPERS)
endif()
target_link_libraries(mcstat ihklib)

install(TARGETS mcstat
	DESTINATION "${CMAKE_INSTALL_BINDIR}")
