configure_file(mckernel.mk.in mckernel.mk @ONLY)

foreach(file IN ITEMS mckernel.c README)
  configure_file(${file} ${CMAKE_CURRENT_BINARY_DIR}/${file} COPYONLY)
endforeach()

file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/rust)
configure_file(rust/mckernel_crash_helpers.rs
  ${CMAKE_CURRENT_BINARY_DIR}/rust/mckernel_crash_helpers.rs COPYONLY)
