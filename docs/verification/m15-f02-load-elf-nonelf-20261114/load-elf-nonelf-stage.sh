#!/usr/bin/bash
# Functional McKernel OS/apps/Rust/allowed assembly ONLY; NO SECURITY TESTING.
# SOURCE ONLY: separate source/operation reviews and fresh Root admission first.
set -euo pipefail
umask 077
export LC_ALL=C LANG=C TZ=UTC TMPDIR=/output/tmp
ulimit -v 1048576
cd /output
[[ ${ROOT_ACTUAL_CHANGED_OBJECT_SHA256:-} == d511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445 ]]
if [[ -e caller.o || -e load-elf-nonelf || -e LOAD-ELF-NONELF-COMPLETE ]]; then
    printf '%s\n' 'Refuse reused non-ELF-header case output.' >&2
    exit 2
fi
/usr/bin/mkdir -p /output/tmp /output/metadata
printf '%s\n' \
 '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2  /usr/bin/cc' \
 'b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4  /lib64/libc.so.6' \
 'be20c2b16781eea6c69d47816bf15869f90f2a009628c310049da1d2f3c31e4e  /qualified-numa/libnuma.so' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 '6d9d8306923ce129f5578b5ae3fac68e6d84e82046a9c4723bea4adbe99dccb1  /retained/main-desc-source.txt' \
 'ff6968cab1c07fb5ec7d6ea4679599de763a4987fa7e16442d7c9a7f694f2933  /input/load-elf-nonelf-caller.c' \
 'd511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445  /retained/changed-mcexec_helpers.o' \
 | /usr/bin/sha256sum --check > /output/INPUTS.before.sha256-check
/usr/bin/stat -L --format='%n %d %i %f %s %Y %Z' /retained/main-desc-source.txt > /output/INPUT.before.stat

# One new small C/test ELF only; unchanged production/SDK/providers/ABI reused.
/usr/bin/cc -std=gnu11 -O2 -g -fPIC -fno-builtin -Wall -Wextra -Werror \
    -I/input -c /input/load-elf-nonelf-caller.c -o /output/caller.o \
    > /output/COMPILE.stdout 2> /output/COMPILE.stderr
/usr/bin/cc -g -fPIE -pie -Wl,--trace -Wl,--cref \
    -Wl,-Map=/output/load-elf-nonelf.map \
    -Wl,--dependency-file=/output/load-elf-nonelf.link.d \
    -Wl,--wrap=main -Wl,--wrap=fopen -Wl,--wrap=fread -Wl,--wrap=fclose \
    -Wl,--wrap=fflush -Wl,--wrap=malloc -Wl,--wrap=calloc -Wl,--wrap=realloc \
    -Wl,--wrap=free -Wl,--wrap=ioctl /output/caller.o /retained/changed-mcexec_helpers.o \
    -o /output/load-elf-nonelf -Wl,-rpath,/qualified-numa: /retained/libmcexec.a \
    /usr/lib64/librt.a /qualified-numa/libnuma.so -lpthread \
    > /output/LINK.stdout 2> /output/LINK.stderr

# Only new test entry/actualCRT/selected public load_elf boundary, no green inventory.
/usr/bin/nm --format=posix --extern-only --defined-only /output/load-elf-nonelf \
    > /output/metadata/caller-defined.nm
/usr/bin/objdump --disassemble=_start --reloc /output/load-elf-nonelf \
    > /output/metadata/caller-startup.objdump
for symbol in __wrap_main main load_elf; do
    [[ $(/usr/bin/grep -Ec "^${symbol} T " /output/metadata/caller-defined.nm) == 1 ]]
done
/usr/bin/grep -Eq 'lea[[:space:]].*%rdi.*<__wrap_main>' /output/metadata/caller-startup.objdump
/usr/bin/grep -q '__libc_start_main' /output/metadata/caller-startup.objdump

# Exact original C source is read as plain DATA only, not executed or recopied.
/output/load-elf-nonelf > /output/CASE.stdout 2> /output/CASE.stderr
printf '%s\n' 'mcexec_load_elfmag_mismatch_bridge: ELFMAG mismatched.' > /output/EXPECTED.stderr
[[ $(/usr/bin/wc -c < /output/EXPECTED.stderr) == 55 ]]
/usr/bin/cmp /output/EXPECTED.stderr /output/CASE.stderr
[[ $(/usr/bin/wc -l < /output/CASE.stdout) == 1 ]]
/usr/bin/grep -Fq '"case_pass":true}' /output/CASE.stdout
/usr/bin/stat -L --format='%n %d %i %f %s %Y %Z' /retained/main-desc-source.txt > /output/INPUT.after.stat
/usr/bin/cmp /output/INPUT.before.stat /output/INPUT.after.stat
/usr/bin/sha256sum /output/caller.o /output/load-elf-nonelf /output/load-elf-nonelf.map \
    /retained/changed-mcexec_helpers.o /retained/libmcexec.a /input/uprotocol.h \
    /input/load-elf-nonelf-caller.c /retained/main-desc-source.txt > /output/ARTIFACTS.sha256
printf '%s\n' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 '6d9d8306923ce129f5578b5ae3fac68e6d84e82046a9c4723bea4adbe99dccb1  /retained/main-desc-source.txt' \
 'ff6968cab1c07fb5ec7d6ea4679599de763a4987fa7e16442d7c9a7f694f2933  /input/load-elf-nonelf-caller.c' \
 'd511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445  /retained/changed-mcexec_helpers.o' \
 | /usr/bin/sha256sum --check > /output/INPUTS.after.sha256-check
printf '%s\n' 'One public load_elf non-ELF complete-header early guard only: output reset, exact real diagnostic/flush/NULL and borrowed FILE caller close. No descriptor allocation/free compensation, PHDR/GET_CREDV/ioctl/backend/productionmain/native or wholeF02 acceptance. Independent case/family Q and Root receipt required.' \
    > /output/LOAD-ELF-NONELF-COMPLETE
