savedcmd_/candidate/modules/mcctrl_rust.o := RUST_MODFILE=/candidate/modules/mcctrl rustc --edition=2021 -Zbinary_dep_depinfo=y -Astable_features -Dunsafe_op_in_unsafe_fn -Dnon_ascii_idents -Wrust_2018_idioms -Wunreachable_pub -Wmissing_docs -Wrustdoc::missing_crate_level_docs -Wclippy::all -Wclippy::mut_mut -Wclippy::needless_bitwise_bool -Wclippy::needless_continue -Wclippy::no_mangle_with_rust_abi -Wclippy::dbg_macro -Cpanic=abort -Cembed-bitcode=n -Clto=n -Cforce-unwind-tables=n -Ccodegen-units=1 -Csymbol-mangling-version=v0 -Crelocation-model=static -Zfunction-sections=n -Wclippy::float_arithmetic --target=./scripts/target.json -Ctarget-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2 -Zcf-protection=branch -Zno-jump-tables -Ztune-cpu=generic -Cno-redzone=y -Ccode-model=kernel -Zfunction-return=thunk-extern -Zpatchable-function-entry=16,16 -Copt-level=2 -Cdebug-assertions=n -Coverflow-checks=n -Dwarnings -Cdebuginfo=2 --check-cfg 'cfg(MODULE)' --check-cfg 'cfg(mckernel_current_fork_adoption_opt_in)' --cfg mckernel_current_fork_adoption_opt_in  --cfg MODULE  @./include/generated/rustc_cfg -Zallow-features=arbitrary_self_types,new_uninit,used_with_arg -Zcrate-attr=no_std -Zcrate-attr='feature(arbitrary_self_types,new_uninit,used_with_arg)' -Zunstable-options --extern force:alloc --extern kernel --crate-type rlib -L ./rust/ --crate-name mcctrl_rust --sysroot=/dev/null --out-dir /candidate/modules/ --emit=dep-info=/candidate/modules/.mcctrl_rust.o.d --emit=obj=/candidate/modules/mcctrl_rust.o /candidate/modules/mcctrl_rust.rs 

source_/candidate/modules/mcctrl_rust.o := /candidate/modules/mcctrl_rust.rs

deps_/candidate/modules/mcctrl_rust.o := \
  /candidate/modules/mcctrl_exec.rs \
  /candidate/modules/mcctrl_process.rs \
  /candidate/modules/current_fork_host.rs \
  /candidate/modules/mcctrl_vm.rs \
  /candidate/modules/user_string.rs \
  /candidate/modules/application_image.rs \
  /candidate/modules/abi/x86_64.rs \
  /candidate/modules/abi/os_service.rs \
  /candidate/modules/abi/application.rs \
  ./rust/libcore.rmeta \
  ./rust/libkernel.rmeta \
  ./rust/liballoc.rmeta \
  ./rust/libcompiler_builtins.rmeta \
  ./rust/libmacros.so \
  ./rust/libbindings.rmeta \
  ./rust/libuapi.rmeta \
  ./rust/libbuild_error.rmeta \

/candidate/modules/mcctrl_rust.o: $(deps_/candidate/modules/mcctrl_rust.o)

$(deps_/candidate/modules/mcctrl_rust.o):
