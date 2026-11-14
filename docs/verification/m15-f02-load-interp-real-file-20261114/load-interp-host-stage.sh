#!/usr/bin/bash
# Functional McKernel OS/apps/Rust only; NO SECURITY TESTING.
# Source proposal only: distinct review and fresh Root operation admission first.
set -euo pipefail
umask 077
export LC_ALL=C LANG=C TZ=UTC TMPDIR=/output/tmp
ulimit -v 1048576
cd /output
[[ ${ROOT_ACTUAL_CHANGED_OBJECT_SHA256:-} == d511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445 ]]
if [[ -e caller.o || -e load-interp-host || -e LOAD-INTERP-STAGE-COMPLETE ]]; then
    printf '%s\n' 'Refuse reused interpreter-case output identity.' >&2
    exit 2
fi
/usr/bin/mkdir -p /output/tmp /output/metadata
printf '%s\n' \
 '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2  /usr/bin/cc' \
 'b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4  /lib64/libc.so.6' \
 'be20c2b16781eea6c69d47816bf15869f90f2a009628c310049da1d2f3c31e4e  /qualified-numa/libnuma.so' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 'c491fb1f58a2daef90047eb159498def6caef95b863e18b4adf37e202a923d66  /input/load-interp-host-caller.c' \
 '6ffc96880d35fe1db04eeecd990687103b7a9089422288767fd0864edf43fc8c  /retained/interp-bearing-input.elf' \
 'd511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445  /retained/changed-mcexec_helpers.o' \
 | /usr/bin/sha256sum --check > /output/INPUTS.before.sha256-check

# Only one new small C observer/test ELF. No Rust compile/production relink.
/usr/bin/cc -std=gnu11 -O2 -g -fPIC -fno-builtin -Wall -Wextra -Werror \
    -I/input -c /input/load-interp-host-caller.c -o /output/caller.o \
    > /output/COMPILE.stdout 2> /output/COMPILE.stderr
/usr/bin/cc -g -fPIE -pie -Wl,--trace -Wl,--cref \
    -Wl,-Map=/output/load-interp-host.map \
    -Wl,--dependency-file=/output/load-interp-host.link.d \
    -Wl,--wrap=main -Wl,--wrap=fopen -Wl,--wrap=fclose -Wl,--wrap=fflush \
    -Wl,--wrap=malloc -Wl,--wrap=calloc -Wl,--wrap=realloc -Wl,--wrap=free \
    -Wl,--wrap=ioctl /output/caller.o /retained/changed-mcexec_helpers.o \
    -o /output/load-interp-host -Wl,-rpath,/qualified-numa: /retained/libmcexec.a \
    /usr/lib64/librt.a /qualified-numa/libnuma.so -lpthread \
    > /output/LINK.stdout 2> /output/LINK.stderr

# Only the newly linked test-entry/realCRT boundary, not provider/ABI replay.
/usr/bin/nm --format=posix --extern-only --defined-only /output/load-interp-host \
    > /output/metadata/caller-defined.nm
/usr/bin/objdump --disassemble=_start --reloc /output/load-interp-host \
    > /output/metadata/caller-startup.objdump
for symbol in __wrap_main main load_interp mcexec_load_alloc_desc_bridge; do
    [[ $(/usr/bin/grep -Ec "^${symbol} T " /output/metadata/caller-defined.nm) == 1 ]]
done
/usr/bin/grep -Eq 'lea[[:space:]].*%rdi.*<__wrap_main>' /output/metadata/caller-startup.objdump
/usr/bin/grep -q '__libc_start_main' /output/metadata/caller-startup.objdump

# The retained fourcase ELF is opened only as immutable data; never executed.
/output/load-interp-host > /output/CASE.stdout 2> /output/CASE.stderr
printf '%s\n' 'mcexec_load_pt_interp_on_interp_bridge: PT_INTERP on interp' \
    > /output/EXPECTED.stderr
/usr/bin/cmp /output/EXPECTED.stderr /output/CASE.stderr
[[ $(/usr/bin/wc -l < /output/CASE.stdout) == 1 ]]
/usr/bin/grep -Fq '"case_pass":true}' /output/CASE.stdout
/usr/bin/stat --format='%n %s %a' /retained/interp-bearing-input.elf > /output/INPUT.stat
/usr/bin/sha256sum /output/caller.o /output/load-interp-host /output/load-interp-host.map \
    /retained/changed-mcexec_helpers.o /retained/interp-bearing-input.elf \
    /retained/libmcexec.a /input/uprotocol.h /input/load-interp-host-caller.c \
    > /output/ARTIFACTS.sha256
printf '%s\n' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 'c491fb1f58a2daef90047eb159498def6caef95b863e18b4adf37e202a923d66  /input/load-interp-host-caller.c' \
 '6ffc96880d35fe1db04eeecd990687103b7a9089422288767fd0864edf43fc8c  /retained/interp-bearing-input.elf' \
 'd511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445  /retained/changed-mcexec_helpers.o' \
 | /usr/bin/sha256sum --check > /output/INPUTS.after.sha256-check
printf '%s\n' 'One real PT_INTERP interpreter rejection only; exact NULL/realloc1000/production-free and borrowed FILE closure observed. Independent result/family qualification and Root receipt remain required. No passing shebang case replay, production main/backend/native or wholeF02 acceptance.' \
    > /output/LOAD-INTERP-STAGE-COMPLETE
