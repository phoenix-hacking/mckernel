savedcmd_/candidate/modules/ihk_smp_x86_64.o := RUST_MODFILE=/candidate/modules/ihk-smp-x86_64 rustc --edition=2021 -Zbinary_dep_depinfo=y -Astable_features -Dunsafe_op_in_unsafe_fn -Dnon_ascii_idents -Wrust_2018_idioms -Wunreachable_pub -Wmissing_docs -Wrustdoc::missing_crate_level_docs -Wclippy::all -Wclippy::mut_mut -Wclippy::needless_bitwise_bool -Wclippy::needless_continue -Wclippy::no_mangle_with_rust_abi -Wclippy::dbg_macro -Cpanic=abort -Cembed-bitcode=n -Clto=n -Cforce-unwind-tables=n -Ccodegen-units=1 -Csymbol-mangling-version=v0 -Crelocation-model=static -Zfunction-sections=n -Wclippy::float_arithmetic --target=./scripts/target.json -Ctarget-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2 -Zcf-protection=branch -Zno-jump-tables -Ztune-cpu=generic -Cno-redzone=y -Ccode-model=kernel -Zfunction-return=thunk-extern -Zpatchable-function-entry=16,16 -Copt-level=2 -Cdebug-assertions=n -Coverflow-checks=n -Dwarnings -Cdebuginfo=2  --cfg MODULE  @./include/generated/rustc_cfg -Zallow-features=arbitrary_self_types,new_uninit,used_with_arg -Zcrate-attr=no_std -Zcrate-attr='feature(arbitrary_self_types,new_uninit,used_with_arg)' -Zunstable-options --extern force:alloc --extern kernel --crate-type rlib -L ./rust/ --crate-name ihk_smp_x86_64 --sysroot=/dev/null --out-dir /candidate/modules/ --emit=dep-info=/candidate/modules/.ihk_smp_x86_64.o.d --emit=obj=/candidate/modules/ihk_smp_x86_64.o /candidate/modules/ihk_smp_x86_64.rs 

source_/candidate/modules/ihk_smp_x86_64.o := /candidate/modules/ihk_smp_x86_64.rs

deps_/candidate/modules/ihk_smp_x86_64.o := \
    $(wildcard include/config/COMPAT) \
  /candidate/modules/smp_resource.rs \
  /candidate/modules/smp_cpu.rs \
  /candidate/modules/abi/x86_64.rs \
  /candidate/modules/smp_topology.rs \
  /candidate/modules/smp_memory.rs \
    $(wildcard include/config/NUMA) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
    $(wildcard include/config/MEMORY_HOTPLUG) \
    $(wildcard include/config/DYNAMIC_MEMORY_LAYOUT) \
    $(wildcard include/config/X86_5LEVEL) \
  /candidate/modules/smp_service.rs \
  /candidate/modules/sysfs_memory.rs \
  /candidate/modules/sysfs_zeroing.rs \
  /candidate/modules/smp_procfs.rs \
  /candidate/modules/sysfs_snoop.rs \
  /candidate/modules/procfs_objects.rs \
  /candidate/modules/ihk_mapping.rs \
  /candidate/modules/smp_image.rs \
  /candidate/modules/smp_loader.rs \
  /candidate/modules/user_string.rs \
  /candidate/modules/smp_startup.rs \
  /candidate/modules/smp_trampoline.rs \
  /candidate/modules/smp_boot_code.rs \
  /candidate/modules/ikc_queue.rs \
  /candidate/modules/ikc_master.rs \
  /candidate/modules/smp_ikc.rs \
  /candidate/modules/abi/vdso.rs \
  /candidate/modules/smp_vdso.rs \
    $(wildcard include/config/PARAVIRT_CLOCK) \
    $(wildcard include/config/HYPERV_TIMER) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
  /candidate/modules/sysfs_objects.rs \
  /candidate/modules/sysfs_os.rs \
  /candidate/modules/sysfs_tree.rs \
  /candidate/modules/sysfs_setup.rs \
  /candidate/modules/abi/sysfs.rs \
  /candidate/modules/abi/sysfs_request.rs \
  /candidate/modules/sysfs_rpc.rs \
  /candidate/modules/sysfs_remote.rs \
  /candidate/modules/abi/application.rs \
  /candidate/modules/application_rpc.rs \
  /candidate/modules/application_syscall.rs \
  /candidate/modules/application_image.rs \
  /candidate/modules/exec_transfer_checked.rs \
  /candidate/modules/exec_delivery.rs \
  /candidate/modules/smp_application.rs \
  /candidate/modules/current_fork_task_mm.rs \
  /candidate/modules/current_fork_control.rs \
  /candidate/modules/smp_application_syscall.rs \
  /candidate/modules/smp_application_image.rs \
  /candidate/modules/application_pager.rs \
  /candidate/modules/smp_file_pager.rs \
  /candidate/modules/zero_pages.rs \
  /candidate/modules/smp_trampoline.S \
  /candidate/modules/smp_startup_entry.S \
  /candidate/modules/ihk-compat-build-id.bin \
  ./rust/libcore.rmeta \
  ./rust/libkernel.rmeta \
  ./rust/liballoc.rmeta \
  ./rust/libcompiler_builtins.rmeta \
  ./rust/libmacros.so \
  ./rust/libbindings.rmeta \
  ./rust/libuapi.rmeta \
  ./rust/libbuild_error.rmeta \

/candidate/modules/ihk_smp_x86_64.o: $(deps_/candidate/modules/ihk_smp_x86_64.o)

$(deps_/candidate/modules/ihk_smp_x86_64.o):
