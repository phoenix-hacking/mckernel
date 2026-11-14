cmake_minimum_required(VERSION 3.11)
# Nonshipped selected-target driver. The production mcexec rule below is unchanged.
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE "Debug" CACHE STRING "Build type: Debug Release..." FORCE)
endif()
project(mckernel LANGUAGES C ASM)
include(GNUInstallDirs)
set(MCKERNEL_VERSION "1.8.0")
set(BUILD_TARGET "smp-x86" CACHE STRING "Build target")
set(ARCH "x86_64")
set(BUILDID "" CACHE STRING "Actual matching IHK configuration BUILDID")
if(NOT BUILDID STREQUAL "8d288b8")
  message(FATAL_ERROR "Bind actual current IHK8d288b8 BUILDID")
endif()
# These warning options and two definitions equal the retained actual default
# production ASM flags. The selected assembly has no #include dependencies.
set(CFLAGS_WARNING -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare
    -Wno-unused-function -Wno-implicit-fallthrough -Wno-stringop-truncation
    CACHE STRING "Warning flags")
add_compile_options(${CFLAGS_WARNING})
option(ENABLE_WERROR "Enable -Werror" OFF)
if(ENABLE_WERROR)
  add_compile_options(-Werror)
endif()
option(PROFILE_ENABLE "System call profile" ON)
if(PROFILE_ENABLE)
  add_definitions(-DPROFILE_ENABLE)
endif()
option(ENABLE_LINUX_WORK_IRQ_FOR_IKC "Use Linux work IRQ for IKC IPI" ON)
if(ENABLE_LINUX_WORK_IRQ_FOR_IKC)
  add_definitions(-DIHK_IKC_USE_LINUX_WORK_IRQ)
endif()
option(ENABLE_KMSG_REDIRECT "Redirect kernel messages" OFF)
option(ENABLE_QLMPI "Enable qlmpi programs" OFF)
option(ENABLE_UTI "Enable uti support" OFF)
# Preserve production include arguments; Rust and this no-include assembly do
# not consume C/IHK/kernel headers. No missing header is fabricated or qualified.
set(IHK_FULL_SOURCE_DIR "/source/ihk")
set(KERNEL_DIR "/source/executer/kernel")
find_library(LIBRT rt)
if(NOT LIBRT)
  message(FATAL_ERROR "error: couldn't find librt")
endif()
find_library(LIBNUMA numa)
if(NOT LIBNUMA)
  message(FATAL_ERROR "error: couldn't find libnuma")
endif()
# Same production install RPATH; actual build/stage bytes must be collected.
set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_FULL_LIBDIR}")
add_subdirectory("/source/executer/user" "executer/user")
# Passive link provenance only; no implementation/provider/selection change.
set_property(TARGET mcexec APPEND_STRING PROPERTY LINK_FLAGS
             " -Wl,--trace -Wl,-Map=/output/mcexec.map")
