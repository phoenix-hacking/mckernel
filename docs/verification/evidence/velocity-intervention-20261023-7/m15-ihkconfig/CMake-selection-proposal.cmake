# Private CMake insertion proposal ONLY. Not applied to canonical IHK.
# Place ihkconfig.rs and build_ihkconfig.py in ihk/linux/user/rust/ after review.
# Replace only add_executable(ihkconfig ihkconfig.c); keep existing target
# PIC/link/install properties and libraries after this block unchanged.
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
option(ENABLE_RUST_USER_TOOLS "Enable Rust helpers in McKernel user tools" ON)
option(IHK_ALLOW_CLI_C_FALLBACK "Allow explicit C reference CLI for comparison only" OFF)
if(ENABLE_RUST_USER_TOOLS AND ARCH STREQUAL "x86_64")
  find_program(RUSTC rustc)
  if(NOT RUSTC)
    message(FATAL_ERROR "Rust ihkconfig requires rustc; no silent production C fallback")
  endif()
  find_package(PythonInterp 3 REQUIRED)
  set(IHKCONFIG_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/ihkconfig.o")
  add_custom_command(
    OUTPUT "${IHKCONFIG_RUST_OBJ}"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
    COMMAND ${PYTHON_EXECUTABLE}
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/build_ihkconfig.py"
      --rustc "${RUSTC}"
      --source "${CMAKE_CURRENT_SOURCE_DIR}/rust/ihkconfig.rs"
      --output "${IHKCONFIG_RUST_OBJ}"
      --config "${PROJECT_BINARY_DIR}/config.h"
      --krm "$<BOOL:${ENABLE_KRM_WORKAROUND}>"
    DEPENDS
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/ihkconfig.rs"
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/build_ihkconfig.py"
      "${PROJECT_BINARY_DIR}/config.h"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihk_host_user.h"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihklib.h"
    VERBATIM)
  add_custom_target(ihkconfig_rust_main DEPENDS "${IHKCONFIG_RUST_OBJ}")
  set_source_files_properties("${IHKCONFIG_RUST_OBJ}"
    PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
  add_executable(ihkconfig "${IHKCONFIG_RUST_OBJ}")
  add_dependencies(ihkconfig ihkconfig_rust_main)
  set_target_properties(ihkconfig PROPERTIES LINKER_LANGUAGE C)
elseif(IHK_ALLOW_CLI_C_FALLBACK)
  add_executable(ihkconfig ihkconfig.c)
else()
  message(FATAL_ERROR "This supported ihkconfig profile requires Rust/x86_64; C reference fallback must be explicit")
endif()
