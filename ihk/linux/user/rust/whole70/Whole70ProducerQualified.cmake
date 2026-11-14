# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Real selected headers -> four generated RS files + actual stat cfg -> one Rust archive.
# Nonshipped C metadata witnesses never provide a production library symbol.
find_package(PythonInterp 3 REQUIRED)
if(NOT IHK_USER_RUSTC OR NOT IS_ABSOLUTE "${IHK_USER_RUSTC}"
   OR NOT EXISTS "${IHK_USER_RUSTC}" OR IS_DIRECTORY "${IHK_USER_RUSTC}")
  message(FATAL_ERROR "Set IHK_USER_RUSTC to the existing pinned supported user compiler file; preserve compute RUSTC")
endif()
set(_whole70_source "${CMAKE_CURRENT_SOURCE_DIR}/rust/whole70")
set(_whole70_output "${CMAKE_CURRENT_BINARY_DIR}/rust/whole70")
file(GLOB _whole70_rust_sources "${_whole70_source}/*.rs")
file(GLOB _whole70_witness_sources "${_whole70_source}/abi/*.c")
file(GLOB_RECURSE _whole70_public_headers "${PROJECT_SOURCE_DIR}/linux/include/*.h")
file(GLOB_RECURSE _whole70_generated_headers "${PROJECT_BINARY_DIR}/linux/include/*.h")
set(IHKLIB_PRODUCED_RUST_ARCHIVE "${_whole70_output}/libihklib_whole70.a")
set(IHKLIB_PRODUCED_NATIVE_RSP "${_whole70_output}/native-static-libs.rsp")
add_custom_command(
  OUTPUT "${IHKLIB_PRODUCED_RUST_ARCHIVE}" "${IHKLIB_PRODUCED_NATIVE_RSP}"
    "${_whole70_output}/producer-receipt.json"
  BYPRODUCTS "${_whole70_output}/perf_pages_abi.rs" "${_whole70_output}/dump_abi.rs"
    "${_whole70_output}/diagnostic_origins.rs"
    "${_whole70_output}/create_diagnostic_origins.rs" "${_whole70_output}/actual-stat-cfg.txt"
    "${_whole70_output}/source_export_actual_contracts.inc"
    "${_whole70_output}/source-export-contracts.json"
  COMMAND "${PYTHON_EXECUTABLE}" "${_whole70_source}/build_whole70_qualified.py"
    --cc "${CMAKE_C_COMPILER}" --rustc "${IHK_USER_RUSTC}"
    --source-dir "${_whole70_source}" --out-dir "${_whole70_output}"
    --include-dir "${PROJECT_SOURCE_DIR}/linux/include"
    --include-dir "${PROJECT_SOURCE_DIR}/linux/include/ihk/arch/${ARCH}"
    --include-dir "${PROJECT_BINARY_DIR}/linux/include"
    --include-dir "${PROJECT_BINARY_DIR}"
  DEPENDS ${_whole70_rust_sources} ${_whole70_witness_sources}
    "${IHK_USER_RUSTC}" "${CMAKE_C_COMPILER}"
    ${_whole70_public_headers} ${_whole70_generated_headers}
    "${_whole70_source}/build_whole70_qualified.py" "${_whole70_source}/rust_diagnostics.py"
    "${PROJECT_BINARY_DIR}/config.h"
    "${CMAKE_CURRENT_SOURCE_DIR}/ihklib.c"
    "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt" "${CMAKE_BINARY_DIR}/CMakeCache.txt"
  VERBATIM)
add_custom_target(ihklib_whole70_archive DEPENDS "${IHKLIB_PRODUCED_RUST_ARCHIVE}"
  "${IHKLIB_PRODUCED_NATIVE_RSP}" "${_whole70_output}/producer-receipt.json")
