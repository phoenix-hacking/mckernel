set(PROJECT_SOURCE_DIR "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-cmake-probe-bound-successor-1/not_gnu/src")
set(MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL ON)
set(CMAKE_GENERATOR "Unix Makefiles")
set(CMAKE_MAKE_PROGRAM "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-cmake-probe-bound-successor-1/fake-make.py")
set(MCKERNEL_M14_EXPECTED_MAKE_SHA256 "33de68cd69115c24f04de003e88a23adce72ac2d6377f3be1dde7701ae2084e2")
set(MCKERNEL_M14_EXPECTED_UNAME_R "6.12.0-test.x86_64")
set(UNAME_R "6.12.0-test.x86_64")
set(MCKERNEL_M14_EXPECTED_MAP_KERNEL_START "0xfffffffffe800000")
set(KERNEL_DIR "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/attempt-0002/m14-cmake-probe-bound-successor-1/not_gnu/kernel")
# M14_GUARD_PREFLIGHT_BEGIN
# The execution owner must already have established a fresh exclusive build
# root before CMake entry; checks below do not supply that ownership proof.
if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
    if (NOT CMAKE_GENERATOR STREQUAL "Unix Makefiles")
        message(FATAL_ERROR "M14 configure requires the Unix Makefiles generator")
    endif()
    if (NOT IS_ABSOLUTE "${CMAKE_MAKE_PROGRAM}" OR NOT EXISTS "${CMAKE_MAKE_PROGRAM}" OR
        NOT DEFINED MCKERNEL_M14_EXPECTED_MAKE_SHA256)
        message(FATAL_ERROR "M14 configure requires a bound absolute make executable")
    endif()
    string(LENGTH "${MCKERNEL_M14_EXPECTED_MAKE_SHA256}" MCKERNEL_M14_MAKE_HASH_LENGTH)
    if (NOT MCKERNEL_M14_MAKE_HASH_LENGTH EQUAL 64 OR
        NOT MCKERNEL_M14_EXPECTED_MAKE_SHA256 MATCHES "^[0-9a-f]+$")
        message(FATAL_ERROR "M14 configure requires an exact make SHA256")
    endif()
    file(SHA256 "${CMAKE_MAKE_PROGRAM}" MCKERNEL_M14_ACTUAL_MAKE_SHA256)
    if (NOT MCKERNEL_M14_ACTUAL_MAKE_SHA256 STREQUAL MCKERNEL_M14_EXPECTED_MAKE_SHA256)
        message(FATAL_ERROR "M14 configure make executable hash mismatch")
    endif()
    set(MCKERNEL_M14_PRE_VERIFIER "${PROJECT_SOURCE_DIR}/scripts/verify_m14_configure_probe.py")
    set(MCKERNEL_M14_ELF_VERIFIER "${PROJECT_SOURCE_DIR}/scripts/verify_m14_elf.py")
    if (NOT EXISTS "${MCKERNEL_M14_PRE_VERIFIER}" OR NOT EXISTS "${MCKERNEL_M14_ELF_VERIFIER}")
        message(FATAL_ERROR "M14 configure verifier sources are missing")
    endif()
    file(SHA256 "${MCKERNEL_M14_PRE_VERIFIER}" MCKERNEL_M14_PRE_SHA256)
    file(SHA256 "${MCKERNEL_M14_ELF_VERIFIER}" MCKERNEL_M14_ELF_SHA256)
    if (NOT MCKERNEL_M14_PRE_SHA256 STREQUAL "fa9bd547813bdad6848ff58fed7b48686af0fcf2cd50197a6866338d6ebe9902" OR
        NOT MCKERNEL_M14_ELF_SHA256 STREQUAL "157e2bd952f07c70a867fa9bd78165ac364c21d87f7dc32e3ecc482c191f7ca7")
        message(FATAL_ERROR "M14 configure verifier source hash mismatch")
    endif()
    execute_process(COMMAND "${CMAKE_MAKE_PROGRAM}" --version
        RESULT_VARIABLE MCKERNEL_M14_MAKE_VERSION_RESULT
        OUTPUT_VARIABLE MCKERNEL_M14_MAKE_VERSION_OUTPUT TIMEOUT 5)
    if (NOT MCKERNEL_M14_MAKE_VERSION_RESULT STREQUAL "0" OR
        NOT MCKERNEL_M14_MAKE_VERSION_OUTPUT MATCHES "^GNU Make")
        message(FATAL_ERROR "M14 configure requires a bound GNU Make executable")
    endif()
endif()
# M14_GUARD_PREFLIGHT_END
set(tmpdir ${CMAKE_CURRENT_BINARY_DIR}/tmp.resolve_MODULES_END)
file(REMOVE_RECURSE ${tmpdir})
file(MAKE_DIRECTORY ${tmpdir})
file(WRITE ${tmpdir}/driver.c "#include <linux/module.h>\n")
file(APPEND ${tmpdir}/driver.c "MODULE_LICENSE(\"GPL\");\n")
file(APPEND ${tmpdir}/driver.c "unsigned long MAP_KERNEL_START = MODULES_END - (1UL << 23);\n")
file(WRITE ${tmpdir}/Makefile "obj-m := driver.o\n")
file(APPEND ${tmpdir}/Makefile "all:\n")
file(APPEND ${tmpdir}/Makefile "\tmake ${KBUILD_MAKE_FLAGS_STR} -C ${KERNEL_DIR} M=${tmpdir} modules\n")

if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
    if (NOT DEFINED MCKERNEL_M14_EXPECTED_UNAME_R OR MCKERNEL_M14_EXPECTED_UNAME_R STREQUAL "" OR
        NOT DEFINED MCKERNEL_M14_EXPECTED_MAP_KERNEL_START OR MCKERNEL_M14_EXPECTED_MAP_KERNEL_START STREQUAL "" OR
        NOT UNAME_R STREQUAL MCKERNEL_M14_EXPECTED_UNAME_R)
        message(FATAL_ERROR "M14 configure requires an explicit matching kernel release and expected map")
    endif()
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    set(MCKERNEL_M14_PROBE_VERIFIER "${PROJECT_SOURCE_DIR}/scripts/verify_m14_configure_probe.py")
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B "${MCKERNEL_M14_PROBE_VERIFIER}"
        --phase identity --kernel-dir "${KERNEL_DIR}" --uname-r "${MCKERNEL_M14_EXPECTED_UNAME_R}"
        --expected-map "${MCKERNEL_M14_EXPECTED_MAP_KERNEL_START}"
        RESULT_VARIABLE MCKERNEL_M14_PROBE_IDENTITY_RESULT)
    if (NOT MCKERNEL_M14_PROBE_IDENTITY_RESULT STREQUAL "0")
        message(FATAL_ERROR "M14 configure kernel release identity rejected")
    endif()
    # This RESULT_VARIABLE is the wait result of CMake's own make child.
    execute_process(COMMAND "${CMAKE_MAKE_PROGRAM}" -C "${tmpdir}"
        RESULT_VARIABLE MCKERNEL_M14_PROBE_MAKE_RESULT)
    if (NOT MCKERNEL_M14_PROBE_MAKE_RESULT STREQUAL "0")
        message(FATAL_ERROR "M14 configure probe make failed: ${MCKERNEL_M14_PROBE_MAKE_RESULT}")
    endif()
    execute_process(COMMAND "${Python3_EXECUTABLE}" -I -B "${MCKERNEL_M14_PROBE_VERIFIER}"
        --phase probe --kernel-dir "${KERNEL_DIR}" --uname-r "${MCKERNEL_M14_EXPECTED_UNAME_R}"
        --expected-map "${MCKERNEL_M14_EXPECTED_MAP_KERNEL_START}"
        --build-dir "${CMAKE_CURRENT_BINARY_DIR}" --make-status "${MCKERNEL_M14_PROBE_MAKE_RESULT}"
        RESULT_VARIABLE MCKERNEL_M14_PROBE_VERIFY_RESULT
        OUTPUT_VARIABLE MCKERNEL_M14_PROBE_MAP OUTPUT_STRIP_TRAILING_WHITESPACE)
    if (NOT MCKERNEL_M14_PROBE_VERIFY_RESULT STREQUAL "0" OR
        NOT MCKERNEL_M14_PROBE_MAP STREQUAL MCKERNEL_M14_EXPECTED_MAP_KERNEL_START)
        message(FATAL_ERROR "M14 configure probe module/map rejected")
    endif()
    set(MAP_KERNEL_START "${MCKERNEL_M14_PROBE_MAP}")
else()
execute_process(COMMAND make -C ${tmpdir})
execute_process(COMMAND bash -c "offset=`readelf -S ${tmpdir}/driver.ko | grep .data | sed 's/.* //g'`; echo $((0x$offset))"
  OUTPUT_VARIABLE MAP_KERNEL_START_OFFSET OUTPUT_STRIP_TRAILING_WHITESPACE)
execute_process(COMMAND bash -c "dd if=${tmpdir}/driver.ko bs=1 skip=${MAP_KERNEL_START_OFFSET} count=8 2>/dev/null | od -tx8 -Ax | head -1 | sed 's|.* |0x|g'"
  OUTPUT_VARIABLE MAP_KERNEL_START OUTPUT_STRIP_TRAILING_WHITESPACE)
endif()
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/accepted-map" "${MAP_KERNEL_START}")
