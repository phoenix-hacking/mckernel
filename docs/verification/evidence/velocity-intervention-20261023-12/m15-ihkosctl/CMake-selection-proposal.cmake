# Private M15-F07 selector proposal only. Root coordinates ihkconfig/libihk
# edits in this shared CMake file; no canonical or IHK gitlink change here.
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Place ihkosctl.rs/build_ihkosctl.py under ihk/linux/user/rust after qualification.
# Replace only add_executable(ihkosctl ihkosctl.c); retain existing PIC/link/install.
option(ENABLE_RUST_USER_TOOLS "Enable Rust helpers in McKernel user tools" ON)
option(IHK_ALLOW_CLI_C_FALLBACK "Allow explicit C reference CLI for comparison only" OFF)
if(ENABLE_RUST_USER_TOOLS AND ARCH STREQUAL "x86_64")
  find_program(RUSTC rustc)
  if(NOT RUSTC)
    message(FATAL_ERROR "Rust ihkosctl requires rustc; no silent production C fallback")
  endif()
  find_package(PythonInterp 3 REQUIRED)
  set(IHKOSCTL_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/ihkosctl.o")
  add_custom_command(
    OUTPUT "${IHKOSCTL_RUST_OBJ}"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
    COMMAND ${PYTHON_EXECUTABLE}
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/build_ihkosctl.py"
      --rustc "${RUSTC}"
      --source "${CMAKE_CURRENT_SOURCE_DIR}/rust/ihkosctl.rs"
      --output "${IHKOSCTL_RUST_OBJ}"
      --config "${PROJECT_BINARY_DIR}/config.h"
    DEPENDS
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/ihkosctl.rs"
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/build_ihkosctl.py"
      "${PROJECT_BINARY_DIR}/config.h"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihklib.h"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihklib_private.h"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihk_host_user.h"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihk_debug.h"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihk_rusage.h"
    VERBATIM)
  add_custom_target(ihkosctl_rust_main DEPENDS "${IHKOSCTL_RUST_OBJ}")
  set_source_files_properties("${IHKOSCTL_RUST_OBJ}"
    PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
  add_executable(ihkosctl "${IHKOSCTL_RUST_OBJ}")
  add_dependencies(ihkosctl ihkosctl_rust_main)
  set_target_properties(ihkosctl PROPERTIES LINKER_LANGUAGE C)
elseif(IHK_ALLOW_CLI_C_FALLBACK)
  add_executable(ihkosctl ihkosctl.c)
else()
  message(FATAL_ERROR "Supported ihkosctl requires Rust/x86_64; explicit reference fallback only")
endif()
