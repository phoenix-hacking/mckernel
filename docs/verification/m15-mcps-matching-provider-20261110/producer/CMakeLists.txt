cmake_minimum_required(VERSION 3.16)
project(McKernelMcpsMatchingProvider LANGUAGES C)
# Narrow actual selected target; no full McKernel, mcinspect producer or main run.
include(GNUInstallDirs)
set(prefix "${CMAKE_INSTALL_PREFIX}")
set(ARCH x86_64)
set(BUILD_TARGET smp-x86)
# The selected /usr/local production branch is exactly root CMake269-273.
if(NOT CMAKE_INSTALL_PREFIX STREQUAL "/usr/local")
  message(FATAL_ERROR "This packet is bound to the current /usr/local profile")
endif()
set(MCKERNELDIR "${CMAKE_INSTALL_PREFIX}/${BUILD_TARGET}/kernel")
# Preserve the root's actual global install-RPATH setting. Actual PROGRAMS
# installation is read back; no TARGETS-style rewrite is assumed.
set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_FULL_LIBDIR}")
option(ENABLE_RUST_USER_TOOLS "Enable Rust helpers in McKernel user tools" ON)
set(MCKERNEL_RUNTIME_TOOL_RUSTC "" CACHE FILEPATH "Pinned independent runtime compiler")
if(NOT IS_ABSOLUTE "${MCKERNEL_RUNTIME_TOOL_RUSTC}" OR
   NOT EXISTS "${MCKERNEL_RUNTIME_TOOL_RUSTC}" OR
   IS_DIRECTORY "${MCKERNEL_RUNTIME_TOOL_RUSTC}")
  message(FATAL_ERROR "Bind the exact qualified absolute runtime Rust compiler")
endif()
set(MCPS_MATCHED_MCINSPECT "" CACHE FILEPATH "Exact existing qualified mcinspect63502 executable")
if(NOT IS_ABSOLUTE "${MCPS_MATCHED_MCINSPECT}" OR
   NOT EXISTS "${MCPS_MATCHED_MCINSPECT}" OR
   IS_DIRECTORY "${MCPS_MATCHED_MCINSPECT}")
  message(FATAL_ERROR "Bind the existing actual mcinspect63502 provider")
endif()
# Real retained executable input, with no build/command or stand-in body.
add_executable(mcinspect IMPORTED GLOBAL)
set_target_properties(mcinspect PROPERTIES IMPORTED_LOCATION "${MCPS_MATCHED_MCINSPECT}")
include("${CMAKE_CURRENT_SOURCE_DIR}/production-mcps-target.cmake")
# Exact selected mcps arm of production install(PROGRAMS); vmcore is not built.
install(PROGRAMS "${CMAKE_CURRENT_BINARY_DIR}/mcps"
  DESTINATION "${CMAKE_INSTALL_BINDIR}")
# Stage the unchanged real subprocess provider, without rebuilding, relinking,
# stripping or running it. This private copy is separate from product selection.
install(PROGRAMS "${MCPS_MATCHED_MCINSPECT}"
  DESTINATION "${CMAKE_INSTALL_BINDIR}")
