#!/usr/bin/bash
# Functional McKernel OS/apps/Rust only; NO SECURITY TESTING.
# SOURCE ONLY: actual new producer qualification + separate Root admission first.
set -euo pipefail
umask 077
export LC_ALL=C LANG=C TZ=UTC TMPDIR=/output/tmp
ulimit -v 1048576
cd /output
if [[ ! ${ROOT_ACTUAL_CHANGED_OBJECT_SHA256:-} =~ ^[0-9a-f]{64}$ ]]; then
    printf '%s\n' 'Require Root actual qualified changed-object identity.' >&2
    exit 2
fi
if [[ $ROOT_ACTUAL_CHANGED_OBJECT_SHA256 == b245426d68723200ad11f0523f6231568e08eb935f69fd22f92faf8200dfa57b ||
      $ROOT_ACTUAL_CHANGED_OBJECT_SHA256 == 122ffbef83fc563554dcc57c6da3580f881ecda421e8d37e063ab3b2b787500e ]]; then
    printf '%s\n' 'Reject frozen old production objects as repaired evidence.' >&2
    exit 2
fi
if [[ -e caller.o || -e shebang-host || -e input.shebang || -e outer.shebang ||
      -e inner.shebang || -e eof.shebang || -e SHEBANG-STAGE-COMPLETE ]]; then
    printf '%s\n' 'Refuse reused output/case identity.' >&2
    exit 2
fi
/usr/bin/mkdir -p /output/tmp /output/metadata
printf '%s\n' \
 '2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2  /usr/bin/cc' \
 'b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4  /lib64/libc.so.6' \
 'be20c2b16781eea6c69d47816bf15869f90f2a009628c310049da1d2f3c31e4e  /qualified-numa/libnuma.so' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 '240cb874d687455c44dbfb7848270b22079fc0f3f2596142a7d50a9c161fe627  /input/shebang-host-caller.c' \
 | /usr/bin/sha256sum --check > /output/INPUTS.before.sha256-check
printf '%s  %s\n' "$ROOT_ACTUAL_CHANGED_OBJECT_SHA256" /retained/changed-mcexec_helpers.o \
 | /usr/bin/sha256sum --check > /output/CHANGED-OBJECT.before.sha256-check

# Only this changed C observer is compiled here. DispatchSource owns the one
# changed Rust production A+B producer; this consumer never rebuilds either.
/usr/bin/cc -std=gnu11 -O2 -g -fPIC -fno-builtin -Wall -Wextra -Werror \
    -I/input -c /input/shebang-host-caller.c -o /output/caller.o \
    > /output/COMPILE.stdout 2> /output/COMPILE.stderr
/usr/bin/cc -g -fPIE -pie -Wl,--trace -Wl,--cref \
    -Wl,-Map=/output/shebang-host.map \
    -Wl,--dependency-file=/output/shebang-host.link.d \
    -Wl,--wrap=main -Wl,--wrap=fopen -Wl,--wrap=getline \
    -Wl,--wrap=fclose -Wl,--wrap=malloc -Wl,--wrap=free -Wl,--wrap=ioctl \
    /output/caller.o /retained/changed-mcexec_helpers.o -o /output/shebang-host \
    -Wl,-rpath,/qualified-numa: /retained/libmcexec.a \
    /usr/lib64/librt.a /qualified-numa/libnuma.so -lpthread \
    > /output/LINK.stdout 2> /output/LINK.stderr

# NEW test-entry/startup facts, not reruns of existing provider/ABI inventories.
/usr/bin/nm --format=posix --extern-only --defined-only /output/shebang-host \
    > /output/metadata/caller-defined.nm
/usr/bin/objdump --disassemble=_start --reloc /output/shebang-host \
    > /output/metadata/caller-startup.objdump
for symbol in __wrap_main main load_elf_desc load_elf_desc_shebang mcexec_load_main_desc_body; do
    [[ $(/usr/bin/grep -Ec "^${symbol} T " /output/metadata/caller-defined.nm) == 1 ]]
done
/usr/bin/grep -Eq 'lea[[:space:]].*%rdi.*<__wrap_main>' /output/metadata/caller-startup.objdump
/usr/bin/grep -q '__libc_start_main' /output/metadata/caller-startup.objdump

# Four fixed affected paths, real regular files/libc, no synthetic failures or
# backend/provider behavior. Unexpected ioctl is a nonreturning refusal.
/output/shebang-host > /output/CASE.stdout 2> /output/CASE.stderr
/usr/bin/od -An -tx1 /output/input.shebang > /output/INPUT.direct.hex
/usr/bin/od -An -tx1 /output/outer.shebang > /output/INPUT.outer.hex
/usr/bin/od -An -tx1 /output/inner.shebang > /output/INPUT.inner.hex
/usr/bin/od -An -tx1 /output/eof.shebang > /output/INPUT.eof.hex
/usr/bin/stat --format='%n %s %a' /output/input.shebang /output/outer.shebang \
    /output/inner.shebang /output/eof.shebang > /output/INPUTS.stat
/usr/bin/sha256sum /output/caller.o /output/shebang-host /output/shebang-host.map \
    /output/input.shebang /output/outer.shebang /output/inner.shebang /output/eof.shebang \
    /retained/changed-mcexec_helpers.o /retained/libmcexec.a \
    /input/uprotocol.h /input/shebang-host-caller.c > /output/ARTIFACTS.sha256
printf '%s  %s\n' "$ROOT_ACTUAL_CHANGED_OBJECT_SHA256" /retained/changed-mcexec_helpers.o \
 | /usr/bin/sha256sum --check > /output/CHANGED-OBJECT.after.sha256-check
printf '%s\n' \
 'eb866f7f55d69d6af481daa90ceaa4e319201f65c7b14925fd1b86a1d7356ddc  /retained/libmcexec.a' \
 '1770a59cf4486380eb5aa483d3634dc1e4c9c9c16d1bf09865d4ff8f71191e69  /input/uprotocol.h' \
 '240cb874d687455c44dbfb7848270b22079fc0f3f2596142a7d50a9c161fe627  /input/shebang-host-caller.c' \
 | /usr/bin/sha256sum --check > /output/INPUTS.after.sha256-check
printf '%s\n' 'Changed-object HOST observations returned zero; exact changed-result and Root capture/family qualification remain required. Direct public-base caller free is distinct from production recursive/main-error frees; later backend-dependent branches remain unobserved.' \
    > /output/SHEBANG-STAGE-COMPLETE
