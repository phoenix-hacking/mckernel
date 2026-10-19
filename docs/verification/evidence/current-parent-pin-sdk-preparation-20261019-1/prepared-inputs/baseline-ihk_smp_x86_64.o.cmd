savedcmd_drivers/misc/mckernel/ihk_smp_x86_64.o := RUST_MODFILE=drivers/misc/mckernel/ihk-smp-x86_64 rustc --edition=2021 -Zbinary_dep_depinfo=y -Astable_features -Dunsafe_op_in_unsafe_fn -Dnon_ascii_idents -Wrust_2018_idioms -Wunreachable_pub -Wmissing_docs -Wrustdoc::missing_crate_level_docs -Wclippy::all -Wclippy::mut_mut -Wclippy::needless_bitwise_bool -Wclippy::needless_continue -Wclippy::no_mangle_with_rust_abi -Wclippy::dbg_macro -Cpanic=abort -Cembed-bitcode=n -Clto=n -Cforce-unwind-tables=n -Ccodegen-units=1 -Csymbol-mangling-version=v0 -Crelocation-model=static -Zfunction-sections=n -Wclippy::float_arithmetic --target=./scripts/target.json -Ctarget-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2 -Zcf-protection=branch -Zno-jump-tables -Ztune-cpu=generic -Cno-redzone=y -Ccode-model=kernel -Zfunction-return=thunk-extern -Zpatchable-function-entry=16,16 -Copt-level=2 -Cdebug-assertions=n -Coverflow-checks=n -Dwarnings -Cdebuginfo=2  --cfg MODULE  @./include/generated/rustc_cfg -Zallow-features=arbitrary_self_types,new_uninit,used_with_arg -Zcrate-attr=no_std -Zcrate-attr='feature(arbitrary_self_types,new_uninit,used_with_arg)' -Zunstable-options --extern force:alloc --extern kernel --crate-type rlib -L ./rust/ --crate-name ihk_smp_x86_64 --sysroot=/dev/null --out-dir drivers/misc/mckernel/ --emit=dep-info=drivers/misc/mckernel/.ihk_smp_x86_64.o.d --emit=obj=drivers/misc/mckernel/ihk_smp_x86_64.o /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk_smp_x86_64.rs 

source_drivers/misc/mckernel/ihk_smp_x86_64.o := /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk_smp_x86_64.rs

deps_drivers/misc/mckernel/ihk_smp_x86_64.o := \
    $(wildcard include/config/COMPAT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_resource.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_cpu.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/abi/x86_64.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_topology.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_memory.rs \
    $(wildcard include/config/NUMA) \
    $(wildcard include/config/SPARSEMEM_VMEMMAP) \
    $(wildcard include/config/MEMORY_HOTPLUG) \
    $(wildcard include/config/DYNAMIC_MEMORY_LAYOUT) \
    $(wildcard include/config/X86_5LEVEL) \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_service.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/sysfs_memory.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/sysfs_zeroing.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_procfs.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/sysfs_snoop.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/procfs_objects.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk_mapping.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_image.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_loader.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/user_string.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_startup.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_trampoline.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_boot_code.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ikc_queue.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ikc_master.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_ikc.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/abi/vdso.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_vdso.rs \
    $(wildcard include/config/PARAVIRT_CLOCK) \
    $(wildcard include/config/HYPERV_TIMER) \
    $(wildcard include/config/AMD_MEM_ENCRYPT) \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/sysfs_objects.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/sysfs_os.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/sysfs_tree.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/sysfs_setup.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/abi/sysfs.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/abi/sysfs_request.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/sysfs_rpc.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/sysfs_remote.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/abi/application.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/application_rpc.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/application_syscall.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/application_image.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_application.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_application_syscall.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_application_image.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/application_pager.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_file_pager.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/zero_pages.rs \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_trampoline.S \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/smp_startup_entry.S \
  /out/source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk-compat-build-id.bin \
  ./rust/libcore.rmeta \
  ./rust/libkernel.rmeta \
  ./rust/liballoc.rmeta \
  ./rust/libcompiler_builtins.rmeta \
  ./rust/libmacros.so \
  ./rust/libbindings.rmeta \
  ./rust/libuapi.rmeta \
  ./rust/libbuild_error.rmeta \

drivers/misc/mckernel/ihk_smp_x86_64.o: $(deps_drivers/misc/mckernel/ihk_smp_x86_64.o)

$(deps_drivers/misc/mckernel/ihk_smp_x86_64.o):
