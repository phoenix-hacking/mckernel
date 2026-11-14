# NONSHIPPED build orchestration. Production gets only bfd_accessors.o (Rust).
# This pinned qualification deliberately fails on other BFD/ABI selections.
if(CMAKE_CROSSCOMPILING)
  message(FATAL_ERROR "BFD Rust accessor needs a separately qualified native layout witness")
endif()
if(NOT "${LIBBFD}" STREQUAL "/usr/lib64/libbfd.so")
  message(FATAL_ERROR "BFD Rust accessor: unqualified library selector")
endif()
file(SHA256 "/usr/include/bfd.h" _bfd_header_sha)
file(SHA256 "${LIBBFD}" _bfd_library_sha)
file(SHA256 "${CMAKE_C_COMPILER}" _bfd_cc_sha)
if(NOT _bfd_header_sha STREQUAL "de900a9fe4ac94543ee1382cebc3063c3d7e20d16bc934fc816133dd55fe2432" OR
   NOT _bfd_library_sha STREQUAL "6cfd31804974c248c9512879e7b77a94862f92150c2171d901140464ea936ab3" OR
   NOT _bfd_cc_sha STREQUAL "2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2")
  message(FATAL_ERROR "BFD Rust accessor: selected Rocky header/library/compiler pin mismatch")
endif()
set(_bfd_witness "${CMAKE_CURRENT_SOURCE_DIR}/cmake/bfd_layout_witness.c")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  "${_bfd_witness}" "/usr/include/bfd.h" "${LIBBFD}")
# Do not reuse cached try_run output across header/configuration changes.
unset(_bfd_run CACHE)
unset(_bfd_compile CACHE)
try_run(_bfd_run _bfd_compile "${CMAKE_CURRENT_BINARY_DIR}/bfd-layout-probe"
  "${_bfd_witness}"
  CMAKE_FLAGS "-DCMAKE_C_STANDARD=11" "-DCMAKE_C_STANDARD_REQUIRED=ON"
  LINK_LIBRARIES "${LIBBFD}"
  RUN_OUTPUT_VARIABLE _bfd_layout
  COMPILE_OUTPUT_VARIABLE _bfd_compile_log)
if(NOT _bfd_compile OR NOT "${_bfd_run}" STREQUAL "0")
  message(FATAL_ERROR "BFD typed layout witness failed: ${_bfd_compile_log}")
endif()
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/rust")
set(_bfd_layout_rs "${CMAKE_CURRENT_BINARY_DIR}/rust/bfd_layout.rs")
file(WRITE "${_bfd_layout_rs}" "${_bfd_layout}")
set(BFD_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/bfd_accessors.o")
add_custom_command(OUTPUT "${BFD_RUST_OBJ}"
  COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= "MCKERNEL_BFD_LAYOUT_RS=${_bfd_layout_rs}" ${RUSTC}
    --crate-name bfd_accessors --crate-type lib --edition=2021
    -C panic=abort -C opt-level=2 -C debuginfo=1 -C force-unwind-tables=no
    --emit=obj=${BFD_RUST_OBJ}
    "${CMAKE_CURRENT_SOURCE_DIR}/rust/bfd_accessors.rs"
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/bfd_accessors.rs" "${_bfd_layout_rs}"
  COMMENT "Building Rust BFD accessors from checked selected-header layout"
  VERBATIM)
add_custom_target(bfd_rust_accessors DEPENDS "${BFD_RUST_OBJ}")
set_source_files_properties("${BFD_RUST_OBJ}" PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
