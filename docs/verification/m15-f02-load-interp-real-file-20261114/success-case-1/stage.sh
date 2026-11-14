#!/usr/bin/bash
# Functional McKernel OS/apps/Rust/allowed assembly only; NO SECURITY TESTING.
# SOURCE ONLY: genuine loader seal + distinct review/fresh Root admission first.
set -euo pipefail
umask 077
export LC_ALL=C LANG=C TZ=UTC TMPDIR=/output/tmp
ulimit -v 1048576
cd /output
[[ ${ROOT_ACTUAL_CHANGED_OBJECT_SHA256:-} == d511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445 ]]
# Actual data header and checksum-list identities must also be pinned in Root's
# future readonly source/input map; this gate does not invent their authority.
[[ -r /input/loader-input-seal.h && -r /input/LOADER-INPUTS.sha256 ]]
if [[ -e caller.o || -e load-interp-success || -e LOAD-INTERP-SUCCESS-COMPLETE ]]; then
    printf '%s\n' 'Refuse reused successful-interpreter output identity.' >&2
    exit 2
fi
/usr/bin/mkdir -p /output/tmp /output/metadata
printf '%s\n' \
 '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2  /usr/bin/cc' \
 'b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4  /lib64/libc.so.6' \
 'be20c2b16781eea6c69d47816bf15869f90f2a009628c310049da1d2f3c31e4e  /qualified-numa/libnuma.so' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 '5a8a8b03e6f7dc69a2a1976c9fc2182862bb08370dae35773f8917baf823cc51  /input/load-interp-success-caller.c' \
 'd511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445  /retained/changed-mcexec_helpers.o' \
 | /usr/bin/sha256sum --check > /output/INPUTS.before.sha256-check
/usr/bin/sha256sum --check /input/LOADER-INPUTS.sha256 > /output/LOADER.before.sha256-check
/usr/bin/stat -L --format='%n %d %i %f %s %Y %Z' /lib64/ld-linux-x86-64.so.2 \
    > /output/LOADER.before.stat

# Only this new small C and test ELF; production/SDK/ABI/provider work is reused.
/usr/bin/cc -std=gnu11 -O2 -g -fPIC -fno-builtin -Wall -Wextra -Werror \
    -I/input -c /input/load-interp-success-caller.c -o /output/caller.o \
    > /output/COMPILE.stdout 2> /output/COMPILE.stderr
/usr/bin/cc -g -fPIE -pie -Wl,--trace -Wl,--cref \
    -Wl,-Map=/output/load-interp-success.map \
    -Wl,--dependency-file=/output/load-interp-success.link.d \
    -Wl,--wrap=main -Wl,--wrap=fopen -Wl,--wrap=fclose -Wl,--wrap=fflush \
    -Wl,--wrap=malloc -Wl,--wrap=calloc -Wl,--wrap=realloc -Wl,--wrap=free \
    -Wl,--wrap=ioctl /output/caller.o /retained/changed-mcexec_helpers.o \
    -o /output/load-interp-success -Wl,-rpath,/qualified-numa: /retained/libmcexec.a \
    /usr/lib64/librt.a /qualified-numa/libnuma.so -lpthread \
    > /output/LINK.stdout 2> /output/LINK.stderr

# Only the new test ELF's actualCRT --wrap=main boundary.
/usr/bin/nm --format=posix --extern-only --defined-only /output/load-interp-success \
    > /output/metadata/caller-defined.nm
/usr/bin/objdump --disassemble=_start --reloc /output/load-interp-success \
    > /output/metadata/caller-startup.objdump
for symbol in __wrap_main main load_interp mcexec_load_alloc_desc_bridge; do
    [[ $(/usr/bin/grep -Ec "^${symbol} T " /output/metadata/caller-defined.nm) == 1 ]]
done
/usr/bin/grep -Eq 'lea[[:space:]].*%rdi.*<__wrap_main>' /output/metadata/caller-startup.objdump
/usr/bin/grep -q '__libc_start_main' /output/metadata/caller-startup.objdump

# ONE new successful interpreter publication case. Loader is read as data only.
/output/load-interp-success > /output/CASE.stdout 2> /output/CASE.stderr
[[ ! -s /output/CASE.stderr && $(/usr/bin/wc -l < /output/CASE.stdout) == 1 ]]
/usr/bin/grep -Fq '"case_pass":true}' /output/CASE.stdout
/usr/bin/sha256sum --check /input/LOADER-INPUTS.sha256 > /output/LOADER.after.sha256-check
/usr/bin/stat -L --format='%n %d %i %f %s %Y %Z' /lib64/ld-linux-x86-64.so.2 \
    > /output/LOADER.after.stat
/usr/bin/cmp /output/LOADER.before.stat /output/LOADER.after.stat
/usr/bin/sha256sum /output/caller.o /output/load-interp-success /output/load-interp-success.map \
    /retained/changed-mcexec_helpers.o /retained/libmcexec.a /input/uprotocol.h \
    /input/load-interp-success-caller.c /input/loader-input-seal.h /input/LOADER-INPUTS.sha256 \
    /lib64/ld-linux-x86-64.so.2 > /output/ARTIFACTS.sha256
printf '%s\n' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 '5a8a8b03e6f7dc69a2a1976c9fc2182862bb08370dae35773f8917baf823cc51  /input/load-interp-success-caller.c' \
 'd511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445  /retained/changed-mcexec_helpers.o' \
 | /usr/bin/sha256sum --check > /output/INPUTS.after.sha256-check
printf '%s\n' 'One genuine successful load_interp publication/returned-descriptor and borrowed FILE lifetime case only. Final descriptor free is caller-owned success cleanup, not a production error-cleanup claim. No oldfourcase/rejection replay, loader execution, production main/backend/phase1/native or wholeF02 credit. Independent result/family Q and Root receipt required.' \
    > /output/LOAD-INTERP-SUCCESS-COMPLETE
