# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# PRIVATE FUTURE FRAGMENT, NOT EXECUTED OR INTEGRATED. Nonshipped witness only.
# Follows existing BfdRustAccessors.cmake selected-header -> Rust data pattern.
# This does not qualify or link the selected SDK libbfd.a provider.
if(CMAKE_CROSSCOMPILING)
  message(FATAL_ERROR "ldump2 selected BFD layout requires separately qualified native witness")
endif()
file(SHA256 "/usr/include/bfd.h" _ldump2_bfd_header_sha)
file(SHA256 "${CMAKE_C_COMPILER}" _ldump2_bfd_cc_sha)
if(NOT _ldump2_bfd_header_sha STREQUAL "de900a9fe4ac94543ee1382cebc3063c3d7e20d16bc934fc816133dd55fe2432" OR
   NOT _ldump2_bfd_cc_sha STREQUAL "2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2")
  message(FATAL_ERROR "ldump2 BFD layout requires reviewed selected Rocky header/compiler bytes")
endif()
set(_ldump2_bfd_witness "${CMAKE_CURRENT_LIST_DIR}/section_layout_witness.c")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  "${_ldump2_bfd_witness}" "/usr/include/bfd.h" "${CMAKE_C_COMPILER}"
  "/usr/include/ansidecl.h" "/usr/include/symcat.h" "/usr/include/diagnostics.h")
unset(_ldump2_bfd_run CACHE)
unset(_ldump2_bfd_compile CACHE)
try_run(_ldump2_bfd_run _ldump2_bfd_compile
  "${CMAKE_CURRENT_BINARY_DIR}/ldump2-bfd-layout-probe" "${_ldump2_bfd_witness}"
  CMAKE_FLAGS "-DCMAKE_C_STANDARD=11" "-DCMAKE_C_STANDARD_REQUIRED=ON"
  RUN_OUTPUT_VARIABLE _ldump2_bfd_layout
  COMPILE_OUTPUT_VARIABLE _ldump2_bfd_compile_log)
if(NOT _ldump2_bfd_compile OR NOT "${_ldump2_bfd_run}" STREQUAL "0")
  message(FATAL_ERROR "ldump2 selected BFD typed witness failed: ${_ldump2_bfd_compile_log}")
endif()
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/rust")
set(LDUMP2_BFD_LAYOUT_RS "${CMAKE_CURRENT_BINARY_DIR}/rust/ldump2_bfd_section_layout.rs")
file(WRITE "${LDUMP2_BFD_LAYOUT_RS}" "${_ldump2_bfd_layout}")
set(LDUMP2_BFD_LAYOUT_ENV "MCKERNEL_LDUMP2_BFD_LAYOUT_RS=${LDUMP2_BFD_LAYOUT_RS}")
set(LDUMP2_BFD_LAYOUT_DEPENDS
  "${_ldump2_bfd_witness}" "${LDUMP2_BFD_LAYOUT_RS}" "/usr/include/bfd.h"
  "/usr/include/ansidecl.h" "/usr/include/symcat.h" "/usr/include/diagnostics.h")
# Root's future reviewed successor must add ${LDUMP2_BFD_LAYOUT_ENV} to the
# existing cmake -E env Rust full-body compile, and ${LDUMP2_BFD_LAYOUT_DEPENDS}
# to that object's DEPENDS. Preserve all other existing producer argv/flags.
# E.g. COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= "${LDUMP2_BFD_LAYOUT_ENV}" ${RUSTC} ...
# Actual selected SDK compiler/archive binding and cohort admission remain open.
