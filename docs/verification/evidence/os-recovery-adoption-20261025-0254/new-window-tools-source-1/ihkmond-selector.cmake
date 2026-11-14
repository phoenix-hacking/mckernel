# PRIVATE proposal: root coordinates this shared ihk/linux/user/CMakeLists.txt.
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# After qualification, put ihkmond.rs under ihk/linux/user/rust.
# Replace add_executable(ihkmond ihkmond.c), its PIC/link flag lines and
# target_link_libraries(ihkmond...) with this Rust binary build.
# Remove only "ihkmond" from the existing install(TARGETS ...) list, leaving
# ihkconfig/ihkosctl/ihklib. Install the same daemon name in SBINDIR below.
option(ENABLE_RUST_USER_TOOLS "Enable Rust helpers in McKernel user tools" ON)
if(ENABLE_RUST_USER_TOOLS AND ARCH STREQUAL "x86_64")
  if(NOT IHK_USER_RUSTC OR NOT IS_ABSOLUTE "${IHK_USER_RUSTC}"
     OR NOT EXISTS "${IHK_USER_RUSTC}" OR NOT LIBUDEV
     OR NOT IS_ABSOLUTE "${CMAKE_C_COMPILER}")
    message(FATAL_ERROR "Rust ihkmond requires rustc and the selected platform libudev")
  endif()
  set(IHKMOND_RUST_CFG "")
  if(ENABLE_KMSG_REDIRECT)
    list(APPEND IHKMOND_RUST_CFG --cfg ihkmond_kmsg_redirect)
  endif()
  set(IHKMOND_RUST_BIN "${CMAKE_CURRENT_BINARY_DIR}/ihkmond")
  add_custom_command(
    OUTPUT "${IHKMOND_RUST_BIN}"
    COMMAND ${CMAKE_COMMAND} -E env "IHKMOND_TMP=/tmp/ihkmond"
      "${IHK_USER_RUSTC}" --edition=2021 -C opt-level=2 -C debuginfo=1 -C relocation-model=pic
      ${IHKMOND_RUST_CFG}
      -C "linker=${CMAKE_C_COMPILER}"
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/ihkmond.rs"
      -C "link-arg=$<TARGET_FILE:ihklib>"
      -C "link-arg=${LIBUDEV}"
      -C "link-arg=-Wl,-rpath,${CMAKE_INSTALL_FULL_LIBDIR}"
      -o "${IHKMOND_RUST_BIN}"
    DEPENDS ihklib "$<TARGET_FILE:ihklib>" "${LIBUDEV}"
      "${IHK_USER_RUSTC}" "${CMAKE_C_COMPILER}"
      "${CMAKE_CURRENT_SOURCE_DIR}/rust/ihkmond.rs"
      "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt"
      "${CMAKE_BINARY_DIR}/CMakeCache.txt"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihklib.h"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihklib_private.h"
      "${PROJECT_SOURCE_DIR}/linux/include/ihk/ihk_host_user.h"
    VERBATIM)
  add_custom_target(ihkmond ALL DEPENDS "${IHKMOND_RUST_BIN}")
  add_dependencies(ihkmond ihklib)
  install(PROGRAMS "${IHKMOND_RUST_BIN}" DESTINATION "${CMAKE_INSTALL_SBINDIR}")
elseif(IHK_ALLOW_CLI_C_FALLBACK)
  add_executable(ihkmond ihkmond.c)
  set_property(TARGET ihkmond PROPERTY POSITION_INDEPENDENT_CODE ON)
  set_property(TARGET ihkmond PROPERTY LINK_FLAGS "-fPIE -pie")
  target_link_libraries(ihkmond ihklib ${LIBUDEV} pthread)
  install(TARGETS ihkmond RUNTIME DESTINATION "${CMAKE_INSTALL_SBINDIR}")
else()
  message(FATAL_ERROR "Supported ihkmond successor requires Rust/x86_64; no silent production C fallback")
endif()
# No ihkmond_fixture cfg or test helper/stub is selected in production.
# Keep original C inactive as comparison source only after matching native proof.
