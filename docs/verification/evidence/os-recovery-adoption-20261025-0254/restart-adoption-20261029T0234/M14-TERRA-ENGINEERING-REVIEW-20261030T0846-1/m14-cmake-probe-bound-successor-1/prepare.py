from pathlib import Path
s=Path('preimage/CMakeLists.txt').read_text()
marker='set(tmpdir ${CMAKE_CURRENT_BINARY_DIR}/tmp.resolve_MODULES_END)'
pre='''# M14_GUARD_PREFLIGHT_BEGIN
# The execution owner must already have established a fresh exclusive build
# root before CMake entry; checks below do not supply that ownership proof.
if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
    if (NOT CMAKE_GENERATOR STREQUAL "Unix Makefiles")
        message(FATAL_ERROR "M14 configure requires the Unix Makefiles generator")
    endif()
    if (NOT IS_ABSOLUTE "${CMAKE_MAKE_PROGRAM}" OR NOT EXISTS "${CMAKE_MAKE_PROGRAM}" OR
        NOT "${CMAKE_MAKE_PROGRAM}" MATCHES "^/[A-Za-z0-9_./+-]+$" OR
        NOT "${KERNEL_DIR}" MATCHES "^/[A-Za-z0-9_./+-]+$" OR
        NOT "${CMAKE_CURRENT_BINARY_DIR}" MATCHES "^/[A-Za-z0-9_./+-]+$" OR
        NOT DEFINED MCKERNEL_M14_EXPECTED_MAKE_SHA256 OR
        NOT DEFINED MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS)
        message(FATAL_ERROR "M14 configure requires a bound absolute make executable")
    endif()
    if (NOT "${KBUILD_MAKE_FLAGS}" STREQUAL "${MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS}" OR
        NOT "${KBUILD_MAKE_FLAGS}" MATCHES "^[-A-Za-z0-9_=;./+:]*$")
        message(FATAL_ERROR "M14 configure Kbuild make flags are not bound")
    endif()
    string(REPLACE ";" " " MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS_STR "${MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS}")
    if (NOT "${KBUILD_MAKE_FLAGS_STR}" STREQUAL "${MCKERNEL_M14_EXPECTED_KBUILD_MAKE_FLAGS_STR}")
        message(FATAL_ERROR "M14 configure Kbuild make flag expansion changed")
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
'''
assert s.count(marker)==1;s=s.replace(marker,pre+marker)
nested = 'file(APPEND ${tmpdir}/Makefile "\\tmake ${KBUILD_MAKE_FLAGS_STR} -C ${KERNEL_DIR} M=${tmpdir} modules\\n")'
replacement = '''if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)
    # Use the same hash-bound GNU Make for the nested kernel build.
    file(APPEND ${tmpdir}/Makefile "\\t${CMAKE_MAKE_PROGRAM} ${KBUILD_MAKE_FLAGS_STR} -C ${KERNEL_DIR} M=${tmpdir} modules\\n")
else()
'''+nested+'''
endif()'''
assert s.count(nested)==1;s=s.replace(nested,replacement)
old='COMMAND "${Python3_EXECUTABLE}" "${MCKERNEL_M14_PROBE_VERIFIER}"';new='COMMAND "${Python3_EXECUTABLE}" -I -B "${MCKERNEL_M14_PROBE_VERIFIER}"';assert s.count(old)==2;s=s.replace(old,new)
Path('postimage/CMakeLists.txt').write_text(s)
