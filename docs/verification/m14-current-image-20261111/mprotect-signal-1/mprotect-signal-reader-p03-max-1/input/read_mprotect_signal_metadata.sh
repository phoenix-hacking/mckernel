#!/usr/bin/bash
# Passive actual mprotect/signal4 image/ABI/table metadata only; never execute a target.
set -euo pipefail
set -o noclobber
umask 022
/usr/bin/test -s /work/output/build/kernel/mckernel.img
/usr/bin/test -s /work/output/build/kernel/mckernel.img.map
/usr/bin/test -s /work/output/build/tmp.resolve_MODULES_END/driver.ko
/usr/bin/readelf -W -h -l -S -n /work/output/build/kernel/mckernel.img > /evidence/image-elf.stdout
/usr/bin/readelf -W -s -r /work/output/build/kernel/mckernel.img > /evidence/image-symbols-relocations.stdout
/usr/bin/readelf -W -s -r /work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o /work/output/build/kernel/rust/mckernel_rust.o > /evidence/affected-constituent-symbols-relocations.stdout
/usr/bin/nm -n /work/output/build/kernel/mckernel.img > /evidence/image-nm.stdout
/usr/bin/cat /work/output/build/kernel/mckernel.img.map > /evidence/image-map.stdout
/usr/bin/sha256sum /work/output/build/config.h /work/output/build/ihk/config.h /work/output/build/kernel/config/smp-x86.lds /work/output/build/kernel/mckernel.img /work/output/build/kernel/mckernel.img.map /work/output/build/kernel/CMakeFiles/mckernel.img.dir/mem.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o /work/output/build/kernel/rust/mckernel_rust.o /work/output/build/tmp.resolve_MODULES_END/driver.ko > /evidence/artifact-identities.sha256
/usr/bin/stat '--format=%a %s %n' /work/output/build/config.h /work/output/build/ihk/config.h /work/output/build/kernel/config/smp-x86.lds /work/output/build/kernel/mckernel.img /work/output/build/kernel/mckernel.img.map /work/output/build/kernel/CMakeFiles/mckernel.img.dir/mem.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/rust/abi_checks.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/context.S.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/cpu.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/interrupt.S.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/memory.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o /work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/trampoline.S.o /work/output/build/kernel/rust/mckernel_rust.o /work/output/build/tmp.resolve_MODULES_END/driver.ko > /evidence/artifact-modes.stdout
/usr/bin/cat /work/output/build/CMakeCache.txt > /evidence/regenerated-CMakeCache.txt
/usr/bin/cat /work/output/build/compile_commands.json > /evidence/regenerated-compile_commands.json
/usr/bin/cat /work/output/build/kernel/CMakeFiles/mckernel.img.dir/flags.make > /evidence/regenerated-flags.make
/usr/bin/cat /work/output/build/kernel/CMakeFiles/mckernel.img.dir/build.make > /evidence/regenerated-build.make
/usr/bin/cat /work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.txt > /evidence/regenerated-link.txt
/usr/bin/cat /work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.d > /evidence/regenerated-link.d
/usr/bin/cat /work/output/build/kernel/rust/mckernel_rust.d > /evidence/regenerated-mckernel_rust.d
/usr/bin/cat /work/output/build/kernel/rust/mckernel_rust.raw.d > /evidence/regenerated-mckernel_rust.raw.d
/usr/bin/cat /work/output/build/kernel/CMakeFiles/mckernel_rust_obj.dir/build.make > /evidence/regenerated-Rust-build.make
/usr/bin/readelf -W -x .rodata /work/output/build/kernel/CMakeFiles/mckernel.img.dir/syscall.c.o > /evidence/C-tables-and-ABI-rodata.stdout
/usr/bin/readelf -W -x .lrodata.f03_do_fork_rust_abi_words /work/output/build/kernel/rust/mckernel_rust.o > /evidence/Rust-ABI104-rodata.stdout
/usr/bin/readelf -W -x .rodata /work/output/build/kernel/mckernel.img > /evidence/image-tables-and-ABI-rodata.stdout
/usr/bin/objdump -drw --disassemble=mprotect_set_host_vma_bridge /work/output/build/kernel/rust/mckernel_rust.o > /evidence/new-mprotect_set_host_vma_bridge-Rust-disassembly.stdout
/usr/bin/objdump -drw --disassemble=mprotect_set_host_vma_bridge /work/output/build/kernel/mckernel.img > /evidence/new-mprotect_set_host_vma_bridge-final-disassembly.stdout
/usr/bin/objdump -drw --disassemble=syscall_forward_context_bridge /work/output/build/kernel/rust/mckernel_rust.o > /evidence/new-syscall_forward_context_bridge-Rust-disassembly.stdout
/usr/bin/objdump -drw --disassemble=syscall_forward_context_bridge /work/output/build/kernel/mckernel.img > /evidence/new-syscall_forward_context_bridge-final-disassembly.stdout
/usr/bin/objdump -drw --disassemble=syscall_forward_rt_sigprocmask_bridge /work/output/build/kernel/rust/mckernel_rust.o > /evidence/new-syscall_forward_rt_sigprocmask_bridge-Rust-disassembly.stdout
/usr/bin/objdump -drw --disassemble=syscall_forward_rt_sigprocmask_bridge /work/output/build/kernel/mckernel.img > /evidence/new-syscall_forward_rt_sigprocmask_bridge-final-disassembly.stdout
/usr/bin/objdump -drw --disassemble=syscall_forward_sigaction_update_bridge /work/output/build/kernel/rust/mckernel_rust.o > /evidence/new-syscall_forward_sigaction_update_bridge-Rust-disassembly.stdout
/usr/bin/objdump -drw --disassemble=syscall_forward_sigaction_update_bridge /work/output/build/kernel/mckernel.img > /evidence/new-syscall_forward_sigaction_update_bridge-final-disassembly.stdout
