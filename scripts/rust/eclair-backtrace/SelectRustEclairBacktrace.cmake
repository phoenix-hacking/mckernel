# Functional McKernel OS/apps migration only; no security testing.
# Default OFF retains the working Expect program until matching qualification/root cutover.
# Independent selector from boot/stop; installed name and PROGRAMS mode are unchanged.
option(ENABLE_RUST_ECLAIR_BACKTRACE "Select Rust installed eclair backtrace helper" OFF)
if(ENABLE_RUST_ECLAIR_BACKTRACE)
  set(MCKERNEL_RUNTIME_TOOL_RUSTC "" CACHE FILEPATH "Pinned runtime tool compiler; independent of compute RUSTC")
  if(NOT IS_ABSOLUTE "${MCKERNEL_RUNTIME_TOOL_RUSTC}" OR NOT EXISTS "${MCKERNEL_RUNTIME_TOOL_RUSTC}")
    message(FATAL_ERROR "Rust backtrace consumer requires the absolute pinned MCKERNEL_RUNTIME_TOOL_RUSTC")
  endif()
  foreach(_value prefix ARCH)
    if("${${_value}}" MATCHES "[^A-Za-z0-9_./:+,@%=-]")
      message(FATAL_ERROR "Rust backtrace configuration requires reviewed literal configured values: ${_value}")
    endif()
  endforeach()
  set(_eclair_src "${PROJECT_SOURCE_DIR}/scripts/rust/eclair-backtrace")
  set(_eclair_build "${PROJECT_BINARY_DIR}/rust-eclair-backtrace")
  file(MAKE_DIRECTORY "${_eclair_build}")
  configure_file("${_eclair_src}/config.rs.in" "${_eclair_build}/config.rs" @ONLY)
  foreach(_file eclair_backtrace.rs eclair_native.rs eclair_main.rs)
    configure_file("${_eclair_src}/${_file}" "${_eclair_build}/${_file}" COPYONLY)
  endforeach()
  set(_eclair_output "${PROJECT_BINARY_DIR}/eclair-dump-backtrace.exp")
  add_custom_command(OUTPUT "${_eclair_output}"
    COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= "${MCKERNEL_RUNTIME_TOOL_RUSTC}"
      --edition=2021 --crate-name eclair_dump_backtrace -C panic=abort -C opt-level=2
      "${_eclair_build}/eclair_main.rs" -o "${_eclair_output}"
    DEPENDS "${MCKERNEL_RUNTIME_TOOL_RUSTC}" "${_eclair_build}/eclair_main.rs" "${_eclair_build}/eclair_backtrace.rs"
      "${_eclair_build}/eclair_native.rs" "${_eclair_build}/config.rs" VERBATIM)
  add_custom_target(eclair_backtrace_rust_program ALL DEPENDS "${_eclair_output}")
else()
  message(WARNING "M15 debt: explicit retained expect helper selected")
  configure_file(scripts/eclair-dump-backtrace.exp.in eclair-dump-backtrace.exp @ONLY)
endif()
install(PROGRAMS "${PROJECT_BINARY_DIR}/eclair-dump-backtrace.exp"
  DESTINATION "${CMAKE_INSTALL_BINDIR}")
