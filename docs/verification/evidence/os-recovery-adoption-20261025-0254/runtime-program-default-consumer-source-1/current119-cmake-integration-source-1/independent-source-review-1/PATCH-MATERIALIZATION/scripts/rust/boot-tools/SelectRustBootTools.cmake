# Functional OS/apps Rust migration only; no security testing.
# Default OFF retains the working scripts until matching qualification/root cutover.
# Explicit ON builds the unchanged existing Rust program bodies at their shipped names.
option(ENABLE_RUST_BOOT_TOOLS "Select Rust installed McKernel boot/stop programs" OFF)
if(ENABLE_RUST_BOOT_TOOLS)
  set(MCKERNEL_RUNTIME_TOOL_RUSTC "" CACHE FILEPATH "Pinned runtime tool compiler; independent of compute RUSTC")
  if(NOT IS_ABSOLUTE "${MCKERNEL_RUNTIME_TOOL_RUSTC}" OR NOT EXISTS "${MCKERNEL_RUNTIME_TOOL_RUSTC}")
    message(FATAL_ERROR "Rust boot/stop consumers require the absolute pinned MCKERNEL_RUNTIME_TOOL_RUSTC")
  endif()
  foreach(_value prefix ETCDIR KMODDIR MCKERNELDIR ARCH BUILDID)
    if("${${_value}}" MATCHES "[^A-Za-z0-9_./:+,@%=-]")
      message(FATAL_ERROR "Rust boot/stop configuration requires reviewed literal configured values: ${_value}")
    endif()
  endforeach()
  set(_boot_src "${PROJECT_SOURCE_DIR}/scripts/rust/boot-tools")
  set(_boot_build "${PROJECT_BINARY_DIR}/rust-boot-tools")
  file(MAKE_DIRECTORY "${_boot_build}")
  configure_file("${_boot_src}/config.rs.in" "${_boot_build}/config.rs" @ONLY)
  foreach(_file platform.rs reboot.rs stop.rs mcreboot_main.rs mcstop_main.rs)
    configure_file("${_boot_src}/${_file}" "${_boot_build}/${_file}" COPYONLY)
  endforeach()
  foreach(_entry mcreboot mcstop)
    if(_entry STREQUAL "mcreboot")
      set(_output "${PROJECT_BINARY_DIR}/mcreboot.sh")
    else()
      set(_output "${PROJECT_BINARY_DIR}/mcstop+release.sh")
    endif()
    add_custom_command(OUTPUT "${_output}"
      COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= "${MCKERNEL_RUNTIME_TOOL_RUSTC}"
        --edition=2021 --crate-name ${_entry} -C panic=abort -C opt-level=2
        "${_boot_build}/${_entry}_main.rs" -o "${_output}"
      DEPENDS "${MCKERNEL_RUNTIME_TOOL_RUSTC}" "${_boot_build}/${_entry}_main.rs" "${_boot_build}/config.rs"
        "${_boot_build}/platform.rs" "${_boot_build}/reboot.rs" "${_boot_build}/stop.rs"
      VERBATIM)
    add_custom_target(${_entry}_rust_program ALL DEPENDS "${_output}")
  endforeach()
else()
  message(WARNING "M15 debt: explicit retained shell boot/stop fallback selected")
  configure_file(scripts/mcreboot-smp.sh.in mcreboot.sh @ONLY)
  configure_file(scripts/mcstop+release-smp.sh.in mcstop+release.sh @ONLY)
endif()
install(PROGRAMS "${PROJECT_BINARY_DIR}/mcreboot.sh"
  "${PROJECT_BINARY_DIR}/mcstop+release.sh" DESTINATION "${CMAKE_INSTALL_SBINDIR}")
