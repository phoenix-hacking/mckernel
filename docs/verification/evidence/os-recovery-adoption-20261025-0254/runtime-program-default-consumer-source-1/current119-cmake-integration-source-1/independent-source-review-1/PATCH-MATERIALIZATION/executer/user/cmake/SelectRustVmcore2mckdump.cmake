# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Reuses the existing private wrapper; current script remains selected until joint ACK qualification.
option(ENABLE_RUST_VMCORE2MCKDUMP "Select the jointly qualified Rust vmcore wrapper/converter contract" OFF)
if(ENABLE_RUST_VMCORE2MCKDUMP)
  if(NOT ENABLE_RUST_USER_TOOLS OR NOT CMAKE_SYSTEM_NAME STREQUAL "Linux" OR NOT ARCH STREQUAL "x86_64" OR NOT TARGET ldump2mcdump_rust_helpers)
    message(FATAL_ERROR "Rust vmcore wrapper requires the actual Linux/x86_64 Rust ldump2mcdump producer")
  endif()
  # Source presence is necessary; source/fixture/SDK/native acceptance is a separate root decision.
  file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/rust/ldump2mcdump_helpers.rs" _vmcore_ack_source_sha256)
  if(NOT _vmcore_ack_source_sha256 STREQUAL "5205663e825abfb26d8eb0e01c225c1eb7cecd95051832b7234890dba5f3de78")
    message(FATAL_ERROR "Rust vmcore wrapper requires the exact jointly reviewed ACK producer; current unmodified converter is incompatible")
  endif()
  set(MCKERNEL_RUNTIME_TOOL_RUSTC "" CACHE FILEPATH "Pinned runtime tool compiler; independent of compute RUSTC")
  if(NOT IS_ABSOLUTE "${MCKERNEL_RUNTIME_TOOL_RUSTC}" OR NOT EXISTS "${MCKERNEL_RUNTIME_TOOL_RUSTC}")
    message(FATAL_ERROR "Rust vmcore wrapper requires the absolute pinned MCKERNEL_RUNTIME_TOOL_RUSTC")
  endif()
  set(VMCORE2MCKDUMP_RUST_BIN "${CMAKE_CURRENT_BINARY_DIR}/vmcore2mckdump")
  add_custom_command(
    OUTPUT "${VMCORE2MCKDUMP_RUST_BIN}"
    COMMAND ${CMAKE_COMMAND} -E env
      "VMCORE_INSTALLDIR=${prefix}" "VMCORE_ARCH=${ARCH}"
      "VMCORE_CRASH=/usr/bin/crash" "VMCORE_PROMPT_TIMEOUT_MS=300000"
      "${MCKERNEL_RUNTIME_TOOL_RUSTC}" --edition=2021 -C opt-level=2 -C debuginfo=1
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/vmcore2mckdump.rs" -o "${VMCORE2MCKDUMP_RUST_BIN}"
    DEPENDS "${MCKERNEL_RUNTIME_TOOL_RUSTC}" "${CMAKE_CURRENT_SOURCE_DIR}/rust/vmcore2mckdump.rs"
      "${CMAKE_CURRENT_SOURCE_DIR}/cmake/SelectRustVmcore2mckdump.cmake"
      "${PROJECT_BINARY_DIR}/CMakeCache.txt"
    VERBATIM)
  add_custom_target(vmcore2mckdump_rust ALL DEPENDS "${VMCORE2MCKDUMP_RUST_BIN}")
  add_dependencies(vmcore2mckdump_rust ldump2mcdump)
else()
  configure_file(vmcore2mckdump.in vmcore2mckdump @ONLY)
endif()
