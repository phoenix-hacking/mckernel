# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Qualifies the exact production daemon selector with the accepted real DSO.
# The full IHK default graph/install/native lifecycle remains a separate join.
cmake_minimum_required(VERSION 3.11)
project(m15_daemon_selected_rule C)
include(GNUInstallDirs)
set(ARCH x86_64)
set(PROJECT_SOURCE_DIR "/src/ihk")
set(IHK_USER_RUSTC "/nightly/bin/rustc")
set(LIBUDEV "/usr/lib64/libudev.so")
set(ENABLE_RUST_USER_TOOLS ON)
set(ENABLE_KMSG_REDIRECT OFF)
set(IHK_ALLOW_CLI_C_FALLBACK OFF)
add_library(ihklib SHARED IMPORTED GLOBAL)
set_target_properties(ihklib PROPERTIES IMPORTED_LOCATION "/accepted-libihk/libihk.so")
add_subdirectory(user sdk-daemon)
