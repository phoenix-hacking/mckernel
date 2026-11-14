# Private M15-P05 proposal only; not applied to executer/user/CMakeLists.txt.
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Install rust/mcps.rs after review, then replace configure_file(mcps.in mcps @ONLY)
# with this block. Remove only the generated "${CMAKE_CURRENT_BINARY_DIR}/mcps"
# entry from install(PROGRAMS), leaving vmcore2mckdump. Add install(TARGETS mcps).
# Root must coordinate this shared file with the BFD-shim selector lane.
if(ENABLE_RUST_USER_TOOLS AND ARCH STREQUAL "x86_64")
  # Original shell expands configured values unquoted. This candidate supports
  # literal install paths and deliberately does not implement shell expansion.
  if("${prefix}" MATCHES "[^A-Za-z0-9_./:+,@%=-]" OR
     "${MCKERNELDIR}" MATCHES "[^A-Za-z0-9_./:+,@%=-]")
    message(FATAL_ERROR "Review mcps shell-to-Rust semantics for nonliteral configured paths")
  endif()
  find_program(RUSTC rustc)
  if(NOT RUSTC)
    message(FATAL_ERROR "Rust mcps requires rustc; no silent shell fallback")
  endif()
  set(MCPS_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/mcps.o")
  add_custom_command(
    OUTPUT "${MCPS_RUST_OBJ}"
    COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_CURRENT_BINARY_DIR}/rust"
    COMMAND ${CMAKE_COMMAND} -E env
      "MCPS_PREFIX=${prefix}" "MCPS_MCKERNELDIR=${MCKERNELDIR}"
      ${RUSTC} --crate-name mcps --crate-type lib --edition=2021
      -C panic=abort -C opt-level=2 -C debuginfo=1 -C relocation-model=pic
      -C force-unwind-tables=no "--emit=obj=${MCPS_RUST_OBJ}"
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/mcps.rs"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/mcps.rs"
    VERBATIM)
  add_custom_target(mcps_rust_main DEPENDS "${MCPS_RUST_OBJ}")
  set_source_files_properties("${MCPS_RUST_OBJ}"
    PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
  add_executable(mcps "${MCPS_RUST_OBJ}")
  add_dependencies(mcps mcps_rust_main mcinspect)
  set_target_properties(mcps PROPERTIES LINKER_LANGUAGE C)
  set_property(TARGET mcps PROPERTY POSITION_INDEPENDENT_CODE ON)
  set_property(TARGET mcps PROPERTY LINK_FLAGS "-fPIE -pie")
  install(TARGETS mcps DESTINATION "${CMAKE_INSTALL_BINDIR}")
else()
  message(FATAL_ERROR "Supported mcps profile requires Rust/x86_64; no shell production successor selected")
endif()
