# Private integration proposal only; no canonical changes.
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Apply only after root adopts and verifies the matched converter-ack.patch.
# Existing unmodified converter has NO acknowledgment: this wrapper must not be
# published against it as a working production successor.
# Replace configure_file(vmcore2mckdump.in vmcore2mckdump @ONLY) with this block.
# Existing install(PROGRAMS "${CMAKE_CURRENT_BINARY_DIR}/vmcore2mckdump" ...)
# can keep that exact output path; coordinate its list with the mcps selector.
if(ENABLE_RUST_USER_TOOLS AND CMAKE_SYSTEM_NAME STREQUAL "Linux")
  find_program(RUSTC rustc)
  if(NOT RUSTC)
    message(FATAL_ERROR "Rust vmcore2mckdump requires rustc; no silent shell/Expect fallback")
  endif()
  set(VMCORE2MCKDUMP_RUST_BIN "${CMAKE_CURRENT_BINARY_DIR}/vmcore2mckdump")
  add_custom_command(
    OUTPUT "${VMCORE2MCKDUMP_RUST_BIN}"
    COMMAND ${CMAKE_COMMAND} -E env
      "VMCORE_INSTALLDIR=${prefix}"
      "VMCORE_ARCH=${ARCH}"
      "VMCORE_CRASH=/usr/bin/crash"
      "VMCORE_PROMPT_TIMEOUT_MS=300000"
      ${RUSTC} --edition=2021 -C opt-level=2 -C debuginfo=1
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/vmcore2mckdump.rs"
      -o "${VMCORE2MCKDUMP_RUST_BIN}"
    DEPENDS
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/vmcore2mckdump.rs"
      "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt"
      "${PROJECT_BINARY_DIR}/CMakeCache.txt"
    VERBATIM)
  add_custom_target(vmcore2mckdump_rust ALL DEPENDS "${VMCORE2MCKDUMP_RUST_BIN}")
  add_dependencies(vmcore2mckdump_rust ldump2mcdump)
else()
  message(FATAL_ERROR "Supported vmcore2mckdump successor requires Rust/Linux")
endif()
# Before acceptance leave the original configured script/source/install selector
# unchanged. Retain vmcore2mckdump.in as a comparison reference after cutover.
