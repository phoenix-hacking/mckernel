# Functional OS/apps Rust migration only; no security testing.
# Replace only the two boot/stop configure_file lines and corresponding install
# stanza at top-level CMakeLists.txt:306-315. Keep eclair configuration untouched.
# Stage this batch's Rust files under scripts/rust/boot-tools before selection.
option(ENABLE_RUST_BOOT_TOOLS "Select Rust installed McKernel boot/stop programs" ON)
if(ENABLE_RUST_BOOT_TOOLS)
  find_program(MCK_BOOT_RUSTC rustc REQUIRED)
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
      COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= ${MCK_BOOT_RUSTC}
        --edition=2021 --crate-name ${_entry} -C panic=abort -C opt-level=2
        "${_boot_build}/${_entry}_main.rs" -o "${_output}"
      DEPENDS "${_boot_build}/${_entry}_main.rs" "${_boot_build}/config.rs"
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
