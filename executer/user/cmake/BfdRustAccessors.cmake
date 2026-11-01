# NONSHIPPED build orchestration. Production gets only bfd_accessors.o (Rust).
# This pinned qualification deliberately fails on other BFD/ABI selections.
if(CMAKE_CROSSCOMPILING)
  message(FATAL_ERROR "BFD Rust accessor needs a separately qualified native layout witness")
endif()
if(CMAKE_CONFIGURATION_TYPES)
  message(FATAL_ERROR "BFD Rust accessor: qualify a separate layout for a multi-configuration generator")
endif()
if(NOT "${LIBBFD}" STREQUAL "/usr/lib64/libbfd.so")
  message(FATAL_ERROR "BFD Rust accessor: unqualified library selector")
endif()
# try_run does not inherit directory definitions/options. Bind its profile
# explicitly and reject DEBUG_BFD_SEND wherever the selected build defines it.
get_directory_property(_bfd_directory_defs COMPILE_DEFINITIONS)
get_directory_property(_bfd_directory_options COMPILE_OPTIONS)
string(FIND "${_bfd_directory_defs};${_bfd_directory_options}" "$<" _bfd_genex_position)
if(NOT _bfd_genex_position EQUAL -1)
  message(FATAL_ERROR "BFD Rust accessor: directory generator expressions require separate profile qualification")
endif()
set(_bfd_probe_flags ${_bfd_directory_options})
foreach(_bfd_definition IN LISTS _bfd_directory_defs)
  if(_bfd_definition MATCHES "(^|[;:<>])DEBUG_BFD_SEND($|[=;:<>])")
    message(FATAL_ERROR "BFD Rust accessor: DEBUG_BFD_SEND is outside the qualified profile")
  endif()
  list(APPEND _bfd_probe_flags "-D${_bfd_definition}")
endforeach()
set(_bfd_flag_view "${CMAKE_C_FLAGS};${_bfd_directory_options}")
set(_bfd_configurations ${CMAKE_CONFIGURATION_TYPES} "${CMAKE_BUILD_TYPE}")
foreach(_bfd_configuration IN LISTS _bfd_configurations)
  string(TOUPPER "${_bfd_configuration}" _bfd_configuration_upper)
  string(APPEND _bfd_flag_view ";${CMAKE_C_FLAGS_${_bfd_configuration_upper}}")
endforeach()
if(_bfd_flag_view MATCHES "(^|[,;:<> \t])-D[ \t]*DEBUG_BFD_SEND($|[=,;:<> \t])")
  message(FATAL_ERROR "BFD Rust accessor: DEBUG_BFD_SEND is outside the qualified profile")
endif()
file(SHA256 "/usr/include/bfd.h" _bfd_header_sha)
file(SHA256 "${LIBBFD}" _bfd_library_sha)
file(SHA256 "${CMAKE_C_COMPILER}" _bfd_cc_sha)
# The selected libbfd.so is an ld script. Bind its actual BFD implementation,
# using the recorded binutils-devel-2.41-63.el10 selected-source manifest.
# libsframe and the script's -liberty/-lz/-ldl selections still need separate
# SDK closure; tracking an input below does not qualify its implementation.
file(SHA256 "/usr/lib64/libbfd.a" _bfd_archive_sha)
if(NOT _bfd_header_sha STREQUAL "de900a9fe4ac94543ee1382cebc3063c3d7e20d16bc934fc816133dd55fe2432" OR
   NOT _bfd_library_sha STREQUAL "6cfd31804974c248c9512879e7b77a94862f92150c2171d901140464ea936ab3" OR
   NOT _bfd_cc_sha STREQUAL "2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2" OR
   NOT _bfd_archive_sha STREQUAL "2324c3f9557b3387126123659badf4cccdbbd272104aec42a21c709c31bf6d4e")
  message(FATAL_ERROR "BFD Rust accessor: selected Rocky header/library/compiler pin mismatch")
endif()
set(_bfd_witness "${CMAKE_CURRENT_SOURCE_DIR}/cmake/bfd_layout_witness.c")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  "${_bfd_witness}" "/usr/include/bfd.h" "${LIBBFD}" "${CMAKE_C_COMPILER}"
  "/usr/lib64/libbfd.a" "/usr/lib64/libsframe.a")
# Do not reuse cached try_run output across header/configuration changes.
unset(_bfd_run CACHE)
unset(_bfd_compile CACHE)
if(DEFINED CMAKE_TRY_COMPILE_CONFIGURATION)
  set(_bfd_had_probe_configuration TRUE)
  set(_bfd_saved_probe_configuration "${CMAKE_TRY_COMPILE_CONFIGURATION}")
else()
  set(_bfd_had_probe_configuration FALSE)
endif()
# A single generated layout must use this build's configuration-specific flags.
set(CMAKE_TRY_COMPILE_CONFIGURATION "${CMAKE_BUILD_TYPE}")
try_run(_bfd_run _bfd_compile "${CMAKE_CURRENT_BINARY_DIR}/bfd-layout-probe"
  "${_bfd_witness}"
  CMAKE_FLAGS "-DCMAKE_C_STANDARD=11" "-DCMAKE_C_STANDARD_REQUIRED=ON"
  COMPILE_DEFINITIONS ${_bfd_probe_flags}
  LINK_LIBRARIES "${LIBBFD}"
  RUN_OUTPUT_VARIABLE _bfd_layout
  COMPILE_OUTPUT_VARIABLE _bfd_compile_log)
if(_bfd_had_probe_configuration)
  set(CMAKE_TRY_COMPILE_CONFIGURATION "${_bfd_saved_probe_configuration}")
else()
  unset(CMAKE_TRY_COMPILE_CONFIGURATION)
endif()
if(NOT _bfd_compile OR NOT "${_bfd_run}" STREQUAL "0")
  message(FATAL_ERROR "BFD typed layout witness failed: ${_bfd_compile_log}")
endif()
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/rust")
set(_bfd_layout_rs "${CMAKE_CURRENT_BINARY_DIR}/rust/bfd_layout.rs")
file(WRITE "${_bfd_layout_rs}" "${_bfd_layout}")
set(BFD_RUST_OBJ "${CMAKE_CURRENT_BINARY_DIR}/rust/bfd_accessors.o")
add_custom_command(OUTPUT "${BFD_RUST_OBJ}"
  COMMAND ${CMAKE_COMMAND} -E env MAKEFLAGS= "MCKERNEL_BFD_LAYOUT_RS=${_bfd_layout_rs}" ${MCKERNEL_RUNTIME_TOOL_RUSTC}
    --crate-name bfd_accessors --crate-type lib --edition=2021
    -C panic=abort -C opt-level=2 -C debuginfo=1 -C force-unwind-tables=no
    --emit=obj=${BFD_RUST_OBJ}
    "${CMAKE_CURRENT_SOURCE_DIR}/rust/bfd_accessors.rs"
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/rust/bfd_accessors.rs" "${_bfd_layout_rs}"
    "${MCKERNEL_RUNTIME_TOOL_RUSTC}"
  COMMENT "Building Rust BFD accessors from checked selected-header layout"
  VERBATIM)
add_custom_target(bfd_rust_accessors DEPENDS "${BFD_RUST_OBJ}")
set_source_files_properties("${BFD_RUST_OBJ}" PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
