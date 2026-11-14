#!/usr/bin/bash
# Functional McKernel OS/apps/Rust/allowed assembly ONLY; NO SECURITY TESTING.
# SOURCE ONLY: distinct source/operation reviews and fresh Root admission first.
set -euo pipefail
umask 077
export LC_ALL=C LANG=C TZ=UTC TMPDIR=/output/tmp
ulimit -v 1048576
cd /output
[[ ${ROOT_ACTUAL_CHANGED_OBJECT_SHA256:-} == d511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445 ]]
if [[ -e caller.o || -e main-desc-host || -e MAIN-DESC-STAGE-COMPLETE ]]; then
    printf '%s\n' 'Refuse reused main-descriptor output identity.' >&2
    exit 2
fi
/usr/bin/mkdir -p /output/tmp /output/metadata
printf '%s\n' \
 '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2  /usr/bin/cc' \
 'b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4  /lib64/libc.so.6' \
 'be20c2b16781eea6c69d47816bf15869f90f2a009628c310049da1d2f3c31e4e  /qualified-numa/libnuma.so' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 '6d9d8306923ce129f5578b5ae3fac68e6d84e82046a9c4723bea4adbe99dccb1  /input/main-desc-host-caller.c' \
 'd511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445  /retained/changed-mcexec_helpers.o' \
 | /usr/bin/sha256sum --check > /output/INPUTS.before.sha256-check

# Only a new small C observer and test ELF; no Rust/production/provider rebuild.
/usr/bin/cc -std=gnu11 -O2 -g -fPIC -fno-builtin -Wall -Wextra -Werror \
    -I/input -c /input/main-desc-host-caller.c -o /output/caller.o \
    > /output/COMPILE.stdout 2> /output/COMPILE.stderr
/usr/bin/cc -g -fPIE -pie -Wl,--trace -Wl,--cref \
    -Wl,-Map=/output/main-desc-host.map \
    -Wl,--dependency-file=/output/main-desc-host.link.d \
    -Wl,--wrap=main -Wl,--wrap=malloc -Wl,--wrap=calloc -Wl,--wrap=realloc \
    -Wl,--wrap=free -Wl,--wrap=getrlimit -Wl,--wrap=ioctl \
    /output/caller.o /retained/changed-mcexec_helpers.o -o /output/main-desc-host \
    -Wl,-rpath,/qualified-numa: /retained/libmcexec.a /usr/lib64/librt.a \
    /qualified-numa/libnuma.so -lpthread > /output/LINK.stdout 2> /output/LINK.stderr

# Only this newly linked test's realCRT/selected public callable boundary.
/usr/bin/nm --format=posix --extern-only --defined-only /output/main-desc-host \
    > /output/metadata/caller-defined.nm
/usr/bin/objdump --disassemble=_start --reloc /output/main-desc-host \
    > /output/metadata/caller-startup.objdump
for symbol in __wrap_main main mcexec_prepare_main_desc_body mcexec_flatten_strings_result mcexec_load_alloc_desc_bridge; do
    [[ $(/usr/bin/grep -Ec "^${symbol} T " /output/metadata/caller-defined.nm) == 1 ]]
done
/usr/bin/grep -Eq 'lea[[:space:]].*%rdi.*<__wrap_main>' /output/metadata/caller-startup.objdump
/usr/bin/grep -q '__libc_start_main' /output/metadata/caller-startup.objdump

# ONE new normal preparation case; stop before finish_main_image/PREPARE_IMAGE.
/output/main-desc-host > /output/CASE.stdout 2> /output/CASE.stderr
[[ ! -s /output/CASE.stderr && $(/usr/bin/wc -l < /output/CASE.stdout) == 1 ]]
/usr/bin/grep -Fq '"case_pass":true}' /output/CASE.stdout
/usr/bin/sha256sum /output/caller.o /output/main-desc-host /output/main-desc-host.map \
    /retained/changed-mcexec_helpers.o /retained/libmcexec.a /input/uprotocol.h \
    /input/main-desc-host-caller.c > /output/ARTIFACTS.sha256
printf '%s\n' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 '6d9d8306923ce129f5578b5ae3fac68e6d84e82046a9c4723bea4adbe99dccb1  /input/main-desc-host-caller.c' \
 'd511b91b230c1ccb4f84ff00de6ed8b5a770829373d2f81ca752d22f09dce445  /retained/changed-mcexec_helpers.o' \
 | /usr/bin/sha256sum --check > /output/INPUTS.after.sha256-check
printf '%s\n' 'One actual main-descriptor rlimit/env/args/CPU/vDSO/ownership preparation case only. Prefix and temporary production frees must occur after real publication/copy; args/env/descriptor cleanup is documented caller ownership, never compensation. No finish_main_image/PREPARE_IMAGE/ioctl/backend/productionmain/phase1/native or wholeF02 credit. Independent result/family Q and Root receipt required.' \
    > /output/MAIN-DESC-STAGE-COMPLETE
