# Cargo's environment comments contain colons that CMake 3.28's depfile parser
# can treat as target separators, rejecting the file or losing its dependencies.
# Keep rustc's raw output and pass only file-dependency rules to CMake. The
# environment values are explicit custom-command arguments, so changing them
# already changes the generated build rule.
if (NOT DEFINED INPUT OR NOT DEFINED OUTPUT OR INPUT STREQUAL OUTPUT)
    message(FATAL_ERROR "Rust depfile normalization requires distinct INPUT and OUTPUT paths")
endif()
file(READ "${INPUT}" _rust_depfile)
string(REGEX REPLACE "(^|\n)# env-dep:[^\n]*" "\\1" _rust_depfile "${_rust_depfile}")
file(WRITE "${OUTPUT}" "${_rust_depfile}")
