savedcmd_drivers/misc/mckernel/mcctrl_rust.o := RUST_MODFILE=drivers/misc/mckernel/mcctrl rustc --edition=2021 -Zbinary_dep_depinfo=y -Astable_features -Dunsafe_op_in_unsafe_fn -Dnon_ascii_idents -Wrust_2018_idioms -Wunreachable_pub -Wmissing_docs -Wrustdoc::missing_crate_level_docs -Wclippy::all -Wclippy::mut_mut -Wclippy::needless_bitwise_bool -Wclippy::needless_continue -Wclippy::no_mangle_with_rust_abi -Wclippy::dbg_macro -Cpanic=abort -Cembed-bitcode=n -Clto=n -Cforce-unwind-tables=n -Ccodegen-units=1 -Csymbol-mangling-version=v0 -Crelocation-model=static -Zfunction-sections=n -Wclippy::float_arithmetic --target=./scripts/target.json -Ctarget-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2 -Zcf-protection=branch -Zno-jump-tables -Ztune-cpu=generic -Cno-redzone=y -Ccode-model=kernel -Zfunction-return=thunk-extern -Zpatchable-function-entry=16,16 -Copt-level=2 -Cdebug-assertions=n -Coverflow-checks=n -Dwarnings -Cdebuginfo=2 --check-cfg 'cfg(mckernel_current_fork_adoption_opt_in)' --check-cfg 'cfg(MODULE)' --check-cfg 'cfg(m15_fixture)' --check-cfg 'cfg(CONFIG_X86_64, CONFIG_SMP, CONFIG_PER_VMA_LOCK, CONFIG_TRACING, CONFIG_MEMCG, CONFIG_HAVE_JUMP_LABEL_HACK, CONFIG_KCSAN, CONFIG_DEBUG_LOCK_ALLOC, CONFIG_DEBUG_VM, CONFIG_LOCKDEP, CONFIG_NOINSTR_VALIDATION, CONFIG_PREEMPT_RT, CONFIG_TRACEPOINTS, CONFIG_JUMP_LABEL, CONFIG_OBJTOOL, CONFIG_GENERIC_BUG, CONFIG_GENERIC_BUG_RELATIVE_POINTERS, CONFIG_DEBUG_BUGVERBOSE, CONFIG_BUG, values(none(), "y", "m", "n"))'  --cfg MODULE  @./include/generated/rustc_cfg -Zallow-features=arbitrary_self_types,new_uninit,used_with_arg -Zcrate-attr=no_std -Zcrate-attr='feature(arbitrary_self_types,new_uninit,used_with_arg)' -Zunstable-options --extern force:alloc --extern kernel --crate-type rlib -L ./rust/ --crate-name mcctrl_rust --sysroot=/dev/null --out-dir drivers/misc/mckernel/ --emit=dep-info=drivers/misc/mckernel/.mcctrl_rust.o.d --emit=obj=drivers/misc/mckernel/mcctrl_rust.o /source/drivers/misc/mckernel/mcctrl_rust.rs 

source_drivers/misc/mckernel/mcctrl_rust.o := /source/drivers/misc/mckernel/mcctrl_rust.rs

deps_drivers/misc/mckernel/mcctrl_rust.o := \
  /source/drivers/misc/mckernel/mcctrl_exec.rs \
  /source/drivers/misc/mckernel/mcctrl_process.rs \
  /source/drivers/misc/mckernel/current_fork_host.rs \
  /source/drivers/misc/mckernel/mcctrl_vm.rs \
  /source/drivers/misc/mckernel/mcctrl_mm_write.rs \
    $(wildcard include/config/UNDECLARED_MCCTRL_CONFIG) \
    $(wildcard include/config/SMP) \
    $(wildcard include/config/PER_VMA_LOCK) \
    $(wildcard include/config/TRACING) \
    $(wildcard include/config/MEMCG) \
    $(wildcard include/config/HAVE_JUMP_LABEL_HACK) \
    $(wildcard include/config/KCSAN) \
    $(wildcard include/config/DEBUG_LOCK_ALLOC) \
    $(wildcard include/config/DEBUG_VM) \
    $(wildcard include/config/LOCKDEP) \
    $(wildcard include/config/NOINSTR_VALIDATION) \
    $(wildcard include/config/PREEMPT_RT) \
    $(wildcard include/config/TRACEPOINTS) \
    $(wildcard include/config/JUMP_LABEL) \
    $(wildcard include/config/OBJTOOL) \
    $(wildcard include/config/GENERIC_BUG) \
    $(wildcard include/config/GENERIC_BUG_RELATIVE_POINTERS) \
    $(wildcard include/config/DEBUG_BUGVERBOSE) \
    $(wildcard include/config/BUG) \
  /source/drivers/misc/mckernel/user_string.rs \
  /source/drivers/misc/mckernel/application_image.rs \
  /source/drivers/misc/mckernel/abi/x86_64.rs \
  /source/drivers/misc/mckernel/abi/os_service.rs \
  /source/drivers/misc/mckernel/abi/application.rs \
  ./rust/libcore.rmeta \
  ./rust/libkernel.rmeta \
  ./rust/liballoc.rmeta \
  ./rust/libcompiler_builtins.rmeta \
  ./rust/libmacros.so \
  ./rust/libbindings.rmeta \
  ./rust/libuapi.rmeta \
  ./rust/libbuild_error.rmeta \

drivers/misc/mckernel/mcctrl_rust.o: $(deps_drivers/misc/mckernel/mcctrl_rust.o)

$(deps_drivers/misc/mckernel/mcctrl_rust.o):
