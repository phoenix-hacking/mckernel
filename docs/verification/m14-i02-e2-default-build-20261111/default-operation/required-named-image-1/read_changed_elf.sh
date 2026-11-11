#!/usr/bin/bash
# Conditional new-byte readback only; no image/module/program execution.
set -euo pipefail
set -o noclobber
umask 022
changed=0
value=$(/usr/bin/sha256sum /work/output/build/kernel/mckernel.img)
value=${value%% *}
if [[ "$value" != 100d078609104b9853b14705fb3d0ee6ef4d6597101e5dad3f948ae46a94a5e2 ]]; then
    changed=1
    /usr/bin/readelf -W -h -l -S -n /work/output/build/kernel/mckernel.img > /evidence/changed-image-headers.stdout
    /usr/bin/readelf -W -s -r /work/output/build/kernel/mckernel.img > /evidence/changed-image-symbols-relocations.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/mckernel.img.map)
value=${value%% *}
if [[ "$value" != 6f11926be391d76579a60f37a60297585c629b81f980a844e4c70f60b39c6cd9 ]]; then
    changed=1
    /usr/bin/cat /work/output/build/kernel/mckernel.img.map > /evidence/changed-image-map.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/mem.c.o)
value=${value%% *}
if [[ "$value" != 4b595744494abba0493d75a1475e48b3745e1a668f5575543e81797b994e4f7c ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/mem.c.o > /evidence/changed-object-5.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o)
value=${value%% *}
if [[ "$value" != 7559299363060b0cafbbec97ed2b00412fa71c19bc4caf17caa7478adfaf5e38 ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o > /evidence/changed-object-6.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o)
value=${value%% *}
if [[ "$value" != 3717ed77bd1761c734e93a72d4e5a0b770698f17760470286019f6ec6a6973dd ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o > /evidence/changed-object-7.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o)
value=${value%% *}
if [[ "$value" != e139686acfa04f6d7576da5656693d13c4235e5beefb7f8ae3c9f7ccf03ea9b0 ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o > /evidence/changed-object-8.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o)
value=${value%% *}
if [[ "$value" != dce0972b3291f970d49a5fa6d64f25c587423aafa63efc8b47bcfdbdfb679c7a ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o > /evidence/changed-object-9.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o)
value=${value%% *}
if [[ "$value" != 3bed7de9807b6d8e70e87722a11b3d103119203822b9e022ebd0ecbc570bbce1 ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o > /evidence/changed-object-10.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o)
value=${value%% *}
if [[ "$value" != 66bcbec1fc5086cac18a8009f0e1b36ecaba7bf11f38cadd5de9f03e3873ee44 ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o > /evidence/changed-object-11.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o)
value=${value%% *}
if [[ "$value" != d3207c7a7844086196676c82d66e6aa4f1233e37b167460e23ba089ec71aca85 ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o > /evidence/changed-object-12.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o)
value=${value%% *}
if [[ "$value" != 9c4761b951ed58bbfc9c732d5d8cb844ca90751397686e2e25988d6252b0b972 ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o > /evidence/changed-object-13.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o)
value=${value%% *}
if [[ "$value" != ebd728290101289164a887deb52dc7977d896e9627a2cb1323fd649db89055c5 ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o > /evidence/changed-object-14.ELF.stdout
fi
value=$(/usr/bin/sha256sum /work/output/build/kernel/rust/mckernel_rust.o)
value=${value%% *}
if [[ "$value" != 4a1f34064c238e7cf9ccf21ca06c0219300b226fbdcf7b69abe082efe94c2912 ]]; then
    changed=1
    /usr/bin/readelf -W -h -S -s -r /work/output/build/kernel/rust/mckernel_rust.o > /evidence/changed-object-15.ELF.stdout
fi
[[ "$changed" == 1 ]]
printf "%s\n" "PASS_CHANGED_BYTE_PASSIVE_READ_ONLY" > /evidence/STATUS
